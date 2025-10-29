try:
    from config import Settings
except ImportError:
    from ..config import Settings
from agents import Agent, function_tool
from agents.realtime import RealtimeAgent
import requests
from .utils.responses import ToolResponse
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX


@function_tool
def get_amtrak_train_status(train_number: str) -> dict:
    """Get real-time status and tracking for an Amtrak train.

    Args:
        train_number: Amtrak train number (e.g., "3", "2150", "174")
    Returns:
        ToolResponse with location, speed, delays, and station stops
    """
    url = f"https://api-v3.amtraker.com/v3/trains/{train_number}"
    response = requests.get(url)
    data = response.json()
    return ToolResponse(
        response_type="amtrak_train_status",
        agent_name="Amtrak",
        friendly_name="Checking the status of train " + train_number,
        display_response=True,
        response=data
    ).to_dict()


AMTRAK_AGENT = Agent(
    name="Amtrak",
    model="gpt-4o",
    handoff_description=RECOMMENDED_PROMPT_PREFIX + "Amtrak train tracking.",
    instructions=RECOMMENDED_PROMPT_PREFIX +
    "Track Amtrak trains with real-time location and delays.",
    tools=[get_amtrak_train_status],
)

REALTIME_AMTRAK_AGENT = RealtimeAgent(
    name="Amtrak",
    instructions=RECOMMENDED_PROMPT_PREFIX + "Check Amtrak train status.",
    tools=[get_amtrak_train_status]
)

ALL_TOOLS = [get_amtrak_train_status]
