"""
Refactored FastAPI application with improved modularity and maintainability.

This version separates concerns into dedicated services and handlers:
- Authentication logic -> services/auth_service.py
- Location detection -> services/location_service.py  
- Chat management -> services/chat_service.py
- WebSocket handling -> websocket/handlers.py
- Connection management -> websocket/connection_manager.py
- CORS configuration -> middleware/cors.py
- Import handling -> config/imports.py
"""

import logging
from typing import Annotated, Optional

from fastapi import FastAPI, Form, Header, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from openai import OpenAI
from agents import set_tracing_export_api_key

# Import our modular components
try:
    from utils.imports import get_settings, get_routers
    from middleware.cors import CORSConfig
    from services.chat_service import ChatService
    from services.api_service import APIService
    from websocket.connection_manager import ConnectionManager
    from websocket.handlers import WebSocketHandler
    from ingest_integrations import ingest_integrations
except ImportError:
    from .utils.imports import get_settings, get_routers
    from .middleware.cors import CORSConfig
    from .services.chat_service import ChatService
    from .services.api_service import APIService
    from .websocket.connection_manager import ConnectionManager
    from .websocket.handlers import WebSocketHandler
    from .ingest_integrations import ingest_integrations

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ODAPIApplication:
    """Main application class for ODAI API."""

    def __init__(self):
        """Initialize the ODAI application with all required services and configurations."""
        # Initialize settings
        Settings = get_settings()
        self.settings = Settings()

        # Set up OpenAI client and tracing
        set_tracing_export_api_key(self.settings.openai_api_key)
        self.openai_client = OpenAI(api_key=self.settings.openai_api_key)

        # Initialize services
        self.chat_service = ChatService()
        self.api_service = APIService()
        self.connection_manager = ConnectionManager()
        self.websocket_handler = WebSocketHandler(
            self.settings, self.openai_client, self.connection_manager
        )

        # Create FastAPI app
        self.app = self._create_app()

        # Set up routes
        self._setup_routes()

        logger.info(
            f"ODAI API initialized in {'production' if self.settings.production else 'development'} mode")

    def _create_app(self) -> FastAPI:
        """Create and configure the FastAPI application."""
        app = FastAPI(
            title="ODAI API",
            description="AI Assistant API with modular architecture",
            redoc_url=None,
            docs_url=None,
            openapi_url=None
        )

        # Add CORS middleware
        if self.settings.production:
            origins = CORSConfig.get_production_origins()
        else:
            origins = CORSConfig.get_development_origins()

        CORSConfig.add_cors_middleware(app, origins=origins)

        # Include routers
        routers = get_routers()
        for router_name, router in routers.items():
            app.include_router(router)
            logger.info(f"Included {router_name} router")

        return app

    def _setup_routes(self):
        """Set up application routes."""

        @self.app.get("/")
        async def root():
            """Root endpoint - serve static file or redirect based on environment."""
            if not self.settings.production:
                return FileResponse("static/index.html")
            else:
                return RedirectResponse(url="https://odai.com")

        @self.app.websocket("/chats/{chat_id}")
        async def websocket_endpoint(
            websocket: WebSocket,
            chat_id: str,
            token: str,
            x_forwarded_for: Annotated[str | None, Header()] = None,
            cf_connecting_ip: Annotated[str | None, Header()] = None,
        ):
            """WebSocket endpoint for chat interactions."""
            try:
                await self.websocket_handler.handle_websocket_connection(
                    websocket=websocket,
                    chat_id=chat_id,
                    token=token,
                    x_forwarded_for=x_forwarded_for,
                    cf_connecting_ip=cf_connecting_ip
                )
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for chat {chat_id}")
            except Exception as e:
                logger.error(f"WebSocket error for chat {chat_id}: {e}")

        @self.app.post("/waitlist")
        async def add_to_waitlist(email: Annotated[str, Form()]):
            """Add email to waitlist."""
            try:
                self.api_service.add_email_to_waitlist(email)
                logger.info(f"Added email to waitlist: {email}")
                return {"status": "success"}
            except Exception as e:
                logger.error(f"Error adding email to waitlist: {e}")
                return {"status": "error", "message": "Failed to add email to waitlist"}

        @self.app.post("/email")
        async def add_email(email: Annotated[str, Form()]):
            """Add email to waitlist (alias for /waitlist)."""
            try:
                self.api_service.add_email_to_waitlist(email)
                logger.info(f"Added email via /email endpoint: {email}")
                return {"status": "success"}
            except Exception as e:
                logger.error(f"Error adding email via /email endpoint: {e}")
                return {"status": "error", "message": "Failed to add email"}

        @self.app.get('/test')
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "success",
                "service": "ODAI API",
                "environment": "production" if self.settings.production else "development",
                "connections": self.connection_manager.connection_count
            }
            
        @self.app.post('/google_access_request')
        async def google_access_request(authorization: Annotated[str, Header()], email: Annotated[str, Form()]):
            """Request Google access."""
            return self.api_service.request_google_access(self.settings.production, authorization, email)
        
        @self.app.get('/update_integrations')
        async def update_integrations():
            """Update integrations."""
            ingest_integrations()
            return {"status": "success"}
    

    def get_app(self) -> FastAPI:
        """Get the FastAPI application instance."""
        return self.app


# Create the application instance
odai_app = ODAPIApplication()
APP = odai_app.get_app()

# Export for backward compatibility
app = APP
manager = odai_app.connection_manager