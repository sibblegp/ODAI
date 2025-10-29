"""Tests for the Plaid router module."""

import json
import pytest
from unittest.mock import Mock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
import datetime
from datetime import date, timedelta

from routers.plaid import PLAID_ROUTER


class TestPlaidRouter:
    """Test the Plaid router configuration."""
    
    def test_router_prefix(self):
        """Test that the router has the correct prefix."""
        assert PLAID_ROUTER.prefix == '/auth/plaid'
    
    def test_router_has_routes(self):
        """Test that the router has the expected routes."""
        route_paths = [str(route.path) for route in PLAID_ROUTER.routes]
        assert '/auth/plaid/info' in route_paths
        assert '/auth/plaid/create_link_token' in route_paths
        assert '/auth/plaid/set_access_token' in route_paths
        assert '/auth/plaid/accounts' in route_paths
        assert '/auth/plaid/accounts/{account_id}' in route_paths
    
    def test_router_methods(self):
        """Test that routes have correct HTTP methods."""
        route_methods = {}
        for route in PLAID_ROUTER.routes:
            route_methods[str(route.path)] = route.methods
        
        # Test HTTP methods for each endpoint
        assert route_methods['/auth/plaid/info'] == {'POST'}
        assert route_methods['/auth/plaid/create_link_token'] == {'POST'}
        assert route_methods['/auth/plaid/set_access_token'] == {'POST'}
        assert route_methods['/auth/plaid/accounts'] == {'GET'}
        assert route_methods['/auth/plaid/accounts/{account_id}'] == {'DELETE'}


class TestUtilityFunctions:
    """Test utility functions in the plaid module."""
    
    def test_empty_to_none(self):
        """Test the empty_to_none function."""
        from routers.plaid import empty_to_none
        
        # Test with environment variable not set
        with patch('os.getenv') as mock_getenv:
            mock_getenv.return_value = None
            assert empty_to_none('TEST_VAR') is None
        
        # Test with empty string
        with patch('os.getenv') as mock_getenv:
            mock_getenv.return_value = ""
            assert empty_to_none('TEST_VAR') is None
        
        # Test with actual value
        with patch('os.getenv') as mock_getenv:
            mock_getenv.return_value = "test_value"
            assert empty_to_none('TEST_VAR') == "test_value"
    
    def test_json_serial(self):
        """Test the json_serial function for datetime serialization."""
        from routers.plaid import json_serial
        
        # Test datetime serialization
        dt = datetime.datetime(2023, 12, 25, 10, 30, 45)
        assert json_serial(dt) == "2023-12-25T10:30:45"
        
        # Test date serialization
        d = date(2023, 12, 25)
        assert json_serial(d) == "2023-12-25"
        
        # Test unsupported type raises TypeError
        with pytest.raises(TypeError):
            json_serial({"dict": "value"})


class TestPlaidInfoEndpoint:
    """Test the /auth/plaid/info endpoint."""
    
    def setup_method(self):
        """Set up test app for each test."""
        self.app = FastAPI()
        self.app.include_router(PLAID_ROUTER)
        self.client = TestClient(self.app)
    
    def test_info_endpoint_returns_basic_info(self):
        """Test that info endpoint returns expected structure."""
        response = self.client.post("/auth/plaid/info")
        assert response.status_code == 200
        
        data = response.json()
        assert 'item_id' in data
        assert 'access_token' in data
        assert 'products' in data
        
        # Check default values
        assert data['item_id'] is None
        assert data['access_token'] is None
        assert isinstance(data['products'], list)
    
    @patch('routers.plaid.PLAID_PRODUCTS', ['transactions', 'auth', 'accounts'])
    def test_info_endpoint_returns_configured_products(self):
        """Test that info endpoint returns configured products."""
        response = self.client.post("/auth/plaid/info")
        assert response.status_code == 200
        
        data = response.json()
        assert data['products'] == ['transactions', 'auth', 'accounts']


class TestCreateLinkTokenEndpoint:
    """Test the /auth/plaid/create_link_token endpoint."""
    
    def setup_method(self):
        """Set up test app for each test."""
        self.app = FastAPI()
        self.app.include_router(PLAID_ROUTER)
        self.client = TestClient(self.app)
    
    def test_create_link_token_requires_authorization(self):
        """Test that create_link_token requires authorization header."""
        # Missing authorization header should fail with 422
        response = self.client.post("/auth/plaid/create_link_token")
        assert response.status_code == 422
    
    @patch('routers.plaid.validate_google_token')
    def test_create_link_token_invalid_token(self, mock_validate):
        """Test create_link_token with invalid token."""
        mock_validate.return_value = (False, None, False)
        
        response = self.client.post(
            "/auth/plaid/create_link_token",
            headers={"authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 200
        assert response.json() == {'error': 'Invalid token'}
    
    @patch('routers.plaid.validate_google_token')
    def test_create_link_token_anonymous_user(self, mock_validate):
        """Test create_link_token with anonymous user."""
        mock_user = Mock()
        mock_validate.return_value = (True, mock_user, True)
        
        response = self.client.post(
            "/auth/plaid/create_link_token",
            headers={"authorization": "Bearer anon_token"}
        )
        assert response.status_code == 200
        assert response.json() == {'error': 'Anonymous user'}
    
    @patch('routers.plaid.validate_google_token')
    def test_create_link_token_user_not_found(self, mock_validate):
        """Test create_link_token when user is None."""
        mock_validate.return_value = (True, None, False)
        
        response = self.client.post(
            "/auth/plaid/create_link_token",
            headers={"authorization": "Bearer token"}
        )
        assert response.status_code == 200
        assert response.json() == {'error': 'User not found'}
    
    @patch('routers.plaid.validate_google_token')
    @patch('routers.plaid.client')
    @patch('routers.plaid.PlaidToken')
    def test_create_link_token_success(self, mock_plaid_token, mock_client, mock_validate):
        """Test successful create_link_token."""
        # Mock user validation
        mock_user = Mock()
        mock_validate.return_value = (True, mock_user, False)
        
        # Mock Plaid client response
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            'link_token': 'link-test-token',
            'expiration': '2023-12-25T10:00:00Z'
        }
        mock_client.link_token_create.return_value = mock_response
        
        response = self.client.post(
            "/auth/plaid/create_link_token",
            headers={"authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        assert response.json() == {
            'link_token': 'link-test-token',
            'expiration': '2023-12-25T10:00:00Z'
        }
        
        # Verify PlaidToken was created
        mock_plaid_token.create_token_request.assert_called_once_with(mock_user, None)
    
    @patch('routers.plaid.validate_google_token')
    @patch('routers.plaid.client')
    def test_create_link_token_plaid_api_error(self, mock_client, mock_validate):
        """Test create_link_token with Plaid API error."""
        # Mock user validation
        mock_user = Mock()
        mock_validate.return_value = (True, mock_user, False)
        
        # Mock Plaid API exception
        import plaid
        error_body = json.dumps({'error_code': 'INVALID_REQUEST'})
        api_exception = plaid.ApiException()
        api_exception.status = 400
        api_exception.reason = 'Bad Request'
        api_exception.body = error_body
        mock_client.link_token_create.side_effect = api_exception
        
        response = self.client.post(
            "/auth/plaid/create_link_token",
            headers={"authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        assert response.json() == {'error_code': 'INVALID_REQUEST'}


class TestSetAccessTokenEndpoint:
    """Test the /auth/plaid/set_access_token endpoint."""
    
    def setup_method(self):
        """Set up test app for each test."""
        self.app = FastAPI()
        self.app.include_router(PLAID_ROUTER)
        self.client = TestClient(self.app)
    
    def test_set_access_token_requires_authorization(self):
        """Test that set_access_token requires authorization header."""
        response = self.client.post(
            "/auth/plaid/set_access_token",
            data={"public_token": "public-test-token"}
        )
        assert response.status_code == 422
    
    def test_set_access_token_requires_public_token(self):
        """Test that set_access_token requires public_token form field."""
        response = self.client.post(
            "/auth/plaid/set_access_token",
            headers={"authorization": "Bearer token"}
        )
        assert response.status_code == 422
    
    @patch('routers.plaid.validate_google_token')
    def test_set_access_token_invalid_token(self, mock_validate):
        """Test set_access_token with invalid token."""
        mock_validate.return_value = (False, None, False)
        
        response = self.client.post(
            "/auth/plaid/set_access_token",
            headers={"authorization": "Bearer invalid_token"},
            data={"public_token": "public-test-token"}
        )
        assert response.status_code == 200
        assert response.json() == {'error': 'Invalid token'}
    
    @patch('routers.plaid.validate_google_token')
    def test_set_access_token_anonymous_user(self, mock_validate):
        """Test set_access_token with anonymous user."""
        mock_user = Mock()
        mock_validate.return_value = (True, mock_user, True)
        
        response = self.client.post(
            "/auth/plaid/set_access_token",
            headers={"authorization": "Bearer anon_token"},
            data={"public_token": "public-test-token"}
        )
        assert response.status_code == 200
        assert response.json() == {'error': 'Anonymous user'}
    
    @patch('routers.plaid.validate_google_token')
    @patch('routers.plaid.client')
    @patch('routers.plaid.PlaidToken')
    @patch('routers.plaid.SETTINGS')
    def test_set_access_token_success_non_production(self, mock_settings, mock_plaid_token, 
                                                     mock_client, mock_validate):
        """Test successful set_access_token in non-production."""
        # Mock settings
        mock_settings.production = False
        
        # Mock user validation
        mock_user = Mock()
        mock_validate.return_value = (True, mock_user, False)
        
        # Mock exchange response
        mock_exchange_response = {
            'access_token': 'access-test-token',
            'item_id': 'item-test-id'
        }
        mock_exchange = MagicMock()
        mock_exchange.__getitem__ = lambda self, key: mock_exchange_response[key]
        mock_exchange.to_dict.return_value = mock_exchange_response
        mock_client.item_public_token_exchange.return_value = mock_exchange
        
        # Mock accounts response
        mock_accounts_response = {
            'accounts': [
                {'name': 'Test Checking', 'mask': '1234'},
                {'name': 'Test Savings', 'mask': '5678'}
            ],
            'item': {
                'institution_name': 'Test Bank'
            }
        }
        mock_accounts = MagicMock()
        mock_accounts.__getitem__ = lambda self, key: mock_accounts_response[key]
        mock_client.accounts_balance_get.return_value = mock_accounts
        
        response = self.client.post(
            "/auth/plaid/set_access_token",
            headers={"authorization": "Bearer valid_token"},
            data={"public_token": "public-test-token"}
        )
        
        assert response.status_code == 200
        # Router now always returns success: True
        assert response.json() == {'success': True}
        
        # Verify PlaidToken was saved
        mock_plaid_token.save_or_add_token.assert_called_once_with(
            [{'name': 'Test Checking', 'mask': '1234'}, {'name': 'Test Savings', 'mask': '5678'}],
            'access-test-token',
            'item-test-id',
            mock_user,
            'Test Bank'
        )
    
    @patch('routers.plaid.validate_google_token')
    @patch('routers.plaid.client')
    @patch('routers.plaid.PlaidToken')
    @patch('routers.plaid.SETTINGS')
    def test_set_access_token_success_production(self, mock_settings, mock_plaid_token, 
                                                 mock_client, mock_validate):
        """Test successful set_access_token in production."""
        # Mock settings
        mock_settings.production = True
        
        # Mock user validation
        mock_user = Mock()
        mock_validate.return_value = (True, mock_user, False)
        
        # Mock exchange response
        mock_exchange_response = {
            'access_token': 'access-test-token',
            'item_id': 'item-test-id'
        }
        mock_exchange = MagicMock()
        mock_exchange.__getitem__ = lambda self, key: mock_exchange_response[key]
        mock_client.item_public_token_exchange.return_value = mock_exchange
        
        # Mock accounts response
        mock_accounts_response = {
            'accounts': [{'name': 'Test Account', 'mask': '9999'}],
            'item': {
                'institution_name': 'Production Bank'
            }
        }
        mock_accounts = MagicMock()
        mock_accounts.__getitem__ = lambda self, key: mock_accounts_response[key]
        mock_client.accounts_balance_get.return_value = mock_accounts
        
        response = self.client.post(
            "/auth/plaid/set_access_token",
            headers={"authorization": "Bearer valid_token"},
            data={"public_token": "public-test-token"}
        )
        
        # In production, should return success instead of token details
        assert response.status_code == 200
        assert response.json() == {'success': True}
    
    @patch('routers.plaid.validate_google_token')
    @patch('routers.plaid.client')
    def test_set_access_token_plaid_api_error(self, mock_client, mock_validate):
        """Test set_access_token with Plaid API error."""
        # Mock user validation
        mock_user = Mock()
        mock_validate.return_value = (True, mock_user, False)
        
        # Mock Plaid API exception
        import plaid
        error_body = json.dumps({'error_code': 'INVALID_PUBLIC_TOKEN'})
        api_exception = plaid.ApiException()
        api_exception.status = 400
        api_exception.reason = 'Bad Request'
        api_exception.body = error_body
        mock_client.item_public_token_exchange.side_effect = api_exception
        
        response = self.client.post(
            "/auth/plaid/set_access_token",
            headers={"authorization": "Bearer valid_token"},
            data={"public_token": "invalid-public-token"}
        )
        
        assert response.status_code == 200
        assert response.json() == {'error_code': 'INVALID_PUBLIC_TOKEN'}


class TestGetAccountsEndpoint:
    """Test GET /accounts endpoint."""
    
    def setup_method(self):
        """Set up test client."""
        # Create minimal app to avoid import issues
        from fastapi import FastAPI
        app = FastAPI()
        from routers.plaid import PLAID_ROUTER
        app.include_router(PLAID_ROUTER)
        self.client = TestClient(app)
    
    def test_get_accounts_requires_authorization(self):
        """Test get_accounts requires authorization header."""
        response = self.client.get("/auth/plaid/accounts")
        assert response.status_code == 422  # Missing required header
    
    @patch('routers.plaid.validate_google_token')
    def test_get_accounts_invalid_token(self, mock_validate):
        """Test get_accounts with invalid token."""
        mock_validate.return_value = (False, None, False)
        
        response = self.client.get(
            "/auth/plaid/accounts",
            headers={"authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401
        assert response.json() == {'detail': 'Invalid token'}
    
    @patch('routers.plaid.validate_google_token')
    def test_get_accounts_anonymous_user(self, mock_validate):
        """Test get_accounts with anonymous user."""
        mock_user = Mock()
        mock_validate.return_value = (True, mock_user, True)
        
        response = self.client.get(
            "/auth/plaid/accounts",
            headers={"authorization": "Bearer anon_token"}
        )
        assert response.status_code == 401
        assert response.json() == {'detail': 'Anonymous user'}
    
    @patch('routers.plaid.validate_google_token')
    def test_get_accounts_user_not_found(self, mock_validate):
        """Test get_accounts when user is not found."""
        mock_validate.return_value = (True, None, False)
        
        response = self.client.get(
            "/auth/plaid/accounts",
            headers={"authorization": "Bearer valid_token"}
        )
        assert response.status_code == 401
        assert response.json() == {'detail': 'User not found'}
    
    @patch('routers.plaid.validate_google_token')
    @patch('routers.plaid.PlaidToken')
    def test_get_accounts_success_with_accounts(self, mock_plaid_token, mock_validate):
        """Test successful get_accounts with linked accounts."""
        # Mock user validation
        mock_user = Mock()
        mock_user.reference_id = 'user_123'
        mock_validate.return_value = (True, mock_user, False)
        
        # Mock accounts data
        mock_accounts = [
            {
                'bank_name': 'Chase Bank',
                'mask': [
                    {'name': 'Chase Checking', 'mask': '1234'},
                    {'name': 'Chase Savings', 'mask': '5678'}
                ]
            },
            {
                'bank_name': 'Bank of America',
                'mask': [
                    {'name': 'BoA Credit Card', 'mask': '9999'}
                ]
            }
        ]
        mock_plaid_token.get_accounts_by_user_id.return_value = mock_accounts
        
        response = self.client.get(
            "/auth/plaid/accounts",
            headers={"authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        assert response.json() == {'accounts': mock_accounts}
        mock_plaid_token.get_accounts_by_user_id.assert_called_once_with('user_123')
    
    @patch('routers.plaid.validate_google_token')
    @patch('routers.plaid.PlaidToken')
    def test_get_accounts_success_no_accounts(self, mock_plaid_token, mock_validate):
        """Test successful get_accounts with no linked accounts."""
        # Mock user validation
        mock_user = Mock()
        mock_user.reference_id = 'user_456'
        mock_validate.return_value = (True, mock_user, False)
        
        # Mock empty accounts
        mock_plaid_token.get_accounts_by_user_id.return_value = []
        
        response = self.client.get(
            "/auth/plaid/accounts",
            headers={"authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        assert response.json() == {'accounts': []}
        mock_plaid_token.get_accounts_by_user_id.assert_called_once_with('user_456')


class TestDeleteAccountEndpoint:
    """Test DELETE /accounts/{account_id} endpoint."""
    
    def setup_method(self):
        """Set up test client."""
        from fastapi import FastAPI
        app = FastAPI()
        from routers.plaid import PLAID_ROUTER
        app.include_router(PLAID_ROUTER)
        self.client = TestClient(app)
    
    def test_delete_account_requires_authorization(self):
        """Test delete_account requires authorization header."""
        response = self.client.delete("/auth/plaid/accounts/test_account_id")
        assert response.status_code == 422  # Missing required header
    
    @patch('routers.plaid.validate_google_token')
    def test_delete_account_invalid_token(self, mock_validate):
        """Test delete_account with invalid token."""
        mock_validate.return_value = (False, None, False)
        
        response = self.client.delete(
            "/auth/plaid/accounts/test_account_id",
            headers={"authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401
        assert response.json() == {'detail': 'Invalid token'}
    
    @patch('routers.plaid.validate_google_token')
    def test_delete_account_anonymous_user(self, mock_validate):
        """Test delete_account with anonymous user."""
        mock_user = Mock()
        mock_validate.return_value = (True, mock_user, True)
        
        response = self.client.delete(
            "/auth/plaid/accounts/test_account_id",
            headers={"authorization": "Bearer anon_token"}
        )
        assert response.status_code == 401
        assert response.json() == {'detail': 'Anonymous user'}
    
    @patch('routers.plaid.validate_google_token')
    def test_delete_account_user_not_found(self, mock_validate):
        """Test delete_account when user is not found."""
        mock_validate.return_value = (True, None, False)
        
        response = self.client.delete(
            "/auth/plaid/accounts/test_account_id",
            headers={"authorization": "Bearer valid_token"}
        )
        assert response.status_code == 401
        assert response.json() == {'detail': 'User not found'}
    
    @patch('routers.plaid.validate_google_token')
    @patch('routers.plaid.PlaidToken')
    def test_delete_account_user_tokens_not_found(self, mock_plaid_token, mock_validate):
        """Test delete_account when user has no tokens."""
        # Mock user validation
        mock_user = Mock()
        mock_user.reference_id = 'user_123'
        mock_validate.return_value = (True, mock_user, False)
        
        # Mock no tokens found
        mock_plaid_token.get_tokens_by_user_id.return_value = None
        
        response = self.client.delete(
            "/auth/plaid/accounts/test_account_id",
            headers={"authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 401
        assert response.json() == {'detail': 'User not found'}
        mock_plaid_token.get_tokens_by_user_id.assert_called_once_with('user_123')
    
    @patch('routers.plaid.validate_google_token')
    @patch('routers.plaid.PlaidToken')
    def test_delete_account_token_not_found(self, mock_plaid_token, mock_validate):
        """Test delete_account when the specific account is not found."""
        # Mock user validation
        mock_user = Mock()
        mock_user.reference_id = 'user_123'
        mock_validate.return_value = (True, mock_user, False)
        
        # Mock tokens exist but delete fails
        mock_user_tokens = Mock()
        mock_user_tokens.delete_account.return_value = False
        mock_plaid_token.get_tokens_by_user_id.return_value = mock_user_tokens
        
        response = self.client.delete(
            "/auth/plaid/accounts/non_existent_account",
            headers={"authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 404
        assert response.json() == {'detail': 'Token not found'}
        mock_plaid_token.get_tokens_by_user_id.assert_called_once_with('user_123')
        mock_user_tokens.delete_account.assert_called_once_with(mock_user, 'non_existent_account')
    
    @patch('routers.plaid.validate_google_token')
    @patch('routers.plaid.PlaidToken')
    def test_delete_account_success(self, mock_plaid_token, mock_validate):
        """Test successful account deletion."""
        # Mock user validation
        mock_user = Mock()
        mock_user.reference_id = 'user_123'
        mock_validate.return_value = (True, mock_user, False)
        
        # Mock successful deletion
        mock_user_tokens = Mock()
        mock_user_tokens.delete_account.return_value = True
        mock_plaid_token.get_tokens_by_user_id.return_value = mock_user_tokens
        
        response = self.client.delete(
            "/auth/plaid/accounts/account_to_delete",
            headers={"authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        assert response.json() == {'success': True}
        mock_plaid_token.get_tokens_by_user_id.assert_called_once_with('user_123')
        mock_user_tokens.delete_account.assert_called_once_with(mock_user, 'account_to_delete')


class TestPlaidConfiguration:
    """Test Plaid configuration and initialization."""
    
    @patch('routers.plaid.SETTINGS')
    def test_plaid_client_configuration(self, mock_settings):
        """Test that Plaid client is configured correctly."""
        mock_settings.plaid_client_id = 'test_client_id'
        mock_settings.plaid_secret = 'test_secret'
        
        # Re-import to apply mocked settings
        import importlib
        import routers.plaid
        importlib.reload(routers.plaid)
        
        # Verify configuration was created (can't easily test the actual values)
        assert hasattr(routers.plaid, 'configuration')
        assert hasattr(routers.plaid, 'api_client')
        assert hasattr(routers.plaid, 'client')
    
    @patch.dict('os.environ', {
        'PLAID_ENV': 'development',
        'PLAID_PRODUCTS': 'auth,transactions,accounts',
        'PLAID_COUNTRY_CODES': 'US,CA',
        'PLAID_REDIRECT_URI': 'https://example.com/callback'
    })
    def test_environment_variables_loaded(self):
        """Test that environment variables are loaded correctly."""
        # Re-import to pick up environment changes
        import importlib
        import routers.plaid
        importlib.reload(routers.plaid)
        
        assert routers.plaid.PLAID_ENV == 'development'
        assert routers.plaid.PLAID_PRODUCTS == ['auth', 'transactions', 'accounts']
        assert routers.plaid.PLAID_COUNTRY_CODES == ['US', 'CA']
        assert routers.plaid.PLAID_REDIRECT_URI == 'https://example.com/callback'


# Note: These tests provide comprehensive coverage of the Plaid router functionality.
# They test all endpoints, error conditions, utility functions, and configuration.
# The tests use mocking to avoid actual API calls to Plaid and Firebase.