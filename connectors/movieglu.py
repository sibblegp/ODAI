import datetime
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents.realtime import RealtimeAgent
import requests
from agents import Agent, function_tool
from requests.auth import HTTPBasicAuth
from .utils.responses import ToolResponse
try:
    from config import Settings
except ImportError:
    from ..config import Settings

SETTINGS = Settings()


def build_headers(latitude: float, longitude: float):
    return {
        'Authorization': SETTINGS.movieglu_api_authorization,
        'x-api-key': SETTINGS.movieglu_api_key,
        'client': 'ODAI',
        'territory': 'US',
        'geolocation': f'{latitude};{longitude}',
        'api-version': 'v201',
        'device-datetime': datetime.datetime.now(datetime.timezone.utc).isoformat().split('+')[0] + 'Z',
    }


def get_films_showing(latitude: float, longitude: float):
    headers = build_headers(latitude, longitude)
    response = requests.get(
        'https://api-gate2.movieglu.com/filmsNowShowing/?n=20', headers=headers)
    if SETTINGS.local:
        print(response.text)
    if response.status_code == 204:
        return []
    return response.json()


def get_nearby_theaters(latitude: float, longitude: float):
    headers = build_headers(latitude, longitude)
    response = requests.get(
        'https://api-gate2.movieglu.com/cinemasNearby/?n=20', headers=headers)
    if SETTINGS.local:
        print(response.text)
    if response.status_code == 204:
        return []
    return response.json()


def search_theaters(latitude: float, longitude: float, query: str):
    headers = build_headers(latitude, longitude)
    response = requests.get(
        f'https://api-gate2.movieglu.com/cinemaLiveSearch/?query={query}&n=20', headers=headers)
    if SETTINGS.local:
        print(response.text)
    if response.status_code == 204:
        return []
    return response.json()


def search_films(latitude: float, longitude: float, query: str):
    headers = build_headers(latitude, longitude)
    response = requests.get(
        f'https://api-gate2.movieglu.com/filmLiveSearch/?query={query}&n=20', headers=headers)
    if SETTINGS.local:
        print(response.text)
    if response.status_code == 204:
        return []
    return response.json()


def get_theater_showtimes(theater_id: int, film_id: int, latitude: float, longitude: float, date: str):
    """
    Get showtimes for a specific theater.

    Args:
        theater_id (str): The unique identifier for the theater
        film_id (str): The unique identifier for the film (currently unused but kept for API consistency)
        latitude (float): Latitude coordinate for location-based results
        longitude (float): Longitude coordinate for location-based results
        date (str): Date in YYYY-MM-DD format to get showtimes for
    Returns:
        dict: JSON response containing showtimes for the specified theater

    Example:
        >>> get_theater_showtimes("12345", "67890", 40.7128, -74.0060)
        {
            "cinema": {...},
            "films": [...],
            "showtimes": [...]
        }
    """
    headers = build_headers(latitude, longitude)
    response = requests.get(
        f'https://api-gate2.movieglu.com/cinemaShowTimes/?film_id={film_id}&date={date}&cinema_id={theater_id}', headers=headers)
    if SETTINGS.local:
        print(response.text)
    if response.status_code == 204:
        return []
    return response.json()


def get_film_showtimes(film_id: str, latitude: float, longitude: float, date: str):
    """
    Get showtimes for a specific film on a given date.

    Args:
        film_id (str): The unique identifier for the film
        latitude (float): Latitude coordinate for location-based results
        longitude (float): Longitude coordinate for location-based results
        date (str): Date in YYYY-MM-DD format to get showtimes for

    Returns:
        dict: JSON response containing showtimes for the specified film on the given date

    Example:
        >>> get_film_showtimes("12345", 40.7128, -74.0060, "2024-01-15")
        {
            "films": [...],
            "cinemas": [...],
            "showtimes": [...]
        }
    """
    headers = build_headers(latitude, longitude)
    response = requests.get(
        f'https://api-gate2.movieglu.com/filmShowTimes/?n=20&film_id={film_id}&date={date}', headers=headers)
    if SETTINGS.local:
        print(response.text)
    if response.status_code == 204:
        return []
    return response.json()


@function_tool
def search_films_near_location(latitude: float, longitude: float, query: str):
    """Search for films by title or keyword near a location.

    Args:
        latitude: Geographic latitude coordinate
        longitude: Geographic longitude coordinate
        query: Search term for film titles or keywords

    Returns:
        ToolResponse with list of matching films
    """
    films = search_films(latitude, longitude, query)
    return ToolResponse(
        response_type="movieglu_search_films",
        agent_name="MovieGlu",
        friendly_name="MovieGlu",
        response=films,
    ).to_dict()


@function_tool
def get_films_showing_near_location(latitude: float, longitude: float):
    """Get all films currently showing in theaters near a location.

    Args:
        latitude: Geographic latitude coordinate
        longitude: Geographic longitude coordinate

    Returns:
        ToolResponse with list of currently showing films
    """
    films = get_films_showing(latitude, longitude)
    return ToolResponse(
        response_type="movieglu_films_showing_near_location",
        agent_name="MovieGlu",
        friendly_name="MovieGlu",
        response=films,
    ).to_dict()


@function_tool
def get_nearby_theaters_near_location(latitude: float, longitude: float):
    """Get movie theaters near a geographic location.

    Args:
        latitude: Geographic latitude coordinate
        longitude: Geographic longitude coordinate

    Returns:
        ToolResponse with list of nearby theaters sorted by distance
    """
    theaters = get_nearby_theaters(latitude, longitude)
    return ToolResponse(
        response_type="movieglu_nearby_theaters",
        agent_name="MovieGlu",
        friendly_name="MovieGlu",
        response=theaters,
    ).to_dict()


@function_tool
def search_theaters_near_location(latitude: float, longitude: float, query: str):
    """Search for theaters by name near a location.

    Args:
        latitude: Geographic latitude coordinate
        longitude: Geographic longitude coordinate
        query: Search term for theater names or features

    Returns:
        ToolResponse with list of matching theaters
    """
    theaters = search_theaters(latitude, longitude, query)
    return ToolResponse(
        response_type="movieglu_search_theaters",
        agent_name="MovieGlu",
        friendly_name="MovieGlu",
        response=theaters,
    ).to_dict()


@function_tool
def get_theater_showtimes_near_location(latitude: float, longitude: float, theater_id: int, film_id: int, date: str):
    """Get showtimes for a specific theater and film on a date.

    Args:
        latitude: Geographic latitude coordinate
        longitude: Geographic longitude coordinate
        theater_id: MovieGlu cinema ID from theater search
        film_id: MovieGlu film ID from film search
        date: Date in YYYY-MM-DD format

    Returns:
        ToolResponse with showtime data for the theater
    """
    print(
        f"Getting showtimes for theater {theater_id} for film {film_id} on {date}")
    try:
        showtimes = get_theater_showtimes(
            theater_id, film_id, latitude, longitude, date)
        print(showtimes)
    except Exception as e:
        print(f"Error getting showtimes: {e}")
        showtimes = []

    return ToolResponse(
        response_type="movieglu_theater_showtimes",
        agent_name="MovieGlu",
        friendly_name="MovieGlu",
        response=showtimes,
    ).to_dict()


@function_tool
def get_film_showtimes_near_location(latitude: float, longitude: float, film_id: str, date: str):
    """Get all showtimes for a film across nearby theaters on a date.

    Args:
        latitude: Geographic latitude coordinate
        longitude: Geographic longitude coordinate
        film_id: MovieGlu film ID from film search
        date: Date in YYYY-MM-DD format

    Returns:
        ToolResponse with showtimes across all nearby theaters
    """
    print(f"Getting showtimes for film {film_id} on {date}")
    showtimes = get_film_showtimes(film_id, latitude, longitude, date)
    return ToolResponse(
        response_type="movieglu_film_showtimes",
        agent_name="MovieGlu",
        friendly_name="MovieGlu",
        response=showtimes,
    ).to_dict()


MOVIEGLU_AGENT = Agent(
    name="MovieGlu",
    model="gpt-4o",
    instructions=RECOMMENDED_PROMPT_PREFIX +
    """You are a movie theater and showtime assistant powered by MovieGlu. Search for films and theaters, get showtimes, and help users find movies to watch near their location.""",
    tools=[get_films_showing_near_location, get_nearby_theaters_near_location, search_theaters_near_location,
           get_theater_showtimes_near_location, get_film_showtimes_near_location, search_films_near_location],
    handoff_description=RECOMMENDED_PROMPT_PREFIX +
    """Movie theater and showtime assistant via MovieGlu.""",
)

REALTIME_MOVIEGLU_AGENT = RealtimeAgent(
    name="MovieGlu",
    instructions=RECOMMENDED_PROMPT_PREFIX +
    "An agent for getting movie showtimes and information",
    tools=[get_films_showing_near_location, get_nearby_theaters_near_location, search_theaters_near_location,
           get_theater_showtimes_near_location, get_film_showtimes_near_location, search_films_near_location]
)

ALL_TOOLS = [get_films_showing_near_location, get_nearby_theaters_near_location, search_theaters_near_location,
             get_theater_showtimes_near_location, get_film_showtimes_near_location, search_films_near_location]
