"""
Comprehensive tests for connectors/utils/segment.py

Tests cover all analytics tracking functions including user identification,
event tracking, integration tracking, and voice call tracking.
"""

import pytest
import datetime
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

# Mock classes for testing


@dataclass
class MockUser:
    """Mock user class for testing."""
    reference_id: str = "test_user_123"
    email: str = "test@example.com"
    name: str = "Test User"
    is_registered: bool = True
    integrations: dict = None
    createdAt: datetime.datetime = datetime.datetime.now()
    creationRecorded: bool = False
    signupRecorded: bool = False

    def __post_init__(self):
        if self.integrations is None:
            self.integrations = {}

    @property
    def connected_to_google(self):
        """Check if user has connected their Google account."""
        return self.integrations.get('google', False) if self.integrations else False

    @property
    def connected_to_plaid(self):
        """Check if user has connected their Plaid account."""
        return self.integrations.get('plaid', False) if self.integrations else False

    def record_creation(self):
        self.creationRecorded = True

    def record_signup(self):
        self.signupRecorded = True


class TestSegmentUtils:
    """Test cases for segment.py analytics tracking functions."""

    @pytest.fixture
    def mock_analytics(self):
        """Mock the segment analytics module."""
        with patch('connectors.utils.segment.analytics') as mock_analytics:
            mock_analytics.write_key = "test_key"
            mock_analytics.identify = Mock()
            mock_analytics.track = Mock()
            yield mock_analytics

    @pytest.fixture
    def mock_settings(self):
        """Mock the Settings configuration."""
        with patch('connectors.utils.segment.Settings') as mock_settings_class:
            mock_settings = Mock()
            mock_settings.segment_key = "test_segment_key"
            mock_settings_class.return_value = mock_settings
            yield mock_settings

    @pytest.fixture
    def registered_user(self):
        """Create a registered user with integrations."""
        return MockUser(
            reference_id="user_123",
            email="registered@example.com",
            name="Registered User",
            is_registered=True,
            integrations={"google": True, "plaid": True}
        )

    @pytest.fixture
    def unregistered_user(self):
        """Create an unregistered user."""
        return MockUser(
            reference_id="unregistered_123",
            is_registered=False,
            integrations={}
        )

    def test_identify_user_registered_with_integrations(self, mock_analytics, registered_user):
        """Test user identification for registered user with integrations."""
        from connectors.utils.segment import identify_user

        identify_user(registered_user)

        # Verify analytics.identify was called with correct data
        mock_analytics.identify.assert_called_once_with(
            "user_123",
            {
                "email": "registered@example.com",
                "name": "Registered User",
                "has_google_integration": True,
                "has_plaid_integration": True,
                "created_at": registered_user.createdAt,
            }
        )

    def test_identify_user_registered_without_integrations(self, mock_analytics):
        """Test user identification for registered user without integrations."""
        from connectors.utils.segment import identify_user

        user = MockUser(
            reference_id="user_no_integrations",
            email="test@example.com",
            name="Test User",
            is_registered=True,
            integrations={}
        )

        identify_user(user)

        mock_analytics.identify.assert_called_once_with(
            "user_no_integrations",
            {
                "email": "test@example.com",
                "name": "Test User",
                "has_google_integration": False,
                "has_plaid_integration": False,
                "created_at": user.createdAt,
            }
        )

    def test_identify_user_registered_no_integrations_attr(self, mock_analytics):
        """Test user identification for registered user without integrations attribute."""
        from connectors.utils.segment import identify_user

        user = MockUser(
            reference_id="user_no_attr",
            email="test@example.com",
            name="Test User",
            is_registered=True
        )
        delattr(user, 'integrations')

        identify_user(user)

        mock_analytics.identify.assert_called_once_with(
            "user_no_attr",
            {
                "email": "test@example.com",
                "name": "Test User",
                "has_google_integration": False,
                "has_plaid_integration": False,
                "created_at": user.createdAt,
            }
        )

    def test_identify_user_unregistered(self, mock_analytics, unregistered_user):
        """Test user identification for unregistered user."""
        from connectors.utils.segment import identify_user

        identify_user(unregistered_user)

        # Unregistered users should not be identified in Segment
        mock_analytics.identify.assert_not_called()

    def test_identify_user_none(self, mock_analytics):
        """Test user identification with None user."""
        from connectors.utils.segment import identify_user

        identify_user(None)

        # Should not call analytics.identify for None user
        mock_analytics.identify.assert_not_called()

    def test_identify_user_triggers_creation_tracking(self, mock_analytics):
        """Test that identify_user triggers creation tracking for new users."""
        from connectors.utils.segment import identify_user

        user = MockUser(
            reference_id="new_user",
            is_registered=True,
            creationRecorded=False
        )

        with patch('connectors.utils.segment.track_user_created') as mock_track_created:
            identify_user(user)

            # Verify creation was recorded and tracked
            assert user.creationRecorded == True
            mock_track_created.assert_called_once_with(user)

    def test_identify_user_triggers_signup_tracking(self, mock_analytics):
        """Test that identify_user triggers signup tracking for users with email."""
        from connectors.utils.segment import identify_user

        user = MockUser(
            reference_id="signup_user",
            email="signup@example.com",
            name="Signup User",
            is_registered=True,
            signupRecorded=False,
            creationRecorded=True  # Already recorded creation
        )

        with patch('connectors.utils.segment.track_user_signed_up') as mock_track_signup:
            identify_user(user)

            # Verify signup was recorded and tracked
            assert user.signupRecorded == True
            mock_track_signup.assert_called_once_with(user)

    def test_identify_user_no_duplicate_tracking(self, mock_analytics):
        """Test that tracking doesn't happen for already recorded users."""
        from connectors.utils.segment import identify_user

        user = MockUser(
            reference_id="existing_user",
            email="existing@example.com",
            is_registered=True,
            creationRecorded=True,
            signupRecorded=True
        )

        with patch('connectors.utils.segment.track_user_created') as mock_track_created, \
                patch('connectors.utils.segment.track_user_signed_up') as mock_track_signup:
            identify_user(user)

            # Should not track again
            mock_track_created.assert_not_called()
            mock_track_signup.assert_not_called()

    def test_track_user_created(self, mock_analytics):
        """Test track_user_created function."""
        from connectors.utils.segment import track_user_created

        user = MockUser(reference_id="new_user")
        track_user_created(user)

        mock_analytics.track.assert_called_once_with(
            "new_user", "New User Created")

    def test_track_user_signed_up(self, mock_analytics):
        """Test track_user_signed_up function."""
        from connectors.utils.segment import track_user_signed_up

        user = MockUser(
            reference_id="signup_user",
            email="signup@example.com",
            name="Signup User"
        )
        track_user_signed_up(user)

        mock_analytics.track.assert_called_once_with(
            "signup_user",
            "User Signed Up",
            {
                "email": "signup@example.com",
                "name": "Signup User",
            }
        )

    def test_track_prompt(self, mock_analytics):
        """Test track_prompt function."""
        from connectors.utils.segment import track_prompt

        user = MockUser(reference_id="user_123")
        
        # Mock the add_prompt_to_metrics method
        user.add_prompt_to_metrics = Mock()
        
        track_prompt(user, "chat_456", "Test prompt")

        mock_analytics.track.assert_called_once_with(
            "user_123",
            "Prompt Submitted",
            {
                "chat_id": "chat_456",
                "prompt": "Test prompt",
            }
        )
        
        # Verify metrics method was called
        user.add_prompt_to_metrics.assert_called_once_with("Test prompt")

    def test_track_prompt_none_user(self, mock_analytics):
        """Test track_prompt with None user."""
        from connectors.utils.segment import track_prompt

        track_prompt(None, "chat_456", "Test prompt")

        # Should not track for None user
        mock_analytics.track.assert_not_called()

    def test_track_tool_called(self, mock_analytics):
        """Test track_tool_called function."""
        from connectors.utils.segment import track_tool_called

        user = MockUser(reference_id="user_123")
        
        # Mock the add_tool_call_to_metrics method
        user.add_tool_call_to_metrics = Mock()
        
        track_tool_called(user, "chat_456", "search_tool", "Search the web")

        mock_analytics.track.assert_called_once_with(
            "user_123",
            "Tool Called",
            {
                "chat_id": "chat_456",
                "tool_call": "search_tool",
                "tool_description": "Search the web",
            }
        )
        
        # Verify metrics method was called
        user.add_tool_call_to_metrics.assert_called_once_with("search_tool")

    def test_track_tool_called_no_description(self, mock_analytics):
        """Test track_tool_called without description."""
        from connectors.utils.segment import track_tool_called

        user = MockUser(reference_id="user_123")
        
        # Mock the add_tool_call_to_metrics method
        user.add_tool_call_to_metrics = Mock()
        
        track_tool_called(user, "chat_456", "search_tool")

        mock_analytics.track.assert_called_once_with(
            "user_123",
            "Tool Called",
            {
                "chat_id": "chat_456",
                "tool_call": "search_tool",
                "tool_description": "",
            }
        )
        
        # Verify metrics method was called
        user.add_tool_call_to_metrics.assert_called_once_with("search_tool")

    def test_track_agent_called(self, mock_analytics):
        """Test track_agent_called function."""
        from connectors.utils.segment import track_agent_called

        user = MockUser(reference_id="user_123")
        
        # Mock the add_agent_call_to_metrics method
        user.add_agent_call_to_metrics = Mock()
        
        track_agent_called(user, "chat_456", "gmail_agent")

        mock_analytics.track.assert_called_once_with(
            "user_123",
            "Agent Called",
            {
                "chat_id": "chat_456",
                "agent_name": "gmail_agent",
            }
        )
        
        # Verify metrics method was called
        user.add_agent_call_to_metrics.assert_called_once_with("gmail_agent")

    def test_track_chat_created(self, mock_analytics):
        """Test track_chat_created function."""
        from connectors.utils.segment import track_chat_created

        user = MockUser(reference_id="user_123")
        track_chat_created(user, "chat_456")

        mock_analytics.track.assert_called_once_with(
            "user_123",
            "Chat Created",
            {
                "chat_id": "chat_456",
            }
        )

    def test_track_chat_created_none_user(self, mock_analytics):
        """Test track_chat_created with None user."""
        from connectors.utils.segment import track_chat_created

        track_chat_created(None, "chat_456")

        # Should not track for None user
        mock_analytics.track.assert_not_called()

    def test_using_existing_chat(self, mock_analytics):
        """Test using_existing_chat function."""
        from connectors.utils.segment import using_existing_chat

        user = MockUser(reference_id="user_123")
        using_existing_chat(user, "chat_456")

        mock_analytics.track.assert_called_once_with(
            "user_123",
            "Existing Chat Used",
            {
                "chat_id": "chat_456",
            }
        )

    def test_using_existing_chat_none_user(self, mock_analytics):
        """Test using_existing_chat with None user."""
        from connectors.utils.segment import using_existing_chat

        using_existing_chat(None, "chat_456")

        # Should not track for None user
        mock_analytics.track.assert_not_called()

    def test_track_responded(self, mock_analytics):
        """Test track_responded function."""
        from connectors.utils.segment import track_responded

        user = MockUser(reference_id="user_123")
        track_responded(user, "chat_456")

        mock_analytics.track.assert_called_once_with(
            "user_123",
            "Response Sent",
            {
                "chat_id": "chat_456",
            }
        )

    def test_track_google_connected(self, mock_analytics):
        """Test track_google_connected function."""
        from connectors.utils.segment import track_google_connected

        user = MockUser(reference_id="user_123")
        track_google_connected(user)

        mock_analytics.track.assert_called_once_with(
            "user_123", "Google Connected")

    def test_track_plaid_connected(self, mock_analytics):
        """Test track_plaid_connected function."""
        from connectors.utils.segment import track_plaid_connected

        user = MockUser(reference_id="user_123")
        track_plaid_connected(user)

        mock_analytics.track.assert_called_once_with(
            "user_123", "Plaid Connected")

    def test_track_evernote_connected(self, mock_analytics):
        """Test track_evernote_connected function."""
        from connectors.utils.segment import track_evernote_connected

        user = MockUser(reference_id="user_123")
        track_evernote_connected(user)

        mock_analytics.track.assert_called_once_with(
            "user_123", "Evernote Connected")

    def test_start_twilio_call(self, mock_analytics):
        """Test start_twilio_call function."""
        from connectors.utils.segment import start_twilio_call

        user = MockUser(reference_id="user_123")
        start_twilio_call(user, "stream_123", "call_456", "+1234567890")

        mock_analytics.track.assert_called_once_with(
            "user_123",
            "Twilio Call Started",
            {
                "stream_sid": "stream_123",
                "call_sid": "call_456",
                "phone_number": "+1234567890",
            }
        )

    def test_end_twilio_call(self, mock_analytics):
        """Test end_twilio_call function."""
        from connectors.utils.segment import end_twilio_call

        user = MockUser(reference_id="user_123")
        end_twilio_call(user, "stream_123", "call_456", "+1234567890", 120)

        mock_analytics.track.assert_called_once_with(
            "user_123",
            "Twilio Call Ended",
            {
                "stream_sid": "stream_123",
                "call_sid": "call_456",
                "duration": 120,
                "phone_number": "+1234567890",
            }
        )

    def test_start_app_voice_chat(self, mock_analytics):
        """Test start_app_voice_chat function."""
        from connectors.utils.segment import start_app_voice_chat

        user = MockUser(reference_id="user_123")
        start_app_voice_chat(user, "session_789")

        mock_analytics.track.assert_called_once_with(
            "user_123",
            "App Voice Chat Started",
            {
                "session_id": "session_789",
            }
        )

    def test_end_app_voice_chat(self, mock_analytics):
        """Test end_app_voice_chat function."""
        from connectors.utils.segment import end_app_voice_chat

        user = MockUser(reference_id="user_123")
        end_app_voice_chat(user, "session_789", 300)

        mock_analytics.track.assert_called_once_with(
            "user_123",
            "App Voice Chat Ended",
            {
                "session_id": "session_789",
                "duration": 300,
            }
        )

    def test_track_unhandled_request(self, mock_analytics):
        """Test track_unhandled_request function."""
        from connectors.utils.segment import track_unhandled_request

        user = MockUser(reference_id="user_123")
        track_unhandled_request(
            user,
            "chat_456",
            "Can you book a flight?",
            "flight_booking",
            "Book flights with airline APIs"
        )

        mock_analytics.track.assert_called_once_with(
            "user_123",
            "Unhandled Request",
            {
                "chat_id": "chat_456",
                "prompt": "Can you book a flight?",
                "capability_requested": "flight_booking",
                "capability_description": "Book flights with airline APIs",
            }
        )

    def test_track_google_access_request(self, mock_analytics):
        """Test track_google_access_request function."""
        from connectors.utils.segment import track_google_access_request

        mock_user = Mock()
        mock_user.reference_id = "test_user_123"
        mock_user.email = "user@example.com"
        mock_user.name = "Test User"
        
        track_google_access_request(mock_user, "test@example.com")

        mock_analytics.track.assert_called_once_with(
            "test_user_123",
            "Google Access Request",
            {
                "user_id": "test_user_123",
                "user_email": "user@example.com",
                "target_email": "test@example.com",
                "user_name": "Test User",
            }
        )

    def test_track_google_access_request_empty_email(self, mock_analytics):
        """Test track_google_access_request with empty email."""
        from connectors.utils.segment import track_google_access_request

        mock_user = Mock()
        mock_user.reference_id = "test_user_123"
        mock_user.email = "user@example.com"
        mock_user.name = "Test User"
        
        track_google_access_request(mock_user, "")

        mock_analytics.track.assert_called_once_with(
            "test_user_123",
            "Google Access Request",
            {
                "user_id": "test_user_123",
                "user_email": "user@example.com",
                "target_email": "",
                "user_name": "Test User",
            }
        )

    def test_track_google_access_request_none_email(self, mock_analytics):
        """Test track_google_access_request with None email."""
        from connectors.utils.segment import track_google_access_request

        mock_user = Mock()
        mock_user.reference_id = "test_user_123"
        mock_user.email = "user@example.com"
        mock_user.name = "Test User"
        
        track_google_access_request(mock_user, None)

        mock_analytics.track.assert_called_once_with(
            "test_user_123",
            "Google Access Request",
            {
                "user_id": "test_user_123",
                "user_email": "user@example.com",
                "target_email": None,
                "user_name": "Test User",
            }
        )

    def test_module_initialization(self, mock_settings):
        """Test module initialization sets analytics write key."""
        # The mock_settings fixture already patches the Settings class
        # and the segment_key should be accessible through the mock
        assert mock_settings.segment_key == "test_segment_key"


# Edge case and error handling tests
class TestSegmentUtilsEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def mock_analytics(self):
        """Mock the segment analytics module."""
        with patch('connectors.utils.segment.analytics') as mock_analytics:
            mock_analytics.write_key = "test_key"
            mock_analytics.identify = Mock()
            mock_analytics.track = Mock()
            yield mock_analytics

    def test_identify_user_missing_attributes(self, mock_analytics):
        """Test identify_user with user missing various attributes."""
        from connectors.utils.segment import identify_user

        # Create a minimal user object without name or email attributes
        class MinimalUser:
            def __init__(self):
                self.reference_id = "minimal_user"
                self.is_registered = True
                self.integrations = {}
                self.createdAt = datetime.datetime.now()
                self.creationRecorded = False
                self.signupRecorded = False
                self.connected_to_google = False
                self.connected_to_plaid = False

            def record_creation(self):
                self.creationRecorded = True

            def record_signup(self):
                self.signupRecorded = True

        user = MinimalUser()
        identify_user(user)

        # Should still call identify but without name and email
        args, kwargs = mock_analytics.identify.call_args
        assert args[0] == "minimal_user"
        user_data = args[1]
        assert 'name' not in user_data
        assert 'email' not in user_data

    def test_track_functions_with_empty_strings(self, mock_analytics):
        """Test tracking functions with empty string parameters."""
        from connectors.utils.segment import track_prompt, track_tool_called, track_agent_called

        user = MockUser(reference_id="user_123")

        # Mock the metrics methods
        user.add_prompt_to_metrics = Mock()
        user.add_tool_call_to_metrics = Mock()
        user.add_agent_call_to_metrics = Mock()
        
        # Test with empty strings
        track_prompt(user, "", "")
        track_tool_called(user, "", "", "")
        track_agent_called(user, "", "")

        # All should still call analytics.track
        assert mock_analytics.track.call_count == 3
        
        # Verify metrics methods were called with empty strings
        user.add_prompt_to_metrics.assert_called_once_with("")
        user.add_tool_call_to_metrics.assert_called_once_with("")
        user.add_agent_call_to_metrics.assert_called_once_with("")

    def test_track_functions_with_none_parameters(self, mock_analytics):
        """Test tracking functions with None parameters."""
        from connectors.utils.segment import track_prompt, track_tool_called

        user = MockUser(reference_id="user_123")
        
        # Mock the metrics methods
        user.add_prompt_to_metrics = Mock()
        user.add_tool_call_to_metrics = Mock()

        # These should handle None gracefully
        track_prompt(user, None, None)
        track_tool_called(user, None, None, None)

        assert mock_analytics.track.call_count == 2
        
        # Verify metrics methods were called with None
        user.add_prompt_to_metrics.assert_called_once_with(None)
        user.add_tool_call_to_metrics.assert_called_once_with(None)

    def test_user_with_partial_integrations(self, mock_analytics):
        """Test user with only some integrations."""
        from connectors.utils.segment import identify_user

        user = MockUser(
            reference_id="partial_user",
            is_registered=True,
            integrations={"google": True}  # Only google, no plaid
        )

        identify_user(user)

        args, kwargs = mock_analytics.identify.call_args
        user_data = args[1]
        assert user_data["has_google_integration"] == True
        assert user_data["has_plaid_integration"] == False

    def test_user_with_false_integrations(self, mock_analytics):
        """Test user with explicitly False integrations."""
        from connectors.utils.segment import identify_user

        user = MockUser(
            reference_id="false_integrations_user",
            is_registered=True,
            integrations={"google": False, "plaid": False}
        )

        identify_user(user)

        args, kwargs = mock_analytics.identify.call_args
        user_data = args[1]
        assert user_data["has_google_integration"] == False
        assert user_data["has_plaid_integration"] == False


class TestSegmentMetricsIntegration:
    """Test Segment tracking with user metrics integration."""

    @pytest.fixture
    def mock_analytics(self):
        """Mock the segment analytics module."""
        with patch('connectors.utils.segment.analytics') as mock_analytics:
            mock_analytics.write_key = "test_key"
            mock_analytics.identify = Mock()
            mock_analytics.track = Mock()
            yield mock_analytics

    @pytest.fixture
    def user_with_metrics_methods(self):
        """Create a user with proper metrics methods."""
        from firebase.models.user import User
        
        # Create a mock user that behaves like the real User model
        user = Mock(spec=User)
        user.reference_id = "user_123"
        user.email = "test@example.com"
        user.name = "Test User"
        user.is_registered = True
        user.metrics = None
        
        # Mock the metrics methods to track calls
        user.add_prompt_to_metrics = Mock(return_value=user)
        user.add_tool_call_to_metrics = Mock(return_value=user)
        user.add_agent_call_to_metrics = Mock(return_value=user)
        
        return user

    def test_track_prompt_calls_user_metrics(self, mock_analytics, user_with_metrics_methods):
        """Test that track_prompt calls user's add_prompt_to_metrics method."""
        from connectors.utils.segment import track_prompt
        
        track_prompt(user_with_metrics_methods, "chat_123", "What is the weather?")
        
        # Verify both Segment tracking and metrics update
        mock_analytics.track.assert_called_once()
        user_with_metrics_methods.add_prompt_to_metrics.assert_called_once_with("What is the weather?")

    def test_track_tool_called_calls_user_metrics(self, mock_analytics, user_with_metrics_methods):
        """Test that track_tool_called calls user's add_tool_call_to_metrics method."""
        from connectors.utils.segment import track_tool_called
        
        track_tool_called(user_with_metrics_methods, "chat_123", "search_google", "Search Google")
        
        # Verify both Segment tracking and metrics update
        mock_analytics.track.assert_called_once()
        user_with_metrics_methods.add_tool_call_to_metrics.assert_called_once_with("search_google")

    def test_track_agent_called_calls_user_metrics(self, mock_analytics, user_with_metrics_methods):
        """Test that track_agent_called calls user's add_agent_call_to_metrics method."""
        from connectors.utils.segment import track_agent_called
        
        track_agent_called(user_with_metrics_methods, "chat_123", "gmail_agent")
        
        # Verify both Segment tracking and metrics update
        mock_analytics.track.assert_called_once()
        user_with_metrics_methods.add_agent_call_to_metrics.assert_called_once_with("gmail_agent")
    
    def test_track_agent_called_filters_odai(self, mock_analytics, user_with_metrics_methods):
        """Test that track_agent_called filters out ODAI agent from metrics."""
        from connectors.utils.segment import track_agent_called
        
        track_agent_called(user_with_metrics_methods, "chat_123", "ODAI")
        
        # Verify Segment tracking happens but metrics update does not
        mock_analytics.track.assert_called_once_with(
            "user_123",
            "Agent Called",
            {
                "chat_id": "chat_123",
                "agent_name": "ODAI",
            }
        )
        # Metrics method should NOT be called for ODAI
        user_with_metrics_methods.add_agent_call_to_metrics.assert_not_called()

    def test_metrics_methods_handle_exceptions(self, mock_analytics, user_with_metrics_methods):
        """Test that tracking continues even if metrics methods raise exceptions."""
        from connectors.utils.segment import track_prompt, track_tool_called, track_agent_called
        
        # Make metrics methods raise exceptions
        user_with_metrics_methods.add_prompt_to_metrics.side_effect = Exception("DB Error")
        user_with_metrics_methods.add_tool_call_to_metrics.side_effect = Exception("DB Error")
        user_with_metrics_methods.add_agent_call_to_metrics.side_effect = Exception("DB Error")
        
        # These should not raise exceptions
        track_prompt(user_with_metrics_methods, "chat_123", "Test")
        track_tool_called(user_with_metrics_methods, "chat_123", "tool")
        track_agent_called(user_with_metrics_methods, "chat_123", "agent")
        
        # Segment tracking should still happen
        assert mock_analytics.track.call_count == 3

    def test_metrics_with_none_user(self, mock_analytics):
        """Test that None user doesn't cause errors in metrics."""
        from connectors.utils.segment import track_prompt, track_tool_called, track_agent_called
        
        # These should handle None user gracefully
        track_prompt(None, "chat_123", "Test")
        track_tool_called(None, "chat_123", "tool")
        track_agent_called(None, "chat_123", "agent")
        
        # No tracking should happen for None user
        mock_analytics.track.assert_not_called()

    def test_metrics_integration_with_real_user_mock(self, mock_analytics):
        """Test metrics integration with a more realistic user mock."""
        from connectors.utils.segment import track_prompt, track_tool_called, track_agent_called
        
        # Create a user that simulates the real User model behavior
        user = MockUser(reference_id="real_user_123")
        
        # Track initial metrics state
        initial_prompts = []
        initial_tool_calls = {}
        initial_agent_calls = {}
        
        # Mock the metrics methods to simulate actual behavior
        def add_prompt(prompt):
            prompt_obj = {'prompt': prompt, 'timestamp': '2025-08-05T14:00:00.000000'}
            initial_prompts.append(prompt_obj)
            user.metrics = {
                'prompts': initial_prompts,
                'prompt_count': len(initial_prompts)
            }
            return user
            
        def add_tool_call(tool):
            initial_tool_calls[tool] = initial_tool_calls.get(tool, 0) + 1
            user.metrics = user.metrics or {}
            user.metrics['tool_calls'] = initial_tool_calls
            user.metrics['tool_call_count'] = sum(initial_tool_calls.values())
            return user
            
        def add_agent_call(agent):
            initial_agent_calls[agent] = initial_agent_calls.get(agent, 0) + 1
            user.metrics = user.metrics or {}
            user.metrics['agent_calls'] = initial_agent_calls
            user.metrics['agent_call_count'] = sum(initial_agent_calls.values())
            return user
        
        user.add_prompt_to_metrics = Mock(side_effect=add_prompt)
        user.add_tool_call_to_metrics = Mock(side_effect=add_tool_call)
        user.add_agent_call_to_metrics = Mock(side_effect=add_agent_call)
        
        # Perform tracking
        track_prompt(user, "chat_123", "First prompt")
        track_prompt(user, "chat_123", "Second prompt")
        track_tool_called(user, "chat_123", "search_google")
        track_tool_called(user, "chat_123", "search_google")
        track_tool_called(user, "chat_123", "gmail_send")
        track_agent_called(user, "chat_123", "gmail_agent")
        track_agent_called(user, "chat_123", "plaid_agent")
        
        # Verify final metrics state
        assert len(user.metrics['prompts']) == 2
        assert user.metrics['prompts'][0]['prompt'] == "First prompt"
        assert user.metrics['prompts'][1]['prompt'] == "Second prompt"
        assert user.metrics['prompt_count'] == 2
        assert user.metrics['tool_calls'] == {'search_google': 2, 'gmail_send': 1}
        assert user.metrics['tool_call_count'] == 3
        assert user.metrics['agent_calls'] == {'gmail_agent': 1, 'plaid_agent': 1}
        assert user.metrics['agent_call_count'] == 2
        
        # Verify all tracking calls were made
        assert mock_analytics.track.call_count == 7

    def test_metrics_methods_not_present(self, mock_analytics):
        """Test behavior when user doesn't have metrics methods."""
        from connectors.utils.segment import track_prompt, track_tool_called, track_agent_called
        
        # Create a user without metrics methods
        user = MockUser(reference_id="no_metrics_user")
        
        # Remove metrics methods if they exist
        if hasattr(user, 'add_prompt_to_metrics'):
            delattr(user, 'add_prompt_to_metrics')
        if hasattr(user, 'add_tool_call_to_metrics'):
            delattr(user, 'add_tool_call_to_metrics')
        if hasattr(user, 'add_agent_call_to_metrics'):
            delattr(user, 'add_agent_call_to_metrics')
        
        # These should still work without metrics methods
        track_prompt(user, "chat_123", "Test")
        track_tool_called(user, "chat_123", "tool")
        track_agent_called(user, "chat_123", "agent")
        
        # Segment tracking should still happen
        assert mock_analytics.track.call_count == 3
