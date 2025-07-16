"""
Broker Router
FastAPI router for broker-related endpoints
"""
from fastapi import APIRouter, Header, Depends
from typing import Optional

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

# ========================================
# PENDING BACKEND FEATURES (Frontend Support)
# ========================================

@router.get("/status")
async def get_broker_status():
    """Get broker service status"""
    return {
        "status": "operational",
        "service": "broker_integration",
        "message": "Broker service is running",
        "endpoints": {
            "holdings": "/api/broker/holdings",
            "positions": "/api/broker/positions", 
            "profile": "/api/broker/profile",
            "margins": "/api/broker/margins"
        },
        "features": {
            "authentication": "planned",
            "portfolio_sync": "planned",
            "trading": "planned"
        }
    }

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
