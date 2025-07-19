from fastapi import APIRouter, Depends, HTTPException
from .service import portfolio_service
from .models import FetchResponse
from ..auth.router import get_user_from_headers
from ..database.service import get_latest_portfolio_snapshot as get_snapshot_from_db

router = APIRouter(prefix="/api/portfolio", tags=["Portfolio"])

@router.post("/fetch-live", response_model=FetchResponse)
async def fetch_live_portfolio(user_id: str = Depends(get_user_from_headers)):
    """
    Fetches the latest portfolio from the broker, stores it, and returns it.
    """
    try:
        snapshot = portfolio_service.fetch_and_store_portfolio(user_id)
        return FetchResponse(
            success=True, 
            message="Portfolio fetched successfully",
            data=snapshot
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch portfolio: {str(e)}")

@router.get("/latest")
async def get_latest_portfolio(user_id: str = Depends(get_user_from_headers)):
    """
    Returns the latest stored portfolio snapshot from the database.
    """
    try:
        snapshot = get_snapshot_from_db(user_id)
        if not snapshot:
            raise HTTPException(status_code=404, detail="No portfolio data found")
        
        return {
            "success": True,
            "message": "Latest portfolio retrieved",
            "data": snapshot
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve portfolio: {str(e)}")

@router.get("/holdings")
async def get_holdings(user_id: str = Depends(get_user_from_headers)):
    """Get portfolio holdings"""
    try:
        snapshot = get_snapshot_from_db(user_id)
        if not snapshot:
            return {"holdings": []}
        
        return {
            "success": True,
            "holdings": snapshot.get("holdings", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get holdings: {str(e)}")

@router.get("/positions")
async def get_positions(user_id: str = Depends(get_user_from_headers)):
    """Get portfolio positions"""
    try:
        snapshot = get_snapshot_from_db(user_id)
        if not snapshot:
            return {"positions": []}
        
        return {
            "success": True,
            "positions": snapshot.get("positions", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get positions: {str(e)}")

# ========================================
# PENDING BACKEND FEATURES (Frontend Support)
# ========================================

@router.get("/data")
async def get_portfolio_data(user_id: str = Depends(get_user_from_headers)):
    """Get portfolio data - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "Portfolio data endpoint is planned but not yet implemented",
        "feature": "portfolio_data",
        "user_id": user_id,
        "frontend_expectation": "Get comprehensive portfolio data",
        "planned_features": [
            "Portfolio summary",
            "Performance metrics",
            "Asset allocation"
        ]
    }

@router.get("/live")
async def get_live_portfolio(user_id: str = Depends(get_user_from_headers)):
    """Get live portfolio - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "Live portfolio endpoint is planned but not yet implemented",
        "feature": "live_portfolio",
        "user_id": user_id,
        "frontend_expectation": "Get real-time portfolio data",
        "planned_features": [
            "Real-time updates",
            "Live pricing",
            "Instant P&L"
        ]
    } 