#!/usr/bin/env python3
"""
Quantum Leap Trading Platform - Production Backend
Fixed version for Railway deployment with AI components
"""

import os
import sys
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Quantum Leap Trading Platform",
    description="AI-powered trading platform with comprehensive portfolio management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint (CRITICAL for Railway deployment)
@app.get("/health")
async def health_check():
    """Health check endpoint for Railway deployment"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "quantum-leap-backend",
        "version": "1.0.0",
        "port": os.environ.get("PORT", "8000")
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Quantum Leap Trading Platform API",
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "docs": "/docs",
        "health": "/health",
        "version": "1.0.0"
    }

# Import and include routers with error handling
routers_loaded = []

try:
    # Import new AI components router first
    from app.ai_engine.ai_components_router import router as ai_components_router
    app.include_router(ai_components_router, prefix="/api")
    routers_loaded.append("AI Components")
    logger.info("✅ AI Components router loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️  AI Components router not available: {str(e)}")

try:
    # Import existing routers
    from app.portfolio.router import router as portfolio_router
    app.include_router(portfolio_router, prefix="/api")
    routers_loaded.append("Portfolio")
    logger.info("✅ Portfolio router loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️  Portfolio router not available: {str(e)}")

try:
    from app.broker.router import router as broker_router
    app.include_router(broker_router, prefix="/api")
    routers_loaded.append("Broker")
    logger.info("✅ Broker router loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️  Broker router not available: {str(e)}")

try:
    from app.trading_engine.simple_router import router as trading_engine_router
    app.include_router(trading_engine_router, prefix="/api")
    routers_loaded.append("Trading Engine")
    logger.info("✅ Trading Engine router loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️  Trading Engine router not available: {str(e)}")

try:
    from app.ai_engine.simple_analysis_router import router as ai_router
    app.include_router(ai_router, prefix="/api")
    routers_loaded.append("AI Analysis")
    logger.info("✅ AI Analysis router loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️  AI Analysis router not available: {str(e)}")

# Status endpoint showing loaded routers
@app.get("/status")
async def status():
    """Status endpoint showing loaded components"""
    return {
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "routers_loaded": routers_loaded,
        "total_routers": len(routers_loaded),
        "environment": os.environ.get("RAILWAY_ENVIRONMENT", "development"),
        "port": os.environ.get("PORT", "8000")
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    # Get port from environment variable (Railway sets this)
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"  # CRITICAL: Must bind to 0.0.0.0 for Railway
    
    logger.info(f"🚀 Starting Quantum Leap Trading Platform")
    logger.info(f"   Host: {host}")
    logger.info(f"   Port: {port}")
    logger.info(f"   Routers loaded: {len(routers_loaded)}")
    logger.info(f"   Environment: {os.environ.get('RAILWAY_ENVIRONMENT', 'development')}")
    
    # Run with uvicorn
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )