from agents import Agent, function_tool, RunContextWrapper
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents.realtime import RealtimeAgent
from .utils.responses import ToolResponse
from .utils.context import ChatContext
from .utils.display_response import display_response_check
import requests
from .utils.cloudflare import Cloudflare


@function_tool
def fetch_website(wrapper: RunContextWrapper[ChatContext], url: str):
    """Fetch website content and convert to markdown.

    Args:
        wrapper: Execution context with authentication
        url: Complete URL with protocol (https://example.com)
    Returns:
        ToolResponse with website content in clean markdown format
    """
    cloudflare = Cloudflare()
    response = cloudflare.render_site_to_markdown(url)
    return ToolResponse(
        response_type="website_content",
        agent_name="Website",
        friendly_name="Website Content",
        response=response
    ).to_dict()


FETCH_WEBSITE_AGENT = Agent(
    name="Fetch Website",
    model="gpt-4o",
    instructions=RECOMMENDED_PROMPT_PREFIX +
    "Fetch websites and convert to markdown.",
    handoff_description=RECOMMENDED_PROMPT_PREFIX + "Fetch website content.",
    tools=[fetch_website]
)

REALTIME_FETCH_WEBSITE_AGENT = RealtimeAgent(
    name="Fetch Website",
    instructions=RECOMMENDED_PROMPT_PREFIX +
    "Fetch websites and return content in markdown.",
    tools=[fetch_website]
)

ALL_TOOLS = [fetch_website]
