"""
End-to-end integration tests for API endpoints.

These tests use FastAPI TestClient to test actual request/response flow
with minimal mocking, ensuring that field names and data structures
are correct throughout the entire request lifecycle.
"""

import pytest
import json
import datetime
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
import jwt

# Import the application
from api import APP


class TestAPIEndpointsE2E:
    """End-to-end tests for main API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        return TestClient(APP)
    
    @pytest.fixture
    def mock_auth_token(self):
        """Create a mock JWT token for authentication."""
        payload = {
            'sub': 'test_user_123',
            'email': 'test@example.com',
            'name': 'Test User',
            'exp': datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1)
        }
        # Use a test secret key
        return jwt.encode(payload, 'test_secret_key', algorithm='HS256')
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns correct response."""
        response = client.get("/")
        
        # In non-production, should return static file or redirect
        assert response.status_code in [200, 307, 404]  # 404 if static file doesn't exist
    
    def test_health_check_endpoint(self, client):
        """Test health check endpoint returns correct structure."""
        response = client.get("/test")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert 'status' in data
        assert data['status'] == 'success'
        assert 'service' in data
        assert data['service'] == 'ODAI API'
        assert 'environment' in data
        assert data['environment'] in ['production', 'development']
        assert 'connections' in data
        assert isinstance(data['connections'], int)
    
    def test_waitlist_endpoint_structure(self, client):
        """Test waitlist endpoint with correct data structure."""
        with patch('api.odai_app.api_service.add_email_to_waitlist') as mock_add:
            # Test valid email
            response = client.post(
                "/waitlist",
                data={'email': 'newuser@example.com'}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert 'status' in data
            assert data['status'] == 'success'
            
            # Verify the service was called with correct email
            mock_add.assert_called_once_with('newuser@example.com')
    
    def test_email_endpoint_structure(self, client):
        """Test email endpoint (alias for waitlist) with correct structure."""
        with patch('api.odai_app.api_service.add_email_to_waitlist') as mock_add:
            response = client.post(
                "/email",
                data={'email': 'alias@example.com'}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert 'status' in data
            assert data['status'] == 'success'
            
            # Verify the service was called
            mock_add.assert_called_once_with('alias@example.com')
    
    def test_google_access_request_structure(self, client, mock_auth_token):
        """Test Google access request with correct structure."""
        with patch('api.odai_app.api_service.request_google_access') as mock_request:
            mock_request.return_value = {'status': 'success', 'message': 'Access requested'}
            
            response = client.post(
                "/google_access_request",
                headers={'Authorization': f'Bearer {mock_auth_token}'},
                data={'email': 'access@example.com'}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify service was called with correct parameters
            mock_request.assert_called_once()
            call_args = mock_request.call_args[0]
            assert call_args[1] == f'Bearer {mock_auth_token}'  # authorization
            assert call_args[2] == 'access@example.com'  # email
    
    def test_reset_google_tokens_structure(self, client, mock_auth_token):
        """Test reset Google tokens endpoint structure."""
        with patch('api.odai_app.settings.production', False), \
             patch('api.odai_app.api_service.reset_google_tokens') as mock_reset:
            
            response = client.post(
                "/reset_google_tokens",
                headers={'Authorization': f'Bearer {mock_auth_token}'}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert 'status' in data
            assert data['status'] == 'success'
            
            # Verify service was called
            mock_reset.assert_called_once_with(f'Bearer {mock_auth_token}')
    
    def test_reset_plaid_tokens_structure(self, client, mock_auth_token):
        """Test reset Plaid tokens endpoint structure."""
        with patch('api.odai_app.settings.production', False), \
             patch('api.odai_app.api_service.reset_plaid_tokens') as mock_reset:
            
            response = client.post(
                "/reset_plaid_tokens",
                headers={'Authorization': f'Bearer {mock_auth_token}'}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert 'status' in data
            assert data['status'] == 'success'
            
            # Verify service was called
            mock_reset.assert_called_once_with(f'Bearer {mock_auth_token}')
    
    def test_update_integrations_endpoint(self, client):
        """Test update integrations endpoint."""
        with patch('api.ingest_integrations') as mock_ingest:
            response = client.get("/update_integrations")
            
            assert response.status_code == 200
            data = response.json()
            assert 'status' in data
            assert data['status'] == 'success'
            
            # Verify ingest was called
            mock_ingest.assert_called_once()
    
    def test_production_endpoint_restrictions(self, client, mock_auth_token):
        """Test that certain endpoints are restricted in production."""
        with patch('api.odai_app.settings.production', True):
            # Reset endpoints should return 404 in production
            response = client.post(
                "/reset_google_tokens",
                headers={'Authorization': f'Bearer {mock_auth_token}'}
            )
            assert response.status_code == 404
            
            response = client.post(
                "/reset_plaid_tokens",
                headers={'Authorization': f'Bearer {mock_auth_token}'}
            )
            assert response.status_code == 404


class TestWebSocketEndpointE2E:
    """End-to-end tests for WebSocket endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        return TestClient(APP)
    
    def test_websocket_connection_structure(self, client):
        """Test WebSocket connection with correct structure."""
        with patch('api.odai_app.websocket_handler.handle_websocket_connection') as mock_handler:
            # Mock the handler to accept the connection
            async def mock_connect(*args, **kwargs):
                pass
            mock_handler.return_value = mock_connect()
            
            # Note: TestClient doesn't fully support WebSocket testing
            # This tests that the endpoint exists and is configured correctly
            chat_id = "test_chat_123"
            token = "test_token"
            
            # Verify the WebSocket endpoint is registered
            routes = [route.path for route in APP.routes]
            assert "/chats/{chat_id}" in routes


class TestAPIServiceIntegration:
    """Test API service methods with real data structures."""
    
    def test_api_service_add_email_to_waitlist(self):
        """Test that add_email_to_waitlist uses correct Firebase structure."""
        from services.api_service import APIService
        
        with patch('services.api_service.get_firebase_models') as mock_get_models:
            # Mock the Waitlist model
            mock_waitlist = Mock()
            mock_get_models.return_value = [None, None, mock_waitlist, None, None]
            
            service = APIService()
            
            # Call the method
            service.add_email_to_waitlist('waitlist@example.com')
            
            # Verify Waitlist.add_email was called with correct structure
            mock_waitlist.add_email.assert_called_once_with('waitlist@example.com')
    
    def test_api_service_request_google_access(self):
        """Test that request_google_access maintains correct structure."""
        from services.api_service import APIService
        
        with patch('services.auth_service.AuthService.validate_user_token') as mock_validate, \
             patch('services.api_service.get_firebase_models') as mock_get_models, \
             patch('services.api_service.get_segment_tracking') as mock_get_tracking:
            
            # Mock user validation - returns (valid, user, user_anonymous)
            mock_user = Mock()
            mock_user.reference_id = 'user_123'
            mock_user.email = 'user@example.com'
            mock_user.name = 'Test User'
            mock_validate.return_value = (True, mock_user, False)
            
            # Mock GoogleAccessRequest and tracking
            mock_request = Mock()
            mock_track = Mock()
            mock_get_models.return_value = [None, None, None, None, mock_request]
            mock_get_tracking.return_value = [None, None, None, None, None, None, mock_track]
            
            service = APIService()
            
            # Call the method
            result = service.request_google_access(
                production=False,
                authentication='Bearer test_token',
                email='target@example.com'
            )
            
            # Verify correct structure was used
            assert result['status'] == 'success'
            
            # Verify tracking was called with user and email
            mock_track.assert_called_once_with(mock_user, 'target@example.com')
            
            # Verify GoogleAccessRequest.create_request was called
            mock_request.create_request.assert_called_once_with(mock_user, 'target@example.com')
    
    def test_api_service_reset_tokens_structure(self):
        """Test that reset token methods use correct structure."""
        from services.api_service import APIService
        
        with patch('services.auth_service.AuthService.validate_user_token') as mock_validate, \
             patch('services.api_service.get_firebase_models') as mock_get_models, \
             patch('services.api_service.get_segment_tracking') as mock_get_tracking, \
             patch('firebase.models.google_token.GoogleToken') as mock_google_token, \
             patch('firebase.models.plaid_token.PlaidToken') as mock_plaid_token:
            
            # Mock user validation - returns (valid, user, user_anonymous)
            mock_user = Mock()
            mock_user.reference_id = 'reset_user_123'
            mock_user.disconnect_from_google = Mock()
            mock_user.disconnect_from_plaid = Mock()
            mock_validate.return_value = (True, mock_user, False)
            
            # Setup mocks
            mock_get_models.return_value = [None, None, None, None, None]
            mock_get_tracking.return_value = [None, None, None, None, None, None, None]
            
            service = APIService()
            
            # Test reset Google tokens
            service.reset_google_tokens('Bearer test_token')
            
            # Verify correct methods were called
            mock_user.disconnect_from_google.assert_called_once()
            mock_google_token.reset_tokens.assert_called_once_with('reset_user_123')
            
            # Test reset Plaid tokens
            service.reset_plaid_tokens('Bearer test_token')
            
            # Verify correct methods were called  
            mock_user.disconnect_from_plaid.assert_called_once()
            mock_plaid_token.reset_tokens.assert_called_once_with('reset_user_123')


class TestErrorHandling:
    """Test error handling throughout the request lifecycle."""
    
    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        return TestClient(APP)
    
    def test_waitlist_error_handling(self, client):
        """Test waitlist endpoint handles errors correctly."""
        with patch('api.odai_app.api_service.add_email_to_waitlist') as mock_add:
            # Simulate an error
            mock_add.side_effect = Exception("Database error")
            
            response = client.post(
                "/waitlist",
                data={'email': 'error@example.com'}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert 'status' in data
            assert data['status'] == 'error'
            assert 'message' in data
    
    def test_invalid_form_data(self, client):
        """Test endpoints handle invalid form data correctly."""
        # Missing email field
        response = client.post("/waitlist", data={})
        assert response.status_code == 422  # Unprocessable Entity
        
        # Invalid data type
        response = client.post("/waitlist", json={'email': 'test@example.com'})
        assert response.status_code == 422  # Form data expected, not JSON
    
    def test_missing_authorization_header(self, client):
        """Test endpoints that require auth handle missing header correctly."""
        response = client.post(
            "/google_access_request",
            data={'email': 'test@example.com'}
        )
        assert response.status_code == 422  # Missing required header
    
    def test_malformed_authorization_token(self, client):
        """Test handling of malformed authorization tokens."""
        with patch('api.odai_app.api_service.request_google_access') as mock_request:
            mock_request.return_value = {'status': 'error', 'message': 'Invalid token'}
            
            response = client.post(
                "/google_access_request",
                headers={'Authorization': 'Invalid_Token'},
                data={'email': 'test@example.com'}
            )
            
            # Should handle the error gracefully
            assert response.status_code == 200
            data = response.json()
            assert 'status' in data