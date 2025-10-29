from agents.realtime.agent import RealtimeAgent
from agents import function_tool
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

try:
    # from walgreens import WALGREENS_AGENT
    from amadeus_agent import REALTIME_AMADEUS_AGENT
    from yelp import YELP_REALTIME_AGENT
    # from opentable import OPENTABLE_AGENT
    # from alpaca import ALPACA_AGENT
    from coinmarketcap import COINMARKETCAP_REALTIME_AGENT
    # from location import LOCATION_AGENT
    # from flights import FLIGHT_AGENT
    # from instacart import INSTACART_AGENT
    # from spotify import SPOTIFY_AGENT
    # from slack import SLACK_AGENT
    from plaid_agent import PLAID_AGENT
    from finnhub_agent import FINNHUB_REALTIME_AGENT
    from google_calendar import GOOGLE_CALENDAR_AGENT
    from google_docs import GOOGLE_DOCS_AGENT
    from tripadvisor import TRIPADVISOR_AGENT
    from google_shopping import GOOGLE_SHOPPING_AGENT
    from google_news import GOOGLE_NEWS_AGENT
    from google_search import REALTIME_GOOGLE_SEARCH_AGENT
    from fetch_website import REALTIME_FETCH_WEBSITE_AGENT
    from amazon import AMAZON_REALTIME_AGENT
    from open_external_url import OPEN_EXTERNAL_URL_AGENT
    # from twitter import TWITTER_AGENT
    from amtrak import REALTIME_AMTRAK_AGENT
    from ticketmaster import REALTIME_TICKETMASTER_AGENT
    # from evernote import EVERNOTE_AGENT
    from weatherapi import REALTIME_WEATHERAPI_AGENT
    from easypost_agent import EASYPOST_AGENT
    from movieglu import REALTIME_MOVIEGLU_AGENT
    from twilio_assistant import hangup_call
    from flightaware import REALTIME_FLIGHTAWARE_AGENT
except ImportError:
    # from .walgreens import WALGREENS_AGENT
    from .amadeus_agent import REALTIME_AMADEUS_AGENT
    from .yelp import YELP_REALTIME_AGENT
    # from .opentable import OPENTABLE_AGENT
    # from .alpaca import ALPACA_AGENT
    from .coinmarketcap import COINMARKETCAP_REALTIME_AGENT
    # from .location import LOCATION_AGENT
    from .gmail import GMAIL_AGENT
    # from .flights import FLIGHT_AGENT
    # from .instacart import INSTACART_AGENT
    # from .spotify import SPOTIFY_AGENT
    # from .slack import SLACK_AGENT
    from .plaid_agent import PLAID_AGENT
    from .finnhub_agent import FINNHUB_REALTIME_AGENT
    from .google_calendar import GOOGLE_CALENDAR_AGENT
    from .google_docs import GOOGLE_DOCS_AGENT
    from .tripadvisor import TRIPADVISOR_AGENT
    from .google_shopping import GOOGLE_SHOPPING_AGENT
    from .google_news import GOOGLE_NEWS_AGENT
    from .google_search import REALTIME_GOOGLE_SEARCH_AGENT
    from .fetch_website import REALTIME_FETCH_WEBSITE_AGENT
    from .amazon import AMAZON_REALTIME_AGENT
    from .open_external_url import OPEN_EXTERNAL_URL_AGENT
    # from .twitter import TWITTER_AGENT
    from .amtrak import REALTIME_AMTRAK_AGENT
    # from .evernote import EVERNOTE_AGENT
    from .ticketmaster import REALTIME_TICKETMASTER_AGENT
    from .weatherapi import REALTIME_WEATHERAPI_AGENT
    from .easypost_agent import EASYPOST_AGENT
    from .movieglu import REALTIME_MOVIEGLU_AGENT
    from .twilio_assistant import hangup_call
    from .flightaware import REALTIME_FLIGHTAWARE_AGENT
try:
    from finnhub_agent import get_stock_price_at_finnhub
except ImportError:
    from .finnhub_agent import get_stock_price_at_finnhub

try:
    from connectors.coinmarketcap import ALL_TOOLS as COINMARKETCAP_TOOLS
    from connectors.plaid_agent import ALL_TOOLS as PLAID_TOOLS
    from connectors.finnhub_agent import ALL_TOOLS as FINNHUB_TOOLS
    from connectors.google_calendar import ALL_TOOLS as GOOGLE_CALENDAR_TOOLS
    from connectors.google_docs import ALL_TOOLS as GOOGLE_DOCS_TOOLS
    from connectors.tripadvisor import ALL_TOOLS as TRIPADVISOR_TOOLS
    from connectors.google_shopping import ALL_TOOLS as GOOGLE_SHOPPING_TOOLS
    from connectors.google_news import ALL_TOOLS as GOOGLE_NEWS_TOOLS
    from connectors.google_search import ALL_TOOLS as GOOGLE_SEARCH_TOOLS
    from connectors.amtrak import ALL_TOOLS as AMTRAK_TOOLS
    from connectors.ticketmaster import ALL_TOOLS as TICKETMASTER_TOOLS
    from connectors.weatherapi import ALL_TOOLS as WEATHERAPI_TOOLS
    from connectors.easypost_agent import ALL_TOOLS as EASYPOST_TOOLS
    from connectors.movieglu import ALL_TOOLS as MOVIEGLU_TOOLS
    from connectors.yelp import ALL_TOOLS as YELP_TOOLS
    from connectors.gmail import ALL_TOOLS as GMAIL_TOOLS
    from connectors.fetch_website import ALL_TOOLS as FETCH_WEBSITE_TOOLS
    from connectors.flightaware import ALL_TOOLS as FLIGHTAWARE_TOOLS
except ImportError:
    from .coinmarketcap import ALL_TOOLS as COINMARKETCAP_TOOLS
    from .plaid_agent import ALL_TOOLS as PLAID_TOOLS
    from .finnhub_agent import ALL_TOOLS as FINNHUB_TOOLS
    from .google_calendar import ALL_TOOLS as GOOGLE_CALENDAR_TOOLS
    from .google_docs import ALL_TOOLS as GOOGLE_DOCS_TOOLS
    from .tripadvisor import ALL_TOOLS as TRIPADVISOR_TOOLS
    from .google_shopping import ALL_TOOLS as GOOGLE_SHOPPING_TOOLS
    from .google_news import ALL_TOOLS as GOOGLE_NEWS_TOOLS
    from .google_search import ALL_TOOLS as GOOGLE_SEARCH_TOOLS
    from .ticketmaster import ALL_TOOLS as TICKETMASTER_TOOLS
    from .easypost_agent import ALL_TOOLS as EASYPOST_TOOLS
    from .movieglu import ALL_TOOLS as MOVIEGLU_TOOLS
    from .yelp import ALL_TOOLS as YELP_TOOLS
    from .gmail import ALL_TOOLS as GMAIL_TOOLS
    from .amtrak import ALL_TOOLS as AMTRAK_TOOLS
    from .weatherapi import ALL_TOOLS as WEATHERAPI_TOOLS
    from .fetch_website import ALL_TOOLS as FETCH_WEBSITE_TOOLS
    from .flightaware import ALL_TOOLS as FLIGHTAWARE_TOOLS
VOICE_ORCHESTRATOR_TOOLS = [
    *COINMARKETCAP_TOOLS,
    # *PLAID_TOOLS,
    *FINNHUB_TOOLS,
    # *GOOGLE_CALENDAR_TOOLS,
    # *GOOGLE_DOCS_TOOLS,
    *TRIPADVISOR_TOOLS,
    *GOOGLE_SHOPPING_TOOLS,
    *GOOGLE_NEWS_TOOLS,
    *GOOGLE_SEARCH_TOOLS,
    *AMTRAK_TOOLS,
    *TICKETMASTER_TOOLS,
    *WEATHERAPI_TOOLS,
    *EASYPOST_TOOLS,
    *MOVIEGLU_TOOLS,
    *YELP_TOOLS,
    # *GMAIL_TOOLS,
    *FETCH_WEBSITE_TOOLS,
    *FLIGHTAWARE_TOOLS,
]

SYSTEM_MESSAGE = """
**System Prompt — ODAI Voice Assistant**

You are **ODAI Voice**, a real-time voice agent. Your mission is to be helpful, kind, concise, friendly, and straight to the point.

**Core Voice Principles**

1. **Speak naturally.** Use clear, conversational sentences that sound like a human helper.
2. **Stay concise.** Deliver only the information the user needs right now—no extra commentary, no filler.
3. **Be friendly and reassuring.** Use a warm tone that puts the listener at ease.
4. **Remember it’s voice.**
   • Don’t spell out URLs or read long strings of text.
   • If you need to reference a source, paraphrase; never mention a web address.
   • When listing, say “first,” “second,” “third,” and so on—never “one,” “two,” “three” or bullet points.

**Using Tools**

* You have multiple tools at your disposal (news, calendar, email, stock quotes, weather, etc.).
* Quickly choose the single most relevant tool or combination of tools.
* Summarize the result in plain speech, focusing on the part that answers the user’s immediate question.
* If a tool returns extensive data, distill it to the essential facts before speaking.

**Interaction Guidelines**

* **Acknowledge, then act.** Briefly confirm what the user asked (“Sure, here’s the weather for today”) before delivering the answer.
* **Clarify sparingly.** Only ask follow-up questions if absolutely necessary to fulfill the request.
* **Keep context short-lived.** Retain just enough recent information to maintain a smooth conversation; avoid repeating it aloud unless asked.
* **End with help.** Conclude answers with a short offer: “Anything else I can help you with?”

By following these rules, you provide fast, friendly voice assistance that respects the listener’s time and attention.

If the user says the conversation is over, say goodbye and then call the hangup_call tool.

"""

AUDIO_AGENT = RealtimeAgent(
    name="ODAI-Voice",
    instructions=RECOMMENDED_PROMPT_PREFIX + SYSTEM_MESSAGE,
    # tools=[hangup_call],
    tools=[hangup_call, *VOICE_ORCHESTRATOR_TOOLS],
    # handoffs=[FINNHUB_REALTIME_AGENT, AMAZON_REALTIME_AGENT, COINMARKETCAP_REALTIME_AGENT, REALTIME_AMADEUS_AGENT, REALTIME_AMTRAK_AGENT,
            #   REALTIME_FETCH_WEBSITE_AGENT, REALTIME_MOVIEGLU_AGENT, REALTIME_FLIGHTAWARE_AGENT, REALTIME_TICKETMASTER_AGENT, REALTIME_WEATHERAPI_AGENT, YELP_REALTIME_AGENT, REALTIME_GOOGLE_SEARCH_AGENT]
)
