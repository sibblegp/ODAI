"""
Comprehensive tests for connectors/google_news.py

Tests cover the Google News agent, its tools, and various edge cases.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from agents import Agent
from connectors.google_news import (
    GOOGLE_NEWS_AGENT,
    get_google_news_top_stories,
    search_google_news,
    ALL_TOOLS
)


class TestGoogleNewsConfig:
    """Test Google News agent configuration and setup."""

    def test_google_news_agent_exists(self):
        """Test that GOOGLE_NEWS_AGENT is properly configured."""
        assert GOOGLE_NEWS_AGENT is not None
        assert isinstance(GOOGLE_NEWS_AGENT, Agent)
        assert GOOGLE_NEWS_AGENT.name == "Google News"
        assert GOOGLE_NEWS_AGENT.model == "gpt-4o"
        assert len(GOOGLE_NEWS_AGENT.tools) == 2

    def test_all_tools_exported(self):
        """Test that ALL_TOOLS contains expected tools."""
        assert len(ALL_TOOLS) == 2
        assert get_google_news_top_stories in ALL_TOOLS
        assert search_google_news in ALL_TOOLS

    def test_agent_handoffs_configured(self):
        """Test that agent handoffs are properly configured."""
        assert hasattr(GOOGLE_NEWS_AGENT, 'handoffs')
        # GOOGLE_DOCS, OPEN_EXTERNAL_URL, FETCH_WEBSITE, GMAIL
        assert len(GOOGLE_NEWS_AGENT.handoffs) == 4

    def test_agent_instructions_configured(self):
        """Test that agent instructions are properly set."""
        assert GOOGLE_NEWS_AGENT.instructions is not None
        assert "Google News" in GOOGLE_NEWS_AGENT.instructions
        assert "news" in GOOGLE_NEWS_AGENT.instructions.lower()
        assert "headlines" in GOOGLE_NEWS_AGENT.instructions.lower(
        ) or "stories" in GOOGLE_NEWS_AGENT.instructions.lower()

    def test_agent_handoff_description_configured(self):
        """Test that agent handoff description is properly set."""
        assert GOOGLE_NEWS_AGENT.handoff_description is not None
        assert "Google News" in GOOGLE_NEWS_AGENT.handoff_description
        assert "news" in GOOGLE_NEWS_AGENT.handoff_description.lower()


class TestGetGoogleNewsTopStoriesTools:
    """Test the get_google_news_top_stories tool."""

    @patch('connectors.google_news.GoogleSearch')
    @pytest.mark.asyncio
    async def test_get_top_stories_success(self, mock_search_class):
        """Test successful retrieval of top news stories."""
        # Mock SerpAPI response
        mock_search = Mock()
        mock_search_class.return_value = mock_search
        mock_search.get_dict.return_value = {
            'news_results': [
                {
                    'title': 'Breaking News: Major Event Occurs',
                    'link': 'https://example.com/news1',
                    'source': 'News Source 1',
                    'date': '1 hour ago',
                    'snippet': 'A major event has occurred today...'
                },
                {
                    'title': 'Tech Company Announces New Product',
                    'link': 'https://example.com/news2',
                    'source': 'Tech News Daily',
                    'date': '3 hours ago',
                    'snippet': 'The company revealed their latest innovation...'
                }
            ]
        }

        # Mock the tool context
        mock_ctx = Mock()

        result = await get_google_news_top_stories.on_invoke_tool(
            mock_ctx,
            '{}'
        )

        # Verify SerpAPI was called with correct params
        mock_search_class.assert_called_once()
        call_args = mock_search_class.call_args[0][0]
        assert call_args['engine'] == 'google_news'
        assert 'api_key' in call_args

        # Verify response structure
        assert result['response_type'] == 'google_news_top_stories'
        assert result['agent_name'] == 'Google'
        assert result['friendly_name'] == 'Google News Top Stories'
        assert result['display_response'] is False
        assert len(result['response']) == 2
        assert result['response'][0]['title'] == 'Breaking News: Major Event Occurs'

    @patch('connectors.google_news.GoogleSearch')
    @pytest.mark.asyncio
    async def test_get_top_stories_empty_results(self, mock_search_class):
        """Test handling when no top stories are found."""
        mock_search = Mock()
        mock_search_class.return_value = mock_search
        mock_search.get_dict.return_value = {
            'news_results': []
        }

        mock_ctx = Mock()
        result = await get_google_news_top_stories.on_invoke_tool(
            mock_ctx,
            '{}'
        )

        assert result['response'] == []

    @patch('connectors.google_news.GoogleSearch')
    @pytest.mark.asyncio
    async def test_get_top_stories_api_error(self, mock_search_class):
        """Test handling of SerpAPI errors."""
        mock_search = Mock()
        mock_search_class.return_value = mock_search
        mock_search.get_dict.side_effect = Exception("SerpAPI Error")

        mock_ctx = Mock()
        result = await get_google_news_top_stories.on_invoke_tool(
            mock_ctx,
            '{}'
        )

        # The function tool framework catches exceptions and returns error message as string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()


class TestSearchGoogleNewsTool:
    """Test the search_google_news tool."""

    @patch('connectors.google_news.GoogleSearch')
    @pytest.mark.asyncio
    async def test_search_news_success(self, mock_search_class):
        """Test successful news search."""
        # Mock SerpAPI response
        mock_search = Mock()
        mock_search_class.return_value = mock_search
        mock_search.get_dict.return_value = {
            'news_results': [
                {
                    'title': 'AI Breakthrough Announced',
                    'link': 'https://example.com/ai-news',
                    'source': 'AI Weekly',
                    'date': '2 hours ago',
                    'snippet': 'Researchers have developed a new AI system...'
                },
                {
                    'title': 'Machine Learning in Healthcare',
                    'link': 'https://example.com/ml-health',
                    'source': 'Health Tech News',
                    'date': '5 hours ago',
                    'snippet': 'New ML applications in medical diagnosis...'
                }
            ]
        }

        mock_ctx = Mock()
        result = await search_google_news.on_invoke_tool(
            mock_ctx,
            '{"query": "artificial intelligence"}'
        )

        # Verify SerpAPI was called with correct params
        mock_search_class.assert_called_once()
        call_args = mock_search_class.call_args[0][0]
        assert call_args['q'] == 'artificial intelligence'
        assert call_args['engine'] == 'google_news'
        assert 'api_key' in call_args

        # Verify response structure
        assert result['response_type'] == 'google_news_search_results'
        assert result['agent_name'] == 'Google'
        assert result['friendly_name'] == 'Google News Search Results'
        assert result['display_response'] is False
        assert len(result['response']) == 2
        assert result['response'][0]['title'] == 'AI Breakthrough Announced'

    @patch('connectors.google_news.GoogleSearch')
    @pytest.mark.asyncio
    async def test_search_news_empty_query(self, mock_search_class):
        """Test searching with empty query."""
        mock_search = Mock()
        mock_search_class.return_value = mock_search
        mock_search.get_dict.return_value = {
            'news_results': []
        }

        mock_ctx = Mock()
        result = await search_google_news.on_invoke_tool(
            mock_ctx,
            '{"query": ""}'
        )

        # Empty query should still make API call
        mock_search_class.assert_called_once()
        call_args = mock_search_class.call_args[0][0]
        assert call_args['q'] == ''

    @patch('connectors.google_news.GoogleSearch')
    @pytest.mark.asyncio
    async def test_search_news_special_characters(self, mock_search_class):
        """Test searching with special characters in query."""
        mock_search = Mock()
        mock_search_class.return_value = mock_search
        mock_search.get_dict.return_value = {
            'news_results': [
                {
                    'title': 'COVID-19 Update',
                    'link': 'https://example.com/covid',
                    'source': 'Health News',
                    'date': '1 hour ago',
                    'snippet': 'Latest COVID-19 statistics...'
                }
            ]
        }

        mock_ctx = Mock()
        result = await search_google_news.on_invoke_tool(
            mock_ctx,
            '{"query": "COVID-19 & vaccines"}'
        )

        call_args = mock_search_class.call_args[0][0]
        assert call_args['q'] == 'COVID-19 & vaccines'

    @patch('connectors.google_news.GoogleSearch')
    @pytest.mark.asyncio
    async def test_search_news_no_results(self, mock_search_class):
        """Test handling when search returns no results."""
        mock_search = Mock()
        mock_search_class.return_value = mock_search
        mock_search.get_dict.return_value = {
            'news_results': []
        }

        mock_ctx = Mock()
        result = await search_google_news.on_invoke_tool(
            mock_ctx,
            '{"query": "extremely obscure topic xyz123"}'
        )

        assert result['response'] == []

    @patch('connectors.google_news.GoogleSearch')
    @pytest.mark.asyncio
    async def test_search_news_api_error(self, mock_search_class):
        """Test handling of SerpAPI errors during search."""
        mock_search = Mock()
        mock_search_class.return_value = mock_search
        mock_search.get_dict.side_effect = Exception("SerpAPI Error")

        mock_ctx = Mock()
        result = await search_google_news.on_invoke_tool(
            mock_ctx,
            '{"query": "test query"}'
        )

        assert isinstance(result, str)
        assert "error occurred" in result.lower()


class TestGoogleNewsAgentIntegration:
    """Integration tests for Google News agent components."""

    def test_agent_tools_registration(self):
        """Test that tools are properly registered with the agent."""
        tool_names = [tool.name for tool in GOOGLE_NEWS_AGENT.tools]
        assert "get_google_news_top_stories" in tool_names
        assert "search_google_news" in tool_names

    def test_agent_model_configuration(self):
        """Test that agent uses correct model."""
        assert GOOGLE_NEWS_AGENT.model == "gpt-4o"

    def test_agent_handoffs_registration(self):
        """Test that handoffs are properly registered."""
        handoff_names = [agent.name for agent in GOOGLE_NEWS_AGENT.handoffs]
        assert "Google Docs" in handoff_names
        assert "OpenExternalUrl" in handoff_names
        assert "Fetch Website" in handoff_names
        assert "GMail" in handoff_names

    def test_import_dependencies(self):
        """Test that agent dependencies are properly imported."""
        try:
            from connectors.google_news import (
                GOOGLE_NEWS_AGENT,
                get_google_news_top_stories,
                search_google_news
            )
            assert GOOGLE_NEWS_AGENT is not None
            assert get_google_news_top_stories is not None
            assert search_google_news is not None
        except ImportError as e:
            pytest.fail(f"Failed to import Google News components: {e}")


class TestGoogleNewsEdgeCases:
    """Test edge cases and error conditions."""

    def test_get_top_stories_tool_signature(self):
        """Test that get_google_news_top_stories tool has correct parameter schema."""
        schema = get_google_news_top_stories.params_json_schema
        assert "properties" in schema
        # This tool takes no parameters
        assert len(schema["properties"]) == 0

    def test_search_news_tool_signature(self):
        """Test that search_google_news tool has correct parameter schema."""
        schema = search_google_news.params_json_schema
        assert "properties" in schema
        params = schema["properties"]
        assert "query" in params
        assert params["query"]["type"] == "string"

    def test_agent_name_consistency(self):
        """Test that agent name is consistent."""
        assert GOOGLE_NEWS_AGENT.name == "Google News"

    def test_all_tools_contains_all_functions(self):
        """Test that ALL_TOOLS exports all available tool functions."""
        expected_tools = [get_google_news_top_stories, search_google_news]
        assert len(ALL_TOOLS) == len(expected_tools)
        for tool in expected_tools:
            assert tool in ALL_TOOLS

    def test_agent_instructions_mention_key_functionality(self):
        """Test that agent instructions mention key functionality."""
        instructions = GOOGLE_NEWS_AGENT.instructions
        assert "Google News" in instructions
        assert "headlines" in instructions.lower() or "stories" in instructions.lower()
        assert "search" in instructions.lower()

    @pytest.mark.asyncio
    async def test_search_missing_query_param(self):
        """Test search tool with missing query parameter."""
        mock_ctx = Mock()

        result = await search_google_news.on_invoke_tool(
            mock_ctx,
            '{}'  # Missing query parameter
        )

        assert isinstance(result, str)
        assert "error" in result.lower()

    @patch('connectors.google_news.GoogleSearch')
    @pytest.mark.asyncio
    async def test_malformed_api_response(self, mock_search_class):
        """Test handling of malformed API response."""
        mock_search = Mock()
        mock_search_class.return_value = mock_search
        # Return response without expected 'news_results' key
        mock_search.get_dict.return_value = {
            'error': 'API limit reached'
        }

        mock_ctx = Mock()
        result = await get_google_news_top_stories.on_invoke_tool(
            mock_ctx,
            '{}'
        )

        # Should raise KeyError which gets caught and returned as error string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()

    @patch('connectors.google_news.GoogleSearch')
    @pytest.mark.asyncio
    async def test_unicode_query_handling(self, mock_search_class):
        """Test handling of Unicode characters in search query."""
        mock_search = Mock()
        mock_search_class.return_value = mock_search
        mock_search.get_dict.return_value = {
            'news_results': [
                {
                    'title': 'Unicode News: 新闻',
                    'link': 'https://example.com/unicode',
                    'source': 'International News',
                    'date': 'Today',
                    'snippet': 'News in multiple languages...'
                }
            ]
        }

        mock_ctx = Mock()
        result = await search_google_news.on_invoke_tool(
            mock_ctx,
            '{"query": "新闻 émojis 🌍"}'
        )

        call_args = mock_search_class.call_args[0][0]
        assert call_args['q'] == '新闻 émojis 🌍'
        assert result['response'][0]['title'] == 'Unicode News: 新闻'
