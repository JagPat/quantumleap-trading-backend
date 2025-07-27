"""
Automatic Trading Engine Package
"""
import logging
from .database_schema import create_trading_engine_tables, check_trading_engine_health
from .event_bus import event_bus, EventType, EventPriority
from .monitoring import trading_monitor

logger = logging.getLogger(__name__)

def initialize_trading_engine():
    """Initialize the trading engine components"""
    try:
        # Create database tables
        logger.info("Creating trading engine database tables...")
        create_trading_engine_tables()
        
        # Check database health
        health = check_trading_engine_health()
        if health["status"] != "healthy":
            logger.error(f"Trading engine database health check failed: {health}")
            return False
        
        logger.info("Trading engine database initialized successfully")
        
        # Initialize event bus
        logger.info("Initializing event bus...")
        # Event bus is already initialized as global instance
        
        # Initialize monitoring
        logger.info("Initializing monitoring system...")
        # Monitor is already initialized as global instance
        
        logger.info("Trading engine initialization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize trading engine: {e}")
        return False

# Export main components
__all__ = [
    'initialize_trading_engine',
    'event_bus',
    'trading_monitor',
    'EventType',
    'EventPriority'
]