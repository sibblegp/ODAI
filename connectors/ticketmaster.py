from agents import Agent, function_tool, RunContextWrapper
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents.realtime import RealtimeAgent
import requests
from .utils.context import ChatContext
from .utils.responses import ToolResponse
from .gmail import GMAIL_AGENT
from .google_docs import GOOGLE_DOCS_AGENT
from .weatherapi import WEATHERAPI_AGENT


@function_tool
def get_ticketmaster_events_near_location(wrapper: RunContextWrapper[ChatContext], query: str, city: str, stateCode: str, countryCode: str) -> dict:
    """Search events by location and keyword.

    Args:
        wrapper: Context with auth
        query: Artist/event/genre keyword (empty for all)
        city: City name
        stateCode: 2-letter state/province
        countryCode: 2-letter ISO country

    Returns:
        ToolResponse with events: name, dates, venue, prices
    """
    response = requests.get(
        f"https://app.ticketmaster.com/discovery/v2/events.json?keyword={query}&city={city}&stateCode={stateCode}&countryCode={countryCode}&apikey={wrapper.context.settings.ticketmaster_consumer_key}")
    return ToolResponse(
        response_type="ticketmaster_events_near_location",
        agent_name="Ticketmaster",
        friendly_name="Ticketmaster Event Search",
        display_response=True,
        response=response.json()['_embedded']['events']
    ).to_dict()


@function_tool
def get_ticketmaster_event_details(wrapper: RunContextWrapper[ChatContext], eventId: str) -> dict:
    """Get full event details including pricing and venue info.

    Args:
        wrapper: Context with auth
        eventId: Event ID from search results

    Returns:
        ToolResponse with complete event info, prices, seating, venue details
    """
    response = requests.get(
        f"https://app.ticketmaster.com/discovery/v2/events/{eventId}.json?apikey={wrapper.context.settings.ticketmaster_consumer_key}")
    return ToolResponse(
        response_type="ticketmaster_event_details",
        agent_name="Ticketmaster",
        friendly_name="Ticketmaster Event Details",
        display_response=True,
        response=response.json()
    ).to_dict()


@function_tool
def get_ticketmaster_attractions_by_query(wrapper: RunContextWrapper[ChatContext], query: str) -> dict:
    """Search for artists, teams, performers.

    Args:
        wrapper: Context with auth
        query: Artist/team/comedian name

    Returns:
        ToolResponse with attractions: name, id, upcoming events, genres
    """
    response = requests.get(
        f"https://app.ticketmaster.com/discovery/v2/attractions.json?keyword={query}&apikey={wrapper.context.settings.ticketmaster_consumer_key}")
    return ToolResponse(
        response_type="ticketmaster_attractions_by_query",
        agent_name="Ticketmaster",
        friendly_name="Ticketmaster Attraction Search",
        display_response=True,
        response=response.json()['_embedded']['attractions']
    ).to_dict()


@function_tool
def find_ticketmaster_venues_near_location(wrapper: RunContextWrapper[ChatContext], query: str, stateCode: str, countryCode: str) -> dict:
    """Search venues by location.

    Args:
        wrapper: Context with auth
        query: Venue name or type
        stateCode: 2-letter state
        countryCode: 2-letter country

    Returns:
        ToolResponse with venues: name, address, parking, accessibility
    """
    response = requests.get(
        f"https://app.ticketmaster.com/discovery/v2/venues.json?keyword={query}&stateCode={stateCode}&countryCode={countryCode}&apikey={wrapper.context.settings.ticketmaster_consumer_key}")
    return ToolResponse(
        response_type="ticketmaster_venues_near_location",
        agent_name="Ticketmaster",
        friendly_name="Ticketmaster Venue Search",
        display_response=True,
        response=response.json()['_embedded']['venues']
    ).to_dict()


@function_tool
def get_ticketmaster_venue_details(wrapper: RunContextWrapper[ChatContext], venueId: str) -> dict:
    """Get venue details including address, parking, accessibility.

    Args:
        wrapper: Context with auth
        venueId: Venue ID from search

    Returns:
        ToolResponse with venue info, box office, parking, ADA details
    """
    response = requests.get(
        f"https://app.ticketmaster.com/discovery/v2/venues/{venueId}.json?apikey={wrapper.context.settings.ticketmaster_consumer_key}")
    return ToolResponse(
        response_type="ticketmaster_venue_details",
        agent_name="Ticketmaster",
        friendly_name="Ticketmaster Venue Details",
        display_response=True,
        response=response.json()
    ).to_dict()


@function_tool
def get_ticketmaster_events_by_venue_id(wrapper: RunContextWrapper[ChatContext], venueId: str) -> dict:
    """Get all upcoming events at a venue.

    Args:
        wrapper: Context with auth
        venueId: Venue ID

    Returns:
        ToolResponse with chronological event list
    """
    response = requests.get(
        f"https://app.ticketmaster.com/discovery/v2/events.json?venueId={venueId}&apikey={wrapper.context.settings.ticketmaster_consumer_key}")
    return ToolResponse(
        response_type="ticketmaster_events_by_venue_id",
        agent_name="Ticketmaster",
        friendly_name="Ticketmaster Events by Venue",
        display_response=True,
        response=response.json()['_embedded']['events']
    ).to_dict()


@function_tool
def get_ticketmaster_events_by_attraction_id(wrapper: RunContextWrapper[ChatContext], attractionId: str) -> dict:
    """Get all tour dates/events for an artist or team.

    Args:
        wrapper: Context with auth
        attractionId: Attraction ID from search

    Returns:
        ToolResponse with complete tour schedule
    """
    response = requests.get(
        f"https://app.ticketmaster.com/discovery/v2/events.json?attractionId={attractionId}&apikey={wrapper.context.settings.ticketmaster_consumer_key}")
    return ToolResponse(
        response_type="ticketmaster_events_by_attraction_id",
        agent_name="Ticketmaster",
        friendly_name="Ticketmaster Events by Attraction",
        display_response=True,
        response=response.json()['_embedded']['events']
    ).to_dict()


TICKETMASTER_AGENT = Agent(
    name="Ticketmaster",
    model="gpt-4o",
    handoff_description=RECOMMENDED_PROMPT_PREFIX +
    """Ticketmaster: find events, artists, venues. Get schedules, prices, tickets.""",
    instructions=RECOMMENDED_PROMPT_PREFIX +
    """Ticketmaster assistant. Search events by location/artist/venue. Get details, prices, schedules. Location needs city, state, country codes.""",
    tools=[get_ticketmaster_events_near_location, get_ticketmaster_event_details, find_ticketmaster_venues_near_location, get_ticketmaster_venue_details,
           get_ticketmaster_attractions_by_query, get_ticketmaster_events_by_venue_id, get_ticketmaster_events_by_attraction_id],
    handoffs=[GMAIL_AGENT, GOOGLE_DOCS_AGENT, WEATHERAPI_AGENT]
)

REALTIME_TICKETMASTER_AGENT = RealtimeAgent(
    name="Ticketmaster",
    instructions=RECOMMENDED_PROMPT_PREFIX +
    "You are a Ticketmaster assistant that can help users find events near them and get details about specific events, venues, and attractions.",
    tools=[get_ticketmaster_events_near_location, get_ticketmaster_event_details, find_ticketmaster_venues_near_location, get_ticketmaster_venue_details,
           get_ticketmaster_attractions_by_query, get_ticketmaster_events_by_venue_id, get_ticketmaster_events_by_attraction_id]
)

ALL_TOOLS = [get_ticketmaster_events_near_location, get_ticketmaster_event_details, find_ticketmaster_venues_near_location,
             get_ticketmaster_venue_details, get_ticketmaster_attractions_by_query, get_ticketmaster_events_by_venue_id, get_ticketmaster_events_by_attraction_id]
