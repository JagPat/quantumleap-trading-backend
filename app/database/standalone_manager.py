"""
Standalone Railway Database Manager

Completely standalone database manager that doesn't depend on any
existing configuration classes to avoid conflicts.
"""

import os
import sqlite3
import logging
import threading
import time
from contextlib import contextmanager
from typing import Dict, Any, Optional, List
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import optimization components
try:
    from .query_optimizer import get_query_optimizer
    from .performance_collector import get_performance_collector
    OPTIMIZATION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Query optimization not available: {e}")
    OPTIMIZATION_AVAILABLE = False

class StandaloneDatabaseManager:
    """Standalone Railway-optimized database manager"""
    
    def __init__(self, database_url: Optional[str] = None):
        # Get database URL from environment or use default
        self.database_url = database_url or os.getenv('DATABASE_URL', 'sqlite:///production_trading.db')
        self.is_postgresql = self.database_url.startswith(('postgresql://', 'postgres://'))
        self._lock = threading.Lock()
        self.query_metrics = []
        
        # Check PostgreSQL availability
        self.postgresql_available = False
        if self.is_postgresql:
            try:
                import psycopg2
                self.postgresql_available = True
                logger.info("✅ PostgreSQL support available for Railway")
            except ImportError:
                logger.warning("⚠️  PostgreSQL URL provided but psycopg2 not available, falling back to SQLite")
                self.database_url = 'sqlite:///production_trading.db'
                self.is_postgresql = False
        
        # Initialize optimization components
        self.query_optimizer = None
        self.performance_collector = None
        
        if OPTIMIZATION_AVAILABLE:
            try:
                self.query_optimizer = get_query_optimizer(self)
                self.performance_collector = get_performance_collector()
                logger.info("🔧 Query optimization and performance monitoring enabled")
            except Exception as e:
                logger.warning(f"⚠️  Optimization components not available: {e}")
        
        logger.info(f"🗄️  Database manager initialized")
        logger.info(f"   URL: {self.database_url[:50]}...")
        logger.info(f"   Type: {'PostgreSQL' if self.is_postgresql else 'SQLite'}")
        logger.info(f"   Optimization: {'Enabled' if self.query_optimizer else 'Disabled'}")
    
    @contextmanager
    def get_connection(self):
        """Get database connection with automatic cleanup"""
        connection = None
        
        try:
            if self.is_postgresql and self.postgresql_available:
                import psycopg2
                connection = psycopg2.connect(self.database_url)
                logger.debug("Connected to PostgreSQL")
            else:
                # SQLite connection with optimizations
                db_path = self.database_url.replace('sqlite:///', '')
                
                # Ensure directory exists
                db_dir = os.path.dirname(db_path)
                if db_dir:
                    os.makedirs(db_dir, exist_ok=True)
                
                connection = sqlite3.connect(db_path, timeout=30.0)
                connection.row_factory = sqlite3.Row  # Enable dict-like access
                
                # Apply SQLite optimizations for Railway
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("PRAGMA synchronous=NORMAL")
                connection.execute("PRAGMA cache_size=10000")
                connection.execute("PRAGMA temp_store=MEMORY")
                connection.execute("PRAGMA mmap_size=268435456")  # 256MB
                
                logger.debug("Connected to SQLite with optimizations")
            
            yield connection
            
        except Exception as e:
            logger.error(f"❌ Database connection error: {e}")
            raise
        finally:
            if connection:
                connection.close()
                logger.debug("Database connection closed")
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute query with performance tracking and optimization"""
        start_time = time.time()
        query_hash = None
        
        # Analyze query for optimization if available
        if self.query_optimizer:
            try:
                query_hash = self.query_optimizer._hash_query(query)
                # Get optimized query if available
                plan = self.query_optimizer.analyze_query(query)
                if plan.optimized_query:
                    logger.debug(f"🔧 Using optimized query for {query_hash[:8]}")
                    query = plan.optimized_query
            except Exception as e:
                logger.debug(f"Query optimization failed: {e}")
        
        try:
            with self.get_connection() as conn:
                if self.is_postgresql and self.postgresql_available:
                    with conn.cursor() as cursor:
                        cursor.execute(query, params or ())
                        if cursor.description:
                            columns = [desc[0] for desc in cursor.description]
                            rows = cursor.fetchall()
                            result = [dict(zip(columns, row)) for row in rows]
                        else:
                            result = []
                        conn.commit()
                else:
                    cursor = conn.cursor()
                    cursor.execute(query, params or ())
                    if cursor.description:
                        result = [dict(row) for row in cursor.fetchall()]
                    else:
                        result = []
                    conn.commit()
            
            execution_time = (time.time() - start_time) * 1000
            
            # Record metrics with optimization components
            self._record_metrics(execution_time, True)
            
            if self.performance_collector and query_hash:
                self.performance_collector.record_query_performance(
                    query_hash, execution_time, True
                )
            
            if self.query_optimizer:
                self.query_optimizer.analyze_query(query, execution_time)
            
            logger.debug(f"Query executed in {execution_time:.2f}ms")
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            # Record error metrics
            self._record_metrics(execution_time, False, str(e))
            
            if self.performance_collector and query_hash:
                self.performance_collector.record_query_performance(
                    query_hash, execution_time, False, str(e)
                )
            
            logger.error(f"❌ Query execution failed after {execution_time:.2f}ms: {e}")
            raise
    
    def execute_transaction(self, operations: List[Dict[str, Any]]) -> bool:
        """Execute multiple operations in a transaction"""
        start_time = time.time()
        
        try:
            with self.get_connection() as conn:
                if self.is_postgresql and self.postgresql_available:
                    conn.autocommit = False
                    try:
                        with conn.cursor() as cursor:
                            for op in operations:
                                cursor.execute(op['query'], op.get('params', ()))
                        conn.commit()
                    except Exception:
                        conn.rollback()
                        raise
                    finally:
                        conn.autocommit = True
                else:
                    conn.execute("BEGIN TRANSACTION")
                    try:
                        cursor = conn.cursor()
                        for op in operations:
                            cursor.execute(op['query'], op.get('params', ()))
                        conn.commit()
                    except Exception:
                        conn.rollback()
                        raise
            
            execution_time = (time.time() - start_time) * 1000
            logger.info(f"✅ Transaction completed in {execution_time:.2f}ms")
            return True
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"❌ Transaction failed after {execution_time:.2f}ms: {e}")
            return False
    
    def _record_metrics(self, execution_time_ms: float, success: bool, error: Optional[str] = None):
        """Record query metrics"""
        metric = {
            'execution_time_ms': execution_time_ms,
            'timestamp': datetime.now().isoformat(),
            'success': success,
            'error': error
        }
        
        with self._lock:
            self.query_metrics.append(metric)
            # Keep only last 1000 metrics to prevent memory issues
            if len(self.query_metrics) > 1000:
                self.query_metrics = self.query_metrics[-1000:]
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        with self._lock:
            if not self.query_metrics:
                return {
                    'status': 'no_data',
                    'message': 'No query metrics available yet'
                }
            
            # Get recent successful queries
            recent_metrics = [m for m in self.query_metrics[-100:] if m['success']]
            
            if not recent_metrics:
                return {
                    'status': 'no_recent_data',
                    'message': 'No recent successful queries'
                }
            
            execution_times = [m['execution_time_ms'] for m in recent_metrics]
            execution_times.sort()
            
            count = len(execution_times)
            total_queries = len(self.query_metrics[-100:])
            
            return {
                'status': 'healthy',
                'query_count': count,
                'total_queries': total_queries,
                'avg_execution_time_ms': round(sum(execution_times) / count, 2),
                'p50_execution_time_ms': execution_times[count // 2] if count > 0 else 0,
                'p95_execution_time_ms': execution_times[int(count * 0.95)] if count > 0 else 0,
                'p99_execution_time_ms': execution_times[int(count * 0.99)] if count > 0 else 0,
                'error_rate': round((total_queries - count) / total_queries, 3) if total_queries > 0 else 0,
                'timestamp': datetime.now().isoformat()
            }
    
    def health_check(self) -> Dict[str, Any]:
        """Comprehensive database health check"""
        try:
            with self.get_connection() as conn:
                if self.is_postgresql and self.postgresql_available:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT version()")
                        version = cursor.fetchone()[0]
                        db_type = 'postgresql'
                else:
                    cursor = conn.cursor()
                    cursor.execute("SELECT sqlite_version()")
                    version = cursor.fetchone()[0]
                    db_type = 'sqlite'
                
                performance = self.get_performance_metrics()
                
                # Determine overall health status
                overall_status = 'healthy'
                if performance.get('p95_execution_time_ms', 0) > 100:
                    overall_status = 'degraded'
                if performance.get('error_rate', 0) > 0.05:  # 5% error rate
                    overall_status = 'unhealthy'
                
                return {
                    'status': overall_status,
                    'database': {
                        'type': db_type,
                        'version': version,
                        'url_configured': bool(self.database_url),
                        'postgresql_available': self.postgresql_available
                    },
                    'performance': performance,
                    'railway': {
                        'environment': os.getenv('RAILWAY_ENVIRONMENT', 'local'),
                        'database_url_provided': bool(os.getenv('DATABASE_URL'))
                    },
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'database': {
                    'type': 'postgresql' if self.is_postgresql else 'sqlite',
                    'url_configured': bool(self.database_url),
                    'postgresql_available': self.postgresql_available
                },
                'timestamp': datetime.now().isoformat()
            }
    
    def optimize_database(self) -> bool:
        """Run database optimization procedures"""
        try:
            if self.is_postgresql and self.postgresql_available:
                # PostgreSQL optimizations
                self.execute_query("ANALYZE")
                logger.info("✅ PostgreSQL ANALYZE completed")
            else:
                # SQLite optimizations
                self.execute_query("ANALYZE")
                self.execute_query("VACUUM")
                self.execute_query("PRAGMA optimize")
                logger.info("✅ SQLite optimization completed")
            return True
        except Exception as e:
            logger.error(f"❌ Database optimization failed: {e}")
            return False
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get database connection information"""
        if self.is_postgresql:
            from urllib.parse import urlparse
            try:
                parsed = urlparse(self.database_url)
                return {
                    'type': 'postgresql',
                    'host': parsed.hostname,
                    'port': parsed.port or 5432,
                    'database': parsed.path.lstrip('/') if parsed.path else '',
                    'username': parsed.username,
                    'ssl_enabled': True,
                    'railway_managed': bool(os.getenv('RAILWAY_ENVIRONMENT'))
                }
            except Exception as e:
                return {
                    'type': 'postgresql',
                    'error': f'Failed to parse URL: {e}',
                    'railway_managed': bool(os.getenv('RAILWAY_ENVIRONMENT'))
                }
        else:
            db_path = self.database_url.replace('sqlite:///', '')
            return {
                'type': 'sqlite',
                'path': db_path,
                'file_exists': os.path.exists(db_path),
                'file_size_mb': round(os.path.getsize(db_path) / 1024 / 1024, 2) if os.path.exists(db_path) else 0,
                'railway_managed': False
            }
    
    def get_query_recommendations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get query optimization recommendations"""
        if not self.query_optimizer:
            return []
        
        try:
            return self.query_optimizer.get_query_recommendations(limit)
        except Exception as e:
            logger.error(f"Failed to get query recommendations: {e}")
            return []
    
    def get_index_recommendations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get index recommendations"""
        if not self.query_optimizer:
            return []
        
        try:
            return self.query_optimizer.get_index_recommendations(limit)
        except Exception as e:
            logger.error(f"Failed to get index recommendations: {e}")
            return []
    
    def get_performance_dashboard(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """Get comprehensive performance dashboard"""
        if not self.performance_collector:
            return {
                'status': 'optimization_disabled',
                'message': 'Performance monitoring not available'
            }
        
        try:
            return self.performance_collector.get_performance_dashboard(time_window_minutes)
        except Exception as e:
            logger.error(f"Failed to get performance dashboard: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get optimization system summary"""
        summary = {
            'optimization_enabled': bool(self.query_optimizer),
            'performance_monitoring_enabled': bool(self.performance_collector),
            'timestamp': datetime.now().isoformat()
        }
        
        if self.query_optimizer:
            try:
                summary['query_optimizer'] = self.query_optimizer.get_performance_summary()
            except Exception as e:
                summary['query_optimizer_error'] = str(e)
        
        if self.performance_collector:
            try:
                summary['system_health'] = self.performance_collector._calculate_system_health()
                summary['active_alerts'] = len(self.performance_collector.active_alerts)
            except Exception as e:
                summary['performance_collector_error'] = str(e)
        
        return summary

# Global instance for Railway deployment
_standalone_db_manager = None

def get_standalone_database_manager() -> StandaloneDatabaseManager:
    """Get the global standalone database manager instance"""
    global _standalone_db_manager
    if _standalone_db_manager is None:
        _standalone_db_manager = StandaloneDatabaseManager()
    return _standalone_db_manager

# Utility functions for Railway integration
def check_railway_database_health() -> Dict[str, Any]:
    """Check database health specifically for Railway deployment"""
    try:
        db_manager = get_standalone_database_manager()
        return db_manager.health_check()
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'railway_environment': os.getenv('RAILWAY_ENVIRONMENT'),
            'timestamp': datetime.now().isoformat()
        }

def optimize_for_railway() -> bool:
    """Apply Railway-specific database optimizations"""
    try:
        db_manager = get_standalone_database_manager()
        return db_manager.optimize_database()
    except Exception as e:
        logger.error(f"❌ Railway database optimization failed: {e}")
        return False

def get_railway_connection_info() -> Dict[str, Any]:
    """Get Railway database connection information"""
    try:
        db_manager = get_standalone_database_manager()
        return db_manager.get_connection_info()
    except Exception as e:
        return {
            'error': str(e),
            'railway_environment': os.getenv('RAILWAY_ENVIRONMENT')
        }

def get_query_optimization_recommendations(limit: int = 10) -> List[Dict[str, Any]]:
    """Get query optimization recommendations for Railway"""
    try:
        db_manager = get_standalone_database_manager()
        return db_manager.get_query_recommendations(limit)
    except Exception as e:
        logger.error(f"❌ Failed to get query recommendations: {e}")
        return []

def get_index_optimization_recommendations(limit: int = 10) -> List[Dict[str, Any]]:
    """Get index recommendations for Railway"""
    try:
        db_manager = get_standalone_database_manager()
        return db_manager.get_index_recommendations(limit)
    except Exception as e:
        logger.error(f"❌ Failed to get index recommendations: {e}")
        return []

def get_railway_performance_dashboard(time_window_minutes: int = 60) -> Dict[str, Any]:
    """Get Railway performance dashboard"""
    try:
        db_manager = get_standalone_database_manager()
        return db_manager.get_performance_dashboard(time_window_minutes)
    except Exception as e:
        logger.error(f"❌ Failed to get performance dashboard: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'railway_environment': os.getenv('RAILWAY_ENVIRONMENT')
        }

def get_railway_optimization_summary() -> Dict[str, Any]:
    """Get Railway optimization system summary"""
    try:
        db_manager = get_standalone_database_manager()
        return db_manager.get_optimization_summary()
    except Exception as e:
        logger.error(f"❌ Failed to get optimization summary: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'railway_environment': os.getenv('RAILWAY_ENVIRONMENT')
        }