"""
Broker Router
FastAPI router for broker-related endpoints
"""
from fastapi import APIRouter, Header, Depends, HTTPException
from typing import Optional
import json
import os
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/broker", tags=["Broker Integration"])

def get_user_from_headers(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> str:
    """Extract user ID from headers"""
    if x_user_id:
        return x_user_id
    # Fallback to a default for testing
    return "default_user"

def get_session_file_path(user_id: str) -> str:
    """Get session file path for user"""
    sessions_dir = "sessions"
    if not os.path.exists(sessions_dir):
        os.makedirs(sessions_dir)
    return os.path.join(sessions_dir, f"session_{user_id}.json")

def load_user_session(user_id: str) -> dict:
    """Load user session from file"""
    try:
        session_file = get_session_file_path(user_id)
        if os.path.exists(session_file):
            with open(session_file, 'r') as f:
                session_data = json.load(f)
                
            # Check if session is expired (24 hours)
            last_updated = datetime.fromisoformat(session_data.get('last_updated', '1970-01-01T00:00:00'))
            if datetime.now() - last_updated < timedelta(hours=24):
                return session_data
            else:
                print(f"Session expired for user {user_id}")
                return {}
        return {}
    except Exception as e:
        print(f"Error loading session for user {user_id}: {e}")
        return {}

def save_user_session(user_id: str, session_data: dict) -> bool:
    """Save user session to file"""
    try:
        session_file = get_session_file_path(user_id)
        session_data['last_updated'] = datetime.now().isoformat()
        session_data['user_id'] = user_id
        
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving session for user {user_id}: {e}")
        return False

def validate_user_session(user_id: str, access_token: str) -> bool:
    """Validate user session with stored data"""
    try:
        session_data = load_user_session(user_id)
        if not session_data:
            return False
            
        stored_token = session_data.get('access_token')
        if not stored_token or stored_token != access_token:
            return False
            
        # Check if session is still valid
        last_updated = datetime.fromisoformat(session_data.get('last_updated', '1970-01-01T00:00:00'))
        if datetime.now() - last_updated > timedelta(hours=24):
            return False
            
        return True
    except Exception as e:
        print(f"Error validating session for user {user_id}: {e}")
        return False

@router.get("/status-header")
async def get_broker_status_header():
    """Get broker service status for header display (no auth required)"""
    try:
        return {
            "status": "operational",
            "service": "broker",
            "is_connected": False,
            "message": "Broker service available",
            "timestamp": datetime.now().isoformat(),
            "auth_required": True
        }
    except Exception as e:
        return {
            "status": "error",
            "service": "broker",
            "is_connected": False,
            "message": f"Broker service error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@router.get("/status")
async def get_broker_status(
    user_id: str = Depends(get_user_from_headers),
    authorization: Optional[str] = Header(None)
):
    """Get broker service status with session validation"""
    try:
        # Extract access token from authorization header
        access_token = None
        if authorization and authorization.startswith('token '):
            parts = authorization.split(' ')
            if len(parts) >= 2:
                token_part = parts[1]
                if ':' in token_part:
                    access_token = token_part.split(':')[1]
        
        if not access_token:
            return {
                "status": "error",
                "message": "No access token provided",
                "is_connected": False,
                "user_id": user_id
            }
        
        # Validate session
        is_valid = validate_user_session(user_id, access_token)
        
        if is_valid:
            # Update session timestamp
            session_data = load_user_session(user_id)
            save_user_session(user_id, session_data)
            
            return {
                "status": "success",
                "message": "Session is valid and active",
                "is_connected": True,
                "user_id": user_id,
                "last_validated": datetime.now().isoformat(),
                "service": "broker_integration"
            }
        else:
            return {
                "status": "error",
                "message": "Invalid or expired session",
                "is_connected": False,
                "user_id": user_id
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error checking broker status: {str(e)}",
            "is_connected": False,
            "user_id": user_id
        }

@router.post("/session/validate")
async def validate_session(
    user_id: str = Depends(get_user_from_headers),
    authorization: Optional[str] = Header(None)
):
    """Validate and refresh user session"""
    try:
        # Extract access token from authorization header
        access_token = None
        if authorization and authorization.startswith('token '):
            parts = authorization.split(' ')
            if len(parts) >= 2:
                token_part = parts[1]
                if ':' in token_part:
                    access_token = token_part.split(':')[1]
        
        if not access_token:
            raise HTTPException(status_code=401, detail="No access token provided")
        
        # Validate session
        is_valid = validate_user_session(user_id, access_token)
        
        if is_valid:
            # Update session timestamp
            session_data = load_user_session(user_id)
            save_user_session(user_id, session_data)
            
            return {
                "status": "success",
                "message": "Session validated and refreshed",
                "is_valid": True,
                "user_id": user_id,
                "last_validated": datetime.now().isoformat()
            }
        else:
            return {
                "status": "error",
                "message": "Invalid or expired session",
                "is_valid": False,
                "user_id": user_id
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error validating session: {str(e)}")

@router.post("/session/create")
async def create_session(
    session_data: dict,
    user_id: str = Depends(get_user_from_headers)
):
    """Create or update user session"""
    try:
        # Save session data
        success = save_user_session(user_id, session_data)
        
        if success:
            return {
                "status": "success",
                "message": "Session created successfully",
                "user_id": user_id,
                "created_at": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create session")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating session: {str(e)}")

@router.get("/session")
async def get_session(user_id: str):
    """Get user session information"""
    try:
        session_data = load_user_session(user_id)
        
        if session_data:
            # Remove sensitive information before returning
            safe_session = {
                "status": "active",
                "user_id": user_id,
                "last_updated": session_data.get('last_updated'),
                "is_valid": True,
                "session_exists": True
            }
            return safe_session
        else:
            return {
                "status": "inactive",
                "user_id": user_id,
                "is_valid": False,
                "session_exists": False,
                "message": "No active session found"
            }
    except Exception as e:
        return {
            "status": "error",
            "user_id": user_id,
            "is_valid": False,
            "session_exists": False,
            "message": f"Error retrieving session: {str(e)}"
        }

@router.delete("/session")
async def delete_session(user_id: str = Depends(get_user_from_headers)):
    """Delete user session"""
    try:
        session_file = get_session_file_path(user_id)
        if os.path.exists(session_file):
            os.remove(session_file)
            
        return {
            "status": "success",
            "message": "Session deleted successfully",
            "user_id": user_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting session: {str(e)}")

# ========================================
# PENDING BACKEND FEATURES (Frontend Support)
# ========================================

@router.get("/holdings")
async def get_holdings(user_id: str = Depends(get_user_from_headers)):
    """Get broker holdings - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "Broker holdings are planned but not yet implemented",
        "feature": "broker_holdings",
        "user_id": user_id,
        "frontend_expectation": "Get current portfolio holdings from broker",
        "planned_features": [
            "Real-time holdings data",
            "Position tracking",
            "Portfolio composition"
        ]
    }

@router.get("/positions")
async def get_positions(user_id: str = Depends(get_user_from_headers)):
    """Get broker positions - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "Broker positions are planned but not yet implemented",
        "feature": "broker_positions",
        "user_id": user_id,
        "frontend_expectation": "Get current trading positions from broker",
        "planned_features": [
            "Open positions",
            "P&L tracking",
            "Position sizing"
        ]
    }

@router.get("/profile")
async def get_profile(user_id: str = Depends(get_user_from_headers)):
    """Get broker profile - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "Broker profile is planned but not yet implemented",
        "feature": "broker_profile",
        "user_id": user_id,
        "frontend_expectation": "Get user profile information from broker",
        "planned_features": [
            "User details",
            "Account information",
            "Trading permissions"
        ]
    }

@router.get("/margins")
async def get_margins(user_id: str = Depends(get_user_from_headers)):
    """Get broker margins - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "Broker margins are planned but not yet implemented",
        "feature": "broker_margins",
        "user_id": user_id,
        "frontend_expectation": "Get margin information from broker",
        "planned_features": [
            "Margin requirements",
            "Available margin",
            "Margin utilization"
        ]
    }

# ========================================
# ADDITIONAL MISSING ENDPOINTS (Frontend Support)
# ========================================

@router.get("/orders")
async def get_orders(user_id: str = Depends(get_user_from_headers)):
    """Get broker orders - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "Broker orders are planned but not yet implemented",
        "feature": "broker_orders",
        "user_id": user_id,
        "frontend_expectation": "Get order history and status from broker",
        "planned_features": [
            "Order history",
            "Order status tracking",
            "Order management"
        ]
    }
