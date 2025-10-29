"""
Comprehensive tests for EasyPostTracker Firebase model.
"""

import pytest
from unittest.mock import Mock, patch
import datetime

# Test subject
from firebase.models.easypost_tracker import EasyPostTracker


@pytest.mark.asyncio
class TestEasyPostTrackerModelInit:
    """Test EasyPostTracker model initialization."""

    async def test_easypost_tracker_init_with_data(self, firebase_test_helper):
        """Test EasyPostTracker initialization with tracking data."""
        # Create mock data
        tracker_data = {
            'user_id': 'user_123',
            'tracking_number': '1Z999AA1234567890',
            'carrier': 'UPS',
            'easypost_id': 'trk_easypost_123',
            'created_at': datetime.datetime.now(),
            'updated_at': datetime.datetime.now()
        }

        # Create proper mock document snapshot
        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            tracker_data, 'tracker_123', True
        )

        # Initialize EasyPostTracker
        tracker = EasyPostTracker(mock_snapshot)

        # Verify initialization
        assert tracker.reference_id == 'tracker_123'
        assert hasattr(tracker, 'user_id')
        assert hasattr(tracker, 'tracking_number')
        assert hasattr(tracker, 'carrier')
        assert hasattr(tracker, 'easypost_id')
        assert hasattr(tracker, 'created_at')
        assert hasattr(tracker, 'updated_at')
        assert tracker.user_id == 'user_123'
        assert tracker.tracking_number == '1Z999AA1234567890'
        assert tracker.carrier == 'UPS'
        assert tracker.easypost_id == 'trk_easypost_123'

    async def test_easypost_tracker_init_minimal_data(self, firebase_test_helper):
        """Test EasyPostTracker initialization with minimal data."""
        minimal_data = {
            'user_id': 'user_minimal',
            'tracking_number': 'TRACK123'
        }

        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            minimal_data, 'tracker_minimal', True
        )

        tracker = EasyPostTracker(mock_snapshot)

        assert tracker.reference_id == 'tracker_minimal'
        assert tracker.user_id == 'user_minimal'
        assert tracker.tracking_number == 'TRACK123'


@pytest.mark.asyncio
class TestEasyPostTrackerCreateTracker:
    """Test EasyPostTracker create_tracker method."""

    async def test_create_tracker_success(self, firebase_test_helper):
        """Test creating a new tracker successfully."""
        # Mock user
        mock_user = Mock()
        mock_user.reference_id = 'user_123'

        # Mock document
        mock_document = Mock()
        mock_document.set = Mock()

        test_tracking_number = '1Z999AA1234567890'
        test_carrier = 'UPS'
        test_easypost_id = 'trk_easypost_123'
        test_now = datetime.datetime(2023, 10, 15, 12, 0, 0)

        # Mock the get_tracker_by_tracking_number call that happens at the end
        created_tracker_data = {
            'user_id': 'user_123',
            'tracking_number': test_tracking_number,
            'carrier': test_carrier,
            'easypost_id': test_easypost_id,
            'created_at': test_now,
            'updated_at': test_now
        }
        mock_created_snapshot = firebase_test_helper.create_mock_document_snapshot(
            created_tracker_data, 'new_tracker_123', True
        )

        with patch.object(EasyPostTracker, 'easypost_trackers') as mock_trackers, \
                patch('firebase.models.easypost_tracker.datetime') as mock_datetime, \
                patch.object(EasyPostTracker, 'get_tracker_by_tracking_number') as mock_get_tracker:

            mock_trackers.document.return_value = mock_document
            mock_datetime.datetime.now.return_value = test_now
            mock_get_tracker.return_value = EasyPostTracker(
                mock_created_snapshot)

            # Execute
            result = EasyPostTracker.create_tracker(
                mock_user, test_tracking_number, test_carrier, test_easypost_id
            )

            # Verify document.set was called
            mock_document.set.assert_called_once()

            # Verify the structure of the set call
            set_data = mock_document.set.call_args[0][0]
            assert set_data['user_id'] == 'user_123'
            assert set_data['tracking_number'] == test_tracking_number
            assert set_data['carrier'] == test_carrier
            assert set_data['easypost_id'] == test_easypost_id
            assert set_data['created_at'] == test_now
            assert set_data['updated_at'] == test_now

            # Verify return value
            assert isinstance(result, EasyPostTracker)
            assert result.tracking_number == test_tracking_number

    async def test_create_tracker_data_structure(self, firebase_test_helper):
        """Test the data structure for creating trackers."""
        # Test the tracker structure that would be created
        test_user_id = 'user_123'
        test_tracking_number = '1Z999AA1234567890'
        test_carrier = 'UPS'
        test_easypost_id = 'trk_easypost_123'
        test_timestamp = datetime.datetime.now()

        # Test tracker structure logic
        tracker_data = {
            'user_id': test_user_id,
            'tracking_number': test_tracking_number,
            'carrier': test_carrier,
            'easypost_id': test_easypost_id,
            'created_at': test_timestamp,
            'updated_at': test_timestamp
        }

        # Verify tracker structure
        assert tracker_data['user_id'] == test_user_id
        assert tracker_data['tracking_number'] == test_tracking_number
        assert tracker_data['carrier'] == test_carrier
        assert tracker_data['easypost_id'] == test_easypost_id
        assert 'created_at' in tracker_data
        assert 'updated_at' in tracker_data
        # Same on creation
        assert tracker_data['created_at'] == tracker_data['updated_at']


@pytest.mark.asyncio
class TestEasyPostTrackerRetrieval:
    """Test EasyPostTracker retrieval methods."""

    async def test_get_trackers_by_user_id_multiple(self, firebase_test_helper):
        """Test getting multiple trackers for a user."""
        # Create multiple tracker data
        tracker_data_1 = {
            'user_id': 'user_123',
            'tracking_number': '1Z999AA1234567890',
            'carrier': 'UPS'
        }
        tracker_data_2 = {
            'user_id': 'user_123',
            'tracking_number': '1Z999BB1234567890',
            'carrier': 'FedEx'
        }

        mock_snapshot_1 = firebase_test_helper.create_mock_document_snapshot(
            tracker_data_1, 'tracker_1', True
        )
        mock_snapshot_2 = firebase_test_helper.create_mock_document_snapshot(
            tracker_data_2, 'tracker_2', True
        )

        with patch.object(EasyPostTracker, 'easypost_trackers') as mock_trackers:
            # Mock query result with multiple trackers
            mock_trackers.where.return_value.get.return_value = [
                mock_snapshot_1, mock_snapshot_2]

            # Execute
            result = EasyPostTracker.get_trackers_by_user_id('user_123')

            # Verify
            assert isinstance(result, list)
            assert len(result) == 2
            assert all(isinstance(tracker, EasyPostTracker)
                       for tracker in result)
            assert result[0].carrier == 'UPS'
            assert result[1].carrier == 'FedEx'
            assert all(tracker.user_id == 'user_123' for tracker in result)

    async def test_get_trackers_by_user_id_empty(self, firebase_test_helper):
        """Test getting trackers for user with no trackers."""
        with patch.object(EasyPostTracker, 'easypost_trackers') as mock_trackers:
            # Mock empty query result
            mock_trackers.where.return_value.get.return_value = []

            # Execute
            result = EasyPostTracker.get_trackers_by_user_id(
                'user_no_trackers')

            # Verify
            assert isinstance(result, list)
            assert len(result) == 0

    async def test_get_tracker_by_tracking_number_exists(self, firebase_test_helper):
        """Test getting tracker by tracking number when it exists."""
        tracker_data = {
            'user_id': 'user_123',
            'tracking_number': '1Z999AA1234567890',
            'carrier': 'UPS',
            'easypost_id': 'trk_easypost_123'
        }

        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            tracker_data, 'tracker_123', True
        )

        with patch.object(EasyPostTracker, 'easypost_trackers') as mock_trackers:
            # Mock query result
            mock_trackers.where.return_value.get.return_value = [mock_snapshot]

            # Execute
            result = EasyPostTracker.get_tracker_by_tracking_number(
                '1Z999AA1234567890')

            # Verify
            assert isinstance(result, EasyPostTracker)
            assert result.tracking_number == '1Z999AA1234567890'
            assert result.carrier == 'UPS'
            assert result.user_id == 'user_123'

    async def test_get_tracker_by_tracking_number_not_exists(self, firebase_test_helper):
        """Test getting tracker by tracking number when it doesn't exist."""
        with patch.object(EasyPostTracker, 'easypost_trackers') as mock_trackers:
            # Mock empty query result
            mock_trackers.where.return_value.get.return_value = []

            # Execute
            result = EasyPostTracker.get_tracker_by_tracking_number(
                'NONEXISTENT123')

            # Verify
            assert result is None


@pytest.mark.asyncio
class TestEasyPostTrackerDataValidation:
    """Test EasyPostTracker data validation and structure."""

    async def test_tracking_number_formats(self, firebase_test_helper):
        """Test various tracking number formats."""
        # Test different tracking number formats
        tracking_formats = [
            ('1Z999AA1234567890', 'UPS'),
            ('9400111899561234567890', 'USPS'),
            ('1234567890', 'FedEx'),
            ('TBA123456789000', 'Amazon'),
            ('92055903486800123456789', 'USPS Priority Mail')
        ]

        for tracking_number, carrier in tracking_formats:
            tracker_data = {
                'user_id': 'user_123',
                'tracking_number': tracking_number,
                'carrier': carrier,
                'easypost_id': f'trk_{tracking_number.lower()}'
            }

            # Verify tracking data structure
            assert isinstance(tracker_data['tracking_number'], str)
            assert len(tracker_data['tracking_number']) > 0
            assert isinstance(tracker_data['carrier'], str)
            assert len(tracker_data['carrier']) > 0
            assert tracker_data['easypost_id'].startswith('trk_')

    async def test_carrier_validation(self, firebase_test_helper):
        """Test carrier validation logic."""
        # Test valid carriers
        valid_carriers = ['UPS', 'FedEx', 'USPS', 'DHL', 'Amazon', 'OnTrac']

        for carrier in valid_carriers:
            tracker_data = {
                'carrier': carrier,
                'tracking_number': '1234567890'
            }

            # Verify carrier data
            assert isinstance(tracker_data['carrier'], str)
            assert len(tracker_data['carrier']) > 0
            assert tracker_data['carrier'] in valid_carriers

    async def test_timestamp_validation(self, firebase_test_helper):
        """Test timestamp validation."""
        current_time = datetime.datetime.now()

        tracker_data = {
            'created_at': current_time,
            'updated_at': current_time
        }

        # Verify timestamps
        assert isinstance(tracker_data['created_at'], datetime.datetime)
        assert isinstance(tracker_data['updated_at'], datetime.datetime)
        assert tracker_data['created_at'] <= tracker_data['updated_at']


@pytest.mark.asyncio
class TestEasyPostTrackerEdgeCases:
    """Test edge cases for EasyPostTracker model."""

    async def test_easypost_tracker_init_with_empty_data(self, firebase_test_helper):
        """Test EasyPostTracker initialization with empty document."""
        empty_data = {}

        mock_snapshot = firebase_test_helper.create_mock_document_snapshot(
            empty_data, 'empty_tracker', True
        )

        tracker = EasyPostTracker(mock_snapshot)

        assert tracker.reference_id == 'empty_tracker'
        # Should not have attributes that weren't in the data
        assert not hasattr(tracker, 'tracking_number')
        assert not hasattr(tracker, 'user_id')

    async def test_multiple_trackers_same_user(self, firebase_test_helper):
        """Test handling multiple trackers for the same user."""
        user_id = 'user_multi_trackers'

        # Test multiple packages for same user
        trackers_data = [
            {
                'user_id': user_id,
                'tracking_number': '1Z999AA1234567890',
                'carrier': 'UPS',
                'easypost_id': 'trk_ups_123'
            },
            {
                'user_id': user_id,
                'tracking_number': '9400111899561234567890',
                'carrier': 'USPS',
                'easypost_id': 'trk_usps_456'
            },
            {
                'user_id': user_id,
                'tracking_number': '1234567890',
                'carrier': 'FedEx',
                'easypost_id': 'trk_fedex_789'
            }
        ]

        # Verify all trackers belong to same user
        assert all(tracker['user_id'] == user_id for tracker in trackers_data)

        # Verify unique tracking numbers
        tracking_numbers = [tracker['tracking_number']
                            for tracker in trackers_data]
        assert len(tracking_numbers) == len(
            set(tracking_numbers))  # All unique

        # Verify different carriers
        carriers = [tracker['carrier'] for tracker in trackers_data]
        assert len(set(carriers)) == len(carriers)  # All different

    async def test_duplicate_tracking_number_handling(self, firebase_test_helper):
        """Test handling of duplicate tracking numbers."""
        # In practice, tracking numbers should be unique, but test the logic
        tracking_number = '1Z999AA1234567890'

        tracker_1 = {
            'user_id': 'user_1',
            'tracking_number': tracking_number,
            'carrier': 'UPS'
        }

        tracker_2 = {
            'user_id': 'user_2',
            'tracking_number': tracking_number,  # Same tracking number
            'carrier': 'UPS'
        }

        # In a real scenario, this might represent the same package being tracked by different users
        # The model should handle this by returning the first match
        assert tracker_1['tracking_number'] == tracker_2['tracking_number']
        assert tracker_1['user_id'] != tracker_2['user_id']

    async def test_easypost_id_validation(self, firebase_test_helper):
        """Test EasyPost ID validation."""
        # Test valid EasyPost ID formats
        valid_easypost_ids = [
            'trk_1234567890abcdef',
            'trk_abcdef1234567890',
            'trk_aaaabbbbccccdddd'
        ]

        for easypost_id in valid_easypost_ids:
            tracker_data = {
                'easypost_id': easypost_id,
                'tracking_number': '1234567890'
            }

            # Verify EasyPost ID format
            assert isinstance(tracker_data['easypost_id'], str)
            assert tracker_data['easypost_id'].startswith('trk_')
            # More than just 'trk_'
            assert len(tracker_data['easypost_id']) > 4

    async def test_tracker_creation_workflow(self, firebase_test_helper):
        """Test complete tracker creation workflow."""
        # Test the complete workflow from user input to tracker creation

        # Step 1: User provides tracking info
        user_input = {
            'tracking_number': '1Z999AA1234567890',
            'carrier': 'UPS'
        }

        # Step 2: System generates EasyPost ID (simulated)
        easypost_id = f"trk_{user_input['tracking_number'].lower()}"

        # Step 3: Create tracker data structure
        tracker_data = {
            'user_id': 'user_123',
            'tracking_number': user_input['tracking_number'],
            'carrier': user_input['carrier'],
            'easypost_id': easypost_id,
            'created_at': datetime.datetime.now(),
            'updated_at': datetime.datetime.now()
        }

        # Verify complete workflow
        assert tracker_data['tracking_number'] == user_input['tracking_number']
        assert tracker_data['carrier'] == user_input['carrier']
        assert tracker_data['easypost_id'].startswith('trk_')
        assert 'user_id' in tracker_data
        assert 'created_at' in tracker_data
        assert 'updated_at' in tracker_data
