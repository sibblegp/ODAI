# ODAI AI Assistant Agents Documentation

## Overview

ODAI (ODAI AI Assistant) is a comprehensive AI assistant platform built on FastAPI that orchestrates multiple specialized agents to handle diverse user requests. The system uses OpenAI's Agent framework with a hub-and-spoke architecture where a central orchestrator routes requests to specialized agents.

## Architecture

### Core Components

1. **Main Application** (`api.py`): FastAPI application with WebSocket support
2. **Orchestrator** (`connectors/orchestrator.py`): Central agent that routes requests
3. **Voice Orchestrator** (`connectors/voice_orchestrator.py`): Specialized for voice interactions
4. **Individual Agents**: Specialized tools for specific services and APIs
5. **Services Layer**: Authentication, chat management, location services
6. **Firebase Integration**: User management, chat history, token tracking

### Agent Communication Flow

```
User Request → WebSocket → Orchestrator → Specialized Agent(s) → Response → User
```

The orchestrator uses the **H.A.N.D.O.F.F.** decision framework:
- **H**as capability: Does the agent solve this task?
- **A**ccess: Does it have the right data/API permissions?
- **N**ovelty/Need: Is a tool call necessary vs. known info?
- **D**elay/Cost: Prefer fewer/cheaper calls if quality unaffected
- **O**utput quality: Will it return the needed format/info?
- **F**ailure fallback: Choose alternates if first likely fails
- **F**usion: Orchestrate multiple agents and merge results

## Agent Categories

### 1. Communication & Productivity
- **GMail Agent**: Email management (send, receive, search, reply)
- **Google Calendar Agent**: Event scheduling and calendar management
- **Google Docs Agent**: Document creation, search, and collaboration
- **Slack Agent**: Team communication integration
- **Twilio Assistant**: Voice and SMS capabilities

### 2. Information & Search
- **Google Search Agent**: Web search functionality
- **Google News Agent**: News headlines and stories
- **Fetch Website Agent**: Website content extraction
- **Google Shopping Agent**: Product search and price comparison

### 3. Financial Services
- **Plaid Agent**: Bank account integration (balances, transactions)
- **Plaid Connector Agent**: Account connection setup
- **FinnHub Agent**: Stock market data and financial information
- **CoinMarketCap Agent**: Cryptocurrency prices and market data
- **Exchange Rate Agent**: Currency conversion

### 4. Travel & Transportation
- **FlightAware Agent**: Real-time flight status and tracking
- **Flights Agent**: Flight booking and information
- **AMADEUS Agent**: Flight and hotel search
- **Amtrak Agent**: Train status and schedules
- **Caltrain Agent**: Regional train information

### 5. Local Services & Entertainment
- **Yelp Agent**: Restaurant and business search with reviews
- **TripAdvisor Agent**: Travel recommendations and reviews
- **Ticketmaster Agent**: Event tickets and venue information
- **MovieGlu Agent**: Movie showtimes and theater information

### 6. Weather & Location
- **AccuWeather Agent**: Detailed weather forecasts
- **WeatherAPI Agent**: Current weather and forecasts
- **Location Service**: IP-based location detection

### 7. E-commerce & Shopping
- **Amazon Agent**: Product search and details
- **Google Shopping Agent**: Cross-retailer product comparison

### 8. Utilities & Tools
- **EasyPost Agent**: Package tracking across carriers
- **Open External URL Agent**: URL opening in browser
- **Google Connections Agent**: Google account OAuth setup

## Individual Agent Details

### Gmail Agent (`connectors/gmail.py`)
**Capabilities:**
- Fetch and search inbox messages
- Send emails with attachments
- Reply to existing threads
- Search emails by sender or content
- HTML and plain text message processing

**Key Functions:**
- `fetch_google_email_inbox()`: Retrieve inbox messages
- `search_google_mail()`: Search emails by query
- `send_google_email()`: Send new emails
- `reply_to_google_email()`: Reply to existing threads

**Authentication:** Google OAuth2 with Gmail scope

### Plaid Agent (`connectors/plaid_agent.py`)
**Capabilities:**
- Connect to bank and credit card accounts
- Retrieve account balances
- Fetch transaction history
- Support multiple financial institutions

**Key Functions:**
- `get_accounts_at_plaid()`: Get account balances and details
- `get_transactions_at_plaid()`: Retrieve transaction history

**Environment:** Sandbox (development) and Production environments

### Google Search Agent (`connectors/google_search.py`)
**Capabilities:**
- Perform web searches using SerpAPI
- Return organic search results with metadata
- Extract rich snippets and sitelinks

**Key Functions:**
- `search_google()`: Execute search queries and return results

**Integration:** SerpAPI for Google search results

### Weather Agents
**WeatherAPI Agent** (`connectors/weatherapi.py`):
- Current weather conditions
- Multi-day forecasts (1-14 days)
- Hourly predictions
- Supports various location formats

**AccuWeather Agent** (`connectors/accuweather.py`):
- Real-time weather by coordinates
- Detailed hourly and daily forecasts
- Weather alerts and conditions

### Flight Tracking Agents
**FlightAware Agent** (`connectors/flightaware.py`):
- Real-time flight status
- Departure/arrival information
- Gate and terminal details

**Flight Agent** (`connectors/flights.py`):
- IATA flight code lookups
- Airport information
- Booking capabilities (inactive in current version)

## Orchestrator System

### Main Orchestrator (`connectors/orchestrator.py`)

The central ODAI orchestrator uses gpt-4o and implements the **O.D.A.R.** loop:
1. **Observe**: Parse user input and context
2. **Decide**: Choose appropriate agent(s)
3. **Act**: Execute tool calls (parallel when safe)
4. **Respond**: Synthesize results for user

**Handoff Agents (35+ available):**
```python
ORCHESTRATOR_AGENT = Agent(
    name="ODAI",
    model="gpt-4o",
    handoffs=[
        YELP_AGENT, COINMARKETCAP_AGENT, GMAIL_AGENT,
        PLAID_AGENT, GOOGLE_CALENDAR_AGENT, GOOGLE_DOCS_AGENT,
        # ... all 35+ agents
    ]
)
```

**Tool Call Tracking:**
The system tracks 100+ tool calls with user-friendly progress messages:
```python
TOOL_CALLS = {
    "search_businesses_at_yelp": "Searching Yelp...",
    "get_stock_price_at_finnhub": "Getting Stock Price...",
    "send_google_email": "Sending Email...",
    # ... 100+ tool mappings
}
```

### Voice Orchestrator (`connectors/voice_orchestrator.py`)

Specialized for real-time voice interactions using `RealtimeAgent`:
- Optimized for conversational speech
- Reduced tool set for faster responses
- Voice-specific prompting and response formatting
- Integration with Twilio for phone calls

## Configuration & Setup

### Settings Management (`config.py`)
- **Local Development**: Uses `.env` files
- **Production**: Google Secret Manager integration
- **API Keys**: 25+ service integrations managed
- **Environment Detection**: Automatic local vs. production switching

### Key Configuration Classes:
```python
class Settings(BaseSettings):
    openai_api_key: str
    production: bool
    # 25+ API keys for various services
    plaid_client_id: str
    google_client_id: str
    serpapi_api_key: str
    # ... additional service keys
```

### Firebase Integration
- **Models** (`firebase/models/`): User, Chat, Tokens, Usage tracking
- **Authentication**: Token-based user management
- **Chat History**: Persistent conversation storage
- **Analytics**: Segment integration for usage tracking

## API Structure

### WebSocket Endpoint
```
WSS /chats/{chat_id}?token={auth_token}
```

**Message Format:**
```json
{
    "message": "User prompt text",
    "thread_id": "unique_thread_identifier"
}
```

### REST Endpoints
- `GET /`: Health check and static file serving
- `POST /waitlist`: Email collection
- `POST /google_access_request`: OAuth initiation
- `GET /update_integrations`: Refresh agent configurations
- Development-only endpoints for token reset

### Agent Integration Pattern

Each agent follows a consistent pattern:

```python
@function_tool(is_enabled=enable_check_function)
def agent_function(wrapper: RunContextWrapper[ChatContext], ...params) -> dict:
    """Tool description and usage instructions."""
    # API call logic
    return ToolResponse(
        response_type="agent_specific_type",
        agent_name="Service Name",
        friendly_name="Human Readable Name",
        display_response=True,
        response=processed_data
    ).to_dict()

AGENT = Agent(
    name="Agent Name",
    instructions=PROMPT_PREFIX + specific_instructions,
    handoffs=[related_agents],
    tools=[agent_function, other_tools]
)
```

## Voice vs Regular Agents

### Regular Agents
- Full feature set available
- Detailed responses with formatting
- Support for complex multi-step operations
- Can handle long-form content

### Voice Agents (`REALTIME_*` variants)
- Optimized for speech synthesis
- Concise, conversational responses
- Limited tool set for faster execution
- Special formatting for voice output
- Integration with phone system via Twilio

## Development & Testing

### Project Structure
```
backend/
├── api.py                 # Main FastAPI application
├── connectors/           # All agent implementations
│   ├── orchestrator.py   # Central orchestrator
│   ├── voice_orchestrator.py # Voice-specific orchestrator
│   ├── gmail.py          # Email agent
│   ├── plaid_agent.py    # Financial services
│   └── [35+ other agents]
├── services/             # Core business logic
├── websocket/            # Real-time communication
├── firebase/             # Database models
├── routers/              # API route handlers
└── tests/                # Comprehensive test suite
```

### Agent Registration
Agents are automatically registered through:
1. Import in orchestrator files
2. Addition to handoffs list
3. Integration configuration in `integrations.yaml`
4. Tool call mapping in `TOOL_CALLS` dictionary

### Testing
- **Unit Tests**: Individual agent functionality
- **Integration Tests**: Full agent workflows
- **E2E Tests**: Complete user journeys
- **Firebase Tests**: Database operations
- **WebSocket Tests**: Real-time communication

## Integration Configuration (`integrations.yaml`)

Each agent has a standardized configuration:

```yaml
- id: AgentID
  name: "Human Readable Name"
  description: "Detailed capability description"
  logo: "https://logo-url"
  prompts:
    - "Example usage prompt 1"
    - "Example usage prompt 2"
```

This configuration drives:
- Frontend integration display
- User onboarding prompts
- Agent capability documentation
- Marketing and user education materials

## Security & Authentication

### Multi-layer Security
1. **Firebase Authentication**: User identity management
2. **OAuth2 Integration**: Google, Plaid, and other service auth
3. **API Key Management**: Secure secret storage
4. **Token Validation**: All requests authenticated
5. **Rate Limiting**: Built into individual agents
6. **Environment Isolation**: Separate dev/prod configurations

### Privacy Considerations
- User data encrypted in transit and at rest
- Service tokens stored securely in Firebase
- Agent responses filtered for sensitive information
- Audit logging for all user interactions

## Monitoring & Analytics

### Usage Tracking
- **Segment Integration**: User behavior analytics
- **Token Usage**: OpenAI API consumption tracking
- **Agent Performance**: Success rates and latencies
- **Error Monitoring**: Sentry integration for error tracking

### Metrics Collected
- Agent usage frequency
- Tool call success rates
- User engagement patterns
- Error rates and types
- Performance benchmarks

## Conclusion

ODAI represents a sophisticated multi-agent AI system capable of handling diverse user needs through specialized, interconnected agents. The architecture prioritizes modularity, scalability, and user experience while maintaining security and performance standards. The system continues to evolve with new agent integrations and enhanced capabilities.

For development questions or agent integration requests, refer to the individual agent files and test suites for implementation details.