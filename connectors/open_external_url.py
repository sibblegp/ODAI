from agents import Agent
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents import function_tool, RunContextWrapper
from .utils.responses import ToolResponse, OpenWindowResponse, OpenTabResponse
from .utils.context import ChatContext
import json

# @function_tool
# def open_external_url(wrapper: RunContextWrapper[ChatContext], url: str) -> dict:
#     """Opens a URL in a new tab.

#     Args:
#         wrapper (RunContextWrapper[ChatContext]): The context wrapper containing chat information
#         url (str): The URL to open in a new tab

#     Returns:
#         dict: A dictionary containing the response with the URL to open
#     """
#     return OpenTabResponse('OpenExternalUrl', url).to_dict()


@function_tool
def open_external_url_in_window(wrapper: RunContextWrapper[ChatContext], url: str) -> dict:
    """Opens a URL in a new browser window.

    Args:
        wrapper: Execution context wrapper containing chat session information
        url: Complete URL to open with protocol (e.g., "https://example.com")
    Returns:
        OpenWindowResponse with URL and window configuration.
    """
    return OpenWindowResponse('OpenExternalUrl', url).to_dict()


@function_tool
def open_external_url_in_tab(wrapper: RunContextWrapper[ChatContext], url: str) -> dict:
    """Opens a URL in a new browser tab.

    Args:
        wrapper: Execution context wrapper containing chat session information
        url: Complete URL to open with protocol (e.g., "https://example.com")
    Returns:
        OpenTabResponse with URL and target="_blank".
    """
    return OpenTabResponse('OpenExternalUrl', url).to_dict()


OPEN_EXTERNAL_URL_AGENT = Agent(
    name="OpenExternalUrl",
    model="gpt-4o",
    handoff_description=RECOMMENDED_PROMPT_PREFIX +
    "Open external URLs in new window or tab.",
    tools=[open_external_url_in_window, open_external_url_in_tab])
