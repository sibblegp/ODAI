"""
Comprehensive tests for connectors/open_external_url.py

Tests cover the open_external_url functions, agent configuration, and response types.
"""

import pytest
from unittest.mock import Mock, patch
from agents import Agent, RunContextWrapper
from connectors.open_external_url import (
    OPEN_EXTERNAL_URL_AGENT,
    open_external_url_in_window,
    open_external_url_in_tab
)
from connectors.utils.responses import OpenWindowResponse, OpenTabResponse
from connectors.utils.context import ChatContext


class TestOpenExternalUrlConfig:
    """Test Open External URL agent configuration and setup."""

    def test_open_external_url_agent_exists(self):
        """Test that OPEN_EXTERNAL_URL_AGENT is properly configured."""
        assert OPEN_EXTERNAL_URL_AGENT is not None
        assert isinstance(OPEN_EXTERNAL_URL_AGENT, Agent)
        assert OPEN_EXTERNAL_URL_AGENT.name == "OpenExternalUrl"
        assert OPEN_EXTERNAL_URL_AGENT.model == "gpt-4o"
        assert len(OPEN_EXTERNAL_URL_AGENT.tools) == 2

    def test_agent_tools_configured(self):
        """Test that agent tools are properly configured."""
        tool_names = [tool.name for tool in OPEN_EXTERNAL_URL_AGENT.tools]
        assert 'open_external_url_in_window' in tool_names
        assert 'open_external_url_in_tab' in tool_names

    def test_agent_handoff_description_configured(self):
        """Test that agent handoff description is properly set."""
        assert OPEN_EXTERNAL_URL_AGENT.handoff_description is not None
        assert "Open external URLs" in OPEN_EXTERNAL_URL_AGENT.handoff_description
        assert "Open external URLs" in OPEN_EXTERNAL_URL_AGENT.handoff_description
        assert "new window or tab" in OPEN_EXTERNAL_URL_AGENT.handoff_description

    def test_no_handoffs_configured(self):
        """Test that no handoffs are configured for this agent."""
        assert not hasattr(OPEN_EXTERNAL_URL_AGENT, 'handoffs') or OPEN_EXTERNAL_URL_AGENT.handoffs is None or len(
            OPEN_EXTERNAL_URL_AGENT.handoffs) == 0


class TestOpenExternalUrlInWindowTool:
    """Test the open_external_url_in_window tool."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock context wrapper."""
        mock_ctx = Mock(spec=ChatContext)
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx
        return mock_wrapper

    @pytest.mark.asyncio
    async def test_open_external_url_in_window_success(self, mock_context):
        """Test successful URL opening in a new window."""
        test_url = "https://example.com"

        result = await open_external_url_in_window.on_invoke_tool(
            mock_context,
            f'{{"url": "{test_url}"}}'
        )

        # Verify response structure
        assert result["response_type"] == "open_window"
        assert result["agent_name"] == "OpenExternalUrl"
        assert result["response"]["url"] == test_url
        assert result["display_response"] is True

    @pytest.mark.asyncio
    async def test_open_external_url_in_window_with_query_params(self, mock_context):
        """Test opening URL with query parameters in a new window."""
        test_url = "https://example.com/search?q=test&page=1"

        result = await open_external_url_in_window.on_invoke_tool(
            mock_context,
            f'{{"url": "{test_url}"}}'
        )

        assert result["response_type"] == "open_window"
        assert result["response"]["url"] == test_url

    @pytest.mark.asyncio
    async def test_open_external_url_in_window_special_characters(self, mock_context):
        """Test opening URL with special characters in a new window."""
        test_url = "https://example.com/path?param=value%20with%20spaces&other=@#$"

        result = await open_external_url_in_window.on_invoke_tool(
            mock_context,
            f'{{"url": "{test_url}"}}'
        )

        assert result["response_type"] == "open_window"
        assert result["response"]["url"] == test_url

    @pytest.mark.asyncio
    async def test_open_external_url_in_window_different_protocols(self, mock_context):
        """Test opening URLs with different protocols in a new window."""
        protocols = ["http://", "https://", "ftp://", "mailto:"]

        for protocol in protocols:
            test_url = f"{protocol}example.com"

            result = await open_external_url_in_window.on_invoke_tool(
                mock_context,
                f'{{"url": "{test_url}"}}'
            )

            assert result["response_type"] == "open_window"
            assert result["response"]["url"] == test_url

    def test_open_external_url_in_window_tool_signature(self):
        """Test that open_external_url_in_window tool has correct parameter schema."""
        schema = open_external_url_in_window.params_json_schema
        assert "properties" in schema
        params = schema["properties"]
        assert "url" in params
        assert params["url"]["type"] == "string"

    def test_open_external_url_in_window_docstring(self):
        """Test that open_external_url_in_window has appropriate description."""
        description = open_external_url_in_window.description.lower()
        assert "opens a url" in description
        # Check for browser window concept instead of exact phrase
        assert "browser window" in description or "window" in description


class TestOpenExternalUrlInTabTool:
    """Test the open_external_url_in_tab tool."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock context wrapper."""
        mock_ctx = Mock(spec=ChatContext)
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx
        return mock_wrapper

    @pytest.mark.asyncio
    async def test_open_external_url_in_tab_success(self, mock_context):
        """Test successful URL opening in a new tab."""
        test_url = "https://example.com"

        result = await open_external_url_in_tab.on_invoke_tool(
            mock_context,
            f'{{"url": "{test_url}"}}'
        )

        # Verify response structure
        assert result["response_type"] == "open_tab"
        assert result["agent_name"] == "OpenExternalUrl"
        assert result["response"]["url"] == test_url
        assert result["display_response"] is True

    @pytest.mark.asyncio
    async def test_open_external_url_in_tab_with_fragment(self, mock_context):
        """Test opening URL with fragment/anchor in a new tab."""
        test_url = "https://example.com/page#section"

        result = await open_external_url_in_tab.on_invoke_tool(
            mock_context,
            f'{{"url": "{test_url}"}}'
        )

        assert result["response_type"] == "open_tab"
        assert result["response"]["url"] == test_url

    @pytest.mark.asyncio
    async def test_open_external_url_in_tab_localhost(self, mock_context):
        """Test opening localhost URLs in a new tab."""
        test_urls = [
            "http://localhost:3000",
            "http://127.0.0.1:8080",
            "http://localhost/path"
        ]

        for test_url in test_urls:
            result = await open_external_url_in_tab.on_invoke_tool(
                mock_context,
                f'{{"url": "{test_url}"}}'
            )

            assert result["response_type"] == "open_tab"
            assert result["response"]["url"] == test_url

    @pytest.mark.asyncio
    async def test_open_external_url_in_tab_long_url(self, mock_context):
        """Test opening very long URLs in a new tab."""
        test_url = "https://example.com/" + "a" * 1000 + "?param=" + "b" * 500

        result = await open_external_url_in_tab.on_invoke_tool(
            mock_context,
            f'{{"url": "{test_url}"}}'
        )

        assert result["response_type"] == "open_tab"
        assert result["response"]["url"] == test_url

    def test_open_external_url_in_tab_tool_signature(self):
        """Test that open_external_url_in_tab tool has correct parameter schema."""
        schema = open_external_url_in_tab.params_json_schema
        assert "properties" in schema
        params = schema["properties"]
        assert "url" in params
        assert params["url"]["type"] == "string"

    def test_open_external_url_in_tab_docstring(self):
        """Test that open_external_url_in_tab has appropriate description."""
        description = open_external_url_in_tab.description.lower()
        assert "opens a url" in description
        assert "new" in description and "tab" in description


class TestOpenExternalUrlResponseTypes:
    """Test the response types used by open external URL tools."""

    def test_open_window_response_structure(self):
        """Test OpenWindowResponse structure and behavior."""
        agent_name = "TestAgent"
        url = "https://example.com"

        response = OpenWindowResponse(agent_name, url)
        result = response.to_dict()

        # Verify required fields
        assert result["response_type"] == "open_window"
        assert result["agent_name"] == agent_name
        assert result["response"]["url"] == url
        assert result["display_response"] is True

    def test_open_tab_response_structure(self):
        """Test OpenTabResponse structure and behavior."""
        agent_name = "TestAgent"
        url = "https://example.com"

        response = OpenTabResponse(agent_name, url)
        result = response.to_dict()

        # Verify required fields
        assert result["response_type"] == "open_tab"
        assert result["agent_name"] == agent_name
        assert result["response"]["url"] == url
        assert result["display_response"] is True

    def test_response_type_consistency(self):
        """Test that both response types have consistent structure."""
        url = "https://example.com"

        window_response = OpenWindowResponse("Agent", url).to_dict()
        tab_response = OpenTabResponse("Agent", url).to_dict()

        # Both should have same fields except response_type
        assert set(window_response.keys()) == set(tab_response.keys())
        assert window_response["response_type"] == "open_window"
        assert tab_response["response_type"] == "open_tab"


class TestOpenExternalUrlErrorHandling:
    """Test error handling for open external URL functions."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock context wrapper."""
        mock_ctx = Mock(spec=ChatContext)
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx
        return mock_wrapper

    @pytest.mark.asyncio
    async def test_missing_url_parameter_window(self, mock_context):
        """Test open_external_url_in_window with missing URL parameter."""
        result = await open_external_url_in_window.on_invoke_tool(
            mock_context,
            '{}'
        )

        # The function tool framework catches missing parameters
        assert isinstance(result, str)
        assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_missing_url_parameter_tab(self, mock_context):
        """Test open_external_url_in_tab with missing URL parameter."""
        result = await open_external_url_in_tab.on_invoke_tool(
            mock_context,
            '{}'
        )

        # The function tool framework catches missing parameters
        assert isinstance(result, str)
        assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_invalid_json_window(self, mock_context):
        """Test open_external_url_in_window with invalid JSON."""
        result = await open_external_url_in_window.on_invoke_tool(
            mock_context,
            'invalid json'
        )

        # The function tool framework catches JSON parse errors
        assert isinstance(result, str)
        assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_invalid_json_tab(self, mock_context):
        """Test open_external_url_in_tab with invalid JSON."""
        result = await open_external_url_in_tab.on_invoke_tool(
            mock_context,
            'invalid json'
        )

        # The function tool framework catches JSON parse errors
        assert isinstance(result, str)
        assert "error" in result.lower()


class TestOpenExternalUrlIntegration:
    """Integration tests for open external URL components."""

    def test_all_imports_work(self):
        """Test that all imports work correctly."""
        try:
            from connectors.open_external_url import (
                OPEN_EXTERNAL_URL_AGENT,
                open_external_url_in_window,
                open_external_url_in_tab
            )

            # Basic validation
            assert OPEN_EXTERNAL_URL_AGENT is not None
            assert hasattr(open_external_url_in_window, 'on_invoke_tool')
            assert callable(open_external_url_in_window.on_invoke_tool)
            assert hasattr(open_external_url_in_tab, 'on_invoke_tool')
            assert callable(open_external_url_in_tab.on_invoke_tool)

        except ImportError as e:
            pytest.fail(f"Failed to import open_external_url components: {e}")

    def test_agent_tools_registration(self):
        """Test that tools are properly registered with the agent."""
        tool_names = [tool.name for tool in OPEN_EXTERNAL_URL_AGENT.tools]
        assert "open_external_url_in_window" in tool_names
        assert "open_external_url_in_tab" in tool_names

    def test_agent_model_configuration(self):
        """Test that agent uses correct model."""
        assert OPEN_EXTERNAL_URL_AGENT.model == "gpt-4o"

    def test_commented_out_function(self):
        """Test that the commented out open_external_url function is not available."""
        import connectors.open_external_url as module

        # The commented out function should not be available
        assert not hasattr(module, 'open_external_url')

    def test_tool_functions_are_function_tools(self):
        """Test that tool functions are properly decorated with @function_tool."""
        from agents import FunctionTool

        assert hasattr(open_external_url_in_window, 'params_json_schema')
        assert hasattr(open_external_url_in_tab, 'params_json_schema')

        # They should have the function tool attributes
        assert hasattr(open_external_url_in_window, 'on_invoke_tool')
        assert hasattr(open_external_url_in_tab, 'on_invoke_tool')


class TestOpenExternalUrlEdgeCases:
    """Test edge cases for open external URL functionality."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock context wrapper."""
        mock_ctx = Mock(spec=ChatContext)
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx
        return mock_wrapper

    @pytest.mark.asyncio
    async def test_empty_url_string_window(self, mock_context):
        """Test open_external_url_in_window with empty URL string."""
        result = await open_external_url_in_window.on_invoke_tool(
            mock_context,
            '{"url": ""}'
        )

        # Should still return a valid response with empty URL
        assert result["response_type"] == "open_window"
        assert result["response"]["url"] == ""

    @pytest.mark.asyncio
    async def test_empty_url_string_tab(self, mock_context):
        """Test open_external_url_in_tab with empty URL string."""
        result = await open_external_url_in_tab.on_invoke_tool(
            mock_context,
            '{"url": ""}'
        )

        # Should still return a valid response with empty URL
        assert result["response_type"] == "open_tab"
        assert result["response"]["url"] == ""

    @pytest.mark.asyncio
    async def test_url_with_unicode_characters(self, mock_context):
        """Test URLs with unicode characters."""
        test_url = "https://example.com/測試/página/страница"

        result = await open_external_url_in_window.on_invoke_tool(
            mock_context,
            f'{{"url": "{test_url}"}}'
        )

        assert result["response_type"] == "open_window"
        assert result["response"]["url"] == test_url

    @pytest.mark.asyncio
    async def test_relative_url_handling(self, mock_context):
        """Test handling of relative URLs."""
        relative_urls = ["/path/to/page", "../page", "./page", "page.html"]

        for url in relative_urls:
            result = await open_external_url_in_tab.on_invoke_tool(
                mock_context,
                f'{{"url": "{url}"}}'
            )

            assert result["response_type"] == "open_tab"
            assert result["response"]["url"] == url

    def test_module_exports(self):
        """Test that the module exports the expected items."""
        import connectors.open_external_url as module

        # Check expected exports
        expected_exports = [
            'OPEN_EXTERNAL_URL_AGENT',
            'open_external_url_in_window',
            'open_external_url_in_tab'
        ]

        for export in expected_exports:
            assert hasattr(module, export), f"Missing export: {export}"

    def test_no_all_tools_export(self):
        """Test that there's no ALL_TOOLS export (unlike other connectors)."""
        import connectors.open_external_url as module

        # This connector doesn't export ALL_TOOLS
        assert not hasattr(module, 'ALL_TOOLS')
