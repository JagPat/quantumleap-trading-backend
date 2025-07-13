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
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime
from kiteconnect.exceptions import KiteException
from typing import Optional
from fastapi.staticfiles import StaticFiles

# Import configuration
from app.core.config import settings

# Import database initialization
from app.database.service import init_database

# Import routers
from app.auth.router import router as auth_router
from app.portfolio.router import router as portfolio_router

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

# Add session middleware for OAuth state management
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "a-secure-secret-key"),
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def on_startup():
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
app.include_router(portfolio_router)

# Serve frontend static files - adjust the path as needed
# This assumes your 'dist' or 'build' folder from the frontend is placed at the root
# of the backend project in a folder named 'static'.
try:
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
except RuntimeError:
    logger.warning("Static files directory not found. Skipping mount.")

# Health check endpoints
@app.get("/")
def read_root():
    """Root endpoint"""
    return {"message": "Welcome to QuantumLeap Trading Backend"}

@app.get("/health")
async def health_check():
    """Simple health check endpoint for Railway deployment"""
    return {"status": "healthy"}

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
    
    # Get Railway PORT if available
    port = int(os.environ.get("PORT", 8000))
    
    print(f"🚀 Starting QuantumLeap Trading Backend on port {port}")
    print(f"🔧 Debug mode: {settings.debug}")
    
    uvicorn.run(app, host="0.0.0.0", port=port) 