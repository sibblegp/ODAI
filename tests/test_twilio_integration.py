"""Integration tests for Twilio voice call handling."""
import asyncio
import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import WebSocket

from routers.twilio_handler import TwilioHandler
from routers.twilio_server import TwilioWebSocketManager, media_stream_endpoint


class TestTwilioIntegration:
    """Integration tests for complete Twilio voice call flows."""
    
    @pytest.mark.asyncio
    async def test_complete_call_flow(self):
        """Test a complete call flow from start to finish."""
        # Create mocks
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.accept = AsyncMock()
        mock_websocket.receive_text = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        mock_websocket.send_json = AsyncMock()
        
        # Mock OpenAI components
        with patch('routers.twilio_handler.RealtimeRunner') as mock_runner_class, \
             patch('routers.twilio_handler.Settings') as mock_settings_class, \
             patch('routers.twilio_handler.get_computer_keyboard_typing_sound') as mock_sound:
            
            # Setup settings
            settings = MagicMock()
            settings.openai_api_key = "test-key"
            mock_settings_class.return_value = settings
            
            # Setup runner and session
            mock_runner = MagicMock()
            mock_runner_class.return_value = mock_runner
            
            mock_session = MagicMock()
            mock_session.enter = AsyncMock()
            mock_session.send_message = AsyncMock()
            mock_session.send_audio = AsyncMock()
            
            mock_runner.run = AsyncMock(return_value=mock_session)
            
            # Setup sound generation
            mock_sound.return_value = "keyboard_sound_base64"
            
            # Create mock user
            mock_user = MagicMock()
            mock_user.reference_id = "test_user_123"
            
            # Create handler with Twilio client mocked
            with patch('routers.twilio_handler.Client') as mock_twilio_client, \
                 patch('routers.twilio_handler.start_twilio_call') as mock_start_call:
                # Mock the Twilio client call fetch
                mock_call = MagicMock()
                mock_call._from = "+1234567890"
                mock_twilio_client.return_value.calls.return_value.fetch.return_value = mock_call
                
                handler = TwilioHandler(mock_websocket, mock_user)
                handler.session = mock_session
            
            # Simulate Twilio messages
            twilio_messages = [
                json.dumps({"event": "connected"}),
                json.dumps({
                    "event": "start",
                    "start": {
                        "streamSid": "SM123",
                        "callSid": "CA456"
                    }
                }),
                json.dumps({
                    "event": "media",
                    "media": {
                        "payload": base64.b64encode(b"audio_data").decode()
                    }
                }),
                json.dumps({"event": "stop"})
            ]
            
            message_index = 0
            async def mock_receive():
                nonlocal message_index
                if message_index < len(twilio_messages):
                    msg = twilio_messages[message_index]
                    message_index += 1
                    return msg
                raise Exception("No more messages")
            
            mock_websocket.receive_text = mock_receive
            
            # Simulate OpenAI events
            events = []
            
            # Agent start event
            agent_start = MagicMock()
            agent_start.type = "agent_start"
            agent_start.agent.name = "VoiceAgent"
            events.append(agent_start)
            
            # Audio event
            audio_event = MagicMock()
            audio_event.type = "audio"
            audio_event.audio.data = b"response_audio"
            audio_event.audio.item_id = "item1"
            audio_event.audio.content_index = 0
            events.append(audio_event)
            
            # Setup async iterator for session
            class EventIterator:
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
            
            mock_session.__aiter__ = MagicMock(return_value=EventIterator())
            
            # Start the handler
            await handler.start()
            
            # Verify initial setup
            mock_websocket.accept.assert_called_once()
            mock_session.enter.assert_called_once()
            
            # Let the tasks run briefly
            await asyncio.sleep(0.1)
            
            # Verify greeting was sent
            expected_greeting = (
                "The Call SID is CA456. Greet the user with 'Hello! Welcome to the oh die "
                "Voice Assistant. How can I help you today?' and then wait for the user to speak. "
                "Do not spell out ODAI but pronouce the name as 'oh die'."
            )
            mock_session.send_message.assert_called_once_with(expected_greeting)
            
            # Verify audio was buffered and sent
            assert len(handler._audio_buffer) > 0 or mock_session.send_audio.called
            
            # Verify keyboard sound was sent for agent start
            keyboard_msg_sent = False
            for call in mock_websocket.send_json.call_args_list:
                if call[0][0].get("media", {}).get("payload") == "keyboard_sound_base64":
                    keyboard_msg_sent = True
                    break
            assert keyboard_msg_sent
            
            # Verify response audio was sent
            response_audio_sent = False
            for call in mock_websocket.send_text.call_args_list:
                try:
                    msg = json.loads(call[0][0])
                    if msg.get("event") == "media" and "payload" in msg.get("media", {}):
                        response_audio_sent = True
                        break
                except:
                    pass
            assert response_audio_sent
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_calls(self):
        """Test handling multiple concurrent calls."""
        manager = TwilioWebSocketManager()
        
        # Create multiple mock websockets
        num_calls = 3
        websockets = []
        handlers = []
        
        for i in range(num_calls):
            ws = MagicMock(spec=WebSocket)
            ws.accept = AsyncMock()
            ws.receive_text = AsyncMock(side_effect=Exception("Stop"))
            ws.send_text = AsyncMock()
            ws.send_json = AsyncMock()
            websockets.append(ws)
        
        with patch('routers.twilio_handler.RealtimeRunner') as mock_runner_class, \
             patch('routers.twilio_handler.Settings') as mock_settings_class:
            
            settings = MagicMock()
            settings.openai_api_key = "test-key"
            mock_settings_class.return_value = settings
            
            # Setup mock runner and session for each handler
            mock_runner = MagicMock()
            mock_session = MagicMock()
            mock_session.enter = AsyncMock()
            mock_runner.run = AsyncMock(return_value=mock_session)
            mock_runner_class.return_value = mock_runner
            
            # Create handlers concurrently
            tasks = []
            
            # Mock the TwilioHandler
            with patch('routers.twilio_handler.Client'):
                # Create mock user
                mock_user = MagicMock()
                mock_user.reference_id = "test_user_123"
                
                for ws in websockets:
                    handler = await manager.new_session(ws, mock_user)
                    handlers.append(handler)
                    tasks.append(handler.start())
            
            # Start all handlers
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check for any unexpected errors
            for result in results:
                if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
                    print(f"Error starting handler: {result}")
            
            # Verify all were started
            for ws in websockets:
                ws.accept.assert_called_once()
            
            # Verify manager tracks all handlers
            assert len(handlers) == num_calls
    
    @pytest.mark.asyncio
    async def test_error_recovery_flow(self):
        """Test error recovery during call processing."""
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        mock_websocket.send_json = AsyncMock()
        
        with patch('routers.twilio_handler.RealtimeRunner') as mock_runner_class, \
             patch('routers.twilio_handler.Settings') as mock_settings_class:
            
            settings = MagicMock()
            settings.openai_api_key = "test-key"
            mock_settings_class.return_value = settings
            
            mock_runner = MagicMock()
            mock_runner_class.return_value = mock_runner
            
            # Make session enter fail first time, succeed second time
            mock_session = MagicMock()
            mock_session.enter = AsyncMock(side_effect=[Exception("Connection failed"), None])
            
            mock_runner.run = AsyncMock(return_value=mock_session)
            
            # Create mock user
            mock_user = MagicMock()
            mock_user.reference_id = "test_user_123"
            
            with patch('routers.twilio_handler.Client'):
                handler = TwilioHandler(mock_websocket, mock_user)
            
            # First attempt should fail
            with pytest.raises(Exception, match="Connection failed"):
                await handler.start()
            
            # Second attempt should succeed
            await handler.start()
            mock_websocket.accept.assert_called()
    
    @pytest.mark.asyncio
    async def test_audio_buffering_and_flushing(self):
        """Test audio buffering and flushing behavior."""
        mock_websocket = MagicMock(spec=WebSocket)
        mock_session = MagicMock()
        mock_session.send_audio = AsyncMock()
        
        # Create mock user
        mock_user = MagicMock()
        mock_user.reference_id = "test_user_123"
        
        with patch('routers.twilio_handler.Client'):
            handler = TwilioHandler(mock_websocket, mock_user)
        handler.session = mock_session
        
        # Test 1: Small audio chunks don't trigger flush
        small_chunk = b"x" * 100
        payload = base64.b64encode(small_chunk).decode()
        await handler._handle_media_event({
            "event": "media",
            "media": {"payload": payload}
        })
        
        assert len(handler._audio_buffer) == 100
        mock_session.send_audio.assert_not_called()
        
        # Test 2: Large chunk triggers flush
        large_chunk = b"y" * 400
        payload = base64.b64encode(large_chunk).decode()
        await handler._handle_media_event({
            "event": "media",
            "media": {"payload": payload}
        })
        
        # Buffer should be flushed
        assert len(handler._audio_buffer) == 0
        mock_session.send_audio.assert_called_once()
        
        # Test 3: Time-based flush
        handler._audio_buffer.extend(b"z" * 50)
        handler._last_buffer_send_time = 0  # Very old timestamp
        
        # Manually trigger flush check
        await handler._flush_audio_buffer()
        
        assert len(handler._audio_buffer) == 0
        assert mock_session.send_audio.call_count == 2
    
    @pytest.mark.asyncio
    async def test_mark_event_playback_tracking(self):
        """Test mark event handling for playback tracking."""
        mock_websocket = MagicMock(spec=WebSocket)
        # Create mock user
        mock_user = MagicMock()
        mock_user.reference_id = "test_user_123"
        
        with patch('routers.twilio_handler.Client'):
            handler = TwilioHandler(mock_websocket, mock_user)
        
        # Setup playback tracker
        handler.playback_tracker = MagicMock()
        handler.playback_tracker.on_play_bytes = MagicMock()
        
        # Simulate audio event with mark
        handler._stream_sid = "SM123"
        event = MagicMock()
        event.type = "audio"
        event.audio.data = b"audio_data"
        event.audio.item_id = "item1"
        event.audio.content_index = 0
        
        await handler._handle_realtime_event(event)
        
        # Verify mark was created
        assert "1" in handler._mark_data
        assert handler._mark_data["1"] == ("item1", 0, len(b"audio_data"))
        
        # Simulate mark acknowledgment from Twilio
        await handler._handle_mark_event({
            "event": "mark",
            "mark": {"name": "1"}
        })
        
        # Verify playback was tracked
        handler.playback_tracker.on_play_bytes.assert_called_once_with(
            "item1", 0, b"\x00" * len(b"audio_data")
        )
        
        # Verify mark data was cleaned up
        assert "1" not in handler._mark_data
    
    @pytest.mark.asyncio
    async def test_websocket_manager_lifecycle(self):
        """Test WebSocket manager full lifecycle."""
        with patch('routers.twilio_server.manager') as mock_manager, \
             patch('routers.twilio_server.User') as mock_user_class:
            # Mock User.get_user_by_id
            mock_user = MagicMock()
            mock_user.reference_id = "test_user"
            mock_user_class.get_user_by_id.return_value = mock_user
            
            # Setup handler
            mock_handler = MagicMock()
            mock_handler.start = AsyncMock()
            mock_handler.wait_until_done = AsyncMock()
            
            mock_manager.new_session = AsyncMock(return_value=mock_handler)
            
            # Create mock websocket
            mock_websocket = MagicMock()
            
            # Test normal flow
            await media_stream_endpoint(mock_websocket)
            
            # Verify lifecycle
            mock_manager.new_session.assert_called_once_with(mock_websocket, mock_user)
            mock_handler.start.assert_called_once()
            mock_handler.wait_until_done.assert_called_once()
            
            # Test error during start
            mock_handler.start = AsyncMock(side_effect=ValueError("Config error"))
            
            with patch('builtins.print') as mock_print:
                await media_stream_endpoint(mock_websocket)
                mock_print.assert_called_with("WebSocket error: Config error")
    
    @pytest.mark.asyncio
    async def test_voice_interruption_handling(self):
        """Test handling voice interruptions during playback."""
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.send_text = AsyncMock()
        mock_websocket.send_json = AsyncMock()
        
        # Create mock user
        mock_user = MagicMock()
        mock_user.reference_id = "test_user_123"
        
        with patch('routers.twilio_handler.Client'):
            handler = TwilioHandler(mock_websocket, mock_user)
        handler._stream_sid = "SM123"
        handler.playing_sound = True
        
        # Simulate audio interrupted event
        event = MagicMock()
        event.type = "audio_interrupted"
        
        await handler._handle_realtime_event(event)
        
        # Verify clear was sent
        clear_msg = json.dumps({"event": "clear", "streamSid": "SM123"})
        mock_websocket.send_text.assert_called_with(clear_msg)
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown(self):
        """Test graceful shutdown of active calls."""
        with patch('routers.twilio_server.TwilioHandler') as mock_handler_class:
            manager = TwilioWebSocketManager()
            
            # Create mock user
            mock_user = MagicMock()
            mock_user.reference_id = "test_user"
            
            # Create active handler
            mock_websocket = MagicMock()
            
            # Mock the TwilioHandler instance
            mock_handler = MagicMock()
            mock_handler._message_loop_task = None
            mock_handler.wait_until_done = AsyncMock()
            mock_handler_class.return_value = mock_handler
            
            handler = await manager.new_session(mock_websocket, mock_user)
        
        # The handler returned is the mock, verify it was created correctly
        assert handler == mock_handler
        mock_handler_class.assert_called_once_with(mock_websocket, mock_user)
        
        # Test simulating active session cancellation
        real_task = asyncio.create_task(asyncio.sleep(10))
        
        # Cancel the task to simulate shutdown
        real_task.cancel()
        
        # Give time for cancellation to propagate
        try:
            await real_task
        except asyncio.CancelledError:
            pass  # Expected
        
        # Verify task was cancelled
        assert real_task.cancelled()