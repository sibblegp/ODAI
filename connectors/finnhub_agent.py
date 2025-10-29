import json
from typing import Optional

import finnhub
from agents import Agent, RunContextWrapper, function_tool
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents.realtime.agent import RealtimeAgent

from .gmail import GMAIL_AGENT
from .google_docs import GOOGLE_DOCS_AGENT
from .utils.context import ChatContext
from .utils.responses import ToolResponse

try:
    from config import Settings
except ImportError:
    from ..config import Settings

SETTINGS = Settings()


FINNHUB_CLIENT = finnhub.Client(
    api_key=SETTINGS.finnhub_api_key)


def get_company_profile_at_finnhub(symbol: str) -> dict | None:
    matching_companies = FINNHUB_CLIENT.symbol_lookup(symbol)
    for company in matching_companies['result']:
        if company['symbol'] == symbol:
            company['description'] = company['description'].title()
            return company
    return None


@function_tool
def get_stock_price_at_finnhub(wrapper: RunContextWrapper[ChatContext], symbol: str) -> dict:
    """Get real-time stock price. Args: symbol: ticker symbol. Returns: price and trading data."""
    quote = FINNHUB_CLIENT.quote(symbol)
    company_profile = get_company_profile_at_finnhub(symbol)
    # display_response = display_response_check(
    #     wrapper.context.prompt,
    #     "Given this prompt, should a whole response with all stock data be returned to the user be displayed to the user? " +
    #     "All stock data should be displayed when they are asking for the stock price. All stock data should not be displayed when they are asking for some specific information other than the " +
    #     "such as low or high or open. Return your response in json format with a boolean value called " +
    #     "'display_response'."
    # )
    return ToolResponse(
        response_type="stock_price",
        agent_name="Finnhub",
        friendly_name="Stock Quote",
        display_response=True,
        response={
            'price': quote['c'],
            'symbol': symbol,
            'change': quote['d'],
            'percent_change': quote['dp'],
            'open': quote['o'],
            'high': quote['h'],
            'low': quote['l'],
            'company': company_profile
        }
    ).to_dict()


@function_tool
def get_annual_financials_at_finnhub(wrapper: RunContextWrapper[ChatContext], symbol: str, year: Optional[int] = None, most_recent: bool = True) -> dict:
    """Get annual financials. Args: symbol: ticker, year: specific year, most_recent: latest data. Returns: financial statements."""
    print(year, most_recent)
    annual_financials = FINNHUB_CLIENT.financials_reported(
        symbol=symbol, freq='annual')
    company_profile = get_company_profile_at_finnhub(symbol)
    if most_recent:
        annual_financials = annual_financials['data'][0]
    elif year:
        for report in annual_financials['data']:
            if report['year'] == year:
                annual_financials = report
                break
    return ToolResponse(
        response_type="get_annual_stock_financials",
        agent_name="Finnhub",
        friendly_name="Annual Financials",
        display_response=True,
        response={
            'annual_financials': annual_financials,
            'company': company_profile
        }
    ).to_dict()


@function_tool
def get_quarterly_stock_financials_at_finnhub(wrapper: RunContextWrapper[ChatContext], symbol: str, year: int, quarter: int, most_recent: bool = True) -> dict:
    """Get quarterly financials. Args: symbol: ticker, year: year, quarter: 1-4, most_recent: latest. Returns: financial statements."""
    if not 1 <= quarter <= 4:
        raise ValueError("Quarter must be between 1 and 4")
    quarterly_financials = FINNHUB_CLIENT.financials_reported(
        symbol=symbol, freq='quarterly')
    company_profile = get_company_profile_at_finnhub(symbol)
    if most_recent:
        quarterly_financials = quarterly_financials['data'][0]
    elif year and quarter:
        for report in quarterly_financials['data']:
            if report['year'] == year and report['quarter'] == quarter:
                quarterly_financials = report
                break
    return ToolResponse(
        response_type="get_quarterly_stock_financials",
        agent_name="Finnhub",
        friendly_name="Quarterly Financials",
        display_response=True,
        response={
            'quarterly_financials': quarterly_financials,
            'company': company_profile
        }
    ).to_dict()


INSTRUCTIONS = """Provide real-time stock quotes and financial statements."""

FINNHUB_AGENT = Agent(
    name="Finnhub",
    model="gpt-4o",
    handoff_description=RECOMMENDED_PROMPT_PREFIX +
    """Stock quotes and financials.""",
    instructions=RECOMMENDED_PROMPT_PREFIX + INSTRUCTIONS,
    tools=[get_stock_price_at_finnhub, get_annual_financials_at_finnhub,
           get_quarterly_stock_financials_at_finnhub],
    handoffs=[GOOGLE_DOCS_AGENT, GMAIL_AGENT]
)

FINNHUB_REALTIME_AGENT = RealtimeAgent(
    name="Finnhub",
    instructions=INSTRUCTIONS,
    tools=[get_stock_price_at_finnhub, get_annual_financials_at_finnhub,
           get_quarterly_stock_financials_at_finnhub],
)

ALL_TOOLS = [get_stock_price_at_finnhub, get_annual_financials_at_finnhub,
             get_quarterly_stock_financials_at_finnhub]
