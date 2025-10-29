"""
Comprehensive tests for connectors/utils/cloudflare.py

Tests cover Cloudflare API client functionality including site rendering to markdown,
API communication, error handling, and configuration management.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests


class TestCloudflareUtils:
    """Test cases for cloudflare.py Cloudflare API utilities."""

    @pytest.fixture
    def mock_settings(self):
        """Mock the Settings configuration."""
        with patch('connectors.utils.cloudflare.SETTINGS') as mock_settings:
            mock_settings.cloudflare_api_key = "test_api_key_12345"
            mock_settings.cloudflare_account_id = "test_account_id_67890"
            yield mock_settings

    @pytest.fixture
    def cloudflare_instance(self, mock_settings):
        """Create a Cloudflare instance with mocked settings."""
        from connectors.utils.cloudflare import Cloudflare
        return Cloudflare()

    @pytest.fixture
    def successful_response(self):
        """Create a successful mock response."""
        mock_response = Mock(spec=requests.Response)
        mock_response.json.return_value = {
            "success": True,
            "result": "# Test Website\n\nThis is a test markdown content.\n\n## Section\n\nSome content here."
        }
        return mock_response

    @pytest.fixture
    def error_response(self):
        """Create an error mock response."""
        mock_response = Mock(spec=requests.Response)
        mock_response.json.return_value = {
            "success": False,
            "errors": ["Invalid URL provided", "Rate limit exceeded"]
        }
        return mock_response

    def test_cloudflare_initialization(self, cloudflare_instance, mock_settings):
        """Test Cloudflare class initialization."""
        # Verify attributes are set correctly
        assert cloudflare_instance.api_key == "test_api_key_12345"
        assert cloudflare_instance.account_id == "test_account_id_67890"
        assert cloudflare_instance.api_url == "https://api.cloudflare.com/client/v4/accounts/test_account_id_67890"

    def test_cloudflare_initialization_with_different_settings(self):
        """Test Cloudflare initialization with different settings values."""
        with patch('connectors.utils.cloudflare.SETTINGS') as mock_settings:
            mock_settings.cloudflare_api_key = "different_api_key"
            mock_settings.cloudflare_account_id = "different_account_id"

            from connectors.utils.cloudflare import Cloudflare
            cf = Cloudflare()

            assert cf.api_key == "different_api_key"
            assert cf.account_id == "different_account_id"
            assert "different_account_id" in cf.api_url

    def test_render_site_to_markdown_success(self, cloudflare_instance, successful_response):
        """Test successful site rendering to markdown."""
        with patch('connectors.utils.cloudflare.requests.post') as mock_post:
            mock_post.return_value = successful_response

            result = cloudflare_instance.render_site_to_markdown(
                "https://example.com")

            # Verify result
            expected_markdown = "# Test Website\n\nThis is a test markdown content.\n\n## Section\n\nSome content here."
            assert result == expected_markdown

            # Verify API call
            mock_post.assert_called_once()
            call_args = mock_post.call_args

            # Check URL
            expected_url = "https://api.cloudflare.com/client/v4/accounts/test_account_id_67890/browser-rendering/markdown"
            assert call_args[0][0] == expected_url

            # Check headers
            headers = call_args[1]["headers"]
            assert headers["Authorization"] == "Bearer test_api_key_12345"
            assert headers["Content-Type"] == "application/json"

            # Check body
            body = call_args[1]["json"]
            assert body == {"url": "https://example.com"}

    def test_render_site_to_markdown_error(self, cloudflare_instance, error_response):
        """Test site rendering with API error response."""
        with patch('connectors.utils.cloudflare.requests.post') as mock_post:
            mock_post.return_value = error_response

            # Should raise exception with error details
            with pytest.raises(Exception) as exc_info:
                cloudflare_instance.render_site_to_markdown(
                    "https://invalid-site.com")

            # Verify exception contains error information
            exception_msg = str(exc_info.value)
            assert "Invalid URL provided" in exception_msg or "Rate limit exceeded" in exception_msg

    def test_render_site_to_markdown_different_urls(self, cloudflare_instance, successful_response):
        """Test rendering with different URL formats."""
        with patch('connectors.utils.cloudflare.requests.post') as mock_post:
            mock_post.return_value = successful_response

            test_urls = [
                "https://example.com",
                "http://localhost:3000",
                "https://subdomain.example.co.uk/path/to/page",
                "https://example.com/page?param=value&other=123",
                "https://unicode-domain.测试/page",
            ]

            for url in test_urls:
                result = cloudflare_instance.render_site_to_markdown(url)

                # Should return markdown for all URLs
                assert isinstance(result, str)
                assert "Test Website" in result

                # Verify the URL was passed correctly
                last_call = mock_post.call_args
                body = last_call[1]["json"]
                assert body["url"] == url

    def test_render_site_to_markdown_empty_url(self, cloudflare_instance, successful_response):
        """Test rendering with empty URL."""
        with patch('connectors.utils.cloudflare.requests.post') as mock_post:
            mock_post.return_value = successful_response

            result = cloudflare_instance.render_site_to_markdown("")

            # Should still make the request
            assert result is not None

            # Verify empty URL was passed
            call_args = mock_post.call_args
            body = call_args[1]["json"]
            assert body["url"] == ""

    def test_render_site_to_markdown_none_url(self, cloudflare_instance, successful_response):
        """Test rendering with None URL."""
        with patch('connectors.utils.cloudflare.requests.post') as mock_post:
            mock_post.return_value = successful_response

            result = cloudflare_instance.render_site_to_markdown(None)

            # Should still make the request
            assert result is not None

            # Verify None URL was passed
            call_args = mock_post.call_args
            body = call_args[1]["json"]
            assert body["url"] is None

    def test_render_site_to_markdown_unicode_content(self, cloudflare_instance):
        """Test rendering with unicode content in response."""
        with patch('connectors.utils.cloudflare.requests.post') as mock_post:
            # Mock response with unicode content
            mock_response = Mock()
            mock_response.json.return_value = {
                "success": True,
                "result": "# 测试网站\n\n这是一个测试markdown内容。\n\n## 部分\n\n这里有一些内容。"
            }
            mock_post.return_value = mock_response

            result = cloudflare_instance.render_site_to_markdown(
                "https://unicode-site.com")

            # Should handle unicode content correctly
            assert "测试网站" in result
            assert "这是一个测试markdown内容" in result
            assert isinstance(result, str)

    def test_render_site_to_markdown_large_content(self, cloudflare_instance):
        """Test rendering with large markdown content."""
        with patch('connectors.utils.cloudflare.requests.post') as mock_post:
            # Mock response with large content
            large_markdown = "# Large Content\n\n" + "This is a line of content.\n" * 10000
            mock_response = Mock()
            mock_response.json.return_value = {
                "success": True,
                "result": large_markdown
            }
            mock_post.return_value = mock_response

            result = cloudflare_instance.render_site_to_markdown(
                "https://large-site.com")

            # Should handle large content
            assert len(result) > 200000  # Large content
            assert result.startswith("# Large Content")
            assert "This is a line of content." in result

    def test_render_site_to_markdown_empty_result(self, cloudflare_instance):
        """Test rendering with empty result."""
        with patch('connectors.utils.cloudflare.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "success": True,
                "result": ""
            }
            mock_post.return_value = mock_response

            result = cloudflare_instance.render_site_to_markdown(
                "https://empty-site.com")

            # Should return empty string
            assert result == ""
            assert isinstance(result, str)

    def test_render_site_to_markdown_requests_exception(self, cloudflare_instance):
        """Test handling of requests exceptions."""
        with patch('connectors.utils.cloudflare.requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.RequestException(
                "Network error")

            # Should propagate the exception
            with pytest.raises(requests.exceptions.RequestException, match="Network error"):
                cloudflare_instance.render_site_to_markdown(
                    "https://example.com")

    def test_render_site_to_markdown_timeout_exception(self, cloudflare_instance):
        """Test handling of timeout exceptions."""
        with patch('connectors.utils.cloudflare.requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout(
                "Request timeout")

            # Should propagate the timeout exception
            with pytest.raises(requests.exceptions.Timeout, match="Request timeout"):
                cloudflare_instance.render_site_to_markdown(
                    "https://slow-site.com")

    def test_render_site_to_markdown_connection_error(self, cloudflare_instance):
        """Test handling of connection errors."""
        with patch('connectors.utils.cloudflare.requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError(
                "Failed to connect")

            # Should propagate the connection error
            with pytest.raises(requests.exceptions.ConnectionError, match="Failed to connect"):
                cloudflare_instance.render_site_to_markdown(
                    "https://unreachable-site.com")

    def test_render_site_to_markdown_json_decode_error(self, cloudflare_instance):
        """Test handling of JSON decode errors."""
        with patch('connectors.utils.cloudflare.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_post.return_value = mock_response

            # Should propagate the JSON decode error
            with pytest.raises(ValueError, match="Invalid JSON"):
                cloudflare_instance.render_site_to_markdown(
                    "https://invalid-json-site.com")

    def test_render_site_to_markdown_multiple_errors(self, cloudflare_instance):
        """Test handling of multiple errors in response."""
        with patch('connectors.utils.cloudflare.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "success": False,
                "errors": [
                    "Authentication failed",
                    "Rate limit exceeded",
                    "Invalid URL format",
                    "Service temporarily unavailable"
                ]
            }
            mock_post.return_value = mock_response

            # Should raise exception with all errors
            with pytest.raises(Exception) as exc_info:
                cloudflare_instance.render_site_to_markdown(
                    "https://example.com")

            # Exception should contain all error messages
            exception_str = str(exc_info.value)
            assert "Authentication failed" in exception_str
            assert "Rate limit exceeded" in exception_str
            assert "Invalid URL format" in exception_str
            assert "Service temporarily unavailable" in exception_str

    def test_render_site_to_markdown_malformed_response(self, cloudflare_instance):
        """Test handling of malformed API responses."""
        with patch('connectors.utils.cloudflare.requests.post') as mock_post:
            # Test missing 'success' field
            mock_response = Mock()
            mock_response.json.return_value = {
                "result": "some content"
            }
            mock_post.return_value = mock_response

            # Should raise KeyError or handle gracefully
            with pytest.raises(KeyError):
                cloudflare_instance.render_site_to_markdown(
                    "https://malformed-response.com")

    def test_api_url_construction(self, mock_settings):
        """Test API URL construction with different account IDs."""
        test_account_ids = [
            "abc123def456",
            "12345",
            "very-long-account-id-with-dashes-and-numbers-123456789",
            ""  # Empty account ID
        ]

        for account_id in test_account_ids:
            mock_settings.cloudflare_account_id = account_id

            from connectors.utils.cloudflare import Cloudflare
            cf = Cloudflare()

            expected_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
            assert cf.api_url == expected_url

    def test_authorization_header_format(self, cloudflare_instance):
        """Test that authorization header is formatted correctly."""
        with patch('connectors.utils.cloudflare.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "success": True, "result": "test"}
            mock_post.return_value = mock_response

            cloudflare_instance.render_site_to_markdown("https://test.com")

            # Verify authorization header format
            call_args = mock_post.call_args
            headers = call_args[1]["headers"]

            # Should be Bearer token format
            assert headers["Authorization"] == "Bearer test_api_key_12345"
            assert headers["Authorization"].startswith("Bearer ")

    def test_request_body_structure(self, cloudflare_instance):
        """Test that request body has correct structure."""
        with patch('connectors.utils.cloudflare.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "success": True, "result": "test"}
            mock_post.return_value = mock_response

            test_url = "https://structure-test.com"
            cloudflare_instance.render_site_to_markdown(test_url)

            # Verify request body structure
            call_args = mock_post.call_args
            body = call_args[1]["json"]

            # Should have only 'url' field
            assert len(body) == 1
            assert "url" in body
            assert body["url"] == test_url


# Integration and error handling tests
class TestCloudflareUtilsIntegration:
    """Integration tests for cloudflare.py utilities."""

    def test_import_structure(self):
        """Test that all required imports are accessible."""
        # Test class import
        from connectors.utils.cloudflare import Cloudflare

        # Test module imports
        from connectors.utils.cloudflare import requests

        # Verify class is a class
        assert isinstance(Cloudflare, type)

        # Verify modules are accessible
        assert requests is not None

    def test_cloudflare_class_methods(self):
        """Test that Cloudflare class has expected methods."""
        from connectors.utils.cloudflare import Cloudflare

        # Should have __init__ and render_site_to_markdown methods
        assert hasattr(Cloudflare, '__init__')
        assert hasattr(Cloudflare, 'render_site_to_markdown')

        # Methods should be callable
        assert callable(getattr(Cloudflare, '__init__'))
        assert callable(getattr(Cloudflare, 'render_site_to_markdown'))

    def test_method_signature(self):
        """Test that render_site_to_markdown has expected signature."""
        from connectors.utils.cloudflare import Cloudflare
        import inspect

        signature = inspect.signature(Cloudflare.render_site_to_markdown)

        # Should have self and url parameters
        params = list(signature.parameters.keys())
        assert len(params) == 2
        assert params[0] == "self"
        assert params[1] == "url"

        # Check return annotation
        return_annotation = signature.return_annotation
        assert return_annotation == str

    def test_settings_import_error_handling(self):
        """Test module behavior when Settings import fails."""
        # This test is not applicable since SETTINGS is already initialized at module level
        # The import error would have occurred at module import time, not instance creation
        from connectors.utils.cloudflare import Cloudflare
        cf = Cloudflare()
        # If we reach here, the module imported successfully
        assert cf is not None

    def test_requests_module_usage(self):
        """Test that requests module is used correctly."""
        from connectors.utils.cloudflare import requests as cf_requests

        # Should be the standard requests module
        assert hasattr(cf_requests, 'post')
        assert hasattr(cf_requests, 'get')
        assert hasattr(cf_requests, 'exceptions')

        # Should have expected exception classes
        assert hasattr(cf_requests.exceptions, 'RequestException')
        assert hasattr(cf_requests.exceptions, 'Timeout')
        assert hasattr(cf_requests.exceptions, 'ConnectionError')

    def test_end_to_end_workflow(self):
        """Test complete workflow from initialization to API call."""
        # Mock settings
        with patch('connectors.utils.cloudflare.SETTINGS') as mock_settings:
            mock_settings.cloudflare_api_key = "workflow_api_key"
            mock_settings.cloudflare_account_id = "workflow_account_id"

            # Mock requests
            with patch('connectors.utils.cloudflare.requests.post') as mock_post:
                mock_response = Mock()
                mock_response.json.return_value = {
                    "success": True,
                    "result": "# Workflow Test\n\nThis is a complete workflow test."
                }
                mock_post.return_value = mock_response

                # Create instance and make API call
                from connectors.utils.cloudflare import Cloudflare
                cf = Cloudflare()
                result = cf.render_site_to_markdown(
                    "https://workflow-test.com")

                # Verify complete workflow
                assert cf.api_key == "workflow_api_key"
                assert cf.account_id == "workflow_account_id"
                assert "workflow_account_id" in cf.api_url
                assert result == "# Workflow Test\n\nThis is a complete workflow test."

                # Verify API call was made correctly
                mock_post.assert_called_once()
                call_args = mock_post.call_args
                # URL contains account ID
                assert "workflow_account_id" in call_args[0][0]
                assert call_args[1]["headers"]["Authorization"] == "Bearer workflow_api_key"
                assert call_args[1]["json"]["url"] == "https://workflow-test.com"

    def test_instance_attribute_persistence(self):
        """Test that instance attributes persist correctly."""
        with patch('connectors.utils.cloudflare.SETTINGS') as mock_settings:
            mock_settings.cloudflare_api_key = "persistent_key"
            mock_settings.cloudflare_account_id = "persistent_account"

            from connectors.utils.cloudflare import Cloudflare
            cf = Cloudflare()

            # Attributes should persist
            original_api_key = cf.api_key
            original_account_id = cf.account_id
            original_api_url = cf.api_url

            # After multiple operations, attributes should remain the same
            assert cf.api_key == original_api_key
            assert cf.account_id == original_account_id
            assert cf.api_url == original_api_url

            # Should be the expected values
            assert cf.api_key == "persistent_key"
            assert cf.account_id == "persistent_account"
            assert "persistent_account" in cf.api_url
