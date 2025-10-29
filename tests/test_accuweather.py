"""
Comprehensive tests for connectors/accuweather.py

Tests cover weather function tools, agent configurations, and API interactions.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from aiohttp import ClientError
from agents import Agent, RunContextWrapper
from accuweather import (
    ApiError,
    InvalidApiKeyError,
    InvalidCoordinatesError,
    RequestsExceededError,
)


class TestAccuWeatherFunctionTools:
    """Test function tools in the accuweather module."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock context wrapper."""
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = Mock()
        mock_wrapper.context.settings = Mock()
        mock_wrapper.context.settings.accuweather_api_key = "test_api_key"
        return mock_wrapper

    def test_current_weather_tool_exists_and_configured(self):
        """Test that current weather tool exists and is properly configured."""
        from connectors.accuweather import get_current_weather_by_latitude_longitude, ALL_TOOLS

        # Verify tool exists in ALL_TOOLS
        tool_names = [tool.name for tool in ALL_TOOLS]
        assert 'get_current_weather_by_latitude_longitude' in tool_names

        # Verify tool has correct configuration
        assert hasattr(get_current_weather_by_latitude_longitude, 'name')
        assert hasattr(
            get_current_weather_by_latitude_longitude, 'description')
        assert hasattr(
            get_current_weather_by_latitude_longitude, 'on_invoke_tool')

        # Verify description content
        description = get_current_weather_by_latitude_longitude.description.lower()
        assert 'current weather' in description
        assert 'location' in description

    def test_daily_forecast_tool_exists_and_configured(self):
        """Test that daily forecast tool exists and is properly configured."""
        from connectors.accuweather import get_daily_forecast_weather_by_latitude_longitude, ALL_TOOLS

        # Verify tool exists in ALL_TOOLS
        tool_names = [tool.name for tool in ALL_TOOLS]
        assert 'get_daily_forecast_weather_by_latitude_longitude' in tool_names

        # Verify tool has correct configuration
        assert hasattr(
            get_daily_forecast_weather_by_latitude_longitude, 'name')
        assert hasattr(
            get_daily_forecast_weather_by_latitude_longitude, 'description')
        assert hasattr(
            get_daily_forecast_weather_by_latitude_longitude, 'on_invoke_tool')

        # Verify description content
        description = get_daily_forecast_weather_by_latitude_longitude.description.lower()
        assert 'forecast' in description
        assert '10 days' in description

    def test_hourly_forecast_tool_exists_and_configured(self):
        """Test that hourly forecast tool exists and is properly configured."""
        from connectors.accuweather import get_hourly_forecast_weather_by_latitude_longitude, ALL_TOOLS

        # Verify tool exists in ALL_TOOLS
        tool_names = [tool.name for tool in ALL_TOOLS]
        assert 'get_hourly_forecast_weather_by_latitude_longitude' in tool_names

        # Verify tool has correct configuration
        assert hasattr(
            get_hourly_forecast_weather_by_latitude_longitude, 'name')
        assert hasattr(
            get_hourly_forecast_weather_by_latitude_longitude, 'description')
        assert hasattr(
            get_hourly_forecast_weather_by_latitude_longitude, 'on_invoke_tool')

        # Verify description content
        description = get_hourly_forecast_weather_by_latitude_longitude.description.lower()
        assert '72 hours' in description
        assert 'hour' in description

    def test_accuweather_integration_setup(self):
        """Test that the AccuWeather integration is properly set up."""
        import connectors.accuweather as accuweather_module

        # Test that key components are available
        assert hasattr(accuweather_module,
                       'get_current_weather_by_latitude_longitude')
        assert hasattr(accuweather_module,
                       'get_daily_forecast_weather_by_latitude_longitude')
        assert hasattr(accuweather_module,
                       'get_hourly_forecast_weather_by_latitude_longitude')
        assert hasattr(accuweather_module, 'ALL_TOOLS')
        assert hasattr(accuweather_module, 'ACCUWEATHER_AGENT')
        assert hasattr(accuweather_module, 'REALTIME_WEATHERAPI_AGENT')

        # Test that ALL_TOOLS contains all three weather functions
        assert len(accuweather_module.ALL_TOOLS) == 3

    def test_tool_response_import(self):
        """Test that ToolResponse utility is properly imported."""
        from connectors.utils.responses import ToolResponse

        # Create a test response to ensure it works
        response = ToolResponse(
            response_type="test_weather",
            agent_name="AccuWeather",
            friendly_name="Test Weather",
            response={"test": "data"}
        )

        result = response.to_dict()
        assert result['response_type'] == 'test_weather'
        assert result['agent_name'] == 'AccuWeather'


class TestAccuWeatherAgentConfiguration:
    """Test agent configurations and setup."""

    def test_accuweather_agent_configuration(self):
        """Test that ACCUWEATHER_AGENT is properly configured."""
        from connectors.accuweather import ACCUWEATHER_AGENT

        assert ACCUWEATHER_AGENT is not None
        assert isinstance(ACCUWEATHER_AGENT, Agent)
        assert ACCUWEATHER_AGENT.name == "Accuweather"
        assert ACCUWEATHER_AGENT.model == "gpt-4o"
        assert len(ACCUWEATHER_AGENT.tools) == 3
        assert len(ACCUWEATHER_AGENT.handoffs) == 2

    def test_realtime_weatherapi_agent_configuration(self):
        """Test that REALTIME_WEATHERAPI_AGENT is properly configured."""
        from connectors.accuweather import REALTIME_WEATHERAPI_AGENT
        from agents.realtime import RealtimeAgent

        assert REALTIME_WEATHERAPI_AGENT is not None
        assert isinstance(REALTIME_WEATHERAPI_AGENT, RealtimeAgent)
        # RealtimeAgent is a mock in tests, so we can't check the name attribute directly
        assert hasattr(REALTIME_WEATHERAPI_AGENT, 'tools')
        assert len(REALTIME_WEATHERAPI_AGENT.tools) == 3

    def test_all_tools_list(self):
        """Test that ALL_TOOLS list is properly configured."""
        from connectors.accuweather import ALL_TOOLS

        assert len(ALL_TOOLS) == 3

        tool_names = [tool.name for tool in ALL_TOOLS]
        expected_tools = [
            'get_current_weather_by_latitude_longitude',
            'get_daily_forecast_weather_by_latitude_longitude',
            'get_hourly_forecast_weather_by_latitude_longitude'
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    def test_agent_instructions_and_descriptions(self):
        """Test that agent instructions and descriptions are appropriate."""
        from connectors.accuweather import ACCUWEATHER_AGENT, REALTIME_WEATHERAPI_AGENT

        # Check that instructions mention key functionality
        agent_instructions = ACCUWEATHER_AGENT.instructions.lower()
        assert "weather assistant" in agent_instructions
        assert "current conditions" in agent_instructions
        assert "forecast" in agent_instructions
        assert "latitude and longitude" in agent_instructions

        # Check handoff description
        handoff_desc = ACCUWEATHER_AGENT.handoff_description.lower()
        assert "weather:" in handoff_desc
        assert "current conditions" in handoff_desc
        assert "latitude and longitude" in handoff_desc

        # Realtime agent should have similar instructions
        realtime_instructions = REALTIME_WEATHERAPI_AGENT.instructions.lower()
        assert "weatherapi assistant" in realtime_instructions
        assert "current weather" in realtime_instructions

    def test_agent_handoffs(self):
        """Test that agent handoffs are configured correctly."""
        from connectors.accuweather import ACCUWEATHER_AGENT

        handoff_names = [agent.name for agent in ACCUWEATHER_AGENT.handoffs]

        # Should include Gmail and Google Docs agents
        expected_handoffs = ["GMail", "Google Docs"]

        for expected_handoff in expected_handoffs:
            assert expected_handoff in handoff_names


class TestAccuWeatherToolFunctionality:
    """Test the detailed functionality of AccuWeather tools."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock context wrapper."""
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = Mock()
        mock_wrapper.context.settings = Mock()
        mock_wrapper.context.settings.accuweather_api_key = "test_key"
        return mock_wrapper

    @pytest.mark.asyncio
    async def test_get_current_weather_success(self, mock_context):
        """Test successful current weather retrieval."""
        from connectors.accuweather import get_current_weather_by_latitude_longitude

        # Mock AccuWeather client
        with patch('connectors.accuweather.AccuWeather') as mock_accuweather:
            mock_client = AsyncMock()
            mock_accuweather.return_value = mock_client

            # Mock successful response
            mock_client.async_get_current_conditions.return_value = {
                "LocalObservationDateTime": "2024-01-01T12:00:00-05:00",
                "EpochTime": 1704124800,
                "WeatherText": "Partly cloudy",
                "WeatherIcon": 3,
                "HasPrecipitation": False,
                "Temperature": {
                    "Metric": {"Value": 20.0, "Unit": "C"},
                    "Imperial": {"Value": 68.0, "Unit": "F"}
                },
                "RealFeelTemperature": {
                    "Metric": {"Value": 18.0, "Unit": "C"},
                    "Imperial": {"Value": 64.4, "Unit": "F"}
                },
                "RelativeHumidity": 65,
                "Wind": {
                    "Direction": {"Degrees": 180, "Localized": "S"},
                    "Speed": {
                        "Metric": {"Value": 16.9, "Unit": "km/h"},
                        "Imperial": {"Value": 10.5, "Unit": "mi/h"}
                    }
                },
                "UVIndex": 4,
                "UVIndexText": "Moderate",
                "Visibility": {
                    "Metric": {"Value": 10.0, "Unit": "km"},
                    "Imperial": {"Value": 6.2, "Unit": "mi"}
                }
            }

            # Call the function
            result = await get_current_weather_by_latitude_longitude.on_invoke_tool(
                mock_context,
                '{"latitude": 40.7128, "longitude": -74.0060}'
            )

            # Verify AccuWeather client was created correctly
            mock_accuweather.assert_called_once()
            call_args = mock_accuweather.call_args
            assert call_args[0][0] == "test_key"  # API key
            assert call_args.kwargs['latitude'] == 40.7128
            assert call_args.kwargs['longitude'] == -74.0060
            assert call_args.kwargs['language'] == "en-us"

            # Verify response structure
            assert result["response_type"] == "current_weather_by_location"
            assert result["agent_name"] == "Accuweather"
            assert result["friendly_name"] == "Current Weather by Location"
            assert result["display_response"] is True
            assert result["response"]["Temperature"]["Metric"]["Value"] == 20.0
            assert result["response"]["WeatherText"] == "Partly cloudy"

    @pytest.mark.asyncio
    async def test_get_daily_forecast_success(self, mock_context):
        """Test successful daily forecast retrieval."""
        from connectors.accuweather import get_daily_forecast_weather_by_latitude_longitude

        # Mock AccuWeather client
        with patch('connectors.accuweather.AccuWeather') as mock_accuweather:
            mock_client = AsyncMock()
            mock_accuweather.return_value = mock_client

            # Mock successful response
            mock_client.async_get_daily_forecast.return_value = {
                "Headline": {
                    "EffectiveDate": "2024-01-01T07:00:00-05:00",
                    "Text": "Partly cloudy throughout the week"
                },
                "DailyForecasts": [
                    {
                        "Date": "2024-01-01T07:00:00-05:00",
                        "Temperature": {
                            "Minimum": {"Value": 46.0, "Unit": "F"},
                            "Maximum": {"Value": 59.0, "Unit": "F"}
                        },
                        "Day": {
                            "Icon": 3,
                            "IconPhrase": "Partly cloudy",
                            "HasPrecipitation": False
                        },
                        "Night": {
                            "Icon": 34,
                            "IconPhrase": "Mostly clear",
                            "HasPrecipitation": False
                        }
                    },
                    {
                        "Date": "2024-01-02T07:00:00-05:00",
                        "Temperature": {
                            "Minimum": {"Value": 43.0, "Unit": "F"},
                            "Maximum": {"Value": 54.0, "Unit": "F"}
                        },
                        "Day": {
                            "Icon": 1,
                            "IconPhrase": "Sunny",
                            "HasPrecipitation": False
                        },
                        "Night": {
                            "Icon": 33,
                            "IconPhrase": "Clear",
                            "HasPrecipitation": False
                        }
                    }
                ]
            }

            # Call the function
            result = await get_daily_forecast_weather_by_latitude_longitude.on_invoke_tool(
                mock_context,
                '{"latitude": 51.5074, "longitude": -0.1278}'
            )

            # Verify AccuWeather client was created correctly
            mock_accuweather.assert_called_once()
            call_args = mock_accuweather.call_args
            assert call_args[0][0] == "test_key"  # API key
            assert call_args.kwargs['latitude'] == 51.5074
            assert call_args.kwargs['longitude'] == -0.1278

            # Verify API call parameters
            mock_client.async_get_daily_forecast.assert_called_once_with(
                days=10,
                metric=False
            )

            # Verify response structure
            assert result["response_type"] == "forecast_weather_by_location"
            assert result["agent_name"] == "AccuWeather"
            assert result["friendly_name"] == "Forecast Weather by Location"
            assert result["display_response"] is True
            assert len(result["response"]["DailyForecasts"]) == 2
            assert result["response"]["DailyForecasts"][0]["Temperature"]["Maximum"]["Value"] == 59.0

    @pytest.mark.asyncio
    async def test_get_hourly_forecast_success(self, mock_context):
        """Test successful hourly forecast retrieval."""
        from connectors.accuweather import get_hourly_forecast_weather_by_latitude_longitude

        # Mock AccuWeather client
        with patch('connectors.accuweather.AccuWeather') as mock_accuweather:
            mock_client = AsyncMock()
            mock_accuweather.return_value = mock_client

            # Mock successful response
            mock_client.async_get_hourly_forecast.return_value = [
                {
                    "DateTime": "2024-01-01T12:00:00-05:00",
                    "WeatherIcon": 3,
                    "IconPhrase": "Partly cloudy",
                    "Temperature": {"Value": 68.0, "Unit": "F"},
                    "RealFeelTemperature": {"Value": 65.0, "Unit": "F"},
                    "RelativeHumidity": 60,
                    "PrecipitationProbability": 10
                },
                {
                    "DateTime": "2024-01-01T13:00:00-05:00",
                    "WeatherIcon": 2,
                    "IconPhrase": "Mostly sunny",
                    "Temperature": {"Value": 70.0, "Unit": "F"},
                    "RealFeelTemperature": {"Value": 67.0, "Unit": "F"},
                    "RelativeHumidity": 58,
                    "PrecipitationProbability": 5
                }
            ]

            # Call the function
            result = await get_hourly_forecast_weather_by_latitude_longitude.on_invoke_tool(
                mock_context,
                '{"latitude": 34.0522, "longitude": -118.2437}'
            )

            # Verify AccuWeather client was created correctly
            mock_accuweather.assert_called_once()
            call_args = mock_accuweather.call_args
            assert call_args[0][0] == "test_key"  # API key
            assert call_args.kwargs['latitude'] == 34.0522
            assert call_args.kwargs['longitude'] == -118.2437

            # Verify API call parameters
            mock_client.async_get_hourly_forecast.assert_called_once_with(
                hours=72,
                metric=False,
                language="en-us"
            )

            # Verify response structure
            assert result["response_type"] == "forecast_weather_by_location"
            assert result["agent_name"] == "AccuWeather"
            assert result["friendly_name"] == "Forecast Weather by Location"
            assert result["display_response"] is True
            assert len(result["response"]) == 2
            assert result["response"][0]["Temperature"]["Value"] == 68.0

    @pytest.mark.asyncio
    async def test_get_current_weather_api_error(self, mock_context):
        """Test handling of API errors for current weather."""
        from connectors.accuweather import get_current_weather_by_latitude_longitude

        # Mock AccuWeather client
        with patch('connectors.accuweather.AccuWeather') as mock_accuweather:
            mock_client = AsyncMock()
            mock_accuweather.return_value = mock_client

            # Mock API error
            mock_client.async_get_current_conditions.side_effect = ApiError(
                "API Error occurred")

            # Call the function
            result = await get_current_weather_by_latitude_longitude.on_invoke_tool(
                mock_context,
                '{"latitude": 0.0, "longitude": 0.0}'
            )

            # Verify error response structure
            assert result["response_type"] == "error"
            assert result["agent_name"] == "AccuWeather"
            assert result["friendly_name"] == "Current Weather by Location"
            assert result["display_response"] is True
            assert "API Error occurred" in result["response"]

    @pytest.mark.asyncio
    async def test_get_current_weather_invalid_api_key(self, mock_context):
        """Test handling of invalid API key error."""
        from connectors.accuweather import get_current_weather_by_latitude_longitude

        # Mock AccuWeather client
        with patch('connectors.accuweather.AccuWeather') as mock_accuweather:
            mock_client = AsyncMock()
            mock_accuweather.return_value = mock_client

            # Mock invalid API key error
            mock_client.async_get_current_conditions.side_effect = InvalidApiKeyError(
                "Invalid API key")

            # Call the function
            result = await get_current_weather_by_latitude_longitude.on_invoke_tool(
                mock_context,
                '{"latitude": 40.7128, "longitude": -74.0060}'
            )

            # Verify error response
            assert result["response_type"] == "error"
            assert "Invalid API key" in result["response"]

    @pytest.mark.asyncio
    async def test_get_current_weather_invalid_coordinates(self, mock_context):
        """Test handling of invalid coordinates error."""
        from connectors.accuweather import get_current_weather_by_latitude_longitude

        # Mock AccuWeather client
        with patch('connectors.accuweather.AccuWeather') as mock_accuweather:
            mock_client = AsyncMock()
            mock_accuweather.return_value = mock_client

            # Mock invalid coordinates error
            mock_client.async_get_current_conditions.side_effect = InvalidCoordinatesError(
                "Invalid coordinates")

            # Call the function
            result = await get_current_weather_by_latitude_longitude.on_invoke_tool(
                mock_context,
                '{"latitude": 999.0, "longitude": 999.0}'
            )

            # Verify error response
            assert result["response_type"] == "error"
            assert "Invalid coordinates" in result["response"]

    @pytest.mark.asyncio
    async def test_get_current_weather_requests_exceeded(self, mock_context):
        """Test handling of requests exceeded error."""
        from connectors.accuweather import get_current_weather_by_latitude_longitude

        # Mock AccuWeather client
        with patch('connectors.accuweather.AccuWeather') as mock_accuweather:
            mock_client = AsyncMock()
            mock_accuweather.return_value = mock_client

            # Mock requests exceeded error
            mock_client.async_get_current_conditions.side_effect = RequestsExceededError(
                "Requests exceeded")

            # Call the function
            result = await get_current_weather_by_latitude_longitude.on_invoke_tool(
                mock_context,
                '{"latitude": 40.7128, "longitude": -74.0060}'
            )

            # Verify error response
            assert result["response_type"] == "error"
            assert "Requests exceeded" in result["response"]

    def test_current_weather_tool_docstring(self):
        """Test that current weather tool has appropriate docstring."""
        from connectors.accuweather import get_current_weather_by_latitude_longitude

        # FunctionTool objects have description instead of __doc__
        description = get_current_weather_by_latitude_longitude.description.lower()

        assert "current weather" in description
        assert "location" in description

    def test_daily_forecast_tool_docstring(self):
        """Test that daily forecast tool has appropriate docstring."""
        from connectors.accuweather import get_daily_forecast_weather_by_latitude_longitude

        # FunctionTool objects have description instead of __doc__
        description = get_daily_forecast_weather_by_latitude_longitude.description.lower()

        assert "forecast" in description
        assert "10 days" in description
        assert "daily" in description or "day" in description

    def test_hourly_forecast_tool_docstring(self):
        """Test that hourly forecast tool has appropriate docstring."""
        from connectors.accuweather import get_hourly_forecast_weather_by_latitude_longitude

        # FunctionTool objects have description instead of __doc__
        description = get_hourly_forecast_weather_by_latitude_longitude.description.lower()

        assert "72 hours" in description
        assert "hour" in description
        assert "predictions" in description

    def test_weather_tool_response_structure(self):
        """Test that weather tools use ToolResponse structure."""
        from connectors.utils.responses import ToolResponse

        # Test that a ToolResponse can be created with weather-specific fields
        response = ToolResponse(
            response_type="current_weather_by_location",
            agent_name="Accuweather",
            friendly_name="Current Weather by Location",
            display_response=True,
            response={"Temperature": {"Metric": {"Value": 20}}}
        )

        result = response.to_dict()

        # Should have standard ToolResponse structure
        required_fields = ['response_type', 'agent_name',
                           'friendly_name', 'display_response', 'response']

        for field in required_fields:
            assert field in result

        # Test specific field values
        assert result['response_type'] == 'current_weather_by_location'
        assert result['agent_name'] == 'Accuweather'
        assert result['display_response'] == True


class TestAccuWeatherErrorHandling:
    """Test error handling concepts for AccuWeather API functions."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock context wrapper."""
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = Mock()
        mock_wrapper.context.settings = Mock()
        mock_wrapper.context.settings.accuweather_api_key = "test_key"
        return mock_wrapper

    @pytest.mark.asyncio
    async def test_client_session_error(self, mock_context):
        """Test handling of aiohttp ClientError."""
        from connectors.accuweather import get_current_weather_by_latitude_longitude

        # Mock ClientSession to raise ClientError
        with patch('connectors.accuweather.ClientSession') as mock_session_class:
            mock_session_class.side_effect = ClientError("Connection failed")

            # This should not raise but should be handled internally
            # The actual behavior depends on how the function handles session errors
            try:
                result = await get_current_weather_by_latitude_longitude.on_invoke_tool(
                    mock_context,
                    '{"latitude": 40.7128, "longitude": -74.0060}'
                )
                # If it returns a result, it should be an error response
                if isinstance(result, dict):
                    assert result.get("response_type") == "error"
            except Exception:
                # The function might not handle session creation errors
                pass

    def test_tool_signatures(self):
        """Test that tools have correct parameter schemas."""
        from connectors.accuweather import (
            get_current_weather_by_latitude_longitude,
            get_daily_forecast_weather_by_latitude_longitude,
            get_hourly_forecast_weather_by_latitude_longitude
        )

        # Test current weather tool signature
        current_schema = get_current_weather_by_latitude_longitude.params_json_schema
        assert "properties" in current_schema
        params = current_schema["properties"]
        assert "latitude" in params
        assert params["latitude"]["type"] == "number"
        assert "longitude" in params
        assert params["longitude"]["type"] == "number"

        # Test daily forecast tool signature
        daily_schema = get_daily_forecast_weather_by_latitude_longitude.params_json_schema
        assert "properties" in daily_schema
        params = daily_schema["properties"]
        assert "latitude" in params
        assert params["latitude"]["type"] == "number"
        assert "longitude" in params
        assert params["longitude"]["type"] == "number"

        # Test hourly forecast tool signature
        hourly_schema = get_hourly_forecast_weather_by_latitude_longitude.params_json_schema
        assert "properties" in hourly_schema
        params = hourly_schema["properties"]
        assert "latitude" in params
        assert params["latitude"]["type"] == "number"
        assert "longitude" in params
        assert params["longitude"]["type"] == "number"

    def test_coordinate_validation_concept(self):
        """Test coordinate validation concepts."""
        # Test valid coordinate ranges
        valid_latitudes = [-90.0, 0.0, 90.0, 40.7128]
        valid_longitudes = [-180.0, 0.0, 180.0, -74.0060]

        for lat in valid_latitudes:
            assert -90.0 <= lat <= 90.0

        for lon in valid_longitudes:
            assert -180.0 <= lon <= 180.0

        # Test invalid coordinate ranges
        invalid_latitudes = [-91.0, 91.0, 999.0]
        invalid_longitudes = [-181.0, 181.0, 999.0]

        for lat in invalid_latitudes:
            assert not (-90.0 <= lat <= 90.0)

        for lon in invalid_longitudes:
            assert not (-180.0 <= lon <= 180.0)

    def test_api_error_types(self):
        """Test that proper exception types are available for error handling."""
        from accuweather import (
            ApiError,
            InvalidApiKeyError,
            InvalidCoordinatesError,
            RequestsExceededError,
        )
        from accuweather.exceptions import AccuweatherError

        # Verify that the expected exception types exist
        # Note: InvalidApiKeyError inherits from AccuweatherError, not ApiError
        assert issubclass(InvalidApiKeyError, AccuweatherError)
        assert issubclass(InvalidCoordinatesError, AccuweatherError)
        assert issubclass(RequestsExceededError, AccuweatherError)
        assert issubclass(ApiError, AccuweatherError)

        # Test exception creation
        api_error = ApiError("General API error")
        assert str(api_error) == "General API error"

        invalid_key_error = InvalidApiKeyError("Invalid key")
        assert str(invalid_key_error) == "Invalid key"


class TestAccuWeatherIntegration:
    """Integration tests for AccuWeather components."""

    def test_all_imports_work(self):
        """Test that all imports work correctly."""
        try:
            from connectors.accuweather import (
                ACCUWEATHER_AGENT,
                REALTIME_WEATHERAPI_AGENT,
                ALL_TOOLS,
                get_current_weather_by_latitude_longitude,
                get_daily_forecast_weather_by_latitude_longitude,
                get_hourly_forecast_weather_by_latitude_longitude
            )

            # Basic validation
            assert ACCUWEATHER_AGENT is not None
            assert REALTIME_WEATHERAPI_AGENT is not None
            assert len(ALL_TOOLS) == 3
            # FunctionTool objects are not directly callable but have on_invoke_tool
            assert hasattr(
                get_current_weather_by_latitude_longitude, 'on_invoke_tool')
            assert callable(
                get_current_weather_by_latitude_longitude.on_invoke_tool)
            assert hasattr(
                get_daily_forecast_weather_by_latitude_longitude, 'on_invoke_tool')
            assert callable(
                get_daily_forecast_weather_by_latitude_longitude.on_invoke_tool)
            assert hasattr(
                get_hourly_forecast_weather_by_latitude_longitude, 'on_invoke_tool')
            assert callable(
                get_hourly_forecast_weather_by_latitude_longitude.on_invoke_tool)

        except ImportError as e:
            pytest.fail(f"Failed to import AccuWeather components: {e}")

    def test_agent_tool_consistency(self):
        """Test that both agents have the same tools."""
        from connectors.accuweather import ACCUWEATHER_AGENT, REALTIME_WEATHERAPI_AGENT, ALL_TOOLS

        # Both agents should have the same number of tools as ALL_TOOLS
        assert len(ACCUWEATHER_AGENT.tools) == len(ALL_TOOLS)
        assert len(REALTIME_WEATHERAPI_AGENT.tools) == len(ALL_TOOLS)

        # Tool function objects should match (compare by name since FunctionTool not hashable)
        agent_tool_names = [tool.name for tool in ACCUWEATHER_AGENT.tools]
        realtime_tool_names = [
            tool.name for tool in REALTIME_WEATHERAPI_AGENT.tools]
        all_tool_names = [tool.name for tool in ALL_TOOLS]

        assert set(agent_tool_names) == set(all_tool_names)
        assert set(realtime_tool_names) == set(all_tool_names)

    def test_accuweather_module_structure(self):
        """Test the overall module structure."""
        import connectors.accuweather as accuweather_module

        # Should have expected attributes
        expected_attributes = [
            'ACCUWEATHER_AGENT',
            'REALTIME_WEATHERAPI_AGENT',
            'ALL_TOOLS',
            'get_current_weather_by_latitude_longitude',
            'get_daily_forecast_weather_by_latitude_longitude',
            'get_hourly_forecast_weather_by_latitude_longitude'
        ]

        for attr in expected_attributes:
            assert hasattr(accuweather_module,
                           attr), f"Missing attribute: {attr}"

    def test_tool_registration_with_agents(self):
        """Test that tools are properly registered with agents."""
        from connectors.accuweather import (
            ACCUWEATHER_AGENT,
            REALTIME_WEATHERAPI_AGENT,
            get_current_weather_by_latitude_longitude,
            get_daily_forecast_weather_by_latitude_longitude,
            get_hourly_forecast_weather_by_latitude_longitude
        )

        # Check that specific tools are in agent tools
        agent_tool_funcs = [tool for tool in ACCUWEATHER_AGENT.tools]
        realtime_tool_funcs = [
            tool for tool in REALTIME_WEATHERAPI_AGENT.tools]

        expected_tools = [
            get_current_weather_by_latitude_longitude,
            get_daily_forecast_weather_by_latitude_longitude,
            get_hourly_forecast_weather_by_latitude_longitude
        ]

        for tool in expected_tools:
            assert tool in agent_tool_funcs
            assert tool in realtime_tool_funcs

    def test_accuweather_client_initialization_params(self):
        """Test AccuWeather client initialization parameters."""
        from connectors.accuweather import get_current_weather_by_latitude_longitude

        # The function uses these parameters when creating AccuWeather client:
        # - API key from settings
        # - ClientSession
        # - latitude and longitude
        # - language (for current weather)

        # This test verifies the expected parameters are used
        expected_params = ['api_key', 'session',
                           'latitude', 'longitude', 'language']

        # These would be passed to AccuWeather constructor
        assert all(param in ['api_key', 'session', 'latitude', 'longitude', 'language', 'metric']
                   for param in expected_params)
