"""Authentication service for handling user validation and token verification."""

import logging
from typing import Tuple, Optional

from fastapi import HTTPException, WebSocket

try:
    from utils.imports import get_auth_service, get_settings
except ImportError:
    from ..utils.imports import get_auth_service, get_settings

try:
    from firebase.models.user import User
except ImportError:
    from ..firebase.models.user import User

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Custom exception for authentication errors."""
    pass


class AuthService:
    """Service for handling user authentication and validation."""

    def __init__(self, production: bool = False):
        self.production = production
        self.validate_google_token = get_auth_service()
        settings = get_settings()
        self.settings = settings()

    def validate_user_token(self, token: Optional[str]) -> Tuple[bool, User, bool]:
        """
        Validate user token and return validation result.

        Args:
            token: The authentication token to validate

        Returns:
            Tuple of (is_valid, user_object, is_anonymous)

        Raises:
            AuthenticationError: If authentication fails
        """
        if not token:
            raise AuthenticationError("No token provided")

        try:
            valid, user, user_anonymous = self.validate_google_token(token)

            if user is None:
                raise AuthenticationError("Invalid token - no user found")

            if self.production and user_anonymous:
                raise AuthenticationError(
                    "Anonymous users not allowed in production")

            if not valid:
                raise AuthenticationError("Token validation failed")

            if self.production and not user.check_terms_of_service_accepted():
                raise AuthenticationError("Terms of service not accepted")

            return valid, user, user_anonymous

        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise AuthenticationError(f"Authentication failed: {str(e)}")

    async def authenticate_websocket(self, websocket: WebSocket, token: str) -> Tuple[any, bool]:
        """
        Authenticate a WebSocket connection.

        Args:
            websocket: The WebSocket connection
            token: The authentication token

        Returns:
            Tuple of (user_object, is_anonymous)

        Raises:
            Will close the WebSocket connection on authentication failure
        """
        try:
            valid, user, user_anonymous = self.validate_user_token(token)
            logger.info(
                f"WebSocket authenticated for user: {user.reference_id}")
            return user, user_anonymous

        except AuthenticationError as e:
            logger.warning(f"WebSocket authentication failed: {e}")
            await websocket.close(code=1008, reason=str(e))
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error during WebSocket authentication: {e}")
            await websocket.close(code=1008, reason="Authentication failed")
            raise AuthenticationError("Unexpected authentication error") from e

    def authenticate_http_request(self, token: Optional[str]) -> Tuple[any, bool]:
        """
        Authenticate an HTTP request.

        Args:
            token: The authentication token

        Returns:
            Tuple of (user_object, is_anonymous)

        Raises:
            HTTPException: If authentication fails
        """
        try:
            valid, user, user_anonymous = self.validate_user_token(token)
            return user, user_anonymous

        except AuthenticationError as e:
            logger.warning(f"HTTP authentication failed: {e}")
            raise HTTPException(status_code=401, detail=str(e))
        except Exception as e:
            logger.error(f"Unexpected error during HTTP authentication: {e}")
            raise HTTPException(
                status_code=500, detail="Authentication service error")

    def get_user_integrations(self, user: any) -> dict:
        """
        Get user integration settings.

        Args:
            user: The user object

        Returns:
            Dictionary of integration settings
        """
        return {
            "google": user.connected_to_google,
            "plaid": user.connected_to_plaid,
        }
        
