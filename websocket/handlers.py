"""WebSocket handlers for managing chat interactions and streaming responses."""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

from fastapi import WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosed
from openai import OpenAI
from openai.types.responses import (
    ResponseCompletedEvent,
    ResponseFunctionToolCall,
    ResponseOutputItemAddedEvent,
    ResponseTextDeltaEvent,
    ResponseTextDoneEvent
)
from agents import Runner

try:
    from connectors.orchestrator import Orchestrator, TOOL_CALLS
    from utils.imports import get_chat_context, get_prompt_services
    from services.auth_service import AuthService
    from services.chat_service import ChatService
    from services.location_service import LocationService
    from websocket.connection_manager import ConnectionManager
except ImportError:
    from ..connectors.orchestrator import Orchestrator, TOOL_CALLS
    from ..utils.imports import get_chat_context, get_prompt_services
    from ..services.auth_service import AuthService
    from ..services.chat_service import ChatService
    from ..services.location_service import LocationService
    from ..websocket.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)


class WebSocketHandler:
    """Handler for WebSocket chat interactions."""

    def __init__(self, settings: Any, openai_client: OpenAI, connection_manager: ConnectionManager):
        self.settings = settings
        self.openai_client = openai_client
        self.connection_manager = connection_manager
        self.auth_service = AuthService(production=settings.production)
        self.chat_service = ChatService()

        # Import dependencies
        self.TOOL_CALLS = TOOL_CALLS
        self.ChatContext = get_chat_context()
        self.AgentCapabilities, self.determine_if_request_handled = get_prompt_services()

        self.agent_capabilities = self.AgentCapabilities()

    async def handle_websocket_connection(
        self,
        websocket: WebSocket,
        chat_id: str,
        token: str,
        x_forwarded_for: Optional[str] = None,
        cf_connecting_ip: Optional[str] = None
    ) -> None:
        """
        Handle a complete WebSocket connection lifecycle.

        Args:
            websocket: The WebSocket connection
            chat_id: The chat identifier
            token: Authentication token
            x_forwarded_for: X-Forwarded-For header
            cf_connecting_ip: CF-Connecting-IP header
        """
        try:
            # Authenticate user
            user, user_anonymous = await self.auth_service.authenticate_websocket(websocket, token)

            # Get location information
            location_info = LocationService.get_location_info(
                x_forwarded_for, cf_connecting_ip)

            # Connect WebSocket
            await self.connection_manager.connect(websocket)
            logger.info(
                f"User {user.reference_id} connected to chat {chat_id}")

            # Get or create chat
            chat, is_new_chat, last_message_id = self.chat_service.get_or_create_chat(
                chat_id, user, location_info
            )

            # Handle chat messages
            await self._handle_chat_loop(websocket, user, chat, chat_id, last_message_id)

        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
        finally:
            self.connection_manager.disconnect(websocket)

    async def _handle_chat_loop(
        self,
        websocket: WebSocket,
        user: Any,
        chat: Any,
        chat_id: str,
        last_message_id: Optional[str]
    ) -> None:
        """Handle the main chat message loop."""
        update_time = last_message_id is not None

        orchestrator = Orchestrator(user)
        await orchestrator.build_dynamic_agents(user)
        orchestrator_agent = orchestrator.agent

        while True:
            try:
                # Receive user prompt
                prompt = await websocket.receive_text()
                self.chat_service.track_user_prompt(user, chat_id, prompt)

                # Update chat timestamp if needed
                if update_time:
                    chat.update_timestamp()
                update_time = True

                # Process the chat message
                await self._process_chat_message(
                    websocket, orchestrator_agent, user, chat, chat_id, prompt, last_message_id
                )

            except (WebSocketDisconnect, ConnectionClosed):
                logger.info("WebSocket disconnected")
                break

            except Exception as e:
                logger.error(f"Error in chat loop: {e}")
                break

    async def _process_chat_message(
        self,
        websocket: WebSocket,
        orchestrator_agent: Any,  # Agent instance from Orchestrator().agent
        user: Any,
        chat: Any,
        chat_id: str,
        prompt: str,
        last_message_id: Optional[str]
    ) -> None:
        """Process a single chat message."""
        # Create runner and context
        runner = Runner()

        context = self.ChatContext(
            user_id=user.reference_id,
            user=user,
            chat_id=chat_id,
            prompt=prompt,
            production=self.settings.production,
            project_id=self.settings.project_id,
            logged_in=False,
            settings=self.settings,
            openai_client=self.openai_client,
            is_google_enabled=user.connected_to_google,
            is_plaid_enabled=user.connected_to_plaid,
        )

        # Run the agent
        if last_message_id:
            logger.info(f"Running agent with {len(chat.messages)} messages using previous message id {last_message_id}")
            result = runner.run_streamed(
                orchestrator_agent,
                [{"content": prompt, "role": "user"}],
                context=context,
                previous_response_id=last_message_id
            )
        else:
            logger.info(f"Running agent with {len(chat.messages)} messages using existing messages")
            result = runner.run_streamed(
                orchestrator_agent,
                chat.messages + [{"content": prompt, "role": "user"}],
                context=context,
            )

        # Handle streaming events
        responses, token_usage, new_last_message_id = await self._handle_streaming_events(
            websocket, result, user, chat_id, prompt
        )

        # Finalize the chat interaction
        await self._finalize_chat_interaction(
            websocket, user, chat, chat_id, prompt, result, responses, token_usage, new_last_message_id
        )

    async def _handle_streaming_events(
        self,
        websocket: WebSocket,
        result: Any,
        user: Any,
        chat_id: str,
        prompt: str
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int], Optional[str]]:
        """Handle streaming events from the agent."""
        responses = [{"type": "user_prompt",
                      "prompt": prompt, 'id': str(uuid.uuid4())}]
        current_agent = None
        input_tokens = 0
        output_tokens = 0
        cached_input_tokens = 0
        last_message_id = None

        async for event in result.stream_events():
            response = await self._process_stream_event(
                event, websocket, user, chat_id, current_agent
            )

            if response:
                response['id'] = str(uuid.uuid4())
                responses.append(response)

            # Update current agent if changed
            if event.type == "agent_updated_stream_event" and event.new_agent.name != "ODAI":
                current_agent = event.new_agent.name

            # Track token usage
            if (event.type == "raw_response_event" and
                    isinstance(event.data, ResponseCompletedEvent)):
                last_message_id = event.data.response.id
                print(f"Last message id: {last_message_id}")
                if event.data.response.usage:
                    input_tokens += event.data.response.usage.input_tokens
                    output_tokens += event.data.response.usage.output_tokens
                    cached_input_tokens += event.data.response.usage.input_tokens_details.cached_tokens

        token_usage = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_input_tokens": cached_input_tokens
        }

        return responses, token_usage, last_message_id

    async def _process_stream_event(
        self,
        event: Any,
        websocket: WebSocket,
        user: Any,
        chat_id: str,
        current_agent: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Process a single stream event."""
        response = None

        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
            # Handle text deltas
            if self.settings.local:
                print(event.data.delta, end="", flush=True)

            partial_response = {
                "type": "raw_response_event",
                "delta": event.data.delta,
                "current_agent": current_agent if current_agent else "ODAI",
            }
            await websocket.send_text(json.dumps(partial_response))

        elif (event.type == "raw_response_event" and
              isinstance(event.data, ResponseOutputItemAddedEvent) and
              isinstance(event.data.item, ResponseFunctionToolCall)):
            # Handle tool calls
            if 'transfer' not in event.data.item.name:
                if not self.settings.production:
                    logger.info(f"Tool called: {event.data.item.name}")

                tool_description = self.TOOL_CALLS.get(event.data.item.name)
                self.chat_service.track_tool_call(
                    user, chat_id, event.data.item.name, tool_description)

                response = {
                    "type": "tool_call",
                    "name": event.data.item.name,
                    "description": tool_description,
                    "current_agent": current_agent if current_agent else "ODAI",
                }
                await websocket.send_text(json.dumps(response))
        elif event.type == "raw_response_event" and isinstance(event.data, ResponseTextDoneEvent):
            response = {
                        "type": "llm_response",
                        "current_agent": (
                            current_agent if current_agent is not None else "ODAI"
                        ),
                        "response": event.data.text,
                    }
                
        elif event.type == "agent_updated_stream_event":
            # Handle agent updates
            if not self.settings.production:
                logger.info(f"Agent updated: {event.new_agent.name}")

            self.chat_service.track_agent_call(
                user, chat_id, event.new_agent.name)

            if event.new_agent.name != "ODAI":
                response = {
                    "type": "agent_updated",
                    "new_agent": event.new_agent.name,
                    "current_agent": event.new_agent.name,
                    "name": event.new_agent.name,
                }
                await websocket.send_text(json.dumps(response))

        elif event.type == "run_item_stream_event":
            response = await self._handle_run_item_event(event, websocket, current_agent)

        return response

    async def _handle_run_item_event(
        self,
        event: Any,
        websocket: WebSocket,
        current_agent: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Handle run item stream events."""
        if event.item.type == "tool_call_output_item":
            output = event.item.output

            # Handle case where output might be a string instead of dict
            if isinstance(output, str):
                try:
                    print(f"Tool output: {output}")
                    output = json.loads(output)
                    print(f"Tool output JSON: {output}")
                except json.JSONDecodeError:
                    logger.warning(f"Tool output is not valid JSON: {output[:100]}...")
                    response = {
                        "type": "tool_output",
                        "output": output,
                        "current_agent": current_agent if current_agent else "ODAI",
                    }
                    await websocket.send_text(json.dumps(response, default=self._json_serial))
                    return response

            # Only send if display_response is True or not specified
            if output.get("display_response", True):
                response = {
                    "type": "tool_output",
                    "output": output,
                    "current_agent": current_agent if current_agent else "ODAI",
                }
                await websocket.send_text(json.dumps(response, default=self._json_serial))
                return response

        elif event.item.type == "handoff_call_item":
            if not self.settings.production:
                logger.info(f"Handoff occurred: {event.item.raw_item.name}")

            response = {
                "type": "handoff",
                "name": event.item.raw_item.name,
                "current_agent": current_agent if current_agent else "ODAI",
            }
            await websocket.send_text(json.dumps(response))
            return response

        return None

    async def _finalize_chat_interaction(
        self,
        websocket: WebSocket,
        user: Any,
        chat: Any,
        chat_id: str,
        prompt: str,
        result: Any,
        responses: List[Dict[str, Any]],
        token_usage: Dict[str, int],
        last_message_id: Optional[str]
    ) -> None:
        """Finalize the chat interaction with suggested prompts and database updates."""
        # Send end of stream
        await websocket.send_text(json.dumps({"type": "end_of_stream"}))
        await asyncio.sleep(0.1)

        # Generate and send suggested prompts
        previously_suggested_prompts = self._extract_previous_suggested_prompts(
            responses)
        result_input_list = result.to_input_list()
        logging.info(f"Result input list: {result_input_list}")

        suggested_prompts = await self.agent_capabilities.generate_suggested_prompts(
            result_input_list, user, previously_suggested_prompts
        )

        if self.settings.local:
            logger.info(f"Suggested prompts: {suggested_prompts}")

        suggested_prompts_response = {
            "type": "suggested_prompts",
            "prompts": suggested_prompts
        }
        responses.append(suggested_prompts_response)
        await websocket.send_text(json.dumps(suggested_prompts_response))
        await asyncio.sleep(0.1)

        # Track response and update database
        self.chat_service.track_user_response(user, chat_id)

        # Update chat messages and responses
        await self.chat_service.update_chat_messages(chat, result_input_list, last_message_id)
        await self.chat_service.add_chat_responses(chat, responses)

        # Check if request was handled
        request_handled, capability_requested, capability_description = await self.determine_if_request_handled(
            result_input_list, user, chat_id, prompt
        )

        if not request_handled:
            await self.chat_service.record_unhandled_request(
                user, chat, prompt, capability_requested, capability_description
            )

        # Record token usage
        await self.chat_service.record_token_usage(
            user,
            token_usage["input_tokens"],
            token_usage["cached_input_tokens"],
            token_usage["output_tokens"]
        )
        await self.chat_service.update_chat_token_usage(
            chat,
            token_usage["input_tokens"],
            token_usage["cached_input_tokens"],
            token_usage["output_tokens"]
        )

    def _extract_previous_suggested_prompts(self, responses: List[Dict[str, Any]]) -> List[str]:
        """Extract previously suggested prompts from responses."""
        previously_suggested = []
        for response in responses:
            if response["type"] == "suggested_prompts":
                previously_suggested.extend(response.get("demo_prompts", []))
        return previously_suggested
        

    @staticmethod
    def _json_serial(obj):
        """JSON serializer for objects not serializable by default json code."""
        import datetime
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
