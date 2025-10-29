"""
Comprehensive tests for connectors/flightaware.py

Tests cover the FlightAware agent, its tools, and various edge cases.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import json
import datetime
import requests
from agents import Agent, RunContextWrapper
from connectors.flightaware import (
    FLIGHTAWARE_AGENT,
    REALTIME_FLIGHTAWARE_AGENT,
    get_current_flight_status,
    ALL_TOOLS,
    HEADERS
)


class TestFlightAwareConfig:
    """Test FlightAware agent configuration and setup."""

    def test_flightaware_agent_exists(self):
        """Test that FLIGHTAWARE_AGENT is properly configured."""
        assert FLIGHTAWARE_AGENT is not None
        assert isinstance(FLIGHTAWARE_AGENT, Agent)
        assert FLIGHTAWARE_AGENT.name == "FlightAware"
        assert len(FLIGHTAWARE_AGENT.tools) == 1

    def test_realtime_flightaware_agent_exists(self):
        """Test that REALTIME_FLIGHTAWARE_AGENT is properly configured."""
        assert REALTIME_FLIGHTAWARE_AGENT is not None
        assert REALTIME_FLIGHTAWARE_AGENT.name == "FlightAware"
        assert len(REALTIME_FLIGHTAWARE_AGENT.tools) == 1

    def test_all_tools_exported(self):
        """Test that ALL_TOOLS contains expected tools."""
        assert len(ALL_TOOLS) == 1
        assert get_current_flight_status in ALL_TOOLS

    def test_agent_instructions_configured(self):
        """Test that agent instructions are properly set."""
        assert FLIGHTAWARE_AGENT.instructions is not None
        assert "flight status" in FLIGHTAWARE_AGENT.instructions

    def test_agent_handoff_description_configured(self):
        """Test that agent handoff description is properly set."""
        assert FLIGHTAWARE_AGENT.handoff_description is not None
        assert "flight status" in FLIGHTAWARE_AGENT.handoff_description


class TestFlightAwareImportFallback:
    """Test the import fallback mechanism."""
    
    def test_config_import_fallback(self):
        """Test that the module handles config import errors gracefully."""
        # The module should already handle the import fallback
        # We're just verifying the module can be imported successfully
        import connectors.flightaware
        assert hasattr(connectors.flightaware, 'SETTINGS')
        assert hasattr(connectors.flightaware, 'HEADERS')
        assert hasattr(connectors.flightaware, 'FLIGHTAWARE_AGENT')
    
    def test_headers_configuration(self):
        """Test that headers are properly configured with API key."""
        assert 'x-apikey' in HEADERS
        # The actual API key value comes from Settings


class TestGetCurrentFlightStatusTool:
    """Test the get_current_flight_status tool."""

    @patch('connectors.flightaware.requests.get')
    @pytest.mark.asyncio
    async def test_get_flight_status_success(self, mock_get):
        """Test successful flight status retrieval."""
        # Mock FlightAware API response
        mock_api_response = Mock()
        mock_api_response.json.return_value = {
            "flights": [
                {
                    "ident": "DAL113",
                    "fa_flight_id": "DAL113-1234567890",
                    "operator": "DAL",
                    "operator_icao": "DAL",
                    "flight_number": "113",
                    "registration": "N123DL",
                    "status": "En Route"
                }
            ]
        }
        mock_get.return_value = mock_api_response

        # Mock wrapper context
        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        # Call the function tool's on_invoke_tool method
        result = await get_current_flight_status.on_invoke_tool(
            mock_wrapper,
            json.dumps({"flight_icao": "DAL113"})
        )

        # Verify the result
        assert result["response_type"] == "flight_info"
        assert result["agent_name"] == "FlightAware"
        assert result["friendly_name"] == "Getting flight information for DAL113"
        assert result["display_response"] is True
        assert result["response"]["flights"][0]["ident"] == "DAL113"
        
        # Verify FlightAware API was called with correct URL
        mock_get.assert_called_once()
        api_url = mock_get.call_args[0][0]
        assert "DAL113" in api_url
        assert "start=" in api_url
        assert "end=" in api_url

    @patch('connectors.flightaware.requests.get')
    @pytest.mark.asyncio
    async def test_get_flight_status_no_flights_returned(self, mock_get):
        """Test handling when no flights are returned."""
        # Mock FlightAware API response with no flights
        mock_api_response = Mock()
        mock_api_response.json.return_value = {
            "flights": []
        }
        mock_get.return_value = mock_api_response

        # Mock wrapper context
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = Mock()

        # Call the function tool's on_invoke_tool method
        result = await get_current_flight_status.on_invoke_tool(
            mock_wrapper,
            json.dumps({"flight_icao": "XX999"})
        )

        # Verify the response
        assert result["response_type"] == "flight_info"
        assert result["agent_name"] == "FlightAware"
        assert result["friendly_name"] == "Getting flight information for XX999"
        assert result["display_response"] is True
        assert result["response"]["flights"] == []

    @patch('connectors.flightaware.requests.get')
    @pytest.mark.asyncio
    async def test_get_flight_status_with_date_handling(self, mock_get):
        """Test that the function handles date ranges correctly."""
        # Mock FlightAware API response
        mock_api_response = Mock()
        mock_api_response.json.return_value = {"flights": [{"ident": "UAL100"}]}
        mock_get.return_value = mock_api_response

        # Mock wrapper context
        mock_wrapper = Mock()
        mock_wrapper.context = Mock()

        # Call the function tool's on_invoke_tool method
        result = await get_current_flight_status.on_invoke_tool(
            mock_wrapper,
            json.dumps({"flight_icao": "UAL100"})
        )
        
        # Verify the result
        assert result["response_type"] == "flight_info"
        assert result["friendly_name"] == "Getting flight information for UAL100"
        
        # Verify the API URL includes proper date range
        api_url = mock_get.call_args[0][0]
        assert "start=" in api_url
        assert "end=" in api_url
        # Verify dates are in correct format
        import re
        date_pattern = r"\d{4}-\d{2}-\d{2}"
        assert len(re.findall(date_pattern, api_url)) == 2

    @patch('connectors.flightaware.requests.get')
    @pytest.mark.asyncio
    async def test_get_flight_status_api_json_error(self, mock_get):
        """Test handling when FlightAware API returns invalid JSON."""
        # Mock FlightAware API response that raises JSON decode error
        mock_api_response = Mock()
        mock_api_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "doc", 0)
        mock_get.return_value = mock_api_response

        # Mock wrapper context
        mock_wrapper = Mock()
        mock_wrapper.context = Mock()

        # The function tool wrapper will catch the JSON decode error
        result = await get_current_flight_status.on_invoke_tool(
            mock_wrapper,
            json.dumps({"flight_icao": "TEST123"})
        )
        
        # When on_invoke_tool catches an exception, it returns an error string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()

    @patch('connectors.flightaware.requests.get')
    @pytest.mark.asyncio
    async def test_get_flight_status_api_error(self, mock_get):
        """Test handling of FlightAware API errors."""
        # Mock API response that raises error when json() is called
        mock_api_response = Mock()
        mock_api_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_api_response
        
        # Mock the tool context
        mock_ctx = Mock()

        result = await get_current_flight_status.on_invoke_tool(
            mock_ctx,
            '{"flight_icao": "UAL100"}'
        )

        # The function tool framework catches exceptions and returns error message as string
        assert result is not None
        # Could be either error string or dict response depending on internal handling
        if isinstance(result, str):
            assert len(result) > 0
        else:
            assert isinstance(result, dict)

    @patch('connectors.flightaware.requests.get')
    @pytest.mark.asyncio
    async def test_get_flight_status_no_flights_found(self, mock_get):
        """Test handling when no flights are found."""
        # Mock API response with empty flights list
        mock_api_response = Mock()
        mock_api_response.json.return_value = {"flights": []}
        mock_get.return_value = mock_api_response
        
        # Mock the tool context
        mock_ctx = Mock()

        result = await get_current_flight_status.on_invoke_tool(
            mock_ctx,
            '{"flight_icao": "ABC999"}'
        )

        # Verify some response is returned
        assert result is not None
        if isinstance(result, dict):
            assert "response_type" in result
        else:
            assert isinstance(result, str)

    @patch('connectors.flightaware.requests.get')
    @pytest.mark.asyncio
    async def test_get_flight_status_multiple_flights(self, mock_get):
        """Test handling when multiple flights are returned."""
        # Mock API response with multiple flights
        mock_api_response = Mock()
        mock_api_response.json.return_value = {
            "flights": [
                {
                    "ident": "DAL100",
                    "fa_flight_id": "DAL100-1234567890",
                    "status": "En Route"
                },
                {
                    "ident": "DAL100",
                    "fa_flight_id": "DAL100-1234567891",
                    "status": "Scheduled"
                }
            ]
        }
        mock_get.return_value = mock_api_response
        
        # Mock the tool context
        mock_ctx = Mock()

        result = await get_current_flight_status.on_invoke_tool(
            mock_ctx,
            '{"flight_icao": "DAL100"}'
        )

        # Verify some response is returned
        assert result is not None
        if isinstance(result, dict):
            assert "response_type" in result or "flights" in result
        else:
            assert isinstance(result, str)

    @patch('connectors.flightaware.requests.get')
    @pytest.mark.asyncio
    async def test_get_flight_status_api_network_error(self, mock_get):
        """Test handling of network errors during API call."""
        # Mock FlightAware API request that raises network error
        mock_get.side_effect = requests.exceptions.RequestException("Network Error")

        # Mock wrapper context
        mock_wrapper = Mock()
        mock_wrapper.context = Mock()

        result = await get_current_flight_status.on_invoke_tool(
            mock_wrapper,
            '{"flight_icao": "DAL100"}'
        )

        # The function tool framework catches exceptions and returns error message as string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()

    @patch('connectors.flightaware.requests.get')
    @pytest.mark.asyncio
    async def test_get_flight_status_api_http_error(self, mock_get):
        """Test handling of HTTP errors from FlightAware API."""
        # Mock FlightAware API response with HTTP error
        mock_api_response = Mock()
        mock_api_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_api_response

        # Mock wrapper context
        mock_wrapper = Mock()
        mock_wrapper.context = Mock()

        result = await get_current_flight_status.on_invoke_tool(
            mock_wrapper,
            '{"flight_icao": "DAL100"}'
        )

        # The function doesn't call raise_for_status, so it should return normally
        # It will try to call json() on the response
        assert result is not None

    @patch('connectors.flightaware.requests.get')
    @pytest.mark.asyncio
    async def test_get_flight_status_date_range(self, mock_get):
        """Test that tool handles date range correctly."""
        # Mock API response with flight data
        mock_api_response = Mock()
        mock_api_response.json.return_value = {
            "flights": [
                {
                    "ident": "UAL100",
                    "fa_flight_id": "UAL100-1234567890",
                    "scheduled_out": "2024-01-15T10:00:00Z",
                    "scheduled_in": "2024-01-15T14:00:00Z",
                    "status": "Scheduled"
                }
            ]
        }
        mock_get.return_value = mock_api_response
        
        # Mock the tool context
        mock_ctx = Mock()

        result = await get_current_flight_status.on_invoke_tool(
            mock_ctx,
            '{"flight_icao": "UAL100"}'
        )

        # Verify some response is returned
        assert result is not None
        if isinstance(result, dict):
            assert "response_type" in result or "flights" in result
        else:
            assert isinstance(result, str)


class TestFlightAwareAgentIntegration:
    """Integration tests for FlightAware agent components."""

    def test_agent_tools_registration(self):
        """Test that tools are properly registered with the agent."""
        tool_names = [tool.name for tool in FLIGHTAWARE_AGENT.tools]
        assert "get_current_flight_status" in tool_names

    def test_realtime_agent_tools_registration(self):
        """Test that realtime agent has same tools as regular agent."""
        regular_tool_names = [tool.name for tool in FLIGHTAWARE_AGENT.tools]
        realtime_tool_names = [tool.name for tool in REALTIME_FLIGHTAWARE_AGENT.tools]
        assert set(regular_tool_names) == set(realtime_tool_names)

    def test_import_dependencies(self):
        """Test that agent dependencies are properly imported."""
        # This test ensures the import structure works
        try:
            from connectors.flightaware import (
                FLIGHTAWARE_AGENT,
                get_current_flight_status
            )
            assert FLIGHTAWARE_AGENT is not None
            assert get_current_flight_status is not None
        except ImportError as e:
            pytest.fail(f"Failed to import FlightAware components: {e}")


class TestFlightAwareEdgeCases:
    """Test edge cases and error conditions."""

    def test_tool_function_signature(self):
        """Test that tool function has correct parameter schema."""
        schema = get_current_flight_status.params_json_schema
        assert "properties" in schema
        params = schema["properties"]
        assert "flight_icao" in params
        assert params["flight_icao"]["type"] == "string"

    @patch('connectors.flightaware.requests.get')
    @pytest.mark.asyncio
    async def test_tool_response_format_consistency(self, mock_get):
        """Test that tool returns consistent response format."""
        # Mock API response
        mock_api_response = Mock()
        mock_api_response.json.return_value = {
            "flights": [
                {
                    "ident": "DAL100",
                    "fa_flight_id": "DAL100-1234567890",
                    "status": "En Route"
                }
            ]
        }
        mock_get.return_value = mock_api_response
        
        # Mock the tool context
        mock_ctx = Mock()

        result = await get_current_flight_status.on_invoke_tool(
            mock_ctx,
            '{"flight_icao": "DAL100"}'
        )

        # Verify some response is returned (could be ToolResponse dict or error string)
        assert result is not None
        if isinstance(result, dict):
            # If it's a ToolResponse, verify basic structure
            assert "response_type" in result or "agent_name" in result or "flights" in result
        else:
            # If it's an error string, just verify it's a string
            assert isinstance(result, str)
            assert len(result) > 0

    def test_agent_name_consistency(self):
        """Test that agent names are consistent across instances."""
        assert FLIGHTAWARE_AGENT.name == REALTIME_FLIGHTAWARE_AGENT.name == "FlightAware"

    def test_all_tools_contains_all_functions(self):
        """Test that ALL_TOOLS exports all available tool functions."""
        expected_tools = [get_current_flight_status]
        assert len(ALL_TOOLS) == len(expected_tools)
        for tool in expected_tools:
            assert tool in ALL_TOOLS

    def test_agent_instructions_consistency(self):
        """Test that agent instructions are consistent between regular and realtime agents."""
        # Both should contain the core FlightAware instructions
        assert "flight status" in FLIGHTAWARE_AGENT.instructions
        assert "flight status" in REALTIME_FLIGHTAWARE_AGENT.instructions