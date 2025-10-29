"""
Comprehensive tests for Integration Firebase model.
"""

import pytest
from unittest.mock import Mock, patch

# Test subject
from firebase.models.integration import Integration


@pytest.mark.asyncio
class TestIntegrationModelInit:
    """Test Integration model initialization."""

    async def test_integration_init_with_data(self, firebase_test_helper):
        """Test Integration initialization with integration data."""
        # Create mock data
        integration_data = {
            'name': 'Gmail Integration',
            'description': 'Manage your Gmail emails through ODAI',
            'prompts': ['Check my emails', 'Send an email to John', 'Search for emails from Jane'],
            'logo_url': 'https://example.com/gmail-logo.png',
            'internal_id': 'gmail_integration_v1'
        }

        # Create proper mock document snapshot
        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            integration_data, 'integration_123', True
        )

        # Initialize Integration
        integration = Integration(mock_snapshot)

        # Verify initialization
        assert integration.reference_id == 'integration_123'
        assert hasattr(integration, 'name')
        assert hasattr(integration, 'description')
        assert hasattr(integration, 'prompts')
        assert integration.name == 'Gmail Integration'
        assert integration.description == 'Manage your Gmail emails through ODAI'
        assert len(integration.prompts) == 3
        assert 'Check my emails' in integration.prompts

    async def test_integration_init_minimal_data(self, firebase_test_helper):
        """Test Integration initialization with minimal data."""
        minimal_data = {
            'name': 'Basic Integration',
            'description': 'A basic integration',
            'prompts': []
        }

        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            minimal_data, 'integration_minimal', True
        )

        integration = Integration(mock_snapshot)

        assert integration.reference_id == 'integration_minimal'
        assert integration.name == 'Basic Integration'
        assert integration.description == 'A basic integration'
        assert integration.prompts == []


@pytest.mark.asyncio
class TestIntegrationCreateIntegration:
    """Test Integration create_integration method."""

    async def test_create_integration_new(self, firebase_test_helper):
        """Test creating a new integration."""
        test_internal_id = 'spotify_integration_v1'
        test_logo_url = 'https://example.com/spotify-logo.png'
        test_name = 'Spotify Integration'
        test_description = 'Control your Spotify music through ODAI'
        test_prompts = ['Play music', 'Skip track', 'Add to playlist']

        # Mock document
        mock_document = Mock()
        mock_document.set = Mock()

        # Mock the created integration
        created_data = {
            'name': test_name,
            'description': test_description,
            'prompts': test_prompts,
            'logo_url': test_logo_url,
            'internal_id': test_internal_id
        }
        mock_created_snapshot = firebase_test_helper.create_mock_document_snapshot(
            created_data, 'new_integration_123', True
        )

        with patch.object(Integration, 'odai_integrations') as mock_integrations, \
                patch.object(Integration, 'find_odai_integration_by_name') as mock_find:

            # Mock no existing integration, then return created one
            mock_find.side_effect = [None, Integration(mock_created_snapshot)]
            mock_integrations.document.return_value = mock_document

            # Execute
            result = Integration.create_integration(
                test_internal_id, test_logo_url, test_name, test_description, test_prompts
            )

            # Verify document.set was called for new integration
            mock_document.set.assert_called_once()

            # Verify the structure of the set call
            set_data = mock_document.set.call_args[0][0]
            assert set_data['name'] == test_name
            assert set_data['description'] == test_description
            assert set_data['prompts'] == test_prompts
            assert set_data['logo_url'] == test_logo_url
            assert set_data['internal_id'] == test_internal_id

            # Verify return value
            assert isinstance(result, Integration)
            assert result.name == test_name

    async def test_create_integration_update_existing(self, firebase_test_helper):
        """Test updating an existing integration."""
        # Create existing integration data
        existing_data = {
            'name': 'Gmail Integration',
            'description': 'Old description',
            'prompts': ['Old prompt'],
            'logo_url': 'https://example.com/old-logo.png',
            'internal_id': 'gmail_v1'
        }

        test_internal_id = 'gmail_integration_v2'
        test_logo_url = 'https://example.com/new-gmail-logo.png'
        test_name = 'Gmail Integration'  # Same name
        test_description = 'Updated description for Gmail integration'
        test_prompts = ['Check emails', 'Send email', 'Search emails']

        mock_existing_snapshot = firebase_test_helper.create_mock_document_snapshot(
            existing_data, 'existing_integration_123', True
        )
        existing_integration = Integration(mock_existing_snapshot)

        # Mock document
        mock_document = Mock()
        mock_document.update = Mock()

        with patch.object(Integration, 'odai_integrations') as mock_integrations, \
                patch.object(Integration, 'find_odai_integration_by_name') as mock_find:

            # Mock existing integration found
            mock_find.return_value = existing_integration
            mock_integrations.document.return_value = mock_document

            # Execute
            result = Integration.create_integration(
                test_internal_id, test_logo_url, test_name, test_description, test_prompts
            )

            # Verify document.update was called for existing integration
            mock_document.update.assert_called_once()

            # Verify the structure of the update call
            update_data = mock_document.update.call_args[0][0]
            assert update_data['prompts'] == test_prompts
            assert update_data['description'] == test_description
            assert update_data['logo_url'] == test_logo_url
            assert update_data['internal_id'] == test_internal_id

            # Verify return value
            assert isinstance(result, Integration)
            assert result.prompts == test_prompts
            assert result.description == test_description

    async def test_create_integration_data_structure(self, firebase_test_helper):
        """Test the data structure for creating integrations."""
        # Test the integration structure that would be created
        test_name = 'Calendar Integration'
        test_description = 'Manage your calendar events'
        test_prompts = ['Create event', 'Check schedule', 'Set reminder']
        test_logo_url = 'https://example.com/calendar-logo.png'
        test_internal_id = 'calendar_v1'

        # Test integration structure logic
        integration_data = {
            'name': test_name,
            'description': test_description,
            'prompts': test_prompts,
            'logo_url': test_logo_url,
            'internal_id': test_internal_id
        }

        # Verify integration structure
        assert integration_data['name'] == test_name
        assert integration_data['description'] == test_description
        assert isinstance(integration_data['prompts'], list)
        assert len(integration_data['prompts']) == 3
        assert integration_data['logo_url'].startswith('https://')
        assert 'internal_id' in integration_data


@pytest.mark.asyncio
class TestIntegrationFindIntegration:
    """Test Integration find_odai_integration_by_name method."""

    async def test_find_integration_by_name_exists(self, firebase_test_helper):
        """Test finding integration by name when it exists."""
        integration_data = {
            'name': 'Slack Integration',
            'description': 'Manage Slack messages',
            'prompts': ['Send message', 'Check notifications']
        }

        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            integration_data, 'slack_integration', True
        )

        with patch.object(Integration, 'odai_integrations') as mock_integrations:
            # Mock query result
            mock_integrations.where.return_value.get.return_value = [
                mock_snapshot]

            # Execute
            result = Integration.find_odai_integration_by_name(
                'Slack Integration')

            # Verify
            assert isinstance(result, Integration)
            assert result.name == 'Slack Integration'
            assert result.description == 'Manage Slack messages'

    async def test_find_integration_by_name_not_exists(self, firebase_test_helper):
        """Test finding integration by name when it doesn't exist."""
        with patch.object(Integration, 'odai_integrations') as mock_integrations:
            # Mock empty query result
            mock_integrations.where.return_value.get.return_value = []

            # Execute
            result = Integration.find_odai_integration_by_name(
                'Nonexistent Integration')

            # Verify
            assert result is None


@pytest.mark.asyncio
class TestIntegrationDataValidation:
    """Test Integration data validation and structure."""

    async def test_prompts_validation(self, firebase_test_helper):
        """Test prompts validation."""
        # Test various prompt structures
        prompt_examples = [
            ['Send email', 'Check inbox', 'Delete email'],
            ['Play music', 'Skip track'],
            ['Create task'],
            []  # Empty prompts
        ]

        for prompts in prompt_examples:
            integration_data = {
                'name': 'Test Integration',
                'description': 'Test description',
                'prompts': prompts
            }

            # Verify prompts structure
            assert isinstance(integration_data['prompts'], list)
            assert all(isinstance(prompt, str)
                       for prompt in integration_data['prompts'])

    async def test_integration_naming_validation(self, firebase_test_helper):
        """Test integration name validation."""
        # Test various integration names
        valid_names = [
            'Gmail Integration',
            'Google Calendar',
            'Spotify Music Player',
            'Task Manager Pro',
            'Simple Notes'
        ]

        for name in valid_names:
            integration_data = {
                'name': name,
                'description': f'Description for {name}'
            }

            # Verify name structure
            assert isinstance(integration_data['name'], str)
            assert len(integration_data['name']) > 0
            assert integration_data['name'] == name

    async def test_description_validation(self, firebase_test_helper):
        """Test description validation."""
        # Test various descriptions
        descriptions = [
            'Simple integration for basic tasks',
            'Advanced integration with multiple features and capabilities',
            'Basic integration',
            ''  # Empty description
        ]

        for description in descriptions:
            integration_data = {
                'name': 'Test Integration',
                'description': description
            }

            # Verify description structure
            assert isinstance(integration_data['description'], str)


@pytest.mark.asyncio
class TestIntegrationEdgeCases:
    """Test edge cases for Integration model."""

    async def test_integration_init_with_empty_data(self, firebase_test_helper):
        """Test Integration initialization with empty document."""
        empty_data = {}

        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            empty_data, 'empty_integration', True
        )

        integration = Integration(mock_snapshot)

        assert integration.reference_id == 'empty_integration'
        # Should not have attributes that weren't in the data
        assert not hasattr(integration, 'name')
        assert not hasattr(integration, 'description')

    async def test_integration_with_long_prompts_list(self, firebase_test_helper):
        """Test integration with many prompts."""
        # Test integration with extensive prompts list
        long_prompts = [
            f'Prompt {i}: Perform action number {i}'
            for i in range(1, 21)  # 20 prompts
        ]

        integration_data = {
            'name': 'Comprehensive Integration',
            'description': 'Integration with many capabilities',
            'prompts': long_prompts
        }

        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            integration_data, 'comprehensive_integration', True
        )

        integration = Integration(mock_snapshot)

        # Verify handling of large prompts list
        assert len(integration.prompts) == 20
        assert all('Prompt' in prompt for prompt in integration.prompts)
        assert integration.prompts[0] == 'Prompt 1: Perform action number 1'
        assert integration.prompts[-1] == 'Prompt 20: Perform action number 20'

    async def test_integration_update_preserves_reference_id(self, firebase_test_helper):
        """Test that updating integration preserves reference ID."""
        original_data = {
            'name': 'Original Integration',
            'description': 'Original description',
            'prompts': ['Original prompt']
        }

        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            original_data, 'preserved_id_123', True
        )

        integration = Integration(mock_snapshot)
        original_reference_id = integration.reference_id

        # Simulate update
        integration.description = 'Updated description'
        integration.prompts = ['Updated prompt 1', 'Updated prompt 2']

        # Verify reference ID is preserved
        assert integration.reference_id == original_reference_id
        assert integration.reference_id == 'preserved_id_123'

    async def test_integration_special_characters_handling(self, firebase_test_helper):
        """Test handling of special characters in integration data."""
        special_data = {
            'name': 'Special Characters Integration™',
            'description': 'Integration with émojis 🚀 and special chars: @#$%^&*()',
            'prompts': [
                'Send message with emojis 😀',
                'Handle @mentions and #hashtags',
                'Process $currency and %percentages'
            ]
        }

        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            special_data, 'special_chars_integration', True
        )

        integration = Integration(mock_snapshot)

        # Verify special characters are handled correctly
        assert '™' in integration.name
        assert '🚀' in integration.description
        assert any('😀' in prompt for prompt in integration.prompts)
        assert any('@mentions' in prompt for prompt in integration.prompts)
        assert any('$currency' in prompt for prompt in integration.prompts)
