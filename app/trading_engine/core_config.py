"""
Core Trading Engine Configuration
Minimal configuration without external dependencies
"""
import os
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class TradingEngineConfig:
    """Core trading engine configuration without external dependencies"""
    
    def __init__(self):
        self.config = {
            # System Configuration
            'max_concurrent_orders': int(os.getenv('MAX_CONCURRENT_ORDERS', '10')),
            'order_timeout_seconds': int(os.getenv('ORDER_TIMEOUT_SECONDS', '30')),
            'risk_check_enabled': os.getenv('RISK_CHECK_ENABLED', 'true').lower() == 'true',
            'emergency_stop_enabled': os.getenv('EMERGENCY_STOP_ENABLED', 'true').lower() == 'true',
            
            # Risk Management
            'max_position_size_percent': float(os.getenv('MAX_POSITION_SIZE_PERCENT', '10.0')),
            'max_portfolio_exposure_percent': float(os.getenv('MAX_PORTFOLIO_EXPOSURE_PERCENT', '80.0')),
            'max_sector_exposure_percent': float(os.getenv('MAX_SECTOR_EXPOSURE_PERCENT', '25.0')),
            'default_stop_loss_percent': float(os.getenv('DEFAULT_STOP_LOSS_PERCENT', '5.0')),
            
            # Market Data
            'market_data_refresh_seconds': int(os.getenv('MARKET_DATA_REFRESH_SECONDS', '5')),
            
            # Database
            'database_url': os.getenv('DATABASE_URL', 'sqlite:///trading_engine.db'),
            'database_pool_size': int(os.getenv('DATABASE_POOL_SIZE', '5')),
            
            # Logging
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'log_file': os.getenv('LOG_FILE', '/tmp/trading_engine.log'),
            
            # API Keys (optional)
            'kite_api_key': os.getenv('KITE_API_KEY'),
            'kite_api_secret': os.getenv('KITE_API_SECRET'),
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> bool:
        """Set configuration value"""
        try:
            self.config[key] = value
            logger.info(f"Configuration updated: {key} = {value}")
            return True
        except Exception as e:
            logger.error(f"Failed to set configuration {key}: {e}")
            return False
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values"""
        return self.config.copy()
    
    def validate(self) -> Dict[str, Any]:
        """Validate configuration and return status"""
        issues = []
        
        # Validate numeric ranges
        if self.config['max_position_size_percent'] <= 0 or self.config['max_position_size_percent'] > 100:
            issues.append("max_position_size_percent must be between 0 and 100")
        
        if self.config['max_portfolio_exposure_percent'] <= 0 or self.config['max_portfolio_exposure_percent'] > 100:
            issues.append("max_portfolio_exposure_percent must be between 0 and 100")
        
        if self.config['order_timeout_seconds'] <= 0:
            issues.append("order_timeout_seconds must be positive")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'config': self.config
        }

# Global configuration instance
trading_config = TradingEngineConfig()

def get_trading_config() -> TradingEngineConfig:
    """Get the global trading configuration instance"""
    return trading_config

def check_trading_engine_health() -> Dict[str, Any]:
    """Check trading engine health without external dependencies"""
    try:
        config_status = trading_config.validate()
        
        return {
            'status': 'healthy' if config_status['valid'] else 'degraded',
            'config_valid': config_status['valid'],
            'config_issues': config_status['issues'],
            'timestamp': '2025-07-27T05:30:00.000Z',
            'components': {
                'configuration': 'healthy',
                'logging': 'healthy',
                'database': 'unknown'  # Will be updated when database is available
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': '2025-07-27T05:30:00.000Z'
        }

def get_trading_system_config(key: str) -> Optional[str]:
    """Get trading system configuration value"""
    try:
        value = trading_config.get(key)
        return str(value) if value is not None else None
    except Exception as e:
        logger.error(f"Failed to get config {key}: {e}")
        return None

def set_trading_system_config(key: str, value: str, reason: str = "") -> bool:
    """Set trading system configuration value"""
    try:
        # Convert string values to appropriate types
        config_value = value
        if key.endswith('_enabled'):
            config_value = value.lower() == 'true'
        elif key.endswith('_seconds') or key.endswith('_percent') or key == 'max_concurrent_orders':
            try:
                config_value = float(value) if '.' in value else int(value)
            except ValueError:
                config_value = value
        
        success = trading_config.set(key, config_value)
        if success and reason:
            logger.info(f"Config change reason: {reason}")
        return success
    except Exception as e:
        logger.error(f"Failed to set config {key}: {e}")
        return False