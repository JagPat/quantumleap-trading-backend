"""
Authentication service - handles all broker authentication logic
"""
import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException
from kiteconnect import KiteConnect
from kiteconnect.exceptions import KiteException

from ..core.config import settings
from ..database.service import store_user_credentials
from .models import GenerateSessionResponse

logger = logging.getLogger(__name__)


class AuthService:
    """Service class for handling broker authentication"""
    
    def __init__(self):
        pass
    
    def clean_request_token(self, request_token: str) -> str:
        """
        Clean and validate request token from broker callback
        
        Args:
            request_token: Raw request token from broker callback
            
        Returns:
            Cleaned request token
            
        Raises:
            HTTPException: If token is invalid
        """
        clean_token = request_token.strip()
        
        # Handle URL format from Zerodha
        if clean_token.startswith('http') or '://' in clean_token:
            logger.error(f"Invalid request_token format - appears to be a URL: {clean_token}")
            
            import urllib.parse as urlparse
            parsed_url = urlparse.urlparse(clean_token)
            query_params = urlparse.parse_qs(parsed_url.query)
            
            # Check for request_token parameter first
            if 'request_token' in query_params:
                clean_token = query_params['request_token'][0]
                logger.info(f"Extracted token from request_token parameter: {clean_token}")
            # Check for sess_id parameter (Zerodha's format)
            elif 'sess_id' in query_params:
                clean_token = query_params['sess_id'][0]
                logger.info(f"Extracted token from sess_id parameter: {clean_token}")
            else:
                logger.error(f"Could not find token in URL parameters: {query_params}")
                raise HTTPException(status_code=400, detail="No valid token found in URL parameters")
        
        # Validate token format
        if not clean_token or len(clean_token) < 10 or not clean_token.replace('_', '').replace('-', '').isalnum():
            logger.error(f"Request token appears invalid or too short: {clean_token}")
            raise HTTPException(status_code=400, detail="Invalid request_token received from Zerodha")
        
        logger.info(f"Cleaned request_token: {clean_token}")
        return clean_token
    
    def generate_session(self, request_token: str, api_key: str, api_secret: str) -> GenerateSessionResponse:
        """
        Generate broker session using request token
        
        Args:
            request_token: Request token from broker OAuth flow
            api_key: Broker API key
            api_secret: Broker API secret
            
        Returns:
            GenerateSessionResponse with access token and user data
        """
        try:
            # Create KiteConnect instance
            kite = KiteConnect(api_key=api_key)
            
            # Generate session with request token
            session_data = kite.generate_session(request_token, api_secret=api_secret)
            access_token = session_data.get("access_token")
            
            if not access_token:
                return GenerateSessionResponse(
                    status="error", 
                    message="Failed to generate access token from Zerodha"
                )
            
            # Get user profile
            kite.set_access_token(access_token)
            profile = kite.profile()
            
            user_id = profile.get("user_id", "")
            user_name = profile.get("user_name", "")
            email = profile.get("email", "")
            
            if not user_id:
                return GenerateSessionResponse(
                    status="error", 
                    message="Unable to retrieve user ID from Zerodha profile"
                )
            
            # Store credentials in database
            success = store_user_credentials(
                user_id=user_id,
                api_key=api_key,
                api_secret=api_secret,
                access_token=access_token,
                user_name=user_name,
                email=email
            )
            
            if not success:
                return GenerateSessionResponse(
                    status="error", 
                    message="Failed to store user credentials securely"
                )
            
            logger.info(f"Successfully generated session for user: {user_id}")
            
            return GenerateSessionResponse(
                status="success",
                access_token=access_token,
                user_data={
                    "user_id": user_id,
                    "user_name": user_name,
                    "email": email,
                    "profile": profile
                }
            )
            
        except KiteException as e:
            logger.error(f"Kite API error in generate_session: {str(e)}")
            return GenerateSessionResponse(
                status="error", 
                message=f"The error from Zerodha was: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error in generate_session: {str(e)}")
            return GenerateSessionResponse(
                status="error", 
                message=f"Internal server error: {str(e)}"
            )
    
    def get_connection_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get broker connection status for user
        
        Args:
            user_id: User identifier
            
        Returns:
            Connection status information
        """
        # This would check database for user credentials and verify connection
        # Implementation depends on your database service
        pass


# Service instance
auth_service = AuthService() 