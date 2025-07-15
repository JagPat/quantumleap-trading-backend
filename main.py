<<<<<<< HEAD
import os
from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from app.core.config import settings
from app.logger import logger
from app.database.service import init_db
from app.auth.router import router as auth_router
from app.portfolio.router import router as portfolio_router
from app.ai_engine.router import router as ai_router, alt_router as ai_alt_router

# Initialize the database
init_db()

app = FastAPI(
    title="QuantumLeap Trading Backend API",
    description="Modernized API with modular architecture for broker authentication, portfolio management, and AI-powered trading operations.",
    version="2.0.0"
)

# CORS Middleware
=======
"""
QuantumLeap Trading Backend - Modernized Main Application
Version: 2.0.0

Modular architecture with separate authentication, portfolio, and trading modules.
"""
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles

# Import configuration
from app.core.config import settings

# Import database initialization
from app.database.service import init_database

# Import routers
from app.auth.router import router as auth_router
from app.portfolio.router import router as portfolio_router

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Modernized API with modular architecture for broker authentication, portfolio management, and trading operations."
)

# # Add session middleware for OAuth state management
# app.add_middleware(
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "a-secure-secret-key"),
)

>>>>>>> 1dc30303b85cf886c4618fb5b1e5e73642d1324b
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

<<<<<<< HEAD
@app.on_event("startup")
async def startup_event():
    logger.info("Starting QuantumLeap Trading Backend")
    logger.info("Database initialized.")

@app.get("/")
async def root():
    """Root endpoint for basic health check."""
    return {
        "status": "healthy",
        "architecture": "modular",
        "features": ["auth", "portfolio", "ai_engine"]
    }

@app.get("/health")
async def health_check():
    """Simple health check endpoint for Railway deployment"""
    return {"status": "ok"}

# Include modular routers
app.include_router(auth_router)
app.include_router(portfolio_router)
app.include_router(ai_router)
app.include_router(ai_alt_router)


# Legacy compatibility endpoints (if needed, but ideally removed in favor of direct calls to new endpoints)
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
    
    port = int(os.environ.get("PORT", 8000))
    
    print(f"🚀 Starting QuantumLeap Trading Backend on port {port}")
    print(f"🔧 Debug mode: {settings.debug}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
=======
# Initialize database on startup
@app.on_event("startup")
async def on_startup():
    """Initialize database and startup tasks"""
    logger.info("Starting QuantumLeap Trading Backend")
    init_database()
    logger.info("Database initialized.")

# # Include routers
app.include_router(auth_router, prefix="/api/auth")
app.include_router(portfolio_router)

# # Serve frontend static files - adjust the path as needed
# # This assumes your 'dist' or 'build' folder from the frontend is placed at the root
# # of the backend project in a folder named 'static'.
# try:
#     app.mount("/", StaticFiles(directory="static", html=True), name="static")
# except RuntimeError:
#     logger.warning("Static files directory not found. Skipping mount.")

# Health check endpoints
@app.get("/health")
async def health_check():
    """Simple health check endpoint for Railway deployment"""
    return {"status": "ok"} 
>>>>>>> 1dc30303b85cf886c4618fb5b1e5e73642d1324b
