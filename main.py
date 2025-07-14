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