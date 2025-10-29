# ODAI Backend

ODAI is an AI-powered personal assistant platform built with FastAPI that provides real-time chat and voice interactions through extensive third-party integrations. The platform leverages OpenAI's GPT models and an agent-based architecture to deliver a comprehensive AI assistant experience.

Written with pride solo by George Sibble in about 60 days.

## Table of Contents

- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Code Organization](#code-organization)
- [Key Features](#key-features)
- [Security](#security)
- [Prerequisites](#prerequisites)
- [Local Development Setup](#local-development-setup)
- [Running Tests](#running-tests)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

## Project Overview

ODAI is a production-grade AI assistant platform that pushes the boundaries of what's possible with modern AI technology. Built from the ground up in just 60 days, it demonstrates sophisticated software engineering across multiple cutting-edge domains.

### Technical Highlights

**Advanced Agent Architecture**
- Implements OpenAI's latest agent framework with intelligent tool orchestration across 30+ third-party services
- Multi-agent system with specialized orchestrators for different interaction modes (chat, voice)
- Context-aware tool selection that dynamically routes requests to the appropriate service connector
- Automatic conversation title generation and semantic understanding

**Real-Time Streaming Infrastructure**
- Custom WebSocket implementation enabling character-by-character AI response streaming
- Live tool call visualization showing users exactly what the AI is doing in real-time
- Sophisticated connection lifecycle management with automatic reconnection and state preservation
- Bidirectional communication supporting both text and voice data streams

**Next-Generation Voice Interface**
- Full-duplex voice conversations using Twilio WebRTC integration
- Real-time audio processing and streaming to OpenAI's speech models
- Seamless transition between text and voice modalities within the same conversation
- Production-ready voice call handling with sophisticated error recovery

**Enterprise-Grade Security**
- Google Cloud KMS-based encryption for all sensitive tokens and credentials
- User-specific encryption keys ensuring data isolation
- OAuth 2.0 flows for 15+ services with secure state management
- Production-enforced authentication middleware with Firebase integration

**Comprehensive Integration Ecosystem**
The platform seamlessly connects with 30+ services across multiple domains:
- **Financial Services**: Plaid (banking), Finnhub (stocks), CoinMarketCap (crypto), Alpaca (trading)
- **Travel & Transportation**: Amadeus (flights), FlightAware, Amtrak, TripAdvisor
- **Productivity**: Gmail, Google Calendar/Docs, Slack, Evernote, Twilio
- **Shopping & Commerce**: Amazon, Google Shopping, Yelp, Ticketmaster
- **Information**: Google Search/News, Weather API, Web scraping

**Production-Ready Engineering**
- 700+ tests achieving 90%+ code coverage across the entire codebase
- Parallel test execution with advanced test runner supporting multiple configurations
- Google App Engine deployment with auto-scaling (2-20 instances)
- Comprehensive error handling, logging, and monitoring
- Clean layered architecture separating concerns across API, Service, Integration, and Data layers

## Architecture

The application follows a clean, layered architecture:

```
┌─────────────────────────────────────────┐
│      Client Applications                 │
│  (Web, Mobile, Voice Calls)             │
└─────────────────┬───────────────────────┘
                  │ WebSocket/HTTP
┌─────────────────▼───────────────────────┐
│         API Layer                        │
│  (FastAPI, Routers, WebSocket)          │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│       Service Layer                      │
│  (AuthService, ChatService,             │
│   LocationService)                       │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│     Integration Layer                    │
│  (Orchestrator + 30+ Connectors)        │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│        Data Layer                        │
│   (Firebase/Firestore Models)            │
└─────────────────────────────────────────┘
```

## Project Structure

```
backend/
├── api.py                  # Main FastAPI application entry point
├── requirements.txt        # Production dependencies
├── test_requirements.txt   # Testing dependencies
├── app.yaml               # Development deployment config
├── prod.yaml              # Production deployment config
├── run_tests.py           # Custom test runner
├── CLAUDE.md              # AI assistant guidance
│
├── routers/               # API route handlers
│   ├── google.py         # Google OAuth endpoints
│   ├── plaid.py          # Financial account linking
│   ├── twilio/           # Voice call handling
│   └── app_voice.py      # In-app voice interactions
│
├── services/              # Business logic layer
│   ├── auth_service.py   # Authentication and authorization
│   ├── chat_service.py   # Chat management and AI integration
│   └── location_service.py # Geolocation services
│
├── websocket/             # WebSocket implementation
│   ├── connection_manager.py  # Connection lifecycle
│   └── websocket_handler.py   # Chat interaction flow
│
├── firebase/              # Data models and persistence
│   ├── models/           # Firestore document models
│   │   ├── user.py      # User profiles and settings
│   │   ├── chat.py      # Chat conversations
│   │   ├── tokens.py    # OAuth token storage
│   │   └── ...
│   └── firebase_init.py  # Firebase initialization
│
├── connectors/            # Third-party integrations
│   ├── orchestrator.py   # Main AI agent orchestrator
│   ├── voice_orchestrator.py  # Voice-specific orchestrator
│   ├── plaid_agent.py    # Financial services
│   ├── gmail_agent.py    # Email integration
│   └── ...               # 30+ other integrations
│
└── tests/                 # Test suite
    ├── test_*.py         # Test files mirror source structure
    └── conftest.py       # pytest configuration
```

## Code Organization

### Design Patterns

1. **Layered Architecture**: Clear separation between API, Service, Integration, and Data layers
2. **Dependency Injection**: Services receive dependencies via constructors
3. **Repository Pattern**: Firebase models abstract database operations
4. **Agent-Based Architecture**: Specialized agents for different domains
5. **Async/Await**: Consistent async patterns throughout

### Key Conventions

- **File Naming**: Snake_case for Python files (e.g., `auth_service.py`)
- **Class Naming**: PascalCase for classes (e.g., `AuthService`)
- **Function Naming**: Snake_case for functions (e.g., `validate_token()`)
- **Test Files**: Prefix with `test_` (e.g., `test_auth_service.py`)
- **Environment Variables**: UPPER_SNAKE_CASE (e.g., `OPENAI_API_KEY`)

### Adding New Features

1. **New API Endpoint**:
   - Add router in `routers/` directory
   - Register in `api.py` using `app.include_router()`

2. **New Service**:
   - Create service class in `services/`
   - Initialize in `ODAPIApplication.__init__()`
   - Add tests in `tests/test_<service_name>.py`

3. **New Integration**:
   - Create agent in `connectors/`
   - Register in `orchestrator.py`
   - Add required API keys to Secret Manager

4. **New Data Model**:
   - Create model in `firebase/models/`
   - Inherit from `FireStoreObject`
   - Implement required methods

## Key Features

### Authentication
- Firebase ID token validation
- Google OAuth 2.0 integration
- User-specific encryption keys via Google Cloud KMS
- Production-enforced security rules

### Real-time Communication
- WebSocket support for streaming chat
- Character-by-character response streaming
- Tool call visualization
- Voice interaction via Twilio WebRTC

### AI Integration
- OpenAI gpt-4o with agents framework
- Context-aware tool selection
- Multi-agent orchestration
- Automatic chat title generation

### Data Security
- All sensitive tokens encrypted at rest
- User-specific encryption keys
- Secure OAuth state management
- Comprehensive audit logging

## Security

### Best Practices
- Never commit secrets or API keys
- Use Google Secret Manager for production secrets
- Enable 2FA on all service accounts
- Regular security audits
- Encrypted storage for all sensitive data

### Authentication Flow
1. Client obtains Firebase ID token
2. Token validated on each request
3. User object loaded with permissions
4. Request processed with user context

## Prerequisites

- Python 3.11+
- Google Cloud SDK (for deployment)
- Firebase project setup
- Access to required API keys (stored in Google Secret Manager or `.env` for local development)

## Local Development Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd odai/backend
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r test_requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the backend directory with the following variables:

```bash
# Set local development flag
LOCAL=true

# Firebase credentials
FIREBASE_SERVICE_ACCOUNT_KEY='{...}'  # JSON service account key

# API Keys (get these from your respective services)
OPENAI_API_KEY=your_openai_key
PLAID_CLIENT_ID=your_plaid_client_id
PLAID_SECRET=your_plaid_secret
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
# ... add other required API keys

# Google OAuth (for local development)
GOOGLE_OAUTH_CLIENT_ID=your_client_id
GOOGLE_OAUTH_CLIENT_SECRET=your_client_secret
```

### 4. Run the Application

```bash
# Start the FastAPI server with hot reload
uvicorn api:APP --reload --host 0.0.0.0 --port 8080

# Or use the run script if available
python run_local.py
```

The API will be available at `http://localhost:8080`

## Running Tests

### Test Runner Script

The project includes a custom test runner with various options:

```bash
# Run all tests
python run_tests.py

# Run tests with coverage report
python run_tests.py --coverage

# Run specific test file (e.g., auth_service)
python run_tests.py --file auth_service

# Run tests with verbose output
python run_tests.py --verbose

# Run only fast tests (skip slow integration tests)
python run_tests.py --fast

# Run tests and open coverage report in browser
python run_tests.py --coverage --open
```

### Direct pytest Commands

You can also use pytest directly:

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_auth_service.py

# Run with coverage
pytest tests/ --cov=services --cov-report=html

# Run specific test function
pytest tests/test_chat_service.py::test_create_chat

# Run tests in parallel
pytest tests/ -n auto
```

### Test Categories

Tests are organized into categories:
- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **Slow Tests**: Tests that interact with external services (marked with `@pytest.mark.slow`)

## Deployment

### Development Environment

Deploy to the development environment using Google App Engine:

```bash
# Ensure you're authenticated with gcloud
gcloud auth login
gcloud config set project odai-dev-5e4fd

# Deploy using development configuration
gcloud app deploy app.yaml --version=your-version-name

# Or use the deployment script
./deploy_development.sh
```

### Production Environment

Deploy to production with extra caution:

```bash
# Switch to production project
gcloud config set project odai-prod

# Deploy using production configuration
gcloud app deploy prod.yaml --version=your-version-name

# Or use the deployment script
./deploy_production.sh
```

### Configuration Differences

**Development (`app.yaml`)**:
- Manual scaling with 1 instance
- Relaxed authentication rules
- Debug logging enabled
- Lower resource allocation

**Production (`prod.yaml`)**:
- Auto-scaling (2-20 instances)
- Strict authentication requirements
- Production logging levels
- Higher resource allocation
- Additional security measures

## Contributing

### Development Workflow
1. Create feature branch from `dev`
2. Implement feature with tests
3. Ensure all tests pass: `python run_tests.py`
4. Run linting and type checking if available
5. Create pull request to `dev`
6. After review, merge to `dev`
7. Deploy to development environment
8. After testing, merge to `main` for production

### Code Quality
- Write comprehensive tests (aim for >90% coverage)
- Follow existing code patterns
- Document complex logic
- Use type hints where appropriate
- Handle errors gracefully

### Testing Requirements
- All new features must include tests
- Tests should cover both success and error cases
- Mock external dependencies
- Use fixtures for common test data

For more detailed information about working with this codebase, see `CLAUDE.md` for AI assistant guidance.

## License

Copyright (c) 2025 ODAI, Inc. and George Sibble

Written by George Sibble.

This project is licensed under the MIT License - you are free to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the software, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.