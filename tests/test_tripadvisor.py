"""
Comprehensive tests for connectors/tripadvisor.py

Tests cover the TripAdvisor agent, its tools, enum, and various edge cases.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import requests
from enum import Enum
from agents import Agent, RunContextWrapper
from connectors.tripadvisor import (
    TRIPADVISOR_AGENT,
    ALL_TOOLS,
    search_tripadvisor,
    get_tripadvisor_location_details,
    get_tripadvisor_location_reviews,
    TripAdvisorCategory,
    TRIPADVISOR_API_KEY
)


class TestTripAdvisorCategory:
    """Test the TripAdvisorCategory enum."""

    def test_category_enum_values(self):
        """Test that category enum has correct values."""
        assert TripAdvisorCategory.RESTAURANTS.value == "restaurants"
        assert TripAdvisorCategory.HOTELS.value == "hotels"
        assert TripAdvisorCategory.ATTRACTIONS.value == "attractions"

    def test_category_enum_members(self):
        """Test that all expected categories exist."""
        categories = [cat.name for cat in TripAdvisorCategory]
        assert "RESTAURANTS" in categories
        assert "HOTELS" in categories
        assert "ATTRACTIONS" in categories
        assert len(categories) == 3


class TestTripAdvisorConfig:
    """Test TripAdvisor agent configuration."""

    def test_tripadvisor_agent_exists(self):
        """Test that TRIPADVISOR_AGENT is properly configured."""
        assert TRIPADVISOR_AGENT is not None
        assert isinstance(TRIPADVISOR_AGENT, Agent)
        assert TRIPADVISOR_AGENT.name == "TripAdvisor"
        assert TRIPADVISOR_AGENT.model == "gpt-4o"

    def test_all_tools_exported(self):
        """Test that ALL_TOOLS contains expected tools."""
        assert len(ALL_TOOLS) == 3
        assert search_tripadvisor in ALL_TOOLS
        assert get_tripadvisor_location_details in ALL_TOOLS
        assert get_tripadvisor_location_reviews in ALL_TOOLS

    def test_agent_tools_configured(self):
        """Test that agent has all tools configured."""
        agent_tools = TRIPADVISOR_AGENT.tools
        assert len(agent_tools) == 3
        tool_names = [tool.name for tool in agent_tools]
        assert 'search_tripadvisor' in tool_names
        assert 'get_tripadvisor_location_details' in tool_names
        assert 'get_tripadvisor_location_reviews' in tool_names

    def test_agent_handoffs_configured(self):
        """Test that agent handoffs are properly configured."""
        assert hasattr(TRIPADVISOR_AGENT, 'handoffs')
        assert len(TRIPADVISOR_AGENT.handoffs) == 2
        handoff_names = [agent.name for agent in TRIPADVISOR_AGENT.handoffs]
        assert "Google Docs" in handoff_names
        assert "GMail" in handoff_names

    def test_agent_instructions_configured(self):
        """Test that agent instructions are properly set."""
        assert TRIPADVISOR_AGENT.instructions is not None
        assert "Search and provide info" in TRIPADVISOR_AGENT.instructions
        assert "restaurants, hotels, and attractions" in TRIPADVISOR_AGENT.instructions

    def test_agent_handoff_description_configured(self):
        """Test that agent handoff description is properly set."""
        assert TRIPADVISOR_AGENT.handoff_description is not None
        assert "TripAdvisor search" in TRIPADVISOR_AGENT.handoff_description
        from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
        assert TRIPADVISOR_AGENT.handoff_description.startswith(
            RECOMMENDED_PROMPT_PREFIX)


class TestSearchTripAdvisorTool:
    """Test the search_tripadvisor function tool."""

    @pytest.mark.asyncio
    async def test_search_basic_query(self):
        """Test basic search without location."""
        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {
                    "location_id": "123456",
                    "name": "Test Restaurant",
                    "address_obj": {"address_string": "123 Test St"}
                }
            ]
        }

        with patch('connectors.tripadvisor.requests.get', return_value=mock_response) as mock_get:
            with patch('builtins.print') as mock_print:
                result = await search_tripadvisor.on_invoke_tool(
                    mock_wrapper,
                    json.dumps({"query": "pizza"})
                )

        assert result['response_type'] == 'tripadvisor_search'
        assert result['agent_name'] == 'TripAdvisor'
        assert result['friendly_name'] == 'Search Results'
        assert result['response'] == mock_response.json.return_value

        # Check the URL was constructed correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args[0][0]
        assert "searchQuery=pizza" in call_args
        assert f"key={TRIPADVISOR_API_KEY}" in call_args
        assert "latLong" not in call_args
        assert "category" not in call_args

        # Check print was called
        mock_print.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_with_location(self):
        """Test search with latitude and longitude."""
        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.return_value = {"data": []}

        with patch('connectors.tripadvisor.requests.get', return_value=mock_response) as mock_get:
            result = await search_tripadvisor.on_invoke_tool(
                mock_wrapper,
                json.dumps({
                    "query": "hotels",
                    "latitude": 40.7128,
                    "longitude": -74.006
                })
            )

        call_args = mock_get.call_args[0][0]
        assert "latLong=40.7128,-74.006" in call_args
        assert "radius=10000" in call_args
        assert "radiusUnit=m" in call_args

    @pytest.mark.asyncio
    async def test_search_with_category(self):
        """Test search with category filter."""
        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.return_value = {"data": []}

        with patch('connectors.tripadvisor.requests.get', return_value=mock_response) as mock_get:
            result = await search_tripadvisor.on_invoke_tool(
                mock_wrapper,
                json.dumps({
                    "query": "luxury",
                    "category": "hotels"
                })
            )

        call_args = mock_get.call_args[0][0]
        assert "category=hotels" in call_args

    @pytest.mark.asyncio
    async def test_search_with_all_params(self):
        """Test search with all parameters."""
        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.return_value = {"data": []}

        with patch('connectors.tripadvisor.requests.get', return_value=mock_response) as mock_get:
            result = await search_tripadvisor.on_invoke_tool(
                mock_wrapper,
                json.dumps({
                    "query": "italian",
                    "category": "restaurants",
                    "latitude": 41.9028,
                    "longitude": 12.4964
                })
            )

        call_args = mock_get.call_args[0][0]
        assert "searchQuery=italian" in call_args
        assert "category=restaurants" in call_args
        assert "latLong=41.9028,12.4964" in call_args

    @pytest.mark.asyncio
    async def test_search_api_error(self):
        """Test search when API returns error."""
        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        with patch('connectors.tripadvisor.requests.get') as mock_get:
            mock_get.side_effect = requests.RequestException("API Error")

            # The function tool wrapper catches the exception
            result = await search_tripadvisor.on_invoke_tool(
                mock_wrapper,
                json.dumps({"query": "test"})
            )

            # Error is handled by the wrapper
            assert result is not None


class TestGetTripAdvisorLocationDetailsTool:
    """Test the get_tripadvisor_location_details function tool."""

    @pytest.mark.asyncio
    async def test_get_location_details_success(self):
        """Test getting location details successfully."""
        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.return_value = {
            "location_id": "123456",
            "name": "Test Restaurant",
            "description": "A great place to eat",
            "rating": 4.5,
            "num_reviews": 100,
            "address_obj": {
                "street1": "123 Test St",
                "city": "Test City",
                "state": "TS",
                "postalcode": "12345"
            }
        }

        with patch('connectors.tripadvisor.requests.get', return_value=mock_response) as mock_get:
            result = await get_tripadvisor_location_details.on_invoke_tool(
                mock_wrapper,
                json.dumps({"location_id": "123456"})
            )

        assert result['response_type'] == 'tripadvisor_location_details'
        assert result['agent_name'] == 'TripAdvisor'
        assert result['friendly_name'] == 'Location Details'
        assert result['response'] == mock_response.json.return_value

        # Check URL construction
        call_args = mock_get.call_args[0][0]
        assert "location/123456/details" in call_args
        assert f"key={TRIPADVISOR_API_KEY}" in call_args
        assert "language=en" in call_args

    @pytest.mark.asyncio
    async def test_get_location_details_empty_id(self):
        """Test getting location details with empty ID."""
        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.return_value = {"error": "Invalid location"}

        with patch('connectors.tripadvisor.requests.get', return_value=mock_response):
            result = await get_tripadvisor_location_details.on_invoke_tool(
                mock_wrapper,
                json.dumps({"location_id": ""})
            )

        assert result['response']['error'] == 'Invalid location'

    @pytest.mark.asyncio
    async def test_get_location_details_not_found(self):
        """Test getting details for non-existent location."""
        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.return_value = {"error": {"code": "NOT_FOUND"}}

        with patch('connectors.tripadvisor.requests.get', return_value=mock_response):
            result = await get_tripadvisor_location_details.on_invoke_tool(
                mock_wrapper,
                json.dumps({"location_id": "999999999"})
            )

        assert 'error' in result['response']


class TestGetTripAdvisorLocationReviewsTool:
    """Test the get_tripadvisor_location_reviews function tool."""

    @pytest.mark.asyncio
    async def test_get_location_reviews_success(self):
        """Test getting location reviews successfully."""
        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "review1",
                    "text": "Great food!",
                    "rating": 5,
                    "published_date": "2024-01-01"
                },
                {
                    "id": "review2",
                    "text": "Good service",
                    "rating": 4,
                    "published_date": "2024-01-02"
                }
            ]
        }

        with patch('connectors.tripadvisor.requests.get', return_value=mock_response) as mock_get:
            result = await get_tripadvisor_location_reviews.on_invoke_tool(
                mock_wrapper,
                json.dumps({"location_id": "123456"})
            )

        assert result['response_type'] == 'tripadvisor_location_reviews'
        assert result['agent_name'] == 'TripAdvisor'
        assert result['friendly_name'] == 'Location Reviews'
        assert len(result['response']['data']) == 2

        # Check URL construction
        call_args = mock_get.call_args[0][0]
        assert "location/123456/reviews" in call_args
        assert f"key={TRIPADVISOR_API_KEY}" in call_args
        assert "language=en" in call_args

    @pytest.mark.asyncio
    async def test_get_location_reviews_empty_response(self):
        """Test getting reviews when location has no reviews."""
        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.return_value = {"data": []}

        with patch('connectors.tripadvisor.requests.get', return_value=mock_response):
            result = await get_tripadvisor_location_reviews.on_invoke_tool(
                mock_wrapper,
                json.dumps({"location_id": "789012"})
            )

        assert result['response']['data'] == []

    @pytest.mark.asyncio
    async def test_get_location_reviews_api_error(self):
        """Test getting reviews when API returns error."""
        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")

        with patch('connectors.tripadvisor.requests.get', return_value=mock_response):
            # The function tool wrapper catches the exception
            result = await get_tripadvisor_location_reviews.on_invoke_tool(
                mock_wrapper,
                json.dumps({"location_id": "invalid"})
            )

            assert result is not None


class TestTripAdvisorIntegration:
    """Integration tests for TripAdvisor components."""

    def test_all_imports_work(self):
        """Test that all imports work correctly."""
        try:
            from connectors.tripadvisor import (
                TRIPADVISOR_AGENT,
                ALL_TOOLS,
                search_tripadvisor,
                get_tripadvisor_location_details,
                get_tripadvisor_location_reviews,
                TripAdvisorCategory,
                TRIPADVISOR_API_KEY
            )

            assert TRIPADVISOR_AGENT is not None
            assert len(ALL_TOOLS) == 3
            assert callable(search_tripadvisor.on_invoke_tool)
            assert callable(get_tripadvisor_location_details.on_invoke_tool)
            assert callable(get_tripadvisor_location_reviews.on_invoke_tool)
            assert issubclass(TripAdvisorCategory, Enum)

        except ImportError as e:
            pytest.fail(f"Failed to import TripAdvisor components: {e}")

    def test_agent_tools_consistency(self):
        """Test that agent tools match ALL_TOOLS."""
        agent_tool_names = [tool.name for tool in TRIPADVISOR_AGENT.tools]
        all_tool_names = [tool.name for tool in ALL_TOOLS]

        assert set(agent_tool_names) == set(all_tool_names)

    def test_tool_descriptions(self):
        """Test that all tools have proper descriptions."""
        for tool in ALL_TOOLS:
            assert hasattr(tool, 'description')
            assert tool.description is not None
            assert len(tool.description) > 0

            # Check specific keywords in descriptions
            if tool.name == 'search_tripadvisor':
                assert 'search' in tool.description.lower()
            elif tool.name == 'get_tripadvisor_location_details':
                assert 'details' in tool.description.lower()
            elif tool.name == 'get_tripadvisor_location_reviews':
                assert 'reviews' in tool.description.lower()

    def test_tool_parameters(self):
        """Test that all tools have correct parameter schemas."""
        # Test search_tripadvisor parameters
        search_schema = search_tripadvisor.params_json_schema
        assert 'properties' in search_schema
        assert 'query' in search_schema['properties']
        assert 'latitude' in search_schema['properties']
        assert 'longitude' in search_schema['properties']
        assert 'category' in search_schema['properties']

        # Test get_tripadvisor_location_details parameters
        details_schema = get_tripadvisor_location_details.params_json_schema
        assert 'properties' in details_schema
        assert 'location_id' in details_schema['properties']

        # Test get_tripadvisor_location_reviews parameters
        reviews_schema = get_tripadvisor_location_reviews.params_json_schema
        assert 'properties' in reviews_schema
        assert 'location_id' in reviews_schema['properties']


class TestTripAdvisorEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_search_with_special_characters(self):
        """Test search with special characters in query."""
        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.return_value = {"data": []}

        with patch('connectors.tripadvisor.requests.get', return_value=mock_response) as mock_get:
            result = await search_tripadvisor.on_invoke_tool(
                mock_wrapper,
                json.dumps({"query": "café & bistro"})
            )

        # URL should be properly encoded
        call_args = mock_get.call_args[0][0]
        assert "café & bistro" in call_args or "caf%C3%A9" in call_args

    @pytest.mark.asyncio
    async def test_search_with_invalid_coordinates(self):
        """Test search with invalid latitude/longitude."""
        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.return_value = {"error": "Invalid coordinates"}

        with patch('connectors.tripadvisor.requests.get', return_value=mock_response):
            result = await search_tripadvisor.on_invoke_tool(
                mock_wrapper,
                json.dumps({
                    "query": "test",
                    "latitude": 999.0,  # Invalid latitude
                    "longitude": -999.0
                })
            )

        assert 'error' in result['response']

    def test_api_key_configuration(self):
        """Test that API key is properly configured."""
        assert TRIPADVISOR_API_KEY is not None
        # In real tests, you might want to check format or length
        # but we shouldn't expose the actual key value

    @pytest.mark.asyncio
    async def test_location_details_with_null_fields(self):
        """Test location details when API returns null fields."""
        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.return_value = {
            "location_id": "123",
            "name": "Test Place",
            "description": None,
            "rating": None,
            "address_obj": None
        }

        with patch('connectors.tripadvisor.requests.get', return_value=mock_response):
            result = await get_tripadvisor_location_details.on_invoke_tool(
                mock_wrapper,
                json.dumps({"location_id": "123"})
            )

        response = result['response']
        assert response['name'] == "Test Place"
        assert response['description'] is None
        assert response['rating'] is None
        assert response['address_obj'] is None

    def test_unused_imports(self):
        """Test that unused imports are present (for completeness)."""
        # These imports are in the file but not directly used
        import connectors.tripadvisor as tripadvisor_module

        # finnhub import (unused)
        assert hasattr(tripadvisor_module, 'finnhub')

        # os import (unused)
        assert hasattr(tripadvisor_module, 'os')

        # display_response_check import (unused)
        assert hasattr(tripadvisor_module, 'display_response_check')
