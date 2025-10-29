
from agents import Agent, RunContextWrapper, function_tool
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from serpapi import GoogleSearch  # type: ignore

from .fetch_website import FETCH_WEBSITE_AGENT
from .gmail import GMAIL_AGENT
from .google_docs import GOOGLE_DOCS_AGENT
from .open_external_url import OPEN_EXTERNAL_URL_AGENT
from .utils.context import ChatContext
from .utils.responses import ToolResponse

try:
    from config import Settings
except ImportError:
    from ..config import Settings
SETTINGS = Settings()
SERPAPI_API_KEY = SETTINGS.serpapi_api_key


@function_tool
def get_google_news_top_stories(wrapper: RunContextWrapper[ChatContext]):
    """Retrieve the latest breaking news and top stories from Google News across all major categories.

    WHEN TO USE THIS TOOL:
    - User asks about current news, today's news, or latest news without a specific topic
    - User mentions: "what's in the news", "top stories", "headlines", "breaking news"
    - User wants a general news update or daily news briefing
    - User asks "what's happening today" or "what's going on in the world"
    - User requests news overview without specifying a topic
    - User asks about major events or important stories
    - User wants to know trending news stories
    - User asks for a news summary or news roundup
    - User mentions "catch me up on the news" or "news update"
    - User asks about current events or world events
    - Start of conversation when user might want news updates
    - User asks "what should I know about today"

    WHAT THIS TOOL DOES:
    - Fetches the most important current news stories from Google News
    - Provides top headlines from multiple news categories
    - Returns breaking news and developing stories
    - Includes diverse sources for balanced coverage
    - Shows publication times to ensure freshness
    - Covers world news, US news, business, technology, entertainment, sports, science, and health
    - Provides article titles, sources, snippets, and links
    - Automatically curates the most relevant stories

    KEY TRIGGER PHRASES:
    - "what's in the news"
    - "top stories"
    - "latest news"
    - "breaking news"
    - "current news"
    - "today's news"
    - "headlines"
    - "news update"
    - "what's happening"
    - "current events"
    - "major news"
    - "important stories"
    - "news briefing"
    - "daily news"
    - "trending news"
    - "world events"
    - "catch me up"
    - "news summary"
    - "what's going on"
    - "news today"

    COMMON USE CASES:
    - Morning news briefing
    - Staying informed about current events
    - Getting a quick news overview
    - Checking for breaking news
    - Daily news routine
    - Catching up after being offline
    - General awareness of world events

    Args:
        wrapper: Run context with chat context

    Returns:
        ToolResponse containing:
            - Article titles and headlines
            - News sources (CNN, BBC, Reuters, etc.)
            - Publication dates and times
            - Article snippets/summaries
            - Direct links to full articles
            - Source credibility indicators

    Note: Returns the top stories algorithm-selected by Google News.
    Does not require a search query - automatically provides top stories.
    Results are updated in real-time as news develops.
    """
    params = {
        # 'q': query,
        'engine': 'google_news',
        'api_key': SERPAPI_API_KEY
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    # print(results.keys())
    top_stories = results['news_results']
    return ToolResponse(
        response_type="google_news_top_stories",
        agent_name="Google",
        friendly_name="Google News Top Stories",
        display_response=False,
        response=top_stories
    ).to_dict()


@function_tool
def search_google_news(wrapper: RunContextWrapper[ChatContext], query: str):
    """Search Google News for specific topics, events, people, companies, or any custom news query.

    WHEN TO USE THIS TOOL:
    - User asks about news on a SPECIFIC topic, person, company, or event
    - User mentions: "news about [topic]", "what's happening with [topic]", "[topic] news"
    - User asks about specific companies (Apple, Tesla, Google, etc.)
    - User asks about specific people (celebrities, politicians, CEOs, athletes)
    - User asks about specific events (elections, sports events, conferences)
    - User asks about specific locations (country news, city news, regional events)
    - User asks about specific industries (tech news, finance news, healthcare news)
    - User wants updates on ongoing stories or developing situations
    - User asks about specific categories with detail (e.g., "AI news", "climate change news")
    - User mentions specific news topics like politics, economy, technology, sports teams
    - User asks "any news about [X]" or "latest on [X]"
    - User wants to track a specific story or topic over time
    - User asks about specific incidents, accidents, or announcements

    WHAT THIS TOOL DOES:
    - Searches Google News for articles matching the specific query
    - Returns relevant articles from the past few days to weeks
    - Filters results to match the search terms precisely
    - Provides multiple perspectives on the same topic
    - Includes local, national, and international sources
    - Returns chronologically relevant results (newest first)
    - Finds niche topics and specialized news
    - Locates news about specific entities (people, companies, places)

    KEY TRIGGER PHRASES WITH TOPICS:
    - "news about [specific topic]"
    - "[company name] news"
    - "what's happening with [person/company]"
    - "latest on [event/topic]"
    - "updates on [situation]"
    - "[topic] headlines"
    - "search news for [query]"
    - "find news about [subject]"
    - "[industry] news"
    - "[location] news"
    - "any news on [topic]"
    - "[person name] in the news"
    - "developments in [field]"
    - "[event] coverage"
    - "stories about [topic]"

    EXAMPLE QUERIES TO SEARCH FOR:
    - "Apple iPhone announcement"
    - "Tesla stock"
    - "President Biden"
    - "World Cup"
    - "artificial intelligence breakthroughs"
    - "climate change summit"
    - "SpaceX launch"
    - "COVID variants"
    - "cryptocurrency regulation"
    - "Taylor Swift tour"
    - "earthquake Japan"
    - "Fed interest rates"
    - "Ukraine conflict"
    - "Silicon Valley layoffs"

    COMMON USE CASES:
    - Tracking specific companies or stocks
    - Following political developments
    - Monitoring industry trends
    - Researching specific events
    - Following celebrities or public figures
    - Tracking sports teams or events
    - Monitoring local news for specific areas
    - Following developing stories
    - Researching for specific topics

    Args:
        wrapper: Run context with chat context
        query: Search query for news articles - be specific and include key terms
            Examples: "Apple earnings", "climate change 2024", "World Cup finals"

    Returns:
        ToolResponse containing:
            - Articles specifically matching the search query
            - Relevance-ranked results
            - Source diversity for balanced coverage
            - Recent publication dates
            - Direct links to full articles
            - Snippets highlighting query relevance

    Note: More specific queries return more relevant results.
    Use entity names (companies, people) for best results.
    Combines multiple related articles on the same topic.
    """
    params = {
        'q': query,
        'engine': 'google_news',
        'api_key': SERPAPI_API_KEY
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    # print(results.keys())
    search_results = results['news_results']
    return ToolResponse(
        response_type="google_news_search_results",
        agent_name="Google",
        friendly_name="Google News Search Results",
        display_response=False,
        response=search_results
    ).to_dict()


GOOGLE_NEWS_AGENT = Agent(
    name="Google News",
    model="gpt-4o",
    instructions=RECOMMENDED_PROMPT_PREFIX + """You are a Google News assistant that provides comprehensive, up-to-date news information from around the world.

Your primary functions:
1. Deliver breaking news and top headlines across all categories
2. Search for specific news topics, people, companies, or events
3. Provide balanced coverage from multiple reputable sources
4. Track developing stories and ongoing events
5. Offer news summaries and daily briefings
6. Find specialized or niche news topics

You should proactively use your tools when users:
- Ask about current events or what's happening
- Want news updates (general or specific topics)
- Mention specific people, companies, or events in a news context
- Request daily briefings or news summaries
- Ask about headlines or breaking news
- Want to track specific stories or topics
- Need information about recent developments
- Ask "what's in the news" or similar phrases

For general news requests, use get_google_news_top_stories.
For specific topics, people, or companies, use search_google_news with relevant query terms.

Always provide concise summaries of multiple articles when appropriate, and offer to search for more specific topics if the user needs detailed information.""",
    handoff_description=RECOMMENDED_PROMPT_PREFIX + """Google News - Real-time News & Current Events Assistant

I can help with:
• Latest breaking news and top headlines
• News about specific topics, companies, or people
• Current events and world happenings
• Daily news briefings and summaries
• Tracking developing stories
• Industry-specific news (tech, finance, sports, etc.)
• Local and international news coverage

Use me when the user asks about news, current events, headlines, or wants updates on specific topics, people, or companies.""",
    tools=[get_google_news_top_stories, search_google_news],
    handoffs=[GOOGLE_DOCS_AGENT, OPEN_EXTERNAL_URL_AGENT,
              FETCH_WEBSITE_AGENT, GMAIL_AGENT]
)

ALL_TOOLS = [get_google_news_top_stories, search_google_news]
