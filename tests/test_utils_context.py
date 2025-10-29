"""
Comprehensive tests for connectors/utils/context.py

Tests cover ChatContext dataclass functionality, integration checking utilities,
and proper handling of user context and settings.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass, fields


# Module-level fixtures that can be shared across test classes
@pytest.fixture
def mock_user():
    """Create a mock User object."""
    mock_user = Mock()
    mock_user.reference_id = "test_user_123"
    mock_user.email = "test@example.com"
    mock_user.name = "Test User"
    return mock_user


@pytest.fixture
def mock_settings():
    """Create a mock Settings object."""
    mock_settings = Mock()
    mock_settings.production = False
    mock_settings.project_id = "test-project"
    mock_settings.openai_api_key = "test_openai_key"
    return mock_settings


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    return Mock()


@pytest.fixture
def sample_chat_context(mock_user, mock_settings, mock_openai_client):
    """Create a sample ChatContext instance."""
    from connectors.utils.context import ChatContext

    return ChatContext(
        user_id="user_123",
        logged_in=True,
        chat_id="chat_456",
        prompt="Test prompt",
        production=False,
        project_id="test-project",
        user=mock_user,
        settings=mock_settings,
        openai_client=mock_openai_client,
        is_google_enabled=True,
        is_plaid_enabled=False
    )


class TestChatContext:
    """Test cases for ChatContext dataclass."""

    def test_chat_context_creation(self, sample_chat_context, mock_user, mock_settings, mock_openai_client):
        """Test ChatContext creation with all fields."""
        assert sample_chat_context.user_id == "user_123"
        assert sample_chat_context.logged_in == True
        assert sample_chat_context.chat_id == "chat_456"
        assert sample_chat_context.prompt == "Test prompt"
        assert sample_chat_context.production == False
        assert sample_chat_context.project_id == "test-project"
        assert sample_chat_context.user == mock_user
        assert sample_chat_context.settings == mock_settings
        assert sample_chat_context.openai_client == mock_openai_client
        assert sample_chat_context.is_google_enabled == True
        assert sample_chat_context.is_plaid_enabled == False

    def test_chat_context_minimal_creation(self, mock_user, mock_settings, mock_openai_client):
        """Test ChatContext creation with minimal required fields."""
        from connectors.utils.context import ChatContext

        # Create with just required fields (defaults for optional)
        context = ChatContext(
            user_id="user_minimal",
            logged_in=False,
            chat_id="chat_minimal",
            prompt="Minimal prompt",
            production=True,
            project_id="minimal-project",
            user=mock_user,
            settings=mock_settings,
            openai_client=mock_openai_client
        )

        # Check required fields
        assert context.user_id == "user_minimal"
        assert context.logged_in == False
        assert context.chat_id == "chat_minimal"
        assert context.prompt == "Minimal prompt"
        assert context.production == True
        assert context.project_id == "minimal-project"
        assert context.user == mock_user
        assert context.settings == mock_settings
        assert context.openai_client == mock_openai_client

        # Check default values for optional fields
        assert context.is_google_enabled == False
        assert context.is_plaid_enabled == False

    def test_chat_context_is_dataclass(self):
        """Test that ChatContext is properly defined as a dataclass."""
        from connectors.utils.context import ChatContext

        # Verify it's a dataclass
        assert hasattr(ChatContext, '__dataclass_fields__')

        # Check expected fields exist
        field_names = [field.name for field in fields(ChatContext)]
        expected_fields = [
            'user_id', 'logged_in', 'chat_id', 'prompt', 'production',
            'project_id', 'user', 'settings', 'openai_client',
            'is_google_enabled', 'is_plaid_enabled'
        ]

        for expected_field in expected_fields:
            assert expected_field in field_names

    def test_chat_context_field_types(self):
        """Test that ChatContext fields have proper type annotations."""
        from connectors.utils.context import ChatContext

        field_dict = {field.name: field.type for field in fields(ChatContext)}

        # Check basic types
        assert field_dict['user_id'] == str
        assert field_dict['logged_in'] == bool
        assert field_dict['chat_id'] == str
        assert field_dict['prompt'] == str
        assert field_dict['production'] == bool
        assert field_dict['project_id'] == str
        assert field_dict['is_google_enabled'] == bool
        assert field_dict['is_plaid_enabled'] == bool

    def test_chat_context_default_values(self):
        """Test ChatContext default values."""
        from connectors.utils.context import ChatContext

        field_dict = {
            field.name: field.default for field in fields(ChatContext)}

        # Check default values
        assert field_dict['is_google_enabled'] == False
        assert field_dict['is_plaid_enabled'] == False

    def test_chat_context_equality(self, mock_user, mock_settings, mock_openai_client):
        """Test ChatContext equality comparison."""
        from connectors.utils.context import ChatContext

        context1 = ChatContext(
            user_id="user_123",
            logged_in=True,
            chat_id="chat_456",
            prompt="Test prompt",
            production=False,
            project_id="test-project",
            user=mock_user,
            settings=mock_settings,
            openai_client=mock_openai_client
        )

        context2 = ChatContext(
            user_id="user_123",
            logged_in=True,
            chat_id="chat_456",
            prompt="Test prompt",
            production=False,
            project_id="test-project",
            user=mock_user,
            settings=mock_settings,
            openai_client=mock_openai_client
        )

        # Should be equal with same data
        assert context1 == context2

    def test_chat_context_string_representation(self, sample_chat_context):
        """Test ChatContext string representation."""
        str_repr = str(sample_chat_context)

        # Should contain key information
        assert "ChatContext" in str_repr
        assert "user_123" in str_repr
        assert "chat_456" in str_repr

    def test_chat_context_field_access(self, sample_chat_context):
        """Test that all fields are accessible."""
        # All fields should be accessible without errors
        assert hasattr(sample_chat_context, 'user_id')
        assert hasattr(sample_chat_context, 'logged_in')
        assert hasattr(sample_chat_context, 'chat_id')
        assert hasattr(sample_chat_context, 'prompt')
        assert hasattr(sample_chat_context, 'production')
        assert hasattr(sample_chat_context, 'project_id')
        assert hasattr(sample_chat_context, 'user')
        assert hasattr(sample_chat_context, 'settings')
        assert hasattr(sample_chat_context, 'openai_client')
        assert hasattr(sample_chat_context, 'is_google_enabled')
        assert hasattr(sample_chat_context, 'is_plaid_enabled')

    def test_chat_context_field_modification(self, sample_chat_context):
        """Test that fields can be modified (dataclass is mutable by default)."""
        # Modify fields
        sample_chat_context.user_id = "modified_user"
        sample_chat_context.is_google_enabled = False
        sample_chat_context.prompt = "Modified prompt"

        # Verify modifications
        assert sample_chat_context.user_id == "modified_user"
        assert sample_chat_context.is_google_enabled == False
        assert sample_chat_context.prompt == "Modified prompt"


class TestContextUtilityFunctions:
    """Test cases for context utility functions."""

    @pytest.fixture
    def mock_context_with_agent(self):
        """Create a mock context object with integration states."""
        mock_ctx = Mock()
        mock_context = Mock()
        mock_context.is_google_enabled = True
        mock_context.is_plaid_enabled = False
        mock_ctx.context = mock_context
        return mock_ctx

    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent object."""
        return Mock()

    def test_is_google_enabled_true(self, mock_context_with_agent, mock_agent):
        """Test is_google_enabled when Google is enabled."""
        from connectors.utils.context import is_google_enabled

        # Set Google as enabled
        mock_context_with_agent.context.is_google_enabled = True

        result = is_google_enabled(mock_context_with_agent, mock_agent)

        assert result == True

    def test_is_google_enabled_false(self, mock_context_with_agent, mock_agent):
        """Test is_google_enabled when Google is disabled."""
        from connectors.utils.context import is_google_enabled

        # Set Google as disabled
        mock_context_with_agent.context.is_google_enabled = False

        result = is_google_enabled(mock_context_with_agent, mock_agent)

        assert result == False

    def test_is_plaid_enabled_true(self, mock_context_with_agent, mock_agent):
        """Test is_plaid_enabled when Plaid is enabled."""
        from connectors.utils.context import is_plaid_enabled

        # Set Plaid as enabled
        mock_context_with_agent.context.is_plaid_enabled = True

        result = is_plaid_enabled(mock_context_with_agent, mock_agent)

        assert result == True

    def test_is_plaid_enabled_false(self, mock_context_with_agent, mock_agent):
        """Test is_plaid_enabled when Plaid is disabled."""
        from connectors.utils.context import is_plaid_enabled

        # Set Plaid as disabled
        mock_context_with_agent.context.is_plaid_enabled = False

        result = is_plaid_enabled(mock_context_with_agent, mock_agent)

        assert result == False

    def test_utility_functions_signature(self):
        """Test that utility functions have expected signatures."""
        from connectors.utils.context import is_google_enabled, is_plaid_enabled
        import inspect

        # Check is_google_enabled signature
        google_sig = inspect.signature(is_google_enabled)
        google_params = list(google_sig.parameters.keys())
        assert len(google_params) == 2
        assert google_params[0] == "ctx"
        assert google_params[1] == "agent"

        # Check is_plaid_enabled signature
        plaid_sig = inspect.signature(is_plaid_enabled)
        plaid_params = list(plaid_sig.parameters.keys())
        assert len(plaid_params) == 2
        assert plaid_params[0] == "ctx"
        assert plaid_params[1] == "agent"

    def test_utility_functions_with_none_context(self, mock_agent):
        """Test utility functions with None context."""
        from connectors.utils.context import is_google_enabled, is_plaid_enabled

        # Should handle None context gracefully or raise appropriate error
        with pytest.raises(AttributeError):
            is_google_enabled(None, mock_agent)

        with pytest.raises(AttributeError):
            is_plaid_enabled(None, mock_agent)

    def test_utility_functions_with_missing_context_attribute(self, mock_agent):
        """Test utility functions with context missing the 'context' attribute."""
        from connectors.utils.context import is_google_enabled, is_plaid_enabled

        mock_ctx_no_context = Mock()
        del mock_ctx_no_context.context  # Remove the context attribute

        with pytest.raises(AttributeError):
            is_google_enabled(mock_ctx_no_context, mock_agent)

        with pytest.raises(AttributeError):
            is_plaid_enabled(mock_ctx_no_context, mock_agent)

    def test_utility_functions_with_none_agent(self, mock_context_with_agent):
        """Test utility functions with None agent."""
        from connectors.utils.context import is_google_enabled, is_plaid_enabled

        # Functions should work regardless of agent value (agent param not used in implementation)
        result_google = is_google_enabled(mock_context_with_agent, None)
        result_plaid = is_plaid_enabled(mock_context_with_agent, None)

        # Should return the context values regardless of agent
        assert result_google == mock_context_with_agent.context.is_google_enabled
        assert result_plaid == mock_context_with_agent.context.is_plaid_enabled


# Integration and import tests
class TestContextIntegration:
    """Integration tests for context.py module."""

    def test_imports_structure(self):
        """Test that all required imports are accessible."""
        # Test dataclass import
        from connectors.utils.context import ChatContext

        # Test utility functions
        from connectors.utils.context import is_google_enabled, is_plaid_enabled

        # Verify types
        assert ChatContext is not None
        assert callable(is_google_enabled)
        assert callable(is_plaid_enabled)

    def test_dataclass_import(self):
        """Test dataclass decorator import."""
        from connectors.utils.context import dataclass
        assert dataclass is not None

    def test_optional_typing_import(self):
        """Test Optional typing import."""
        from connectors.utils.context import Optional
        assert Optional is not None

    def test_dependencies_import_with_mocking(self):
        """Test that dependencies can be imported with proper mocking."""
        # Mock the dependencies that might not be available in test environment
        with patch('firebase.User') as mock_user_class, \
                patch('config.Settings') as mock_settings_class, \
                patch('connectors.utils.context.OpenAI') as mock_openai_class:

            # Re-import the module to test import behavior
            import importlib
            import connectors.utils.context
            importlib.reload(connectors.utils.context)

            # Should not raise ImportError
            from connectors.utils.context import ChatContext
            assert ChatContext is not None

# Edge cases and error handling
class TestContextEdgeCases:
    """Test edge cases and error handling."""

    def test_chat_context_with_extreme_values(self, mock_user, mock_settings, mock_openai_client):
        """Test ChatContext with extreme or unusual values."""
        from connectors.utils.context import ChatContext

        # Test with very long strings
        long_string = "x" * 10000

        context = ChatContext(
            user_id=long_string,
            logged_in=True,
            chat_id=long_string,
            prompt=long_string,
            production=False,
            project_id=long_string,
            user=mock_user,
            settings=mock_settings,
            openai_client=mock_openai_client
        )

        # Should handle long strings without issues
        assert len(context.user_id) == 10000
        assert len(context.chat_id) == 10000
        assert len(context.prompt) == 10000
        assert len(context.project_id) == 10000

    def test_chat_context_with_empty_strings(self, mock_user, mock_settings, mock_openai_client):
        """Test ChatContext with empty string values."""
        from connectors.utils.context import ChatContext

        context = ChatContext(
            user_id="",
            logged_in=False,
            chat_id="",
            prompt="",
            production=True,
            project_id="",
            user=mock_user,
            settings=mock_settings,
            openai_client=mock_openai_client
        )

        # Should handle empty strings
        assert context.user_id == ""
        assert context.chat_id == ""
        assert context.prompt == ""
        assert context.project_id == ""

    def test_chat_context_with_unicode_strings(self, mock_user, mock_settings, mock_openai_client):
        """Test ChatContext with unicode strings."""
        from connectors.utils.context import ChatContext

        context = ChatContext(
            user_id="用户123",
            logged_in=True,
            chat_id="聊天456",
            prompt="测试提示",
            production=False,
            project_id="测试项目",
            user=mock_user,
            settings=mock_settings,
            openai_client=mock_openai_client
        )

        # Should handle unicode strings
        assert context.user_id == "用户123"
        assert context.chat_id == "聊天456"
        assert context.prompt == "测试提示"
        assert context.project_id == "测试项目"

    def test_chat_context_field_immutability_check(self, mock_user, mock_settings, mock_openai_client):
        """Test if ChatContext fields can be made immutable (frozen=True)."""
        from connectors.utils.context import ChatContext

        # Current implementation allows mutation, but we test the behavior
        context = ChatContext(
            user_id="test",
            logged_in=True,
            chat_id="test",
            prompt="test",
            production=False,
            project_id="test",
            user=mock_user,
            settings=mock_settings,
            openai_client=mock_openai_client
        )

        # Should be mutable (default dataclass behavior)
        context.user_id = "modified"
        assert context.user_id == "modified"

    def test_utility_functions_with_dynamic_context_values(self):
        """Test utility functions with dynamically changing context values."""
        from connectors.utils.context import is_google_enabled, is_plaid_enabled

        mock_ctx = Mock()
        mock_context = Mock()
        mock_ctx.context = mock_context
        mock_agent = Mock()

        # Test changing values
        mock_context.is_google_enabled = True
        assert is_google_enabled(mock_ctx, mock_agent) == True

        mock_context.is_google_enabled = False
        assert is_google_enabled(mock_ctx, mock_agent) == False

        mock_context.is_plaid_enabled = True
        assert is_plaid_enabled(mock_ctx, mock_agent) == True

        mock_context.is_plaid_enabled = False
        assert is_plaid_enabled(mock_ctx, mock_agent) == False
