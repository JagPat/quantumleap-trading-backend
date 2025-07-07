from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sqlite3
import os
import logging
from datetime import datetime
from kiteconnect import KiteConnect
import hashlib
from cryptography.fernet import Fernet
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="QuantumLeap Trading - Backend API",
    version="1.0.0",
    description="API specification for the backend service that connects to a broker (e.g., Kite Connect) and powers the QuantumLeap Trading frontend."
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
DATABASE_PATH = "trading_app.db"

# Encryption key for storing sensitive data
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", Fernet.generate_key())
cipher_suite = Fernet(ENCRYPTION_KEY)

def encrypt_data(data: str) -> str:
    """Encrypt sensitive data"""
    return cipher_suite.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt sensitive data"""
    return cipher_suite.decrypt(encrypted_data.encode()).decode()

def init_database():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Create users table for storing broker credentials
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            api_key TEXT NOT NULL,
            api_secret TEXT NOT NULL,
            access_token TEXT,
            user_name TEXT,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_database()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "QuantumLeap Trading Backend API is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Import additional modules
from models import (
    GenerateSessionRequest, GenerateSessionResponse, UserData,
    PortfolioSummaryResponse, PortfolioSummaryData,
    HoldingsResponse, HoldingItem, PositionsResponse, ErrorResponse
)
from database import store_user_credentials, get_user_credentials, user_exists
from kite_service import (
    KiteService, get_kite_service, calculate_portfolio_summary, format_holdings_data
)
from kiteconnect.exceptions import KiteException

@app.get("/api/broker/callback", tags=["Broker Authentication"])
async def broker_callback(request: Request, request_token: str = Query(...), action: str = Query(...)):
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
        # Remove any URL encoding and ensure it's a clean token
        clean_token = request_token.strip()
        
        # Validate that this looks like a proper request_token (not a URL)
        if clean_token.startswith('http') or '://' in clean_token:
            logger.error(f"Invalid request_token format - appears to be a URL: {clean_token}")
            # Try to extract token from URL - Zerodha uses sess_id parameter for request_token
            import urllib.parse as urlparse
            parsed_url = urlparse.urlparse(clean_token)
            query_params = urlparse.parse_qs(parsed_url.query)
            
            # Check for request_token parameter first
            if 'request_token' in query_params:
                clean_token = query_params['request_token'][0]
                logger.info(f"Extracted token from request_token parameter: {clean_token}")
            # Check for sess_id parameter (Zerodha's format)
            elif 'sess_id' in query_params:
                clean_token = query_params['sess_id'][0]
                logger.info(f"Extracted token from sess_id parameter: {clean_token}")
            else:
                logger.error(f"Could not find token in URL parameters: {query_params}")
                raise HTTPException(status_code=400, detail="No valid token found in URL parameters")
        
        # Additional validation - Zerodha request tokens are typically alphanumeric
        if not clean_token or len(clean_token) < 10 or not clean_token.replace('_', '').replace('-', '').isalnum():
            logger.error(f"Request token appears invalid or too short: {clean_token}")
            raise HTTPException(status_code=400, detail="Invalid request_token received from Zerodha")
        
        logger.info(f"Cleaned request_token: {clean_token}")
        
        # Redirect to frontend with the cleaned request_token
        frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:8501")
        redirect_url = f"{frontend_url}/BrokerCallback?request_token={clean_token}&action={action}"
        
        logger.info(f"Redirecting to: {redirect_url}")
        
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        logger.error(f"Error in broker_callback: {str(e)}")
        raise HTTPException(status_code=500, detail="Callback processing failed")

@app.post("/api/broker/generate-session", tags=["Broker Authentication"])
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
    try:
        # Create KiteService instance
        kite_service = KiteService(
            api_key=request.api_key,
            api_secret=request.api_secret
        )
        
        # Generate session with request token
        session_data = kite_service.generate_session(request.request_token)
        access_token = session_data.get("access_token")
        
        if not access_token:
            return {"status": "error", "message": "Failed to generate access token from Zerodha"}
        
        # Get user profile to get user_id for storage
        kite_service.kite.set_access_token(access_token)
        profile = kite_service.get_profile()
        
        user_id = profile.get("user_id", "")
        user_name = profile.get("user_name", "")
        email = profile.get("email", "")
        
        if not user_id:
            return {"status": "error", "message": "Unable to retrieve user ID from Zerodha profile"}
        
        # Store credentials in database using user_id from profile
        success = store_user_credentials(
            user_id=user_id,
            api_key=request.api_key,
            api_secret=request.api_secret,
            access_token=access_token,
            user_name=user_name,
            email=email
        )
        
        if not success:
            return {"status": "error", "message": "Failed to store user credentials securely"}
        
        logger.info(f"Successfully generated session for user: {user_id}")
        
        # Return the session data with access_token and user_data as required by Base44
        return {
            "status": "success", 
            "access_token": access_token,
            "user_data": {
                "user_id": user_id,
                "user_name": user_name,
                "email": email,
                "profile": profile
            }
        }
        
    except KiteException as e:
        logger.error(f"Kite API error in generate_session: {str(e)}")
        return {"status": "error", "message": f"The error from Zerodha was: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error in generate_session: {str(e)}")
        return {"status": "error", "message": f"Internal server error: {str(e)}"}

@app.get("/api/portfolio/summary", response_model=PortfolioSummaryResponse, tags=["Portfolio Data"])
async def get_portfolio_summary(user_id: str = Query(..., description="User ID")):
    """
    Get Portfolio Summary
    
    Fetches a high-level summary of the user's portfolio, including P&L.
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
async def get_holdings(user_id: str = Query(..., description="User ID")):
    """
    Get Holdings
    
    Fetches the user's long-term equity holdings from the broker.
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
async def get_positions(user_id: str = Query(..., description="User ID")):
    """
    Get Positions
    
    Fetches the user's current day (intraday and F&O) positions from the broker.
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