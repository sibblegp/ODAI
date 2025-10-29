"""
Comprehensive tests for connectors/google_connections.py

Tests cover the Google Connections agent and the connect_google_account function tool
for handling Google account connection and access request workflows.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from agents import RunContextWrapper


class TestGoogleConnectionsAgent:
    """Test cases for GOOGLE_CONNECTIONS_AGENT."""

    def test_google_connections_agent_import(self):
        """Test that GOOGLE_CONNECTIONS_AGENT can be imported."""
        from connectors.google_connections import GOOGLE_CONNECTIONS_AGENT
        
        assert GOOGLE_CONNECTIONS_AGENT is not None
        assert hasattr(GOOGLE_CONNECTIONS_AGENT, 'name')
        assert hasattr(GOOGLE_CONNECTIONS_AGENT, 'instructions')
        assert hasattr(GOOGLE_CONNECTIONS_AGENT, 'tools')

    def test_google_connections_agent_configuration(self):
        """Test GOOGLE_CONNECTIONS_AGENT configuration."""
        from connectors.google_connections import GOOGLE_CONNECTIONS_AGENT
        
        # Verify agent name
        assert GOOGLE_CONNECTIONS_AGENT.name == "Google Connections"
        
        # Verify instructions contain key phrases
        assert "handling when a user is not connected to Google" in GOOGLE_CONNECTIONS_AGENT.instructions
        assert "ALWAYS CALL THE connect_google_account TOOL" in GOOGLE_CONNECTIONS_AGENT.instructions
        
        # Verify tools
        assert len(GOOGLE_CONNECTIONS_AGENT.tools) == 1
        # The tool is a FunctionTool object, check its name
        tool = GOOGLE_CONNECTIONS_AGENT.tools[0]
        assert hasattr(tool, 'name') or hasattr(tool, '_name') or str(tool).find('connect_google_account') != -1

    def test_google_connections_agent_has_connect_google_account_tool(self):
        """Test that GOOGLE_CONNECTIONS_AGENT has connect_google_account tool."""
        from connectors.google_connections import GOOGLE_CONNECTIONS_AGENT, connect_google_account
        
        # The tool should be in the agent's tools list
        assert connect_google_account in GOOGLE_CONNECTIONS_AGENT.tools


class TestConnectGoogleAccountFunction:
    """Test cases for the connect_google_account function."""

    @pytest.fixture
    def mock_wrapper(self):
        """Create a mock RunContextWrapper."""
        wrapper = Mock(spec=RunContextWrapper)
        wrapper.context = Mock()
        wrapper.context.user = Mock()
        wrapper.context.user.reference_id = "test_user_123"
        wrapper.context.user.google_access_request = None
        wrapper.context.agent_name = "Google Connections"
        return wrapper

    @pytest.mark.asyncio
    @patch('connectors.google_connections.GoogleAccessRequest')
    async def test_connect_google_account_with_request_and_ready(self, mock_google_access_request, mock_wrapper):
        """Test when existing request exists and user is ready_for_google."""
        from connectors.google_connections import connect_google_account
        
        # Configure mock to return an existing request
        mock_existing_request = Mock()
        mock_google_access_request.get_request_for_user.return_value = mock_existing_request
        # User has ready_for_google attribute set to True
        mock_wrapper.context.user.ready_for_google = True
        
        # Call the function using on_invoke_tool (pass empty dict as input)
        result = await connect_google_account.on_invoke_tool(mock_wrapper, {})
        
        # Should return ConnectGoogleAccountResponse
        assert result['response_type'] == 'connect_google_account'
        assert result['agent_name'] == 'Google Connections'
        assert result['friendly_name'] == 'Connect Google Account'
        assert result['response'] == "Please press the button above to connect your Google account"
        assert result['display_response'] == True
        
        # Verify GoogleAccessRequest was called correctly
        mock_google_access_request.get_request_for_user.assert_called_once_with("test_user_123")

    @pytest.mark.asyncio
    @patch('connectors.google_connections.GoogleAccessRequest')
    async def test_connect_google_account_default_case(self, mock_google_access_request, mock_wrapper):
        """Test default case - returns RequestGoogleAccessResponse."""
        from connectors.google_connections import connect_google_account
        
        # Configure mock - any combination that doesn't meet the condition
        # Case 1: No existing request
        mock_google_access_request.get_request_for_user.return_value = None
        # Explicitly set ready_for_google to False to avoid Mock's hasattr behavior
        mock_wrapper.context.user.ready_for_google = False
        
        # Call the function using on_invoke_tool (pass empty dict as input)
        result = await connect_google_account.on_invoke_tool(mock_wrapper, {})
        
        # Should return RequestGoogleAccessResponse (default)
        assert result['response_type'] == 'request_google_access'
        assert result['agent_name'] == 'Google Connections'
        assert result['friendly_name'] == 'Request Google Access'
        assert result['response'] == "Please press the button above to request access to your Google account"
        assert result['display_response'] == True

    @pytest.mark.asyncio
    @patch('connectors.google_connections.GoogleAccessRequest')
    async def test_connect_google_account_with_request_no_ready_attr(self, mock_google_access_request, mock_wrapper):
        """Test when existing request but no ready_for_google attribute."""
        from connectors.google_connections import connect_google_account
        
        # Configure mock to return an existing request
        mock_existing_request = Mock()
        mock_google_access_request.get_request_for_user.return_value = mock_existing_request
        # Remove ready_for_google attribute if it exists
        if hasattr(mock_wrapper.context.user, 'ready_for_google'):
            delattr(mock_wrapper.context.user, 'ready_for_google')
        
        # Call the function using on_invoke_tool (pass empty dict as input)
        result = await connect_google_account.on_invoke_tool(mock_wrapper, {})
        
        # Should return ToolResponse with existing request message
        assert result['response_type'] == 'google_access_request'
        assert result['agent_name'] == 'Google Connections'
        assert result['friendly_name'] == 'Existing Google Access Request'
        assert result['response'] == 'You already have an existing Google access request. Please wait for it to be approved.'
        assert result['display_response'] == True
        
        # Verify GoogleAccessRequest was called correctly
        mock_google_access_request.get_request_for_user.assert_called_once_with("test_user_123")

    @pytest.mark.asyncio
    @patch('connectors.google_connections.GoogleAccessRequest')
    async def test_connect_google_account_with_request_ready_false(self, mock_google_access_request, mock_wrapper):
        """Test when existing request and ready_for_google is False."""
        from connectors.google_connections import connect_google_account
        
        # Configure mock to return an existing request
        mock_existing_request = Mock()
        mock_google_access_request.get_request_for_user.return_value = mock_existing_request
        # User has ready_for_google attribute set to False
        mock_wrapper.context.user.ready_for_google = False
        
        # Call the function using on_invoke_tool (pass empty dict as input)
        result = await connect_google_account.on_invoke_tool(mock_wrapper, {})
        
        # Should return ToolResponse with existing request message (elif branch)
        assert result['response_type'] == 'google_access_request'
        assert result['agent_name'] == 'Google Connections'
        assert result['friendly_name'] == 'Existing Google Access Request'
        assert result['response'] == 'You already have an existing Google access request. Please wait for it to be approved.'
        assert result['display_response'] == True
        
        # Verify GoogleAccessRequest was called correctly
        mock_google_access_request.get_request_for_user.assert_called_once_with("test_user_123")

    def test_connect_google_account_function_attributes(self):
        """Test connect_google_account function attributes and decorators."""
        from connectors.google_connections import connect_google_account
        
        # Should have a description (FunctionTool attribute)
        assert hasattr(connect_google_account, 'description')
        assert "Agent Instruction:" in connect_google_account.description
        assert "Response Types to Expect:" in connect_google_account.description
        
        # Should be a FunctionTool
        assert hasattr(connect_google_account, 'on_invoke_tool')
        assert callable(connect_google_account.on_invoke_tool)

    @pytest.mark.asyncio
    @patch('connectors.google_connections.GoogleAccessRequest')
    async def test_connect_google_account_different_user_ids(self, mock_google_access_request, mock_wrapper):
        """Test connect_google_account with different user IDs."""
        from connectors.google_connections import connect_google_account
        
        user_ids = ["user_123", "user_456", "", "unicode_用户"]
        
        for user_id in user_ids:
            mock_wrapper.context.user.reference_id = user_id
            mock_google_access_request.get_request_for_user.return_value = None
            
            result = await connect_google_account.on_invoke_tool(mock_wrapper, {})
            
            # Should always return a valid response
            assert 'response_type' in result
            assert result['response_type'] in ['request_google_access', 'connect_google_account', 'google_access_request']
            
            # Verify the correct user ID was used
            mock_google_access_request.get_request_for_user.assert_called_with(user_id)
            mock_google_access_request.reset_mock()

    @pytest.mark.asyncio
    @patch('connectors.google_connections.GoogleAccessRequest')
    async def test_connect_google_account_different_agent_names(self, mock_google_access_request):
        """Test connect_google_account with different agent names."""
        from connectors.google_connections import connect_google_account
        
        agent_names = ["Google Connections", "Gmail Agent", "Calendar Agent", ""]
        
        for agent_name in agent_names:
            wrapper = Mock(spec=RunContextWrapper)
            wrapper.context = Mock()
            wrapper.context.user = Mock()
            wrapper.context.user.reference_id = "test_user"
            wrapper.context.agent_name = agent_name
            
            mock_google_access_request.get_request_for_user.return_value = None
            
            result = await connect_google_account.on_invoke_tool(wrapper, {})
            
            # Agent name should always be 'Google Connections' (hardcoded in the function)
            assert result['agent_name'] == 'Google Connections'

    def test_connect_google_account_response_types_import(self):
        """Test that response types can be imported correctly."""
        from connectors.google_connections import (
            ConnectGoogleAccountResponse,
            RequestGoogleAccessResponse
        )
        
        # Both should be classes
        assert isinstance(ConnectGoogleAccountResponse, type)
        assert isinstance(RequestGoogleAccessResponse, type)

    @pytest.mark.asyncio
    @patch('connectors.google_connections.GoogleAccessRequest')
    async def test_connect_google_account_response_consistency(self, mock_google_access_request, mock_wrapper):
        """Test that responses are consistent with response class definitions."""
        from connectors.google_connections import connect_google_account
        from connectors.utils.responses import ConnectGoogleAccountResponse, RequestGoogleAccessResponse
        
        # Test RequestGoogleAccessResponse case
        mock_google_access_request.get_request_for_user.return_value = None
        # Explicitly set ready_for_google to False to avoid Mock's hasattr behavior
        mock_wrapper.context.user.ready_for_google = False
        result = await connect_google_account.on_invoke_tool(mock_wrapper, {})
        
        # Create the response object directly and compare
        expected_response = RequestGoogleAccessResponse("Google Connections")
        assert result == expected_response.to_dict()
        
        # Test ConnectGoogleAccountResponse case
        mock_google_access_request.get_request_for_user.return_value = Mock()
        # Add ready_for_google to trigger ConnectGoogleAccountResponse
        mock_wrapper.context.user.ready_for_google = True
        result = await connect_google_account.on_invoke_tool(mock_wrapper, {})
        
        # Create the response object directly and compare
        expected_response = ConnectGoogleAccountResponse("Google Connections")
        assert result == expected_response.to_dict()


class TestGoogleConnectionsIntegration:
    """Integration tests for google_connections module."""

    def test_module_imports(self):
        """Test that all necessary imports work correctly."""
        try:
            from connectors.google_connections import (
                GOOGLE_CONNECTIONS_AGENT,
                connect_google_account,
                ConnectGoogleAccountResponse,
                RequestGoogleAccessResponse,
                ChatContext,
                GoogleAccessRequest
            )
            # All imports should succeed
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import from google_connections: {e}")

    def test_agent_tool_relationship(self):
        """Test the relationship between agent and its tools."""
        from connectors.google_connections import GOOGLE_CONNECTIONS_AGENT, connect_google_account
        
        # The agent should have exactly one tool
        assert len(GOOGLE_CONNECTIONS_AGENT.tools) == 1
        
        # The tool should be the connect_google_account function
        assert GOOGLE_CONNECTIONS_AGENT.tools[0] == connect_google_account

    @pytest.mark.asyncio
    @patch('connectors.google_connections.GoogleAccessRequest')
    async def test_full_workflow_no_request_to_request(self, mock_google_access_request):
        """Test full workflow from no request to having a request."""
        from connectors.google_connections import connect_google_account
        
        # Create wrapper
        wrapper = Mock(spec=RunContextWrapper)
        wrapper.context = Mock()
        wrapper.context.user = Mock()
        wrapper.context.user.reference_id = "workflow_user"
        wrapper.context.agent_name = "Google Connections"
        
        # First call - no existing request
        mock_google_access_request.get_request_for_user.return_value = None
        # Explicitly set ready_for_google to False to avoid Mock's hasattr behavior
        wrapper.context.user.ready_for_google = False
        first_result = await connect_google_account.on_invoke_tool(wrapper, {})
        
        assert first_result['response_type'] == 'request_google_access'
        
        # Simulate user creating a request and being ready
        mock_request = Mock()
        mock_google_access_request.get_request_for_user.return_value = mock_request
        wrapper.context.user.ready_for_google = True
        
        # Second call - request exists and user is ready
        second_result = await connect_google_account.on_invoke_tool(wrapper, {})
        
        assert second_result['response_type'] == 'connect_google_account'
        
        # Both calls should have checked for the same user
        calls = mock_google_access_request.get_request_for_user.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == "workflow_user"
        assert calls[1][0][0] == "workflow_user"

    def test_agent_handoff_compatibility(self):
        """Test that the agent is compatible with handoff scenarios."""
        from connectors.google_connections import GOOGLE_CONNECTIONS_AGENT
        from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
        
        # Instructions should include the recommended prefix
        assert GOOGLE_CONNECTIONS_AGENT.instructions.startswith(RECOMMENDED_PROMPT_PREFIX)
        
        # Instructions should mention handoff behavior
        assert "HANDED OFF TO" in GOOGLE_CONNECTIONS_AGENT.instructions

    @pytest.mark.asyncio
    async def test_error_handling_preparation(self):
        """Test preparation for error handling scenarios."""
        from connectors.google_connections import connect_google_account
        
        # The function handles None wrapper by returning an error response
        # The FunctionTool decorator catches the AttributeError and returns error message
        result = await connect_google_account.on_invoke_tool(None, {})
        # FunctionTool returns an error message string when there's an error
        assert isinstance(result, str)
        assert "error occurred" in result.lower()
        assert "NoneType" in result
        
        # The function should handle missing context attributes
        wrapper = Mock(spec=RunContextWrapper)
        wrapper.context = None
        
        result = await connect_google_account.on_invoke_tool(wrapper, {})
        # FunctionTool returns an error message string when there's an error
        assert isinstance(result, str)
        assert "error occurred" in result.lower()