"""
End-to-end integration tests for Plaid router.

These tests verify the complete request/response flow for Plaid endpoints,
ensuring that the actual field name 'account_names_and_numbers' is used
throughout the entire lifecycle.
"""

import pytest
import json
import datetime
import base64
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
import jwt

# Import the router
from routers.plaid import PLAID_ROUTER as plaid_router


class TestPlaidRouterE2E:
    """End-to-end tests for Plaid router endpoints."""
    
    @pytest.fixture
    def app(self):
        """Create a test FastAPI app with the Plaid router."""
        app = FastAPI()
        app.include_router(plaid_router)
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
        user.integrations = {}
        user.set_connected_to_plaid = Mock()
        return user
    
    def test_plaid_link_token_creation(self, client, mock_auth_token, mock_user):
        """Test /auth/plaid/create_link_token creates token with correct structure."""
        with patch('routers.plaid.validate_google_token') as mock_validate, \
             patch('routers.plaid.PlaidToken') as mock_plaid_token, \
             patch('routers.plaid.client') as mock_plaid_client:
            
            mock_validate.return_value = (True, mock_user, False)
            
            # Mock PlaidToken.create_token_request
            mock_token = Mock()
            mock_token.redirect_uri = 'https://app.example.com/plaid/callback'
            mock_plaid_token.create_token_request.return_value = mock_token
            
            # Mock Plaid client response (needs to_dict method)
            mock_response = Mock()
            mock_response.to_dict.return_value = {
                'link_token': 'link-test-token-123',
                'expiration': '2024-01-01T12:00:00Z'
            }
            mock_plaid_client.link_token_create.return_value = mock_response
            
            response = client.post(
                "/auth/plaid/create_link_token",
                headers={'Authorization': f'Bearer {mock_auth_token}'}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert 'link_token' in data
            assert data['link_token'] == 'link-test-token-123'
            
            # Verify PlaidToken.create_token_request was called
            mock_plaid_token.create_token_request.assert_called_once()
            call_args = mock_plaid_token.create_token_request.call_args
            assert call_args[0][0] == mock_user  # user argument
    
    def test_plaid_exchange_public_token_structure(self, client, mock_auth_token, mock_user):
        """Test /auth/plaid/set_access_token uses account_names_and_numbers field."""
        with patch('routers.plaid.validate_google_token') as mock_validate, \
             patch('routers.plaid.PlaidToken') as mock_plaid_token, \
             patch('routers.plaid.client') as mock_plaid_client:
            
            mock_validate.return_value = (True, mock_user, False)
            
            # Mock Plaid client responses
            mock_exchange_response = Mock()
            mock_exchange_response.__getitem__ = lambda self, key: {'access_token': 'access-test-token', 'item_id': 'item-test-id'}[key]
            mock_plaid_client.item_public_token_exchange.return_value = mock_exchange_response
            
            # CRITICAL: Mock accounts_balance_get response with correct structure
            mock_accounts_response = Mock()
            mock_accounts_response.__getitem__ = lambda self, key: {
                'accounts': [
                    {
                        'account_id': 'acc_1',
                        'name': 'Plaid Checking',
                        'mask': '0000',
                        'type': 'depository',
                        'subtype': 'checking'
                    },
                    {
                        'account_id': 'acc_2',
                        'name': 'Plaid Saving',
                        'mask': '1111',
                        'type': 'depository',
                        'subtype': 'savings'
                    }
                ],
                'item': {
                    'institution_name': 'Plaid Test Bank'
                }
            }[key]
            mock_plaid_client.accounts_balance_get.return_value = mock_accounts_response
            
            # Mock PlaidToken.save_or_add_token
            mock_token = Mock()
            mock_plaid_token.save_or_add_token.return_value = mock_token
            
            response = client.post(
                "/auth/plaid/set_access_token",
                headers={'Authorization': f'Bearer {mock_auth_token}'},
                data={'public_token': 'public-test-token'}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert 'success' in data
            assert data['success'] == True
            
            # CRITICAL: Verify save_or_add_token was called with account_names_and_numbers
            mock_plaid_token.save_or_add_token.assert_called_once()
            call_args = mock_plaid_token.save_or_add_token.call_args[0]
            
            # Check that the first argument is account_names_and_numbers with correct structure
            account_data = call_args[0]  # First positional arg is account_names_and_numbers
            assert isinstance(account_data, list)
            assert len(account_data) == 2
            assert account_data[0]['name'] == 'Plaid Checking'
            assert account_data[0]['mask'] == '0000'
            assert account_data[1]['name'] == 'Plaid Saving'
            assert account_data[1]['mask'] == '1111'
            
            # Verify other arguments (positional)
            assert call_args[1] == 'access-test-token'  # access_token
            assert call_args[2] == 'item-test-id'  # item_id
            assert call_args[3] == mock_user  # user
    
    def test_plaid_accounts_endpoint_structure(self, client, mock_auth_token, mock_user):
        """Test /plaid/accounts returns account_names_and_numbers in response."""
        with patch('routers.plaid.validate_google_token') as mock_validate, \
             patch('routers.plaid.PlaidToken') as mock_plaid_token:
            
            mock_validate.return_value = (True, mock_user, False)
            
            # Mock PlaidToken.get_accounts_by_user_id with correct structure
            mock_accounts = [
                {
                    'bank_name': 'Chase Bank',
                    'mask': [  # This contains account_names_and_numbers
                        {'name': 'Chase Checking', 'mask': '1234'},
                        {'name': 'Chase Savings', 'mask': '5678'}
                    ],
                    'id': 'token_id_1'
                },
                {
                    'bank_name': 'Wells Fargo',
                    'mask': [
                        {'name': 'WF Checking', 'mask': '9012'}
                    ],
                    'id': 'token_id_2'
                }
            ]
            mock_plaid_token.get_accounts_by_user_id.return_value = mock_accounts
            
            response = client.get(
                "/auth/plaid/accounts",
                headers={'Authorization': f'Bearer {mock_auth_token}'}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure contains account information
            assert 'accounts' in data
            assert len(data['accounts']) == 2
            
            # Verify first bank accounts
            assert data['accounts'][0]['bank_name'] == 'Chase Bank'
            assert len(data['accounts'][0]['mask']) == 2
            assert data['accounts'][0]['mask'][0]['name'] == 'Chase Checking'
            assert data['accounts'][0]['mask'][0]['mask'] == '1234'
            
            # Verify get_accounts_by_user_id was called with correct user_id
            mock_plaid_token.get_accounts_by_user_id.assert_called_once_with('test_user_123')
    
    
    
    def test_plaid_delete_account_structure(self, client, mock_auth_token, mock_user):
        """Test /plaid/delete_account uses correct structure."""
        with patch('routers.plaid.validate_google_token') as mock_validate, \
             patch('routers.plaid.PlaidToken') as mock_plaid_token:
            
            mock_validate.return_value = (True, mock_user, False)
            
            # Mock PlaidToken
            mock_token = Mock()
            mock_token.delete_account.return_value = True
            mock_plaid_token.get_tokens_by_user_id.return_value = mock_token
            
            response = client.delete(
                "/auth/plaid/accounts/account_to_delete_123",
                headers={'Authorization': f'Bearer {mock_auth_token}'}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert 'success' in data
            assert data['success'] == True
            
            # Verify delete_account was called with user and correct account_id
            mock_token.delete_account.assert_called_once_with(mock_user, 'account_to_delete_123')
    
    def test_plaid_error_handling(self, client, mock_auth_token):
        """Test Plaid router handles errors correctly."""
        with patch('routers.plaid.validate_google_token') as mock_validate:
            # Test with invalid auth (returns False)
            mock_validate.return_value = (False, None, False)
            
            response = client.get(
                "/auth/plaid/accounts",
                headers={'Authorization': f'Bearer invalid_token'}
            )
            
            # Should return 401 Unauthorized
            assert response.status_code == 401
    
    def test_plaid_field_name_regression(self, client, mock_auth_token, mock_user):
        """
        Regression test to ensure 'account_names_and_numbers' is used, not 'account_names'.
        This test would FAIL if the field name reverted.
        """
        with patch('routers.plaid.validate_google_token') as mock_validate, \
             patch('routers.plaid.PlaidToken') as mock_plaid_token, \
             patch('routers.plaid.client') as mock_plaid_client:
            
            mock_validate.return_value = (True, mock_user, False)
            
            # Set up mocks
            mock_exchange = Mock()
            mock_exchange.__getitem__ = lambda self, key: {'access_token': 'test_access', 'item_id': 'test_item'}[key]
            mock_plaid_client.item_public_token_exchange.return_value = mock_exchange
            
            mock_accounts = Mock()
            mock_accounts.__getitem__ = lambda self, key: {
                'accounts': [{'name': 'Test Account', 'mask': '1234'}],
                'item': {'institution_name': 'Test Institution'}
            }[key]
            mock_plaid_client.accounts_balance_get.return_value = mock_accounts
            
            # Capture what save_or_add_token is called with
            captured_args = {}
            def capture_save_call(*args, **kwargs):
                # save_or_add_token(account_names_and_numbers, access_token, item_id, user, bank_name)
                if len(args) >= 5:
                    captured_args['account_names_and_numbers'] = args[0]
                    captured_args['access_token'] = args[1]
                    captured_args['item_id'] = args[2]
                    captured_args['user'] = args[3]
                    captured_args['bank_name'] = args[4]
                captured_args.update(kwargs)
                return Mock()
            
            mock_plaid_token.save_or_add_token.side_effect = capture_save_call
            
            response = client.post(
                "/auth/plaid/set_access_token",
                headers={'Authorization': f'Bearer {mock_auth_token}'},
                data={'public_token': 'public_token'}
            )
            
            assert response.status_code == 200
            
            # CRITICAL: Verify the correct field name is used
            assert 'account_names_and_numbers' in captured_args
            assert 'account_names' not in captured_args  # Old field name should NOT be present


