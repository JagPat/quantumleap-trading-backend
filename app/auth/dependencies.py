from fastapi import Header, HTTPException
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def get_user_from_headers(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> str:
    """
    Extract user ID from Kite Connect authorization headers for auth endpoints.
    
    Expected format: Authorization: token api_key:access_token
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    if not authorization.startswith("token "):
        raise HTTPException(status_code=401, detail="Invalid authorization format. Expected 'token api_key:access_token'")
    
    try:
        # Extract api_key:access_token part
        token_part = authorization[6:]  # Remove "token " prefix
        if ":" not in token_part:
            raise HTTPException(status_code=401, detail="Invalid token format. Expected 'api_key:access_token'")
        
        api_key, access_token = token_part.split(":", 1)
        
        if not api_key or not access_token:
            raise HTTPException(status_code=401, detail="Missing api_key or access_token")
        
        # Use X-User-ID header if provided, otherwise use api_key as fallback
        user_id = x_user_id if x_user_id and x_user_id != 'unknown' else api_key
        
        logger.info(f"🔐 Auth endpoint - user_id: {user_id}, api_key: {api_key[:8]}...")
        return user_id
        
    except ValueError as e:
        logger.error(f"Failed to parse authorization header: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid authorization header format") 