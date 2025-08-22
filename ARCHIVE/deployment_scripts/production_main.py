
import os
import sys
import json
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import existing components
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.trading_engine.router import trading_router as trading_engine_router
from app.trading_engine.monitoring import TradingEngineMonitor
from app.trading_engine.event_bus import EventManager
from app.ai_engine.analysis_router import ai_analysis_router
from app.portfolio.service import portfolio_router

# Configure logging with error handling
try:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('production.log'),
            logging.StreamHandler()
        ]
    )
except Exception as e:
    # Fallback to console logging only
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    print(f"Warning: Could not create log file, using console logging: {e}")
logger = logging.getLogger(__name__)

# Global components
event_manager = None
trading_monitor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global event_manager, trading_monitor
    
    logger.info("🚀 Starting production trading engine...")
    
    # Initialize core components
    event_manager = EventManager()
    trading_monitor = TradingEngineMonitor()
    
    # Start background services
    await event_manager.start()
    await trading_monitor.start()
    
    logger.info("✅ Production trading engine started successfully")
    
    yield
    
    # Cleanup
    logger.info("🛑 Shutting down production trading engine...")
    if trading_monitor:
        await trading_monitor.stop()
    if event_manager:
        await event_manager.stop()
    logger.info("✅ Production trading engine stopped")

# Create FastAPI app
app = FastAPI(
    title="Quantum Leap Trading Engine - Production",
    description="Automated Trading Engine for Production Environment",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://quantum-leap-frontend.vercel.app", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(trading_engine_router, prefix="/api/trading-engine", tags=["Trading Engine"])
app.include_router(ai_analysis_router, prefix="/api/ai", tags=["AI Analysis"])
app.include_router(portfolio_router, prefix="/api/portfolio", tags=["Portfolio"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Quantum Leap Trading Engine - Production",
        "version": "1.0.0",
        "status": "operational",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    global trading_monitor
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "database": "healthy",
            "event_bus": "healthy",
            "trading_engine": "healthy",
            "ai_engine": "healthy"
        }
    }
    
    if trading_monitor:
        system_health = await trading_monitor.get_system_health()
        health_status["components"].update(system_health)
    
    return health_status

@app.get("/metrics")
async def get_metrics():
    """System metrics endpoint"""
    global trading_monitor
    
    if not trading_monitor:
        raise HTTPException(status_code=503, detail="Monitoring not available")
    
    metrics = await trading_monitor.get_performance_metrics()
    return metrics

if __name__ == "__main__":
    import uvicorn
    
    # Production server configuration
    uvicorn.run(
        "production_main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        workers=4,
        log_level="info",
        access_log=True,
        reload=False
    )
