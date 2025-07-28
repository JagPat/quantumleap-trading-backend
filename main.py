# Force redeploy - simplified main.py - 2024-07-16
"""
QuantumLeap Trading Backend - Simplified Main Application
Version: 2.0.0
"""
import logging
import os
from datetime import datetime
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

# Enhanced CORS configuration for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # React dev server
        "http://127.0.0.1:5173",  # Alternative localhost
        "http://127.0.0.1:3000",  # Alternative localhost
        "https://web-production-de0bc.up.railway.app",  # Production backend
        "*"  # Fallback for all origins
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
    ],
    expose_headers=["*"],
)

# Health check endpoints
@app.get("/health")
async def health_check():
    """Enhanced health check endpoint with component status"""
    try:
        # Try to get component status if startup monitor is available
        component_status = {}
        fallback_components = []
        
        # This will be populated during startup
        if hasattr(app.state, 'startup_monitor'):
            startup_monitor = app.state.startup_monitor
            component_statuses = startup_monitor.get_component_statuses()
            
            for name, status in component_statuses.items():
                component_status[name] = {
                    "status": status.status.value,
                    "healthy": status.status.value == "loaded",
                    "load_duration": status.load_duration
                }
                
                if status.status.value == "fallback":
                    fallback_components.append(name)
        
        overall_status = "ok"
        if len(fallback_components) > len(component_status) / 2:
            overall_status = "degraded"
        elif len(fallback_components) > 0:
            overall_status = "partial"
        
        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "components": component_status,
            "fallback_active": len(fallback_components) > 0,
            "fallback_components": fallback_components,
            "message": f"System operational with {len(fallback_components)} components in fallback mode" if fallback_components else "All systems operational"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "message": "Health check failed"
        }

@app.get("/ping")
async def ping():
    """Ultra-simple ping endpoint"""
    return {"ping": "pong"}

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
    """Enhanced readiness check endpoint"""
    try:
        ready = True
        components = {}
        
        # Check component readiness if startup monitor is available
        if hasattr(app.state, 'startup_monitor'):
            startup_monitor = app.state.startup_monitor
            component_statuses = startup_monitor.get_component_statuses()
            
            for name, status in component_statuses.items():
                is_ready = status.status.value in ["loaded", "fallback"]
                components[name] = {
                    "status": "ready" if is_ready else "not_ready",
                    "mode": "production" if status.status.value == "loaded" else "fallback",
                    "load_duration": status.load_duration
                }
                
                if not is_ready:
                    ready = False
        else:
            # Fallback component status
            components = {
                "database": {"status": "ready", "mode": "production"},
                "auth": {"status": "ready", "mode": "production"},
                "portfolio": {"status": "ready", "mode": "unknown"},
                "ai_engine": {"status": "ready", "mode": "fallback"}
            }
        
        return {
            "status": "ready" if ready else "not_ready",
            "timestamp": datetime.now().isoformat(),
            "components": components,
            "message": "All components ready" if ready else "Some components not ready"
        }
        
    except Exception as e:
        return {
            "status": "not_ready",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "message": "Readiness check failed"
        }

@app.get("/component-status")
async def get_component_status():
    """Get detailed component status information"""
    try:
        if hasattr(app.state, 'startup_monitor'):
            startup_monitor = app.state.startup_monitor
            component_statuses = startup_monitor.get_component_statuses()
            
            return {
                "timestamp": datetime.now().isoformat(),
                "components": {
                    name: {
                        "status": status.status.value,
                        "error_message": status.error_message,
                        "load_time": status.load_time.isoformat(),
                        "fallback_reason": status.fallback_reason,
                        "load_duration": status.load_duration,
                        "healthy": status.status.value == "loaded",
                        "real_data": status.status.value == "loaded"
                    }
                    for name, status in component_statuses.items()
                },
                "summary": {
                    "total": len(component_statuses),
                    "loaded": sum(1 for s in component_statuses.values() if s.status.value == "loaded"),
                    "fallback": sum(1 for s in component_statuses.values() if s.status.value == "fallback"),
                    "failed": sum(1 for s in component_statuses.values() if s.status.value == "failed")
                }
            }
        else:
            return {
                "timestamp": datetime.now().isoformat(),
                "error": "Startup monitor not available",
                "components": {},
                "summary": {"total": 0, "loaded": 0, "fallback": 0, "failed": 0}
            }
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "components": {},
            "summary": {"total": 0, "loaded": 0, "fallback": 0, "failed": 0}
        }

@app.get("/fallback-status")
async def get_fallback_status():
    """Get information about components in fallback mode"""
    try:
        if hasattr(app.state, 'startup_monitor'):
            startup_monitor = app.state.startup_monitor
            fallback_info = startup_monitor.get_fallback_components_info()
            
            return {
                "timestamp": datetime.now().isoformat(),
                "fallback_active": len(fallback_info) > 0,
                "fallback_count": len(fallback_info),
                "components": fallback_info,
                "message": "Some components are running in fallback mode with limited functionality" 
                          if fallback_info else "All components running normally"
            }
        else:
            return {
                "timestamp": datetime.now().isoformat(),
                "fallback_active": False,
                "fallback_count": 0,
                "components": {},
                "message": "Startup monitor not available"
            }
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "fallback_active": True,
            "fallback_count": 0,
            "components": {},
            "message": "Fallback status check failed"
        }

# CORS preflight handler
@app.options("/{path:path}")
async def options_handler(path: str):
    """Handle CORS preflight requests"""
    return {"message": "OK"}

@app.get("/")
async def root():
    """Root endpoint with basic app info and health links"""
    return {
        "message": "QuantumLeap Trading Backend API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
        "deployment": "latest",
        "cors_enabled": True,
        "frontend_origins": [
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000"
        ],
        "monitoring": {
            "health": "/health",
            "readiness": "/readyz",
            "component_status": "/component-status",
            "fallback_status": "/fallback-status",
            "startup_summary": "/health/startup-summary",
            "startup_events": "/health/startup-events",
            "performance_metrics": "/health/performance-metrics",
            "memory_usage": "/health/memory-usage"
        }
    }

# Initialize database on startup
@app.on_event("startup")
async def on_startup():
    """Initialize database and startup tasks with robust fallback system"""
    print("🚀 Starting QuantumLeap Trading Backend...")
    logger.info("Starting QuantumLeap Trading Backend")
    
    # Initialize infrastructure validator
    try:
        from app.core.infrastructure_validator import InfrastructureValidator
        validator = InfrastructureValidator()
        
        print("🏗️ Validating infrastructure...")
        validation_results = validator.validate_all()
        
        # Log validation results
        for category, result in validation_results.items():
            if result.success:
                print(f"✅ Infrastructure {category}: {result.message}")
            else:
                print(f"❌ Infrastructure {category}: {result.message}")
                for error in result.errors:
                    print(f"   - {error}")
        
        logger.info("Infrastructure validation completed")
    except Exception as e:
        print(f"❌ Infrastructure validation failed: {e}")
        logger.error(f"Infrastructure validation failed: {e}")
    
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
    
    # Initialize startup monitor and component loader
    try:
        from app.core.startup_monitor import StartupMonitor
        from app.core.component_loader import ComponentLoader
        
        startup_monitor = StartupMonitor()
        component_loader = ComponentLoader()
        
        startup_monitor.log_startup_progress("system", "loading", "Initializing component loader")
        
        # Load Portfolio Router with component loader
        startup_monitor.log_startup_progress("portfolio", "loading", "Loading portfolio router")
        
        portfolio_result = component_loader.load_router_with_fallback(
            "portfolio",
            "app.portfolio.router.router",
            "/api/portfolio",
            validate_syntax=True
        )
        
        if portfolio_result.router:
            app.include_router(portfolio_result.router)
            if portfolio_result.success:
                startup_monitor.log_startup_progress("portfolio", "success", "Portfolio router loaded", portfolio_result.load_duration)
            else:
                startup_monitor.log_startup_progress("portfolio", "fallback", "Portfolio router in fallback mode", portfolio_result.load_duration)
        else:
            startup_monitor.log_startup_progress("portfolio", "failed", "Portfolio router failed completely")
            
        # Update startup monitor with component status
        if hasattr(component_loader, 'get_component_status'):
            portfolio_status = component_loader.get_component_status("portfolio")
            if portfolio_status:
                startup_monitor.update_component_status(portfolio_status)
            
    except Exception as e:
        print(f"❌ Component loader initialization failed: {e}")
        logger.error(f"Component loader initialization failed: {e}")
        
        # Fallback to original loading logic
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
        except Exception as fallback_e:
            print(f"❌ Portfolio service import failed: {fallback_e}")
            logger.error(f"❌ Portfolio service import failed: {fallback_e}")
            print(f"❌ Portfolio error type: {type(fallback_e).__name__}")
            print(f"❌ Portfolio error details: {str(fallback_e)}")
            
            print("⚠️ Using fallback portfolio router with database cleanup endpoints")
            try:
                # Import external fallback portfolio router with cleanup endpoints
                from app.portfolio.fallback_router import router as fallback_portfolio_router
                app.include_router(fallback_portfolio_router)
                print("🔄 External fallback portfolio router loaded and registered.")
                logger.info("🔄 External fallback portfolio router loaded and registered.")
            except Exception as final_fallback_e:
                print(f"❌ Failed to create fallback portfolio router: {final_fallback_e}")
                logger.error(f"❌ Failed to create fallback portfolio router: {final_fallback_e}")
    
    # Load Broker Router with component loader
    try:
        if 'component_loader' in locals() and 'startup_monitor' in locals():
            startup_monitor.log_startup_progress("broker", "loading", "Loading broker router")
            
            broker_result = component_loader.load_router_with_fallback(
                "broker",
                "app.broker.router.router",
                "/api/broker",
                validate_syntax=True
            )
            
            if broker_result.router:
                app.include_router(broker_result.router)
                if broker_result.success:
                    startup_monitor.log_startup_progress("broker", "success", "Broker router loaded", broker_result.load_duration)
                else:
                    startup_monitor.log_startup_progress("broker", "fallback", "Broker router in fallback mode", broker_result.load_duration)
            else:
                startup_monitor.log_startup_progress("broker", "failed", "Broker router failed completely")
                
            # Update startup monitor with component status
            broker_status = component_loader.get_component_status("broker")
            if broker_status:
                startup_monitor.update_component_status(broker_status)
        else:
            raise Exception("Component loader not available")
            
    except Exception as e:
        print(f"❌ Broker component loading failed: {e}")
        logger.error(f"❌ Broker component loading failed: {e}")
        
        # Fallback to original loading logic
        try:
            print("🔍 Attempting to load broker router...")
            logger.info("🔍 Attempting to load broker router...")
            
            from app.broker.router import router as broker_router
            app.include_router(broker_router)
            print("✅ Broker router loaded and registered.")
            logger.info("✅ Broker router loaded and registered.")
        except Exception as fallback_e:
            print(f"❌ Broker service import failed: {fallback_e}")
            logger.error(f"❌ Broker service import failed: {fallback_e}")
            print(f"❌ Broker error type: {type(fallback_e).__name__}")
            print(f"❌ Broker error details: {str(fallback_e)}")
            
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
                        "error": str(fallback_e),
                        "fallback_active": True,
                        "real_data": False,
                        "component": "broker",
                        "timestamp": datetime.now().isoformat(),
                        "warning": "⚠️ This is fallback data - broker service is temporarily unavailable"
                    }
                
                @fallback_broker_router.get("/{path:path}")
                async def fallback_broker_catchall(path: str):
                    raise HTTPException(status_code=503, detail="Broker service unavailable")
                
                app.include_router(fallback_broker_router)
                print("🔄 Fallback broker router created and registered.")
                logger.info("🔄 Fallback broker router created and registered.")
            except Exception as final_fallback_e:
                print(f"❌ Failed to create fallback broker router: {final_fallback_e}")
                logger.error(f"❌ Failed to create fallback broker router: {final_fallback_e}")
    
    # Load Trading Router with component loader
    try:
        if 'component_loader' in locals() and 'startup_monitor' in locals():
            startup_monitor.log_startup_progress("trading", "loading", "Loading trading router")
            
            trading_result = component_loader.load_router_with_fallback(
                "trading",
                "app.trading.router.router",
                "/api/trading",
                validate_syntax=True
            )
            
            if trading_result.router:
                app.include_router(trading_result.router)
                if trading_result.success:
                    startup_monitor.log_startup_progress("trading", "success", "Trading router loaded", trading_result.load_duration)
                else:
                    startup_monitor.log_startup_progress("trading", "fallback", "Trading router in fallback mode", trading_result.load_duration)
            else:
                startup_monitor.log_startup_progress("trading", "failed", "Trading router failed completely")
                
            # Update startup monitor with component status
            trading_status = component_loader.get_component_status("trading")
            if trading_status:
                startup_monitor.update_component_status(trading_status)
        else:
            raise Exception("Component loader not available")
            
    except Exception as e:
        print(f"❌ Trading component loading failed: {e}")
        logger.error(f"❌ Trading component loading failed: {e}")
        
        # Fallback to original loading logic
        try:
            print("🔍 Attempting to load trading router...")
            logger.info("🔍 Attempting to load trading router...")
            
            from app.trading.router import router as trading_router
            app.include_router(trading_router)
            print("✅ Trading router loaded and registered.")
            logger.info("✅ Trading router loaded and registered.")
        except Exception as fallback_e:
            print(f"❌ Trading service import failed: {fallback_e}")
            logger.error(f"❌ Trading service import failed: {fallback_e}")
            print(f"❌ Trading error type: {type(fallback_e).__name__}")
            print(f"❌ Trading error details: {str(fallback_e)}")
            
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
                        "error": str(fallback_e),
                        "fallback_active": True,
                        "real_data": False,
                        "component": "trading",
                        "timestamp": datetime.now().isoformat(),
                        "warning": "⚠️ This is fallback data - trading service is temporarily unavailable"
                    }
                
                @fallback_trading_router.get("/{path:path}")
                async def fallback_trading_catchall(path: str):
                    raise HTTPException(status_code=503, detail="Trading service unavailable")
                
                app.include_router(fallback_trading_router)
                print("🔄 Fallback trading router created and registered.")
                logger.info("🔄 Fallback trading router created and registered.")
            except Exception as final_fallback_e:
                print(f"❌ Failed to create fallback trading router: {final_fallback_e}")
                logger.error(f"❌ Failed to create fallback trading router: {final_fallback_e}")
    
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

    # Generate startup summary
    try:
        if 'startup_monitor' in locals():
            startup_monitor.log_startup_progress("database", "success", "Database initialized")
            
            # Set infrastructure results if available
            if 'validation_results' in locals():
                startup_monitor.set_infrastructure_results(validation_results)
            
            # Generate and display startup summary
            startup_summary = startup_monitor.generate_startup_summary()
            
            # Create health endpoints
            health_router = startup_monitor.create_health_endpoints()
            app.include_router(health_router)
            
            # Store startup monitor in app state for health endpoints
            app.state.startup_monitor = startup_monitor
            
            print("✅ Startup monitoring completed")
        else:
            print("⚠️ Startup monitor not available")
    except Exception as e:
        print(f"❌ Startup summary generation failed: {e}")
        logger.error(f"Startup summary generation failed: {e}")

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

# Chat router - Phase 4 implementation
try:
    print("🔄 Including chat router...")
    from app.ai_engine.chat_router import router as chat_router
    app.include_router(chat_router)
    print("✅ Chat router loaded and registered.")
    logger.info("✅ Chat router loaded and registered.")
except Exception as e:
    print(f"❌ Failed to load chat router: {e}")
    logger.error(f"❌ Failed to load chat router: {e}")

# Analysis router - Portfolio AI analysis endpoints
try:
    print("🔄 Including analysis router...")
    from app.ai_engine.analysis_router import router as analysis_router
    app.include_router(analysis_router)
    print("✅ Analysis router loaded and registered.")
    logger.info("✅ Analysis router loaded and registered.")
except Exception as e:
    print(f"❌ Failed to load analysis router: {e}")
    logger.error(f"❌ Failed to load analysis router: {e}")
    
    # Create fallback analysis router for portfolio endpoint
    try:
        from fastapi import APIRouter
        
        fallback_analysis_router = APIRouter(prefix="/api/ai/analysis", tags=["AI Analysis - Fallback"])
        
        @fallback_analysis_router.post("/portfolio")
        async def fallback_portfolio_analysis(portfolio_data: dict):
            return {
                "status": "fallback",
                "analysis": {
                    "health_score": 75.0,
                    "risk_level": "MODERATE",
                    "recommendations": [
                        {
                            "type": "DIVERSIFICATION",
                            "title": "Consider diversifying across sectors",
                            "description": "Portfolio analysis service temporarily unavailable",
                            "priority": "MEDIUM"
                        }
                    ]
                },
                "message": "Portfolio analysis service in fallback mode",
                "error": str(e)
            }
        
        app.include_router(fallback_analysis_router)
        print("🔄 Fallback analysis router created and registered.")
        logger.info("🔄 Fallback analysis router created and registered.")
    except Exception as fallback_e:
        print(f"❌ Failed to create fallback analysis router: {fallback_e}")
        logger.error(f"❌ Failed to create fallback analysis router: {fallback_e}")
    
    # Create fallback chat router
    try:
        from fastapi import APIRouter
        
        fallback_chat_router = APIRouter(prefix="/api/ai/chat", tags=["AI Chat - Fallback"])
        
        @fallback_chat_router.get("/health")
        async def fallback_chat_health():
            return {
                "status": "fallback",
                "message": "Chat service in fallback mode",
                "error": str(e)
            }
        
        @fallback_chat_router.post("/message")
        async def fallback_chat_message():
            return {
                "status": "error",
                "reply": "Chat service is currently unavailable. Please try again later.",
                "thread_id": "fallback",
                "message_id": "fallback",
                "provider_used": "none",
                "tokens_used": 0,
                "cost_cents": 0
            }
        
        app.include_router(fallback_chat_router)
        print("🔄 Fallback chat router created and registered.")
        logger.info("🔄 Fallback chat router created and registered.")
    except Exception as fallback_e:
        print(f"❌ Failed to create fallback chat router: {fallback_e}")
        logger.error(f"❌ Failed to create fallback chat router: {fallback_e}")

# Trading Engine Router - New automatic trading functionality
try:
    print("🔄 Including production trading engine router...")
    from app.trading_engine.production_router import router as production_trading_engine_router
    app.include_router(production_trading_engine_router)
    print("✅ Production trading engine router loaded and registered.")
    logger.info("✅ Production trading engine router loaded and registered.")
except Exception as e:
    print(f"❌ Failed to load production trading engine router: {e}")
    logger.error(f"❌ Failed to load production trading engine router: {e}")
    
    # Try to load full trading engine router
    try:
        print("🔄 Including full trading engine router...")
        from app.trading_engine.router import router as trading_engine_router
        app.include_router(trading_engine_router)
        print("✅ Full trading engine router loaded and registered.")
        logger.info("✅ Full trading engine router loaded and registered.")
    except Exception as full_e:
        print(f"❌ Failed to load full trading engine router: {full_e}")
        logger.error(f"❌ Failed to load full trading engine router: {full_e}")
        
        # Try to load simplified trading engine router
        try:
            print("🔄 Loading simplified trading engine router...")
            from app.trading_engine.simple_router import router as simple_trading_engine_router
            app.include_router(simple_trading_engine_router)
            print("✅ Simplified trading engine router loaded and registered.")
            logger.info("✅ Simplified trading engine router loaded and registered.")
        except Exception as simple_e:
            print(f"❌ Failed to load simplified trading engine router: {simple_e}")
            logger.error(f"❌ Failed to load simplified trading engine router: {simple_e}")
        
        # Create minimal fallback trading engine router
        try:
            from fastapi import APIRouter
            
            # Capture the error message for use in fallback functions
            error_message = str(e)
            
            fallback_trading_engine_router = APIRouter(prefix="/api/trading-engine", tags=["Trading Engine - Fallback"])
            
            @fallback_trading_engine_router.get("/health")
            async def fallback_trading_engine_health():
                return {
                    "status": "fallback",
                    "message": "Trading engine service in minimal fallback mode",
                    "error": error_message,
                    "timestamp": datetime.now().isoformat()
                }
            
            @fallback_trading_engine_router.get("/metrics")
            async def fallback_trading_engine_metrics():
                return {
                    "status": "fallback",
                    "metrics": {
                        "orders_processed": 0,
                        "signals_processed": 0,
                        "active_strategies": 0,
                        "error": "Metrics service unavailable"
                    },
                    "timestamp": datetime.now().isoformat()
                }
            
            @fallback_trading_engine_router.get("/alerts")
            async def fallback_trading_engine_alerts():
                return {
                    "status": "fallback",
                    "alerts": [],
                    "alert_count": 0,
                    "error": "Alerts service unavailable",
                    "last_updated": datetime.now().isoformat()
                }
            
            app.include_router(fallback_trading_engine_router)
            print("🔄 Minimal fallback trading engine router created and registered.")
            logger.info("🔄 Minimal fallback trading engine router created and registered.")
        except Exception as fallback_e:
            print(f"❌ Failed to create minimal fallback trading engine router: {fallback_e}")
            logger.error(f"❌ Failed to create minimal fallback trading engine router: {fallback_e}")

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
# FORCE REDEPLOY - Fixed AIStrategyResponse import - Sun Jul 20 04:41:00 IST 2025
