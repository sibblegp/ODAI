"""
Comprehensive tests for connectors/spotify.py

Tests cover the Spotify agent, its tools, and various edge cases.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from agents import Agent
from connectors.spotify import (
    SPOTIFY_AGENT,
    create_playlist_on_spotify,
    search_for_song,
    add_song_to_playlist
)


class TestSpotifyConfig:
    """Test Spotify agent configuration and setup."""

    def test_spotify_agent_exists(self):
        """Test that SPOTIFY_AGENT is properly configured."""
        assert SPOTIFY_AGENT is not None
        assert isinstance(SPOTIFY_AGENT, Agent)
        assert SPOTIFY_AGENT.name == "Spotify Agent"
        assert SPOTIFY_AGENT.model == "gpt-4o"
        assert len(SPOTIFY_AGENT.tools) == 3

    def test_agent_instructions_configured(self):
        """Test that agent instructions are properly set."""
        assert SPOTIFY_AGENT.instructions is not None
        assert "create playlists" in SPOTIFY_AGENT.instructions
        assert "search for songs" in SPOTIFY_AGENT.instructions
        assert "add songs to playlists" in SPOTIFY_AGENT.instructions

    def test_agent_handoff_description_configured(self):
        """Test that agent handoff description is properly set."""
        assert SPOTIFY_AGENT.handoff_description is not None
        assert "playlist" in SPOTIFY_AGENT.handoff_description
        assert "search for songs" in SPOTIFY_AGENT.handoff_description
        assert "Spotify" in SPOTIFY_AGENT.handoff_description

    def test_spotify_tools_exist(self):
        """Test that all Spotify tools exist."""
        assert create_playlist_on_spotify is not None
        assert search_for_song is not None
        assert add_song_to_playlist is not None


class TestCreatePlaylistTool:
    """Test the create_playlist_on_spotify tool."""

    @patch('connectors.spotify.requests.post')
    @pytest.mark.asyncio
    async def test_create_playlist_success(self, mock_post):
        """Test successful playlist creation."""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'id': 'test-playlist-id',
            'name': 'My Test Playlist',
            'description': 'Playlist created via API',
            'public': False,
            'owner': {'id': 'gsibble'}
        }
        mock_post.return_value = mock_response

        # Mock the tool context
        mock_ctx = Mock()

        result = await create_playlist_on_spotify.on_invoke_tool(
            mock_ctx,
            '{"playlist_name": "My Test Playlist"}'
        )

        # Verify API call was made correctly
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert "https://api.spotify.com/v1/users/gsibble/playlists" in args[0]
        assert "Authorization" in kwargs["headers"]
        assert kwargs["json"]["name"] == "My Test Playlist"
        assert kwargs["json"]["public"] is False

        # Verify response structure
        assert result['response_type'] == 'spotify_create_playlist'
        assert result['playlist_id'] == 'test-playlist-id'
        assert result['playlist_name'] == 'My Test Playlist'
        assert result['success'] is True

    @patch('connectors.spotify.requests.post')
    @pytest.mark.asyncio
    async def test_create_playlist_failure(self, mock_post):
        """Test playlist creation failure."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        mock_ctx = Mock()
        result = await create_playlist_on_spotify.on_invoke_tool(
            mock_ctx,
            '{"playlist_name": "Failed Playlist"}'
        )

        assert result['response_type'] == 'spotify_create_playlist'
        assert result['success'] is False
        assert 'error' in result
        assert '401' in result['error']

    @patch('connectors.spotify.requests.post')
    @pytest.mark.asyncio
    async def test_create_playlist_api_error(self, mock_post):
        """Test handling of API errors during playlist creation."""
        mock_post.side_effect = Exception("Connection Error")

        mock_ctx = Mock()
        result = await create_playlist_on_spotify.on_invoke_tool(
            mock_ctx,
            '{"playlist_name": "Error Playlist"}'
        )

        # The function tool framework catches exceptions and returns error message as string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()


class TestSearchForSongTool:
    """Test the search_for_song tool."""

    @patch('connectors.spotify.requests.get')
    @patch('builtins.print')
    @pytest.mark.asyncio
    async def test_search_for_song_success(self, mock_print, mock_get):
        """Test successful song search."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            'tracks': {
                'items': [
                    {
                        'id': 'song-id-1',
                        'name': 'Test Song',
                        'artists': [{'name': 'Test Artist'}],
                        'album': {'name': 'Test Album'},
                        'uri': 'spotify:track:song-id-1'
                    },
                    {
                        'id': 'song-id-2',
                        'name': 'Another Song',
                        'artists': [{'name': 'Another Artist'}],
                        'album': {'name': 'Another Album'},
                        'uri': 'spotify:track:song-id-2'
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        mock_ctx = Mock()
        result = await search_for_song.on_invoke_tool(
            mock_ctx,
            '{"query": "test song"}'
        )

        # Verify API call
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert "https://api.spotify.com/v1/search" in args[0]
        assert "q=test song" in args[0]
        assert "type=track" in args[0]
        assert "Authorization" in kwargs["headers"]

        # Verify print was called with first track
        mock_print.assert_called_once()

        # Verify response structure
        assert result['response_type'] == 'spotify_search_for_songs'
        assert result['songs']['id'] == 'song-id-1'
        assert result['songs']['name'] == 'Test Song'

    @patch('connectors.spotify.requests.get')
    @patch('builtins.print')
    @pytest.mark.asyncio
    async def test_search_for_song_empty_results(self, mock_print, mock_get):
        """Test search with no results."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'tracks': {
                'items': []
            }
        }
        mock_get.return_value = mock_response

        mock_ctx = Mock()
        result = await search_for_song.on_invoke_tool(
            mock_ctx,
            '{"query": "nonexistent song xyz123"}'
        )

        # Should raise IndexError which gets caught and returned as error string
        assert isinstance(result, str)
        assert "error occurred" in result.lower()

    @patch('connectors.spotify.requests.get')
    @pytest.mark.asyncio
    async def test_search_for_song_special_characters(self, mock_get):
        """Test search with special characters in query."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'tracks': {
                'items': [
                    {
                        'id': 'song-id-special',
                        'name': 'Song with émojis 🎵',
                        'artists': [{'name': 'Artist'}],
                        'album': {'name': 'Album'},
                        'uri': 'spotify:track:song-id-special'
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        mock_ctx = Mock()
        result = await search_for_song.on_invoke_tool(
            mock_ctx,
            '{"query": "song with émojis 🎵"}'
        )

        # Verify query is included in URL
        args, _ = mock_get.call_args
        # May be URL encoded
        assert "émojis" in args[0] or "%C3%A9mojis" in args[0]

    @patch('connectors.spotify.requests.get')
    @pytest.mark.asyncio
    async def test_search_for_song_api_error(self, mock_get):
        """Test handling of API errors during search."""
        mock_get.side_effect = Exception("API Error")

        mock_ctx = Mock()
        result = await search_for_song.on_invoke_tool(
            mock_ctx,
            '{"query": "test"}'
        )

        assert isinstance(result, str)
        assert "error occurred" in result.lower()


class TestAddSongToPlaylistTool:
    """Test the add_song_to_playlist tool."""

    @patch('connectors.spotify.requests.post')
    @pytest.mark.asyncio
    async def test_add_song_to_playlist_success(self, mock_post):
        """Test successful song addition to playlist."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        mock_ctx = Mock()
        result = await add_song_to_playlist.on_invoke_tool(
            mock_ctx,
            '{"playlist_id": "test-playlist-id", "song_uri": "spotify:track:song-id-1"}'
        )

        # Verify API call
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert "https://api.spotify.com/v1/playlists/test-playlist-id/tracks" in args[0]
        assert "Authorization" in kwargs["headers"]
        assert kwargs["json"]["uris"] == ["spotify:track:song-id-1"]

        # Verify response
        assert result['response_type'] == 'spotify_add_songs_to_playlist'
        assert result['success'] is True

    @patch('connectors.spotify.requests.post')
    @pytest.mark.asyncio
    async def test_add_song_to_playlist_failure(self, mock_post):
        """Test failed song addition to playlist."""
        mock_response = Mock()
        mock_response.status_code = 404  # Playlist not found
        mock_post.return_value = mock_response

        mock_ctx = Mock()
        result = await add_song_to_playlist.on_invoke_tool(
            mock_ctx,
            '{"playlist_id": "nonexistent-playlist", "song_uri": "spotify:track:song-id"}'
        )

        assert result['response_type'] == 'spotify_add_songs_to_playlist'
        assert result['success'] is False

    @patch('connectors.spotify.requests.post')
    @pytest.mark.asyncio
    async def test_add_song_to_playlist_api_error(self, mock_post):
        """Test handling of API errors when adding songs."""
        mock_post.side_effect = Exception("API Error")

        mock_ctx = Mock()
        result = await add_song_to_playlist.on_invoke_tool(
            mock_ctx,
            '{"playlist_id": "test-id", "song_uri": "spotify:track:test"}'
        )

        assert isinstance(result, str)
        assert "error occurred" in result.lower()


class TestSpotifyAgentIntegration:
    """Integration tests for Spotify agent components."""

    def test_agent_tools_registration(self):
        """Test that tools are properly registered with the agent."""
        tool_names = [tool.name for tool in SPOTIFY_AGENT.tools]
        assert "create_playlist_on_spotify" in tool_names
        assert "search_for_song" in tool_names
        assert "add_song_to_playlist" in tool_names

    def test_agent_model_configuration(self):
        """Test that agent uses correct model."""
        assert SPOTIFY_AGENT.model == "gpt-4o"

    def test_import_dependencies(self):
        """Test that agent dependencies are properly imported."""
        try:
            from connectors.spotify import (
                SPOTIFY_AGENT,
                create_playlist_on_spotify,
                search_for_song,
                add_song_to_playlist
            )
            assert SPOTIFY_AGENT is not None
            assert create_playlist_on_spotify is not None
            assert search_for_song is not None
            assert add_song_to_playlist is not None
        except ImportError as e:
            pytest.fail(f"Failed to import Spotify components: {e}")

    def test_tool_function_signatures(self):
        """Test that tool functions have correct parameter schemas."""
        # Test create_playlist parameters
        create_schema = create_playlist_on_spotify.params_json_schema
        assert "properties" in create_schema
        params = create_schema["properties"]
        assert "playlist_name" in params

        # Test search_for_song parameters
        search_schema = search_for_song.params_json_schema
        assert "properties" in search_schema
        params = search_schema["properties"]
        assert "query" in params

        # Test add_song_to_playlist parameters
        add_schema = add_song_to_playlist.params_json_schema
        assert "properties" in add_schema
        params = add_schema["properties"]
        assert "playlist_id" in params
        assert "song_uri" in params


class TestSpotifyEdgeCases:
    """Test edge cases and error conditions."""

    def test_agent_name_consistency(self):
        """Test that agent name is consistent."""
        assert SPOTIFY_AGENT.name == "Spotify Agent"

    def test_all_tools_have_descriptions(self):
        """Test that all tools have proper descriptions."""
        tools = [create_playlist_on_spotify,
                 search_for_song, add_song_to_playlist]

        for tool in tools:
            assert hasattr(tool, 'description')
            assert tool.description is not None
            assert len(tool.description) > 0

    @pytest.mark.asyncio
    async def test_missing_required_parameters(self):
        """Test tools with missing required parameters."""
        mock_ctx = Mock()

        # Test search_for_song without query
        result = await search_for_song.on_invoke_tool(
            mock_ctx,
            '{}'
        )
        assert isinstance(result, str)
        assert "error" in result.lower()

        # Test add_song_to_playlist without playlist_id
        result = await add_song_to_playlist.on_invoke_tool(
            mock_ctx,
            '{"song_uri": "spotify:track:test"}'
        )
        assert isinstance(result, str)
        assert "error" in result.lower()

    def test_hardcoded_user_id(self):
        """Test that there's a hardcoded user ID in create_playlist."""
        # This is a known issue - the URL uses hardcoded 'gsibble' username
        # We can verify this by checking the module source
        import connectors.spotify
        import inspect

        # Get the source of the entire module
        module_source = inspect.getsource(connectors.spotify)

        # Check that gsibble is hardcoded in the playlist URL
        assert "gsibble/playlists" in module_source  # Document the current behavior

    def test_access_token_hardcoded(self):
        """Test that access token is hardcoded (security issue)."""
        from connectors.spotify import ACCESS_TOKEN
        assert ACCESS_TOKEN is not None
        assert len(ACCESS_TOKEN) > 0
        # This is a security issue that should be addressed

    @patch('connectors.spotify.requests.post')
    @pytest.mark.asyncio
    async def test_single_song_uri_list(self, mock_post):
        """Test that add_song_to_playlist wraps single URI in list."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        mock_ctx = Mock()
        await add_song_to_playlist.on_invoke_tool(
            mock_ctx,
            '{"playlist_id": "test-id", "song_uri": "spotify:track:single"}'
        )

        # Verify single URI is wrapped in list
        _, kwargs = mock_post.call_args
        assert kwargs["json"]["uris"] == ["spotify:track:single"]

    def test_requests_library_import(self):
        """Test that requests library is properly imported."""
        import connectors.spotify
        assert hasattr(connectors.spotify, 'requests')

    def test_agent_instructions_mention_ai_generated(self):
        """Test that instructions mention AI-generated playlists."""
        instructions = SPOTIFY_AGENT.instructions
        assert "AI generated" in instructions or "own knowledge" in instructions
