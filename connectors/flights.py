from agents import Agent, function_tool
import requests
from openai import OpenAI
import random
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
try:
    from config import Settings
except ImportError:
    from ..config import Settings
from pprint import pprint
from .utils.responses import ToolResponse
from datetime import datetime
from .google_docs import GOOGLE_DOCS_AGENT
from .gmail import GMAIL_AGENT
from .google_calendar import GOOGLE_CALENDAR_AGENT

SETTINGS = Settings()

client = OpenAI(api_key=SETTINGS.openai_api_key)

AVIATIONSTACK_API_KEY = SETTINGS.aviationstack_api_key


@function_tool
def get_flight_info_by_iata(flight_iata: str) -> dict:
    """Get flight information using a flight's IATA code.

    This function retrieves comprehensive real-time flight data using the standardized
    IATA flight code format, which combines the airline's two-letter code with the
    flight number. It provides current status, times, gates, and tracking information
    for active, scheduled, and completed flights.

    Args:
        flight_iata: str - The IATA flight code combining airline code + flight number.
                          Format: 2 letters + 1-4 digits (e.g., 'DL113', 'AA100', 'UA401')
                          Common airline codes:
                          - AA: American Airlines
                          - DL: Delta Air Lines
                          - UA: United Airlines
                          - SW: Southwest Airlines
                          - BA: British Airways
                          - LH: Lufthansa
                          - AF: Air France
                          - EK: Emirates

    Returns:
        dict: ToolResponse containing:
            - response_type: "flight_info"
            - agent_name: "AviationStack"
            - display_response: True
            - response: List of flight data objects (usually 1), each containing:
                - flight_date: str - Date of flight (YYYY-MM-DD)
                - flight_status: str - Current status:
                    - "scheduled": Not yet departed
                    - "active": Currently in flight
                    - "landed": Arrived at destination
                    - "cancelled": Flight cancelled
                    - "incident": Disruption occurred
                    - "diverted": Redirected to alternate airport
                - departure: dict - Departure information:
                    - airport: str - Full airport name
                    - timezone: str - Airport timezone
                    - iata: str - Airport IATA code
                    - icao: str - Airport ICAO code
                    - terminal: str - Terminal number/letter
                    - gate: str - Gate number
                    - delay: int - Delay in minutes (null if on time)
                    - scheduled: str - Scheduled departure (local time)
                    - estimated: str - Updated departure time (local time)
                    - actual: str - Actual departure time (local time)
                    - estimated_runway: str - Estimated runway time
                    - actual_runway: str - Actual runway time
                - arrival: dict - Arrival information (same structure as departure)
                - airline: dict - Airline details:
                    - name: str - Full airline name
                    - iata: str - Airline IATA code
                    - icao: str - Airline ICAO code
                - flight: dict - Flight identifiers:
                    - number: str - Flight number
                    - iata: str - IATA flight code
                    - icao: str - ICAO flight code
                    - codeshared: dict - Codeshare information (if applicable)
                - aircraft: dict - Aircraft information:
                    - registration: str - Aircraft registration
                    - iata: str - Aircraft type IATA code
                    - icao: str - Aircraft type ICAO code
                    - icao24: str - 24-bit ICAO address
                - live: dict - Real-time tracking data (if available):
                    - updated: str - Last update timestamp
                    - latitude: float - Current latitude
                    - longitude: float - Current longitude
                    - altitude: float - Altitude in meters
                    - direction: float - Heading in degrees
                    - speed_horizontal: float - Ground speed in km/h
                    - speed_vertical: float - Vertical speed in m/s
                    - is_ground: bool - Whether on ground

    Example:
        # Get info for Delta flight 113
        get_flight_info_by_iata("DL113")

        # Check American Airlines flight 100
        get_flight_info_by_iata("AA100")

        # Track United flight 401
        get_flight_info_by_iata("UA401")

    Notes:
        - All times are in LOCAL TIME at respective airports (ignore +00:00 suffix)
        - Use this when you have the complete IATA code (e.g., "DL113")
        - For separate airline name + number, use get_flight_info_by_airline_and_flight_number
        - Returns empty list if flight not found
        - Historical data may be limited to recent dates
        - Live tracking data only available for flights currently in air
        - Gate and terminal info may not be available for all airports
        - Codeshare flights may appear under multiple IATA codes
    """

    url = f"http://api.aviationstack.com/v1/flights?access_key={AVIATIONSTACK_API_KEY}&flight_iata={flight_iata}"
    response = requests.get(url)
    data = response.json()['data']
    print(data)
    data = strip_timezone_data(data)
    return ToolResponse(
        response_type="flight_info",
        agent_name="AviationStack",
        friendly_name="Flight Information",
        display_response=True,
        response=data
    ).to_dict()


@function_tool
def get_flight_info_by_airline_and_flight_number(airline: str, flight_number: str, flight_date: str) -> dict:
    """Get flight information using an airline name and flight number.

    This function retrieves flight data when you have the airline's full name and
    flight number as separate components. It automatically converts the airline name
    to its IATA code and combines it with the flight number to fetch comprehensive
    flight details for the specified date.

    Args:
        airline: str - Full airline name or common variations. The function uses AI
                      to resolve the correct IATA code. Examples:
                      - "Delta Airlines", "Delta Air Lines", "Delta"
                      - "American Airlines", "American", "AA"
                      - "United Airlines", "United", "UAL"
                      - "Southwest Airlines", "Southwest"
                      - "British Airways", "BA"
                      - "JetBlue Airways", "JetBlue"
                      - "Alaska Airlines", "Alaska"
                      - "Spirit Airlines", "Spirit"
        flight_number: str - The numeric flight number WITHOUT airline code.
                            Just the digits, no letters. Examples:
                            - "113" (not "DL113")
                            - "100" (not "AA100")
                            - "401" (not "UA401")
                            - "1234" (not "SW1234")
        flight_date: str - The date of the flight in YYYY-MM-DD format.
                          Must be exact date for accurate results.
                          Examples: "2024-03-15", "2024-12-25"

    Returns:
        dict: ToolResponse containing:
            - response_type: "flight_info"
            - agent_name: "AviationStack"
            - display_response: True
            - response: List of flight data objects for the specified date, each containing:
                - flight_date: str - Date of flight
                - flight_status: str - Current status (scheduled/active/landed/cancelled)
                - departure: dict - Departure details:
                    - airport: str - Full departure airport name
                    - timezone: str - Local timezone at departure
                    - iata: str - Departure airport code
                    - terminal: str - Departure terminal
                    - gate: str - Departure gate
                    - scheduled: str - Scheduled local departure time
                    - estimated: str - Updated local departure time
                    - actual: str - Actual local departure time
                    - delay: int - Delay in minutes
                - arrival: dict - Arrival details (same structure as departure)
                - airline: dict - Airline information:
                    - name: str - Full airline name
                    - iata: str - 2-letter airline code
                - flight: dict - Flight identifiers:
                    - number: str - Flight number
                    - iata: str - Complete IATA flight code
                - aircraft: dict - Aircraft details:
                    - registration: str - Tail number
                    - iata: str - Aircraft type code
                - live: dict - Real-time tracking (if in flight):
                    - latitude: float - Current position
                    - longitude: float - Current position
                    - altitude: float - Current altitude
                    - speed_horizontal: float - Ground speed

    Example:
        # Get Delta flight 113 info
        get_flight_info_by_airline_and_flight_number(
            "Delta Airlines", "113", "2024-03-15"
        )

        # Check American flight 100
        get_flight_info_by_airline_and_flight_number(
            "American Airlines", "100", "2024-03-20"
        )

        # Track United flight 401
        get_flight_info_by_airline_and_flight_number(
            "United", "401", "2024-03-25"
        )

    Notes:
        - Uses gpt-4o to intelligently resolve airline names to IATA codes
        - All times shown are LOCAL times at respective airports
        - Date parameter is required for accurate results
        - Flight number should be digits only (no airline prefix)
        - Works with common airline name variations and abbreviations
        - Returns empty list if flight not found on specified date
        - For direct IATA codes (e.g., "DL113"), use get_flight_info_by_iata instead
        - Some regional/codeshare flights may have multiple entries
        - Historical data availability varies by airline
    """

    prompt = f"What is the IATA code for {airline} flight {flight_number}? Just return the IATA code, no other text."
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
        # response_format={"type": "json_object"}
    )
    iata_code = response.choices[0].message.content
    print(iata_code)

    url = f"http://api.aviationstack.com/v1/flights?access_key={AVIATIONSTACK_API_KEY}&flight_iata={iata_code}&flight_date={flight_date}"
    response = requests.get(url)
    print(response.json())
    data = response.json()['data']
    data = strip_timezone_data(data)
    return ToolResponse(
        response_type="flight_info",
        agent_name="AviationStack",
        friendly_name="Getting flight information",
        display_response=True,
        response=data
    ).to_dict()


def strip_timezone_data(flights: list) -> list:
    try:
        for flight in flights:
            flight['departure']['scheduled'] = flight['departure']['scheduled'].split(
                '+')[0]
            flight['departure']['estimated'] = flight['departure']['estimated'].split(
                '+')[0]
            flight['arrival']['scheduled'] = flight['arrival']['scheduled'].split(
                '+')[0]
            flight['arrival']['estimated'] = flight['arrival']['estimated'].split(
                '+')[0]
    except Exception as e:
        print(e)
        pass
    return flights


FLIGHT_AGENT = Agent(
    name="AviationStack",
    model="gpt-4o",
    instructions=RECOMMENDED_PROMPT_PREFIX + """
        I can help with flight-related tasks including:
        - Getting flight information by IATA code or airline/flight number
        - Finding flights between airports
        - Finding flights currently in the air
        

        Only call booking a flight after the "confirm_flight_details" tool has been called and the traveler has confirmed the details.

        If the user is asking about flights that are currently in the air, set the currently_in_air parameter to True on the find_flights_between_airports tool.
        """,
    tools=[
        get_flight_info_by_iata,
        get_flight_info_by_airline_and_flight_number
    ],
    handoff_description=RECOMMENDED_PROMPT_PREFIX + """
        Flight information assistant that can:
        - Get detailed flight information using IATA codes or airline/flight numbers
        - Find available flights between airports
        - Track flights currently in the air
        - Help with flight booking after confirmation
    """,
    handoffs=[GOOGLE_DOCS_AGENT, GMAIL_AGENT, GOOGLE_CALENDAR_AGENT]
)

ALL_TOOLS = [get_flight_info_by_iata,
             get_flight_info_by_airline_and_flight_number]
