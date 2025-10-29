"""Tests for the Evernote router module."""

import pytest
from unittest.mock import Mock, patch

from routers.evernote import EVERNOTE_ROUTER


class TestEvernoteRouter:
    """Test the Evernote router configuration."""
    
    def test_router_prefix(self):
        """Test that the router has the correct prefix."""
        assert EVERNOTE_ROUTER.prefix == '/auth/evernote'
    
    def test_router_has_no_active_routes(self):
        """Test that all routes are currently commented out."""
        # Since all routes are commented out, the router should have no routes
        assert len(EVERNOTE_ROUTER.routes) == 0
    
    def test_settings_import(self):
        """Test that Settings is imported correctly."""
        from routers.evernote import SETTINGS
        assert SETTINGS is not None


# Note: The Evernote integration is currently disabled (all routes are commented out).
# These tests verify the basic module structure and imports.
# When the integration is re-enabled, comprehensive tests should be added for:
# - The /authorize endpoint with token validation
# - The /callback endpoint with OAuth verification
# - Error handling for invalid tokens
# - Integration with EvernoteToken Firebase model
# - Proper redirect responses