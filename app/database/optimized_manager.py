"""
Railway-Optimized Database Manager

High-performance database manager designed for Railway deployment
with support for both SQLite (development) and PostgreSQL (production).
"""

import os
import sqlite3
import logging
import threading
import time
from contextlib import contextmanager
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import json

# Try to import PostgreSQL support for Railway production
try:
    import psycopg2
    import psycopg2.pool
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Database configuration for Railway deployment"""
    # Railway automatically provides DATABASE_URL for PostgreSQL
    database_url: str = os.getenv('DATABASE_URL', 'sqlite:///production_trading.db')
    
    # Connection pool settings optimized for Railway
    min_connections: int = 2
    max_connections: int = 20  # Railway has connection limits
    connection_timeout: int = 30
    idle_timeout: int = 300
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # Performance settings
    query_timeout: int = 50  # 50ms target
    enable_wal_mode: bool = True  # For SQLite performance
    enable_query_cache: bool = True
    cache_size: int = 1000
    
    # Railway-specific settings
    enable_ssl: bool = True  # Railway requires SSL for PostgreSQL
    pool_pre_ping: bool = True  # Check connections before use

@dataclass
class QueryMetrics:
    """Query performance metrics"""
    query_hash: str
    execution_time_ms: float
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None

class ConnectionPool:
    """Railway-optimized connection pool"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.is_postgresql = config.database_url.startswith('postgresql://')
        self._pool = None
        self._sqlite_connections = {}
        self._lock = threading.Lock()
        self._metrics = []
        
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize connection pool based on database type"""
        if self.is_postgresql and POSTGRESQL_AVAILABLE:
            self._initialize_postgresql_pool()
        else:
            self._initialize_sqlite_pool()
    
    def _initialize_postgresql_pool(self):
        """Initialize PostgreSQL connection pool for Railway"""
        try:
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=self.config.min_connections,
                maxconn=self.config.max_connections,
                dsn=self.config.database_url,
                connect_timeout=self.config.connection_timeout
            )
            logger.info("PostgreSQL connection pool initialized for Railway")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL pool: {e}")
            # Fallback to SQLite
            self._initialize_sqlite_pool()
    
    def _initialize_sqlite_pool(self):
        """Initialize SQLite connection management"""
        # Extract database path from URL
        if self.config.database_url.startswith('sqlite:///'):
            db_path = self.config.database_url[10:]  # Remove 'sqlite:///'
        else:
            db_path = 'production_trading.db'
        
        self.db_path = db_path
        self.is_postgresql = False
        
        # Ensure database directory exists
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else '.', exist_ok=True)
        
        logger.info(f"SQLite connection management initialized: {db_path}")
    
    @contextmanager
    def get_connection(self):
        """Get database connection with automatic cleanup"""
        connection = None
        start_time = time.time()
        
        try:
            if self.is_postgresql and self._pool:
                connection = self._pool.getconn()
                if self.config.pool_pre_ping:
                    # Test connection
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT 1")
            else:
                connection = self._get_sqlite_connection()
            
            yield connection
            
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            if connection and self.is_postgresql:
                # Mark connection as bad
                self._pool.putconn(connection, close=True)
                connection = None
            raise
        finally:
            execution_time = (time.time() - start_time) * 1000
            
            if connection:
                if self.is_postgresql and self._pool:
                    self._pool.putconn(connection)
                elif not self.is_postgresql:
                    self._return_sqlite_connection(connection)
            
            # Record metrics
            self._record_connection_metrics(execution_time)
    
    def _get_sqlite_connection(self):
        """Get SQLite connection with optimizations"""
        thread_id = threading.get_ident()
        
        with self._lock:
            if thread_id not in self._sqlite_connections:
                conn = sqlite3.connect(
                    self.db_path,
                    timeout=self.config.connection_timeout,
                    check_same_thread=False
                )
                
                # Apply SQLite optimizations
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA cache_size=10000")
                conn.execute("PRAGMA temp_store=MEMORY")
                conn.execute("PRAGMA mmap_size=268435456")  # 256MB
                
                self._sqlite_connections[thread_id] = conn
            
            return self._sqlite_connections[thread_id]
    
    def _return_sqlite_connection(self, connection):
        """Return SQLite connection (no-op for thread-local connections)"""
        pass
    
    def _record_connection_metrics(self, execution_time_ms: float):
        """Record connection performance metrics"""
        metric = {
            'type': 'connection',
            'execution_time_ms': execution_time_ms,
            'timestamp': datetime.now().isoformat(),
            'database_type': 'postgresql' if self.is_postgresql else 'sqlite'
        }
        
        with self._lock:
            self._metrics.append(metric)
            # Keep only last 1000 metrics
            if len(self._metrics) > 1000:
                self._metrics = self._metrics[-1000:]
    
    def get_metrics(self) -> List[Dict[str, Any]]:
        """Get connection metrics"""
        with self._lock:
            return self._metrics.copy()
    
    def health_check(self) -> Dict[str, Any]:
        """Check connection pool health"""
        try:
            with self.get_connection() as conn:
                if self.is_postgresql:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT version()")
                        version = cursor.fetchone()[0]
                else:
                    cursor = conn.cursor()
                    cursor.execute("SELECT sqlite_version()")
                    version = cursor.fetchone()[0]
                
                return {
                    'status': 'healthy',
                    'database_type': 'postgresql' if self.is_postgresql else 'sqlite',
                    'version': version,
                    'pool_size': self.config.max_connections if self.is_postgresql else len(self._sqlite_connections),
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

class OptimizedDatabaseManager:
    """Railway-optimized database manager"""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self.pool = ConnectionPool(self.config)
        self.query_cache = {} if self.config.enable_query_cache else None
        self.query_metrics = []
        self._lock = threading.Lock()
        
        logger.info(f"Database manager initialized for Railway deployment")
        logger.info(f"Database URL: {self.config.database_url[:50]}...")
    
    def execute_query(self, query: str, params: Optional[tuple] = None, 
                     timeout: Optional[int] = None) -> List[Dict[str, Any]]:
        """Execute query with performance optimization"""
        timeout = timeout or self.config.query_timeout
        start_time = time.time()
        query_hash = hash(query)
        
        # Check cache first
        if self.query_cache and params is None:
            cached_result = self.query_cache.get(query_hash)
            if cached_result and (time.time() - cached_result['timestamp']) < 300:  # 5 min cache
                return cached_result['data']
        
        try:
            with self.pool.get_connection() as conn:
                if self.pool.is_postgresql:
                    with conn.cursor() as cursor:
                        cursor.execute(query, params or ())
                        if cursor.description:
                            columns = [desc[0] for desc in cursor.description]
                            rows = cursor.fetchall()
                            result = [dict(zip(columns, row)) for row in rows]
                        else:
                            result = []
                else:
                    cursor = conn.cursor()
                    cursor.execute(query, params or ())
                    if cursor.description:
                        columns = [desc[0] for desc in cursor.description]
                        rows = cursor.fetchall()
                        result = [dict(zip(columns, row)) for row in rows]
                    else:
                        result = []
                    conn.commit()
            
            execution_time = (time.time() - start_time) * 1000
            
            # Cache result if applicable
            if self.query_cache and params is None and execution_time > 10:  # Cache slow queries
                self.query_cache[query_hash] = {
                    'data': result,
                    'timestamp': time.time()
                }
                
                # Limit cache size
                if len(self.query_cache) > self.config.cache_size:
                    oldest_key = min(self.query_cache.keys(), 
                                   key=lambda k: self.query_cache[k]['timestamp'])
                    del self.query_cache[oldest_key]
            
            # Record metrics
            self._record_query_metrics(query_hash, execution_time, True)
            
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self._record_query_metrics(query_hash, execution_time, False, str(e))
            logger.error(f"Query execution failed: {e}")
            raise
    
    def execute_transaction(self, operations: List[Dict[str, Any]]) -> bool:
        """Execute multiple operations in a transaction"""
        start_time = time.time()
        
        try:
            with self.pool.get_connection() as conn:
                if self.pool.is_postgresql:
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
            logger.info(f"Transaction completed in {execution_time:.2f}ms")
            return True
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Transaction failed after {execution_time:.2f}ms: {e}")
            return False
    
    def _record_query_metrics(self, query_hash: str, execution_time_ms: float, 
                            success: bool, error_message: Optional[str] = None):
        """Record query performance metrics"""
        metric = QueryMetrics(
            query_hash=str(query_hash),
            execution_time_ms=execution_time_ms,
            timestamp=datetime.now(),
            success=success,
            error_message=error_message
        )
        
        with self._lock:
            self.query_metrics.append(metric)
            # Keep only last 10000 metrics
            if len(self.query_metrics) > 10000:
                self.query_metrics = self.query_metrics[-10000:]
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        with self._lock:
            if not self.query_metrics:
                return {'status': 'no_data'}
            
            recent_metrics = [m for m in self.query_metrics 
                            if m.timestamp > datetime.now() - timedelta(hours=1)]
            
            if not recent_metrics:
                return {'status': 'no_recent_data'}
            
            execution_times = [m.execution_time_ms for m in recent_metrics if m.success]
            
            if not execution_times:
                return {'status': 'no_successful_queries'}
            
            execution_times.sort()
            count = len(execution_times)
            
            return {
                'status': 'healthy',
                'query_count': count,
                'avg_execution_time_ms': sum(execution_times) / count,
                'p50_execution_time_ms': execution_times[count // 2],
                'p95_execution_time_ms': execution_times[int(count * 0.95)],
                'p99_execution_time_ms': execution_times[int(count * 0.99)],
                'error_rate': len([m for m in recent_metrics if not m.success]) / len(recent_metrics),
                'cache_hit_rate': len(self.query_cache) / max(count, 1) if self.query_cache else 0,
                'timestamp': datetime.now().isoformat()
            }
    
    def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for Railway deployment"""
        pool_health = self.pool.health_check()
        performance_metrics = self.get_performance_metrics()
        
        overall_status = 'healthy'
        if pool_health['status'] != 'healthy':
            overall_status = 'unhealthy'
        elif performance_metrics.get('p95_execution_time_ms', 0) > 100:
            overall_status = 'degraded'
        
        return {
            'status': overall_status,
            'database': pool_health,
            'performance': performance_metrics,
            'config': {
                'database_type': 'postgresql' if self.pool.is_postgresql else 'sqlite',
                'max_connections': self.config.max_connections,
                'query_timeout_ms': self.config.query_timeout,
                'cache_enabled': self.config.enable_query_cache
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def optimize_database(self):
        """Run database optimization procedures"""
        try:
            if self.pool.is_postgresql:
                # PostgreSQL optimizations
                self.execute_query("ANALYZE")
                logger.info("PostgreSQL ANALYZE completed")
            else:
                # SQLite optimizations
                self.execute_query("ANALYZE")
                self.execute_query("VACUUM")
                self.execute_query("PRAGMA optimize")
                logger.info("SQLite optimization completed")
        except Exception as e:
            logger.error(f"Database optimization failed: {e}")

# Global database manager instance for Railway
db_manager = OptimizedDatabaseManager()

def get_database_manager() -> OptimizedDatabaseManager:
    """Get the global database manager instance"""
    return db_manager