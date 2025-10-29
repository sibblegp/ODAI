"""
Comprehensive unit tests for services.auth_service module.

Tests cover all methods of AuthService class including:
- Token validation
- WebSocket authentication
- HTTP request authentication  
- User integration settings
- Error handling and edge cases
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException, WebSocket

# Import the modules to test
from services.auth_service import AuthService, AuthenticationError

# Add patch import for settings
from unittest.mock import PropertyMock


class TestAuthenticationError:
    """Test the custom AuthenticationError exception."""

    def test_authentication_error_creation(self):
        """Test creating AuthenticationError with message."""
        error = AuthenticationError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)


# Module-level fixtures available to all test classes
@pytest.fixture
def mock_validate_google_token():
    """Mock the validate_google_token function."""
    mock = Mock()
    # Set a default return value as a tuple to avoid unpacking errors
    mock.return_value = (True, Mock(), False)
    return mock


@pytest.fixture
def auth_service_production(mock_validate_google_token):
    """Create AuthService instance for production environment."""
    mock_settings = Mock()
    mock_settings.production = True
    with patch('services.auth_service.get_auth_service', return_value=mock_validate_google_token):
        with patch('services.auth_service.get_settings', return_value=lambda: mock_settings):
            return AuthService(production=True)


@pytest.fixture
def auth_service_development(mock_validate_google_token):
    """Create AuthService instance for development environment."""
    mock_settings = Mock()
    mock_settings.production = False
    with patch('services.auth_service.get_auth_service', return_value=mock_validate_google_token):
        with patch('services.auth_service.get_settings', return_value=lambda: mock_settings):
            return AuthService(production=False)


@pytest.fixture
def mock_user():
    """Create a mock user object."""
    user = Mock()
    user.reference_id = "test_user_123"
    user.integrations = {
        "google": True,
        "plaid": False
    }
    user.connected_to_google = True
    user.connected_to_plaid = False
    user.check_terms_of_service_accepted = Mock(return_value=True)
    return user


@pytest.fixture
def mock_user_no_integrations():
    """Create a mock user object without integrations."""
    user = Mock()
    user.reference_id = "test_user_456"
    user.integrations = None
    user.connected_to_google = False
    user.connected_to_plaid = False
    user.check_terms_of_service_accepted = Mock(return_value=True)
    return user


@pytest.fixture
def mock_user_no_terms():
    """Create a mock user object who hasn't accepted terms of service."""
    user = Mock()
    user.reference_id = "test_user_789"
    user.integrations = {
        "google": True,
        "plaid": False
    }
    user.connected_to_google = True
    user.connected_to_plaid = False
    user.check_terms_of_service_accepted = Mock(return_value=False)
    return user


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket object."""
    websocket = Mock(spec=WebSocket)
    websocket.close = AsyncMock()
    return websocket


class TestAuthService:
    """Test suite for AuthService class."""


class TestAuthServiceInit:
    """Test AuthService initialization."""

    @patch('services.auth_service.get_auth_service')
    def test_init_production_mode(self, mock_get_auth_service):
        """Test AuthService initialization in production mode."""
        mock_validate_func = Mock()
        mock_get_auth_service.return_value = mock_validate_func

        service = AuthService(production=True)

        assert service.production is True
        assert service.validate_google_token == mock_validate_func
        mock_get_auth_service.assert_called_once()

    @patch('services.auth_service.get_auth_service')
    def test_init_development_mode(self, mock_get_auth_service):
        """Test AuthService initialization in development mode."""
        mock_validate_func = Mock()
        mock_get_auth_service.return_value = mock_validate_func

        service = AuthService(production=False)

        assert service.production is False
        assert service.validate_google_token == mock_validate_func
        mock_get_auth_service.assert_called_once()


class TestValidateUserToken:
    """Test the validate_user_token method."""

    def test_validate_user_token_success(self, auth_service_development, mock_user):
        """Test successful token validation."""
        auth_service_development.validate_google_token.return_value = (
            True, mock_user, False)

        result = auth_service_development.validate_user_token("valid_token")

        assert result == (True, mock_user, False)
        auth_service_development.validate_google_token.assert_called_once_with(
            "valid_token")

    def test_validate_user_token_no_token(self, auth_service_development):
        """Test validation with no token provided."""
        with pytest.raises(AuthenticationError, match="No token provided"):
            auth_service_development.validate_user_token(None)

        with pytest.raises(AuthenticationError, match="No token provided"):
            auth_service_development.validate_user_token("")

    def test_validate_user_token_invalid_user(self, auth_service_development):
        """Test validation with invalid user (None)."""
        auth_service_development.validate_google_token.return_value = (
            False, None, False)

        with pytest.raises(AuthenticationError, match="Invalid token - no user found"):
            auth_service_development.validate_user_token("invalid_token")

    def test_validate_user_token_anonymous_production(self, auth_service_production, mock_user):
        """Test anonymous user rejection in production."""
        auth_service_production.validate_google_token.return_value = (
            True, mock_user, True)

        with pytest.raises(AuthenticationError, match="Anonymous users not allowed in production"):
            auth_service_production.validate_user_token("anonymous_token")

    def test_validate_user_token_anonymous_development(self, auth_service_development, mock_user):
        """Test anonymous user acceptance in development."""
        auth_service_development.validate_google_token.return_value = (
            True, mock_user, True)

        result = auth_service_development.validate_user_token(
            "anonymous_token")

        assert result == (True, mock_user, True)

    def test_validate_user_token_invalid_validation(self, auth_service_development, mock_user):
        """Test token validation failure."""
        auth_service_development.validate_google_token.return_value = (
            False, mock_user, False)

        with pytest.raises(AuthenticationError, match="Token validation failed"):
            auth_service_development.validate_user_token("invalid_token")

    def test_validate_user_token_exception_handling(self, auth_service_development):
        """Test exception handling during token validation."""
        auth_service_development.validate_google_token.side_effect = Exception(
            "External service error")

        with pytest.raises(AuthenticationError, match="Authentication failed: External service error"):
            auth_service_development.validate_user_token("token")

    def test_validate_user_token_terms_not_accepted_production(self, auth_service_production, mock_user_no_terms):
        """Test validation with terms of service not accepted in production."""
        auth_service_production.validate_google_token.return_value = (
            True, mock_user_no_terms, False)

        with pytest.raises(AuthenticationError, match="Terms of service not accepted"):
            auth_service_production.validate_user_token("valid_token")

    def test_validate_user_token_terms_accepted_production(self, auth_service_production, mock_user):
        """Test validation with terms of service accepted in production."""
        auth_service_production.validate_google_token.return_value = (
            True, mock_user, False)

        result = auth_service_production.validate_user_token("valid_token")
        assert result == (True, mock_user, False)
        mock_user.check_terms_of_service_accepted.assert_called_once()

    def test_validate_user_token_terms_not_accepted_development(self, auth_service_development, mock_user_no_terms):
        """Test validation with terms of service not accepted in development."""
        auth_service_development.validate_google_token.return_value = (
            True, mock_user_no_terms, False)

        # In development, terms check should pass even if not accepted
        result = auth_service_development.validate_user_token("valid_token")
        assert result == (True, mock_user_no_terms, False)


class TestAuthenticateWebSocket:
    """Test the authenticate_websocket method."""

    @pytest.mark.asyncio
    async def test_authenticate_websocket_success(self, auth_service_development, mock_user, mock_websocket):
        """Test successful WebSocket authentication."""
        auth_service_development.validate_google_token.return_value = (
            True, mock_user, False)

        result = await auth_service_development.authenticate_websocket(mock_websocket, "valid_token")

        assert result == (mock_user, False)
        mock_websocket.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_authenticate_websocket_auth_error(self, auth_service_development, mock_websocket):
        """Test WebSocket authentication failure."""
        auth_service_development.validate_google_token.return_value = (
            False, None, False)

        with pytest.raises(AuthenticationError):
            await auth_service_development.authenticate_websocket(mock_websocket, "invalid_token")

        mock_websocket.close.assert_called_once_with(
            code=1008, reason="Authentication failed: Invalid token - no user found")

    @pytest.mark.asyncio
    async def test_authenticate_websocket_unexpected_error(self, auth_service_development, mock_websocket):
        """Test WebSocket authentication with unexpected error."""
        auth_service_development.validate_google_token.side_effect = RuntimeError(
            "Unexpected error")

        with pytest.raises(AuthenticationError, match="Authentication failed: Unexpected error"):
            await auth_service_development.authenticate_websocket(mock_websocket, "token")

        mock_websocket.close.assert_called_once_with(
            code=1008, reason="Authentication failed: Unexpected error")

    @pytest.mark.asyncio
    async def test_authenticate_websocket_no_token(self, auth_service_development, mock_websocket):
        """Test WebSocket authentication with no token."""
        with pytest.raises(AuthenticationError):
            await auth_service_development.authenticate_websocket(mock_websocket, "")

        mock_websocket.close.assert_called_once_with(
            code=1008, reason="No token provided")

    @pytest.mark.asyncio
    async def test_authenticate_websocket_terms_not_accepted_production(self, auth_service_production, mock_user_no_terms, mock_websocket):
        """Test WebSocket authentication with terms not accepted in production."""
        auth_service_production.validate_google_token.return_value = (
            True, mock_user_no_terms, False)

        with pytest.raises(AuthenticationError):
            await auth_service_production.authenticate_websocket(mock_websocket, "valid_token")

        mock_websocket.close.assert_called_once_with(
            code=1008, reason="Authentication failed: Terms of service not accepted")

    @pytest.mark.asyncio
    async def test_authenticate_websocket_terms_accepted_production(self, auth_service_production, mock_user, mock_websocket):
        """Test WebSocket authentication with terms accepted in production."""
        auth_service_production.validate_google_token.return_value = (
            True, mock_user, False)

        result = await auth_service_production.authenticate_websocket(mock_websocket, "valid_token")

        assert result == (mock_user, False)
        mock_websocket.close.assert_not_called()
        mock_user.check_terms_of_service_accepted.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_websocket_terms_not_accepted_development(self, auth_service_development, mock_user_no_terms, mock_websocket):
        """Test WebSocket authentication with terms not accepted in development."""
        auth_service_development.validate_google_token.return_value = (
            True, mock_user_no_terms, False)

        # In development, should succeed even without terms accepted
        result = await auth_service_development.authenticate_websocket(mock_websocket, "valid_token")

        assert result == (mock_user_no_terms, False)
        mock_websocket.close.assert_not_called()


class TestAuthenticateHttpRequest:
    """Test the authenticate_http_request method."""

    def test_authenticate_http_request_success(self, auth_service_development, mock_user):
        """Test successful HTTP request authentication."""
        auth_service_development.validate_google_token.return_value = (
            True, mock_user, False)

        result = auth_service_development.authenticate_http_request(
            "valid_token")

        assert result == (mock_user, False)

    def test_authenticate_http_request_auth_error(self, auth_service_development):
        """Test HTTP request authentication failure."""
        auth_service_development.validate_google_token.return_value = (
            False, None, False)

        with pytest.raises(HTTPException) as exc_info:
            auth_service_development.authenticate_http_request("invalid_token")

        assert exc_info.value.status_code == 401
        assert "Invalid token - no user found" in str(exc_info.value.detail)

    def test_authenticate_http_request_unexpected_error(self, auth_service_development):
        """Test HTTP request authentication with unexpected error."""
        auth_service_development.validate_google_token.side_effect = RuntimeError(
            "Unexpected error")

        with pytest.raises(HTTPException) as exc_info:
            auth_service_development.authenticate_http_request("token")

        assert exc_info.value.status_code == 401
        assert "Authentication failed: Unexpected error" in str(
            exc_info.value.detail)

    def test_authenticate_http_request_no_token(self, auth_service_development):
        """Test HTTP request authentication with no token."""
        with pytest.raises(HTTPException) as exc_info:
            auth_service_development.authenticate_http_request(None)

        assert exc_info.value.status_code == 401
        assert "No token provided" in str(exc_info.value.detail)

    def test_authenticate_http_request_terms_not_accepted_production(self, auth_service_production, mock_user_no_terms):
        """Test HTTP request authentication with terms not accepted in production."""
        auth_service_production.validate_google_token.return_value = (
            True, mock_user_no_terms, False)

        with pytest.raises(HTTPException) as exc_info:
            auth_service_production.authenticate_http_request("valid_token")

        assert exc_info.value.status_code == 401
        assert "Terms of service not accepted" in str(exc_info.value.detail)

    def test_authenticate_http_request_terms_accepted_production(self, auth_service_production, mock_user):
        """Test HTTP request authentication with terms accepted in production."""
        auth_service_production.validate_google_token.return_value = (
            True, mock_user, False)

        result = auth_service_production.authenticate_http_request("valid_token")

        assert result == (mock_user, False)
        mock_user.check_terms_of_service_accepted.assert_called_once()

    def test_authenticate_http_request_terms_not_accepted_development(self, auth_service_development, mock_user_no_terms):
        """Test HTTP request authentication with terms not accepted in development."""
        auth_service_development.validate_google_token.return_value = (
            True, mock_user_no_terms, False)

        # In development, should succeed even without terms accepted
        result = auth_service_development.authenticate_http_request("valid_token")

        assert result == (mock_user_no_terms, False)


class TestGetUserIntegrations:
    """Test the get_user_integrations method."""

    def test_get_user_integrations_with_integrations(self, auth_service_development, mock_user):
        """Test getting user integrations when they exist."""
        result = auth_service_development.get_user_integrations(mock_user)

        expected = {
            "google": True,
            "plaid": False
        }
        assert result == expected

    def test_get_user_integrations_no_integrations(self, auth_service_development, mock_user_no_integrations):
        """Test getting user integrations when they don't exist."""
        result = auth_service_development.get_user_integrations(
            mock_user_no_integrations)

        expected = {
            "google": False,
            "plaid": False
        }
        assert result == expected

    def test_get_user_integrations_no_integrations_attribute(self, auth_service_development):
        """Test getting user integrations when user has no integrations attribute."""
        user_without_attr = Mock()
        user_without_attr.connected_to_google = False
        user_without_attr.connected_to_plaid = False

        result = auth_service_development.get_user_integrations(
            user_without_attr)

        expected = {
            "google": False,
            "plaid": False
        }
        assert result == expected

    def test_get_user_integrations_partial_integrations(self, auth_service_development):
        """Test getting user integrations with partial integration data."""
        user = Mock()
        user.reference_id = "test_user"
        user.integrations = {"google": True}  # Missing plaid
        user.connected_to_google = True
        user.connected_to_plaid = False

        result = auth_service_development.get_user_integrations(user)

        expected = {
            "google": True,
            "plaid": False
        }
        assert result == expected


class TestAuthServiceIntegration:
    """Integration tests for AuthService."""

    @pytest.mark.asyncio
    async def test_full_websocket_flow_success(self, mock_user, mock_websocket):
        """Test complete WebSocket authentication flow."""
        mock_validate_func = Mock(return_value=(True, mock_user, False))

        with patch('services.auth_service.get_auth_service', return_value=mock_validate_func):
            service = AuthService(production=False)
            user, is_anonymous = await service.authenticate_websocket(mock_websocket, "valid_token")
            integrations = service.get_user_integrations(user)

        assert user == mock_user
        assert is_anonymous is False
        assert integrations["google"] is True
        assert integrations["plaid"] is False
        mock_websocket.close.assert_not_called()

    def test_full_http_flow_success(self, mock_user):
        """Test complete HTTP authentication flow."""
        mock_validate_func = Mock(return_value=(True, mock_user, False))

        with patch('services.auth_service.get_auth_service', return_value=mock_validate_func):
            service = AuthService(production=False)
            user, is_anonymous = service.authenticate_http_request(
                "valid_token")
            integrations = service.get_user_integrations(user)

        assert user == mock_user
        assert is_anonymous is False
        assert integrations["google"] is True
        assert integrations["plaid"] is False


class TestAuthServiceTermsOfServiceIntegration:
    """Integration tests for terms of service enforcement across different scenarios."""

    @pytest.mark.asyncio
    async def test_full_auth_flow_terms_not_accepted_production(self, mock_user_no_terms, mock_websocket):
        """Test complete authentication flow with terms not accepted in production."""
        mock_validate_func = Mock(return_value=(True, mock_user_no_terms, False))
        mock_settings = Mock()
        mock_settings.production = True

        with patch('services.auth_service.get_auth_service', return_value=mock_validate_func):
            with patch('services.auth_service.get_settings', return_value=lambda: mock_settings):
                service = AuthService(production=True)
                
                # Test validate_user_token
                with pytest.raises(AuthenticationError, match="Terms of service not accepted"):
                    service.validate_user_token("valid_token")
                
                # Test authenticate_websocket
                with pytest.raises(AuthenticationError):
                    await service.authenticate_websocket(mock_websocket, "valid_token")
                mock_websocket.close.assert_called_with(
                    code=1008, reason="Authentication failed: Terms of service not accepted")
                
                # Test authenticate_http_request
                with pytest.raises(HTTPException) as exc_info:
                    service.authenticate_http_request("valid_token")
                assert exc_info.value.status_code == 401
                assert "Terms of service not accepted" in str(exc_info.value.detail)

    def test_anonymous_user_terms_check_production(self, mock_user):
        """Test that anonymous users are rejected before terms check in production."""
        mock_validate_func = Mock(return_value=(True, mock_user, True))  # Anonymous user
        mock_settings = Mock()
        mock_settings.production = True

        with patch('services.auth_service.get_auth_service', return_value=mock_validate_func):
            with patch('services.auth_service.get_settings', return_value=lambda: mock_settings):
                service = AuthService(production=True)
                
                # Should fail on anonymous check before reaching terms check
                with pytest.raises(AuthenticationError, match="Anonymous users not allowed in production"):
                    service.validate_user_token("anonymous_token")
                
                # Terms check should not have been called
                mock_user.check_terms_of_service_accepted.assert_not_called()

    def test_terms_check_only_in_production(self, mock_user_no_terms):
        """Test that terms check only happens when service is in production mode."""
        mock_validate_func = Mock(return_value=(True, mock_user_no_terms, False))
        
        # Test with production=False in settings
        mock_settings = Mock()
        mock_settings.production = False

        with patch('services.auth_service.get_auth_service', return_value=mock_validate_func):
            with patch('services.auth_service.get_settings', return_value=lambda: mock_settings):
                service = AuthService(production=True)  # Service initialized as production
                
                # Should fail because service.production is True
                with pytest.raises(AuthenticationError, match="Terms of service not accepted"):
                    service.validate_user_token("valid_token")
                
                # Terms check should have been called
                mock_user_no_terms.check_terms_of_service_accepted.assert_called_once()


class TestAuthServiceEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_string_token(self, auth_service_development):
        """Test handling of empty string token."""
        with pytest.raises(AuthenticationError, match="No token provided"):
            auth_service_development.validate_user_token("")

    def test_whitespace_only_token(self, auth_service_development):
        """Test handling of whitespace-only token."""
        # Whitespace-only tokens are treated as valid tokens and passed to validation
        # They will likely fail validation, so we expect an authentication error
        auth_service_development.validate_google_token.return_value = (
            False, None, False)

        with pytest.raises(AuthenticationError, match="Authentication failed: Invalid token - no user found"):
            auth_service_development.validate_user_token("   ")

    def test_user_with_empty_integrations_dict(self, auth_service_development):
        """Test user with empty integrations dictionary."""
        user = Mock()
        user.reference_id = "test_user"
        user.integrations = {}
        user.connected_to_google = False
        user.connected_to_plaid = False

        result = auth_service_development.get_user_integrations(user)

        expected = {
            "google": False,
            "plaid": False
        }
        assert result == expected

    @patch('services.auth_service.logger')
    @pytest.mark.asyncio
    async def test_logging_on_websocket_auth_success(self, mock_logger, auth_service_development, mock_user, mock_websocket):
        """Test that successful WebSocket auth logs appropriately."""
        auth_service_development.validate_google_token.return_value = (
            True, mock_user, False)

        await auth_service_development.authenticate_websocket(mock_websocket, "valid_token")
        mock_logger.info.assert_called_with(
            f"WebSocket authenticated for user: {mock_user.reference_id}")

    @patch('services.auth_service.logger')
    def test_logging_on_auth_error(self, mock_logger, auth_service_development):
        """Test that authentication errors are logged appropriately."""
        auth_service_development.validate_google_token.side_effect = Exception(
            "Test error")

        with pytest.raises(AuthenticationError):
            auth_service_development.validate_user_token("token")

        mock_logger.error.assert_called_once()
        args = mock_logger.error.call_args[0][0]
        assert "Token validation error" in args


# Pytest configuration and fixtures for the entire test module
@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all mocks between tests."""
    yield
    # Any cleanup can be done here if needed


if __name__ == "__main__":
    # Allow running tests directly with python -m pytest
    pytest.main([__file__])
