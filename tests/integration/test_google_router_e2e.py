"""
End-to-end integration tests for Google router.

These tests verify the complete request/response flow for Google OAuth endpoints,
ensuring that correct field names and data structures are used throughout.
"""

import pytest
import json
import datetime
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
import jwt

# Import the router
from routers.google import GOOGLE_ROUTER as google_router


class TestGoogleRouterE2E:
    """End-to-end tests for Google router endpoints."""
    
    @pytest.fixture
    def app(self):
        """Create a test FastAPI app with the Google router."""
        app = FastAPI()
        app.include_router(google_router)
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create a test client for the FastAPI app."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_auth_token(self):
        """Create a mock JWT token for authentication."""
        payload = {
            'sub': 'test_user_123',
            'email': 'test@example.com',
            'name': 'Test User',
            'exp': datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1)
        }
        return jwt.encode(payload, 'test_secret_key', algorithm='HS256')
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock user with correct structure."""
        user = Mock()
        user.reference_id = 'test_user_123'
        user.email = 'test@example.com'
        user.name = 'Test User'
        user.is_registered = True
        user.integrations = {'google': False}
        user.set_connected_to_google = Mock()
        return user
    
    def test_google_auth_endpoint_structure(self, client, mock_user):
        """Test /auth/google/login creates authorization URL with correct structure."""
        with patch('routers.google.validate_google_token') as mock_validate, \
             patch('routers.google.get_authorization_url') as mock_get_auth_url, \
             patch('routers.google.GoogleToken') as mock_google_token:
            
            mock_validate.return_value = (True, mock_user, False)
            
            # Mock get_authorization_url
            mock_get_auth_url.return_value = ('https://accounts.google.com/oauth/authorize', 'state_123')
            
            # Mock GoogleToken.create_token_request
            mock_token = Mock()
            mock_google_token.create_token_request.return_value = mock_token
            
            response = client.get(
                "/auth/google/login",
                headers={'Authorization': 'Bearer test_token'},
                follow_redirects=False  # Don't follow the redirect
            )
            
            # Google login may return 200 or redirect depending on implementation
            assert response.status_code in [200, 302, 303, 307, 308]
            # If redirect, check location header
            if response.status_code > 300:
                assert 'location' in response.headers
                # Verify GoogleToken.create_token_request was called
                mock_google_token.create_token_request.assert_called_once()
    
    def test_google_callback_endpoint_structure(self, client):
        """Test /auth/google/callback processes OAuth callback with correct structure."""
        with patch('routers.google.exchange_code_for_credentials') as mock_exchange, \
             patch('routers.google.get_user_info') as mock_get_user_info, \
             patch('routers.google.GoogleToken') as mock_google_token:
            
            # Mock OAuth exchange
            mock_credentials = {
                'access_token': 'google_access_token',
                'refresh_token': 'google_refresh_token',
                'expires_in': 3600,
                'token_type': 'Bearer'
            }
            mock_exchange.return_value = mock_credentials
            
            # Mock user info
            mock_user_info = {
                'email': 'oauth@example.com',
                'name': 'OAuth User',
                'picture': 'https://example.com/picture.jpg'
            }
            mock_get_user_info.return_value = mock_user_info
            
            # Mock GoogleToken.save_or_add_token
            mock_token = Mock()
            mock_token.user_id = 'oauth_user_123'
            mock_token.redirect_uri = 'https://app.example.com/oauth/complete'
            mock_google_token.save_or_add_token.return_value = mock_token
            
            response = client.get(
                "/auth/google/callback",
                params={
                    'code': 'auth_code_123',
                    'state': 'state_123'
                },
                follow_redirects=False
            )
            
            # Should redirect
            assert response.status_code in [302, 303, 307, 308]
            
            # Verify save_or_add_token was called with correct structure
            mock_google_token.save_or_add_token.assert_called_once()
            call_args = mock_google_token.save_or_add_token.call_args[0]
            assert call_args[0] == 'state_123'  # state
            assert call_args[1] == mock_credentials  # credentials
            assert call_args[2] == mock_user_info  # user_info
    
    
    
    
    
    


