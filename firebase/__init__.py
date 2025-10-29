"""
Firebase module - refactored from monolithic firebase.py into modular structure.

This module maintains backward compatibility with existing imports while providing
a clean, modular structure for Firebase models and configuration.

Usage:
    from firebase import Chat, User, GoogleToken  # Still works!
    from firebase.models import Chat, User        # Also works!
    from firebase.base import DB, client          # For direct access
"""

# Import base configuration and utilities
from .base import (
    SETTINGS,
    DB,
    client,
    FireStoreObject,
    track_google_connected,
    track_plaid_connected,
    track_evernote_connected,
    keys,
    access_secret_version,
    datetime,
    json,
    base64,
    uuid
)

# Import all model classes for backward compatibility
from .models import (
    Chat,
    User,
    Waitlist,
    FakeToken,
    GoogleToken,
    PlaidToken,
    TokenUsage,
    EvernoteToken,
    EasyPostTracker,
    Integration,
    UnhandledRequest,
    GoogleAccessRequest
)

# Export everything that was previously available in firebase.py
__all__ = [
    # Base configuration and utilities
    'SETTINGS',
    'DB',
    'client',
    'FireStoreObject',
    'track_google_connected',
    'track_plaid_connected',
    'track_evernote_connected',
    'keys',
    'access_secret_version',
    'datetime',
    'json',
    'base64',
    'uuid',
    # Model classes
    'Chat',
    'User',
    'Waitlist',
    'FakeToken',
    'GoogleToken',
    'PlaidToken',
    'TokenUsage',
    'EvernoteToken',
    'EasyPostTracker',
    'Integration',
    'UnhandledRequest',
    'GoogleAccessRequest'
]
