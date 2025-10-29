# from .utils.display_response import display_response_check
import json

import requests
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

CANOPY_API_KEY = SETTINGS.canopy_api_key


@function_tool
def search_amazon(wrapper: RunContextWrapper[ChatContext], query: str) -> dict:
    """Search Amazon products. Returns top 10 results with price, ratings, Prime status.

    Args:
        wrapper: Context wrapper
        query: Search term (product name, category, brand)

    Returns:
        ToolResponse with product array: asin, url, title, price, rating, isPrime
    """

    product_search_query = '''query ProductSearchQuery($searchTerm: String!) {
        amazonProductSearchResults(input: {searchTerm: $searchTerm}) {
            productResults(input: {limit: "2"}) {
            results {
              asin
              url
              title
              subtitle
              sponsored
              reviewsTotal
              ratingsTotal
              rating
              price {
                currency
                display
                symbol
                value
              }
              mainImageUrl
              imageUrls
              isNew
              isPrime
              brand
            }
          }
        }
      }
    '''
    url = 'https://graphql.canopyapi.co/'
    headers = {
        'Authorization': f'Bearer {CANOPY_API_KEY}'
    }

    variables = {
        'searchTerm': query
    }

    response = requests.post(url, headers=headers, json={
                             'query': product_search_query, 'variables': variables})
    return ToolResponse(
        response_type="amazon_product_search",
        agent_name="Amazon",
        friendly_name="Amazon Product Search",
        response=response.json()['data']['amazonProductSearchResults']
    ).to_dict()


@function_tool
def get_product_details(wrapper: RunContextWrapper[ChatContext], asin: str) -> dict:
    """Get Amazon product details including reviews.

    Args:
        wrapper: Context wrapper
        asin: Amazon Standard Identification Number

    Returns:
        ToolResponse with full product info, pricing, ratings, reviews
    """
    query = '''query ProductDetailsQuery($asin: String!) {
        amazonProduct(input: {asin: $asin}) {
            title
            brand
            mainImageUrl
            ratingsTotal
            rating
            price {
                display
                currency
                symbol
                value
            }
            asin
            imageUrls
            isNew
            isPrime
            reviewsTotal
            reviewsPaginated {
                reviews {
                    body
                    id
                    rating
                    title
                    verifiedPurchase
                }
            }
            sponsored
            subtitle
            url
            topReviews {
                body
                helpfulVotes
                imageUrls
                rating
                reviewer {
                    name
                }
                title
                verifiedPurchase
            }
        }
    }
    '''
    variables = {
        'asin': asin
    }
    url = 'https://graphql.canopyapi.co/'
    headers = {
        'Authorization': f'Bearer {CANOPY_API_KEY}'
    }
    response = requests.post(url, headers=headers, json={
                             'query': query, 'variables': variables})
    return ToolResponse(
        response_type="amazon_product_details",
        agent_name="Amazon",
        friendly_name="Amazon Product Details",
        response=response.json()['data']['amazonProduct']
    ).to_dict()


INSTRUCTIONS = """Amazon shopping assistant. Search products, get details with reviews. Only respond to requests mentioning Amazon. Returns top 2 search results."""

AMAZON_AGENT = Agent(
    name="Amazon",
    model="gpt-4o",
    instructions=RECOMMENDED_PROMPT_PREFIX + INSTRUCTIONS,
    handoff_description=RECOMMENDED_PROMPT_PREFIX +
    """Amazon product search and details. Only handles Amazon-specific requests.""",
    tools=[search_amazon, get_product_details],
    handoffs=[GOOGLE_DOCS_AGENT, GMAIL_AGENT]
)

AMAZON_REALTIME_AGENT = RealtimeAgent(
    name="Amazon",
    instructions=INSTRUCTIONS,
    tools=[search_amazon, get_product_details]
)
