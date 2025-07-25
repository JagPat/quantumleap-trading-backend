"""
Authentication router - FastAPI endpoints for broker authentication
"""
import logging
from fastapi import APIRouter, HTTPException, Depends, Query, Request, Header
from fastapi.responses import RedirectResponse
from typing import Optional
from datetime import datetime

from ..core.config import settings
from .models import GenerateSessionRequest, GenerateSessionResponse, BrokerProfileResponse
from .service import auth_service
from .dependencies import get_user_from_headers

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["Authentication"])


@router.get("/broker/callback")
async def broker_callback(
    request: Request, 
    request_token: str = Query(...), 
    action: str = Query(...),
    state: str = Query(None),
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
    # CRITICAL FIX: Use config-based frontend URL detection
    # When Kite Connect redirects to our backend, there's no referer header
    # So we use the configured frontend URL
    
    from app.core.config import settings
    frontend_url_override = settings.frontend_url
    
    logger.info(f"🔄 Using configured frontend URL: {frontend_url_override}")
    
    try:
        # Log the full request for debugging
        logger.info(f"🔄 Received broker callback with request_token: {request_token}")
        logger.info(f"🔄 Full URL: {request.url}")
        logger.info(f"🔄 Query params: {dict(request.query_params)}")
        
        # Clean and validate the request_token
        clean_token = auth_service.clean_request_token(request_token)
        
        # Try to get API credentials from query params, state file, or session
        stored_api_key = api_key
        stored_api_secret = api_secret
        
        # If no credentials in query params, try to get from state file first
        if not stored_api_key or not stored_api_secret:
            if state:
                try:
                    import json
                    import os
                    temp_file = os.path.join("oauth_temp", f"oauth_{state}.json")
                    if os.path.exists(temp_file):
                        with open(temp_file, 'r') as f:
                            oauth_data = json.load(f)
                        stored_api_key = oauth_data.get('api_key')
                        stored_api_secret = oauth_data.get('api_secret')
                        logger.info(f"🔍 Retrieved credentials from state file: api_key={stored_api_key[:8] if stored_api_key else 'None'}...")
                        
                        # Clean up temp file
                        os.remove(temp_file)
                    else:
                        logger.warning(f"🔍 State file not found: {temp_file}")
                except Exception as e:
                    logger.error(f"🔍 Error reading state file: {e}")
            
            # Fallback to session if state method failed
            if not stored_api_key or not stored_api_secret:
                session_data = request.session.get('zerodha_oauth', {})
                stored_api_key = session_data.get('api_key')
                stored_api_secret = session_data.get('api_secret')
                logger.info(f"🔍 Retrieved credentials from session: api_key={stored_api_key[:8] if stored_api_key else 'None'}...")
                logger.info(f"🔍 Full session data keys: {list(request.session.keys())}")
                logger.info(f"🔍 Session ID: {request.session.get('session_id', 'No session ID')}")
        
        # If we have credentials, attempt token exchange here
        if stored_api_key and stored_api_secret:
            try:
                logger.info(f"🔄 Attempting token exchange with API key: {stored_api_key[:8]}...")
                
                # Generate session using the auth service with direct token exchange
                session_result = auth_service.generate_session(
                    request_token=clean_token,
                    api_key=stored_api_key,
                    api_secret=stored_api_secret
                )
                
                if session_result.status == "success":
                    # Store session data in FastAPI session
                    user_id = session_result.user_data.get("user_id")
                    access_token = session_result.access_token
                    
                    # Store in session for later retrieval
                    request.session['zerodha_auth'] = {
                        'user_id': user_id,
                        'access_token': access_token,
                        'api_key': stored_api_key,
                        'user_data': session_result.user_data,
                        'is_connected': True,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # CRITICAL: Store credentials in database for portfolio service
                    from ..database.service import store_user_credentials
                    user_data = session_result.user_data
                    store_success = store_user_credentials(
                        user_id=user_id,
                        api_key=stored_api_key,
                        api_secret=stored_api_secret,
                        access_token=access_token,
                        user_name=user_data.get("user_name"),
                        email=user_data.get("email"),
                        last_successful_connection=datetime.now().isoformat()
                    )
                    
                    if store_success:
                        logger.info(f"✅ Credentials stored in database for user: {user_id}")
                    else:
                        logger.error(f"❌ Failed to store credentials in database for user: {user_id}")
                    
                    logger.info(f"✅ Token exchange successful for user: {user_id}")
                    
                    # Clear OAuth temp data
                    if 'zerodha_oauth' in request.session:
                        del request.session['zerodha_oauth']
                    
                    # CRITICAL FIX: Use correct frontend broker callback URL
                    redirect_url = f"{frontend_url_override}/broker-callback?status=success&user_id={user_id}&action={action}"
                    
                else:
                    logger.error(f"❌ Token exchange failed: {session_result.message}")
                    # Redirect to frontend with error
                    redirect_url = f"{frontend_url_override}/broker-callback?status=error&error={session_result.message}&action={action}"
                    
            except Exception as exchange_error:
                logger.error(f"❌ Token exchange error: {str(exchange_error)}")
                # Redirect to frontend with error
                redirect_url = f"{frontend_url_override}/broker-callback?status=error&error={str(exchange_error)}&action={action}"
        else:
            # No credentials available - redirect to frontend with request_token for manual exchange
            logger.info(f"🔄 No API credentials available, redirecting to frontend with request_token")
            redirect_url = f"{frontend_url_override}/broker-callback?request_token={clean_token}&action={action}"
        
        logger.info(f"🔄 Redirecting to: {redirect_url}")
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        logger.error(f"❌ Error in broker_callback: {str(e)}")
        # Redirect to frontend with error status
        error_url = f"{frontend_url_override}/broker-callback?status=error&error={str(e)}&action={action}"
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
async def get_broker_session(request: Request, user_id: str = Query(..., description="User ID")):
    """
    Get Stored Broker Session Data
    
    Returns the stored session data for a user including access_token and profile info.
    This is used by the frontend to check if a user is already authenticated.
    """
    try:
        # First check FastAPI session storage
        session_auth = request.session.get('zerodha_auth', {})
        
        if session_auth and session_auth.get('is_connected'):
            # Validate session is for the requested user
            session_user_id = session_auth.get('user_id')
            if session_user_id == user_id or not user_id or user_id == 'unknown':
                logger.info(f"✅ Found active session for user: {session_user_id}")
                return {
                    "status": "success",
                    "is_connected": True,
                    "user_data": session_auth.get('user_data', {}),
                    "access_token": session_auth.get('access_token'),
                    "connection_status": "connected",
                    "timestamp": session_auth.get('timestamp')
                }
        
        # Fallback to database lookup
        logger.info(f"🔍 No session found, checking database for user: {user_id}")
        
        # Get user credentials from database
        credentials = auth_service.get_user_credentials(user_id)
        
        if not credentials:
            logger.info(f"❌ No credentials found for user: {user_id}")
            raise HTTPException(status_code=401, detail="No session found for user")
        
        # Check if credentials are valid by testing a simple API call
        api_key = credentials.get("api_key")
        access_token = credentials.get("access_token")
        
        if not api_key or not access_token:
            logger.warning(f"❌ Incomplete credentials for user: {user_id}")
            return {
                "status": "error",
                "message": "Incomplete credentials found",
                "is_connected": False,
                "connection_status": "disconnected"
            }
        
        # Test the connection
        from kiteconnect import KiteConnect
        try:
            kite = KiteConnect(api_key=api_key)
            kite.set_access_token(access_token)
            
            # Test with profile call
            profile = kite.profile()
            
            # Store in session for future use
            request.session['zerodha_auth'] = {
                'user_id': profile.get('user_id'),
                'access_token': access_token,
                'api_key': api_key,
                'user_data': {
                    'user_id': profile.get('user_id'),
                    'user_name': profile.get('user_name'),
                    'email': profile.get('email'),
                    'profile': profile
                },
                'is_connected': True,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Database credentials valid for user: {user_id}")
            return {
                "status": "success",
                "is_connected": True,
                "user_data": {
                    'user_id': profile.get('user_id'),
                    'user_name': profile.get('user_name'),
                    'email': profile.get('email'),
                    'api_key': api_key,
                    'profile': profile
                },
                "access_token": access_token,
                "connection_status": "connected"
            }
            
        except Exception as e:
            logger.error(f"❌ Database credentials invalid for user {user_id}: {str(e)}")
            return {
                "status": "error",
                "message": f"Invalid or expired credentials: {str(e)}",
                "is_connected": False,
                "connection_status": "expired"
            }
        
    except Exception as e:
        logger.error(f"❌ Error getting broker session: {str(e)}")
        return {
            "status": "error",
            "message": f"Session retrieval failed: {str(e)}",
            "is_connected": False,
            "connection_status": "error"
        }


@router.get("/broker/status-header")
async def get_broker_status_with_headers(user_id: str = Depends(get_user_from_headers)):
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

@router.post("/broker/profile")
async def broker_profile(user_id: str = Query(..., description="User ID")):
    """
    Returns broker profile for the authenticated user.
    """
    try:
        # Try to get from database
        credentials = auth_service.get_user_credentials(user_id)
        if not credentials:
            raise HTTPException(status_code=404, detail="No credentials found for user")
        # Simulate profile info (expand as needed)
        profile = {
            "user_id": user_id,
            "user_name": credentials.get("user_name", ""),
            "email": credentials.get("email", ""),
            "api_key": credentials.get("api_key", ""),
        }
        return {"status": "success", "profile": profile}
    except Exception as e:
        logger.error(f"Error getting broker profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get broker profile")

@router.post("/broker/margins")
async def broker_margins(user_id: str = Query(..., description="User ID")):
    """
    Returns margin info for the authenticated user. Placeholder for now.
    """
    try:
        # TODO: Implement real margin fetch from broker API
        margins = {
            "available": 1000000,
            "utilized": 0,
            "span": 0,
            "exposure": 0
        }
        return {"status": "success", "margins": margins}
    except Exception as e:
        logger.error(f"Error getting broker margins: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get broker margins")


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


@router.post("/broker/test-oauth")
async def test_oauth_flow(request: Request, api_key: str = Query(...), api_secret: str = Query(...)):
    """
    Test OAuth Flow Setup
    
    Stores API credentials for OAuth callback using stateless approach.
    This endpoint helps test the complete OAuth flow.
    """
    try:
        import uuid
        import json
        import os
        
        # Generate unique state parameter for this OAuth flow
        state = str(uuid.uuid4())
        
        # Store credentials in temporary file (stateless approach)
        # This survives the OAuth redirect unlike HTTP sessions
        temp_dir = "oauth_temp"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            
        temp_file = os.path.join(temp_dir, f"oauth_{state}.json")
        oauth_data = {
            'api_key': api_key,
            'api_secret': api_secret,
            'timestamp': datetime.now().isoformat(),
            'state': state
        }
        
        with open(temp_file, 'w') as f:
            json.dump(oauth_data, f)
        
        # Also store in session as backup (may not work across redirects)
        request.session['zerodha_oauth'] = oauth_data
        
        # Generate OAuth URL with state parameter
        oauth_url = f"https://kite.zerodha.com/connect/login?api_key={api_key}&v=3&state={state}"
        
        logger.info(f"🔄 Test OAuth setup complete for API key: {api_key[:8]}... with state: {state}")
        
        return {
            "status": "success",
            "message": "OAuth credentials stored for callback",
            "oauth_url": oauth_url,
            "redirect_url": "https://web-production-de0bc.up.railway.app/broker/callback",
            "api_key": api_key[:8] + "...",
            "state": state
        }
        
    except Exception as e:
        logger.error(f"❌ Error setting up test OAuth: {str(e)}")
        return {
            "status": "error",
            "message": f"OAuth setup failed: {str(e)}"
        }


@router.get("/broker/session-debug")
async def debug_session(request: Request):
    """
    Debug Session Data
    
    Returns current session data for debugging purposes.
    """
    try:
        session_data = dict(request.session)
        
        # Mask sensitive data
        if 'zerodha_auth' in session_data:
            auth_data = session_data['zerodha_auth'].copy()
            if 'access_token' in auth_data:
                auth_data['access_token'] = auth_data['access_token'][:16] + "..."
            session_data['zerodha_auth'] = auth_data
        
        if 'zerodha_oauth' in session_data:
            oauth_data = session_data['zerodha_oauth'].copy()
            if 'api_secret' in oauth_data:
                oauth_data['api_secret'] = oauth_data['api_secret'][:8] + "..."
            session_data['zerodha_oauth'] = oauth_data
        
        return {
            "status": "success",
            "session_data": session_data,
            "session_keys": list(request.session.keys())
        }
        
    except Exception as e:
        logger.error(f"❌ Error debugging session: {str(e)}")
        return {
            "status": "error",
            "message": f"Session debug failed: {str(e)}"
        } 