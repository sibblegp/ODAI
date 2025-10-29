import segment.analytics as analytics
from datetime import timezone
from typing import Protocol, Any, Optional

try:
    from config import Settings
except ImportError:
    from ...config import Settings

SETTINGS = Settings()

analytics.write_key = SETTINGS.segment_key


class UserProtocol(Protocol):
    """Protocol defining the interface expected for User objects in segment tracking."""
    
    reference_id: str
    createdAt: Any
    is_registered: bool
    integrations: Optional[dict]
    email: Optional[str]
    name: Optional[str]
    creationRecorded: Optional[bool]
    signupRecorded: Optional[bool]
    
    def record_creation(self) -> 'UserProtocol':
        ...
    
    def record_signup(self) -> 'UserProtocol':
        ...
    
    def add_prompt_to_metrics(self, prompt: str) -> None:
        ...
    
    def add_tool_call_to_metrics(self, tool_call: str) -> None:
        ...
    
    def add_agent_call_to_metrics(self, agent_name: str) -> None:
        ...


def identify_user(user: Optional[UserProtocol]) -> None:
    if user is not None:
        if hasattr(user, 'is_registered') and user.is_registered:
            # Build user data dict, handling missing attributes
            user_data = {
                "has_google_integration": user.connected_to_google,
                "has_plaid_integration": user.connected_to_plaid,
                "created_at": user.createdAt,
            }
            
            # Only add email and name if they exist
            if hasattr(user, 'email'):
                user_data["email"] = user.email
            if hasattr(user, 'name'):
                user_data["name"] = user.name

            analytics.identify(user.reference_id, user_data)

        if not hasattr(user, 'creationRecorded') or user.creationRecorded == False:
            user.record_creation()
            track_user_created(user)

        if hasattr(user, 'email') and hasattr(user, 'signupRecorded') and user.signupRecorded == False:
            user.record_signup()
            track_user_signed_up(user)


def track_user_created(user: UserProtocol) -> None:
    analytics.track(user.reference_id, "New User Created")


def track_user_signed_up(user: UserProtocol) -> None:
    analytics.track(user.reference_id, "User Signed Up", {
        "email": user.email,
        "name": user.name,
    })


def track_prompt(user: Optional[UserProtocol], chat_id: str, prompt: str) -> None:
    if user is not None:
        analytics.track(user.reference_id, "Prompt Submitted", {
            "chat_id": chat_id,
            "prompt": prompt,
        })
        # Add to metrics if method exists
        if hasattr(user, 'add_prompt_to_metrics'):
            try:
                user.add_prompt_to_metrics(prompt)
            except Exception:
                # Silently ignore metrics errors to not break tracking
                pass


def track_tool_called(user: Optional[UserProtocol], chat_id: str, tool_call: str, tool_description: str = '') -> None:
    if user is not None:
        analytics.track(user.reference_id, "Tool Called", {
            "chat_id": chat_id,
            "tool_call": tool_call,
            "tool_description": tool_description,
        })
        # Add to metrics if method exists
        if hasattr(user, 'add_tool_call_to_metrics'):
            try:
                user.add_tool_call_to_metrics(tool_call)
            except Exception:
                # Silently ignore metrics errors to not break tracking
                pass


def track_agent_called(user: Optional[UserProtocol], chat_id: str, agent_name: str) -> None:
    if user is not None:
        analytics.track(user.reference_id, "Agent Called", {
            "chat_id": chat_id,
            "agent_name": agent_name,
        })
        # Add to metrics if method exists
        if hasattr(user, 'add_agent_call_to_metrics'):
            try:
                if agent_name != 'ODAI':
                    user.add_agent_call_to_metrics(agent_name)
            except Exception:
                # Silently ignore metrics errors to not break tracking
                pass


def track_chat_created(user: Optional[UserProtocol], chat_id: str) -> None:
    if user is not None:
        analytics.track(user.reference_id, "Chat Created", {
            "chat_id": chat_id,
        })


def using_existing_chat(user: Optional[UserProtocol], chat_id: str) -> None:
    if user is not None:
        analytics.track(user.reference_id, "Existing Chat Used", {
            "chat_id": chat_id,
        })


def track_responded(user: UserProtocol, chat_id: str) -> None:
    analytics.track(user.reference_id, "Response Sent", {
        "chat_id": chat_id,
    })


def track_google_connected(user: UserProtocol) -> None:
    analytics.track(user.reference_id, "Google Connected")


def track_plaid_connected(user: UserProtocol) -> None:
    analytics.track(user.reference_id, "Plaid Connected")


def track_evernote_connected(user: UserProtocol) -> None:
    analytics.track(user.reference_id, "Evernote Connected")


def start_twilio_call(user: UserProtocol, stream_sid: str, call_sid: str, phone_number: Optional[str]) -> None:
    analytics.track(user.reference_id, "Twilio Call Started", {
        "stream_sid": stream_sid,
        "call_sid": call_sid,
        "phone_number": phone_number,
    })


def end_twilio_call(user: UserProtocol, stream_sid: str, call_sid: str, phone_number: Optional[str], duration: int) -> None:
    analytics.track(user.reference_id, "Twilio Call Ended", {
        "stream_sid": stream_sid,
        "call_sid": call_sid,
        "duration": duration,
        "phone_number": phone_number,
    })


def start_app_voice_chat(user: UserProtocol, session_id: str) -> None:
    analytics.track(user.reference_id, "App Voice Chat Started", {
        "session_id": session_id,
    })


def end_app_voice_chat(user: UserProtocol, session_id: str, duration: int) -> None:
    analytics.track(user.reference_id, "App Voice Chat Ended", {
        "session_id": session_id,
        "duration": duration,
    })


def track_unhandled_request(user: UserProtocol, chat_id: str, prompt: str, capability_requested: str, capability_description: str) -> None:
    analytics.track(user.reference_id, "Unhandled Request", {
        "chat_id": chat_id,
        "prompt": prompt,
        "capability_requested": capability_requested,
        "capability_description": capability_description,
    })

def track_google_access_request(user: UserProtocol, email: str) -> None:
    analytics.track(user.reference_id, "Google Access Request", {
        'user_id': user.reference_id,
        'user_email': user.email,
        "target_email": email,
        'user_name': user.name
    })