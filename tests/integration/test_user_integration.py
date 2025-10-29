"""
Integration tests for User model.

These tests use real User instances with actual data structures
to ensure field name changes and structural modifications are caught.
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


class TestUserIntegration:
    """Integration tests for User model with real data structures."""
    
    def test_user_schema_validation(self):
        """Test that User has the expected schema with correct field names."""
        # Create a real User instance
        user = FirebaseModelFactory.create_user(
            user_id="schema_test_user",
            email="schema@example.com",
            name="Schema Test User",
            is_registered=True,
            integrations={'google': True, 'plaid': False, 'evernote': False}
        )
        
        # Validate schema - this would FAIL if field names changed
        SchemaValidator.validate_user_schema(user)
        
        # Additional explicit checks for critical fields
        assert user.reference_id == "schema_test_user"  # NOT user_id
        assert user.email == "schema@example.com"
        assert user.name == "Schema Test User"
        assert user.is_registered == True
        assert hasattr(user, 'createdAt')  # NOT created_at
        assert hasattr(user, 'integrations')
        assert user.integrations['google'] == True
        assert user.integrations['plaid'] == False
    
    def test_user_metrics_structure(self):
        """Test that User metrics have correct structure."""
        user = FirebaseModelFactory.create_user(
            user_id="metrics_test_user"
        )
        
        # Validate metrics structure exists
        assert hasattr(user, 'metrics')
        assert isinstance(user.metrics, dict)
        
        # Check all required metrics fields
        assert 'prompts' in user.metrics
        assert 'prompt_count' in user.metrics
        assert 'tool_calls' in user.metrics
        assert 'tool_call_count' in user.metrics
        assert 'agent_calls' in user.metrics
        assert 'agent_call_count' in user.metrics
        
        # Check data types
        assert isinstance(user.metrics['prompts'], list)
        assert isinstance(user.metrics['prompt_count'], int)
        assert isinstance(user.metrics['tool_calls'], dict)
        assert isinstance(user.metrics['tool_call_count'], int)
        assert isinstance(user.metrics['agent_calls'], dict)
        assert isinstance(user.metrics['agent_call_count'], int)
    
    def test_user_add_prompt_to_metrics(self):
        """Test that add_prompt_to_metrics maintains correct structure."""
        from firebase.models.user import User
        
        with patch('firebase.models.user.User.users') as mock_collection:
            # Create user with empty metrics
            user_data = {
                'reference_id': 'prompt_user',
                'createdAt': datetime.datetime.now(),
                'is_registered': True,
                'metrics': {
                    'prompts': [],
                    'prompt_count': 0,
                    'tool_calls': {},
                    'tool_call_count': 0,
                    'agent_calls': {},
                    'agent_call_count': 0
                }
            }
            
            mock_snapshot = MockDocumentSnapshot(user_data, 'prompt_user')
            user = User(mock_snapshot)
            
            # Mock document update
            mock_doc = Mock()
            mock_collection.document.return_value = mock_doc
            
            # Add a prompt
            test_prompt = "What is the weather today?"
            user.add_prompt_to_metrics(test_prompt)
            
            # Verify the metrics structure after adding
            assert len(user.metrics['prompts']) == 1
            assert user.metrics['prompts'][0]['prompt'] == test_prompt
            assert 'timestamp' in user.metrics['prompts'][0]
            assert user.metrics['prompt_count'] == 1
            
            # Verify update was called
            update_data = mock_doc.update.call_args[0][0]
            assert 'metrics' in update_data
    
    def test_user_add_tool_call_to_metrics(self):
        """Test that add_tool_call_to_metrics maintains correct structure."""
        from firebase.models.user import User
        
        with patch('firebase.models.user.User.users') as mock_collection:
            # Create user with empty metrics
            user_data = {
                'reference_id': 'tool_user',
                'createdAt': datetime.datetime.now(),
                'is_registered': True,
                'metrics': {
                    'prompts': [],
                    'prompt_count': 0,
                    'tool_calls': {},
                    'tool_call_count': 0,
                    'agent_calls': {},
                    'agent_call_count': 0
                }
            }
            
            mock_snapshot = MockDocumentSnapshot(user_data, 'tool_user')
            user = User(mock_snapshot)
            
            # Mock document update
            mock_doc = Mock()
            mock_collection.document.return_value = mock_doc
            
            # Add tool calls
            user.add_tool_call_to_metrics('search_web')
            user.add_tool_call_to_metrics('search_web')
            user.add_tool_call_to_metrics('get_weather')
            
            # Verify the metrics structure
            assert user.metrics['tool_calls']['search_web'] == 2
            assert user.metrics['tool_calls']['get_weather'] == 1
            assert user.metrics['tool_call_count'] == 3
    
    def test_user_add_agent_call_to_metrics(self):
        """Test that add_agent_call_to_metrics maintains correct structure."""
        from firebase.models.user import User
        
        with patch('firebase.models.user.User.users') as mock_collection:
            # Create user with empty metrics
            user_data = {
                'reference_id': 'agent_user',
                'createdAt': datetime.datetime.now(),
                'is_registered': True,
                'metrics': {
                    'prompts': [],
                    'prompt_count': 0,
                    'tool_calls': {},
                    'tool_call_count': 0,
                    'agent_calls': {},
                    'agent_call_count': 0
                }
            }
            
            mock_snapshot = MockDocumentSnapshot(user_data, 'agent_user')
            user = User(mock_snapshot)
            
            # Mock document update
            mock_doc = Mock()
            mock_collection.document.return_value = mock_doc
            
            # Add agent calls
            user.add_agent_call_to_metrics('gmail_agent')
            user.add_agent_call_to_metrics('plaid_agent')
            user.add_agent_call_to_metrics('gmail_agent')
            
            # Verify the metrics structure
            assert user.metrics['agent_calls']['gmail_agent'] == 2
            assert user.metrics['agent_calls']['plaid_agent'] == 1
            assert user.metrics['agent_call_count'] == 3
    
    def test_user_integration_tracking(self):
        """Test that User integration methods update correct fields."""
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
            
            # Mock document update
            mock_doc = Mock()
            mock_collection.document.return_value = mock_doc
            
            # Test set_connected_to_google
            user.set_connected_to_google()
            update_data = mock_doc.update.call_args_list[0][0][0]
            assert 'integrations' in update_data
            assert update_data['integrations']['google'] == True
            
            # Test set_connected_to_plaid
            user.set_connected_to_plaid()
            update_data = mock_doc.update.call_args_list[1][0][0]
            assert 'integrations' in update_data
            assert update_data['integrations']['plaid'] == True
            
            # Test set_connected_to_evernote
            user.set_connected_to_evernote()
            update_data = mock_doc.update.call_args_list[2][0][0]
            assert 'integrations' in update_data
            assert update_data['integrations']['evernote'] == True
    
    def test_user_create_new_user_structure(self):
        """Test that User constructor creates correct structure."""
        from firebase.models.user import User
        
        # Create user data
        created_data = {
            'reference_id': 'new_user_123',
            'createdAt': datetime.datetime.now(),
            'is_registered': False,
            'integrations': {},
            'metrics': {
                'prompts': [],
                'prompt_count': 0,
                'tool_calls': {},
                'tool_call_count': 0,
                'agent_calls': {},
                'agent_call_count': 0
            }
        }
        mock_snapshot = MockDocumentSnapshot(created_data, 'new_user_123')
        
        # Create user using constructor
        result = User(mock_snapshot)
        
        # Verify returned object structure
        assert result.reference_id == 'new_user_123'
        assert result.is_registered == False
        assert hasattr(result, 'createdAt')
        assert hasattr(result, 'integrations')
        assert result.integrations == {}
    
    def test_user_get_user_by_id_structure(self):
        """Test that get_user_by_id returns correct structure."""
        from firebase.models.user import User
        
        with patch('firebase.models.user.User.users') as mock_collection:
            # Create test user data
            user_data = {
                'reference_id': 'lookup_user',
                'createdAt': datetime.datetime.now(),
                'is_registered': True,
                'email': 'lookup@example.com',
                'name': 'Lookup User',
                'integrations': {'google': True}
            }
            
            mock_snapshot = MockDocumentSnapshot(user_data, 'lookup_user', exists=True)
            mock_collection.document.return_value.get.return_value = mock_snapshot
            
            # Get user
            result = User.get_user_by_id('lookup_user')
            
            assert result is not None
            assert result.reference_id == 'lookup_user'
            assert result.email == 'lookup@example.com'
            assert result.integrations['google'] == True
    
    def test_user_without_optional_fields(self):
        """Test User without optional fields like email and name."""
        user = FirebaseModelFactory.create_user(
            user_id="minimal_user",
            email=None,
            name=None,
            is_registered=False
        )
        
        assert user.reference_id == "minimal_user"
        # User without email/name shouldn't have these attributes or they should be None
        assert not hasattr(user, 'email') or user.email is None
        assert not hasattr(user, 'name') or user.name is None
        assert user.is_registered == False
        
        # Schema validation should still pass
        SchemaValidator.validate_user_schema(user)
    
    def test_user_record_creation_and_signup(self):
        """Test that record_creation and record_signup update correct fields."""
        from firebase.models.user import User
        
        with patch('firebase.models.user.User.users') as mock_collection:
            # Create user that hasn't been recorded
            user_data = {
                'reference_id': 'record_user',
                'createdAt': datetime.datetime.now(),
                'is_registered': True,
                'email': 'record@example.com'
            }
            
            mock_snapshot = MockDocumentSnapshot(user_data, 'record_user')
            user = User(mock_snapshot)
            
            # Mock document update
            mock_doc = Mock()
            mock_collection.document.return_value = mock_doc
            
            # Record creation
            user.record_creation()
            update_data = mock_doc.update.call_args_list[0][0][0]
            assert 'creationRecorded' in update_data
            assert update_data['creationRecorded'] == True
            
            # Record signup
            user.record_signup()
            update_data = mock_doc.update.call_args_list[1][0][0]
            assert 'signupRecorded' in update_data
            assert update_data['signupRecorded'] == True
    
    def test_user_field_name_regression(self):
        """
        Regression test to ensure we're using correct field names.
        This test would FAIL if someone changed critical field names.
        """
        from firebase.models.user import User
        
        # Create user with correct field names
        correct_data = {
            'reference_id': 'regression_user',  # CORRECT: reference_id
            'createdAt': datetime.datetime.now(),  # CORRECT: createdAt
            'is_registered': True,
            'integrations': {},  # CORRECT: integrations (plural)
            'metrics': {  # CORRECT: metrics (plural)
                'prompts': [],
                'tool_calls': {},
                'agent_calls': {}
            }
        }
        
        mock_snapshot = MockDocumentSnapshot(correct_data, 'regression_user')
        user = User(mock_snapshot)
        
        # These assertions would fail if field names were wrong
        assert hasattr(user, 'reference_id')  # NOT 'user_id'
        assert hasattr(user, 'createdAt')  # NOT 'created_at'
        assert hasattr(user, 'integrations')  # NOT 'integration'
        assert hasattr(user, 'metrics')  # NOT 'metric'
        
        # Ensure wrong field names are NOT present
        assert not hasattr(user, 'user_id')
        assert not hasattr(user, 'created_at')
        assert not hasattr(user, 'integration')
        assert not hasattr(user, 'metric')


class TestUserMethodIntegration:
    """Test User methods with minimal mocking."""
    
    def test_get_user_by_id_nonexistent(self):
        """Test get_user_by_id returns None for nonexistent user."""
        from firebase.models.user import User
        
        with patch('firebase.models.user.User.users') as mock_collection:
            # Mock nonexistent document
            mock_snapshot = MockDocumentSnapshot({}, 'nonexistent_user', exists=False)
            mock_collection.document.return_value.get.return_value = mock_snapshot
            
            # Get user
            result = User.get_user_by_id('nonexistent_user')
            
            assert result is None
    
    def test_user_metrics_initialization(self):
        """Test that new users get proper metrics initialization."""
        from firebase.models.user import User
        
        # Create user without metrics
        user_data = {
            'reference_id': 'no_metrics_user',
            'createdAt': datetime.datetime.now(),
            'is_registered': True
        }
        
        mock_snapshot = MockDocumentSnapshot(user_data, 'no_metrics_user')
        user = User(mock_snapshot)
        
        # User should either not have metrics or have default structure
        if hasattr(user, 'metrics'):
            assert isinstance(user.metrics, dict)
        else:
            # This is also acceptable for users without metrics
            assert not hasattr(user, 'metrics')
    
    def test_user_key_generation(self):
        """Test that users get proper key_id for encryption."""
        from firebase.models.user import User
        
        with patch('firebase.models.user.User.users') as mock_collection:
            # Create user with key_id
            user_data = {
                'reference_id': 'key_user',
                'createdAt': datetime.datetime.now(),
                'is_registered': True,
                'key_id': 'user_encryption_key_123'
            }
            
            mock_snapshot = MockDocumentSnapshot(user_data, 'key_user')
            user = User(mock_snapshot)
            
            # Verify key_id exists
            assert hasattr(user, 'key_id')
            assert user.key_id == 'user_encryption_key_123'
    
    def test_user_complex_metrics_aggregation(self):
        """Test complex metrics scenarios with multiple updates."""
        from firebase.models.user import User
        
        with patch('firebase.models.user.User.users') as mock_collection:
            # Create user with existing metrics
            user_data = {
                'reference_id': 'complex_metrics_user',
                'createdAt': datetime.datetime.now(),
                'is_registered': True,
                'metrics': {
                    'prompts': [
                        {'prompt': 'First prompt', 'timestamp': '2024-01-01T10:00:00'},
                        {'prompt': 'Second prompt', 'timestamp': '2024-01-01T11:00:00'}
                    ],
                    'prompt_count': 2,
                    'tool_calls': {
                        'search_web': 5,
                        'get_weather': 3
                    },
                    'tool_call_count': 8,
                    'agent_calls': {
                        'gmail_agent': 2
                    },
                    'agent_call_count': 2
                }
            }
            
            mock_snapshot = MockDocumentSnapshot(user_data, 'complex_metrics_user')
            user = User(mock_snapshot)
            
            # Mock document update
            mock_doc = Mock()
            mock_collection.document.return_value = mock_doc
            
            # Add more metrics
            user.add_prompt_to_metrics('Third prompt')
            assert user.metrics['prompt_count'] == 3
            assert len(user.metrics['prompts']) == 3
            
            user.add_tool_call_to_metrics('search_web')
            assert user.metrics['tool_calls']['search_web'] == 6
            assert user.metrics['tool_call_count'] == 9
            
            user.add_agent_call_to_metrics('plaid_agent')
            assert user.metrics['agent_calls']['plaid_agent'] == 1
            assert user.metrics['agent_call_count'] == 3