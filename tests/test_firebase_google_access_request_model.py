"""
Comprehensive tests for firebase/models/google_access_request.py

Tests cover the GoogleAccessRequest model for managing Google service
access requests in Firestore.
"""

import pytest
import datetime
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from google.cloud.firestore_v1.base_query import FieldFilter


class TestGoogleAccessRequestModel:
    """Test cases for GoogleAccessRequest model."""

    @pytest.fixture
    def mock_firestore_doc(self):
        """Create a mock Firestore document."""
        mock_doc = Mock()
        mock_doc.reference = Mock()
        mock_doc.reference.id = "test_request_id"
        mock_doc.to_dict.return_value = {
            'email': 'test@example.com',
            'created_at': datetime.datetime.now(),
            'user_id': 'test_user_123'
        }
        return mock_doc

    def test_google_access_request_initialization(self, mock_firestore_doc):
        """Test GoogleAccessRequest initialization."""
        from firebase.models.google_access_request import GoogleAccessRequest
        
        # Create instance
        request = GoogleAccessRequest(mock_firestore_doc)
        
        # Verify attributes are set correctly
        assert request.reference_id == "test_request_id"
        assert request.email == 'test@example.com'
        assert hasattr(request, 'created_at')
        assert hasattr(request, 'user_id')
        assert request.user_id == 'test_user_123'
        
        # Verify the document reference is stored
        assert request._GoogleAccessRequest__media_object == mock_firestore_doc

    def test_google_access_request_inherits_from_firestore_object(self, mock_firestore_doc):
        """Test that GoogleAccessRequest inherits from FireStoreObject."""
        from firebase.models.google_access_request import GoogleAccessRequest
        from firebase.base import FireStoreObject
        
        request = GoogleAccessRequest(mock_firestore_doc)
        
        # Should be instance of FireStoreObject
        assert isinstance(request, FireStoreObject)

    def test_google_access_request_dynamic_attributes(self, mock_firestore_doc):
        """Test that GoogleAccessRequest sets attributes dynamically from document."""
        # Add custom attributes to mock document
        mock_firestore_doc.to_dict.return_value = {
            'email': 'custom@example.com',
            'created_at': datetime.datetime(2024, 1, 1),
            'user_id': 'custom_user',
            'custom_field': 'custom_value',
            'another_field': 42
        }
        
        from firebase.models.google_access_request import GoogleAccessRequest
        
        request = GoogleAccessRequest(mock_firestore_doc)
        
        # All fields should be set as attributes
        assert request.email == 'custom@example.com'
        assert request.created_at == datetime.datetime(2024, 1, 1)
        assert request.user_id == 'custom_user'
        assert request.custom_field == 'custom_value'
        assert request.another_field == 42

    @patch('firebase.models.google_access_request.GoogleAccessRequest.google_access_requests')
    def test_create_request_success(self, mock_collection):
        """Test successful creation of a new request."""
        from firebase.models.google_access_request import GoogleAccessRequest
        
        # Mock the where query to return no existing requests
        mock_where = Mock()
        mock_where.get.return_value = []  # No existing requests
        mock_collection.where.return_value = mock_where
        
        # Mock document creation
        mock_doc_ref = Mock()
        mock_collection.document.return_value = mock_doc_ref
        
        # Mock user
        mock_user = Mock()
        mock_user.reference_id = "user_123"
        
        # Create request
        result = GoogleAccessRequest.create_request(mock_user, "new@example.com")
        
        # Should return True
        assert result == True
        
        # Verify collection was queried for existing request
        mock_collection.where.assert_called_once()
        filter_arg = mock_collection.where.call_args[1]['filter']
        assert isinstance(filter_arg, FieldFilter)
        assert filter_arg.field_path == 'user_id'
        assert filter_arg.op_string == '=='
        assert filter_arg.value == 'user_123'
        
        # Verify document was created with correct data
        mock_doc_ref.set.assert_called_once()
        set_data = mock_doc_ref.set.call_args[0][0]
        assert set_data['email'] == 'new@example.com'
        assert set_data['user_id'] == 'user_123'
        assert 'created_at' in set_data
        assert isinstance(set_data['created_at'], datetime.datetime)

    @patch('firebase.models.google_access_request.GoogleAccessRequest.google_access_requests')
    def test_create_request_already_exists(self, mock_collection):
        """Test creation when request already exists."""
        from firebase.models.google_access_request import GoogleAccessRequest
        
        # Mock the where query to return an existing request
        mock_where = Mock()
        mock_where.get.return_value = [Mock()]  # Existing request found
        mock_collection.where.return_value = mock_where
        
        # Mock user
        mock_user = Mock()
        mock_user.reference_id = "user_123"
        
        # Should return True without creating a new document
        result = GoogleAccessRequest.create_request(mock_user, "existing@example.com")
        
        assert result == True
        
        # Verify collection was queried but no document was created
        mock_collection.where.assert_called_once()
        mock_collection.document.assert_not_called()

    @patch('firebase.models.google_access_request.GoogleAccessRequest.google_access_requests')
    def test_get_request_for_user_found(self, mock_collection):
        """Test getting request for a user when it exists."""
        from firebase.models.google_access_request import GoogleAccessRequest
        
        # Mock the where query to return a request
        mock_request_doc = Mock()
        mock_where = Mock()
        mock_where.get.return_value = [mock_request_doc]
        mock_collection.where.return_value = mock_where
        
        # Get request
        result = GoogleAccessRequest.get_request_for_user("user_123")
        
        # Should return the first request
        assert result == mock_request_doc
        
        # Verify collection was queried correctly
        mock_collection.where.assert_called_once()
        filter_arg = mock_collection.where.call_args[1]['filter']
        assert isinstance(filter_arg, FieldFilter)
        assert filter_arg.field_path == 'user_id'
        assert filter_arg.op_string == '=='
        assert filter_arg.value == 'user_123'

    @patch('firebase.models.google_access_request.GoogleAccessRequest.google_access_requests')
    def test_get_request_for_user_not_found(self, mock_collection):
        """Test getting request for a user when none exists."""
        from firebase.models.google_access_request import GoogleAccessRequest
        
        # Mock the where query to return no requests
        mock_where = Mock()
        mock_where.get.return_value = []
        mock_collection.where.return_value = mock_where
        
        # Get request
        result = GoogleAccessRequest.get_request_for_user("user_456")
        
        # Should return None
        assert result is None
        
        # Verify collection was queried correctly
        mock_collection.where.assert_called_once()

    @patch('firebase.models.google_access_request.GoogleAccessRequest.google_access_requests')
    def test_get_request_for_user_multiple_requests(self, mock_collection):
        """Test getting request when multiple exist (returns first)."""
        from firebase.models.google_access_request import GoogleAccessRequest
        
        # Mock the where query to return multiple requests
        mock_request1 = Mock()
        mock_request2 = Mock()
        mock_request3 = Mock()
        mock_where = Mock()
        mock_where.get.return_value = [mock_request1, mock_request2, mock_request3]
        mock_collection.where.return_value = mock_where
        
        # Get request
        result = GoogleAccessRequest.get_request_for_user("user_789")
        
        # Should return the first request
        assert result == mock_request1

    def test_google_access_request_imports(self):
        """Test that imports work correctly."""
        try:
            from firebase.models.google_access_request import (
                GoogleAccessRequest,
                datetime,
                json,
                base64,
                FieldFilter,
                FireStoreObject,
                SETTINGS,
                keys,
                User
            )
            # All imports should succeed
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import from google_access_request: {e}")

    @patch('firebase.models.google_access_request.GoogleAccessRequest.google_access_requests')
    def test_create_request_with_different_emails(self, mock_collection):
        """Test creating requests with various email formats."""
        from firebase.models.google_access_request import GoogleAccessRequest
        
        # Mock successful creation
        mock_where = Mock()
        mock_where.get.return_value = []
        mock_collection.where.return_value = mock_where
        mock_doc_ref = Mock()
        mock_collection.document.return_value = mock_doc_ref
        
        mock_user = Mock()
        mock_user.reference_id = "user_123"
        
        # Test various email formats
        test_emails = [
            "simple@example.com",
            "user.name@example.com",
            "user+tag@example.com",
            "user@subdomain.example.com",
            "unicode@测试.com",
            ""  # Empty email
        ]
        
        for email in test_emails:
            mock_collection.reset_mock()
            mock_doc_ref.reset_mock()
            
            result = GoogleAccessRequest.create_request(mock_user, email)
            assert result == True
            
            # Verify user_id was used in query and email in document
            filter_arg = mock_collection.where.call_args[1]['filter']
            assert filter_arg.value == 'user_123'
            
            set_data = mock_doc_ref.set.call_args[0][0]
            assert set_data['email'] == email

    @patch('firebase.models.google_access_request.GoogleAccessRequest.google_access_requests')
    def test_create_request_timestamp_precision(self, mock_collection):
        """Test that created_at timestamp is set correctly."""
        from firebase.models.google_access_request import GoogleAccessRequest
        
        # Mock successful creation
        mock_where = Mock()
        mock_where.get.return_value = []
        mock_collection.where.return_value = mock_where
        mock_doc_ref = Mock()
        mock_collection.document.return_value = mock_doc_ref
        
        mock_user = Mock()
        mock_user.reference_id = "user_123"
        
        # Capture time before and after
        time_before = datetime.datetime.now()
        result = GoogleAccessRequest.create_request(mock_user, "timing@example.com")
        time_after = datetime.datetime.now()
        
        # Get the created_at value
        set_data = mock_doc_ref.set.call_args[0][0]
        created_at = set_data['created_at']
        
        # Verify timestamp is within expected range
        assert isinstance(created_at, datetime.datetime)
        assert time_before <= created_at <= time_after

    def test_google_access_request_collection_reference(self):
        """Test that google_access_requests collection is properly defined."""
        from firebase.models.google_access_request import GoogleAccessRequest
        
        # Should have google_access_requests collection reference
        assert hasattr(GoogleAccessRequest, 'google_access_requests')
        
        # Should be accessible from the class
        assert GoogleAccessRequest.google_access_requests is not None


class TestGoogleAccessRequestIntegration:
    """Integration tests for GoogleAccessRequest model."""

    @patch('firebase.base.DB')
    def test_collection_reference_from_base(self, mock_db):
        """Test that collection reference comes from FireStoreObject base."""
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        
        # Re-import to get fresh class with mocked DB
        import importlib
        import firebase.base
        importlib.reload(firebase.base)
        
        from firebase.models.google_access_request import GoogleAccessRequest
        
        # The collection should be defined in base
        assert hasattr(GoogleAccessRequest, 'google_access_requests')

    def test_model_workflow(self):
        """Test complete workflow of creating and retrieving requests."""
        from firebase.models.google_access_request import GoogleAccessRequest
        
        with patch.object(GoogleAccessRequest, 'google_access_requests') as mock_collection:
            # Setup mocks for the workflow
            mock_where = Mock()
            mock_collection.where.return_value = mock_where
            mock_doc_ref = Mock()
            mock_collection.document.return_value = mock_doc_ref
            
            # Step 1: Check for existing request (none found)
            mock_where.get.return_value = []
            mock_user = Mock(reference_id="workflow_user")
            
            result = GoogleAccessRequest.get_request_for_user("workflow_user")
            assert result is None
            
            # Step 2: Create new request
            mock_where.get.return_value = []  # Still no existing
            created = GoogleAccessRequest.create_request(mock_user, "workflow@example.com")
            assert created == True
            
            # Step 3: Check again (now found)
            mock_request_doc = Mock()
            mock_where.get.return_value = [mock_request_doc]
            
            result = GoogleAccessRequest.get_request_for_user("workflow_user")
            assert result == mock_request_doc

    @patch('firebase.models.google_access_request.GoogleAccessRequest.google_access_requests')
    def test_error_handling_scenarios(self, mock_collection):
        """Test various error handling scenarios."""
        from firebase.models.google_access_request import GoogleAccessRequest
        
        # Setup mock to handle the where query
        mock_where = Mock()
        mock_where.get.return_value = []  # Empty list for len() check
        mock_collection.where.return_value = mock_where
        
        # Test with None user - should raise AttributeError when accessing user.reference_id
        with pytest.raises(AttributeError):
            GoogleAccessRequest.create_request(None, "test@example.com")
        
        # Test with user missing reference_id
        mock_user = Mock(spec=[])  # No attributes
        with pytest.raises(AttributeError):
            GoogleAccessRequest.create_request(mock_user, "test@example.com")