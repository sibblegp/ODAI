"""
Comprehensive tests for connectors/evernote.py

Tests cover the Evernote agent, its tools, and various edge cases.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from agents import Agent
from connectors.evernote import (
    EVERNOTE_AGENT,
    create_evernote_note
)


class TestEvernoteConfig:
    """Test Evernote agent configuration and setup."""

    def test_evernote_agent_exists(self):
        """Test that EVERNOTE_AGENT is properly configured."""
        assert EVERNOTE_AGENT is not None
        assert isinstance(EVERNOTE_AGENT, Agent)
        assert EVERNOTE_AGENT.name == "Evernote"
        assert EVERNOTE_AGENT.model == "gpt-4o"
        assert len(EVERNOTE_AGENT.tools) == 1

    def test_agent_handoffs_configured(self):
        """Test that agent handoffs are properly configured."""
        assert hasattr(EVERNOTE_AGENT, 'handoffs')
        # GOOGLE_DOCS_AGENT, GMAIL_AGENT
        assert len(EVERNOTE_AGENT.handoffs) == 2

    def test_agent_instructions_configured(self):
        """Test that agent instructions are properly set."""
        assert EVERNOTE_AGENT.instructions is not None
        # Instructions now focus on functionality
        assert "evernote" in EVERNOTE_AGENT.instructions.lower(
        ) or "note" in EVERNOTE_AGENT.instructions.lower()

    def test_agent_handoff_description_configured(self):
        """Test that agent handoff description is properly set."""
        assert EVERNOTE_AGENT.handoff_description is not None
        # Handoff description focuses on functionality
        assert "evernote" in EVERNOTE_AGENT.handoff_description.lower(
        ) or "note" in EVERNOTE_AGENT.handoff_description.lower()


class TestCreateEvernoteNoteTool:
    """Test the create_evernote_note tool."""

    @patch('connectors.evernote.EvernoteToken.get_evernote_token_by_user_id')
    @patch('connectors.evernote.EvernoteClient')
    @pytest.mark.asyncio
    async def test_create_note_success(self, mock_evernote_client, mock_get_token):
        """Test successful note creation."""
        # Mock Evernote token
        mock_token = Mock()
        mock_token.access_token = "test_access_token"
        mock_get_token.return_value = mock_token

        # Mock Evernote client and note store
        mock_client_instance = Mock()
        mock_note_store = Mock()
        mock_client_instance.get_note_store.return_value = mock_note_store
        mock_evernote_client.return_value = mock_client_instance

        # Mock the tool context
        mock_ctx = Mock()

        result = await create_evernote_note.on_invoke_tool(
            mock_ctx,
            '{"title": "Test Note", "content": "This is a test note content"}'
        )

        # Verify calls
        assert mock_get_token.call_count == 1
        mock_evernote_client.assert_called_once_with(
            token="test_access_token", sandbox=False)
        mock_client_instance.get_note_store.assert_called_once()
        mock_note_store.createNote.assert_called_once()

        # Verify response
        assert result["response_type"] == "evernote_note_created"
        assert result["agent_name"] == "Evernote"
        assert result["friendly_name"] == "Evernote Note Created"
        assert result["display_response"] is False
        assert result["response"]["success"] is True

    @patch('connectors.evernote.EvernoteToken.get_evernote_token_by_user_id')
    @pytest.mark.asyncio
    async def test_create_note_no_token(self, mock_get_token):
        """Test note creation when user has no Evernote token."""
        # Mock no token found
        mock_get_token.return_value = None

        # Mock the tool context
        mock_ctx = Mock()

        result = await create_evernote_note.on_invoke_tool(
            mock_ctx,
            '{"title": "Test Note", "content": "This is a test note content"}'
        )

        # Verify response indicates need to connect account
        assert result["response_type"] == "error"
        assert result["agent_name"] == "Evernote"
        assert result["display_response"] is True
        assert "not connected to Evernote" in result["response"]
        assert "connect your Evernote account" in result["response"]

    @patch('connectors.evernote.EvernoteToken.get_evernote_token_by_user_id')
    @patch('connectors.evernote.EvernoteClient')
    @pytest.mark.asyncio
    async def test_create_note_evernote_api_error(self, mock_evernote_client, mock_get_token):
        """Test handling of Evernote API errors."""
        # Mock Evernote token
        mock_token = Mock()
        mock_token.access_token = "test_access_token"
        mock_get_token.return_value = mock_token

        # Mock Evernote client to raise error
        mock_evernote_client.side_effect = Exception("Evernote API Error")

        # Mock the tool context
        mock_ctx = Mock()

        result = await create_evernote_note.on_invoke_tool(
            mock_ctx,
            '{"title": "Test Note", "content": "Content"}'
        )

        # Verify error response
        assert result["response_type"] == "error"
        assert result["agent_name"] == "Evernote"
        assert result["display_response"] is True
        assert "Error creating Evernote note" in result["response"]
        assert "Evernote API Error" in result["response"]

    @patch('connectors.evernote.EvernoteToken.get_evernote_token_by_user_id')
    @patch('connectors.evernote.EvernoteClient')
    @pytest.mark.asyncio
    async def test_create_note_note_store_error(self, mock_evernote_client, mock_get_token):
        """Test handling of note store errors."""
        # Mock Evernote token
        mock_token = Mock()
        mock_token.access_token = "test_access_token"
        mock_get_token.return_value = mock_token

        # Mock Evernote client and note store with error
        mock_client_instance = Mock()
        mock_note_store = Mock()
        mock_note_store.createNote.side_effect = Exception(
            "Note creation failed")
        mock_client_instance.get_note_store.return_value = mock_note_store
        mock_evernote_client.return_value = mock_client_instance

        # Mock the tool context
        mock_ctx = Mock()

        result = await create_evernote_note.on_invoke_tool(
            mock_ctx,
            '{"title": "Test Note", "content": "Content"}'
        )

        # Verify error response
        assert result["response_type"] == "error"
        assert "Error creating Evernote note" in result["response"]
        assert "Note creation failed" in result["response"]

    @patch('connectors.evernote.EvernoteToken.get_evernote_token_by_user_id')
    @patch('connectors.evernote.EvernoteClient')
    @pytest.mark.asyncio
    async def test_create_note_with_html_content(self, mock_evernote_client, mock_get_token):
        """Test note creation with HTML content."""
        # Mock Evernote token
        mock_token = Mock()
        mock_token.access_token = "test_access_token"
        mock_get_token.return_value = mock_token

        # Mock Evernote client and note store
        mock_client_instance = Mock()
        mock_note_store = Mock()
        mock_client_instance.get_note_store.return_value = mock_note_store
        mock_evernote_client.return_value = mock_client_instance

        # Mock the tool context
        mock_ctx = Mock()

        html_content = "<p>This is <strong>HTML</strong> content</p>"
        result = await create_evernote_note.on_invoke_tool(
            mock_ctx,
            f'{{"title": "HTML Note", "content": "{html_content}"}}'
        )

        # Verify successful creation
        assert result["response"]["success"] is True
        mock_note_store.createNote.assert_called_once()

    @patch('connectors.evernote.EvernoteToken.get_evernote_token_by_user_id')
    @patch('connectors.evernote.EvernoteClient')
    @pytest.mark.asyncio
    async def test_create_note_with_long_content(self, mock_evernote_client, mock_get_token):
        """Test note creation with very long content."""
        # Mock Evernote token
        mock_token = Mock()
        mock_token.access_token = "test_access_token"
        mock_get_token.return_value = mock_token

        # Mock Evernote client and note store
        mock_client_instance = Mock()
        mock_note_store = Mock()
        mock_client_instance.get_note_store.return_value = mock_note_store
        mock_evernote_client.return_value = mock_client_instance

        # Mock the tool context
        mock_ctx = Mock()

        long_content = "A" * 10000  # Very long content
        result = await create_evernote_note.on_invoke_tool(
            mock_ctx,
            f'{{"title": "Long Note", "content": "{long_content}"}}'
        )

        # Verify successful creation
        assert result["response"]["success"] is True

    @patch('connectors.evernote.EvernoteToken.get_evernote_token_by_user_id')
    @patch('connectors.evernote.EvernoteClient')
    @pytest.mark.asyncio
    async def test_create_note_with_empty_title(self, mock_evernote_client, mock_get_token):
        """Test note creation with empty title."""
        # Mock Evernote token
        mock_token = Mock()
        mock_token.access_token = "test_access_token"
        mock_get_token.return_value = mock_token

        # Mock Evernote client and note store
        mock_client_instance = Mock()
        mock_note_store = Mock()
        mock_client_instance.get_note_store.return_value = mock_note_store
        mock_evernote_client.return_value = mock_client_instance

        # Mock the tool context
        mock_ctx = Mock()

        result = await create_evernote_note.on_invoke_tool(
            mock_ctx,
            '{"title": "", "content": "Content without title"}'
        )

        # Verify successful creation (Evernote should handle empty titles)
        assert result["response"]["success"] is True

    @patch('connectors.evernote.EvernoteToken.get_evernote_token_by_user_id')
    @patch('connectors.evernote.EvernoteClient')
    @pytest.mark.asyncio
    async def test_create_note_with_special_characters(self, mock_evernote_client, mock_get_token):
        """Test note creation with special characters in title and content."""
        # Mock Evernote token
        mock_token = Mock()
        mock_token.access_token = "test_access_token"
        mock_get_token.return_value = mock_token

        # Mock Evernote client and note store
        mock_client_instance = Mock()
        mock_note_store = Mock()
        mock_client_instance.get_note_store.return_value = mock_note_store
        mock_evernote_client.return_value = mock_client_instance

        # Mock the tool context
        mock_ctx = Mock()

        result = await create_evernote_note.on_invoke_tool(
            mock_ctx,
            '{"title": "Special: éñ 中文 🚀", "content": "Content with émojis 🎉 and unicode ñáéíóú"}'
        )

        # Verify successful creation
        assert result["response"]["success"] is True


class TestEvernoteAgentIntegration:
    """Integration tests for Evernote agent components."""

    def test_agent_tools_registration(self):
        """Test that tools are properly registered with the agent."""
        tool_names = [tool.name for tool in EVERNOTE_AGENT.tools]
        assert "create_evernote_note" in tool_names

    def test_agent_model_configuration(self):
        """Test that agent uses correct model."""
        assert EVERNOTE_AGENT.model == "gpt-4o"

    def test_import_dependencies(self):
        """Test that agent dependencies are properly imported."""
        # This test ensures the import structure works
        try:
            from connectors.evernote import (
                EVERNOTE_AGENT,
                create_evernote_note
            )
            assert EVERNOTE_AGENT is not None
            assert create_evernote_note is not None
        except ImportError as e:
            pytest.fail(f"Failed to import Evernote components: {e}")


class TestEvernoteEdgeCases:
    """Test edge cases and error conditions."""

    def test_tool_function_signature(self):
        """Test that tool function has correct parameter schema."""
        schema = create_evernote_note.params_json_schema
        assert "properties" in schema
        params = schema["properties"]
        assert "title" in params
        assert "content" in params
        assert params["title"]["type"] == "string"
        assert params["content"]["type"] == "string"

    @pytest.mark.asyncio
    async def test_tool_response_format_consistency(self):
        """Test that tool returns consistent ToolResponse format."""
        with patch('connectors.evernote.EvernoteToken.get_evernote_token_by_user_id') as mock_get_token:
            with patch('connectors.evernote.EvernoteClient') as mock_evernote_client:
                # Mock no token scenario
                mock_get_token.return_value = None

                # Mock the tool context
                mock_ctx = Mock()

                result = await create_evernote_note.on_invoke_tool(
                    mock_ctx,
                    '{"title": "Test", "content": "Test content"}'
                )

                # Verify ToolResponse format
                required_fields = ["response_type", "agent_name",
                                   "friendly_name", "display_response", "response"]
                for field in required_fields:
                    assert field in result

                assert result["response_type"] == "error"
                assert result["agent_name"] == "Evernote"
                assert result["display_response"] is True

    def test_agent_name_consistency(self):
        """Test that agent name is consistent."""
        assert EVERNOTE_AGENT.name == "Evernote"

    @patch('connectors.evernote.EvernoteToken.get_evernote_token_by_user_id')
    @patch('connectors.evernote.EvernoteClient')
    @pytest.mark.asyncio
    async def test_create_note_sandbox_mode(self, mock_evernote_client, mock_get_token):
        """Test that Evernote client is created with sandbox=False."""
        # Mock Evernote token
        mock_token = Mock()
        mock_token.access_token = "test_access_token"
        mock_get_token.return_value = mock_token

        # Mock Evernote client
        mock_client_instance = Mock()
        mock_note_store = Mock()
        mock_client_instance.get_note_store.return_value = mock_note_store
        mock_evernote_client.return_value = mock_client_instance

        # Mock the tool context
        mock_ctx = Mock()

        await create_evernote_note.on_invoke_tool(
            mock_ctx,
            '{"title": "Test", "content": "Test content"}'
        )

        # Verify Evernote client created with sandbox=False
        mock_evernote_client.assert_called_once_with(
            token="test_access_token", sandbox=False)

    @patch('connectors.evernote.EvernoteToken.get_evernote_token_by_user_id')
    @pytest.mark.asyncio
    async def test_create_note_database_error(self, mock_get_token):
        """Test handling of database errors when getting token."""
        mock_get_token.side_effect = Exception("Database connection error")

        # Mock the tool context
        mock_ctx = Mock()

        result = await create_evernote_note.on_invoke_tool(
            mock_ctx,
            '{"title": "Test", "content": "Test content"}'
        )

        # Verify error response
        assert result["response_type"] == "error"
        assert "Error creating Evernote note" in result["response"]
        assert "Database connection error" in result["response"]
