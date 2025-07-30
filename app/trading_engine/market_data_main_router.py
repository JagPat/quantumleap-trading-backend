"""
Market Data Main Router
Simplified router that includes only the market data and condition monitoring components
"""
from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

# Create main router
router = APIRouter(prefix="/api/trading-engine", tags=["Trading Engine - Market Data"])

# Import market data components
try:
    from .market_data_router import router as market_data_router
    router.include_router(market_data_router, prefix="/market-data", tags=["Market Data"])
    logger.info("Market data router included")
    MARKET_DATA_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Market data router not available: {e}")
    MARKET_DATA_AVAILABLE = False

try:
    from .market_condition_router import router as market_condition_router
    router.include_router(market_condition_router, prefix="/market-condition", tags=["Market Condition"])
    logger.info("Market condition router included")
    MARKET_CONDITION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Market condition router not available: {e}")
    MARKET_CONDITION_AVAILABLE = False

# Add a simple health check
@router.get("/health")
async def market_data_health():
    """Health check for market data components"""
    return {
        "status": "ok",
        "components": {
            "market_data": MARKET_DATA_AVAILABLE,
            "market_condition": MARKET_CONDITION_AVAILABLE
        },
        "message": "Market data components operational"
    }

@router.get("/status")
async def market_data_status():
    """Status endpoint for market data components"""
    return {
        "status": "success",
        "market_data_available": MARKET_DATA_AVAILABLE,
        "market_condition_available": MARKET_CONDITION_AVAILABLE,
        "endpoints": {
            "market_data": "/api/trading-engine/market-data/*" if MARKET_DATA_AVAILABLE else None,
            "market_condition": "/api/trading-engine/market-condition/*" if MARKET_CONDITION_AVAILABLE else None
        }
    }