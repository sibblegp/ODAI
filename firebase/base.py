"""Base Firebase configuration and FireStoreObject class."""

import firebase_admin
from firebase_admin import credentials, firestore, messaging
from google.oauth2 import service_account
from openai import OpenAI
import json
import datetime
import base64
import os
import uuid

try:
    from connectors.utils.segment import track_google_connected, track_plaid_connected, track_evernote_connected, track_plaid_connected
except ImportError:
    from ..connectors.utils.segment import track_google_connected, track_plaid_connected, track_evernote_connected, track_plaid_connected

try:
    from config import Settings
except ImportError:
    from ..config import Settings

try:
    from connectors.utils import keys
except ImportError:
    from ..connectors.utils import keys

try:
    from connectors.utils.secrets import access_secret_version
except ImportError:
    from ..connectors.utils.secrets import access_secret_version

# Initialize settings
SETTINGS = Settings()

# Initialize Firebase
if not SETTINGS.production:
    cred = credentials.Certificate(
        'certificate_file.json')
else:
    json_credentials = access_secret_version(
        SETTINGS.project_id, 'firebase_credentials')
    if json_credentials is not None:
        cred = service_account.Credentials.from_service_account_info(
            json.loads(json_credentials))

firebase_admin.initialize_app(cred)

# Initialize Firestore client
DB = firestore.client()

# Initialize OpenAI client
client = OpenAI(api_key=SETTINGS.openai_api_key)


class FireStoreObject:
    """Base class for all Firestore objects with collection references."""

    users = DB.collection('users')
    waitlist = DB.collection('waitlist')
    chats = DB.collection('chats')
    google_tokens = DB.collection('google_tokens')
    plaid_tokens = DB.collection('plaid_tokens')
    token_usage = DB.collection('token_usage')
    evernote_tokens = DB.collection('evernote_tokens')
    easypost_trackers = DB.collection('easypost_trackers')
    odai_integrations = DB.collection('odai_integrations')
    unhandled_requests = DB.collection('unhandled_requests')
    google_access_requests = DB.collection('google_access_requests')


# Export commonly used objects for convenience
__all__ = [
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
    'uuid'
]
