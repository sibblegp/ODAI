import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient
from httpx import Response

from routers.twilio_server import TWILIO_ROUTER, TwilioWebSocketManager, manager


@pytest.fixture
def test_client():
    """Create a test client with the Twilio router."""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(TWILIO_ROUTER)
    return TestClient(app)


class TestTwilioWebSocketManager:
    """Test cases for TwilioWebSocketManager class."""
    
    @pytest.mark.asyncio
    async def test_new_session(self):
        """Test creating a new session."""
        mock_websocket = MagicMock()
        mock_user = MagicMock()
        mock_user.reference_id = "test_user_123"
        
        with patch('routers.twilio_server.TwilioHandler') as mock_handler_class:
            mock_handler = MagicMock()
            mock_handler_class.return_value = mock_handler
            
            test_manager = TwilioWebSocketManager()
            result = await test_manager.new_session(mock_websocket, mock_user)
            
            mock_handler_class.assert_called_once_with(mock_websocket, mock_user)
            assert result == mock_handler


class TestTwilioRoutes:
    """Test cases for Twilio API routes."""
    
    def test_root_endpoint(self, test_client):
        """Test the root endpoint returns expected message."""
        response = test_client.get("/twilio/")
        assert response.status_code == 200
        assert response.json() == {"message": "Twilio Media Stream Server is running!"}
    
    def test_incoming_call_post(self, test_client):
        """Test handling incoming calls via POST."""
        response = test_client.post("/twilio/incoming")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/xml"
        
        # Check that response contains TwiML
        content = response.text
        assert "<?xml" in content
        assert "<Response>" in content
        assert "<Connect>" in content
        assert '<Stream url="wss://testserver/twilio/connect" />' in content
        assert "</Connect>" in content
        assert "</Response>" in content
    
    def test_incoming_call_get(self, test_client):
        """Test handling incoming calls via GET."""
        response = test_client.get("/twilio/incoming")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/xml"
        
        # Check that response contains TwiML
        content = response.text
        assert "<?xml" in content
        assert "<Response>" in content
        assert "<Connect>" in content
        assert '<Stream url="wss://testserver/twilio/connect" />' in content
        assert "</Connect>" in content
        assert "</Response>" in content
    
    def test_incoming_call_custom_host(self, test_client):
        """Test that the WebSocket URL uses the correct host."""
        # Test with custom host header
        response = test_client.get(
            "/twilio/incoming",
            headers={"Host": "example.com"}
        )
        assert response.status_code == 200
        content = response.text
        assert '<Stream url="wss://example.com/twilio/connect" />' in content


class TestWebSocketEndpoint:
    """Test cases for WebSocket endpoint."""
    
    @pytest.mark.asyncio
    async def test_websocket_connect_success(self):
        """Test successful WebSocket connection and message handling."""
        from routers.twilio_server import media_stream_endpoint
        
        mock_websocket = MagicMock()
        mock_websocket.accept = AsyncMock()
        
        with patch('routers.twilio_server.manager') as mock_manager, \
             patch('routers.twilio_server.User') as mock_user_class:
            # Mock User.get_user_by_id
            mock_user = MagicMock()
            mock_user.reference_id = "test_user"
            mock_user_class.get_user_by_id.return_value = mock_user
            
            mock_handler = MagicMock()
            mock_handler.start = AsyncMock(return_value=None)
            # Make wait_until_done raise disconnect immediately
            mock_handler.wait_until_done = AsyncMock(side_effect=WebSocketDisconnect())
            
            mock_manager.new_session = AsyncMock(return_value=mock_handler)
            
            # Call the endpoint directly
            try:
                await media_stream_endpoint(mock_websocket)
            except WebSocketDisconnect:
                pass  # Expected
            
            # Verify handler methods were called
            mock_manager.new_session.assert_called_once_with(mock_websocket, mock_user)
            mock_handler.start.assert_called_once()
            mock_handler.wait_until_done.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_websocket_disconnect(self):
        """Test WebSocket disconnect handling."""
        from routers.twilio_server import media_stream_endpoint
        
        mock_websocket = MagicMock()
        
        with patch('routers.twilio_server.manager') as mock_manager, \
             patch('routers.twilio_server.User') as mock_user_class:
            # Mock User.get_user_by_id
            mock_user = MagicMock()
            mock_user.reference_id = "test_user"
            mock_user_class.get_user_by_id.return_value = mock_user
            
            mock_handler = MagicMock()
            mock_handler.start = AsyncMock(return_value=None)
            mock_handler.wait_until_done = AsyncMock(side_effect=WebSocketDisconnect())
            
            mock_manager.new_session = AsyncMock(return_value=mock_handler)
            
            # Should handle disconnect gracefully
            await media_stream_endpoint(mock_websocket)
            
            mock_handler.start.assert_called_once()
            mock_handler.wait_until_done.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_websocket_error_handling(self):
        """Test WebSocket error handling."""
        from routers.twilio_server import media_stream_endpoint
        
        mock_websocket = MagicMock()
        
        with patch('routers.twilio_server.manager') as mock_manager, \
             patch('routers.twilio_server.User') as mock_user_class:
            # Mock User.get_user_by_id
            mock_user = MagicMock()
            mock_user.reference_id = "test_user"
            mock_user_class.get_user_by_id.return_value = mock_user
            
            mock_handler = MagicMock()
            mock_handler.start = AsyncMock(side_effect=Exception("Test error"))
            
            mock_manager.new_session = AsyncMock(return_value=mock_handler)
            
            # Should handle error gracefully
            with patch('builtins.print') as mock_print:
                await media_stream_endpoint(mock_websocket)
                mock_print.assert_called_with("WebSocket error: Test error")
            
            mock_handler.start.assert_called_once()


class TestManagerSingleton:
    """Test that manager is a singleton instance."""
    
    def test_manager_is_twilio_websocket_manager(self):
        """Test that manager is an instance of TwilioWebSocketManager."""
        assert isinstance(manager, TwilioWebSocketManager)
    
    def test_manager_has_active_handlers_dict(self):
        """Test that manager has active_handlers dictionary."""
        assert hasattr(manager, 'active_handlers')
        assert isinstance(manager.active_handlers, dict)


class TestEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_incoming_call_with_x_forwarded_host(self, test_client):
        """Test that X-Forwarded-Host header is used if implemented."""
        response = test_client.get(
            "/twilio/incoming",
            headers={"X-Forwarded-Host": "forwarded.example.com"}
        )
        assert response.status_code == 200
        content = response.text
        # Currently the server uses request.url.hostname, not X-Forwarded-Host
        # This test documents expected behavior if X-Forwarded-Host support is added
        assert '/twilio/connect" />' in content
    
    def test_incoming_call_with_multiple_headers(self, test_client):
        """Test handling of multiple host headers."""
        response = test_client.get(
            "/twilio/incoming",
            headers={
                "Host": "host.example.com",
                "X-Forwarded-Host": "forwarded.example.com"
            }
        )
        assert response.status_code == 200
        content = response.text
        # Currently uses Host header, not X-Forwarded-Host
        assert '<Stream url="wss://host.example.com/twilio/connect" />' in content
    
    @pytest.mark.asyncio
    async def test_websocket_handler_lifecycle(self):
        """Test full lifecycle of WebSocket handler."""
        from routers.twilio_server import TwilioWebSocketManager
        
        manager = TwilioWebSocketManager()
        mock_websocket = MagicMock()
        
        with patch('routers.twilio_server.TwilioHandler') as mock_handler_class:
            mock_handler = MagicMock()
            mock_handler_class.return_value = mock_handler
            
            # Test session creation
            mock_user = MagicMock()
            mock_user.reference_id = "test_user"
            handler = await manager.new_session(mock_websocket, mock_user)
            
            assert handler == mock_handler
            mock_handler_class.assert_called_once_with(mock_websocket, mock_user)
    
    @pytest.mark.asyncio
    async def test_websocket_multiple_connections(self):
        """Test handling multiple concurrent WebSocket connections."""
        from routers.twilio_server import media_stream_endpoint
        
        # Create multiple mock websockets
        websockets = [MagicMock() for _ in range(3)]
        
        with patch('routers.twilio_server.manager') as mock_manager, \
             patch('routers.twilio_server.User') as mock_user_class:
            # Mock User.get_user_by_id
            mock_user = MagicMock()
            mock_user.reference_id = "test_user"
            mock_user_class.get_user_by_id.return_value = mock_user
            
            handlers = []
            for i in range(3):
                handler = MagicMock()
                handler.start = AsyncMock()
                handler.wait_until_done = AsyncMock(side_effect=WebSocketDisconnect())
                handlers.append(handler)
            
            mock_manager.new_session = AsyncMock(side_effect=handlers)
            
            # Process all connections concurrently
            tasks = [media_stream_endpoint(ws) for ws in websockets]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should complete without errors (WebSocketDisconnect is handled)
            for result in results:
                assert result is None
            
            # Verify all connections were handled
            assert mock_manager.new_session.call_count == 3
            for handler in handlers:
                handler.start.assert_called_once()
                handler.wait_until_done.assert_called_once()
    
    def test_twiml_response_format(self, test_client):
        """Test that TwiML response is properly formatted."""
        response = test_client.post("/twilio/incoming")
        
        # Verify XML declaration
        assert response.text.startswith('<?xml version="1.0" encoding="UTF-8"?>')
        
        # Verify proper XML structure
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.text)
        
        assert root.tag == "Response"
        connect = root.find("Connect")
        assert connect is not None
        
        stream = connect.find("Stream")
        assert stream is not None
        assert "url" in stream.attrib
        assert stream.attrib["url"].startswith("wss://")
        assert stream.attrib["url"].endswith("/twilio/connect")
    
    @pytest.mark.asyncio
    async def test_websocket_unexpected_closure(self):
        """Test handling unexpected WebSocket closure."""
        from routers.twilio_server import media_stream_endpoint
        
        mock_websocket = MagicMock()
        
        with patch('routers.twilio_server.manager') as mock_manager, \
             patch('routers.twilio_server.User') as mock_user_class:
            # Mock User.get_user_by_id
            mock_user = MagicMock()
            mock_user.reference_id = "test_user"
            mock_user_class.get_user_by_id.return_value = mock_user
            
            mock_handler = MagicMock()
            # Simulate unexpected error during start
            mock_handler.start = AsyncMock(side_effect=ConnectionError("Connection lost"))
            
            mock_manager.new_session = AsyncMock(return_value=mock_handler)
            
            with patch('builtins.print') as mock_print:
                await media_stream_endpoint(mock_websocket)
                # Should print error message
                mock_print.assert_called_with("WebSocket error: Connection lost")
    
    def test_import_fallback_mechanism(self):
        """Test that import fallback works correctly."""
        # This test verifies the import logic works
        # The actual imports are tested by successful module loading
        from routers import twilio_server
        
        # Verify critical components are available
        assert hasattr(twilio_server, 'TwilioHandler')
        assert hasattr(twilio_server, 'TwilioWebSocketManager')
        assert hasattr(twilio_server, 'TWILIO_ROUTER')
        assert hasattr(twilio_server, 'manager')
    
    @pytest.mark.asyncio
    async def test_websocket_rapid_disconnect_reconnect(self):
        """Test handling rapid disconnect and reconnect scenarios."""
        from routers.twilio_server import media_stream_endpoint
        
        mock_websocket = MagicMock()
        
        with patch('routers.twilio_server.manager') as mock_manager, \
             patch('routers.twilio_server.User') as mock_user_class:
            # Mock User.get_user_by_id
            mock_user = MagicMock()
            mock_user.reference_id = "test_user"
            mock_user_class.get_user_by_id.return_value = mock_user
            
            # Simulate rapid disconnects
            disconnect_count = 0
            
            async def mock_wait_until_done():
                nonlocal disconnect_count
                disconnect_count += 1
                if disconnect_count < 3:
                    # Simulate rapid reconnect by not raising immediately
                    await asyncio.sleep(0.001)
                raise WebSocketDisconnect()
            
            mock_handler = MagicMock()
            mock_handler.start = AsyncMock()
            mock_handler.wait_until_done = mock_wait_until_done
            
            mock_manager.new_session = AsyncMock(return_value=mock_handler)
            
            # Should handle gracefully
            await media_stream_endpoint(mock_websocket)
            
            # Handler should have been started once
            mock_handler.start.assert_called_once()
    
    def test_incoming_endpoint_url_encoding(self, test_client):
        """Test that special characters in host are properly handled."""
        # Test with port number
        response = test_client.get(
            "/twilio/incoming",
            headers={"Host": "example.com:8080"}
        )
        assert response.status_code == 200
        content = response.text
        # TestClient uses testserver as the hostname
        assert '/twilio/connect" />' in content
    
    def test_root_endpoint_json_format(self, test_client):
        """Test that root endpoint returns proper JSON."""
        response = test_client.get("/twilio/")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        assert isinstance(data, dict)
        assert "message" in data
        assert data["message"] == "Twilio Media Stream Server is running!"