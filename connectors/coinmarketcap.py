import requests
from agents import Agent, function_tool
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

from .utils.responses import ToolResponse

try:
    from config import Settings
except ImportError:
    from ..config import Settings
try:
    # from connectors.twitter import TWITTER_AGENT
    from connectors.fetch_website import FETCH_WEBSITE_AGENT
    from connectors.gmail import GMAIL_AGENT
    from connectors.google_docs import GOOGLE_DOCS_AGENT
    from connectors.open_external_url import OPEN_EXTERNAL_URL_AGENT
except ImportError:
    from .google_docs import GOOGLE_DOCS_AGENT
    # from .twitter import TWITTER_AGENT
    from .fetch_website import FETCH_WEBSITE_AGENT
    from .open_external_url import OPEN_EXTERNAL_URL_AGENT
    from .gmail import GMAIL_AGENT

from agents.realtime import RealtimeAgent

SETTINGS = Settings()

COINMAKRETCAP_API_KEY = SETTINGS.coinmarketcap_api_key


@function_tool
def check_crypto_price_at_coinmarketcap(crypto_symbol: str) -> dict:
    """Check current price and market data for a cryptocurrency.

    Args:
        crypto_symbol: Cryptocurrency ticker symbol (e.g., BTC, ETH, SOL)
    Returns:
        ToolResponse with price, market cap, volume, and percentage changes
    """
    headers = {
        "X-CMC_PRO_API_KEY": COINMAKRETCAP_API_KEY
    }
    response = requests.get(
        f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest?symbol={crypto_symbol}", headers=headers)
    data = response.json()
    # print(data)
    return ToolResponse(
        response_type="crypto_price",
        agent_name="CoinMarketCap",
        friendly_name="Checking the price of " + crypto_symbol,
        display_response=True,
        response=data
    ).to_dict()


INSTRUCTIONS = """Provide real-time cryptocurrency prices and market data from CoinMarketCap."""

COINMARKETCAP_AGENT = Agent(
    name="CoinMarketCap",
    model="gpt-4o",
    handoff_description=RECOMMENDED_PROMPT_PREFIX +
    "Cryptocurrency prices from CoinMarketCap.",
    instructions=RECOMMENDED_PROMPT_PREFIX + INSTRUCTIONS,
    tools=[check_crypto_price_at_coinmarketcap],
    handoffs=[GOOGLE_DOCS_AGENT, FETCH_WEBSITE_AGENT,
              OPEN_EXTERNAL_URL_AGENT, GMAIL_AGENT]
)


COINMARKETCAP_REALTIME_AGENT = RealtimeAgent(
    name="CoinMarketCap",
    instructions=INSTRUCTIONS,
    tools=[check_crypto_price_at_coinmarketcap]
)

ALL_TOOLS = [check_crypto_price_at_coinmarketcap]
