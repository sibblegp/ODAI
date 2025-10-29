from openai.types.responses import ResponseTextDeltaEvent
import os
from agents import Agent, Runner, set_tracing_export_api_key, ItemHelpers
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents import ModelSettings
import sentry_sdk
from sentry_sdk.integrations.openai_agents import OpenAIAgentsIntegration

try:
    from firebase import User
except ImportError:
    from ..firebase import User

try:
    from config import Settings
except ImportError as e:
    print(e)
    from ..config import Settings

SETTINGS = Settings()
os.environ["OPENAI_API_KEY"] = SETTINGS.openai_api_key

ENVIRONMENT = "production" if SETTINGS.production else "development"

if SETTINGS.sentry_dsn and isinstance(SETTINGS.sentry_dsn, str) and SETTINGS.sentry_dsn.startswith(("http://", "https://")):
    if not SETTINGS.local:
        sentry_sdk.init(
            dsn=SETTINGS.sentry_dsn,
            integrations=[OpenAIAgentsIntegration()],
            traces_sample_rate=1.0,
            send_default_pii=True,
            environment=ENVIRONMENT
        )

try:
    # from walgreens import WALGREENS_AGENT
    from yelp import YELP_AGENT
    # from opentable import OPENTABLE_AGENT
    # from alpaca import ALPACA_AGENT
    from coinmarketcap import COINMARKETCAP_AGENT
    # from location import LOCATION_AGENT
    from flights import FLIGHT_AGENT
    # from instacart import INSTACART_AGENT
    # from spotify import SPOTIFY_AGENT
    # from slack import SLACK_AGENT
    from plaid_agent import PLAID_AGENT
    from finnhub_agent import FINNHUB_AGENT
    from google_calendar import GOOGLE_CALENDAR_AGENT
    from google_docs import GOOGLE_DOCS_AGENT
    from tripadvisor import TRIPADVISOR_AGENT
    from google_shopping import GOOGLE_SHOPPING_AGENT
    from google_news import GOOGLE_NEWS_AGENT
    from google_search import GOOGLE_SEARCH_AGENT
    from fetch_website import FETCH_WEBSITE_AGENT
    from amazon import AMAZON_AGENT
    from open_external_url import OPEN_EXTERNAL_URL_AGENT
    # from twitter import TWITTER_AGENT
    from amtrak import AMTRAK_AGENT
    from ticketmaster import TICKETMASTER_AGENT
    # from evernote import EVERNOTE_AGENT
    from weatherapi import WEATHERAPI_AGENT
    from easypost_agent import EASYPOST_AGENT
    from movieglu import MOVIEGLU_AGENT
    from amadeus_agent import AMADEUS_AGENT
    from flightaware import FLIGHTAWARE_AGENT
    from exchange_rate import EXCHANGE_RATE_AGENT
    from accuweather import ACCUWEATHER_AGENT
    from google_connections import GOOGLE_CONNECTIONS_AGENT
    from caltrain import CALTRAIN_AGENT
    from plaid_connector import PLAID_CONNECTOR_AGENT
except ImportError:
    # from .walgreens import WALGREENS_AGENT
    from .yelp import YELP_AGENT
    # from .opentable import OPENTABLE_AGENT
    # from .alpaca import ALPACA_AGENT
    from .coinmarketcap import COINMARKETCAP_AGENT
    # from .location import LOCATION_AGENT
    from .gmail import GMAIL_AGENT
    from .flights import FLIGHT_AGENT
    # from .instacart import INSTACART_AGENT
    # from .spotify import SPOTIFY_AGENT
    # from .slack import SLACK_AGENT
    from .plaid_agent import PLAID_AGENT
    from .finnhub_agent import FINNHUB_AGENT
    from .google_calendar import GOOGLE_CALENDAR_AGENT
    from .google_docs import GOOGLE_DOCS_AGENT
    from .tripadvisor import TRIPADVISOR_AGENT
    from .google_shopping import GOOGLE_SHOPPING_AGENT
    from .google_news import GOOGLE_NEWS_AGENT
    from .google_search import GOOGLE_SEARCH_AGENT
    from .fetch_website import FETCH_WEBSITE_AGENT
    from .amazon import AMAZON_AGENT
    from .open_external_url import OPEN_EXTERNAL_URL_AGENT
    # from .twitter import TWITTER_AGENT
    from .amtrak import AMTRAK_AGENT
    # from .evernote import EVERNOTE_AGENT
    from .ticketmaster import TICKETMASTER_AGENT
    from .weatherapi import WEATHERAPI_AGENT
    from .easypost_agent import EASYPOST_AGENT
    from .movieglu import MOVIEGLU_AGENT
    from .amadeus_agent import AMADEUS_AGENT
    from .flightaware import FLIGHTAWARE_AGENT
    from .exchange_rate import EXCHANGE_RATE_AGENT
    from .accuweather import ACCUWEATHER_AGENT
    from .google_connections import GOOGLE_CONNECTIONS_AGENT
    from .caltrain import CALTRAIN_AGENT
    from .plaid_connector import PLAID_CONNECTOR_AGENT
set_tracing_export_api_key(SETTINGS.openai_api_key)
# enable_verbose_stdout_logging()

SYSTEM_PROMPT = """
==== ODAI ORCHESTRATOR SYSTEM PROMPT ====

YOU ARE: The ODAI Orchestrator — a friendly, efficient personal assistant that routes user requests to the best-suited specialist agents/tools, stitches results together, and replies concisely.

MISSION:
1. Understand the user’s intent and context.
2. Decide whether to answer directly or delegate to one or more agents/tools.
3. Execute (or coordinate) the minimal, most capable set of actions to fulfill the request.
4. You can also take the results of one tool call and pass it off to another agent for another tool call.
5. Return a clear, concise final answer. Mention (at a high level) what you used (“I checked your email and calendar…”), but don’t overwhelm.

TONE & STYLE:
- Warm, professional, confident. 
- Default to ≤3 short paragraphs or a tight bullet list.
- Use the user’s vocabulary and preferred format if they’ve indicated one.
- If they ask for detail, give it; otherwise stay lean.
- Never expose internal IDs, API keys, or raw stack traces.

CORE LOOP (O.D.A.R.):
1. **Observe**: Parse user input, prior context, and tool results.
2. **Decide**: 
   - Can I answer from context/memory? If yes, do so.
   - Else, which agent(s)/tool(s) best match the task? (See AGENT SELECTION RULES.)
3. **Act**: Call the chosen agent(s)/tool(s). If multiple are needed, parallelize where safe.
4. **Respond**: Summarize results but make sure to give the user an answer to their question if possible; confirm completion or next step. Offer to do follow-ups.

AGENT SELECTION RULES (H.A.N.D.O.F.F.):
- **H**as capability: Does the agent explicitly solve this task?
- **A**ccess: Does it have the right data/API permissions?
- **N**ovelty/Need: Is a tool call actually necessary vs. known info?
- **D**elay/Cost: Prefer fewer/cheaper calls if quality unaffected.
- **O**utput quality: Will it return the format/info you need?
- **F**ailure fallback: Choose alternates if the first is likely to fail.
- **F**usion: When task spans areas, orchestrate multiple agents and merge.

TOOL & AGENT USE:
- Use the registry you’re provided. Know each agent’s:
  - name/id
  - description/capabilities
  - required/optional args
  - auth/data scopes
- Validate inputs before calling.
- If a tool returns excessive text/data, summarize according to the prompt.
- If a call fails or output is malformed, retry once with corrected args; then gracefully degrade or ask the user.

OUTPUT CONTRACT:
- USER-FACING MESSAGE: Concise, friendly answer or next-step question.
- (OPTIONAL) INTERNAL METADATA (hidden from user, if supported):
  - intent
  - chosen_agents/tools & why
  - plan/steps
  - errors/retries
- Only reveal what the SDK requires to function; do not leak private rationale unless explicitly requested AND allowed.

WHEN TO ASK CLARIFYING QUESTIONS:
- Ambiguous goal or missing critical parameters (dates, symbols, file targets, etc.).
- High-risk actions (sending emails, financial trades).
- Otherwise, make best, low-risk assumptions and state them.

MEMORY & PRIVACY:
- Respect user privacy and permissions.
- Use previously stored preferences to reduce friction.

ERROR & EDGE-CASE HANDLING:
- Tool error: brief apology, auto-retry once, then fallback or ask user.
- Empty/irrelevant result: quickly confirm the scope or try an alternative.
- Conflicting outputs: resolve by priority (accuracy > recency > cost), or ask.

FORMATTING GUIDELINES:
- Bullets or numbered lists for multi-step instructions.
- Quote or inline-code only when needed (commands, code, formulas).
- If you used tools, casually reference that (“I checked your portfolio…”) without dumping raw output.
- Provide actionable next steps when relevant.
- Don't display images in the response.

SAFETY & COMPLIANCE:
- Follow {{SAFETY_POLICY_REFERENCE}} and all legal/compliance constraints.
- Never perform disallowed actions even if asked.
- For medical, legal, or financial advice: add appropriate disclaimers and suggest consulting a professional when necessary.

DEFAULT ASSUMPTIONS:
- Currency: USD
- Units: Imperial when appropriate and metric when appropriate
Override if user specifies otherwise.

CLOSING:
Always end with either (a) confirmation of completion or (b) the smallest next question to move forward.

==== END PROMPT ====
"""

ORCHESTRATOR_AGENT = Agent(
    name="ODAI",
    model="gpt-4o",
    instructions=(
        RECOMMENDED_PROMPT_PREFIX +
        (
            "You are a helpful AI assistant that can help with a wide range of tasks. "
            "You can hand off to available agents and make tool calls. "
            "If someone tries to access Google Docs, GMAil, or Google Calendar, you can tell them to type in "
            "\"Connect my Google account\" or \"Connect to Google\" to connect their Google account."
            "If someone asks to connect to their Google account, hand off to the Google Connections agent."
            "If someone asks to connect to their bank or credit card account, hand off to the Plaid Connector agent."
            "If someone asks for their bank or credit card account balance and they have no accounts connected, hand off to the Plaid Connector agent."
        )
    ),
    handoffs=[
        YELP_AGENT,
        COINMARKETCAP_AGENT,
        GMAIL_AGENT,
        FLIGHTAWARE_AGENT,
        PLAID_AGENT,
        FINNHUB_AGENT,
        GOOGLE_CALENDAR_AGENT,
        GOOGLE_DOCS_AGENT,
        TRIPADVISOR_AGENT,
        GOOGLE_SHOPPING_AGENT,
        GOOGLE_NEWS_AGENT,
        GOOGLE_SEARCH_AGENT,
        FETCH_WEBSITE_AGENT,
        AMAZON_AGENT,
        OPEN_EXTERNAL_URL_AGENT,
        AMTRAK_AGENT,
        TICKETMASTER_AGENT,
        EASYPOST_AGENT,
        MOVIEGLU_AGENT,
        AMADEUS_AGENT,
        EXCHANGE_RATE_AGENT,
        ACCUWEATHER_AGENT,
        GOOGLE_CONNECTIONS_AGENT,
        CALTRAIN_AGENT,
        PLAID_CONNECTOR_AGENT,
    ],
    model_settings=ModelSettings(
        include_usage=True
    )
)

TOOL_CALLS = {
    # Alpaca (inactive)
    "get_stock_price_at_alpaca": "Checking Stock Price...",

    # CoinMarketCap
    "check_crypto_price_at_coinmarketcap": "Checking Crypto Price...",

    # Flights (inactive)
    "get_flight_info_by_iata": "Getting Flight Info...",
    "find_flights_between_airports": "Searching Flights...",
    "find_rount_trip_flights": "Searching Flights...",
    "get_available_seats": "Checking Available Seats...",
    "get_traveler_info": None,
    "set_traveler_info": None,
    "confirm_flight_details_prior_to_booking": "Confirming Flight Details...",
    "book_flight": "Booking Flight...",
    "get_flight_info_by_airline_and_flight_number": "Getting Flight Info...",

    # Instacart (inactive)
    "add_to_instacart_basket": "Adding Item to Instacart Basket...",
    "checkout_instacart_basket": "Checking Out at Instacart...",

    # Location (inactive)
    "request_current_location": "Fetching Your Location...",
    "store_location": None,
    "store_latitude_longitude": None,

    # OpenTable (inactive)
    "check_restaurant_availability_at_opentable": "Checking OpenTable for Availability...",
    "make_restaurant_reservation_at_opentable": "Making Reservation...",

    # Walgreens (inactive)
    "get_available_prescriptions_for_walgreens": "Getting Prescriptions....",
    "refill_prescription_at_walgreens": "Refilling Prescription...",

    # Yelp
    "search_businesses_at_yelp": "Searching Yelp...",
    "get_business_reviews_at_yelp": "Getting Reviews...",

    # Finnhub
    "get_stock_price_at_finnhub": "Getting Stock Price...",
    'get_annual_financials_at_finnhub': 'Getting Annual Stock Financials...',
    "get_quarterly_stock_financials_at_finnhub": "Getting Quarterly Stock Financials...",

    # Google Calendar
    "get_google_calendar_events": "Getting Calendar Events...",
    "create_google_calendar_event": "Creating Calendar Event...",
    "delete_google_calendar_event": "Deleting Calendar Event...",

    # Gmail
    "fetch_google_email_inbox": "Fetching Inbox...",
    "search_google_mail": "Searching Emails...",
    "search_google_mail_from_email": "Searching Emails from Sender...",
    "send_google_email": "Sending Email...",
    "reply_to_google_email": "Replying to Email...",

    # Google Docs
    "save_google_doc": "Saving Google Doc...",
    "search_google_docs_by_name_or_content": "Searching Google Docs...",

    # Google News
    "get_google_news_top_stories": "Getting Google News Top Stories...",
    "search_google_news": "Searching Google News...",

    # Google Shopping
    "get_google_products": "Getting Google Products...",

    # Google Search
    "search_google": "Searching Google...",

    # Fetch Website
    "fetch_website": "Fetching Website...",

    # Amazon
    "search_amazon": "Searching Amazon...",
    "get_product_details": "Getting Product Details...",

    # Open External URL
    "open_external_url_in_window": "Opening External URL in Window...",
    "open_external_url_in_tab": "Opening External URL in Tab...",

    # Plaid
    'get_accounts_at_plaid': 'Getting Accounts...',
    'get_transactions_at_plaid': 'Getting Transactions...',

    # Amtrak
    'get_amtrak_train_status': 'Getting Amtrak Train Status...',

    # Ticketmaster
    'get_ticketmaster_events_near_location': 'Getting Ticketmaster Events...',
    'get_ticketmaster_event_details': 'Getting Ticketmaster Event Details...',
    'find_ticketmaster_venues_near_location': 'Finding Ticketmaster Venues...',
    'get_ticketmaster_venue_details': 'Getting Ticketmaster Venue Details...',
    'get_ticketmaster_attractions_by_query': 'Getting Ticketmaster Attractions...',
    'get_ticketmaster_events_by_attraction_id': 'Getting Ticketmaster Events by Attraction...',
    'get_ticketmaster_events_by_venue_id': 'Getting Ticketmaster Events by Venue...',

    # Weather API
    'get_current_weather_by_location': 'Getting Current Weather...',
    'get_forecast_weather_by_location': 'Getting Forecast Weather...',

    # AccuWeather
    'get_current_weather_by_latitude_longitude': 'Getting Current Weather...',
    'get_daily_forecast_weather_by_latitude_longitude': 'Getting Daily Forecast...',
    'get_hourly_forecast_weather_by_latitude_longitude': 'Getting Hourly Forecast...',

    # EasyPost
    'get_tracking_info_with_easypost': 'Getting Tracking Info...',
    'get_all_packages_with_easypost': 'Getting All Packages...',

    # MovieGlu
    'get_films_showing_near_location': 'Getting Films Showing Near Location...',
    'search_films_near_location': 'Searching Films...',
    'search_theaters_near_location': 'Searching Theaters...',
    'get_nearby_theaters_near_location': 'Getting Nearby Theaters...',
    'get_theater_showtimes_near_location': 'Getting Theater Showtimes...',
    'get_film_showtimes_near_location': 'Getting Film Showtimes...',

    # Amadeus
    'get_flight_info': 'Searching Flights...',
    'get_hotel_prices': 'Searching Hotels...',

    # FlightAware
    'get_current_flight_status': 'Getting Flight Status...',

    # Exchange Rate
    'get_exchange_rates_for_currency': 'Getting Exchange Rates...',
    'get_exchange_rate_for_currency_pair': 'Getting Exchange Rate...',

    # TripAdvisor
    'search_tripadvisor': 'Searching TripAdvisor...',
    'get_tripadvisor_location_details': 'Getting Location Details...',
    'get_tripadvisor_location_reviews': 'Getting Location Reviews...',

    # Google Connections
    'connect_google_account': 'Connecting Google Account...',

    # Caltrain
    'get_caltrain_status': 'Getting Caltrain Status...',

    # Plaid Connector
    'connect_plaid_account': 'Connecting Plaid Account...',
}


class Orchestrator:
    """
    Orchestrator is a class that creates an ODAI agent that can hand off to other agents and make tool calls.
    """

    def __init__(self, user: User):
        self.instructions = (RECOMMENDED_PROMPT_PREFIX +
                             (
                                 "You are a helpful AI assistant that can help with a wide range of tasks. "
                                 "You can hand off to available agents and make tool calls. "
                                 "If someone tries to access Google Docs, GMAil, or Google Calendar, you can tell them to type in "
                                 "\"Connect my Google account\" or \"Connect to Google\" to connect their Google account."
                                 "If someone asks to connect to their Google account, hand off to the Google Connections agent."
                                 "If someone asks to connect to their bank or credit card account, hand off to the Plaid Connector agent."
                                 "If someone asks for their bank or credit card account balance and they have no accounts connected, hand off to the Plaid Connector agent."
                             ))
        self.model = "gpt-4o"
        self.handoffs = [
            YELP_AGENT,
            COINMARKETCAP_AGENT,
            GMAIL_AGENT,
            FLIGHTAWARE_AGENT,
            PLAID_AGENT,
            FINNHUB_AGENT,
            GOOGLE_CALENDAR_AGENT,
            GOOGLE_DOCS_AGENT,
            TRIPADVISOR_AGENT,
            GOOGLE_SHOPPING_AGENT,
            GOOGLE_NEWS_AGENT,
            GOOGLE_SEARCH_AGENT,
            FETCH_WEBSITE_AGENT,
            AMAZON_AGENT,
            OPEN_EXTERNAL_URL_AGENT,
            AMTRAK_AGENT,
            TICKETMASTER_AGENT,
            EASYPOST_AGENT,
            MOVIEGLU_AGENT,
            AMADEUS_AGENT,
            EXCHANGE_RATE_AGENT,
            ACCUWEATHER_AGENT,
            GOOGLE_CONNECTIONS_AGENT,
            CALTRAIN_AGENT,
            PLAID_CONNECTOR_AGENT,
        ]
        self.model_settings = ModelSettings(
            include_usage=True
        )

    @property
    def agent(self):
        return Agent(
            name="ODAI",
            model=self.model,
            instructions=self.instructions,
            handoffs=self.handoffs,
            model_settings=self.model_settings
        )

    async def build_dynamic_agents(self, user: User):

        pass
        #asana_connector = AsanaConnector(user)
        #asana_agent = await asana_connector.get_agent()
        #self.handoffs.append(asana_agent)
        
