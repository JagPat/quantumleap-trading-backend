"""
Authentication service - handles all broker authentication logic
"""
import logging
import jwt
import requests
import hashlib
from typing import Optional, Dict, Any
from fastapi import HTTPException
from kiteconnect import KiteConnect
from kiteconnect.exceptions import KiteException

from ..core.config import settings
from ..database.service import store_user_credentials, get_user_credentials, delete_user_credentials, get_user_credentials_by_email
from .models import GenerateSessionResponse, Base44User, BrokerProfileResponse

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
    
    def exchange_token_direct(self, request_token: str, api_key: str, api_secret: str) -> tuple[str, str]:
        """
        Direct token exchange with Kite Connect API using proper SHA256 checksum
        
        Args:
            request_token: Request token from Zerodha OAuth
            api_key: Zerodha API key
            api_secret: Zerodha API secret
            
        Returns:
            Tuple of (access_token, user_id)
            
        Raises:
            HTTPException: If token exchange fails
        """
        try:
            # CRITICAL: Implement proper SHA256 checksum as per Kite Connect v3 docs
            checksum_string = api_key + request_token + api_secret
            checksum = hashlib.sha256(checksum_string.encode()).hexdigest()
            
            logger.info(f"🔐 Token exchange - API key: {api_key[:8]}..., Request token: {request_token[:8]}...")
            logger.info(f"🔐 Checksum string length: {len(checksum_string)}, Checksum: {checksum[:16]}...")
            
            # POST to Kite Connect session endpoint
            response = requests.post(
                'https://api.kite.trade/session/token',
                data={
                    'api_key': api_key,
                    'request_token': request_token,
                    'checksum': checksum
                },
                headers={
                    'X-Kite-Version': '3',
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                timeout=30
            )
            
            logger.info(f"🔐 Kite API response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"❌ Kite API error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"Token exchange failed with status {response.status_code}: {response.text}"
                )
            
            response_data = response.json()
            logger.info(f"🔐 Kite API response keys: {list(response_data.keys())}")
            
            if 'data' not in response_data:
                logger.error(f"❌ Invalid response format: {response_data}")
                raise HTTPException(status_code=400, detail="Invalid response format from Kite API")
            
            data = response_data['data']
            access_token = data.get('access_token')
            user_id = data.get('user_id')
            
            if not access_token or not user_id:
                logger.error(f"❌ Missing access_token or user_id in response: {data}")
                raise HTTPException(status_code=400, detail="Incomplete token data from Kite API")
            
            logger.info(f"✅ Token exchange successful - User ID: {user_id}, Access token: {access_token[:16]}...")
            return access_token, user_id
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Network error during token exchange: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Network error during token exchange: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Unexpected error during token exchange: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Token exchange failed: {str(e)}")
    
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
            # Use direct token exchange for better control and error handling
            access_token, user_id = self.exchange_token_direct(request_token, api_key, api_secret)
            
            # Get user profile using KiteConnect
            kite = KiteConnect(api_key=api_key)
            kite.set_access_token(access_token)
            profile = kite.profile()
            
            user_name = profile.get("user_name", "")
            email = profile.get("email", "")
            
            logger.info(f"✅ Profile retrieved - Name: {user_name}, Email: {email}")
            
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
            
            logger.info(f"✅ Successfully generated session for user: {user_id}")
            
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
            
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except KiteException as e:
            logger.error(f"❌ Kite API error in generate_session: {str(e)}")
            return GenerateSessionResponse(
                status="error", 
                message=f"Zerodha API error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"❌ Unexpected error in generate_session: {str(e)}")
            return GenerateSessionResponse(
                status="error", 
                message=f"Internal server error: {str(e)}"
            )
    
    def invalidate_session(self, user_id: str) -> Dict[str, Any]:
        """
        Invalidate broker session for user (logout)
        
        Args:
            user_id: User identifier
            
        Returns:
            Status of invalidation operation
        """
        try:
            if not user_id or user_id.strip() == "":
                logger.warning("Empty or invalid user_id provided for invalidate_session")
                return {
                    "status": "error",
                    "message": "User ID is required for session invalidation"
                }
            
            # Get user credentials from database
            credentials = get_user_credentials(user_id)
            
            if not credentials:
                logger.warning(f"No credentials found for user: {user_id}")
                return {
                    "status": "warning",
                    "message": "No active session found for user"
                }
            
            api_key = credentials.get("api_key")
            access_token = credentials.get("access_token")
            
            if api_key and access_token:
                try:
                    # Create KiteConnect instance and invalidate token
                    kite = KiteConnect(api_key=api_key)
                    kite.invalidate_access_token(access_token=access_token)
                    logger.info(f"Successfully invalidated Zerodha session for user: {user_id}")
                except KiteException as e:
                    logger.warning(f"Zerodha invalidation failed for user {user_id}: {str(e)}")
                    # Continue with local cleanup even if Zerodha fails
                except Exception as e:
                    logger.warning(f"Error during Zerodha invalidation for user {user_id}: {str(e)}")
                    # Continue with local cleanup
            
            # Remove credentials from local database
            delete_success = delete_user_credentials(user_id)
            
            if delete_success:
                logger.info(f"Successfully removed local credentials for user: {user_id}")
                return {
                    "status": "success",
                    "message": "Session invalidated and credentials removed"
                }
            else:
                logger.error(f"Failed to remove local credentials for user: {user_id}")
                return {
                    "status": "error",
                    "message": "Failed to remove local credentials"
                }
                
        except Exception as e:
            logger.error(f"Unexpected error invalidating session for user {user_id}: {str(e)}")
            return {
                "status": "error",
                "message": f"Session invalidation failed: {str(e)}"
            }
    
    def invalidate_session_by_email(self, email: str) -> Dict[str, Any]:
        """
        Invalidate broker session for user by email (for JWT-based disconnect)
        
        Args:
            email: User email address
            
        Returns:
            Status of invalidation operation
        """
        try:
            if not email or email.strip() == "":
                logger.warning("Empty or invalid email provided for invalidate_session_by_email")
                return {
                    "status": "error",
                    "message": "Email is required for session invalidation"
                }
            
            # Get user credentials from database by email
            credentials = get_user_credentials_by_email(email)
            
            if not credentials:
                logger.warning(f"No credentials found for email: {email}")
                return {
                    "status": "warning",
                    "message": "No active session found for user"
                }
            
            user_id = credentials.get("user_id")
            api_key = credentials.get("api_key")
            access_token = credentials.get("access_token")
            
            if api_key and access_token:
                try:
                    # Create KiteConnect instance and invalidate token
                    kite = KiteConnect(api_key=api_key)
                    kite.invalidate_access_token(access_token=access_token)
                    logger.info(f"Successfully invalidated Zerodha session for email: {email}")
                except KiteException as e:
                    logger.warning(f"Zerodha invalidation failed for email {email}: {str(e)}")
                    # Continue with local cleanup even if Zerodha fails
                except Exception as e:
                    logger.warning(f"Error during Zerodha invalidation for email {email}: {str(e)}")
                    # Continue with local cleanup
            
            # Remove credentials from local database using user_id
            if user_id:
                delete_success = delete_user_credentials(user_id)
                
                if delete_success:
                    logger.info(f"Successfully removed local credentials for email: {email}")
                    return {
                        "status": "success",
                        "message": "Session invalidated and credentials removed"
                    }
                else:
                    logger.error(f"Failed to remove local credentials for email: {email}")
                    return {
                        "status": "error",
                        "message": "Failed to remove local credentials"
                    }
            else:
                logger.error(f"No user_id found for email: {email}")
                return {
                    "status": "error",
                    "message": "Invalid user data found"
                }
                
        except Exception as e:
            logger.error(f"Unexpected error invalidating session for email {email}: {str(e)}")
            return {
                "status": "error",
                "message": f"Session invalidation failed: {str(e)}"
            }

    def get_connection_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get broker connection status for user
        """
        from ..database.service import store_user_credentials
        from datetime import datetime
        try:
            if not user_id or user_id.strip() == "":
                return {
                    "status": "error",
                    "is_connected": False,
                    "message": "User ID is required for status check",
                    "last_successful_connection": None,
                    "token_expiry": None,
                    "last_error": "User ID missing"
                }
            credentials = get_user_credentials(user_id)
            if not credentials:
                return {
                    "status": "disconnected",
                    "is_connected": False,
                    "message": "No active session",
                    "last_successful_connection": None,
                    "token_expiry": None,
                    "last_error": "No active session"
                }
            access_token = credentials.get("access_token")
            api_key = credentials.get("api_key")
            if not access_token or not api_key:
                return {
                    "status": "disconnected",
                    "is_connected": False,
                    "message": "Incomplete credentials",
                    "last_successful_connection": credentials.get("last_successful_connection"),
                    "token_expiry": credentials.get("token_expiry"),
                    "last_error": "Incomplete credentials"
                }
            # Test connection with simple API call
            try:
                kite = KiteConnect(api_key=api_key)
                kite.set_access_token(access_token)
                profile = kite.profile()  # Simple test call
                # Try to get token expiry if available (Kite API may not provide directly)
                token_expiry = credentials.get("token_expiry")
                # Update last_successful_connection and clear last_error
                now_str = datetime.now().isoformat()
                store_user_credentials(
                    user_id=user_id,
                    api_key=api_key,
                    api_secret=credentials.get("api_secret"),
                    access_token=access_token,
                    user_name=credentials.get("user_name"),
                    email=credentials.get("email"),
                    last_successful_connection=now_str,
                    token_expiry=token_expiry,
                    last_error=None
                )
                return {
                    "status": "connected",
                    "is_connected": True,
                    "user_data": {
                        "user_id": profile.get("user_id"),
                        "user_name": profile.get("user_name"),
                        "email": profile.get("email")
                    },
                    "message": "Active connection verified",
                    "last_successful_connection": now_str,
                    "token_expiry": token_expiry,
                    "last_error": None
                }
            except KiteException as e:
                # Update last_error
                last_error = f"Connection test failed: {str(e)}"
                store_user_credentials(
                    user_id=user_id,
                    api_key=api_key,
                    api_secret=credentials.get("api_secret"),
                    access_token=access_token,
                    user_name=credentials.get("user_name"),
                    email=credentials.get("email"),
                    last_successful_connection=credentials.get("last_successful_connection"),
                    token_expiry=credentials.get("token_expiry"),
                    last_error=last_error
                )
                return {
                    "status": "disconnected",
                    "is_connected": False,
                    "message": last_error,
                    "last_successful_connection": credentials.get("last_successful_connection"),
                    "token_expiry": credentials.get("token_expiry"),
                    "last_error": last_error
                }
        except Exception as e:
            last_error = f"Status check failed: {str(e)}"
            store_user_credentials(
                user_id=user_id,
                api_key=credentials.get("api_key") if 'credentials' in locals() and credentials else None,
                api_secret=credentials.get("api_secret") if 'credentials' in locals() and credentials else None,
                access_token=credentials.get("access_token") if 'credentials' in locals() and credentials else None,
                user_name=credentials.get("user_name") if 'credentials' in locals() and credentials else None,
                email=credentials.get("email") if 'credentials' in locals() and credentials else None,
                last_successful_connection=credentials.get("last_successful_connection") if 'credentials' in locals() and credentials else None,
                token_expiry=credentials.get("token_expiry") if 'credentials' in locals() and credentials else None,
                last_error=last_error
            )
            return {
                "status": "error",
                "is_connected": False,
                "message": last_error,
                "last_successful_connection": credentials.get("last_successful_connection") if 'credentials' in locals() and credentials else None,
                "token_expiry": credentials.get("token_expiry") if 'credentials' in locals() and credentials else None,
                "last_error": last_error
            }
    
    def validate_base44_token(self, authorization_header: str) -> Base44User:
        """
        Validate Base44 JWT token and extract user information
        
        Args:
            authorization_header: Authorization header with Bearer token
            
        Returns:
            Base44User object with user information
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            if not authorization_header or not authorization_header.startswith('Bearer '):
                raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
            
            token = authorization_header.split(' ')[1]
            
            # For now, we'll decode without verification since we don't have Base44's public key
            # In production, you should verify the token with Base44's public key
            try:
                # Decode token without verification for now
                decoded = jwt.decode(token, options={"verify_signature": False})
                logger.info(f"✅ Base44 token decoded successfully")
                
                # Extract user information
                user_email = decoded.get('email')
                user_id = decoded.get('sub') or decoded.get('user_id')
                app_id = decoded.get('app_id')
                
                if not user_email:
                    raise HTTPException(status_code=401, detail="Token missing email claim")
                
                logger.info(f"✅ Valid Base44 token for user: {user_email}")
                
                return Base44User(
                    email=user_email,
                    user_id=user_id or user_email,
                    app_id=app_id,
                    permissions=decoded.get('permissions', [])
                )
                
            except jwt.InvalidTokenError as e:
                logger.error(f"❌ JWT decode error: {str(e)}")
                raise HTTPException(status_code=401, detail="Invalid JWT token")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Base44 token validation failed: {str(e)}")
            raise HTTPException(status_code=401, detail="Token validation failed")
    
    def get_broker_profile(self, authorization_header: str) -> BrokerProfileResponse:
        """
        Get broker profile information for authenticated Base44 user
        
        Args:
            authorization_header: Authorization header with Bearer token
            
        Returns:
            BrokerProfileResponse with user profile data
        """
        try:
            # Validate Base44 token and get user info
            base44_user = self.validate_base44_token(authorization_header)
            logger.info(f"🔍 Getting broker profile for Base44 user: {base44_user.email}")
            
            # Look up user's broker credentials by email
            credentials = self.get_user_credentials_by_email(base44_user.email)
            
            if not credentials:
                logger.warning(f"❌ No broker credentials found for user: {base44_user.email}")
                return BrokerProfileResponse(
                    status="error",
                    message="No active broker session found. Please authenticate with your broker first."
                )
            
            api_key = credentials.get("api_key")
            access_token = credentials.get("access_token")
            
            if not api_key or not access_token:
                logger.warning(f"❌ Incomplete broker credentials for user: {base44_user.email}")
                return BrokerProfileResponse(
                    status="error",
                    message="Incomplete broker credentials. Please re-authenticate with your broker."
                )
            
            # Test the broker connection and get profile
            try:
                kite = KiteConnect(api_key=api_key)
                kite.set_access_token(access_token)
                
                # Get user profile from Zerodha
                profile = kite.profile()
                
                logger.info(f"✅ Successfully retrieved broker profile for user: {base44_user.email}")
                
                return BrokerProfileResponse(
                    status="success",
                    user_data={
                        "user_id": profile.get("user_id"),
                        "user_name": profile.get("user_name"),
                        "email": profile.get("email"),
                        "broker": "ZERODHA",
                        "profile": profile,
                        "base44_user": base44_user.email
                    }
                )
                
            except KiteException as e:
                logger.error(f"❌ Zerodha API failed for user {base44_user.email}: {str(e)}")
                
                # Check if it's a token/session issue
                if "token" in str(e).lower() or "session" in str(e).lower() or "invalid" in str(e).lower():
                    return BrokerProfileResponse(
                        status="error",
                        message="Session expired or invalid. Please re-authenticate with your broker."
                    )
                else:
                    return BrokerProfileResponse(
                        status="error",
                        message=f"Broker API error: {str(e)}"
                    )
                    
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Error getting broker profile: {str(e)}")
            return BrokerProfileResponse(
                status="error",
                message=f"Internal server error: {str(e)}"
            )
    
    def disconnect_session_by_jwt(self, authorization_header: str) -> Dict[str, Any]:
        """
        Disconnect broker session using JWT token (for Base44 integration)
        
        Args:
            authorization_header: Authorization header with Bearer token
            
        Returns:
            Status of disconnect operation
        """
        try:
            # Validate Base44 token and get user info
            base44_user = self.validate_base44_token(authorization_header)
            logger.info(f"🔌 Disconnecting broker session for Base44 user: {base44_user.email}")
            
            # Use email-based disconnect
            result = self.invalidate_session_by_email(base44_user.email)
            
            if result["status"] == "success":
                logger.info(f"✅ Successfully disconnected session for Base44 user: {base44_user.email}")
                return {
                    "status": "success",
                    "message": "Broker session disconnected successfully",
                    "data": {
                        "is_connected": False,
                        "connection_status": "disconnected",
                        "user_email": base44_user.email
                    }
                }
            elif result["status"] == "warning":
                logger.info(f"⚠️ No active session found for Base44 user: {base44_user.email}")
                return {
                    "status": "success",
                    "message": "No active session found (already disconnected)",
                    "data": {
                        "is_connected": False,
                        "connection_status": "disconnected",
                        "user_email": base44_user.email
                    }
                }
            else:
                logger.error(f"❌ Failed to disconnect session for Base44 user: {base44_user.email}")
                return {
                    "status": "error",
                    "message": result["message"],
                    "data": {
                        "is_connected": False,
                        "connection_status": "error",
                        "user_email": base44_user.email
                    }
                }
                
        except HTTPException as e:
            logger.error(f"❌ JWT validation failed for disconnect: {str(e.detail)}")
            return {
                "status": "error",
                "message": f"Authentication failed: {str(e.detail)}",
                "data": {
                    "is_connected": False,
                    "connection_status": "error"
                }
            }
        except Exception as e:
            logger.error(f"❌ Unexpected error in JWT-based disconnect: {str(e)}")
            return {
                "status": "error",
                "message": f"Disconnect failed: {str(e)}",
                "data": {
                    "is_connected": False,
                    "connection_status": "error"
                }
            }
    
    def get_user_credentials_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user credentials by email address
        
        Args:
            email: User email address
            
        Returns:
            User credentials dict or None if not found
        """
        try:
            return get_user_credentials_by_email(email)
        except Exception as e:
            logger.error(f"Error getting user credentials by email {email}: {str(e)}")
            return None

    def get_user_credentials(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user credentials from database
        
        Args:
            user_id: User identifier
            
        Returns:
            User credentials dictionary or None if not found
        """
        try:
            return get_user_credentials(user_id)
        except Exception as e:
            logger.error(f"Error getting user credentials: {str(e)}")
            return None


# Service instance
auth_service = AuthService() 