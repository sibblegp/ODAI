"""
Comprehensive tests for connectors/amtrak.py

Tests cover the Amtrak agent, its tools, and various edge cases.
"""

import pytest
from unittest.mock import Mock, patch
from agents import Agent
from connectors.amtrak import (
    AMTRAK_AGENT,
    REALTIME_AMTRAK_AGENT,
    get_amtrak_train_status,
    ALL_TOOLS
)


class TestAmtrakConfig:
    """Test Amtrak agent configuration and setup."""

    def test_amtrak_agent_exists(self):
        """Test that AMTRAK_AGENT is properly configured."""
        assert AMTRAK_AGENT is not None
        assert isinstance(AMTRAK_AGENT, Agent)
        assert AMTRAK_AGENT.name == "Amtrak"
        assert AMTRAK_AGENT.model == "gpt-4o"
        assert len(AMTRAK_AGENT.tools) == 1

    def test_realtime_amtrak_agent_exists(self):
        """Test that REALTIME_AMTRAK_AGENT is properly configured."""
        assert REALTIME_AMTRAK_AGENT is not None
        assert REALTIME_AMTRAK_AGENT.name == "Amtrak"
        assert len(REALTIME_AMTRAK_AGENT.tools) == 1

    def test_all_tools_exported(self):
        """Test that ALL_TOOLS contains expected tools."""
        assert len(ALL_TOOLS) == 1
        assert get_amtrak_train_status in ALL_TOOLS

    def test_agent_instructions_configured(self):
        """Test that agent instructions are properly set."""
        assert AMTRAK_AGENT.instructions is not None
        # Instructions now focus on train tracking
        assert "track" in AMTRAK_AGENT.instructions.lower(
        ) or "train" in AMTRAK_AGENT.instructions.lower()

    def test_agent_handoff_description_configured(self):
        """Test that agent handoff description is properly set."""
        assert AMTRAK_AGENT.handoff_description is not None
        # Handoff description focuses on functionality
        assert "amtrak" in AMTRAK_AGENT.handoff_description.lower(
        ) or "train" in AMTRAK_AGENT.handoff_description.lower()


class TestGetAmtrakTrainStatusTool:
    """Test the get_amtrak_train_status tool."""

    @patch('connectors.amtrak.requests.get')
    @pytest.mark.asyncio
    async def test_get_train_status_success(self, mock_get):
        """Test successful train status retrieval."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "trainNumber": "1234",
            "trainName": "Silver Star",
            "routeName": "New York - Miami",
            "trainState": "Active",
            "lat": 40.7589,
            "lon": -73.9851,
            "heading": 180,
            "velocity": 79,
            "stations": [
                {
                    "stationName": "New York Penn Station",
                    "code": "NYP",
                    "schArr": "2023-01-01T15:15:00",
                    "postArr": "2023-01-01T15:15:00",
                    "status": "Departed"
                }
            ]
        }
        mock_get.return_value = mock_response

        # Mock the tool context
        mock_ctx = Mock()

        result = await get_amtrak_train_status.on_invoke_tool(
            mock_ctx,
            '{"train_number": "1234"}'
        )

        # Verify API call was made correctly
        mock_get.assert_called_once_with(
            "https://api-v3.amtraker.com/v3/trains/1234")

        # Verify response structure
        assert result["response_type"] == "amtrak_train_status"
        assert result["agent_name"] == "Amtrak"
        assert result["friendly_name"] == "Checking the status of train 1234"
        assert result["display_response"] is True
        assert result["response"]["trainNumber"] == "1234"
        assert result["response"]["trainName"] == "Silver Star"

    @patch('connectors.amtrak.requests.get')
    @pytest.mark.asyncio
    async def test_get_train_status_train_not_found(self, mock_get):
        """Test handling when train is not found."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "error": "Train not found",
            "message": "No train found with number 9999"
        }
        mock_get.return_value = mock_response

        # Mock the tool context
        mock_ctx = Mock()

        result = await get_amtrak_train_status.on_invoke_tool(
            mock_ctx,
            '{"train_number": "9999"}'
        )

        # Verify API call was made
        mock_get.assert_called_once_with(
            "https://api-v3.amtraker.com/v3/trains/9999")

        # Verify error response is passed through
        assert result["response_type"] == "amtrak_train_status"
        assert result["response"]["error"] == "Train not found"

    @patch('connectors.amtrak.requests.get')
    @pytest.mark.asyncio
    async def test_get_train_status_api_error(self, mock_get):
        """Test handling of API errors."""
        mock_get.side_effect = Exception("Network error")

        # Mock the tool context
        mock_ctx = Mock()

        result = await get_amtrak_train_status.on_invoke_tool(
            mock_ctx,
            '{"train_number": "1234"}'
        )

        # The function tool framework catches exceptions and returns error message as string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()

    @patch('connectors.amtrak.requests.get')
    @pytest.mark.asyncio
    async def test_get_train_status_delayed_train(self, mock_get):
        """Test handling of delayed train status."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "trainNumber": "2170",
            "trainName": "Pennsylvanian",
            "trainState": "Active",
            "lat": 40.4406,
            "lon": -79.9959,
            "velocity": 0,
            "stations": [
                {
                    "stationName": "Pittsburgh",
                    "code": "PGH",
                    "schArr": "2023-01-01T23:40:00",
                    "postArr": "2023-01-02T00:15:00",
                    "status": "Departed",
                    "delaySeconds": 2100
                }
            ]
        }
        mock_get.return_value = mock_response

        # Mock the tool context
        mock_ctx = Mock()

        result = await get_amtrak_train_status.on_invoke_tool(
            mock_ctx,
            '{"train_number": "2170"}'
        )

        # Verify delayed train data is returned correctly
        assert result["response"]["trainNumber"] == "2170"
        assert result["response"]["stations"][0]["delaySeconds"] == 2100

    @patch('connectors.amtrak.requests.get')
    @pytest.mark.asyncio
    async def test_get_train_status_with_special_characters(self, mock_get):
        """Test train number with special characters or letters."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "trainNumber": "123A",
            "trainName": "Special Train",
            "trainState": "Active"
        }
        mock_get.return_value = mock_response

        # Mock the tool context
        mock_ctx = Mock()

        result = await get_amtrak_train_status.on_invoke_tool(
            mock_ctx,
            '{"train_number": "123A"}'
        )

        # Verify API call with special characters
        mock_get.assert_called_once_with(
            "https://api-v3.amtraker.com/v3/trains/123A")
        assert result["response"]["trainNumber"] == "123A"

    @patch('connectors.amtrak.requests.get')
    @pytest.mark.asyncio
    async def test_get_train_status_empty_train_number(self, mock_get):
        """Test handling of empty train number."""
        mock_response = Mock()
        mock_response.json.return_value = {"error": "Invalid train number"}
        mock_get.return_value = mock_response

        # Mock the tool context
        mock_ctx = Mock()

        result = await get_amtrak_train_status.on_invoke_tool(
            mock_ctx,
            '{"train_number": ""}'
        )

        # Verify API call is still made with empty string
        mock_get.assert_called_once_with(
            "https://api-v3.amtraker.com/v3/trains/")


class TestAmtrakAgentIntegration:
    """Integration tests for Amtrak agent components."""

    def test_agent_tools_registration(self):
        """Test that tools are properly registered with the agent."""
        tool_names = [tool.name for tool in AMTRAK_AGENT.tools]
        assert "get_amtrak_train_status" in tool_names

    def test_agent_model_configuration(self):
        """Test that agent uses correct model."""
        assert AMTRAK_AGENT.model == "gpt-4o"

    def test_realtime_agent_tools_registration(self):
        """Test that realtime agent has same tools as regular agent."""
        regular_tool_names = [tool.name for tool in AMTRAK_AGENT.tools]
        realtime_tool_names = [
            tool.name for tool in REALTIME_AMTRAK_AGENT.tools]
        assert set(regular_tool_names) == set(realtime_tool_names)

    def test_import_dependencies(self):
        """Test that agent dependencies are properly imported."""
        # This test ensures the import structure works
        try:
            from connectors.amtrak import (
                AMTRAK_AGENT,
                get_amtrak_train_status
            )
            assert AMTRAK_AGENT is not None
            assert get_amtrak_train_status is not None
        except ImportError as e:
            pytest.fail(f"Failed to import Amtrak components: {e}")


class TestAmtrakEdgeCases:
    """Test edge cases and error conditions."""

    def test_tool_function_signature(self):
        """Test that tool function has correct parameter schema."""
        schema = get_amtrak_train_status.params_json_schema
        assert "properties" in schema
        params = schema["properties"]
        assert "train_number" in params
        assert params["train_number"]["type"] == "string"

    @pytest.mark.asyncio
    async def test_tool_response_format_consistency(self):
        """Test that tool returns consistent ToolResponse format."""
        with patch('connectors.amtrak.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"trainNumber": "1234"}
            mock_get.return_value = mock_response

            # Mock the tool context
            mock_ctx = Mock()

            result = await get_amtrak_train_status.on_invoke_tool(
                mock_ctx,
                '{"train_number": "1234"}'
            )

            # Verify ToolResponse format
            required_fields = ["response_type", "agent_name",
                               "friendly_name", "display_response", "response"]
            for field in required_fields:
                assert field in result

            assert result["response_type"] == "amtrak_train_status"
            assert result["agent_name"] == "Amtrak"
            assert result["display_response"] is True

    @patch('connectors.amtrak.requests.get')
    @pytest.mark.asyncio
    async def test_get_train_status_json_parse_error(self, mock_get):
        """Test handling when API returns invalid JSON."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        # Mock the tool context
        mock_ctx = Mock()

        result = await get_amtrak_train_status.on_invoke_tool(
            mock_ctx,
            '{"train_number": "1234"}'
        )

        # The function tool framework catches exceptions and returns error message as string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()

    def test_agent_name_consistency(self):
        """Test that agent names are consistent across instances."""
        assert AMTRAK_AGENT.name == REALTIME_AMTRAK_AGENT.name == "Amtrak"

    def test_all_tools_contains_all_functions(self):
        """Test that ALL_TOOLS exports all available tool functions."""
        # Currently there's only one tool, but this test ensures consistency
        expected_tools = [get_amtrak_train_status]
        assert len(ALL_TOOLS) == len(expected_tools)
        for tool in expected_tools:
            assert tool in ALL_TOOLS
