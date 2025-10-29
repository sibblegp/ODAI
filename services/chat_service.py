"""Chat service for handling chat management and Firebase interactions."""

import logging
from typing import Optional, List, Dict, Any

try:
    from firebase.models.chat import Chat
    from utils.imports import get_firebase_models, get_segment_tracking
    from services.location_service import LocationInfo
except ImportError:
    from ..firebase.models.chat import Chat
    from ..utils.imports import get_firebase_models, get_segment_tracking
    from ..services.location_service import LocationInfo
    
try:
    from firebase.models.user import User
except ImportError:
    from ..firebase.models.user import User

logger = logging.getLogger(__name__)


class ChatService:
    """Service for managing chats and Firebase interactions."""

    def __init__(self):
        # Import Firebase models
        self.Chat, self.TokenUsage, _, self.UnhandledRequest, _ = get_firebase_models()

        # Import segment tracking functions
        (
            self.track_agent_called,
            self.track_chat_created,
            self.track_prompt,
            self.track_responded,
            self.track_tool_called,
            self.using_existing_chat,
            _
        ) = get_segment_tracking()

    def get_or_create_chat(
        self,
        chat_id: str,
        user: Any,
        location_info: LocationInfo
    ) -> tuple[Any, bool, Optional[str]]:
        """
        Get an existing chat or create a new one.

        Args:
            chat_id: The chat identifier
            user: The user object
            location_info: Location information for the user

        Returns:
            Tuple of (chat_object, is_new_chat, last_message_id)
        """
        try:
            chat = self.Chat.get_chat_by_id(chat_id, user.reference_id)

            if chat is None:
                # Create new chat
                chat = self.Chat.create_chat(
                    chat_id,
                    user,
                    location_info.latitude_longitude,
                    location_info.city_state,
                    location_info.timezone,
                    location_info.ip
                )
                self.track_chat_created(user, chat_id)
                logger.info(
                    f"Created new chat {chat_id} for user {user.reference_id}")
                return chat, True, None
            else:
                # Use existing chat
                self.using_existing_chat(user, chat_id)
                last_message_id = getattr(chat, 'last_message_id', None)
                logger.info(
                    f"Using existing chat {chat_id} for user {user.reference_id}")
                return chat, False, last_message_id

        except Exception as e:
            logger.error(f"Error getting or creating chat {chat_id}: {e}")
            raise

    async def update_chat_messages(
        self,
        chat: Chat,
        messages: List[Dict[str, Any]],
        last_message_id: Optional[str] = None
    ) -> None:
        """
        Update chat messages in Firebase.

        Args:
            chat: The chat object
            messages: List of messages to update
            last_message_id: The last message ID
        """
        try:
            await chat.update_messages(messages, last_message_id)
            logger.debug(
                f"Updated messages for chat {chat.chat_id if hasattr(chat, 'chat_id') else 'unknown'}")
        except Exception as e:
            logger.error(f"Error updating chat messages: {e}")
            raise

    async def add_chat_responses(self, chat: Any, responses: List[Dict[str, Any]]) -> None:
        """
        Add responses to a chat.

        Args:
            chat: The chat object
            responses: List of responses to add
        """
        try:
            await chat.add_responses(responses)
            logger.debug(f"Added {len(responses)} responses to chat")
        except Exception as e:
            logger.error(f"Error adding chat responses: {e}")
            raise

    async def update_chat_token_usage(
        self,
        chat: Any,
        input_tokens: int,
        cached_input_tokens: int,
        output_tokens: int
    ) -> None:
        """
        Update token usage for a chat.

        Args:
            chat: The chat object
            input_tokens: Number of input tokens used
            cached_input_tokens: Number of cached input tokens used
            output_tokens: Number of output tokens used
        """
        try:
            await chat.update_token_usage(input_tokens, cached_input_tokens, output_tokens)
            logger.debug(
                f"Updated token usage: input={input_tokens}, cached={cached_input_tokens}, output={output_tokens}")
        except Exception as e:
            logger.error(f"Error updating chat token usage: {e}")
            raise

    async def record_token_usage(
        self,
        user: Any,
        input_tokens: int,
        cached_input_tokens: int,
        output_tokens: int
    ) -> None:
        """
        Record token usage for a user.

        Args:
            user: The user object
            input_tokens: Number of input tokens used
            cached_input_tokens: Number of cached input tokens used
            output_tokens: Number of output tokens used
        """
        try:
            await self.TokenUsage.add_usage(user, input_tokens, cached_input_tokens, output_tokens)
            logger.debug(f"Recorded token usage for user {user.reference_id}")
        except Exception as e:
            logger.error(f"Error recording token usage: {e}")
            raise

    async def record_unhandled_request(
        self,
        user: Any,
        chat: Any,
        prompt: str,
        capability_requested: str,
        capability_description: str
    ) -> None:
        """
        Record an unhandled request.

        Args:
            user: The user object
            chat: The chat object
            prompt: The user's prompt
            capability_requested: The capability that was requested
            capability_description: Description of the capability
        """
        try:
            await self.UnhandledRequest.create_unhandled_request(
                user, chat, prompt, capability_requested, capability_description
            )
            logger.info(
                f"Recorded unhandled request for user {user.reference_id}")
        except Exception as e:
            logger.error(f"Error recording unhandled request: {e}")
            raise


    # Tracking methods
    def track_user_prompt(self, user: Any, chat_id: str, prompt: str) -> None:
        """Track user prompt submission."""
        try:
            self.track_prompt(user, chat_id, prompt)
        except Exception as e:
            logger.error(f"Error tracking prompt: {e}")

    def track_agent_call(self, user: User, chat_id: str, agent_name: str) -> None:
        """Track agent call."""
        try:
            self.track_agent_called(user, chat_id, agent_name)
        except Exception as e:
            logger.error(f"Error tracking agent call: {e}")

    def track_tool_call(
        self,
        user: Any,
        chat_id: str,
        tool_name: str,
        tool_description: Optional[str] = None
    ) -> None:
        """Track tool call."""
        try:
            if tool_description:
                self.track_tool_called(
                    user, chat_id, tool_name, tool_description)
            else:
                self.track_tool_called(user, chat_id, tool_name)
        except Exception as e:
            logger.error(f"Error tracking tool call: {e}")

    def track_user_response(self, user: Any, chat_id: str) -> None:
        """Track user response."""
        try:
            self.track_responded(user, chat_id)
        except Exception as e:
            logger.error(f"Error tracking response: {e}")
