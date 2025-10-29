"""In-app voice chat router.

This module provides WebSocket endpoints for handling voice conversations
directly within the ODAI application, allowing users to interact with the
AI assistant using voice without going through Twilio.
"""

try:
    from config import Settings
except ImportError:
    from ..config import Settings

import logging
from typing import Any
from agents.realtime.config import (RealtimeRunConfig,
                                    RealtimeSessionModelSettings,
                                    RealtimeTurnDetectionConfig)
from agents.realtime.events import RealtimeSessionEvent
from agents.realtime.runner import RealtimeRunner
from agents.realtime import RealtimeSession
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from openai import OpenAI
from twilio.rest import Client
from twilio.twiml.voice_response import Connect, VoiceResponse

try:
    from connectors.utils.context import ChatContext
except ImportError:
    from ..connectors.utils.context import ChatContext
try:
    from firebase import User
except ImportError:
    from ..firebase import User

import asyncio
import base64
import json
import struct
import datetime
import phonenumbers

try:
    from connectors.voice_orchestrator import AUDIO_AGENT
except ImportError:
    from ..connectors.voice_orchestrator import AUDIO_AGENT
    
try:
    from connectors.utils.segment import (start_app_voice_chat,
                                          end_app_voice_chat,
                                          track_tool_called)
except ImportError:
    from ..connectors.utils.segment import (start_app_voice_chat,
                                            end_app_voice_chat,
                                            track_tool_called)
try:
    from connectors.orchestrator import TOOL_CALLS
except ImportError:
    from ..connectors.orchestrator import TOOL_CALLS

SETTINGS = Settings()

APP_VOICE_ROUTER = APIRouter(prefix='/app/voice')

client = Client(SETTINGS.twilio_account_sid, SETTINGS.twilio_auth_token)
OPENAI_CLIENT = OpenAI(api_key=SETTINGS.openai_api_key)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REALTIME_RUN_CONFIG = RealtimeRunConfig(
        model_settings=RealtimeSessionModelSettings(
            voice="sage",
            turn_detection=RealtimeTurnDetectionConfig(
                type='server_vad',
                threshold=0.8,
                interrupt_response=False,
                silence_duration_ms=250
            )
        )
    )

class RealtimeWebSocketManager:
    """Manages WebSocket connections for in-app voice chat sessions.
    
    This class handles the lifecycle of real-time voice chat sessions,
    including connection management, event processing, and analytics tracking.
    """
    
    def __init__(self):
        self.active_sessions: dict[str, RealtimeSession] = {}
        self.session_contexts: dict[str, Any] = {}
        self.websockets: dict[str, WebSocket] = {}
        self.contexts: dict[str, ChatContext] = {}
        self.start_times: dict[str, datetime.datetime] = {} 

    async def connect(self, websocket: WebSocket, session_id: str, context: ChatContext):
        self.websockets[session_id] = websocket
        runner = RealtimeRunner(AUDIO_AGENT, config=REALTIME_RUN_CONFIG)
        session_context = await runner.run(context=context)
        session = await session_context.__aenter__()
        self.active_sessions[session_id] = session
        self.session_contexts[session_id] = session_context
        self.contexts[session_id] = context
        self.start_times[session_id] = datetime.datetime.now()
        await session_context.send_message("Greet the user with 'Hello! Welcome to the O-die Voice Assistant. How can I help you today?' and then wait for the user to speak. O-die is pronounced as 'oh die'.")
        start_app_voice_chat(context.user, session_id)
        # Start event processing task
        asyncio.create_task(self._process_events(session_id))

    async def disconnect(self, session_id: str):
        duration = (datetime.datetime.now() - self.start_times[session_id]).total_seconds()
        end_app_voice_chat(self.contexts[session_id].user, session_id, duration)
        if session_id in self.session_contexts:
            await self.session_contexts[session_id].__aexit__(None, None, None)
            del self.session_contexts[session_id]
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        if session_id in self.websockets:
            del self.websockets[session_id]
        if session_id in self.contexts:
            del self.contexts[session_id]
        if session_id in self.start_times:
            del self.start_times[session_id]
        

    async def send_audio(self, session_id: str, audio_bytes: bytes):
        if session_id in self.active_sessions:
            await self.active_sessions[session_id].send_audio(audio_bytes)

    async def _process_events(self, session_id: str):
        try:
            session = self.active_sessions[session_id]
            websocket = self.websockets[session_id]

            async for event in session:
                await self._serialize_event(event, websocket, session_id)
                # await websocket.send_text(json.dumps(event_data))
        except Exception as e:
            logger.error(f"Error processing events for session {session_id}: {e}")

    async def _serialize_event(self, event: RealtimeSessionEvent, websocket: WebSocket, session_id: str) -> dict[str, Any]:
        base_event: dict[str, Any] = {
            "type": event.type,
        }

        if event.type == "agent_start":
            print(f"Agent started: {event.agent.name}")
            response = {'event': 'agent_start', 'agent': event.agent.name}
            await websocket.send_json(response)
        elif event.type == "agent_end":
            print(f"Agent ended: {event.agent.name}")
            response = {'event': 'agent_end', 'agent': event.agent.name}
            await websocket.send_json(response)
        elif event.type == "handoff":
            print(f"Handoff from {event.from_agent.name} to {event.to_agent.name}")
            response = {'event': 'handoff', 'from_agent': event.from_agent.name, 'to_agent': event.to_agent.name}
            await websocket.send_json(response)
        elif event.type == "tool_start":
            print(f"Tool started: {event.tool.name}")
            response = {'event': 'tool_start', 'tool': event.tool.name}
            await websocket.send_json(response)
            track_tool_called(self.contexts[session_id].user, session_id, event.tool.name, TOOL_CALLS[event.tool.name])
        elif event.type == "tool_end":
            print(f"Tool ended: {event.tool.name}; output: {event.output}")
            response = {'event': 'tool_end', 'tool': event.tool.name, 'output': event.output}
            await websocket.send_json(response)
        elif event.type == "audio":
            audio_payload = base64.b64encode(event.audio.data).decode("utf-8")
            audio_delta = {
                    "event": "audio",
                    "payload": audio_payload
                }
            await websocket.send_json(audio_delta)
        elif event.type == "audio_interrupted":
            response = {'event': 'audio_interrupted'}
            await websocket.send_json(response)
        elif event.type == "audio_end":
            print("Audio ended")
            response = {'event': 'audio_end'}
            await websocket.send_json(response)
        elif event.type == "history_updated":
            print("History updated")
            response = {'event': 'history_updated'}
            await websocket.send_json(response)
        elif event.type == "history_added":
            print("History added")
            response = {'event': 'history_added'}
            await websocket.send_json(response)
        elif event.type == "guardrail_tripped":
            base_event["guardrail_results"] = [
                {"name": result.guardrail.name} for result in event.guardrail_results
            ]
        elif event.type == "raw_model_event":
            base_event["raw_model_event"] = {
                "type": event.data.type,
            }
        elif event.type == "error":
            print(f"Error: {event.error}")
        else:
            assert_never(event)

        return base_event


manager = RealtimeWebSocketManager()

@APP_VOICE_ROUTER.websocket('/stream/{session_id}')
async def connect(websocket: WebSocket, session_id: str, token: str) -> None:
    """Handle WebSocket connection for in-app voice chat.
    
    Establishes a voice chat session, processes audio streams, and manages
    the conversation lifecycle between the user and AI assistant.
    
    Args:
        websocket: WebSocket connection from the client
        session_id: Unique identifier for the chat session
        token: Authentication token (currently unused in dev)
    """
    await websocket.accept()
    try:
        user = User.get_user_by_id('lvX2TjNNcYYSroYeJ3LpRuUwwWs1')
        if user is not None:
            context = ChatContext(
                user_id=user.reference_id,
                user=user,
                chat_id='1',
                prompt='Hello',
                production=SETTINGS.production,
                project_id=SETTINGS.project_id,
                logged_in=False,
                settings=SETTINGS,
                openai_client=OPENAI_CLIENT,
                is_google_enabled=False,
                is_plaid_enabled=False
            )
        else:
            await websocket.close()
            return
        await manager.connect(websocket, session_id, context)
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            # print(f"Message: {message}")

            if 'event' in message:
                if message["event"] == "audio":
                    # Convert int16 array to bytes
                    audio = base64.b64decode(message['payload'])
                    await manager.send_audio(session_id, audio)
                    

    except WebSocketDisconnect:
        print(f"WebSocket disconnected")
        await manager.disconnect(session_id)
