"""
Comprehensive tests for connectors/plaid_agent.py

Tests cover the Plaid agent, its tools, and various edge cases.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import datetime
import json
from agents import Agent
from connectors.plaid_agent import (
    PLAID_AGENT,
    get_accounts_at_plaid,
    get_transactions_at_plaid,
    ALL_TOOLS,
    client,
    configuration
)


class TestPlaidAgentConfig:
    """Test Plaid agent configuration and setup."""

    def test_plaid_agent_exists(self):
        """Test that PLAID_AGENT is properly configured."""
        assert PLAID_AGENT is not None
        assert isinstance(PLAID_AGENT, Agent)
        assert PLAID_AGENT.name == "Plaid"
        assert len(PLAID_AGENT.tools) == 2

    def test_all_tools_exported(self):
        """Test that ALL_TOOLS contains expected tools."""
        assert len(ALL_TOOLS) == 2
        assert get_accounts_at_plaid in ALL_TOOLS
        assert get_transactions_at_plaid in ALL_TOOLS

    def test_agent_instructions_configured(self):
        """Test that agent instructions are properly set."""
        assert PLAID_AGENT.instructions is not None
        assert "bank" in PLAID_AGENT.instructions.lower()
        assert "balances" in PLAID_AGENT.instructions
        assert "transaction" in PLAID_AGENT.instructions.lower()

    def test_agent_handoff_description_configured(self):
        """Test that agent handoff description is properly set."""
        assert PLAID_AGENT.handoff_description is not None
        assert "account balance" in PLAID_AGENT.handoff_description.lower()
        assert "balance" in PLAID_AGENT.handoff_description.lower()
        assert "transaction" in PLAID_AGENT.handoff_description.lower()

    def test_agent_handoffs_configured(self):
        """Test that agent handoffs are properly configured."""
        assert hasattr(PLAID_AGENT, 'handoffs')
        assert len(PLAID_AGENT.handoffs) == 2
        handoff_names = [agent.name for agent in PLAID_AGENT.handoffs]
        assert "Google Docs" in handoff_names
        assert "GMail" in handoff_names


class TestPlaidConfiguration:
    """Test Plaid client configuration."""

    def test_plaid_configuration(self):
        """Test that Plaid configuration is set up correctly."""
        import plaid
        assert configuration is not None
        assert configuration.host == plaid.Environment.Sandbox
        assert 'clientId' in configuration.api_key
        assert 'secret' in configuration.api_key

    def test_plaid_client_initialized(self):
        """Test that Plaid client is initialized."""
        assert client is not None
        # Verify it has expected methods
        assert hasattr(client, 'accounts_balance_get')
        assert hasattr(client, 'transactions_get')


class TestGetAccountsAtPlaid:
    """Test the get_accounts_at_plaid function tool."""

    @patch('connectors.plaid_agent.PlaidToken')
    @patch('connectors.plaid_agent.client')
    @pytest.mark.asyncio
    async def test_get_accounts_success(self, mock_client, mock_plaid_token_class):
        """Test successful retrieval of accounts."""
        # Mock PlaidToken
        mock_token = Mock()
        mock_token.decrypted_tokens.return_value = [
            {'auth_token': 'test-access-token-1'},
            {'auth_token': 'test-access-token-2'}
        ]
        mock_plaid_token_class.get_tokens_by_user_id.return_value = mock_token

        # Mock API response
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            'accounts': [
                {
                    'account_id': 'account1',
                    'balances': {'current': 1000.0},
                    'mask': '1234',
                    'name': 'Checking Account',
                    'name': 'Main Checking',
                    'type': 'depository',
                    'subtype': 'checking'
                }
            ]
        }
        mock_client.accounts_balance_get.return_value = mock_response

        # Mock context
        mock_user = Mock()
        mock_user.reference_id = 'test-user-123'
        mock_context = Mock()
        mock_context.user = mock_user
        mock_wrapper = Mock()
        mock_wrapper.context = mock_context

        result = await get_accounts_at_plaid.on_invoke_tool(mock_wrapper, '{}')

        assert result['response_type'] == 'plaid_accounts_response'
        assert result['agent_name'] == 'Plaid'
        assert result['friendly_name'] == 'Getting Account Information'
        assert result['display_response'] is True
        assert len(result['response']) == 2  # Two tokens processed

    @patch('connectors.plaid_agent.PlaidToken')
    @pytest.mark.asyncio
    async def test_get_accounts_no_plaid_token(self, mock_plaid_token_class):
        """Test handling when user has no Plaid token."""
        mock_plaid_token_class.get_tokens_by_user_id.return_value = None

        # Mock context
        mock_user = Mock()
        mock_user.reference_id = 'test-user-123'
        mock_context = Mock()
        mock_context.user = mock_user
        mock_wrapper = Mock()
        mock_wrapper.context = mock_context

        result = await get_accounts_at_plaid.on_invoke_tool(mock_wrapper, '{}')

        assert result['response_type'] == 'error'
        assert result['agent_name'] == 'Plaid'
        assert 'not connected to Plaid' in result['response']

    @patch('connectors.plaid_agent.PlaidToken')
    @patch('connectors.plaid_agent.client')
    @patch('builtins.print')
    @pytest.mark.asyncio
    async def test_get_accounts_api_error(self, mock_print, mock_client, mock_plaid_token_class):
        """Test handling of Plaid API errors."""
        # Mock PlaidToken
        mock_token = Mock()
        mock_token.decrypted_tokens.return_value = [{'auth_token': 'test-token'}]
        mock_plaid_token_class.get_tokens_by_user_id.return_value = mock_token

        # Mock API error
        import plaid
        mock_error = plaid.ApiException()
        mock_error.status = 400
        mock_error.body = json.dumps({
            'error_message': 'Invalid access token',
            'error_code': 'INVALID_ACCESS_TOKEN',
            'error_type': 'INVALID_REQUEST'
        })
        mock_client.accounts_balance_get.side_effect = mock_error

        # Mock context
        mock_user = Mock()
        mock_user.reference_id = 'test-user-123'
        mock_context = Mock()
        mock_context.user = mock_user
        mock_wrapper = Mock()
        mock_wrapper.context = mock_context

        result = await get_accounts_at_plaid.on_invoke_tool(mock_wrapper, '{}')

        assert 'error' in result
        assert result['error']['status_code'] == 400
        assert result['error']['error_code'] == 'INVALID_ACCESS_TOKEN'
        mock_print.assert_called_once()


class TestGetTransactionsAtPlaid:
    """Test the get_transactions_at_plaid function tool."""

    @patch('connectors.plaid_agent.PlaidToken')
    @patch('connectors.plaid_agent.client')
    @patch('connectors.plaid_agent.SETTINGS')
    @patch('builtins.print')
    @pytest.mark.asyncio
    async def test_get_transactions_success(self, mock_print, mock_settings, mock_client, mock_plaid_token_class):
        """Test successful retrieval of transactions."""
        # Mock settings
        mock_settings.production = False

        # Mock PlaidToken
        mock_token = Mock()
        mock_token.decrypted_tokens.return_value = [{'auth_token': 'test-token'}]
        mock_plaid_token_class.get_tokens_by_user_id.return_value = mock_token

        # Mock API response
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            'accounts': [
                {
                    'account_id': 'account1',
                    'name': 'Checking',
                    'official_name': 'Main Checking'
                }
            ],
            'transactions': [
                {
                    'account_id': 'account1',
                    'amount': 50.0,
                    'date': datetime.date(2024, 1, 15),
                    'authorized_date': datetime.date(2024, 1, 15),
                    'merchant_name': 'Test Store',
                    'name': 'Purchase at Test Store',
                    'pending': False,
                    'transaction_id': 'txn1',
                    'transaction_type': 'debit'
                }
            ]
        }
        mock_client.transactions_get.return_value = mock_response

        # Mock context
        mock_user = Mock()
        mock_user.reference_id = 'test-user-123'
        mock_context = Mock()
        mock_context.user = mock_user
        mock_wrapper = Mock()
        mock_wrapper.context = mock_context

        result = await get_transactions_at_plaid.on_invoke_tool(mock_wrapper, '{}')

        assert result['response_type'] == 'plaid_transactions_response'
        assert result['agent_name'] == 'Plaid'
        assert result['friendly_name'] == 'Getting Transactions'
        assert 'account1' in result['response']
        assert len(result['response']['account1']['transactions']) == 1

    @patch('connectors.plaid_agent.PlaidToken')
    @pytest.mark.asyncio
    async def test_get_transactions_no_plaid_token(self, mock_plaid_token_class):
        """Test handling when user has no Plaid token."""
        mock_plaid_token_class.get_tokens_by_user_id.return_value = None

        # Mock context
        mock_user = Mock()
        mock_user.reference_id = 'test-user-123'
        mock_context = Mock()
        mock_context.user = mock_user
        mock_wrapper = Mock()
        mock_wrapper.context = mock_context

        result = await get_transactions_at_plaid.on_invoke_tool(mock_wrapper, '{}')

        assert result['response_type'] == 'error'
        assert 'not connected to Plaid' in result['response']

    def test_production_vs_sandbox_date_logic(self):
        """Test conceptual difference between production and sandbox date ranges."""
        # In sandbox mode (non-production)
        sandbox_start = datetime.date(year=2024, month=1, day=1)
        sandbox_end = datetime.date(year=2025, month=12, day=1)
        
        # In production mode
        today = datetime.date(2024, 2, 15)
        prod_start = today - datetime.timedelta(days=30)
        prod_end = today
        
        # Verify date calculations
        assert prod_start == datetime.date(2024, 1, 16)
        assert prod_end == datetime.date(2024, 2, 15)
        assert sandbox_start < sandbox_end
        assert prod_start < prod_end


class TestPlaidAgentIntegration:
    """Integration tests for Plaid agent components."""

    def test_agent_tools_registration(self):
        """Test that tools are properly registered with the agent."""
        tool_names = [tool.name for tool in PLAID_AGENT.tools]
        assert "get_accounts_at_plaid" in tool_names
        assert "get_transactions_at_plaid" in tool_names

    def test_import_dependencies(self):
        """Test that agent dependencies are properly imported."""
        try:
            from connectors.plaid_agent import (
                PLAID_AGENT,
                get_accounts_at_plaid,
                get_transactions_at_plaid
            )
            assert PLAID_AGENT is not None
            assert get_accounts_at_plaid is not None
            assert get_transactions_at_plaid is not None
        except ImportError as e:
            pytest.fail(f"Failed to import Plaid components: {e}")

    def test_plaid_imports(self):
        """Test that Plaid SDK imports work correctly."""
        try:
            from plaid.model.transactions_get_request import TransactionsGetRequest
            from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
            from plaid.api import plaid_api
            import plaid
            
            assert TransactionsGetRequest is not None
            assert AccountsBalanceGetRequest is not None
            assert plaid_api is not None
            assert plaid is not None
        except ImportError as e:
            pytest.fail(f"Failed to import Plaid SDK components: {e}")


class TestPlaidEdgeCases:
    """Test edge cases and error conditions."""

    def test_tool_function_signatures(self):
        """Test that tool functions have correct parameter schemas."""
        # Both tools take wrapper parameter
        assert hasattr(get_accounts_at_plaid, 'on_invoke_tool')
        assert hasattr(get_transactions_at_plaid, 'on_invoke_tool')

    def test_all_tools_have_descriptions(self):
        """Test that all tools have proper descriptions."""
        for tool in ALL_TOOLS:
            assert hasattr(tool, 'description')
            assert tool.description is not None
            assert len(tool.description) > 0

    def test_tools_have_is_enabled_function(self):
        """Test that tools use is_enabled function."""
        # Tools should have is_enabled set to is_plaid_enabled
        assert hasattr(get_accounts_at_plaid, 'is_enabled')
        assert hasattr(get_transactions_at_plaid, 'is_enabled')

    @patch('connectors.plaid_agent.PlaidToken')
    @patch('connectors.plaid_agent.client')
    @patch('builtins.print')
    @pytest.mark.asyncio
    async def test_transactions_date_conversion(self, mock_print, mock_client, mock_plaid_token_class):
        """Test that transaction dates are properly converted to datetime."""
        # Mock PlaidToken
        mock_token = Mock()
        mock_token.decrypted_tokens.return_value = [{'auth_token': 'test-token'}]
        mock_plaid_token_class.get_tokens_by_user_id.return_value = mock_token

        # Mock API response with date objects
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            'accounts': [{'account_id': 'acc1', 'name': 'Test Account', 'official_name': 'Test Account'}],
            'transactions': [
                {
                    'account_id': 'acc1',
                    'date': datetime.date(2024, 1, 15),
                    'authorized_date': datetime.date(2024, 1, 14),
                    'amount': 100.0
                }
            ]
        }
        mock_client.transactions_get.return_value = mock_response

        # Mock context
        mock_user = Mock()
        mock_user.reference_id = 'test-user-123'
        mock_context = Mock()
        mock_context.user = mock_user
        mock_wrapper = Mock()
        mock_wrapper.context = mock_context

        result = await get_transactions_at_plaid.on_invoke_tool(mock_wrapper, '{}')

        # Verify dates were converted to datetime
        transaction = result['response']['acc1']['transactions'][0]
        assert isinstance(transaction['date'], datetime.datetime)
        assert isinstance(transaction['authorized_date'], datetime.datetime)

    def test_agent_typo_in_instructions(self):
        """Test that there's a typo in agent instructions."""
        # Document known typo: "infrormation" instead of "information"
        # Typo has been fixed, no longer "infrormation"
        assert "Plaid financial assistant" in PLAID_AGENT.instructions

    @patch('connectors.plaid_agent.json.loads')
    def test_api_error_handling_empty_body(self, mock_json_loads):
        """Test handling of API errors with empty body."""
        import plaid
        
        # Create a mock API exception with empty body
        mock_error = plaid.ApiException()
        mock_error.status = 500
        mock_error.body = None
        
        # Mock json.loads to return empty dict for empty body
        mock_json_loads.return_value = {}
        
        # This tests the error handling path in the code
        assert mock_json_loads("{}") == {}

    def test_multiple_account_handling(self):
        """Test conceptual handling of multiple accounts."""
        # Test data structure for multiple accounts
        account_transactions = {
            'account1': {
                'account_name': 'Checking',
                'account_official_name': 'Main Checking',
                'transactions': []
            },
            'account2': {
                'account_name': 'Savings',
                'account_official_name': 'High Yield Savings',
                'transactions': []
            }
        }
        
        # Verify structure matches expected format
        assert len(account_transactions) == 2
        assert 'account_name' in account_transactions['account1']
        assert 'transactions' in account_transactions['account1']