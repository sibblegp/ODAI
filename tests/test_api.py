"""
Comprehensive tests for api.py with proper isolation.

Tests are designed to prevent module conflicts with other tests.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.testclient import TestClient


class TestODAPIApplication:
    """Test ODAPIApplication class and endpoints."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Set up mocks for each test."""
        self.mock_settings = Mock()
        self.mock_settings.production = False
        self.mock_settings.openai_api_key = "test-key"
        
        self.mock_settings_class = Mock(return_value=self.mock_settings)
        self.mock_cors = Mock()
        self.mock_cors.get_development_origins.return_value = ["*"]
        self.mock_cors.get_production_origins.return_value = ["https://odai.com"]
        
        self.patches = [
            patch('agents.set_tracing_export_api_key'),
            patch('openai.OpenAI'),
            patch('utils.imports.get_settings', return_value=self.mock_settings_class),
            patch('utils.imports.get_routers', return_value={}),
            patch('middleware.cors.CORSConfig', self.mock_cors),
            patch('services.chat_service.ChatService'),
            patch('services.api_service.APIService'),
            patch('websocket.connection_manager.ConnectionManager'),
            patch('websocket.handlers.WebSocketHandler'),
            patch('ingest_integrations.ingest_integrations'),
        ]
        
        # Start all patches
        for p in self.patches:
            p.start()
        
        yield
        
        # Stop all patches
        for p in self.patches:
            p.stop()
        
        # Clean up api module
        import sys
        if 'api' in sys.modules:
            del sys.modules['api']

    def test_initialization(self):
        """Test ODAPIApplication initialization."""
        import api
        
        assert hasattr(api, 'ODAPIApplication')
        assert hasattr(api, 'odai_app')
        assert hasattr(api.odai_app, 'app')
        assert isinstance(api.odai_app.app, FastAPI)

    def test_app_configuration(self):
        """Test FastAPI app configuration."""
        import api
        
        assert api.odai_app.app.title == "ODAI API"
        assert api.odai_app.app.description == "AI Assistant API with modular architecture"
        assert api.odai_app.app.redoc_url is None
        assert api.odai_app.app.docs_url is None
        assert api.odai_app.app.openapi_url is None

    def test_cors_configuration_dev(self):
        """Test CORS configuration in development mode."""
        import api
        
        self.mock_cors.get_development_origins.assert_called_once()
        self.mock_cors.add_cors_middleware.assert_called_once()

    def test_cors_configuration_prod(self):
        """Test CORS configuration in production mode."""
        # Update settings for production
        self.mock_settings.production = True
        
        # Reimport api module
        import sys
        if 'api' in sys.modules:
            del sys.modules['api']
        
        import api
        
        self.mock_cors.get_production_origins.assert_called_once()
        self.mock_cors.add_cors_middleware.assert_called_once()

    def test_root_endpoint_dev(self):
        """Test root endpoint in development mode."""
        import api
        
        client = TestClient(api.app)
        
        with patch('api.FileResponse') as mock_file_response:
            mock_file_response.return_value.status_code = 200
            mock_file_response.return_value.headers = {}
            
            response = client.get("/")
            
            assert response.status_code == 200
            mock_file_response.assert_called_once_with("static/index.html")

    def test_root_endpoint_prod(self):
        """Test root endpoint in production mode."""
        # Update settings for production
        self.mock_settings.production = True
        
        # Reimport api module
        import sys
        if 'api' in sys.modules:
            del sys.modules['api']
        
        import api
        
        client = TestClient(api.app)
        response = client.get("/", follow_redirects=False)
        
        assert response.status_code == 307
        assert response.headers["location"] == "https://odai.com"

    def test_health_check_endpoint(self):
        """Test /test health check endpoint."""
        with patch('websocket.connection_manager.ConnectionManager') as mock_conn_mgr_class:
            mock_conn_mgr = Mock()
            mock_conn_mgr.connection_count = 10
            mock_conn_mgr_class.return_value = mock_conn_mgr
            
            # Reimport to get new mock
            import sys
            if 'api' in sys.modules:
                del sys.modules['api']
            
            import api
            
            client = TestClient(api.app)
            response = client.get("/test")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["service"] == "ODAI API"
            assert data["environment"] == "development"
            assert data["connections"] == 10

    def test_waitlist_endpoint_success(self):
        """Test /waitlist endpoint with successful submission."""
        with patch('services.chat_service.ChatService') as mock_chat_service_class, \
             patch('services.api_service.APIService') as mock_api_service_class:
            mock_chat_service = Mock()
            mock_chat_service_class.return_value = mock_chat_service
            
            mock_api_service = Mock()
            mock_api_service.add_email_to_waitlist = Mock()
            mock_api_service_class.return_value = mock_api_service
            
            # Reimport to get new mock
            import sys
            if 'api' in sys.modules:
                del sys.modules['api']
            
            import api
            
            client = TestClient(api.app)
            response = client.post("/waitlist", data={"email": "test@example.com"})
            
            assert response.status_code == 200
            assert response.json() == {"status": "success"}
            mock_api_service.add_email_to_waitlist.assert_called_once_with("test@example.com")

    def test_waitlist_endpoint_error(self):
        """Test /waitlist endpoint with error."""
        with patch('services.chat_service.ChatService') as mock_chat_service_class, \
             patch('services.api_service.APIService') as mock_api_service_class:
            mock_chat_service = Mock()
            mock_chat_service_class.return_value = mock_chat_service
            
            mock_api_service = Mock()
            mock_api_service.add_email_to_waitlist = Mock(side_effect=Exception("DB Error"))
            mock_api_service_class.return_value = mock_api_service
            
            # Reimport to get new mock
            import sys
            if 'api' in sys.modules:
                del sys.modules['api']
            
            import api
            
            client = TestClient(api.app)
            response = client.post("/waitlist", data={"email": "test@example.com"})
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert "Failed to add email to waitlist" in data["message"]

    def test_email_endpoint(self):
        """Test /email endpoint (alias for waitlist)."""
        with patch('services.chat_service.ChatService') as mock_chat_service_class, \
             patch('services.api_service.APIService') as mock_api_service_class:
            mock_chat_service = Mock()
            mock_chat_service_class.return_value = mock_chat_service
            
            mock_api_service = Mock()
            mock_api_service.add_email_to_waitlist = Mock()
            mock_api_service_class.return_value = mock_api_service
            
            # Reimport to get new mock
            import sys
            if 'api' in sys.modules:
                del sys.modules['api']
            
            import api
            
            client = TestClient(api.app)
            response = client.post("/email", data={"email": "test@example.com"})
            
            assert response.status_code == 200
            assert response.json() == {"status": "success"}
            mock_api_service.add_email_to_waitlist.assert_called_with("test@example.com")

    def test_google_access_request_endpoint(self):
        """Test /google_access_request endpoint."""
        with patch('services.chat_service.ChatService') as mock_chat_service_class, \
             patch('services.api_service.APIService') as mock_api_service_class:
            mock_chat_service = Mock()
            mock_chat_service_class.return_value = mock_chat_service
            
            mock_api_service = Mock()
            mock_api_service.request_google_access = Mock(return_value={"status": "success", "data": "test"})
            mock_api_service_class.return_value = mock_api_service
            
            # Reimport to get new mock
            import sys
            if 'api' in sys.modules:
                del sys.modules['api']
            
            import api
            
            client = TestClient(api.app)
            response = client.post(
                "/google_access_request",
                headers={"authorization": "Bearer token123"},
                data={"email": "test@example.com"}
            )
            
            assert response.status_code == 200
            assert response.json() == {"status": "success", "data": "test"}
            mock_api_service.request_google_access.assert_called_once_with(
                False, "Bearer token123", "test@example.com"
            )

    def test_update_integrations_endpoint(self):
        """Test /update_integrations endpoint."""
        import api
        
        client = TestClient(api.app)
        response = client.get("/update_integrations")
        
        assert response.status_code == 200
        assert response.json() == {"status": "success"}

    def test_reset_plaid_tokens_endpoint_success(self):
        """Test /reset_plaid_tokens endpoint successful case."""
        with patch('services.chat_service.ChatService') as mock_chat_service_class, \
             patch('services.api_service.APIService') as mock_api_service_class:
            mock_chat_service = Mock()
            mock_chat_service_class.return_value = mock_chat_service
            
            mock_api_service = Mock()
            mock_api_service.reset_plaid_tokens = Mock(return_value=True)
            mock_api_service_class.return_value = mock_api_service
            
            # Reimport to get new mock
            import sys
            if 'api' in sys.modules:
                del sys.modules['api']
            
            import api
            # Set to non-production for testing
            api.odai_app.settings.production = False
            
            client = TestClient(api.app)
            response = client.post(
                "/reset_plaid_tokens",
                headers={"authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 200
            assert response.json() == {"status": "success"}
            mock_api_service.reset_plaid_tokens.assert_called_once_with("Bearer test_token")

    def test_reset_plaid_tokens_endpoint_production(self):
        """Test /reset_plaid_tokens endpoint in production mode."""
        with patch('services.chat_service.ChatService') as mock_chat_service_class, \
             patch('services.api_service.APIService') as mock_api_service_class:
            mock_chat_service = Mock()
            mock_chat_service_class.return_value = mock_chat_service
            
            mock_api_service = Mock()
            mock_api_service_class.return_value = mock_api_service
            
            # Reimport to get new mock
            import sys
            if 'api' in sys.modules:
                del sys.modules['api']
            
            import api
            # Set to production mode
            api.odai_app.settings.production = True
            
            client = TestClient(api.app)
            response = client.post(
                "/reset_plaid_tokens",
                headers={"authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 404
            mock_api_service.reset_plaid_tokens.assert_not_called()

    def test_reset_plaid_tokens_endpoint_missing_auth(self):
        """Test /reset_plaid_tokens endpoint with missing authorization."""
        import sys
        if 'api' in sys.modules:
            del sys.modules['api']
        
        import api
        
        client = TestClient(api.app)
        response = client.post("/reset_plaid_tokens")
        
        # Should return 422 for missing required header
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_websocket_endpoint(self):
        """Test WebSocket endpoint."""
        with patch('websocket.handlers.WebSocketHandler') as mock_ws_handler_class:
            mock_ws_handler = AsyncMock()
            mock_ws_handler.handle_websocket_connection = AsyncMock()
            mock_ws_handler_class.return_value = mock_ws_handler
            
            # Reimport to get new mock
            import sys
            if 'api' in sys.modules:
                del sys.modules['api']
            
            import api
            
            # Get the websocket endpoint function from the app's routes
            websocket_route = None
            for route in api.app.routes:
                if hasattr(route, 'path') and route.path == "/chats/{chat_id}":
                    websocket_route = route
                    break
            
            assert websocket_route is not None, "WebSocket route not found"
            
            # Mock the websocket
            mock_websocket = Mock(spec=WebSocket)
            mock_websocket.accept = AsyncMock()
            mock_websocket.send_text = AsyncMock()
            mock_websocket.receive_text = AsyncMock()
            
            # Call the endpoint function directly
            await websocket_route.endpoint(
                websocket=mock_websocket,
                chat_id="test-chat-id",
                token="test-token",
                x_forwarded_for=None,
                cf_connecting_ip=None
            )
            
            # Verify handler was called
            mock_ws_handler.handle_websocket_connection.assert_called_once()
            call_args = mock_ws_handler.handle_websocket_connection.call_args
            assert call_args[1]["chat_id"] == "test-chat-id"
            assert call_args[1]["token"] == "test-token"

    @pytest.mark.asyncio
    async def test_websocket_disconnect_handling(self):
        """Test WebSocket disconnect handling."""
        with patch('websocket.handlers.WebSocketHandler') as mock_ws_handler_class:
            mock_ws_handler = AsyncMock()
            mock_ws_handler.handle_websocket_connection = AsyncMock(side_effect=WebSocketDisconnect())
            mock_ws_handler_class.return_value = mock_ws_handler
            
            # Reimport to get new mock
            import sys
            if 'api' in sys.modules:
                del sys.modules['api']
            
            import api
            
            # Get the websocket endpoint function
            websocket_route = None
            for route in api.app.routes:
                if hasattr(route, 'path') and route.path == "/chats/{chat_id}":
                    websocket_route = route
                    break
            
            assert websocket_route is not None
            
            # Mock websocket
            mock_websocket = Mock(spec=WebSocket)
            
            # Call endpoint directly - should handle disconnect gracefully
            await websocket_route.endpoint(
                websocket=mock_websocket,
                chat_id="test-chat-id",
                token="test-token",
                x_forwarded_for=None,
                cf_connecting_ip=None
            )
            
            # Verify handler was called
            mock_ws_handler.handle_websocket_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_error_handling(self):
        """Test WebSocket error handling."""
        with patch('websocket.handlers.WebSocketHandler') as mock_ws_handler_class:
            mock_ws_handler = AsyncMock()
            mock_ws_handler.handle_websocket_connection = AsyncMock(side_effect=Exception("Test error"))
            mock_ws_handler_class.return_value = mock_ws_handler
            
            # Reimport to get new mock
            import sys
            if 'api' in sys.modules:
                del sys.modules['api']
            
            import api
            
            # Get the websocket endpoint function
            websocket_route = None
            for route in api.app.routes:
                if hasattr(route, 'path') and route.path == "/chats/{chat_id}":
                    websocket_route = route
                    break
            
            assert websocket_route is not None
            
            # Mock websocket
            mock_websocket = Mock(spec=WebSocket)
            
            # Call endpoint directly - should handle error gracefully
            await websocket_route.endpoint(
                websocket=mock_websocket,
                chat_id="test-chat-id",
                token="test-token",
                x_forwarded_for=None,
                cf_connecting_ip=None
            )
            
            # Verify handler was called despite the error
            mock_ws_handler.handle_websocket_connection.assert_called_once()

    def test_get_app_method(self):
        """Test get_app method returns FastAPI instance."""
        import api
        
        fastapi_app = api.odai_app.get_app()
        
        assert isinstance(fastapi_app, FastAPI)
        assert fastapi_app == api.odai_app.app

    def test_module_exports(self):
        """Test module-level exports."""
        import api
        
        # Verify exports
        assert hasattr(api, 'odai_app')
        assert hasattr(api, 'APP')
        assert hasattr(api, 'app')
        assert hasattr(api, 'manager')
        
        # Verify relationships
        assert api.APP == api.app
        assert api.APP == api.odai_app.get_app()
        assert api.manager == api.odai_app.connection_manager

    def test_logging_configuration(self):
        """Test that logging is configured."""
        import api
        
        # Verify logging setup
        assert hasattr(api, 'logger')
        assert api.logger is not None