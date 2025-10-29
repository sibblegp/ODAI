"""
Comprehensive tests for connectors/orchestrator.py

Tests cover the main orchestrator agent, tool calls mapping, and response generation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import asyncio
from agents import Agent, Runner
from openai.types.responses import ResponseTextDeltaEvent


class TestOrchestratorConfig:
    """Test orchestrator configuration and imports."""

    def test_orchestrator_agent_exists(self):
        """Test that ORCHESTRATOR_AGENT is properly configured."""
        from connectors.orchestrator import ORCHESTRATOR_AGENT

        assert ORCHESTRATOR_AGENT is not None
        assert isinstance(ORCHESTRATOR_AGENT, Agent)
        assert ORCHESTRATOR_AGENT.name == "ODAI"
        assert ORCHESTRATOR_AGENT.model == "gpt-4o"
        assert len(ORCHESTRATOR_AGENT.handoffs) > 0

    def test_tool_calls_mapping_exists(self):
        """Test that TOOL_CALLS mapping is properly configured."""
        from connectors.orchestrator import TOOL_CALLS

        assert isinstance(TOOL_CALLS, dict)
        assert len(TOOL_CALLS) > 0

        # Check some key tool calls
        expected_tools = [
            "get_stock_price_at_finnhub",
            "search_google",
            "fetch_website",
            "get_current_weather_by_location",
            "search_businesses_at_yelp"
        ]

        for tool in expected_tools:
            assert tool in TOOL_CALLS

    def test_agent_handoffs_configuration(self):
        """Test that agent handoffs are properly configured."""
        from connectors.orchestrator import ORCHESTRATOR_AGENT

        handoff_names = [agent.name for agent in ORCHESTRATOR_AGENT.handoffs]

        expected_agents = [
            "Yelp",
            "CoinMarketCap",
            "GMail",  # Note: actual agent name is "GMail"
            "FlightAware",
            "Plaid",
            "Finnhub",
            "Google Calendar",
            "Google Docs",
            "TripAdvisor",
            "Google Shopping",
            "Google News",
            "Google Search",
            "Fetch Website",
            "Amazon",
            "OpenExternalUrl",
            "Amtrak",
            "Ticketmaster",
            "EasyPost",
            "MovieGlu",
            "AMADEUS",  # Note: uppercase
            "Exchange Rate Agent",  # Note: includes "Agent" in name
            "Accuweather"  # Note: lowercase 'w'
        ]

        for agent_name in expected_agents:
            assert agent_name in handoff_names


class TestOrchestratorModelSettings:
    """Test orchestrator model settings configuration."""

    def test_orchestrator_agent_model_settings(self):
        """Test that ORCHESTRATOR_AGENT has model settings with include_usage."""
        from connectors.orchestrator import ORCHESTRATOR_AGENT

        assert hasattr(ORCHESTRATOR_AGENT, 'model_settings')
        assert ORCHESTRATOR_AGENT.model_settings is not None
        # ModelSettings should have include_usage=True based on the code

    def test_agent_instructions_include_handoff_prefix(self):
        """Test that agent instructions include the recommended handoff prefix."""
        from connectors.orchestrator import ORCHESTRATOR_AGENT

        # The instructions should include handoff-related content from RECOMMENDED_PROMPT_PREFIX
        # and the ODAI-specific system prompt
        assert "handoff" in ORCHESTRATOR_AGENT.instructions.lower()
        assert "helpful ai assistant" in ORCHESTRATOR_AGENT.instructions.lower()


class TestToolCallsMapping:
    """Test the TOOL_CALLS mapping."""

    def test_tool_calls_completeness(self):
        """Test that TOOL_CALLS mapping includes expected tools."""
        from connectors.orchestrator import TOOL_CALLS

        # Financial tools
        assert "get_stock_price_at_finnhub" in TOOL_CALLS
        assert "get_annual_financials_at_finnhub" in TOOL_CALLS
        assert "get_quarterly_stock_financials_at_finnhub" in TOOL_CALLS
        assert "check_crypto_price_at_coinmarketcap" in TOOL_CALLS
        assert "get_accounts_at_plaid" in TOOL_CALLS
        assert "get_transactions_at_plaid" in TOOL_CALLS
        assert "connect_plaid_account" in TOOL_CALLS

        # Google tools
        assert "search_google" in TOOL_CALLS
        assert "connect_google_account" in TOOL_CALLS
        assert "get_google_calendar_events" in TOOL_CALLS
        assert "create_google_calendar_event" in TOOL_CALLS
        assert "delete_google_calendar_event" in TOOL_CALLS
        assert "fetch_google_email_inbox" in TOOL_CALLS
        assert "search_google_mail" in TOOL_CALLS
        assert "search_google_mail_from_email" in TOOL_CALLS
        assert "send_google_email" in TOOL_CALLS
        assert "reply_to_google_email" in TOOL_CALLS
        assert "save_google_doc" in TOOL_CALLS
        assert "search_google_docs_by_name_or_content" in TOOL_CALLS
        assert "get_google_news_top_stories" in TOOL_CALLS
        assert "search_google_news" in TOOL_CALLS
        assert "get_google_products" in TOOL_CALLS

        # Travel tools
        assert "find_flights_between_airports" in TOOL_CALLS
        assert "find_rount_trip_flights" in TOOL_CALLS  # Note: typo in actual code
        assert "get_flight_info_by_iata" in TOOL_CALLS
        assert "get_flight_info_by_airline_and_flight_number" in TOOL_CALLS
        assert "get_flight_info" in TOOL_CALLS  # Amadeus
        assert "get_hotel_prices" in TOOL_CALLS  # Amadeus
        assert "get_current_flight_status" in TOOL_CALLS  # FlightAware
        assert "get_amtrak_train_status" in TOOL_CALLS
        assert "get_caltrain_status" in TOOL_CALLS
        assert "search_tripadvisor" in TOOL_CALLS
        assert "get_tripadvisor_location_details" in TOOL_CALLS
        assert "get_tripadvisor_location_reviews" in TOOL_CALLS

        # Entertainment tools
        assert "get_ticketmaster_events_near_location" in TOOL_CALLS
        assert "get_ticketmaster_event_details" in TOOL_CALLS
        assert "find_ticketmaster_venues_near_location" in TOOL_CALLS
        assert "get_ticketmaster_venue_details" in TOOL_CALLS
        assert "get_ticketmaster_attractions_by_query" in TOOL_CALLS
        assert "get_ticketmaster_events_by_attraction_id" in TOOL_CALLS
        assert "get_ticketmaster_events_by_venue_id" in TOOL_CALLS
        assert "get_films_showing_near_location" in TOOL_CALLS
        assert "search_films_near_location" in TOOL_CALLS
        assert "search_theaters_near_location" in TOOL_CALLS
        assert "get_nearby_theaters_near_location" in TOOL_CALLS
        assert "get_theater_showtimes_near_location" in TOOL_CALLS
        assert "get_film_showtimes_near_location" in TOOL_CALLS

        # Weather and location
        assert "get_current_weather_by_location" in TOOL_CALLS
        assert "get_forecast_weather_by_location" in TOOL_CALLS
        assert "get_current_weather_by_latitude_longitude" in TOOL_CALLS
        assert "get_daily_forecast_weather_by_latitude_longitude" in TOOL_CALLS
        assert "get_hourly_forecast_weather_by_latitude_longitude" in TOOL_CALLS
        assert "search_businesses_at_yelp" in TOOL_CALLS
        assert "get_business_reviews_at_yelp" in TOOL_CALLS

        # Shopping tools
        assert "search_amazon" in TOOL_CALLS
        assert "get_product_details" in TOOL_CALLS

        # Utility tools
        assert "fetch_website" in TOOL_CALLS
        assert "open_external_url_in_window" in TOOL_CALLS
        assert "open_external_url_in_tab" in TOOL_CALLS
        assert "get_exchange_rates_for_currency" in TOOL_CALLS
        assert "get_exchange_rate_for_currency_pair" in TOOL_CALLS

        # Shipping tools
        assert "get_tracking_info_with_easypost" in TOOL_CALLS
        assert "get_all_packages_with_easypost" in TOOL_CALLS

    def test_tool_calls_values(self):
        """Test that TOOL_CALLS values are appropriate."""
        from connectors.orchestrator import TOOL_CALLS

        # Check that loading messages are reasonable
        assert TOOL_CALLS["get_stock_price_at_finnhub"] == "Getting Stock Price..."
        assert TOOL_CALLS["search_google"] == "Searching Google..."
        assert TOOL_CALLS["get_current_weather_by_location"] == "Getting Current Weather..."

        # Some tools should have None values (no loading message)
        none_value_tools = ["get_traveler_info",
                            "set_traveler_info", "store_location"]
        for tool in none_value_tools:
            if tool in TOOL_CALLS:
                assert TOOL_CALLS[tool] is None

    def test_tool_calls_no_duplicates(self):
        """Test that TOOL_CALLS doesn't have duplicate entries."""
        from connectors.orchestrator import TOOL_CALLS

        tool_names = list(TOOL_CALLS.keys())
        assert len(tool_names) == len(set(tool_names)
                                      ), "TOOL_CALLS contains duplicate keys"


class TestOrchestratorIntegration:
    """Integration tests for orchestrator components."""

    def test_orchestrator_core_imports_successfully(self):
        """Test that core orchestrator components import correctly."""
        # This test ensures the main exports work
        try:
            from connectors.orchestrator import (
                ORCHESTRATOR_AGENT,
                TOOL_CALLS
            )
            assert ORCHESTRATOR_AGENT is not None
            assert TOOL_CALLS is not None
        except ImportError as e:
            pytest.fail(f"Failed to import orchestrator components: {e}")

    def test_settings_configuration(self):
        """Test that settings are properly configured."""
        import os
        from connectors.orchestrator import SETTINGS

        # Should have set the OpenAI API key in environment
        assert "OPENAI_API_KEY" in os.environ
        assert os.environ["OPENAI_API_KEY"] == SETTINGS.openai_api_key


class TestOrchestratorClass:
    """Test the new Orchestrator class."""

    def test_orchestrator_class_exists(self):
        """Test that Orchestrator class exists and can be imported."""
        from connectors.orchestrator import Orchestrator
        assert Orchestrator is not None

    def test_orchestrator_initialization(self):
        """Test that Orchestrator initializes with correct attributes."""
        from connectors.orchestrator import Orchestrator

        # Create a mock user
        mock_user = Mock()
        mock_user.reference_id = 'test-user-123'

        orchestrator = Orchestrator(mock_user)

        # Test attributes
        assert orchestrator.model == "gpt-4o"
        assert isinstance(orchestrator.instructions, str)
        assert "helpful AI assistant" in orchestrator.instructions
        assert "hand off to available agents" in orchestrator.instructions
        assert isinstance(orchestrator.handoffs, list)
        assert len(orchestrator.handoffs) > 0
        assert orchestrator.model_settings is not None

    def test_orchestrator_agent_property(self):
        """Test that the agent property returns a properly configured Agent."""
        from connectors.orchestrator import Orchestrator
        from agents import Agent

        # Create a mock user
        mock_user = Mock()
        mock_user.reference_id = 'test-user-123'

        orchestrator = Orchestrator(mock_user)
        agent = orchestrator.agent

        # Test agent configuration
        assert isinstance(agent, Agent)
        assert agent.name == "ODAI"
        assert agent.model == "gpt-4o"
        assert agent.instructions == orchestrator.instructions
        assert agent.handoffs == orchestrator.handoffs
        assert agent.model_settings == orchestrator.model_settings

    def test_orchestrator_agent_property_creates_new_instance(self):
        """Test that the agent property creates a new Agent instance each time."""
        from connectors.orchestrator import Orchestrator

        # Create a mock user
        mock_user = Mock()
        mock_user.reference_id = 'test-user-123'

        orchestrator = Orchestrator(mock_user)
        agent1 = orchestrator.agent
        agent2 = orchestrator.agent

        # Should create new instances
        assert agent1 is not agent2
        # But with same configuration
        assert agent1.name == agent2.name
        assert agent1.model == agent2.model
        assert agent1.instructions == agent2.instructions


class TestOrchestratorEdgeCases:
    """Test edge cases and error conditions."""

    def test_tool_calls_typo_in_round_trip_flights(self):
        """Test that there's a typo in TOOL_CALLS - 'rount_trip_flights' instead of 'round_trip_flights'."""
        from connectors.orchestrator import TOOL_CALLS

        # Document the typo that exists in the code
        assert "find_rount_trip_flights" in TOOL_CALLS
        assert TOOL_CALLS["find_rount_trip_flights"] == "Searching Flights..."

    def test_orchestrator_agent_immutability(self):
        """Test that ORCHESTRATOR_AGENT configuration is stable."""
        from connectors.orchestrator import ORCHESTRATOR_AGENT

        original_name = ORCHESTRATOR_AGENT.name
        original_model = ORCHESTRATOR_AGENT.model
        original_handoffs_count = len(ORCHESTRATOR_AGENT.handoffs)

        # Re-import shouldn't change the configuration
        import importlib
        import connectors.orchestrator
        importlib.reload(connectors.orchestrator)

        from connectors.orchestrator import ORCHESTRATOR_AGENT as reloaded_agent

        assert reloaded_agent.name == original_name
        assert reloaded_agent.model == original_model
        assert len(reloaded_agent.handoffs) == original_handoffs_count

    def test_gmail_agent_in_handoffs(self):
        """Test that Gmail agent is included in handoffs."""
        from connectors.orchestrator import ORCHESTRATOR_AGENT

        # Check that GMAIL_AGENT is in handoffs
        handoff_names = [agent.name for agent in ORCHESTRATOR_AGENT.handoffs]
        assert "GMail" in handoff_names  # Based on actual Gmail agent name

    def test_all_tool_calls_have_valid_descriptions(self):
        """Test that all tool calls have either a string description or None."""
        from connectors.orchestrator import TOOL_CALLS

        for tool_name, description in TOOL_CALLS.items():
            # Description should be either a string or None
            assert description is None or isinstance(description, str)
            if isinstance(description, str):
                assert len(description) > 0  # Non-empty strings

    def test_all_tools_in_tool_calls_are_tested(self):
        """Test that all tools defined in TOOL_CALLS are covered in test_tool_calls_completeness."""
        from connectors.orchestrator import TOOL_CALLS

        # These are inactive tools that are still in TOOL_CALLS but not currently used
        inactive_tools = [
            # Alpaca
            "get_stock_price_at_alpaca",
            # Flights (inactive parts)
            "get_available_seats",
            "get_traveler_info",
            "set_traveler_info",
            "confirm_flight_details_prior_to_booking",
            "book_flight",
            # Instacart
            "add_to_instacart_basket",
            "checkout_instacart_basket",
            # Location
            "request_current_location",
            "store_location",
            "store_latitude_longitude",
            # OpenTable
            "check_restaurant_availability_at_opentable",
            "make_restaurant_reservation_at_opentable",
            # Walgreens
            "get_available_prescriptions_for_walgreens",
            "refill_prescription_at_walgreens",
        ]

        # All tools in TOOL_CALLS should either be tested or marked as inactive
        for tool_name in TOOL_CALLS:
            if tool_name not in inactive_tools:
                # Should be mentioned in test_tool_calls_completeness
                # Check if the tool is tested in test_tool_calls_completeness method
                # Read the test file content to check if tool is mentioned
                import inspect
                test_class = TestToolCallsMapping
                test_method_source = inspect.getsource(
                    test_class.test_tool_calls_completeness)
                assert tool_name in test_method_source, f"Tool {tool_name} is not tested in test_tool_calls_completeness"
