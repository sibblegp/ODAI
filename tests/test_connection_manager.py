"""
Comprehensive unit tests for websocket.connection_manager module.

Tests cover all methods of ConnectionManager class including:
- WebSocket connection management (connect/disconnect)
- Personal message sending
- JSON message handling
- Broadcasting to multiple connections
- Error handling and connection cleanup
- Connection counting and state management
- Logging verification
- Edge cases and boundary conditions
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from typing import List

# Import the modules to test
from websocket.connection_manager import ConnectionManager


# Module-level fixtures available to all test classes
@pytest.fixture
def connection_manager():
    """Create a ConnectionManager instance for testing."""
    return ConnectionManager()


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket object."""
    websocket = Mock()
    websocket.accept = AsyncMock()
    websocket.send_text = AsyncMock()
    websocket.close = AsyncMock()
    return websocket


@pytest.fixture
def mock_websocket_list():
    """Create a list of mock WebSocket objects."""
    websockets = []
    for i in range(3):
        ws = Mock()
        ws.accept = AsyncMock()
        ws.send_text = AsyncMock()
        ws.close = AsyncMock()
        websockets.append(ws)
    return websockets


@pytest.fixture
def sample_json_data():
    """Create sample JSON data for testing."""
    return {
        "type": "message",
        "content": "Hello World",
        "timestamp": "2024-01-01T12:00:00Z",
        "user_id": "test_user_123"
    }


class TestConnectionManagerInit:
    """Test ConnectionManager initialization."""

    def test_init_creates_empty_connection_list(self):
        """Test that ConnectionManager initializes with empty connection list."""
        manager = ConnectionManager()

        assert isinstance(manager.active_connections, list)
        assert len(manager.active_connections) == 0
        assert manager.connection_count == 0


class TestConnectionManagerConnect:
    """Test the connect method."""

    @pytest.mark.asyncio
    async def test_connect_success(self, connection_manager, mock_websocket):
        """Test successful WebSocket connection."""
        # Execute
        await connection_manager.connect(mock_websocket)

        # Verify
        mock_websocket.accept.assert_called_once()
        assert mock_websocket in connection_manager.active_connections
        assert connection_manager.connection_count == 1

    @pytest.mark.asyncio
    async def test_connect_multiple_websockets(self, connection_manager, mock_websocket_list):
        """Test connecting multiple WebSockets."""
        # Execute - connect all websockets
        for ws in mock_websocket_list:
            await connection_manager.connect(ws)

        # Verify
        for ws in mock_websocket_list:
            ws.accept.assert_called_once()
            assert ws in connection_manager.active_connections

        assert connection_manager.connection_count == len(mock_websocket_list)

    @pytest.mark.asyncio
    async def test_connect_same_websocket_twice(self, connection_manager, mock_websocket):
        """Test connecting the same WebSocket twice."""
        # Execute
        await connection_manager.connect(mock_websocket)
        await connection_manager.connect(mock_websocket)

        # Verify - should have 2 entries (no deduplication)
        assert mock_websocket.accept.call_count == 2
        assert connection_manager.active_connections.count(mock_websocket) == 2
        assert connection_manager.connection_count == 2

    @pytest.mark.asyncio
    @patch('websocket.connection_manager.logger')
    async def test_connect_logs_new_connection(self, mock_logger, connection_manager, mock_websocket):
        """Test that connect logs the new connection."""
        # Execute
        await connection_manager.connect(mock_websocket)

        # Verify logging
        mock_logger.info.assert_called_once_with(
            "New WebSocket connection established. Total connections: 1"
        )

    @pytest.mark.asyncio
    async def test_connect_websocket_accept_exception(self, connection_manager, mock_websocket):
        """Test handling exception during websocket.accept()."""
        # Setup
        mock_websocket.accept.side_effect = Exception("Accept failed")

        # Execute & Verify
        with pytest.raises(Exception, match="Accept failed"):
            await connection_manager.connect(mock_websocket)

        # Connection should not be added to active connections on failure
        assert mock_websocket not in connection_manager.active_connections
        assert connection_manager.connection_count == 0


class TestConnectionManagerDisconnect:
    """Test the disconnect method."""

    @pytest.mark.asyncio
    async def test_disconnect_existing_connection(self, connection_manager, mock_websocket):
        """Test disconnecting an existing WebSocket connection."""
        # Setup - connect first
        await connection_manager.connect(mock_websocket)
        assert connection_manager.connection_count == 1

        # Execute
        connection_manager.disconnect(mock_websocket)

        # Verify
        assert mock_websocket not in connection_manager.active_connections
        assert connection_manager.connection_count == 0

    def test_disconnect_non_existing_connection(self, connection_manager, mock_websocket):
        """Test disconnecting a non-existing WebSocket connection."""
        # Execute - should not raise an exception
        connection_manager.disconnect(mock_websocket)

        # Verify - no change in connections
        assert connection_manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_disconnect_one_of_multiple_connections(self, connection_manager, mock_websocket_list):
        """Test disconnecting one connection when multiple exist."""
        # Setup - connect all websockets
        for ws in mock_websocket_list:
            await connection_manager.connect(ws)

        initial_count = connection_manager.connection_count
        websocket_to_remove = mock_websocket_list[1]

        # Execute
        connection_manager.disconnect(websocket_to_remove)

        # Verify
        assert websocket_to_remove not in connection_manager.active_connections
        assert connection_manager.connection_count == initial_count - 1

        # Other connections should remain
        for i, ws in enumerate(mock_websocket_list):
            if i != 1:  # Skip the removed one
                assert ws in connection_manager.active_connections

    @pytest.mark.asyncio
    @patch('websocket.connection_manager.logger')
    async def test_disconnect_logs_closure(self, mock_logger, connection_manager, mock_websocket):
        """Test that disconnect logs the connection closure."""
        # Setup - connect first
        await connection_manager.connect(mock_websocket)
        mock_logger.reset_mock()  # Clear previous log calls

        # Execute
        connection_manager.disconnect(mock_websocket)

        # Verify logging
        mock_logger.info.assert_called_once_with(
            "WebSocket connection closed. Total connections: 0"
        )

    @pytest.mark.asyncio
    async def test_disconnect_duplicate_websocket_entries(self, connection_manager, mock_websocket):
        """Test disconnecting when the same websocket was connected multiple times."""
        # Setup - connect same websocket twice
        await connection_manager.connect(mock_websocket)
        await connection_manager.connect(mock_websocket)
        assert connection_manager.connection_count == 2

        # Execute - disconnect once
        connection_manager.disconnect(mock_websocket)

        # Verify - should remove only one instance
        assert connection_manager.connection_count == 1
        assert mock_websocket in connection_manager.active_connections


class TestSendPersonalMessage:
    """Test the send_personal_message method."""

    @pytest.mark.asyncio
    async def test_send_personal_message_success(self, connection_manager, mock_websocket):
        """Test successfully sending a personal message."""
        # Setup
        await connection_manager.connect(mock_websocket)
        message = "Hello, user!"

        # Execute
        await connection_manager.send_personal_message(message, mock_websocket)

        # Verify
        mock_websocket.send_text.assert_called_once_with(message)
        # Connection should still be active
        assert mock_websocket in connection_manager.active_connections

    @pytest.mark.asyncio
    async def test_send_personal_message_websocket_error(self, connection_manager, mock_websocket):
        """Test handling error when sending personal message."""
        # Setup
        await connection_manager.connect(mock_websocket)
        mock_websocket.send_text.side_effect = Exception("Send failed")
        message = "Hello, user!"

        # Execute
        await connection_manager.send_personal_message(message, mock_websocket)

        # Verify
        mock_websocket.send_text.assert_called_once_with(message)
        # Connection should be removed due to error
        assert mock_websocket not in connection_manager.active_connections
        assert connection_manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_send_personal_message_empty_string(self, connection_manager, mock_websocket):
        """Test sending an empty string as personal message."""
        # Setup
        await connection_manager.connect(mock_websocket)

        # Execute
        await connection_manager.send_personal_message("", mock_websocket)

        # Verify
        mock_websocket.send_text.assert_called_once_with("")
        assert mock_websocket in connection_manager.active_connections

    @pytest.mark.asyncio
    @patch('websocket.connection_manager.logger')
    async def test_send_personal_message_logs_error(self, mock_logger, connection_manager, mock_websocket):
        """Test that send_personal_message logs errors appropriately."""
        # Setup
        await connection_manager.connect(mock_websocket)
        error_msg = "Connection broken"
        mock_websocket.send_text.side_effect = Exception(error_msg)

        # Execute
        await connection_manager.send_personal_message("test", mock_websocket)

        # Verify logging
        mock_logger.error.assert_called_once_with(
            f"Error sending message to WebSocket: {error_msg}")


class TestSendJsonMessage:
    """Test the send_json_message method."""

    @pytest.mark.asyncio
    async def test_send_json_message_success(self, connection_manager, mock_websocket, sample_json_data):
        """Test successfully sending a JSON message."""
        # Setup
        await connection_manager.connect(mock_websocket)

        # Execute
        await connection_manager.send_json_message(sample_json_data, mock_websocket)

        # Verify
        expected_message = json.dumps(sample_json_data)
        mock_websocket.send_text.assert_called_once_with(expected_message)
        assert mock_websocket in connection_manager.active_connections

    @pytest.mark.asyncio
    async def test_send_json_message_websocket_error(self, connection_manager, mock_websocket, sample_json_data):
        """Test handling error when sending JSON message."""
        # Setup
        await connection_manager.connect(mock_websocket)
        mock_websocket.send_text.side_effect = Exception("Send failed")

        # Execute
        await connection_manager.send_json_message(sample_json_data, mock_websocket)

        # Verify
        expected_message = json.dumps(sample_json_data)
        mock_websocket.send_text.assert_called_once_with(expected_message)
        # Connection should be removed due to error
        assert mock_websocket not in connection_manager.active_connections

    @pytest.mark.asyncio
    async def test_send_json_message_empty_dict(self, connection_manager, mock_websocket):
        """Test sending an empty dictionary as JSON message."""
        # Setup
        await connection_manager.connect(mock_websocket)
        empty_data = {}

        # Execute
        await connection_manager.send_json_message(empty_data, mock_websocket)

        # Verify
        expected_message = json.dumps(empty_data)
        mock_websocket.send_text.assert_called_once_with(expected_message)
        assert mock_websocket in connection_manager.active_connections

    @pytest.mark.asyncio
    async def test_send_json_message_complex_data(self, connection_manager, mock_websocket):
        """Test sending complex nested JSON data."""
        # Setup
        await connection_manager.connect(mock_websocket)
        complex_data = {
            "nested": {
                "array": [1, 2, 3],
                "boolean": True,
                "null_value": None
            },
            "unicode": "Hello 🌍"
        }

        # Execute
        await connection_manager.send_json_message(complex_data, mock_websocket)

        # Verify
        expected_message = json.dumps(complex_data)
        mock_websocket.send_text.assert_called_once_with(expected_message)

    @pytest.mark.asyncio
    @patch('websocket.connection_manager.logger')
    async def test_send_json_message_logs_error(self, mock_logger, connection_manager, mock_websocket):
        """Test that send_json_message logs errors appropriately."""
        # Setup
        await connection_manager.connect(mock_websocket)
        error_msg = "JSON send failed"
        mock_websocket.send_text.side_effect = Exception(error_msg)

        # Execute
        await connection_manager.send_json_message({"test": "data"}, mock_websocket)

        # Verify logging
        mock_logger.error.assert_called_once_with(
            f"Error sending JSON message to WebSocket: {error_msg}")


class TestBroadcast:
    """Test the broadcast method."""

    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_connections(self, connection_manager, mock_websocket_list):
        """Test broadcasting message to multiple connections."""
        # Setup - connect all websockets
        for ws in mock_websocket_list:
            await connection_manager.connect(ws)

        message = "Broadcast message"

        # Execute
        await connection_manager.broadcast(message)

        # Verify - all websockets should receive the message
        for ws in mock_websocket_list:
            ws.send_text.assert_called_once_with(message)

        # All connections should remain active
        assert connection_manager.connection_count == len(mock_websocket_list)

    @pytest.mark.asyncio
    async def test_broadcast_to_empty_connection_list(self, connection_manager):
        """Test broadcasting when no connections exist."""
        # Execute - should not raise an exception
        await connection_manager.broadcast("No one to receive this")

        # Verify - no connections affected
        assert connection_manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_broadcast_with_some_failed_connections(self, connection_manager, mock_websocket_list):
        """Test broadcasting when some connections fail."""
        # Setup - connect all websockets
        for ws in mock_websocket_list:
            await connection_manager.connect(ws)

        # Make the second websocket fail
        mock_websocket_list[1].send_text.side_effect = Exception(
            "Connection failed")

        message = "Broadcast message"

        # Execute
        await connection_manager.broadcast(message)

        # Verify - all websockets attempted to receive the message
        for ws in mock_websocket_list:
            ws.send_text.assert_called_once_with(message)

        # Failed connection should be removed
        assert mock_websocket_list[1] not in connection_manager.active_connections
        assert connection_manager.connection_count == len(
            mock_websocket_list) - 1

        # Other connections should remain
        assert mock_websocket_list[0] in connection_manager.active_connections
        assert mock_websocket_list[2] in connection_manager.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_all_connections_fail(self, connection_manager, mock_websocket_list):
        """Test broadcasting when all connections fail."""
        # Setup - connect all websockets
        for ws in mock_websocket_list:
            await connection_manager.connect(ws)

        # Make all websockets fail
        for ws in mock_websocket_list:
            ws.send_text.side_effect = Exception("All connections failed")

        # Execute
        await connection_manager.broadcast("This will fail")

        # Verify - all connections should be removed
        assert connection_manager.connection_count == 0
        for ws in mock_websocket_list:
            assert ws not in connection_manager.active_connections

    @pytest.mark.asyncio
    @patch('websocket.connection_manager.logger')
    async def test_broadcast_logs_errors(self, mock_logger, connection_manager, mock_websocket):
        """Test that broadcast logs errors appropriately."""
        # Setup
        await connection_manager.connect(mock_websocket)
        error_msg = "Broadcast failed"
        mock_websocket.send_text.side_effect = Exception(error_msg)

        # Execute
        await connection_manager.broadcast("test message")

        # Verify logging
        mock_logger.error.assert_called_once_with(
            f"Error broadcasting to WebSocket: {error_msg}")


class TestBroadcastJson:
    """Test the broadcast_json method."""

    @pytest.mark.asyncio
    async def test_broadcast_json_to_multiple_connections(self, connection_manager, mock_websocket_list, sample_json_data):
        """Test broadcasting JSON message to multiple connections."""
        # Setup - connect all websockets
        for ws in mock_websocket_list:
            await connection_manager.connect(ws)

        # Execute
        await connection_manager.broadcast_json(sample_json_data)

        # Verify - all websockets should receive the JSON message
        expected_message = json.dumps(sample_json_data)
        for ws in mock_websocket_list:
            ws.send_text.assert_called_once_with(expected_message)

    @pytest.mark.asyncio
    async def test_broadcast_json_empty_dict(self, connection_manager, mock_websocket):
        """Test broadcasting empty JSON object."""
        # Setup
        await connection_manager.connect(mock_websocket)

        # Execute
        await connection_manager.broadcast_json({})

        # Verify
        expected_message = json.dumps({})
        mock_websocket.send_text.assert_called_once_with(expected_message)

    @pytest.mark.asyncio
    async def test_broadcast_json_to_empty_connection_list(self, connection_manager, sample_json_data):
        """Test broadcasting JSON when no connections exist."""
        # Execute - should not raise an exception
        await connection_manager.broadcast_json(sample_json_data)

        # Verify - no connections affected
        assert connection_manager.connection_count == 0


class TestConnectionCount:
    """Test the connection_count property."""

    @pytest.mark.asyncio
    async def test_connection_count_initially_zero(self, connection_manager):
        """Test that connection count starts at zero."""
        assert connection_manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_connection_count_increases_with_connections(self, connection_manager, mock_websocket_list):
        """Test that connection count increases as connections are added."""
        for i, ws in enumerate(mock_websocket_list):
            await connection_manager.connect(ws)
            assert connection_manager.connection_count == i + 1

    @pytest.mark.asyncio
    async def test_connection_count_decreases_with_disconnections(self, connection_manager, mock_websocket_list):
        """Test that connection count decreases as connections are removed."""
        # Setup - connect all
        for ws in mock_websocket_list:
            await connection_manager.connect(ws)

        initial_count = connection_manager.connection_count

        # Disconnect one by one
        for i, ws in enumerate(mock_websocket_list):
            connection_manager.disconnect(ws)
            assert connection_manager.connection_count == initial_count - \
                (i + 1)


class TestConnectionManagerIntegration:
    """Integration tests for ConnectionManager."""

    @pytest.mark.asyncio
    async def test_full_connection_lifecycle(self, connection_manager, mock_websocket):
        """Test complete connection lifecycle: connect, send messages, disconnect."""
        # Connect
        await connection_manager.connect(mock_websocket)
        assert connection_manager.connection_count == 1

        # Send personal message
        await connection_manager.send_personal_message("Hello", mock_websocket)
        mock_websocket.send_text.assert_called_with("Hello")

        # Send JSON message
        json_data = {"type": "test", "data": "value"}
        await connection_manager.send_json_message(json_data, mock_websocket)
        expected_json = json.dumps(json_data)
        mock_websocket.send_text.assert_called_with(expected_json)

        # Disconnect
        connection_manager.disconnect(mock_websocket)
        assert connection_manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_multiple_connections_with_broadcast(self, connection_manager, mock_websocket_list):
        """Test managing multiple connections and broadcasting."""
        # Connect multiple websockets
        for ws in mock_websocket_list:
            await connection_manager.connect(ws)

        assert connection_manager.connection_count == len(mock_websocket_list)

        # Broadcast text message
        await connection_manager.broadcast("Hello everyone")
        for ws in mock_websocket_list:
            ws.send_text.assert_called_with("Hello everyone")

        # Reset mocks for next assertion
        for ws in mock_websocket_list:
            ws.send_text.reset_mock()

        # Broadcast JSON message
        json_data = {"announcement": "Server maintenance"}
        await connection_manager.broadcast_json(json_data)
        expected_json = json.dumps(json_data)
        for ws in mock_websocket_list:
            ws.send_text.assert_called_with(expected_json)

        # Disconnect all
        for ws in mock_websocket_list:
            connection_manager.disconnect(ws)

        assert connection_manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_error_recovery_and_cleanup(self, connection_manager, mock_websocket_list):
        """Test error handling and automatic cleanup during operations."""
        # Connect all websockets
        for ws in mock_websocket_list:
            await connection_manager.connect(ws)

        # Make middle connection fail during personal message
        failing_ws = mock_websocket_list[1]
        failing_ws.send_text.side_effect = Exception("Connection lost")

        # Send personal message - should remove failing connection
        await connection_manager.send_personal_message("Test", failing_ws)
        assert failing_ws not in connection_manager.active_connections
        assert connection_manager.connection_count == len(
            mock_websocket_list) - 1

        # Reset the failing websocket for broadcast test
        failing_ws.send_text.side_effect = Exception("Still failing")
        connection_manager.active_connections.append(
            failing_ws)  # Re-add for test

        # Broadcast should remove failing connections
        await connection_manager.broadcast("Broadcast test")
        assert failing_ws not in connection_manager.active_connections

        # Other connections should remain
        working_connections = [
            ws for ws in mock_websocket_list if ws != failing_ws]
        for ws in working_connections:
            assert ws in connection_manager.active_connections


class TestConnectionManagerEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_send_message_to_disconnected_websocket(self, connection_manager, mock_websocket):
        """Test sending message to websocket that's not in active connections."""
        # Don't connect the websocket, just try to send
        await connection_manager.send_personal_message("Test", mock_websocket)

        # Should still attempt to send (no pre-check for active connections)
        mock_websocket.send_text.assert_called_once_with("Test")

    @pytest.mark.asyncio
    async def test_very_large_json_data(self, connection_manager, mock_websocket):
        """Test handling of large JSON data."""
        # Setup
        await connection_manager.connect(mock_websocket)

        # Create large data structure
        large_data = {
            "items": [{"id": i, "data": "x" * 100} for i in range(1000)]
        }

        # Execute
        await connection_manager.send_json_message(large_data, mock_websocket)

        # Verify
        expected_message = json.dumps(large_data)
        mock_websocket.send_text.assert_called_once_with(expected_message)

    @pytest.mark.asyncio
    async def test_special_characters_in_messages(self, connection_manager, mock_websocket):
        """Test handling of special characters and unicode in messages."""
        # Setup
        await connection_manager.connect(mock_websocket)

        # Test various special characters
        special_message = "Hello 🌍! Special chars: àáâãäåæçèéêë ñ ™ © ® 中文 العربية"

        # Execute
        await connection_manager.send_personal_message(special_message, mock_websocket)

        # Verify
        mock_websocket.send_text.assert_called_once_with(special_message)

    @pytest.mark.asyncio
    @patch('websocket.connection_manager.logger')
    async def test_logging_with_multiple_operations(self, mock_logger, connection_manager, mock_websocket_list):
        """Test that logging works correctly with multiple operations."""
        # Connect multiple websockets
        for ws in mock_websocket_list:
            await connection_manager.connect(ws)

        # Verify connect logging
        assert mock_logger.info.call_count == len(mock_websocket_list)

        # Disconnect some websockets
        for i in range(2):
            connection_manager.disconnect(mock_websocket_list[i])

        # Verify total logging calls (connects + disconnects)
        expected_calls = len(mock_websocket_list) + 2
        assert mock_logger.info.call_count == expected_calls


# Pytest configuration and fixtures for the entire test module
@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all mocks between tests."""
    yield
    # Any cleanup can be done here if needed


if __name__ == "__main__":
    # Allow running tests directly with python -m pytest
    pytest.main([__file__])
