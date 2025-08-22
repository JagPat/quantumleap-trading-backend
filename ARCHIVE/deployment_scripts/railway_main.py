#!/usr/bin/env python3
"""
Railway-Optimized Main Application Entry Point
Simplified version to ensure Railway deployment works
"""

import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    
    # Create FastAPI app with minimal configuration
    app = FastAPI(
        title="Quantum Leap Backend API",
        description="Automated Trading and Portfolio Management System",
        version="1.0.0"
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Simplified for Railway
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "message": "Quantum Leap Backend API",
            "version": "1.0.0",
            "status": "operational",
            "timestamp": datetime.now().isoformat(),
            "environment": os.getenv("RAILWAY_ENVIRONMENT", "production"),
            "port": os.getenv("PORT", "8000")
        }
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint for Railway"""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "environment": os.getenv("RAILWAY_ENVIRONMENT", "production")
        }
    
    @app.get("/api/status")
    async def api_status():
        """API status endpoint"""
        return {
            "api_status": "online",
            "timestamp": datetime.now().isoformat(),
            "endpoints": ["/", "/health", "/api/status"]
        }
    
    # Simple test endpoints
    @app.get("/test")
    async def test_endpoint():
        """Test endpoint to verify deployment"""
        return {
            "test": "success",
            "message": "Railway deployment is working!",
            "timestamp": datetime.now().isoformat()
        }
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """Global exception handler"""
        logger.error(f"Global exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": str(exc),
                "timestamp": datetime.now().isoformat()
            }
        )
    
    # For direct execution (Railway compatibility)
    if __name__ == "__main__":
        import uvicorn
        
        port = int(os.getenv("PORT", 8000))
        host = "0.0.0.0"
        
        logger.info(f"🚀 Starting Quantum Leap Backend on {host}:{port}")
        logger.info(f"🌍 Environment: {os.getenv('RAILWAY_ENVIRONMENT', 'development')}")
        
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info"
        )

except ImportError as e:
    logger.error(f"❌ Failed to import required modules: {e}")
    raise
except Exception as e:
    logger.error(f"❌ Failed to start application: {e}")
    raise