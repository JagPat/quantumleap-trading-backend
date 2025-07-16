"""
Fallback Portfolio Router - Development Debug Mode
Provides all portfolio endpoints with placeholder responses when the main portfolio service fails to load.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict, Any
from pydantic import BaseModel

# Simple models for fallback responses
class PortfolioStatusResponse(BaseModel):
    status: str
    message: str
    mode: str
    endpoints: list

class PortfolioDataResponse(BaseModel):
    status: str
    data: Optional[Dict[str, Any]] = None
    message: str

class FetchResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None

router = APIRouter(prefix="/api/portfolio", tags=["Portfolio - Fallback"])

def get_user_id_from_headers(
    authorization: Optional[str] = None,
    x_user_id: Optional[str] = None
) -> str:
    """Extract user ID from headers for fallback router"""
    return x_user_id or "debug_user"

@router.get("/status", response_model=PortfolioStatusResponse)
async def portfolio_status():
    """Portfolio service status endpoint - always available in fallback mode"""
    return PortfolioStatusResponse(
        status="fallback",
        message="Portfolio service running in fallback mode - main service failed to load",
        mode="debug",
        endpoints=[
            "/api/portfolio/status",
            "/api/portfolio/latest", 
            "/api/portfolio/fetch-live",
            "/api/portfolio/holdings",
            "/api/portfolio/positions"
        ]
    )

@router.get("/latest", response_model=PortfolioDataResponse)
async def get_latest_portfolio(user_id: str = "debug_user"):
    """Get latest portfolio data - fallback placeholder"""
    return PortfolioDataResponse(
        status="fallback",
        data={
            "user_id": user_id,
            "timestamp": "2024-07-16T00:00:00Z",
            "holdings": [],
            "positions": {"net": [], "day": []},
            "total_value": 0.0,
            "total_pnl": 0.0
        },
        message="Portfolio service not available - showing fallback data"
    )

@router.post("/fetch-live", response_model=FetchResponse)
async def fetch_live_portfolio(user_id: str = "debug_user"):
    """Fetch live portfolio data - fallback placeholder"""
    return FetchResponse(
        status="fallback",
        message="Portfolio service not available - cannot fetch live data",
        data={
            "user_id": user_id,
            "timestamp": "2024-07-16T00:00:00Z",
            "status": "not_available"
        }
    )

@router.get("/holdings", response_model=PortfolioDataResponse)
async def get_holdings(user_id: str = "debug_user"):
    """Get portfolio holdings - fallback placeholder"""
    return PortfolioDataResponse(
        status="fallback",
        data={
            "user_id": user_id,
            "holdings": [],
            "message": "No holdings available - portfolio service in fallback mode"
        },
        message="Portfolio service not available - showing empty holdings"
    )

@router.get("/positions", response_model=PortfolioDataResponse)
async def get_positions(user_id: str = "debug_user"):
    """Get portfolio positions - fallback placeholder"""
    return PortfolioDataResponse(
        status="fallback",
        data={
            "user_id": user_id,
            "positions": {"net": [], "day": []},
            "message": "No positions available - portfolio service in fallback mode"
        },
        message="Portfolio service not available - showing empty positions"
    )

@router.get("/summary", response_model=PortfolioDataResponse)
async def get_portfolio_summary(user_id: str = "debug_user"):
    """Get portfolio summary - fallback placeholder"""
    return PortfolioDataResponse(
        status="fallback",
        data={
            "user_id": user_id,
            "total_value": 0.0,
            "total_pnl": 0.0,
            "todays_pnl": 0.0,
            "total_invested": 0.0,
            "total_pnl_percentage": 0.0
        },
        message="Portfolio service not available - showing zero summary"
    ) 