"""
Comprehensive tests for connectors/google_shopping.py

Tests cover the Google Shopping agent, its tools, and various edge cases.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from agents import Agent, RunContextWrapper
from connectors.google_shopping import (
    GOOGLE_SHOPPING_AGENT,
    get_google_products,
    ALL_TOOLS,
    SERPAPI_API_KEY
)


class TestGoogleShoppingConfig:
    """Test Google Shopping agent configuration and setup."""

    def test_google_shopping_agent_exists(self):
        """Test that GOOGLE_SHOPPING_AGENT is properly configured."""
        assert GOOGLE_SHOPPING_AGENT is not None
        assert isinstance(GOOGLE_SHOPPING_AGENT, Agent)
        assert GOOGLE_SHOPPING_AGENT.name == "Google Shopping"
        assert GOOGLE_SHOPPING_AGENT.model == "gpt-4o"
        assert len(GOOGLE_SHOPPING_AGENT.tools) == 1

    def test_all_tools_exported(self):
        """Test that ALL_TOOLS contains expected tools."""
        assert len(ALL_TOOLS) == 1
        assert get_google_products in ALL_TOOLS

    def test_agent_handoffs_configured(self):
        """Test that agent handoffs are properly configured."""
        assert hasattr(GOOGLE_SHOPPING_AGENT, 'handoffs')
        assert len(GOOGLE_SHOPPING_AGENT.handoffs) == 5
        handoff_names = [
            agent.name for agent in GOOGLE_SHOPPING_AGENT.handoffs]
        assert "Google Docs" in handoff_names
        assert "GMail" in handoff_names
        assert "OpenExternalUrl" in handoff_names
        assert "Fetch Website" in handoff_names

    def test_agent_instructions_configured(self):
        """Test that agent instructions are properly set."""
        assert GOOGLE_SHOPPING_AGENT.instructions is not None
        assert "Search Google Shopping" in GOOGLE_SHOPPING_AGENT.instructions
        assert "compare product prices" in GOOGLE_SHOPPING_AGENT.instructions

    def test_agent_handoff_description_configured(self):
        """Test that agent handoff description is properly set."""
        assert GOOGLE_SHOPPING_AGENT.handoff_description is not None
        assert "Google Shopping for product search" in GOOGLE_SHOPPING_AGENT.handoff_description
        assert "Google Shopping" in GOOGLE_SHOPPING_AGENT.handoff_description
        assert "price comparison" in GOOGLE_SHOPPING_AGENT.handoff_description

    def test_serpapi_api_key_configured(self):
        """Test that SERPAPI_API_KEY is configured."""
        assert SERPAPI_API_KEY is not None
        # It should be loaded from Settings


class TestGetGoogleProductsTool:
    """Test the get_google_products tool."""

    @patch('connectors.google_shopping.GoogleSearch')
    @patch('builtins.print')
    @pytest.mark.asyncio
    async def test_get_google_products_success(self, mock_print, mock_google_search_class):
        """Test successful product search."""
        # Mock GoogleSearch instance
        mock_search = Mock()
        mock_google_search_class.return_value = mock_search

        # Mock search results
        mock_results = {
            'shopping_results': [
                {
                    'title': 'Test Product 1',
                    'price': '$99.99',
                    'source': 'Store A',
                    'link': 'https://store-a.com/product1',
                    'rating': 4.5,
                    'reviews': 150
                },
                {
                    'title': 'Test Product 2',
                    'price': '$79.99',
                    'source': 'Store B',
                    'link': 'https://store-b.com/product2',
                    'rating': 4.2,
                    'reviews': 85
                }
            ],
            'search_metadata': {'status': 'Success'},
            'search_parameters': {'q': 'test query'}
        }
        mock_search.get_dict.return_value = mock_results

        # Mock the tool context
        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        result = await get_google_products.on_invoke_tool(
            mock_wrapper,
            '{"query": "test query"}'
        )

        # Verify GoogleSearch was called correctly
        mock_google_search_class.assert_called_once_with({
            'q': 'test query',
            'engine': 'google_shopping',
            'api_key': SERPAPI_API_KEY
        })
        mock_search.get_dict.assert_called_once()

        # Verify print was called with results keys
        mock_print.assert_called_once_with(mock_results.keys())

        # Verify response structure
        assert result['response_type'] == 'google_products'
        assert result['agent_name'] == 'Google'
        assert result['friendly_name'] == 'Google Products'
        assert result['response'] == mock_results['shopping_results']
        assert len(result['response']) == 2
        assert result['response'][0]['title'] == 'Test Product 1'

    @patch('connectors.google_shopping.GoogleSearch')
    @patch('builtins.print')
    @pytest.mark.asyncio
    async def test_get_google_products_empty_results(self, mock_print, mock_google_search_class):
        """Test product search with no results."""
        mock_search = Mock()
        mock_google_search_class.return_value = mock_search

        # Mock empty results
        mock_results = {
            'shopping_results': [],
            'search_metadata': {'status': 'Success'}
        }
        mock_search.get_dict.return_value = mock_results

        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        result = await get_google_products.on_invoke_tool(
            mock_wrapper,
            '{"query": "very specific product xyz123"}'
        )

        assert result['response_type'] == 'google_products'
        assert result['response'] == []

    @patch('connectors.google_shopping.GoogleSearch')
    @pytest.mark.asyncio
    async def test_get_google_products_special_characters(self, mock_google_search_class):
        """Test product search with special characters in query."""
        mock_search = Mock()
        mock_google_search_class.return_value = mock_search

        mock_results = {
            'shopping_results': [
                {
                    'title': 'Product with special chars & symbols €',
                    'price': '€99.99',
                    'source': 'International Store'
                }
            ]
        }
        mock_search.get_dict.return_value = mock_results

        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        result = await get_google_products.on_invoke_tool(
            mock_wrapper,
            '{"query": "product & accessories €"}'
        )

        # Verify query is passed correctly
        call_args = mock_google_search_class.call_args[0][0]
        assert call_args['q'] == 'product & accessories €'

    @patch('connectors.google_shopping.GoogleSearch')
    @pytest.mark.asyncio
    async def test_get_google_products_api_error(self, mock_google_search_class):
        """Test handling of API errors during search."""
        mock_search = Mock()
        mock_google_search_class.return_value = mock_search

        # Mock API error
        mock_search.get_dict.side_effect = Exception(
            "API Error: Rate limit exceeded")

        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        result = await get_google_products.on_invoke_tool(
            mock_wrapper,
            '{"query": "test product"}'
        )

        # The function tool framework catches exceptions and returns error message as string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()

    @patch('connectors.google_shopping.GoogleSearch')
    @pytest.mark.asyncio
    async def test_get_google_products_missing_shopping_results_key(self, mock_google_search_class):
        """Test handling when 'shopping_results' key is missing."""
        mock_search = Mock()
        mock_google_search_class.return_value = mock_search

        # Mock results without shopping_results key
        mock_results = {
            'error': 'No results found',
            'search_metadata': {'status': 'No Results'}
        }
        mock_search.get_dict.return_value = mock_results

        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        result = await get_google_products.on_invoke_tool(
            mock_wrapper,
            '{"query": "nonexistent product"}'
        )

        # Should raise KeyError which gets caught and returned as error string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()


class TestGoogleShoppingAgentIntegration:
    """Integration tests for Google Shopping agent components."""

    def test_agent_tools_registration(self):
        """Test that tools are properly registered with the agent."""
        tool_names = [tool.name for tool in GOOGLE_SHOPPING_AGENT.tools]
        assert "get_google_products" in tool_names

    def test_agent_model_configuration(self):
        """Test that agent uses correct model."""
        assert GOOGLE_SHOPPING_AGENT.model == "gpt-4o"

    def test_import_dependencies(self):
        """Test that agent dependencies are properly imported."""
        try:
            from connectors.google_shopping import (
                GOOGLE_SHOPPING_AGENT,
                get_google_products,
                ALL_TOOLS
            )
            assert GOOGLE_SHOPPING_AGENT is not None
            assert get_google_products is not None
            assert ALL_TOOLS is not None
        except ImportError as e:
            pytest.fail(f"Failed to import Google Shopping components: {e}")

    def test_finnhub_import_unused(self):
        """Test that finnhub is imported but not used (code quality issue)."""
        # This documents that finnhub is imported but never used in the module
        import connectors.google_shopping
        import inspect

        # Get the source of the module
        module_source = inspect.getsource(connectors.google_shopping)

        # Check that finnhub is imported
        assert "import finnhub" in module_source
        # But it's never used elsewhere in the code
        assert module_source.count("finnhub") == 1  # Only the import line


class TestGoogleShoppingEdgeCases:
    """Test edge cases and error conditions."""

    def test_get_google_products_tool_signature(self):
        """Test that get_google_products tool has correct parameter schema."""
        schema = get_google_products.params_json_schema
        assert "properties" in schema
        params = schema["properties"]
        assert "query" in params
        assert params["query"]["type"] == "string"

    def test_agent_name_consistency(self):
        """Test that agent name is consistent."""
        assert GOOGLE_SHOPPING_AGENT.name == "Google Shopping"

    def test_all_tools_contains_all_functions(self):
        """Test that ALL_TOOLS exports all available tool functions."""
        expected_tools = [get_google_products]
        assert len(ALL_TOOLS) == len(expected_tools)
        for tool in expected_tools:
            assert tool in ALL_TOOLS

    def test_agent_instructions_mention_key_functionality(self):
        """Test that agent instructions mention key functionality."""
        instructions = GOOGLE_SHOPPING_AGENT.instructions
        assert "Search Google Shopping" in instructions
        assert "compare product prices" in instructions

    @pytest.mark.asyncio
    async def test_missing_required_parameters(self):
        """Test tool with missing required parameters."""
        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        # Test get_google_products without query
        result = await get_google_products.on_invoke_tool(
            mock_wrapper,
            '{}'
        )
        assert isinstance(result, str)
        assert "error" in result.lower()

    @patch('connectors.google_shopping.GoogleSearch')
    @pytest.mark.asyncio
    async def test_complex_product_results(self, mock_google_search_class):
        """Test handling of complex product results with all fields."""
        mock_search = Mock()
        mock_google_search_class.return_value = mock_search

        # Mock comprehensive product results
        mock_results = {
            'shopping_results': [
                {
                    'position': 1,
                    'title': 'Premium Laptop Computer',
                    'price': '$1,299.99',
                    'extracted_price': 1299.99,
                    'source': 'TechStore Pro',
                    'link': 'https://techstore.com/laptop123',
                    'rating': 4.7,
                    'reviews': 2345,
                    'thumbnail': 'https://techstore.com/images/laptop123.jpg',
                    'delivery': 'Free 2-day delivery',
                    'product_id': 'LAP123456',
                    'extensions': ['16GB RAM', '512GB SSD', '15.6" Display']
                }
            ],
            'filters': {
                'brands': ['Dell', 'HP', 'Lenovo'],
                'price_range': {'min': 500, 'max': 2000}
            }
        }
        mock_search.get_dict.return_value = mock_results

        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        result = await get_google_products.on_invoke_tool(
            mock_wrapper,
            '{"query": "laptop computer"}'
        )

        assert result['response_type'] == 'google_products'
        assert len(result['response']) == 1
        product = result['response'][0]
        assert product['title'] == 'Premium Laptop Computer'
        assert product['rating'] == 4.7
        assert product['reviews'] == 2345
        assert 'extensions' in product

    def test_settings_import_fallback(self):
        """Test that Settings import has a fallback."""
        # This tests the try/except import pattern for Settings
        import connectors.google_shopping
        import inspect

        module_source = inspect.getsource(connectors.google_shopping)

        # Check that there's a try/except for Settings import
        assert "try:" in module_source
        assert "from config import Settings" in module_source
        assert "except ImportError:" in module_source
        assert "from ..config import Settings" in module_source

    def test_serpapi_dependency(self):
        """Test that serpapi is properly imported."""
        import connectors.google_shopping
        assert hasattr(connectors.google_shopping, 'GoogleSearch')

    @patch('connectors.google_shopping.GoogleSearch')
    @pytest.mark.asyncio
    async def test_long_query_handling(self, mock_google_search_class):
        """Test handling of very long search queries."""
        mock_search = Mock()
        mock_google_search_class.return_value = mock_search

        mock_results = {'shopping_results': []}
        mock_search.get_dict.return_value = mock_results

        # Create a very long query
        long_query = "laptop computer " * 50  # Very long query

        mock_ctx = Mock()
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        result = await get_google_products.on_invoke_tool(
            mock_wrapper,
            f'{{"query": "{long_query}"}}'
        )

        # Verify the long query was passed to the API
        call_args = mock_google_search_class.call_args[0][0]
        assert call_args['q'] == long_query
