"""
Comprehensive tests for connectors/utils/google.py

Tests cover Google credentials fetching, token retrieval, and error handling
for Google OAuth integration functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from google.oauth2.credentials import Credentials


class TestGoogleUtils:
    """Test cases for google.py Google credentials utilities."""

    @pytest.fixture
    def mock_google_token_class(self):
        """Mock the GoogleToken class."""
        with patch('connectors.utils.google.GoogleToken') as mock_class:
            yield mock_class

    @pytest.fixture
    def mock_credentials_class(self):
        """Mock the Google OAuth2 Credentials class."""
        with patch('connectors.utils.google.Credentials') as mock_creds_class:
            yield mock_creds_class

    @pytest.fixture
    def mock_google_account_needed_response(self):
        """Mock the GoogleAccountNeededResponse class."""
        with patch('connectors.utils.google.GoogleAccountNeededResponse') as mock_response:
            yield mock_response

    @pytest.fixture
    def sample_google_token_credentials(self):
        """Sample Google token credentials data."""
        return {
            "client_id": "test_client_id.googleusercontent.com",
            "client_secret": "test_client_secret",
            "refresh_token": "test_refresh_token",
            "type": "authorized_user"
        }

    def test_fetch_google_creds_success(self, mock_google_token_class, mock_credentials_class, sample_google_token_credentials):
        """Test successful Google credentials fetching."""
        from connectors.utils.google import fetch_google_creds

        # Setup mocks
        mock_google_token = Mock()
        mock_google_token.get_default_account_credentials.return_value = sample_google_token_credentials
        mock_google_token_class.get_tokens_by_user_id.return_value = mock_google_token

        mock_credentials = Mock(spec=Credentials)
        mock_credentials_class.from_authorized_user_info.return_value = mock_credentials

        # Call function
        result = fetch_google_creds("user_123")

        # Verify results
        assert result == mock_credentials
        mock_google_token_class.get_tokens_by_user_id.assert_called_once_with(
            "user_123")
        mock_google_token.get_default_account_credentials.assert_called_once()
        mock_credentials_class.from_authorized_user_info.assert_called_once_with(
            sample_google_token_credentials)

    def test_fetch_google_creds_no_token_found(self, mock_google_token_class, mock_credentials_class):
        """Test when no Google token is found for user."""
        from connectors.utils.google import fetch_google_creds

        # Setup mock to return None for no token found
        mock_google_token_class.get_tokens_by_user_id.return_value = None

        # Call function
        result = fetch_google_creds("user_no_token")

        # Verify results
        assert result is None
        mock_google_token_class.get_tokens_by_user_id.assert_called_once_with(
            "user_no_token")
        mock_credentials_class.from_authorized_user_info.assert_not_called()

    def test_fetch_google_creds_no_default_credentials(self, mock_google_token_class, mock_credentials_class):
        """Test when Google token exists but has no default credentials."""
        from connectors.utils.google import fetch_google_creds

        # Setup mocks
        mock_google_token = Mock()
        mock_google_token.get_default_account_credentials.return_value = None
        mock_google_token_class.get_tokens_by_user_id.return_value = mock_google_token

        # Call function
        result = fetch_google_creds("user_no_default_creds")

        # Verify results
        assert result is None
        mock_google_token_class.get_tokens_by_user_id.assert_called_once_with(
            "user_no_default_creds")
        mock_google_token.get_default_account_credentials.assert_called_once()
        mock_credentials_class.from_authorized_user_info.assert_not_called()

    def test_fetch_google_creds_empty_user_id(self, mock_google_token_class, mock_credentials_class):
        """Test with empty user ID."""
        from connectors.utils.google import fetch_google_creds

        # Setup mock
        mock_google_token_class.get_tokens_by_user_id.return_value = None

        # Call function with empty string
        result = fetch_google_creds("")

        # Verify results
        assert result is None
        mock_google_token_class.get_tokens_by_user_id.assert_called_once_with(
            "")

    def test_fetch_google_creds_none_user_id(self, mock_google_token_class, mock_credentials_class):
        """Test with None user ID."""
        from connectors.utils.google import fetch_google_creds

        # Setup mock
        mock_google_token_class.get_tokens_by_user_id.return_value = None

        # Call function with None
        result = fetch_google_creds(None)

        # Verify results
        assert result is None
        mock_google_token_class.get_tokens_by_user_id.assert_called_once_with(
            None)

    def test_fetch_google_creds_credentials_creation_error(self, mock_google_token_class, mock_credentials_class, sample_google_token_credentials):
        """Test when Credentials.from_authorized_user_info raises an error."""
        from connectors.utils.google import fetch_google_creds

        # Setup mocks
        mock_google_token = Mock()
        mock_google_token.get_default_account_credentials.return_value = sample_google_token_credentials
        mock_google_token_class.get_tokens_by_user_id.return_value = mock_google_token

        # Make credentials creation raise an exception
        mock_credentials_class.from_authorized_user_info.side_effect = ValueError(
            "Invalid credentials format")

        # Call function - should raise the exception
        with pytest.raises(ValueError, match="Invalid credentials format"):
            fetch_google_creds("user_invalid_creds")

        # Verify the methods were called
        mock_google_token_class.get_tokens_by_user_id.assert_called_once_with(
            "user_invalid_creds")
        mock_google_token.get_default_account_credentials.assert_called_once()
        mock_credentials_class.from_authorized_user_info.assert_called_once_with(
            sample_google_token_credentials)

    def test_fetch_google_creds_token_method_error(self, mock_google_token_class, mock_credentials_class):
        """Test when get_default_account_credentials raises an error."""
        from connectors.utils.google import fetch_google_creds

        # Setup mocks
        mock_google_token = Mock()
        mock_google_token.get_default_account_credentials.side_effect = Exception(
            "Token access error")
        mock_google_token_class.get_tokens_by_user_id.return_value = mock_google_token

        # Call function - should raise the exception
        with pytest.raises(Exception, match="Token access error"):
            fetch_google_creds("user_token_error")

        # Verify the methods were called
        mock_google_token_class.get_tokens_by_user_id.assert_called_once_with(
            "user_token_error")
        mock_google_token.get_default_account_credentials.assert_called_once()
        mock_credentials_class.from_authorized_user_info.assert_not_called()

    def test_fetch_google_creds_with_minimal_credentials(self, mock_google_token_class, mock_credentials_class):
        """Test with minimal valid credentials."""
        from connectors.utils.google import fetch_google_creds

        minimal_creds = {
            "client_id": "minimal_client_id",
            "refresh_token": "minimal_refresh_token"
        }

        # Setup mocks
        mock_google_token = Mock()
        mock_google_token.get_default_account_credentials.return_value = minimal_creds
        mock_google_token_class.get_tokens_by_user_id.return_value = mock_google_token

        mock_credentials = Mock(spec=Credentials)
        mock_credentials_class.from_authorized_user_info.return_value = mock_credentials

        # Call function
        result = fetch_google_creds("user_minimal")

        # Verify results
        assert result == mock_credentials
        mock_credentials_class.from_authorized_user_info.assert_called_once_with(
            minimal_creds)

    def test_fetch_google_creds_with_complete_credentials(self, mock_google_token_class, mock_credentials_class):
        """Test with complete credentials including access token."""
        from connectors.utils.google import fetch_google_creds

        complete_creds = {
            "client_id": "complete_client_id.googleusercontent.com",
            "client_secret": "complete_client_secret",
            "refresh_token": "complete_refresh_token",
            "access_token": "complete_access_token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "type": "authorized_user"
        }

        # Setup mocks
        mock_google_token = Mock()
        mock_google_token.get_default_account_credentials.return_value = complete_creds
        mock_google_token_class.get_tokens_by_user_id.return_value = mock_google_token

        mock_credentials = Mock(spec=Credentials)
        mock_credentials_class.from_authorized_user_info.return_value = mock_credentials

        # Call function
        result = fetch_google_creds("user_complete")

        # Verify results
        assert result == mock_credentials
        mock_credentials_class.from_authorized_user_info.assert_called_once_with(
            complete_creds)

    def test_fetch_google_creds_return_type(self, mock_google_token_class, mock_credentials_class, sample_google_token_credentials):
        """Test that function returns proper Credentials type or None."""
        from connectors.utils.google import fetch_google_creds

        # Setup mocks for successful case
        mock_google_token = Mock()
        mock_google_token.get_default_account_credentials.return_value = sample_google_token_credentials
        mock_google_token_class.get_tokens_by_user_id.return_value = mock_google_token

        mock_credentials = Mock(spec=Credentials)
        mock_credentials_class.from_authorized_user_info.return_value = mock_credentials

        # Test successful case
        result = fetch_google_creds("user_success")
        assert result is not None
        assert result == mock_credentials

        # Test failure case
        mock_google_token_class.get_tokens_by_user_id.return_value = None
        result = fetch_google_creds("user_failure")
        assert result is None

    def test_fetch_google_creds_user_id_types(self, mock_google_token_class):
        """Test function with different user ID types."""
        from connectors.utils.google import fetch_google_creds

        # Setup mock
        mock_google_token_class.get_tokens_by_user_id.return_value = None

        # Test with string
        fetch_google_creds("string_user_id")
        mock_google_token_class.get_tokens_by_user_id.assert_called_with(
            "string_user_id")

        # Test with integer converted to string
        fetch_google_creds(str(12345))
        mock_google_token_class.get_tokens_by_user_id.assert_called_with(
            "12345")

        # Test with UUID-like string
        fetch_google_creds("550e8400-e29b-41d4-a716-446655440000")
        mock_google_token_class.get_tokens_by_user_id.assert_called_with(
            "550e8400-e29b-41d4-a716-446655440000")


# Integration tests
class TestGoogleUtilsIntegration:
    """Integration tests for google.py utilities."""

    def test_import_structure(self):
        """Test that all required imports are accessible."""
        # These should not raise ImportError
        from connectors.utils.google import fetch_google_creds
        from connectors.utils.google import GoogleToken
        from connectors.utils.google import Credentials
        from connectors.utils.google import GoogleAccountNeededResponse

        # Verify they are callable/accessible
        assert callable(fetch_google_creds)
        assert GoogleToken is not None
        assert Credentials is not None
        assert GoogleAccountNeededResponse is not None

    def test_type_hints_compatibility(self):
        """Test that type hints work as expected."""
        from connectors.utils.google import fetch_google_creds

        # Test with proper mocking to ensure type hints work
        with patch('connectors.utils.google.GoogleToken') as mock_token_class, \
                patch('connectors.utils.google.Credentials') as mock_creds_class:

            mock_token_class.get_tokens_by_user_id.return_value = None

            result = fetch_google_creds("test_user")

            # Type hint indicates return should be Credentials | None
            assert result is None or isinstance(
                result, type(mock_creds_class.return_value))

    def test_function_signature(self):
        """Test that function has the expected signature."""
        from connectors.utils.google import fetch_google_creds
        import inspect

        signature = inspect.signature(fetch_google_creds)

        # Should have one parameter with string type hint
        params = list(signature.parameters.keys())
        assert len(params) == 1
        assert params[0] == "user_id"

        # Check return annotation (Credentials | None)
        return_annotation = signature.return_annotation
        assert return_annotation is not None


# Error handling and edge cases
class TestGoogleUtilsEdgeCases:
    """Test edge cases and error conditions."""

    def test_malformed_credentials_data(self):
        """Test handling of malformed credentials data."""
        from connectors.utils.google import fetch_google_creds

        with patch('connectors.utils.google.GoogleToken') as mock_token_class, \
                patch('connectors.utils.google.Credentials') as mock_creds_class:

            # Setup mock with malformed data
            mock_google_token = Mock()
            mock_google_token.get_default_account_credentials.return_value = {
                "invalid": "data",
                "missing": "required_fields"
            }
            mock_token_class.get_tokens_by_user_id.return_value = mock_google_token

            # Simulate Credentials constructor rejecting malformed data
            mock_creds_class.from_authorized_user_info.side_effect = ValueError(
                "Invalid credentials")

            with pytest.raises(ValueError, match="Invalid credentials"):
                fetch_google_creds("user_malformed")

    def test_empty_credentials_dict(self):
        """Test handling of empty credentials dictionary."""
        from connectors.utils.google import fetch_google_creds

        with patch('connectors.utils.google.GoogleToken') as mock_token_class, \
                patch('connectors.utils.google.Credentials') as mock_creds_class:

            # Setup mock with empty dict
            mock_google_token = Mock()
            mock_google_token.get_default_account_credentials.return_value = {}
            mock_token_class.get_tokens_by_user_id.return_value = mock_google_token

            # Simulate Credentials constructor handling empty dict
            mock_creds_class.from_authorized_user_info.side_effect = ValueError(
                "Empty credentials")

            with pytest.raises(ValueError, match="Empty credentials"):
                fetch_google_creds("user_empty_creds")

    def test_credentials_with_none_values(self):
        """Test handling of credentials with None values."""
        from connectors.utils.google import fetch_google_creds

        with patch('connectors.utils.google.GoogleToken') as mock_token_class, \
                patch('connectors.utils.google.Credentials') as mock_creds_class:

            # Setup mock with None values
            mock_google_token = Mock()
            mock_google_token.get_default_account_credentials.return_value = {
                "client_id": None,
                "refresh_token": None
            }
            mock_token_class.get_tokens_by_user_id.return_value = mock_google_token

            mock_credentials = Mock(spec=Credentials)
            mock_creds_class.from_authorized_user_info.return_value = mock_credentials

            # Should still work if Credentials class handles None values
            result = fetch_google_creds("user_none_values")
            assert result == mock_credentials
