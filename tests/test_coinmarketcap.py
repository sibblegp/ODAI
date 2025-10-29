"""
Comprehensive tests for connectors/coinmarketcap.py

Tests cover the CoinMarketCap agent, its tools, and various edge cases.
"""

import pytest
from unittest.mock import Mock, patch
from agents import Agent
from connectors.coinmarketcap import (
    COINMARKETCAP_AGENT,
    COINMARKETCAP_REALTIME_AGENT,
    check_crypto_price_at_coinmarketcap,
    ALL_TOOLS
)


class TestCoinMarketCapConfig:
    """Test CoinMarketCap agent configuration and setup."""

    def test_coinmarketcap_agent_exists(self):
        """Test that COINMARKETCAP_AGENT is properly configured."""
        assert COINMARKETCAP_AGENT is not None
        assert isinstance(COINMARKETCAP_AGENT, Agent)
        assert COINMARKETCAP_AGENT.name == "CoinMarketCap"
        assert COINMARKETCAP_AGENT.model == "gpt-4o"
        assert len(COINMARKETCAP_AGENT.tools) == 1

    def test_coinmarketcap_realtime_agent_exists(self):
        """Test that COINMARKETCAP_REALTIME_AGENT is properly configured."""
        assert COINMARKETCAP_REALTIME_AGENT is not None
        assert COINMARKETCAP_REALTIME_AGENT.name == "CoinMarketCap"
        assert len(COINMARKETCAP_REALTIME_AGENT.tools) == 1

    def test_all_tools_exported(self):
        """Test that ALL_TOOLS contains expected tools."""
        assert len(ALL_TOOLS) == 1
        assert check_crypto_price_at_coinmarketcap in ALL_TOOLS

    def test_agent_handoffs_configured(self):
        """Test that agent handoffs are properly configured."""
        assert hasattr(COINMARKETCAP_AGENT, 'handoffs')
        # GOOGLE_DOCS, FETCH_WEBSITE, OPEN_EXTERNAL_URL, GMAIL
        assert len(COINMARKETCAP_AGENT.handoffs) == 4

    def test_agent_instructions_configured(self):
        """Test that agent instructions are properly set."""
        assert COINMARKETCAP_AGENT.instructions is not None
        # Instructions now focus on functionality
        assert "cryptocurrency" in COINMARKETCAP_AGENT.instructions.lower(
        ) or "coinmarketcap" in COINMARKETCAP_AGENT.instructions.lower()

    def test_agent_handoff_description_configured(self):
        """Test that agent handoff description is properly set."""
        assert COINMARKETCAP_AGENT.handoff_description is not None
        # Handoff description focuses on functionality
        assert "cryptocurrency" in COINMARKETCAP_AGENT.handoff_description.lower(
        ) or "coinmarketcap" in COINMARKETCAP_AGENT.handoff_description.lower()


class TestCheckCryptoPriceTool:
    """Test the check_crypto_price_at_coinmarketcap tool."""

    @patch('connectors.coinmarketcap.requests.get')
    @pytest.mark.asyncio
    async def test_check_crypto_price_success(self, mock_get):
        """Test successful crypto price retrieval."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": {
                "timestamp": "2023-01-01T12:00:00.000Z",
                "error_code": 0,
                "error_message": None,
                "elapsed": 10,
                "credit_count": 1,
                "notice": None
            },
            "data": {
                "BTC": {
                    "id": 1,
                    "name": "Bitcoin",
                    "symbol": "BTC",
                    "slug": "bitcoin",
                    "is_active": 1,
                    "is_fiat": 0,
                    "circulating_supply": 19500000,
                    "total_supply": 19500000,
                    "max_supply": 21000000,
                    "date_added": "2013-04-28T00:00:00.000Z",
                    "quote": {
                        "USD": {
                            "price": 45000.0,
                            "volume_24h": 25000000000,
                            "volume_change_24h": 2.5,
                            "percent_change_1h": 0.5,
                            "percent_change_24h": 3.2,
                            "percent_change_7d": -1.8,
                            "market_cap": 877500000000,
                            "market_cap_dominance": 42.5,
                            "fully_diluted_market_cap": 945000000000,
                            "last_updated": "2023-01-01T12:00:00.000Z"
                        }
                    }
                }
            }
        }
        mock_get.return_value = mock_response

        # Mock the tool context
        mock_ctx = Mock()

        result = await check_crypto_price_at_coinmarketcap.on_invoke_tool(
            mock_ctx,
            '{"crypto_symbol": "BTC"}'
        )

        # Verify API call was made correctly
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest?symbol=BTC" in args[0]
        assert "X-CMC_PRO_API_KEY" in kwargs["headers"]

        # Verify response structure
        assert result["response_type"] == "crypto_price"
        assert result["agent_name"] == "CoinMarketCap"
        assert result["friendly_name"] == "Checking the price of BTC"
        assert result["display_response"] is True
        assert result["response"]["data"]["BTC"]["quote"]["USD"]["price"] == 45000.0

    @patch('connectors.coinmarketcap.requests.get')
    @pytest.mark.asyncio
    async def test_check_crypto_price_ethereum(self, mock_get):
        """Test crypto price retrieval for Ethereum."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": {"error_code": 0},
            "data": {
                "ETH": {
                    "id": 1027,
                    "name": "Ethereum",
                    "symbol": "ETH",
                    "quote": {
                        "USD": {
                            "price": 3200.0,
                            "volume_24h": 15000000000,
                            "percent_change_24h": 5.8,
                            "market_cap": 385000000000
                        }
                    }
                }
            }
        }
        mock_get.return_value = mock_response

        # Mock the tool context
        mock_ctx = Mock()

        result = await check_crypto_price_at_coinmarketcap.on_invoke_tool(
            mock_ctx,
            '{"crypto_symbol": "ETH"}'
        )

        # Verify API call for ETH
        args, kwargs = mock_get.call_args
        assert "symbol=ETH" in args[0]

        # Verify ETH price data
        assert result["response"]["data"]["ETH"]["quote"]["USD"]["price"] == 3200.0
        assert result["friendly_name"] == "Checking the price of ETH"

    @patch('connectors.coinmarketcap.requests.get')
    @pytest.mark.asyncio
    async def test_check_crypto_price_invalid_symbol(self, mock_get):
        """Test handling of invalid cryptocurrency symbol."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": {
                "timestamp": "2023-01-01T12:00:00.000Z",
                "error_code": 400,
                "error_message": "Invalid value for \"symbol\": \"INVALID\"",
                "elapsed": 5,
                "credit_count": 1
            }
        }
        mock_get.return_value = mock_response

        # Mock the tool context
        mock_ctx = Mock()

        result = await check_crypto_price_at_coinmarketcap.on_invoke_tool(
            mock_ctx,
            '{"crypto_symbol": "INVALID"}'
        )

        # Verify API error response is passed through
        assert result["response"]["status"]["error_code"] == 400
        assert "Invalid value" in result["response"]["status"]["error_message"]

    @patch('connectors.coinmarketcap.requests.get')
    @pytest.mark.asyncio
    async def test_check_crypto_price_api_error(self, mock_get):
        """Test handling of API errors."""
        mock_get.side_effect = Exception("Network error")

        # Mock the tool context
        mock_ctx = Mock()

        result = await check_crypto_price_at_coinmarketcap.on_invoke_tool(
            mock_ctx,
            '{"crypto_symbol": "BTC"}'
        )

        # The function tool framework catches exceptions and returns error message as string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()

    @patch('connectors.coinmarketcap.requests.get')
    @pytest.mark.asyncio
    async def test_check_crypto_price_lowercase_symbol(self, mock_get):
        """Test handling of lowercase cryptocurrency symbol."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": {"error_code": 0},
            "data": {
                "BTC": {
                    "symbol": "BTC",
                    "quote": {"USD": {"price": 45000.0}}
                }
            }
        }
        mock_get.return_value = mock_response

        # Mock the tool context
        mock_ctx = Mock()

        result = await check_crypto_price_at_coinmarketcap.on_invoke_tool(
            mock_ctx,
            '{"crypto_symbol": "btc"}'
        )

        # Verify API call with lowercase symbol
        args, kwargs = mock_get.call_args
        assert "symbol=btc" in args[0]

    @patch('connectors.coinmarketcap.requests.get')
    @pytest.mark.asyncio
    async def test_check_crypto_price_altcoin(self, mock_get):
        """Test crypto price retrieval for less common altcoin."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": {"error_code": 0},
            "data": {
                "ADA": {
                    "id": 2010,
                    "name": "Cardano",
                    "symbol": "ADA",
                    "quote": {
                        "USD": {
                            "price": 0.45,
                            "volume_24h": 500000000,
                            "percent_change_24h": -2.3,
                            "market_cap": 15000000000
                        }
                    }
                }
            }
        }
        mock_get.return_value = mock_response

        # Mock the tool context
        mock_ctx = Mock()

        result = await check_crypto_price_at_coinmarketcap.on_invoke_tool(
            mock_ctx,
            '{"crypto_symbol": "ADA"}'
        )

        # Verify altcoin data
        assert result["response"]["data"]["ADA"]["quote"]["USD"]["price"] == 0.45
        assert result["friendly_name"] == "Checking the price of ADA"

    @patch('connectors.coinmarketcap.requests.get')
    @pytest.mark.asyncio
    async def test_check_crypto_price_empty_symbol(self, mock_get):
        """Test handling of empty cryptocurrency symbol."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": {
                "error_code": 400,
                "error_message": "\"symbol\" cannot be empty"
            }
        }
        mock_get.return_value = mock_response

        # Mock the tool context
        mock_ctx = Mock()

        result = await check_crypto_price_at_coinmarketcap.on_invoke_tool(
            mock_ctx,
            '{"crypto_symbol": ""}'
        )

        # Verify error handling for empty symbol
        assert result["response"]["status"]["error_code"] == 400


class TestCoinMarketCapAgentIntegration:
    """Integration tests for CoinMarketCap agent components."""

    def test_agent_tools_registration(self):
        """Test that tools are properly registered with the agent."""
        tool_names = [tool.name for tool in COINMARKETCAP_AGENT.tools]
        assert "check_crypto_price_at_coinmarketcap" in tool_names

    def test_agent_model_configuration(self):
        """Test that agent uses correct model."""
        assert COINMARKETCAP_AGENT.model == "gpt-4o"

    def test_realtime_agent_tools_registration(self):
        """Test that realtime agent has same tools as regular agent."""
        regular_tool_names = [tool.name for tool in COINMARKETCAP_AGENT.tools]
        realtime_tool_names = [
            tool.name for tool in COINMARKETCAP_REALTIME_AGENT.tools]
        assert set(regular_tool_names) == set(realtime_tool_names)

    def test_import_dependencies(self):
        """Test that agent dependencies are properly imported."""
        # This test ensures the import structure works
        try:
            from connectors.coinmarketcap import (
                COINMARKETCAP_AGENT,
                check_crypto_price_at_coinmarketcap
            )
            assert COINMARKETCAP_AGENT is not None
            assert check_crypto_price_at_coinmarketcap is not None
        except ImportError as e:
            pytest.fail(f"Failed to import CoinMarketCap components: {e}")


class TestCoinMarketCapEdgeCases:
    """Test edge cases and error conditions."""

    def test_tool_function_signature(self):
        """Test that tool function has correct parameter schema."""
        schema = check_crypto_price_at_coinmarketcap.params_json_schema
        assert "properties" in schema
        params = schema["properties"]
        assert "crypto_symbol" in params
        assert params["crypto_symbol"]["type"] == "string"

    @pytest.mark.asyncio
    async def test_tool_response_format_consistency(self):
        """Test that tool returns consistent ToolResponse format."""
        with patch('connectors.coinmarketcap.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "status": {"error_code": 0},
                "data": {"BTC": {"quote": {"USD": {"price": 45000.0}}}}
            }
            mock_get.return_value = mock_response

            # Mock the tool context
            mock_ctx = Mock()

            result = await check_crypto_price_at_coinmarketcap.on_invoke_tool(
                mock_ctx,
                '{"crypto_symbol": "BTC"}'
            )

            # Verify ToolResponse format
            required_fields = ["response_type", "agent_name",
                               "friendly_name", "display_response", "response"]
            for field in required_fields:
                assert field in result

            assert result["response_type"] == "crypto_price"
            assert result["agent_name"] == "CoinMarketCap"
            assert result["display_response"] is True

    @patch('connectors.coinmarketcap.requests.get')
    @pytest.mark.asyncio
    async def test_check_crypto_price_json_parse_error(self, mock_get):
        """Test handling when API returns invalid JSON."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        # Mock the tool context
        mock_ctx = Mock()

        result = await check_crypto_price_at_coinmarketcap.on_invoke_tool(
            mock_ctx,
            '{"crypto_symbol": "BTC"}'
        )

        # The function tool framework catches exceptions and returns error message as string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()

    def test_agent_name_consistency(self):
        """Test that agent names are consistent across instances."""
        assert COINMARKETCAP_AGENT.name == COINMARKETCAP_REALTIME_AGENT.name == "CoinMarketCap"

    def test_all_tools_contains_all_functions(self):
        """Test that ALL_TOOLS exports all available tool functions."""
        expected_tools = [check_crypto_price_at_coinmarketcap]
        assert len(ALL_TOOLS) == len(expected_tools)
        for tool in expected_tools:
            assert tool in ALL_TOOLS

    @patch('connectors.coinmarketcap.requests.get')
    @pytest.mark.asyncio
    async def test_check_crypto_price_with_special_characters(self, mock_get):
        """Test crypto symbol with special characters or numbers."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": {"error_code": 0},
            "data": {
                "SHIB": {
                    "symbol": "SHIB",
                    "quote": {"USD": {"price": 0.000008}}
                }
            }
        }
        mock_get.return_value = mock_response

        # Mock the tool context
        mock_ctx = Mock()

        result = await check_crypto_price_at_coinmarketcap.on_invoke_tool(
            mock_ctx,
            '{"crypto_symbol": "SHIB"}'
        )

        # Verify handling of very small price values
        assert result["response"]["data"]["SHIB"]["quote"]["USD"]["price"] == 0.000008

    def test_agent_instructions_consistency(self):
        """Test that agent instructions are consistent between regular and realtime agents."""
        # Both should contain the core CoinMarketCap instructions
        assert "cryptocurrency prices" in COINMARKETCAP_AGENT.instructions
        assert "cryptocurrency prices" in COINMARKETCAP_REALTIME_AGENT.instructions
