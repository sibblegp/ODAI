"""
Base test infrastructure for Firebase models.

Provides common fixtures, mocks, and utilities for testing all Firebase model classes.
Handles mocking of Firebase dependencies that would otherwise fail in test environments.
"""

import pytest
import datetime
import json
import base64
import uuid
import sys
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Any, Dict, List, Optional


# Global mock objects that will be used across tests
MOCK_FIREBASE_ADMIN = None
MOCK_FIRESTORE = None
MOCK_OPENAI = None
MOCK_SETTINGS = None
MOCK_KEYS = None


def create_mock_firebase_admin():
    """Create mock firebase_admin module."""
    mock_admin = Mock()

    # Mock firebase_admin functions
    mock_admin.initialize_app = Mock()

    # Mock credentials
    mock_admin.credentials = Mock()
    mock_admin.credentials.Certificate = Mock(return_value="mock_credential")

    # Mock firestore
    mock_admin.firestore = Mock()
    mock_client = Mock()
    mock_admin.firestore.client = Mock(return_value=mock_client)

    # Mock messaging
    mock_admin.messaging = Mock()

    return mock_admin


def create_mock_firestore_client():
    """Create a comprehensive mock Firestore client."""
    mock_client = Mock()

    def create_mock_collection(name):
        mock_collection = Mock()
        mock_collection.name = name

        def create_mock_document(doc_id=None):
            mock_document = Mock()
            mock_document.id = doc_id or "test_doc_123"

            # Mock document snapshot
            mock_snapshot = Mock()
            mock_snapshot.exists = True
            mock_snapshot.reference = Mock()
            mock_snapshot.reference.id = doc_id or "test_doc_123"
            mock_snapshot.to_dict = Mock(return_value={})

            mock_document.get = Mock(return_value=mock_snapshot)
            mock_document.set = Mock()
            mock_document.update = Mock()

            return mock_document

        def create_mock_query(**kwargs):
            mock_query = Mock()
            mock_query.where = Mock(return_value=mock_query)
            mock_query.get = Mock(return_value=[])
            return mock_query

        mock_collection.document = create_mock_document
        mock_collection.where = create_mock_query

        return mock_collection

    mock_client.collection = create_mock_collection
    return mock_client


def create_mock_openai():
    """Create a mock OpenAI client."""
    mock_openai = Mock()

    # Mock chat completions
    mock_completion = Mock()
    mock_completion.choices = [Mock()]
    mock_completion.choices[0].message = Mock()
    mock_completion.choices[0].message.content = "Mock Generated Title"

    mock_openai.chat = Mock()
    mock_openai.chat.completions = Mock()
    mock_openai.chat.completions.create = Mock(return_value=mock_completion)

    return mock_openai


def create_mock_settings():
    """Create mock settings."""
    mock_settings = Mock()
    mock_settings.production = False
    mock_settings.local = True
    mock_settings.project_id = "test-project-123"
    mock_settings.key_ring_id = "test-key-ring"
    mock_settings.openai_api_key = "test-openai-key"
    return mock_settings


def create_mock_keys():
    """Create mock keys utility."""
    mock_keys = Mock()

    # Mock key management
    mock_keys.create_key_hsm = Mock(return_value="mock_key_123")

    # Mock encryption
    mock_encrypt_response = Mock()
    mock_encrypt_response.ciphertext = b"mock_encrypted_data"
    mock_keys.encrypt_symmetric = Mock(return_value=mock_encrypt_response)

    # Mock decryption
    mock_decrypt_response = Mock()
    mock_decrypt_response.plaintext = Mock()
    mock_decrypt_response.plaintext.decode = Mock(
        return_value="mock_decrypted_data")
    mock_keys.decrypt_symmetric = Mock(return_value=mock_decrypt_response)

    return mock_keys


def create_mock_segment_tracking():
    """Create mock segment tracking functions."""
    return {
        'track_google_connected': Mock(),
        'track_plaid_connected': Mock(),
        'track_evernote_connected': Mock()
    }


@pytest.fixture(scope="session", autouse=True)
def setup_firebase_mocks():
    """Setup comprehensive Firebase mocking for all tests."""
    global MOCK_FIREBASE_ADMIN, MOCK_FIRESTORE, MOCK_OPENAI, MOCK_SETTINGS, MOCK_KEYS

    # Create all mock objects
    MOCK_FIREBASE_ADMIN = create_mock_firebase_admin()
    MOCK_FIRESTORE = create_mock_firestore_client()
    MOCK_OPENAI = create_mock_openai()
    MOCK_SETTINGS = create_mock_settings()
    MOCK_KEYS = create_mock_keys()
    MOCK_SEGMENT = create_mock_segment_tracking()

    # Mock all Firebase-related modules before they get imported
    with patch.dict('sys.modules', {
        'firebase_admin': MOCK_FIREBASE_ADMIN,
        'firebase_admin.credentials': MOCK_FIREBASE_ADMIN.credentials,
        'firebase_admin.firestore': MOCK_FIREBASE_ADMIN.firestore,
        'firebase_admin.messaging': MOCK_FIREBASE_ADMIN.messaging,
        'google.oauth2.service_account': Mock(),
        'openai': Mock(OpenAI=lambda **kwargs: MOCK_OPENAI),
        'config': Mock(Settings=lambda: MOCK_SETTINGS),
        'connectors.utils.keys': MOCK_KEYS,
        'connectors.utils.secrets': Mock(access_secret_version=Mock(return_value=None)),
        'agents.realtime.agent': Mock(RealtimeAgent=Mock),
    }):

        # Mock the base Firebase objects
        with patch('firebase.base.DB', MOCK_FIRESTORE), \
                patch('firebase.base.client', MOCK_OPENAI), \
                patch('firebase.base.SETTINGS', MOCK_SETTINGS), \
                patch('firebase.base.keys', MOCK_KEYS), \
                patch('firebase.base.track_google_connected', MOCK_SEGMENT['track_google_connected']), \
                patch('firebase.base.track_plaid_connected', MOCK_SEGMENT['track_plaid_connected']), \
                patch('firebase.base.track_evernote_connected', MOCK_SEGMENT['track_evernote_connected']):

            yield {
                'firebase_admin': MOCK_FIREBASE_ADMIN,
                'firestore': MOCK_FIRESTORE,
                'openai': MOCK_OPENAI,
                'settings': MOCK_SETTINGS,
                'keys': MOCK_KEYS,
                'segment': MOCK_SEGMENT
            }


# Module-level fixtures for Firebase testing
@pytest.fixture
def mock_firestore_document():
    """Create a mock Firestore document."""
    mock_doc = Mock()
    mock_doc.reference = Mock()
    mock_doc.reference.id = "test_doc_123"
    mock_doc.exists = True
    mock_doc.to_dict = Mock(return_value={
        'name': 'Test User',
        'email': 'test@example.com',
        'created_at': datetime.datetime.now(),
        'integrations': {'google': True, 'plaid': False}
    })
    return mock_doc


@pytest.fixture
def mock_firestore_collection():
    """Create a mock Firestore collection."""
    mock_collection = Mock()
    mock_collection.document = Mock()
    mock_collection.where = Mock()
    return mock_collection


@pytest.fixture
def mock_firestore_db():
    """Get the global mock Firestore database client."""
    return MOCK_FIRESTORE


@pytest.fixture
def mock_firebase_settings():
    """Get the global mock Firebase settings."""
    return MOCK_SETTINGS


@pytest.fixture
def mock_openai_client():
    """Get the global mock OpenAI client."""
    return MOCK_OPENAI


@pytest.fixture
def mock_keys_utility():
    """Get the global mock keys utility."""
    return MOCK_KEYS


@pytest.fixture
def mock_segment_tracking():
    """Get the global mock segment tracking functions."""
    return create_mock_segment_tracking()


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        'name': 'John Doe',
        'email': 'john.doe@example.com',
        'integrations': {'google': True, 'plaid': False, 'evernote': False},
        'creationRecorded': True,
        'signupRecorded': True,
        'is_registered': True,
        'key_id': 'user_key_123'
    }


@pytest.fixture
def sample_chat_data():
    """Sample chat data for testing."""
    return {
        'original_ip': '192.168.1.1',
        'expires_at': datetime.datetime.now() + datetime.timedelta(days=5),
        'user_id': 'user_123',
        'deleted': False,
        'created_at': datetime.datetime.now(),
        'updated_at': datetime.datetime.now(),
        'messages': [
            {'content': 'System message', 'role': 'system'},
            {'content': 'Hello', 'role': 'user'},
            {'content': 'Hi there!', 'role': 'assistant'}
        ],
        'responses': [
            {'type': 'user_prompt', 'prompt': 'Hello'},
            {'type': 'assistant_response', 'content': 'Hi there!'}
        ],
        'display_in_search': True,
        'title': 'Test Chat',
        'last_message_id': 'msg_123',
        'chat_token_usage': {
            'input_tokens': 10,
            'cached_input_tokens': 2,
            'output_tokens': 15,
            'total_tokens': 27
        }
    }


@pytest.fixture
def sample_google_token_data():
    """Sample Google token data for testing."""
    return {
        'user_id': 'user_123',
        'state': 'oauth_state_123',
        'created_at': datetime.datetime.now(),
        'redirect_uri': 'https://example.com/callback',
        'accounts': {
            'test@gmail.com': {
                'email': 'test@gmail.com',
                'name': 'Test User',
                'picture': 'https://example.com/avatar.jpg',
                'created_at': datetime.datetime.now(),
                'token': base64.b64encode(json.dumps({
                    'access_token': 'test_access_token',
                    'refresh_token': 'test_refresh_token'
                }).encode()).decode(),
                'default': True
            }
        }
    }


@pytest.fixture
def sample_plaid_token_data():
    """Sample Plaid token data for testing."""
    return {
        'user_id': 'user_123',
        'created_at': datetime.datetime.now(),
        'redirect_uri': 'https://example.com/plaid-callback',
        'tokens': [
            {
                'valid': True,
                'created_at': datetime.datetime.now(),
                'auth_token': base64.b64encode('test_auth_token'.encode()).decode(),
                'item_id': base64.b64encode('test_item_id'.encode()).decode(),
                'account_names_and_numbers': [
                    {'name': 'Checking Account', 'mask': '1234'},
                    {'name': 'Savings Account', 'mask': '5678'}
                ]
            }
        ]
    }


@pytest.fixture
def sample_token_usage_data():
    """Sample token usage data for testing."""
    current_year = datetime.datetime.now().strftime("%Y")
    current_month = datetime.datetime.now().strftime("%m")
    current_day = datetime.datetime.now().strftime("%d")

    return {
        'usage': {
            current_year: {
                'usage': {
                    'input_tokens': 100,
                    'output_tokens': 150,
                    'cached_input_tokens': 20,
                    'total_cost': 0.5
                },
                current_month: {
                    'usage': {
                        'input_tokens': 50,
                        'output_tokens': 75,
                        'cached_input_tokens': 10,
                        'total_cost': 0.25
                    },
                    current_day: {
                        'input_tokens': 25,
                        'output_tokens': 35,
                        'cached_input_tokens': 5,
                        'total_cost': 0.12
                    }
                }
            }
        },
        'total_usage': {
            'input_tokens': 1000,
            'output_tokens': 1500,
            'cached_input_tokens': 200,
            'total_cost': 5.0
        }
    }


class FirebaseModelTestHelper:
    """Helper class for Firebase model testing."""

    @staticmethod
    def create_mock_document_snapshot(data: Dict[str, Any], doc_id: str = "test_doc_123", exists: bool = True):
        """Create a mock Firestore document snapshot."""
        mock_doc = Mock()
        mock_doc.exists = exists
        mock_doc.to_dict = Mock(return_value=data)
        mock_doc.reference = Mock()
        mock_doc.reference.id = doc_id
        return mock_doc

    @staticmethod
    def create_mock_query_result(results: List[Dict[str, Any]]):
        """Create a mock Firestore query result."""
        mock_results = []
        for i, data in enumerate(results):
            mock_doc = FirebaseModelTestHelper.create_mock_document_snapshot(
                data, f"doc_{i}", True
            )
            mock_results.append(mock_doc)
        return mock_results

    @staticmethod
    def setup_firestore_mocks(mock_db, collection_name: str, document_data: Dict[str, Any], doc_id: str = "test_doc"):
        """Setup comprehensive Firestore mocks for a collection."""
        mock_collection = Mock()
        mock_document = Mock()
        mock_doc_snapshot = FirebaseModelTestHelper.create_mock_document_snapshot(
            document_data, doc_id)

        # Setup collection mock
        mock_db.collection.return_value = mock_collection

        # Setup document mock
        mock_collection.document.return_value = mock_document
        mock_document.get.return_value = mock_doc_snapshot
        mock_document.set = Mock()
        mock_document.update = Mock()

        # Setup query mock
        mock_collection.where.return_value = Mock()
        mock_collection.where.return_value.where.return_value = Mock()
        mock_collection.where.return_value.where.return_value.get.return_value = [
            mock_doc_snapshot]
        mock_collection.where.return_value.get.return_value = [
            mock_doc_snapshot]

        return mock_collection, mock_document, mock_doc_snapshot


@pytest.fixture
def firebase_test_helper():
    """Provide the FirebaseModelTestHelper class."""
    return FirebaseModelTestHelper


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__])
