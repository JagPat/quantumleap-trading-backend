"""
QuantumLeap Trading Backend - Modernized Main Application
Version: 2.0.0

Modular architecture with separate authentication, portfolio, and trading modules.
"""
import logging
import os
import sys
from fastapi import FastAPI, Query, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime
from kiteconnect.exceptions import KiteException
from typing import Optional

# Import configuration
from app.core.config import settings

# Import database initialization
from app.database.service import init_database

# Import routers
from app.auth.router import router as auth_router

# Import models and services for portfolio endpoints
from models import PortfolioSummaryResponse, PortfolioSummaryData, HoldingsResponse, PositionsResponse
from kite_service import KiteService, get_kite_service, calculate_portfolio_summary, format_holdings_data

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

# Security scheme for API documentation
security = HTTPBearer()

def get_user_from_headers(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> str:
    """
    Extract user ID from Kite Connect authorization headers.
    
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
        
        logger.info(f"🔐 Authentication extracted - user_id: {user_id}, api_key: {api_key[:8]}...")
        return user_id
        
    except ValueError as e:
        logger.error(f"Failed to parse authorization header: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Modernized API with modular architecture for broker authentication, portfolio management, and trading operations."
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database and startup tasks"""
    logger.info("🚀 Starting QuantumLeap Trading Backend v2.0.0")
    logger.info(f"📍 Current working directory: {os.getcwd()}")
    logger.info(f"🔧 Python path: {sys.path[:3]}")
    logger.info(f"⚙️ Settings loaded: {settings.app_name}")
    
    try:
        init_database()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}")
        raise
    
    logger.info("✅ Backend startup complete - all modules loaded")

# Include routers
app.include_router(auth_router)

# Health check endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"{settings.app_name} v{settings.app_version}",
        "status": "healthy",
        "architecture": "modular"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "version": settings.app_version
    }

# Portfolio endpoints with header-based authentication
@app.get("/api/portfolio/data", tags=["Portfolio Data"])
async def get_portfolio_data(user_id: str = Depends(get_user_from_headers)):
    """
    Get Portfolio Data
    
    Fetches combined portfolio data including summary, holdings, and positions.
    Requires Kite Connect authorization header: Authorization: token api_key:access_token
    """
    try:
        # Get KiteService for user
        kite_service = get_kite_service(user_id)
        if not kite_service:
            raise HTTPException(status_code=401, detail="Unauthorized or broker not connected")
        
        # Fetch all portfolio data
        holdings = kite_service.get_holdings()
        positions = kite_service.get_positions()
        
        # Calculate portfolio summary
        summary = calculate_portfolio_summary(holdings, positions)
        
        # Format holdings data
        formatted_holdings = format_holdings_data(holdings)
        
        logger.info(f"Successfully fetched portfolio data for user: {user_id}")
        
        return {
            "status": "success",
            "data": {
                "summary": summary,
                "holdings": formatted_holdings,
                "positions": positions
            }
        }
        
    except KiteException as e:
        logger.error(f"Kite API error in get_portfolio_data: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Broker API error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_portfolio_data: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/portfolio/summary", response_model=PortfolioSummaryResponse, tags=["Portfolio Data"])
async def get_portfolio_summary(user_id: str = Depends(get_user_from_headers)):
    """
    Get Portfolio Summary
    
    Fetches a high-level summary of the user's portfolio, including P&L.
    Requires Kite Connect authorization header: Authorization: token api_key:access_token
    """
    try:
        # Get KiteService for user
        kite_service = get_kite_service(user_id)
        if not kite_service:
            raise HTTPException(status_code=401, detail="Unauthorized or broker not connected")
        
        # Fetch holdings and positions
        holdings = kite_service.get_holdings()
        positions = kite_service.get_positions()
        
        # Calculate portfolio summary
        summary = calculate_portfolio_summary(holdings, positions)
        
        logger.info(f"Successfully fetched portfolio summary for user: {user_id}")
        
        return PortfolioSummaryResponse(
            status="success",
            data=PortfolioSummaryData(
                total_value=summary["total_value"],
                total_pnl=summary["total_pnl"],
                todays_pnl=summary["todays_pnl"]
            )
        )
        
    except KiteException as e:
        logger.error(f"Kite API error in get_portfolio_summary: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Broker API error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_portfolio_summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/portfolio/holdings", response_model=HoldingsResponse, tags=["Portfolio Data"])
async def get_holdings(user_id: str = Depends(get_user_from_headers)):
    """
    Get Holdings
    
    Fetches the user's long-term equity holdings from the broker.
    Requires Kite Connect authorization header: Authorization: token api_key:access_token
    """
    try:
        # Get KiteService for user
        kite_service = get_kite_service(user_id)
        if not kite_service:
            raise HTTPException(status_code=401, detail="Unauthorized or broker not connected")
        
        # Fetch holdings
        holdings = kite_service.get_holdings()
        
        # Format holdings data
        formatted_holdings = format_holdings_data(holdings)
        
        logger.info(f"Successfully fetched holdings for user: {user_id}")
        
        return HoldingsResponse(
            status="success",
            data=formatted_holdings
        )
        
    except KiteException as e:
        logger.error(f"Kite API error in get_holdings: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Broker API error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_holdings: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/portfolio/positions", response_model=PositionsResponse, tags=["Portfolio Data"])
async def get_positions(user_id: str = Depends(get_user_from_headers)):
    """
    Get Positions
    
    Fetches the user's current day (intraday and F&O) positions from the broker.
    Requires Kite Connect authorization header: Authorization: token api_key:access_token
    """
    try:
        # Get KiteService for user
        kite_service = get_kite_service(user_id)
        if not kite_service:
            raise HTTPException(status_code=401, detail="Unauthorized or broker not connected")
        
        # Fetch positions
        positions = kite_service.get_positions()
        
        logger.info(f"Successfully fetched positions for user: {user_id}")
        
        return PositionsResponse(
            status="success",
            data=positions
        )
        
    except KiteException as e:
        logger.error(f"Kite API error in get_positions: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Broker API error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_positions: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Legacy compatibility endpoints
# These will redirect to the new auth module endpoints
from fastapi import Request
from fastapi.responses import RedirectResponse

@app.get("/api/broker/callback")
async def legacy_broker_callback(request: Request):
    """Legacy redirect to new auth module"""
    return RedirectResponse(url=str(request.url).replace("/api/broker/callback", "/api/auth/broker/callback"))

@app.post("/api/broker/generate-session")
async def legacy_generate_session(request: Request):
    """Legacy redirect to new auth module"""
    return RedirectResponse(url=str(request.url).replace("/api/broker/generate-session", "/api/auth/broker/generate-session"))

@app.post("/api/broker/invalidate-session")
async def legacy_invalidate_session(request: Request):
    """Legacy redirect to new auth module"""
    return RedirectResponse(url=str(request.url).replace("/api/broker/invalidate-session", "/api/auth/broker/invalidate-session"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main_v2:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    ) 