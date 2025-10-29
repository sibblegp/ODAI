"""
Comprehensive tests for connectors/yelp.py

Tests cover the Yelp agent, its tools, and various edge cases.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from agents import Agent
from connectors.yelp import (
    YELP_AGENT,
    YELP_REALTIME_AGENT,
    search_businesses_at_yelp,
    get_business_reviews_at_yelp,
    ALL_TOOLS
)


class TestYelpConfig:
    """Test Yelp agent configuration and setup."""

    def test_yelp_agent_exists(self):
        """Test that YELP_AGENT is properly configured."""
        assert YELP_AGENT is not None
        assert isinstance(YELP_AGENT, Agent)
        assert YELP_AGENT.name == "Yelp"
        assert YELP_AGENT.model == "gpt-4o"
        assert len(YELP_AGENT.tools) == 2

    def test_yelp_realtime_agent_exists(self):
        """Test that YELP_REALTIME_AGENT is properly configured."""
        assert YELP_REALTIME_AGENT is not None
        assert YELP_REALTIME_AGENT.name == "Yelp"
        assert len(YELP_REALTIME_AGENT.tools) == 2

    def test_all_tools_exported(self):
        """Test that ALL_TOOLS contains expected tools."""
        assert len(ALL_TOOLS) == 2
        assert search_businesses_at_yelp in ALL_TOOLS
        assert get_business_reviews_at_yelp in ALL_TOOLS

    def test_agent_handoffs_configured(self):
        """Test that agent handoffs are properly configured."""
        assert hasattr(YELP_AGENT, 'handoffs')
        assert len(YELP_AGENT.handoffs) == 2  # GOOGLE_DOCS_AGENT, GMAIL_AGENT

    def test_agent_instructions_configured(self):
        """Test that agent instructions are properly set."""
        assert YELP_AGENT.instructions is not None
        assert "Search Yelp for businesses" in YELP_AGENT.instructions
        assert "retrieve reviews" in YELP_AGENT.instructions


class TestSearchBusinessesTool:
    """Test the search_businesses_at_yelp tool."""

    @patch('connectors.yelp.requests.get')
    @pytest.mark.asyncio
    async def test_search_businesses_success(self, mock_get):
        """Test successful business search."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "businesses": [
                {
                    "id": "test-business-1",
                    "name": "Test Restaurant",
                    "rating": 4.5,
                    "review_count": 100,
                    "location": {"address1": "123 Main St"},
                    "coordinates": {"latitude": 42.3601, "longitude": -71.0589},
                    "price": "$$",
                    "phone": "+1234567890",
                    "url": "https://yelp.com/biz/test-restaurant"
                }
            ]
        }
        mock_get.return_value = mock_response

        # Mock the tool context
        mock_ctx = Mock()

        result = await search_businesses_at_yelp.on_invoke_tool(
            mock_ctx,
            '{"location": "Boston, MA", "search_term": "sushi", "sort_by_rating": true, "limit": 5}'
        )

        # Verify API call was made correctly
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert "https://api.yelp.com/v3/businesses/search" in args[0]
        assert "Authorization" in kwargs["headers"]
        assert kwargs["params"]["location"] == "Boston, MA"
        assert kwargs["params"]["term"] == "sushi"
        assert kwargs["params"]["limit"] == 5
        assert kwargs["params"]["sort_by"] == "rating"

        # Verify response structure
        assert result["response_type"] == "yelp_search_results"
        assert result["agent_name"] == "Yelp"
        assert result["display_response"] is True
        assert len(result["response"]) == 1
        assert result["response"][0]["name"] == "Test Restaurant"

    @patch('connectors.yelp.requests.get')
    @pytest.mark.asyncio
    async def test_search_businesses_default_limit(self, mock_get):
        """Test search with default limit when None provided."""
        mock_response = Mock()
        mock_response.json.return_value = {"businesses": []}
        mock_get.return_value = mock_response

        # Mock the tool context
        mock_ctx = Mock()

        await search_businesses_at_yelp.on_invoke_tool(
            mock_ctx,
            '{"location": "Boston, MA", "search_term": "pizza", "sort_by_rating": false, "limit": null}'
        )

        # Verify default limit of 10 is used
        args, kwargs = mock_get.call_args
        assert kwargs["params"]["limit"] == 10

    @patch('connectors.yelp.requests.get')
    @pytest.mark.asyncio
    async def test_search_businesses_sort_by_best_match(self, mock_get):
        """Test search sorted by best match."""
        mock_response = Mock()
        mock_response.json.return_value = {"businesses": []}
        mock_get.return_value = mock_response

        # Mock the tool context
        mock_ctx = Mock()

        await search_businesses_at_yelp.on_invoke_tool(
            mock_ctx,
            '{"location": "Boston, MA", "search_term": "coffee", "sort_by_rating": false, "limit": 5}'
        )

        # Verify sort_by is set to best_match
        args, kwargs = mock_get.call_args
        assert kwargs["params"]["sort_by"] == "best_match"

    @patch('connectors.yelp.requests.get')
    @pytest.mark.asyncio
    async def test_search_businesses_api_error(self, mock_get):
        """Test handling of API errors."""
        mock_get.side_effect = Exception("API Error")

        # Mock the tool context
        mock_ctx = Mock()

        result = await search_businesses_at_yelp.on_invoke_tool(
            mock_ctx,
            '{"location": "Boston, MA", "search_term": "sushi", "sort_by_rating": true, "limit": 5}'
        )

        # The function tool framework catches exceptions and returns error message as string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()

    @patch('connectors.yelp.requests.get')
    @pytest.mark.asyncio
    async def test_search_businesses_empty_response(self, mock_get):
        """Test handling of empty business results."""
        mock_response = Mock()
        mock_response.json.return_value = {"businesses": []}
        mock_get.return_value = mock_response

        # Mock the tool context
        mock_ctx = Mock()

        result = await search_businesses_at_yelp.on_invoke_tool(
            mock_ctx,
            '{"location": "Boston, MA", "search_term": "nonexistent", "sort_by_rating": true, "limit": 5}'
        )

        assert result["response"] == []
        assert result["response_type"] == "yelp_search_results"


class TestGetBusinessReviewsTool:
    """Test the get_business_reviews_at_yelp tool."""

    @patch('connectors.yelp.requests.get')
    @pytest.mark.asyncio
    async def test_get_business_reviews_success(self, mock_get):
        """Test successful review retrieval."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "reviews": [
                {
                    "rating": 5,
                    "text": "Amazing food and service!",
                    "time_created": "2023-01-01T12:00:00Z",
                    "user": {
                        "name": "John Doe",
                        "profile_url": "https://yelp.com/user/johndoe"
                    }
                },
                {
                    "rating": 4,
                    "text": "Good food, but a bit pricey.",
                    "time_created": "2023-01-02T15:30:00Z",
                    "user": {
                        "name": "Jane Smith",
                        "profile_url": "https://yelp.com/user/janesmith"
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        # Mock the tool context
        mock_ctx = Mock()

        result = await get_business_reviews_at_yelp.on_invoke_tool(
            mock_ctx,
            '{"business_id": "test-business-id"}'
        )

        # Verify API call was made correctly
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert "https://api.yelp.com/v3/businesses/test-business-id/reviews" in args[0]
        assert "sort_by=yelp_sort" in args[0]
        assert "Authorization" in kwargs["headers"]

        # Verify response structure
        assert result["response_type"] == "yelp_reviews"
        assert result["agent_name"] == "Yelp"
        assert result["display_response"] is True
        assert len(result["response"]) == 2
        assert result["response"][0]["rating"] == 5
        assert result["response"][1]["rating"] == 4

    @patch('connectors.yelp.requests.get')
    @pytest.mark.asyncio
    async def test_get_business_reviews_api_error(self, mock_get):
        """Test handling of API errors when getting reviews."""
        mock_get.side_effect = Exception("API Error")

        # Mock the tool context
        mock_ctx = Mock()

        result = await get_business_reviews_at_yelp.on_invoke_tool(
            mock_ctx,
            '{"business_id": "test-business-id"}'
        )

        # The function tool framework catches exceptions and returns error message as string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()

    @patch('connectors.yelp.requests.get')
    @pytest.mark.asyncio
    async def test_get_business_reviews_empty_response(self, mock_get):
        """Test handling of empty review results."""
        mock_response = Mock()
        mock_response.json.return_value = {"reviews": []}
        mock_get.return_value = mock_response

        # Mock the tool context
        mock_ctx = Mock()

        result = await get_business_reviews_at_yelp.on_invoke_tool(
            mock_ctx,
            '{"business_id": "no-reviews-business"}'
        )

        assert result["response"] == []
        assert result["response_type"] == "yelp_reviews"


class TestYelpAgentIntegration:
    """Integration tests for Yelp agent components."""

    def test_agent_tools_registration(self):
        """Test that tools are properly registered with the agent."""
        tool_names = [tool.name for tool in YELP_AGENT.tools]
        assert "search_businesses_at_yelp" in tool_names
        assert "get_business_reviews_at_yelp" in tool_names

    def test_agent_model_configuration(self):
        """Test that agent uses correct model."""
        assert YELP_AGENT.model == "gpt-4o"

    def test_realtime_agent_tools_registration(self):
        """Test that realtime agent has same tools as regular agent."""
        regular_tool_names = [tool.name for tool in YELP_AGENT.tools]
        realtime_tool_names = [tool.name for tool in YELP_REALTIME_AGENT.tools]
        assert set(regular_tool_names) == set(realtime_tool_names)

    def test_import_dependencies(self):
        """Test that agent dependencies are properly imported."""
        # This test ensures the import structure works
        try:
            from connectors.yelp import (
                YELP_AGENT,
                search_businesses_at_yelp,
                get_business_reviews_at_yelp
            )
            assert YELP_AGENT is not None
            assert search_businesses_at_yelp is not None
            assert get_business_reviews_at_yelp is not None
        except ImportError as e:
            pytest.fail(f"Failed to import Yelp components: {e}")


class TestYelpEdgeCases:
    """Test edge cases and error conditions."""

    @patch('connectors.yelp.requests.get')
    @pytest.mark.asyncio
    async def test_search_with_special_characters(self, mock_get):
        """Test search with special characters in location and search term."""
        mock_response = Mock()
        mock_response.json.return_value = {"businesses": []}
        mock_get.return_value = mock_response

        # Mock the tool context
        mock_ctx = Mock()

        await search_businesses_at_yelp.on_invoke_tool(
            mock_ctx,
            '{"location": "San José, CA", "search_term": "café & bakery", "sort_by_rating": true, "limit": 5}'
        )

        # Verify the API call was made (requests should handle URL encoding)
        mock_get.assert_called_once()

    @patch('connectors.yelp.requests.get')
    @pytest.mark.asyncio
    async def test_reviews_with_invalid_business_id(self, mock_get):
        """Test reviews retrieval with invalid business ID."""
        mock_response = Mock()
        mock_response.json.return_value = {"reviews": []}
        mock_get.return_value = mock_response

        # Mock the tool context
        mock_ctx = Mock()

        result = await get_business_reviews_at_yelp.on_invoke_tool(
            mock_ctx,
            '{"business_id": ""}'
        )

        # Should still make API call and return empty results
        assert result["response"] == []

    def test_tool_function_signatures(self):
        """Test that tool functions have correct parameter schemas."""
        # Test search_businesses_at_yelp parameters
        search_schema = search_businesses_at_yelp.params_json_schema
        assert "properties" in search_schema
        params = search_schema["properties"]
        assert "location" in params
        assert "search_term" in params
        assert "sort_by_rating" in params
        assert "limit" in params

        # Test get_business_reviews_at_yelp parameters
        reviews_schema = get_business_reviews_at_yelp.params_json_schema
        assert "properties" in reviews_schema
        params = reviews_schema["properties"]
        assert "business_id" in params

    @pytest.mark.asyncio
    async def test_tool_response_format_consistency(self):
        """Test that both tools return consistent ToolResponse format."""
        with patch('connectors.yelp.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"businesses": [], "reviews": []}
            mock_get.return_value = mock_response

            # Mock the tool context
            mock_ctx = Mock()

            # Test search tool response format
            search_result = await search_businesses_at_yelp.on_invoke_tool(
                mock_ctx,
                '{"location": "Boston", "search_term": "sushi", "sort_by_rating": true, "limit": 5}'
            )
            required_fields = ["response_type", "agent_name",
                               "friendly_name", "display_response", "response"]
            for field in required_fields:
                assert field in search_result

            # Test reviews tool response format
            reviews_result = await get_business_reviews_at_yelp.on_invoke_tool(
                mock_ctx,
                '{"business_id": "test-id"}'
            )
            for field in required_fields:
                assert field in reviews_result
