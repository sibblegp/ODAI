import json
from agents import Agent, function_tool, RunContextWrapper
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents.realtime import RealtimeAgent
import requests
import datetime
from .utils.responses import ToolResponse
from .utils.context import ChatContext
try:
    from config import Settings
except ImportError:
    from ..config import Settings


SETTINGS = Settings()

HEADERS = {
    'x-apikey': SETTINGS.flightaware_api_key,
}


@function_tool
def get_current_flight_status(wrapper: RunContextWrapper[ChatContext], flight_icao: str) -> dict:
    """Get the current real-time status of a flight using its ICAO code.

    This function queries FlightAware's AeroAPI to retrieve comprehensive, real-time
    flight tracking data including position, altitude, speed, and status updates.
    It searches for flights within a 48-hour window (24 hours past to 24 hours future).

    Args:
        wrapper: RunContextWrapper[ChatContext] - The execution context containing
                authentication and configuration
        flight_icao: str - The flight code in ICAO format ONLY.
                          ICAO format: 3-letter airline + flight number (e.g., "DAL113", "AAL100")

                          IMPORTANT: If user provides IATA format (2-letter airline code), 
                          you MUST convert it to ICAO before calling this function:
                          - DL → DAL (Delta)
                          - AA → AAL (American)
                          - UA → UAL (United)
                          - SW → SWA (Southwest)
                          - BA → BAW (British Airways)
                          - LY → ELY (El Al)
                          - AF → AFR (Air France)
                          - LH → DLH (Lufthansa)

    Returns:
        dict: ToolResponse containing:
            - response_type: "flight_info"
            - agent_name: "FlightAware"
            - display_response: True
            - response: Either error message string or FlightAware API response with:
                - flights: list - Array of flight instances within the date range:
                    - ident: str - Flight identifier (ICAO format)
                    - ident_iata: str - Flight identifier (IATA format)
                    - fa_flight_id: str - FlightAware's unique flight ID
                    - operator: str - Operating airline ICAO code
                    - operator_iata: str - Operating airline IATA code
                    - flight_number: str - Numeric flight number
                    - registration: str - Aircraft tail number
                    - atc_ident: str - ATC callsign
                    - inbound_fa_flight_id: str - Previous flight segment ID
                    - codeshares: list - Codeshare flight numbers
                    - codeshares_iata: list - Codeshare IATA codes
                    - blocked: bool - Whether tracking is blocked
                    - diverted: bool - Whether flight was diverted
                    - cancelled: bool - Whether flight was cancelled
                    - position_only: bool - Limited tracking data
                    - origin: dict - Departure airport details:
                        - code: str - Airport ICAO code
                        - code_iata: str - Airport IATA code
                        - code_lid: str - FAA LID code
                        - timezone: str - Airport timezone
                        - name: str - Airport name
                        - city: str - City name
                        - airport_info_url: str - FlightAware airport page
                    - destination: dict - Arrival airport (same structure as origin)
                    - departure_delay: int - Delay in seconds
                    - arrival_delay: int - Delay in seconds
                    - filed_ete: int - Filed estimated time enroute (seconds)
                    - scheduled_out: str - Scheduled departure time (ISO 8601)
                    - estimated_out: str - Estimated departure time
                    - actual_out: str - Actual departure time
                    - scheduled_off: str - Scheduled takeoff time
                    - estimated_off: str - Estimated takeoff time
                    - actual_off: str - Actual takeoff time
                    - scheduled_on: str - Scheduled landing time
                    - estimated_on: str - Estimated landing time
                    - actual_on: str - Actual landing time
                    - scheduled_in: str - Scheduled arrival at gate
                    - estimated_in: str - Estimated arrival at gate
                    - actual_in: str - Actual arrival at gate
                    - progress_percent: int - Flight progress (0-100)
                    - status: str - Current status text
                    - aircraft_type: str - Aircraft type code
                    - route_distance: int - Distance in nautical miles
                    - filed_airspeed: int - Filed speed in knots
                    - filed_altitude: int - Filed altitude in feet
                    - route: str - Filed route string
                    - baggage_claim: str - Baggage claim info
                    - seats_cabin_business: int - Business class seats
                    - seats_cabin_coach: int - Economy seats
                    - seats_cabin_first: int - First class seats
                    - gate_origin: str - Departure gate
                    - gate_destination: str - Arrival gate
                    - terminal_origin: str - Departure terminal
                    - terminal_destination: str - Arrival terminal
                    - type: str - Flight type (e.g., "Airline")

    Example:
        # Track Delta flight 113 (must use ICAO format)
        get_current_flight_status(wrapper, "DAL113")

        # Track American Airlines flight 100
        get_current_flight_status(wrapper, "AAL100")

        # Track El Al flight 15
        get_current_flight_status(wrapper, "ELY15")

    Notes:
        - REQUIRES ICAO format - AI must convert IATA codes before calling
        - Searches 48-hour window centered on current time
        - All times are in ISO 8601 format with timezone info
        - Display times in local timezone of respective airports
        - Returns multiple instances if flight operates multiple times
        - Active flights (in air) are prioritized in results
        - Gate/terminal info may not be available for all airports
        - Some fields may be null depending on flight status
        - Blocked flights have limited tracking information
        - Invalid ICAO codes will return empty results
    """

    start_date = (datetime.datetime.now() -
                  datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = (datetime.datetime.now() +
                datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    url = f"https://aeroapi.flightaware.com/aeroapi/flights/{flight_icao}?start={start_date}&end={end_date}"
    response = requests.get(url, headers=HEADERS)
    return ToolResponse(
        response_type="flight_info",
        agent_name="FlightAware",
        friendly_name="Getting flight information for " + flight_icao,
        display_response=True,
        response=response.json()
    ).to_dict()


FLIGHTAWARE_AGENT = Agent(
    name="FlightAware",
    model="gpt-4o",
    instructions=RECOMMENDED_PROMPT_PREFIX + """You are a FlightAware flight tracking assistant that provides real-time flight status and comprehensive tracking information.

CRITICAL: The get_current_flight_status function ONLY accepts ICAO format flight codes (3-letter airline code + flight number).

When users provide flight codes:
1. If they give IATA format (2-letter code like DL113), YOU MUST convert to ICAO (DAL113) before calling the function
2. Common IATA to ICAO conversions:
   - DL → DAL (Delta)
   - AA → AAL (American)
   - UA → UAL (United)
   - SW → SWA (Southwest)
   - BA → BAW (British Airways)
   - LY → ELY (El Al)
   - AF → AFR (Air France)
   - LH → DLH (Lufthansa)
   - EK → UAE (Emirates)
   - QF → QFA (Qantas)

Your capabilities include:
1. **Real-time Flight Tracking**:
   - Current position, altitude, and speed
   - Flight status (scheduled, active, landed, cancelled, diverted)
   - Progress percentage for active flights
   - Aircraft type and registration

2. **Schedule Information**:
   - Scheduled, estimated, and actual times for:
     - Gate departure/arrival
     - Takeoff and landing
   - Departure and arrival delays
   - Gate and terminal assignments

3. **Flight Details**:
   - Origin and destination airports
   - Route information and distance
   - Filed altitude and airspeed
   - Codeshare flight numbers
   - Seat configuration by cabin class

4. **Airport Information**:
   - Airport names and city locations
   - IATA/ICAO codes
   - Local timezones for accurate time display

When helping users:
- ALWAYS convert IATA codes to ICAO before calling the function
- Search 48-hour window (24h past to 24h future)
- Display times in airport local timezones
- Explain delays and status clearly
- Prioritize active (in-air) flights in results
- Note if tracking is blocked or limited""",
    handoff_description=RECOMMENDED_PROMPT_PREFIX + """A comprehensive flight tracking assistant powered by FlightAware's AeroAPI.

Capabilities:
- Real-time flight status and position tracking
- Schedule information with delays and actual times
- Gate, terminal, and baggage claim details
- Aircraft type and registration info
- Route, altitude, and speed data
- REQUIRES ICAO format (3-letter codes) - converts IATA automatically
- 48-hour search window for flight instances""",
    tools=[get_current_flight_status],
)

REALTIME_FLIGHTAWARE_AGENT = RealtimeAgent(
    name="FlightAware",
    instructions=RECOMMENDED_PROMPT_PREFIX +
    "A tool for getting the current flight status of a flight",
    tools=[get_current_flight_status]
)

ALL_TOOLS = [get_current_flight_status]
