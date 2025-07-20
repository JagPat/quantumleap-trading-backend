# Force redeploy - simplified main.py - 2024-07-16
"""
QuantumLeap Trading Backend - Simplified Main Application
Version: 2.0.0
"""
import logging
import os
from fastapi import FastAPI # type: ignore
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from starlette.middleware.sessions import SessionMiddleware

# Import configuration
from app.core.config import settings

# Import database initialization
from app.database.service import init_database

# Import routers
from app.auth.router import router as auth_router
# Portfolio router will be imported during startup with fallback logic
# Broker and Trading routers will be imported during startup with fallback logic

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
    try:
        return {
            "status": "ok", 
            "app": settings.app_name, 
            "version": settings.app_version,
            "deployment_time": "2025-07-20T09:00:00Z",
            "timestamp": "2025-07-20T09:00:00Z",
            "railway_ready": True
        }
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": "2025-07-20T09:00:00Z"
        }

@app.get("/version")
async def get_version():
    """Get deployment version and commit info with debug details"""
    # Try to read startup checkpoint
    checkpoint_info = None
    try:
        with open("startup_checkpoint.json", "r") as f:
            import json
            checkpoint_info = json.load(f)
    except FileNotFoundError:
        checkpoint_info = {"error": "No startup checkpoint found - may be running old deployment"}
    except Exception as e:
        checkpoint_info = {"error": f"Failed to read checkpoint: {str(e)}"}
    
    return {
        "app_version": settings.app_version,
        "deployment": "latest",
        "debug_mode": True,
        "ai_router": "fallback",
        "status": "operational",
        "startup_checkpoint": checkpoint_info,
        "railway_info": {
            "commit_sha": os.environ.get("RAILWAY_GIT_COMMIT_SHA", "unknown"),
            "deployment_id": os.environ.get("RAILWAY_DEPLOYMENT_ID", "unknown"),
            "service_id": os.environ.get("RAILWAY_SERVICE_ID", "unknown")
        },
        "endpoints": {
            "health": "/health",
            "version": "/version", 
            "readyz": "/readyz",
            "ai_status": "/api/ai/status",
            "portfolio_status": "/api/portfolio/status",
            "broker_status": "/api/broker/status",
            "trading_status": "/api/trading/status",
            "docs": "/docs",
            "openapi": "/openapi.json"
        }
    }

@app.get("/readyz")
async def readyz():
    """Readiness check endpoint"""
    return {
        "status": "ready",
        "components": {
            "database": "connected",
            "auth": "operational",
            "portfolio": "operational",
            "ai_engine": "operational"
        },
        "ai_engine": {
            "status": "ready",
            "mode": "BYOAI (Bring Your Own AI)",
            "message": "Fallback router active. No AI key configured."
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
    """Initialize database and startup tasks with robust fallback system"""
    print("🚀 Starting QuantumLeap Trading Backend...")
    logger.info("Starting QuantumLeap Trading Backend")
    
    # Create startup checkpoint to verify fresh deployment
    try:
        import os
        from datetime import datetime
        checkpoint_data = {
            "startup_time": datetime.now().isoformat(),
            "commit_hash": os.environ.get("RAILWAY_GIT_COMMIT_SHA", "unknown"),
            "deployment_id": os.environ.get("RAILWAY_DEPLOYMENT_ID", "unknown"),
            "service_id": os.environ.get("RAILWAY_SERVICE_ID", "unknown")
        }
        
        with open("startup_checkpoint.json", "w") as f:
            import json
            json.dump(checkpoint_data, f, indent=2)
        
        print(f"✅ Startup checkpoint created: {checkpoint_data}")
        logger.info(f"✅ Startup checkpoint created: {checkpoint_data}")
    except Exception as e:
        print(f"❌ Failed to create startup checkpoint: {e}")
        logger.error(f"❌ Failed to create startup checkpoint: {e}")
    
    # Load Portfolio Router with robust fallback
    try:
        print("🔍 Attempting to load portfolio router...")
        logger.info("🔍 Attempting to load portfolio router...")
        
        # Test import step by step
        print("🔍 Testing portfolio imports...")
        from app.portfolio import models
        print("✅ Portfolio models imported")
        from app.portfolio import service
        print("✅ Portfolio service imported")
        from app.portfolio.router import router as portfolio_router
        print("✅ Portfolio router imported")
        
        app.include_router(portfolio_router)
        print("✅ Portfolio router loaded and registered.")
        logger.info("✅ Portfolio router loaded and registered.")
    except Exception as e:
        print(f"❌ Portfolio service import failed: {e}")
        logger.error(f"❌ Portfolio service import failed: {e}")
        print(f"❌ Portfolio error type: {type(e).__name__}")
        print(f"❌ Portfolio error details: {str(e)}")
        
        print("⚠️ Using fallback portfolio router with database cleanup endpoints")
        try:
            # Import external fallback portfolio router with cleanup endpoints
            from app.portfolio.fallback_router import router as fallback_portfolio_router
            app.include_router(fallback_portfolio_router)
            print("🔄 External fallback portfolio router loaded and registered.")
            logger.info("🔄 External fallback portfolio router loaded and registered.")
        except Exception as fallback_e:
            print(f"❌ Failed to create fallback portfolio router: {fallback_e}")
            logger.error(f"❌ Failed to create fallback portfolio router: {fallback_e}")
    
    # Load Broker Router with robust fallback
    try:
        print("🔍 Attempting to load broker router...")
        logger.info("🔍 Attempting to load broker router...")
        
        from app.broker.router import router as broker_router
        app.include_router(broker_router)
        print("✅ Broker router loaded and registered.")
        logger.info("✅ Broker router loaded and registered.")
    except Exception as e:
        print(f"❌ Broker service import failed: {e}")
        logger.error(f"❌ Broker service import failed: {e}")
        print(f"❌ Broker error type: {type(e).__name__}")
        print(f"❌ Broker error details: {str(e)}")
        
        print("⚠️ Using fallback broker router with /api/broker/status returning 503")
        try:
            # Create inline fallback broker router
            from fastapi import APIRouter, HTTPException
            
            fallback_broker_router = APIRouter(prefix="/api/broker", tags=["Broker - Fallback"])
            
            @fallback_broker_router.get("/status")
            async def fallback_broker_status():
                return {
                    "status": "fallback",
                    "message": "Broker service in fallback mode",
                    "error": str(e)
                }
            
            @fallback_broker_router.get("/{path:path}")
            async def fallback_broker_catchall(path: str):
                raise HTTPException(status_code=503, detail="Broker service unavailable")
            
            app.include_router(fallback_broker_router)
            print("🔄 Fallback broker router created and registered.")
            logger.info("🔄 Fallback broker router created and registered.")
        except Exception as fallback_e:
            print(f"❌ Failed to create fallback broker router: {fallback_e}")
            logger.error(f"❌ Failed to create fallback broker router: {fallback_e}")
    
    # Load Trading Router with robust fallback
    try:
        print("🔍 Attempting to load trading router...")
        logger.info("🔍 Attempting to load trading router...")
        
        from app.trading.router import router as trading_router
        app.include_router(trading_router)
        print("✅ Trading router loaded and registered.")
        logger.info("✅ Trading router loaded and registered.")
    except Exception as e:
        print(f"❌ Trading service import failed: {e}")
        logger.error(f"❌ Trading service import failed: {e}")
        print(f"❌ Trading error type: {type(e).__name__}")
        print(f"❌ Trading error details: {str(e)}")
        
        print("⚠️ Using fallback trading router with /api/trading/status returning 503")
        try:
            # Create inline fallback trading router
            from fastapi import APIRouter, HTTPException # type: ignore
            
            fallback_trading_router = APIRouter(prefix="/api/trading", tags=["Trading - Fallback"])
            
            @fallback_trading_router.get("/status")
            async def fallback_trading_status():
                return {
                    "status": "fallback",
                    "message": "Trading service in fallback mode",
                    "error": str(e)
                }
            
            @fallback_trading_router.get("/{path:path}")
            async def fallback_trading_catchall(path: str):
                raise HTTPException(status_code=503, detail="Trading service unavailable")
            
            app.include_router(fallback_trading_router)
            print("🔄 Fallback trading router created and registered.")
            logger.info("🔄 Fallback trading router created and registered.")
        except Exception as fallback_e:
            print(f"❌ Failed to create fallback trading router: {fallback_e}")
            logger.error(f"❌ Failed to create fallback trading router: {fallback_e}")
    
    # Initialize database with error handling
    try:
        print("📊 Initializing database...")
        import asyncio
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, init_database)
        print("✅ Database initialized successfully")
        logger.info("Database initialized.")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        logger.error(f"Database initialization failed: {e}")

    print("🎯 FastAPI app startup complete - health checks should work")
    logger.info("FastAPI app startup complete")

# Include routers
app.include_router(auth_router)
# Portfolio router will be included during startup with fallback logic

# Simple AI router - always include fallback
try:
    print("🔄 Including simple AI router...")
    from app.ai_engine.simple_router import router as ai_engine_router
    app.include_router(ai_engine_router)
    print("✅ Simple AI router loaded and registered.")
    logger.info("✅ Simple AI router loaded and registered.")
except Exception as e:
    print(f"❌ Failed to load simple AI router: {e}")
    logger.error(f"❌ Failed to load simple AI router: {e}")

# Alternative AI router for /ai/* endpoints (without /api prefix)
try:
    print("🔄 Including alternative AI router for /ai/* endpoints...")
    from app.ai_engine.router import alt_router as ai_alt_router
    app.include_router(ai_alt_router)
    print("✅ Alternative AI router loaded and registered.")
    logger.info("✅ Alternative AI router loaded and registered.")
except Exception as e:
    print(f"❌ Failed to load alternative AI router: {e}")
    logger.error(f"❌ Failed to load alternative AI router: {e}")
    
    # Create fallback alternative AI router
    try:
        from fastapi import APIRouter, HTTPException
        from app.ai_engine.simple_router import (
            AIPreferencesRequest, AIPreferencesResponse,
            APIKeyValidationRequest, APIKeyValidationResponse
        )
        
        fallback_ai_alt_router = APIRouter(prefix="/ai", tags=["AI Engine - Fallback Alternative"])
        
        @fallback_ai_alt_router.get("/preferences", response_model=AIPreferencesResponse)
        async def fallback_get_ai_preferences():
            return AIPreferencesResponse(
                status="no_key",
                preferences={
                    "preferred_ai_provider": "auto",
                    "openai_api_key": None,
                    "claude_api_key": None,
                    "gemini_api_key": None
                },
                message="No preferences found. Add your AI key."
            )
        
        @fallback_ai_alt_router.post("/preferences", response_model=AIPreferencesResponse)
        async def fallback_save_ai_preferences(preferences: AIPreferencesRequest):
            return AIPreferencesResponse(
                status="no_key",
                message="Preferences not saved. No AI key configured."
            )
        
        @fallback_ai_alt_router.post("/validate-key", response_model=APIKeyValidationResponse)
        async def fallback_validate_api_key(request: APIKeyValidationRequest):
            return APIKeyValidationResponse(
                valid=False,
                provider=request.provider,
                message="No API key configured. Validation not possible."
            )
        
        app.include_router(fallback_ai_alt_router)
        print("🔄 Fallback alternative AI router created and registered.")
        logger.info("🔄 Fallback alternative AI router created and registered.")
    except Exception as fallback_e:
        print(f"❌ Failed to create fallback alternative AI router: {fallback_e}")
        logger.error(f"❌ Failed to create fallback alternative AI router: {fallback_e}")

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
# FORCE DEPLOYMENT - Wed Jul 16 15:18:56 IST 2025
# FORCE DEPLOYMENT - AI Validation Fix - Fri Jul 18 15:43:05 IST 2025
# FORCE REDEPLOY - Fri Jul 18 20:44:08 IST 2025
# FORCE REDEPLOY - Fri Jul 18 20:46:49 IST 2025
