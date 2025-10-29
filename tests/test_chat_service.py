"""
Comprehensive unit tests for services.chat_service module.

Tests cover all methods of ChatService class including:
- Service initialization
- Chat management (get/create)
- Message and response handling
- Token usage tracking
- Unhandled request recording
- Segment tracking methods
- Error handling and edge cases
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Any, Dict, List

# Import the modules to test
from services.chat_service import ChatService
from services.location_service import LocationInfo


# Module-level fixtures available to all test classes
@pytest.fixture
def mock_firebase_models():
    """Mock Firebase model classes."""
    chat_model = Mock()
    token_usage_model = Mock()
    waitlist_model = Mock()
    unhandled_request_model = Mock()
    google_access_request_model = Mock()
    return chat_model, token_usage_model, waitlist_model, unhandled_request_model, google_access_request_model


@pytest.fixture
def mock_segment_tracking():
    """Mock segment tracking functions."""
    return (
        Mock(),  # track_agent_called
        Mock(),  # track_chat_created
        Mock(),  # track_prompt
        Mock(),  # track_responded
        Mock(),  # track_tool_called
        Mock(),  # using_existing_chat
        Mock(),  # track_google_access_request
    )


@pytest.fixture
def chat_service(mock_firebase_models, mock_segment_tracking):
    """Create ChatService instance with mocked dependencies."""
    with patch('services.chat_service.get_firebase_models', return_value=mock_firebase_models), \
            patch('services.chat_service.get_segment_tracking', return_value=mock_segment_tracking):
        return ChatService()


@pytest.fixture
def mock_user():
    """Create a mock user object."""
    user = Mock()
    user.reference_id = "test_user_123"
    return user


@pytest.fixture
def mock_chat():
    """Create a mock chat object."""
    chat = Mock()
    chat.chat_id = "test_chat_456"
    chat.last_message_id = "last_msg_789"
    chat.update_messages = AsyncMock()
    chat.add_responses = AsyncMock()
    chat.update_token_usage = AsyncMock()
    return chat


@pytest.fixture
def location_info():
    """Create a LocationInfo object for testing."""
    return LocationInfo(
        ip="192.168.1.1",
        latitude_longitude="40.7128,-74.0060",
        city_state="New York, NY",
        timezone="America/New_York",
        latitude="40.7128",
        longitude="-74.0060"
    )


@pytest.fixture
def sample_messages():
    """Create sample messages for testing."""
    return [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"}
    ]


@pytest.fixture
def sample_responses():
    """Create sample responses for testing."""
    return [
        {"type": "user_prompt", "prompt": "Hello", "id": "resp_1"},
        {"type": "tool_call", "name": "search", "id": "resp_2"}
    ]


class TestChatServiceInit:
    """Test ChatService initialization."""

    @patch('services.chat_service.get_firebase_models')
    @patch('services.chat_service.get_segment_tracking')
    def test_init_success(self, mock_get_segment, mock_get_firebase):
        """Test successful ChatService initialization."""
        # Setup mocks
        firebase_models = (Mock(), Mock(), Mock(), Mock(), Mock())
        segment_funcs = (Mock(), Mock(), Mock(), Mock(), Mock(), Mock(), Mock())

        mock_get_firebase.return_value = firebase_models
        mock_get_segment.return_value = segment_funcs

        # Create service
        service = ChatService()

        # Verify initialization
        assert service.Chat == firebase_models[0]
        assert service.TokenUsage == firebase_models[1]
        assert service.UnhandledRequest == firebase_models[3]

        assert service.track_agent_called == segment_funcs[0]
        assert service.track_chat_created == segment_funcs[1]
        assert service.track_prompt == segment_funcs[2]
        assert service.track_responded == segment_funcs[3]
        assert service.track_tool_called == segment_funcs[4]
        assert service.using_existing_chat == segment_funcs[5]

        mock_get_firebase.assert_called_once()
        mock_get_segment.assert_called_once()


class TestGetOrCreateChat:
    """Test the get_or_create_chat method."""

    def test_get_existing_chat(self, chat_service, mock_user, location_info, mock_chat):
        """Test getting an existing chat."""
        # Setup
        chat_service.Chat.get_chat_by_id.return_value = mock_chat

        # Execute
        result_chat, is_new, last_msg_id = chat_service.get_or_create_chat(
            "test_chat_id", mock_user, location_info
        )

        # Verify
        assert result_chat == mock_chat
        assert is_new is False
        assert last_msg_id == "last_msg_789"

        chat_service.Chat.get_chat_by_id.assert_called_once_with(
            "test_chat_id", mock_user.reference_id)
        chat_service.using_existing_chat.assert_called_once_with(
            mock_user, "test_chat_id")
        chat_service.Chat.create_chat.assert_not_called()

    def test_create_new_chat(self, chat_service, mock_user, location_info):
        """Test creating a new chat."""
        # Setup
        new_chat = Mock()
        chat_service.Chat.get_chat_by_id.return_value = None
        chat_service.Chat.create_chat.return_value = new_chat

        # Execute
        result_chat, is_new, last_msg_id = chat_service.get_or_create_chat(
            "new_chat_id", mock_user, location_info
        )

        # Verify
        assert result_chat == new_chat
        assert is_new is True
        assert last_msg_id is None

        chat_service.Chat.get_chat_by_id.assert_called_once_with("new_chat_id", mock_user.reference_id)
        chat_service.Chat.create_chat.assert_called_once_with(
            "new_chat_id",
            mock_user,
            location_info.latitude_longitude,
            location_info.city_state,
            location_info.timezone,
            location_info.ip
        )
        chat_service.track_chat_created.assert_called_once_with(
            mock_user, "new_chat_id")

    def test_get_existing_chat_no_last_message_id(self, chat_service, mock_user, location_info):
        """Test getting existing chat without last_message_id attribute."""
        # Setup
        # Mock without last_message_id attribute
        chat_without_last_msg = Mock(spec=[])
        chat_service.Chat.get_chat_by_id.return_value = chat_without_last_msg

        # Execute
        result_chat, is_new, last_msg_id = chat_service.get_or_create_chat(
            "test_chat_id", mock_user, location_info
        )

        # Verify
        assert result_chat == chat_without_last_msg
        assert is_new is False
        assert last_msg_id is None

    def test_get_or_create_chat_exception(self, chat_service, mock_user, location_info):
        """Test exception handling in get_or_create_chat."""
        # Setup
        chat_service.Chat.get_chat_by_id.side_effect = Exception(
            "Database error")

        # Execute & Verify
        with pytest.raises(Exception, match="Database error"):
            chat_service.get_or_create_chat(
                "test_chat_id", mock_user, location_info)


class TestUpdateChatMessages:
    """Test the update_chat_messages method."""

    @pytest.mark.asyncio
    async def test_update_chat_messages_success(self, chat_service, mock_chat, sample_messages):
        """Test successful chat message update."""
        # Execute
        await chat_service.update_chat_messages(mock_chat, sample_messages, "last_msg_123")

        # Verify
        mock_chat.update_messages.assert_called_once_with(
            sample_messages, "last_msg_123")

    @pytest.mark.asyncio
    async def test_update_chat_messages_no_last_id(self, chat_service, mock_chat, sample_messages):
        """Test chat message update without last message ID."""
        # Execute
        await chat_service.update_chat_messages(mock_chat, sample_messages)

        # Verify
        mock_chat.update_messages.assert_called_once_with(
            sample_messages, None)

    @pytest.mark.asyncio
    async def test_update_chat_messages_exception(self, chat_service, mock_chat, sample_messages):
        """Test exception handling in update_chat_messages."""
        # Setup
        mock_chat.update_messages.side_effect = Exception("Update failed")

        # Execute & Verify
        with pytest.raises(Exception, match="Update failed"):
            await chat_service.update_chat_messages(mock_chat, sample_messages)


class TestAddChatResponses:
    """Test the add_chat_responses method."""

    @pytest.mark.asyncio
    async def test_add_chat_responses_success(self, chat_service, mock_chat, sample_responses):
        """Test successful addition of chat responses."""
        # Execute
        await chat_service.add_chat_responses(mock_chat, sample_responses)

        # Verify
        mock_chat.add_responses.assert_called_once_with(sample_responses)

    @pytest.mark.asyncio
    async def test_add_chat_responses_exception(self, chat_service, mock_chat, sample_responses):
        """Test exception handling in add_chat_responses."""
        # Setup
        mock_chat.add_responses.side_effect = Exception("Add responses failed")

        # Execute & Verify
        with pytest.raises(Exception, match="Add responses failed"):
            await chat_service.add_chat_responses(mock_chat, sample_responses)


class TestUpdateChatTokenUsage:
    """Test the update_chat_token_usage method."""

    @pytest.mark.asyncio
    async def test_update_chat_token_usage_success(self, chat_service, mock_chat):
        """Test successful chat token usage update."""
        # Execute
        await chat_service.update_chat_token_usage(mock_chat, 100, 20, 80)

        # Verify
        mock_chat.update_token_usage.assert_called_once_with(100, 20, 80)

    @pytest.mark.asyncio
    async def test_update_chat_token_usage_exception(self, chat_service, mock_chat):
        """Test exception handling in update_chat_token_usage."""
        # Setup
        mock_chat.update_token_usage.side_effect = Exception(
            "Token update failed")

        # Execute & Verify
        with pytest.raises(Exception, match="Token update failed"):
            await chat_service.update_chat_token_usage(mock_chat, 100, 20, 80)


class TestRecordTokenUsage:
    """Test the record_token_usage method."""

    @pytest.mark.asyncio
    async def test_record_token_usage_success(self, chat_service, mock_user):
        """Test successful token usage recording."""
        # Setup
        chat_service.TokenUsage.add_usage = AsyncMock()

        # Execute
        await chat_service.record_token_usage(mock_user, 150, 30, 120)

        # Verify
        chat_service.TokenUsage.add_usage.assert_called_once_with(
            mock_user, 150, 30, 120)

    @pytest.mark.asyncio
    async def test_record_token_usage_exception(self, chat_service, mock_user):
        """Test exception handling in record_token_usage."""
        # Setup
        chat_service.TokenUsage.add_usage = AsyncMock(
            side_effect=Exception("Record failed"))

        # Execute & Verify
        with pytest.raises(Exception, match="Record failed"):
            await chat_service.record_token_usage(mock_user, 150, 30, 120)


class TestRecordUnhandledRequest:
    """Test the record_unhandled_request method."""

    @pytest.mark.asyncio
    async def test_record_unhandled_request_success(self, chat_service, mock_user, mock_chat):
        """Test successful unhandled request recording."""
        # Setup
        chat_service.UnhandledRequest.create_unhandled_request = AsyncMock()

        # Execute
        await chat_service.record_unhandled_request(
            mock_user, mock_chat, "test prompt", "search_capability", "Search the web"
        )

        # Verify
        chat_service.UnhandledRequest.create_unhandled_request.assert_called_once_with(
            mock_user, mock_chat, "test prompt", "search_capability", "Search the web"
        )

    @pytest.mark.asyncio
    async def test_record_unhandled_request_exception(self, chat_service, mock_user, mock_chat):
        """Test exception handling in record_unhandled_request."""
        # Setup
        chat_service.UnhandledRequest.create_unhandled_request = AsyncMock(
            side_effect=Exception("Record unhandled failed")
        )

        # Execute & Verify
        with pytest.raises(Exception, match="Record unhandled failed"):
            await chat_service.record_unhandled_request(
                mock_user, mock_chat, "test prompt", "search_capability", "Search the web"
            )


class TestTrackingMethods:
    """Test the segment tracking methods."""

    def test_track_user_prompt_success(self, chat_service, mock_user):
        """Test successful user prompt tracking."""
        # Execute
        chat_service.track_user_prompt(mock_user, "chat_123", "Hello world")

        # Verify
        chat_service.track_prompt.assert_called_once_with(
            mock_user, "chat_123", "Hello world")

    def test_track_user_prompt_exception(self, chat_service, mock_user):
        """Test exception handling in track_user_prompt."""
        # Setup
        chat_service.track_prompt.side_effect = Exception("Tracking failed")

        # Execute (should not raise, just log)
        chat_service.track_user_prompt(mock_user, "chat_123", "Hello world")

        # Verify it was still called despite the exception
        chat_service.track_prompt.assert_called_once_with(
            mock_user, "chat_123", "Hello world")

    def test_track_agent_call_success(self, chat_service, mock_user):
        """Test successful agent call tracking."""
        # Execute
        chat_service.track_agent_call(mock_user, "chat_123", "search_agent")

        # Verify
        chat_service.track_agent_called.assert_called_once_with(
            mock_user, "chat_123", "search_agent")

    def test_track_agent_call_exception(self, chat_service, mock_user):
        """Test exception handling in track_agent_call."""
        # Setup
        chat_service.track_agent_called.side_effect = Exception(
            "Agent tracking failed")

        # Execute (should not raise, just log)
        chat_service.track_agent_call(mock_user, "chat_123", "search_agent")

        # Verify it was still called despite the exception
        chat_service.track_agent_called.assert_called_once_with(
            mock_user, "chat_123", "search_agent")

    def test_track_tool_call_with_description(self, chat_service, mock_user):
        """Test successful tool call tracking with description."""
        # Execute
        chat_service.track_tool_call(
            mock_user, "chat_123", "web_search", "Search the web")

        # Verify
        chat_service.track_tool_called.assert_called_once_with(
            mock_user, "chat_123", "web_search", "Search the web"
        )

    def test_track_tool_call_without_description(self, chat_service, mock_user):
        """Test successful tool call tracking without description."""
        # Execute
        chat_service.track_tool_call(mock_user, "chat_123", "web_search")

        # Verify
        chat_service.track_tool_called.assert_called_once_with(
            mock_user, "chat_123", "web_search")

    def test_track_tool_call_exception(self, chat_service, mock_user):
        """Test exception handling in track_tool_call."""
        # Setup
        chat_service.track_tool_called.side_effect = Exception(
            "Tool tracking failed")

        # Execute (should not raise, just log)
        chat_service.track_tool_call(
            mock_user, "chat_123", "web_search", "Search the web")

        # Verify it was still called despite the exception
        chat_service.track_tool_called.assert_called_once_with(
            mock_user, "chat_123", "web_search", "Search the web"
        )

    def test_track_user_response_success(self, chat_service, mock_user):
        """Test successful user response tracking."""
        # Execute
        chat_service.track_user_response(mock_user, "chat_123")

        # Verify
        chat_service.track_responded.assert_called_once_with(
            mock_user, "chat_123")

    def test_track_user_response_exception(self, chat_service, mock_user):
        """Test exception handling in track_user_response."""
        # Setup
        chat_service.track_responded.side_effect = Exception(
            "Response tracking failed")

        # Execute (should not raise, just log)
        chat_service.track_user_response(mock_user, "chat_123")

        # Verify it was still called despite the exception
        chat_service.track_responded.assert_called_once_with(
            mock_user, "chat_123")


class TestChatServiceIntegration:
    """Integration tests for ChatService."""

    @pytest.mark.asyncio
    async def test_full_chat_creation_flow(self, chat_service, mock_user, location_info):
        """Test complete chat creation and message handling flow."""
        # Setup
        new_chat = Mock()
        new_chat.update_messages = AsyncMock()
        new_chat.add_responses = AsyncMock()
        new_chat.update_token_usage = AsyncMock()

        chat_service.Chat.get_chat_by_id.return_value = None
        chat_service.Chat.create_chat.return_value = new_chat

        # Execute chat creation
        chat, is_new, last_msg_id = chat_service.get_or_create_chat(
            "new_chat", mock_user, location_info
        )

        # Execute message operations
        messages = [{"role": "user", "content": "Hello"}]
        responses = [{"type": "user_prompt", "content": "Hello"}]

        await chat_service.update_chat_messages(chat, messages)
        await chat_service.add_chat_responses(chat, responses)
        await chat_service.update_chat_token_usage(chat, 50, 10, 40)

        # Verify all operations
        assert chat == new_chat
        assert is_new is True
        assert last_msg_id is None

        chat_service.track_chat_created.assert_called_once_with(
            mock_user, "new_chat")
        new_chat.update_messages.assert_called_once_with(messages, None)
        new_chat.add_responses.assert_called_once_with(responses)
        new_chat.update_token_usage.assert_called_once_with(50, 10, 40)

    @pytest.mark.asyncio
    async def test_full_existing_chat_flow(self, chat_service, mock_user, location_info, mock_chat):
        """Test complete existing chat handling flow."""
        # Setup
        chat_service.Chat.get_chat_by_id.return_value = mock_chat
        chat_service.TokenUsage.add_usage = AsyncMock()

        # Execute
        chat, is_new, last_msg_id = chat_service.get_or_create_chat(
            "existing_chat", mock_user, location_info
        )

        await chat_service.record_token_usage(mock_user, 100, 20, 80)
        chat_service.track_user_prompt(
            mock_user, "existing_chat", "Hello again")

        # Verify
        assert chat == mock_chat
        assert is_new is False
        assert last_msg_id == "last_msg_789"

        chat_service.using_existing_chat.assert_called_once_with(
            mock_user, "existing_chat")
        chat_service.TokenUsage.add_usage.assert_called_once_with(
            mock_user, 100, 20, 80)
        chat_service.track_prompt.assert_called_once_with(
            mock_user, "existing_chat", "Hello again")


class TestChatServiceEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_zero_token_usage(self, chat_service, mock_user, mock_chat):
        """Test handling zero token usage."""
        # Setup
        chat_service.TokenUsage.add_usage = AsyncMock()

        # Execute
        await chat_service.record_token_usage(mock_user, 0, 0, 0)
        await chat_service.update_chat_token_usage(mock_chat, 0, 0, 0)

        # Verify
        chat_service.TokenUsage.add_usage.assert_called_once_with(
            mock_user, 0, 0, 0)
        mock_chat.update_token_usage.assert_called_once_with(0, 0, 0)

    @pytest.mark.asyncio
    async def test_empty_messages_and_responses(self, chat_service, mock_chat):
        """Test handling empty messages and responses."""
        # Execute
        await chat_service.update_chat_messages(mock_chat, [])
        await chat_service.add_chat_responses(mock_chat, [])

        # Verify
        mock_chat.update_messages.assert_called_once_with([], None)
        mock_chat.add_responses.assert_called_once_with([])

    def test_track_tool_call_with_none_description(self, chat_service, mock_user):
        """Test tool call tracking with explicit None description."""
        # Execute
        chat_service.track_tool_call(mock_user, "chat_123", "tool_name", None)

        # Verify (should call without description)
        chat_service.track_tool_called.assert_called_once_with(
            mock_user, "chat_123", "tool_name")

    @patch('services.chat_service.logger')
    def test_logging_on_chat_creation(self, mock_logger, chat_service, mock_user, location_info):
        """Test that chat creation logs appropriately."""
        # Setup
        new_chat = Mock()
        chat_service.Chat.get_chat_by_id.return_value = None
        chat_service.Chat.create_chat.return_value = new_chat

        # Execute
        chat_service.get_or_create_chat("new_chat", mock_user, location_info)

        # Verify logging
        mock_logger.info.assert_called_with(
            f"Created new chat new_chat for user {mock_user.reference_id}"
        )

    @patch('services.chat_service.logger')
    def test_logging_on_existing_chat(self, mock_logger, chat_service, mock_user, location_info, mock_chat):
        """Test that existing chat usage logs appropriately."""
        # Setup
        chat_service.Chat.get_chat_by_id.return_value = mock_chat

        # Execute
        chat_service.get_or_create_chat(
            "existing_chat", mock_user, location_info)

        # Verify logging
        mock_logger.info.assert_called_with(
            f"Using existing chat existing_chat for user {mock_user.reference_id}"
        )


# Pytest configuration and fixtures for the entire test module
@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all mocks between tests."""
    yield
    # Any cleanup can be done here if needed


if __name__ == "__main__":
    # Allow running tests directly with python -m pytest
    pytest.main([__file__])
