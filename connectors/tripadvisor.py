from agents import Agent
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents import function_tool, RunContextWrapper
from .utils.responses import ToolResponse
import finnhub
from .utils.context import ChatContext
from .utils.display_response import display_response_check
import json
from typing import Optional
import os
import requests
from enum import Enum
from .google_docs import GOOGLE_DOCS_AGENT
from .gmail import GMAIL_AGENT

try:
    from config import Settings
except ImportError:
    from ..config import Settings

SETTINGS = Settings()

TRIPADVISOR_API_KEY = SETTINGS.tripadvisor_api_key


class TripAdvisorCategory(Enum):
    RESTAURANTS = "restaurants"
    HOTELS = "hotels"
    ATTRACTIONS = "attractions"


@function_tool
def search_tripadvisor(wrapper: RunContextWrapper[ChatContext], query: str, category: Optional[TripAdvisorCategory] = None, latitude: Optional[float] = None, longitude: Optional[float] = None):
    """Search TripAdvisor for restaurants, hotels, and attractions. Args: query: search terms, category: filter type, latitude/longitude: location. Returns: search results."""
    if latitude and longitude:
        url = f"https://api.content.tripadvisor.com/api/v1/location/search?language=en&key={TRIPADVISOR_API_KEY}&searchQuery={query}&latLong={latitude},{longitude}&radius=10000&radiusUnit=m"
    else:
        url = f"https://api.content.tripadvisor.com/api/v1/location/search?language=en&key={TRIPADVISOR_API_KEY}&searchQuery={query}"
    if category:
        url += f"&category={category.value}"

    print(url)
    response = requests.get(url)
    data = response.json()
    return ToolResponse(
        response_type="tripadvisor_search",
        agent_name="TripAdvisor",
        friendly_name="Search Results",
        response=data
    ).to_dict()


@function_tool
def get_tripadvisor_location_details(wrapper: RunContextWrapper[ChatContext], location_id: str):
    """Get TripAdvisor location details. Args: location_id: location ID. Returns: detailed info."""
    url = f"https://api.content.tripadvisor.com/api/v1/location/{location_id}/details?language=en&key={TRIPADVISOR_API_KEY}"
    response = requests.get(url)
    data = response.json()
    return ToolResponse(
        response_type="tripadvisor_location_details",
        agent_name="TripAdvisor",
        friendly_name="Location Details",
        response=data
    ).to_dict()


@function_tool
def get_tripadvisor_location_reviews(wrapper: RunContextWrapper[ChatContext], location_id: str):
    """Get TripAdvisor location reviews. Args: location_id: location ID. Returns: customer reviews."""
    url = f"https://api.content.tripadvisor.com/api/v1/location/{location_id}/reviews?language=en&key={TRIPADVISOR_API_KEY}"
    response = requests.get(url)
    data = response.json()
    return ToolResponse(
        response_type="tripadvisor_location_reviews",
        agent_name="TripAdvisor",
        friendly_name="Location Reviews",
        response=data
    ).to_dict()


TRIPADVISOR_AGENT = Agent(
    name="TripAdvisor",
    model="gpt-4o",
    instructions=RECOMMENDED_PROMPT_PREFIX +
    """Search and provide info on restaurants, hotels, and attractions from TripAdvisor.""",
    handoff_description=RECOMMENDED_PROMPT_PREFIX +
    """TripAdvisor search for travel locations.""",
    tools=[search_tripadvisor, get_tripadvisor_location_details,
           get_tripadvisor_location_reviews],
    handoffs=[GOOGLE_DOCS_AGENT, GMAIL_AGENT]
)

ALL_TOOLS = [search_tripadvisor, get_tripadvisor_location_details,
             get_tripadvisor_location_reviews]
