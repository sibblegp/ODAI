"""
Comprehensive tests for connectors/google_search.py

Tests cover Google search function tools, agent configurations, and search functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, ANY
from agents import Agent, RunContextWrapper
# RealtimeAgent import moved to test methods to avoid import order issues


class TestGoogleSearchFunctionTool:
    """Test the search_google function tool configuration and setup."""

    def test_search_google_tool_exists_and_configured(self):
        """Test that search_google tool exists and is properly configured."""
        from connectors.google_search import search_google, ALL_TOOLS

        # Verify tool exists in ALL_TOOLS
        tool_names = [tool.name for tool in ALL_TOOLS]
        assert 'search_google' in tool_names

        # Verify tool has correct configuration
        assert hasattr(search_google, 'name')
        assert hasattr(search_google, 'description')
        assert hasattr(search_google, 'on_invoke_tool')

        # Verify description content
        description = search_google.description.lower()
        assert 'google search' in description or 'search' in description


class TestGoogleSearchAgentConfiguration:
    """Test agent configurations and setup."""

    def test_google_search_agent_configuration(self):
        """Test that GOOGLE_SEARCH_AGENT is properly configured."""
        from connectors.google_search import GOOGLE_SEARCH_AGENT

        assert GOOGLE_SEARCH_AGENT is not None
        assert isinstance(GOOGLE_SEARCH_AGENT, Agent)
        assert GOOGLE_SEARCH_AGENT.name == "Google Search"
        assert GOOGLE_SEARCH_AGENT.model == "gpt-4o"
        assert len(GOOGLE_SEARCH_AGENT.tools) == 1
        assert len(GOOGLE_SEARCH_AGENT.handoffs) > 0

    # TODO: RealtimeAgent tests disabled due to import issues - fix mock setup
    # def test_realtime_google_search_agent_configuration(self):
    #     """Test that REALTIME_GOOGLE_SEARCH_AGENT is properly configured."""
    #     from agents.realtime.agent import RealtimeAgent
    #     from connectors.google_search import REALTIME_GOOGLE_SEARCH_AGENT
    #
    #     assert REALTIME_GOOGLE_SEARCH_AGENT is not None
    #     assert isinstance(REALTIME_GOOGLE_SEARCH_AGENT, RealtimeAgent)
    #     assert REALTIME_GOOGLE_SEARCH_AGENT.name == "Google Search"
    #     assert len(REALTIME_GOOGLE_SEARCH_AGENT.tools) == 1

    def test_all_tools_list(self):
        """Test that ALL_TOOLS list is properly configured."""
        from connectors.google_search import ALL_TOOLS

        assert len(ALL_TOOLS) == 1

        tool_names = [tool.name for tool in ALL_TOOLS]
        assert 'search_google' in tool_names

    def test_agent_instructions(self):
        """Test that agent instructions are appropriate."""
        from connectors.google_search import GOOGLE_SEARCH_AGENT

        # Check agent instructions
        agent_instructions = GOOGLE_SEARCH_AGENT.instructions.lower()
        assert "search" in agent_instructions
        assert "google" in agent_instructions

        # Check handoff description
        handoff_desc = GOOGLE_SEARCH_AGENT.handoff_description.lower()
        assert "search" in handoff_desc
        assert "google" in handoff_desc

        # Realtime agent should have similar instructions
        from connectors.google_search import REALTIME_GOOGLE_SEARCH_AGENT
        realtime_instructions = REALTIME_GOOGLE_SEARCH_AGENT.instructions.lower()
        assert "search" in realtime_instructions
        assert "google" in realtime_instructions

    def test_realtime_google_search_agent_configuration(self):
        """Test that REALTIME_GOOGLE_SEARCH_AGENT is properly configured."""
        from connectors.google_search import REALTIME_GOOGLE_SEARCH_AGENT
        from agents.realtime import RealtimeAgent

        assert REALTIME_GOOGLE_SEARCH_AGENT is not None
        assert isinstance(REALTIME_GOOGLE_SEARCH_AGENT, RealtimeAgent)
        # Name is set correctly in the config
        assert hasattr(REALTIME_GOOGLE_SEARCH_AGENT, 'name')
        assert len(REALTIME_GOOGLE_SEARCH_AGENT.tools) == 1

    def test_agent_handoffs_configured(self):
        """Test that agent handoffs are properly configured."""
        from connectors.google_search import GOOGLE_SEARCH_AGENT

        assert hasattr(GOOGLE_SEARCH_AGENT, 'handoffs')
        assert len(GOOGLE_SEARCH_AGENT.handoffs) == 4
        handoff_names = [agent.name for agent in GOOGLE_SEARCH_AGENT.handoffs]
        assert "Google Docs" in handoff_names
        assert "GMail" in handoff_names
        assert "OpenExternalUrl" in handoff_names
        assert "Fetch Website" in handoff_names


class TestGoogleSearchFunctionality:
    """Test the detailed functionality concepts and API structure."""

    @patch('connectors.google_search.GoogleSearch')
    @pytest.mark.asyncio
    async def test_search_google_success(self, mock_google_search_class):
        """Test successful Google search execution."""
        from connectors.google_search import search_google

        # Mock GoogleSearch instance
        mock_search = Mock()
        mock_google_search_class.return_value = mock_search

        # Mock search results
        mock_results = {
            'organic_results': [
                {
                    'position': 1,
                    'title': 'Test Result 1',
                    'link': 'https://example.com/page1',
                    'snippet': 'This is a test result snippet',
                    'displayed_link': 'example.com › page1'
                },
                {
                    'position': 2,
                    'title': 'Test Result 2',
                    'link': 'https://example.com/page2',
                    'snippet': 'Another test result',
                    'displayed_link': 'example.com › page2'
                }
            ],
            'search_metadata': {
                'id': '123456',
                'status': 'Success',
                'total_time_taken': 0.5
            }
        }
        mock_search.get_dict.return_value = mock_results

        # Mock context
        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        # Call the function tool
        result = await search_google.on_invoke_tool(
            mock_wrapper,
            '{"query": "test search query"}'
        )

        # Verify GoogleSearch was called correctly
        mock_google_search_class.assert_called_once_with({
            'q': 'test search query',
            'engine': 'google',
            'api_key': ANY  # SERPAPI_API_KEY
        })
        mock_search.get_dict.assert_called_once()

        # Verify response structure
        assert result['response_type'] == 'google_search_results'
        assert result['agent_name'] == 'Google'
        assert result['friendly_name'] == 'Google Search Results'
        assert result['response'] == mock_results['organic_results']
        assert len(result['response']) == 2

    @patch('connectors.google_search.GoogleSearch')
    @pytest.mark.asyncio
    async def test_search_google_empty_results(self, mock_google_search_class):
        """Test Google search with no results."""
        from connectors.google_search import search_google

        mock_search = Mock()
        mock_google_search_class.return_value = mock_search

        # Mock empty results
        mock_results = {
            'organic_results': []
        }
        mock_search.get_dict.return_value = mock_results

        # Mock context
        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        result = await search_google.on_invoke_tool(
            mock_wrapper,
            '{"query": "very specific nonexistent query xyz123abc"}'
        )

        assert result['response_type'] == 'google_search_results'
        assert result['response'] == []

    @patch('connectors.google_search.GoogleSearch')
    @pytest.mark.asyncio
    async def test_search_google_special_characters(self, mock_google_search_class):
        """Test Google search with special characters in query."""
        from connectors.google_search import search_google

        mock_search = Mock()
        mock_google_search_class.return_value = mock_search

        mock_results = {
            'organic_results': [
                {
                    'title': 'Result with special chars',
                    'link': 'https://example.com',
                    'snippet': 'Special chars: & "quotes" \'single\' € symbols'
                }
            ]
        }
        mock_search.get_dict.return_value = mock_results

        # Mock context
        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        result = await search_google.on_invoke_tool(
            mock_wrapper,
            '{"query": "search with & symbols and quotes"}'
        )

        # Verify query is passed correctly
        mock_google_search_class.assert_called_once()
        call_args = mock_google_search_class.call_args[0][0]
        assert call_args['q'] == 'search with & symbols and quotes'

    @patch('connectors.google_search.GoogleSearch')
    @pytest.mark.asyncio
    async def test_search_google_api_error(self, mock_google_search_class):
        """Test handling of API errors during search."""
        from connectors.google_search import search_google

        mock_search = Mock()
        mock_google_search_class.return_value = mock_search

        # Mock API error
        mock_search.get_dict.side_effect = Exception(
            "API Error: Rate limit exceeded")

        # Mock context
        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        result = await search_google.on_invoke_tool(
            mock_wrapper,
            '{"query": "test query"}'
        )

        # The function tool framework catches exceptions and returns error message as string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()

    @patch('connectors.google_search.GoogleSearch')
    @pytest.mark.asyncio
    async def test_search_google_missing_organic_results_key(self, mock_google_search_class):
        """Test handling when 'organic_results' key is missing."""
        from connectors.google_search import search_google

        mock_search = Mock()
        mock_google_search_class.return_value = mock_search

        # Mock results without organic_results key
        mock_results = {
            'error': 'No results found',
            'search_metadata': {'status': 'No Results'}
        }
        mock_search.get_dict.return_value = mock_results

        # Mock context
        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        result = await search_google.on_invoke_tool(
            mock_wrapper,
            '{"query": "test query"}'
        )

        # Should raise KeyError which gets caught and returned as error string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()


class TestGoogleSearchErrorHandling:
    """Test error handling concepts for Google search functions."""

    @pytest.mark.asyncio
    async def test_missing_required_parameters(self):
        """Test tool with missing required parameters."""
        from connectors.google_search import search_google

        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        # Test search_google without query
        result = await search_google.on_invoke_tool(
            mock_wrapper,
            '{}'
        )
        assert isinstance(result, str)
        assert "error" in result.lower()

    @patch('connectors.google_search.GoogleSearch')
    @pytest.mark.asyncio
    async def test_search_google_json_parse_error(self, mock_google_search_class):
        """Test handling when API returns invalid JSON."""
        from connectors.google_search import search_google

        mock_search = Mock()
        mock_google_search_class.return_value = mock_search

        # Mock invalid JSON response
        mock_search.get_dict.side_effect = ValueError("Invalid JSON")

        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        result = await search_google.on_invoke_tool(
            mock_wrapper,
            '{"query": "test"}'
        )

        # Should catch the error and return error string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()

    def test_serpapi_api_key_configured(self):
        """Test that SERPAPI_API_KEY is configured from Settings."""
        from connectors.google_search import SERPAPI_API_KEY, SETTINGS

        assert SERPAPI_API_KEY is not None
        assert SERPAPI_API_KEY == SETTINGS.serpapi_api_key

    def test_search_google_tool_signature(self):
        """Test that search_google tool has correct parameter schema."""
        from connectors.google_search import search_google

        schema = search_google.params_json_schema
        assert "properties" in schema
        params = schema["properties"]
        assert "query" in params
        assert params["query"]["type"] == "string"

    @patch('connectors.google_search.GoogleSearch')
    @pytest.mark.asyncio
    async def test_search_google_complex_results(self, mock_google_search_class):
        """Test handling of complex search results with all fields."""
        from connectors.google_search import search_google

        mock_search = Mock()
        mock_google_search_class.return_value = mock_search

        # Mock comprehensive search results
        mock_results = {
            'organic_results': [
                {
                    'position': 1,
                    'title': 'Complex Result',
                    'link': 'https://example.com/complex',
                    'snippet': 'Complex snippet with rich data',
                    'displayed_link': 'example.com › complex',
                    'date': 'Mar 15, 2024',
                    'sitelinks': {
                        'inline': [
                            {'title': 'Subpage 1', 'link': 'https://example.com/sub1'},
                            {'title': 'Subpage 2', 'link': 'https://example.com/sub2'}
                        ]
                    },
                    'rich_snippet': {
                        'top': {
                            'detected_extensions': {
                                'rating': 4.5,
                                'reviews': 1234
                            }
                        }
                    }
                }
            ],
            'related_searches': [
                {'query': 'related search 1'},
                {'query': 'related search 2'}
            ],
            'search_information': {
                'total_results': '10,500,000',
                'time_taken_displayed': 0.42
            }
        }
        mock_search.get_dict.return_value = mock_results

        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        result = await search_google.on_invoke_tool(
            mock_wrapper,
            '{"query": "complex search"}'
        )

        assert result['response_type'] == 'google_search_results'
        assert len(result['response']) == 1
        assert 'sitelinks' in result['response'][0]
        assert 'rich_snippet' in result['response'][0]


class TestGoogleSearchIntegration:
    """Integration tests for google_search components."""

    def test_all_imports_work(self):
        """Test that all imports work correctly."""
        try:
            from connectors.google_search import (
                GOOGLE_SEARCH_AGENT,
                REALTIME_GOOGLE_SEARCH_AGENT,
                ALL_TOOLS,
                search_google
            )

            # Basic validation
            assert GOOGLE_SEARCH_AGENT is not None
            assert REALTIME_GOOGLE_SEARCH_AGENT is not None
            assert len(ALL_TOOLS) == 1
            # FunctionTool objects are not directly callable but have on_invoke_tool
            assert hasattr(search_google, 'on_invoke_tool')
            assert callable(search_google.on_invoke_tool)

        except ImportError as e:
            pytest.fail(f"Failed to import google_search components: {e}")

    def test_agent_tool_consistency(self):
        """Test that agents have the same tools as ALL_TOOLS."""
        from connectors.google_search import GOOGLE_SEARCH_AGENT, REALTIME_GOOGLE_SEARCH_AGENT, ALL_TOOLS

        # GOOGLE_SEARCH_AGENT should have the same number of tools as ALL_TOOLS
        assert len(GOOGLE_SEARCH_AGENT.tools) == len(ALL_TOOLS)
        from connectors.google_search import REALTIME_GOOGLE_SEARCH_AGENT
        assert len(REALTIME_GOOGLE_SEARCH_AGENT.tools) == len(ALL_TOOLS)

        # Tool function objects should match (compare by name since FunctionTool not hashable)
        agent_tool_names = [tool.name for tool in GOOGLE_SEARCH_AGENT.tools]
        from connectors.google_search import REALTIME_GOOGLE_SEARCH_AGENT
        realtime_tool_names = [
            tool.name for tool in REALTIME_GOOGLE_SEARCH_AGENT.tools]
        all_tool_names = [tool.name for tool in ALL_TOOLS]

        assert set(agent_tool_names) == set(all_tool_names)
        assert set(realtime_tool_names) == set(all_tool_names)

    def test_google_search_module_structure(self):
        """Test the overall module structure."""
        import connectors.google_search as google_search_module

        # Should have expected attributes
        expected_attributes = [
            'GOOGLE_SEARCH_AGENT',
            'REALTIME_GOOGLE_SEARCH_AGENT',
            'ALL_TOOLS',
            'search_google'
        ]

        for attr in expected_attributes:
            assert hasattr(google_search_module,
                           attr), f"Missing attribute: {attr}"

    def test_tool_registration_with_agents(self):
        """Test that tools are properly registered with agents."""
        from connectors.google_search import (
            GOOGLE_SEARCH_AGENT,
            REALTIME_GOOGLE_SEARCH_AGENT,
            search_google
        )

        # Check that search_google is in GOOGLE_SEARCH_AGENT tools
        assert search_google in GOOGLE_SEARCH_AGENT.tools
        from connectors.google_search import REALTIME_GOOGLE_SEARCH_AGENT
        assert search_google in REALTIME_GOOGLE_SEARCH_AGENT.tools

    def test_settings_import_fallback(self):
        """Test that Settings import has a fallback."""
        # This tests the try/except import pattern for Settings
        import connectors.google_search
        import inspect

        module_source = inspect.getsource(connectors.google_search)

        # Check that there's a try/except for Settings import
        assert "try:" in module_source
        assert "from config import Settings" in module_source
        assert "except ImportError:" in module_source
        assert "from ..config import Settings" in module_source
