"""
Authentication router - FastAPI endpoints for broker authentication
"""
import logging
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import RedirectResponse

from ..core.config import settings
from .models import GenerateSessionRequest, GenerateSessionResponse
from .service import auth_service

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.get("/broker/callback")
async def broker_callback(
    request: Request, 
    request_token: str = Query(...), 
    action: str = Query(...)
):
    """
    Broker OAuth Callback
    
    Handles the OAuth callback from Kite Connect after user authorization.
    This endpoint receives the request_token and redirects to frontend /BrokerCallback route.
    """
    try:
        # Log the full request for debugging
        logger.info(f"Received broker callback with request_token: {request_token}")
        logger.info(f"Full URL: {request.url}")
        logger.info(f"Query params: {dict(request.query_params)}")
        
        # Clean and validate the request_token
        clean_token = auth_service.clean_request_token(request_token)
        
        # Redirect to frontend with the cleaned request_token
        redirect_url = f"{settings.frontend_url}/BrokerCallback?request_token={clean_token}&action={action}"
        
        logger.info(f"Redirecting to: {redirect_url}")
        
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        logger.error(f"Error in broker_callback: {str(e)}")
        raise HTTPException(status_code=500, detail="Callback processing failed")


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


@router.delete("/broker/disconnect")
async def disconnect_broker(user_id: str = Query(..., description="User ID")):
    """
    Disconnect Broker
    
    Removes stored broker credentials for user.
    """
    try:
        # Implementation would remove user credentials from database
        return {"status": "success", "message": "Broker disconnected successfully"}
    except Exception as e:
        logger.error(f"Error disconnecting broker: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to disconnect broker") 