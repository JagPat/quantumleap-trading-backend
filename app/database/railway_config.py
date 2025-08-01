"""
Railway-Specific Database Configuration

Optimized database configuration for Railway deployment with automatic
environment detection and fallback strategies.
"""

import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RailwayDatabaseConfig:
    """Railway-optimized database configuration"""
    
    # Railway environment detection
    is_railway_production: bool = os.getenv('RAILWAY_ENVIRONMENT') == 'production'
    is_railway_staging: bool = os.getenv('RAILWAY_ENVIRONMENT') == 'staging'
    is_railway: bool = bool(os.getenv('RAILWAY_ENVIRONMENT'))
    
    # Database URL with Railway auto-detection
    database_url: str = os.getenv('DATABASE_URL', 'sqlite:///production_trading.db')
    
    # Railway-specific connection limits
    max_connections: int = 15 if is_railway else 5  # Railway has connection limits
    min_connections: int = 2
    connection_timeout: int = 30
    idle_timeout: int = 600  # 10 minutes for Railway
    
    # Performance settings optimized for Railway
    query_timeout_ms: int = 50  # Target 50ms queries
    slow_query_threshold_ms: int = 100
    enable_query_logging: bool = not is_railway_production  # Disable in prod
    
    # Railway SSL and security
    enable_ssl: bool = is_railway
    ssl_require: bool = is_railway_production
    
    # Caching settings
    enable_query_cache: bool = True
    cache_size: int = 2000 if is_railway else 1000
    cache_ttl_seconds: int = 300  # 5 minutes
    
    # Monitoring and alerting
    enable_metrics: bool = True
    metrics_retention_hours: int = 24
    alert_on_slow_queries: bool = is_railway_production
    
    # Backup and recovery (Railway-specific)
    enable_auto_backup: bool = is_railway_production
    backup_interval_hours: int = 6
    backup_retention_days: int = 7

def get_railway_database_config() -> RailwayDatabaseConfig:
    """Get Railway-optimized database configuration"""
    config = RailwayDatabaseConfig()
    
    # Log configuration for debugging
    logger.info(f"Railway Database Configuration:")
    logger.info(f"  Environment: {os.getenv('RAILWAY_ENVIRONMENT', 'local')}")
    logger.info(f"  Database Type: {'PostgreSQL' if config.database_url.startswith('postgresql') else 'SQLite'}")
    logger.info(f"  Max Connections: {config.max_connections}")
    logger.info(f"  SSL Enabled: {config.enable_ssl}")
    logger.info(f"  Query Cache: {config.enable_query_cache}")
    
    return config

def get_database_connection_string() -> str:
    """Get the appropriate database connection string for Railway"""
    # Railway automatically provides DATABASE_URL for PostgreSQL
    database_url = os.getenv('DATABASE_URL')
    
    if database_url:
        # Railway PostgreSQL
        if database_url.startswith('postgresql://'):
            logger.info("Using Railway PostgreSQL database")
            return database_url
        elif database_url.startswith('postgres://'):
            # Convert postgres:// to postgresql:// for compatibility
            logger.info("Converting postgres:// to postgresql:// for Railway")
            return database_url.replace('postgres://', 'postgresql://', 1)
    
    # Fallback to SQLite for local development
    sqlite_path = os.getenv('SQLITE_DATABASE_PATH', 'production_trading.db')
    logger.info(f"Using SQLite database: {sqlite_path}")
    return f'sqlite:///{sqlite_path}'

def validate_railway_environment() -> Dict[str, Any]:
    """Validate Railway environment and database configuration"""
    validation_results = {
        'valid': True,
        'warnings': [],
        'errors': [],
        'environment': {}
    }
    
    # Check Railway environment
    railway_env = os.getenv('RAILWAY_ENVIRONMENT')
    validation_results['environment']['railway_environment'] = railway_env
    validation_results['environment']['is_railway'] = bool(railway_env)
    
    # Check database configuration
    database_url = os.getenv('DATABASE_URL')
    validation_results['environment']['database_url_provided'] = bool(database_url)
    
    if railway_env and not database_url:
        validation_results['warnings'].append(
            "Running on Railway but DATABASE_URL not provided. Using SQLite fallback."
        )
    
    # Check PostgreSQL availability for Railway
    if database_url and database_url.startswith(('postgresql://', 'postgres://')):
        try:
            import psycopg2
            validation_results['environment']['postgresql_driver_available'] = True
        except ImportError:
            validation_results['errors'].append(
                "PostgreSQL database URL provided but psycopg2 driver not available"
            )
            validation_results['valid'] = False
    
    # Check SSL requirements
    if railway_env == 'production' and database_url:
        if not database_url.startswith(('postgresql://', 'postgres://')):
            validation_results['warnings'].append(
                "Production environment detected but not using PostgreSQL"
            )
    
    # Check connection limits
    max_connections = int(os.getenv('DATABASE_MAX_CONNECTIONS', '15'))
    if max_connections > 20:
        validation_results['warnings'].append(
            f"Max connections ({max_connections}) may exceed Railway limits"
        )
    
    return validation_results

def setup_railway_database_logging():
    """Setup database logging optimized for Railway"""
    railway_env = os.getenv('RAILWAY_ENVIRONMENT')
    
    # Configure logging based on environment
    if railway_env == 'production':
        # Minimal logging in production
        logging.getLogger('app.database').setLevel(logging.WARNING)
    elif railway_env in ['staging', 'development']:
        # More verbose logging in staging/dev
        logging.getLogger('app.database').setLevel(logging.INFO)
    else:
        # Full logging for local development
        logging.getLogger('app.database').setLevel(logging.DEBUG)
    
    logger.info(f"Database logging configured for Railway environment: {railway_env}")

# Railway-specific database utilities
class RailwayDatabaseUtils:
    """Utility functions for Railway database operations"""
    
    @staticmethod
    def get_connection_info() -> Dict[str, Any]:
        """Get database connection information for Railway"""
        database_url = get_database_connection_string()
        
        if database_url.startswith('postgresql://'):
            # Parse PostgreSQL connection info
            from urllib.parse import urlparse
            parsed = urlparse(database_url)
            
            return {
                'type': 'postgresql',
                'host': parsed.hostname,
                'port': parsed.port or 5432,
                'database': parsed.path.lstrip('/'),
                'username': parsed.username,
                'ssl_enabled': True,
                'railway_managed': True
            }
        else:
            # SQLite connection info
            db_path = database_url.replace('sqlite:///', '')
            return {
                'type': 'sqlite',
                'path': db_path,
                'file_exists': os.path.exists(db_path),
                'railway_managed': False
            }
    
    @staticmethod
    def check_railway_database_health() -> Dict[str, Any]:
        """Check database health specifically for Railway deployment"""
        try:
            from .optimized_manager import get_database_manager
            
            db_manager = get_database_manager()
            health_check = db_manager.health_check()
            
            # Add Railway-specific health checks
            railway_health = {
                'railway_environment': os.getenv('RAILWAY_ENVIRONMENT'),
                'database_url_configured': bool(os.getenv('DATABASE_URL')),
                'connection_info': RailwayDatabaseUtils.get_connection_info(),
                'core_health': health_check
            }
            
            return railway_health
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'railway_environment': os.getenv('RAILWAY_ENVIRONMENT')
            }
    
    @staticmethod
    def optimize_for_railway():
        """Apply Railway-specific database optimizations"""
        try:
            from .optimized_manager import get_database_manager
            
            db_manager = get_database_manager()
            
            # Run optimization
            db_manager.optimize_database()
            
            logger.info("Railway database optimization completed")
            return True
            
        except Exception as e:
            logger.error(f"Railway database optimization failed: {e}")
            return False

# Initialize Railway configuration on import
railway_config = get_railway_database_config()
setup_railway_database_logging()

# Validate environment
validation = validate_railway_environment()
if not validation['valid']:
    for error in validation['errors']:
        logger.error(f"Railway Database Configuration Error: {error}")
for warning in validation['warnings']:
    logger.warning(f"Railway Database Configuration Warning: {warning}")