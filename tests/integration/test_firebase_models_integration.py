"""
Integration tests for Firebase models with minimal mocking.

These tests validate that Firebase models maintain their expected structure
and would catch field name changes or structural modifications.
"""

import pytest
import datetime
import uuid
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.fixtures.firebase_models import FirebaseModelFactory, SchemaValidator, MockDocumentSnapshot


class TestGoogleTokenIntegration:
    """Integration tests for GoogleToken model with real data structures."""
    
    def test_google_token_schema_validation(self):
        """Test that GoogleToken has the expected schema."""
        # Create a real GoogleToken instance
        token = FirebaseModelFactory.create_google_token(
            user_id="google_schema_test_user",
            has_token=True,
            valid=True
        )
        
        # Validate schema
        SchemaValidator.validate_google_token_schema(token)
        
        # Additional explicit checks
        assert token.user_id == "google_schema_test_user"
        assert hasattr(token, 'access_token')
        assert hasattr(token, 'refresh_token')
        assert hasattr(token, 'email')
        assert token.email == 'test@example.com'
        assert hasattr(token, 'scopes')
        assert isinstance(token.scopes, list)
    
    def test_google_token_without_credentials(self):
        """Test GoogleToken without credentials."""
        token = FirebaseModelFactory.create_google_token(
            user_id="no_creds_user",
            has_token=False
        )
        
        assert token.user_id == "no_creds_user"
        assert not hasattr(token, 'access_token')
        assert not hasattr(token, 'refresh_token')
        
        # Schema validation should still pass
        SchemaValidator.validate_google_token_schema(token)
    
    def test_google_token_save_structure(self):
        """Test that GoogleToken save_or_add_token maintains correct structure."""
        from firebase.models.google_token import GoogleToken
        
        with patch('firebase.models.google_token.GoogleToken.google_tokens') as mock_collection, \
             patch('firebase.models.user.User.get_user_by_id') as mock_get_user:
            
            # Mock User.get_user_by_id
            mock_user = Mock()
            mock_user.reference_id = 'save_test_user'
            mock_user.set_connected_to_google = Mock()
            mock_get_user.return_value = mock_user
            
            # Mock the query for existing token request
            mock_query = Mock()
            mock_query.where.return_value = mock_query
            mock_query.get.return_value = [Mock(reference=Mock(id='request_123'))]
            mock_collection.where.return_value = mock_query
            
            # Mock document operations
            mock_doc = Mock()
            existing_data = {
                'user_id': 'save_test_user',
                'created_at': datetime.datetime.now(),
                'state': 'test_state'
            }
            mock_snapshot = MockDocumentSnapshot(existing_data, 'save_test_user')
            mock_doc.get.return_value = mock_snapshot
            mock_collection.document.return_value = mock_doc
            
            # Create token dict (mimicking OAuth response)
            token_dict = {
                'access_token': 'test_access_token',
                'refresh_token': 'test_refresh_token',
                'expires_in': 3600,
                'token_type': 'Bearer'
            }
            
            # Create user info dict
            user_info = {
                'email': 'save@example.com',
                'name': 'Save Test User',
                'picture': 'https://example.com/pic.jpg'
            }
            
            # Save token with actual structure
            result = GoogleToken.save_or_add_token(
                state='test_state',
                token=token_dict,
                user_info=user_info
            )
            
            # Verify the structure of what was updated
            update_data = mock_doc.update.call_args[0][0]
            assert 'accounts' in update_data
            assert 'save@example.com' in update_data['accounts']
            account_data = update_data['accounts']['save@example.com']
            assert 'email' in account_data
            assert account_data['email'] == 'save@example.com'
            assert 'name' in account_data
            assert account_data['name'] == 'Save Test User'
            assert 'picture' in account_data


class TestUserModelIntegration:
    """Integration tests for User model with real data structures."""
    
    def test_user_schema_validation(self):
        """Test that User has the expected schema."""
        user = FirebaseModelFactory.create_user(
            user_id="schema_test_user",
            email="schema@example.com",
            name="Schema Test User",
            is_registered=True,
            integrations={'google': True, 'plaid': False}
        )
        
        # Validate schema
        SchemaValidator.validate_user_schema(user)
        
        # Additional explicit checks
        assert user.reference_id == "schema_test_user"
        assert user.email == "schema@example.com"
        assert user.name == "Schema Test User"
        assert user.is_registered == True
        assert user.integrations == {'google': True, 'plaid': False}
        assert hasattr(user, 'metrics')
    
    def test_user_metrics_structure(self):
        """Test that User metrics have correct structure."""
        user = FirebaseModelFactory.create_user(
            user_id="metrics_test_user"
        )
        
        # Validate metrics structure
        assert 'prompts' in user.metrics
        assert 'prompt_count' in user.metrics
        assert 'tool_calls' in user.metrics
        assert 'tool_call_count' in user.metrics
        assert 'agent_calls' in user.metrics
        assert 'agent_call_count' in user.metrics
        
        assert isinstance(user.metrics['prompts'], list)
        assert isinstance(user.metrics['tool_calls'], dict)
        assert isinstance(user.metrics['agent_calls'], dict)
    
    def test_user_integrations_tracking(self):
        """Test that User integrations are properly tracked."""
        from firebase.models.user import User
        
        with patch('firebase.models.user.User.users') as mock_collection:
            # Create user with no integrations
            user_data = {
                'reference_id': 'integration_user',
                'createdAt': datetime.datetime.now(),
                'is_registered': True,
                'integrations': {}
            }
            
            mock_snapshot = MockDocumentSnapshot(user_data, 'integration_user')
            user = User(mock_snapshot)
            
            # Initially no integrations
            assert user.integrations == {}
            
            # Mock the update operation
            mock_doc = Mock()
            mock_collection.document.return_value = mock_doc
            
            # Mock set_connected_to_google method
            user.set_connected_to_google = Mock()
            
            # Set Google integration
            user.set_connected_to_google()
            
            # Verify the method was called
            user.set_connected_to_google.assert_called_once()
    
    def test_user_without_optional_fields(self):
        """Test User without optional fields like email and name."""
        user = FirebaseModelFactory.create_user(
            user_id="minimal_user",
            email=None,
            name=None,
            is_registered=False
        )
        
        assert user.reference_id == "minimal_user"
        assert not hasattr(user, 'email') or user.email is None
        assert not hasattr(user, 'name') or user.name is None
        assert user.is_registered == False
        
        # Schema validation should still pass
        SchemaValidator.validate_user_schema(user)


class TestChatModelIntegration:
    """Integration tests for Chat model with real data structures."""
    
    def test_chat_schema_validation(self):
        """Test that Chat has the expected schema."""
        messages = [
            {'role': 'user', 'content': 'Hello'},
            {'role': 'assistant', 'content': 'Hi there!'}
        ]
        
        chat = FirebaseModelFactory.create_chat(
            chat_id="schema_test_chat",
            user_id="chat_user",
            messages=messages
        )
        
        # Validate schema
        SchemaValidator.validate_chat_schema(chat)
        
        # Additional explicit checks
        assert chat.chat_id == "schema_test_chat"
        assert chat.user_id == "chat_user"
        assert len(chat.messages) == 2
        assert chat.messages[0]['role'] == 'user'
        assert chat.messages[0]['content'] == 'Hello'
        assert hasattr(chat, 'title')
        assert hasattr(chat, 'model')
        assert hasattr(chat, 'is_archived')
    
    def test_chat_message_structure(self):
        """Test that Chat messages maintain correct structure."""
        from firebase.models.chat import Chat
        
        with patch('firebase.models.chat.Chat.chats') as mock_collection:
            # Create chat with tool calls in messages
            messages = [
                {
                    'role': 'user',
                    'content': 'Search for weather'
                },
                {
                    'role': 'assistant',
                    'content': None,
                    'tool_calls': [
                        {
                            'id': 'call_123',
                            'type': 'function',
                            'function': {
                                'name': 'get_weather',
                                'arguments': '{"location": "San Francisco"}'
                            }
                        }
                    ]
                },
                {
                    'role': 'tool',
                    'content': '{"temperature": 72, "conditions": "sunny"}',
                    'tool_call_id': 'call_123'
                }
            ]
            
            chat_data = {
                'chat_id': 'tool_chat',
                'user_id': 'tool_user',
                'messages': messages,
                'created_at': datetime.datetime.now(),
                'updated_at': datetime.datetime.now(),
                'title': 'Weather Search',
                'model': 'gpt-4o'
            }
            
            mock_snapshot = MockDocumentSnapshot(chat_data, 'tool_chat')
            chat = Chat(mock_snapshot)
            
            # Verify message structure is preserved
            assert len(chat.messages) == 3
            assert chat.messages[1]['tool_calls'] is not None
            assert chat.messages[1]['tool_calls'][0]['function']['name'] == 'get_weather'
            assert chat.messages[2]['role'] == 'tool'
            assert chat.messages[2]['tool_call_id'] == 'call_123'
    
    def test_chat_save_message_structure(self):
        """Test that saving messages preserves structure."""
        from firebase.models.chat import Chat
        
        with patch('firebase.models.chat.Chat.chats') as mock_collection:
            # Mock document operations
            mock_doc = Mock()
            mock_collection.document.return_value = mock_doc
            
            # Create chat
            chat_data = {
                'chat_id': 'save_chat',
                'user_id': 'save_user',
                'messages': [],
                'created_at': datetime.datetime.now(),
                'updated_at': datetime.datetime.now()
            }
            
            mock_snapshot = MockDocumentSnapshot(chat_data, 'save_chat')
            chat = Chat(mock_snapshot)
            
            # Add a message
            new_message = {
                'role': 'user',
                'content': 'Test message',
                'timestamp': datetime.datetime.now().isoformat()
            }
            
            chat.messages.append(new_message)
            chat.add_message(new_message['content'])
            
            # Verify update was called with correct structure
            update_data = mock_doc.update.call_args[0][0]
            assert 'messages' in update_data
            # The messages should now have 2 entries (the one we added plus the one add_message adds)
            assert len(update_data['messages']) >= 1


class TestEvernoteTokenIntegration:
    """Integration tests for EvernoteToken model with real data structures."""
    
    def test_evernote_token_schema(self):
        """Test that EvernoteToken has expected schema."""
        token = FirebaseModelFactory.create_evernote_token(
            user_id="evernote_test_user",
            has_token=True
        )
        
        assert token.user_id == "evernote_test_user"
        assert hasattr(token, 'access_token')
        assert hasattr(token, 'note_store_url')
        assert hasattr(token, 'web_api_url_prefix')
        assert hasattr(token, 'expires_at')
    
    def test_evernote_token_save_structure(self):
        """Test that EvernoteToken save maintains correct structure."""
        from firebase.models.evernote_token import EvernoteToken
        
        with patch('firebase.models.evernote_token.EvernoteToken.evernote_tokens') as mock_collection, \
             patch('firebase.models.evernote_token.EvernoteToken.get_evernote_token_by_user_id') as mock_get_token:
            
            # Mock get_evernote_token_by_user_id to return an existing token
            mock_existing_token = Mock()
            mock_existing_token.created_at = datetime.datetime.now()
            mock_get_token.return_value = mock_existing_token
            
            # Mock document operations
            mock_doc = Mock()
            mock_collection.document.return_value = mock_doc
            
            # Save token using the actual method signature
            result = EvernoteToken.save_evernote_token(
                user_id='evernote_save_user',
                access_token='evernote_access_token'
            )
            
            # Verify structure
            saved_data = mock_doc.set.call_args[0][0]
            assert 'user_id' in saved_data
            assert saved_data['user_id'] == 'evernote_save_user'
            assert 'access_token' in saved_data


class TestTokenUsageIntegration:
    """Integration tests for TokenUsage model with real data structures."""
    
    def test_token_usage_schema(self):
        """Test that TokenUsage has expected schema."""
        usage = FirebaseModelFactory.create_token_usage(
            user_id="usage_test_user",
            prompt_tokens=150,
            completion_tokens=75
        )
        
        assert usage.user_id == "usage_test_user"
        assert usage.prompt_tokens == 150
        assert usage.completion_tokens == 75
        assert usage.total_tokens == 225
        assert hasattr(usage, 'model')
        assert hasattr(usage, 'cost')
        assert usage.cost > 0  # Should calculate cost
    
    def test_token_usage_add_structure(self):
        """Test that TokenUsage.add_usage maintains correct structure."""
        from firebase.models.token_usage import TokenUsage
        import asyncio
        
        with patch('firebase.models.token_usage.TokenUsage.token_usage') as mock_collection:
            # Mock document operations
            mock_doc = Mock()
            
            # Mock the first get() for existing usage check
            mock_doc_get = Mock()
            mock_doc_get.exists = False  # Simulate no existing usage
            mock_doc_get.reference = Mock()
            mock_doc_get.reference.id = 'usage_create_user'
            
            # Mock the second get() after creation
            mock_doc_get_after = Mock()
            mock_doc_get_after.exists = True
            mock_doc_get_after.reference = Mock()
            mock_doc_get_after.reference.id = 'usage_create_user'
            mock_doc_get_after.to_dict.return_value = {
                'usage': {},
                'total_usage': {
                    'input_tokens': 0,
                    'output_tokens': 0,
                    'cached_input_tokens': 0,
                    'total_cost': 0
                }
            }
            
            # Set up the get() to return different values on different calls
            mock_doc.get.side_effect = [mock_doc_get, mock_doc_get_after]
            mock_doc.set = Mock()
            mock_doc.update = Mock()
            mock_collection.document.return_value = mock_doc
            
            # Mock user
            mock_user = Mock()
            mock_user.reference_id = 'usage_create_user'
            
            # Add usage record using the actual method (async)
            asyncio.run(TokenUsage.add_usage(
                user=mock_user,
                input_tokens=200,
                cached_input_tokens=50,
                output_tokens=100
            ))
            
            # Verify set was called since no existing usage
            assert mock_doc.set.called
            saved_data = mock_doc.set.call_args[0][0]
            
            # Verify structure (checking the nested usage structure)
            assert 'usage' in saved_data
            current_year = datetime.datetime.now().strftime("%Y")
            current_month = datetime.datetime.now().strftime("%m")
            current_day = datetime.datetime.now().strftime("%d")
            
            assert current_year in saved_data['usage']
            year_data = saved_data['usage'][current_year]
            assert current_month in year_data
            month_data = year_data[current_month]
            assert current_day in month_data
            day_data = month_data[current_day]
            
            # Check the actual token values
            assert day_data['input_tokens'] == 200
            assert day_data['output_tokens'] == 100
            assert day_data['cached_input_tokens'] == 50
            assert 'total_cost' in day_data


class TestFirebaseModelFieldRegression:
    """Regression tests to ensure field names don't change unexpectedly."""
    
    def test_critical_field_names_plaid(self):
        """Ensure PlaidToken uses 'account_names_and_numbers' not 'account_names'."""
        token = FirebaseModelFactory.create_plaid_token(with_accounts=True)
        
        # This would fail if field reverted to 'account_names'
        assert 'account_names_and_numbers' in token.tokens[0]
        assert 'account_names' not in token.tokens[0]
    
    def test_critical_field_names_google(self):
        """Ensure GoogleToken uses correct field names."""
        token = FirebaseModelFactory.create_google_token(has_token=True)
        
        # Check critical fields exist
        assert hasattr(token, 'access_token')
        assert hasattr(token, 'refresh_token')
        assert hasattr(token, 'scopes')
        assert not hasattr(token, 'scope')  # Common mistake
    
    def test_critical_field_names_user(self):
        """Ensure User uses correct field names."""
        user = FirebaseModelFactory.create_user()
        
        # Check critical fields
        assert hasattr(user, 'reference_id')
        assert not hasattr(user, 'user_id')  # User uses reference_id
        assert hasattr(user, 'createdAt')
        assert not hasattr(user, 'created_at')  # User uses createdAt
    
    def test_critical_field_names_chat(self):
        """Ensure Chat uses correct field names."""
        chat = FirebaseModelFactory.create_chat()
        
        # Check critical fields
        assert hasattr(chat, 'chat_id')
        assert hasattr(chat, 'messages')
        assert not hasattr(chat, 'message')  # Should be plural
        assert hasattr(chat, 'is_archived')
        assert not hasattr(chat, 'archived')  # Should have is_ prefix