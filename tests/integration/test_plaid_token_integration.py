"""
Integration tests for PlaidToken model.

These tests use real PlaidToken instances with actual data structures
to ensure field name changes and structural modifications are caught.
"""

import pytest
import datetime
import uuid
import base64
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.fixtures.firebase_models import FirebaseModelFactory, SchemaValidator, MockDocumentSnapshot


class TestPlaidTokenIntegration:
    """Integration tests for PlaidToken model with real data structures."""
    
    def test_plaid_token_schema_validation(self):
        """Test that PlaidToken has the expected schema with correct field names."""
        # Create a real PlaidToken instance
        token = FirebaseModelFactory.create_plaid_token(
            user_id="schema_test_user",
            with_accounts=True
        )
        
        # Validate schema - this would FAIL if field names changed
        SchemaValidator.validate_plaid_token_schema(token)
        
        # Additional explicit checks for the critical field
        assert token.tokens[0]['account_names_and_numbers'] is not None
        assert len(token.tokens[0]['account_names_and_numbers']) == 2
        assert token.tokens[0]['account_names_and_numbers'][0]['name'] == 'Test Checking Account'
        assert token.tokens[0]['account_names_and_numbers'][0]['mask'] == '1234'
    
    def test_plaid_token_save_or_add_token_structure(self):
        """Test that save_or_add_token uses correct field structure."""
        from firebase.models.plaid_token import PlaidToken
        
        # Mock dependencies
        with patch('firebase.models.plaid_token.PlaidToken.plaid_tokens') as mock_collection, \
             patch('firebase.models.plaid_token.keys') as mock_keys:
            
            # Setup mock user
            mock_user = Mock()
            mock_user.reference_id = 'test_user_123'
            
            # Mock the encryption
            mock_keys.encrypt.return_value = Mock(ciphertext=b'encrypted_data')
            
            # Create existing token request
            request_data = {
                'user_id': 'test_user_123',
                'created_at': datetime.datetime.now(),
                'redirect_uri': 'https://app.example.com',
                'tokens': []
            }
            mock_request_doc = Mock()
            mock_request_doc.reference.id = 'request_123'
            
            # Mock the query for existing token request
            mock_query = Mock()
            mock_query.where.return_value = mock_query
            mock_query.get.return_value = [mock_request_doc]
            mock_collection.where.return_value = mock_query
            
            # Mock the document get
            mock_doc_ref = Mock()
            mock_snapshot = MockDocumentSnapshot(request_data, 'test_user_123')
            mock_doc_ref.get.return_value = mock_snapshot
            mock_collection.document.return_value = mock_doc_ref
            
            # CRITICAL: Pass the actual data structure with correct field name
            account_data = [
                {'name': 'Business Checking', 'mask': '9876'},
                {'name': 'Business Savings', 'mask': '5432'}
            ]
            
            # This call should work with the correct field structure
            result = PlaidToken.save_or_add_token(
                account_names_and_numbers=account_data,  # Correct parameter name
                auth_token='test_auth_token',
                item_id='test_item_id',
                user=mock_user,
                bank_name='Chase Bank'
            )
            
            # Verify the update call contains the correct field name
            update_call = mock_doc_ref.update.call_args[0][0]
            assert 'tokens' in update_call
            
            # The token should have the correct structure
            saved_token = update_call['tokens'][0] if update_call['tokens'] else None
            if saved_token:
                assert 'account_names_and_numbers' in saved_token
                assert saved_token['account_names_and_numbers'] == account_data
                assert 'bank_name' in saved_token
                assert 'id' in saved_token
    
    def test_plaid_token_get_accounts_by_user_id_structure(self):
        """Test that get_accounts_by_user_id returns correct structure."""
        from firebase.models.plaid_token import PlaidToken
        
        with patch('firebase.models.plaid_token.PlaidToken.plaid_tokens') as mock_collection:
            # Create test data with correct field structure
            token_data = {
                'user_id': 'test_user_123',
                'tokens': [
                    {
                        'valid': True,
                        'bank_name': 'Wells Fargo',
                        'account_names_and_numbers': [
                            {'name': 'Personal Checking', 'mask': '1111'},
                            {'name': 'Personal Savings', 'mask': '2222'}
                        ],
                        'id': 'token_id_1'
                    },
                    {
                        'valid': False,  # Invalid token should be filtered
                        'bank_name': 'Bank of America',
                        'account_names_and_numbers': [
                            {'name': 'Credit Card', 'mask': '3333'}
                        ],
                        'id': 'token_id_2'
                    }
                ]
            }
            
            mock_snapshot = MockDocumentSnapshot(token_data, 'test_user_123', exists=True)
            mock_collection.document.return_value.get.return_value = mock_snapshot
            
            # Call the method
            accounts = PlaidToken.get_accounts_by_user_id('test_user_123')
            
            # Verify structure
            assert len(accounts) == 1  # Only valid token
            assert accounts[0]['bank_name'] == 'Wells Fargo'
            # The mask field should contain the account_names_and_numbers
            assert accounts[0]['mask'] == token_data['tokens'][0]['account_names_and_numbers']
            assert accounts[0]['id'] == 'token_id_1'
    
    def test_plaid_token_decrypted_tokens_structure(self):
        """Test that decrypted_tokens returns correct structure."""
        from firebase.models.plaid_token import PlaidToken
        import base64
        
        with patch('firebase.models.plaid_token.keys') as mock_keys, \
             patch('firebase.models.user.User') as mock_user_class, \
             patch('firebase.models.plaid_token.SETTINGS') as mock_settings:
            
            # Test in local mode (since account_names_and_numbers is now included in both modes)
            mock_settings.local = True
            
            # Mock user
            mock_user = Mock()
            mock_user.reference_id = 'test_user_123'
            mock_user.key_id = 'test-key-id'
            mock_user_class.get_user_by_id.return_value = mock_user
            
            # Create token with properly base64 encoded encrypted data
            token_data = {
                'user_id': 'test_user_123',
                'created_at': datetime.datetime.now(),
                'redirect_uri': 'https://app.example.com/plaid/callback',
                'tokens': [{
                    'valid': True,
                    'created_at': datetime.datetime.now(),
                    'auth_token': base64.b64encode(b'encrypted_auth_token').decode('utf-8'),
                    'item_id': base64.b64encode(b'encrypted_item_id').decode('utf-8'),
                    'account_names_and_numbers': [
                        {'name': 'Test Checking Account', 'mask': '1234'},
                        {'name': 'Test Savings Account', 'mask': '5678'}
                    ],
                    'bank_name': 'Test Bank',
                    'id': str(uuid.uuid4())
                }]
            }
            
            mock_snapshot = MockDocumentSnapshot(token_data, 'test_user_123')
            token = PlaidToken(mock_snapshot)
            
            # Call decrypted_tokens
            decrypted = token.decrypted_tokens()
            
            # Verify structure - account_names_and_numbers is now included in both local and non-local modes
            assert len(decrypted) == 1
            assert 'account_names_and_numbers' in decrypted[0]
            assert decrypted[0]['account_names_and_numbers'] == token.tokens[0]['account_names_and_numbers']
            assert 'auth_token' in decrypted[0]
            assert 'item_id' in decrypted[0]
    
    def test_plaid_token_empty_tokens_handling(self):
        """Test PlaidToken with empty tokens list."""
        token = FirebaseModelFactory.create_plaid_token(
            user_id="empty_test_user",
            with_accounts=False
        )
        
        assert token.tokens == []
        assert token.user_id == "empty_test_user"
        
        # Schema validation should still pass for empty tokens
        SchemaValidator.validate_plaid_token_schema(token)
    
    def test_plaid_token_multiple_accounts(self):
        """Test PlaidToken with multiple bank accounts."""
        from firebase.models.plaid_token import PlaidToken
        
        # Create token with custom account structure
        data = {
            'user_id': 'multi_account_user',
            'created_at': datetime.datetime.now(),
            'redirect_uri': 'https://app.example.com/plaid/callback',
            'tokens': [
                {
                    'valid': True,
                    'created_at': datetime.datetime.now(),
                    'auth_token': 'encrypted_auth_1',
                    'item_id': 'encrypted_item_1',
                    'account_names_and_numbers': [
                        {'name': 'Chase Checking', 'mask': '1234'},
                        {'name': 'Chase Savings', 'mask': '5678'},
                        {'name': 'Chase Credit Card', 'mask': '9012'}
                    ],
                    'bank_name': 'Chase Bank',
                    'id': str(uuid.uuid4())
                },
                {
                    'valid': True,
                    'created_at': datetime.datetime.now() - datetime.timedelta(days=30),
                    'auth_token': 'encrypted_auth_2',
                    'item_id': 'encrypted_item_2',
                    'account_names_and_numbers': [
                        {'name': 'Wells Fargo Checking', 'mask': '4321'}
                    ],
                    'bank_name': 'Wells Fargo',
                    'id': str(uuid.uuid4())
                }
            ]
        }
        
        mock_snapshot = MockDocumentSnapshot(data, 'multi_account_user')
        token = PlaidToken(mock_snapshot)
        
        # Validate structure
        assert len(token.tokens) == 2
        assert len(token.tokens[0]['account_names_and_numbers']) == 3
        assert len(token.tokens[1]['account_names_and_numbers']) == 1
        
        # Validate all accounts have correct structure
        for token_entry in token.tokens:
            assert 'account_names_and_numbers' in token_entry
            for account in token_entry['account_names_and_numbers']:
                assert 'name' in account
                assert 'mask' in account
    
    def test_plaid_token_field_name_regression(self):
        """
        Regression test to ensure we're using 'account_names_and_numbers' not 'account_names'.
        This test would FAIL if someone changed the field back to 'account_names'.
        """
        from firebase.models.plaid_token import PlaidToken
        
        # Try to create a token with the OLD field name - this should fail validation
        data = {
            'user_id': 'regression_test_user',
            'created_at': datetime.datetime.now(),
            'redirect_uri': 'https://app.example.com/plaid/callback',
            'tokens': [{
                'valid': True,
                'created_at': datetime.datetime.now(),
                'auth_token': 'encrypted',
                'item_id': 'encrypted',
                'account_names': [  # WRONG field name - old version
                    {'name': 'Account', 'mask': '1234'}
                ],
                'bank_name': 'Test Bank',
                'id': str(uuid.uuid4())
            }]
        }
        
        mock_snapshot = MockDocumentSnapshot(data, 'regression_test_user')
        token = PlaidToken(mock_snapshot)
        
        # This validation should FAIL because 'account_names_and_numbers' is missing
        with pytest.raises(AssertionError) as exc_info:
            SchemaValidator.validate_plaid_token_schema(token)
        
        assert "Token missing 'account_names_and_numbers' field" in str(exc_info.value)


class TestPlaidTokenMethodIntegration:
    """Test PlaidToken methods with minimal mocking."""
    
    def test_create_token_request_real_structure(self):
        """Test create_token_request creates proper structure."""
        from firebase.models.plaid_token import PlaidToken
        
        with patch('firebase.models.plaid_token.PlaidToken.plaid_tokens') as mock_collection:
            # Mock user
            mock_user = Mock()
            mock_user.reference_id = 'request_user_123'
            
            # Mock the document operations
            mock_doc = Mock()
            mock_collection.document.return_value = mock_doc
            
            # Mock the get() to return non-existing initially (for new user)
            mock_snapshot_not_exists = Mock()
            mock_snapshot_not_exists.exists = False
            
            # Then return existing snapshot after set() is called
            created_data = {
                'user_id': 'request_user_123',
                'created_at': datetime.datetime.now(),
                'redirect_uri': 'https://app.example.com/plaid/callback',
                'tokens': []
            }
            mock_snapshot_exists = MockDocumentSnapshot(created_data, 'request_user_123')
            
            # First call returns not exists, second call returns exists
            mock_doc.get.side_effect = [mock_snapshot_not_exists, mock_snapshot_exists]
            
            # Create the request with required redirect_uri parameter
            result = PlaidToken.create_token_request(mock_user, redirect_uri='https://app.example.com/plaid/callback')
            
            # Verify the structure of what was saved
            saved_data = mock_doc.set.call_args[0][0]
            assert 'user_id' in saved_data
            assert saved_data['user_id'] == 'request_user_123'
            assert 'created_at' in saved_data
            assert 'redirect_uri' in saved_data
            assert saved_data['redirect_uri'] == 'https://app.example.com/plaid/callback'
            assert 'tokens' in saved_data
            assert saved_data['tokens'] == []  # Should start empty
            
            # Verify the returned object has correct structure
            assert result.user_id == 'request_user_123'
            assert result.tokens == []
    
    def test_reset_tokens_real_structure(self):
        """Test reset_tokens properly deletes user tokens."""
        from firebase.models.plaid_token import PlaidToken
        
        with patch('firebase.models.plaid_token.PlaidToken.plaid_tokens') as mock_collection:
            # Mock existing token
            mock_doc = Mock()
            mock_doc.exists = True
            mock_doc.reference.delete = Mock()
            mock_collection.document.return_value.get.return_value = mock_doc
            
            # Reset tokens
            result = PlaidToken.reset_tokens('user_to_reset')
            
            assert result == True
            mock_doc.reference.delete.assert_called_once()
    
    def test_get_tokens_by_user_id_real_structure(self):
        """Test get_tokens_by_user_id returns proper structure."""
        from firebase.models.plaid_token import PlaidToken
        
        with patch('firebase.models.plaid_token.PlaidToken.plaid_tokens') as mock_collection:
            # Create test token data
            token_data = {
                'user_id': 'lookup_user',
                'created_at': datetime.datetime.now(),
                'tokens': [{
                    'valid': True,
                    'account_names_and_numbers': [
                        {'name': 'Checking', 'mask': '7890'}
                    ],
                    'bank_name': 'Local Bank',
                    'id': 'token_xyz'
                }]
            }
            
            mock_snapshot = MockDocumentSnapshot(token_data, 'lookup_user', exists=True)
            mock_collection.document.return_value.get.return_value = mock_snapshot
            
            # Get tokens
            result = PlaidToken.get_tokens_by_user_id('lookup_user')
            
            assert result is not None
            assert result.user_id == 'lookup_user'
            assert len(result.tokens) == 1
            assert 'account_names_and_numbers' in result.tokens[0]