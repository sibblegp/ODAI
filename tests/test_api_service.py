"""Tests for the APIService class."""

import pytest
from unittest.mock import Mock, patch

from services.api_service import APIService


@pytest.fixture
def api_service():
    """Create an APIService instance with mocked dependencies."""
    with patch('services.api_service.get_firebase_models') as mock_get_firebase_models, \
         patch('services.api_service.get_segment_tracking') as mock_get_segment_tracking, \
         patch('firebase.models.google_token.GoogleToken') as mock_google_token, \
         patch('firebase.models.plaid_token.PlaidToken') as mock_plaid_token:
        
        # Mock Firebase models
        mock_waitlist = Mock()
        mock_google_access_request = Mock()
        mock_get_firebase_models.return_value = (
            Mock(),  # Chat
            Mock(),  # TokenUsage
            mock_waitlist,  # Waitlist
            Mock(),  # UnhandledRequest
            mock_google_access_request  # GoogleAccessRequest
        )
        
        # Mock segment tracking
        mock_track_google_access = Mock()
        mock_get_segment_tracking.return_value = (
            Mock(),  # track_agent_called
            Mock(),  # track_chat_created
            Mock(),  # track_prompt
            Mock(),  # track_responded
            Mock(),  # track_tool_called
            Mock(),  # using_existing_chat
            mock_track_google_access  # track_google_access_request
        )
        
        service = APIService()
        # Override with the mocked tokens since they're imported in __init__
        service.GoogleToken = mock_google_token
        service.PlaidToken = mock_plaid_token
        return service


class TestAddEmailToWaitlist:
    """Test the add_email_to_waitlist method."""

    def test_add_email_to_waitlist_success(self, api_service):
        """Test successful email addition to waitlist."""
        # Execute
        api_service.add_email_to_waitlist("test@example.com")

        # Verify
        api_service.Waitlist.add_email.assert_called_once_with(
            "test@example.com")

    def test_add_email_to_waitlist_exception(self, api_service):
        """Test exception handling in add_email_to_waitlist."""
        # Setup
        api_service.Waitlist.add_email.side_effect = Exception(
            "Waitlist add failed")

        # Execute & Verify
        with pytest.raises(Exception, match="Waitlist add failed"):
            api_service.add_email_to_waitlist("test@example.com")


class TestRequestGoogleAccess:
    """Test the request_google_access method."""

    @patch('services.api_service.AuthService')
    def test_request_google_access_success(self, mock_auth_service_class, api_service):
        """Test successful Google access request."""
        # Setup
        mock_auth_service = Mock()
        mock_user = Mock()
        mock_auth_service.validate_user_token.return_value = (True, mock_user, False)
        mock_auth_service_class.return_value = mock_auth_service
        
        # Execute
        result = api_service.request_google_access(True, "test_auth_token", "test@example.com")

        # Verify
        assert result == {'status': 'success'}
        mock_auth_service_class.assert_called_once_with(True)
        mock_auth_service.validate_user_token.assert_called_once_with("test_auth_token")
        api_service.GoogleAccessRequest.create_request.assert_called_once_with(mock_user, "test@example.com")
        api_service.track_google_access_request.assert_called_once_with(mock_user, "test@example.com")

    @patch('services.api_service.AuthService')
    def test_request_google_access_exception(self, mock_auth_service_class, api_service):
        """Test exception handling in request_google_access."""
        # Setup
        mock_auth_service = Mock()
        mock_user = Mock()
        mock_auth_service.validate_user_token.return_value = (True, mock_user, False)
        mock_auth_service_class.return_value = mock_auth_service
        
        api_service.GoogleAccessRequest.create_request.side_effect = Exception("Request already exists")
        
        # Execute & Verify
        with pytest.raises(Exception, match="Request already exists"):
            api_service.request_google_access(True, "test_auth_token", "test@example.com")
        
        # Verify tracking was not called due to exception
        api_service.track_google_access_request.assert_not_called()

    @patch('services.api_service.logger')
    @patch('services.api_service.AuthService')
    def test_request_google_access_with_logging(self, mock_auth_service_class, mock_logger, api_service):
        """Test Google access request logs appropriately."""
        # Setup
        mock_auth_service = Mock()
        mock_user = Mock()
        mock_auth_service.validate_user_token.return_value = (True, mock_user, False)
        mock_auth_service_class.return_value = mock_auth_service
        
        # Execute
        result = api_service.request_google_access(True, "test_auth_token", "test@example.com")

        # Verify logging
        mock_logger.info.assert_called_with("Requested Google access for test@example.com")


class TestResetGoogleTokens:
    """Test the reset_google_tokens method."""

    @patch('services.api_service.AuthService')
    def test_reset_google_tokens_success(self, mock_auth_service_class, api_service):
        """Test successful Google tokens reset."""
        # Setup
        mock_auth_service = Mock()
        mock_user = Mock()
        mock_auth_service.validate_user_token.return_value = (True, mock_user, False)
        mock_auth_service_class.return_value = mock_auth_service
        api_service.GoogleToken.reset_tokens.return_value = True
        
        # Execute
        result = api_service.reset_google_tokens("test_auth_token")

        # Verify
        assert result is True
        mock_auth_service_class.assert_called_once_with(False)
        mock_auth_service.validate_user_token.assert_called_once_with("test_auth_token")
        mock_user.disconnect_from_google.assert_called_once()
        api_service.GoogleToken.reset_tokens.assert_called_once_with(mock_user.reference_id)

    @patch('services.api_service.AuthService')
    def test_reset_google_tokens_no_user(self, mock_auth_service_class, api_service):
        """Test reset tokens with no user."""
        # Setup
        mock_auth_service = Mock()
        mock_auth_service.validate_user_token.return_value = (False, None, False)
        mock_auth_service_class.return_value = mock_auth_service
        
        # Execute
        result = api_service.reset_google_tokens("test_auth_token")

        # Verify
        assert result is False
        api_service.GoogleToken.reset_tokens.assert_not_called()

    @patch('services.api_service.AuthService')
    def test_reset_google_tokens_exception(self, mock_auth_service_class, api_service):
        """Test exception handling in reset_google_tokens."""
        # Setup
        mock_auth_service = Mock()
        mock_auth_service.validate_user_token.side_effect = Exception("Auth failed")
        mock_auth_service_class.return_value = mock_auth_service
        
        # Execute & Verify
        with pytest.raises(Exception, match="Auth failed"):
            api_service.reset_google_tokens("test_auth_token")


class TestResetPlaidTokens:
    """Test the reset_plaid_tokens method."""

    @patch('services.api_service.AuthService')
    def test_reset_plaid_tokens_success(self, mock_auth_service_class, api_service):
        """Test successful Plaid tokens reset."""
        # Setup
        mock_auth_service = Mock()
        mock_user = Mock()
        mock_user.reference_id = "user_123"
        mock_auth_service.validate_user_token.return_value = (True, mock_user, False)
        mock_auth_service_class.return_value = mock_auth_service
        
        # Execute
        result = api_service.reset_plaid_tokens("test_auth_token")
        
        # Verify
        assert result is True
        mock_auth_service_class.assert_called_once_with(False)
        mock_auth_service.validate_user_token.assert_called_once_with("test_auth_token")
        mock_user.disconnect_from_plaid.assert_called_once()
        api_service.PlaidToken.reset_tokens.assert_called_once_with("user_123")

    @patch('services.api_service.AuthService')
    def test_reset_plaid_tokens_no_user(self, mock_auth_service_class, api_service):
        """Test reset Plaid tokens with no user."""
        # Setup
        mock_auth_service = Mock()
        mock_auth_service.validate_user_token.return_value = (False, None, False)
        mock_auth_service_class.return_value = mock_auth_service
        
        # Execute
        result = api_service.reset_plaid_tokens("test_auth_token")
        
        # Verify
        assert result is False
        api_service.PlaidToken.reset_tokens.assert_not_called()

    @patch('services.api_service.AuthService')
    @patch('services.api_service.logger')
    def test_reset_plaid_tokens_exception(self, mock_logger, mock_auth_service_class, api_service):
        """Test exception handling in reset_plaid_tokens."""
        # Setup
        mock_auth_service = Mock()
        mock_auth_service.validate_user_token.side_effect = Exception("Auth failed")
        mock_auth_service_class.return_value = mock_auth_service
        
        # Execute and verify exception is raised
        with pytest.raises(Exception, match="Auth failed"):
            api_service.reset_plaid_tokens("test_auth_token")
        
        # Verify logging
        mock_logger.error.assert_called_once()
        assert "Error resetting Plaid tokens" in str(mock_logger.error.call_args)

    @patch('services.api_service.AuthService')
    def test_reset_plaid_tokens_anonymous_user(self, mock_auth_service_class, api_service):
        """Test reset Plaid tokens with anonymous user."""
        # Setup
        mock_auth_service = Mock()
        mock_user = Mock()
        mock_user.reference_id = "anon_user"
        mock_auth_service.validate_user_token.return_value = (True, mock_user, True)
        mock_auth_service_class.return_value = mock_auth_service
        
        # Execute
        result = api_service.reset_plaid_tokens("test_auth_token")
        
        # Verify - should still process for anonymous user (based on implementation)
        assert result is True
        mock_user.disconnect_from_plaid.assert_called_once()
        api_service.PlaidToken.reset_tokens.assert_called_once_with("anon_user")


class TestAdditionalScenarios:
    """Test additional scenarios."""

    def test_empty_email_to_waitlist(self, api_service):
        """Test adding empty email to waitlist."""
        # Execute
        api_service.add_email_to_waitlist("")

        # Verify (should still call the underlying method)
        api_service.Waitlist.add_email.assert_called_once_with("")