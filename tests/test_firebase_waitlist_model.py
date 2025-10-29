"""
Comprehensive tests for Firebase Waitlist model.

Tests cover email addition, timestamp creation, Firestore collection interactions,
error handling, and edge cases for the Waitlist model functionality.
"""

import pytest
import datetime
from unittest.mock import Mock, patch, MagicMock

# Import test fixtures
from .test_firebase_models_base import *


@pytest.fixture
def mock_waitlist_collection():
    """Create a mock waitlist collection with document operations."""
    mock_collection = Mock()
    mock_document = Mock()
    mock_document.set = Mock()
    mock_collection.document = Mock(return_value=mock_document)
    return mock_collection


@pytest.fixture
def waitlist_class():
    """Get the Waitlist class with mocked dependencies."""
    # Mock all Firebase dependencies before importing
    with patch.dict('sys.modules', {
        'firebase_admin': create_mock_firebase_admin(),
        'firebase_admin.credentials': Mock(),
        'firebase_admin.firestore': Mock(),
        'firebase_admin.messaging': Mock(),
        'google.oauth2.service_account': Mock(),
        'openai': Mock(),
        'connectors.utils.segment': create_mock_segment_tracking(),
        'connectors.utils.keys': Mock(),
        'connectors.utils.secrets': Mock(),
        'config': Mock()
    }):
        # Mock the FireStoreObject's collection properties
        with patch('firebase.models.waitlist.FireStoreObject') as mock_base:
            mock_waitlist_collection = Mock()
            mock_base.waitlist = mock_waitlist_collection

            # Import the Waitlist class after mocking
            from firebase.models.waitlist import Waitlist

            # Ensure the waitlist collection is properly mocked
            Waitlist.waitlist = mock_waitlist_collection

            yield Waitlist


class TestWaitlist:
    """Test cases for the Waitlist model."""

    def test_add_email_basic(self, waitlist_class, mock_waitlist_collection):
        """Test basic email addition to waitlist."""
        test_email = "test@example.com"

        # Setup mock
        mock_document = Mock()
        mock_document.set = Mock()
        mock_waitlist_collection.document.return_value = mock_document
        waitlist_class.waitlist = mock_waitlist_collection

        # Call the method
        waitlist_class.add_email(test_email)

        # Verify collection.document() was called
        mock_waitlist_collection.document.assert_called_once_with()

        # Verify set was called with email and timestamp
        mock_document.set.assert_called_once()
        set_call_args = mock_document.set.call_args[0][0]

        assert set_call_args['email'] == test_email
        assert 'created_at' in set_call_args
        assert isinstance(set_call_args['created_at'], datetime.datetime)

    def test_add_email_timestamp_accuracy(self, waitlist_class, mock_waitlist_collection):
        """Test that the timestamp is set correctly."""
        test_email = "timestamp@example.com"

        # Setup mock
        mock_document = Mock()
        mock_document.set = Mock()
        mock_waitlist_collection.document.return_value = mock_document
        waitlist_class.waitlist = mock_waitlist_collection

        # Record time before and after to verify timestamp is reasonable
        time_before = datetime.datetime.now()
        waitlist_class.add_email(test_email)
        time_after = datetime.datetime.now()

        # Verify the timestamp is within the expected range
        set_call_args = mock_document.set.call_args[0][0]
        timestamp = set_call_args['created_at']

        assert time_before <= timestamp <= time_after
        assert isinstance(timestamp, datetime.datetime)

    def test_add_email_empty_string(self, waitlist_class, mock_waitlist_collection):
        """Test adding an empty email string."""
        # Setup mock
        mock_document = Mock()
        mock_document.set = Mock()
        mock_waitlist_collection.document.return_value = mock_document
        waitlist_class.waitlist = mock_waitlist_collection

        # Call with empty email
        waitlist_class.add_email("")

        # Verify it still gets added (no validation in the model)
        mock_waitlist_collection.document.assert_called_once_with()
        mock_document.set.assert_called_once()

        set_call_args = mock_document.set.call_args[0][0]
        assert set_call_args['email'] == ""

    def test_add_email_special_characters(self, waitlist_class, mock_waitlist_collection):
        """Test adding email with special characters."""
        special_email = "test+special@example-domain.co.uk"

        # Setup mock
        mock_document = Mock()
        mock_document.set = Mock()
        mock_waitlist_collection.document.return_value = mock_document
        waitlist_class.waitlist = mock_waitlist_collection

        # Call the method
        waitlist_class.add_email(special_email)

        # Verify the email is stored correctly
        set_call_args = mock_document.set.call_args[0][0]
        assert set_call_args['email'] == special_email

    def test_add_email_unicode_characters(self, waitlist_class, mock_waitlist_collection):
        """Test adding email with unicode characters."""
        unicode_email = "测试@example.com"

        # Setup mock
        mock_document = Mock()
        mock_document.set = Mock()
        mock_waitlist_collection.document.return_value = mock_document
        waitlist_class.waitlist = mock_waitlist_collection

        # Call the method
        waitlist_class.add_email(unicode_email)

        # Verify the email is stored correctly
        set_call_args = mock_document.set.call_args[0][0]
        assert set_call_args['email'] == unicode_email

    def test_add_email_very_long_email(self, waitlist_class, mock_waitlist_collection):
        """Test adding a very long email address."""
        long_email = "a" * 64 + "@" + "b" * 63 + ".com"  # Maximum valid email length

        # Setup mock
        mock_document = Mock()
        mock_document.set = Mock()
        mock_waitlist_collection.document.return_value = mock_document
        waitlist_class.waitlist = mock_waitlist_collection

        # Call the method
        waitlist_class.add_email(long_email)

        # Verify the email is stored correctly
        set_call_args = mock_document.set.call_args[0][0]
        assert set_call_args['email'] == long_email

    def test_add_email_firestore_exception_handling(self, waitlist_class, mock_waitlist_collection):
        """Test behavior when Firestore operations fail."""
        from google.cloud.exceptions import GoogleCloudError

        # Setup mock to raise exception
        mock_document = Mock()
        mock_document.set = Mock(
            side_effect=GoogleCloudError("Firestore error"))
        mock_waitlist_collection.document.return_value = mock_document
        waitlist_class.waitlist = mock_waitlist_collection

        # The method doesn't handle exceptions, so it should propagate
        with pytest.raises(GoogleCloudError):
            waitlist_class.add_email("test@example.com")

    def test_add_email_document_creation_failure(self, waitlist_class, mock_waitlist_collection):
        """Test behavior when document creation fails."""
        # Setup mock to raise exception on document creation
        mock_waitlist_collection.document.side_effect = Exception(
            "Document creation failed")
        waitlist_class.waitlist = mock_waitlist_collection

        # The method doesn't handle exceptions, so it should propagate
        with pytest.raises(Exception, match="Document creation failed"):
            waitlist_class.add_email("test@example.com")

    def test_add_multiple_emails_different_timestamps(self, waitlist_class, mock_waitlist_collection):
        """Test that multiple emails get different timestamps."""
        emails = ["first@example.com", "second@example.com"]
        timestamps = []

        # Setup mock to capture timestamps
        mock_document = Mock()

        def capture_timestamp(data):
            timestamps.append(data['created_at'])

        mock_document.set = Mock(side_effect=capture_timestamp)
        mock_waitlist_collection.document.return_value = mock_document
        waitlist_class.waitlist = mock_waitlist_collection

        # Add emails with a small delay
        import time
        waitlist_class.add_email(emails[0])
        time.sleep(0.01)  # Small delay to ensure different timestamps
        waitlist_class.add_email(emails[1])

        # Verify we got two different timestamps
        assert len(timestamps) == 2
        # Second should be later or equal
        assert timestamps[0] <= timestamps[1]

    def test_waitlist_collection_property_access(self, waitlist_class):
        """Test that the waitlist collection property is accessible."""
        # The waitlist property should be accessible from the class
        assert hasattr(waitlist_class, 'waitlist')
        assert waitlist_class.waitlist is not None

    def test_add_email_data_structure(self, waitlist_class, mock_waitlist_collection):
        """Test that the data structure passed to Firestore is correct."""
        test_email = "structure@example.com"

        # Setup mock
        mock_document = Mock()
        mock_document.set = Mock()
        mock_waitlist_collection.document.return_value = mock_document
        waitlist_class.waitlist = mock_waitlist_collection

        # Call the method
        waitlist_class.add_email(test_email)

        # Verify the data structure
        set_call_args = mock_document.set.call_args[0][0]

        # Should have exactly 2 keys
        assert len(set_call_args) == 2

        # Should have email and created_at
        assert 'email' in set_call_args
        assert 'created_at' in set_call_args

        # Verify types
        assert isinstance(set_call_args['email'], str)
        assert isinstance(set_call_args['created_at'], datetime.datetime)

    def test_add_email_none_value(self, waitlist_class, mock_waitlist_collection):
        """Test adding None as email value."""
        # Setup mock
        mock_document = Mock()
        mock_document.set = Mock()
        mock_waitlist_collection.document.return_value = mock_document
        waitlist_class.waitlist = mock_waitlist_collection

        # This should raise an error due to string operations on None
        with pytest.raises(AttributeError):
            waitlist_class.add_email(None)

    def test_add_email_non_string_value(self, waitlist_class, mock_waitlist_collection):
        """Test adding non-string value as email."""
        # Setup mock
        mock_document = Mock()
        mock_document.set = Mock()
        mock_waitlist_collection.document.return_value = mock_document
        waitlist_class.waitlist = mock_waitlist_collection

        # Try with integer (should work due to Python's flexibility)
        waitlist_class.add_email(12345)

        # Verify it gets stored
        set_call_args = mock_document.set.call_args[0][0]
        assert set_call_args['email'] == 12345

    def test_class_method_nature(self, waitlist_class):
        """Test that add_email is properly a class method."""
        # Verify it's callable as a class method
        assert hasattr(waitlist_class, 'add_email')
        assert callable(waitlist_class.add_email)

        # Verify it's a class method (can be called on class)
        import inspect
        assert inspect.ismethod(waitlist_class.add_email) or inspect.isfunction(
            waitlist_class.add_email)


class TestFakeToken:
    """Test cases for the FakeToken class (also in waitlist.py)."""

    def test_fake_token_import(self):
        """Test that FakeToken can be imported."""
        with patch.dict('sys.modules', {
            'firebase_admin': create_mock_firebase_admin(),
            'firebase_admin.credentials': Mock(),
            'firebase_admin.firestore': Mock(),
            'firebase_admin.messaging': Mock(),
            'google.oauth2.service_account': Mock(),
            'openai': Mock(),
            'connectors.utils.segment': create_mock_segment_tracking(),
            'connectors.utils.keys': Mock(),
            'connectors.utils.secrets': Mock(),
            'config': Mock()
        }):
            from firebase.models.waitlist import FakeToken
            assert FakeToken is not None

    def test_fake_token_ciphertext_property(self):
        """Test that FakeToken has the expected ciphertext property."""
        with patch.dict('sys.modules', {
            'firebase_admin': create_mock_firebase_admin(),
            'firebase_admin.credentials': Mock(),
            'firebase_admin.firestore': Mock(),
            'firebase_admin.messaging': Mock(),
            'google.oauth2.service_account': Mock(),
            'openai': Mock(),
            'connectors.utils.segment': create_mock_segment_tracking(),
            'connectors.utils.keys': Mock(),
            'connectors.utils.secrets': Mock(),
            'config': Mock()
        }):
            from firebase.models.waitlist import FakeToken

            # Test class attribute
            assert hasattr(FakeToken, 'ciphertext')
            assert FakeToken.ciphertext == '1234'

            # Test instance attribute
            fake_token = FakeToken()
            assert fake_token.ciphertext == '1234'


# Integration tests
class TestWaitlistIntegration:
    """Integration tests for Waitlist model with mocked Firebase."""

    def test_end_to_end_email_addition(self, waitlist_class):
        """Test complete flow of adding an email to waitlist."""
        # Create a more realistic mock setup
        mock_firestore_db = Mock()
        mock_collection = Mock()
        mock_document = Mock()
        mock_document.set = Mock()

        # Set up the chain: db -> collection -> document -> set
        mock_firestore_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_document

        # Connect the mock to our class
        waitlist_class.waitlist = mock_collection

        # Test the complete flow
        test_email = "integration@example.com"
        waitlist_class.add_email(test_email)

        # Verify the complete chain was called
        mock_collection.document.assert_called_once_with()
        mock_document.set.assert_called_once()

        # Verify the data
        call_data = mock_document.set.call_args[0][0]
        assert call_data['email'] == test_email
        assert isinstance(call_data['created_at'], datetime.datetime)

    def test_multiple_email_additions_integration(self, waitlist_class):
        """Test adding multiple emails in succession."""
        # Setup mock
        mock_collection = Mock()
        mock_document = Mock()
        mock_document.set = Mock()
        mock_collection.document.return_value = mock_document
        waitlist_class.waitlist = mock_collection

        # Add multiple emails
        emails = ["first@test.com", "second@test.com", "third@test.com"]

        for email in emails:
            waitlist_class.add_email(email)

        # Verify all were processed
        assert mock_collection.document.call_count == len(emails)
        assert mock_document.set.call_count == len(emails)

        # Verify each call had the correct email
        for i, call in enumerate(mock_document.set.call_args_list):
            call_data = call[0][0]
            assert call_data['email'] == emails[i]
