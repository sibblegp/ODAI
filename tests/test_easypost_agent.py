"""
Comprehensive tests for connectors/easypost_agent.py

Tests cover the EasyPost agent, its tools, and various edge cases.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from agents import Agent
from connectors.easypost_agent import (
    EASYPOST_AGENT,
    get_tracking_info_with_easypost,
    get_all_packages_with_easypost,
    ALL_TOOLS
)


class TestEasyPostConfig:
    """Test EasyPost agent configuration and setup."""

    def test_easypost_agent_exists(self):
        """Test that EASYPOST_AGENT is properly configured."""
        assert EASYPOST_AGENT is not None
        assert isinstance(EASYPOST_AGENT, Agent)
        assert EASYPOST_AGENT.name == "EasyPost"
        assert EASYPOST_AGENT.model == "gpt-4o"
        assert len(EASYPOST_AGENT.tools) == 2

    def test_all_tools_exported(self):
        """Test that ALL_TOOLS contains expected tools."""
        assert len(ALL_TOOLS) == 2
        assert get_tracking_info_with_easypost in ALL_TOOLS
        assert get_all_packages_with_easypost in ALL_TOOLS

    def test_agent_handoffs_configured(self):
        """Test that agent handoffs are properly configured."""
        assert hasattr(EASYPOST_AGENT, 'handoffs')
        # GOOGLE_DOCS_AGENT, GMAIL_AGENT
        assert len(EASYPOST_AGENT.handoffs) == 2

    def test_agent_instructions_configured(self):
        """Test that agent instructions are properly set."""
        assert EASYPOST_AGENT.instructions is not None
        # Instructions now focus on functionality
        assert "track" in EASYPOST_AGENT.instructions.lower(
        ) or "package" in EASYPOST_AGENT.instructions.lower()

    def test_agent_handoff_description_configured(self):
        """Test that agent handoff description is properly set."""
        assert EASYPOST_AGENT.handoff_description is not None
        # Handoff description focuses on functionality
        assert "package" in EASYPOST_AGENT.handoff_description.lower(
        ) or "easypost" in EASYPOST_AGENT.handoff_description.lower()


class TestGetTrackingInfoTool:
    """Test the get_tracking_info_with_easypost tool."""

    @patch('connectors.easypost_agent.EasyPostTracker.get_tracker_by_tracking_number')
    @patch('connectors.easypost_agent.EASYPOST_CLIENT.tracker.retrieve')
    @pytest.mark.asyncio
    async def test_get_tracking_info_existing_tracker(self, mock_retrieve, mock_get_tracker):
        """Test getting tracking info for existing tracker."""
        # Mock existing tracker
        mock_existing_tracker = Mock()
        mock_existing_tracker.easypost_id = "trk_123456"
        mock_get_tracker.return_value = mock_existing_tracker

        # Mock EasyPost API response
        mock_tracking_info = Mock()
        mock_tracking_info.to_dict.return_value = {
            "id": "trk_123456",
            "tracking_code": "1Z999AA1234567890",
            "status": "delivered",
            "carrier": "UPS",
            "est_delivery_date": "2023-01-01",
            "tracking_details": [
                {
                    "datetime": "2023-01-01T09:00:00Z",
                    "status": "delivered",
                    "message": "Delivered"
                }
            ]
        }
        mock_retrieve.return_value = mock_tracking_info

        # Mock the tool context
        mock_ctx = Mock()
        mock_wrapper = Mock()
        mock_wrapper.context.user = Mock()

        result = await get_tracking_info_with_easypost.on_invoke_tool(
            mock_ctx,
            '{"tracking_number": "1Z999AA1234567890"}'
        )

        # Verify calls
        mock_get_tracker.assert_called_once_with("1Z999AA1234567890")
        mock_retrieve.assert_called_once_with("trk_123456")

        # Verify response structure
        assert result["response_type"] == "easypost_tracking_info"
        assert result["agent_name"] == "EasyPost"
        assert result["friendly_name"] == "EasyPostTracking Info"
        assert result["display_response"] is True
        assert result["response"]["status"] == "delivered"
        assert result["response"]["carrier"] == "UPS"

    @patch('connectors.easypost_agent.EasyPostTracker.get_tracker_by_tracking_number')
    @patch('connectors.easypost_agent.EasyPostTracker.create_tracker')
    @patch('connectors.easypost_agent.EASYPOST_CLIENT.tracker.create')
    @pytest.mark.asyncio
    async def test_get_tracking_info_new_tracker(self, mock_create, mock_create_tracker, mock_get_tracker):
        """Test creating new tracker when none exists."""
        # Mock no existing tracker
        mock_get_tracker.return_value = None

        # Mock EasyPost API response for new tracker
        mock_tracking_info = Mock()
        mock_tracking_info.id = "trk_789012"
        mock_tracking_info.carrier = "FedEx"
        mock_tracking_info.to_dict.return_value = {
            "id": "trk_789012",
            "tracking_code": "1234567890",
            "status": "in_transit",
            "carrier": "FedEx",
            "est_delivery_date": "2023-01-02"
        }
        mock_create.return_value = mock_tracking_info

        # Mock the tool context
        mock_ctx = Mock()

        result = await get_tracking_info_with_easypost.on_invoke_tool(
            mock_ctx,
            '{"tracking_number": "1234567890"}'
        )

        # Verify calls
        mock_get_tracker.assert_called_once_with("1234567890")
        mock_create.assert_called_once_with(tracking_code="1234567890")
        # Just verify create_tracker was called, not the exact arguments since mock objects have different IDs
        assert mock_create_tracker.call_count == 1
        args, kwargs = mock_create_tracker.call_args
        assert args[1] == "1234567890"  # tracking_number
        assert args[2] == "FedEx"       # carrier
        assert args[3] == "trk_789012"  # easypost_id

        # Verify response
        assert result["response"]["status"] == "in_transit"
        assert result["response"]["carrier"] == "FedEx"

    @patch('connectors.easypost_agent.EasyPostTracker.get_tracker_by_tracking_number')
    @patch('connectors.easypost_agent.EASYPOST_CLIENT.tracker.create')
    @pytest.mark.asyncio
    async def test_get_tracking_info_api_error(self, mock_create, mock_get_tracker):
        """Test handling of EasyPost API errors."""
        mock_get_tracker.return_value = None
        mock_create.side_effect = Exception("EasyPost API Error")

        # Mock the tool context
        mock_ctx = Mock()

        result = await get_tracking_info_with_easypost.on_invoke_tool(
            mock_ctx,
            '{"tracking_number": "1234567890"}'
        )

        # The function tool framework catches exceptions and returns error message as string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()

    @patch('connectors.easypost_agent.EasyPostTracker.get_tracker_by_tracking_number')
    @patch('connectors.easypost_agent.EASYPOST_CLIENT.tracker.retrieve')
    @pytest.mark.asyncio
    async def test_get_tracking_info_invalid_tracking_number(self, mock_retrieve, mock_get_tracker):
        """Test handling of invalid tracking number."""
        mock_existing_tracker = Mock()
        mock_existing_tracker.easypost_id = "trk_invalid"
        mock_get_tracker.return_value = mock_existing_tracker

        mock_retrieve.side_effect = Exception("Invalid tracking number")

        # Mock the tool context
        mock_ctx = Mock()

        result = await get_tracking_info_with_easypost.on_invoke_tool(
            mock_ctx,
            '{"tracking_number": "INVALID123"}'
        )

        # The function tool framework catches exceptions and returns error message as string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()


class TestGetAllPackagesTool:
    """Test the get_all_packages_with_easypost tool."""

    @patch('connectors.easypost_agent.EasyPostTracker.get_trackers_by_user_id')
    @patch('connectors.easypost_agent.EASYPOST_CLIENT.tracker.retrieve')
    @pytest.mark.asyncio
    async def test_get_all_packages_success(self, mock_retrieve, mock_get_trackers):
        """Test successful retrieval of all packages."""
        # Mock stored packages
        mock_package1 = Mock()
        mock_package1.easypost_id = "trk_123"
        mock_package2 = Mock()
        mock_package2.easypost_id = "trk_456"
        mock_get_trackers.return_value = [mock_package1, mock_package2]

        # Mock EasyPost API responses
        mock_tracking1 = Mock()
        mock_tracking1.to_dict.return_value = {
            "id": "trk_123",
            "tracking_code": "1Z999AA1234567890",
            "status": "delivered",
            "carrier": "UPS"
        }
        mock_tracking2 = Mock()
        mock_tracking2.to_dict.return_value = {
            "id": "trk_456",
            "tracking_code": "1234567890",
            "status": "in_transit",
            "carrier": "FedEx"
        }
        mock_retrieve.side_effect = [mock_tracking1, mock_tracking2]

        # Mock the tool context
        mock_ctx = Mock()

        result = await get_all_packages_with_easypost.on_invoke_tool(
            mock_ctx,
            '{}'
        )

        # Verify calls - the actual user reference_id will be from the mock context
        assert mock_get_trackers.call_count == 1
        assert mock_retrieve.call_count == 2

        # Verify response
        assert result["response_type"] == "easypost_all_packages"
        assert result["agent_name"] == "EasyPost"
        assert result["friendly_name"] == "All Stored Packages"
        assert result["display_response"] is True
        assert len(result["response"]) == 2
        assert result["response"][0]["status"] == "delivered"
        assert result["response"][1]["status"] == "in_transit"

    @patch('connectors.easypost_agent.EasyPostTracker.get_trackers_by_user_id')
    @pytest.mark.asyncio
    async def test_get_all_packages_empty_list(self, mock_get_trackers):
        """Test handling when user has no packages."""
        mock_get_trackers.return_value = []

        # Mock the tool context
        mock_ctx = Mock()

        result = await get_all_packages_with_easypost.on_invoke_tool(
            mock_ctx,
            '{}'
        )

        # Verify empty response
        assert result["response"] == []
        assert result["response_type"] == "easypost_all_packages"

    @patch('connectors.easypost_agent.EasyPostTracker.get_trackers_by_user_id')
    @pytest.mark.asyncio
    async def test_get_all_packages_database_error(self, mock_get_trackers):
        """Test handling of database errors."""
        mock_get_trackers.side_effect = Exception("Database error")

        # Mock the tool context
        mock_ctx = Mock()

        result = await get_all_packages_with_easypost.on_invoke_tool(
            mock_ctx,
            '{}'
        )

        # The function tool framework catches exceptions and returns error message as string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()

    @patch('connectors.easypost_agent.EasyPostTracker.get_trackers_by_user_id')
    @patch('connectors.easypost_agent.EASYPOST_CLIENT.tracker.retrieve')
    @pytest.mark.asyncio
    async def test_get_all_packages_partial_failure(self, mock_retrieve, mock_get_trackers):
        """Test handling when some packages fail to retrieve."""
        # Mock stored packages
        mock_package1 = Mock()
        mock_package1.easypost_id = "trk_123"
        mock_package2 = Mock()
        mock_package2.easypost_id = "trk_456"
        mock_get_trackers.return_value = [mock_package1, mock_package2]

        # Mock first successful, second fails
        mock_tracking1 = Mock()
        mock_tracking1.to_dict.return_value = {
            "id": "trk_123", "status": "delivered"}
        mock_retrieve.side_effect = [mock_tracking1, Exception("API Error")]

        # Mock the tool context
        mock_ctx = Mock()

        result = await get_all_packages_with_easypost.on_invoke_tool(
            mock_ctx,
            '{}'
        )

        # The function tool framework catches exceptions and returns error message as string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()


class TestEasyPostAgentIntegration:
    """Integration tests for EasyPost agent components."""

    def test_agent_tools_registration(self):
        """Test that tools are properly registered with the agent."""
        tool_names = [tool.name for tool in EASYPOST_AGENT.tools]
        assert "get_tracking_info_with_easypost" in tool_names
        assert "get_all_packages_with_easypost" in tool_names

    def test_agent_model_configuration(self):
        """Test that agent uses correct model."""
        assert EASYPOST_AGENT.model == "gpt-4o"

    def test_import_dependencies(self):
        """Test that agent dependencies are properly imported."""
        # This test ensures the import structure works
        try:
            from connectors.easypost_agent import (
                EASYPOST_AGENT,
                get_tracking_info_with_easypost,
                get_all_packages_with_easypost
            )
            assert EASYPOST_AGENT is not None
            assert get_tracking_info_with_easypost is not None
            assert get_all_packages_with_easypost is not None
        except ImportError as e:
            pytest.fail(f"Failed to import EasyPost components: {e}")


class TestEasyPostEdgeCases:
    """Test edge cases and error conditions."""

    def test_tracking_tool_function_signature(self):
        """Test that tracking tool function has correct parameter schema."""
        schema = get_tracking_info_with_easypost.params_json_schema
        assert "properties" in schema
        params = schema["properties"]
        assert "tracking_number" in params
        assert params["tracking_number"]["type"] == "string"

    def test_all_packages_tool_function_signature(self):
        """Test that all packages tool function has correct parameter schema."""
        schema = get_all_packages_with_easypost.params_json_schema
        assert "properties" in schema
        # This tool doesn't require parameters besides the wrapper

    @pytest.mark.asyncio
    async def test_tool_response_format_consistency(self):
        """Test that tools return consistent ToolResponse format."""
        with patch('connectors.easypost_agent.EasyPostTracker.get_tracker_by_tracking_number') as mock_get_tracker:
            with patch('connectors.easypost_agent.EASYPOST_CLIENT.tracker.retrieve') as mock_retrieve:
                mock_get_tracker.return_value = Mock(easypost_id="trk_123")
                mock_tracking = Mock()
                mock_tracking.to_dict.return_value = {
                    "id": "trk_123", "status": "delivered"}
                mock_retrieve.return_value = mock_tracking

                # Mock the tool context
                mock_ctx = Mock()

                result = await get_tracking_info_with_easypost.on_invoke_tool(
                    mock_ctx,
                    '{"tracking_number": "1234567890"}'
                )

                # Verify ToolResponse format
                required_fields = ["response_type", "agent_name",
                                   "friendly_name", "display_response", "response"]
                for field in required_fields:
                    assert field in result

                assert result["response_type"] == "easypost_tracking_info"
                assert result["agent_name"] == "EasyPost"
                assert result["display_response"] is True

    def test_all_tools_contains_all_functions(self):
        """Test that ALL_TOOLS exports all available tool functions."""
        expected_tools = [get_tracking_info_with_easypost,
                          get_all_packages_with_easypost]
        assert len(ALL_TOOLS) == len(expected_tools)
        for tool in expected_tools:
            assert tool in ALL_TOOLS

    @patch('connectors.easypost_agent.EasyPostTracker.create_tracker')
    @patch('connectors.easypost_agent.EASYPOST_CLIENT.tracker.create')
    @patch('connectors.easypost_agent.EasyPostTracker.get_tracker_by_tracking_number')
    @pytest.mark.asyncio
    async def test_tracking_info_with_empty_tracking_number(self, mock_get_tracker, mock_create, mock_create_tracker):
        """Test handling of empty tracking number."""
        mock_get_tracker.return_value = None
        
        # Mock the created tracker response
        mock_tracker = Mock()
        mock_tracker.id = "trk_test123"
        mock_tracker.carrier = "USPS"
        mock_tracker.to_dict.return_value = {
            "id": "trk_test123",
            "tracking_code": "",
            "carrier": "USPS",
            "status": "unknown"
        }
        mock_create.return_value = mock_tracker

        # Mock the tool context with user
        mock_ctx = Mock()
        mock_ctx.user = Mock()
        mock_ctx.user.reference_id = "user123"

        result = await get_tracking_info_with_easypost.on_invoke_tool(
            mock_ctx,
            '{"tracking_number": ""}'
        )

        # Should still attempt to look up empty string
        mock_get_tracker.assert_called_once_with("")
        mock_create.assert_called_once_with(tracking_code="")

    def test_agent_name_consistency(self):
        """Test that agent name is consistent."""
        assert EASYPOST_AGENT.name == "EasyPost"
