from agents import Agent, function_tool
from typing import Optional
import os
from agents.realtime import RealtimeAgent
import requests
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from .utils.responses import ToolResponse
from .google_docs import GOOGLE_DOCS_AGENT
from .gmail import GMAIL_AGENT

try:
    from config import Settings
except ImportError:
    from ..config import Settings

SETTINGS = Settings()

YELP_API_KEY = SETTINGS.yelp_api_key


@function_tool
def search_businesses_at_yelp(location: str, search_term: str, sort_by_rating: Optional[bool], limit: Optional[int]) -> dict:
    """Search for restaurants and businesses using the Yelp API.

    Business hours return a day identifier as a number. 0 is Monday, 1 is Tuesday, etc. No listing for a specific day means the business is closed on that day.

    Args:
        location: Location to search (e.g., "Boston, MA", "10001")
        search_term: What to search for (e.g., "sushi", "coffee shops")
        sort_by_rating: True for highest rating first, False/None for best match
        limit: Number of results (default: 10, max: 50)
    Returns:
        ToolResponse with list of businesses including name, rating, price, location.
    """
    print(location)
    url = "https://api.yelp.com/v3/businesses/search"
    headers = {
        "Authorization": f"Bearer {YELP_API_KEY}"
    }
    if limit is None:
        limit = 10
    params = {
        "location": location,
        "term": search_term,
        "limit": limit,
        "sort_by": "rating" if sort_by_rating else "best_match"
    }
    print(params)
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    return ToolResponse(
        response_type="yelp_search_results",
        agent_name="Yelp",
        friendly_name="Searching Yelp for " + search_term + " in " + location,
        display_response=True,
        response=data["businesses"]
    ).to_dict()


@function_tool
def get_business_reviews_at_yelp(business_id: str) -> dict:
    """Get detailed customer reviews for a specific business from Yelp.

    Args:
        business_id: Unique Yelp business ID from search results
    Returns:
        ToolResponse with up to 3 reviews including rating, text, and user info.
    """
    url = f"https://api.yelp.com/v3/businesses/{business_id}/reviews?sort_by=yelp_sort"
    headers = {
        "Authorization": f"Bearer {YELP_API_KEY}"
    }
    print(business_id)
    response = requests.get(url, headers=headers)
    data = response.json()
    print(data)
    return ToolResponse(
        response_type="yelp_reviews",
        agent_name="Yelp",
        friendly_name="Getting reviews from Yelp",
        display_response=True,
        response=data["reviews"]
    ).to_dict()


YELP_AGENT = Agent(
    name="Yelp",
    model="gpt-4o",
    tools=[search_businesses_at_yelp, get_business_reviews_at_yelp],
    handoff_description=RECOMMENDED_PROMPT_PREFIX + "Yelp search and reviews.",
    # instructions="You are a helpful assistant that helps find restaurants and get their reviews"
    #     "You will provide responses in JSON format. Each response should include a "
    #     "'prompt' field containing a follow-up question or statement for the user and a 'response'. "
    #     "The prompt should just be a question or statement to the user about next steps without any details from tool calls. "
    #     "The prompt should be a natural conversational question or statement, without "
    #     "any details from tool calls. Keep responses clean and simple - "
    #     "do not wrap the JSON in any markdown or HTML formatting."
    #     "Do not include any other field other than the 'prompt' field in the JSON response.",
    instructions=RECOMMENDED_PROMPT_PREFIX +
    "Search Yelp for businesses and retrieve reviews. Do not display results by default.",
    handoffs=[GOOGLE_DOCS_AGENT, GMAIL_AGENT]
)

YELP_REALTIME_AGENT = RealtimeAgent(
    name="Yelp",
    instructions=RECOMMENDED_PROMPT_PREFIX +
    "Search Yelp for businesses and retrieve customer reviews.",
    tools=[search_businesses_at_yelp, get_business_reviews_at_yelp]
)

ALL_TOOLS = [search_businesses_at_yelp, get_business_reviews_at_yelp]
