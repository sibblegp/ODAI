"""WebSocket connection manager for handling multiple concurrent connections."""

import json
import logging
from typing import List

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for the application."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection and add it to active connections.
        
        Args:
            websocket: The WebSocket connection to accept and track
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            f"New WebSocket connection established. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from active connections.
        
        Args:
            websocket: The WebSocket connection to remove
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(
                f"WebSocket connection closed. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
        """Send a message to a specific WebSocket connection.
        
        Args:
            message: The text message to send
            websocket: The target WebSocket connection
        """
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending message to WebSocket: {e}")
            self.disconnect(websocket)

    async def send_json_message(self, data: dict, websocket: WebSocket) -> None:
        """Send a JSON message to a specific WebSocket connection.
        
        Args:
            data: Dictionary to serialize and send as JSON
            websocket: The target WebSocket connection
        """
        try:
            message = json.dumps(data)
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending JSON message to WebSocket: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str) -> None:
        """Send a message to all active WebSocket connections.
        
        Automatically removes connections that fail to receive the message.
        
        Args:
            message: The text message to broadcast
        """
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.append(connection)

        # Remove disconnected connections
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_json(self, data: dict) -> None:
        """Send a JSON message to all active WebSocket connections.
        
        Args:
            data: Dictionary to serialize and broadcast as JSON
        """
        message = json.dumps(data)
        await self.broadcast(message)

    @property
    def connection_count(self) -> int:
        """Get the number of active connections.
        
        Returns:
            int: Number of currently active WebSocket connections
        """
        return len(self.active_connections)
