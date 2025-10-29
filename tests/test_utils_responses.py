"""
Comprehensive tests for connectors/utils/responses.py

Tests cover all response classes including ToolResponse base class and specialized
response types for various tool interactions and account requirements.
"""

import pytest
import json
from unittest.mock import Mock, patch


class TestToolResponse:
    """Test cases for the base ToolResponse class."""

    def test_tool_response_creation(self):
        """Test basic ToolResponse creation."""
        from connectors.utils.responses import ToolResponse

        response = ToolResponse(
            response_type="test_type",
            agent_name="test_agent",
            friendly_name="Test Response",
            response={"data": "test"},
            display_response=True
        )

        # Verify all attributes are set correctly
        assert response.response_type == "test_type"
        assert response.agent_name == "test_agent"
        assert response.friendly_name == "Test Response"
        assert response.response == {"data": "test"}
        assert response.display_response == True

    def test_tool_response_default_display_response(self):
        """Test ToolResponse with default display_response."""
        from connectors.utils.responses import ToolResponse

        response = ToolResponse(
            response_type="test_type",
            agent_name="test_agent",
            friendly_name="Test Response",
            response="simple response"
        )

        # Default display_response should be True
        assert response.display_response == True

    def test_tool_response_to_dict(self):
        """Test ToolResponse to_dict method."""
        from connectors.utils.responses import ToolResponse

        response = ToolResponse(
            response_type="test_type",
            agent_name="test_agent",
            friendly_name="Test Response",
            response=["list", "data"],
            display_response=False
        )

        result_dict = response.to_dict()

        expected = {
            "response_type": "test_type",
            "agent_name": "test_agent",
            "friendly_name": "Test Response",
            "response": ["list", "data"],
            "display_response": False
        }

        assert result_dict == expected
        assert isinstance(result_dict, dict)

    def test_tool_response_to_json(self):
        """Test ToolResponse to_json method."""
        from connectors.utils.responses import ToolResponse

        response = ToolResponse(
            response_type="json_test",
            agent_name="json_agent",
            friendly_name="JSON Test",
            response={"nested": {"data": 42}},
            display_response=True
        )

        json_result = response.to_json()

        # Should return valid JSON string
        assert isinstance(json_result, str)

        # Parse back to verify structure
        parsed = json.loads(json_result)
        expected = {
            "response_type": "json_test",
            "agent_name": "json_agent",
            "friendly_name": "JSON Test",
            "response": {"nested": {"data": 42}},
            "display_response": True
        }

        assert parsed == expected

    def test_tool_response_with_different_response_types(self):
        """Test ToolResponse with different response data types."""
        from connectors.utils.responses import ToolResponse

        # Test with dict
        dict_response = ToolResponse("dict", "agent", "Dict", {"key": "value"})
        assert isinstance(dict_response.response, dict)

        # Test with string
        str_response = ToolResponse(
            "string", "agent", "String", "text response")
        assert isinstance(str_response.response, str)

        # Test with list
        list_response = ToolResponse("list", "agent", "List", [1, 2, 3])
        assert isinstance(list_response.response, list)

        # All should convert to dict properly
        for response in [dict_response, str_response, list_response]:
            result_dict = response.to_dict()
            assert "response" in result_dict
            assert "response_type" in result_dict

    def test_tool_response_json_serialization_edge_cases(self):
        """Test JSON serialization with edge cases."""
        from connectors.utils.responses import ToolResponse

        # Test with None values
        none_response = ToolResponse("none", "agent", "None", None)
        json_str = none_response.to_json()
        parsed = json.loads(json_str)
        assert parsed["response"] is None

        # Test with empty structures
        empty_dict_response = ToolResponse("empty_dict", "agent", "Empty", {})
        json_str = empty_dict_response.to_json()
        parsed = json.loads(json_str)
        assert parsed["response"] == {}

        # Test with unicode
        unicode_response = ToolResponse(
            "unicode", "agent", "Unicode", {"text": "测试文本"})
        json_str = unicode_response.to_json()
        parsed = json.loads(json_str)
        assert parsed["response"]["text"] == "测试文本"


class TestOpenWindowResponse:
    """Test cases for OpenWindowResponse class."""

    def test_open_window_response_creation(self):
        """Test OpenWindowResponse creation."""
        from connectors.utils.responses import OpenWindowResponse

        response = OpenWindowResponse("window_agent", "https://example.com")

        # Verify attributes
        assert response.response_type == 'open_window'
        assert response.agent_name == "window_agent"
        assert response.friendly_name == 'Open Window'
        assert response.response == {'url': 'https://example.com'}
        assert response.display_response == True

    def test_open_window_response_inheritance(self):
        """Test that OpenWindowResponse inherits from ToolResponse."""
        from connectors.utils.responses import OpenWindowResponse, ToolResponse

        response = OpenWindowResponse("test_agent", "https://test.com")

        # Should be instance of ToolResponse
        assert isinstance(response, ToolResponse)

        # Should have all ToolResponse methods
        assert hasattr(response, 'to_dict')
        assert hasattr(response, 'to_json')

    def test_open_window_response_to_dict(self):
        """Test OpenWindowResponse to_dict method."""
        from connectors.utils.responses import OpenWindowResponse

        response = OpenWindowResponse("browser_agent", "https://google.com")
        result_dict = response.to_dict()

        expected = {
            "response_type": "open_window",
            "agent_name": "browser_agent",
            "friendly_name": "Open Window",
            "response": {"url": "https://google.com"},
            "display_response": True
        }

        assert result_dict == expected

    def test_open_window_response_different_urls(self):
        """Test OpenWindowResponse with different URL formats."""
        from connectors.utils.responses import OpenWindowResponse

        test_urls = [
            "https://example.com",
            "http://localhost:3000",
            "https://subdomain.example.co.uk/path?param=value",
            "ftp://files.example.com",
            "mailto:test@example.com",
            ""  # Empty URL
        ]

        for url in test_urls:
            response = OpenWindowResponse("url_agent", url)
            assert response.response["url"] == url

            # Should serialize properly
            json_str = response.to_json()
            parsed = json.loads(json_str)
            assert parsed["response"]["url"] == url


class TestOpenTabResponse:
    """Test cases for OpenTabResponse class."""

    def test_open_tab_response_creation(self):
        """Test OpenTabResponse creation."""
        from connectors.utils.responses import OpenTabResponse

        response = OpenTabResponse("tab_agent", "https://example.com")

        # Verify attributes
        assert response.response_type == 'open_tab'
        assert response.agent_name == "tab_agent"
        assert response.friendly_name == 'Open Tab'
        assert response.response == {'url': 'https://example.com'}
        assert response.display_response == True

    def test_open_tab_response_inheritance(self):
        """Test that OpenTabResponse inherits from ToolResponse."""
        from connectors.utils.responses import OpenTabResponse, ToolResponse

        response = OpenTabResponse("test_agent", "https://test.com")

        # Should be instance of ToolResponse
        assert isinstance(response, ToolResponse)

    def test_open_tab_vs_open_window_difference(self):
        """Test difference between OpenTabResponse and OpenWindowResponse."""
        from connectors.utils.responses import OpenTabResponse, OpenWindowResponse

        tab_response = OpenTabResponse("agent", "https://example.com")
        window_response = OpenWindowResponse("agent", "https://example.com")

        # Only difference should be response_type
        assert tab_response.response_type == 'open_tab'
        assert window_response.response_type == 'open_window'
        assert tab_response.friendly_name == 'Open Tab'
        assert window_response.friendly_name == 'Open Window'

        # Everything else should be the same
        assert tab_response.response == window_response.response
        assert tab_response.display_response == window_response.display_response

    def test_open_tab_response_to_json(self):
        """Test OpenTabResponse JSON serialization."""
        from connectors.utils.responses import OpenTabResponse

        response = OpenTabResponse("browser", "https://github.com")
        json_str = response.to_json()
        parsed = json.loads(json_str)

        expected = {
            "response_type": "open_tab",
            "agent_name": "browser",
            "friendly_name": "Open Tab",
            "response": {"url": "https://github.com"},
            "display_response": True
        }

        assert parsed == expected


class TestAccountNeededResponse:
    """Test cases for AccountNeededResponse class."""

    def test_account_needed_response_creation(self):
        """Test AccountNeededResponse creation."""
        from connectors.utils.responses import AccountNeededResponse

        response = AccountNeededResponse("service_agent", "twitter")

        # Verify attributes
        assert response.response_type == 'account_needed'
        assert response.agent_name == "service_agent"
        assert response.friendly_name == 'Account Needed'
        assert response.response == {'account_type': 'twitter'}
        assert response.display_response == True

    def test_account_needed_response_different_account_types(self):
        """Test AccountNeededResponse with different account types."""
        from connectors.utils.responses import AccountNeededResponse

        account_types = [
            "google",
            "facebook",
            "twitter",
            "linkedin",
            "github",
            "custom_service"
        ]

        for account_type in account_types:
            response = AccountNeededResponse("auth_agent", account_type)
            assert response.response["account_type"] == account_type

            # Verify serialization
            result_dict = response.to_dict()
            assert result_dict["response"]["account_type"] == account_type

    def test_account_needed_response_inheritance(self):
        """Test that AccountNeededResponse inherits from ToolResponse."""
        from connectors.utils.responses import AccountNeededResponse, ToolResponse

        response = AccountNeededResponse("auth_agent", "oauth_service")

        # Should be instance of ToolResponse
        assert isinstance(response, ToolResponse)

        # Should have all ToolResponse functionality
        json_str = response.to_json()
        parsed = json.loads(json_str)
        assert parsed["response_type"] == "account_needed"

    def test_account_needed_response_empty_account_type(self):
        """Test AccountNeededResponse with empty account type."""
        from connectors.utils.responses import AccountNeededResponse

        response = AccountNeededResponse("agent", "")
        assert response.response["account_type"] == ""

        # Should still serialize properly
        json_str = response.to_json()
        parsed = json.loads(json_str)
        assert parsed["response"]["account_type"] == ""


class TestGoogleAccountNeededResponse:
    """Test cases for GoogleAccountNeededResponse class."""

    def test_google_account_needed_response_creation(self):
        """Test GoogleAccountNeededResponse creation."""
        from connectors.utils.responses import GoogleAccountNeededResponse

        response = GoogleAccountNeededResponse("google_agent")

        # Verify attributes
        assert response.response_type == 'google_account_needed'
        assert response.agent_name == "google_agent"
        assert response.friendly_name == 'Google Account Needed'
        assert response.response == {'account_type_needed': 'google'}
        assert response.display_response == True

    def test_google_account_needed_response_inheritance(self):
        """Test that GoogleAccountNeededResponse inherits from ToolResponse."""
        from connectors.utils.responses import GoogleAccountNeededResponse, ToolResponse

        response = GoogleAccountNeededResponse("gmail_agent")

        # Should be instance of ToolResponse
        assert isinstance(response, ToolResponse)

    def test_google_account_needed_vs_account_needed(self):
        """Test difference between GoogleAccountNeededResponse and AccountNeededResponse."""
        from connectors.utils.responses import GoogleAccountNeededResponse, AccountNeededResponse

        google_response = GoogleAccountNeededResponse("agent")
        account_response = AccountNeededResponse("agent", "google")

        # Should have different response types
        assert google_response.response_type == 'google_account_needed'
        assert account_response.response_type == 'account_needed'

        # Should have different response structures
        assert google_response.response == {'account_type_needed': 'google'}
        assert account_response.response == {'account_type': 'google'}

        # Should have different friendly names
        assert google_response.friendly_name == 'Google Account Needed'
        assert account_response.friendly_name == 'Account Needed'

    def test_google_account_needed_response_to_dict(self):
        """Test GoogleAccountNeededResponse to_dict method."""
        from connectors.utils.responses import GoogleAccountNeededResponse

        response = GoogleAccountNeededResponse("calendar_agent")
        result_dict = response.to_dict()

        expected = {
            "response_type": "google_account_needed",
            "agent_name": "calendar_agent",
            "friendly_name": "Google Account Needed",
            "response": {"account_type_needed": "google"},
            "display_response": True
        }

        assert result_dict == expected

    def test_google_account_needed_response_json_serialization(self):
        """Test GoogleAccountNeededResponse JSON serialization."""
        from connectors.utils.responses import GoogleAccountNeededResponse

        response = GoogleAccountNeededResponse("drive_agent")
        json_str = response.to_json()
        parsed = json.loads(json_str)

        expected = {
            "response_type": "google_account_needed",
            "agent_name": "drive_agent",
            "friendly_name": "Google Account Needed",
            "response": {"account_type_needed": "google"},
            "display_response": True
        }

        assert parsed == expected

    def test_google_account_needed_response_agent_name_variations(self):
        """Test GoogleAccountNeededResponse with various agent names."""
        from connectors.utils.responses import GoogleAccountNeededResponse

        agent_names = [
            "gmail_agent",
            "google_calendar",
            "google_drive",
            "google_docs",
            "google_sheets",
            "",  # Empty agent name
            "测试代理"  # Unicode agent name
        ]

        for agent_name in agent_names:
            response = GoogleAccountNeededResponse(agent_name)
            assert response.agent_name == agent_name

            # Should serialize properly regardless of agent name
            json_str = response.to_json()
            parsed = json.loads(json_str)
            assert parsed["agent_name"] == agent_name


class TestConnectGoogleAccountResponse:
    """Test cases for ConnectGoogleAccountResponse class."""

    def test_connect_google_account_response_creation(self):
        """Test ConnectGoogleAccountResponse creation."""
        from connectors.utils.responses import ConnectGoogleAccountResponse

        response = ConnectGoogleAccountResponse("google_agent")

        # Verify attributes
        assert response.response_type == 'connect_google_account'
        assert response.agent_name == "google_agent"
        assert response.friendly_name == 'Connect Google Account'
        assert response.response == "Please press the button above to connect your Google account"
        assert response.display_response == True

    def test_connect_google_account_response_inheritance(self):
        """Test that ConnectGoogleAccountResponse inherits from ToolResponse."""
        from connectors.utils.responses import ConnectGoogleAccountResponse, ToolResponse

        response = ConnectGoogleAccountResponse("auth_agent")

        # Should be instance of ToolResponse
        assert isinstance(response, ToolResponse)

        # Should have all ToolResponse methods
        assert hasattr(response, 'to_dict')
        assert hasattr(response, 'to_json')

    def test_connect_google_account_response_to_dict(self):
        """Test ConnectGoogleAccountResponse to_dict method."""
        from connectors.utils.responses import ConnectGoogleAccountResponse

        response = ConnectGoogleAccountResponse("oauth_agent")
        result_dict = response.to_dict()

        expected = {
            "response_type": "connect_google_account",
            "agent_name": "oauth_agent",
            "friendly_name": "Connect Google Account",
            "response": "Please press the button above to connect your Google account",
            "display_response": True
        }

        assert result_dict == expected

    def test_connect_google_account_response_json_serialization(self):
        """Test ConnectGoogleAccountResponse JSON serialization."""
        from connectors.utils.responses import ConnectGoogleAccountResponse

        response = ConnectGoogleAccountResponse("google_auth")
        json_str = response.to_json()
        parsed = json.loads(json_str)

        expected = {
            "response_type": "connect_google_account",
            "agent_name": "google_auth",
            "friendly_name": "Connect Google Account",
            "response": "Please press the button above to connect your Google account",
            "display_response": True
        }

        assert parsed == expected

    def test_connect_google_account_vs_google_account_needed(self):
        """Test difference between ConnectGoogleAccountResponse and GoogleAccountNeededResponse."""
        from connectors.utils.responses import ConnectGoogleAccountResponse, GoogleAccountNeededResponse

        connect_response = ConnectGoogleAccountResponse("agent")
        needed_response = GoogleAccountNeededResponse("agent")

        # Should have different response types
        assert connect_response.response_type == 'connect_google_account'
        assert needed_response.response_type == 'google_account_needed'

        # Should have different response structures
        assert connect_response.response == "Please press the button above to connect your Google account"
        assert needed_response.response == {'account_type_needed': 'google'}

        # Should have different friendly names
        assert connect_response.friendly_name == 'Connect Google Account'
        assert needed_response.friendly_name == 'Google Account Needed'


class TestRequestGoogleAccessResponse:
    """Test cases for RequestGoogleAccessResponse class."""

    def test_request_google_access_response_creation(self):
        """Test RequestGoogleAccessResponse creation."""
        from connectors.utils.responses import RequestGoogleAccessResponse

        response = RequestGoogleAccessResponse("google_agent")

        # Verify attributes
        assert response.response_type == 'request_google_access'
        assert response.agent_name == "google_agent"
        assert response.friendly_name == 'Request Google Access'
        assert response.response == "Please press the button above to request access to your Google account"
        assert response.display_response == True

    def test_request_google_access_response_inheritance(self):
        """Test that RequestGoogleAccessResponse inherits from ToolResponse."""
        from connectors.utils.responses import RequestGoogleAccessResponse, ToolResponse

        response = RequestGoogleAccessResponse("access_agent")

        # Should be instance of ToolResponse
        assert isinstance(response, ToolResponse)

        # Should have all ToolResponse methods
        assert hasattr(response, 'to_dict')
        assert hasattr(response, 'to_json')

    def test_request_google_access_response_to_dict(self):
        """Test RequestGoogleAccessResponse to_dict method."""
        from connectors.utils.responses import RequestGoogleAccessResponse

        response = RequestGoogleAccessResponse("request_agent")
        result_dict = response.to_dict()

        expected = {
            "response_type": "request_google_access",
            "agent_name": "request_agent",
            "friendly_name": "Request Google Access",
            "response": "Please press the button above to request access to your Google account",
            "display_response": True
        }

        assert result_dict == expected

    def test_request_google_access_response_json_serialization(self):
        """Test RequestGoogleAccessResponse JSON serialization."""
        from connectors.utils.responses import RequestGoogleAccessResponse

        response = RequestGoogleAccessResponse("google_request")
        json_str = response.to_json()
        parsed = json.loads(json_str)

        expected = {
            "response_type": "request_google_access",
            "agent_name": "google_request",
            "friendly_name": "Request Google Access",
            "response": "Please press the button above to request access to your Google account",
            "display_response": True
        }

        assert parsed == expected

    def test_request_google_access_agent_name_variations(self):
        """Test RequestGoogleAccessResponse with various agent names."""
        from connectors.utils.responses import RequestGoogleAccessResponse

        agent_names = [
            "google_connections",
            "oauth_handler",
            "access_manager",
            "",  # Empty agent name
            "测试代理"  # Unicode agent name
        ]

        for agent_name in agent_names:
            response = RequestGoogleAccessResponse(agent_name)
            assert response.agent_name == agent_name

            # Should serialize properly regardless of agent name
            json_str = response.to_json()
            parsed = json.loads(json_str)
            assert parsed["agent_name"] == agent_name

    def test_connect_vs_request_google_response_difference(self):
        """Test difference between ConnectGoogleAccountResponse and RequestGoogleAccessResponse."""
        from connectors.utils.responses import ConnectGoogleAccountResponse, RequestGoogleAccessResponse

        connect_response = ConnectGoogleAccountResponse("agent")
        request_response = RequestGoogleAccessResponse("agent")

        # Should have different response types
        assert connect_response.response_type == 'connect_google_account'
        assert request_response.response_type == 'request_google_access'

        # Should have different friendly names
        assert connect_response.friendly_name == 'Connect Google Account'
        assert request_response.friendly_name == 'Request Google Access'

        # Both should have string responses
        assert connect_response.response == "Please press the button above to connect your Google account"
        assert request_response.response == "Please press the button above to request access to your Google account"


# Integration and error handling tests
class TestResponsesIntegration:
    """Integration tests for responses.py utilities."""

    def test_all_response_types_import(self):
        """Test that all response classes can be imported."""
        from connectors.utils.responses import (
            ToolResponse,
            OpenWindowResponse,
            OpenTabResponse,
            AccountNeededResponse,
            GoogleAccountNeededResponse,
            ConnectGoogleAccountResponse,
            RequestGoogleAccessResponse
        )

        # All should be classes
        assert isinstance(ToolResponse, type)
        assert isinstance(OpenWindowResponse, type)
        assert isinstance(OpenTabResponse, type)
        assert isinstance(AccountNeededResponse, type)
        assert isinstance(GoogleAccountNeededResponse, type)
        assert isinstance(ConnectGoogleAccountResponse, type)
        assert isinstance(RequestGoogleAccessResponse, type)

    def test_inheritance_chain(self):
        """Test that all response classes inherit from ToolResponse."""
        from connectors.utils.responses import (
            ToolResponse,
            OpenWindowResponse,
            OpenTabResponse,
            AccountNeededResponse,
            GoogleAccountNeededResponse,
            ConnectGoogleAccountResponse,
            RequestGoogleAccessResponse
        )

        # Create instances
        responses = [
            OpenWindowResponse("agent", "url"),
            OpenTabResponse("agent", "url"),
            AccountNeededResponse("agent", "service"),
            GoogleAccountNeededResponse("agent"),
            ConnectGoogleAccountResponse("agent"),
            RequestGoogleAccessResponse("agent")
        ]

        # All should be instances of ToolResponse
        for response in responses:
            assert isinstance(response, ToolResponse)
            assert hasattr(response, 'to_dict')
            assert hasattr(response, 'to_json')

    def test_json_module_usage(self):
        """Test that json module is used correctly."""
        from connectors.utils.responses import ToolResponse
        import json as real_json

        response = ToolResponse("test", "agent", "Test", {"data": "value"})

        # to_json should produce valid JSON
        json_str = response.to_json()

        # Should be parseable by standard json module
        parsed = real_json.loads(json_str)
        assert isinstance(parsed, dict)
        assert parsed["response_type"] == "test"

    def test_all_response_types_serialization(self):
        """Test that all response types serialize correctly."""
        from connectors.utils.responses import (
            ToolResponse,
            OpenWindowResponse,
            OpenTabResponse,
            AccountNeededResponse,
            GoogleAccountNeededResponse,
            ConnectGoogleAccountResponse,
            RequestGoogleAccessResponse
        )

        responses = [
            ToolResponse("base", "agent", "Base", "data"),
            OpenWindowResponse("agent", "https://example.com"),
            OpenTabResponse("agent", "https://example.com"),
            AccountNeededResponse("agent", "service"),
            GoogleAccountNeededResponse("agent"),
            ConnectGoogleAccountResponse("agent"),
            RequestGoogleAccessResponse("agent")
        ]

        for response in responses:
            # Should convert to dict
            result_dict = response.to_dict()
            assert isinstance(result_dict, dict)
            assert "response_type" in result_dict
            assert "agent_name" in result_dict
            assert "friendly_name" in result_dict
            assert "response" in result_dict
            assert "display_response" in result_dict

            # Should convert to JSON
            json_str = response.to_json()
            assert isinstance(json_str, str)

            # JSON should be parseable
            parsed = json.loads(json_str)
            assert parsed == result_dict

    def test_response_type_uniqueness(self):
        """Test that each response class has a unique response_type."""
        from connectors.utils.responses import (
            OpenWindowResponse,
            OpenTabResponse,
            AccountNeededResponse,
            GoogleAccountNeededResponse,
            ConnectGoogleAccountResponse,
            RequestGoogleAccessResponse
        )

        responses = [
            OpenWindowResponse("agent", "url"),
            OpenTabResponse("agent", "url"),
            AccountNeededResponse("agent", "service"),
            GoogleAccountNeededResponse("agent"),
            ConnectGoogleAccountResponse("agent"),
            RequestGoogleAccessResponse("agent")
        ]

        response_types = [r.response_type for r in responses]

        # All response types should be unique
        assert len(response_types) == len(set(response_types))

        # Verify specific types
        expected_types = ['open_window', 'open_tab',
                          'account_needed', 'google_account_needed',
                          'connect_google_account', 'request_google_access']
        assert set(response_types) == set(expected_types)

    def test_constructor_parameter_handling(self):
        """Test that all constructors handle parameters correctly."""
        from connectors.utils.responses import (
            ToolResponse,
            OpenWindowResponse,
            OpenTabResponse,
            AccountNeededResponse,
            GoogleAccountNeededResponse
        )

        # ToolResponse requires all parameters
        tool_response = ToolResponse("type", "agent", "name", "response")
        assert tool_response.display_response == True  # Default value

        tool_response_explicit = ToolResponse(
            "type", "agent", "name", "response", False)
        assert tool_response_explicit.display_response == False

        # Other responses have fixed parameters except agent_name
        open_window = OpenWindowResponse("test_agent", "test_url")
        assert open_window.agent_name == "test_agent"

        open_tab = OpenTabResponse("test_agent", "test_url")
        assert open_tab.agent_name == "test_agent"

        account_needed = AccountNeededResponse("test_agent", "test_service")
        assert account_needed.agent_name == "test_agent"

        google_account = GoogleAccountNeededResponse("test_agent")
        assert google_account.agent_name == "test_agent"
