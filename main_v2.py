"""
QuantumLeap Trading Backend - Modernized Main Application
Version: 2.0.0

Modular architecture with separate authentication, portfolio, and trading modules.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# Import configuration
from app.core.config import settings

# Import database initialization
from app.database.service import init_database

# Import routers
from app.auth.router import router as auth_router

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

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
    logger.info("Starting QuantumLeap Trading Backend v2.0.0")
    init_database()
    logger.info("Database initialized successfully")

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main_v2:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    ) 