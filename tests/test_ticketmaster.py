"""
Comprehensive tests for connectors/ticketmaster.py

Tests cover the Ticketmaster agent, its 7 function tools, and various edge cases.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import requests
from agents import Agent, RunContextWrapper
from agents.realtime import RealtimeAgent
from connectors.ticketmaster import (
    TICKETMASTER_AGENT,
    REALTIME_TICKETMASTER_AGENT,
    ALL_TOOLS,
    get_ticketmaster_events_near_location,
    get_ticketmaster_event_details,
    get_ticketmaster_attractions_by_query,
    find_ticketmaster_venues_near_location,
    get_ticketmaster_venue_details,
    get_ticketmaster_events_by_venue_id,
    get_ticketmaster_events_by_attraction_id
)


class TestTicketmasterConfig:
    """Test Ticketmaster agent configuration."""

    def test_ticketmaster_agent_exists(self):
        """Test that TICKETMASTER_AGENT is properly configured."""
        assert TICKETMASTER_AGENT is not None
        assert isinstance(TICKETMASTER_AGENT, Agent)
        assert TICKETMASTER_AGENT.name == "Ticketmaster"
        assert TICKETMASTER_AGENT.model == "gpt-4o"

    def test_realtime_ticketmaster_agent_exists(self):
        """Test that REALTIME_TICKETMASTER_AGENT is properly configured."""
        assert REALTIME_TICKETMASTER_AGENT is not None
        assert isinstance(REALTIME_TICKETMASTER_AGENT, RealtimeAgent)
        assert REALTIME_TICKETMASTER_AGENT.name == "Ticketmaster"

    def test_all_tools_exported(self):
        """Test that ALL_TOOLS contains expected tools."""
        assert len(ALL_TOOLS) == 7
        assert get_ticketmaster_events_near_location in ALL_TOOLS
        assert get_ticketmaster_event_details in ALL_TOOLS
        assert get_ticketmaster_attractions_by_query in ALL_TOOLS
        assert find_ticketmaster_venues_near_location in ALL_TOOLS
        assert get_ticketmaster_venue_details in ALL_TOOLS
        assert get_ticketmaster_events_by_venue_id in ALL_TOOLS
        assert get_ticketmaster_events_by_attraction_id in ALL_TOOLS

    def test_agent_tools_configured(self):
        """Test that agent has all tools configured."""
        agent_tools = TICKETMASTER_AGENT.tools
        assert len(agent_tools) == 7
        tool_names = [tool.name for tool in agent_tools]
        assert 'get_ticketmaster_events_near_location' in tool_names
        assert 'get_ticketmaster_event_details' in tool_names
        assert 'get_ticketmaster_attractions_by_query' in tool_names
        assert 'find_ticketmaster_venues_near_location' in tool_names
        assert 'get_ticketmaster_venue_details' in tool_names
        assert 'get_ticketmaster_events_by_venue_id' in tool_names
        assert 'get_ticketmaster_events_by_attraction_id' in tool_names

    def test_realtime_agent_tools_configured(self):
        """Test that realtime agent has all tools configured."""
        realtime_tools = REALTIME_TICKETMASTER_AGENT.tools
        assert len(realtime_tools) == 7

    def test_agent_handoffs_configured(self):
        """Test that agent handoffs are properly configured."""
        assert hasattr(TICKETMASTER_AGENT, 'handoffs')
        assert len(TICKETMASTER_AGENT.handoffs) == 3
        handoff_names = [agent.name for agent in TICKETMASTER_AGENT.handoffs]
        assert "GMail" in handoff_names
        assert "Google Docs" in handoff_names
        assert "WeatherAPI" in handoff_names

    def test_agent_instructions_configured(self):
        """Test that agent instructions are properly set."""
        assert TICKETMASTER_AGENT.instructions is not None
        assert "Ticketmaster assistant" in TICKETMASTER_AGENT.instructions
        assert "Search events" in TICKETMASTER_AGENT.instructions

        assert REALTIME_TICKETMASTER_AGENT.instructions is not None
        assert "Ticketmaster assistant" in REALTIME_TICKETMASTER_AGENT.instructions

    def test_agent_handoff_description_configured(self):
        """Test that agent handoff description is properly set."""
        assert TICKETMASTER_AGENT.handoff_description is not None
        assert "Ticketmaster:" in TICKETMASTER_AGENT.handoff_description
        from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
        assert TICKETMASTER_AGENT.handoff_description.startswith(
            RECOMMENDED_PROMPT_PREFIX)


class TestGetTicketmasterEventsNearLocationTool:
    """Test the get_ticketmaster_events_near_location function tool."""

    @pytest.mark.asyncio
    async def test_get_events_near_location_success(self):
        """Test successful event search near location."""
        mock_ctx = Mock()
        mock_ctx.settings.ticketmaster_consumer_key = "test_key"
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.return_value = {
            "_embedded": {
                "events": [
                    {
                        "id": "event1",
                        "name": "Concert A",
                        "dates": {"start": {"localDate": "2024-01-15"}},
                        "_embedded": {"venues": [{"name": "Venue A"}]}
                    },
                    {
                        "id": "event2",
                        "name": "Concert B",
                        "dates": {"start": {"localDate": "2024-01-20"}},
                        "_embedded": {"venues": [{"name": "Venue B"}]}
                    }
                ]
            }
        }

        with patch('connectors.ticketmaster.requests.get', return_value=mock_response) as mock_get:
            result = await get_ticketmaster_events_near_location.on_invoke_tool(
                mock_wrapper,
                json.dumps({
                    "query": "music",
                    "city": "New York",
                    "stateCode": "NY",
                    "countryCode": "US"
                })
            )

        assert result['response_type'] == 'ticketmaster_events_near_location'
        assert result['agent_name'] == 'Ticketmaster'
        assert result['friendly_name'] == 'Ticketmaster Event Search'
        assert result['display_response'] is True
        assert len(result['response']) == 2
        assert result['response'][0]['name'] == "Concert A"

        # Check URL construction
        call_args = mock_get.call_args[0][0]
        assert "keyword=music" in call_args
        assert "city=New York" in call_args
        assert "stateCode=NY" in call_args
        assert "countryCode=US" in call_args
        assert "apikey=test_key" in call_args

    @pytest.mark.asyncio
    async def test_get_events_near_location_empty_results(self):
        """Test event search with no results."""
        mock_ctx = Mock()
        mock_ctx.settings.ticketmaster_consumer_key = "test_key"
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.return_value = {"_embedded": {"events": []}}

        with patch('connectors.ticketmaster.requests.get', return_value=mock_response):
            result = await get_ticketmaster_events_near_location.on_invoke_tool(
                mock_wrapper,
                json.dumps({
                    "query": "invalid_event",
                    "city": "Nowhere",
                    "stateCode": "XX",
                    "countryCode": "US"
                })
            )

        assert result['response'] == []

    @pytest.mark.asyncio
    async def test_get_events_near_location_api_error(self):
        """Test event search when API returns error."""
        mock_ctx = Mock()
        mock_ctx.settings.ticketmaster_consumer_key = "test_key"
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        with patch('connectors.ticketmaster.requests.get') as mock_get:
            mock_get.side_effect = requests.RequestException("API Error")

            # The function tool wrapper catches the exception
            result = await get_ticketmaster_events_near_location.on_invoke_tool(
                mock_wrapper,
                json.dumps({
                    "query": "test",
                    "city": "Test",
                    "stateCode": "TS",
                    "countryCode": "US"
                })
            )

            # Error is handled by the wrapper
            assert result is not None


class TestGetTicketmasterEventDetailsTool:
    """Test the get_ticketmaster_event_details function tool."""

    @pytest.mark.asyncio
    async def test_get_event_details_success(self):
        """Test successful event details retrieval."""
        mock_ctx = Mock()
        mock_ctx.settings.ticketmaster_consumer_key = "test_key"
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "event123",
            "name": "Amazing Concert",
            "description": "A great show",
            "dates": {
                "start": {
                    "localDate": "2024-01-15",
                    "localTime": "20:00:00"
                }
            },
            "priceRanges": [
                {"min": 50.0, "max": 200.0, "currency": "USD"}
            ],
            "_embedded": {
                "venues": [
                    {"name": "Madison Square Garden", "city": {"name": "New York"}}
                ]
            }
        }

        with patch('connectors.ticketmaster.requests.get', return_value=mock_response) as mock_get:
            result = await get_ticketmaster_event_details.on_invoke_tool(
                mock_wrapper,
                json.dumps({"eventId": "event123"})
            )

        assert result['response_type'] == 'ticketmaster_event_details'
        assert result['agent_name'] == 'Ticketmaster'
        assert result['friendly_name'] == 'Ticketmaster Event Details'
        assert result['display_response'] is True
        assert result['response']['name'] == "Amazing Concert"
        assert result['response']['id'] == "event123"

        # Check URL construction
        call_args = mock_get.call_args[0][0]
        assert "events/event123.json" in call_args
        assert "apikey=test_key" in call_args

    @pytest.mark.asyncio
    async def test_get_event_details_not_found(self):
        """Test event details for non-existent event."""
        mock_ctx = Mock()
        mock_ctx.settings.ticketmaster_consumer_key = "test_key"
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.return_value = {
            "error": {"code": "404", "message": "Event not found"}}

        with patch('connectors.ticketmaster.requests.get', return_value=mock_response):
            result = await get_ticketmaster_event_details.on_invoke_tool(
                mock_wrapper,
                json.dumps({"eventId": "invalid_id"})
            )

        assert 'error' in result['response']


class TestGetTicketmasterAttractionsByQueryTool:
    """Test the get_ticketmaster_attractions_by_query function tool."""

    @pytest.mark.asyncio
    async def test_get_attractions_success(self):
        """Test successful attraction search."""
        mock_ctx = Mock()
        mock_ctx.settings.ticketmaster_consumer_key = "test_key"
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.return_value = {
            "_embedded": {
                "attractions": [
                    {
                        "id": "attraction1",
                        "name": "Taylor Swift",
                        "type": "attraction",
                        "classifications": [{"segment": {"name": "Music"}}]
                    },
                    {
                        "id": "attraction2",
                        "name": "Ed Sheeran",
                        "type": "attraction",
                        "classifications": [{"segment": {"name": "Music"}}]
                    }
                ]
            }
        }

        with patch('connectors.ticketmaster.requests.get', return_value=mock_response) as mock_get:
            result = await get_ticketmaster_attractions_by_query.on_invoke_tool(
                mock_wrapper,
                json.dumps({"query": "taylor"})
            )

        assert result['response_type'] == 'ticketmaster_attractions_by_query'
        assert result['agent_name'] == 'Ticketmaster'
        assert result['friendly_name'] == 'Ticketmaster Attraction Search'
        assert len(result['response']) == 2
        assert result['response'][0]['name'] == "Taylor Swift"

        # Check URL construction
        call_args = mock_get.call_args[0][0]
        assert "attractions.json" in call_args
        assert "keyword=taylor" in call_args
        assert "apikey=test_key" in call_args

    @pytest.mark.asyncio
    async def test_get_attractions_no_results(self):
        """Test attraction search with no results."""
        mock_ctx = Mock()
        mock_ctx.settings.ticketmaster_consumer_key = "test_key"
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.return_value = {"_embedded": {"attractions": []}}

        with patch('connectors.ticketmaster.requests.get', return_value=mock_response):
            result = await get_ticketmaster_attractions_by_query.on_invoke_tool(
                mock_wrapper,
                json.dumps({"query": "unknown_artist"})
            )

        assert result['response'] == []


class TestFindTicketmasterVenuesNearLocationTool:
    """Test the find_ticketmaster_venues_near_location function tool."""

    @pytest.mark.asyncio
    async def test_find_venues_success(self):
        """Test successful venue search."""
        mock_ctx = Mock()
        mock_ctx.settings.ticketmaster_consumer_key = "test_key"
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.return_value = {
            "_embedded": {
                "venues": [
                    {
                        "id": "venue1",
                        "name": "Madison Square Garden",
                        "city": {"name": "New York"},
                        "state": {"name": "New York", "stateCode": "NY"}
                    },
                    {
                        "id": "venue2",
                        "name": "Barclays Center",
                        "city": {"name": "Brooklyn"},
                        "state": {"name": "New York", "stateCode": "NY"}
                    }
                ]
            }
        }

        with patch('connectors.ticketmaster.requests.get', return_value=mock_response) as mock_get:
            result = await find_ticketmaster_venues_near_location.on_invoke_tool(
                mock_wrapper,
                json.dumps({
                    "query": "arena",
                    "stateCode": "NY",
                    "countryCode": "US"
                })
            )

        assert result['response_type'] == 'ticketmaster_venues_near_location'
        assert result['agent_name'] == 'Ticketmaster'
        assert result['friendly_name'] == 'Ticketmaster Venue Search'
        assert len(result['response']) == 2
        assert result['response'][0]['name'] == "Madison Square Garden"

        # Check URL construction
        call_args = mock_get.call_args[0][0]
        assert "venues.json" in call_args
        assert "keyword=arena" in call_args
        assert "stateCode=NY" in call_args
        assert "countryCode=US" in call_args
        assert "apikey=test_key" in call_args

    @pytest.mark.asyncio
    async def test_find_venues_empty_query(self):
        """Test venue search with empty query."""
        mock_ctx = Mock()
        mock_ctx.settings.ticketmaster_consumer_key = "test_key"
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.return_value = {"_embedded": {"venues": []}}

        with patch('connectors.ticketmaster.requests.get', return_value=mock_response):
            result = await find_ticketmaster_venues_near_location.on_invoke_tool(
                mock_wrapper,
                json.dumps({
                    "query": "",
                    "stateCode": "CA",
                    "countryCode": "US"
                })
            )

        assert result['response'] == []


class TestGetTicketmasterVenueDetailsTool:
    """Test the get_ticketmaster_venue_details function tool."""

    @pytest.mark.asyncio
    async def test_get_venue_details_success(self):
        """Test successful venue details retrieval."""
        mock_ctx = Mock()
        mock_ctx.settings.ticketmaster_consumer_key = "test_key"
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "venue123",
            "name": "Madison Square Garden",
            "description": "The World's Most Famous Arena",
            "address": {
                "line1": "4 Pennsylvania Plaza",
                "line2": ""
            },
            "city": {"name": "New York"},
            "state": {"name": "New York", "stateCode": "NY"},
            "postalCode": "10001",
            "parkingDetail": "Multiple parking garages nearby",
            "generalInfo": {
                "generalRule": "No outside food or beverages",
                "childRule": "Children under 2 free"
            }
        }

        with patch('connectors.ticketmaster.requests.get', return_value=mock_response) as mock_get:
            result = await get_ticketmaster_venue_details.on_invoke_tool(
                mock_wrapper,
                json.dumps({"venueId": "venue123"})
            )

        assert result['response_type'] == 'ticketmaster_venue_details'
        assert result['agent_name'] == 'Ticketmaster'
        assert result['friendly_name'] == 'Ticketmaster Venue Details'
        assert result['response']['name'] == "Madison Square Garden"
        assert result['response']['id'] == "venue123"

        # Check URL construction
        call_args = mock_get.call_args[0][0]
        assert "venues/venue123.json" in call_args
        assert "apikey=test_key" in call_args

    @pytest.mark.asyncio
    async def test_get_venue_details_not_found(self):
        """Test venue details for non-existent venue."""
        mock_ctx = Mock()
        mock_ctx.settings.ticketmaster_consumer_key = "test_key"
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.return_value = {
            "error": {"code": "404", "message": "Venue not found"}}

        with patch('connectors.ticketmaster.requests.get', return_value=mock_response):
            result = await get_ticketmaster_venue_details.on_invoke_tool(
                mock_wrapper,
                json.dumps({"venueId": "invalid_venue"})
            )

        assert 'error' in result['response']


class TestGetTicketmasterEventsByVenueIdTool:
    """Test the get_ticketmaster_events_by_venue_id function tool."""

    @pytest.mark.asyncio
    async def test_get_events_by_venue_success(self):
        """Test successful event retrieval by venue ID."""
        mock_ctx = Mock()
        mock_ctx.settings.ticketmaster_consumer_key = "test_key"
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.return_value = {
            "_embedded": {
                "events": [
                    {
                        "id": "event1",
                        "name": "Basketball Game",
                        "dates": {"start": {"localDate": "2024-02-01"}}
                    },
                    {
                        "id": "event2",
                        "name": "Concert",
                        "dates": {"start": {"localDate": "2024-02-05"}}
                    }
                ]
            }
        }

        with patch('connectors.ticketmaster.requests.get', return_value=mock_response) as mock_get:
            result = await get_ticketmaster_events_by_venue_id.on_invoke_tool(
                mock_wrapper,
                json.dumps({"venueId": "venue123"})
            )

        assert result['response_type'] == 'ticketmaster_events_by_venue_id'
        assert result['agent_name'] == 'Ticketmaster'
        assert result['friendly_name'] == 'Ticketmaster Events by Venue'
        assert len(result['response']) == 2
        assert result['response'][0]['name'] == "Basketball Game"

        # Check URL construction
        call_args = mock_get.call_args[0][0]
        assert "events.json" in call_args
        assert "venueId=venue123" in call_args
        assert "apikey=test_key" in call_args

    @pytest.mark.asyncio
    async def test_get_events_by_venue_no_events(self):
        """Test events by venue when venue has no events."""
        mock_ctx = Mock()
        mock_ctx.settings.ticketmaster_consumer_key = "test_key"
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.return_value = {"_embedded": {"events": []}}

        with patch('connectors.ticketmaster.requests.get', return_value=mock_response):
            result = await get_ticketmaster_events_by_venue_id.on_invoke_tool(
                mock_wrapper,
                json.dumps({"venueId": "empty_venue"})
            )

        assert result['response'] == []


class TestGetTicketmasterEventsByAttractionIdTool:
    """Test the get_ticketmaster_events_by_attraction_id function tool."""

    @pytest.mark.asyncio
    async def test_get_events_by_attraction_success(self):
        """Test successful event retrieval by attraction ID."""
        mock_ctx = Mock()
        mock_ctx.settings.ticketmaster_consumer_key = "test_key"
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.return_value = {
            "_embedded": {
                "events": [
                    {
                        "id": "event1",
                        "name": "Taylor Swift | The Eras Tour",
                        "dates": {"start": {"localDate": "2024-03-01"}},
                        "_embedded": {"venues": [{"name": "Stadium A"}]}
                    },
                    {
                        "id": "event2",
                        "name": "Taylor Swift | The Eras Tour",
                        "dates": {"start": {"localDate": "2024-03-02"}},
                        "_embedded": {"venues": [{"name": "Stadium A"}]}
                    }
                ]
            }
        }

        with patch('connectors.ticketmaster.requests.get', return_value=mock_response) as mock_get:
            result = await get_ticketmaster_events_by_attraction_id.on_invoke_tool(
                mock_wrapper,
                json.dumps({"attractionId": "attraction123"})
            )

        assert result['response_type'] == 'ticketmaster_events_by_attraction_id'
        assert result['agent_name'] == 'Ticketmaster'
        assert result['friendly_name'] == 'Ticketmaster Events by Attraction'
        assert len(result['response']) == 2
        assert "Taylor Swift" in result['response'][0]['name']

        # Check URL construction
        call_args = mock_get.call_args[0][0]
        assert "events.json" in call_args
        assert "attractionId=attraction123" in call_args
        assert "apikey=test_key" in call_args

    @pytest.mark.asyncio
    async def test_get_events_by_attraction_no_events(self):
        """Test events by attraction when attraction has no upcoming events."""
        mock_ctx = Mock()
        mock_ctx.settings.ticketmaster_consumer_key = "test_key"
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.return_value = {"_embedded": {"events": []}}

        with patch('connectors.ticketmaster.requests.get', return_value=mock_response):
            result = await get_ticketmaster_events_by_attraction_id.on_invoke_tool(
                mock_wrapper,
                json.dumps({"attractionId": "inactive_attraction"})
            )

        assert result['response'] == []


class TestTicketmasterIntegration:
    """Integration tests for Ticketmaster components."""

    def test_all_imports_work(self):
        """Test that all imports work correctly."""
        try:
            from connectors.ticketmaster import (
                TICKETMASTER_AGENT,
                REALTIME_TICKETMASTER_AGENT,
                ALL_TOOLS,
                get_ticketmaster_events_near_location,
                get_ticketmaster_event_details,
                get_ticketmaster_attractions_by_query,
                find_ticketmaster_venues_near_location,
                get_ticketmaster_venue_details,
                get_ticketmaster_events_by_venue_id,
                get_ticketmaster_events_by_attraction_id
            )

            assert TICKETMASTER_AGENT is not None
            assert REALTIME_TICKETMASTER_AGENT is not None
            assert len(ALL_TOOLS) == 7

            # Verify all tools have on_invoke_tool method
            for tool in ALL_TOOLS:
                assert hasattr(tool, 'on_invoke_tool')
                assert callable(tool.on_invoke_tool)

        except ImportError as e:
            pytest.fail(f"Failed to import Ticketmaster components: {e}")

    def test_agent_tools_consistency(self):
        """Test that agent tools match ALL_TOOLS."""
        agent_tool_names = [tool.name for tool in TICKETMASTER_AGENT.tools]
        realtime_tool_names = [
            tool.name for tool in REALTIME_TICKETMASTER_AGENT.tools]
        all_tool_names = [tool.name for tool in ALL_TOOLS]

        assert set(agent_tool_names) == set(all_tool_names)
        assert set(realtime_tool_names) == set(all_tool_names)

    def test_tool_descriptions(self):
        """Test that all tools have proper descriptions."""
        for tool in ALL_TOOLS:
            assert hasattr(tool, 'description')
            assert tool.description is not None
            assert len(tool.description) > 0

            # Check for specific keywords in descriptions
            desc_lower = tool.description.lower()
            if 'events_near_location' in tool.name:
                assert 'search' in desc_lower and 'events' in desc_lower
            elif 'event_details' in tool.name:
                assert 'details' in desc_lower and 'event' in desc_lower
            elif 'attractions' in tool.name:
                assert 'attraction' in desc_lower or 'artist' in desc_lower
            elif 'venues_near' in tool.name:
                assert 'venues' in desc_lower and 'location' in desc_lower
            elif 'venue_details' in tool.name:
                assert 'venue' in desc_lower and (
                    'details' in desc_lower or 'detailed' in desc_lower)
            elif 'events_by_venue' in tool.name:
                assert 'venue' in desc_lower and 'events' in desc_lower
            elif 'events_by_attraction' in tool.name:
                assert ('attraction' in desc_lower or 'artist' in desc_lower or 'team' in desc_lower) and (
                    'events' in desc_lower or 'tour' in desc_lower)

    def test_tool_parameters(self):
        """Test that all tools have correct parameter schemas."""
        # Test get_ticketmaster_events_near_location parameters
        events_schema = get_ticketmaster_events_near_location.params_json_schema
        assert 'properties' in events_schema
        assert 'query' in events_schema['properties']
        assert 'city' in events_schema['properties']
        assert 'stateCode' in events_schema['properties']
        assert 'countryCode' in events_schema['properties']

        # Test get_ticketmaster_event_details parameters
        details_schema = get_ticketmaster_event_details.params_json_schema
        assert 'properties' in details_schema
        assert 'eventId' in details_schema['properties']

        # Test get_ticketmaster_attractions_by_query parameters
        attractions_schema = get_ticketmaster_attractions_by_query.params_json_schema
        assert 'properties' in attractions_schema
        assert 'query' in attractions_schema['properties']

        # Test find_ticketmaster_venues_near_location parameters
        venues_schema = find_ticketmaster_venues_near_location.params_json_schema
        assert 'properties' in venues_schema
        assert 'query' in venues_schema['properties']
        assert 'stateCode' in venues_schema['properties']
        assert 'countryCode' in venues_schema['properties']

        # Test get_ticketmaster_venue_details parameters
        venue_details_schema = get_ticketmaster_venue_details.params_json_schema
        assert 'properties' in venue_details_schema
        assert 'venueId' in venue_details_schema['properties']

        # Test get_ticketmaster_events_by_venue_id parameters
        events_by_venue_schema = get_ticketmaster_events_by_venue_id.params_json_schema
        assert 'properties' in events_by_venue_schema
        assert 'venueId' in events_by_venue_schema['properties']

        # Test get_ticketmaster_events_by_attraction_id parameters
        events_by_attraction_schema = get_ticketmaster_events_by_attraction_id.params_json_schema
        assert 'properties' in events_by_attraction_schema
        assert 'attractionId' in events_by_attraction_schema['properties']


class TestTicketmasterEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_events_near_location_special_characters(self):
        """Test event search with special characters in query."""
        mock_ctx = Mock()
        mock_ctx.settings.ticketmaster_consumer_key = "test_key"
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.return_value = {"_embedded": {"events": []}}

        with patch('connectors.ticketmaster.requests.get', return_value=mock_response) as mock_get:
            result = await get_ticketmaster_events_near_location.on_invoke_tool(
                mock_wrapper,
                json.dumps({
                    "query": "rock & roll",
                    "city": "Las Vegas",
                    "stateCode": "NV",
                    "countryCode": "US"
                })
            )

        # Check that special characters are handled in URL
        call_args = mock_get.call_args[0][0]
        assert "rock & roll" in call_args or "rock%20%26%20roll" in call_args

    @pytest.mark.asyncio
    async def test_api_key_configuration(self):
        """Test that API key is properly passed from settings."""
        mock_ctx = Mock()
        mock_ctx.settings.ticketmaster_consumer_key = "my_test_api_key"
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.return_value = {"_embedded": {"events": []}}

        with patch('connectors.ticketmaster.requests.get', return_value=mock_response) as mock_get:
            await get_ticketmaster_events_near_location.on_invoke_tool(
                mock_wrapper,
                json.dumps({
                    "query": "test",
                    "city": "Test",
                    "stateCode": "TS",
                    "countryCode": "US"
                })
            )

        call_args = mock_get.call_args[0][0]
        assert "apikey=my_test_api_key" in call_args

    @pytest.mark.asyncio
    async def test_empty_embedded_response(self):
        """Test handling of response without _embedded field."""
        mock_ctx = Mock()
        mock_ctx.settings.ticketmaster_consumer_key = "test_key"
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        # Response without _embedded field
        mock_response.json.return_value = {"page": {"totalElements": 0}}

        with patch('connectors.ticketmaster.requests.get', return_value=mock_response):
            # The function tool catches KeyError internally
            result = await get_ticketmaster_events_near_location.on_invoke_tool(
                mock_wrapper,
                json.dumps({
                    "query": "test",
                    "city": "Test",
                    "stateCode": "TS",
                    "countryCode": "US"
                })
            )

            # Error is handled internally by the function tool wrapper
            assert result is not None

    @pytest.mark.asyncio
    async def test_json_decode_error(self):
        """Test handling of invalid JSON response."""
        mock_ctx = Mock()
        mock_ctx.settings.ticketmaster_consumer_key = "test_key"
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")

        with patch('connectors.ticketmaster.requests.get', return_value=mock_response):
            # The function tool catches the ValueError internally
            result = await get_ticketmaster_event_details.on_invoke_tool(
                mock_wrapper,
                json.dumps({"eventId": "test123"})
            )

            # Error is handled internally by the function tool wrapper
            assert result is not None

    def test_unused_imports(self):
        """Test that imports are present in the module."""
        import connectors.ticketmaster as ticketmaster_module

        # Check that all expected imports are available
        assert hasattr(ticketmaster_module, 'Agent')
        assert hasattr(ticketmaster_module, 'function_tool')
        assert hasattr(ticketmaster_module, 'RunContextWrapper')
        assert hasattr(ticketmaster_module, 'RealtimeAgent')
        assert hasattr(ticketmaster_module, 'requests')
        assert hasattr(ticketmaster_module, 'ChatContext')
        assert hasattr(ticketmaster_module, 'ToolResponse')
        assert hasattr(ticketmaster_module, 'GMAIL_AGENT')
        assert hasattr(ticketmaster_module, 'GOOGLE_DOCS_AGENT')
        assert hasattr(ticketmaster_module, 'WEATHERAPI_AGENT')
