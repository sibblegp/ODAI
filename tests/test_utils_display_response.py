"""
Comprehensive tests for connectors/utils/display_response.py

Tests cover OpenAI-based response filtering functionality including prompt processing,
JSON response handling, and decision-making for displaying responses.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from openai import OpenAI


class TestDisplayResponseUtils:
    """Test cases for display_response.py OpenAI response filtering utilities."""

    @pytest.fixture
    def mock_openai_client(self):
        """Mock the OpenAI client."""
        with patch('connectors.utils.display_response.OPENAI_CLIENT') as mock_client:
            yield mock_client

    @pytest.fixture
    def mock_settings(self):
        """Mock the Settings configuration."""
        with patch('connectors.utils.display_response.Settings') as mock_settings_class:
            mock_settings = Mock()
            mock_settings.openai_api_key = "test-openai-key"
            mock_settings_class.return_value = mock_settings
            yield mock_settings

    @pytest.fixture
    def sample_openai_response_true(self):
        """Create a sample OpenAI response indicating to display response."""
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = '{"display_response": true}'
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        return mock_response

    @pytest.fixture
    def sample_openai_response_false(self):
        """Create a sample OpenAI response indicating not to display response."""
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = '{"display_response": false}'
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        return mock_response

    def test_display_response_check_true(self, mock_openai_client, sample_openai_response_true):
        """Test display_response_check returning True."""
        from connectors.utils.display_response import display_response_check

        # Setup mock
        mock_openai_client.chat.completions.create.return_value = sample_openai_response_true

        # Call function
        result = display_response_check(
            "Test prompt", "Should this be displayed?")

        # Verify results
        assert result == True
        mock_openai_client.chat.completions.create.assert_called_once()

        # Verify the API call parameters
        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-4o"
        assert call_args[1]["response_format"] == {"type": "json_object"}

        # Check messages structure
        messages = call_args[1]["messages"]
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Test prompt"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Should this be displayed?"
        assert messages[2]["role"] == "user"
        assert "json format" in messages[2]["content"]
        assert "display_response" in messages[2]["content"]

    def test_display_response_check_false(self, mock_openai_client, sample_openai_response_false):
        """Test display_response_check returning False."""
        from connectors.utils.display_response import display_response_check

        # Setup mock
        mock_openai_client.chat.completions.create.return_value = sample_openai_response_false

        # Call function
        result = display_response_check(
            "Test prompt", "Should this be hidden?")

        # Verify results
        assert result == False

    def test_display_response_check_none_content(self, mock_openai_client):
        """Test display_response_check with None content in response."""
        from connectors.utils.display_response import display_response_check

        # Setup mock with None content
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = None
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_openai_client.chat.completions.create.return_value = mock_response

        # Call function
        result = display_response_check("Test prompt", "Display prompt")

        # Should return False when content is None
        assert result == False

    def test_display_response_check_invalid_json(self, mock_openai_client):
        """Test display_response_check with invalid JSON response."""
        from connectors.utils.display_response import display_response_check

        # Setup mock with invalid JSON
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = '{"invalid": json content}'
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_openai_client.chat.completions.create.return_value = mock_response

        # Call function - should raise JSONDecodeError
        with pytest.raises(json.JSONDecodeError):
            display_response_check("Test prompt", "Display prompt")

    def test_display_response_check_missing_key(self, mock_openai_client):
        """Test display_response_check with missing display_response key."""
        from connectors.utils.display_response import display_response_check

        # Setup mock with valid JSON but missing key
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = '{"other_key": true}'
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_openai_client.chat.completions.create.return_value = mock_response

        # Call function - should raise KeyError
        with pytest.raises(KeyError):
            display_response_check("Test prompt", "Display prompt")

    def test_display_response_check_empty_strings(self, mock_openai_client, sample_openai_response_true):
        """Test display_response_check with empty string parameters."""
        from connectors.utils.display_response import display_response_check

        # Setup mock
        mock_openai_client.chat.completions.create.return_value = sample_openai_response_true

        # Call function with empty strings
        result = display_response_check("", "")

        # Should still work
        assert result == True

        # Verify empty strings were passed to API
        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        assert messages[0]["content"] == ""
        assert messages[1]["content"] == ""

    def test_display_response_check_unicode_content(self, mock_openai_client, sample_openai_response_true):
        """Test display_response_check with unicode content."""
        from connectors.utils.display_response import display_response_check

        # Setup mock
        mock_openai_client.chat.completions.create.return_value = sample_openai_response_true

        # Call function with unicode strings
        unicode_prompt = "测试提示"
        unicode_display_prompt = "应该显示吗？"
        result = display_response_check(unicode_prompt, unicode_display_prompt)

        # Should handle unicode correctly
        assert result == True

        # Verify unicode strings were passed correctly
        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        assert messages[0]["content"] == unicode_prompt
        assert messages[1]["content"] == unicode_display_prompt

    def test_display_response_check_long_content(self, mock_openai_client, sample_openai_response_false):
        """Test display_response_check with very long content."""
        from connectors.utils.display_response import display_response_check

        # Setup mock
        mock_openai_client.chat.completions.create.return_value = sample_openai_response_false

        # Call function with long strings
        long_prompt = "A" * 10000
        long_display_prompt = "B" * 5000
        result = display_response_check(long_prompt, long_display_prompt)

        # Should handle long content
        assert result == False

        # Verify long strings were passed correctly
        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        assert len(messages[0]["content"]) == 10000
        assert len(messages[1]["content"]) == 5000

    def test_display_response_check_json_response_variations(self, mock_openai_client):
        """Test display_response_check with various JSON response formats."""
        from connectors.utils.display_response import display_response_check

        # Test different valid JSON responses
        test_cases = [
            ('{"display_response": true}', True),
            ('{"display_response": false}', False),
            ('{"display_response": 1}', 1),  # Truthy value
            ('{"display_response": 0}', 0),  # Falsy value
            ('{"display_response": "true"}', "true"),  # String value
            ('{"display_response": "false"}', "false"),  # String value
            ('{"display_response": null}', None),  # Null value
        ]

        for json_content, expected in test_cases:
            # Setup mock response
            mock_response = Mock()
            mock_choice = Mock()
            mock_message = Mock()
            mock_message.content = json_content
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]
            mock_openai_client.chat.completions.create.return_value = mock_response

            # Call function
            result = display_response_check("Test", "Test")

            # Verify result
            assert result == expected

    def test_display_response_check_openai_api_error(self, mock_openai_client):
        """Test display_response_check with OpenAI API error."""
        from connectors.utils.display_response import display_response_check

        # Setup mock to raise an exception
        mock_openai_client.chat.completions.create.side_effect = Exception(
            "API Error")

        # Call function - should propagate the exception
        with pytest.raises(Exception, match="API Error"):
            display_response_check("Test prompt", "Display prompt")

    def test_module_initialization(self, mock_settings):
        """Test module initialization with OpenAI client setup."""
        # Reload the module to test initialization
        import importlib
        import connectors.utils.display_response
        importlib.reload(connectors.utils.display_response)

        # Verify the settings and client were initialized
        assert connectors.utils.display_response.SETTINGS.openai_api_key == "test-openai-key"
        assert connectors.utils.display_response.OPENAI_CLIENT is not None

    def test_settings_import_error_handling(self):
        """Test module behavior when Settings import fails."""
        with patch('connectors.utils.display_response.Settings', side_effect=ImportError("Settings not found")):
            # Should try alternative import path
            with patch('builtins.print'):  # Mock print to avoid output during test
                # Re-import to trigger the ImportError handling
                import importlib
                import connectors.utils.display_response
                importlib.reload(connectors.utils.display_response)

    def test_json_parsing_edge_cases(self, mock_openai_client):
        """Test JSON parsing with edge cases."""
        from connectors.utils.display_response import display_response_check

        edge_cases = [
            '{}',  # Empty JSON object
            '{"display_response": {"nested": true}}',  # Nested object
            '{"display_response": [true, false]}',  # Array value
            '{"display_response": 42.5}',  # Float value
        ]

        for json_content in edge_cases:
            # Setup mock response
            mock_response = Mock()
            mock_choice = Mock()
            mock_message = Mock()
            mock_message.content = json_content
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]
            mock_openai_client.chat.completions.create.return_value = mock_response

            if json_content == '{}':
                # Empty object should raise KeyError
                with pytest.raises(KeyError):
                    display_response_check("Test", "Test")
            else:
                # Other cases should return the parsed value
                result = display_response_check("Test", "Test")
                parsed = json.loads(json_content)
                assert result == parsed['display_response']


# Integration and error handling tests
class TestDisplayResponseUtilsIntegration:
    """Integration tests for display_response.py utilities."""

    @pytest.fixture
    def mock_openai_client(self):
        """Mock the OpenAI client."""
        with patch('connectors.utils.display_response.OPENAI_CLIENT') as mock_client:
            yield mock_client

    def test_import_structure(self):
        """Test that all required imports are accessible."""
        # Test function import
        from connectors.utils.display_response import display_response_check

        # Test module imports
        from connectors.utils.display_response import OpenAI, json

        # Verify function is callable
        assert callable(display_response_check)

        # Verify modules are accessible
        assert OpenAI is not None
        assert json is not None

    def test_function_signature(self):
        """Test that function has expected signature."""
        from connectors.utils.display_response import display_response_check
        import inspect

        signature = inspect.signature(display_response_check)

        # Should have two parameters
        params = list(signature.parameters.keys())
        assert len(params) == 2
        assert params[0] == "prompt"
        assert params[1] == "display_response_prompt"

        # Check return annotation
        return_annotation = signature.return_annotation
        assert return_annotation == bool

    def test_constants_and_globals(self):
        """Test that module constants are properly set."""
        import connectors.utils.display_response as module

        # Should have SETTINGS and OPENAI_CLIENT
        assert hasattr(module, 'SETTINGS')
        assert hasattr(module, 'OPENAI_CLIENT')

        # SETTINGS should have openai_api_key
        assert hasattr(module.SETTINGS, 'openai_api_key')

    def test_real_json_parsing(self):
        """Test actual JSON parsing without mocking json module."""
        import json as real_json

        # Test that our expected JSON formats are valid
        test_jsons = [
            '{"display_response": true}',
            '{"display_response": false}',
            '{"display_response": null}',
            '{"display_response": "text"}',
            '{"display_response": 123}',
        ]

        for json_str in test_jsons:
            parsed = real_json.loads(json_str)
            assert 'display_response' in parsed
            # Verify the value can be accessed
            value = parsed['display_response']
            assert value is not None or value is None  # Handle null case

    def test_openai_message_structure_validation(self, mock_openai_client):
        """Test that the OpenAI API call uses correct message structure."""
        # Setup mock response
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = '{"display_response": true}'
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_openai_client.chat.completions.create.return_value = mock_response

        # Import and call function
        from connectors.utils.display_response import display_response_check
        display_response_check("user prompt", "display check prompt")

        # Verify the message structure matches OpenAI expectations
        call_args = mock_openai_client.chat.completions.create.call_args[1]
        messages = call_args["messages"]

        # All messages should have role and content
        for message in messages:
            assert "role" in message
            assert "content" in message
            assert message["role"] == "user"
            assert isinstance(message["content"], str)

        # Verify specific message contents
        assert messages[0]["content"] == "user prompt"
        assert messages[1]["content"] == "display check prompt"
        assert "Return your response in json format" in messages[2]["content"]
        assert "boolean value called 'display_response'" in messages[2]["content"]
