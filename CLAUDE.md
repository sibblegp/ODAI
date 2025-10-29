# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Testing
```bash
# Run all tests with advanced test runner
python run_tests.py                               # Run all tests with parallel execution
python run_tests.py --coverage                    # Run tests with coverage report
python run_tests.py --file auth_service           # Run specific test file
python run_tests.py --verbose                     # Run tests with verbose output
python run_tests.py --workers 8                   # Run tests with 8 parallel workers

# Direct pytest commands
pytest tests/                                     # Run all tests
pytest tests/test_auth_service.py                 # Run specific test file
pytest tests/ --cov=services --cov-report=html    # Generate HTML coverage report
pytest tests/ -xvs                                # Stop on first failure with verbose output
```

### Development
```bash
# Install dependencies
pip install -r requirements.txt                   # 173 production dependencies
pip install -r test_requirements.txt              # Testing dependencies

# Run locally (set LOCAL=true in environment)
uvicorn api:APP --reload                          # Run with auto-reload
uvicorn api:APP --host 0.0.0.0 --port 8080       # Run on specific host/port

# Deploy to environments
./deploy_development.sh                           # Deploy to dev (odai-dev-5e4fd)
./deploy_production.sh                            # Deploy to prod (odai-prod)
```

## Project Overview

ODAI is a sophisticated AI assistant platform built with FastAPI, featuring:
- **30+ Third-Party Integrations**: Financial, travel, communication, entertainment services
- **Real-time WebSocket Support**: Streaming chat responses with connection lifecycle management
- **Voice Interface**: Twilio integration for voice-based AI interactions
- **Enterprise Security**: Google Cloud KMS encryption, OAuth 2.0 authentication
- **Comprehensive Testing**: 700+ tests with 90%+ coverage across 67 test files
- **Cloud-Native Architecture**: Google App Engine with auto-scaling (2-20 instances in production)

## Code Architecture

### High-Level Structure
```
api.py (FastAPI main)
├── routers/              # API endpoints & route handlers
│   ├── app_voice.py      # Voice interaction endpoints
│   ├── google.py         # Google services integration
│   ├── twilio_handler.py # SMS/voice handling
│   └── voice_utils/      # Audio processing utilities
├── services/             # Business logic layer
│   ├── auth_service.py   # Authentication & OAuth
│   ├── chat_service.py   # OpenAI chat management
│   └── api_service.py    # Non-chat API endpoints
├── connectors/           # 30+ third-party integrations
│   ├── orchestrator.py   # Agent tool orchestration
│   └── [integration].py  # Individual service connectors
├── firebase/models/      # Data models & encryption
│   ├── user.py           # User profiles
│   ├── chat.py           # Chat sessions
│   └── [model]_token.py  # Encrypted token storage
├── websocket/            # Real-time communication
│   └── handlers/         # WebSocket connection handlers
├── middleware/           # Application middleware
└── tests/                # 67 test files, 700+ tests
```

### Core Components

#### 1. **API Layer** (`api.py`, `routers/`)
- FastAPI application with CORS middleware and authentication
- RESTful endpoints + WebSocket support for real-time chat
- Routers:
  - `app_voice.py`: Voice-based AI interactions
  - `google.py`: Google OAuth and services (Calendar, Docs, Gmail)
  - `plaid.py`: Banking integration
  - `evernote.py`: Note-taking integration
  - `twilio_handler.py`: SMS/voice communication

#### 2. **Service Layer** (`services/`)
- `auth_service.py`: Google OAuth, JWT tokens, user management (84% coverage)
- `chat_service.py`: OpenAI integration, message processing, agent tools (97% coverage)
- `api_service.py`: Non-chat API endpoint orchestration
- `location_service.py`: IP-based geolocation services

#### 3. **WebSocket Layer** (`websocket/`)
- Real-time bidirectional communication for streaming chat
- Connection lifecycle management with authentication
- Message queuing and error handling
- Support for both text and voice interactions

#### 4. **Data Layer** (`firebase/models/`)
- **User Management**: `user.py` - profiles, preferences, integration settings
- **Chat Storage**: `chat.py` - sessions, messages, conversation history
- **Token Management**: Encrypted storage using Google Cloud KMS
  - `google_token.py`: Google OAuth tokens
  - `plaid_token.py`: Banking credentials
  - `evernote_token.py`: Note service tokens
- **Analytics**: `token_usage.py` - OpenAI API usage and cost tracking
- **Error Tracking**: `unhandled_request.py` - Failed request logging

#### 5. **Integration Layer** (`connectors/`)

##### Financial & Banking
- `plaid_agent.py`: Bank account access and transactions
- `finnhub_agent.py`: Stock market data and financial news
- `coinmarketcap.py`: Cryptocurrency prices and market data
- `exchange_rate.py`: Currency conversion rates

##### Travel & Transportation
- `amadeus_agent.py`: Flight booking and travel planning
- `flightaware.py`: Real-time flight tracking
- `amtrak.py`: Train schedules and bookings
- `caltrain.py`: California commuter rail status

##### Communication & Productivity
- `gmail.py`: Email management and sending
- `google_calendar.py`: Calendar events and scheduling
- `google_docs.py`: Document creation and editing
- `slack.py`: Team messaging integration
- `twilio_assistant.py`: SMS and voice communication

##### E-commerce & Shopping
- `amazon.py`: Product search and shopping
- `google_shopping.py`: Price comparison and product search
- `yelp.py`: Restaurant and business reviews

##### Entertainment & Media
- `spotify.py`: Music streaming and playlist management
- `movieglu.py`: Movie showtimes and theater information
- `ticketmaster.py`: Event tickets and entertainment
- `tripadvisor.py`: Travel reviews and recommendations

##### Weather & Location
- `accuweather.py`: Weather forecasts and conditions
- `weatherapi.py`: Alternative weather data source

##### Core Infrastructure
- `orchestrator.py`: Agent tool management and routing
- `voice_orchestrator.py`: Voice-specific agent handling
- `google_connections.py`: Google API connection pooling

### Key Design Patterns

- **Agent Tool Architecture**: Function-based tools for AI capabilities with OpenAI agents
- **Repository Pattern**: Firebase models abstract database operations
- **Dependency Injection**: Services receive dependencies via constructors
- **Middleware Pipeline**: Authentication, CORS, error handling in layers
- **Async/Await**: Consistent async patterns for WebSocket and external APIs
- **Encryption at Rest**: Google Cloud KMS for sensitive data protection
- **Connection Pooling**: Efficient management of external API connections

### Testing Strategy

- **Test Suite Statistics**:
  - 67 test files covering all modules
  - 700+ individual test cases
  - 90%+ code coverage across tested modules
  - Parallel test execution with 8 workers in CI/CD

- **Test Categories**:
  - **Unit Tests**: Isolated component testing with mocked dependencies
  - **Integration Tests**: End-to-end workflow validation
  - **WebSocket Tests**: Real-time connection and streaming tests
  - **Authentication Tests**: OAuth flow and token validation
  - **Connector Tests**: Each third-party integration thoroughly tested

- **Testing Tools & Configuration**:
  - `run_tests.py`: Advanced test runner with coverage reporting
  - `pytest.ini`: Async support, timeout settings, warning filters
  - Comprehensive mocking of external services (OpenAI, Google Cloud, Firebase)
  - Edge case coverage including empty data, invalid inputs, error conditions

### Environment Configuration

- **Local Development**:
  - Set `LOCAL=true` environment variable
  - Use `.env` file for API keys and secrets
  - Python 3.13 recommended
  - 4GB RAM minimum for development

- **Cloud Deployment**:
  - Google App Engine with auto-scaling
  - Development: 1 instance, 4GB RAM (`odai-dev-5e4fd`)
  - Production: 2-20 instances, 4GB RAM (`odai-prod`)
  - Google Secret Manager for API key storage
  - Cloud KMS for encryption keys

- **Configuration Files**:
  - `app.yaml`: Development environment settings
  - `prod.yaml`: Production environment settings
  - `pytest.ini`: Test configuration
  - `requirements.txt`: 173 production dependencies
  - `test_requirements.txt`: Testing dependencies

### Recent Architectural Improvements

- **Modular Service Refactoring**: Migrated from monolithic 614-line file to modular service architecture
- **Centralized Import Management**: `utils/imports.py` for clean dependency handling
- **Enhanced WebSocket Support**: Improved streaming with connection lifecycle management
- **Voice Interface Addition**: Twilio integration for voice-based AI interactions
- **Advanced Testing Infrastructure**: Parallel test execution with comprehensive coverage reporting
- **Security Enhancements**: Cloud KMS encryption for all sensitive tokens

### Additional Documentation

- `TESTING_README.md`: Comprehensive testing guide (504 lines)
- `REFACTORING_SUMMARY.md`: Details of modular architecture migration
- `LAUNCH_PLAN.md`: Product launch and go-to-market strategy
- `README.md`: Main project documentation