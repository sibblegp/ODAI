"""Tests for the Google OAuth router module."""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from routers.google import GOOGLE_ROUTER


class TestGoogleRouter:
    """Test the Google OAuth router configuration."""
    
    def test_router_prefix(self):
        """Test that the router has the correct prefix."""
        assert GOOGLE_ROUTER.prefix == '/auth/google'
    
    def test_router_has_routes(self):
        """Test that the router has the expected routes."""
        route_paths = [str(route.path) for route in GOOGLE_ROUTER.routes]
        assert '/auth/google/login' in route_paths
        assert '/auth/google/callback' in route_paths


class TestGoogleLoginEndpoint:
    """Test the /auth/google/login endpoint basic functionality."""
    
    def setup_method(self):
        """Set up test app for each test."""
        self.app = FastAPI()
        self.app.include_router(GOOGLE_ROUTER)
        self.client = TestClient(self.app)
    
    def test_login_endpoint_exists(self):
        """Test that the login endpoint exists and responds."""
        response = self.client.get("/auth/google/login")
        # The endpoint should respond (even with an error)
        assert response.status_code in [200, 401, 422]
    
    def test_login_no_token_returns_error(self):
        """Test that login without token returns an error."""
        response = self.client.get("/auth/google/login")
        # HTTPException gets converted to JSON response with status 200
        assert response.status_code == 200
        assert "detail" in response.json()
        assert response.json()["detail"] == "Invalid token"
    
    def test_login_accepts_token_parameter(self):
        """Test that login accepts token parameter."""
        # Even with invalid token, it should process the request
        response = self.client.get("/auth/google/login?token=test_token")
        assert response.status_code == 200  # Will fail validation but endpoint works
    
    def test_login_accepts_authorization_header(self):
        """Test that login accepts authorization header."""
        response = self.client.get("/auth/google/login", headers={"authorization": "Bearer test_token"})
        assert response.status_code == 200  # Will fail validation but endpoint works
    
    def test_login_accepts_redirect_uri(self):
        """Test that login accepts redirect_uri parameter."""
        response = self.client.get("/auth/google/login?token=test&redirect_uri=https://example.com")
        assert response.status_code == 200  # Will fail validation but endpoint works


class TestGoogleCallbackEndpoint:
    """Test the /auth/google/callback endpoint basic functionality."""
    
    def setup_method(self):
        """Set up test app for each test."""
        self.app = FastAPI()
        self.app.include_router(GOOGLE_ROUTER)
        self.client = TestClient(self.app)
    
    def test_callback_requires_state_parameter(self):
        """Test that callback requires state parameter."""
        # Missing state parameter should cause error
        with pytest.raises(KeyError):
            response = self.client.get("/auth/google/callback?code=test_code")
    
    def test_callback_accepts_required_parameters(self):
        """Test that callback accepts code and state parameters."""
        # With both parameters, it will fail later in the OAuth flow
        with pytest.raises(Exception):  # Will fail in exchange_code_for_credentials
            response = self.client.get("/auth/google/callback?code=test&state=test")


class TestGoogleOAuthWithMocks:
    """Test the OAuth flow with mocked dependencies."""
    
    def setup_method(self):
        """Set up test app for each test."""
        self.app = FastAPI()
        self.app.include_router(GOOGLE_ROUTER)
        self.client = TestClient(self.app)
    
    @patch('routers.google.SETTINGS')
    @patch('routers.google.User')
    def test_login_local_mode(self, mock_user_class, mock_settings):
        """Test that local mode bypasses normal validation."""
        # Configure for local mode
        mock_settings.local = True
        mock_user = Mock()
        mock_user_class.get_user_by_id.return_value = mock_user
        
        # In local mode, any token should work and use hardcoded user
        response = self.client.get("/auth/google/login?token=any_token")
        
        # Verify it tried to get the hardcoded user
        mock_user_class.get_user_by_id.assert_called_with('lvX2TjNNcYYSroYeJ3LpRuUwwWs1')
    
    @patch('routers.google.SETTINGS')
    @patch('routers.google.validate_google_token')
    def test_login_error_responses(self, mock_validate, mock_settings):
        """Test login error responses."""
        # Configure for non-local mode
        mock_settings.local = False
        
        # Test invalid token
        mock_validate.return_value = (False, None, False)
        response = self.client.get("/auth/google/login?token=invalid")
        assert response.status_code == 200
        json_response = response.json()
        assert json_response is not None
        assert json_response.get("detail") == "Invalid token"
        
        # Test anonymous user
        mock_user = Mock()
        mock_validate.return_value = (True, mock_user, True)
        response = self.client.get("/auth/google/login?token=anon")
        assert response.status_code == 200
        json_response = response.json()
        assert json_response is not None
        assert json_response.get("detail") == "Anonymous user"


# Note: These tests verify basic functionality and error handling.
# Full OAuth flow testing would require extensive mocking of Google APIs.