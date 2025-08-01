#!/usr/bin/env python3
"""
Main application entry point for Quantum Leap Backend
"""

import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    
    # Import routers with error handling
    routers_to_include = []
    
    try:
        from app.ai_engine.analysis_router import ai_analysis_router
        routers_to_include.append(("ai_analysis_router", ai_analysis_router, "/api/ai", ["AI Analysis"]))
        logger.info("✅ AI Analysis router loaded")
    except Exception as e:
        logger.warning(f"⚠️ AI Analysis router not available: {e}")
    
    try:
        from app.portfolio.service import portfolio_router
        routers_to_include.append(("portfolio_router", portfolio_router, "/api/portfolio", ["Portfolio"]))
        logger.info("✅ Portfolio router loaded")
    except Exception as e:
        logger.warning(f"⚠️ Portfolio router not available: {e}")
    
    try:
        from app.trading_engine.router import trading_engine_router
        routers_to_include.append(("trading_engine_router", trading_engine_router, "/api/trading-engine", ["Trading Engine"]))
        logger.info("✅ Trading Engine router loaded")
    except Exception as e:
        logger.warning(f"⚠️ Trading Engine router not available: {e}")
    
    # Database Optimization Routes
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("standalone_manager", "app/database/standalone_manager.py")
        standalone_db = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(standalone_db)
        logger.info("✅ Database optimization system loaded")
    except Exception as e:
        logger.warning(f"⚠️ Database optimization system not available: {e}")
        standalone_db = None
    
    # Create FastAPI app
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
            "https://quantum-leap-frontend-git-main-jagrut-patels-projects.vercel.app"
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include available routers
    for router_name, router, prefix, tags in routers_to_include:
        try:
            app.include_router(router, prefix=prefix, tags=tags)
            logger.info(f"✅ Included {router_name} at {prefix}")
        except Exception as e:
            logger.error(f"❌ Failed to include {router_name}: {e}")
    
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "message": "Quantum Leap Backend API",
            "version": "1.0.0",
            "status": "operational",
            "timestamp": datetime.now().isoformat(),
            "available_endpoints": [prefix for _, _, prefix, _ in routers_to_include]
        }
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint for Railway"""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "environment": os.getenv("RAILWAY_ENVIRONMENT", "development")
        }
    
    # Database Optimization Endpoints
    if standalone_db:
        @app.get("/api/database/health")
        async def database_health():
            """Get comprehensive database health status"""
            try:
                return standalone_db.check_railway_database_health()
            except Exception as e:
                logger.error(f"Database health check failed: {e}")
                return {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        
        @app.get("/api/database/metrics")
        async def database_metrics():
            """Get database performance metrics"""
            try:
                db_manager = standalone_db.get_standalone_database_manager()
                return db_manager.get_performance_metrics()
            except Exception as e:
                logger.error(f"Database metrics failed: {e}")
                return {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        
        @app.get("/api/database/connection-info")
        async def database_connection_info():
            """Get database connection information"""
            try:
                return standalone_db.get_railway_connection_info()
            except Exception as e:
                logger.error(f"Database connection info failed: {e}")
                return {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        
        @app.post("/api/database/optimize")
        async def optimize_database():
            """Run database optimization procedures"""
            try:
                success = standalone_db.optimize_for_railway()
                return {
                    "status": "success" if success else "failed",
                    "message": "Database optimization completed" if success else "Database optimization failed",
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"Database optimization failed: {e}")
                return {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        
        @app.get("/api/database/query-recommendations")
        async def get_query_recommendations():
            """Get query optimization recommendations"""
            try:
                recommendations = standalone_db.get_query_optimization_recommendations()
                return {
                    "status": "success",
                    "recommendations": recommendations,
                    "count": len(recommendations),
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"Query recommendations failed: {e}")
                return {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        
        @app.get("/api/database/index-recommendations")
        async def get_index_recommendations():
            """Get index optimization recommendations"""
            try:
                recommendations = standalone_db.get_index_optimization_recommendations()
                return {
                    "status": "success",
                    "recommendations": recommendations,
                    "count": len(recommendations),
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"Index recommendations failed: {e}")
                return {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        
        @app.get("/api/database/performance-dashboard")
        async def get_performance_dashboard():
            """Get comprehensive performance dashboard"""
            try:
                dashboard = standalone_db.get_railway_performance_dashboard()
                return dashboard
            except Exception as e:
                logger.error(f"Performance dashboard failed: {e}")
                return {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        
        @app.get("/api/database/optimization-summary")
        async def get_optimization_summary():
            """Get optimization system summary"""
            try:
                summary = standalone_db.get_railway_optimization_summary()
                return summary
            except Exception as e:
                logger.error(f"Optimization summary failed: {e}")
                return {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        
        logger.info("✅ Database optimization endpoints added")
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """Global exception handler"""
        logger.error(f"Global exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred",
                "timestamp": datetime.now().isoformat()
            }
        )
    
    if __name__ == "__main__":
        import uvicorn
        
        port = int(os.getenv("PORT", 8000))
        host = "0.0.0.0"
        
        logger.info(f"🚀 Starting Quantum Leap Backend on {host}:{port}")
        logger.info(f"📊 Available routers: {len(routers_to_include)}")
        
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info"
        )

except ImportError as e:
    logger.error(f"❌ Failed to import required modules: {e}")
    logger.info("🔧 This might be due to missing dependencies. Please check requirements.txt")
    sys.exit(1)
except Exception as e:
    logger.error(f"❌ Failed to start application: {e}")
    sys.exit(1)