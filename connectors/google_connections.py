from agents import Agent, RunContextWrapper, function_tool
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

from .utils.context import ChatContext
from .utils.responses import (ConnectGoogleAccountResponse,
                              RequestGoogleAccessResponse, ToolResponse)

try:
    from firebase.models.google_access_request import GoogleAccessRequest
except ImportError:
    from ..firebase.models.google_access_request import GoogleAccessRequest

@function_tool
def connect_google_account(wrapper: RunContextWrapper[ChatContext]) -> ConnectGoogleAccountResponse | RequestGoogleAccessResponse:
    """
    Agent Instruction:
    Use this function when a user wants to access Google services (such as Gmail, Google Docs, Sheets, Presentations, Calendar, or Drive) but does not have their Google account connected. This function will initiate the process to connect or request access to a Google account for the user.
    
    Call this tool when a user says "Connect to Google" or "Connect my Google account"

    Response Types to Expect:
    - 'connect_google_account': Indicates the user can proceed to connect their Google account.
    - 'request_google_access': Indicates the user must first request access to connect a Google account.
    """
    existing_request = GoogleAccessRequest.get_request_for_user(wrapper.context.user.reference_id)
    if hasattr(wrapper.context.user, 'ready_for_google') and wrapper.context.user.ready_for_google:
        print("Connecting Google account")
        return ConnectGoogleAccountResponse('Google Connections').to_dict() 
    elif existing_request:
        print("Existing Google access request")
        return ToolResponse(
            response_type="google_access_request",
            agent_name='Google Connections',
            friendly_name="Existing Google Access Request",
            response="You already have an existing Google access request. Please wait for it to be approved."
        ).to_dict()
    else:
        print("Requesting Google access")
        return RequestGoogleAccessResponse('Google Connections').to_dict()
    
GOOGLE_CONNECTIONS_AGENT = Agent(
    name="Google Connections",
    instructions=RECOMMENDED_PROMPT_PREFIX + "This agent is responsible for handling when a user is not connected to Google. ALWAYS CALL THE connect_google_account TOOL WHEN HANDED OFF TO.",
    tools=[connect_google_account],
)