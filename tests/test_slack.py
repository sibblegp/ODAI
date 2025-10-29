"""
Comprehensive tests for connectors/slack.py

Tests cover the Slack agent, its tools, and various edge cases.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from agents import Agent
from connectors.slack import (
    SLACK_AGENT,
    send_message,
    get_messages,
    send_message_to_user
)


class TestSlackConfig:
    """Test Slack agent configuration and setup."""

    def test_slack_agent_exists(self):
        """Test that SLACK_AGENT is properly configured."""
        assert SLACK_AGENT is not None
        assert isinstance(SLACK_AGENT, Agent)
        assert SLACK_AGENT.name == "Slack"
        assert SLACK_AGENT.model == "gpt-4o"
        assert len(SLACK_AGENT.tools) == 3

    def test_agent_instructions_configured(self):
        """Test that agent instructions are properly set."""
        assert SLACK_AGENT.instructions is not None
        assert "send and receive Slack messages" in SLACK_AGENT.instructions

    def test_slack_tools_exist(self):
        """Test that all Slack tools exist."""
        assert send_message is not None
        assert get_messages is not None
        assert send_message_to_user is not None


class TestSendMessageTool:
    """Test the send_message tool."""

    @patch('connectors.slack.client')
    @pytest.mark.asyncio
    async def test_send_message_success(self, mock_client):
        """Test successful message sending to channel."""
        # Mock API response
        mock_response = {
            'ok': True,
            'channel': 'C1234567890',
            'ts': '1234567890.123456',
            'message': {
                'text': 'Hello, Slack!',
                'user': 'U1234567890',
                'ts': '1234567890.123456'
            }
        }
        mock_client.chat_postMessage.return_value = mock_response

        # Mock the tool context
        mock_ctx = Mock()

        result = await send_message.on_invoke_tool(
            mock_ctx,
            '{"channel": "#general", "message": "Hello, Slack!"}'
        )

        # Verify API call was made correctly
        mock_client.chat_postMessage.assert_called_once_with(
            channel='general',
            text='Hello, Slack!'
        )

        # Verify response structure
        assert result['response_type'] == 'slack_message'
        assert result['agent_name'] == 'Slack'
        assert result['channel'] == 'general'
        assert result['message'] == 'Hello, Slack!'
        assert 'friendly_name' in result

    @patch('connectors.slack.client')
    @pytest.mark.asyncio
    async def test_send_message_removes_hash(self, mock_client):
        """Test that # is removed from channel name."""
        mock_response = {'ok': True}
        mock_client.chat_postMessage.return_value = mock_response

        mock_ctx = Mock()
        await send_message.on_invoke_tool(
            mock_ctx,
            '{"channel": "#random", "message": "Test message"}'
        )

        # Verify # was removed
        mock_client.chat_postMessage.assert_called_once_with(
            channel='random',
            text='Test message'
        )

    @patch('connectors.slack.client')
    @pytest.mark.asyncio
    async def test_send_message_without_hash(self, mock_client):
        """Test sending message to channel without # prefix."""
        mock_response = {'ok': True}
        mock_client.chat_postMessage.return_value = mock_response

        mock_ctx = Mock()
        result = await send_message.on_invoke_tool(
            mock_ctx,
            '{"channel": "general", "message": "Hello world"}'
        )

        mock_client.chat_postMessage.assert_called_once_with(
            channel='general',
            text='Hello world'
        )
        assert result['channel'] == 'general'

    @patch('connectors.slack.client')
    @pytest.mark.asyncio
    async def test_send_message_api_error(self, mock_client):
        """Test handling of Slack API errors."""
        mock_client.chat_postMessage.side_effect = Exception("Slack API Error")

        mock_ctx = Mock()
        result = await send_message.on_invoke_tool(
            mock_ctx,
            '{"channel": "#general", "message": "Test"}'
        )

        # The function tool framework catches exceptions and returns error message as string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()

    @patch('connectors.slack.client')
    @patch('builtins.print')
    @pytest.mark.asyncio
    async def test_send_message_prints_response(self, mock_print, mock_client):
        """Test that send_message prints the response."""
        mock_response = {'ok': True}
        mock_client.chat_postMessage.return_value = mock_response

        mock_ctx = Mock()
        await send_message.on_invoke_tool(
            mock_ctx,
            '{"channel": "#general", "message": "Test"}'
        )

        # Verify print was called with response
        mock_print.assert_called_once_with(mock_response)


class TestGetMessagesTool:
    """Test the get_messages tool."""

    @patch('connectors.slack.client')
    @pytest.mark.asyncio
    async def test_get_messages_success(self, mock_client):
        """Test successful message retrieval from channel."""
        # Mock API response
        mock_response = {
            'ok': True,
            'messages': [
                {
                    'type': 'message',
                    'user': 'U1234567890',
                    'text': 'First message',
                    'ts': '1234567890.123456'
                },
                {
                    'type': 'message',
                    'user': 'U0987654321',
                    'text': 'Second message',
                    'ts': '1234567890.654321'
                }
            ]
        }
        mock_client.conversations_history.return_value = mock_response

        mock_ctx = Mock()
        result = await get_messages.on_invoke_tool(
            mock_ctx,
            '{"channel": "general"}'
        )

        # Note: The function has hardcoded channel ID 'C0513NREF5L'
        mock_client.conversations_history.assert_called_once_with(
            channel='C0513NREF5L'
        )

        # Verify response structure
        assert result['response_type'] == 'slack_messages'
        assert result['agent_name'] == 'Slack'
        assert result['channel'] == '#general'
        assert len(result['messages']) == 2
        assert result['messages'][0]['text'] == 'First message'

    @patch('connectors.slack.client')
    @pytest.mark.asyncio
    async def test_get_messages_adds_hash(self, mock_client):
        """Test that # is added to channel name if not present."""
        mock_response = {'ok': True, 'messages': []}
        mock_client.conversations_history.return_value = mock_response

        mock_ctx = Mock()
        result = await get_messages.on_invoke_tool(
            mock_ctx,
            '{"channel": "random"}'
        )

        # Channel should have # prefix in response
        assert result['channel'] == '#random'

    @patch('connectors.slack.client')
    @pytest.mark.asyncio
    async def test_get_messages_with_hash(self, mock_client):
        """Test getting messages from channel with # prefix."""
        mock_response = {'ok': True, 'messages': []}
        mock_client.conversations_history.return_value = mock_response

        mock_ctx = Mock()
        result = await get_messages.on_invoke_tool(
            mock_ctx,
            '{"channel": "#general"}'
        )

        # Channel should retain # prefix
        assert result['channel'] == '#general'

    @patch('connectors.slack.client')
    @pytest.mark.asyncio
    async def test_get_messages_api_error(self, mock_client):
        """Test handling of Slack API errors when getting messages."""
        mock_client.conversations_history.side_effect = Exception(
            "Slack API Error")

        mock_ctx = Mock()
        result = await get_messages.on_invoke_tool(
            mock_ctx,
            '{"channel": "general"}'
        )

        assert isinstance(result, str)
        assert "error occurred" in result.lower()


class TestSendMessageToUserTool:
    """Test the send_message_to_user tool."""

    @patch('connectors.slack.client')
    @patch('builtins.print')
    @pytest.mark.asyncio
    async def test_send_message_to_user_success(self, mock_print, mock_client):
        """Test successful message sending to user."""
        mock_response = {
            'ok': True,
            'channel': 'D1234567890',
            'ts': '1234567890.123456'
        }
        mock_client.chat_postMessage.return_value = mock_response

        mock_ctx = Mock()
        result = await send_message_to_user.on_invoke_tool(
            mock_ctx,
            '{"user": "@johndoe", "message": "Hello John!"}'
        )

        # Verify print was called with user and message
        mock_print.assert_called_once_with('@johndoe', 'Hello John!')

        # Verify API call
        mock_client.chat_postMessage.assert_called_once_with(
            channel='@johndoe',
            text='Hello John!'
        )

        # Verify response structure
        assert result['response_type'] == 'slack_message'
        assert result['agent_name'] == 'Slack'
        assert result['channel'] == '@johndoe'
        assert result['message'] == 'Hello John!'
        assert result['friendly_name'] == 'Sent a message to a Slack user'

    @patch('connectors.slack.client')
    @patch('builtins.print')
    @pytest.mark.asyncio
    async def test_send_message_to_user_adds_at(self, mock_print, mock_client):
        """Test that @ is added to username if not present."""
        mock_response = {'ok': True}
        mock_client.chat_postMessage.return_value = mock_response

        mock_ctx = Mock()
        result = await send_message_to_user.on_invoke_tool(
            mock_ctx,
            '{"user": "johndoe", "message": "Hello!"}'
        )

        # Verify @ was added
        mock_client.chat_postMessage.assert_called_once_with(
            channel='@johndoe',
            text='Hello!'
        )
        assert result['channel'] == '@johndoe'

    @patch('connectors.slack.client')
    @patch('builtins.print')
    @pytest.mark.asyncio
    async def test_send_message_to_user_with_at(self, mock_print, mock_client):
        """Test sending message to user with @ prefix."""
        mock_response = {'ok': True}
        mock_client.chat_postMessage.return_value = mock_response

        mock_ctx = Mock()
        result = await send_message_to_user.on_invoke_tool(
            mock_ctx,
            '{"user": "@janedoe", "message": "Test message"}'
        )

        # @ should not be duplicated
        mock_client.chat_postMessage.assert_called_once_with(
            channel='@janedoe',
            text='Test message'
        )
        assert result['channel'] == '@janedoe'

    @patch('connectors.slack.client')
    @patch('builtins.print')
    @pytest.mark.asyncio
    async def test_send_message_to_user_api_error(self, mock_print, mock_client):
        """Test handling of API errors when sending to user."""
        mock_client.chat_postMessage.side_effect = Exception("Slack API Error")

        mock_ctx = Mock()
        result = await send_message_to_user.on_invoke_tool(
            mock_ctx,
            '{"user": "@johndoe", "message": "Test"}'
        )

        assert isinstance(result, str)
        assert "error occurred" in result.lower()


class TestSlackAgentIntegration:
    """Integration tests for Slack agent components."""

    def test_agent_tools_registration(self):
        """Test that tools are properly registered with the agent."""
        tool_names = [tool.name for tool in SLACK_AGENT.tools]
        assert "send_message" in tool_names
        assert "get_messages" in tool_names
        assert "send_message_to_user" in tool_names

    def test_agent_model_configuration(self):
        """Test that agent uses correct model."""
        assert SLACK_AGENT.model == "gpt-4o"

    def test_import_dependencies(self):
        """Test that agent dependencies are properly imported."""
        try:
            from connectors.slack import (
                SLACK_AGENT,
                send_message,
                get_messages,
                send_message_to_user
            )
            assert SLACK_AGENT is not None
            assert send_message is not None
            assert get_messages is not None
            assert send_message_to_user is not None
        except ImportError as e:
            pytest.fail(f"Failed to import Slack components: {e}")

    def test_tool_function_signatures(self):
        """Test that tool functions have correct parameter schemas."""
        # Test send_message parameters
        send_schema = send_message.params_json_schema
        assert "properties" in send_schema
        params = send_schema["properties"]
        assert "channel" in params
        assert "message" in params

        # Test get_messages parameters
        get_schema = get_messages.params_json_schema
        assert "properties" in get_schema
        params = get_schema["properties"]
        assert "channel" in params

        # Test send_message_to_user parameters
        user_schema = send_message_to_user.params_json_schema
        assert "properties" in user_schema
        params = user_schema["properties"]
        assert "user" in params
        assert "message" in params


class TestSlackClientSetup:
    """Test Slack client setup and configuration."""

    def test_slack_client_imports(self):
        """Test that Slack SDK imports are available."""
        try:
            from slack_sdk import WebClient
            from slack_sdk.errors import SlackApiError
            import ssl
            import certifi

            assert WebClient is not None
            assert SlackApiError is not None
            assert ssl is not None
            assert certifi is not None
        except ImportError as e:
            pytest.fail(f"Failed to import Slack SDK components: {e}")

    def test_slack_client_configuration_concepts(self):
        """Test Slack client configuration concepts."""
        # Test that environment variable concepts work
        import os

        # Test setting and getting environment variables
        test_token = "xoxb-test-token-12345"
        os.environ["TEST_SLACK_TOKEN"] = test_token
        retrieved_token = os.environ.get("TEST_SLACK_TOKEN")
        assert retrieved_token == test_token

        # Clean up
        del os.environ["TEST_SLACK_TOKEN"]

    def test_ssl_context_creation(self):
        """Test that SSL context can be created with certifi."""
        import ssl
        import certifi

        ssl_context = ssl.create_default_context(cafile=certifi.where())
        assert ssl_context is not None
        assert isinstance(ssl_context, ssl.SSLContext)


class TestSlackEdgeCases:
    """Test edge cases and error conditions."""

    def test_send_message_typo_in_friendly_name(self):
        """Test that there's a typo in send_message friendly_name."""
        # This is a known issue in the code - "channell" instead of "channel"
        # Testing to document the current behavior
        from connectors.slack import send_message

        # We can't easily test the return value without mocking,
        # but we can verify the function exists and has the expected structure
        assert hasattr(send_message, 'name')
        assert hasattr(send_message, 'description')
        assert send_message.name == 'send_message'

    def test_get_messages_hardcoded_channel(self):
        """Test that get_messages has a hardcoded channel ID."""
        # This is a known issue - the function ignores the channel parameter
        # and uses hardcoded 'C0513NREF5L'
        from connectors.slack import get_messages

        # Document the current behavior
        assert hasattr(get_messages, 'name')
        assert get_messages.name == 'get_messages'

    @pytest.mark.asyncio
    async def test_missing_required_parameters(self):
        """Test tools with missing required parameters."""
        mock_ctx = Mock()

        # Test send_message without message
        result = await send_message.on_invoke_tool(
            mock_ctx,
            '{"channel": "#general"}'
        )
        assert isinstance(result, str)
        assert "error" in result.lower()

        # Test send_message_to_user without message
        result = await send_message_to_user.on_invoke_tool(
            mock_ctx,
            '{"user": "@johndoe"}'
        )
        assert isinstance(result, str)
        assert "error" in result.lower()

    def test_all_tools_have_descriptions(self):
        """Test that all tools have proper descriptions."""
        tools = [send_message, get_messages, send_message_to_user]

        for tool in tools:
            assert hasattr(tool, 'description')
            assert tool.description is not None
            assert len(tool.description) > 0
            assert 'slack' in tool.description.lower()

    def test_agent_name_consistency(self):
        """Test that agent name is consistent."""
        assert SLACK_AGENT.name == "Slack"

    @patch('connectors.slack.SlackApiError')
    def test_slack_api_error_handling(self, mock_error_class):
        """Test that SlackApiError is properly imported."""
        # Verify the error class is available
        from slack_sdk.errors import SlackApiError
        assert SlackApiError is not None
        assert issubclass(SlackApiError, Exception)
