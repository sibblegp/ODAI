"""Google OAuth authentication module.

This module handles Google OAuth 2.0 authentication flow, including:
- Generating authorization URLs
- Exchanging authorization codes for credentials
- Retrieving user information from Google APIs
"""

import os
import json
import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
try:
    from ..config import Settings
except:
    from config import Settings
    
try:
    from connectors.utils.secrets import access_secret_version
except ImportError:
    from ..connectors.utils.secrets import access_secret_version

SETTINGS = Settings()


if os.environ.get("PRODUCTION", "false") == "false":
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
    REDIRECT_URI = 'http://127.0.0.1:8000/auth/google/callback'
else:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
    REDIRECT_URI = 'https://api.odai.chat/auth/google/callback'

SCOPES= ['https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile',
                'https://www.googleapis.com/auth/calendar.events.owned',
                'https://www.googleapis.com/auth/gmail.send',
                'https://www.googleapis.com/auth/documents',
                'https://www.googleapis.com/auth/gmail.modify',
                'https://www.googleapis.com/auth/docs',
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/spreadsheets.readonly',
                'https://www.googleapis.com/auth/presentations.readonly']

def get_authorization_url():
    """Generate Google OAuth authorization URL.
    
    Returns:
        tuple: (authorization_url, state) - The authorization URL and state parameter
    
    Raises:
        ValueError: If Google OAuth credentials are not found in production
    """
    # Required, call the from_client_secrets_file method to retrieve the client ID from a
    # client_secret.json file. The client ID (from that file) and access scopes are required. (You can
    # also use the from_client_config method, which passes the client configuration as it originally
    # appeared in a client secrets file but doesn't access the file itself.)
    
    if not SETTINGS.production:
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file('credentials.json',
        scopes=SCOPES)
    else:
        json_credentials = access_secret_version(SETTINGS.project_id,'google_oauth_credentials')
        if json_credentials is None:
            raise ValueError('No Google OAuth credentials found')
        flow = google_auth_oauthlib.flow.Flow.from_client_config(json.loads(json_credentials), scopes=SCOPES)

    # Required, indicate where the API server will redirect the user after the user completes
    # the authorization flow. The redirect URI is required. The value must exactly
    # match one of the authorized redirect URIs for the OAuth 2.0 client, which you
    # configured in the API Console. If this value doesn't match an authorized URI,
    # you will get a 'redirect_uri_mismatch' error.
    # flow.redirect_uri = 'https://dev.api.odai.chat/auth/google/callback'
    if SETTINGS.local:
        flow.redirect_uri = 'http://127.0.0.1:8000/auth/google/callback'
    else:
        if not SETTINGS.production:
            flow.redirect_uri = 'https://dev.api.odai.com/auth/google/callback'
        else:
            flow.redirect_uri = 'https://api.odai.com/auth/google/callback'

    # Generate URL for request to Google's OAuth 2.0 server.
    # Use kwargs to set optional request parameters.
    authorization_url, state = flow.authorization_url(
        # Recommended, enable offline access so that you can refresh an access token without
        # re-prompting the user for permission. Recommended for web server apps.
        access_type='offline',
        # Optional, enable incremental authorization. Recommended as a best practice.
        
        # include_granted_scopes='true',
        
        # Optional, if your application knows which user is trying to authenticate, it can use this
        # parameter to provide a hint to the Google Authentication Server.
        # login_hint='hint@example.com',
        # Optional, set prompt to 'consent' will prompt the user for consent
        prompt='consent')
    return authorization_url, state

def exchange_code_for_credentials(auth_response):
    """Exchange authorization code for OAuth credentials.
    
    Args:
        auth_response: The authorization response URL containing the code
        
    Returns:
        dict: Dictionary containing OAuth credentials
        
    Raises:
        ValueError: If Google OAuth credentials are not found in production
    """
    
    if not SETTINGS.production:
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file('credentials.json',
        scopes=SCOPES)
    else:
        json_credentials = access_secret_version(SETTINGS.project_id,'google_oauth_credentials')
        if json_credentials is None:
            raise ValueError('No Google OAuth credentials found')
        flow = google_auth_oauthlib.flow.Flow.from_client_config(json.loads(json_credentials), scopes=SCOPES)

    # flow.redirect_uri = 'https://dev.api.odai.chat/auth/google/callback'
    if SETTINGS.local:
        flow.redirect_uri = 'http://127.0.0.1:8000/auth/google/callback'
    else:
        if not SETTINGS.production:
            flow.redirect_uri = 'https://dev.api.odai.com/auth/google/callback'
        else:
            flow.redirect_uri = 'https://api.odai.com/auth/google/callback'
    flow.fetch_token(authorization_response=auth_response)
    # print(flow.credentials)
    return credentials_to_dict(flow.credentials)

def get_user_info(credentials):
    """Retrieve user information from Google APIs.
    
    Args:
        credentials: Dictionary containing OAuth credentials
        
    Returns:
        dict: User information from Google
    """
    creds = Credentials.from_authorized_user_info(credentials)
    service = build('oauth2', 'v2', credentials=creds)
    user_info = service.userinfo().get().execute()
    return user_info

def credentials_to_dict(credentials):
    """Convert Google OAuth credentials object to dictionary.
    
    Args:
        credentials: Google OAuth credentials object
        
    Returns:
        dict: Dictionary representation of credentials
    """
    return {'token': credentials.token,
          'refresh_token': credentials.refresh_token,
          'token_uri': credentials.token_uri,
          'client_id': credentials.client_id,
          'client_secret': credentials.client_secret,
          'granted_scopes': credentials.granted_scopes}