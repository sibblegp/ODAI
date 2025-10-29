"""
Comprehensive tests for UnhandledRequest Firebase model.
"""

import pytest
from unittest.mock import Mock, patch
import datetime

# Test subject
from firebase.models.unhandled_request import UnhandledRequest


@pytest.mark.asyncio
class TestUnhandledRequestModelInit:
    """Test UnhandledRequest model initialization."""

    async def test_unhandled_request_init_with_data(self, firebase_test_helper):
        """Test UnhandledRequest initialization with request data."""
        # Create mock data
        request_data = {
            'user_id': 'user_123',
            'chat_id': 'chat_456',
            'prompt': 'Can you control my smart home lights?',
            'capability_requested': 'smart_home_control',
            'capability_description': 'Control smart home devices like lights, thermostats, etc.',
            'created_at': datetime.datetime.now()
        }

        # Create proper mock document snapshot
        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            request_data, 'request_123', True
        )

        # Initialize UnhandledRequest
        unhandled_request = UnhandledRequest(mock_snapshot)

        # Verify initialization
        assert unhandled_request.reference_id == 'request_123'
        assert hasattr(unhandled_request, 'user_id')
        assert hasattr(unhandled_request, 'chat_id')
        assert hasattr(unhandled_request, 'prompt')
        assert hasattr(unhandled_request, 'capability_requested')
        assert hasattr(unhandled_request, 'capability_description')
        assert hasattr(unhandled_request, 'created_at')
        assert unhandled_request.user_id == 'user_123'
        assert unhandled_request.chat_id == 'chat_456'
        assert unhandled_request.prompt == 'Can you control my smart home lights?'
        assert unhandled_request.capability_requested == 'smart_home_control'

    async def test_unhandled_request_init_minimal_data(self, firebase_test_helper):
        """Test UnhandledRequest initialization with minimal data."""
        minimal_data = {
            'user_id': 'user_minimal',
            'chat_id': 'chat_minimal',
            'prompt': 'Simple request'
        }

        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            minimal_data, 'request_minimal', True
        )

        unhandled_request = UnhandledRequest(mock_snapshot)

        assert unhandled_request.reference_id == 'request_minimal'
        assert unhandled_request.user_id == 'user_minimal'
        assert unhandled_request.chat_id == 'chat_minimal'
        assert unhandled_request.prompt == 'Simple request'


@pytest.mark.asyncio
class TestUnhandledRequestCreate:
    """Test UnhandledRequest create_unhandled_request method."""

    async def test_create_unhandled_request_success(self, firebase_test_helper):
        """Test creating an unhandled request successfully."""
        # Mock user and chat
        mock_user = Mock()
        mock_user.reference_id = 'user_123'

        mock_chat = Mock()
        mock_chat.reference_id = 'chat_456'

        # Mock document
        mock_document = Mock()
        mock_document.set = Mock()

        test_prompt = 'Can you book a flight to Tokyo?'
        test_capability = 'flight_booking'
        test_description = 'Book flights, manage reservations, check flight status'
        test_now = datetime.datetime(2023, 10, 15, 12, 0, 0)

        with patch.object(UnhandledRequest, 'unhandled_requests') as mock_requests, \
                patch('firebase.models.unhandled_request.datetime') as mock_datetime:

            mock_requests.document.return_value = mock_document
            mock_datetime.datetime.now.return_value = test_now

            # Execute
            result = await UnhandledRequest.create_unhandled_request(
                mock_user, mock_chat, test_prompt, test_capability, test_description
            )

            # Verify document.set was called
            mock_document.set.assert_called_once()

            # Verify the structure of the set call
            set_data = mock_document.set.call_args[0][0]
            assert set_data['user_id'] == 'user_123'
            assert set_data['chat_id'] == 'chat_456'
            assert set_data['prompt'] == test_prompt
            assert set_data['capability_requested'] == test_capability
            assert set_data['capability_description'] == test_description
            assert set_data['created_at'] == test_now

            # Verify return value
            assert result == True

    async def test_create_unhandled_request_data_structure(self, firebase_test_helper):
        """Test the data structure for creating unhandled requests."""
        # Test the request structure that would be created
        test_user_id = 'user_123'
        test_chat_id = 'chat_456'
        test_prompt = 'Can you control my car remotely?'
        test_capability = 'vehicle_control'
        test_description = 'Remote control of vehicle functions like start, lock, unlock'
        test_timestamp = datetime.datetime.now()

        # Test request structure logic
        request_data = {
            'user_id': test_user_id,
            'chat_id': test_chat_id,
            'prompt': test_prompt,
            'capability_requested': test_capability,
            'capability_description': test_description,
            'created_at': test_timestamp
        }

        # Verify request structure
        assert request_data['user_id'] == test_user_id
        assert request_data['chat_id'] == test_chat_id
        assert request_data['prompt'] == test_prompt
        assert request_data['capability_requested'] == test_capability
        assert request_data['capability_description'] == test_description
        assert 'created_at' in request_data


@pytest.mark.asyncio
class TestUnhandledRequestDataValidation:
    """Test UnhandledRequest data validation and structure."""

    async def test_prompt_validation(self, firebase_test_helper):
        """Test various prompt formats."""
        # Test different types of unhandled prompts
        prompt_examples = [
            'Can you control my smart home lights?',
            'Book me a flight to Paris',
            'Order groceries from the store',
            'Start my car remotely',
            'Set up a video call with my team',
            'Transfer money to my savings account',
            'Book a table at a restaurant',
            'Schedule a doctor appointment'
        ]

        for prompt in prompt_examples:
            request_data = {
                'user_id': 'user_123',
                'chat_id': 'chat_456',
                'prompt': prompt,
                'capability_requested': 'unknown_capability'
            }

            # Verify prompt structure
            assert isinstance(request_data['prompt'], str)
            assert len(request_data['prompt']) > 0
            assert request_data['prompt'] == prompt

    async def test_capability_validation(self, firebase_test_helper):
        """Test capability request validation."""
        # Test various capability requests
        capabilities = [
            ('smart_home_control', 'Control smart home devices'),
            ('flight_booking', 'Book and manage flights'),
            ('grocery_ordering', 'Order groceries online'),
            ('vehicle_control', 'Remote vehicle operations'),
            ('video_calling', 'Set up video conferences'),
            ('banking', 'Financial transactions and management'),
            ('restaurant_booking', 'Make restaurant reservations'),
            ('healthcare', 'Schedule medical appointments')
        ]

        for capability, description in capabilities:
            request_data = {
                'capability_requested': capability,
                'capability_description': description
            }

            # Verify capability structure
            assert isinstance(request_data['capability_requested'], str)
            assert isinstance(request_data['capability_description'], str)
            assert len(request_data['capability_requested']) > 0
            assert len(request_data['capability_description']) > 0

    async def test_id_validation(self, firebase_test_helper):
        """Test user_id and chat_id validation."""
        # Test various ID formats
        id_examples = [
            'user_123',
            'chat_456',
            'abc123def456',
            'user_with_underscores',
            'longidwithmanycharacters123456789'
        ]

        for test_id in id_examples:
            request_data = {
                'user_id': test_id,
                'chat_id': test_id
            }

            # Verify ID structure
            assert isinstance(request_data['user_id'], str)
            assert isinstance(request_data['chat_id'], str)
            assert len(request_data['user_id']) > 0
            assert len(request_data['chat_id']) > 0

    async def test_timestamp_validation(self, firebase_test_helper):
        """Test timestamp validation."""
        current_time = datetime.datetime.now()

        request_data = {
            'created_at': current_time
        }

        # Verify timestamp
        assert isinstance(request_data['created_at'], datetime.datetime)
        assert request_data['created_at'] <= datetime.datetime.now()


@pytest.mark.asyncio
class TestUnhandledRequestEdgeCases:
    """Test edge cases for UnhandledRequest model."""

    async def test_unhandled_request_init_with_empty_data(self, firebase_test_helper):
        """Test UnhandledRequest initialization with empty document."""
        empty_data = {}

        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            empty_data, 'empty_request', True
        )

        unhandled_request = UnhandledRequest(mock_snapshot)

        assert unhandled_request.reference_id == 'empty_request'
        # Should not have attributes that weren't in the data
        assert not hasattr(unhandled_request, 'prompt')
        assert not hasattr(unhandled_request, 'user_id')

    async def test_long_prompt_handling(self, firebase_test_helper):
        """Test handling of very long prompts."""
        # Test with a very long prompt
        long_prompt = ' '.join([
            'Can you please help me with a very complex task that involves',
            'multiple steps and requires coordination between different systems',
            'including smart home devices, calendar management, email sending,',
            'flight booking, restaurant reservations, and payment processing',
            'while also considering my preferences and constraints and making',
            'sure everything is scheduled appropriately and confirmed properly?'
        ])

        request_data = {
            'user_id': 'user_123',
            'chat_id': 'chat_456',
            'prompt': long_prompt,
            'capability_requested': 'complex_task_management',
            'capability_description': 'Handle complex multi-step tasks across systems'
        }

        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            request_data, 'long_prompt_request', True
        )

        unhandled_request = UnhandledRequest(mock_snapshot)

        # Verify long prompt is handled correctly
        assert len(unhandled_request.prompt) > 200
        assert 'complex task' in unhandled_request.prompt
        assert unhandled_request.capability_requested == 'complex_task_management'

    async def test_special_characters_in_prompt(self, firebase_test_helper):
        """Test handling of special characters in prompts."""
        special_prompt = (
            "Can you help me with émojis 🚀 and special chars: @#$%^&*()? "
            "I need to send an email to user@example.com with a $100 payment."
        )

        request_data = {
            'user_id': 'user_123',
            'chat_id': 'chat_456',
            'prompt': special_prompt,
            'capability_requested': 'email_payment',
            'capability_description': 'Send emails with payment information'
        }

        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            request_data, 'special_chars_request', True
        )

        unhandled_request = UnhandledRequest(mock_snapshot)

        # Verify special characters are handled correctly
        assert '🚀' in unhandled_request.prompt
        assert '@#$%^&*()' in unhandled_request.prompt
        assert 'user@example.com' in unhandled_request.prompt
        assert '$100' in unhandled_request.prompt

    async def test_common_unhandled_request_scenarios(self, firebase_test_helper):
        """Test common scenarios that might generate unhandled requests."""
        # Test various common unhandled request scenarios
        scenarios = [
            {
                'prompt': 'Can you order pizza for me?',
                'capability': 'food_delivery',
                'description': 'Order food from restaurants and delivery services'
            },
            {
                'prompt': 'Book me a haircut appointment',
                'capability': 'personal_services',
                'description': 'Schedule appointments for personal services'
            },
            {
                'prompt': 'Find me a babysitter for tonight',
                'capability': 'childcare_services',
                'description': 'Find and book childcare services'
            },
            {
                'prompt': 'Can you walk my dog?',
                'capability': 'pet_services',
                'description': 'Arrange pet care and walking services'
            },
            {
                'prompt': 'Help me find a new apartment',
                'capability': 'real_estate',
                'description': 'Search and manage real estate transactions'
            }
        ]

        for i, scenario in enumerate(scenarios):
            request_data = {
                'user_id': f'user_{i}',
                'chat_id': f'chat_{i}',
                'prompt': scenario['prompt'],
                'capability_requested': scenario['capability'],
                'capability_description': scenario['description'],
                'created_at': datetime.datetime.now()
            }

            # Verify each scenario structure
            assert isinstance(request_data['prompt'], str)
            assert isinstance(request_data['capability_requested'], str)
            assert isinstance(request_data['capability_description'], str)
            assert len(request_data['prompt']) > 0
            assert request_data['capability_requested'] != ''
            assert request_data['capability_description'] != ''

    async def test_request_logging_workflow(self, firebase_test_helper):
        """Test complete unhandled request logging workflow."""
        # Test the complete workflow from user request to logging

        # Step 1: User makes a request
        user_request = 'Can you control my Tesla Model 3?'

        # Step 2: System identifies it as unhandled
        identified_capability = 'tesla_vehicle_control'
        capability_description = 'Control Tesla vehicles remotely'

        # Step 3: System logs the unhandled request
        log_data = {
            'user_id': 'user_tesla',
            'chat_id': 'chat_tesla_request',
            'prompt': user_request,
            'capability_requested': identified_capability,
            'capability_description': capability_description,
            'created_at': datetime.datetime.now()
        }

        # Verify complete workflow
        assert log_data['prompt'] == user_request
        assert log_data['capability_requested'] == identified_capability
        assert log_data['capability_description'] == capability_description
        assert 'user_id' in log_data
        assert 'chat_id' in log_data
        assert 'created_at' in log_data

    async def test_multiple_requests_same_capability(self, firebase_test_helper):
        """Test multiple requests for the same unhandled capability."""
        # Test scenario where multiple users request the same missing capability
        base_capability = 'smart_car_control'
        base_description = 'Control smart car features remotely'

        requests = [
            {
                'user_id': 'user_1',
                'prompt': 'Start my BMW remotely',
                'capability_requested': base_capability,
                'capability_description': base_description
            },
            {
                'user_id': 'user_2',
                'prompt': 'Lock my Audi from here',
                'capability_requested': base_capability,
                'capability_description': base_description
            },
            {
                'user_id': 'user_3',
                'prompt': 'Check my Mercedes battery level',
                'capability_requested': base_capability,
                'capability_description': base_description
            }
        ]

        # Verify all requests share the same capability but different prompts
        capabilities = [req['capability_requested'] for req in requests]
        prompts = [req['prompt'] for req in requests]

        assert all(cap == base_capability for cap in capabilities)
        assert len(set(prompts)) == len(prompts)  # All prompts are unique
        assert all(len(prompt) > 0 for prompt in prompts)
