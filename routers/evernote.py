from evernote.api.client import EvernoteClient
try:
    from config import Settings
except ImportError:
    from ..config import Settings

from fastapi import APIRouter
from fastapi.responses import RedirectResponse
try:
    from authorization import validate_google_token
except ImportError:
    from ..authorization import validate_google_token

try:
    from firebase import EvernoteToken
except ImportError:
    from ..firebase import EvernoteToken

SETTINGS = Settings()

EVERNOTE_ROUTER = APIRouter(prefix='/auth/evernote')

# EVERNOTE_CLIENT = EvernoteClient(
#     consumer_key=SETTINGS.evernote_consumer_key,
#     consumer_secret=SETTINGS.evernote_consumer_secret,
#     sandbox=False
# )

# @EVERNOTE_ROUTER.get('/authorize')
# def authorize(token: str, redirect_uri: str):
#     valid, user, user_anonymous = validate_google_token(token)
#     if not valid:
#         return {'error': 'Invalid token'}
#     if user_anonymous:
#         return {'error': 'Anonymous user'}
#     if user is None:
#         return {'error': 'User not found'}
#     request_token = EVERNOTE_CLIENT.get_request_token(redirect_uri)
#     oauth_token = request_token['oauth_token']
#     oauth_token_secret = request_token['oauth_token_secret']
#     EvernoteToken.start_evernote_token_request(user, oauth_token, oauth_token_secret)
#     auth_url = EVERNOTE_CLIENT.get_authorize_url(request_token)
#     return RedirectResponse(auth_url)

# @EVERNOTE_ROUTER.get('/callback')
# def callback(oauth_verifier: str, oauth_token: str):
#     request = EvernoteToken.retrieve_evernote_token_by_oauth_token(oauth_token)
#     access_token = EVERNOTE_CLIENT.get_access_token(oauth_token, request.oauth_token_secret, oauth_verifier)
#     EvernoteToken.save_evernote_token(request.user_id, access_token)
#     return {'access_token': access_token}