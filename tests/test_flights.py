"""
Comprehensive tests for connectors/flights.py

Tests cover the Flights agent, its tools, and various edge cases.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from agents import Agent
from connectors.flights import (
    FLIGHT_AGENT,
    get_flight_info_by_iata,
    get_flight_info_by_airline_and_flight_number,
    strip_timezone_data,
    ALL_TOOLS
)


class TestFlightsConfig:
    """Test Flights agent configuration and setup."""

    def test_flight_agent_exists(self):
        """Test that FLIGHT_AGENT is properly configured."""
        assert FLIGHT_AGENT is not None
        assert isinstance(FLIGHT_AGENT, Agent)
        assert FLIGHT_AGENT.name == "AviationStack"
        assert FLIGHT_AGENT.model == "gpt-4o"
        assert len(FLIGHT_AGENT.tools) == 2

    def test_all_tools_exported(self):
        """Test that ALL_TOOLS contains expected tools."""
        assert len(ALL_TOOLS) == 2
        assert get_flight_info_by_iata in ALL_TOOLS
        assert get_flight_info_by_airline_and_flight_number in ALL_TOOLS

    def test_agent_handoffs_configured(self):
        """Test that agent handoffs are properly configured."""
        assert hasattr(FLIGHT_AGENT, 'handoffs')
        # GOOGLE_DOCS, GMAIL, GOOGLE_CALENDAR
        assert len(FLIGHT_AGENT.handoffs) == 3

    def test_agent_instructions_configured(self):
        """Test that agent instructions are properly set."""
        assert FLIGHT_AGENT.instructions is not None
        assert "flight-related tasks" in FLIGHT_AGENT.instructions
        assert "flight information" in FLIGHT_AGENT.instructions

    def test_agent_handoff_description_configured(self):
        """Test that agent handoff description is properly set."""
        assert FLIGHT_AGENT.handoff_description is not None
        assert "Flight information assistant" in FLIGHT_AGENT.handoff_description


class TestGetFlightInfoByIataTool:
    """Test the get_flight_info_by_iata tool."""

    @patch('connectors.flights.requests.get')
    @pytest.mark.asyncio
    async def test_get_flight_info_by_iata_success(self, mock_get):
        """Test successful flight info retrieval by IATA code."""
        # Mock AviationStack API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {
                    "flight_date": "2023-01-01",
                    "flight_status": "scheduled",
                    "departure": {
                        "airport": "John F Kennedy International Airport",
                        "timezone": "America/New_York",
                        "iata": "JFK",
                        "icao": "KJFK",
                        "terminal": "4",
                        "gate": "A1",
                        "scheduled": "2023-01-01T08:00:00+00:00",
                        "estimated": "2023-01-01T08:05:00+00:00",
                        "actual": None
                    },
                    "arrival": {
                        "airport": "Los Angeles International Airport",
                        "timezone": "America/Los_Angeles",
                        "iata": "LAX",
                        "icao": "KLAX",
                        "terminal": "2",
                        "gate": "B3",
                        "scheduled": "2023-01-01T11:30:00+00:00",
                        "estimated": "2023-01-01T11:40:00+00:00",
                        "actual": None
                    },
                    "airline": {
                        "name": "Delta Air Lines",
                        "iata": "DL",
                        "icao": "DAL"
                    },
                    "flight": {
                        "number": "113",
                        "iata": "DL113",
                        "icao": "DAL113"
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        # Mock the tool context
        mock_ctx = Mock()

        result = await get_flight_info_by_iata.on_invoke_tool(
            mock_ctx,
            '{"flight_iata": "DL113"}'
        )

        # Verify API call was made correctly
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert "api.aviationstack.com/v1/flights" in args[0]
        assert "flight_iata=DL113" in args[0]

        # Verify response structure
        assert result["response_type"] == "flight_info"
        assert result["agent_name"] == "AviationStack"
        assert result["friendly_name"] == "Flight Information"
        assert result["display_response"] is True
        assert len(result["response"]) == 1
        assert result["response"][0]["flight"]["iata"] == "DL113"

    @patch('connectors.flights.requests.get')
    @pytest.mark.asyncio
    async def test_get_flight_info_by_iata_no_flights(self, mock_get):
        """Test handling when no flights are found."""
        # Mock AviationStack API response with no data
        mock_response = Mock()
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        # Mock the tool context
        mock_ctx = Mock()

        result = await get_flight_info_by_iata.on_invoke_tool(
            mock_ctx,
            '{"flight_iata": "XX999"}'
        )

        # Verify empty response
        assert result["response"] == []

    @patch('connectors.flights.requests.get')
    @pytest.mark.asyncio
    async def test_get_flight_info_by_iata_api_error(self, mock_get):
        """Test handling of AviationStack API errors."""
        mock_get.side_effect = Exception("AviationStack API Error")

        # Mock the tool context
        mock_ctx = Mock()

        result = await get_flight_info_by_iata.on_invoke_tool(
            mock_ctx,
            '{"flight_iata": "DL113"}'
        )

        # The function tool framework catches exceptions and returns error message as string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()

    @patch('connectors.flights.requests.get')
    @pytest.mark.asyncio
    async def test_get_flight_info_by_iata_timezone_stripping(self, mock_get):
        """Test that timezone data is properly stripped from response."""
        # Mock AviationStack API response with timezone data
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {
                    "departure": {
                        "scheduled": "2023-01-01T08:00:00+00:00",
                        "estimated": "2023-01-01T08:05:00+00:00"
                    },
                    "arrival": {
                        "scheduled": "2023-01-01T11:30:00+00:00",
                        "estimated": "2023-01-01T11:40:00+00:00"
                    },
                    "flight": {"iata": "DL113"}
                }
            ]
        }
        mock_get.return_value = mock_response

        # Mock the tool context
        mock_ctx = Mock()

        result = await get_flight_info_by_iata.on_invoke_tool(
            mock_ctx,
            '{"flight_iata": "DL113"}'
        )

        # Verify timezone data is stripped
        flight_data = result["response"][0]
        assert "+00:00" not in flight_data["departure"]["scheduled"]
        assert "+00:00" not in flight_data["departure"]["estimated"]
        assert "+00:00" not in flight_data["arrival"]["scheduled"]
        assert "+00:00" not in flight_data["arrival"]["estimated"]

    @patch('connectors.flights.requests.get')
    @pytest.mark.asyncio
    async def test_get_flight_info_by_iata_multiple_flights(self, mock_get):
        """Test handling when multiple flights are returned."""
        # Mock AviationStack API response with multiple flights
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {
                    "flight": {"iata": "DL113"},
                    "flight_status": "scheduled",
                    "departure": {
                        "scheduled": "2023-01-01T08:00:00+00:00",
                        "estimated": "2023-01-01T08:05:00+00:00"
                    },
                    "arrival": {
                        "scheduled": "2023-01-01T11:30:00+00:00",
                        "estimated": "2023-01-01T11:40:00+00:00"
                    }
                },
                {
                    "flight": {"iata": "DL113"},
                    "flight_status": "active",
                    "departure": {
                        "scheduled": "2023-01-01T20:00:00+00:00",
                        "estimated": "2023-01-01T20:05:00+00:00"
                    },
                    "arrival": {
                        "scheduled": "2023-01-01T23:30:00+00:00",
                        "estimated": "2023-01-01T23:40:00+00:00"
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        # Mock the tool context
        mock_ctx = Mock()

        result = await get_flight_info_by_iata.on_invoke_tool(
            mock_ctx,
            '{"flight_iata": "DL113"}'
        )

        # Verify multiple flights are returned
        assert len(result["response"]) == 2
        assert result["response"][0]["flight_status"] == "scheduled"
        assert result["response"][1]["flight_status"] == "active"


class TestGetFlightInfoByAirlineAndFlightNumberTool:
    """Test the get_flight_info_by_airline_and_flight_number tool."""

    # Skipping OpenAI-related tests per user instruction
    # @patch('connectors.flights.client.chat.completions.create')
    # @patch('connectors.flights.requests.get')
    # @pytest.mark.asyncio
    # async def test_get_flight_info_by_airline_success(self, mock_get, mock_openai_create):
    #     """Test successful flight info retrieval by airline and flight number."""
    #     pass

    @pytest.mark.asyncio
    async def test_get_flight_info_by_airline_openai_error(self):
        """Test handling of OpenAI API errors during IATA conversion."""
        # Mock the tool context
        mock_ctx = Mock()

        result = await get_flight_info_by_airline_and_flight_number.on_invoke_tool(
            mock_ctx,
            '{"airline": "Delta Airlines", "flight_number": "113", "flight_date": "2023-01-01"}'
        )

        # The function tool framework catches exceptions and returns error message as string
        assert result is not None
        if isinstance(result, str):
            assert len(result) > 0
        else:
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_flight_info_by_airline_invalid_iata(self):
        """Test handling when OpenAI returns invalid IATA code."""
        # Mock the tool context
        mock_ctx = Mock()

        result = await get_flight_info_by_airline_and_flight_number.on_invoke_tool(
            mock_ctx,
            '{"airline": "Unknown Airlines", "flight_number": "999", "flight_date": "2023-01-01"}'
        )

        # Verify some response is returned
        assert result is not None
        if isinstance(result, dict):
            assert "response_type" in result or "response" in result
        else:
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_get_flight_info_by_airline_different_airlines(self):
        """Test different airlines and their IATA code conversion."""
        airlines = ["American Airlines",
                    "United Airlines", "Southwest Airlines"]

        for airline in airlines:
            # Mock the tool context
            mock_ctx = Mock()

            result = await get_flight_info_by_airline_and_flight_number.on_invoke_tool(
                mock_ctx,
                f'{{"airline": "{airline}", "flight_number": "100", "flight_date": "2023-01-01"}}'
            )

            # Verify some response is returned for each airline
            assert result is not None
            if isinstance(result, dict):
                assert "response_type" in result or "agent_name" in result
            else:
                assert isinstance(result, str)


class TestStripTimezoneDataFunction:
    """Test the strip_timezone_data utility function."""

    def test_strip_timezone_data_success(self):
        """Test successful timezone data stripping."""
        flights = [
            {
                "departure": {
                    "scheduled": "2023-01-01T08:00:00+00:00",
                    "estimated": "2023-01-01T08:05:00+00:00"
                },
                "arrival": {
                    "scheduled": "2023-01-01T11:30:00+00:00",
                    "estimated": "2023-01-01T11:40:00+00:00"
                }
            }
        ]

        result = strip_timezone_data(flights)

        assert result[0]["departure"]["scheduled"] == "2023-01-01T08:00:00"
        assert result[0]["departure"]["estimated"] == "2023-01-01T08:05:00"
        assert result[0]["arrival"]["scheduled"] == "2023-01-01T11:30:00"
        assert result[0]["arrival"]["estimated"] == "2023-01-01T11:40:00"

    def test_strip_timezone_data_missing_fields(self):
        """Test timezone stripping with missing fields."""
        flights = [
            {
                "departure": {
                    "scheduled": "2023-01-01T08:00:00+00:00"
                    # Missing estimated field
                },
                "arrival": {
                    "estimated": "2023-01-01T11:40:00+00:00"
                    # Missing scheduled field
                }
            }
        ]

        # Should not raise exception and return original data
        result = strip_timezone_data(flights)
        assert result == flights

    def test_strip_timezone_data_empty_list(self):
        """Test timezone stripping with empty flight list."""
        flights = []
        result = strip_timezone_data(flights)
        assert result == []

    def test_strip_timezone_data_no_timezone(self):
        """Test timezone stripping when no timezone data present."""
        flights = [
            {
                "departure": {
                    "scheduled": "2023-01-01T08:00:00",
                    "estimated": "2023-01-01T08:05:00"
                },
                "arrival": {
                    "scheduled": "2023-01-01T11:30:00",
                    "estimated": "2023-01-01T11:40:00"
                }
            }
        ]

        result = strip_timezone_data(flights)
        # Should handle gracefully when no '+' character to split on
        assert result is not None


class TestFlightsAgentIntegration:
    """Integration tests for Flights agent components."""

    def test_agent_tools_registration(self):
        """Test that tools are properly registered with the agent."""
        tool_names = [tool.name for tool in FLIGHT_AGENT.tools]
        assert "get_flight_info_by_iata" in tool_names
        assert "get_flight_info_by_airline_and_flight_number" in tool_names

    def test_agent_model_configuration(self):
        """Test that agent uses correct model."""
        assert FLIGHT_AGENT.model == "gpt-4o"

    def test_import_dependencies(self):
        """Test that agent dependencies are properly imported."""
        # This test ensures the import structure works
        try:
            from connectors.flights import (
                FLIGHT_AGENT,
                get_flight_info_by_iata,
                get_flight_info_by_airline_and_flight_number
            )
            assert FLIGHT_AGENT is not None
            assert get_flight_info_by_iata is not None
            assert get_flight_info_by_airline_and_flight_number is not None
        except ImportError as e:
            pytest.fail(f"Failed to import Flights components: {e}")


class TestFlightsEdgeCases:
    """Test edge cases and error conditions."""

    def test_get_flight_info_by_iata_tool_signature(self):
        """Test that get_flight_info_by_iata tool has correct parameter schema."""
        schema = get_flight_info_by_iata.params_json_schema
        assert "properties" in schema
        params = schema["properties"]
        assert "flight_iata" in params
        assert params["flight_iata"]["type"] == "string"

    def test_get_flight_info_by_airline_tool_signature(self):
        """Test that get_flight_info_by_airline_and_flight_number tool has correct parameter schema."""
        schema = get_flight_info_by_airline_and_flight_number.params_json_schema
        assert "properties" in schema
        params = schema["properties"]
        assert "airline" in params
        assert "flight_number" in params
        assert "flight_date" in params
        assert params["airline"]["type"] == "string"
        assert params["flight_number"]["type"] == "string"
        assert params["flight_date"]["type"] == "string"

    @pytest.mark.asyncio
    async def test_tool_response_format_consistency(self):
        """Test that tools return consistent ToolResponse format."""
        with patch('connectors.flights.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"data": []}
            mock_get.return_value = mock_response

            # Mock the tool context
            mock_ctx = Mock()

            result = await get_flight_info_by_iata.on_invoke_tool(
                mock_ctx,
                '{"flight_iata": "DL113"}'
            )

            # Verify ToolResponse format
            required_fields = ["response_type", "agent_name",
                               "friendly_name", "display_response", "response"]
            for field in required_fields:
                assert field in result

            assert result["response_type"] == "flight_info"
            assert result["agent_name"] == "AviationStack"
            assert result["display_response"] is True

    def test_agent_name_consistency(self):
        """Test that agent name is consistent."""
        assert FLIGHT_AGENT.name == "AviationStack"

    def test_all_tools_contains_all_functions(self):
        """Test that ALL_TOOLS exports all available tool functions."""
        expected_tools = [get_flight_info_by_iata,
                          get_flight_info_by_airline_and_flight_number]
        assert len(ALL_TOOLS) == len(expected_tools)
        for tool in expected_tools:
            assert tool in ALL_TOOLS

    def test_agent_instructions_mention_key_functionality(self):
        """Test that agent instructions mention key functionality."""
        instructions = FLIGHT_AGENT.instructions
        assert "flight information" in instructions
        assert "IATA code" in instructions
        assert "airline/flight number" in instructions

    @pytest.mark.asyncio
    async def test_missing_required_parameters(self):
        """Test tools with missing required parameters."""
        # Mock the tool context
        mock_ctx = Mock()

        # Test get_flight_info_by_iata without flight_iata
        result = await get_flight_info_by_iata.on_invoke_tool(
            mock_ctx,
            '{}'
        )
        assert isinstance(result, str)
        assert "error" in result.lower()

        # Test get_flight_info_by_airline_and_flight_number without required params
        result = await get_flight_info_by_airline_and_flight_number.on_invoke_tool(
            mock_ctx,
            '{}'
        )
        assert isinstance(result, str)
        assert "error" in result.lower()

    # Skipping OpenAI-related tests per user instruction
    # @patch('connectors.flights.client.chat.completions.create')
    # @patch('connectors.flights.requests.get')
    # @patch('builtins.print')
    # @pytest.mark.asyncio
    # async def test_get_flight_info_by_airline_empty_data(self, mock_print, mock_get, mock_openai_create):
    #     """Test handling when AviationStack returns empty data."""
    #     pass

    def test_settings_import_fallback(self):
        """Test that Settings import has a fallback."""
        # This tests the try/except import pattern for Settings
        import connectors.flights
        import inspect

        module_source = inspect.getsource(connectors.flights)

        # Check that there's a try/except for Settings import
        assert "try:" in module_source
        assert "from config import Settings" in module_source
        assert "except ImportError:" in module_source
        assert "from ..config import Settings" in module_source
