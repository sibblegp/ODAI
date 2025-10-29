import asyncio
import base64
import json
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import WebSocket

from routers.twilio_handler import TwilioHandler, logger


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket for testing."""
    websocket = MagicMock(spec=WebSocket)
    websocket.accept = AsyncMock()
    websocket.receive_text = AsyncMock()
    websocket.send_text = AsyncMock()
    websocket.send_json = AsyncMock()
    return websocket


@pytest.fixture
def mock_settings():
    """Create mock settings with OpenAI API key."""
    with patch('routers.twilio_handler.Settings') as mock_settings_class:
        settings = MagicMock()
        settings.openai_api_key = "test-api-key"
        mock_settings_class.return_value = settings
        yield settings


@pytest.fixture
def mock_realtime_session():
    """Create a mock RealtimeSession."""
    session = MagicMock()
    session.enter = AsyncMock()
    session.send_message = AsyncMock()
    session.send_audio = AsyncMock()
    return session


@pytest.fixture
def mock_runner():
    """Create a mock RealtimeRunner."""
    with patch('routers.twilio_handler.RealtimeRunner') as mock_runner_class:
        runner = MagicMock()
        mock_runner_class.return_value = runner
        yield runner


@pytest.fixture
def mock_user():
    """Create a mock User object."""
    user = MagicMock()
    user.reference_id = "test_user_123"
    user.email = "test@example.com"
    return user


class TestTwilioHandler:
    """Test cases for TwilioHandler class."""
    
    def test_init(self, mock_websocket, mock_user):
        """Test TwilioHandler initialization."""
        with patch('routers.twilio_handler.Client'):
            handler = TwilioHandler(mock_websocket, mock_user)
        
        assert handler.twilio_websocket == mock_websocket
        assert handler._message_loop_task is None
        assert handler.session is None
        assert handler.call_sids is None
        assert isinstance(handler.contexts, dict)
        assert handler.playing_sound is None
        
        # Audio buffering configuration
        assert handler.CHUNK_LENGTH_S == 0.05
        assert handler.SAMPLE_RATE == 8000
        assert handler.BUFFER_SIZE_BYTES == 400
        
        assert handler._stream_sid is None
        assert isinstance(handler._audio_buffer, bytearray)
        assert handler._mark_counter == 0
        assert isinstance(handler._mark_data, dict)
    
    @pytest.mark.asyncio
    async def test_start_success(self, mock_websocket, mock_user, mock_settings, mock_runner, mock_realtime_session):
        """Test successful session start."""
        handler = TwilioHandler(mock_websocket, mock_user)
        
        # Mock the runner.run method to return our mock session
        mock_runner.run = AsyncMock(return_value=mock_realtime_session)
        
        # Mock asyncio tasks
        with patch('asyncio.create_task') as mock_create_task:
            mock_tasks = [MagicMock(), MagicMock(), MagicMock()]
            mock_create_task.side_effect = mock_tasks
            
            await handler.start()
        
        # Verify WebSocket was accepted
        mock_websocket.accept.assert_called_once()
        
        # Verify session was created and entered
        mock_runner.run.assert_called_once()
        mock_realtime_session.enter.assert_called_once()
        
        # Verify tasks were created
        assert mock_create_task.call_count == 3
        assert handler._realtime_session_task == mock_tasks[0]
        assert handler._message_loop_task == mock_tasks[1]
        assert handler._buffer_flush_task == mock_tasks[2]
    
    @pytest.mark.asyncio
    async def test_start_no_api_key(self, mock_websocket, mock_user):
        """Test start fails without API key."""
        with patch('routers.twilio_handler.Client'):
            handler = TwilioHandler(mock_websocket, mock_user)
            
            # Override the settings to have no API key
            handler.settings = MagicMock()
            handler.settings.openai_api_key = None
            
            # Test will raise when trying to get openai_api_key
            with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable is required"):
                await handler.start()
    
    @pytest.mark.asyncio
    async def test_wait_until_done(self, mock_websocket, mock_user):
        """Test wait_until_done method."""
        handler = TwilioHandler(mock_websocket, mock_user)
        
        # Create a mock task that can be awaited
        async def mock_coro():
            pass
        
        mock_task = asyncio.create_task(mock_coro())
        handler._message_loop_task = mock_task
        
        await handler.wait_until_done()
        
        # Task should be done
        assert mock_task.done()
    
    @pytest.mark.asyncio
    async def test_handle_twilio_message_connected(self, mock_websocket, mock_user):
        """Test handling 'connected' event from Twilio."""
        handler = TwilioHandler(mock_websocket, mock_user)
        
        message = {"event": "connected"}
        await handler._handle_twilio_message(message)
        
        # Should not crash and handle gracefully
        assert True
    
    @pytest.mark.asyncio
    async def test_handle_twilio_message_start(self, mock_websocket, mock_user, mock_realtime_session):
        """Test handling 'start' event from Twilio."""
        with patch('routers.twilio_handler.Client') as mock_twilio_client:
            with patch('routers.twilio_handler.start_twilio_call') as mock_start_call:
                # Mock the Twilio client call fetch
                mock_call = MagicMock()
                mock_call._from = "+1234567890"
                mock_twilio_client.return_value.calls.return_value.fetch.return_value = mock_call
                
                handler = TwilioHandler(mock_websocket, mock_user)
                handler.session = mock_realtime_session
                
                message = {
                    "event": "start",
                    "start": {
                        "streamSid": "test-stream-sid",
                        "callSid": "test-call-sid"
                    }
                }
                
                await handler._handle_twilio_message(message)
                
                assert handler._stream_sid == "test-stream-sid"
                assert handler.call_sid == "test-call-sid"
                
                # Verify greeting message was sent
                expected_greeting = (
                    "The Call SID is test-call-sid. Greet the user with 'Hello! Welcome to the oh die "
                    "Voice Assistant. How can I help you today?' and then wait for the user to speak. "
                    "Do not spell out ODAI but pronouce the name as 'oh die'."
                )
                mock_realtime_session.send_message.assert_called_once_with(expected_greeting)
                
                # Verify start_twilio_call was called
                mock_start_call.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_twilio_message_media(self, mock_websocket, mock_user):
        """Test handling 'media' event from Twilio."""
        handler = TwilioHandler(mock_websocket, mock_user)
        
        # Create some test audio data
        test_audio = b"test audio data"
        encoded_audio = base64.b64encode(test_audio).decode("utf-8")
        
        message = {
            "event": "media",
            "media": {
                "payload": encoded_audio
            }
        }
        
        with patch.object(handler, '_handle_media_event') as mock_handle_media:
            await handler._handle_twilio_message(message)
            mock_handle_media.assert_called_once_with(message)
    
    @pytest.mark.asyncio
    async def test_handle_twilio_message_mark(self, mock_websocket, mock_user):
        """Test handling 'mark' event from Twilio."""
        handler = TwilioHandler(mock_websocket, mock_user)
        
        message = {
            "event": "mark",
            "mark": {
                "name": "1"
            }
        }
        
        with patch.object(handler, '_handle_mark_event') as mock_handle_mark:
            await handler._handle_twilio_message(message)
            mock_handle_mark.assert_called_once_with(message)
    
    @pytest.mark.asyncio
    async def test_handle_twilio_message_stop(self, mock_websocket, mock_user):
        """Test handling 'stop' event from Twilio."""
        with patch('routers.twilio_handler.Client') as mock_twilio_client:
            with patch('routers.twilio_handler.end_twilio_call') as mock_end_call:
                handler = TwilioHandler(mock_websocket, mock_user)
                handler._stream_sid = "test-stream-sid"
                handler.call_sid = "test-call-sid"
                
                message = {"event": "stop"}
                await handler._handle_twilio_message(message)
                
                # Verify end_twilio_call was called
                mock_end_call.assert_called_once()
                # Should not crash and handle gracefully
                assert True
    
    @pytest.mark.asyncio
    async def test_handle_media_event(self, mock_websocket, mock_user, mock_realtime_session):
        """Test processing audio data from Twilio."""
        handler = TwilioHandler(mock_websocket, mock_user)
        handler.session = mock_realtime_session
        
        # Create test audio data
        test_audio = b"x" * 400  # Exactly BUFFER_SIZE_BYTES
        encoded_audio = base64.b64encode(test_audio).decode("utf-8")
        
        message = {
            "event": "media",
            "media": {
                "payload": encoded_audio
            }
        }
        
        with patch.object(handler, '_flush_audio_buffer') as mock_flush:
            await handler._handle_media_event(message)
            
            # Should have added to buffer and flushed
            mock_flush.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_media_event_no_flush(self, mock_websocket, mock_user):
        """Test that small audio data doesn't trigger flush."""
        handler = TwilioHandler(mock_websocket, mock_user)
        
        # Create small test audio data
        test_audio = b"x" * 100  # Less than BUFFER_SIZE_BYTES
        encoded_audio = base64.b64encode(test_audio).decode("utf-8")
        
        message = {
            "event": "media",
            "media": {
                "payload": encoded_audio
            }
        }
        
        with patch.object(handler, '_flush_audio_buffer') as mock_flush:
            await handler._handle_media_event(message)
            
            # Should not have flushed
            mock_flush.assert_not_called()
            
            # But should have added to buffer
            assert len(handler._audio_buffer) == 100
    
    @pytest.mark.asyncio
    async def test_handle_mark_event(self, mock_websocket, mock_user):
        """Test handling mark events for playback tracking."""
        handler = TwilioHandler(mock_websocket, mock_user)
        
        # Mock the playback tracker
        handler.playback_tracker = MagicMock()
        handler.playback_tracker.on_play_bytes = MagicMock()
        
        # Set up mark data
        handler._mark_data["1"] = ("item-123", 0, 100)
        
        message = {
            "event": "mark",
            "mark": {
                "name": "1"
            }
        }
        
        await handler._handle_mark_event(message)
        
        # Verify playback tracker was updated
        handler.playback_tracker.on_play_bytes.assert_called_once_with(
            "item-123", 0, b"\x00" * 100
        )
        
        # Verify mark data was cleaned up
        assert "1" not in handler._mark_data
    
    @pytest.mark.asyncio
    async def test_flush_audio_buffer(self, mock_websocket, mock_user, mock_realtime_session):
        """Test flushing audio buffer to OpenAI."""
        handler = TwilioHandler(mock_websocket, mock_user)
        handler.session = mock_realtime_session
        
        # Add some data to buffer
        test_data = b"test audio data"
        handler._audio_buffer.extend(test_data)
        
        await handler._flush_audio_buffer()
        
        # Verify audio was sent
        mock_realtime_session.send_audio.assert_called_once_with(test_data)
        
        # Verify buffer was cleared
        assert len(handler._audio_buffer) == 0
    
    @pytest.mark.asyncio
    async def test_flush_audio_buffer_no_session(self, mock_websocket, mock_user):
        """Test flush does nothing without session."""
        handler = TwilioHandler(mock_websocket, mock_user)
        handler.session = None
        
        # Add some data to buffer
        handler._audio_buffer.extend(b"test")
        
        await handler._flush_audio_buffer()
        
        # Buffer should remain unchanged
        assert len(handler._audio_buffer) == 4
    
    @pytest.mark.asyncio
    async def test_handle_realtime_event_agent_start(self, mock_websocket, mock_user):
        """Test handling agent_start event."""
        handler = TwilioHandler(mock_websocket, mock_user)
        handler._stream_sid = "test-stream-sid"
        
        event = MagicMock()
        event.type = "agent_start"
        event.agent.name = "TestAgent"
        
        with patch('routers.twilio_handler.get_computer_keyboard_typing_sound') as mock_sound:
            mock_sound.return_value = "base64_sound_data"
            
            await handler._handle_realtime_event(event)
            
            # Verify sound was generated and sent
            mock_sound.assert_called_once_with(5, 1)
            expected_message = {
                "event": "media",
                "streamSid": "test-stream-sid",
                "media": {
                    "payload": "base64_sound_data"
                }
            }
            mock_websocket.send_json.assert_called_once_with(expected_message)
            assert handler.playing_sound is True
    
    @pytest.mark.asyncio
    async def test_handle_realtime_event_audio(self, mock_websocket, mock_user):
        """Test handling audio event."""
        handler = TwilioHandler(mock_websocket, mock_user)
        handler._stream_sid = "test-stream-sid"
        handler.playing_sound = True
        
        event = MagicMock()
        event.type = "audio"
        event.audio.data = b"test audio data"
        event.audio.item_id = "item-123"
        event.audio.content_index = 0
        
        await handler._handle_realtime_event(event)
        
        # Verify clear was sent first
        clear_message = {'event': 'clear', 'streamSid': 'test-stream-sid'}
        assert mock_websocket.send_json.call_args_list[0][0][0] == clear_message
        
        # Verify audio was sent
        expected_audio = base64.b64encode(b"test audio data").decode("utf-8")
        audio_message = {
            "event": "media",
            "streamSid": "test-stream-sid",
            "media": {"payload": expected_audio}
        }
        assert json.loads(mock_websocket.send_text.call_args_list[0][0][0]) == audio_message
        
        # Verify mark was sent
        assert handler._mark_counter == 1
        mark_message = {
            "event": "mark",
            "streamSid": "test-stream-sid",
            "mark": {"name": "1"}
        }
        assert json.loads(mock_websocket.send_text.call_args_list[1][0][0]) == mark_message
        
        # Verify playing_sound was set to False
        assert handler.playing_sound is False
    
    @pytest.mark.asyncio
    async def test_handle_realtime_event_audio_interrupted(self, mock_websocket, mock_user):
        """Test handling audio_interrupted event."""
        handler = TwilioHandler(mock_websocket, mock_user)
        handler._stream_sid = "test-stream-sid"
        
        event = MagicMock()
        event.type = "audio_interrupted"
        
        await handler._handle_realtime_event(event)
        
        # Verify clear was sent
        expected_message = {"event": "clear", "streamSid": "test-stream-sid"}
        mock_websocket.send_text.assert_called_once_with(json.dumps(expected_message))
    
    @pytest.mark.asyncio
    async def test_twilio_message_loop(self, mock_websocket, mock_user):
        """Test the Twilio message loop."""
        handler = TwilioHandler(mock_websocket, mock_user)
        
        # Set up messages to receive
        messages = [
            '{"event": "connected"}',
            '{"event": "stop"}'
        ]
        mock_websocket.receive_text.side_effect = messages + [Exception("Stop loop")]
        
        with patch.object(handler, '_handle_twilio_message') as mock_handle:
            # Run the loop - it will exit on exception
            await handler._twilio_message_loop()
            
            # Verify each message was handled
            assert mock_handle.call_count == 2
    
    @pytest.mark.asyncio
    async def test_realtime_session_loop(self, mock_websocket, mock_user, mock_realtime_session):
        """Test the realtime session loop."""
        handler = TwilioHandler(mock_websocket, mock_user)
        handler.session = mock_realtime_session
        
        # Create mock events
        events = [
            MagicMock(type="agent_start"),
            MagicMock(type="audio_end")
        ]
        
        # Create an async generator class
        class AsyncIterator:
            def __init__(self):
                self.index = 0
            
            def __aiter__(self):
                return self
            
            async def __anext__(self):
                if self.index < len(events):
                    event = events[self.index]
                    self.index += 1
                    return event
                raise StopAsyncIteration
        
        # Set up the mock session to be an async iterator
        async_iter = AsyncIterator()
        mock_realtime_session.__aiter__ = MagicMock(return_value=async_iter)
        
        with patch.object(handler, '_handle_realtime_event') as mock_handle:
            await handler._realtime_session_loop()
            
            # Verify each event was handled
            assert mock_handle.call_count == 2
    
    @pytest.mark.asyncio
    async def test_buffer_flush_loop(self, mock_websocket, mock_user):
        """Test the buffer flush loop."""
        handler = TwilioHandler(mock_websocket, mock_user)
        
        # Add some data to buffer
        handler._audio_buffer.extend(b"test")
        handler._last_buffer_send_time = time.time() - 1  # Make it old
        
        # Mock asyncio.sleep to stop after first iteration
        call_count = 0
        async def mock_sleep(duration):
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                raise Exception("Stop")
            return
        
        with patch.object(handler, '_flush_audio_buffer') as mock_flush:
            # Run one iteration of the loop
            with patch('asyncio.sleep', mock_sleep):
                # Run the loop - it will exit on exception
                await handler._buffer_flush_loop()
                
                # Should have flushed due to old data
                mock_flush.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_realtime_event_agent_end(self, mock_websocket, mock_user):
        """Test handling agent_end event."""
        handler = TwilioHandler(mock_websocket, mock_user)
        
        event = MagicMock()
        event.type = "agent_end"
        event.agent.name = "TestAgent"
        
        with patch.object(logger, 'info') as mock_log:
            await handler._handle_realtime_event(event)
            mock_log.assert_called_once_with("Agent ended: TestAgent")
    
    @pytest.mark.asyncio
    async def test_handle_realtime_event_handoff(self, mock_websocket, mock_user):
        """Test handling handoff event."""
        handler = TwilioHandler(mock_websocket, mock_user)
        
        event = MagicMock()
        event.type = "handoff"
        event.from_agent.name = "Agent1"
        event.to_agent.name = "Agent2"
        
        with patch.object(logger, 'info') as mock_log:
            await handler._handle_realtime_event(event)
            mock_log.assert_called_once_with("Handoff from Agent1 to Agent2")
    
    @pytest.mark.asyncio
    async def test_handle_realtime_event_tool_start(self, mock_websocket, mock_user):
        """Test handling tool_start event."""
        with patch('routers.twilio_handler.track_tool_called') as mock_track:
            handler = TwilioHandler(mock_websocket, mock_user)
            handler._stream_sid = "test-stream-sid"
            
            event = MagicMock()
            event.type = "tool_start"
            event.tool.name = "TestTool"
            event.tool.description = "Test tool description"
            
            with patch.object(logger, 'info') as mock_log:
                await handler._handle_realtime_event(event)
                mock_log.assert_called_once_with("Tool started: TestTool")
                mock_track.assert_called_once_with(mock_user, "test-stream-sid", "TestTool", "Test tool description")
    
    @pytest.mark.asyncio
    async def test_handle_realtime_event_tool_end(self, mock_websocket, mock_user):
        """Test handling tool_end event."""
        handler = TwilioHandler(mock_websocket, mock_user)
        
        event = MagicMock()
        event.type = "tool_end"
        event.tool.name = "TestTool"
        event.output = "Test output"
        
        with patch.object(logger, 'debug') as mock_log:
            await handler._handle_realtime_event(event)
            mock_log.assert_called_once_with("Tool ended: TestTool; output: Test output")
    
    @pytest.mark.asyncio
    async def test_handle_realtime_event_audio_end(self, mock_websocket, mock_user):
        """Test handling audio_end event."""
        handler = TwilioHandler(mock_websocket, mock_user)
        
        event = MagicMock()
        event.type = "audio_end"
        
        with patch.object(logger, 'debug') as mock_log:
            await handler._handle_realtime_event(event)
            mock_log.assert_called_with("Audio end")
    
    @pytest.mark.asyncio
    async def test_handle_realtime_event_unknown(self, mock_websocket, mock_user):
        """Test handling unknown event type."""
        handler = TwilioHandler(mock_websocket, mock_user)
        
        event = MagicMock()
        event.type = "unknown_event"
        
        # Should not crash
        await handler._handle_realtime_event(event)
    
    @pytest.mark.asyncio
    async def test_handle_twilio_message_error(self, mock_websocket, mock_user):
        """Test error handling in _handle_twilio_message."""
        handler = TwilioHandler(mock_websocket, mock_user)
        
        # Create a message that will cause an error by mocking the method to raise
        message = {"event": "media", "media": {}}
        
        with patch.object(handler, '_handle_media_event', side_effect=Exception("Test error")):
            with patch.object(logger, 'error') as mock_log:
                await handler._handle_twilio_message(message)
                # Should catch and log error
                mock_log.assert_called_once()
                assert "Error handling Twilio message" in mock_log.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_handle_media_event_decode_error(self, mock_websocket, mock_user):
        """Test handling decode error in media event."""
        handler = TwilioHandler(mock_websocket, mock_user)
        
        message = {
            "event": "media",
            "media": {
                "payload": "invalid_base64!"  # Invalid base64
            }
        }
        
        with patch.object(logger, 'error') as mock_log:
            await handler._handle_media_event(message)
            # Should catch and log error
            mock_log.assert_called_once()
            assert "Error processing audio from Twilio" in mock_log.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_handle_mark_event_error(self, mock_websocket, mock_user):
        """Test error handling in mark event."""
        handler = TwilioHandler(mock_websocket, mock_user)
        
        # Set up mark data
        handler._mark_data["1"] = ("item-123", 0, 100)
        handler.playback_tracker = None  # Will cause AttributeError
        
        message = {
            "event": "mark",
            "mark": {
                "name": "1"
            }
        }
        
        with patch.object(logger, 'error') as mock_log:
            await handler._handle_mark_event(message)
            # Should catch and log error
            mock_log.assert_called_once()
            assert "Error handling mark event" in mock_log.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_flush_audio_buffer_error(self, mock_websocket, mock_user, mock_realtime_session):
        """Test error handling in flush audio buffer."""
        handler = TwilioHandler(mock_websocket, mock_user)
        handler.session = mock_realtime_session
        handler._audio_buffer.extend(b"test")
        
        # Make send_audio raise an error
        mock_realtime_session.send_audio = AsyncMock(side_effect=Exception("Send failed"))
        
        with patch.object(logger, 'error') as mock_log:
            await handler._flush_audio_buffer()
            # Should catch and log error
            mock_log.assert_called_once()
            assert "Error sending buffered audio to OpenAI" in mock_log.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_realtime_session_loop_error(self, mock_websocket, mock_user, mock_realtime_session):
        """Test error handling in realtime session loop."""
        handler = TwilioHandler(mock_websocket, mock_user)
        handler.session = mock_realtime_session
        
        # Create an async generator that raises an error
        class ErrorAsyncIterator:
            def __aiter__(self):
                return self
            
            async def __anext__(self):
                raise Exception("Session error")
        
        mock_realtime_session.__aiter__ = MagicMock(return_value=ErrorAsyncIterator())
        
        with patch.object(logger, 'error') as mock_log:
            await handler._realtime_session_loop()
            # Should catch and log error
            mock_log.assert_called_once()
            assert "Error in realtime session loop" in mock_log.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_start_no_openai_key_error(self, mock_websocket, mock_user):
        """Test that start raises error when no OpenAI key."""
        with patch('routers.twilio_handler.Settings') as mock_settings_class:
            settings = MagicMock()
            settings.openai_api_key = None
            mock_settings_class.return_value = settings
            
            handler = TwilioHandler(mock_websocket, mock_user)
            
            with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable is required"):
                await handler.start()
    
    @pytest.mark.asyncio
    async def test_handle_media_event_empty_payload(self, mock_websocket, mock_user):
        """Test handling media event with empty payload."""
        handler = TwilioHandler(mock_websocket, mock_user)
        
        message = {
            "event": "media",
            "media": {
                "payload": ""
            }
        }
        
        # Should handle gracefully without errors
        await handler._handle_media_event(message)
        
        # Buffer should remain empty
        assert len(handler._audio_buffer) == 0
    
    @pytest.mark.asyncio
    async def test_handle_mark_event_missing_mark_data(self, mock_websocket, mock_user):
        """Test handling mark event when mark data is missing."""
        handler = TwilioHandler(mock_websocket, mock_user)
        
        message = {
            "event": "mark",
            "mark": {
                "name": "999"  # Not in _mark_data
            }
        }
        
        # Should handle gracefully
        await handler._handle_mark_event(message)
    
    @pytest.mark.asyncio
    async def test_concurrent_audio_processing(self, mock_websocket, mock_user, mock_realtime_session):
        """Test handling multiple audio events concurrently."""
        handler = TwilioHandler(mock_websocket, mock_user)
        handler.session = mock_realtime_session
        handler._stream_sid = "test-stream"
        
        # Create multiple audio events
        tasks = []
        for i in range(5):
            event = MagicMock()
            event.type = "audio"
            event.audio.data = f"audio{i}".encode()
            event.audio.item_id = f"item-{i}"
            event.audio.content_index = i
            tasks.append(handler._handle_realtime_event(event))
        
        # Process all events concurrently
        await asyncio.gather(*tasks)
        
        # Verify all audio was sent
        assert mock_websocket.send_text.call_count >= 10  # At least 2 calls per audio event
    
    @pytest.mark.asyncio
    async def test_buffer_timing_edge_case(self, mock_websocket, mock_user, mock_realtime_session):
        """Test buffer flush timing edge cases."""
        handler = TwilioHandler(mock_websocket, mock_user)
        handler.session = mock_realtime_session
        
        # Set buffer time to exactly the threshold (0.1 seconds based on code)
        handler._last_buffer_send_time = time.time() - 0.1
        handler._audio_buffer.extend(b"x" * 10)  # Small amount of data
        
        # Mock asyncio.sleep to stop after first iteration
        call_count = 0
        async def mock_sleep(duration):
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                raise Exception("Stop")
            return
        
        with patch('asyncio.sleep', mock_sleep):
            try:
                await handler._buffer_flush_loop()
            except Exception:
                pass  # Expected
        
        # Should have flushed due to timeout
        mock_realtime_session.send_audio.assert_called_once()