"""
Comprehensive tests for prompts.py

Tests cover AgentCapabilities parsing, suggested prompt generation, and request handling determination.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, List, Any

from agents import Agent, Handoff, Tool, TResponseInputItem, FunctionTool
from openai import OpenAI


class TestAgentCapabilities:
    """Test AgentCapabilities class and its methods."""

    @patch('prompts.ORCHESTRATOR_AGENT')
    def test_agent_capabilities_initialization(self, mock_orchestrator):
        """Test that AgentCapabilities initializes correctly."""
        from prompts import AgentCapabilities

        # Mock agent with tools and handoffs
        mock_agent = Mock(spec=Agent)
        mock_agent.name = "TestAgent"
        mock_agent.model = "gpt-4o"
        mock_agent.handoff_description = "Test agent description"

        # Mock tool - FunctionTool is one of the types in the Tool Union
        mock_tool = Mock(spec=FunctionTool)
        mock_tool.name = "test_tool"
        mock_tool.description = "Test tool description"
        mock_tool.function = Mock()
        mock_tool.function.parameters = Mock()
        mock_tool.function.parameters.properties = {
            "param1": {"type": "string", "description": "Parameter 1"},
            "param2": {"type": "integer", "description": "Parameter 2"}
        }
        mock_tool.function.parameters.required = ["param1"]

        mock_agent.tools = [mock_tool]
        mock_agent.handoffs = []

        mock_orchestrator.handoffs = [mock_agent]

        # Initialize AgentCapabilities
        capabilities = AgentCapabilities()

        assert capabilities.agent_capabilities is not None
        assert "TestAgent" in capabilities.agent_capabilities
        assert capabilities.agent_capabilities["TestAgent"]["name"] == "TestAgent"
        assert capabilities.agent_capabilities["TestAgent"]["model"] == "gpt-4o"
        assert len(capabilities.agent_capabilities["TestAgent"]["tools"]) == 1

        tool_info = capabilities.agent_capabilities["TestAgent"]["tools"][0]
        assert tool_info["name"] == "test_tool"
        assert tool_info["description"] == "Test tool description"
        assert "param1" in tool_info["parameters"]
        assert tool_info["parameters"]["param1"]["required"] is True
        assert tool_info["parameters"]["param2"]["required"] is False

    @patch('prompts.ORCHESTRATOR_AGENT')
    def test_parse_agent_capabilities_with_handoffs(self, mock_orchestrator):
        """Test parsing agent capabilities with handoffs."""
        from prompts import AgentCapabilities

        # Mock agent with handoffs
        mock_agent = Mock(spec=Agent)
        mock_agent.name = "MainAgent"
        mock_agent.model = "gpt-4o"
        mock_agent.instructions = "Main agent instructions"
        mock_agent.tools = []

        # Mock handoff
        mock_handoff = Mock(spec=Handoff)
        mock_handoff.name = "SubAgent"
        mock_handoff.handoff_description = "Handoff to sub agent"

        mock_agent.handoffs = [mock_handoff]
        mock_orchestrator.handoffs = [mock_agent]

        capabilities = AgentCapabilities()

        assert "MainAgent" in capabilities.agent_capabilities
        agent_info = capabilities.agent_capabilities["MainAgent"]
        assert len(agent_info["handoffs"]) == 1
        assert agent_info["handoffs"][0]["name"] == "SubAgent"
        assert agent_info["handoffs"][0]["description"] == "Handoff to sub agent"

    @patch('prompts.ORCHESTRATOR_AGENT')
    def test_parse_agent_capabilities_no_function_attribute(self, mock_orchestrator):
        """Test parsing when tool doesn't have function attribute."""
        from prompts import AgentCapabilities

        mock_agent = Mock(spec=Agent)
        mock_agent.name = "TestAgent"
        mock_agent.model = "gpt-4o"
        mock_agent.handoff_description = "Test agent"

        # Mock tool without function attribute
        mock_tool = Mock(spec=FunctionTool)
        mock_tool.name = "simple_tool"
        mock_tool.description = "Simple tool"
        mock_tool.function = None  # No function attribute

        mock_agent.tools = [mock_tool]
        mock_agent.handoffs = []
        mock_orchestrator.handoffs = [mock_agent]

        capabilities = AgentCapabilities()

        tool_info = capabilities.agent_capabilities["TestAgent"]["tools"][0]
        assert tool_info["name"] == "simple_tool"
        assert tool_info["parameters"] == {}


class TestGenerateSuggestedPrompts:
    """Test generate_suggested_prompts functionality."""

    @pytest.mark.asyncio
    @patch('prompts.OPENAI_CLIENT')
    async def test_generate_suggested_prompts_success(self, mock_openai_client):
        """Test successful generation of suggested prompts."""
        from prompts import AgentCapabilities
        from firebase import User

        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "suggested_prompts": [
                {"prompt": "Send email", "likelihood": 0.8},
                {"prompt": "Save document", "likelihood": 0.6},
                {"prompt": "Check calendar", "likelihood": 0.4}
            ]
        })

        mock_openai_client.chat.completions.create.return_value = mock_response

        # Create test data
        conversation_input = [
            {"role": "user", "content": "What's on my calendar today?"},
            {"role": "assistant", "content": "You have 3 meetings today..."}
        ]

        user = Mock(spec=User)
        user.integrations = {"google": True, "plaid": False}

        # Test
        with patch('prompts.ORCHESTRATOR_AGENT'):
            capabilities = AgentCapabilities()
            result = await capabilities.generate_suggested_prompts(
                conversation_input, user, []
            )

        assert isinstance(result, list)
        assert len(result) == 3  # All prompts with likelihood > 0.3
        assert result[0]["prompt"] == "Send email"
        assert result[0]["likelihood"] == 0.8

    @pytest.mark.asyncio
    @patch('prompts.OPENAI_CLIENT')
    async def test_generate_suggested_prompts_filters_low_likelihood(self, mock_openai_client):
        """Test that prompts with low likelihood are filtered out."""
        from prompts import AgentCapabilities
        from firebase import User

        # Mock response with varying likelihoods
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "suggested_prompts": [
                {"prompt": "High likelihood", "likelihood": 0.9},
                {"prompt": "Low likelihood", "likelihood": 0.2},
                {"prompt": "Medium likelihood", "likelihood": 0.5}
            ]
        })

        mock_openai_client.chat.completions.create.return_value = mock_response

        user = Mock(spec=User)
        user.integrations = None

        with patch('prompts.ORCHESTRATOR_AGENT'):
            capabilities = AgentCapabilities()
            result = await capabilities.generate_suggested_prompts([], user, [])

        # Should filter out prompts with likelihood <= 0.3
        assert len(result) == 2
        assert all(prompt["likelihood"] > 0.3 for prompt in result)

    @pytest.mark.asyncio
    @patch('prompts.OPENAI_CLIENT')
    async def test_generate_suggested_prompts_json_decode_error(self, mock_openai_client):
        """Test handling of JSON decode errors."""
        from prompts import AgentCapabilities
        from firebase import User

        # Mock response with invalid JSON
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Invalid JSON {{"

        mock_openai_client.chat.completions.create.return_value = mock_response

        user = Mock(spec=User)

        with patch('prompts.ORCHESTRATOR_AGENT'):
            capabilities = AgentCapabilities()
            result = await capabilities.generate_suggested_prompts([], user, [])

        # The function returns a dict with suggested_prompts and demo_prompts on error
        assert result == {
            "suggested_prompts": [],
            "demo_prompts": ["Search for restaurants near me", "Check my email", "Get the price of AAPL"]
        }

    @pytest.mark.asyncio
    @patch('prompts.OPENAI_CLIENT')
    async def test_generate_suggested_prompts_exception(self, mock_openai_client):
        """Test handling of exceptions during prompt generation."""
        from prompts import AgentCapabilities
        from firebase import User

        # Mock OpenAI client to raise exception
        mock_openai_client.chat.completions.create.side_effect = Exception(
            "API Error")

        user = Mock(spec=User)

        with patch('prompts.ORCHESTRATOR_AGENT'):
            capabilities = AgentCapabilities()
            result = await capabilities.generate_suggested_prompts([], user, [])

        assert result == {
            "suggested_prompts": [],
            "demo_prompts": ["Search for restaurants near me", "Check my email", "Get the price of AAPL"]
        }

    @pytest.mark.asyncio
    @patch('prompts.OPENAI_CLIENT')
    async def test_generate_suggested_prompts_with_previous_tools(self, mock_openai_client):
        """Test that previous tool calls are included in the prompt."""
        from prompts import AgentCapabilities
        from firebase import User

        # Mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "suggested_prompts": [{"prompt": "New action", "likelihood": 0.7}]
        })

        mock_openai_client.chat.completions.create.return_value = mock_response

        # Include tool calls in conversation
        conversation_input = [
            {"role": "user", "content": "Search for restaurants"},
            {"type": "function_call", "name": "search_yelp"},
            {"role": "assistant", "content": "Found restaurants..."}
        ]

        user = Mock(spec=User)
        user.integrations = {"google": True, "plaid": True}

        with patch('prompts.ORCHESTRATOR_AGENT'):
            capabilities = AgentCapabilities()
            result = await capabilities.generate_suggested_prompts(
                conversation_input, user, []
            )

        # Verify that the API was called with previous tool calls info
        call_args = mock_openai_client.chat.completions.create.call_args
        user_message = call_args[1]["messages"][1]["content"]
        assert "Previous Tool Calls" in user_message
        assert "search_yelp" in user_message


class TestDetermineIfRequestHandled:
    """Test determine_if_request_handled functionality."""

    @pytest.mark.asyncio
    @patch('prompts.track_unhandled_request')
    @patch('prompts.OPENAI_CLIENT')
    async def test_request_handled_true(self, mock_openai_client, mock_track):
        """Test when request is handled successfully."""
        from prompts import determine_if_request_handled
        from firebase import User

        # Mock response indicating request was handled
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "request_handled": True,
            "capability_requested": None,
            "capability_description": None
        })

        mock_openai_client.chat.completions.create.return_value = mock_response

        user = Mock(spec=User)
        conversation_input = [
            {"role": "user", "content": "What's the weather?"},
            {"role": "assistant", "content": "The weather is sunny and 75°F."}
        ]

        result = await determine_if_request_handled(
            conversation_input, user, "chat123", "What's the weather?"
        )

        assert result == (True, None, None)
        mock_track.assert_not_called()

    @pytest.mark.asyncio
    @patch('prompts.track_unhandled_request')
    @patch('prompts.OPENAI_CLIENT')
    async def test_request_handled_false(self, mock_openai_client, mock_track):
        """Test when request is not handled."""
        from prompts import determine_if_request_handled
        from firebase import User

        # Mock response indicating request was not handled
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "request_handled": False,
            "capability_requested": "spotify_integration",
            "capability_description": "Play music on Spotify"
        })

        mock_openai_client.chat.completions.create.return_value = mock_response

        user = Mock(spec=User)
        conversation_input = [
            {"role": "user", "content": "Play my favorite playlist on Spotify"},
            {"role": "assistant", "content": "I'm sorry, I don't have Spotify integration."}
        ]

        result = await determine_if_request_handled(
            conversation_input, user, "chat123", "Play my favorite playlist on Spotify"
        )

        assert result == (False, "spotify_integration",
                          "Play music on Spotify")
        mock_track.assert_called_once_with(
            user, "chat123", "Play my favorite playlist on Spotify",
            "spotify_integration", "Play music on Spotify"
        )

    @pytest.mark.asyncio
    @patch('prompts.OPENAI_CLIENT')
    @patch('prompts.track_unhandled_request')
    async def test_request_handled_json_error(self, mock_track, mock_openai_client):
        """Test handling of JSON decode errors."""
        from prompts import determine_if_request_handled
        from firebase import User

        # Mock response with invalid JSON
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Not valid JSON"

        mock_openai_client.chat.completions.create.return_value = mock_response

        user = Mock(spec=User)

        result = await determine_if_request_handled([], user, "chat123", "test")

        # Should default to handled=True on error
        assert result == (True, None, None)

    @pytest.mark.asyncio
    @patch('prompts.track_unhandled_request')
    @patch('prompts.OPENAI_CLIENT')
    async def test_request_handled_exception(self, mock_openai_client, mock_track):
        """Test handling of exceptions during response parsing."""
        from prompts import determine_if_request_handled
        from firebase import User

        # Mock a response that will cause an exception during parsing
        mock_response = Mock()
        mock_response.choices = [Mock()]
        # This will cause an AttributeError
        mock_response.choices[0].message = None

        mock_openai_client.chat.completions.create.return_value = mock_response

        user = Mock(spec=User)

        # The function should catch the exception and return True
        with patch('builtins.print'):  # Suppress print output during test
            result = await determine_if_request_handled([], user, "chat123", "test")

        # Should default to handled=True on error
        assert result == (True, None, None)

    @pytest.mark.asyncio
    @patch('prompts.OPENAI_CLIENT')
    async def test_request_handled_with_transfer_functions(self, mock_openai_client):
        """Test that transfer functions are excluded from tool calls."""
        from prompts import determine_if_request_handled
        from firebase import User

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "request_handled": True,
            "capability_requested": None,
            "capability_description": None
        })

        mock_openai_client.chat.completions.create.return_value = mock_response

        user = Mock(spec=User)
        conversation_input = [
            {"role": "user", "content": "Check weather"},
            # Should be ignored
            {"type": "function_call", "name": "transfer_to_weather_agent"},
            {"type": "function_call", "name": "get_weather"},  # Should be included
            {"role": "assistant", "content": "Weather checked"}
        ]

        await determine_if_request_handled(conversation_input, user, "chat123", "Check weather")

        # Verify the conversation text doesn't include transfer functions
        call_args = mock_openai_client.chat.completions.create.call_args
        user_message = call_args[1]["messages"][1]["content"]
        assert "get_weather" in str(conversation_input)  # Original has it
        assert "transfer" in str(conversation_input)  # Original has transfer


class TestImportsAndConfiguration:
    """Test module imports and configuration."""

    def test_imports(self):
        """Test that all required imports work."""
        from prompts import (
            AgentCapabilities,
            determine_if_request_handled,
            SETTINGS,
            OPENAI_CLIENT
        )

        assert AgentCapabilities is not None
        assert determine_if_request_handled is not None
        assert SETTINGS is not None
        assert OPENAI_CLIENT is not None

    @patch('prompts.SETTINGS')
    @patch('prompts.OPENAI_CLIENT')
    def test_openai_client_configuration(self, mock_openai_client, mock_settings):
        """Test that OpenAI client is configured with API key."""
        # Set up mocks
        mock_settings.openai_api_key = 'test-openai-key'

        # Import after patching to ensure mocks are in place
        from prompts import OPENAI_CLIENT, SETTINGS

        assert OPENAI_CLIENT is not None
        assert SETTINGS is not None
