"""Centralized imports module to handle conditional imports cleanly."""

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import Settings
    from connectors.orchestrator import ORCHESTRATOR_AGENT, TOOL_CALLS
    from connectors.utils.context import ChatContext
    from firebase import Chat, TokenUsage, Waitlist, UnhandledRequest
    from routers.plaid import PLAID_ROUTER
    from routers.google import GOOGLE_ROUTER
    from routers.twilio_server import TWILIO_ROUTER
    from routers.app_voice import APP_VOICE_ROUTER
    from routers.asana import ASANA_ROUTER
    from authorization import validate_google_token
    from prompts import AgentCapabilities, determine_if_request_handled
    from connectors.utils.segment import (
        track_agent_called,
        track_chat_created,
        track_prompt,
        track_responded,
        track_tool_called,
        using_existing_chat
    )


def safe_import(module_name: str, fallback_name: str = None):
    """Safely import a module with optional fallback for relative imports."""
    try:
        return __import__(module_name, fromlist=[''])
    except ImportError:
        if fallback_name:
            return __import__(fallback_name, fromlist=[''])
        raise


def get_settings():
    """Get Settings class with fallback for relative imports."""
    try:
        from config import Settings
        return Settings
    except ImportError:
        from ..config import Settings
        return Settings


def get_orchestrator():
    """Get orchestrator components with fallback for relative imports."""
    try:
        from connectors.orchestrator import ORCHESTRATOR_AGENT, TOOL_CALLS
        return ORCHESTRATOR_AGENT, TOOL_CALLS
    except ImportError:
        from ..connectors.orchestrator import ORCHESTRATOR_AGENT, TOOL_CALLS
        return ORCHESTRATOR_AGENT, TOOL_CALLS


def get_chat_context():
    """Get ChatContext with fallback for relative imports."""
    try:
        from connectors.utils.context import ChatContext
        return ChatContext
    except ImportError:
        from ..connectors.utils.context import ChatContext
        return ChatContext


def get_firebase_models():
    """Get Firebase models with fallback for relative imports."""
    try:
        from firebase import Chat, TokenUsage, Waitlist, UnhandledRequest, GoogleAccessRequest
        return Chat, TokenUsage, Waitlist, UnhandledRequest, GoogleAccessRequest
    except ImportError:
        from ..firebase import Chat, TokenUsage, Waitlist, UnhandledRequest, GoogleAccessRequest
        return Chat, TokenUsage, Waitlist, UnhandledRequest, GoogleAccessRequest


def get_routers():
    """Get all routers with fallback for relative imports."""
    routers = {}

    try:
        from routers.plaid import PLAID_ROUTER
        routers['plaid'] = PLAID_ROUTER
    except ImportError:
        from ..routers.plaid import PLAID_ROUTER
        routers['plaid'] = PLAID_ROUTER

    try:
        from routers.google import GOOGLE_ROUTER
        routers['google'] = GOOGLE_ROUTER
    except ImportError:
        from ..routers.google import GOOGLE_ROUTER
        routers['google'] = GOOGLE_ROUTER

    try:
        from routers.twilio_server import TWILIO_ROUTER
        routers['twilio'] = TWILIO_ROUTER
    except ImportError:
        from ..routers.twilio_server import TWILIO_ROUTER
        routers['twilio'] = TWILIO_ROUTER

    try:
        from routers.app_voice import APP_VOICE_ROUTER
        routers['app_voice'] = APP_VOICE_ROUTER
    except ImportError:
        from ..routers.app_voice import APP_VOICE_ROUTER
        routers['app_voice'] = APP_VOICE_ROUTER

    try:
        from routers.asana import ASANA_ROUTER
        routers['asana'] = ASANA_ROUTER
    except ImportError:
        from ..routers.asana import ASANA_ROUTER
        routers['asana'] = ASANA_ROUTER

    try:
        from routers.sms import SMS_ROUTER
        routers['sms'] = SMS_ROUTER
    except ImportError:
        from ..routers.sms import SMS_ROUTER
        routers['sms'] = SMS_ROUTER

    return routers


def get_auth_service():
    """Get authorization service with fallback for relative imports."""
    try:
        from authorization import validate_google_token
        return validate_google_token
    except ImportError:
        from ..authorization import validate_google_token
        return validate_google_token


def get_prompt_services():
    """Get prompt services with fallback for relative imports."""
    try:
        from prompts import AgentCapabilities, determine_if_request_handled
        return AgentCapabilities, determine_if_request_handled
    except ImportError:
        from ..prompts import AgentCapabilities, determine_if_request_handled
        return AgentCapabilities, determine_if_request_handled


def get_segment_tracking():
    """Get segment tracking functions with fallback for relative imports."""
    try:
        from connectors.utils.segment import (
            track_agent_called,
            track_chat_created,
            track_prompt,
            track_responded,
            track_tool_called,
            using_existing_chat,
            track_google_access_request
        )
        return (
            track_agent_called,
            track_chat_created,
            track_prompt,
            track_responded,
            track_tool_called,
            using_existing_chat,
            track_google_access_request
        )
    except ImportError:
        from ..connectors.utils.segment import (
            track_agent_called,
            track_chat_created,
            track_prompt,
            track_responded,
            track_tool_called,
            using_existing_chat,
            track_google_access_request
        )
        return (
            track_agent_called,
            track_chat_created,
            track_prompt,
            track_responded,
            track_tool_called,
            using_existing_chat,
            track_google_access_request
        )
