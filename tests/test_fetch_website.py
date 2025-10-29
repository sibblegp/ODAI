"""
Comprehensive tests for connectors/fetch_website.py

Tests cover the Fetch Website agent, its tools, and various edge cases.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from agents import Agent
from connectors.fetch_website import (
    FETCH_WEBSITE_AGENT,
    REALTIME_FETCH_WEBSITE_AGENT,
    fetch_website,
    ALL_TOOLS
)


class TestFetchWebsiteConfig:
    """Test Fetch Website agent configuration and setup."""

    def test_fetch_website_agent_exists(self):
        """Test that FETCH_WEBSITE_AGENT is properly configured."""
        assert FETCH_WEBSITE_AGENT is not None
        assert isinstance(FETCH_WEBSITE_AGENT, Agent)
        assert FETCH_WEBSITE_AGENT.name == "Fetch Website"
        assert FETCH_WEBSITE_AGENT.model == "gpt-4o"
        assert len(FETCH_WEBSITE_AGENT.tools) == 1

    def test_realtime_fetch_website_agent_exists(self):
        """Test that REALTIME_FETCH_WEBSITE_AGENT is properly configured."""
        assert REALTIME_FETCH_WEBSITE_AGENT is not None
        assert REALTIME_FETCH_WEBSITE_AGENT.name == "Fetch Website"
        assert len(REALTIME_FETCH_WEBSITE_AGENT.tools) == 1

    def test_all_tools_exported(self):
        """Test that ALL_TOOLS contains expected tools."""
        assert len(ALL_TOOLS) == 1
        assert fetch_website in ALL_TOOLS

    def test_agent_instructions_configured(self):
        """Test that agent instructions are properly set."""
        assert FETCH_WEBSITE_AGENT.instructions is not None
        assert "Fetch websites" in FETCH_WEBSITE_AGENT.instructions
        assert "markdown" in FETCH_WEBSITE_AGENT.instructions

    def test_agent_handoff_description_configured(self):
        """Test that agent handoff description is properly set."""
        assert FETCH_WEBSITE_AGENT.handoff_description is not None
        assert "Fetch website" in FETCH_WEBSITE_AGENT.handoff_description


class TestFetchWebsiteTool:
    """Test the fetch_website tool."""

    @patch('connectors.fetch_website.Cloudflare')
    @pytest.mark.asyncio
    async def test_fetch_website_success(self, mock_cloudflare_class):
        """Test successful website fetching."""
        # Mock Cloudflare instance and response
        mock_cloudflare = Mock()
        mock_cloudflare.render_site_to_markdown.return_value = {
            "title": "Example Website",
            "content": "# Example Website\n\nThis is example content in markdown format.",
            "url": "https://example.com",
            "status": "success"
        }
        mock_cloudflare_class.return_value = mock_cloudflare

        # Mock the tool context
        mock_ctx = Mock()

        result = await fetch_website.on_invoke_tool(
            mock_ctx,
            '{"url": "https://example.com"}'
        )

        # Verify Cloudflare was called correctly
        mock_cloudflare_class.assert_called_once()
        mock_cloudflare.render_site_to_markdown.assert_called_once_with(
            "https://example.com")

        # Verify response structure
        assert result["response_type"] == "website_content"
        assert result["agent_name"] == "Website"
        assert result["friendly_name"] == "Website Content"
        assert result["response"]["title"] == "Example Website"
        assert "# Example Website" in result["response"]["content"]

    @patch('connectors.fetch_website.Cloudflare')
    @pytest.mark.asyncio
    async def test_fetch_website_with_complex_url(self, mock_cloudflare_class):
        """Test fetching website with complex URL structure."""
        mock_cloudflare = Mock()
        mock_cloudflare.render_site_to_markdown.return_value = {
            "title": "Blog Post - My Website",
            "content": "# Blog Post\n\nThis is a blog post with some content.",
            "url": "https://blog.example.com/posts/2023/my-post?utm_source=test&utm_medium=email",
            "status": "success"
        }
        mock_cloudflare_class.return_value = mock_cloudflare

        # Mock the tool context
        mock_ctx = Mock()

        complex_url = "https://blog.example.com/posts/2023/my-post?utm_source=test&utm_medium=email"
        result = await fetch_website.on_invoke_tool(
            mock_ctx,
            f'{{"url": "{complex_url}"}}'
        )

        # Verify URL was passed correctly
        mock_cloudflare.render_site_to_markdown.assert_called_once_with(
            complex_url)
        assert result["response"]["title"] == "Blog Post - My Website"

    @patch('connectors.fetch_website.Cloudflare')
    @pytest.mark.asyncio
    async def test_fetch_website_cloudflare_error(self, mock_cloudflare_class):
        """Test handling of Cloudflare service errors."""
        mock_cloudflare = Mock()
        mock_cloudflare.render_site_to_markdown.side_effect = Exception(
            "Cloudflare API Error")
        mock_cloudflare_class.return_value = mock_cloudflare

        # Mock the tool context
        mock_ctx = Mock()

        result = await fetch_website.on_invoke_tool(
            mock_ctx,
            '{"url": "https://example.com"}'
        )

        # The function tool framework catches exceptions and returns error message as string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()

    @patch('connectors.fetch_website.Cloudflare')
    @pytest.mark.asyncio
    async def test_fetch_website_invalid_url(self, mock_cloudflare_class):
        """Test handling of invalid URLs."""
        mock_cloudflare = Mock()
        mock_cloudflare.render_site_to_markdown.return_value = {
            "error": "Invalid URL format",
            "status": "error"
        }
        mock_cloudflare_class.return_value = mock_cloudflare

        # Mock the tool context
        mock_ctx = Mock()

        result = await fetch_website.on_invoke_tool(
            mock_ctx,
            '{"url": "not-a-valid-url"}'
        )

        # Verify error response is passed through
        assert result["response"]["error"] == "Invalid URL format"
        assert result["response"]["status"] == "error"

    @patch('connectors.fetch_website.Cloudflare')
    @pytest.mark.asyncio
    async def test_fetch_website_empty_content(self, mock_cloudflare_class):
        """Test handling of websites with no content."""
        mock_cloudflare = Mock()
        mock_cloudflare.render_site_to_markdown.return_value = {
            "title": "Empty Page",
            "content": "",
            "url": "https://empty.example.com",
            "status": "success"
        }
        mock_cloudflare_class.return_value = mock_cloudflare

        # Mock the tool context
        mock_ctx = Mock()

        result = await fetch_website.on_invoke_tool(
            mock_ctx,
            '{"url": "https://empty.example.com"}'
        )

        # Verify empty content is handled
        assert result["response"]["content"] == ""
        assert result["response"]["title"] == "Empty Page"

    @patch('connectors.fetch_website.Cloudflare')
    @pytest.mark.asyncio
    async def test_fetch_website_large_content(self, mock_cloudflare_class):
        """Test handling of websites with large content."""
        mock_cloudflare = Mock()
        large_content = "# Large Content\n" + \
            ("This is a lot of content. " * 1000)
        mock_cloudflare.render_site_to_markdown.return_value = {
            "title": "Large Website",
            "content": large_content,
            "url": "https://large.example.com",
            "status": "success"
        }
        mock_cloudflare_class.return_value = mock_cloudflare

        # Mock the tool context
        mock_ctx = Mock()

        result = await fetch_website.on_invoke_tool(
            mock_ctx,
            '{"url": "https://large.example.com"}'
        )

        # Verify large content is handled
        assert len(result["response"]["content"]) > 1000
        assert result["response"]["title"] == "Large Website"

    @patch('connectors.fetch_website.Cloudflare')
    @pytest.mark.asyncio
    async def test_fetch_website_with_redirects(self, mock_cloudflare_class):
        """Test handling of URLs that redirect."""
        mock_cloudflare = Mock()
        mock_cloudflare.render_site_to_markdown.return_value = {
            "title": "Redirected Content",
            "content": "# Final Destination\n\nThis is the final content after redirect.",
            "url": "https://final.example.com",
            "original_url": "https://redirect.example.com",
            "status": "success"
        }
        mock_cloudflare_class.return_value = mock_cloudflare

        # Mock the tool context
        mock_ctx = Mock()

        result = await fetch_website.on_invoke_tool(
            mock_ctx,
            '{"url": "https://redirect.example.com"}'
        )

        # Verify redirect handling
        assert result["response"]["url"] == "https://final.example.com"
        assert result["response"]["original_url"] == "https://redirect.example.com"

    @patch('connectors.fetch_website.Cloudflare')
    @pytest.mark.asyncio
    async def test_fetch_website_timeout_error(self, mock_cloudflare_class):
        """Test handling of timeout errors."""
        mock_cloudflare = Mock()
        mock_cloudflare.render_site_to_markdown.side_effect = TimeoutError(
            "Request timed out")
        mock_cloudflare_class.return_value = mock_cloudflare

        # Mock the tool context
        mock_ctx = Mock()

        result = await fetch_website.on_invoke_tool(
            mock_ctx,
            '{"url": "https://slow.example.com"}'
        )

        # The function tool framework catches exceptions and returns error message as string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()

    @patch('connectors.fetch_website.Cloudflare')
    @pytest.mark.asyncio
    async def test_fetch_website_with_special_characters(self, mock_cloudflare_class):
        """Test fetching website with special characters in URL."""
        mock_cloudflare = Mock()
        mock_cloudflare.render_site_to_markdown.return_value = {
            "title": "página en español",
            "content": "# Contenido en español\n\nEste es contenido con caracteres especiales: ñáéíóú",
            "url": "https://español.example.com/página",
            "status": "success"
        }
        mock_cloudflare_class.return_value = mock_cloudflare

        # Mock the tool context
        mock_ctx = Mock()

        special_url = "https://español.example.com/página"
        result = await fetch_website.on_invoke_tool(
            mock_ctx,
            f'{{"url": "{special_url}"}}'
        )

        # Verify special characters are handled
        assert "ñáéíóú" in result["response"]["content"]
        assert result["response"]["title"] == "página en español"


class TestFetchWebsiteAgentIntegration:
    """Integration tests for Fetch Website agent components."""

    def test_agent_tools_registration(self):
        """Test that tools are properly registered with the agent."""
        tool_names = [tool.name for tool in FETCH_WEBSITE_AGENT.tools]
        assert "fetch_website" in tool_names

    def test_agent_model_configuration(self):
        """Test that agent uses correct model."""
        assert FETCH_WEBSITE_AGENT.model == "gpt-4o"

    def test_realtime_agent_tools_registration(self):
        """Test that realtime agent has same tools as regular agent."""
        regular_tool_names = [tool.name for tool in FETCH_WEBSITE_AGENT.tools]
        realtime_tool_names = [
            tool.name for tool in REALTIME_FETCH_WEBSITE_AGENT.tools]
        assert set(regular_tool_names) == set(realtime_tool_names)

    def test_import_dependencies(self):
        """Test that agent dependencies are properly imported."""
        # This test ensures the import structure works
        try:
            from connectors.fetch_website import (
                FETCH_WEBSITE_AGENT,
                fetch_website
            )
            assert FETCH_WEBSITE_AGENT is not None
            assert fetch_website is not None
        except ImportError as e:
            pytest.fail(f"Failed to import Fetch Website components: {e}")


class TestFetchWebsiteEdgeCases:
    """Test edge cases and error conditions."""

    def test_tool_function_signature(self):
        """Test that tool function has correct parameter schema."""
        schema = fetch_website.params_json_schema
        assert "properties" in schema
        params = schema["properties"]
        assert "url" in params
        assert params["url"]["type"] == "string"

    @pytest.mark.asyncio
    async def test_tool_response_format_consistency(self):
        """Test that tool returns consistent ToolResponse format."""
        with patch('connectors.fetch_website.Cloudflare') as mock_cloudflare_class:
            mock_cloudflare = Mock()
            mock_cloudflare.render_site_to_markdown.return_value = {
                "title": "Test",
                "content": "Test content",
                "status": "success"
            }
            mock_cloudflare_class.return_value = mock_cloudflare

            # Mock the tool context
            mock_ctx = Mock()

            result = await fetch_website.on_invoke_tool(
                mock_ctx,
                '{"url": "https://example.com"}'
            )

            # Verify ToolResponse format
            required_fields = ["response_type",
                               "agent_name", "friendly_name", "response"]
            for field in required_fields:
                assert field in result

            assert result["response_type"] == "website_content"
            assert result["agent_name"] == "Website"
            assert result["friendly_name"] == "Website Content"

    def test_agent_name_consistency(self):
        """Test that agent names are consistent across instances."""
        assert FETCH_WEBSITE_AGENT.name == REALTIME_FETCH_WEBSITE_AGENT.name == "Fetch Website"

    def test_all_tools_contains_all_functions(self):
        """Test that ALL_TOOLS exports all available tool functions."""
        expected_tools = [fetch_website]
        assert len(ALL_TOOLS) == len(expected_tools)
        for tool in expected_tools:
            assert tool in ALL_TOOLS

    @patch('connectors.fetch_website.Cloudflare')
    @pytest.mark.asyncio
    async def test_fetch_website_empty_url(self, mock_cloudflare_class):
        """Test handling of empty URL."""
        mock_cloudflare = Mock()
        mock_cloudflare.render_site_to_markdown.return_value = {
            "error": "URL cannot be empty",
            "status": "error"
        }
        mock_cloudflare_class.return_value = mock_cloudflare

        # Mock the tool context
        mock_ctx = Mock()

        result = await fetch_website.on_invoke_tool(
            mock_ctx,
            '{"url": ""}'
        )

        # Verify empty URL handling
        mock_cloudflare.render_site_to_markdown.assert_called_once_with("")

    def test_agent_instructions_consistency(self):
        """Test that agent instructions mention key functionality."""
        # Both regular and realtime agents should mention fetching websites
        assert "Fetch websites" in FETCH_WEBSITE_AGENT.instructions
        assert "Fetch websites" in REALTIME_FETCH_WEBSITE_AGENT.instructions
        assert "markdown" in FETCH_WEBSITE_AGENT.instructions
        assert "markdown" in REALTIME_FETCH_WEBSITE_AGENT.instructions
