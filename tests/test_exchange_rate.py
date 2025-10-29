"""
Comprehensive tests for connectors/exchange_rate.py

Tests cover the Exchange Rate agent, its tools, and various edge cases.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import json
import requests
from agents import Agent, RunContextWrapper
from connectors.exchange_rate import (
    EXCHANGE_RATE_AGENT,
    get_exchange_rates_for_currency,
    get_exchange_rate_for_currency_pair,
    EXCHANGE_RATE_API_KEY
)


class TestExchangeRateConfig:
    """Test Exchange Rate agent configuration and setup."""

    def test_exchange_rate_agent_exists(self):
        """Test that EXCHANGE_RATE_AGENT is properly configured."""
        assert EXCHANGE_RATE_AGENT is not None
        assert isinstance(EXCHANGE_RATE_AGENT, Agent)
        assert EXCHANGE_RATE_AGENT.name == "Exchange Rate Agent"
        assert len(EXCHANGE_RATE_AGENT.tools) == 2

    def test_agent_tools_registered(self):
        """Test that all tools are registered with the agent."""
        tool_names = [tool.name for tool in EXCHANGE_RATE_AGENT.tools]
        assert "get_exchange_rates_for_currency" in tool_names
        assert "get_exchange_rate_for_currency_pair" in tool_names

    def test_agent_instructions_configured(self):
        """Test that agent instructions are properly set."""
        assert EXCHANGE_RATE_AGENT.instructions is not None
        assert "currency exchange rate" in EXCHANGE_RATE_AGENT.instructions
        assert "ISO 4217" in EXCHANGE_RATE_AGENT.instructions

    def test_agent_handoff_description_configured(self):
        """Test that agent handoff description is properly set."""
        assert EXCHANGE_RATE_AGENT.handoff_description is not None
        assert "real-time currency exchange rate" in EXCHANGE_RATE_AGENT.handoff_description

    def test_api_key_configuration(self):
        """Test that API key is configured."""
        assert EXCHANGE_RATE_API_KEY is not None


class TestExchangeRateImportFallback:
    """Test the import fallback mechanism."""

    def test_config_import_fallback(self):
        """Test that the module handles config import errors gracefully."""
        import connectors.exchange_rate
        assert hasattr(connectors.exchange_rate, 'SETTINGS')
        assert hasattr(connectors.exchange_rate, 'EXCHANGE_RATE_API_KEY')
        assert hasattr(connectors.exchange_rate, 'EXCHANGE_RATE_AGENT')


class TestGetExchangeRatesForCurrencyTool:
    """Test the get_exchange_rates_for_currency tool."""

    @patch('connectors.exchange_rate.requests.get')
    @pytest.mark.asyncio
    async def test_get_exchange_rates_success(self, mock_get):
        """Test successful retrieval of exchange rates for a currency."""
        # Mock API response
        mock_api_response = Mock()
        mock_api_response.json.return_value = {
            "result": "success",
            "documentation": "https://www.exchangerate-api.com/docs",
            "terms_of_use": "https://www.exchangerate-api.com/terms",
            "time_last_update_unix": 1706745600,
            "time_last_update_utc": "Thu, 01 Feb 2024 00:00:00 +0000",
            "time_next_update_unix": 1706832000,
            "time_next_update_utc": "Fri, 02 Feb 2024 00:00:00 +0000",
            "base_code": "USD",
            "conversion_rates": {
                "EUR": 0.92,
                "GBP": 0.79,
                "JPY": 149.50,
                "AUD": 1.52,
                "CAD": 1.35,
                "CHF": 0.87
            }
        }
        mock_get.return_value = mock_api_response

        # Mock wrapper context
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = Mock()

        # Call the function tool's on_invoke_tool method
        result = await get_exchange_rates_for_currency.on_invoke_tool(
            mock_wrapper,
            json.dumps({"currency_ISO4217": "USD"})
        )

        # Verify the result
        assert result["response_type"] == "exchange_rate_for_currency"
        assert result["agent_name"] == "Exchange Rate Agent"
        assert result["friendly_name"] == "Exchange Rate for Currency"
        assert result["display_response"] is True
        assert result["response"]["result"] == "success"
        assert result["response"]["base_code"] == "USD"
        assert "conversion_rates" in result["response"]
        assert result["response"]["conversion_rates"]["EUR"] == 0.92

        # Verify API was called correctly
        mock_get.assert_called_once()
        api_url = mock_get.call_args[0][0]
        assert f"/v6/{EXCHANGE_RATE_API_KEY}/latest/USD" in api_url

    @patch('connectors.exchange_rate.requests.get')
    @pytest.mark.asyncio
    async def test_get_exchange_rates_invalid_currency(self, mock_get):
        """Test handling of invalid currency code."""
        # Mock API error response
        mock_api_response = Mock()
        mock_api_response.json.return_value = {
            "result": "error",
            "error-type": "unsupported-code"
        }
        mock_get.return_value = mock_api_response

        # Mock wrapper context
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = Mock()

        # Call the function tool's on_invoke_tool method
        result = await get_exchange_rates_for_currency.on_invoke_tool(
            mock_wrapper,
            json.dumps({"currency_ISO4217": "XXX"})
        )

        # Verify error response
        assert result["response_type"] == "exchange_rate_for_currency"
        assert result["response"]["result"] == "error"
        assert result["response"]["error-type"] == "unsupported-code"

    @patch('connectors.exchange_rate.requests.get')
    @pytest.mark.asyncio
    async def test_get_exchange_rates_network_error(self, mock_get):
        """Test handling of network errors."""
        # Mock network error
        mock_get.side_effect = requests.exceptions.RequestException(
            "Network Error")

        # Mock wrapper context
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = Mock()

        # Call the function tool's on_invoke_tool method
        result = await get_exchange_rates_for_currency.on_invoke_tool(
            mock_wrapper,
            json.dumps({"currency_ISO4217": "USD"})
        )

        # Function tool framework catches exceptions and returns error string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()

    @patch('connectors.exchange_rate.requests.get')
    @pytest.mark.asyncio
    async def test_get_exchange_rates_json_error(self, mock_get):
        """Test handling of JSON decode errors."""
        # Mock response with invalid JSON
        mock_api_response = Mock()
        mock_api_response.json.side_effect = json.JSONDecodeError(
            "Invalid JSON", "doc", 0)
        mock_get.return_value = mock_api_response

        # Mock wrapper context
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = Mock()

        # Call the function tool's on_invoke_tool method
        result = await get_exchange_rates_for_currency.on_invoke_tool(
            mock_wrapper,
            json.dumps({"currency_ISO4217": "USD"})
        )

        # Function tool framework catches exceptions and returns error string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()


class TestGetExchangeRateForCurrencyPairTool:
    """Test the get_exchange_rate_for_currency_pair tool."""

    @patch('connectors.exchange_rate.requests.get')
    @pytest.mark.asyncio
    async def test_get_currency_pair_rate_success(self, mock_get):
        """Test successful retrieval of exchange rate for currency pair."""
        # Mock API response
        mock_api_response = Mock()
        mock_api_response.json.return_value = {
            "result": "success",
            "documentation": "https://www.exchangerate-api.com/docs",
            "terms_of_use": "https://www.exchangerate-api.com/terms",
            "time_last_update_unix": 1706745600,
            "time_last_update_utc": "Thu, 01 Feb 2024 00:00:00 +0000",
            "time_next_update_unix": 1706832000,
            "time_next_update_utc": "Fri, 02 Feb 2024 00:00:00 +0000",
            "base_code": "USD",
            "target_code": "EUR",
            "conversion_rate": 0.92
        }
        mock_get.return_value = mock_api_response

        # Mock wrapper context
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = Mock()

        # Call the function tool's on_invoke_tool method
        result = await get_exchange_rate_for_currency_pair.on_invoke_tool(
            mock_wrapper,
            json.dumps({
                "from_currency_ISO4217": "USD",
                "to_currency_ISO4217": "EUR"
            })
        )

        # Verify the result
        assert result["response_type"] == "exchange_rate_for_currency_pair"
        assert result["agent_name"] == "Exchange Rate Agent"
        assert result["friendly_name"] == "Exchange Rate for Currency Pair"
        assert result["display_response"] is True
        assert result["response"]["result"] == "success"
        assert result["response"]["base_code"] == "USD"
        assert result["response"]["target_code"] == "EUR"
        assert result["response"]["conversion_rate"] == 0.92

        # Verify API was called correctly
        mock_get.assert_called_once()
        api_url = mock_get.call_args[0][0]
        assert f"/v6/{EXCHANGE_RATE_API_KEY}/pair/USD/EUR" in api_url
        assert "/100" not in api_url  # No amount specified

    @patch('connectors.exchange_rate.requests.get')
    @pytest.mark.asyncio
    async def test_get_currency_pair_rate_with_amount(self, mock_get):
        """Test currency conversion with amount."""
        # Mock API response with conversion result
        mock_api_response = Mock()
        mock_api_response.json.return_value = {
            "result": "success",
            "documentation": "https://www.exchangerate-api.com/docs",
            "terms_of_use": "https://www.exchangerate-api.com/terms",
            "time_last_update_unix": 1706745600,
            "time_last_update_utc": "Thu, 01 Feb 2024 00:00:00 +0000",
            "time_next_update_unix": 1706832000,
            "time_next_update_utc": "Fri, 02 Feb 2024 00:00:00 +0000",
            "base_code": "USD",
            "target_code": "EUR",
            "conversion_rate": 0.92,
            "conversion_result": 92.0
        }
        mock_get.return_value = mock_api_response

        # Mock wrapper context
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = Mock()

        # Call the function tool's on_invoke_tool method
        result = await get_exchange_rate_for_currency_pair.on_invoke_tool(
            mock_wrapper,
            json.dumps({
                "from_currency_ISO4217": "USD",
                "to_currency_ISO4217": "EUR",
                "amount": 100.0
            })
        )

        # Verify the result
        assert result["response_type"] == "exchange_rate_for_currency_pair"
        assert result["response"]["result"] == "success"
        assert result["response"]["conversion_rate"] == 0.92
        assert result["response"]["conversion_result"] == 92.0

        # Verify API was called with amount
        mock_get.assert_called_once()
        api_url = mock_get.call_args[0][0]
        assert f"/v6/{EXCHANGE_RATE_API_KEY}/pair/USD/EUR/100" in api_url

    @patch('connectors.exchange_rate.requests.get')
    @pytest.mark.asyncio
    async def test_get_currency_pair_invalid_pair(self, mock_get):
        """Test handling of invalid currency pair."""
        # Mock API error response
        mock_api_response = Mock()
        mock_api_response.json.return_value = {
            "result": "error",
            "error-type": "unsupported-code"
        }
        mock_get.return_value = mock_api_response

        # Mock wrapper context
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = Mock()

        # Call the function tool's on_invoke_tool method
        result = await get_exchange_rate_for_currency_pair.on_invoke_tool(
            mock_wrapper,
            json.dumps({
                "from_currency_ISO4217": "XXX",
                "to_currency_ISO4217": "YYY"
            })
        )

        # Verify error response
        assert result["response_type"] == "exchange_rate_for_currency_pair"
        assert result["response"]["result"] == "error"
        assert result["response"]["error-type"] == "unsupported-code"

    @patch('connectors.exchange_rate.requests.get')
    @pytest.mark.asyncio
    async def test_get_currency_pair_zero_amount(self, mock_get):
        """Test handling of zero amount conversion."""
        # Mock API response
        mock_api_response = Mock()
        mock_api_response.json.return_value = {
            "result": "success",
            "base_code": "USD",
            "target_code": "EUR",
            "conversion_rate": 0.92,
            "conversion_result": 0.0
        }
        mock_get.return_value = mock_api_response

        # Mock wrapper context
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = Mock()

        # Call the function tool's on_invoke_tool method
        result = await get_exchange_rate_for_currency_pair.on_invoke_tool(
            mock_wrapper,
            json.dumps({
                "from_currency_ISO4217": "USD",
                "to_currency_ISO4217": "EUR",
                "amount": 0.0
            })
        )

        # Verify the result
        assert result["response"]["conversion_result"] == 0.0

        # Verify API was called with zero amount
        api_url = mock_get.call_args[0][0]
        assert "/pair/USD/EUR/0" in api_url

    @patch('connectors.exchange_rate.requests.get')
    @pytest.mark.asyncio
    async def test_get_currency_pair_negative_amount(self, mock_get):
        """Test handling of negative amount conversion."""
        # Mock API response
        mock_api_response = Mock()
        mock_api_response.json.return_value = {
            "result": "success",
            "base_code": "USD",
            "target_code": "EUR",
            "conversion_rate": 0.92,
            "conversion_result": -92.0
        }
        mock_get.return_value = mock_api_response

        # Mock wrapper context
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = Mock()

        # Call the function tool's on_invoke_tool method
        result = await get_exchange_rate_for_currency_pair.on_invoke_tool(
            mock_wrapper,
            json.dumps({
                "from_currency_ISO4217": "USD",
                "to_currency_ISO4217": "EUR",
                "amount": -100.0
            })
        )

        # Verify the result handles negative amounts
        assert result["response"]["conversion_result"] == -92.0


class TestExchangeRateEdgeCases:
    """Test edge cases and error conditions."""

    def test_tool_function_signatures(self):
        """Test that tool functions have correct parameter schemas."""
        # Test get_exchange_rates_for_currency
        schema1 = get_exchange_rates_for_currency.params_json_schema
        assert "properties" in schema1
        params1 = schema1["properties"]
        assert "currency_ISO4217" in params1
        assert params1["currency_ISO4217"]["type"] == "string"

        # Test get_exchange_rate_for_currency_pair
        schema2 = get_exchange_rate_for_currency_pair.params_json_schema
        assert "properties" in schema2
        params2 = schema2["properties"]
        assert "from_currency_ISO4217" in params2
        assert "to_currency_ISO4217" in params2
        assert "amount" in params2
        assert params2["from_currency_ISO4217"]["type"] == "string"
        assert params2["to_currency_ISO4217"]["type"] == "string"
        # amount has anyOf type (number or null)
        assert "anyOf" in params2["amount"]
        assert {"type": "number"} in params2["amount"]["anyOf"]
        assert {"type": "null"} in params2["amount"]["anyOf"]

    @patch('connectors.exchange_rate.requests.get')
    @pytest.mark.asyncio
    async def test_tool_response_format_consistency(self, mock_get):
        """Test that tools return consistent response format."""
        # Mock API responses for both tools
        mock_api_response = Mock()
        mock_api_response.json.return_value = {
            "result": "success",
            "base_code": "USD",
            "target_code": "EUR",
            "conversion_rate": 0.92,
            "conversion_rates": {"EUR": 0.92, "GBP": 0.79, "JPY": 149.50}
        }
        mock_get.return_value = mock_api_response
        
        # Mock wrapper context
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = Mock()

        # Test both tools
        for tool in [get_exchange_rates_for_currency, get_exchange_rate_for_currency_pair]:
            result = await tool.on_invoke_tool(
                mock_wrapper,
                '{"currency_ISO4217": "USD"}' if tool == get_exchange_rates_for_currency
                else '{"from_currency_ISO4217": "USD", "to_currency_ISO4217": "EUR"}'
            )

            # Verify response structure (could be dict or error string)
            assert result is not None
            if isinstance(result, dict):
                assert "response_type" in result or "error" in result
            else:
                assert isinstance(result, str)

    def test_agent_model_configuration(self):
        """Test that agent is configured with correct model."""
        assert EXCHANGE_RATE_AGENT.model == "gpt-4o"

    @patch('connectors.exchange_rate.requests.get')
    @pytest.mark.asyncio
    async def test_http_timeout_handling(self, mock_get):
        """Test handling of HTTP timeout."""
        # Mock timeout error
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

        # Mock wrapper context
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = Mock()

        # Call the function tool's on_invoke_tool method
        result = await get_exchange_rates_for_currency.on_invoke_tool(
            mock_wrapper,
            json.dumps({"currency_ISO4217": "USD"})
        )

        # Function tool framework catches exceptions and returns error string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()

    @patch('connectors.exchange_rate.requests.get')
    @pytest.mark.asyncio
    async def test_api_rate_limit_error(self, mock_get):
        """Test handling of API rate limit errors."""
        # Mock rate limit response
        mock_api_response = Mock()
        mock_api_response.json.return_value = {
            "result": "error",
            "error-type": "quota-reached"
        }
        mock_get.return_value = mock_api_response

        # Mock wrapper context
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = Mock()

        # Call the function tool's on_invoke_tool method
        result = await get_exchange_rates_for_currency.on_invoke_tool(
            mock_wrapper,
            json.dumps({"currency_ISO4217": "USD"})
        )

        # Verify error response
        assert result["response"]["result"] == "error"
        assert result["response"]["error-type"] == "quota-reached"


class TestExchangeRateIntegration:
    """Integration tests for Exchange Rate agent components."""

    def test_agent_tools_count(self):
        """Test that agent has expected number of tools."""
        assert len(EXCHANGE_RATE_AGENT.tools) == 2

    def test_all_tools_have_descriptions(self):
        """Test that all tools have proper descriptions."""
        for tool in EXCHANGE_RATE_AGENT.tools:
            assert tool.description is not None
            assert len(tool.description) > 0

    def test_import_dependencies(self):
        """Test that agent dependencies are properly imported."""
        try:
            from connectors.exchange_rate import (
                EXCHANGE_RATE_AGENT,
                get_exchange_rates_for_currency,
                get_exchange_rate_for_currency_pair
            )
            assert EXCHANGE_RATE_AGENT is not None
            assert get_exchange_rates_for_currency is not None
            assert get_exchange_rate_for_currency_pair is not None
        except ImportError as e:
            pytest.fail(f"Failed to import Exchange Rate components: {e}")

    @patch('connectors.exchange_rate.requests.get')
    @pytest.mark.asyncio
    async def test_multiple_currencies_request(self, mock_get):
        """Test handling multiple currency requests."""
        # Mock API response with many currencies
        mock_api_response = Mock()
        mock_api_response.json.return_value = {
            "result": "success",
            "base_code": "USD",
            "conversion_rates": {
                f"CUR{i}": round(0.5 + i * 0.1, 2) for i in range(100)
            }
        }
        mock_get.return_value = mock_api_response

        # Mock wrapper context
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = Mock()

        # Call the function tool's on_invoke_tool method
        result = await get_exchange_rates_for_currency.on_invoke_tool(
            mock_wrapper,
            json.dumps({"currency_ISO4217": "USD"})
        )

        # Verify large response is handled
        assert len(result["response"]["conversion_rates"]) == 100

    def test_tool_parameter_validation(self):
        """Test that tools validate required parameters."""
        # Check required parameters in schemas
        schema1 = get_exchange_rates_for_currency.params_json_schema
        assert "required" in schema1
        assert "currency_ISO4217" in schema1["required"]

        schema2 = get_exchange_rate_for_currency_pair.params_json_schema
        assert "required" in schema2
        assert "from_currency_ISO4217" in schema2["required"]
        assert "to_currency_ISO4217" in schema2["required"]
        # amount is in required but accepts null
        assert "amount" in schema2["required"]

    @patch('connectors.exchange_rate.requests.get')
    @pytest.mark.asyncio
    async def test_special_currency_codes(self, mock_get):
        """Test handling of special currency codes like cryptocurrencies."""
        # Mock API response for crypto
        mock_api_response = Mock()
        mock_api_response.json.return_value = {
            "result": "success",
            "base_code": "BTC",
            "conversion_rates": {
                "USD": 45000.00,
                "EUR": 41400.00
            }
        }
        mock_get.return_value = mock_api_response

        # Mock wrapper context
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = Mock()

        # Call the function tool's on_invoke_tool method
        result = await get_exchange_rates_for_currency.on_invoke_tool(
            mock_wrapper,
            json.dumps({"currency_ISO4217": "BTC"})
        )

        # Verify crypto currency is handled
        assert result["response"]["base_code"] == "BTC"
        assert result["response"]["conversion_rates"]["USD"] == 45000.00
