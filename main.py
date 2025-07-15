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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
