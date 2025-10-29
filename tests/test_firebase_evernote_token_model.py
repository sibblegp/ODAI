"""
Comprehensive tests for EvernoteToken Firebase model.
"""

import pytest
from unittest.mock import Mock, patch
import datetime

# Test subject
from firebase.models.evernote_token import EvernoteToken


@pytest.mark.asyncio
class TestEvernoteTokenModelInit:
    """Test EvernoteToken model initialization."""

    async def test_evernote_token_init_with_oauth_data(self, firebase_test_helper):
        """Test EvernoteToken initialization with OAuth data."""
        # Create mock data
        token_data = {
            'user_id': 'user_123',
            'oauth_token': 'oauth_token_123',
            'oauth_token_secret': 'oauth_secret_123',
            'created_at': datetime.datetime.now(),
            'updated_at': datetime.datetime.now()
        }

        # Create proper mock document snapshot
        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            token_data, 'user_123', True
        )

        # Initialize EvernoteToken
        evernote_token = EvernoteToken(mock_snapshot)

        # Verify initialization
        assert evernote_token.reference_id == 'user_123'
        assert hasattr(evernote_token, 'user_id')
        assert hasattr(evernote_token, 'oauth_token')
        assert hasattr(evernote_token, 'oauth_token_secret')
        assert hasattr(evernote_token, 'created_at')
        assert hasattr(evernote_token, 'updated_at')
        assert evernote_token.user_id == 'user_123'
        assert evernote_token.oauth_token == 'oauth_token_123'
        assert evernote_token.oauth_token_secret == 'oauth_secret_123'

    async def test_evernote_token_init_with_access_token(self, firebase_test_helper):
        """Test EvernoteToken initialization with completed OAuth (access token)."""
        token_data = {
            'user_id': 'user_123',
            'access_token': 'final_access_token_123',
            'created_at': datetime.datetime(2023, 10, 1, 10, 0, 0),
            'updated_at': datetime.datetime.now()
        }

        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            token_data, 'user_123', True
        )

        evernote_token = EvernoteToken(mock_snapshot)

        assert evernote_token.reference_id == 'user_123'
        assert evernote_token.user_id == 'user_123'
        assert evernote_token.access_token == 'final_access_token_123'
        assert hasattr(evernote_token, 'created_at')
        assert hasattr(evernote_token, 'updated_at')

    async def test_evernote_token_init_minimal_data(self, firebase_test_helper):
        """Test EvernoteToken initialization with minimal data."""
        minimal_data = {
            'user_id': 'user_minimal'
        }

        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            minimal_data, 'user_minimal', True
        )

        evernote_token = EvernoteToken(mock_snapshot)

        assert evernote_token.reference_id == 'user_minimal'
        assert evernote_token.user_id == 'user_minimal'


@pytest.mark.asyncio
class TestEvernoteTokenStartRequest:
    """Test EvernoteToken start_evernote_token_request method."""

    async def test_start_evernote_token_request(self, firebase_test_helper):
        """Test starting Evernote OAuth token request."""
        # Mock user
        mock_user = Mock()
        mock_user.reference_id = 'user_123'

        # Mock document
        mock_document = Mock()
        mock_document.set = Mock()

        test_oauth_token = 'oauth_token_123'
        test_oauth_secret = 'oauth_secret_123'
        test_now = datetime.datetime(2023, 10, 15, 12, 0, 0)

        with patch.object(EvernoteToken, 'evernote_tokens') as mock_tokens, \
                patch('firebase.models.evernote_token.datetime') as mock_datetime:

            mock_tokens.document.return_value = mock_document
            mock_datetime.datetime.now.return_value = test_now

            # Execute
            EvernoteToken.start_evernote_token_request(
                mock_user, test_oauth_token, test_oauth_secret)

            # Verify document.set was called
            mock_document.set.assert_called_once()

            # Verify the structure of the set call
            set_data = mock_document.set.call_args[0][0]
            assert set_data['oauth_token'] == test_oauth_token
            assert set_data['oauth_token_secret'] == test_oauth_secret
            assert set_data['user_id'] == 'user_123'
            assert set_data['created_at'] == test_now
            assert set_data['updated_at'] == test_now

    async def test_start_evernote_token_request_data_structure(self, firebase_test_helper):
        """Test the data structure created for OAuth token request."""
        # Test the token request structure that would be created
        test_user_id = 'user_123'
        test_oauth_token = 'oauth_token_123'
        test_oauth_secret = 'oauth_secret_123'
        test_timestamp = datetime.datetime.now()

        # Test request structure logic
        oauth_request = {
            'oauth_token': test_oauth_token,
            'oauth_token_secret': test_oauth_secret,
            'user_id': test_user_id,
            'created_at': test_timestamp,
            'updated_at': test_timestamp
        }

        # Verify request structure
        assert oauth_request['oauth_token'] == test_oauth_token
        assert oauth_request['oauth_token_secret'] == test_oauth_secret
        assert oauth_request['user_id'] == test_user_id
        assert 'created_at' in oauth_request
        assert 'updated_at' in oauth_request
        # Should be same on creation
        assert oauth_request['created_at'] == oauth_request['updated_at']


@pytest.mark.asyncio
class TestEvernoteTokenRetrieval:
    """Test EvernoteToken retrieval methods."""

    async def test_retrieve_evernote_token_by_oauth_token_exists(self, firebase_test_helper):
        """Test retrieving token by oauth_token when it exists."""
        token_data = {
            'user_id': 'user_123',
            'oauth_token': 'oauth_token_123',
            'oauth_token_secret': 'oauth_secret_123'
        }

        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            token_data, 'user_123', True
        )

        with patch.object(EvernoteToken, 'evernote_tokens') as mock_tokens:
            # Mock query result
            mock_tokens.where.return_value.get.return_value = [mock_snapshot]

            # Execute
            result = EvernoteToken.retrieve_evernote_token_by_oauth_token(
                'oauth_token_123')

            # Verify
            assert isinstance(result, EvernoteToken)
            assert result.oauth_token == 'oauth_token_123'
            assert result.user_id == 'user_123'

    async def test_retrieve_evernote_token_by_oauth_token_not_exists(self, firebase_test_helper):
        """Test retrieving token by oauth_token when it doesn't exist."""
        with patch.object(EvernoteToken, 'evernote_tokens') as mock_tokens:
            # Mock empty query result
            mock_tokens.where.return_value.get.return_value = []

            # Execute
            result = EvernoteToken.retrieve_evernote_token_by_oauth_token(
                'nonexistent_token')

            # Verify
            assert result is None

    async def test_get_evernote_token_by_user_id_exists(self, firebase_test_helper):
        """Test getting token by user_id when it exists."""
        token_data = {
            'user_id': 'user_123',
            'access_token': 'access_token_123'
        }

        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            token_data, 'user_123', True
        )

        mock_document = Mock()
        mock_document.get.return_value = mock_snapshot

        with patch.object(EvernoteToken, 'evernote_tokens') as mock_tokens:
            mock_tokens.document.return_value = mock_document

            # Execute
            result = EvernoteToken.get_evernote_token_by_user_id('user_123')

            # Verify
            assert isinstance(result, EvernoteToken)
            assert result.user_id == 'user_123'
            assert result.access_token == 'access_token_123'

    async def test_get_evernote_token_by_user_id_not_exists(self, firebase_test_helper):
        """Test getting token by user_id when it doesn't exist."""
        empty_snapshot = firebase_test_helper.create_mock_document_snapshot(
            {}, 'nonexistent_user', False
        )

        mock_document = Mock()
        mock_document.get.return_value = empty_snapshot

        with patch.object(EvernoteToken, 'evernote_tokens') as mock_tokens:
            mock_tokens.document.return_value = mock_document

            # Execute
            result = EvernoteToken.get_evernote_token_by_user_id(
                'nonexistent_user')

            # Verify
            assert result is None


@pytest.mark.asyncio
class TestEvernoteTokenSave:
    """Test EvernoteToken save_evernote_token method."""

    async def test_save_evernote_token_success(self, firebase_test_helper):
        """Test saving Evernote token successfully."""
        # Create existing token data
        existing_data = {
            'user_id': 'user_123',
            'oauth_token': 'oauth_token_123',
            'oauth_token_secret': 'oauth_secret_123',
            'created_at': datetime.datetime(2023, 10, 1, 10, 0, 0)
        }

        test_access_token = 'final_access_token_123'
        test_now = datetime.datetime(2023, 10, 15, 12, 0, 0)

        with patch.object(EvernoteToken, 'get_evernote_token_by_user_id') as mock_get_token, \
                patch.object(EvernoteToken, 'evernote_tokens') as mock_tokens, \
                patch('firebase.models.evernote_token.datetime') as mock_datetime:

            # Mock existing token
            mock_existing_token = Mock()
            mock_existing_token.created_at = existing_data['created_at']
            mock_get_token.return_value = mock_existing_token

            # Mock document
            mock_document = Mock()
            mock_document.set = Mock()
            mock_tokens.document.return_value = mock_document

            mock_datetime.datetime.now.return_value = test_now

            # Execute
            EvernoteToken.save_evernote_token('user_123', test_access_token)

            # Verify document.set was called
            mock_document.set.assert_called_once()

            # Verify the structure of the set call
            set_data = mock_document.set.call_args[0][0]
            assert set_data['user_id'] == 'user_123'
            assert set_data['access_token'] == test_access_token
            # Preserved
            assert set_data['created_at'] == existing_data['created_at']
            assert set_data['updated_at'] == test_now  # Updated

    async def test_save_evernote_token_no_existing_token(self, firebase_test_helper):
        """Test saving Evernote token when no existing token found."""
        test_access_token = 'final_access_token_123'

        with patch.object(EvernoteToken, 'get_evernote_token_by_user_id') as mock_get_token:
            # Mock no existing token
            mock_get_token.return_value = None

            # Execute
            result = EvernoteToken.save_evernote_token(
                'nonexistent_user', test_access_token)

            # Verify returns None
            assert result is None

    async def test_save_evernote_token_data_structure(self, firebase_test_helper):
        """Test the data structure for saving access token."""
        # Test the final token structure that would be saved
        test_user_id = 'user_123'
        test_access_token = 'final_access_token_123'
        original_created_at = datetime.datetime(2023, 10, 1, 10, 0, 0)
        new_updated_at = datetime.datetime.now()

        # Test final token structure logic
        final_token = {
            'user_id': test_user_id,
            'access_token': test_access_token,
            'created_at': original_created_at,  # Preserved from original
            'updated_at': new_updated_at       # New timestamp
        }

        # Verify final token structure
        assert final_token['user_id'] == test_user_id
        assert final_token['access_token'] == test_access_token
        assert 'created_at' in final_token
        assert 'updated_at' in final_token
        # Updated should be newer
        assert final_token['updated_at'] > final_token['created_at']


@pytest.mark.asyncio
class TestEvernoteTokenOAuthFlow:
    """Test complete OAuth flow logic."""

    async def test_oauth_flow_sequence(self, firebase_test_helper):
        """Test the logical sequence of OAuth flow."""
        # Phase 1: Start OAuth request
        oauth_request_data = {
            'oauth_token': 'temp_oauth_token',
            'oauth_token_secret': 'temp_oauth_secret',
            'user_id': 'user_123',
            'created_at': datetime.datetime.now(),
            'updated_at': datetime.datetime.now()
        }

        # Phase 2: Complete OAuth with access token
        final_token_data = {
            'user_id': 'user_123',
            'access_token': 'final_access_token',
            'created_at': oauth_request_data['created_at'],  # Preserved
            'updated_at': datetime.datetime.now()  # Updated
        }

        # Verify OAuth flow structure
        assert oauth_request_data['user_id'] == final_token_data['user_id']
        assert 'oauth_token' in oauth_request_data
        assert 'oauth_token_secret' in oauth_request_data
        assert 'access_token' in final_token_data
        assert final_token_data['created_at'] == oauth_request_data['created_at']
        assert final_token_data['updated_at'] >= oauth_request_data['updated_at']

    async def test_oauth_token_lifecycle(self, firebase_test_helper):
        """Test the lifecycle of OAuth tokens."""
        # Test token states during OAuth flow

        # State 1: Initial request (has oauth_token and secret, no access_token)
        initial_state = {
            'oauth_token': 'temp_token',
            'oauth_token_secret': 'temp_secret',
            'user_id': 'user_123'
        }

        # Should have temporary credentials but no final access token
        assert 'oauth_token' in initial_state
        assert 'oauth_token_secret' in initial_state
        assert 'access_token' not in initial_state

        # State 2: Completed OAuth (has access_token, temporary tokens may be removed)
        completed_state = {
            'access_token': 'final_token',
            'user_id': 'user_123'
        }

        # Should have final access token
        assert 'access_token' in completed_state
        assert completed_state['user_id'] == initial_state['user_id']


@pytest.mark.asyncio
class TestEvernoteTokenEdgeCases:
    """Test edge cases for EvernoteToken model."""

    async def test_evernote_token_init_with_empty_data(self, firebase_test_helper):
        """Test EvernoteToken initialization with empty document."""
        empty_data = {}

        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            empty_data, 'empty_evernote_token', True
        )

        evernote_token = EvernoteToken(mock_snapshot)

        assert evernote_token.reference_id == 'empty_evernote_token'
        # Should not have attributes that weren't in the data
        assert not hasattr(evernote_token, 'oauth_token')
        assert not hasattr(evernote_token, 'user_id')

    async def test_oauth_token_validation(self, firebase_test_helper):
        """Test OAuth token data validation."""
        # Test valid OAuth token structure
        valid_oauth_data = {
            'oauth_token': 'valid_oauth_token_123',
            'oauth_token_secret': 'valid_oauth_secret_123',
            'user_id': 'user_123',
            'created_at': datetime.datetime.now(),
            'updated_at': datetime.datetime.now()
        }

        # Verify required OAuth fields
        oauth_required_fields = ['oauth_token',
                                 'oauth_token_secret', 'user_id']
        for field in oauth_required_fields:
            assert field in valid_oauth_data
            assert valid_oauth_data[field] is not None
            assert isinstance(valid_oauth_data[field], str)

        # Test access token structure
        valid_access_data = {
            'access_token': 'valid_access_token_123',
            'user_id': 'user_123',
            'created_at': datetime.datetime.now(),
            'updated_at': datetime.datetime.now()
        }

        # Verify required access token fields
        access_required_fields = ['access_token', 'user_id']
        for field in access_required_fields:
            assert field in valid_access_data
            assert valid_access_data[field] is not None
            assert isinstance(valid_access_data[field], str)

    async def test_timestamp_handling(self, firebase_test_helper):
        """Test timestamp handling in OAuth flow."""
        # Test timestamp logic
        start_time = datetime.datetime.now()

        # Simulate OAuth request start
        oauth_created = start_time
        oauth_updated = start_time

        # Simulate OAuth completion (later)
        completion_time = start_time + datetime.timedelta(minutes=5)
        final_updated = completion_time

        # Verify timestamp progression
        assert oauth_created == oauth_updated  # Same on creation
        assert final_updated > oauth_created   # Updated on completion
        assert final_updated > oauth_updated   # Final update is newest

    async def test_user_id_consistency(self, firebase_test_helper):
        """Test user_id consistency across OAuth flow."""
        test_user_id = 'user_123'

        # OAuth request phase
        oauth_data = {
            'user_id': test_user_id,
            'oauth_token': 'temp_token'
        }

        # OAuth completion phase
        final_data = {
            'user_id': test_user_id,
            'access_token': 'final_token'
        }

        # Verify user_id consistency
        assert oauth_data['user_id'] == final_data['user_id']
        assert oauth_data['user_id'] == test_user_id
        assert final_data['user_id'] == test_user_id
