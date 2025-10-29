try:
    from config import Settings
except ImportError:
    from ..config import Settings

import logging
from typing import Any
from agents.realtime.config import (RealtimeRunConfig,
                                    RealtimeSessionModelSettings,
                                    RealtimeTurnDetectionConfig,)
from agents.realtime.events import RealtimeSessionEvent
from agents.realtime.runner import RealtimeRunner
from agents.realtime.model import RealtimeModelConfig, RealtimeModelListener
from agents.realtime import RealtimeSession
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from openai import OpenAI
from twilio.rest import Client
from twilio.twiml.voice_response import Connect, VoiceResponse

try:
    from routers.voice_utils.compute_sound import get_computer_keyboard_typing_sound
except ImportError:
    from ..routers.voice_utils.compute_sound import get_computer_keyboard_typing_sound

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
    from connectors.orchestrator import TOOL_CALLS
except ImportError:
    from ..connectors.orchestrator import TOOL_CALLS

try:
    from connectors.voice_orchestrator import AUDIO_AGENT
except ImportError:
    from ..connectors.voice_orchestrator import AUDIO_AGENT

try:
    from connectors.utils.segment import (start_twilio_call,
                                          end_twilio_call,
                                          track_tool_called)
except ImportError:
    from ..connectors.utils.segment import (start_twilio_call,
                                            end_twilio_call,
                                            track_tool_called)

logger = logging.getLogger(__name__)

SETTINGS = Settings()

TWILIO_ROUTER = APIRouter(prefix='/twilio')

client = Client(SETTINGS.twilio_account_sid, SETTINGS.twilio_auth_token)
OPENAI_CLIENT = OpenAI(api_key=SETTINGS.openai_api_key)


def _truncate_str(s: str, max_length: int) -> str:
    if len(s) > max_length:
        return s[:max_length] + "..."
    return s


REALTIME_RUN_CONFIG = RealtimeRunConfig(
    model_settings=RealtimeSessionModelSettings(
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

class RealtimeListener(RealtimeModelListener):
    async def on_event(self, event: RealtimeSessionEvent):
        print(f"Event: {event.type}")


class RealtimeWebSocketManager:
    def __init__(self):
        self.active_sessions: dict[str, RealtimeSession] = {}
        self.session_contexts: dict[str, Any] = {}
        self.websockets: dict[str, WebSocket] = {}
        self.stream_sids: dict[str, str] = {}
        self.call_sids: dict[str, str] = {}
        self.contexts: dict[str, ChatContext] = {}
        self.start_times: dict[str, datetime.datetime] = {}
        self.playing_sound: dict[str, bool] = {}

    async def connect(self, websocket: WebSocket, session_id: str, stream_sid: str, call_sid: str, context: ChatContext):
        self.websockets[session_id] = websocket
        runner = RealtimeRunner(AUDIO_AGENT, config=REALTIME_RUN_CONFIG)
        session_context = await runner.run(context=context, model_config=REALTIME_MODEL_CONFIG)
        session = await session_context.__aenter__()
        session.model.add_listener(RealtimeListener())
        self.active_sessions[session_id] = session
        self.session_contexts[session_id] = session_context
        self.stream_sids[session_id] = stream_sid
        self.contexts[session_id] = context
        self.call_sids[session_id] = call_sid
        self.start_times[session_id] = datetime.datetime.now()
        await session_context.send_message("The Call SID is " + str(call_sid) + ". Greet the user with 'Hello! Welcome to the oh die Voice Assistant. How can I help you today?' and then wait for the user to speak. Do not spell out ODAI but pronouce the name as 'oh die'." )
        print(f"Incoming stream has started {stream_sid}")
        start_twilio_call(context.user, stream_sid, call_sid)
        # Start event processing task
        asyncio.create_task(self._process_events(session_id))

    async def disconnect(self, session_id: str):
        duration = (datetime.datetime.now() -
                    self.start_times[session_id]).total_seconds()
        end_twilio_call(self.contexts[session_id].user,
                        self.stream_sids[session_id], self.call_sids[session_id], duration)
        if session_id in self.session_contexts:
            await self.session_contexts[session_id].__aexit__(None, None, None)
            del self.session_contexts[session_id]
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        if session_id in self.websockets:
            del self.websockets[session_id]
        if session_id in self.stream_sids:
            del self.stream_sids[session_id]
        if session_id in self.call_sids:
            del self.call_sids[session_id]
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
            logger.error(
                f"Error processing events for session {session_id}: {e}")

    async def _serialize_event(self, event: RealtimeSessionEvent, websocket: WebSocket, session_id: str) -> dict[str, Any]:
        base_event: dict[str, Any] = {
            "type": event.type,
        }

        if event.type == "agent_start":
            print(f"Agent started: {event.agent.name}")
            sound = get_computer_keyboard_typing_sound(5, 1)
            audio_delta = {
                "event": "media",
                "streamSid": self.stream_sids[session_id],
                "media": {
                    "payload": sound
                }
            }
            await websocket.send_json(audio_delta)
            self.playing_sound[session_id] = True
        elif event.type == "agent_end":
            print(f"Agent ended: {event.agent.name}")
        elif event.type == "handoff":
            print(
                f"Handoff from {event.from_agent.name} to {event.to_agent.name}")
        elif event.type == "tool_start":
            print(f"Tool started: {event.tool.name}")
            track_tool_called(self.contexts[session_id].user, self.stream_sids[session_id],
                              event.tool.name, TOOL_CALLS.get(event.tool.name, 'Undefined'))
        elif event.type == "tool_end":
            print(f"Tool ended: {event.tool.name}; output: {event.output}")
            message = {'event': 'clear',
                       'streamSid': self.stream_sids[session_id]}
            # await websocket.send_json(message)
        elif event.type == "audio":
            if self.playing_sound[session_id]:
                self.playing_sound[session_id] = False
                message = {'event': 'clear',
                           'streamSid': self.stream_sids[session_id]}
                await websocket.send_json(message)
            audio_payload = base64.b64encode(event.audio.data).decode("utf-8")
            audio_delta = {
                "event": "media",
                "streamSid": self.stream_sids[session_id],
                "media": {
                    "payload": audio_payload
                }
            }
            # print(f"Sending audio delta: {audio_delta}")
            await websocket.send_json(audio_delta)
        elif event.type == "audio_interrupted":
            print("Audio interrupted")
        elif event.type == "audio_end":
            print("Audio ended")
        elif event.type == "history_updated":
            print("History updated")
        elif event.type == "history_added":
            print("History added")
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

        return base_event
    
    async def _on_event(self, event: RealtimeSessionEvent):
        print(f"Event: {event}")


manager = RealtimeWebSocketManager()


@TWILIO_ROUTER.post('/incoming')
async def incoming_voice_get(request: Request) -> HTMLResponse:
    """Handle incoming call and return TwiML response to connect to Media Stream."""
    response = VoiceResponse()
    host = request.url.hostname
    # response.say("Welcome to ODAI. How can I help you today?")
    # print(f"Host: {host}")
    connect = Connect()
    connect.stream(url=f'wss://{host}/twilio/connect')
    response.append(connect)
    return HTMLResponse(content=str(response), media_type="application/xml")


@TWILIO_ROUTER.websocket('/connect')
async def connect(websocket: WebSocket) -> None:
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
        session_id = ''

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            # print(f"Message: {message}")

            if 'event' in message:
                if message["event"] == "media":
                    # Convert int16 array to bytes
                    audio = base64.b64decode(message['media']['payload'])
                    await manager.send_audio(session_id, audio)
                elif message["event"] == "start":
                    print(f"Start message: {message}")
                    stream_sid = message["start"]["streamSid"]
                    call_sid = message["start"]["callSid"]
                    session_id = stream_sid
                    await manager.connect(websocket, session_id, stream_sid, call_sid, context)
                else:
                    print(f"Unknown message: {message}")
            else:
                print(f"Unknown message: {message}")

    except WebSocketDisconnect:
        print(f"WebSocket disconnected")
        await manager.disconnect(session_id)


@TWILIO_ROUTER.websocket('/streaming')
async def voice_streaming(websocket: WebSocket) -> None:
    await websocket.accept()
    # user = User.get_user_by_id('lvX2TjNNcYYSroYeJ3LpRuUwwWs1')
    config = RealtimeRunConfig(
        model_settings=RealtimeSessionModelSettings(
            voice="sage",
            # turn_detection=RealtimeTurnDetectionConfig(
            #     type='server_vad',
            #     threshold=0.8
            # ),
            input_audio_format='g711_ulaw',
            output_audio_format='g711_ulaw'
        )
    )
    runner = RealtimeRunner(AUDIO_AGENT, config=config)
    async with await runner.run() as realtime_session:
        stream_sid = None
        continue_streaming = True
        call_sid = None
        phone_number = None

        async def receive_from_twilio():
            """Receive audio data from Twilio and send it to the OpenAI Realtime API."""
            nonlocal stream_sid, continue_streaming, call_sid, realtime_session

            async for message in websocket.iter_text():
                data = json.loads(message)
                if data['event'] == 'media':
                    audio = base64.b64decode(data['media']['payload'])
                    await realtime_session.send_audio(audio)
                    # print(f"Sent audio to OpenAI Realtime API")
                elif data['event'] == 'start':
                    caller_info = client.calls(
                        data['start']['callSid']).fetch()
                    if caller_info._from:
                        parsed_number = phonenumbers.parse(caller_info._from)
                        phone_number = phonenumbers.format_number(
                            parsed_number, phonenumbers.PhoneNumberFormat.E164)
                    else:
                        phone_number = None
                    print(f"Phone number: {phone_number}")
                    stream_sid = data['start']['streamSid']
                    call_sid = data['start']['callSid']
                    # print(f"Call SID: {call_sid}")
                    await realtime_session.send_message("The Call SID is " + str(call_sid) + ". Greet the user with 'Hello! Welcome to the O-die Voice Assistant. How can I help you today?' and then wait for the user to speak. O-die is pronounced as 'oh die'.")
                    print(f"Incoming stream has started {stream_sid}")
                elif data['event'] == 'stop':
                    continue_streaming = False
                    break

        async def send_to_twilio():
            nonlocal stream_sid, call_sid, realtime_session
            async for event in realtime_session:
                await _on_event(event, stream_sid)
            print("Twilio session ended")

        async def _on_event(event: RealtimeSessionEvent, stream_sid: str | None) -> None:
            # print(type(event))
            if event.type == "agent_start":
                print(f"Agent started: {event.agent.name}")
            elif event.type == "agent_end":
                print(f"Agent ended: {event.agent.name}")
            elif event.type == "handoff":
                print(
                    f"Handoff from {event.from_agent.name} to {event.to_agent.name}"
                )
            elif event.type == "tool_start":
                print(f"Tool started: {event.tool.name}")
            elif event.type == "tool_end":
                print(
                    f"Tool ended: {event.tool.name}; output: {event.output}")
            elif event.type == "audio_end":
                print("Audio ended")
            elif event.type == "audio":
                audio_payload = base64.b64encode(
                    event.audio.data).decode('utf-8')
                audio_delta = {
                    "event": "media",
                    "streamSid": stream_sid,
                    "media": {
                        "payload": audio_payload
                    }
                }
                await websocket.send_json(audio_delta)
            elif event.type == "audio_interrupted":
                # await realtime_session.interrupt()
                # await reatime_session.
                print("Audio interrupted")
            elif event.type == "error":
                pass
            elif event.type == "history_updated":
                pass
            elif event.type == "history_added":
                pass

            # elif event.type == "raw_model_event":
            #     print(f"Raw model event: {_truncate_str(str(event.data), 50)}")
            # else:
            #     print(f"Unknown event type: {event.type}")
            # except Exception as e:
            #     print(f"Error processing event: {_truncate_str(str(e), 50)}")

        async def monitor_connection(send_to_twilio_task, receive_from_twilio_task):
            nonlocal continue_streaming
            while continue_streaming:
                await asyncio.sleep(0.25)
            # logger.info("Connection closed.")
            print("Call Ended")
            continue_streaming = False
            send_to_twilio_task.cancel()
            receive_from_twilio_task.cancel()
            await realtime_session.close()
            await websocket.close()

        send_to_twilio_task = asyncio.create_task(send_to_twilio())
        receive_from_twilio_task = asyncio.create_task(receive_from_twilio())
        monitor_connection_task = asyncio.create_task(
            monitor_connection(send_to_twilio_task, receive_from_twilio_task))

        await asyncio.gather(receive_from_twilio_task, send_to_twilio_task, monitor_connection_task)
