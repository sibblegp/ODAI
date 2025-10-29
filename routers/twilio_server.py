"""Twilio voice call server router.

This module provides endpoints for handling incoming Twilio voice calls
and WebSocket connections for real-time voice streaming and processing.
"""

import os
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

# Import TwilioHandler class - handle both module and package use cases
if TYPE_CHECKING:
    # For type checking, use the relative import
    from .twilio_handler import TwilioHandler
else:
    # At runtime, try both import styles
    try:
        # Try relative import first (when used as a package)
        from .twilio_handler import TwilioHandler
    except ImportError:
        # Fall back to direct import (when run as a script)
        from twilio_handler import TwilioHandler
        
from twilio.rest import Client
from twilio.twiml.voice_response import Connect, VoiceResponse

try:
    from firebase import User
except ImportError:
    from ..firebase import User

try:
    from config import Settings
except ImportError:
    from ..config import Settings

SETTINGS = Settings()

TWILIO_ROUTER = APIRouter(prefix='/twilio')

class TwilioWebSocketManager:
    """Manages WebSocket connections for Twilio voice calls.
    
    Handles creation and lifecycle management of TwilioHandler instances
    for processing voice streams from Twilio.
    """
    
    def __init__(self):
        self.active_handlers: dict[str, TwilioHandler] = {}

    async def new_session(self, websocket: WebSocket, user: User) -> TwilioHandler:
        """Create and configure a new session.
        
        Args:
            websocket: WebSocket connection from Twilio
            user: User object for the caller
            
        Returns:
            TwilioHandler: Handler instance for processing the voice call
        """
        print("Creating twilio handler")

        handler = TwilioHandler(websocket, user)
        return handler

    # In a real app, you'd also want to clean up/close the handler when the call ends


manager = TwilioWebSocketManager()


@TWILIO_ROUTER.get("/")
async def root():
    """Health check endpoint for Twilio server.
    
    Returns:
        dict: Status message indicating server is running
    """
    return {"message": "Twilio Media Stream Server is running!"}


@TWILIO_ROUTER.post("/incoming")
@TWILIO_ROUTER.get("/incoming")
async def incoming_call(request: Request):
    """Handle incoming Twilio phone calls.
    
    Creates a TwiML response that instructs Twilio to connect the call
    to a WebSocket stream for real-time processing.
    
    Args:
        request: FastAPI request object containing call information
        
    Returns:
        HTMLResponse: TwiML response with WebSocket stream connection
    """
    response = VoiceResponse()
    host = request.url.hostname
    # response.say("Welcome to ODAI. How can I help you today?")
    # print(f"Host: {host}")
    connect = Connect()
    connect.stream(url=f'wss://{host}/twilio/connect')
    response.append(connect)
    return HTMLResponse(content=str(response), media_type="application/xml")


@TWILIO_ROUTER.websocket("/connect")
async def media_stream_endpoint(websocket: WebSocket):
    """WebSocket endpoint for Twilio Media Streams.
    
    Handles the WebSocket connection from Twilio, processes incoming
    audio streams, and manages the conversation with the AI assistant.
    
    Args:
        websocket: WebSocket connection from Twilio Media Streams
    """
    if SETTINGS.production:
        user = User.get_user_by_id('bBqawe5AuEty3EH2hcw4')
    else:
        user = User.get_user_by_id('lvX2TjNNcYYSroYeJ3LpRuUwwWs1')
    try:
        handler = await manager.new_session(websocket, user)
        await handler.start()

        await handler.wait_until_done()

    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        