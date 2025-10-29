"""
This module provides integration with Twilio to enable voice assistant capabilities,
such as programmatically hanging up calls.
It defines tools and a realtime agent for use in conversational AI workflows
that interact with Twilio's telephony API.
"""

import asyncio

from agents import function_tool
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents.realtime.agent import RealtimeAgent
from twilio.rest import Client

from .utils.responses import ToolResponse

try:
    from config import Settings
except ImportError:
    from ..config import Settings

SETTINGS = Settings()

@function_tool
async def hangup_call(call_sid: str) -> dict:
    """End an active Twilio voice call programmatically after proper conversation closure.

    This function terminates a voice call through Twilio's API when the conversation has
    reached its natural conclusion. It should only be invoked after the assistant has
    properly said goodbye or confirmed the user wants to end the call. The function includes
    a 2-second delay to ensure farewell messages are fully delivered before disconnection.
    
    This tool is essential for voice assistants to manage call lifecycle and ensure proper
    call termination, preventing calls from remaining open indefinitely. It's typically used
    when the user explicitly says goodbye, requests to end the call, or when the conversation
    has clearly concluded.

    Args:
        call_sid (str): The unique Twilio Call SID (Session Identifier) for the active call.
                       Format: "CA" followed by 32 alphanumeric characters (e.g., "CAe1644a7eed5088b159577c5802d8be38").
                       This SID is provided when the call is initiated and uniquely identifies
                       the call session in Twilio's system.

    Returns:
        dict: Response containing:
            response_type (str): Always 'twilio_hangup' for identifying response type
            agent_name (str): Always 'TWILIO' indicating the service provider
            friendly_name (str): Human-readable action name 'Hangup Call'
            response (str): Confirmation message 'Call hung up'
            display_response (bool): True to show confirmation to the user

    Important usage notes:
        - ALWAYS say goodbye or confirm call ending with the user before calling this function
        - The 2-second delay ensures final messages are delivered before disconnection
        - Never call this function abruptly or without user acknowledgment
        - Ensure the call_sid is valid and corresponds to an active call

    Example conversation flow:
        User: "I think that's all I need, thanks!"
        Assistant: "You're welcome! Have a great day. Goodbye!"
        [Assistant then calls hangup_call(call_sid) to end the call]
    """
    await asyncio.sleep(2)
    client = Client(SETTINGS.twilio_account_sid, SETTINGS.twilio_auth_token)
    client.calls(call_sid).update(status='completed')
    return ToolResponse(response_type='twilio_hangup',
                        agent_name='TWILIO',
                        friendly_name='Hangup Call',
                        response='Call hung up',
                        display_response=True).to_dict()


TWILIO_ASSISTANT_AGENT = RealtimeAgent(
    name="Twilio Assistant",
    instructions=RECOMMENDED_PROMPT_PREFIX + """
        Available tools:
        
        1. hangup_call(call_sid: str) -> dict
           Hang up the call when the voice assistant detects the end of a conversation or call. Call this only after saying goodbye to the user.
        """,
)
