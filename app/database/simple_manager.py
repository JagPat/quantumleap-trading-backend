"""
Simple Railway-Optimized Database Manager

Simplified version that avoids conflicts with existing Settings classes.
"""

import os
import sqlite3
import logging
import threading
import time
from contextlib import contextmanager
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class SimpleDatabaseManager:
    """Simplified Railway-optimized database manager"""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv('DATABASE_URL', 'sqlite:///production_trading.db')
        self.is_postgresql = self.database_url.startswith(('postgresql://', 'postgres://'))
        self._lock = threading.Lock()
        self.query_metrics = []
        
        # Initialize PostgreSQL support if available
        self.postgresql_available = False
        if self.is_postgresql:
            try:
                import psycopg2
                self.postgresql_available = True
                logger.info("PostgreSQL support available for Railway")
            except ImportError:
                logger.warning("PostgreSQL URL provided but psycopg2 not available, falling back to SQLite")
                self.database_url = 'sqlite:///production_trading.db'
                self.is_postgresql = False
        
        logger.info(f"Database manager initialized: {self.database_url[:50]}...")
    
    @contextmanager
    def get_connection(self):
        """Get database connection with automatic cleanup"""
        connection = None
        
        try:
            if self.is_postgresql and self.postgresql_available:
                import psycopg2
                connection = psycopg2.connect(self.database_url)
            else:
                # SQLite connection with optimizations
                db_path = self.database_url.replace('sqlite:///', '')
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else '.', exist_ok=True)
                
                connection = sqlite3.connect(db_path, timeout=30.0)
                connection.row_factory = sqlite3.Row  # Enable dict-like access
                
                # Apply SQLite optimizations
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("PRAGMA synchronous=NORMAL")
                connection.execute("PRAGMA cache_size=10000")
                connection.execute("PRAGMA temp_store=MEMORY")
            
            yield connection
            
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if connection:
                connection.close()
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute query with performance tracking"""
        start_time = time.time()
        
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
            self._record_metrics(execution_time, True)
            
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self._record_metrics(execution_time, False, str(e))
            logger.error(f"Query execution failed: {e}")
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
            logger.info(f"Transaction completed in {execution_time:.2f}ms")
            return True
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Transaction failed after {execution_time:.2f}ms: {e}")
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
            # Keep only last 1000 metrics
            if len(self.query_metrics) > 1000:
                self.query_metrics = self.query_metrics[-1000:]
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        with self._lock:
            if not self.query_metrics:
                return {'status': 'no_data'}
            
            recent_metrics = [m for m in self.query_metrics[-100:] if m['success']]
            
            if not recent_metrics:
                return {'status': 'no_recent_data'}
            
            execution_times = [m['execution_time_ms'] for m in recent_metrics]
            execution_times.sort()
            
            count = len(execution_times)
            
            return {
                'status': 'healthy',
                'query_count': count,
                'avg_execution_time_ms': sum(execution_times) / count,
                'p95_execution_time_ms': execution_times[int(count * 0.95)] if count > 0 else 0,
                'error_rate': len([m for m in self.query_metrics[-100:] if not m['success']]) / min(100, len(self.query_metrics)),
                'timestamp': datetime.now().isoformat()
            }
    
    def health_check(self) -> Dict[str, Any]:
        """Database health check"""
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
                
                return {
                    'status': 'healthy',
                    'database_type': db_type,
                    'version': version,
                    'performance': performance,
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def optimize_database(self) -> bool:
        """Run database optimization"""
        try:
            if self.is_postgresql and self.postgresql_available:
                self.execute_query("ANALYZE")
                logger.info("PostgreSQL ANALYZE completed")
            else:
                self.execute_query("ANALYZE")
                self.execute_query("VACUUM")
                logger.info("SQLite optimization completed")
            return True
        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
            return False

# Global instance
_db_manager = None

def get_simple_database_manager() -> SimpleDatabaseManager:
    """Get the global simple database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = SimpleDatabaseManager()
    return _db_manager