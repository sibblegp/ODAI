"""
Firebase Model Test Factories

This module provides factory methods for creating real Firebase model instances
for testing. These factories create actual model objects with real data structures
to ensure tests catch field name changes and structural modifications.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Optional, Dict, List, Any, TYPE_CHECKING
from unittest.mock import Mock

if TYPE_CHECKING:
    from firebase.models.plaid_token import PlaidToken
    from firebase.models.google_token import GoogleToken
    from firebase.models.evernote_token import EvernoteToken
    from firebase.models.user import User
    from firebase.models.chat import Chat
    from firebase.models.token_usage import TokenUsage


class MockDocumentSnapshot:
    """
    A mock Firestore document snapshot that preserves real data structure.
    This is minimal mocking - only the Firestore interface, not the data.
    """
    def __init__(self, data: dict, doc_id: str, exists: bool = True):
        self._data = data
        self.id = doc_id
        self.exists = exists
        self.reference = Mock()
        self.reference.id = doc_id
        
    def to_dict(self) -> dict:
        """Return the actual data dictionary."""
        return self._data
        
    def get(self, field: str) -> Any:
        """Get a specific field from the document."""
        return self._data.get(field)


class FirebaseModelFactory:
    """Factory for creating real Firebase model instances for testing."""
    
    @staticmethod
    def create_plaid_token(
        user_id: str = "test_user_123",
        with_accounts: bool = True,
        valid: bool = True
    ) -> PlaidToken:
        """
        Create actual PlaidToken instance with real structure.
        This uses the ACTUAL field names and structure from production.
        """
        from firebase.models.plaid_token import PlaidToken
        
        tokens = []
        if with_accounts:
            tokens = [{
                'valid': valid,
                'created_at': datetime.datetime.now(),
                'auth_token': 'encrypted_auth_token_test',
                'item_id': 'encrypted_item_id_test',
                # CRITICAL: Using actual field name 'account_names_and_numbers'
                'account_names_and_numbers': [
                    {'name': 'Test Checking Account', 'mask': '1234'},
                    {'name': 'Test Savings Account', 'mask': '5678'}
                ],
                'bank_name': 'Test Bank',
                'id': str(uuid.uuid4())
            }]
        
        data = {
            'user_id': user_id,
            'created_at': datetime.datetime.now(),
            'redirect_uri': 'https://app.example.com/plaid/callback',
            'tokens': tokens
        }
        
        mock_snapshot = MockDocumentSnapshot(data, user_id)
        return PlaidToken(mock_snapshot)
    
    @staticmethod
    def create_google_token(
        user_id: str = "test_user_123",
        has_token: bool = True,
        valid: bool = True
    ) -> GoogleToken:
        """Create actual GoogleToken instance with real structure."""
        from firebase.models.google_token import GoogleToken
        
        data = {
            'user_id': user_id,
            'created_at': datetime.datetime.now()
        }
        
        if has_token:
            data.update({
                'valid': valid,
                'access_token': 'encrypted_access_token_test',
                'refresh_token': 'encrypted_refresh_token_test',
                'token_expiry': (datetime.datetime.now() + datetime.timedelta(hours=1)).isoformat(),
                'email': 'test@example.com',
                'name': 'Test User',
                'picture': 'https://example.com/picture.jpg',
                'scopes': [
                    'https://www.googleapis.com/auth/gmail.send',
                    'https://www.googleapis.com/auth/calendar'
                ]
            })
        
        mock_snapshot = MockDocumentSnapshot(data, user_id)
        return GoogleToken(mock_snapshot)
    
    @staticmethod
    def create_evernote_token(
        user_id: str = "test_user_123",
        has_token: bool = True
    ) -> EvernoteToken:
        """Create actual EvernoteToken instance with real structure."""
        from firebase.models.evernote_token import EvernoteToken
        
        data = {
            'user_id': user_id,
            'created_at': datetime.datetime.now()
        }
        
        if has_token:
            data.update({
                'access_token': 'encrypted_evernote_token_test',
                'note_store_url': 'https://sandbox.evernote.com/shard/s1/notestore',
                'web_api_url_prefix': 'https://sandbox.evernote.com/shard/s1/',
                'expires_at': datetime.datetime.now() + datetime.timedelta(days=365)
            })
        
        mock_snapshot = MockDocumentSnapshot(data, user_id)
        return EvernoteToken(mock_snapshot)
    
    @staticmethod
    def create_user(
        user_id: str = "test_user_123",
        email: Optional[str] = "test@example.com",
        name: Optional[str] = "Test User",
        is_registered: bool = True,
        integrations: Optional[Dict[str, bool]] = None
    ) -> User:
        """Create actual User instance with real structure."""
        from firebase.models.user import User
        
        if integrations is None:
            integrations = {}
        
        data = {
            'reference_id': user_id,
            'createdAt': datetime.datetime.now(),
            'is_registered': is_registered,
            'integrations': integrations
        }
        
        if email:
            data['email'] = email
        if name:
            data['name'] = name
            
        # Add metrics structure that User model expects
        data['metrics'] = {
            'prompts': [],
            'prompt_count': 0,
            'tool_calls': {},
            'tool_call_count': 0,
            'agent_calls': {},
            'agent_call_count': 0
        }
        
        mock_snapshot = MockDocumentSnapshot(data, user_id)
        return User(mock_snapshot)
    
    @staticmethod
    def create_chat(
        chat_id: str = "chat_123",
        user_id: str = "test_user_123",
        messages: Optional[List[Dict]] = None
    ) -> Chat:
        """Create actual Chat instance with real structure."""
        from firebase.models.chat import Chat
        
        if messages is None:
            messages = []
        
        data = {
            'chat_id': chat_id,
            'user_id': user_id,
            'created_at': datetime.datetime.now(),
            'updated_at': datetime.datetime.now(),
            'messages': messages,
            'title': 'Test Chat',
            'model': 'gpt-4o',
            'is_archived': False
        }
        
        mock_snapshot = MockDocumentSnapshot(data, chat_id)
        return Chat(mock_snapshot)
    
    @staticmethod
    def create_token_usage(
        user_id: str = "test_user_123",
        prompt_tokens: int = 100,
        completion_tokens: int = 50
    ) -> TokenUsage:
        """Create actual TokenUsage instance with real structure."""
        from firebase.models.token_usage import TokenUsage
        
        data = {
            'user_id': user_id,
            'created_at': datetime.datetime.now(),
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': prompt_tokens + completion_tokens,
            'model': 'gpt-4o',
            'cost': (prompt_tokens * 0.01 + completion_tokens * 0.03) / 1000  # Example pricing
        }
        
        mock_snapshot = MockDocumentSnapshot(data, f"{user_id}_{datetime.datetime.now().isoformat()}")
        return TokenUsage(mock_snapshot)


class SchemaValidator:
    """Validates that Firebase models have expected fields and structure."""
    
    @staticmethod
    def validate_plaid_token_schema(token: PlaidToken) -> None:
        """
        Validate PlaidToken has expected fields.
        This would FAIL if 'account_names' was used instead of 'account_names_and_numbers'.
        """
        assert hasattr(token, 'user_id'), "PlaidToken missing user_id"
        assert hasattr(token, 'tokens'), "PlaidToken missing tokens"
        assert hasattr(token, 'created_at'), "PlaidToken missing created_at"
        
        if token.tokens and len(token.tokens) > 0:
            first_token = token.tokens[0]
            
            # CRITICAL: This validates the actual field name
            assert 'account_names_and_numbers' in first_token, \
                f"Token missing 'account_names_and_numbers' field. Found: {first_token.keys()}"
            
            # Validate structure of account_names_and_numbers
            assert isinstance(first_token['account_names_and_numbers'], list), \
                "account_names_and_numbers must be a list"
            
            if first_token['account_names_and_numbers']:
                account = first_token['account_names_and_numbers'][0]
                assert 'name' in account, "Account missing 'name' field"
                assert 'mask' in account, "Account missing 'mask' field"
            
            # Validate other required fields
            assert 'bank_name' in first_token, "Token missing 'bank_name' field"
            assert 'id' in first_token, "Token missing 'id' field"
            assert 'valid' in first_token, "Token missing 'valid' field"
            assert 'auth_token' in first_token, "Token missing 'auth_token' field"
            assert 'item_id' in first_token, "Token missing 'item_id' field"
    
    @staticmethod
    def validate_google_token_schema(token: GoogleToken) -> None:
        """Validate GoogleToken has expected fields."""
        assert hasattr(token, 'user_id'), "GoogleToken missing user_id"
        assert hasattr(token, 'created_at'), "GoogleToken missing created_at"
        
        if hasattr(token, 'access_token'):
            # If token has credentials, validate all required fields
            assert hasattr(token, 'refresh_token'), "GoogleToken missing refresh_token"
            assert hasattr(token, 'token_expiry'), "GoogleToken missing token_expiry"
            assert hasattr(token, 'email'), "GoogleToken missing email"
            assert hasattr(token, 'scopes'), "GoogleToken missing scopes"
            assert isinstance(token.scopes, list), "GoogleToken scopes must be a list"
    
    @staticmethod
    def validate_user_schema(user: User) -> None:
        """Validate User has expected fields."""
        assert hasattr(user, 'reference_id'), "User missing reference_id"
        assert hasattr(user, 'createdAt'), "User missing createdAt"
        assert hasattr(user, 'is_registered'), "User missing is_registered"
        
        if hasattr(user, 'integrations'):
            assert isinstance(user.integrations, dict), "User integrations must be a dict"
        
        if hasattr(user, 'metrics'):
            assert isinstance(user.metrics, dict), "User metrics must be a dict"
            # Validate metrics structure
            if user.metrics:
                assert 'prompts' in user.metrics, "User metrics missing prompts"
                assert 'tool_calls' in user.metrics, "User metrics missing tool_calls"
                assert 'agent_calls' in user.metrics, "User metrics missing agent_calls"
    
    @staticmethod
    def validate_chat_schema(chat: Chat) -> None:
        """Validate Chat has expected fields."""
        assert hasattr(chat, 'chat_id'), "Chat missing chat_id"
        assert hasattr(chat, 'user_id'), "Chat missing user_id"
        assert hasattr(chat, 'messages'), "Chat missing messages"
        assert hasattr(chat, 'created_at'), "Chat missing created_at"
        assert hasattr(chat, 'updated_at'), "Chat missing updated_at"
        assert isinstance(chat.messages, list), "Chat messages must be a list"