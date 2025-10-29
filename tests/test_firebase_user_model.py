"""
Comprehensive unit tests for Firebase User model.

Tests cover all User model methods including:
- User initialization and attribute setting
- User retrieval by ID
- Key generation and management
- Integration tracking (Google, Plaid, Evernote)
- Creation and signup recording
- Edge cases and error scenarios
"""

import pytest
import datetime
import uuid
from unittest.mock import Mock, patch, AsyncMock
from firebase.models.user import User
from tests.test_firebase_models_base import FirebaseModelTestHelper


class TestUserModelInit:
    """Test User model initialization and basic functionality."""

    def test_user_init_with_media_object(self, sample_user_data, firebase_test_helper):
        """Test User initialization with media object."""
        # Create mock media object
        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            sample_user_data, "user_123"
        )

        with patch.object(User, 'check_has_key_and_generate_if_not') as mock_key_check:
            # Execute
            user = User(mock_media_object)

            # Verify basic attributes
            assert user.reference_id == "user_123"
            assert user.name == "John Doe"
            assert user.email == "john.doe@example.com"
            assert user.integrations == {
                'google': True, 'plaid': False, 'evernote': False}
            assert user.is_registered is True
            assert user.key_id == "user_key_123"

            # Verify key check was called
            mock_key_check.assert_called_once()

    def test_user_init_with_minimal_data(self, firebase_test_helper):
        """Test User initialization with minimal data."""
        minimal_data = {
            'name': 'Jane Doe',
            'email': 'jane@example.com'
        }

        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            minimal_data, "user_456"
        )

        with patch.object(User, 'check_has_key_and_generate_if_not'):
            user = User(mock_media_object)

            assert user.reference_id == "user_456"
            assert user.name == "Jane Doe"
            assert user.email == "jane@example.com"
            assert not hasattr(
                user, 'integrations') or user.integrations is None


class TestUserClassMethods:
    """Test User class methods."""

    def test_get_user_by_id_existing(self, sample_user_data, firebase_test_helper):
        """Test retrieving existing user by ID."""
        # Create mock document snapshot
        mock_doc_snapshot = firebase_test_helper.create_mock_document_snapshot(
            sample_user_data, 'user_123', True
        )

        # Mock the Firestore collection and document calls
        mock_document = Mock()
        mock_document.get.return_value = mock_doc_snapshot

        with patch.object(User, 'users') as mock_users, \
                patch.object(User, 'check_has_key_and_generate_if_not'):

            mock_users.document.return_value = mock_document

            # Execute
            user = User.get_user_by_id('user_123')

            # Verify
            assert user is not None
            assert user.reference_id == 'user_123'
            assert user.name == 'John Doe'
            assert user.email == 'john.doe@example.com'

            # Verify Firestore calls
            mock_users.document.assert_called_once_with('user_123')
            mock_document.get.assert_called_once()

    def test_get_user_by_id_not_exists(self, mock_firestore_db):
        """Test retrieving non-existent user by ID."""
        mock_collection = Mock()
        mock_document = Mock()
        mock_snapshot = Mock()
        mock_snapshot.exists = False

        mock_firestore_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_document
        mock_document.get.return_value = mock_snapshot

        # Execute
        user = User.get_user_by_id('nonexistent_user')

        # Verify
        assert user is None


class TestUserKeyManagement:
    """Test User key generation and management."""

    def test_check_has_key_and_generate_if_not_local_environment(self, sample_user_data, firebase_test_helper, mock_firebase_settings):
        """Test key generation check in local environment (should skip)."""
        mock_firebase_settings.local = True

        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            sample_user_data)

        with patch('firebase.models.user.SETTINGS', mock_firebase_settings):
            user = User(mock_media_object)

            # In local environment, should not generate keys
            # No assertions needed as it should just return

    def test_check_has_key_and_generate_if_not_registered_user_without_key(self, firebase_test_helper, mock_firebase_settings, mock_keys_utility):
        """Test key generation for registered user without key."""
        mock_firebase_settings.local = False

        user_data_without_key = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'is_registered': True
        }

        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data_without_key, "user_123"
        )

        # Mock the document update
        mock_document = Mock()
        mock_document.update = Mock()

        # Reset the mock's call count since it's globally shared
        mock_keys_utility.create_key_hsm.reset_mock()

        with patch('firebase.models.user.SETTINGS', mock_firebase_settings), \
                patch('firebase.models.user.keys', mock_keys_utility), \
                patch.object(User, 'users') as mock_users:

            mock_users.document.return_value = mock_document

            # Execute
            user = User(mock_media_object)

            # Verify key was generated and stored
            mock_keys_utility.create_key_hsm.assert_called_once()
            mock_document.update.assert_called_once()

            # Check that key_id was set
            assert hasattr(user, 'key_id')

    def test_check_has_key_and_generate_if_not_unregistered_user(self, firebase_test_helper, mock_firebase_settings):
        """Test key generation skipped for unregistered user."""
        mock_firebase_settings.local = False

        user_data_unregistered = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'is_registered': False
        }

        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data_unregistered)

        with patch('firebase.models.user.SETTINGS', mock_firebase_settings):
            user = User(mock_media_object)

            # Should not have key_id for unregistered user
            assert not hasattr(user, 'key_id') or user.key_id is None

    def test_check_has_key_and_generate_if_not_user_with_existing_key(self, sample_user_data, firebase_test_helper, mock_firebase_settings):
        """Test key generation skipped for user with existing key."""
        # Create fresh mock for keys to avoid interference
        mock_keys = Mock()
        mock_keys.create_key_hsm = Mock(return_value="new_key_123")

        mock_firebase_settings.local = False

        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            sample_user_data)

        with patch('firebase.models.user.SETTINGS', mock_firebase_settings), \
                patch('firebase.models.user.keys', mock_keys):

            user = User(mock_media_object)

            # Should not generate new key since user already has one
            mock_keys.create_key_hsm.assert_not_called()
            assert user.key_id == "user_key_123"


class TestUserRecording:
    """Test User creation and signup recording."""

    def test_record_creation(self, sample_user_data, firebase_test_helper):
        """Test recording user creation."""
        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            sample_user_data)
        mock_document = Mock()
        mock_document.update = Mock()

        with patch.object(User, 'check_has_key_and_generate_if_not'), \
                patch.object(User, 'users') as mock_users:

            mock_users.document.return_value = mock_document

            user = User(mock_media_object)

            # Execute
            result = user.record_creation()

            # Verify
            mock_document.update.assert_called_once_with({
                'creationRecorded': True,
                'signupRecorded': False
            })

            assert result.creationRecorded is True
            assert result.signupRecorded is False
            assert result == user  # Should return self

    def test_record_signup(self, sample_user_data, firebase_test_helper):
        """Test recording user signup."""
        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            sample_user_data)
        mock_document = Mock()
        mock_document.update = Mock()

        with patch.object(User, 'check_has_key_and_generate_if_not'), \
                patch.object(User, 'users') as mock_users:

            mock_users.document.return_value = mock_document

            user = User(mock_media_object)

            # Execute
            result = user.record_signup()

            # Verify
            mock_document.update.assert_called_once_with({
                'signupRecorded': True
            })

            assert result.signupRecorded is True
            assert result == user  # Should return self


class TestUserGoogleIntegration:
    """Test User Google integration methods."""

    def test_set_connected_to_google_new_integrations(self, firebase_test_helper, mock_segment_tracking):
        """Test setting Google connection for user without existing integrations."""
        user_data = {
            'name': 'John Doe',
            'email': 'john@example.com'
        }

        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data, "user_123")
        mock_document = Mock()
        mock_document.update = Mock()

        with patch.object(User, 'check_has_key_and_generate_if_not'), \
                patch.object(User, 'users') as mock_users, \
                patch('firebase.models.user.track_google_connected', mock_segment_tracking['track_google_connected']):

            mock_users.document.return_value = mock_document

            user = User(mock_media_object)

            # Execute
            result = user.set_connected_to_google()

            # Verify
            expected_integrations = {'google': True}
            mock_document.update.assert_called_once_with({
                'integrations': expected_integrations
            })

            assert user.integrations == expected_integrations
            mock_segment_tracking['track_google_connected'].assert_called_once_with(
                user)
            assert result == user

    def test_set_connected_to_google_existing_integrations(self, sample_user_data, firebase_test_helper, mock_segment_tracking):
        """Test setting Google connection for user with existing integrations."""
        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            sample_user_data, "user_123")
        mock_document = Mock()
        mock_document.update = Mock()

        with patch.object(User, 'check_has_key_and_generate_if_not'), \
                patch.object(User, 'users') as mock_users, \
                patch('firebase.models.user.track_google_connected', mock_segment_tracking['track_google_connected']):

            mock_users.document.return_value = mock_document

            user = User(mock_media_object)

            # Execute
            result = user.set_connected_to_google()

            # Verify integrations were updated
            expected_integrations = {'google': True,
                                     'plaid': False, 'evernote': False}
            mock_document.update.assert_called_once_with({
                'integrations': expected_integrations
            })

            assert user.integrations == expected_integrations
            mock_segment_tracking['track_google_connected'].assert_called_once_with(
                user)

    def test_check_has_google_account_true(self, sample_user_data, firebase_test_helper):
        """Test checking Google account when user has Google integration."""
        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            sample_user_data)

        with patch.object(User, 'check_has_key_and_generate_if_not'):
            user = User(mock_media_object)

            # Execute
            result = user.check_has_google_account()

            # Verify
            assert result is True

    def test_check_has_google_account_false(self, firebase_test_helper):
        """Test checking Google account when user doesn't have Google integration."""
        user_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'integrations': {'plaid': True, 'evernote': False}
        }

        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data)

        with patch.object(User, 'check_has_key_and_generate_if_not'):
            user = User(mock_media_object)

            # Execute
            result = user.check_has_google_account()

            # Verify
            assert result is False

    def test_check_has_google_account_no_integrations(self, firebase_test_helper):
        """Test checking Google account when user has no integrations."""
        user_data = {
            'name': 'John Doe',
            'email': 'john@example.com'
        }

        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data)

        with patch.object(User, 'check_has_key_and_generate_if_not'):
            user = User(mock_media_object)

            # Execute
            result = user.check_has_google_account()

            # Verify
            assert result is False

    def test_disconnect_from_google_with_integration(self, firebase_test_helper):
        """Test disconnecting from Google when user has Google integration."""
        user_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'integrations': {'google': True, 'plaid': False, 'evernote': False}
        }

        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data, "user_123")
        mock_document = Mock()
        mock_document.update = Mock()

        with patch.object(User, 'check_has_key_and_generate_if_not'), \
                patch.object(User, 'users') as mock_users:

            mock_users.document.return_value = mock_document

            user = User(mock_media_object)

            # Execute
            result = user.disconnect_from_google()

            # Verify
            expected_integrations = {'google': False, 'plaid': False, 'evernote': False}
            mock_document.update.assert_called_once_with({
                'integrations': expected_integrations
            })

            assert user.integrations == expected_integrations
            assert result == user

    def test_disconnect_from_google_no_integration(self, firebase_test_helper):
        """Test disconnecting from Google when user has no Google integration."""
        user_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'integrations': {'plaid': True, 'evernote': False}
        }

        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data, "user_123")
        mock_document = Mock()
        mock_document.update = Mock()

        with patch.object(User, 'check_has_key_and_generate_if_not'), \
                patch.object(User, 'users') as mock_users:

            mock_users.document.return_value = mock_document

            user = User(mock_media_object)

            # Execute
            result = user.disconnect_from_google()

            # Verify - should not update integrations since Google wasn't connected
            mock_document.update.assert_not_called()
            assert user.integrations == {'plaid': True, 'evernote': False}
            assert result == user

    def test_disconnect_from_google_with_ready_for_google(self, firebase_test_helper):
        """Test disconnecting from Google also clears ready_for_google field."""
        user_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'integrations': {'google': True},
            'ready_for_google': 'some_auth_token'
        }

        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data, "user_123")
        mock_document = Mock()
        mock_document.update = Mock()

        with patch.object(User, 'check_has_key_and_generate_if_not'), \
                patch.object(User, 'users') as mock_users:

            mock_users.document.return_value = mock_document

            user = User(mock_media_object)

            # Execute
            result = user.disconnect_from_google()

            # Verify both updates were made
            assert mock_document.update.call_count == 2
            
            # Check the calls
            calls = mock_document.update.call_args_list
            assert calls[0][0][0] == {'integrations': {'google': False}}
            assert calls[1][0][0] == {'ready_for_google': None}

            assert user.integrations == {'google': False}
            assert user.ready_for_google is None
            assert result == user

    def test_disconnect_from_google_only_ready_for_google(self, firebase_test_helper):
        """Test disconnecting from Google when only ready_for_google exists."""
        user_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'ready_for_google': 'some_auth_token'
        }

        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data, "user_123")
        mock_document = Mock()
        mock_document.update = Mock()

        with patch.object(User, 'check_has_key_and_generate_if_not'), \
                patch.object(User, 'users') as mock_users:

            mock_users.document.return_value = mock_document

            user = User(mock_media_object)

            # Execute
            result = user.disconnect_from_google()

            # Verify only ready_for_google was updated
            mock_document.update.assert_called_once_with({
                'ready_for_google': None
            })

            assert user.ready_for_google is None
            assert result == user

    def test_disconnect_from_google_no_google_fields(self, firebase_test_helper):
        """Test disconnecting from Google when user has no Google-related fields."""
        user_data = {
            'name': 'John Doe',
            'email': 'john@example.com'
        }

        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data, "user_123")
        mock_document = Mock()
        mock_document.update = Mock()

        with patch.object(User, 'check_has_key_and_generate_if_not'), \
                patch.object(User, 'users') as mock_users:

            mock_users.document.return_value = mock_document

            user = User(mock_media_object)

            # Execute
            result = user.disconnect_from_google()

            # Verify no updates were made
            mock_document.update.assert_not_called()
            assert result == user


class TestUserPlaidIntegration:
    """Test User Plaid integration methods."""

    def test_set_connected_to_plaid(self, sample_user_data, firebase_test_helper, mock_segment_tracking):
        """Test setting Plaid connection."""
        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            sample_user_data, "user_123")
        mock_document = Mock()
        mock_document.update = Mock()

        with patch.object(User, 'check_has_key_and_generate_if_not'), \
                patch.object(User, 'users') as mock_users, \
                patch('firebase.models.user.track_plaid_connected', mock_segment_tracking['track_plaid_connected']):

            mock_users.document.return_value = mock_document

            user = User(mock_media_object)

            # Execute
            result = user.set_connected_to_plaid()

            # Verify
            expected_integrations = {'google': True,
                                     'plaid': True, 'evernote': False}
            mock_document.update.assert_called_once_with({
                'integrations': expected_integrations
            })

            assert user.integrations == expected_integrations
            mock_segment_tracking['track_plaid_connected'].assert_called_once_with(
                user)
            assert result == user

    def test_check_has_plaid_account_true(self, firebase_test_helper):
        """Test checking Plaid account when user has Plaid integration."""
        user_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'integrations': {'google': False, 'plaid': True, 'evernote': False}
        }

        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data)

        with patch.object(User, 'check_has_key_and_generate_if_not'):
            user = User(mock_media_object)

            # Execute
            result = user.check_has_plaid_account()

            # Verify
            assert result is True

    def test_check_has_plaid_account_false(self, sample_user_data, firebase_test_helper):
        """Test checking Plaid account when user doesn't have Plaid integration."""
        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            sample_user_data)

        with patch.object(User, 'check_has_key_and_generate_if_not'):
            user = User(mock_media_object)

            # Execute
            result = user.check_has_plaid_account()

            # Verify
            assert result is False

    def test_disconnect_from_plaid_with_integration(self, firebase_test_helper):
        """Test disconnecting from Plaid when user has integration."""
        user_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'integrations': {'google': True, 'plaid': True, 'evernote': False}
        }

        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data, "user_123")
        mock_document = Mock()
        mock_document.update = Mock()

        with patch.object(User, 'check_has_key_and_generate_if_not'), \
             patch.object(User, 'users') as mock_users:
            mock_users.document.return_value = mock_document
            user = User(mock_media_object)

            # Execute
            result = user.disconnect_from_plaid()

            # Verify
            mock_document.update.assert_called_once_with({
                'integrations': {'google': True, 'plaid': False, 'evernote': False}
            })
            assert user.integrations['plaid'] is False
            assert result == user  # Check method chaining

    def test_disconnect_from_plaid_without_integration(self, firebase_test_helper):
        """Test disconnecting from Plaid when user doesn't have integration."""
        user_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'integrations': {'google': True, 'plaid': False, 'evernote': False}
        }

        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data, "user_123")
        mock_document = Mock()
        mock_document.update = Mock()

        with patch.object(User, 'check_has_key_and_generate_if_not'), \
             patch.object(User, 'users') as mock_users:
            mock_users.document.return_value = mock_document
            user = User(mock_media_object)

            # Execute
            result = user.disconnect_from_plaid()

            # Verify - no update should occur
            mock_document.update.assert_not_called()
            assert user.integrations['plaid'] is False
            assert result == user

    def test_disconnect_from_plaid_no_integrations(self, firebase_test_helper):
        """Test disconnecting from Plaid when user has no integrations attribute."""
        user_data = {
            'name': 'John Doe',
            'email': 'john@example.com'
            # No integrations key
        }

        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data, "user_123")
        mock_document = Mock()
        mock_document.update = Mock()

        with patch.object(User, 'check_has_key_and_generate_if_not'), \
             patch.object(User, 'users') as mock_users:
            mock_users.document.return_value = mock_document
            user = User(mock_media_object)

            # Execute
            result = user.disconnect_from_plaid()

            # Verify - no update should occur
            mock_document.update.assert_not_called()
            assert result == user

    def test_disconnect_from_plaid_none_integrations(self, firebase_test_helper):
        """Test disconnecting from Plaid when integrations is None."""
        user_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'integrations': None
        }

        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data, "user_123")
        mock_document = Mock()
        mock_document.update = Mock()

        with patch.object(User, 'check_has_key_and_generate_if_not'), \
             patch.object(User, 'users') as mock_users:
            mock_users.document.return_value = mock_document
            user = User(mock_media_object)

            # Execute
            result = user.disconnect_from_plaid()

            # Verify - no update should occur
            mock_document.update.assert_not_called()
            assert result == user


class TestUserEvernoteIntegration:
    """Test User Evernote integration methods."""

    def test_set_connected_to_evernote(self, sample_user_data, firebase_test_helper, mock_segment_tracking):
        """Test setting Evernote connection."""
        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            sample_user_data, "user_123")
        mock_document = Mock()
        mock_document.update = Mock()

        with patch.object(User, 'check_has_key_and_generate_if_not'), \
                patch.object(User, 'users') as mock_users, \
                patch('firebase.models.user.track_evernote_connected', mock_segment_tracking['track_evernote_connected']):

            mock_users.document.return_value = mock_document

            user = User(mock_media_object)

            # Execute
            result = user.set_connected_to_evernote()

            # Verify
            expected_integrations = {'google': True,
                                     'plaid': False, 'evernote': True}
            mock_document.update.assert_called_once_with({
                'integrations': expected_integrations
            })

            assert user.integrations == expected_integrations
            mock_segment_tracking['track_evernote_connected'].assert_called_once_with(
                user)
            assert result == user

    def test_check_has_evernote_account_true(self, firebase_test_helper):
        """Test checking Evernote account when user has Evernote integration."""
        user_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'integrations': {'google': False, 'plaid': False, 'evernote': True}
        }

        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data)

        with patch.object(User, 'check_has_key_and_generate_if_not'):
            user = User(mock_media_object)

            # Execute
            result = user.check_has_evernote_account()

            # Verify
            assert result is True

    def test_check_has_evernote_account_false(self, sample_user_data, firebase_test_helper):
        """Test checking Evernote account when user doesn't have Evernote integration."""
        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            sample_user_data)

        with patch.object(User, 'check_has_key_and_generate_if_not'):
            user = User(mock_media_object)

            # Execute
            result = user.check_has_evernote_account()

            # Verify
            assert result is False


class TestUserEdgeCases:
    """Test edge cases and error scenarios."""

    def test_user_init_with_empty_data(self, firebase_test_helper):
        """Test User initialization with empty data."""
        empty_data = {}

        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            empty_data, "empty_user")

        with patch.object(User, 'check_has_key_and_generate_if_not'):
            user = User(mock_media_object)

            assert user.reference_id == "empty_user"
            # Should not have attributes that weren't in the data
            assert not hasattr(user, 'name')
            assert not hasattr(user, 'email')

    def test_integrations_with_none_value(self, firebase_test_helper):
        """Test user with None integrations value."""
        user_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'integrations': None
        }

        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data, "user_123")
        mock_document = Mock()
        mock_document.update = Mock()

        with patch.object(User, 'check_has_key_and_generate_if_not'), \
                patch.object(User, 'users') as mock_users, \
                patch('firebase.models.user.track_google_connected') as mock_track:

            mock_users.document.return_value = mock_document

            user = User(mock_media_object)

            # Execute
            user.set_connected_to_google()

            # Should create new integrations dict
            expected_integrations = {'google': True}
            assert user.integrations == expected_integrations

    def test_key_generation_with_uuid_generation(self, firebase_test_helper, mock_firebase_settings):
        """Test that key generation uses proper UUID generation."""
        # Create fresh mocks to avoid interference
        mock_keys = Mock()
        mock_keys.create_key_hsm = Mock(return_value="new_key_123")

        mock_firebase_settings.local = False

        user_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'is_registered': True
        }

        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data, "user_123")
        mock_document = Mock()
        mock_document.update = Mock()

        with patch('firebase.models.user.SETTINGS', mock_firebase_settings), \
                patch('firebase.models.user.keys', mock_keys), \
                patch('firebase.models.user.uuid.uuid4') as mock_uuid, \
                patch.object(User, 'users') as mock_users:

            mock_uuid.return_value = "test-uuid-string"
            mock_users.document.return_value = mock_document

            # Execute
            user = User(mock_media_object)

            # Verify UUID was generated and used
            mock_uuid.assert_called_once()
            mock_keys.create_key_hsm.assert_called_once_with(
                mock_firebase_settings.project_id, 'global', mock_firebase_settings.key_ring_id, 'test-uuid-string'
            )


class TestUserMetrics:
    """Test User metrics tracking methods."""

    def test_add_prompt_to_metrics_no_existing_metrics(self, firebase_test_helper):
        """Test adding prompt to user without existing metrics."""
        user_data = {
            'name': 'John Doe',
            'email': 'john@example.com'
        }
        
        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data, "user_123")
        mock_document = Mock()
        mock_document.update = Mock()
        
        with patch.object(User, 'check_has_key_and_generate_if_not'), \
                patch.object(User, 'users') as mock_users:
            
            mock_users.document.return_value = mock_document
            
            user = User(mock_media_object)
            
            # Execute
            result = user.add_prompt_to_metrics("What is the weather today?")
            
            # Verify
            assert user.metrics['prompt_count'] == 1
            assert len(user.metrics['prompts']) == 1
            assert user.metrics['prompts'][0]['prompt'] == "What is the weather today?"
            assert 'timestamp' in user.metrics['prompts'][0]
            
            # Verify update was called
            mock_document.update.assert_called_once()
            update_args = mock_document.update.call_args[0][0]
            assert update_args['metrics']['prompt_count'] == 1
            assert len(update_args['metrics']['prompts']) == 1
            assert update_args['metrics']['prompts'][0]['prompt'] == "What is the weather today?"
            
            assert result == user

    def test_add_prompt_to_metrics_existing_metrics(self, firebase_test_helper):
        """Test adding prompt to user with existing metrics."""
        user_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'metrics': {
                'prompts': ["Previous prompt"],
                'prompt_count': 1,
                'tool_calls': {'search': 2}
            }
        }
        
        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data, "user_123")
        mock_document = Mock()
        mock_document.update = Mock()
        
        with patch.object(User, 'check_has_key_and_generate_if_not'), \
                patch.object(User, 'users') as mock_users:
            
            mock_users.document.return_value = mock_document
            
            user = User(mock_media_object)
            
            # Execute
            result = user.add_prompt_to_metrics("New prompt")
            
            # Verify
            assert user.metrics['prompt_count'] == 2
            assert len(user.metrics['prompts']) == 2
            assert user.metrics['prompts'][0] == "Previous prompt"  # Original format preserved
            assert user.metrics['prompts'][1]['prompt'] == "New prompt"  # New format
            assert 'timestamp' in user.metrics['prompts'][1]
            assert user.metrics['tool_calls'] == {'search': 2}
            
            assert result == user

    def test_add_prompt_to_metrics_multiple_calls(self, firebase_test_helper):
        """Test adding multiple prompts in sequence."""
        user_data = {
            'name': 'John Doe',
            'email': 'john@example.com'
        }
        
        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data, "user_123")
        mock_document = Mock()
        mock_document.update = Mock()
        
        with patch.object(User, 'check_has_key_and_generate_if_not'), \
                patch.object(User, 'users') as mock_users:
            
            mock_users.document.return_value = mock_document
            
            user = User(mock_media_object)
            
            # Execute multiple calls
            user.add_prompt_to_metrics("First prompt")
            user.add_prompt_to_metrics("Second prompt")
            user.add_prompt_to_metrics("Third prompt")
            
            # Verify final state
            assert user.metrics['prompt_count'] == 3
            assert len(user.metrics['prompts']) == 3
            assert user.metrics['prompts'][0]['prompt'] == "First prompt"
            assert user.metrics['prompts'][1]['prompt'] == "Second prompt"
            assert user.metrics['prompts'][2]['prompt'] == "Third prompt"
            # All should have timestamps
            for prompt_obj in user.metrics['prompts']:
                assert 'timestamp' in prompt_obj
            assert mock_document.update.call_count == 3

    def test_add_tool_call_to_metrics_no_existing_metrics(self, firebase_test_helper):
        """Test adding tool call to user without existing metrics."""
        user_data = {
            'name': 'John Doe',
            'email': 'john@example.com'
        }
        
        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data, "user_123")
        mock_document = Mock()
        mock_document.update = Mock()
        
        with patch.object(User, 'check_has_key_and_generate_if_not'), \
                patch.object(User, 'users') as mock_users, \
                patch('builtins.print') as mock_print:
            
            mock_users.document.return_value = mock_document
            
            user = User(mock_media_object)
            
            # Execute
            result = user.add_tool_call_to_metrics("search_google")
            
            # Verify
            expected_metrics = {
                'tool_calls': {'search_google': 1},
                'tool_call_count': 1
            }
            mock_document.update.assert_called_once_with({
                'metrics': expected_metrics
            })
            
            assert user.metrics == expected_metrics
            assert result == user
            mock_print.assert_called_once_with("Adding tool call to metrics: search_google")

    def test_add_tool_call_to_metrics_existing_tool(self, firebase_test_helper):
        """Test incrementing existing tool call count."""
        user_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'metrics': {
                'tool_calls': {'search_google': 5, 'gmail_send': 2},
                'tool_call_count': 7
            }
        }
        
        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data, "user_123")
        mock_document = Mock()
        mock_document.update = Mock()
        
        with patch.object(User, 'check_has_key_and_generate_if_not'), \
                patch.object(User, 'users') as mock_users:
            
            mock_users.document.return_value = mock_document
            
            user = User(mock_media_object)
            
            # Execute
            result = user.add_tool_call_to_metrics("search_google")
            
            # Verify
            expected_metrics = {
                'tool_calls': {'search_google': 6, 'gmail_send': 2},
                'tool_call_count': 8
            }
            mock_document.update.assert_called_once_with({
                'metrics': expected_metrics
            })
            
            assert user.metrics == expected_metrics
            assert result == user

    def test_add_tool_call_to_metrics_new_tool(self, firebase_test_helper):
        """Test adding a new tool to existing metrics."""
        user_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'metrics': {
                'tool_calls': {'search_google': 3},
                'tool_call_count': 3
            }
        }
        
        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data, "user_123")
        mock_document = Mock()
        mock_document.update = Mock()
        
        with patch.object(User, 'check_has_key_and_generate_if_not'), \
                patch.object(User, 'users') as mock_users:
            
            mock_users.document.return_value = mock_document
            
            user = User(mock_media_object)
            
            # Execute
            result = user.add_tool_call_to_metrics("gmail_send")
            
            # Verify
            expected_metrics = {
                'tool_calls': {'search_google': 3, 'gmail_send': 1},
                'tool_call_count': 4
            }
            mock_document.update.assert_called_once_with({
                'metrics': expected_metrics
            })
            
            assert user.metrics == expected_metrics

    def test_add_agent_call_to_metrics_no_existing_metrics(self, firebase_test_helper):
        """Test adding agent call to user without existing metrics."""
        user_data = {
            'name': 'John Doe',
            'email': 'john@example.com'
        }
        
        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data, "user_123")
        mock_document = Mock()
        mock_document.update = Mock()
        
        with patch.object(User, 'check_has_key_and_generate_if_not'), \
                patch.object(User, 'users') as mock_users:
            
            mock_users.document.return_value = mock_document
            
            user = User(mock_media_object)
            
            # Execute
            result = user.add_agent_call_to_metrics("gmail_agent")
            
            # Verify
            expected_metrics = {
                'agent_calls': {'gmail_agent': 1},
                'agent_call_count': 1
            }
            mock_document.update.assert_called_once_with({
                'metrics': expected_metrics
            })
            
            assert user.metrics == expected_metrics
            assert result == user

    def test_add_agent_call_to_metrics_existing_agent(self, firebase_test_helper):
        """Test incrementing existing agent call count."""
        user_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'metrics': {
                'agent_calls': {'gmail_agent': 10, 'plaid_agent': 5},
                'agent_call_count': 15
            }
        }
        
        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data, "user_123")
        mock_document = Mock()
        mock_document.update = Mock()
        
        with patch.object(User, 'check_has_key_and_generate_if_not'), \
                patch.object(User, 'users') as mock_users:
            
            mock_users.document.return_value = mock_document
            
            user = User(mock_media_object)
            
            # Execute
            result = user.add_agent_call_to_metrics("gmail_agent")
            
            # Verify
            expected_metrics = {
                'agent_calls': {'gmail_agent': 11, 'plaid_agent': 5},
                'agent_call_count': 16
            }
            mock_document.update.assert_called_once_with({
                'metrics': expected_metrics
            })
            
            assert user.metrics == expected_metrics

    def test_metrics_persistence_across_methods(self, firebase_test_helper):
        """Test that metrics persist correctly across different method calls."""
        user_data = {
            'name': 'John Doe',
            'email': 'john@example.com'
        }
        
        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data, "user_123")
        mock_document = Mock()
        mock_document.update = Mock()
        
        with patch.object(User, 'check_has_key_and_generate_if_not'), \
                patch.object(User, 'users') as mock_users:
            
            mock_users.document.return_value = mock_document
            
            user = User(mock_media_object)
            
            # Execute different metric methods
            user.add_prompt_to_metrics("Test prompt")
            user.add_tool_call_to_metrics("search_google")
            user.add_agent_call_to_metrics("gmail_agent")
            
            # Verify combined metrics
            assert 'prompts' in user.metrics
            assert 'tool_calls' in user.metrics
            assert 'agent_calls' in user.metrics
            assert user.metrics['prompt_count'] == 1
            assert user.metrics['tool_call_count'] == 1
            assert user.metrics['agent_call_count'] == 1
            # Verify prompt structure
            assert len(user.metrics['prompts']) == 1
            assert user.metrics['prompts'][0]['prompt'] == "Test prompt"
            assert 'timestamp' in user.metrics['prompts'][0]

    def test_metrics_with_empty_strings(self, firebase_test_helper):
        """Test metrics methods with empty string inputs."""
        user_data = {
            'name': 'John Doe',
            'email': 'john@example.com'
        }
        
        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data, "user_123")
        mock_document = Mock()
        mock_document.update = Mock()
        
        with patch.object(User, 'check_has_key_and_generate_if_not'), \
                patch.object(User, 'users') as mock_users:
            
            mock_users.document.return_value = mock_document
            
            user = User(mock_media_object)
            
            # Execute with empty strings
            user.add_prompt_to_metrics("")
            user.add_tool_call_to_metrics("")
            user.add_agent_call_to_metrics("")
            
            # Verify they were still tracked
            assert len(user.metrics['prompts']) == 1
            assert user.metrics['prompts'][0]['prompt'] == ""
            assert 'timestamp' in user.metrics['prompts'][0]
            assert user.metrics['tool_calls'] == {"": 1}
            assert user.metrics['agent_calls'] == {"": 1}

    def test_metrics_with_special_characters(self, firebase_test_helper):
        """Test metrics methods with special characters in inputs."""
        user_data = {
            'name': 'John Doe',
            'email': 'john@example.com'
        }
        
        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data, "user_123")
        mock_document = Mock()
        mock_document.update = Mock()
        
        with patch.object(User, 'check_has_key_and_generate_if_not'), \
                patch.object(User, 'users') as mock_users:
            
            mock_users.document.return_value = mock_document
            
            user = User(mock_media_object)
            
            # Execute with special characters
            special_prompt = "What's the weather? 🌤️ & temperature in °C"
            special_tool = "tool_with_special-chars_v2.0"
            special_agent = "agent@special#1"
            
            user.add_prompt_to_metrics(special_prompt)
            user.add_tool_call_to_metrics(special_tool)
            user.add_agent_call_to_metrics(special_agent)
            
            # Verify they were tracked correctly
            assert user.metrics['prompts'][0]['prompt'] == special_prompt
            assert 'timestamp' in user.metrics['prompts'][0]
            assert special_tool in user.metrics['tool_calls']
            assert special_agent in user.metrics['agent_calls']

    def test_metrics_with_none_value(self, firebase_test_helper):
        """Test handling of None metrics attribute."""
        user_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'metrics': None
        }
        
        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            user_data, "user_123")
        mock_document = Mock()
        mock_document.update = Mock()
        
        with patch.object(User, 'check_has_key_and_generate_if_not'), \
                patch.object(User, 'users') as mock_users:
            
            mock_users.document.return_value = mock_document
            
            user = User(mock_media_object)
            
            # Verify metrics is None initially
            assert user.metrics is None
            
            # Execute - should create new metrics
            user.add_prompt_to_metrics("Test")
            
            # Verify new metrics were created
            assert user.metrics is not None
            assert len(user.metrics['prompts']) == 1
            assert user.metrics['prompts'][0]['prompt'] == "Test"
            assert 'timestamp' in user.metrics['prompts'][0]
            assert user.metrics['prompt_count'] == 1


if __name__ == "__main__":
    pytest.main([__file__])
