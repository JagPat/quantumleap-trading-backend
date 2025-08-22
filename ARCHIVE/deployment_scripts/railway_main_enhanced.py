#!/usr/bin/env python3
"""
Enhanced Railway-Optimized Main Application
Combines working railway_main.py with database optimization features
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
        allow_origins=[
            "https://quantum-leap-frontend.vercel.app",
            "http://localhost:3000",
            "http://localhost:5173",
            "https://quantum-leap-frontend-git-main-jagrut-patels-projects.vercel.app",
            "*"  # Allow all for Railway
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Try to load operational procedures (simplified version)
    operational_router = None
    try:
        from app.trading_engine.operational_procedures_simple import get_simple_operational_procedures
        
        @app.get("/api/operational/health")
        async def operational_health():
            """Get operational system health status"""
            try:
                ops = get_simple_operational_procedures()
                health = ops.check_system_health()
                return health
            except Exception as e:
                logger.error(f"Operational health check failed: {e}")
                return {"status": "error", "error": str(e)}
        
        @app.get("/api/operational/status")
        async def operational_status():
            """Get comprehensive operational status"""
            try:
                ops = get_simple_operational_procedures()
                status = ops.get_operational_status()
                return status
            except Exception as e:
                logger.error(f"Operational status failed: {e}")
                return {"status": "error", "error": str(e)}
        
        @app.get("/api/operational/metrics")
        async def system_metrics():
            """Get current system metrics"""
            try:
                ops = get_simple_operational_procedures()
                metrics = ops.collect_system_metrics()
                return {
                    "cpu_usage": metrics.cpu_usage,
                    "memory_usage": metrics.memory_usage,
                    "disk_usage": metrics.disk_usage,
                    "network_io": metrics.network_io,
                    "active_connections": metrics.active_connections,
                    "response_time": metrics.response_time,
                    "error_rate": metrics.error_rate,
                    "timestamp": metrics.timestamp.isoformat()
                }
            except Exception as e:
                logger.error(f"System metrics collection failed: {e}")
                return {"status": "error", "error": str(e)}
        
        logger.info("✅ Operational procedures loaded")
        
    except Exception as e:
        logger.warning(f"⚠️ Operational procedures not available: {e}")
    
    # Try to load database optimization (standalone version)
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("standalone_manager", "app/database/standalone_manager.py")
        standalone_db = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(standalone_db)
        
        @app.get("/api/database/health")
        async def database_health():
            """Get database health status"""
            try:
                return standalone_db.check_railway_database_health()
            except Exception as e:
                logger.error(f"Database health check failed: {e}")
                return {"status": "error", "error": str(e)}
        
        @app.get("/api/database/metrics")
        async def database_metrics():
            """Get database performance metrics"""
            try:
                db_manager = standalone_db.get_standalone_database_manager()
                return db_manager.get_performance_metrics()
            except Exception as e:
                logger.error(f"Database metrics failed: {e}")
                return {"status": "error", "error": str(e)}
        
        logger.info("✅ Database optimization system loaded")
        
    except Exception as e:
        logger.warning(f"⚠️ Database optimization system not available: {e}")
    
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "message": "Quantum Leap Backend API",
            "version": "1.0.0",
            "status": "operational",
            "timestamp": datetime.now().isoformat(),
            "environment": os.getenv("RAILWAY_ENVIRONMENT", "production"),
            "port": os.getenv("PORT", "8000"),
            "features": [
                "Basic API endpoints",
                "Operational procedures",
                "Database optimization",
                "System health monitoring"
            ]
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
            "endpoints": [
                "/", "/health", "/api/status", "/test",
                "/api/operational/health", "/api/operational/status", "/api/operational/metrics",
                "/api/database/health", "/api/database/metrics"
            ]
        }
    
    @app.get("/test")
    async def test_endpoint():
        """Test endpoint to verify deployment"""
        return {
            "test": "success",
            "message": "Enhanced Railway deployment is working!",
            "timestamp": datetime.now().isoformat(),
            "features_loaded": {
                "operational_procedures": operational_router is not None,
                "database_optimization": "standalone_db" in locals()
            }
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
        
        logger.info(f"🚀 Starting Enhanced Quantum Leap Backend on {host}:{port}")
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