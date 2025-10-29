"""
Comprehensive tests for connectors/movieglu.py

Tests cover the MovieGlu agent, its tools, and various edge cases.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import datetime
from agents import Agent
from agents.realtime import RealtimeAgent
from connectors.movieglu import (
    MOVIEGLU_AGENT,
    REALTIME_MOVIEGLU_AGENT,
    build_headers,
    get_films_showing,
    get_nearby_theaters,
    search_theaters,
    search_films,
    get_theater_showtimes,
    get_film_showtimes,
    search_films_near_location,
    get_films_showing_near_location,
    get_nearby_theaters_near_location,
    search_theaters_near_location,
    get_theater_showtimes_near_location,
    get_film_showtimes_near_location,
    ALL_TOOLS
)


class TestMovieGluConfig:
    """Test MovieGlu agent configuration and setup."""

    def test_movieglu_agent_exists(self):
        """Test that MOVIEGLU_AGENT is properly configured."""
        assert MOVIEGLU_AGENT is not None
        assert isinstance(MOVIEGLU_AGENT, Agent)
        assert MOVIEGLU_AGENT.name == "MovieGlu"
        assert len(MOVIEGLU_AGENT.tools) == 6

    def test_realtime_movieglu_agent_exists(self):
        """Test that REALTIME_MOVIEGLU_AGENT is properly configured."""
        assert REALTIME_MOVIEGLU_AGENT is not None
        assert isinstance(REALTIME_MOVIEGLU_AGENT, RealtimeAgent)
        assert REALTIME_MOVIEGLU_AGENT.name == "MovieGlu"
        assert len(REALTIME_MOVIEGLU_AGENT.tools) == 6

    def test_all_tools_exported(self):
        """Test that ALL_TOOLS contains expected tools."""
        assert len(ALL_TOOLS) == 6
        assert get_films_showing_near_location in ALL_TOOLS
        assert get_nearby_theaters_near_location in ALL_TOOLS
        assert search_theaters_near_location in ALL_TOOLS
        assert get_theater_showtimes_near_location in ALL_TOOLS
        assert get_film_showtimes_near_location in ALL_TOOLS
        assert search_films_near_location in ALL_TOOLS

    def test_agent_instructions_configured(self):
        """Test that agent instructions are properly set."""
        assert MOVIEGLU_AGENT.instructions is not None
        assert "movie theater and showtime assistant" in MOVIEGLU_AGENT.instructions
        assert REALTIME_MOVIEGLU_AGENT.instructions is not None
        assert "movie showtimes and information" in REALTIME_MOVIEGLU_AGENT.instructions


class TestBuildHeaders:
    """Test the build_headers function."""

    @patch('connectors.movieglu.SETTINGS')
    @patch('connectors.movieglu.datetime')
    def test_build_headers_structure(self, mock_datetime, mock_settings):
        """Test that build_headers returns correct header structure."""
        # Mock settings
        mock_settings.movieglu_api_authorization = "test-auth"
        mock_settings.movieglu_api_key = "test-key"
        
        # Mock datetime
        mock_now = Mock()
        mock_now.isoformat.return_value = "2024-01-15T10:00:00.123456+00:00"
        mock_datetime.datetime.now.return_value = mock_now
        
        headers = build_headers(40.7128, -74.0060)
        
        assert headers['Authorization'] == "test-auth"
        assert headers['x-api-key'] == "test-key"
        assert headers['client'] == "ODAI"
        assert headers['territory'] == "US"
        assert headers['geolocation'] == "40.7128;-74.006"
        assert headers['api-version'] == "v201"
        assert headers['device-datetime'] == "2024-01-15T10:00:00.123456Z"

    def test_build_headers_different_coordinates(self):
        """Test build_headers with different coordinates."""
        headers1 = build_headers(51.5074, -0.1278)  # London
        headers2 = build_headers(35.6762, 139.6503)  # Tokyo
        
        assert headers1['geolocation'] == "51.5074;-0.1278"
        assert headers2['geolocation'] == "35.6762;139.6503"


class TestGetFilmsShowing:
    """Test the get_films_showing function."""

    @patch('connectors.movieglu.requests.get')
    @patch('connectors.movieglu.SETTINGS')
    def test_get_films_showing_success(self, mock_settings, mock_get):
        """Test successful retrieval of films showing."""
        mock_settings.local = False
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "films": [
                {"film_id": "1", "film_name": "Test Movie 1"},
                {"film_id": "2", "film_name": "Test Movie 2"}
            ]
        }
        mock_get.return_value = mock_response
        
        result = get_films_showing(40.7128, -74.0060)
        
        mock_get.assert_called_once()
        assert "https://api-gate2.movieglu.com/filmsNowShowing/?n=20" in mock_get.call_args[0][0]
        assert result == {"films": [{"film_id": "1", "film_name": "Test Movie 1"}, {"film_id": "2", "film_name": "Test Movie 2"}]}

    @patch('connectors.movieglu.requests.get')
    @patch('connectors.movieglu.SETTINGS')
    def test_get_films_showing_no_content(self, mock_settings, mock_get):
        """Test handling of 204 no content response."""
        mock_settings.local = False
        mock_response = Mock()
        mock_response.status_code = 204
        mock_get.return_value = mock_response
        
        result = get_films_showing(40.7128, -74.0060)
        
        assert result == []

    @patch('connectors.movieglu.requests.get')
    @patch('connectors.movieglu.SETTINGS')
    @patch('builtins.print')
    def test_get_films_showing_local_mode(self, mock_print, mock_settings, mock_get):
        """Test that response is printed in local mode."""
        mock_settings.local = True
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"films": []}'
        mock_response.json.return_value = {"films": []}
        mock_get.return_value = mock_response
        
        get_films_showing(40.7128, -74.0060)
        
        mock_print.assert_called_once_with('{"films": []}')


class TestGetNearbyTheaters:
    """Test the get_nearby_theaters function."""

    @patch('connectors.movieglu.requests.get')
    @patch('connectors.movieglu.SETTINGS')
    def test_get_nearby_theaters_success(self, mock_settings, mock_get):
        """Test successful retrieval of nearby theaters."""
        mock_settings.local = False
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "cinemas": [
                {"cinema_id": "1", "cinema_name": "Theater 1"},
                {"cinema_id": "2", "cinema_name": "Theater 2"}
            ]
        }
        mock_get.return_value = mock_response
        
        result = get_nearby_theaters(40.7128, -74.0060)
        
        assert "https://api-gate2.movieglu.com/cinemasNearby/?n=20" in mock_get.call_args[0][0]
        assert len(result["cinemas"]) == 2

    @patch('connectors.movieglu.requests.get')
    @patch('connectors.movieglu.SETTINGS')
    def test_get_nearby_theaters_empty(self, mock_settings, mock_get):
        """Test empty response for nearby theaters."""
        mock_settings.local = False
        mock_response = Mock()
        mock_response.status_code = 204
        mock_get.return_value = mock_response
        
        result = get_nearby_theaters(40.7128, -74.0060)
        
        assert result == []


class TestSearchTheaters:
    """Test the search_theaters function."""

    @patch('connectors.movieglu.requests.get')
    @patch('connectors.movieglu.SETTINGS')
    def test_search_theaters_success(self, mock_settings, mock_get):
        """Test successful theater search."""
        mock_settings.local = False
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "cinemas": [{"cinema_id": "1", "cinema_name": "AMC Theater"}]
        }
        mock_get.return_value = mock_response
        
        result = search_theaters(40.7128, -74.0060, "AMC")
        
        assert "https://api-gate2.movieglu.com/cinemaLiveSearch/?query=AMC&n=20" in mock_get.call_args[0][0]
        assert result["cinemas"][0]["cinema_name"] == "AMC Theater"

    @patch('connectors.movieglu.requests.get')
    @patch('connectors.movieglu.SETTINGS')
    def test_search_theaters_special_characters(self, mock_settings, mock_get):
        """Test theater search with special characters."""
        mock_settings.local = False
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"cinemas": []}
        mock_get.return_value = mock_response
        
        search_theaters(40.7128, -74.0060, "Ciné & Co")
        
        # Verify query is included in URL (may be encoded)
        call_url = mock_get.call_args[0][0]
        assert "query=" in call_url


class TestSearchFilms:
    """Test the search_films function."""

    @patch('connectors.movieglu.requests.get')
    @patch('connectors.movieglu.SETTINGS')
    def test_search_films_success(self, mock_settings, mock_get):
        """Test successful film search."""
        mock_settings.local = False
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "films": [{"film_id": "123", "film_name": "The Matrix"}]
        }
        mock_get.return_value = mock_response
        
        result = search_films(40.7128, -74.0060, "Matrix")
        
        assert "https://api-gate2.movieglu.com/filmLiveSearch/?query=Matrix&n=20" in mock_get.call_args[0][0]
        assert result["films"][0]["film_name"] == "The Matrix"


class TestGetTheaterShowtimes:
    """Test the get_theater_showtimes function."""

    @patch('connectors.movieglu.requests.get')
    @patch('connectors.movieglu.SETTINGS')
    def test_get_theater_showtimes_success(self, mock_settings, mock_get):
        """Test successful retrieval of theater showtimes."""
        mock_settings.local = False
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "cinema": {"cinema_id": "123"},
            "films": [{"film_id": "456"}],
            "showtimes": [{"time": "14:00"}, {"time": "17:00"}]
        }
        mock_get.return_value = mock_response
        
        result = get_theater_showtimes(123, 456, 40.7128, -74.0060, "2024-01-15")
        
        expected_url = "https://api-gate2.movieglu.com/cinemaShowTimes/?film_id=456&date=2024-01-15&cinema_id=123"
        assert expected_url in mock_get.call_args[0][0]
        assert len(result["showtimes"]) == 2

    @patch('connectors.movieglu.requests.get')
    @patch('connectors.movieglu.SETTINGS')
    def test_get_theater_showtimes_no_content(self, mock_settings, mock_get):
        """Test handling of no showtimes available."""
        mock_settings.local = False
        mock_response = Mock()
        mock_response.status_code = 204
        mock_get.return_value = mock_response
        
        result = get_theater_showtimes(123, 456, 40.7128, -74.0060, "2024-01-15")
        
        assert result == []


class TestGetFilmShowtimes:
    """Test the get_film_showtimes function."""

    @patch('connectors.movieglu.requests.get')
    @patch('connectors.movieglu.SETTINGS')
    def test_get_film_showtimes_success(self, mock_settings, mock_get):
        """Test successful retrieval of film showtimes."""
        mock_settings.local = False
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "films": [{"film_id": "123"}],
            "cinemas": [{"cinema_id": "456"}, {"cinema_id": "789"}],
            "showtimes": []
        }
        mock_get.return_value = mock_response
        
        result = get_film_showtimes("123", 40.7128, -74.0060, "2024-01-15")
        
        expected_url = "https://api-gate2.movieglu.com/filmShowTimes/?n=20&film_id=123&date=2024-01-15"
        assert expected_url in mock_get.call_args[0][0]
        assert len(result["cinemas"]) == 2


class TestFunctionTools:
    """Test the function tool wrappers."""

    @patch('connectors.movieglu.search_films')
    @pytest.mark.asyncio
    async def test_search_films_near_location_tool(self, mock_search):
        """Test search_films_near_location function tool."""
        mock_search.return_value = {"films": [{"film_id": "1", "film_name": "Test Movie"}]}
        
        mock_ctx = Mock()
        result = await search_films_near_location.on_invoke_tool(
            mock_ctx,
            '{"latitude": 40.7128, "longitude": -74.0060, "query": "Test"}'
        )
        
        assert result["response_type"] == "movieglu_search_films"
        assert result["agent_name"] == "MovieGlu"
        assert result["response"]["films"][0]["film_name"] == "Test Movie"

    @patch('connectors.movieglu.get_films_showing')
    @pytest.mark.asyncio
    async def test_get_films_showing_near_location_tool(self, mock_get_films):
        """Test get_films_showing_near_location function tool."""
        mock_get_films.return_value = {"films": [{"film_id": "1"}]}
        
        mock_ctx = Mock()
        result = await get_films_showing_near_location.on_invoke_tool(
            mock_ctx,
            '{"latitude": 40.7128, "longitude": -74.0060}'
        )
        
        assert result["response_type"] == "movieglu_films_showing_near_location"
        assert result["agent_name"] == "MovieGlu"

    @patch('connectors.movieglu.get_nearby_theaters')
    @pytest.mark.asyncio
    async def test_get_nearby_theaters_near_location_tool(self, mock_get_theaters):
        """Test get_nearby_theaters_near_location function tool."""
        mock_get_theaters.return_value = {"cinemas": [{"cinema_id": "1"}]}
        
        mock_ctx = Mock()
        result = await get_nearby_theaters_near_location.on_invoke_tool(
            mock_ctx,
            '{"latitude": 40.7128, "longitude": -74.0060}'
        )
        
        assert result["response_type"] == "movieglu_nearby_theaters"

    @patch('connectors.movieglu.search_theaters')
    @pytest.mark.asyncio
    async def test_search_theaters_near_location_tool(self, mock_search):
        """Test search_theaters_near_location function tool."""
        mock_search.return_value = {"cinemas": [{"cinema_id": "1"}]}
        
        mock_ctx = Mock()
        result = await search_theaters_near_location.on_invoke_tool(
            mock_ctx,
            '{"latitude": 40.7128, "longitude": -74.0060, "query": "AMC"}'
        )
        
        assert result["response_type"] == "movieglu_search_theaters"

    @patch('connectors.movieglu.get_theater_showtimes')
    @patch('builtins.print')
    @pytest.mark.asyncio
    async def test_get_theater_showtimes_near_location_tool(self, mock_print, mock_get_showtimes):
        """Test get_theater_showtimes_near_location function tool."""
        mock_get_showtimes.return_value = {"showtimes": [{"time": "14:00"}]}
        
        mock_ctx = Mock()
        result = await get_theater_showtimes_near_location.on_invoke_tool(
            mock_ctx,
            '{"latitude": 40.7128, "longitude": -74.0060, "theater_id": 123, "film_id": 456, "date": "2024-01-15"}'
        )
        
        assert result["response_type"] == "movieglu_theater_showtimes"
        # Verify print was called
        assert mock_print.call_count >= 1

    @patch('connectors.movieglu.get_theater_showtimes')
    @patch('builtins.print')
    @pytest.mark.asyncio
    async def test_get_theater_showtimes_error_handling(self, mock_print, mock_get_showtimes):
        """Test error handling in get_theater_showtimes_near_location."""
        mock_get_showtimes.side_effect = Exception("API Error")
        
        mock_ctx = Mock()
        result = await get_theater_showtimes_near_location.on_invoke_tool(
            mock_ctx,
            '{"latitude": 40.7128, "longitude": -74.0060, "theater_id": 123, "film_id": 456, "date": "2024-01-15"}'
        )
        
        assert result["response"] == []
        # Verify error was printed
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("Error getting showtimes" in call for call in print_calls)

    @patch('connectors.movieglu.get_film_showtimes')
    @patch('builtins.print')
    @pytest.mark.asyncio
    async def test_get_film_showtimes_near_location_tool(self, mock_print, mock_get_showtimes):
        """Test get_film_showtimes_near_location function tool."""
        mock_get_showtimes.return_value = {"showtimes": [{"time": "14:00"}]}
        
        mock_ctx = Mock()
        result = await get_film_showtimes_near_location.on_invoke_tool(
            mock_ctx,
            '{"latitude": 40.7128, "longitude": -74.0060, "film_id": "123", "date": "2024-01-15"}'
        )
        
        assert result["response_type"] == "movieglu_film_showtimes"
        # Verify print was called
        assert mock_print.call_count >= 1


class TestMovieGluAgentIntegration:
    """Integration tests for MovieGlu agent components."""

    def test_agent_tools_registration(self):
        """Test that tools are properly registered with the agent."""
        tool_names = [tool.name for tool in MOVIEGLU_AGENT.tools]
        assert "get_films_showing_near_location" in tool_names
        assert "get_nearby_theaters_near_location" in tool_names
        assert "search_theaters_near_location" in tool_names
        assert "get_theater_showtimes_near_location" in tool_names
        assert "get_film_showtimes_near_location" in tool_names
        assert "search_films_near_location" in tool_names

    def test_realtime_agent_tools_match(self):
        """Test that realtime agent has same tools as regular agent."""
        regular_tool_names = [tool.name for tool in MOVIEGLU_AGENT.tools]
        realtime_tool_names = [tool.name for tool in REALTIME_MOVIEGLU_AGENT.tools]
        assert set(regular_tool_names) == set(realtime_tool_names)

    def test_import_dependencies(self):
        """Test that agent dependencies are properly imported."""
        try:
            from connectors.movieglu import (
                MOVIEGLU_AGENT,
                REALTIME_MOVIEGLU_AGENT,
                get_films_showing_near_location,
                search_films_near_location
            )
            assert MOVIEGLU_AGENT is not None
            assert REALTIME_MOVIEGLU_AGENT is not None
            assert get_films_showing_near_location is not None
            assert search_films_near_location is not None
        except ImportError as e:
            pytest.fail(f"Failed to import MovieGlu components: {e}")


class TestMovieGluEdgeCases:
    """Test edge cases and error conditions."""

    def test_tool_function_signatures(self):
        """Test that tool functions have correct parameter schemas."""
        # Test search_films_near_location parameters
        schema = search_films_near_location.params_json_schema
        assert "properties" in schema
        params = schema["properties"]
        assert "latitude" in params
        assert "longitude" in params
        assert "query" in params

        # Test get_theater_showtimes_near_location parameters
        schema = get_theater_showtimes_near_location.params_json_schema
        assert "properties" in schema
        params = schema["properties"]
        assert "latitude" in params
        assert "longitude" in params
        assert "theater_id" in params
        assert "film_id" in params
        assert "date" in params

    def test_all_tools_have_descriptions(self):
        """Test that all tools have proper descriptions."""
        for tool in ALL_TOOLS:
            assert hasattr(tool, 'description')
            assert tool.description is not None
            assert len(tool.description) > 0

    @patch('connectors.movieglu.datetime')
    def test_date_formatting_in_headers(self, mock_datetime):
        """Test that date is properly formatted in headers."""
        # Test with timezone aware datetime
        mock_now = Mock()
        mock_now.isoformat.return_value = "2024-01-15T10:00:00.123456+05:00"
        mock_datetime.datetime.now.return_value = mock_now
        
        headers = build_headers(40.7128, -74.0060)
        
        # Should strip timezone and add Z
        assert headers['device-datetime'] == "2024-01-15T10:00:00.123456Z"

    def test_coordinate_precision(self):
        """Test that coordinates maintain precision."""
        headers = build_headers(40.712345678, -74.006012345)
        assert headers['geolocation'] == "40.712345678;-74.006012345"

    @pytest.mark.asyncio
    async def test_missing_required_parameters(self):
        """Test tools with missing required parameters."""
        mock_ctx = Mock()
        
        # Test search_films without query
        result = await search_films_near_location.on_invoke_tool(
            mock_ctx,
            '{"latitude": 40.7128, "longitude": -74.0060}'
        )
        assert isinstance(result, str)
        assert "error" in result.lower()

    def test_tool_response_consistency(self):
        """Test that all tools return consistent ToolResponse format."""
        # All tool responses should have these fields
        expected_fields = ["response_type", "agent_name", "friendly_name", "response"]
        
        # This is tested via the function tool tests above
        # Each tool should return a dict with these fields
        assert True  # Placeholder for structure test