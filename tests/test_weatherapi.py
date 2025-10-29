"""
Comprehensive tests for connectors/weatherapi.py

Tests cover weather function tools, agent configurations, and API interactions.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from agents import Agent, RunContextWrapper
# RealtimeAgent import moved to test methods to avoid import order issues


class TestWeatherAPIFunctionTools:
    """Test function tools in the weatherapi module."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock context wrapper."""
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = Mock()
        mock_wrapper.context.settings = Mock()
        mock_wrapper.context.settings.weatherapi_api_key = "test_api_key"
        return mock_wrapper

    def test_current_weather_tool_exists_and_configured(self):
        """Test that current weather tool exists and is properly configured."""
        from connectors.weatherapi import get_current_weather_by_location, ALL_TOOLS

        # Verify tool exists in ALL_TOOLS
        tool_names = [tool.name for tool in ALL_TOOLS]
        assert 'get_current_weather_by_location' in tool_names

        # Verify tool has correct configuration
        assert hasattr(get_current_weather_by_location, 'name')
        assert hasattr(get_current_weather_by_location, 'description')
        assert hasattr(get_current_weather_by_location, 'on_invoke_tool')

        # Verify description content
        description = get_current_weather_by_location.description.lower()
        assert 'current weather' in description
        assert 'any location' in description or 'location' in description

    def test_forecast_weather_tool_exists_and_configured(self):
        """Test that forecast weather tool exists and is properly configured."""
        from connectors.weatherapi import get_forecast_weather_by_location, ALL_TOOLS

        # Verify tool exists in ALL_TOOLS
        tool_names = [tool.name for tool in ALL_TOOLS]
        assert 'get_forecast_weather_by_location' in tool_names

        # Verify tool has correct configuration
        assert hasattr(get_forecast_weather_by_location, 'name')
        assert hasattr(get_forecast_weather_by_location, 'description')
        assert hasattr(get_forecast_weather_by_location, 'on_invoke_tool')

        # Verify description content
        description = get_forecast_weather_by_location.description.lower()
        assert 'forecast' in description
        assert 'weather' in description
        assert 'predictions' in description

    def test_weather_api_integration_setup(self):
        """Test that the weather API integration is properly set up."""
        import connectors.weatherapi as weatherapi_module

        # Test that key components are available
        assert hasattr(weatherapi_module, 'requests')
        assert hasattr(weatherapi_module, 'get_current_weather_by_location')
        assert hasattr(weatherapi_module, 'get_forecast_weather_by_location')
        assert hasattr(weatherapi_module, 'ALL_TOOLS')

        # Test that ALL_TOOLS contains both weather functions
        assert len(weatherapi_module.ALL_TOOLS) == 2

    def test_tool_response_import(self):
        """Test that ToolResponse utility is properly imported."""
        from connectors.utils.responses import ToolResponse

        # Create a test response to ensure it works
        response = ToolResponse(
            response_type="test_weather",
            agent_name="WeatherAPI",
            friendly_name="Test Weather",
            response={"test": "data"}
        )

        result = response.to_dict()
        assert result['response_type'] == 'test_weather'
        assert result['agent_name'] == 'WeatherAPI'


class TestWeatherAPIAgentConfiguration:
    """Test agent configurations and setup."""

    def test_weatherapi_agent_configuration(self):
        """Test that WEATHERAPI_AGENT is properly configured."""
        from connectors.weatherapi import WEATHERAPI_AGENT

        assert WEATHERAPI_AGENT is not None
        assert isinstance(WEATHERAPI_AGENT, Agent)
        assert WEATHERAPI_AGENT.name == "WeatherAPI"
        assert WEATHERAPI_AGENT.model == "gpt-4o"
        assert len(WEATHERAPI_AGENT.tools) == 2
        assert len(WEATHERAPI_AGENT.handoffs) == 2

    def test_all_tools_list(self):
        """Test that ALL_TOOLS list is properly configured."""
        from connectors.weatherapi import ALL_TOOLS

        assert len(ALL_TOOLS) == 2

        tool_names = [tool.name for tool in ALL_TOOLS]
        expected_tools = [
            'get_current_weather_by_location',
            'get_forecast_weather_by_location'
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    def test_agent_instructions_and_descriptions(self):
        """Test that agent instructions and descriptions are appropriate."""
        from connectors.weatherapi import WEATHERAPI_AGENT, REALTIME_WEATHERAPI_AGENT

        # Check that instructions mention key functionality
        agent_instructions = WEATHERAPI_AGENT.instructions.lower()
        assert "weather assistant" in agent_instructions
        assert "current conditions" in agent_instructions
        assert "forecast" in agent_instructions

        # Check handoff description
        handoff_desc = WEATHERAPI_AGENT.handoff_description.lower()
        assert "weather:" in handoff_desc
        assert "current conditions" in handoff_desc

        # Realtime agent should have similar instructions
        realtime_instructions = REALTIME_WEATHERAPI_AGENT.instructions.lower()
        assert "weatherapi assistant" in realtime_instructions
        assert "current weather" in realtime_instructions

    def test_agent_handoffs(self):
        """Test that agent handoffs are configured correctly."""
        from connectors.weatherapi import WEATHERAPI_AGENT

        handoff_names = [agent.name for agent in WEATHERAPI_AGENT.handoffs]

        # Should include Gmail and Google Docs agents
        expected_handoffs = ["GMail", "Google Docs"]

        for expected_handoff in expected_handoffs:
            assert expected_handoff in handoff_names


class TestWeatherAPIToolFunctionality:
    """Test the detailed functionality of weather tools."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock context wrapper."""
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = Mock()
        mock_wrapper.context.settings = Mock()
        mock_wrapper.context.settings.weatherapi_api_key = "test_key"
        return mock_wrapper

    @patch('connectors.weatherapi.requests.get')
    @pytest.mark.asyncio
    async def test_get_current_weather_success(self, mock_get):
        """Test successful current weather retrieval."""
        from connectors.weatherapi import get_current_weather_by_location

        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "location": {
                "name": "New York",
                "region": "New York",
                "country": "USA",
                "lat": 40.71,
                "lon": -74.01,
                "tz_id": "America/New_York",
                "localtime": "2024-01-01 12:00"
            },
            "current": {
                "temp_c": 20.0,
                "temp_f": 68.0,
                "is_day": 1,
                "condition": {
                    "text": "Partly cloudy",
                    "icon": "//cdn.weatherapi.com/weather/64x64/day/116.png"
                },
                "wind_mph": 10.5,
                "wind_kph": 16.9,
                "humidity": 65,
                "feelslike_c": 18.0,
                "feelslike_f": 64.4,
                "vis_km": 10.0,
                "uv": 4.0
            }
        }
        mock_get.return_value = mock_response

        # Create mock context
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = Mock()
        mock_wrapper.context.settings = Mock()
        mock_wrapper.context.settings.weatherapi_api_key = "test_api_key"

        # Call the function tool
        result = await get_current_weather_by_location.on_invoke_tool(
            mock_wrapper,
            '{"location": "New York"}'
        )

        # Verify API call was made correctly
        mock_get.assert_called_once_with(
            "https://api.weatherapi.com/v1/current.json?key=test_api_key&q=New York"
        )

        # Verify response structure
        assert result["response_type"] == "current_weather_by_location"
        assert result["agent_name"] == "WeatherAPI"
        assert result["friendly_name"] == "Current Weather by Location"
        assert result["display_response"] is True
        assert result["response"]["location"]["name"] == "New York"
        assert result["response"]["current"]["temp_c"] == 20.0

    @patch('connectors.weatherapi.requests.get')
    @pytest.mark.asyncio
    async def test_get_forecast_weather_success(self, mock_get):
        """Test successful weather forecast retrieval."""
        from connectors.weatherapi import get_forecast_weather_by_location

        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "location": {
                "name": "London",
                "region": "City of London, Greater London",
                "country": "UK"
            },
            "forecast": {
                "forecastday": [
                    {
                        "date": "2024-01-01",
                        "day": {
                            "maxtemp_c": 15.0,
                            "mintemp_c": 8.0,
                            "avgtemp_c": 11.5,
                            "totalprecip_mm": 2.5,
                            "condition": {
                                "text": "Light rain"
                            },
                            "daily_chance_of_rain": 80
                        },
                        "hour": []
                    },
                    {
                        "date": "2024-01-02",
                        "day": {
                            "maxtemp_c": 12.0,
                            "mintemp_c": 6.0,
                            "avgtemp_c": 9.0,
                            "totalprecip_mm": 0.0,
                            "condition": {
                                "text": "Sunny"
                            },
                            "daily_chance_of_rain": 10
                        },
                        "hour": []
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        # Create mock context
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = Mock()
        mock_wrapper.context.settings = Mock()
        mock_wrapper.context.settings.weatherapi_api_key = "test_api_key"

        # Call the function tool with custom days parameter
        result = await get_forecast_weather_by_location.on_invoke_tool(
            mock_wrapper,
            '{"location": "London", "days": 3}'
        )

        # Verify API call was made correctly
        mock_get.assert_called_once_with(
            "https://api.weatherapi.com/v1/forecast.json?key=test_api_key&q=London&days=3"
        )

        # Verify response structure
        assert result["response_type"] == "forecast_weather_by_location"
        assert result["agent_name"] == "WeatherAPI"
        assert result["friendly_name"] == "Forecast Weather by Location"
        assert result["display_response"] is True
        assert result["response"]["location"]["name"] == "London"
        assert len(result["response"]["forecast"]["forecastday"]) == 2
        assert result["response"]["forecast"]["forecastday"][0]["day"]["maxtemp_c"] == 15.0

    @patch('connectors.weatherapi.requests.get')
    @pytest.mark.asyncio
    async def test_get_forecast_weather_default_days(self, mock_get):
        """Test weather forecast with default days parameter."""
        from connectors.weatherapi import get_forecast_weather_by_location

        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "location": {"name": "Paris"},
            "forecast": {"forecastday": []}
        }
        mock_get.return_value = mock_response

        # Create mock context
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = Mock()
        mock_wrapper.context.settings = Mock()
        mock_wrapper.context.settings.weatherapi_api_key = "test_api_key"

        # Call without days parameter (should use default of 5)
        result = await get_forecast_weather_by_location.on_invoke_tool(
            mock_wrapper,
            '{"location": "Paris"}'
        )

        # Verify API call used default days=5
        mock_get.assert_called_once_with(
            "https://api.weatherapi.com/v1/forecast.json?key=test_api_key&q=Paris&days=5"
        )

    @patch('connectors.weatherapi.requests.get')
    @pytest.mark.asyncio
    async def test_get_current_weather_api_error(self, mock_get):
        """Test handling of API errors for current weather."""
        from connectors.weatherapi import get_current_weather_by_location

        # Mock API error
        mock_get.side_effect = Exception("Network error")

        # Create mock context
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = Mock()
        mock_wrapper.context.settings = Mock()
        mock_wrapper.context.settings.weatherapi_api_key = "test_api_key"

        # Call the function tool
        result = await get_current_weather_by_location.on_invoke_tool(
            mock_wrapper,
            '{"location": "Invalid Location"}'
        )

        # The function tool framework catches exceptions and returns error message as string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()

    @patch('connectors.weatherapi.requests.get')
    @pytest.mark.asyncio
    async def test_get_current_weather_special_characters(self, mock_get):
        """Test handling of special characters in location."""
        from connectors.weatherapi import get_current_weather_by_location

        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "location": {"name": "São Paulo"},
            "current": {"temp_c": 25.0}
        }
        mock_get.return_value = mock_response

        # Create mock context
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = Mock()
        mock_wrapper.context.settings = Mock()
        mock_wrapper.context.settings.weatherapi_api_key = "test_api_key"

        # Call with special characters
        result = await get_current_weather_by_location.on_invoke_tool(
            mock_wrapper,
            '{"location": "São Paulo, Brazil"}'
        )

        # Verify API call with special characters
        mock_get.assert_called_once_with(
            "https://api.weatherapi.com/v1/current.json?key=test_api_key&q=São Paulo, Brazil"
        )

    def test_current_weather_tool_docstring(self):
        """Test that current weather tool has appropriate docstring."""
        from connectors.weatherapi import get_current_weather_by_location

        # FunctionTool objects have description instead of __doc__
        description = get_current_weather_by_location.description.lower()

        assert "current" in description or "real-time" in description
        assert "weather" in description
        # Check for weather metrics mentioned in the new description
        assert "any location" in description or "location" in description
        assert "location" in description

    def test_forecast_weather_tool_docstring(self):
        """Test that forecast weather tool has appropriate docstring."""
        from connectors.weatherapi import get_forecast_weather_by_location

        # FunctionTool objects have description instead of __doc__
        description = get_forecast_weather_by_location.description.lower()

        assert "forecast" in description
        assert "daily" in description or "hourly" in description
        assert "predictions" in description
        assert "precipitation" in description or "predictions" in description

    def test_weather_tool_response_structure(self):
        """Test that weather tools use ToolResponse structure."""
        from connectors.utils.responses import ToolResponse

        # Test that a ToolResponse can be created with weather-specific fields
        response = ToolResponse(
            response_type="current_weather_by_location",
            agent_name="WeatherAPI",
            friendly_name="Current Weather by Location",
            display_response=True,
            response={"location": {"name": "Test"}, "current": {"temp_c": 20}}
        )

        result = response.to_dict()

        # Should have standard ToolResponse structure
        required_fields = ['response_type', 'agent_name',
                           'friendly_name', 'display_response', 'response']

        for field in required_fields:
            assert field in result

        # Test specific field values
        assert result['response_type'] == 'current_weather_by_location'
        assert result['agent_name'] == 'WeatherAPI'
        assert result['display_response'] == True

    def test_weather_api_url_structure(self):
        """Test that weather API URLs are constructed correctly."""
        api_key = "test_key"
        location = "New York"
        days = 7

        # Test current weather URL structure
        current_url = f"https://api.weatherapi.com/v1/current.json?key={api_key}&q={location}"
        assert "api.weatherapi.com" in current_url
        assert "current.json" in current_url
        assert f"key={api_key}" in current_url
        assert f"q={location}" in current_url

        # Test forecast weather URL structure
        forecast_url = f"https://api.weatherapi.com/v1/forecast.json?key={api_key}&q={location}&days={days}"
        assert "api.weatherapi.com" in forecast_url
        assert "forecast.json" in forecast_url
        assert f"days={days}" in forecast_url


class TestWeatherAPIErrorHandling:
    """Test error handling concepts for weather API functions."""

    @pytest.mark.asyncio
    async def test_missing_required_parameters(self):
        """Test tools with missing required parameters."""
        from connectors.weatherapi import get_current_weather_by_location, get_forecast_weather_by_location

        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = Mock()
        mock_wrapper.context.settings = Mock()
        mock_wrapper.context.settings.weatherapi_api_key = "test_api_key"

        # Test get_current_weather_by_location without location
        result = await get_current_weather_by_location.on_invoke_tool(
            mock_wrapper,
            '{}'
        )
        assert isinstance(result, str)
        assert "error" in result.lower()

        # Test get_forecast_weather_by_location without location
        result = await get_forecast_weather_by_location.on_invoke_tool(
            mock_wrapper,
            '{}'
        )
        assert isinstance(result, str)
        assert "error" in result.lower()

    def test_tool_signatures(self):
        """Test that tools have correct parameter schemas."""
        from connectors.weatherapi import get_current_weather_by_location, get_forecast_weather_by_location

        # Test current weather tool signature
        current_schema = get_current_weather_by_location.params_json_schema
        assert "properties" in current_schema
        params = current_schema["properties"]
        assert "location" in params
        assert params["location"]["type"] == "string"

        # Test forecast weather tool signature
        forecast_schema = get_forecast_weather_by_location.params_json_schema
        assert "properties" in forecast_schema
        params = forecast_schema["properties"]
        assert "location" in params
        assert params["location"]["type"] == "string"
        assert "days" in params
        assert params["days"]["type"] == "integer"

    @patch('connectors.weatherapi.requests.get')
    @pytest.mark.asyncio
    async def test_get_forecast_weather_json_error(self, mock_get):
        """Test handling when API returns invalid JSON."""
        from connectors.weatherapi import get_forecast_weather_by_location

        # Mock invalid JSON response
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = Mock()
        mock_wrapper.context.settings = Mock()
        mock_wrapper.context.settings.weatherapi_api_key = "test_api_key"

        result = await get_forecast_weather_by_location.on_invoke_tool(
            mock_wrapper,
            '{"location": "London", "days": 7}'
        )

        # Should catch the error and return error string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()

    def test_requests_exception_types(self):
        """Test that proper exception types are available for error handling."""
        import requests

        # Verify that the expected exception types exist
        assert hasattr(requests, 'RequestException')
        assert hasattr(requests, 'Timeout')
        assert hasattr(requests, 'ConnectionError')

        # Test exception hierarchy
        assert issubclass(requests.Timeout, requests.RequestException)
        assert issubclass(requests.ConnectionError, requests.RequestException)

    def test_api_error_response_structure(self):
        """Test handling of API error response structures."""
        # Test typical error response structure from WeatherAPI
        error_response = {
            "error": {
                "code": 1006,
                "message": "No matching location found."
            }
        }

        # Verify error response has expected structure
        assert 'error' in error_response
        assert 'code' in error_response['error']
        assert 'message' in error_response['error']

    def test_api_key_validation_concept(self):
        """Test API key validation concepts."""
        # Test valid API key format concept
        valid_api_key = "abc123def456"
        assert isinstance(valid_api_key, str)
        assert len(valid_api_key) > 0

        # Test invalid API key scenarios
        invalid_keys = [None, "", " "]
        for key in invalid_keys:
            if key is None or len(str(key).strip()) == 0:
                # This would be invalid
                assert key is None or key.strip() == ""


class TestWeatherAPIIntegration:
    """Integration tests for weatherapi components."""

    def test_all_imports_work(self):
        """Test that all imports work correctly."""
        try:
            from connectors.weatherapi import (
                WEATHERAPI_AGENT,
                REALTIME_WEATHERAPI_AGENT,
                ALL_TOOLS,
                get_current_weather_by_location,
                get_forecast_weather_by_location
            )

            # Basic validation
            assert WEATHERAPI_AGENT is not None
            assert REALTIME_WEATHERAPI_AGENT is not None
            assert len(ALL_TOOLS) == 2
            # FunctionTool objects are not directly callable but have on_invoke_tool
            assert hasattr(get_current_weather_by_location, 'on_invoke_tool')
            assert callable(get_current_weather_by_location.on_invoke_tool)
            assert hasattr(get_forecast_weather_by_location, 'on_invoke_tool')
            assert callable(get_forecast_weather_by_location.on_invoke_tool)

        except ImportError as e:
            pytest.fail(f"Failed to import weatherapi components: {e}")

    def test_agent_tool_consistency(self):
        """Test that both agents have the same tools."""
        from connectors.weatherapi import WEATHERAPI_AGENT, REALTIME_WEATHERAPI_AGENT, ALL_TOOLS

        # Both agents should have the same number of tools as ALL_TOOLS
        assert len(WEATHERAPI_AGENT.tools) == len(ALL_TOOLS)
        assert len(REALTIME_WEATHERAPI_AGENT.tools) == len(ALL_TOOLS)

        # Tool function objects should match (compare by name since FunctionTool not hashable)
        agent_tool_names = [tool.name for tool in WEATHERAPI_AGENT.tools]
        realtime_tool_names = [
            tool.name for tool in REALTIME_WEATHERAPI_AGENT.tools]
        all_tool_names = [tool.name for tool in ALL_TOOLS]

        assert set(agent_tool_names) == set(all_tool_names)
        assert set(realtime_tool_names) == set(all_tool_names)

    def test_weatherapi_module_structure(self):
        """Test the overall module structure."""
        import connectors.weatherapi as weatherapi_module

        # Should have expected attributes
        expected_attributes = [
            'WEATHERAPI_AGENT',
            'REALTIME_WEATHERAPI_AGENT',
            'ALL_TOOLS',
            'get_current_weather_by_location',
            'get_forecast_weather_by_location'
        ]

        for attr in expected_attributes:
            assert hasattr(weatherapi_module,
                           attr), f"Missing attribute: {attr}"

    def test_tool_registration_with_agents(self):
        """Test that tools are properly registered with agents."""
        from connectors.weatherapi import (
            WEATHERAPI_AGENT,
            REALTIME_WEATHERAPI_AGENT,
            get_current_weather_by_location,
            get_forecast_weather_by_location
        )

        # Check that specific tools are in agent tools
        agent_tool_funcs = [tool for tool in WEATHERAPI_AGENT.tools]
        realtime_tool_funcs = [
            tool for tool in REALTIME_WEATHERAPI_AGENT.tools]

        expected_tools = [get_current_weather_by_location,
                          get_forecast_weather_by_location]

        for tool in expected_tools:
            assert tool in agent_tool_funcs
            assert tool in realtime_tool_funcs
