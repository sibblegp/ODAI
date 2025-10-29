try:
    from firebase import GoogleToken
except ImportError:
    from ...firebase import GoogleToken
from google.oauth2.credentials import Credentials
try:
    from .responses import GoogleAccountNeededResponse
except ImportError:
    from ..utils.responses import GoogleAccountNeededResponse

def fetch_google_creds(user_id: str) -> Credentials | None:
    google_token = GoogleToken.get_tokens_by_user_id(user_id)
    if google_token is None:
        return None
    google_token_credentials = google_token.get_default_account_credentials()
    if google_token_credentials is None:
        return None
    
    creds = Credentials.from_authorized_user_info(google_token_credentials)
    return creds