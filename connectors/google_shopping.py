from agents import Agent
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents import function_tool, RunContextWrapper
from .utils.responses import ToolResponse
import finnhub
from .utils.context import ChatContext
from .utils.display_response import display_response_check
import json
from typing import Optional
import os
import requests
from serpapi import GoogleSearch

try:
    from config import Settings
except ImportError:
    from ..config import Settings
from .google_docs import GOOGLE_DOCS_AGENT
from .gmail import GMAIL_AGENT
from .open_external_url import OPEN_EXTERNAL_URL_AGENT
from .fetch_website import FETCH_WEBSITE_AGENT
from .exchange_rate import EXCHANGE_RATE_AGENT

SETTINGS = Settings()

SERPAPI_API_KEY = SETTINGS.serpapi_api_key


@function_tool
def get_google_products(wrapper: RunContextWrapper[ChatContext], query: str):
    """Search Google Shopping for products with prices and sellers.

    Args:
        wrapper: Context wrapper containing chat state and user information
        query: Product search query (e.g., "iPhone 15", "laptops under $1000")
    Returns:
        ToolResponse with shopping results including titles, prices, sellers,
        ratings, and purchase links.
    """
    params = {
        'q': query,
        'engine': 'google_shopping',
        'api_key': SERPAPI_API_KEY
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    print(results.keys())
    products = results['shopping_results']
    return ToolResponse(
        response_type="google_products",
        agent_name="Google",
        friendly_name="Google Products",
        response=products
    ).to_dict()


GOOGLE_SHOPPING_AGENT = Agent(
    name="Google Shopping",
    model="gpt-4o",
    instructions=RECOMMENDED_PROMPT_PREFIX +
    "Search Google Shopping and compare product prices across retailers.",
    handoff_description=RECOMMENDED_PROMPT_PREFIX +
    "Google Shopping for product search and price comparison.",
    tools=[get_google_products],
    handoffs=[GOOGLE_DOCS_AGENT, GMAIL_AGENT, OPEN_EXTERNAL_URL_AGENT,
              FETCH_WEBSITE_AGENT, EXCHANGE_RATE_AGENT]
)

ALL_TOOLS = [get_google_products]
