"""Firebase authentication and authorization module.

This module handles Firebase ID token validation and user authentication
for the ODAI API. It provides functions to verify Firebase tokens and
retrieve associated user information.
"""

from firebase_admin.auth import verify_id_token
import os
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

try:
    from firebase import User
except ImportError:
    from .firebase import User

try:
    from connectors.utils.segment import identify_user
except ImportError:
    from .connectors.utils.segment import identify_user

if 'PRODUCTION' in os.environ:
    PRODUCTION = True
else:
    PRODUCTION = False


def auth_firebase_user(auth_header: str):
    """Authenticate a Firebase user using an ID token.
    
    Args:
        auth_header: Firebase ID token string
        
    Returns:
        str: User ID (uid) from the verified token
        
    Raises:
        HTTPException: 401 error if token is invalid
    """
    results = verify_id_token(auth_header)
    if 'uid' in results:
        print(results['uid'])
        return results['uid']
    else:
        raise HTTPException(
            status_code=401
            , detail="Invalid authentication token")

def validate_google_token(token: str) -> tuple[bool, User | None, bool]:
    """Validate a Google/Firebase ID token and retrieve user information.
    
    Args:
        token: Firebase ID token string
        
    Returns:
        tuple: (is_valid, user_object, is_anonymous)
            - is_valid: True if token is valid
            - user_object: User object if found, None otherwise
            - is_anonymous: True if user is anonymous
    """
    try:
        results = verify_id_token(token)
        if 'uid' in results:
            # print(results)
            logger.info(f"Results: {results}")
            user_id = results['uid']
            logger.info(f"User ID: {user_id}")
            anonymous = results['firebase']['sign_in_provider'] == 'anonymous'
            logger.info(f"Anonymous: {anonymous}")
            user = User.get_user_by_id(user_id)
            logger.info(f"User: {user}")
            if user is not None:
                identify_user(user)
            return True, user, anonymous
        else:
            return False, None, True
        # g.user = firebase_db.User.get_by_id(results['uid'])
        # if g.user is None:
        # abort(401)
        # if hasattr(g.user, 'archived'):
        # if g.user.archived:
        #     abort(404)
    except Exception as e:
        logger.error(f"Error validating Google token: {e}")
        return False, None, True