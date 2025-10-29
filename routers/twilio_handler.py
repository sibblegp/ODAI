"""Twilio WebSocket handler for voice conversations.

This module implements the TwilioHandler class that manages real-time
voice conversations between Twilio callers and the AI assistant. It handles
audio streaming, transcription, and AI responses.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import time
from datetime import datetime
from typing import Any

from fastapi import WebSocket

from agents.realtime.config import (RealtimeRunConfig,
                                    RealtimeSessionModelSettings,
                                    RealtimeTurnDetectionConfig,)

from agents import function_tool
from agents.realtime import (
    RealtimeAgent,
    RealtimePlaybackTracker,
    RealtimeRunner,
    RealtimeSession,
    RealtimeSessionEvent,
    RealtimeModelConfig,
)

import phonenumbers

try:
    from connectors.voice_orchestrator import AUDIO_AGENT
except ImportError:
    from ..connectors.voice_orchestrator import AUDIO_AGENT

try:
    from config import Settings
except ImportError:
    from ..config import Settings

try:
    from connectors.utils.context import ChatContext
except ImportError:
    from ..connectors.utils.context import ChatContext

try:
    from routers.voice_utils.compute_sound import get_computer_keyboard_typing_sound
except ImportError:
    from ..routers.voice_utils.compute_sound import get_computer_keyboard_typing_sound

try:
    from connectors.utils.segment import (start_twilio_call,
                                          end_twilio_call,
                                          track_tool_called)
except ImportError:
    from ..connectors.utils.segment import (start_twilio_call,
                                            end_twilio_call,
                                            track_tool_called)
try:
    from firebase import User
except ImportError:
    from ..firebase import User

from twilio.rest import Client
from openai import OpenAI

SETTINGS = Settings()

logger = logging.getLogger(__name__)


REALTIME_MODEL_CONFIG = RealtimeModelConfig(initial_model_settings=RealtimeSessionModelSettings(
    voice="sage",
    turn_detection=RealtimeTurnDetectionConfig(
        type='semantic_vad',
        # threshold=0.8,
        interrupt_response=True,
        # silence_duration_ms=500
    ),
    input_audio_format='g711_ulaw',
    output_audio_format='g711_ulaw'
)
)

OPENAI_CLIENT = OpenAI(api_key=SETTINGS.openai_api_key)


class TwilioHandler:
    """Handles Twilio voice call interactions with AI assistant.
    
    This class manages the entire lifecycle of a voice call, including:
    - WebSocket communication with Twilio
    - Audio streaming and transcription
    - AI model interactions
    - Call state management and analytics
    """
    
    def __init__(self, twilio_websocket: WebSocket, user: User):
        """Initialize a new Twilio handler.
        
        Args:
            twilio_websocket: WebSocket connection from Twilio
            user: User object for the caller
        """
        self.twilio_websocket = twilio_websocket
        self._message_loop_task: asyncio.Task[None] | None = None
        self.session: RealtimeSession | None = None
        self.playback_tracker = RealtimePlaybackTracker()
        self.settings = Settings()
        self.call_sids: str | None = None
        self.contexts: dict[str, ChatContext] = {}
        # self.start_times: dict[str, datetime.datetime] = {}
        self.playing_sound: bool | None = None
        self.user = user
        self.start_time = datetime.now()
        self.phone_number: str | None = None
        self.twilio_client = Client(SETTINGS.twilio_account_sid,
                             SETTINGS.twilio_auth_token)
        self.context = ChatContext(
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

        # Audio buffering configuration (matching CLI demo)
        self.CHUNK_LENGTH_S = 0.05  # 50ms chunks like CLI demo
        self.SAMPLE_RATE = 8000  # Twilio uses 8kHz for g711_ulaw
        self.BUFFER_SIZE_BYTES = int(
            self.SAMPLE_RATE * self.CHUNK_LENGTH_S)  # 50ms worth of audio

        self._stream_sid: str | None = None
        self._audio_buffer: bytearray = bytearray()
        self._last_buffer_send_time = time.time()

        # Mark event tracking for playback
        self._mark_counter = 0
        self._mark_data: dict[
            str, tuple[str, int, int]
        ] = {}  # mark_id -> (item_id, content_index, byte_count)

    async def start(self) -> None:
        """Start the session."""
        runner = RealtimeRunner(AUDIO_AGENT)
        api_key = self.settings.openai_api_key
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.session = await runner.run(
            context=self.context,
            model_config={
                "api_key": api_key,
                "initial_model_settings": {
                    "voice": "sage",
                    "input_audio_format": "g711_ulaw",
                    "output_audio_format": "g711_ulaw",
                    "turn_detection": {
                        "type": "semantic_vad",
                        "interrupt_response": True,
                        "create_response": True,
                    },
                },
                "playback_tracker": self.playback_tracker,
            }
        )

        await self.session.enter()
        await self.twilio_websocket.accept()
        logger.info("Twilio WebSocket connection accepted")

        self._realtime_session_task = asyncio.create_task(
            self._realtime_session_loop())
        self._message_loop_task = asyncio.create_task(
            self._twilio_message_loop())
        self._buffer_flush_task = asyncio.create_task(
            self._buffer_flush_loop())

    async def wait_until_done(self) -> None:
        """Wait until the session is done."""
        assert self._message_loop_task is not None
        await self._message_loop_task

    async def _realtime_session_loop(self) -> None:
        """Listen for events from the realtime session."""
        assert self.session is not None
        try:
            async for event in self.session:
                await self._handle_realtime_event(event)
        except Exception as e:
            logger.error(f"Error in realtime session loop: {e}")

    async def _twilio_message_loop(self) -> None:
        """Listen for messages from Twilio WebSocket and handle them."""
        try:
            while True:
                message_text = await self.twilio_websocket.receive_text()
                message = json.loads(message_text)
                await self._handle_twilio_message(message)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Twilio message as JSON: {e}")
        except Exception as e:
            logger.error(f"Error in Twilio message loop: {e}")

    async def _handle_realtime_event(self, event: RealtimeSessionEvent) -> None:
        """Handle events from the realtime session."""
        if event.type == "agent_start":
            logger.info(f"Agent started: {event.agent.name}")
            sound = get_computer_keyboard_typing_sound(5, 1)
            audio_delta = {
                "event": "media",
                "streamSid": self._stream_sid,
                "media": {
                    "payload": sound
                }
            }
            await self.twilio_websocket.send_json(audio_delta)
            self.playing_sound = True

        elif event.type == "agent_end":
            logger.info(f"Agent ended: {event.agent.name}")

        elif event.type == "handoff":
            logger.info(
                f"Handoff from {event.from_agent.name} to {event.to_agent.name}")

        elif event.type == "tool_start":
            logger.info(f"Tool started: {event.tool.name}")
            track_tool_called(self.user, self._stream_sid,
                              event.tool.name, event.tool.description)

        elif event.type == "tool_end":
            logger.debug(f"Tool ended: {event.tool.name}; output: {event.output}")

        elif event.type == "audio_end":
            logger.debug("Audio ended")

        if event.type == "audio":
            if self.playing_sound:
                self.playing_sound = False
                message = {'event': 'clear', 'streamSid': self._stream_sid}
                await self.twilio_websocket.send_json(message)

            base64_audio = base64.b64encode(event.audio.data).decode("utf-8")
            await self.twilio_websocket.send_text(
                json.dumps(
                    {
                        "event": "media",
                        "streamSid": self._stream_sid,
                        "media": {"payload": base64_audio},
                    }
                )
            )

            # Send mark event for playback tracking
            self._mark_counter += 1
            mark_id = str(self._mark_counter)
            self._mark_data[mark_id] = (
                event.audio.item_id,
                event.audio.content_index,
                len(event.audio.data),
            )

            await self.twilio_websocket.send_text(
                json.dumps(
                    {
                        "event": "mark",
                        "streamSid": self._stream_sid,
                        "mark": {"name": mark_id},
                    }
                )
            )

        elif event.type == "audio_interrupted":
            logger.debug("Sending audio interrupted to Twilio")
            await self.twilio_websocket.send_text(
                json.dumps({"event": "clear", "streamSid": self._stream_sid})
            )
        elif event.type == "audio_end":
            logger.debug("Audio end")
        elif event.type == "raw_model_event":
            pass
        else:
            pass

    async def _handle_twilio_message(self, message: dict[str, Any]) -> None:
        """Handle incoming messages from Twilio Media Stream."""
        try:
            event = message.get("event")

            if event == "connected":
                logger.info("Twilio media stream connected")
            elif event == "start":
                start_data = message.get("start", {})
                self._stream_sid = start_data.get("streamSid")
                self.call_sid = start_data.get("callSid")
                greeting_message = (
                    f"The Call SID is {self.call_sid}. Greet the user with 'Hello! Welcome to the oh die "
                    "Voice Assistant. How can I help you today?' and then wait for the user to speak. "
                    "Do not spell out ODAI but pronouce the name as 'oh die'."
                )
                caller_info = self.twilio_client.calls(
                    message['start']['callSid']).fetch()
                if caller_info._from:
                    parsed_number = phonenumbers.parse(caller_info._from)
                    self.phone_number = phonenumbers.format_number(
                        parsed_number, phonenumbers.PhoneNumberFormat.E164)
                else:
                    self.phone_number = None
                await self.session.send_message(greeting_message)
                logger.info(f"Media stream started with SID: {self._stream_sid}")
                start_twilio_call(self.user, self._stream_sid, self.call_sid, self.phone_number)
            elif event == "media":
                await self._handle_media_event(message)
            elif event == "mark":
                await self._handle_mark_event(message)
            elif event == "stop":
                duration = (datetime.now() -
                            self.start_time).total_seconds()

                end_twilio_call(self.user, self._stream_sid,
                                self.call_sid, self.phone_number, duration)
                logger.info("Media stream stopped")
        except Exception as e:
            logger.error(f"Error handling Twilio message: {e}")

    async def _handle_media_event(self, message: dict[str, Any]) -> None:
        """Handle audio data from Twilio - buffer it before sending to OpenAI."""
        media = message.get("media", {})
        payload = media.get("payload", "")

        if payload:
            try:
                # Decode base64 audio from Twilio (µ-law format)
                ulaw_bytes = base64.b64decode(payload)

                # Add original µ-law to buffer for OpenAI (they expect µ-law)
                self._audio_buffer.extend(ulaw_bytes)

                # Send buffered audio if we have enough data
                if len(self._audio_buffer) >= self.BUFFER_SIZE_BYTES:
                    await self._flush_audio_buffer()

            except Exception as e:
                logger.error(f"Error processing audio from Twilio: {e}")

    async def _handle_mark_event(self, message: dict[str, Any]) -> None:
        """Handle mark events from Twilio to update playback tracker."""
        try:
            mark_data = message.get("mark", {})
            mark_id = mark_data.get("name", "")

            # Look up stored data for this mark ID
            if mark_id in self._mark_data:
                item_id, item_content_index, byte_count = self._mark_data[mark_id]

                # Convert byte count back to bytes for playback tracker
                audio_bytes = b"\x00" * byte_count  # Placeholder bytes

                # Update playback tracker
                self.playback_tracker.on_play_bytes(
                    item_id, item_content_index, audio_bytes)
                logger.debug(
                    f"Playback tracker updated: {item_id}, index {item_content_index}, {byte_count} bytes"
                )

                # Clean up the stored data
                del self._mark_data[mark_id]

        except Exception as e:
            logger.error(f"Error handling mark event: {e}")

    async def _flush_audio_buffer(self) -> None:
        """Send buffered audio to OpenAI."""
        if not self._audio_buffer or not self.session:
            return

        try:
            # Send the buffered audio
            buffer_data = bytes(self._audio_buffer)
            await self.session.send_audio(buffer_data)

            # Clear the buffer
            self._audio_buffer.clear()
            self._last_buffer_send_time = time.time()

        except Exception as e:
            logger.error(f"Error sending buffered audio to OpenAI: {e}")

    async def _buffer_flush_loop(self) -> None:
        """Periodically flush audio buffer to prevent stale data."""
        try:
            while True:
                await asyncio.sleep(self.CHUNK_LENGTH_S)  # Check every 50ms

                # If buffer has data and it's been too long since last send, flush it
                current_time = time.time()
                if (
                    self._audio_buffer
                    and current_time - self._last_buffer_send_time > self.CHUNK_LENGTH_S * 2
                ):
                    await self._flush_audio_buffer()

        except Exception as e:
            logger.error(f"Error in buffer flush loop: {e}")
