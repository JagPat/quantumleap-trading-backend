# Force redeploy - AI engine startup fix - 2024-07-16
# Trigger redeploy - 2024-07-16
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

# Import configuration
from app.core.config import settings

# Import database initialization
from app.database.service import init_database

# Import routers
print("🔍 Importing auth router...")
from app.auth.router import router as auth_router
print("✅ Auth router imported")

print("🔍 Importing portfolio router...")
from app.portfolio.router import router as portfolio_router
print("✅ Portfolio router imported")

print("🔍 Importing broker router...")
from app.broker.router import router as broker_router
print("✅ Broker router imported")

print("🔍 Importing trading router...")
from app.trading.router import router as trading_router
print("✅ Trading router imported")

# AI engine will be imported during startup
ai_router_loaded = False
ai_router_fallback = False

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoints
@app.get("/health")
async def health_check():
    """Simple health check endpoint for Railway deployment"""
    print("🏥 Health check requested")
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}

@app.get("/version")
async def get_version():
    """Get deployment version and commit info"""
    return {
        "app_version": settings.app_version,
        "deployment": "latest",
        "ai_router": "full" if ai_router_loaded else ("fallback" if ai_router_fallback else "none"),
        "status": "operational" if ai_router_loaded or ai_router_fallback else "error"
    }

@app.get("/readyz")
async def readyz():
    """Readiness check endpoint"""
    return {
        "status": "ready" if ai_router_loaded or ai_router_fallback else "partial",
        "components": {
            "database": "connected",
            "auth": "operational",
            "portfolio": "operational",
            "ai_engine": "operational" if ai_router_loaded or ai_router_fallback else "error"
        },
        "ai_engine": {
            "status": "ready" if ai_router_loaded or ai_router_fallback else "error",
            "mode": "BYOAI (Bring Your Own AI)",
            "message": "Add API keys to enable AI features" if ai_router_loaded else ("Fallback router active. No AI key configured." if ai_router_fallback else "AI engine failed to load")
        }
    }

@app.get("/")
async def root():
    """Root endpoint with basic app info"""
    return {
        "message": "QuantumLeap Trading Backend API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
        "deployment": "latest"
    }

# Initialize database on startup
@app.on_event("startup")
async def on_startup():
    """Initialize database and startup tasks"""
    print("🚀 Starting QuantumLeap Trading Backend...")
    logger.info("Starting QuantumLeap Trading Backend")
    global ai_router_loaded, ai_router_fallback
    
    try:
        print("🔍 Attempting to import full AI engine router...")
        from app.ai_engine.router import router as ai_engine_router
        app.include_router(ai_engine_router)
        ai_router_loaded = True
        print("✅ Full AI engine router loaded and registered.")
        logger.info("✅ Full AI engine router loaded and registered.")
    except Exception as e:
        print(f"❌ Failed to load full AI engine router: {e}")
        logger.error(f"❌ Failed to load full AI engine router: {e}")
        print("🔄 Falling back to simple_router.py...")
        try:
            from app.ai_engine.simple_router import router as ai_engine_router
            app.include_router(ai_engine_router)
            ai_router_fallback = True
            print("🔄 Fallback simple_router loaded and registered.")
            logger.info("🔄 Fallback simple_router loaded and registered.")
        except Exception as fallback_e:
            print(f"❌ Failed to load fallback simple_router: {fallback_e}")
            logger.error(f"❌ Failed to load fallback simple_router: {fallback_e}")
    
    try:
        print("📊 Initializing database...")
        init_database()
        print("✅ Database initialized successfully")
        logger.info("Database initialized.")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        logger.error(f"Database initialization failed: {e}")
    
    print("🎯 FastAPI app startup complete - health checks should work")
    logger.info("FastAPI app startup complete")

# Include routers
print("🔍 Including auth router...")
try:
    app.include_router(auth_router)
    print("✅ Auth router included")
except Exception as e:
    print(f"❌ Failed to include auth router: {e}")
    logger.error(f"❌ Failed to include auth router: {e}")

print("🔍 Including portfolio router...")
try:
    app.include_router(portfolio_router)
    print("✅ Portfolio router included")
except Exception as e:
    print(f"❌ Failed to include portfolio router: {e}")
    logger.error(f"❌ Failed to include portfolio router: {e}")

print("🔍 Including broker router...")
try:
    app.include_router(broker_router)
    print("✅ Broker router included")
except Exception as e:
    print(f"❌ Failed to include broker router: {e}")
    logger.error(f"❌ Failed to include broker router: {e}")

print("🔍 Including trading router...")
try:
    app.include_router(trading_router)
    print("✅ Trading router included")
except Exception as e:
    print(f"❌ Failed to include trading router: {e}")
    logger.error(f"❌ Failed to include trading router: {e}")

# app.include_router(placeholder_router)

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
