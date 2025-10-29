from agents import Agent, function_tool, RunContextWrapper
from .utils.context import ChatContext
import requests
from .utils.responses import ToolResponse
from enum import Enum
import json

class Direction(Enum):
    NORTHBOUND = "northbound"
    SOUTHBOUND = "southbound"

import logging
logger = logging.getLogger(__name__)


@function_tool
def get_caltrain_status(wrapper: RunContextWrapper[ChatContext], station: str, direction: Direction) -> dict:
    """
    Get the status of the Caltrain at the given station and direction.
    
    Direction shuould be northbound or southbound.
    
    If the user says the train to San Francisco, use the northbound direction.
    If the user says the train to San Jose, use the southbound direction.
    If the user says the train is leaving San Francisco, use the southbound direction.
    If the user says the train is arriving at San Francisco, use the northbound direction.
    If the user says the train is arriving at San Jose, use the southbound direction.
    If the user says the train is leaving San Jose, use the northbound direction.
    
    If the user asks about the next train at a station but doesn't specify the direction, ask them to clarify which direction
    
    Use the ExpectedArrivalTime and ExpectedDepartureTime to give accurate times for the train
    
    Take into account all daytimes are in UTC and adjust for the user's timezone. If they are asking for the next train or the current status, make sure to use the train arriving or departing the closest to the current time.
    """
    try:
        caltrain_status = requests.get(f'http://api.511.org/transit/StopMonitoring?api_key={wrapper.context.settings.caltrain_api_key}&agency=CT')
        raw_response = caltrain_status.text.encode().decode('utf-8-sig')
        json_response = json.loads(raw_response)
    except Exception as e:
        logger.error(f"Error getting Caltrain status: {e}")
        return ToolResponse(
            response_type="caltrain_status",
            agent_name="Caltrain",
            friendly_name="Caltrain Status",
            response=f"Error getting Caltrain status: {e}"
        ).to_dict()
    
    return ToolResponse(
        response_type="caltrain_status",
        agent_name="Caltrain",
        friendly_name="Caltrain Status",
        response=json_response
    ).to_dict()
    
CALTRAIN_AGENT = Agent(
    name="Caltrain",
    instructions="This agent is responsible for getting the status of the Caltrain. It should be used when the user asks about the status of the Caltrain at a given station. You should reply with the time of the next train, the time until the next train, and type of train (express or local).",
    tools=[get_caltrain_status],
)