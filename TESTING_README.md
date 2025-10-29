# Testing Guide for ODAI API

This guide explains how to run and understand the comprehensive unit tests for the ODAI API, focusing on the service modules including `auth_service.py` and `chat_service.py`.

## Quick Start

### 1. Install Test Dependencies

```bash
# Install all testing dependencies
pip install -r test_requirements.txt

# Or use the test runner to install dependencies automatically
python run_tests.py --install-deps
```

### 2. Run All Tests

```bash
# Using the test runner script (recommended)
python run_tests.py

# Or directly with pytest
pytest tests/
```

### 3. Run Tests for Specific Services

```bash
# Run auth_service tests only
python run_tests.py --file auth_service
pytest tests/test_auth_service.py

# Run chat_service tests only  
python run_tests.py --file chat_service
pytest tests/test_chat_service.py

# Run connection_manager tests only
python run_tests.py --file connection_manager
pytest tests/test_connection_manager.py

# Run websocket_handlers tests only
python run_tests.py --file websocket_handlers
pytest tests/test_websocket_handlers.py

# Run all service tests
pytest tests/test_auth_service.py tests/test_chat_service.py tests/test_connection_manager.py tests/test_websocket_handlers.py

# Run all Firebase model tests
pytest tests/test_firebase_*_model.py

# Run all tests (services + Firebase models)
pytest tests/
```

## Available Tests

The test suite includes comprehensive coverage for multiple service modules:

### 1. Authentication Service Tests (`tests/test_auth_service.py`)

**29 test methods** covering the `AuthService` class:

- **Classes Tested:**
  - `AuthenticationError` - Custom exception class
  - `AuthService` - Main authentication service class

- **Methods Tested:**
  - `__init__()` - Service initialization
  - `validate_user_token()` - Token validation logic
  - `authenticate_websocket()` - WebSocket authentication
  - `authenticate_http_request()` - HTTP request authentication
  - `get_user_integrations()` - User integration settings

- **Coverage:** 84% code coverage of auth_service.py

### 2. Chat Service Tests (`tests/test_chat_service.py`)

**35 test methods** covering the `ChatService` class:

- **Classes Tested:**
  - `ChatService` - Main chat management service class

- **Methods Tested:**
  - `__init__()` - Service initialization
  - `get_or_create_chat()` - Chat creation and retrieval
  - `update_chat_messages()` - Message management
  - `add_chat_responses()` - Response handling
  - `update_chat_token_usage()` - Token usage tracking
  - `record_token_usage()` - User token recording
  - `record_unhandled_request()` - Unhandled request logging
  - `add_email_to_waitlist()` - Waitlist management
  - `track_user_prompt()` - User prompt tracking
  - `track_agent_call()` - Agent call tracking
  - `track_tool_call()` - Tool call tracking
  - `track_user_response()` - Response tracking

- **Coverage:** 97% code coverage of chat_service.py

### 3. Connection Manager Tests (`tests/test_connection_manager.py`)

**38 test methods** covering the `ConnectionManager` class:

- **Classes Tested:**
  - `ConnectionManager` - WebSocket connection management service

- **Methods Tested:**
  - `__init__()` - Service initialization
  - `connect()` - WebSocket connection acceptance
  - `disconnect()` - Connection removal and cleanup
  - `send_personal_message()` - Direct message sending
  - `send_json_message()` - JSON message sending
  - `broadcast()` - Message broadcasting to all connections
  - `broadcast_json()` - JSON broadcasting to all connections
  - `connection_count` property - Active connection counting

- **Coverage:** 100% code coverage of connection_manager.py

### 4. WebSocket Handlers Tests (`tests/test_websocket_handlers.py`)

**35 test methods** covering the `WebSocketHandler` class:

- **Classes Tested:**
  - `WebSocketHandler` - Main WebSocket chat interaction handler

- **Methods Tested:**
  - `__init__()` - Handler initialization with dependencies
  - `handle_websocket_connection()` - Complete WebSocket lifecycle management
  - `_handle_chat_loop()` - Message processing loop
  - `_process_chat_message()` - Individual message processing
  - `_handle_streaming_events()` - Stream event processing from agents
  - `_process_stream_event()` - Individual stream event handling
  - `_handle_run_item_event()` - Run item event processing
  - `_finalize_chat_interaction()` - Chat interaction finalization
  - `_extract_previous_suggested_prompts()` - Prompt extraction
  - `_json_serial()` - JSON serialization utility

- **Coverage:** 96% code coverage of handlers.py

### 5. Firebase Model Tests

**Comprehensive test coverage for all Firebase models:**

#### Available Firebase Model Tests

- **`tests/test_firebase_chat_model.py`** - Chat model tests (create_chat, update_messages, etc.)
- **`tests/test_firebase_user_model.py`** - User model tests (user creation, integrations, etc.)
- **`tests/test_firebase_google_token_model.py`** - GoogleToken model tests (OAuth flow, encryption, etc.)
- **`tests/test_firebase_plaid_token_model.py`** - PlaidToken model tests (banking tokens, encryption, etc.)
- **`tests/test_firebase_token_usage_model.py`** - TokenUsage model tests (usage tracking, cost calculation, etc.)
- **`tests/test_firebase_waitlist_model.py`** - Waitlist model tests (email addition, timestamp creation, etc.)
- **`tests/test_firebase_evernote_token_model.py`** - EvernoteToken model tests (Evernote integration, etc.)
- **`tests/test_firebase_easypost_tracker_model.py`** - EasyPostTracker model tests (shipment tracking, etc.)
- **`tests/test_firebase_integration_model.py`** - Integration model tests (user integrations, etc.)
- **`tests/test_firebase_unhandled_request_model.py`** - UnhandledRequest model tests (error logging, etc.)

#### Running Firebase Model Tests

```bash
# Run all Firebase model tests
python run_tests.py

# Run specific Firebase model tests
python run_tests.py --file firebase_chat_model
python run_tests.py --file firebase_user_model
python run_tests.py --file firebase_google_token_model
python run_tests.py --file firebase_plaid_token_model
python run_tests.py --file firebase_token_usage_model
python run_tests.py --file firebase_waitlist_model
python run_tests.py --file firebase_evernote_token_model
python run_tests.py --file firebase_easypost_tracker_model
python run_tests.py --file firebase_integration_model
python run_tests.py --file firebase_unhandled_request_model

# Run with coverage for Firebase models
python run_tests.py --file firebase_chat_model --coverage --verbose
```

#### Firebase Model Test Features

- **Comprehensive Mocking:** All Firebase dependencies (Firestore, authentication, OpenAI) are mocked
- **Edge Case Testing:** Tests cover empty data, invalid inputs, and error conditions
- **Integration Testing:** End-to-end model workflows with mocked Firebase operations
- **Error Handling:** Firestore exceptions and validation error testing
- **Data Validation:** Proper data structure and type validation
- **Coverage Optimization:** Tests designed to achieve high code coverage

### 6. Connectors Utils Tests

**Comprehensive test coverage for all utility modules:**

#### Available Utils Test Files

- **`tests/test_utils_segment.py`** - Segment analytics tracking tests (user events, integrations, voice calls)
- **`tests/test_utils_google.py`** - Google credentials fetching tests (OAuth integration, token handling)
- **`tests/test_utils_secrets.py`** - Google Secret Manager tests (secret access, version handling, error cases)
- **`tests/test_utils_context.py`** - ChatContext dataclass tests (context management, integration utilities)
- **`tests/test_utils_keys.py`** - Google Cloud KMS tests (encryption, decryption, key management, CRC32C)
- **`tests/test_utils_display_response.py`** - OpenAI response filtering tests (JSON parsing, decision logic)
- **`tests/test_utils_responses.py`** - Response classes tests (ToolResponse, account responses, serialization)
- **`tests/test_utils_cloudflare.py`** - Cloudflare API tests (site rendering, markdown conversion, error handling)

#### Running Utils Tests

```bash
# Run all utils tests
python run_tests.py

# Run specific utils tests
python run_tests.py --file utils_segment
python run_tests.py --file utils_google
python run_tests.py --file utils_secrets
python run_tests.py --file utils_context
python run_tests.py --file utils_keys
python run_tests.py --file utils_display_response
python run_tests.py --file utils_responses
python run_tests.py --file utils_cloudflare

# Run with coverage for utils modules
python run_tests.py --file utils_segment --coverage --verbose
```

#### Utils Test Features

- **External API Mocking:** All external services (OpenAI, Google Cloud, Cloudflare, Segment) are comprehensively mocked
- **Authentication Testing:** OAuth flows, token management, and credential handling covered
- **Cryptographic Operations:** KMS encryption/decryption with integrity verification testing
- **Data Structure Testing:** Response classes, context objects, and serialization thoroughly tested
- **Error Handling:** Network errors, API failures, authentication issues, and edge cases covered
- **Configuration Testing:** Settings management and environment-specific behavior verified
- **Integration Workflows:** End-to-end utility workflows with proper dependency injection

### Overall Test Statistics
- **Total Tests:** 700+ tests (29 auth + 35 chat + 38 connection_manager + 35 websocket_handlers + 250+ Firebase models + 300+ utils tests)
- **Test Files:** 22 comprehensive test files (4 service + 10 Firebase model + 8 utils test files)
- **Tested Modules Coverage:**
  - `services/auth_service.py`: 84% coverage
  - `services/chat_service.py`: 97% coverage
  - `websocket/connection_manager.py`: 100% coverage
  - `websocket/handlers.py`: 96% coverage
  - `firebase/models/*`: High coverage across all Firebase models
  - `connectors/utils/*`: High coverage across all utility modules
- **Overall Coverage:** 90%+ across all tested modules

### Test Categories

#### 1. Unit Tests
- Test individual methods in isolation
- Mock all external dependencies
- Cover both success and failure scenarios

#### 2. Integration Tests
- Test complete authentication flows
- Verify interaction between methods
- End-to-end authentication scenarios

#### 3. Edge Case Tests
- Empty/null token handling  
- Invalid user scenarios
- Production vs development environment differences
- Partial integration data
- Exception handling

#### 4. Error Handling Tests
- Custom exception behavior
- HTTP exception responses
- WebSocket connection closure
- Logging verification

## Running Tests

### Basic Commands

```bash
# Run all tests with minimal output
pytest tests/

# Run all service tests only
pytest tests/test_auth_service.py tests/test_chat_service.py tests/test_connection_manager.py tests/test_websocket_handlers.py

# Run all Firebase model tests only
pytest tests/test_firebase_*_model.py

# Run with verbose output
pytest tests/ -v

# Run with coverage report for all modules
pytest tests/ --cov=services --cov=websocket --cov=firebase.models --cov-report=html

# Run with coverage report for services only
pytest tests/test_auth_service.py tests/test_chat_service.py tests/test_connection_manager.py tests/test_websocket_handlers.py --cov=services --cov=websocket --cov-report=html

# Run with coverage report for Firebase models only
pytest tests/test_firebase_*_model.py --cov=firebase.models --cov-report=html

# Run specific test class
pytest tests/test_auth_service.py::TestAuthService
pytest tests/test_chat_service.py::TestChatServiceInit
pytest tests/test_connection_manager.py::TestConnectionManagerConnect
pytest tests/test_websocket_handlers.py::TestWebSocketHandlerInit

# Run specific test method
pytest tests/test_auth_service.py::TestValidateUserToken::test_validate_user_token_success
pytest tests/test_chat_service.py::TestGetOrCreateChat::test_create_new_chat
pytest tests/test_connection_manager.py::TestBroadcast::test_broadcast_to_multiple_connections
pytest tests/test_websocket_handlers.py::TestProcessStreamEvent::test_process_text_delta_event
```

### Using the Test Runner Script

The `run_tests.py` script provides convenient options:

```bash
# Install dependencies and run auth_service tests with coverage
python run_tests.py --install-deps --file auth_service --coverage --verbose

# Run all tests quietly
python run_tests.py

# Run with coverage report
python run_tests.py --coverage

# Verbose output
python run_tests.py --verbose
```

### Test Runner Options

| Option | Short | Description |
|--------|-------|-------------|
| `--file auth_service` | `-f auth_service` | Run only auth_service tests |
| `--coverage` | `-c` | Generate coverage report |
| `--verbose` | `-v` | Detailed test output |
| `--install-deps` | | Install test dependencies first |

## Test Structure

### Test Organization

```
tests/
├── __init__.py
└── test_auth_service.py
    ├── TestAuthenticationError      # Custom exception tests
    ├── TestAuthService             # Base fixtures and setup
    ├── TestAuthServiceInit         # Initialization tests
    ├── TestValidateUserToken       # Token validation tests
    ├── TestAuthenticateWebSocket   # WebSocket auth tests
    ├── TestAuthenticateHttpRequest # HTTP auth tests
    ├── TestGetUserIntegrations     # User integration tests
    ├── TestAuthServiceIntegration  # Integration tests
    └── TestAuthServiceEdgeCases    # Edge cases and logging
```

### Test Fixtures

Key fixtures used across tests:

- `mock_validate_google_token` - Mocks the Google token validation function
- `auth_service_production` - AuthService instance for production environment
- `auth_service_development` - AuthService instance for development environment  
- `mock_user` - Mock user object with integrations
- `mock_user_no_integrations` - Mock user without integrations
- `mock_websocket` - Mock WebSocket connection

### Mocking Strategy

Tests use comprehensive mocking to isolate the `AuthService` class:

- **External dependencies**: Google token validation mocked
- **WebSocket connections**: Mocked with AsyncMock for async methods
- **User objects**: Mock objects with configurable attributes
- **Logging**: Patched to verify log messages
- **Import system**: Mocked to avoid import dependencies

## Understanding Test Results

### Success Output

```
tests/test_auth_service.py::TestAuthServiceInit::test_init_production_mode PASSED
tests/test_auth_service.py::TestValidateUserToken::test_validate_user_token_success PASSED
...
================================== 25 passed in 0.12s ==================================
```

### Failure Output

```
tests/test_auth_service.py::TestValidateUserToken::test_validate_user_token_no_token FAILED

FAILURES
================================== FAILURES ===================================
_____________ TestValidateUserToken.test_validate_user_token_no_token _____________

    def test_validate_user_token_no_token(self, auth_service_development):
        """Test validation with no token provided."""
        with pytest.raises(AuthenticationError, match="No token provided"):
>           auth_service_development.validate_user_token(None)
E       AssertionError: AuthenticationError not raised

tests/test_auth_service.py:123: AssertionError
```

### Coverage Reports

When running with `--coverage`, you'll get:

```
Name                          Stmts   Miss  Cover
-------------------------------------------------
services/auth_service.py        45      0   100%
-------------------------------------------------
TOTAL                           45      0   100%

HTML coverage report: htmlcov/index.html
```

## Test Configuration

### pytest.ini

The project includes a `pytest.ini` configuration file with:

- Async test support via `pytest-asyncio`
- Verbose output formatting
- Warning filters
- Test discovery patterns

### Dependencies

Core testing dependencies in `test_requirements.txt`:

- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `pytest-mock` - Enhanced mocking
- `pytest-cov` - Coverage reporting
- `httpx` - HTTP client for FastAPI testing
- `fastapi[all]` - FastAPI testing utilities

## Best Practices

### Writing Tests

1. **Use descriptive test names** that explain what is being tested
2. **Follow AAA pattern** - Arrange, Act, Assert
3. **Mock external dependencies** to isolate units under test
4. **Test both success and failure paths**
5. **Use fixtures** to reduce code duplication
6. **Test edge cases** and boundary conditions

### Running Tests

1. **Run tests frequently** during development
2. **Use coverage reports** to identify untested code
3. **Run specific tests** when working on particular features
4. **Check both unit and integration tests**
5. **Verify tests pass** before committing code

### Debugging Tests

1. **Use `-v` flag** for detailed output
2. **Use `-s` flag** to see print statements
3. **Run individual tests** to isolate issues
4. **Check mock assertions** when tests fail unexpectedly
5. **Verify fixture setup** if initialization fails

## Continuous Integration

To integrate these tests into CI/CD:

```yaml
# Example GitHub Actions workflow
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - run: pip install -r test_requirements.txt
    - run: pytest tests/ --cov --cov-report=xml
    - uses: codecov/codecov-action@v3
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `PYTHONPATH` includes the project root
2. **Missing Dependencies**: Run `pip install -r test_requirements.txt`
3. **Async Test Failures**: Verify `pytest-asyncio` is installed
4. **Mock Assertion Errors**: Check that mocks are configured correctly

### Getting Help

- Check test output for specific error messages
- Verify all dependencies are installed
- Ensure you're running tests from the project root directory
- Review the test file for expected behavior

This comprehensive test suite ensures the `auth_service.py` module is robust, reliable, and maintainable. 