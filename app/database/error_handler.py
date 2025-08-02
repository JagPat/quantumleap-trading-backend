#!/usr/bin/env python3
"""
Database Error Handler
Comprehensive error handling system with categorized error processing,
automatic retry mechanisms, circuit breaker patterns, and intelligent recovery
"""
import os
import sqlite3
import threading
import time
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import random
import traceback
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ErrorCategory(Enum):
    """Database error categories"""
    CONNECTION_ERROR = "connection_error"
    QUERY_ERROR = "query_error"
    TRANSACTION_ERROR = "transaction_error"
    CONSTRAINT_ERROR = "constraint_error"
    TIMEOUT_ERROR = "timeout_error"
    LOCK_ERROR = "lock_error"
    DISK_ERROR = "disk_error"
    CORRUPTION_ERROR = "corruption_error"
    PERMISSION_ERROR = "permission_error"
    UNKNOWN_ERROR = "unknown_error"

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RecoveryAction(Enum):
    """Recovery action types"""
    RETRY = "retry"
    RECONNECT = "reconnect"
    ROLLBACK = "rollback"
    FAILOVER = "failover"
    MANUAL_INTERVENTION = "manual_intervention"
    IGNORE = "ignore"

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

@dataclass

class DatabaseError:
    """Database error information"""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    original_exception: Optional[Exception]
    timestamp: datetime
    context: Dict[str, Any]
    stack_trace: str
    recovery_action: Optional[RecoveryAction] = None
    retry_count: int = 0
    resolved: bool = False

@dataclass
class RetryPolicy:
    """Retry policy configuration"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on_categories: List[ErrorCategory] = None
    
    def __post_init__(self):
        if self.retry_on_categories is None:
            self.retry_on_categories = [
                ErrorCategory.CONNECTION_ERROR,
                ErrorCategory.TIMEOUT_ERROR,
                ErrorCategory.LOCK_ERROR
            ]

@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5
    recovery_timeout: int = 60
    success_threshold: int = 3
    timeout: float = 30.0

class CircuitBreaker:
    """Circuit breaker implementation for database operations"""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.lock = threading.RLock()
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        with self.lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    logger.info("Circuit breaker transitioning to HALF_OPEN")
                else:
                    raise CircuitBreakerOpenError("Circuit breaker is OPEN")
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except Exception as e:
                self._on_failure()
                raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset"""
        if self.last_failure_time is None:
            return True
        
        time_since_failure = time.time() - self.last_failure_time
        return time_since_failure >= self.config.recovery_timeout
    
    def _on_success(self):
        """Handle successful operation"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                logger.info("Circuit breaker reset to CLOSED")
        else:
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning("Circuit breaker opened from HALF_OPEN")
        elif self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time
        }

class DatabaseErrorHandler:
    """Comprehensive database error handling system"""
    
    def __init__(self, database_path: str = None):
        self.database_path = database_path or os.getenv("DATABASE_PATH", "trading_errors.db")
        
        # Error handling configuration
        self.retry_policies: Dict[ErrorCategory, RetryPolicy] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.error_handlers: Dict[ErrorCategory, Callable] = {}
        self.error_history: List[DatabaseError] = []
        
        # Threading
        self.error_lock = threading.RLock()
        
        # Statistics
        self.error_stats = {
            "total_errors": 0,
            "errors_by_category": {},
            "errors_by_severity": {},
            "recovery_success_rate": 0.0
        }
        
        # Initialize system
        self._initialize_error_db()
        self._setup_default_policies()
        self._setup_default_handlers()
        self._setup_circuit_breakers()
    
    def _initialize_error_db(self):
        """Initialize error tracking database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Create error log table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS error_log (
                        error_id TEXT PRIMARY KEY,
                        category TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        message TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        context TEXT,
                        stack_trace TEXT,
                        recovery_action TEXT,
                        retry_count INTEGER DEFAULT 0,
                        resolved BOOLEAN DEFAULT FALSE
                    )
                """)
                
                # Create error statistics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS error_statistics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        category TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        count INTEGER NOT NULL,
                        recovery_success_rate REAL
                    )
                """)
                
                # Create circuit breaker state table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS circuit_breaker_state (
                        breaker_id TEXT PRIMARY KEY,
                        state TEXT NOT NULL,
                        failure_count INTEGER NOT NULL,
                        success_count INTEGER NOT NULL,
                        last_failure_time REAL,
                        updated_at TEXT NOT NULL
                    )
                """)
                
                # Create indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_error_log_timestamp ON error_log(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_error_log_category ON error_log(category)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_error_statistics_timestamp ON error_statistics(timestamp)")
                
                conn.commit()
                logger.info("✅ Error handling database initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize error database: {e}")
            raise
    
    def _setup_default_policies(self):
        """Setup default retry policies"""
        # Connection errors - aggressive retry
        self.retry_policies[ErrorCategory.CONNECTION_ERROR] = RetryPolicy(
            max_attempts=5,
            base_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0
        )
        
        # Timeout errors - moderate retry
        self.retry_policies[ErrorCategory.TIMEOUT_ERROR] = RetryPolicy(
            max_attempts=3,
            base_delay=2.0,
            max_delay=60.0,
            exponential_base=1.5
        )
        
        # Lock errors - quick retry
        self.retry_policies[ErrorCategory.LOCK_ERROR] = RetryPolicy(
            max_attempts=10,
            base_delay=0.1,
            max_delay=5.0,
            exponential_base=1.2
        )
        
        # Query errors - limited retry
        self.retry_policies[ErrorCategory.QUERY_ERROR] = RetryPolicy(
            max_attempts=2,
            base_delay=0.5,
            max_delay=10.0
        )
        
        # No retry for these categories
        for category in [ErrorCategory.CONSTRAINT_ERROR, ErrorCategory.CORRUPTION_ERROR]:
            self.retry_policies[category] = RetryPolicy(max_attempts=1)
    
    def _setup_default_handlers(self):
        """Setup default error handlers"""
        self.error_handlers[ErrorCategory.CONNECTION_ERROR] = self._handle_connection_error
        self.error_handlers[ErrorCategory.QUERY_ERROR] = self._handle_query_error
        self.error_handlers[ErrorCategory.TRANSACTION_ERROR] = self._handle_transaction_error
        self.error_handlers[ErrorCategory.CONSTRAINT_ERROR] = self._handle_constraint_error
        self.error_handlers[ErrorCategory.TIMEOUT_ERROR] = self._handle_timeout_error
        self.error_handlers[ErrorCategory.LOCK_ERROR] = self._handle_lock_error
        self.error_handlers[ErrorCategory.DISK_ERROR] = self._handle_disk_error
        self.error_handlers[ErrorCategory.CORRUPTION_ERROR] = self._handle_corruption_error
        self.error_handlers[ErrorCategory.PERMISSION_ERROR] = self._handle_permission_error
        self.error_handlers[ErrorCategory.UNKNOWN_ERROR] = self._handle_unknown_error
    
    def _setup_circuit_breakers(self):
        """Setup circuit breakers for different operations"""
        # Database connection circuit breaker
        self.circuit_breakers["connection"] = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=30,
                success_threshold=2
            )
        )
        
        # Query execution circuit breaker
        self.circuit_breakers["query"] = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=60,
                success_threshold=3
            )
        )
        
        # Transaction circuit breaker
        self.circuit_breakers["transaction"] = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=45,
                success_threshold=2
            )
        )
    
    def handle_error(self, exception: Exception, context: Dict[str, Any] = None) -> DatabaseError:
        """Handle database error with categorization and recovery"""
        try:
            # Categorize error
            category = self._categorize_error(exception)
            severity = self._determine_severity(category, exception)
            
            # Create error record
            error = DatabaseError(
                error_id=self._generate_error_id(),
                category=category,
                severity=severity,
                message=str(exception),
                original_exception=exception,
                timestamp=datetime.now(),
                context=context or {},
                stack_trace=traceback.format_exc()
            )
            
            # Store error
            with self.error_lock:
                self.error_history.append(error)
                self._store_error(error)
                self._update_statistics(error)
            
            # Determine recovery action
            recovery_action = self._determine_recovery_action(error)
            error.recovery_action = recovery_action
            
            # Execute error handler
            if category in self.error_handlers:
                try:
                    self.error_handlers[category](error)
                except Exception as handler_error:
                    logger.error(f"Error handler failed: {handler_error}")
            
            logger.error(f"Database error handled: {error.error_id} - {category.value} - {error.message}")
            return error
            
        except Exception as e:
            logger.error(f"Failed to handle database error: {e}")
            # Return minimal error record
            return DatabaseError(
                error_id=self._generate_error_id(),
                category=ErrorCategory.UNKNOWN_ERROR,
                severity=ErrorSeverity.HIGH,
                message=str(exception),
                original_exception=exception,
                timestamp=datetime.now(),
                context={},
                stack_trace=traceback.format_exc()
            )
    
    def _categorize_error(self, exception: Exception) -> ErrorCategory:
        """Categorize database error"""
        error_message = str(exception).lower()
        
        # Connection errors
        if any(keyword in error_message for keyword in [
            'connection', 'connect', 'network', 'host', 'unreachable', 'temporary failure'
        ]):
            return ErrorCategory.CONNECTION_ERROR
        
        # Timeout errors
        if any(keyword in error_message for keyword in [
            'timeout', 'timed out', 'deadline exceeded', 'temporary error'
        ]):
            return ErrorCategory.TIMEOUT_ERROR
        
        # Lock errors
        if any(keyword in error_message for keyword in [
            'lock', 'locked', 'deadlock', 'busy'
        ]):
            return ErrorCategory.LOCK_ERROR
        
        # Constraint errors
        if any(keyword in error_message for keyword in [
            'constraint', 'unique', 'foreign key', 'check constraint'
        ]):
            return ErrorCategory.CONSTRAINT_ERROR
        
        # Transaction errors
        if any(keyword in error_message for keyword in [
            'transaction', 'rollback', 'commit'
        ]):
            return ErrorCategory.TRANSACTION_ERROR
        
        # Disk errors
        if any(keyword in error_message for keyword in [
            'disk', 'space', 'full', 'no space', 'i/o error'
        ]):
            return ErrorCategory.DISK_ERROR
        
        # Corruption errors
        if any(keyword in error_message for keyword in [
            'corrupt', 'malformed', 'damaged', 'integrity'
        ]):
            return ErrorCategory.CORRUPTION_ERROR
        
        # Permission errors
        if any(keyword in error_message for keyword in [
            'permission', 'access denied', 'unauthorized'
        ]):
            return ErrorCategory.PERMISSION_ERROR
        
        # Query errors
        if any(keyword in error_message for keyword in [
            'syntax', 'column', 'table', 'sql'
        ]):
            return ErrorCategory.QUERY_ERROR
        
        return ErrorCategory.UNKNOWN_ERROR
    
    def _determine_severity(self, category: ErrorCategory, exception: Exception) -> ErrorSeverity:
        """Determine error severity"""
        # Critical errors
        if category in [ErrorCategory.CORRUPTION_ERROR, ErrorCategory.DISK_ERROR]:
            return ErrorSeverity.CRITICAL
        
        # High severity errors
        if category in [ErrorCategory.CONNECTION_ERROR, ErrorCategory.TRANSACTION_ERROR]:
            return ErrorSeverity.HIGH
        
        # Medium severity errors
        if category in [ErrorCategory.TIMEOUT_ERROR, ErrorCategory.LOCK_ERROR]:
            return ErrorSeverity.MEDIUM
        
        # Low severity errors
        return ErrorSeverity.LOW
    
    def _determine_recovery_action(self, error: DatabaseError) -> RecoveryAction:
        """Determine appropriate recovery action"""
        if error.category == ErrorCategory.CONNECTION_ERROR:
            return RecoveryAction.RECONNECT
        elif error.category in [ErrorCategory.TIMEOUT_ERROR, ErrorCategory.LOCK_ERROR]:
            return RecoveryAction.RETRY
        elif error.category == ErrorCategory.TRANSACTION_ERROR:
            return RecoveryAction.ROLLBACK
        elif error.category in [ErrorCategory.CORRUPTION_ERROR, ErrorCategory.DISK_ERROR]:
            return RecoveryAction.MANUAL_INTERVENTION
        elif error.category == ErrorCategory.CONSTRAINT_ERROR:
            return RecoveryAction.IGNORE
        else:
            return RecoveryAction.RETRY
    
    def _generate_error_id(self) -> str:
        """Generate unique error ID"""
        timestamp = datetime.now().isoformat()
        content = f"error_{timestamp}_{random.randint(1000, 9999)}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _store_error(self, error: DatabaseError):
        """Store error in database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO error_log 
                    (error_id, category, severity, message, timestamp, context, 
                     stack_trace, recovery_action, retry_count, resolved)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    error.error_id,
                    error.category.value,
                    error.severity.value,
                    error.message,
                    error.timestamp.isoformat(),
                    json.dumps(error.context),
                    error.stack_trace,
                    error.recovery_action.value if error.recovery_action else None,
                    error.retry_count,
                    error.resolved
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to store error: {e}")
    
    def _update_statistics(self, error: DatabaseError):
        """Update error statistics"""
        try:
            self.error_stats["total_errors"] += 1
            
            # Update category stats
            category_key = error.category.value
            if category_key not in self.error_stats["errors_by_category"]:
                self.error_stats["errors_by_category"][category_key] = 0
            self.error_stats["errors_by_category"][category_key] += 1
            
            # Update severity stats
            severity_key = error.severity.value
            if severity_key not in self.error_stats["errors_by_severity"]:
                self.error_stats["errors_by_severity"][severity_key] = 0
            self.error_stats["errors_by_severity"][severity_key] += 1
            
        except Exception as e:
            logger.error(f"Failed to update statistics: {e}")
    
    # Error handler methods
    def _handle_connection_error(self, error: DatabaseError):
        """Handle connection errors"""
        logger.warning(f"Handling connection error: {error.error_id}")
        # Connection errors are typically handled by retry mechanism
        pass
    
    def _handle_query_error(self, error: DatabaseError):
        """Handle query errors"""
        logger.warning(f"Handling query error: {error.error_id}")
        # Log query for analysis
        if "query" in error.context:
            logger.error(f"Problematic query: {error.context['query']}")
    
    def _handle_transaction_error(self, error: DatabaseError):
        """Handle transaction errors"""
        logger.warning(f"Handling transaction error: {error.error_id}")
        # Transaction errors usually require rollback
        pass
    
    def _handle_constraint_error(self, error: DatabaseError):
        """Handle constraint errors"""
        logger.info(f"Handling constraint error: {error.error_id}")
        # Constraint errors are usually application logic issues
        pass
    
    def _handle_timeout_error(self, error: DatabaseError):
        """Handle timeout errors"""
        logger.warning(f"Handling timeout error: {error.error_id}")
        # Timeout errors can be retried
        pass
    
    def _handle_lock_error(self, error: DatabaseError):
        """Handle lock errors"""
        logger.warning(f"Handling lock error: {error.error_id}")
        # Lock errors should be retried with backoff
        pass
    
    def _handle_disk_error(self, error: DatabaseError):
        """Handle disk errors"""
        logger.critical(f"Handling disk error: {error.error_id}")
        # Disk errors require immediate attention
        pass
    
    def _handle_corruption_error(self, error: DatabaseError):
        """Handle corruption errors"""
        logger.critical(f"Handling corruption error: {error.error_id}")
        # Corruption errors require manual intervention
        pass
    
    def _handle_permission_error(self, error: DatabaseError):
        """Handle permission errors"""
        logger.error(f"Handling permission error: {error.error_id}")
        # Permission errors require configuration changes
        pass
    
    def _handle_unknown_error(self, error: DatabaseError):
        """Handle unknown errors"""
        logger.error(f"Handling unknown error: {error.error_id}")
        # Unknown errors need investigation
        pass
    
    def with_retry(self, operation_name: str = "database_operation", 
                   custom_policy: RetryPolicy = None):
        """Decorator for operations with retry logic"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                policy = custom_policy or self.retry_policies.get(ErrorCategory.CONNECTION_ERROR, RetryPolicy())
                attempt = 0
                last_error = None
                
                while attempt < policy.max_attempts:
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        attempt += 1
                        last_error = e
                        
                        # Handle the error
                        error = self.handle_error(e, {"operation": operation_name, "attempt": attempt})
                        
                        # Check if we should retry
                        if attempt >= policy.max_attempts or error.category not in policy.retry_on_categories:
                            break
                        
                        # Calculate delay
                        delay = self._calculate_retry_delay(policy, attempt)
                        logger.info(f"Retrying {operation_name} in {delay:.2f}s (attempt {attempt}/{policy.max_attempts})")
                        time.sleep(delay)
                
                # All retries exhausted
                if last_error:
                    raise last_error
            return wrapper
        return decorator
    
    def _calculate_retry_delay(self, policy: RetryPolicy, attempt: int) -> float:
        """Calculate retry delay with exponential backoff and jitter"""
        delay = policy.base_delay * (policy.exponential_base ** (attempt - 1))
        delay = min(delay, policy.max_delay)
        
        if policy.jitter:
            # Add random jitter (±25%)
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0.1, delay)  # Minimum 100ms delay
    

    
    def execute_with_error_handling(self, func: Callable, *args, 
                                   operation_name: str = "database_operation",
                                   retry_policy: RetryPolicy = None,
                                   use_circuit_breaker: bool = True,
                                   circuit_breaker_name: str = "default",
                                   **kwargs) -> Any:
        """Execute function with comprehensive error handling"""
        try:
            # Apply retry decorator
            retry_decorator = self.with_retry(operation_name, retry_policy)
            retried_func = retry_decorator(func)
            
            if use_circuit_breaker:
                if circuit_breaker_name not in self.circuit_breakers:
                    self.circuit_breakers[circuit_breaker_name] = CircuitBreaker(CircuitBreakerConfig())
                breaker = self.circuit_breakers[circuit_breaker_name]
                return breaker.call(retried_func, *args, **kwargs)
            else:
                return retried_func(*args, **kwargs)
        except Exception as e:
            # Final error handling
            error = self.handle_error(e, {
                "operation": operation_name,
                "function": func.__name__,
                "args": str(args)[:200],  # Truncate long args
                "kwargs": str(kwargs)[:200]
            })
            raise DatabaseOperationError(f"Operation failed: {error.message}") from e
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Get recent error counts
                cutoff_time = datetime.now() - timedelta(hours=24)
                cursor.execute("""
                    SELECT category, COUNT(*) FROM error_log 
                    WHERE timestamp > ? GROUP BY category
                """, (cutoff_time.isoformat(),))
                
                recent_errors = dict(cursor.fetchall())
                
                # Get resolution rate
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN resolved = 1 THEN 1 ELSE 0 END) as resolved
                    FROM error_log 
                    WHERE timestamp > ?
                """, (cutoff_time.isoformat(),))
                
                result = cursor.fetchone()
                total_errors = result[0] if result else 0
                resolved_errors = result[1] if result else 0
                resolution_rate = (resolved_errors / max(total_errors, 1)) * 100
                
                return {
                    "total_errors_24h": total_errors,
                    "resolved_errors_24h": resolved_errors,
                    "resolution_rate": resolution_rate,
                    "errors_by_category_24h": recent_errors,
                    "circuit_breaker_states": {
                        name: breaker.get_state() 
                        for name, breaker in self.circuit_breakers.items()
                    },
                    "overall_stats": self.error_stats
                }
                
        except Exception as e:
            logger.error(f"Failed to get error statistics: {e}")
            return {}
    
    def get_recent_errors(self, hours: int = 24, category: ErrorCategory = None) -> List[Dict[str, Any]]:
        """Get recent errors"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                if category:
                    cursor.execute("""
                        SELECT error_id, category, severity, message, timestamp, 
                               recovery_action, retry_count, resolved
                        FROM error_log 
                        WHERE timestamp > ? AND category = ?
                        ORDER BY timestamp DESC LIMIT 100
                    """, (cutoff_time.isoformat(), category.value))
                else:
                    cursor.execute("""
                        SELECT error_id, category, severity, message, timestamp, 
                               recovery_action, retry_count, resolved
                        FROM error_log 
                        WHERE timestamp > ?
                        ORDER BY timestamp DESC LIMIT 100
                    """, (cutoff_time.isoformat(),))
                
                errors = []
                for row in cursor.fetchall():
                    errors.append({
                        "error_id": row[0],
                        "category": row[1],
                        "severity": row[2],
                        "message": row[3],
                        "timestamp": row[4],
                        "recovery_action": row[5],
                        "retry_count": row[6],
                        "resolved": bool(row[7])
                    })
                
                return errors
                
        except Exception as e:
            logger.error(f"Failed to get recent errors: {e}")
            return []
    
    def mark_error_resolved(self, error_id: str) -> bool:
        """Mark error as resolved"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE error_log SET resolved = 1 WHERE error_id = ?
                """, (error_id,))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"Marked error {error_id} as resolved")
                    return True
                else:
                    logger.warning(f"Error {error_id} not found")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to mark error as resolved: {e}")
            return False
    
    def cleanup_old_errors(self, days: int = 30):
        """Clean up old error records"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Delete old resolved errors
                cursor.execute("""
                    DELETE FROM error_log 
                    WHERE timestamp < ? AND resolved = 1
                """, (cutoff_time.isoformat(),))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Cleaned up {deleted_count} old error records")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old errors: {e}")
    
    def reset_circuit_breaker(self, breaker_name: str) -> bool:
        """Reset circuit breaker to closed state"""
        try:
            if breaker_name in self.circuit_breakers:
                breaker = self.circuit_breakers[breaker_name]
                with breaker.lock:
                    breaker.state = CircuitState.CLOSED
                    breaker.failure_count = 0
                    breaker.success_count = 0
                    breaker.last_failure_time = None
                
                logger.info(f"Reset circuit breaker: {breaker_name}")
                return True
            else:
                logger.warning(f"Circuit breaker {breaker_name} not found")
                return False
                
        except Exception as e:
            logger.error(f"Failed to reset circuit breaker: {e}")
            return False

# Custom exceptions
class DatabaseOperationError(Exception):
    """Database operation error"""
    pass

class CircuitBreakerOpenError(Exception):
    """Circuit breaker is open"""
    pass

# Example usage and testing
if __name__ == "__main__":
    # Initialize error handler
    error_handler = DatabaseErrorHandler()
    
    try:
        # Test error handling
        def failing_operation():
            raise sqlite3.OperationalError("database is locked")
        
        # Execute with error handling
        try:
            error_handler.execute_with_error_handling(
                failing_operation,
                operation_name="test_operation"
            )
        except DatabaseOperationError as e:
            print(f"Operation failed: {e}")
        
        # Get statistics
        stats = error_handler.get_error_statistics()
        print(f"Error statistics: {stats}")
        
        # Get recent errors
        recent_errors = error_handler.get_recent_errors(hours=1)
        print(f"Recent errors: {len(recent_errors)}")
        
    except Exception as e:
        print(f"Error: {e}")