from agents import Agent, function_tool, RunContextWrapper
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents.realtime import RealtimeAgent
from .utils.context import ChatContext
from .utils.responses import ToolResponse
import requests
from .gmail import GMAIL_AGENT
from .google_docs import GOOGLE_DOCS_AGENT


@function_tool
def get_current_weather_by_location(wrapper: RunContextWrapper[ChatContext], location: str) -> dict:
    """Get current weather for any location.

    Args:
        wrapper: Context with auth
        location: City, ZIP, coordinates, airport code, or "auto:ip"

    Returns:
        ToolResponse with temp, humidity, wind, precipitation, UV index
    """
    response = requests.get(
        f"https://api.weatherapi.com/v1/current.json?key={wrapper.context.settings.weatherapi_api_key}&q={location}")
    return ToolResponse(
        response_type="current_weather_by_location",
        agent_name="WeatherAPI",
        friendly_name="Current Weather by Location",
        display_response=True,
        response=response.json()
    ).to_dict()


@function_tool
def get_forecast_weather_by_location(wrapper: RunContextWrapper[ChatContext], location: str, days: int = 5) -> dict:
    """Get weather forecast with daily and hourly predictions.

    Args:
        wrapper: Context with auth
        location: City, ZIP, coordinates, airport code, or "auto:ip"
        days: Forecast days 1-14 (default 5)

    Returns:
        ToolResponse with daily/hourly forecasts, precipitation chances, sunrise/sunset
    """
    response = requests.get(
        f"https://api.weatherapi.com/v1/forecast.json?key={wrapper.context.settings.weatherapi_api_key}&q={location}&days={days}")
    return ToolResponse(
        response_type="forecast_weather_by_location",
        agent_name="WeatherAPI",
        friendly_name="Forecast Weather by Location",
        display_response=True,
        response=response.json()
    ).to_dict()


WEATHERAPI_AGENT = Agent(
    name="WeatherAPI",
    model="gpt-4o",
    handoff_description=RECOMMENDED_PROMPT_PREFIX +
    """Weather: current conditions and 1-14 day forecasts. Supports cities, ZIP, coordinates, airports.""",
    instructions=RECOMMENDED_PROMPT_PREFIX +
    """Weather assistant. Provides current conditions and 1-14 day forecasts with hourly breakdowns. Includes temp (C/F), precipitation chances, wind, UV index. Accepts cities, ZIP codes, coordinates, airports.""",
    tools=[get_current_weather_by_location, get_forecast_weather_by_location],
    handoffs=[GMAIL_AGENT, GOOGLE_DOCS_AGENT]
)

REALTIME_WEATHERAPI_AGENT = RealtimeAgent(
    name="WeatherAPI",
    instructions=RECOMMENDED_PROMPT_PREFIX +
    "You are a WeatherAPI assistant that can help users get the current weather for a location. If you are asked for a forecast, call get_forecast_weather_by_location.",
    tools=[get_current_weather_by_location, get_forecast_weather_by_location]
)

ALL_TOOLS = [get_current_weather_by_location, get_forecast_weather_by_location]
