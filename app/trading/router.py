"""
Trading Router
FastAPI router for trading-related endpoints
"""
from fastapi import APIRouter, Header, Depends
from typing import Optional

router = APIRouter(prefix="/api/trading", tags=["Trading Operations"])

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

@router.get("/positions")
async def get_trading_positions(user_id: str = Depends(get_user_from_headers)):
    """Get trading positions - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "Trading positions are planned but not yet implemented",
        "feature": "trading_positions",
        "user_id": user_id,
        "frontend_expectation": "Get active trading positions",
        "planned_features": [
            "Open positions",
            "Position sizing",
            "Risk management"
        ]
    }
