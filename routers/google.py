"""Google OAuth router module.

This module defines API endpoints for Google OAuth authentication flow,
including login initiation and OAuth callback handling.
"""

from fastapi import APIRouter
from fastapi.params import Header
from fastapi.responses import RedirectResponse
from fastapi import HTTPException
from fastapi import Request
from typing import Optional, Annotated
from urllib.parse import urlparse
from urllib.parse import parse_qs
try:
    from auth.google import get_authorization_url, exchange_code_for_credentials, get_user_info
except ImportError:
    from ..auth.google import get_authorization_url, exchange_code_for_credentials, get_user_info

try:
    from firebase import User, GoogleToken
except ImportError:
    from ..firebase import User, GoogleToken
try:
    from authorization import validate_google_token
except ImportError:
    from ..authorization import validate_google_token
try:
    from config import Settings
except ImportError:
    from ..config import Settings

SETTINGS = Settings()


GOOGLE_ROUTER = APIRouter(prefix='/auth/google')

@GOOGLE_ROUTER.get('/login')
async def google_login(token: Optional[str] = None, redirect_uri: Optional[str] = None, authorization: Annotated[str | None, Header()] = None):
    """Initiate Google OAuth login flow.
    
    Args:
        token: Firebase ID token for authentication
        redirect_uri: Optional custom redirect URI after OAuth completion
        authorization: Alternative header-based token authentication
        
    Returns:
        RedirectResponse to Google OAuth consent page
        
    Raises:
        HTTPException: If no valid token is provided or user is anonymous
    """
    if token is None and authorization is not None:
        token = authorization
    if token is None:
        return HTTPException(status_code=401, detail="Invalid token")
    if not redirect_uri:
        if not SETTINGS.production:
            redirect_uri = 'https://demo.odai.chat' if not SETTINGS.local else 'http://127.0.0.1:8000'
        else:
            redirect_uri = 'https://odai.com'
    # print(redirect_uri)
    
    if SETTINGS.local:
        user = User.get_user_by_id('lvX2TjNNcYYSroYeJ3LpRuUwwWs1')
    else:
        valid, user, user_anonymous = validate_google_token(token)
        if user:
            if not valid:
                print("Invalid user")
                return HTTPException(status_code=401, detail="Invalid token")
            if user_anonymous:
                return HTTPException(status_code=401, detail="Anonymous user")
        
            authorization_url, state = get_authorization_url()
            GoogleToken.create_token_request(user, state, redirect_uri)
            # print(state)
            return RedirectResponse(authorization_url)
        else:
            return HTTPException(status_code=401, detail="Invalid token")


@GOOGLE_ROUTER.get('/callback')
async def google_callback(request: Request):
    """Handle Google OAuth callback.
    
    Processes the OAuth callback from Google, exchanges the authorization code
    for credentials, and saves the token for the user.
    
    Args:
        request: FastAPI request object containing OAuth callback parameters
        
    Returns:
        RedirectResponse to the original redirect URI specified during login
    """
    authorization_url = str(request.url)
    parsed_url = urlparse(authorization_url)
    state = parse_qs(parsed_url.query)['state'][0]
    # print(state)
    credentials = exchange_code_for_credentials(authorization_url)
    user_info = get_user_info(credentials)
    saved_token = GoogleToken.save_or_add_token(state, credentials, user_info)
    return RedirectResponse(saved_token.redirect_uri)