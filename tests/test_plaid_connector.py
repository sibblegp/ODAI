"""Tests for the Plaid connector module."""

import pytest
import asyncio
from unittest.mock import Mock, patch

from agents import RunContextWrapper
from connectors.plaid_connector import PLAID_CONNECTOR_AGENT
from connectors.utils.context import ChatContext
from connectors.utils.responses import ConnectPlaidAccountResponse


class TestConnectPlaidAccountFunction:
    """Test the connect_plaid_account function."""

    @pytest.mark.asyncio
    async def test_connect_plaid_account_returns_correct_response(self):
        """Test that connect_plaid_account returns a ConnectPlaidAccountResponse."""
        # Create mock wrapper
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_context = Mock(spec=ChatContext)
        mock_wrapper.context = mock_context

        # Get the tool and call it
        tool = PLAID_CONNECTOR_AGENT.tools[0]
        result = await tool.on_invoke_tool(mock_wrapper, '{}')

        # Assert the response structure
        assert isinstance(result, dict)
        assert result['response_type'] == 'connect_plaid_account'
        assert result['agent_name'] == 'Plaid Connector'
        assert result['friendly_name'] == 'Connect Plaid Account'
        assert result['response'] == "Please press the button above to connect your bank or credit card account"
        assert result['display_response'] is True

    @pytest.mark.asyncio
    async def test_connect_plaid_account_with_different_contexts(self):
        """Test connect_plaid_account with various context configurations."""
        # Test with production context
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_context = Mock(spec=ChatContext)
        mock_context.production = True
        mock_wrapper.context = mock_context

        # Get the tool and call its function
        tool = PLAID_CONNECTOR_AGENT.tools[0]
        result = await tool.on_invoke_tool(mock_wrapper, '{}')
        assert result['response_type'] == 'connect_plaid_account'

        # Test with development context
        mock_context.production = False
        # Get the tool and call its function
        tool = PLAID_CONNECTOR_AGENT.tools[0]
        result = await tool.on_invoke_tool(mock_wrapper, '{}')
        assert result['response_type'] == 'connect_plaid_account'

    @pytest.mark.asyncio
    async def test_connect_plaid_account_response_serialization(self):
        """Test that the response can be properly serialized."""
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_context = Mock(spec=ChatContext)
        mock_wrapper.context = mock_context

        # Get the tool and call its function
        tool = PLAID_CONNECTOR_AGENT.tools[0]
        result = await tool.on_invoke_tool(mock_wrapper, '{}')
        
        # Should be JSON serializable
        import json
        json_str = json.dumps(result)
        parsed = json.loads(json_str)
        
        assert parsed['response_type'] == 'connect_plaid_account'
        assert parsed['agent_name'] == 'Plaid Connector'


class TestPlaidConnectorAgent:
    """Test the PLAID_CONNECTOR_AGENT configuration."""

    def test_agent_name(self):
        """Test that the agent has the correct name."""
        assert PLAID_CONNECTOR_AGENT.name == "Plaid Connector"

    def test_agent_instructions(self):
        """Test that the agent has appropriate instructions."""
        assert "plaid" in PLAID_CONNECTOR_AGENT.instructions.lower() or "bank" in PLAID_CONNECTOR_AGENT.instructions.lower()
        assert "connect_plaid_account" in PLAID_CONNECTOR_AGENT.instructions
        assert "bank or credit card accounts" in PLAID_CONNECTOR_AGENT.instructions
        assert "Don't say click here" in PLAID_CONNECTOR_AGENT.instructions

    def test_agent_tools(self):
        """Test that the agent has the correct tools."""
        assert len(PLAID_CONNECTOR_AGENT.tools) == 1
        tool = PLAID_CONNECTOR_AGENT.tools[0]
        assert tool.name == 'connect_plaid_account'

    def test_agent_has_function_tool(self):
        """Test that the connect_plaid_account is properly configured as a function tool."""
        tool = PLAID_CONNECTOR_AGENT.tools[0]
        assert hasattr(tool, 'name')
        assert tool.name == 'connect_plaid_account'

    def test_agent_no_handoffs(self):
        """Test that the agent has no handoffs."""
        assert not hasattr(PLAID_CONNECTOR_AGENT, 'handoffs') or len(PLAID_CONNECTOR_AGENT.handoffs) == 0


class TestPlaidConnectorIntegration:
    """Integration tests for the Plaid connector."""

    def test_connect_plaid_account_response_structure(self):
        """Test the complete response structure from ConnectPlaidAccountResponse."""
        response = ConnectPlaidAccountResponse('Test Agent')
        response_dict = response.to_dict()

        assert response_dict['response_type'] == 'connect_plaid_account'
        assert response_dict['agent_name'] == 'Test Agent'
        assert response_dict['friendly_name'] == 'Connect Plaid Account'
        assert response_dict['response'] == "Please press the button above to connect your bank or credit card account"
        assert response_dict['display_response'] is True

    @pytest.mark.asyncio
    async def test_agent_tool_execution_flow(self):
        """Test that the agent's tool can be executed properly."""
        # Get the connect_plaid_account tool from the agent
        tool = PLAID_CONNECTOR_AGENT.tools[0]
        
        # Create mock wrapper
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_context = Mock(spec=ChatContext)
        mock_wrapper.context = mock_context

        # Execute the tool's function
        result = await tool.on_invoke_tool(mock_wrapper, '{}')
        
        # Verify the result
        assert result['response_type'] == 'connect_plaid_account'
        assert result['agent_name'] == 'Plaid Connector'

    @pytest.mark.asyncio
    async def test_connect_plaid_account_uses_response_class(self):
        """Test that connect_plaid_account properly uses ConnectPlaidAccountResponse."""
        # Create mock wrapper
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_context = Mock(spec=ChatContext)
        mock_wrapper.context = mock_context

        # Get the tool and call its function
        tool = PLAID_CONNECTOR_AGENT.tools[0]
        result = await tool.on_invoke_tool(mock_wrapper, '{}')

        # Verify the result comes from ConnectPlaidAccountResponse
        assert result['response_type'] == 'connect_plaid_account'
        assert result['agent_name'] == 'Plaid Connector'


class TestPlaidConnectorEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_connect_plaid_account_with_none_context(self):
        """Test behavior when context is None."""
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = None

        # Should still return valid response
        # Get the tool and call its function
        tool = PLAID_CONNECTOR_AGENT.tools[0]
        result = await tool.on_invoke_tool(mock_wrapper, '{}')
        assert result['response_type'] == 'connect_plaid_account'

    def test_agent_instructions_format(self):
        """Test that agent instructions follow expected format."""
        instructions = PLAID_CONNECTOR_AGENT.instructions
        
        # Should contain key components
        assert "System context" in instructions or "helpful" in instructions
        
        # Should contain specific Plaid instructions
        assert "ALWAYS CALL THE connect_plaid_account TOOL" in instructions

    def test_function_tool_description(self):
        """Test that the function tool has proper description."""
        tool = PLAID_CONNECTOR_AGENT.tools[0]
        assert tool.description is not None
        assert "Agent Instruction:" in tool.description
        assert "Response Types to Expect:" in tool.description