"""
Quantum Leap Trading Platform - Optimized Backend
FastAPI backend with database optimization and comprehensive trading features
"""
import os
import sys
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import optimized database components
try:
    from app.database.trading_engine_integration import trading_db_integration
    from app.trading_engine.optimized_order_db import optimized_order_db
    from app.database.trading_performance_dashboard import trading_performance_dashboard
    OPTIMIZATION_AVAILABLE = True
    logger.info("Database optimization components loaded successfully")
except ImportError as e:
    logger.warning(f"Database optimization not available: {e}")
    OPTIMIZATION_AVAILABLE = False

# Import existing components
try:
    from app.ai_engine.simple_analysis_router import router as ai_router
    from app.trading_engine.simple_router import router as trading_router
    from app.portfolio.service import router as portfolio_router
    from app.broker.kite_service import router as broker_router
    AI_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Some components not available: {e}")
    AI_AVAILABLE = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting Quantum Leap Trading Platform...")
    
    if OPTIMIZATION_AVAILABLE:
        try:
            # Initialize optimized database
            await trading_db_integration.initialize()
            await optimized_order_db.initialize()
            
            # Start performance monitoring
            await trading_performance_dashboard.start_monitoring()
            
            logger.info("✅ Database optimization system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database optimization: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Quantum Leap Trading Platform...")
    
    if OPTIMIZATION_AVAILABLE:
        try:
            await trading_performance_dashboard.stop_monitoring()
            await trading_db_integration.shutdown()
            logger.info("✅ Database optimization system shutdown completed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# Create FastAPI app with lifespan
app = FastAPI(
    title="Quantum Leap Trading Platform",
    description="Advanced trading platform with AI analysis and database optimization",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/")
async def root():
    """Root endpoint with system status"""
    return {
        "message": "Quantum Leap Trading Platform API",
        "version": "2.0.0",
        "status": "operational",
        "features": {
            "database_optimization": OPTIMIZATION_AVAILABLE,
            "ai_analysis": AI_AVAILABLE,
            "trading_engine": True,
            "portfolio_management": True
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {}
    }
    
    # Check database optimization
    if OPTIMIZATION_AVAILABLE:
        try:
            db_health = await optimized_order_db.get_health_status()
            health_status["components"]["database"] = db_health
        except Exception as e:
            health_status["components"]["database"] = {"status": "error", "error": str(e)}
            health_status["status"] = "degraded"
    
    # Check AI components
    health_status["components"]["ai_engine"] = {"status": "available" if AI_AVAILABLE else "unavailable"}
    
    return health_status

# Database Optimization Endpoints
if OPTIMIZATION_AVAILABLE:
    
    @app.get("/api/database/performance")
    async def get_database_performance():
        """Get database performance metrics"""
        try:
            metrics = await optimized_order_db.get_performance_metrics()
            return {"success": True, "data": metrics}
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/database/dashboard")
    async def get_performance_dashboard():
        """Get comprehensive performance dashboard data"""
        try:
            dashboard_data = await trading_performance_dashboard.get_dashboard_data()
            return {"success": True, "data": dashboard_data}
        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/database/health")
    async def get_database_health():
        """Get detailed database health status"""
        try:
            health = await optimized_order_db.get_health_status()
            return {"success": True, "data": health}
        except Exception as e:
            logger.error(f"Error getting database health: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/database/backup")
    async def create_database_backup():
        """Create database backup"""
        try:
            backup_name = f"api_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            success = await optimized_order_db.create_backup(backup_name)
            
            if success:
                return {"success": True, "message": f"Backup created: {backup_name}"}
            else:
                raise HTTPException(status_code=500, detail="Backup creation failed")
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/database/cleanup")
    async def cleanup_old_data(days_to_keep: int = 90):
        """Clean up old database data"""
        try:
            await optimized_order_db.cleanup_old_data(days_to_keep)
            return {"success": True, "message": f"Cleaned up data older than {days_to_keep} days"}
        except Exception as e:
            logger.error(f"Error cleaning up data: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/database/metrics/history")
    async def get_metrics_history(hours: int = 24):
        """Get performance metrics history"""
        try:
            history = await trading_performance_dashboard.get_metrics_history(hours)
            return {"success": True, "data": history}
        except Exception as e:
            logger.error(f"Error getting metrics history: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/database/trading-metrics")
    async def get_trading_metrics():
        """Get trading-specific performance metrics"""
        try:
            metrics = await trading_performance_dashboard.get_trading_specific_metrics()
            return {"success": True, "data": metrics}
        except Exception as e:
            logger.error(f"Error getting trading metrics: {e}")
            raise HTTPException(status_code=500, detail=str(e))

# Enhanced Trading Engine Endpoints
@app.get("/api/trading/orders/{user_id}")
async def get_user_orders(user_id: str, limit: int = 100):
    """Get orders for a user with optimization"""
    try:
        if OPTIMIZATION_AVAILABLE:
            orders = await optimized_order_db.get_orders_by_user(user_id, limit=limit)
            return {"success": True, "data": [order.to_dict() for order in orders]}
        else:
            # Fallback to basic implementation
            return {"success": True, "data": [], "message": "Using fallback implementation"}
    except Exception as e:
        logger.error(f"Error getting user orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trading/positions/{user_id}")
async def get_user_positions(user_id: str, include_closed: bool = False):
    """Get positions for a user with optimization"""
    try:
        if OPTIMIZATION_AVAILABLE:
            positions = await optimized_order_db.get_user_positions_optimized(user_id, include_closed)
            return {"success": True, "data": [pos.to_dict() for pos in positions]}
        else:
            # Fallback to basic implementation
            return {"success": True, "data": [], "message": "Using fallback implementation"}
    except Exception as e:
        logger.error(f"Error getting user positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trading/executions/{user_id}")
async def get_user_executions(user_id: str, limit: int = 100):
    """Get executions for a user with optimization"""
    try:
        if OPTIMIZATION_AVAILABLE:
            executions = await optimized_order_db.get_executions_by_user(user_id, limit)
            return {"success": True, "data": [exec.to_dict() for exec in executions]}
        else:
            # Fallback to basic implementation
            return {"success": True, "data": [], "message": "Using fallback implementation"}
    except Exception as e:
        logger.error(f"Error getting user executions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trading/signals/{user_id}")
async def get_active_signals(user_id: str):
    """Get active trading signals for a user"""
    try:
        if OPTIMIZATION_AVAILABLE:
            signals = await optimized_order_db.get_active_signals(user_id)
            return {"success": True, "data": [signal.to_dict() for signal in signals]}
        else:
            # Fallback to basic implementation
            return {"success": True, "data": [], "message": "Using fallback implementation"}
    except Exception as e:
        logger.error(f"Error getting active signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Include existing routers if available
if AI_AVAILABLE:
    try:
        app.include_router(ai_router, prefix="/api/ai", tags=["AI Analysis"])
        app.include_router(trading_router, prefix="/api/trading", tags=["Trading Engine"])
        app.include_router(portfolio_router, prefix="/api/portfolio", tags=["Portfolio"])
        app.include_router(broker_router, prefix="/api/broker", tags=["Broker"])
        logger.info("✅ All API routers included successfully")
    except Exception as e:
        logger.warning(f"Some routers could not be included: {e}")

# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error", "detail": str(exc)}
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    
    logger.info(f"Starting Quantum Leap Trading Platform on port {port}")
    logger.info(f"Database optimization: {'✅ Enabled' if OPTIMIZATION_AVAILABLE else '❌ Disabled'}")
    logger.info(f"AI components: {'✅ Enabled' if AI_AVAILABLE else '❌ Disabled'}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
