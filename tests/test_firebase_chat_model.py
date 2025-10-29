"""
Comprehensive unit tests for Firebase Chat model.

Tests cover all Chat model methods including:
- Chat initialization and attribute setting
- Chat creation with IP and user context
- Message updating and title generation
- Token usage tracking and calculation
- Edge cases and error scenarios
"""

import pytest
import datetime
from unittest.mock import Mock, patch, call, AsyncMock
from firebase.models.chat import Chat
from tests.test_firebase_models_base import FirebaseModelTestHelper


class TestChatModelInit:
    """Test Chat model initialization and basic functionality."""

    def test_chat_init_with_media_object(self, sample_chat_data, firebase_test_helper):
        """Test Chat initialization with media object."""
        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            sample_chat_data, "chat_123"
        )

        # Execute
        chat = Chat(mock_media_object)

        # Verify basic attributes
        assert chat.reference_id == "chat_123"
        assert chat.original_ip == "192.168.1.1"
        assert chat.user_id == "user_123"
        assert chat.deleted is False
        assert chat.display_in_search is True
        assert chat.title == "Test Chat"
        assert chat.last_message_id == "msg_123"
        assert len(chat.messages) == 3
        assert len(chat.responses) == 2
        assert chat.chat_token_usage['total_tokens'] == 27

    def test_chat_init_with_minimal_data(self, firebase_test_helper):
        """Test Chat initialization with minimal data."""
        minimal_data = {
            'original_ip': '127.0.0.1',
            'user_id': 'user_456',
            'messages': []
        }

        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            minimal_data, "chat_456"
        )

        chat = Chat(mock_media_object)

        assert chat.reference_id == "chat_456"
        assert chat.original_ip == "127.0.0.1"
        assert chat.user_id == "user_456"
        assert chat.messages == []


class TestChatClassMethods:
    """Test Chat class methods."""

    def test_get_chat_by_id_existing(self, sample_chat_data, firebase_test_helper):
        """Test retrieving existing chat by ID."""
        mock_doc_snapshot = firebase_test_helper.create_mock_document_snapshot(
            sample_chat_data, 'chat_123', True
        )
        # Add user_id attribute for authorization check
        mock_doc_snapshot.user_id = 'user_123'

        mock_document = Mock()
        mock_document.get.return_value = mock_doc_snapshot

        with patch.object(Chat, 'chats') as mock_chats:
            mock_chats.document.return_value = mock_document

            # Execute
            chat = Chat.get_chat_by_id('chat_123', 'user_123')

            # Verify
            assert chat is not None
            assert chat.reference_id == 'chat_123'
            assert chat.original_ip == '192.168.1.1'

            # Verify Firestore calls
            mock_chats.document.assert_called_once_with('chat_123')
            mock_document.get.assert_called_once()

    def test_get_chat_by_id_not_exists(self):
        """Test retrieving non-existent chat by ID."""
        mock_document = Mock()
        mock_snapshot = Mock()
        mock_snapshot.exists = False

        mock_document.get.return_value = mock_snapshot

        with patch.object(Chat, 'chats') as mock_chats:
            mock_chats.document.return_value = mock_document

            # Execute
            chat = Chat.get_chat_by_id('nonexistent_chat', 'user_123')

            # Verify
            assert chat is None

    def test_create_chat_with_full_context(self, sample_user_data, firebase_test_helper):
        """Test creating a new chat with full user context."""
        # Create mock User
        mock_user = Mock()
        mock_user.reference_id = 'user_123'
        mock_user.name = 'John Doe'
        mock_user.email = 'john@example.com'
        mock_user.integrations = {'google': True,
                                  'plaid': True, 'evernote': False}

        # Mock Google and Plaid tokens
        mock_google_token = Mock()
        mock_google_token.accounts = {
            'test@gmail.com': {'email': 'test@gmail.com'}
        }

        mock_plaid_token = Mock()
        mock_plaid_token.tokens = [
            {'account_names_and_numbers': [
                {'name': 'Checking Account'},
                {'name': 'Savings Account'}
            ]}
        ]

        mock_document = Mock()
        mock_document.set = Mock()
        mock_document.get.return_value = firebase_test_helper.create_mock_document_snapshot(
            {'reference_id': 'chat_123'}, 'chat_123'
        )

        test_now = datetime.datetime(2023, 10, 15, 12, 0, 0)
        expected_expiration = test_now + datetime.timedelta(days=5)

        with patch.object(Chat, 'chats') as mock_chats, \
                patch('firebase.models.chat.datetime') as mock_datetime, \
                patch('firebase.models.chat.GoogleToken') as mock_google_token_class, \
                patch('firebase.models.chat.PlaidToken') as mock_plaid_token_class:

            mock_chats.document.return_value = mock_document
            mock_datetime.datetime.now.return_value = test_now
            mock_datetime.timedelta = datetime.timedelta
            mock_datetime.timezone = datetime.timezone

            mock_google_token_class.get_tokens_by_user_id.return_value = mock_google_token
            mock_plaid_token_class.get_tokens_by_user_id.return_value = mock_plaid_token

            # Execute
            result = Chat.create_chat(
                'chat_123', mock_user, '37.7749,-122.4194',
                'San Francisco, CA, USA', 'America/Los_Angeles', '192.168.1.100'
            )

            # Verify Firestore call was made
            mock_document.set.assert_called_once()
            call_args = mock_document.set.call_args[0][0]

            # Verify basic fields
            assert call_args['original_ip'] == '192.168.1.100'
            assert call_args['user_id'] == 'user_123'
            assert call_args['deleted'] is False
            assert call_args['display_in_search'] is False
            assert len(call_args['messages']) == 1
            assert call_args['messages'][0]['role'] == 'system'
            assert 'John Doe' in call_args['messages'][0]['content']
            assert 'john@example.com' in call_args['messages'][0]['content']

            # Verify result
            assert result is not None

    def test_create_chat_minimal_user(self, firebase_test_helper):
        """Test creating chat with minimal user information."""
        # Mock minimal user
        mock_user = Mock()
        mock_user.reference_id = 'user_456'
        mock_user.name = None
        mock_user.email = None
        mock_user.integrations = None

        mock_document = Mock()
        mock_document.set = Mock()
        mock_document.get.return_value = firebase_test_helper.create_mock_document_snapshot(
            {'reference_id': 'chat_456'}, 'chat_456'
        )

        test_now = datetime.datetime(2023, 10, 15, 12, 0, 0)

        with patch.object(Chat, 'chats') as mock_chats, \
                patch('firebase.models.chat.datetime') as mock_datetime, \
                patch('firebase.models.chat.GoogleToken') as mock_google_token_class, \
                patch('firebase.models.chat.PlaidToken') as mock_plaid_token_class:

            mock_chats.document.return_value = mock_document
            mock_datetime.datetime.now.return_value = test_now
            mock_datetime.timedelta = datetime.timedelta
            mock_datetime.timezone = datetime.timezone

            mock_google_token_class.get_tokens_by_user_id.return_value = None
            mock_plaid_token_class.get_tokens_by_user_id.return_value = None

            # Execute
            result = Chat.create_chat(
                'chat_456', mock_user, '0,0', 'Unknown', 'UTC', '127.0.0.1'
            )

            # Verify basic fields without user details
            mock_document.set.assert_called_once()
            call_args = mock_document.set.call_args[0][0]

            assert call_args['user_id'] == 'user_456'
            assert call_args['original_ip'] == '127.0.0.1'
            system_message = call_args['messages'][0]['content']
            assert 'not connected to any Google accounts' in system_message
            assert 'not connected to any Bank' in system_message


class TestChatMessageManagement:
    """Test Chat message updating and management."""

    def test_add_message(self, sample_chat_data, firebase_test_helper):
        """Test adding a single message."""
        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            sample_chat_data, "chat_123"
        )

        mock_document = Mock()
        mock_document.update = Mock()

        with patch.object(Chat, 'chats') as mock_chats:
            mock_chats.document.return_value = mock_document

            chat = Chat(mock_media_object)
            original_message_count = len(chat.messages)

            # Execute
            chat.add_message("New user message")

            # Verify message was added
            assert len(chat.messages) == original_message_count + 1
            assert chat.messages[-1]['content'] == "New user message"
            assert chat.messages[-1]['role'] == 'user'

            # Verify Firestore update
            mock_document.update.assert_called_once_with({
                'messages': chat.messages
            })

    @pytest.mark.asyncio
    async def test_update_messages_with_title_generation(self, sample_chat_data, firebase_test_helper, mock_openai_client):
        """Test updating messages with title generation."""
        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            sample_chat_data, "chat_123"
        )

        mock_document = Mock()
        mock_document.update = Mock()

        # Configure OpenAI mock
        mock_openai_client.chat.completions.create.return_value.choices[
            0].message.content = "Generated Title"

        test_now = datetime.datetime(2023, 10, 15, 12, 0, 0)
        expected_expiration = test_now + datetime.timedelta(weeks=1000)

        with patch.object(Chat, 'chats') as mock_chats, \
                patch('firebase.models.chat.client', mock_openai_client), \
                patch('firebase.models.chat.datetime') as mock_datetime:

            mock_chats.document.return_value = mock_document
            mock_datetime.datetime.now.return_value = test_now
            mock_datetime.timedelta = datetime.timedelta

            chat = Chat(mock_media_object)

            new_messages = [
                {'content': 'System message', 'role': 'system'},
                {'content': 'Hello', 'role': 'user'},
                {'content': 'Hi there!', 'role': 'assistant'}
            ]

            # Execute
            result = await chat.update_messages(new_messages, "msg_456")

            # Verify title generation API call
            mock_openai_client.chat.completions.create.assert_called_once_with(
                model="gpt-4o",
                messages=[
                    {'role': 'user',
                        'content': '[{"content": "Hello", "role": "user"}, {"content": "Hi there!", "role": "assistant"}]'},
                    {"role": "user", "content": "Give back a title for this chat under 30 characters. Don't wrap it in quotes or use any other formatting."}
                ]
            )

            # Verify Firestore update
            expected_update = {
                'messages': new_messages,
                'title': 'Generated Title',
                'expires_at': expected_expiration,
                'display_in_search': True,
                'last_message_id': 'msg_456'
            }

            mock_document.update.assert_called_once_with(expected_update)

            # Verify object state
            assert chat.messages == new_messages
            assert chat.title == "Generated Title"
            assert result == chat

    @pytest.mark.asyncio
    async def test_add_responses_new(self, sample_chat_data, firebase_test_helper):
        """Test adding responses when responses exist."""
        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            sample_chat_data, "chat_123"
        )

        mock_document = Mock()
        mock_document.update = Mock()

        with patch.object(Chat, 'chats') as mock_chats:
            mock_chats.document.return_value = mock_document

            chat = Chat(mock_media_object)
            original_response_count = len(chat.responses)

            new_responses = [
                {'type': 'user_prompt', 'prompt': 'New question'},
                {'type': 'assistant_response', 'content': 'New answer'}
            ]

            # Execute
            result = await chat.add_responses(new_responses)

            # Verify responses were added
            assert len(chat.responses) == original_response_count + 2
            assert chat.responses[-2:] == new_responses

            # Verify Firestore update
            mock_document.update.assert_called_once_with({
                'responses': chat.responses
            })

            assert result == chat

    @pytest.mark.asyncio
    async def test_add_responses_first_time(self, firebase_test_helper):
        """Test adding responses when no responses exist."""
        chat_data_no_responses = {
            'original_ip': '192.168.1.1',
            'user_id': 'user_123',
            'messages': []
        }

        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            chat_data_no_responses, "chat_123"
        )

        mock_document = Mock()
        mock_document.update = Mock()

        with patch.object(Chat, 'chats') as mock_chats:
            mock_chats.document.return_value = mock_document

            chat = Chat(mock_media_object)

            new_responses = [
                {'type': 'user_prompt', 'prompt': 'First question'}
            ]

            # Execute
            result = await chat.add_responses(new_responses)

            # Verify responses were set
            assert hasattr(chat, 'responses')
            assert chat.responses == new_responses

            # Verify Firestore update
            mock_document.update.assert_called_once_with({
                'responses': new_responses
            })

            assert result == chat


class TestChatTokenUsage:
    """Test Chat token usage tracking."""

    @pytest.mark.asyncio
    async def test_update_token_usage_existing(self, sample_chat_data, firebase_test_helper):
        """Test updating token usage when usage already exists."""
        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            sample_chat_data, "chat_123"
        )

        mock_document = Mock()
        mock_document.update = Mock()

        with patch.object(Chat, 'chats') as mock_chats:
            mock_chats.document.return_value = mock_document

            chat = Chat(mock_media_object)

            # Execute
            result = await chat.update_token_usage(25, 5, 30)

            # Verify token usage was updated (added to existing)
            expected_total_usage = {
                'input_tokens': 35,  # 10 + 25
                'cached_input_tokens': 7,  # 2 + 5
                'output_tokens': 45,  # 15 + 30
                'total_tokens': 87  # 27 + 60
            }

            assert chat.chat_token_usage == expected_total_usage

            # Verify Firestore update
            mock_document.update.assert_called_once_with({
                'chat_token_usage': expected_total_usage
            })

            assert result == chat

    @pytest.mark.asyncio
    async def test_update_token_usage_no_existing(self, firebase_test_helper):
        """Test updating token usage when no existing usage."""
        chat_data_no_usage = {
            'original_ip': '192.168.1.1',
            'user_id': 'user_123',
            'messages': []
        }

        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            chat_data_no_usage, "chat_123"
        )

        mock_document = Mock()
        mock_document.update = Mock()

        with patch.object(Chat, 'chats') as mock_chats:
            mock_chats.document.return_value = mock_document

            chat = Chat(mock_media_object)

            # Execute
            result = await chat.update_token_usage(10, 2, 15)

            # Verify usage is set directly
            expected_usage = {
                'input_tokens': 10,
                'cached_input_tokens': 2,
                'output_tokens': 15,
                'total_tokens': 27
            }

            assert chat.chat_token_usage == expected_usage

            # Verify Firestore update
            mock_document.update.assert_called_once_with({
                'chat_token_usage': expected_usage
            })

            assert result == chat


class TestChatUtilityMethods:
    """Test Chat utility methods."""

    def test_update_timestamp(self, sample_chat_data, firebase_test_helper):
        """Test updating timestamp and adding current time message."""
        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            sample_chat_data, "chat_123"
        )

        test_now = datetime.datetime(2023, 10, 15, 12, 0, 0)

        with patch('firebase.models.chat.datetime') as mock_datetime:
            mock_datetime.datetime.now.return_value = test_now
            mock_datetime.timezone = datetime.timezone

            chat = Chat(mock_media_object)
            original_message_count = len(chat.messages)

            # Execute
            result = chat.update_timestamp()

            # Verify timestamp was updated
            assert chat.updated_at == test_now

            # Verify system message was added
            assert len(chat.messages) == original_message_count + 1
            assert chat.messages[-1]['role'] == 'system'
            assert '2023-10-15 12:00:00 UTC' in chat.messages[-1]['content']

            assert result == chat


class TestChatEdgeCases:
    """Test edge cases and error scenarios."""

    def test_chat_init_with_empty_data(self, firebase_test_helper):
        """Test Chat initialization with empty data."""
        empty_data = {}

        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            empty_data, "empty_chat"
        )

        chat = Chat(mock_media_object)

        assert chat.reference_id == "empty_chat"
        # Should not have attributes that weren't in the data
        assert not hasattr(chat, 'original_ip')
        assert not hasattr(chat, 'user_id')

    def test_chat_with_none_values(self, firebase_test_helper):
        """Test chat handling with None values."""
        chat_data_with_nones = {
            'original_ip': '192.168.1.1',
            'user_id': 'user_123',
            'messages': None,
            'responses': None,
            'chat_token_usage': None
        }

        mock_media_object = firebase_test_helper.create_mock_document_snapshot(
            chat_data_with_nones, "chat_123"
        )

        chat = Chat(mock_media_object)

        assert chat.reference_id == "chat_123"
        assert chat.messages is None
        assert chat.responses is None
        assert chat.chat_token_usage is None

    def test_create_chat_with_user_without_attributes(self, firebase_test_helper):
        """Test creating chat when user object lacks expected attributes."""
        # Mock user without some attributes
        mock_user = Mock()
        mock_user.reference_id = 'user_789'
        # Explicitly set attributes to None to simulate missing attributes
        mock_user.name = None
        mock_user.email = None
        mock_user.integrations = None

        mock_document = Mock()
        mock_document.set = Mock()
        mock_document.get.return_value = firebase_test_helper.create_mock_document_snapshot(
            {'reference_id': 'chat_789'}, 'chat_789'
        )

        test_now = datetime.datetime(2023, 10, 15, 12, 0, 0)

        with patch.object(Chat, 'chats') as mock_chats, \
                patch('firebase.models.chat.datetime') as mock_datetime, \
                patch('firebase.models.chat.GoogleToken') as mock_google_token_class, \
                patch('firebase.models.chat.PlaidToken') as mock_plaid_token_class:

            mock_chats.document.return_value = mock_document
            mock_datetime.datetime.now.return_value = test_now
            mock_datetime.timedelta = datetime.timedelta
            mock_datetime.timezone = datetime.timezone

            mock_google_token_class.get_tokens_by_user_id.return_value = None
            mock_plaid_token_class.get_tokens_by_user_id.return_value = None

            # Execute - should not raise exception
            result = Chat.create_chat(
                'chat_789', mock_user, '0,0', 'Test Location', 'UTC', '192.168.1.1'
            )

            # Verify it handled missing attributes gracefully
            mock_document.set.assert_called_once()
            call_args = mock_document.set.call_args[0][0]

            # Should not include name/email in system message
            system_message = call_args['messages'][0]['content']
            assert 'My name is' not in system_message
            assert 'My email is' not in system_message

            assert result is not None


if __name__ == "__main__":
    pytest.main([__file__])
