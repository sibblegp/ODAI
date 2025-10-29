"""API service for handling non-chat related API endpoints."""

import logging
from typing import Optional

try:
    from utils.imports import get_firebase_models, get_segment_tracking
    from services.auth_service import AuthService
except ImportError:
    from ..utils.imports import get_firebase_models, get_segment_tracking
    from ..services.auth_service import AuthService

logger = logging.getLogger(__name__)


class APIService:
    """Service for managing non-chat API operations."""

    def __init__(self):
        # Import Firebase models
        firebase_models = get_firebase_models()
        self.Waitlist = firebase_models[2]  # Waitlist is the 3rd element
        self.GoogleAccessRequest = firebase_models[4]  # GoogleAccessRequest is the 5th element
        
        # Import Google token model separately for reset functionality
        try:
            from firebase.models.google_token import GoogleToken
            from firebase.models.plaid_token import PlaidToken
            self.GoogleToken = GoogleToken
            self.PlaidToken = PlaidToken
        except ImportError:
            from ..firebase.models.google_token import GoogleToken
            from ..firebase.models.plaid_token import PlaidToken
            self.GoogleToken = GoogleToken
            self.PlaidToken = PlaidToken

        # Import segment tracking functions
        segment_tracking = get_segment_tracking()
        self.track_google_access_request = segment_tracking[6]  # track_google_access_request is the 7th element

    def add_email_to_waitlist(self, email: str) -> None:
        """
        Add an email to the waitlist.

        Args:
            email: The email address to add
        """
        try:
            self.Waitlist.add_email(email)
            logger.info(f"Added email to waitlist: {email}")
        except Exception as e:
            logger.error(f"Error adding email to waitlist: {e}")
            raise
        
    def request_google_access(self, production: bool, authentication: str, email: str) -> dict:
        """
        Request access to Google services.
        
        Args:
            production: Whether running in production mode
            authentication: The authentication token
            email: The email address requesting access
            
        Returns:
            Dictionary with status of the request
        """
        auth_service = AuthService(production)
        valid, user, user_anonymous = auth_service.validate_user_token(authentication)
        try:
            self.GoogleAccessRequest.create_request(user, email)
            self.track_google_access_request(user, email)
            logger.info(f"Requested Google access for {email}")
        except Exception as e:
            logger.error(f"Error requesting Google access: {e}")
            raise
        return {'status': 'success'}
    
    def reset_google_tokens(self, authorization: str) -> bool:
        """
        Reset Google tokens for a user.
        
        Args:
            authorization: The authorization token
            
        Returns:
            True if tokens were reset successfully, False otherwise
        """
        try:
            auth_service = AuthService(False)
            valid, user, user_anonymous = auth_service.validate_user_token(authorization)
            if user is not None:
                user.disconnect_from_google()
                self.GoogleToken.reset_tokens(user.reference_id)
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"Error resetting Google tokens: {e}")
            raise
        
    def reset_plaid_tokens(self, authorization: str) -> bool:
        """
        Reset Plaid tokens for a user.
        
        Args:
            authorization: The authorization token
            
        Returns:
            True if tokens were reset successfully, False otherwise
        """
        try:
            auth_service = AuthService(False)
            valid, user, user_anonymous = auth_service.validate_user_token(authorization)
            if user is not None:
                user.disconnect_from_plaid()
                self.PlaidToken.reset_tokens(user.reference_id)
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"Error resetting Plaid tokens: {e}")
            raise