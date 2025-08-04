from fastapi import APIRouter, Depends, HTTPException, Query
from .service import portfolio_service
from .models import FetchResponse
from ..auth.dependencies import get_user_from_headers
from ..database.service import get_latest_portfolio_snapshot as get_snapshot_from_db, init_database, check_database_health
import sqlite3
from ..core.config import settings
from datetime import datetime
import json

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])

@router.post("/fetch-live", response_model=FetchResponse)
async def fetch_live_portfolio(user_id: str = Depends(get_user_from_headers)):
    """
    Fetches the latest portfolio from the broker, stores it, and returns it.
    """
    try:
        snapshot = portfolio_service.fetch_and_store_portfolio(user_id)
        # Convert snapshot to dict to avoid serialization issues
        snapshot_dict = {
            "user_id": snapshot.user_id,
            "timestamp": snapshot.timestamp,
            "holdings": snapshot.holdings,
            "positions": snapshot.positions,
            "total_value": snapshot.total_value,
            "day_pnl": snapshot.day_pnl,
            "total_pnl": snapshot.total_pnl,
            "summary": {
                "total_value": snapshot.total_value,
                "day_pnl": snapshot.day_pnl,
                "total_pnl": snapshot.total_pnl,
                "holdings_count": len(snapshot.holdings) if snapshot.holdings else 0,
                "positions_count": len(snapshot.positions) if snapshot.positions else 0
            }
        }
        return FetchResponse(
            success=True, 
            message="Portfolio fetched successfully",
            data=snapshot_dict
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch portfolio: {str(e)}")

@router.get("/latest")
async def get_latest_portfolio(user_id: str = Depends(get_user_from_headers)):
    """
    Returns the latest stored portfolio snapshot from the database.
    """
    try:
        snapshot = portfolio_service.get_latest_portfolio(user_id)
        if not snapshot:
            raise HTTPException(status_code=404, detail="No portfolio data found")
        
        # Convert snapshot to dict to avoid serialization issues
        snapshot_dict = {
            "user_id": snapshot.user_id,
            "timestamp": snapshot.timestamp,
            "holdings": snapshot.holdings,
            "positions": snapshot.positions,
            "total_value": snapshot.total_value,
            "day_pnl": snapshot.day_pnl,
            "total_pnl": snapshot.total_pnl,
            "summary": {
                "total_value": snapshot.total_value,
                "day_pnl": snapshot.day_pnl,
                "total_pnl": snapshot.total_pnl,
                "holdings_count": len(snapshot.holdings) if snapshot.holdings else 0,
                "positions_count": len(snapshot.positions) if snapshot.positions else 0
            }
        }
        
        return {
            "status": "success",
            "success": True,
            "message": "Latest portfolio retrieved",
            "data": snapshot_dict
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve portfolio: {str(e)}")

# New endpoints for easier testing without auth headers
@router.get("/fetch-live-simple")
async def fetch_live_portfolio_simple(user_id: str = Query(..., description="User ID")):
    """
    Simplified version that accepts user_id as query parameter for testing.
    """
    try:
        snapshot = portfolio_service.fetch_and_store_portfolio(user_id)
        snapshot_dict = {
            "user_id": snapshot.user_id,
            "timestamp": snapshot.timestamp,
            "holdings": snapshot.holdings,
            "positions": snapshot.positions,
            "total_value": snapshot.total_value,
            "day_pnl": snapshot.day_pnl,
            "total_pnl": snapshot.total_pnl,
            "summary": {
                "total_value": snapshot.total_value,
                "day_pnl": snapshot.day_pnl,
                "total_pnl": snapshot.total_pnl,
                "holdings_count": len(snapshot.holdings) if snapshot.holdings else 0,
                "positions_count": len(snapshot.positions) if snapshot.positions else 0
            }
        }
        return {
            "status": "success",
            "success": True,
            "message": "Portfolio fetched successfully",
            "data": snapshot_dict
        }
    except Exception as e:
        return {
            "status": "error",
            "success": False,
            "message": f"Failed to fetch portfolio: {str(e)}",
            "data": None
        }

@router.get("/latest-simple")
async def get_latest_portfolio_simple(user_id: str = Query(..., description="User ID")):
    """
    Simplified version that accepts user_id as query parameter for testing.
    """
    try:
        snapshot = portfolio_service.get_latest_portfolio(user_id)
        if not snapshot:
            return {
                "status": "error",
                "success": False,
                "message": "No portfolio data found",
                "data": None
            }
        
        # Convert snapshot to dict to avoid serialization issues
        snapshot_dict = {
            "user_id": snapshot.user_id,
            "timestamp": snapshot.timestamp,
            "holdings": snapshot.holdings,
            "positions": snapshot.positions,
            "total_value": snapshot.total_value,
            "day_pnl": snapshot.day_pnl,
            "total_pnl": snapshot.total_pnl,
            "summary": {
                "total_value": snapshot.total_value,
                "day_pnl": snapshot.day_pnl,
                "total_pnl": snapshot.total_pnl,
                "holdings_count": len(snapshot.holdings) if snapshot.holdings else 0,
                "positions_count": len(snapshot.positions) if snapshot.positions else 0
            }
        }
        
        return {
            "status": "success",
            "success": True,
            "message": "Latest portfolio retrieved",
            "data": snapshot_dict
        }
    except Exception as e:
        return {
            "status": "error",
            "success": False,
            "message": f"Failed to retrieve portfolio: {str(e)}",
            "data": None
        }

@router.get("/mock")
async def get_mock_portfolio(user_id: str = Query("test_user", description="User ID")):
    """
    Returns mock portfolio data for testing and development.
    """
    mock_data = {
        "user_id": user_id,
        "timestamp": datetime.now().isoformat(),
        "holdings": [
            {
                "tradingsymbol": "RELIANCE-EQ",
                "exchange": "NSE",
                "isin": "INE002A01018",
                "quantity": 100,
                "t1_quantity": 0,
                "average_price": 2450.50,
                "last_price": 2480.75,
                "pnl": 3025.00,
                "product": "CNC"
            },
            {
                "tradingsymbol": "TCS-EQ",
                "exchange": "NSE", 
                "isin": "INE467B01029",
                "quantity": 50,
                "t1_quantity": 0,
                "average_price": 3850.25,
                "last_price": 3920.50,
                "pnl": 3512.50,
                "product": "CNC"
            }
        ],
        "positions": [
            {
                "tradingsymbol": "NIFTY25JUL5200CE",
                "exchange": "NFO",
                "product": "NRML",
                "quantity": 1,
                "average_price": 45.50,
                "last_price": 52.75,
                "pnl": 725.00,
                "net_quantity": 1
            }
        ],
        "total_value": 125000.00,
        "day_pnl": 7262.50,
        "total_pnl": 15250.00
    }
    
    return {
        "status": "success",
        "success": True,
        "message": "Mock portfolio data retrieved",
        "data": mock_data
    }

@router.get("/status")
async def portfolio_status():
    """
    Portfolio service status endpoint.
    """
    return {
        "status": "operational",
        "service": "portfolio",
        "endpoints": {
            "fetch_live": "/api/portfolio/fetch-live",
            "latest": "/api/portfolio/latest", 
            "fetch_live_simple": "/api/portfolio/fetch-live-simple",
            "latest_simple": "/api/portfolio/latest-simple",
            "mock": "/api/portfolio/mock",
            "summary": "/api/portfolio/summary",
            "performance": "/api/portfolio/performance",
            "status": "/api/portfolio/status"
        },
        "timestamp": datetime.now().isoformat()
    }

@router.get("/holdings")
async def get_holdings(user_id: str = Depends(get_user_from_headers)):
    """Get portfolio holdings"""
    try:
        snapshot = get_snapshot_from_db(user_id)
        if not snapshot:
            return {"holdings": []}
        
        # Parse JSON string to list
        holdings_json = snapshot.get("holdings", "[]")
        holdings = json.loads(holdings_json) if holdings_json else []
        
        return {
            "success": True,
            "holdings": holdings
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
        
        # Parse JSON string to list
        positions_json = snapshot.get("positions", "[]")
        positions = json.loads(positions_json) if positions_json else []
        
        return {
            "success": True,
            "positions": positions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get positions: {str(e)}")

@router.get("/debug-db")
async def debug_database():
    """Debug database connection and tables"""
    try:
        # Use the comprehensive database health check
        health_status = check_database_health()
        
        return {
            "success": True,
            "database_health": health_status
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "database_path": settings.database_path
        }

@router.get("/summary")
async def get_portfolio_summary(user_id: str = Query(..., description="User ID")):
    """
    Get portfolio summary with key metrics
    """
    try:
        snapshot = portfolio_service.get_latest_portfolio(user_id)
        if not snapshot:
            return {
                "status": "error",
                "success": False,
                "message": "No portfolio data found",
                "data": None
            }
        
        # Calculate additional summary metrics
        holdings_count = len(snapshot.holdings) if snapshot.holdings else 0
        positions_count = len(snapshot.positions) if snapshot.positions else 0
        
        # Calculate percentage changes (mock for now)
        day_pnl_percent = (snapshot.day_pnl / snapshot.total_value * 100) if snapshot.total_value > 0 else 0
        total_pnl_percent = (snapshot.total_pnl / (snapshot.total_value - snapshot.total_pnl) * 100) if (snapshot.total_value - snapshot.total_pnl) > 0 else 0
        
        summary_data = {
            "user_id": snapshot.user_id,
            "timestamp": snapshot.timestamp,
            "total_value": snapshot.total_value,
            "day_pnl": snapshot.day_pnl,
            "day_pnl_percent": round(day_pnl_percent, 2),
            "total_pnl": snapshot.total_pnl,
            "total_pnl_percent": round(total_pnl_percent, 2),
            "holdings_count": holdings_count,
            "positions_count": positions_count,
            "invested_value": snapshot.total_value - snapshot.total_pnl,
            "current_value": snapshot.total_value
        }
        
        return {
            "status": "success",
            "success": True,
            "message": "Portfolio summary retrieved",
            "data": summary_data
        }
        
    except Exception as e:
        return {
            "status": "error",
            "success": False,
            "message": f"Failed to get portfolio summary: {str(e)}",
            "data": None
        }

@router.get("/performance")
async def get_portfolio_performance(
    user_id: str = Query(..., description="User ID"),
    timeframe: str = Query("1M", description="Timeframe: 1D, 1W, 1M, 3M, 6M, 1Y")
):
    """
    Get portfolio performance metrics over specified timeframe
    """
    try:
        # For now, return mock performance data
        # In production, this would calculate actual historical performance
        
        mock_performance = {
            "user_id": user_id,
            "timeframe": timeframe,
            "timestamp": datetime.now().isoformat(),
            "performance_metrics": {
                "total_return": 12.5,
                "total_return_percent": 8.3,
                "annualized_return": 15.2,
                "volatility": 18.7,
                "sharpe_ratio": 0.81,
                "max_drawdown": -5.2,
                "win_rate": 68.5,
                "best_day": 3.2,
                "worst_day": -2.8
            },
            "historical_values": [
                {"date": "2024-01-01", "value": 100000},
                {"date": "2024-01-15", "value": 102500},
                {"date": "2024-02-01", "value": 105200},
                {"date": "2024-02-15", "value": 103800},
                {"date": "2024-03-01", "value": 108300},
                {"date": "2024-03-15", "value": 112500}
            ],
            "benchmark_comparison": {
                "benchmark": "NIFTY 50",
                "portfolio_return": 12.5,
                "benchmark_return": 8.7,
                "alpha": 3.8,
                "beta": 1.15,
                "correlation": 0.85
            }
        }
        
        return {
            "status": "success",
            "success": True,
            "message": f"Portfolio performance for {timeframe} retrieved",
            "data": mock_performance
        }
        
    except Exception as e:
        return {
            "status": "error",
            "success": False,
            "message": f"Failed to get portfolio performance: {str(e)}",
            "data": None
        }

@router.delete("/cleanup/{user_id}")
async def cleanup_portfolio_data(user_id: str):
    """
    Clean malformed portfolio data for a specific user
    """
    try:
        # Connect to database
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        # First, check what data exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM portfolio_snapshots 
            WHERE user_id = ?
        """, (user_id,))
        
        existing_count = cursor.fetchone()[0]
        
        if existing_count == 0:
            conn.close()
            return {
                "status": "success",
                "message": f"No portfolio data found for user {user_id}",
                "deleted_count": 0
            }
        
        # Delete all portfolio snapshots for this user
        cursor.execute("""
            DELETE FROM portfolio_snapshots 
            WHERE user_id = ?
        """, (user_id,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return {
            "status": "success",
            "message": f"Cleaned {deleted_count} portfolio snapshots for user {user_id}",
            "deleted_count": deleted_count,
            "user_id": user_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database cleanup failed: {str(e)}")

