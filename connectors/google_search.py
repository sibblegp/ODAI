from agents import Agent
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents import function_tool, RunContextWrapper
from agents.realtime import RealtimeAgent
from .utils.responses import ToolResponse
from .utils.context import ChatContext
from .utils.display_response import display_response_check
import json
from typing import Optional
import os
import requests
from serpapi import GoogleSearch  # type: ignore
from .google_docs import GOOGLE_DOCS_AGENT
from .gmail import GMAIL_AGENT
from .open_external_url import OPEN_EXTERNAL_URL_AGENT
from .fetch_website import FETCH_WEBSITE_AGENT

try:
    from config import Settings
except ImportError:
    from ..config import Settings

SETTINGS = Settings()

SERPAPI_API_KEY = SETTINGS.serpapi_api_key


@function_tool
def search_google(wrapper: RunContextWrapper[ChatContext], query: str):
    """Perform a Google search and return the results.

    Args:
        wrapper: Context wrapper containing settings and user info
        query: Search query string (e.g., "weather in New York", "latest AI news")
    Returns:
        ToolResponse with organic search results containing titles, links, snippets,
        and metadata like dates, sitelinks, and rich snippets.
    """
    params = {
        'q': query,
        'engine': 'google',
        'api_key': SERPAPI_API_KEY
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    # print(results.keys())
    search_results = results['organic_results']
    return ToolResponse(
        response_type="google_search_results",
        agent_name="Google",
        friendly_name="Google Search Results",
        response=search_results
    ).to_dict()


GOOGLE_SEARCH_AGENT = Agent(
    name="Google Search",
    model="gpt-4o",
    instructions=RECOMMENDED_PROMPT_PREFIX +
    "Search the web via Google Search and provide relevant results with titles, links, and snippets.",
    handoff_description=RECOMMENDED_PROMPT_PREFIX +
    "Google Search for web information.",
    tools=[search_google],
    handoffs=[GOOGLE_DOCS_AGENT, GMAIL_AGENT,
              OPEN_EXTERNAL_URL_AGENT, FETCH_WEBSITE_AGENT]
)

REALTIME_GOOGLE_SEARCH_AGENT = RealtimeAgent(
    name="Google Search",
    instructions=RECOMMENDED_PROMPT_PREFIX +
    "Search Google for information when needed.",
    tools=[search_google]
)

ALL_TOOLS = [search_google]
