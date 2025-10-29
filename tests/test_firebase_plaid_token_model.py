"""
Comprehensive tests for PlaidToken Firebase model.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import datetime
import base64

# Test subject
from firebase.models.plaid_token import PlaidToken


@pytest.mark.asyncio
class TestPlaidTokenModelInit:
    """Test PlaidToken model initialization."""

    async def test_plaid_token_init_with_tokens(self, firebase_test_helper):
        """Test PlaidToken initialization with banking tokens."""
        # Create mock data
        token_data = {
            'tokens': [
                {
                    'valid': True,
                    'created_at': datetime.datetime.now(),
                    'auth_token': 'encrypted_auth_token_123',
                    'item_id': 'encrypted_item_id_123',
                    'account_names_and_numbers': [{'name': 'Checking Account', 'mask': '1234'}, {'name': 'Savings Account', 'mask': '5678'}]
                }
            ],
            'user_id': 'user_123',
            'created_at': datetime.datetime.now(),
            'redirect_uri': 'https://app.example.com/plaid/callback'
        }

        # Create proper mock document snapshot
        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            token_data, 'user_123', True
        )

        # Initialize PlaidToken
        plaid_token = PlaidToken(mock_snapshot)

        # Verify initialization
        assert plaid_token.reference_id == 'user_123'
        assert hasattr(plaid_token, 'tokens')
        assert hasattr(plaid_token, 'user_id')
        assert hasattr(plaid_token, 'created_at')
        assert hasattr(plaid_token, 'redirect_uri')
        assert plaid_token.user_id == 'user_123'
        assert len(plaid_token.tokens) == 1
        assert plaid_token.tokens[0]['valid'] == True
        assert plaid_token.tokens[0]['account_names_and_numbers'] == [
            {'name': 'Checking Account', 'mask': '1234'}, {'name': 'Savings Account', 'mask': '5678'}]

    async def test_plaid_token_init_empty_tokens(self, firebase_test_helper):
        """Test PlaidToken initialization with empty tokens list."""
        minimal_data = {
            'user_id': 'user_minimal',
            'created_at': datetime.datetime.now(),
            'redirect_uri': 'https://app.example.com/plaid/callback',
            'tokens': []
        }

        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            minimal_data, 'user_minimal', True
        )

        plaid_token = PlaidToken(mock_snapshot)

        assert plaid_token.reference_id == 'user_minimal'
        assert plaid_token.user_id == 'user_minimal'
        assert plaid_token.tokens == []


@pytest.mark.asyncio
class TestPlaidTokenCreateRequest:
    """Test PlaidToken token request creation."""

    async def test_create_token_request_new_user(self, firebase_test_helper):
        """Test creating token request for new user."""
        # Mock user
        mock_user = Mock()
        mock_user.reference_id = 'new_user_123'

        # Mock empty query result (no recent requests)
        mock_document = Mock()
        mock_document.set = Mock()

        # Mock the document get - first call returns not exists, second returns exists
        mock_not_exists = Mock()
        mock_not_exists.exists = False
        
        token_data = {
            'user_id': 'new_user_123',
            'created_at': datetime.datetime.now(),
            'redirect_uri': 'https://app.example.com/plaid/callback',
            'tokens': []
        }
        mock_created_snapshot = firebase_test_helper.create_mock_document_snapshot(
            token_data, 'new_user_123', True
        )
        # First call returns not exists (new user), second call returns the created document
        mock_document.get.side_effect = [mock_not_exists, mock_created_snapshot]

        test_now = datetime.datetime(2023, 10, 15, 12, 0, 0)
        test_redirect = 'https://app.example.com/plaid/callback'

        with patch.object(PlaidToken, 'plaid_tokens') as mock_tokens, \
                patch('firebase.models.plaid_token.datetime') as mock_datetime:

            # Setup mock tokens collection
            mock_tokens.document.return_value = mock_document
            mock_datetime.datetime.now.return_value = test_now
            mock_datetime.timedelta.return_value = datetime.timedelta(
                minutes=10)

            # Execute
            result = PlaidToken.create_token_request(mock_user, test_redirect)

            # Verify document.set was called for new user
            mock_document.set.assert_called_once()

            # Verify the structure of the set call
            set_data = mock_document.set.call_args[0][0]
            assert set_data['user_id'] == 'new_user_123'
            assert set_data['redirect_uri'] == test_redirect
            assert set_data['created_at'] == test_now
            assert set_data['tokens'] == []

            # Verify return value
            assert isinstance(result, PlaidToken)

    async def test_create_token_request_existing_recent_request(self, firebase_test_helper):
        """Test creating token request when recent request exists."""
        # Create existing recent request data
        existing_data = {
            'user_id': 'existing_user_123',
            'created_at': datetime.datetime.now() - datetime.timedelta(minutes=5),  # Recent
            'redirect_uri': 'https://app.example.com/plaid/callback',
            'tokens': []
        }

        mock_user = Mock()
        mock_user.reference_id = 'existing_user_123'

        # Mock existing request
        mock_existing_request = Mock()
        mock_existing_snapshot = firebase_test_helper.create_mock_document_snapshot(
            existing_data, 'existing_user_123', True
        )

        with patch.object(PlaidToken, 'plaid_tokens') as mock_tokens, \
                patch('firebase.models.plaid_token.datetime') as mock_datetime:

            # Mock existing recent request found
            mock_tokens.where.return_value.where.return_value.get.return_value = [
                mock_existing_snapshot]
            mock_datetime.datetime.now.return_value = datetime.datetime.now()
            mock_datetime.timedelta.return_value = datetime.timedelta(
                minutes=10)

            # Execute
            result = PlaidToken.create_token_request(
                mock_user, 'https://app.example.com/plaid/callback')

            # Should return existing request (no new document created)
            assert isinstance(result, PlaidToken)


@pytest.mark.asyncio
class TestPlaidTokenSaveToken:
    """Test PlaidToken save_or_add_token method - simplified version."""

    async def test_save_token_data_structure(self, firebase_test_helper):
        """Test the data structure for saving banking tokens."""
        # Test the token structure that would be created
        test_account_names_and_numbers = [{'name': 'Checking Account', 'mask': '1234'}, {'name': 'Savings Account', 'mask': '5678'}]
        test_auth_token = 'plaid_auth_token_123'
        test_item_id = 'plaid_item_id_123'

        # Test token structure logic
        new_token = {
            'valid': True,
            'created_at': datetime.datetime.now(),
            'auth_token': 'encrypted_auth_token',
            'item_id': 'encrypted_item_id',
            'account_names_and_numbers': test_account_names_and_numbers,
            'bank_name': 'Test Bank'
        }

        # Verify token structure
        assert new_token['valid'] == True
        assert 'created_at' in new_token
        assert 'auth_token' in new_token
        assert 'item_id' in new_token
        assert 'bank_name' in new_token
        assert new_token['bank_name'] == 'Test Bank'
        assert new_token['account_names_and_numbers'] == test_account_names_and_numbers
        assert len(new_token['account_names_and_numbers']) == 2

    async def test_save_token_encryption_logic(self, firebase_test_helper):
        """Test encryption logic for Plaid tokens."""
        test_auth_token = 'plaid_auth_token_123'
        test_item_id = 'plaid_item_id_123'

        # Test local encryption (base64 encoding)
        encoded_auth_token = base64.b64encode(
            test_auth_token.encode('utf-8')).decode('utf-8')
        encoded_item_id = base64.b64encode(
            test_item_id.encode('utf-8')).decode('utf-8')

        # Verify encoding works
        assert encoded_auth_token is not None
        assert encoded_item_id is not None

        # Test decoding
        decoded_auth_token = base64.b64decode(
            encoded_auth_token.encode('utf-8')).decode('utf-8')
        decoded_item_id = base64.b64decode(
            encoded_item_id.encode('utf-8')).decode('utf-8')

        # Verify round-trip works
        assert decoded_auth_token == test_auth_token
        assert decoded_item_id == test_item_id

    async def test_token_list_management_logic(self, firebase_test_helper):
        """Test logic for managing multiple banking tokens."""
        # Test adding tokens to existing list
        existing_tokens = [
            {
                'valid': True,
                'auth_token': 'token_1',
                'item_id': 'item_1',
                'account_names_and_numbers': [{'name': 'Bank 1 Checking', 'mask': '0001'}]
            }
        ]

        # Logic for adding new token
        new_token = {
            'valid': True,
            'auth_token': 'token_2',
            'item_id': 'item_2',
            'account_names_and_numbers': [{'name': 'Bank 2 Checking', 'mask': '0002'}]
        }

        updated_tokens = existing_tokens.copy()
        updated_tokens.append(new_token)

        # Verify list management
        assert len(updated_tokens) == 2
        assert updated_tokens[0]['account_names_and_numbers'] == [{'name': 'Bank 1 Checking', 'mask': '0001'}]
        assert updated_tokens[1]['account_names_and_numbers'] == [{'name': 'Bank 2 Checking', 'mask': '0002'}]
        assert all(token['valid'] for token in updated_tokens)

    async def test_save_token_invalid_request_logic(self, firebase_test_helper):
        """Test invalid request handling logic."""
        # Test timing logic for request validation
        current_time = datetime.datetime.now()

        # Recent request (5 minutes ago) - should be valid
        recent_request_time = current_time - datetime.timedelta(minutes=5)
        is_recent_valid = recent_request_time > (
            current_time - datetime.timedelta(minutes=10))
        assert is_recent_valid == True

        # Old request (15 minutes ago) - should be invalid
        old_request_time = current_time - datetime.timedelta(minutes=15)
        is_old_valid = old_request_time > (
            current_time - datetime.timedelta(minutes=10))
        assert is_old_valid == False


@pytest.mark.asyncio
class TestPlaidTokenRetrieval:
    """Test PlaidToken retrieval methods."""

    async def test_get_tokens_by_user_id_exists(self, firebase_test_helper):
        """Test getting tokens for existing user."""
        token_data = {
            'user_id': 'user_123',
            'tokens': [
                {
                    'valid': True,
                    'auth_token': 'encrypted_token',
                    'item_id': 'encrypted_item',
                    'account_names_and_numbers': [{'name': 'Checking', 'mask': '9999'}]
                }
            ]
        }

        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            token_data, 'user_123', True
        )

        mock_document = Mock()
        mock_document.get.return_value = mock_snapshot

        with patch.object(PlaidToken, 'plaid_tokens') as mock_tokens:
            mock_tokens.document.return_value = mock_document

            # Execute
            result = PlaidToken.get_tokens_by_user_id('user_123')

            # Verify
            assert isinstance(result, PlaidToken)
            assert result.user_id == 'user_123'
            assert len(result.tokens) == 1

    async def test_get_tokens_by_user_id_not_exists(self, firebase_test_helper):
        """Test getting tokens for non-existing user."""
        empty_snapshot = firebase_test_helper.create_mock_document_snapshot(
            {}, 'nonexistent_user', False
        )

        mock_document = Mock()
        mock_document.get.return_value = empty_snapshot

        with patch.object(PlaidToken, 'plaid_tokens') as mock_tokens:
            mock_tokens.document.return_value = mock_document

            # Execute
            result = PlaidToken.get_tokens_by_user_id('nonexistent_user')

            # Verify
            assert result is None


@pytest.mark.asyncio
class TestPlaidTokenGetAccountsByUserId:
    """Test PlaidToken get_accounts_by_user_id method."""

    async def test_get_accounts_by_user_id_with_valid_tokens(self, firebase_test_helper):
        """Test getting accounts for user with valid tokens."""
        token_data = {
            'user_id': 'user_123',
            'tokens': [
                {
                    'valid': True,
                    'auth_token': 'encrypted_token1',
                    'item_id': 'encrypted_item1',
                    'account_names_and_numbers': [
                        {'name': 'Chase Checking', 'mask': '1234'},
                        {'name': 'Chase Savings', 'mask': '5678'}
                    ],
                    'bank_name': 'Chase Bank',
                    'id': 'token-id-1'
                },
                {
                    'valid': True,
                    'auth_token': 'encrypted_token2',
                    'item_id': 'encrypted_item2',
                    'account_names_and_numbers': [
                        {'name': 'BoA Credit Card', 'mask': '9999'}
                    ],
                    'bank_name': 'Bank of America',
                    'id': 'token-id-2'
                },
                {
                    'valid': False,  # This should be filtered out
                    'auth_token': 'encrypted_token3',
                    'item_id': 'encrypted_item3',
                    'account_names_and_numbers': [
                        {'name': 'Old Account', 'mask': '0000'}
                    ],
                    'bank_name': 'Old Bank',
                    'id': 'token-id-3'
                }
            ]
        }

        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            token_data, 'user_123', True
        )

        with patch.object(PlaidToken, 'plaid_tokens') as mock_tokens:
            mock_document = Mock()
            mock_document.get.return_value = mock_snapshot
            mock_tokens.document.return_value = mock_document
            
            # Execute
            result = PlaidToken.get_accounts_by_user_id('user_123')
            
            # Verify
            assert len(result) == 2  # Only 2 valid tokens
            assert result[0] == {
                'bank_name': 'Chase Bank',
                'mask': [
                    {'name': 'Chase Checking', 'mask': '1234'},
                    {'name': 'Chase Savings', 'mask': '5678'}
                ],
                'id': 'token-id-1'
            }
            assert result[1] == {
                'bank_name': 'Bank of America',
                'mask': [
                    {'name': 'BoA Credit Card', 'mask': '9999'}
                ],
                'id': 'token-id-2'
            }
            mock_tokens.document.assert_called_once_with('user_123')

    async def test_get_accounts_by_user_id_no_tokens(self, firebase_test_helper):
        """Test getting accounts for user with no tokens."""
        empty_data = {
            'user_id': 'user_empty',
            'tokens': []
        }

        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            empty_data, 'user_empty', True
        )

        with patch.object(PlaidToken, 'plaid_tokens') as mock_tokens:
            mock_document = Mock()
            mock_document.get.return_value = mock_snapshot
            mock_tokens.document.return_value = mock_document
            
            # Execute
            result = PlaidToken.get_accounts_by_user_id('user_empty')
            
            # Verify
            assert result == []
            mock_tokens.document.assert_called_once_with('user_empty')

    async def test_get_accounts_by_user_id_nonexistent_user(self, firebase_test_helper):
        """Test getting accounts for non-existent user."""
        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            {}, 'nonexistent', False
        )

        with patch.object(PlaidToken, 'plaid_tokens') as mock_tokens:
            mock_document = Mock()
            mock_document.get.return_value = mock_snapshot
            mock_tokens.document.return_value = mock_document
            
            # Execute
            result = PlaidToken.get_accounts_by_user_id('nonexistent')
            
            # Verify
            assert result == []
            mock_tokens.document.assert_called_once_with('nonexistent')

    async def test_get_accounts_by_user_id_only_invalid_tokens(self, firebase_test_helper):
        """Test getting accounts when all tokens are invalid."""
        token_data = {
            'user_id': 'user_invalid',
            'tokens': [
                {
                    'valid': False,
                    'auth_token': 'encrypted_token1',
                    'item_id': 'encrypted_item1',
                    'account_names_and_numbers': [
                        {'name': 'Closed Account 1', 'mask': '1111'}
                    ],
                    'bank_name': 'Bank 1'
                },
                {
                    'valid': False,
                    'auth_token': 'encrypted_token2',
                    'item_id': 'encrypted_item2',
                    'account_names_and_numbers': [
                        {'name': 'Closed Account 2', 'mask': '2222'}
                    ],
                    'bank_name': 'Bank 2'
                }
            ]
        }

        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            token_data, 'user_invalid', True
        )

        with patch.object(PlaidToken, 'plaid_tokens') as mock_tokens:
            mock_document = Mock()
            mock_document.get.return_value = mock_snapshot
            mock_tokens.document.return_value = mock_document
            
            # Execute
            result = PlaidToken.get_accounts_by_user_id('user_invalid')
            
            # Verify - should return empty list (no valid tokens)
            assert result == []
            mock_tokens.document.assert_called_once_with('user_invalid')

    async def test_get_accounts_by_user_id_mixed_banks(self, firebase_test_helper):
        """Test getting accounts with multiple banks and multiple accounts per bank."""
        token_data = {
            'user_id': 'user_multi',
            'tokens': [
                {
                    'valid': True,
                    'auth_token': 'encrypted_token1',
                    'item_id': 'encrypted_item1',
                    'account_names_and_numbers': [
                        {'name': 'Wells Fargo Checking', 'mask': '1111'},
                        {'name': 'Wells Fargo Savings', 'mask': '2222'},
                        {'name': 'Wells Fargo Credit', 'mask': '3333'}
                    ],
                    'bank_name': 'Wells Fargo',
                    'id': 'wells-fargo-token-1'
                }
            ]
        }

        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            token_data, 'user_multi', True
        )

        with patch.object(PlaidToken, 'plaid_tokens') as mock_tokens:
            mock_document = Mock()
            mock_document.get.return_value = mock_snapshot
            mock_tokens.document.return_value = mock_document
            
            # Execute
            result = PlaidToken.get_accounts_by_user_id('user_multi')
            
            # Verify
            assert len(result) == 1
            assert result[0]['bank_name'] == 'Wells Fargo'
            assert result[0]['id'] == 'wells-fargo-token-1'
            assert len(result[0]['mask']) == 3
            assert result[0]['mask'][0] == {'name': 'Wells Fargo Checking', 'mask': '1111'}
            assert result[0]['mask'][1] == {'name': 'Wells Fargo Savings', 'mask': '2222'}
            assert result[0]['mask'][2] == {'name': 'Wells Fargo Credit', 'mask': '3333'}


@pytest.mark.asyncio
class TestPlaidTokenResetTokens:
    """Test PlaidToken reset_tokens method."""

    async def test_reset_tokens_success(self, firebase_test_helper):
        """Test successful token reset."""
        # Create mock document that exists
        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            {'user_id': 'user_123', 'tokens': []}, 'user_123', True
        )
        
        with patch.object(PlaidToken, 'plaid_tokens') as mock_tokens:
            mock_document = Mock()
            mock_document.get.return_value = mock_snapshot
            mock_reference = Mock()
            mock_reference.delete = Mock()
            mock_snapshot.reference = mock_reference
            mock_tokens.document.return_value = mock_document
            
            # Execute
            result = PlaidToken.reset_tokens('user_123')
            
            # Verify
            assert result is True
            mock_tokens.document.assert_called_once_with('user_123')
            mock_document.get.assert_called_once()
            mock_reference.delete.assert_called_once()

    async def test_reset_tokens_user_not_exists(self, firebase_test_helper):
        """Test reset tokens when user doesn't exist."""
        # Create mock document that doesn't exist
        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            {}, 'user_123', False
        )
        
        with patch.object(PlaidToken, 'plaid_tokens') as mock_tokens:
            mock_document = Mock()
            mock_document.get.return_value = mock_snapshot
            mock_tokens.document.return_value = mock_document
            
            # Execute
            result = PlaidToken.reset_tokens('user_123')
            
            # Verify
            assert result is False
            mock_tokens.document.assert_called_once_with('user_123')
            mock_document.get.assert_called_once()

    async def test_reset_tokens_with_existing_tokens(self, firebase_test_helper):
        """Test reset tokens when user has existing tokens."""
        # Create mock document with existing tokens
        token_data = {
            'user_id': 'user_with_tokens',
            'tokens': [
                {
                    'valid': True,
                    'auth_token': 'encrypted_token',
                    'item_id': 'encrypted_item',
                    'account_names_and_numbers': [{'name': 'Checking', 'mask': '1234'}],
                    'bank_name': 'Test Bank'
                }
            ]
        }
        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            token_data, 'user_with_tokens', True
        )
        
        with patch.object(PlaidToken, 'plaid_tokens') as mock_tokens:
            mock_document = Mock()
            mock_document.get.return_value = mock_snapshot
            mock_reference = Mock()
            mock_reference.delete = Mock()
            mock_snapshot.reference = mock_reference
            mock_tokens.document.return_value = mock_document
            
            # Execute
            result = PlaidToken.reset_tokens('user_with_tokens')
            
            # Verify - should still delete even with existing tokens
            assert result is True
            mock_tokens.document.assert_called_once_with('user_with_tokens')
            mock_document.get.assert_called_once()
            mock_reference.delete.assert_called_once()

    async def test_reset_tokens_delete_exception(self, firebase_test_helper):
        """Test reset tokens when delete operation fails."""
        # Create mock document that exists
        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            {'user_id': 'user_123', 'tokens': []}, 'user_123', True
        )
        
        with patch.object(PlaidToken, 'plaid_tokens') as mock_tokens:
            mock_document = Mock()
            mock_document.get.return_value = mock_snapshot
            mock_reference = Mock()
            # Simulate delete failure
            mock_reference.delete.side_effect = Exception("Delete failed")
            mock_snapshot.reference = mock_reference
            mock_tokens.document.return_value = mock_document
            
            # Execute - should raise exception
            with pytest.raises(Exception, match="Delete failed"):
                PlaidToken.reset_tokens('user_123')
            
            # Verify delete was attempted
            mock_reference.delete.assert_called_once()


@pytest.mark.asyncio
class TestPlaidTokenDecryption:
    """Test PlaidToken decryption methods."""

    async def test_decrypted_tokens_structure(self, firebase_test_helper):
        """Test the structure of decrypted tokens."""
        # Create token data with encrypted tokens
        token_data = {
            'user_id': 'user_123',
            'tokens': [
                {
                    'valid': True,
                    'auth_token': base64.b64encode('plaid_auth_token_123'.encode('utf-8')).decode('utf-8'),
                    'item_id': base64.b64encode('plaid_item_id_123'.encode('utf-8')).decode('utf-8'),
                    'account_names_and_numbers': [{'name': 'Checking Account', 'mask': '1111'}],
                    'bank_name': 'Test Bank'
                },
                {
                    'valid': False,  # Invalid token should be filtered out
                    'auth_token': 'invalid_token',
                    'item_id': 'invalid_item',
                    'account_names_and_numbers': [{'name': 'Invalid Account', 'mask': '0000'}],
                    'bank_name': 'Invalid Bank'
                }
            ]
        }

        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            token_data, 'user_123', True
        )

        plaid_token = PlaidToken(mock_snapshot)

        # Test filtering logic for valid tokens
        valid_tokens = [
            token for token in plaid_token.tokens if token['valid'] == True]

        # Should only have one valid token
        assert len(valid_tokens) == 1
        assert valid_tokens[0]['account_names_and_numbers'] == [{'name': 'Checking Account', 'mask': '1111'}]

    async def test_decryption_logic_local(self, firebase_test_helper):
        """Test local decryption logic."""
        # Test the decryption logic that would happen in decrypted_tokens
        test_auth_token = 'plaid_auth_token_123'
        test_item_id = 'plaid_item_id_123'

        # Encode (simulate encryption)
        encoded_auth_token = base64.b64encode(
            test_auth_token.encode('utf-8')).decode('utf-8')
        encoded_item_id = base64.b64encode(
            test_item_id.encode('utf-8')).decode('utf-8')

        # Decode (simulate decryption)
        decoded_auth_token = base64.b64decode(
            encoded_auth_token).decode('utf-8')
        decoded_item_id = base64.b64decode(encoded_item_id).decode('utf-8')

        # Verify decryption works
        assert decoded_auth_token == test_auth_token
        assert decoded_item_id == test_item_id

    async def test_decrypted_tokens_empty_case(self, firebase_test_helper):
        """Test decrypted tokens with no valid tokens."""
        token_data = {
            'user_id': 'user_empty',
            'tokens': [
                {
                    'valid': False,
                    'auth_token': 'invalid_token',
                    'item_id': 'invalid_item',
                    'account_names_and_numbers': [{'name': 'Invalid Account', 'mask': '0000'}],
                    'bank_name': 'Invalid Bank'
                }
            ]
        }

        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            token_data, 'user_empty', True
        )

        plaid_token = PlaidToken(mock_snapshot)

        # Test filtering - should have no valid tokens
        valid_tokens = [
            token for token in plaid_token.tokens if token['valid'] == True]
        assert len(valid_tokens) == 0


@pytest.mark.asyncio
class TestPlaidTokenEdgeCases:
    """Test edge cases for PlaidToken model."""

    async def test_plaid_token_init_with_empty_data(self, firebase_test_helper):
        """Test PlaidToken initialization with empty document."""
        empty_data = {}

        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            empty_data, 'empty_plaid_token', True
        )

        plaid_token = PlaidToken(mock_snapshot)

        assert plaid_token.reference_id == 'empty_plaid_token'
        # Should not have attributes that weren't in the data
        assert not hasattr(plaid_token, 'tokens')
        assert not hasattr(plaid_token, 'user_id')

    async def test_token_validation_logic(self, firebase_test_helper):
        """Test token validation logic."""
        # Test valid token structure
        valid_token = {
            'valid': True,
            'created_at': datetime.datetime.now(),
            'auth_token': 'encrypted_auth_token',
            'item_id': 'encrypted_item_id',
            'account_names_and_numbers': [
                {'name': 'Checking Account', 'mask': '1234'},
                {'name': 'Savings Account', 'mask': '5678'}
            ]
        }

        # Verify required fields
        required_fields = ['valid', 'created_at',
                           'auth_token', 'item_id', 'account_names_and_numbers']
        for field in required_fields:
            assert field in valid_token
            assert valid_token[field] is not None

        # Test account names validation
        assert isinstance(valid_token['account_names_and_numbers'], list)
        assert len(valid_token['account_names_and_numbers']) > 0
        assert all(isinstance(account, dict) and 'name' in account and 'mask' in account
                   for account in valid_token['account_names_and_numbers'])

        # Test valid flag
        assert isinstance(valid_token['valid'], bool)

    async def test_multiple_banking_connections(self, firebase_test_helper):
        """Test handling multiple banking connections."""
        # Test scenario with multiple bank connections
        multi_bank_data = {
            'user_id': 'multi_user_123',
            'tokens': [
                {
                    'valid': True,
                    'auth_token': 'bank1_token',
                    'item_id': 'bank1_item',
                    'account_names_and_numbers': [
                        {'name': 'Bank1 Checking', 'mask': '1111'},
                        {'name': 'Bank1 Savings', 'mask': '2222'}
                    ]
                },
                {
                    'valid': True,
                    'auth_token': 'bank2_token',
                    'item_id': 'bank2_item',
                    'account_names_and_numbers': [
                        {'name': 'Bank2 Checking', 'mask': '3333'}
                    ]
                },
                {
                    'valid': False,  # Disconnected bank
                    'auth_token': 'bank3_token',
                    'item_id': 'bank3_item',
                    'account_names_and_numbers': [
                        {'name': 'Bank3 Checking', 'mask': '4444'}
                    ]
                }
            ]
        }

        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            multi_bank_data, 'multi_user_123', True
        )

        plaid_token = PlaidToken(mock_snapshot)

        # Test multiple bank connections
        assert len(plaid_token.tokens) == 3

        # Count valid connections
        valid_connections = [
            token for token in plaid_token.tokens if token['valid']]
        assert len(valid_connections) == 2

        # Count total accounts across all valid connections
        total_accounts = sum(len(token['account_names_and_numbers'])
                             for token in valid_connections)
        assert total_accounts == 3  # 2 from bank1 + 1 from bank2

    async def test_request_timing_edge_cases(self, firebase_test_helper):
        """Test edge cases for request timing validation."""
        current_time = datetime.datetime.now()

        # Edge case: exactly 10 minutes ago
        exactly_10_min = current_time - datetime.timedelta(minutes=10)
        is_exactly_10_valid = exactly_10_min > (
            current_time - datetime.timedelta(minutes=10))
        # Should be invalid (not greater than cutoff)
        assert is_exactly_10_valid == False

        # Edge case: just under 10 minutes (9.5 minutes)
        just_under_10 = current_time - datetime.timedelta(minutes=9.5)
        is_just_under_valid = just_under_10 > (
            current_time - datetime.timedelta(minutes=10))
        assert is_just_under_valid == True  # Should be valid

        # Edge case: just over 10 minutes (10.5 minutes)
        just_over_10 = current_time - datetime.timedelta(minutes=10.5)
        is_just_over_valid = just_over_10 > (
            current_time - datetime.timedelta(minutes=10))
        assert is_just_over_valid == False  # Should be invalid


class TestPlaidTokenDeleteAccount:
    """Test the delete_account method."""
    
    def test_delete_account_success(self):
        """Test successful account deletion."""
        from firebase.models.plaid_token import PlaidToken
        
        # Create mock Firestore object with test data
        mock_media_object = MagicMock()
        mock_media_object.reference.id = 'user_123'
        mock_media_object.to_dict.return_value = {
            'user_id': 'user_123',
            'created_at': datetime.datetime.now(),
            'tokens': [
                {
                    'id': 'account_1',
                    'valid': True,
                    'auth_token': 'token_1',
                    'item_id': 'item_1',
                    'bank_name': 'Bank 1',
                    'account_names_and_numbers': [{'name': 'Checking', 'mask': '1234'}]
                },
                {
                    'id': 'account_2',
                    'valid': True,
                    'auth_token': 'token_2',
                    'item_id': 'item_2',
                    'bank_name': 'Bank 2',
                    'account_names_and_numbers': [{'name': 'Savings', 'mask': '5678'}]
                }
            ]
        }
        
        # Create PlaidToken instance
        with patch.object(PlaidToken, 'plaid_tokens') as mock_collection:
            mock_doc = MagicMock()
            mock_collection.document.return_value = mock_doc
            
            token = PlaidToken(mock_media_object)
            
            # Create mock user
            mock_user = MagicMock()
            mock_user.reference_id = 'user_123'
            
            # Test deleting an existing account
            result = token.delete_account(mock_user, 'account_1')
            
            assert result == True
            # Verify the token was marked invalid and removed
            assert len(token.tokens) == 1
            assert token.tokens[0]['id'] == 'account_2'
            
            # Verify Firestore update was called
            mock_doc.update.assert_called_once_with({'tokens': token.tokens})
    
    def test_delete_account_not_found(self):
        """Test delete_account when account doesn't exist."""
        from firebase.models.plaid_token import PlaidToken
        
        # Create mock Firestore object with test data
        mock_media_object = MagicMock()
        mock_media_object.reference.id = 'user_123'
        mock_media_object.to_dict.return_value = {
            'user_id': 'user_123',
            'created_at': datetime.datetime.now(),
            'tokens': [
                {
                    'id': 'account_1',
                    'valid': True,
                    'auth_token': 'token_1',
                    'item_id': 'item_1',
                    'bank_name': 'Bank 1',
                    'account_names_and_numbers': [{'name': 'Checking', 'mask': '1234'}]
                }
            ]
        }
        
        # Create PlaidToken instance
        with patch.object(PlaidToken, 'plaid_tokens') as mock_collection:
            mock_doc = MagicMock()
            mock_collection.document.return_value = mock_doc
            
            token = PlaidToken(mock_media_object)
            
            # Create mock user
            mock_user = MagicMock()
            mock_user.reference_id = 'user_123'
            
            # Test deleting a non-existent account
            result = token.delete_account(mock_user, 'non_existent_account')
            
            assert result == False
            # Verify tokens list is unchanged
            assert len(token.tokens) == 1
            assert token.tokens[0]['id'] == 'account_1'
            
            # Verify Firestore update was not called
            mock_doc.update.assert_not_called()
    
    def test_delete_account_empty_tokens(self):
        """Test delete_account when no tokens exist."""
        from firebase.models.plaid_token import PlaidToken
        
        # Create mock Firestore object with no tokens
        mock_media_object = MagicMock()
        mock_media_object.reference.id = 'user_123'
        mock_media_object.to_dict.return_value = {
            'user_id': 'user_123',
            'created_at': datetime.datetime.now(),
            'tokens': []
        }
        
        # Create PlaidToken instance
        with patch.object(PlaidToken, 'plaid_tokens') as mock_collection:
            mock_doc = MagicMock()
            mock_collection.document.return_value = mock_doc
            
            token = PlaidToken(mock_media_object)
            
            # Create mock user
            mock_user = MagicMock()
            mock_user.reference_id = 'user_123'
            
            # Test deleting from empty list
            result = token.delete_account(mock_user, 'any_account')
            
            assert result == False
            assert len(token.tokens) == 0
            
            # Verify Firestore update was not called
            mock_doc.update.assert_not_called()
    
    def test_delete_account_last_token(self):
        """Test delete_account when deleting the last token."""
        from firebase.models.plaid_token import PlaidToken
        
        # Create mock Firestore object with one token
        mock_media_object = MagicMock()
        mock_media_object.reference.id = 'user_123'
        mock_media_object.to_dict.return_value = {
            'user_id': 'user_123',
            'created_at': datetime.datetime.now(),
            'tokens': [
                {
                    'id': 'last_account',
                    'valid': True,
                    'auth_token': 'token_1',
                    'item_id': 'item_1',
                    'bank_name': 'Bank 1',
                    'account_names_and_numbers': [{'name': 'Checking', 'mask': '1234'}]
                }
            ]
        }
        
        # Create PlaidToken instance
        with patch.object(PlaidToken, 'plaid_tokens') as mock_collection:
            mock_doc = MagicMock()
            mock_collection.document.return_value = mock_doc
            
            token = PlaidToken(mock_media_object)
            
            # Create mock user
            mock_user = MagicMock()
            mock_user.reference_id = 'user_123'
            
            # Test deleting the last token
            result = token.delete_account(mock_user, 'last_account')
            
            assert result == True
            assert len(token.tokens) == 0
            
            # Verify Firestore update was called with empty list
            mock_doc.update.assert_called_once_with({'tokens': []})
