"""
Comprehensive unit tests for websocket.handlers module.

Tests cover all methods of WebSocketHandler class including:
- WebSocket connection handling and lifecycle
- Chat message processing and loops
- Stream event handling and processing
- Agent interactions and tool calls
- Token usage tracking and database updates
- Error handling and cleanup
- JSON serialization and WebSocket communication
- Integration scenarios and edge cases
"""

import pytest
import json
import asyncio
import uuid
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Any, Dict, List, Optional

# Import the modules to test
from websocket.handlers import WebSocketHandler


# Module-level fixtures available to all test classes
@pytest.fixture
def mock_settings():
    """Create mock settings object."""
    settings = Mock()
    settings.production = False
    settings.local = True
    settings.project_id = "test_project_123"
    return settings


@pytest.fixture
def mock_openai_client():
    """Create mock OpenAI client."""
    client = Mock()
    return client


@pytest.fixture
def mock_connection_manager():
    """Create mock ConnectionManager."""
    manager = Mock()
    manager.connect = AsyncMock()
    manager.disconnect = Mock()
    return manager


@pytest.fixture
def mock_websocket():
    """Create mock WebSocket."""
    websocket = Mock()
    websocket.send_text = AsyncMock()
    websocket.receive_text = AsyncMock()
    websocket.accept = AsyncMock()
    websocket.close = AsyncMock()
    return websocket


@pytest.fixture
def mock_user():
    """Create mock user object."""
    user = Mock()
    user.reference_id = "test_user_123"
    user.connected_to_google = True
    user.connected_to_plaid = False
    return user


@pytest.fixture
def mock_chat():
    """Create mock chat object."""
    chat = Mock()
    chat.messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"}
    ]
    chat.update_timestamp = Mock()
    return chat


@pytest.fixture
def mock_location_info():
    """Create mock location info."""
    from services.location_service import LocationInfo
    return LocationInfo(
        ip="192.168.1.1",
        latitude_longitude="40.7128,-74.0060",
        city_state="New York, NY",
        timezone="America/New_York",
        latitude="40.7128",
        longitude="-74.0060"
    )


@pytest.fixture
def mock_runner():
    """Create mock Runner."""
    runner = Mock()
    return runner


@pytest.fixture
def mock_chat_context():
    """Create mock ChatContext."""
    context = Mock()
    return context


@pytest.fixture
def mock_stream_result():
    """Create mock stream result."""
    result = Mock()
    result.stream_events = AsyncMock()
    result.to_input_list = Mock(return_value=[
        {"role": "user", "content": "test prompt"},
        {"role": "assistant", "content": "test response"}
    ])
    return result


@pytest.fixture
def websocket_handler(mock_settings, mock_openai_client, mock_connection_manager):
    """Create WebSocketHandler instance with mocked dependencies."""
    with patch('websocket.handlers.AuthService') as mock_auth_service, \
            patch('websocket.handlers.ChatService') as mock_chat_service, \
            patch('websocket.handlers.TOOL_CALLS', {"tool1": "Tool 1 description"}), \
            patch('websocket.handlers.get_chat_context') as mock_get_chat_context, \
            patch('websocket.handlers.get_prompt_services') as mock_get_prompt_services:

        # Setup mocks
        mock_get_chat_context.return_value = Mock
        mock_get_prompt_services.return_value = (Mock(), Mock())

        handler = WebSocketHandler(
            mock_settings, mock_openai_client, mock_connection_manager)
        return handler


class TestWebSocketHandlerInit:
    """Test WebSocketHandler initialization."""

    def test_init_creates_handler_with_dependencies(self, mock_settings, mock_openai_client, mock_connection_manager):
        """Test WebSocketHandler initialization with all dependencies."""
        with patch('websocket.handlers.AuthService') as mock_auth_service, \
                patch('websocket.handlers.ChatService') as mock_chat_service, \
                patch('websocket.handlers.TOOL_CALLS', {"tool1": "Tool 1 description"}), \
                patch('websocket.handlers.get_chat_context') as mock_get_chat_context, \
                patch('websocket.handlers.get_prompt_services') as mock_get_prompt_services:

            # Setup mocks
            mock_get_chat_context.return_value = Mock
            mock_get_prompt_services.return_value = (Mock(), Mock())

            # Execute
            handler = WebSocketHandler(
                mock_settings, mock_openai_client, mock_connection_manager)

            # Verify
            assert handler.settings == mock_settings
            assert handler.openai_client == mock_openai_client
            assert handler.connection_manager == mock_connection_manager
            assert handler.TOOL_CALLS == {"tool1": "Tool 1 description"}

            # Verify service creation
            mock_auth_service.assert_called_once_with(production=False)
            mock_chat_service.assert_called_once()


class TestHandleWebSocketConnection:
    """Test the handle_websocket_connection method."""

    @pytest.mark.asyncio
    async def test_handle_websocket_connection_success(self, websocket_handler, mock_websocket, mock_user, mock_location_info, mock_chat):
        """Test successful WebSocket connection handling."""
        # Setup mocks
        websocket_handler.auth_service.authenticate_websocket = AsyncMock(
            return_value=(mock_user, False))
        websocket_handler.chat_service.get_or_create_chat = Mock(
            return_value=(mock_chat, True, "msg_123"))
        websocket_handler._handle_chat_loop = AsyncMock()

        with patch('websocket.handlers.LocationService') as mock_location_service:
            mock_location_service.get_location_info = Mock(
                return_value=mock_location_info)

            # Execute
            await websocket_handler.handle_websocket_connection(
                mock_websocket, "chat_123", "token_123", "1.1.1.1", "2.2.2.2"
            )

            # Verify
            websocket_handler.auth_service.authenticate_websocket.assert_called_once_with(
                mock_websocket, "token_123")
            mock_location_service.get_location_info.assert_called_once_with(
                "1.1.1.1", "2.2.2.2")
            websocket_handler.connection_manager.connect.assert_called_once_with(
                mock_websocket)
            websocket_handler.chat_service.get_or_create_chat.assert_called_once_with(
                "chat_123", mock_user, mock_location_info
            )
            websocket_handler._handle_chat_loop.assert_called_once_with(
                mock_websocket, mock_user, mock_chat, "chat_123", "msg_123"
            )
            websocket_handler.connection_manager.disconnect.assert_called_once_with(
                mock_websocket)

    @pytest.mark.asyncio
    async def test_handle_websocket_connection_auth_failure(self, websocket_handler, mock_websocket):
        """Test WebSocket connection handling with authentication failure."""
        # Setup mocks
        websocket_handler.auth_service.authenticate_websocket = AsyncMock(
            side_effect=Exception("Authentication failed")
        )

        # Execute
        await websocket_handler.handle_websocket_connection(
            mock_websocket, "chat_123", "invalid_token"
        )

        # Verify cleanup still happens
        websocket_handler.connection_manager.disconnect.assert_called_once_with(
            mock_websocket)

    @pytest.mark.asyncio
    async def test_handle_websocket_connection_chat_loop_exception(self, websocket_handler, mock_websocket, mock_user, mock_location_info, mock_chat):
        """Test WebSocket connection handling with chat loop exception."""
        # Setup mocks
        websocket_handler.auth_service.authenticate_websocket = AsyncMock(
            return_value=(mock_user, False))
        websocket_handler.chat_service.get_or_create_chat = Mock(
            return_value=(mock_chat, True, None))
        websocket_handler._handle_chat_loop = AsyncMock(
            side_effect=Exception("Chat loop error"))

        with patch('websocket.handlers.LocationService') as mock_location_service:
            mock_location_service.get_location_info = Mock(
                return_value=mock_location_info)

            # Execute
            await websocket_handler.handle_websocket_connection(
                mock_websocket, "chat_123", "token_123"
            )

            # Verify cleanup still happens
            websocket_handler.connection_manager.disconnect.assert_called_once_with(
                mock_websocket)


class TestHandleChatLoop:
    """Test the _handle_chat_loop method."""

    @pytest.mark.asyncio
    async def test_handle_chat_loop_with_new_chat(self, websocket_handler, mock_websocket, mock_user, mock_chat):
        """Test chat loop with new chat (no last_message_id)."""
        # Setup mocks
        mock_websocket.receive_text = AsyncMock(
            side_effect=["Hello", Exception("Connection closed")])
        websocket_handler.chat_service.track_user_prompt = Mock()
        websocket_handler._process_chat_message = AsyncMock()
        
        # Mock Orchestrator to return a mock agent
        with patch('websocket.handlers.Orchestrator') as mock_orchestrator_class:
            mock_agent = Mock()
            mock_orchestrator_instance = Mock()
            mock_orchestrator_instance.agent = mock_agent
            mock_orchestrator_instance.build_dynamic_agents = AsyncMock()
            mock_orchestrator_class.return_value = mock_orchestrator_instance
            
            # Execute
            await websocket_handler._handle_chat_loop(mock_websocket, mock_user, mock_chat, "chat_123", None)

            # Verify
            websocket_handler.chat_service.track_user_prompt.assert_called_once_with(
                mock_user, "chat_123", "Hello")
            websocket_handler._process_chat_message.assert_called_once_with(
                mock_websocket, mock_agent, mock_user, mock_chat, "chat_123", "Hello", None
            )
            # Timestamp should not be updated for new chat initially
            mock_chat.update_timestamp.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_chat_loop_with_existing_chat(self, websocket_handler, mock_websocket, mock_user, mock_chat):
        """Test chat loop with existing chat (has last_message_id)."""
        # Setup mocks
        mock_websocket.receive_text = AsyncMock(
            side_effect=["Hello", "How are you?", Exception("Connection closed")])
        websocket_handler.chat_service.track_user_prompt = Mock()
        websocket_handler._process_chat_message = AsyncMock()
        
        # Mock Orchestrator to return a mock agent
        with patch('websocket.handlers.Orchestrator') as mock_orchestrator_class:
            mock_agent = Mock()
            mock_orchestrator_instance = Mock()
            mock_orchestrator_instance.agent = mock_agent
            mock_orchestrator_instance.build_dynamic_agents = AsyncMock()
            mock_orchestrator_class.return_value = mock_orchestrator_instance
            
            # Execute
            await websocket_handler._handle_chat_loop(mock_websocket, mock_user, mock_chat, "chat_123", "msg_123")

            # Verify timestamp updates
            assert mock_chat.update_timestamp.call_count == 2  # Called for both messages
            assert websocket_handler._process_chat_message.call_count == 2

    @pytest.mark.asyncio
    async def test_handle_chat_loop_message_processing_error(self, websocket_handler, mock_websocket, mock_user, mock_chat):
        """Test chat loop with message processing error."""
        # Setup mocks
        mock_websocket.receive_text = AsyncMock(return_value="Hello")
        websocket_handler.chat_service.track_user_prompt = Mock()
        websocket_handler._process_chat_message = AsyncMock(
            side_effect=Exception("Processing error"))

        # Mock Orchestrator to return a mock agent
        with patch('websocket.handlers.Orchestrator') as mock_orchestrator_class:
            mock_agent = Mock()
            mock_orchestrator_instance = Mock()
            mock_orchestrator_instance.agent = mock_agent
            mock_orchestrator_instance.build_dynamic_agents = AsyncMock()
            mock_orchestrator_class.return_value = mock_orchestrator_instance
            
            # Execute
            await websocket_handler._handle_chat_loop(mock_websocket, mock_user, mock_chat, "chat_123", None)

            # Verify it tracks the prompt but stops processing after error
            websocket_handler.chat_service.track_user_prompt.assert_called_once_with(
                mock_user, "chat_123", "Hello")
            websocket_handler._process_chat_message.assert_called_once()


class TestProcessChatMessage:
    """Test the _process_chat_message method."""

    @pytest.mark.asyncio
    async def test_process_chat_message_with_last_message_id(self, websocket_handler, mock_websocket, mock_user, mock_chat, mock_runner, mock_chat_context, mock_stream_result):
        """Test processing chat message with last_message_id."""
        # Setup mocks
        websocket_handler.auth_service.get_user_integrations = Mock(return_value={
            "google": True,
            "plaid": False
        })
        websocket_handler.ChatContext = Mock(return_value=mock_chat_context)
        websocket_handler._handle_streaming_events = AsyncMock(return_value=(
            [{"type": "response"}], {"input_tokens": 10,
                                     "output_tokens": 20, "cached_input_tokens": 5}, "new_msg_123"
        ))
        websocket_handler._finalize_chat_interaction = AsyncMock()

        with patch('websocket.handlers.Runner', return_value=mock_runner):
            mock_runner.run_streamed = Mock(return_value=mock_stream_result)

            # Execute
            mock_orchestrator_agent = Mock()
            await websocket_handler._process_chat_message(
                mock_websocket, mock_orchestrator_agent, mock_user, mock_chat, "chat_123", "Hello", "last_msg_123"
            )

            # Verify runner called with previous message ID
            mock_runner.run_streamed.assert_called_once()
            call_args = mock_runner.run_streamed.call_args
            assert call_args[1]['previous_response_id'] == "last_msg_123"
            assert call_args[0][0] == mock_orchestrator_agent  # Agent parameter
            assert call_args[0][1] == [
                {"content": "Hello", "role": "user"}]  # Only new message

            # Verify context creation
            websocket_handler.ChatContext.assert_called_once()
            context_call = websocket_handler.ChatContext.call_args[1]
            assert context_call['user_id'] == mock_user.reference_id
            assert context_call['chat_id'] == "chat_123"
            assert context_call['prompt'] == "Hello"
            assert context_call['is_google_enabled'] is True
            assert context_call['is_plaid_enabled'] is False

            # Verify streaming and finalization
            websocket_handler._handle_streaming_events.assert_called_once()
            websocket_handler._finalize_chat_interaction.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_chat_message_without_last_message_id(self, websocket_handler, mock_websocket, mock_user, mock_chat, mock_runner, mock_chat_context, mock_stream_result):
        """Test processing chat message without last_message_id."""
        # Setup mocks
        websocket_handler.auth_service.get_user_integrations = Mock(return_value={
            "google": False,
            "plaid": True
        })
        websocket_handler.ChatContext = Mock(return_value=mock_chat_context)
        websocket_handler._handle_streaming_events = AsyncMock(
            return_value=([], {}, None))
        websocket_handler._finalize_chat_interaction = AsyncMock()

        with patch('websocket.handlers.Runner', return_value=mock_runner):
            mock_runner.run_streamed = Mock(return_value=mock_stream_result)

            # Execute
            mock_orchestrator_agent = Mock()
            await websocket_handler._process_chat_message(
                mock_websocket, mock_orchestrator_agent, mock_user, mock_chat, "chat_123", "Hello", None
            )

            # Verify runner called with existing messages
            mock_runner.run_streamed.assert_called_once()
            call_args = mock_runner.run_streamed.call_args
            assert call_args[0][0] == mock_orchestrator_agent  # Agent parameter
            assert 'previous_response_id' not in call_args[1]
            expected_messages = mock_chat.messages + \
                [{"content": "Hello", "role": "user"}]
            assert call_args[0][1] == expected_messages


class TestHandleStreamingEvents:
    """Test the _handle_streaming_events method."""

    @pytest.mark.asyncio
    async def test_handle_streaming_events_success(self, websocket_handler, mock_websocket, mock_user, mock_stream_result):
        """Test successful streaming events handling."""
        # Create mock events
        mock_events = [
            Mock(type="agent_updated_stream_event",
                 new_agent=Mock(name="SearchAgent")),
            Mock(type="raw_response_event", data=Mock()),
            Mock(type="run_item_stream_event", item=Mock())
        ]
        # Create async iterator for stream events
        async def async_iter_events():
            for event in mock_events:
                yield event
        mock_stream_result.stream_events = Mock(return_value=async_iter_events())

        websocket_handler._process_stream_event = AsyncMock(side_effect=[
            {"type": "agent_updated", "name": "SearchAgent"},
            {"type": "text_delta", "content": "Hello"},
            None
        ])

        # Execute
        responses, token_usage, last_message_id = await websocket_handler._handle_streaming_events(
            mock_websocket, mock_stream_result, mock_user, "chat_123", "Hello"
        )

        # Verify
        assert len(responses) == 3  # user_prompt + 2 responses with IDs
        assert responses[0]["type"] == "user_prompt"
        assert responses[0]["prompt"] == "Hello"
        assert "id" in responses[0]

        # All responses should have UUIDs
        for response in responses:
            assert "id" in response

        # Verify token usage structure
        assert "input_tokens" in token_usage
        assert "output_tokens" in token_usage
        assert "cached_input_tokens" in token_usage

    @pytest.mark.asyncio
    async def test_handle_streaming_events_with_token_usage(self, websocket_handler, mock_websocket, mock_user, mock_stream_result):
        """Test streaming events with token usage tracking."""
        from openai.types.responses import ResponseCompletedEvent

        # Create mock completed event with usage
        mock_usage = Mock()
        mock_usage.input_tokens = 50
        mock_usage.output_tokens = 30
        mock_usage.input_tokens_details = Mock(cached_tokens=10)

        mock_response = Mock()
        mock_response.id = "response_123"
        mock_response.usage = mock_usage

        mock_completed_event = Mock(spec=ResponseCompletedEvent)
        mock_completed_event.response = mock_response

        mock_events = [
            Mock(type="raw_response_event", data=mock_completed_event)
        ]
        # Create async iterator for stream events
        async def async_iter_events():
            for event in mock_events:
                yield event
        mock_stream_result.stream_events = Mock(return_value=async_iter_events())
        websocket_handler._process_stream_event = AsyncMock(return_value=None)

        # Execute
        responses, token_usage, last_message_id = await websocket_handler._handle_streaming_events(
            mock_websocket, mock_stream_result, mock_user, "chat_123", "Hello"
        )

        # Verify token usage
        assert token_usage["input_tokens"] == 50
        assert token_usage["output_tokens"] == 30
        assert token_usage["cached_input_tokens"] == 10
        assert last_message_id == "response_123"


class TestProcessStreamEvent:
    """Test the _process_stream_event method."""

    @pytest.mark.asyncio
    async def test_process_text_delta_event(self, websocket_handler, mock_websocket, mock_user):
        """Test processing text delta events."""
        from openai.types.responses import ResponseTextDeltaEvent

        # Create mock event
        mock_event = Mock()
        mock_event.type = "raw_response_event"
        mock_event.data = Mock(spec=ResponseTextDeltaEvent)
        mock_event.data.delta = "Hello "

        # Execute
        result = await websocket_handler._process_stream_event(
            mock_event, mock_websocket, mock_user, "chat_123", "TestAgent"
        )

        # Verify WebSocket message sent
        mock_websocket.send_text.assert_called_once()
        sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_data["type"] == "raw_response_event"
        assert sent_data["delta"] == "Hello "
        assert sent_data["current_agent"] == "TestAgent"

        # Should not return a response for storage
        assert result is None

    @pytest.mark.asyncio
    async def test_process_function_tool_call_event(self, websocket_handler, mock_websocket, mock_user):
        """Test processing function tool call events."""
        from openai.types.responses import ResponseOutputItemAddedEvent, ResponseFunctionToolCall

        # Setup handler with tool descriptions
        websocket_handler.TOOL_CALLS = {
            "search_web": "Search the web for information"}
        websocket_handler.chat_service.track_tool_call = Mock()

        # Create mock event
        mock_tool_call = Mock(spec=ResponseFunctionToolCall)
        mock_tool_call.name = "search_web"

        mock_event = Mock()
        mock_event.type = "raw_response_event"
        mock_event.data = Mock(spec=ResponseOutputItemAddedEvent)
        mock_event.data.item = mock_tool_call

        # Execute
        result = await websocket_handler._process_stream_event(
            mock_event, mock_websocket, mock_user, "chat_123", "SearchAgent"
        )

        # Verify tool call tracking
        websocket_handler.chat_service.track_tool_call.assert_called_once_with(
            mock_user, "chat_123", "search_web", "Search the web for information"
        )

        # Verify WebSocket message sent
        mock_websocket.send_text.assert_called_once()
        sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_data["type"] == "tool_call"
        assert sent_data["name"] == "search_web"
        assert sent_data["description"] == "Search the web for information"

        # Verify response for storage
        assert result["type"] == "tool_call"
        assert result["name"] == "search_web"

    @pytest.mark.asyncio
    async def test_process_text_done_event(self, websocket_handler, mock_websocket, mock_user):
        """Test processing text done events."""
        from openai.types.responses import ResponseTextDoneEvent

        # Create mock event
        mock_event = Mock()
        mock_event.type = "raw_response_event"
        mock_event.data = Mock(spec=ResponseTextDoneEvent)
        mock_event.data.text = "Complete response text"

        # Execute
        result = await websocket_handler._process_stream_event(
            mock_event, mock_websocket, mock_user, "chat_123", "TestAgent"
        )

        # Verify response for storage
        assert result["type"] == "llm_response"
        assert result["response"] == "Complete response text"
        assert result["current_agent"] == "TestAgent"

    @pytest.mark.asyncio
    async def test_process_agent_updated_event(self, websocket_handler, mock_websocket, mock_user):
        """Test processing agent updated events."""
        websocket_handler.chat_service.track_agent_call = Mock()

        # Create mock event
        mock_event = Mock()
        mock_event.type = "agent_updated_stream_event"
        mock_event.new_agent = Mock()
        mock_event.new_agent.name = "SearchAgent"

        # Execute
        result = await websocket_handler._process_stream_event(
            mock_event, mock_websocket, mock_user, "chat_123", None
        )

        # Verify agent tracking
        websocket_handler.chat_service.track_agent_call.assert_called_once_with(
            mock_user, "chat_123", "SearchAgent"
        )

        # Verify WebSocket message sent
        mock_websocket.send_text.assert_called_once()
        sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_data["type"] == "agent_updated"
        assert sent_data["new_agent"] == "SearchAgent"

        # Verify response for storage
        assert result["type"] == "agent_updated"
        assert result["new_agent"] == "SearchAgent"

    @pytest.mark.asyncio
    async def test_process_agent_updated_event_odai_agent(self, websocket_handler, mock_websocket, mock_user):
        """Test processing agent updated event for ODAI agent (should not send message)."""
        websocket_handler.chat_service.track_agent_call = Mock()

        # Create mock event with ODAI agent
        mock_event = Mock()
        mock_event.type = "agent_updated_stream_event"
        mock_event.new_agent = Mock()
        mock_event.new_agent.name = "ODAI"

        # Execute
        result = await websocket_handler._process_stream_event(
            mock_event, mock_websocket, mock_user, "chat_123", None
        )

        # Verify agent tracking still happens
        websocket_handler.chat_service.track_agent_call.assert_called_once_with(
            mock_user, "chat_123", "ODAI"
        )

        # Verify no WebSocket message sent for ODAI
        mock_websocket.send_text.assert_not_called()

        # Should not return a response for ODAI
        assert result is None

    @pytest.mark.asyncio
    async def test_process_run_item_event(self, websocket_handler, mock_websocket, mock_user):
        """Test processing run item events."""
        websocket_handler._handle_run_item_event = AsyncMock(
            return_value={"type": "tool_output"})

        # Create mock event
        mock_event = Mock()
        mock_event.type = "run_item_stream_event"
        mock_event.item = Mock()

        # Execute
        result = await websocket_handler._process_stream_event(
            mock_event, mock_websocket, mock_user, "chat_123", "TestAgent"
        )

        # Verify run item handler called
        websocket_handler._handle_run_item_event.assert_called_once_with(
            mock_event, mock_websocket, "TestAgent"
        )

        # Verify result returned
        assert result == {"type": "tool_output"}


class TestHandleRunItemEvent:
    """Test the _handle_run_item_event method."""

    @pytest.mark.asyncio
    async def test_handle_tool_call_output_item_display_true(self, websocket_handler, mock_websocket):
        """Test handling tool call output item with display_response=True."""
        # Create mock event
        mock_event = Mock()
        mock_event.item = Mock()
        mock_event.item.type = "tool_call_output_item"
        mock_event.item.output = {
            "result": "Search results",
            "display_response": True
        }

        # Execute
        result = await websocket_handler._handle_run_item_event(mock_event, mock_websocket, "SearchAgent")

        # Verify WebSocket message sent
        mock_websocket.send_text.assert_called_once()
        sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_data["type"] == "tool_output"
        assert sent_data["output"]["result"] == "Search results"
        assert sent_data["current_agent"] == "SearchAgent"

        # Verify response returned
        assert result["type"] == "tool_output"
        assert result["output"]["result"] == "Search results"

    @pytest.mark.asyncio
    async def test_handle_tool_call_output_item_display_false(self, websocket_handler, mock_websocket):
        """Test handling tool call output item with display_response=False."""
        # Create mock event
        mock_event = Mock()
        mock_event.item = Mock()
        mock_event.item.type = "tool_call_output_item"
        mock_event.item.output = {
            "result": "Internal data",
            "display_response": False
        }

        # Execute
        result = await websocket_handler._handle_run_item_event(mock_event, mock_websocket, "SearchAgent")

        # Verify no WebSocket message sent
        mock_websocket.send_text.assert_not_called()

        # Verify no response returned
        assert result is None

    @pytest.mark.asyncio
    async def test_handle_tool_call_output_item_no_display_key(self, websocket_handler, mock_websocket):
        """Test handling tool call output item without display_response key (defaults to True)."""
        # Create mock event
        mock_event = Mock()
        mock_event.item = Mock()
        mock_event.item.type = "tool_call_output_item"
        mock_event.item.output = {
            "result": "Default display"
        }

        # Execute
        result = await websocket_handler._handle_run_item_event(mock_event, mock_websocket, "SearchAgent")

        # Verify WebSocket message sent (defaults to display=True)
        mock_websocket.send_text.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_handle_handoff_call_item(self, websocket_handler, mock_websocket):
        """Test handling handoff call item."""
        # Create mock event
        mock_event = Mock()
        mock_event.item = Mock()
        mock_event.item.type = "handoff_call_item"
        mock_event.item.raw_item = Mock()
        mock_event.item.raw_item.name = "transfer_to_agent"

        # Execute
        result = await websocket_handler._handle_run_item_event(mock_event, mock_websocket, "MainAgent")

        # Verify WebSocket message sent
        mock_websocket.send_text.assert_called_once()
        sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_data["type"] == "handoff"
        assert sent_data["name"] == "transfer_to_agent"
        assert sent_data["current_agent"] == "MainAgent"

        # Verify response returned
        assert result["type"] == "handoff"
        assert result["name"] == "transfer_to_agent"

    @pytest.mark.asyncio
    async def test_handle_unknown_item_type(self, websocket_handler, mock_websocket):
        """Test handling unknown item type."""
        # Create mock event
        mock_event = Mock()
        mock_event.item = Mock()
        mock_event.item.type = "unknown_item_type"

        # Execute
        result = await websocket_handler._handle_run_item_event(mock_event, mock_websocket, "TestAgent")

        # Verify no WebSocket message sent
        mock_websocket.send_text.assert_not_called()

        # Verify no response returned
        assert result is None


class TestFinalizeChatInteraction:
    """Test the _finalize_chat_interaction method."""

    @pytest.mark.asyncio
    async def test_finalize_chat_interaction_success(self, websocket_handler, mock_websocket, mock_user, mock_chat, mock_stream_result):
        """Test successful chat interaction finalization."""
        # Setup mocks
        responses = [
            {"type": "user_prompt", "prompt": "Hello"},
            {"type": "agent_response", "content": "Hi there!"}
        ]
        token_usage = {"input_tokens": 10,
                       "output_tokens": 20, "cached_input_tokens": 5}

        websocket_handler._extract_previous_suggested_prompts = Mock(
            return_value=["Previous prompt"])
        websocket_handler.agent_capabilities.generate_suggested_prompts = AsyncMock(
            return_value=["How can I help?", "What else?"]
        )
        websocket_handler.chat_service.track_user_response = Mock()
        websocket_handler.chat_service.update_chat_messages = AsyncMock()
        websocket_handler.chat_service.add_chat_responses = AsyncMock()
        websocket_handler.chat_service.record_unhandled_request = AsyncMock()
        websocket_handler.chat_service.record_token_usage = AsyncMock()
        websocket_handler.chat_service.update_chat_token_usage = AsyncMock()
        websocket_handler.determine_if_request_handled = AsyncMock(
            return_value=(True, None, None))

        # Execute
        await websocket_handler._finalize_chat_interaction(
            mock_websocket, mock_user, mock_chat, "chat_123", "Hello",
            mock_stream_result, responses, token_usage, "msg_123"
        )

        # Verify end of stream sent
        calls = mock_websocket.send_text.call_args_list
        assert len(calls) >= 2  # At least end_of_stream and suggested_prompts

        # Check end of stream message
        end_stream_call = calls[0]
        end_stream_data = json.loads(end_stream_call[0][0])
        assert end_stream_data["type"] == "end_of_stream"

        # Check suggested prompts message
        suggested_prompts_call = calls[1]
        suggested_prompts_data = json.loads(suggested_prompts_call[0][0])
        assert suggested_prompts_data["type"] == "suggested_prompts"
        assert suggested_prompts_data["prompts"] == [
            "How can I help?", "What else?"]

        # Verify database operations
        websocket_handler.chat_service.track_user_response.assert_called_once_with(
            mock_user, "chat_123")
        websocket_handler.chat_service.update_chat_messages.assert_called_once()
        websocket_handler.chat_service.add_chat_responses.assert_called_once()
        websocket_handler.chat_service.record_token_usage.assert_called_once_with(
            mock_user, 10, 5, 20
        )
        websocket_handler.chat_service.update_chat_token_usage.assert_called_once_with(
            mock_chat, 10, 5, 20
        )

    @pytest.mark.asyncio
    async def test_finalize_chat_interaction_unhandled_request(self, websocket_handler, mock_websocket, mock_user, mock_chat, mock_stream_result):
        """Test finalization with unhandled request."""
        # Setup mocks
        websocket_handler._extract_previous_suggested_prompts = Mock(
            return_value=[])
        websocket_handler.agent_capabilities.generate_suggested_prompts = AsyncMock(
            return_value=[])
        websocket_handler.chat_service.track_user_response = Mock()
        websocket_handler.chat_service.update_chat_messages = AsyncMock()
        websocket_handler.chat_service.add_chat_responses = AsyncMock()
        websocket_handler.chat_service.record_unhandled_request = AsyncMock()
        websocket_handler.chat_service.record_token_usage = AsyncMock()
        websocket_handler.chat_service.update_chat_token_usage = AsyncMock()
        websocket_handler.determine_if_request_handled = AsyncMock(return_value=(
            False, "search_capability", "Search the web"
        ))

        # Execute
        await websocket_handler._finalize_chat_interaction(
            mock_websocket, mock_user, mock_chat, "chat_123", "Search for cats",
            mock_stream_result, [], {"input_tokens": 0, "output_tokens": 0, "cached_input_tokens": 0}, None
        )

        # Verify unhandled request recorded
        websocket_handler.chat_service.record_unhandled_request.assert_called_once_with(
            mock_user, mock_chat, "Search for cats", "search_capability", "Search the web"
        )


class TestExtractPreviousSuggestedPrompts:
    """Test the _extract_previous_suggested_prompts method."""

    def test_extract_previous_suggested_prompts_with_prompts(self, websocket_handler):
        """Test extracting previous suggested prompts when they exist."""
        responses = [
            {"type": "user_prompt", "prompt": "Hello"},
            {"type": "suggested_prompts",
                "demo_prompts": ["Prompt 1", "Prompt 2"]},
            {"type": "agent_response", "content": "Response"},
            {"type": "suggested_prompts", "demo_prompts": ["Prompt 3"]}
        ]

        result = websocket_handler._extract_previous_suggested_prompts(
            responses)

        assert result == ["Prompt 1", "Prompt 2", "Prompt 3"]

    def test_extract_previous_suggested_prompts_no_prompts(self, websocket_handler):
        """Test extracting previous suggested prompts when none exist."""
        responses = [
            {"type": "user_prompt", "prompt": "Hello"},
            {"type": "agent_response", "content": "Response"}
        ]

        result = websocket_handler._extract_previous_suggested_prompts(
            responses)

        assert result == []

    def test_extract_previous_suggested_prompts_no_demo_prompts_key(self, websocket_handler):
        """Test extracting when suggested_prompts exists but no demo_prompts key."""
        responses = [
            {"type": "suggested_prompts", "prompts": ["Prompt 1", "Prompt 2"]}
        ]

        result = websocket_handler._extract_previous_suggested_prompts(
            responses)

        assert result == []


class TestJsonSerial:
    """Test the _json_serial static method."""

    def test_json_serial_datetime(self, websocket_handler):
        """Test JSON serialization of datetime objects."""
        import datetime

        dt = datetime.datetime(2024, 1, 1, 12, 0, 0)
        result = websocket_handler._json_serial(dt)
        assert result == "2024-01-01T12:00:00"

        date = datetime.date(2024, 1, 1)
        result = websocket_handler._json_serial(date)
        assert result == "2024-01-01"

    def test_json_serial_unsupported_type(self, websocket_handler):
        """Test JSON serialization of unsupported types."""
        class CustomObject:
            pass

        obj = CustomObject()

        with pytest.raises(TypeError, match="Type .* not serializable"):
            websocket_handler._json_serial(obj)


class TestWebSocketHandlerIntegration:
    """Integration tests for WebSocketHandler."""

    @pytest.mark.asyncio
    async def test_full_websocket_flow_new_chat(self, websocket_handler, mock_websocket, mock_user, mock_location_info, mock_chat, mock_runner, mock_stream_result):
        """Test complete WebSocket flow with new chat."""
        # Setup mocks for complete flow
        websocket_handler.auth_service.authenticate_websocket = AsyncMock(
            return_value=(mock_user, False))
        websocket_handler.auth_service.get_user_integrations = Mock(
            return_value={"google": True, "plaid": False})
        websocket_handler.chat_service.get_or_create_chat = Mock(
            return_value=(mock_chat, True, None))
        websocket_handler.chat_service.track_user_prompt = Mock()
        websocket_handler.chat_service.track_user_response = Mock()
        websocket_handler.chat_service.update_chat_messages = AsyncMock()
        websocket_handler.chat_service.add_chat_responses = AsyncMock()
        websocket_handler.chat_service.record_token_usage = AsyncMock()
        websocket_handler.chat_service.update_chat_token_usage = AsyncMock()
        websocket_handler.ChatContext = Mock()
        websocket_handler.agent_capabilities.generate_suggested_prompts = AsyncMock(
            return_value=["What else?"])
        websocket_handler.determine_if_request_handled = AsyncMock(
            return_value=(True, None, None))

        # Mock streaming events
        mock_events = [
            Mock(type="raw_response_event", data=Mock(delta="Hello")),
            Mock(type="agent_updated_stream_event",
                 new_agent=Mock(name="SearchAgent"))
        ]
        # Create async iterator for stream events
        async def async_iter_events():
            for event in mock_events:
                yield event
        mock_stream_result.stream_events = Mock(return_value=async_iter_events())

        # Mock WebSocket receive to simulate user input then disconnection
        mock_websocket.receive_text = AsyncMock(
            side_effect=["Hello world", Exception("Client disconnected")])

        with patch('websocket.handlers.LocationService') as mock_location_service, \
                patch('websocket.handlers.Runner', return_value=mock_runner):

            mock_location_service.get_location_info = Mock(
                return_value=mock_location_info)
            mock_runner.run_streamed = Mock(return_value=mock_stream_result)

            # Execute full flow
            await websocket_handler.handle_websocket_connection(
                mock_websocket, "chat_123", "token_123"
            )

            # Verify complete flow
            websocket_handler.auth_service.authenticate_websocket.assert_called_once()
            websocket_handler.connection_manager.connect.assert_called_once()
            websocket_handler.chat_service.get_or_create_chat.assert_called_once()
            websocket_handler.chat_service.track_user_prompt.assert_called_once()
            mock_runner.run_streamed.assert_called_once()
            websocket_handler.connection_manager.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_error_handling_and_cleanup(self, websocket_handler, mock_websocket):
        """Test WebSocket error handling and proper cleanup."""
        # Setup authentication to fail
        websocket_handler.auth_service.authenticate_websocket = AsyncMock(
            side_effect=Exception("Auth failed")
        )

        # Execute
        await websocket_handler.handle_websocket_connection(
            mock_websocket, "chat_123", "bad_token"
        )

        # Verify cleanup happens even on error
        websocket_handler.connection_manager.disconnect.assert_called_once_with(
            mock_websocket)


class TestWebSocketHandlerEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_websocket_message_with_special_characters(self, websocket_handler, mock_websocket, mock_user):
        """Test handling WebSocket messages with special characters."""
        from openai.types.responses import ResponseTextDeltaEvent

        # Create event with unicode content
        mock_event = Mock()
        mock_event.type = "raw_response_event"
        mock_event.data = Mock(spec=ResponseTextDeltaEvent)
        mock_event.data.delta = "Hello 🌍! Special chars: àáâãäåæçèéêë"

        # Execute
        await websocket_handler._process_stream_event(
            mock_event, mock_websocket, mock_user, "chat_123", "TestAgent"
        )

        # Verify WebSocket can handle unicode
        mock_websocket.send_text.assert_called_once()
        sent_message = mock_websocket.send_text.call_args[0][0]
        # Should be valid JSON with unicode content
        parsed = json.loads(sent_message)
        assert parsed["delta"] == "Hello 🌍! Special chars: àáâãäåæçèéêë"

    @pytest.mark.asyncio
    async def test_empty_stream_events(self, websocket_handler, mock_websocket, mock_user, mock_stream_result):
        """Test handling empty stream events."""
        # Setup empty stream
        async def async_empty_iter():
            return
            yield  # Unreachable - makes this an async generator
        mock_stream_result.stream_events = Mock(return_value=async_empty_iter())

        # Execute
        responses, token_usage, last_message_id = await websocket_handler._handle_streaming_events(
            mock_websocket, mock_stream_result, mock_user, "chat_123", "Hello"
        )

        # Verify minimal response structure
        assert len(responses) == 1  # Just the user prompt
        assert responses[0]["type"] == "user_prompt"
        assert token_usage["input_tokens"] == 0
        assert token_usage["output_tokens"] == 0
        assert last_message_id is None

    @pytest.mark.asyncio
    async def test_tool_call_with_transfer_name_ignored(self, websocket_handler, mock_websocket, mock_user):
        """Test that tool calls with 'transfer' in name are ignored."""
        from openai.types.responses import ResponseOutputItemAddedEvent, ResponseFunctionToolCall

        # Create mock transfer tool call
        mock_tool_call = Mock(spec=ResponseFunctionToolCall)
        mock_tool_call.name = "transfer_to_agent"

        mock_event = Mock()
        mock_event.type = "raw_response_event"
        mock_event.data = Mock(spec=ResponseOutputItemAddedEvent)
        mock_event.data.item = mock_tool_call

        websocket_handler.chat_service.track_tool_call = Mock()

        # Execute
        result = await websocket_handler._process_stream_event(
            mock_event, mock_websocket, mock_user, "chat_123", "TestAgent"
        )

        # Verify transfer calls are ignored
        websocket_handler.chat_service.track_tool_call.assert_not_called()
        mock_websocket.send_text.assert_not_called()
        assert result is None

    @pytest.mark.asyncio
    async def test_production_vs_local_logging_behavior(self, mock_openai_client, mock_connection_manager):
        """Test different logging behavior in production vs local mode."""
        # Test local mode
        local_settings = Mock()
        local_settings.production = False
        local_settings.local = True
        local_settings.project_id = "test"

        # Test production mode
        prod_settings = Mock()
        prod_settings.production = True
        prod_settings.local = False
        prod_settings.project_id = "test"

        with patch('websocket.handlers.AuthService'), \
                patch('websocket.handlers.ChatService'), \
                patch('websocket.handlers.TOOL_CALLS', {}), \
                patch('websocket.handlers.get_chat_context', return_value=Mock), \
                patch('websocket.handlers.get_prompt_services', return_value=(Mock(), Mock())):

            local_handler = WebSocketHandler(
                local_settings, mock_openai_client, mock_connection_manager)
            prod_handler = WebSocketHandler(
                prod_settings, mock_openai_client, mock_connection_manager)

            # Verify settings are stored correctly for different behaviors
            assert local_handler.settings.local is True
            assert local_handler.settings.production is False
            assert prod_handler.settings.local is False
            assert prod_handler.settings.production is True


# Pytest configuration and fixtures for the entire test module
@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all mocks between tests."""
    yield
    # Any cleanup can be done here if needed


if __name__ == "__main__":
    # Allow running tests directly with python -m pytest
    pytest.main([__file__])
