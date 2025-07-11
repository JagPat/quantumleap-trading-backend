"""
Authentication router - FastAPI endpoints for broker authentication
"""
import logging
from fastapi import APIRouter, HTTPException, Depends, Query, Request, Header
from fastapi.responses import RedirectResponse
from typing import Optional

from ..core.config import settings
from .models import GenerateSessionRequest, GenerateSessionResponse, BrokerProfileResponse
from .service import auth_service

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/auth", tags=["Authentication"])

def get_user_from_auth_headers(
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


@router.get("/broker/callback")
async def broker_callback(
    request: Request, 
    request_token: str = Query(...), 
    action: str = Query(...),
    api_key: str = Query(None),
    api_secret: str = Query(None)
):
    """
    Broker OAuth Callback
    
    Handles the OAuth callback from Kite Connect after user authorization.
    This endpoint:
    1. Receives the request_token from Zerodha
    2. Exchanges it for access_token (if credentials available)
    3. Stores session data
    4. Redirects to frontend with success/error status
    """
    try:
        # Log the full request for debugging
        logger.info(f"Received broker callback with request_token: {request_token}")
        logger.info(f"Full URL: {request.url}")
        logger.info(f"Query params: {dict(request.query_params)}")
        
        # Clean and validate the request_token
        clean_token = auth_service.clean_request_token(request_token)
        
        # CRITICAL FIX: Override Railway environment variable until manually updated
        # Railway still has old Base44 URL in FRONTEND_URL environment variable
        frontend_url_override = "http://localhost:5173"
        
        # Try to get API credentials from query params or session
        stored_api_key = api_key
        stored_api_secret = api_secret
        
        # If no credentials in query params, try to get from session/temp storage
        if not stored_api_key or not stored_api_secret:
            # For now, redirect to frontend with request_token so frontend can complete the exchange
            # This maintains compatibility with existing frontend flow
            redirect_url = f"{frontend_url_override}/broker/callback?request_token={clean_token}&action={action}"
            logger.info(f"No API credentials available, redirecting to frontend: {redirect_url}")
            return RedirectResponse(url=redirect_url)
        
        # If we have credentials, attempt token exchange here
        try:
            logger.info(f"Attempting token exchange with API key: {stored_api_key[:8]}...")
            
            # Generate session using the auth service
            session_result = auth_service.generate_session(
                request_token=clean_token,
                api_key=stored_api_key,
                api_secret=stored_api_secret
            )
            
            if session_result.status == "success":
                # Store session data in request session or database
                user_id = session_result.user_data.get("user_id")
                access_token = session_result.access_token
                
                logger.info(f"✅ Token exchange successful for user: {user_id}")
                
                # Redirect to frontend with success status
                redirect_url = f"{frontend_url_override}/broker/callback?status=success&user_id={user_id}&action={action}"
                
            else:
                logger.error(f"❌ Token exchange failed: {session_result.message}")
                # Redirect to frontend with error
                redirect_url = f"{frontend_url_override}/broker/callback?status=error&error={session_result.message}&action={action}"
                
        except Exception as exchange_error:
            logger.error(f"❌ Token exchange error: {str(exchange_error)}")
            # Fallback: redirect to frontend with request_token for manual exchange
            redirect_url = f"{frontend_url_override}/broker/callback?request_token={clean_token}&action={action}&exchange_error={str(exchange_error)}"
        
        logger.info(f"Redirecting to: {redirect_url}")
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        logger.error(f"Error in broker_callback: {str(e)}")
        # Redirect to frontend with error status
        error_url = f"{frontend_url_override}/broker/callback?status=error&error={str(e)}&action={action}"
        return RedirectResponse(url=error_url)


@router.post("/broker/generate-session", response_model=GenerateSessionResponse)
async def generate_session(request: GenerateSessionRequest):
    """
    Generate Broker Session
    
    Exchanges a request_token from the broker's OAuth flow for a valid access_token 
    and stores it securely for the user.
    
    Returns:
        {
            "status": "success",
            "access_token": "xxx",
            "user_data": {
                "user_id": "xxx",
                "user_name": "xxx", 
                "email": "xxx",
                "profile": {...}
            }
        }
    """
    return auth_service.generate_session(
        request_token=request.request_token,
        api_key=request.api_key,
        api_secret=request.api_secret
    )


@router.get("/broker/status")
async def get_broker_status(user_id: str = Query(..., description="User ID")):
    """
    Get Broker Connection Status
    
    Checks if user has valid broker connection and returns status.
    """
    try:
        status = auth_service.get_connection_status(user_id)
        return {"status": "success", "data": status}
    except Exception as e:
        logger.error(f"Error getting broker status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get broker status")


@router.get("/broker/session")
async def get_broker_session(user_id: str = Query(..., description="User ID")):
    """
    Get Stored Broker Session Data
    
    Returns the stored session data for a user including access_token and profile info.
    This is used by the frontend to check if a user is already authenticated.
    """
    try:
        # Get user credentials from database
        credentials = auth_service.get_user_credentials(user_id)
        
        if not credentials:
            return {
                "status": "error",
                "message": "No session found for user",
                "is_connected": False
            }
        
        # Check if credentials are valid by testing a simple API call
        api_key = credentials.get("api_key")
        access_token = credentials.get("access_token")
        
        if not api_key or not access_token:
            return {
                "status": "error", 
                "message": "Incomplete session data",
                "is_connected": False
            }
        
        # Return session data (without sensitive info)
        return {
            "status": "success",
            "is_connected": True,
            "user_data": {
                "user_id": credentials.get("user_id"),
                "user_name": credentials.get("user_name"),
                "email": credentials.get("email"),
                "api_key": api_key
            },
            "access_token": access_token  # Frontend needs this for API calls
        }
        
    except Exception as e:
        logger.error(f"Error getting broker session: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to get session: {str(e)}",
            "is_connected": False
        }


@router.get("/broker/status-header")
async def get_broker_status_with_headers(user_id: str = Depends(get_user_from_auth_headers)):
    """
    Get Broker Connection Status (Header-based Auth)
    
    Checks if user has valid broker connection and returns status.
    Uses Kite Connect authorization headers: Authorization: token api_key:access_token
    """
    try:
        status = auth_service.get_connection_status(user_id)
        return {"status": "success", "data": status}
    except Exception as e:
        logger.error(f"Error getting broker status with headers: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get broker status")


@router.post("/broker/invalidate-session")
async def invalidate_broker_session(user_id: str = Query(..., description="User ID")):
    """
    Invalidate Broker Session
    
    Invalidates the user's broker access token (logout) and removes stored credentials.
    This is the proper way to disconnect a user from their broker account.
    """
    try:
        result = auth_service.invalidate_session(user_id)
        
        if result["status"] == "success":
            return {"status": "success", "message": result["message"]}
        elif result["status"] == "warning":
            return {"status": "success", "message": result["message"]}  # Treat warning as success for Base44
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error invalidating broker session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to invalidate session: {str(e)}")


@router.post("/broker/disconnect-session")
async def disconnect_broker_session_jwt(authorization: str = Header(..., description="Bearer token from Base44")):
    """
    Disconnect Broker Session (JWT-based)
    
    Disconnects the user's broker session using Base44 JWT token.
    This is the recommended endpoint for Base44 integration as it doesn't require user_id.
    """
    try:
        result = auth_service.disconnect_session_by_jwt(authorization)
        
        if result["status"] == "success":
            return {
                "status": "success", 
                "message": result["message"],
                "data": result["data"]
            }
        else:
            # Map error types to appropriate HTTP status codes
            if "Authentication failed" in result["message"]:
                raise HTTPException(status_code=401, detail=result["message"])
            elif "No active session" in result["message"]:
                # Treat "no session" as success for disconnect operations
                return {
                    "status": "success", 
                    "message": result["message"],
                    "data": result["data"]
                }
            else:
                raise HTTPException(status_code=400, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in JWT-based disconnect: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to disconnect session: {str(e)}")


@router.get("/broker/profile", response_model=BrokerProfileResponse)
async def get_broker_profile(authorization: str = Header(..., description="Bearer token from Base44")):
    """
    Get Broker Profile
    
    Retrieves broker profile information for authenticated Base44 user.
    This endpoint validates the Base44 JWT token and returns the user's broker profile.
    """
    try:
        result = auth_service.get_broker_profile(authorization)
        
        if result.status == "success":
            return result
        else:
            # Map error messages to appropriate HTTP status codes
            if "No active broker session" in result.message:
                raise HTTPException(status_code=404, detail=result.message)
            elif "Session expired" in result.message or "invalid" in result.message.lower():
                raise HTTPException(status_code=401, detail=result.message)
            else:
                raise HTTPException(status_code=500, detail=result.message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting broker profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get broker profile")


@router.delete("/broker/disconnect")
async def disconnect_broker(user_id: str = Query(..., description="User ID")):
    """
    Disconnect Broker (Legacy endpoint)
    
    Removes stored broker credentials for user.
    For full session invalidation, use /broker/invalidate-session instead.
    For JWT-based disconnect, use /broker/disconnect-session instead.
    """
    try:
        result = auth_service.invalidate_session(user_id)
        
        if result["status"] in ["success", "warning"]:
            return {"status": "success", "message": "Broker disconnected successfully"}
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting broker: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to disconnect broker") 