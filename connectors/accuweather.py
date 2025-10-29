from agents import Agent, function_tool, RunContextWrapper
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents.realtime import RealtimeAgent
from .utils.context import ChatContext
from .utils.responses import ToolResponse
import requests
from .gmail import GMAIL_AGENT
from .google_docs import GOOGLE_DOCS_AGENT


from aiohttp import ClientError, ClientSession

from accuweather import (
    AccuWeather,
    ApiError,
    InvalidApiKeyError,
    InvalidCoordinatesError,
    RequestsExceededError,
)


@function_tool
async def get_current_weather_by_latitude_longitude(wrapper: RunContextWrapper[ChatContext], latitude: float, longitude: float) -> dict:
    """Get current weather for any location.

    Args:
        latitude: Latitude of the location in +/- format
        longitude: Longitude of the location in +/- format

    Args:
        wrapper: Context with auth
        location: City, ZIP, coordinates, airport code, or "auto:ip"

    Returns:
        ToolResponse with temp, humidity, wind, precipitation, UV index
    """
    async with ClientSession() as session:
        accuweather_client = AccuWeather(wrapper.context.settings.accuweather_api_key,
                                         session, latitude=latitude, longitude=longitude, language="en-us")
        try:
            current_conditions = await accuweather_client.async_get_current_conditions()
        except (ApiError, InvalidApiKeyError, InvalidCoordinatesError, RequestsExceededError) as e:
            print(e)
            return ToolResponse(
                response_type="error",
                agent_name="AccuWeather",
                friendly_name="Current Weather by Location",
                display_response=True,
                response=str(e)
            ).to_dict()

    return ToolResponse(
        response_type="current_weather_by_location",
        agent_name="Accuweather",
        friendly_name="Current Weather by Location",
        display_response=True,
        response=current_conditions
    ).to_dict()


@function_tool
async def get_daily_forecast_weather_by_latitude_longitude(wrapper: RunContextWrapper[ChatContext], latitude: float, longitude: float) -> dict:
    """Get weather forecast for the next 10 days

    Args:
        wrapper: Context with auth
        location: City, ZIP, coordinates, airport code, or "auto:ip"
        days: Forecast days 1-14 (default 5)

    Returns:
        ToolResponse with daily/hourly forecasts, precipitation chances, sunrise/sunset
    """
    async with ClientSession() as session:
        accuweather_client = AccuWeather(wrapper.context.settings.accuweather_api_key,
                                         session, latitude=latitude, longitude=longitude)
        try:
            forecast = await accuweather_client.async_get_daily_forecast(days=10, metric=False)
        except (ApiError, InvalidApiKeyError, InvalidCoordinatesError, RequestsExceededError) as e:
            print(e)
            return ToolResponse(
                response_type="error",
                agent_name="AccuWeather",
                friendly_name="Current Weather by Location",
                display_response=True,
                response=str(e)
            ).to_dict()

    return ToolResponse(
        response_type="forecast_weather_by_location",
        agent_name="AccuWeather",
        friendly_name="Forecast Weather by Location",
        display_response=True,
        response=forecast
    ).to_dict()


@function_tool
async def get_hourly_forecast_weather_by_latitude_longitude(wrapper: RunContextWrapper[ChatContext], latitude: float, longitude: float) -> dict:
    """Get 72 hours by hour predictions.

    Use this if someone asks for the weather at a specific time in the next 72 hours

    Args:
        wrapper: Context with auth
        location: City, ZIP, coordinates, airport code, or "auto:ip"
        days: Forecast days 1-14 (default 5)

    Returns:
        ToolResponse with daily/hourly forecasts, precipitation chances, sunrise/sunset
    """
    async with ClientSession() as session:
        accuweather_client = AccuWeather(wrapper.context.settings.accuweather_api_key,
                                         session, latitude=latitude, longitude=longitude)
        try:
            hourly_forecast = await accuweather_client.async_get_hourly_forecast(hours=72, metric=False, language="en-us")
        except (ApiError, InvalidApiKeyError, InvalidCoordinatesError, RequestsExceededError) as e:
            print(e)
            return ToolResponse(
                response_type="error",
                agent_name="AccuWeather",
                friendly_name="Current Weather by Location",
                display_response=True,
                response=str(e)
            ).to_dict()

    return ToolResponse(
        response_type="forecast_weather_by_location",
        agent_name="AccuWeather",
        friendly_name="Forecast Weather by Location",
        display_response=True,
        response=hourly_forecast
    ).to_dict()

ACCUWEATHER_AGENT = Agent(
    name="Accuweather",
    model="gpt-4o",
    handoff_description=RECOMMENDED_PROMPT_PREFIX +
    """Weather: current conditions and 1-14 day forecasts. Supports latitude and longitude.""",
    instructions=RECOMMENDED_PROMPT_PREFIX +
    """Weather assistant. Provides current conditions and 1-7 day forecasts with hourly breakdowns. Includes temp (C/F), precipitation chances, wind, UV index. Accepts latitude and longitude.""",
    tools=[get_current_weather_by_latitude_longitude,
           get_daily_forecast_weather_by_latitude_longitude,
           get_hourly_forecast_weather_by_latitude_longitude],
    handoffs=[GMAIL_AGENT, GOOGLE_DOCS_AGENT]
)

REALTIME_WEATHERAPI_AGENT = RealtimeAgent(
    name="WeatherAPI",
    instructions=RECOMMENDED_PROMPT_PREFIX +
    "You are a WeatherAPI assistant that can help users get the current weather for a location. If you are asked for a forecast, call get_forecast_weather_by_location.",
    tools=[get_current_weather_by_latitude_longitude,
           get_daily_forecast_weather_by_latitude_longitude,
           get_hourly_forecast_weather_by_latitude_longitude]
)

ALL_TOOLS = [get_current_weather_by_latitude_longitude,
             get_daily_forecast_weather_by_latitude_longitude,
             get_hourly_forecast_weather_by_latitude_longitude]
