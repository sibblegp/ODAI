from agents.agent import Agent
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents.realtime.agent import RealtimeAgent
from agents.tool import function_tool
from amadeus import Client, ResponseError

from .utils.responses import ToolResponse

try:
    from config import Settings
except ImportError:
    from ..config import Settings

SETTINGS = Settings()

AMADEUS_CLIENT = Client(
    client_id=SETTINGS.amadeus_client_key,
    client_secret=SETTINGS.amadeus_client_secret,
    hostname='production'
)


@function_tool
def get_flight_info(originIATA: str, destinationIATA: str, departure_date: str, return_date: str | None = None, adults: int = 1, non_stop: bool = False, seat_class: str = 'ECONOMY'):
    """Search flights between airports.

    Args:
        originIATA: 3-letter departure airport code
        destinationIATA: 3-letter arrival airport code
        departure_date: YYYY-MM-DD format
        return_date: YYYY-MM-DD for round trip, None for one-way
        adults: Number of passengers (default 1)
        non_stop: Direct flights only (default False)
        seat_class: ECONOMY/PREMIUM_ECONOMY/BUSINESS/FIRST

    Returns:
        ToolResponse with flight offers: prices, schedules, airlines
    """

    try:

        print(
            f"Getting flights from {originIATA} to {destinationIATA} on {departure_date} for {adults} adults")
        if non_stop:
            send_non_stop = 'true'
        else:
            send_non_stop = 'false'
        if not return_date:
            response = AMADEUS_CLIENT.shopping.flight_offers_search.get(originLocationCode=originIATA, destinationLocationCode=destinationIATA,
                                                                        departureDate=departure_date, adults=adults, nonStop=send_non_stop, max=10, currencyCode='USD', travelClass=seat_class)
        else:
            response = AMADEUS_CLIENT.shopping.flight_offers_search.get(originLocationCode=originIATA, destinationLocationCode=destinationIATA,
                                                                        departureDate=departure_date, returnDate=return_date, adults=adults, nonStop=send_non_stop, max=10, currencyCode='USD', travelClass=seat_class)
        response_dict = {'flight_offers': response.data}
        print(response_dict)
        return ToolResponse(response_type='amadeus_flight_info',
                            agent_name='AMADEUS',
                            friendly_name='Flight Search Results',
                            response=response_dict,
                            display_response=True
                            ).to_dict()
    except ResponseError as e:
        print(e)
        return ToolResponse(response_type='amadeus_flight_info',
                            agent_name='AMADEUS',
                            friendly_name='Flight Search Results',
                            response=str(e),
                            display_response=True
                            ).to_dict()


@function_tool
def get_hotel_prices(latitude: float, longitude: float, check_in_date: str, check_out_date: str, adults: int = 1, children: int = 0, room_count: int = 1, ratings: list[int] = [3, 4, 5]) -> dict:
    """Search hotels by location and dates.

    Args:
        latitude: Search center latitude (-90 to 90)
        longitude: Search center longitude (-180 to 180)
        check_in_date: YYYY-MM-DD format
        check_out_date: YYYY-MM-DD format
        adults: Number of adults (default 1)
        children: Number of children (default 0)
        room_count: Number of rooms (default 1)
        ratings: Star ratings to include (default [3,4,5])

    Returns:
        ToolResponse with hotel offers: prices, availability, amenities
    """
    hotels = AMADEUS_CLIENT.reference_data.locations.hotels.by_geocode.get(
        latitude=latitude, longitude=longitude, ratings=ratings)
    # print(hotels.data)
    hotel_offers = []
    hotel_ids = []
    for hotel in hotels.data[0:20]:
        hotel_ids.append(hotel['hotelId'])
    hotel_offers = AMADEUS_CLIENT.shopping.hotel_offers_search.get(
        hotelIds=hotel_ids, checkInDate=check_in_date, checkOutDate=check_out_date, adults=adults, children=children, roomCount=room_count, currency='USD', max=10)

    # print(hotel_offers.data)
    return ToolResponse(response_type='amadeus_hotel_prices',
                        agent_name='AMADEUS',
                        friendly_name='Hotel Prices',
                        response=hotel_offers.data,
                        display_response=True
                        ).to_dict()


INSTRUCTIONS = """Travel booking assistant. Search flights (one-way/round-trip) and hotels. Supports cabin class, non-stop filters, multi-passenger. Hotels by coordinates with star ratings. Prices in USD."""

AMADEUS_AGENT = Agent(
    name='AMADEUS',
    model="gpt-4o",
    handoff_description=RECOMMENDED_PROMPT_PREFIX +
    """Travel search: flights and hotels with real-time pricing.""",
    instructions=INSTRUCTIONS,
    tools=[get_flight_info, get_hotel_prices]
)

REALTIME_AMADEUS_AGENT = RealtimeAgent(
    name='AMADEUS',
    instructions=RECOMMENDED_PROMPT_PREFIX + INSTRUCTIONS,
    tools=[get_flight_info, get_hotel_prices]
)
