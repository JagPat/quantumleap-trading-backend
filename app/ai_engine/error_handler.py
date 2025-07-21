"""
Error Handler and Monitoring System
Comprehensive error handling, logging, and monitoring for AI engine
"""
import json
import logging
import traceback
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from ..database.service import get_db_connection

logger = logging.getLogger(__name__)

class ErrorSeverity(str, Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(str, Enum):
    """Error categories"""
    API_ERROR = "api_error"
    DATABASE_ERROR = "database_error"
    VALIDATION_ERROR = "validation_error"
    PROVIDER_ERROR = "provider_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    AUTHENTICATION_ERROR = "authentication_error"
    TIMEOUT_ERROR = "timeout_error"
    UNKNOWN_ERROR = "unknown_error"

class ErrorHandler:
    """
    Comprehensive error handling and monitoring system
    """
    
    def __init__(self):
        self.error_thresholds = {
            ErrorSeverity.LOW: 10,      # 10 errors per hour
            ErrorSeverity.MEDIUM: 5,    # 5 errors per hour
            ErrorSeverity.HIGH: 3,      # 3 errors per hour
            ErrorSeverity.CRITICAL: 1   # 1 error per hour
        }
        
    async def log_error(
        self,
        user_id: str,
        error_category: ErrorCategory,
        error_message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        stack_trace: Optional[str] = None
    ) -> str:
        """Log error with comprehensive details"""
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Create error log table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_error_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    error_category TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    context TEXT,
                    stack_trace TEXT,
                    resolved BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            cursor.execute("""
                INSERT INTO ai_error_log 
                (user_id, error_category, error_message, severity, context, stack_trace)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                error_category.value,
                error_message,
                severity.value,
                json.dumps(context) if context else None,
                stack_trace
            ))
            
            error_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # Log to application logger based on severity
            log_message = f"Error {error_id}: {error_category.value} - {error_message}"
            if severity == ErrorSeverity.CRITICAL:
                logger.critical(log_message)
            elif severity == ErrorSeverity.HIGH:
                logger.error(log_message)
            elif severity == ErrorSeverity.MEDIUM:
                logger.warning(log_message)
            else:
                logger.info(log_message)
            
            # Check if alert threshold is exceeded
            await self.check_error_threshold(user_id, error_category, severity)
            
            return str(error_id)
            
        except Exception as e:
            # Fallback logging if database fails
            logger.error(f"Failed to log error to database: {e}")
            logger.error(f"Original error: {error_category.value} - {error_message}")
            return "log_failed"
    
    async def check_error_threshold(
        self,
        user_id: str,
        error_category: ErrorCategory,
        severity: ErrorSeverity
    ):
        """Check if error threshold is exceeded and send alerts"""
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Count errors in the last hour
            cursor.execute("""
                SELECT COUNT(*) FROM ai_error_log
                WHERE user_id = ? AND error_category = ? AND severity = ?
                AND created_at >= datetime('now', '-1 hour')
            """, (user_id, error_category.value, severity.value))
            
            error_count = cursor.fetchone()[0]
            threshold = self.error_thresholds.get(severity, 5)
            
            if error_count >= threshold:
                # Create alert
                await self.create_error_alert(user_id, error_category, severity, error_count, threshold)
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to check error threshold: {e}")
    
    async def create_error_alert(
        self,
        user_id: str,
        error_category: ErrorCategory,
        severity: ErrorSeverity,
        error_count: int,
        threshold: int
    ):
        """Create error alert when threshold is exceeded"""
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Create alerts table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_error_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    error_category TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    error_count INTEGER NOT NULL,
                    threshold_exceeded INTEGER NOT NULL,
                    alert_sent BOOLEAN DEFAULT FALSE,
                    resolved BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            cursor.execute("""
                INSERT INTO ai_error_alerts
                (user_id, error_category, severity, error_count, threshold_exceeded)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, error_category.value, severity.value, error_count, threshold))
            
            conn.commit()
            conn.close()
            
            # Log critical alert
            logger.critical(
                f"ERROR THRESHOLD EXCEEDED - User: {user_id}, "
                f"Category: {error_category.value}, Severity: {severity.value}, "
                f"Count: {error_count}, Threshold: {threshold}"
            )
            
            # In production, this would send email/notification
            
        except Exception as e:
            logger.error(f"Failed to create error alert: {e}")
    
    def error_handler_decorator(self, error_category: ErrorCategory, severity: ErrorSeverity = ErrorSeverity.MEDIUM):
        """Decorator for automatic error handling"""
        
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    # Extract user_id from args/kwargs if available
                    user_id = "system"
                    if args and hasattr(args[0], 'user_id'):
                        user_id = args[0].user_id
                    elif 'user_id' in kwargs:
                        user_id = kwargs['user_id']
                    
                    # Log the error
                    error_id = await self.log_error(
                        user_id=user_id,
                        error_category=error_category,
                        error_message=str(e),
                        severity=severity,
                        context={
                            "function": func.__name__,
                            "args": str(args)[:500],  # Limit size
                            "kwargs": str(kwargs)[:500]
                        },
                        stack_trace=traceback.format_exc()
                    )
                    
                    # Re-raise with error ID
                    raise Exception(f"Error {error_id}: {str(e)}")
            
            return wrapper
        return decorator
    
    async def get_error_summary(self, user_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for monitoring"""
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get error counts by category and severity
            cursor.execute("""
                SELECT 
                    error_category,
                    severity,
                    COUNT(*) as error_count,
                    MAX(created_at) as last_occurrence
                FROM ai_error_log
                WHERE user_id = ?
                AND created_at >= datetime('now', ? || ' hours')
                GROUP BY error_category, severity
                ORDER BY error_count DESC
            """, (user_id, f"-{hours}"))
            
            error_stats = cursor.fetchall()
            
            # Get total error count
            cursor.execute("""
                SELECT COUNT(*) FROM ai_error_log
                WHERE user_id = ?
                AND created_at >= datetime('now', ? || ' hours')
            """, (user_id, f"-{hours}"))
            
            total_errors = cursor.fetchone()[0]
            
            # Get active alerts
            cursor.execute("""
                SELECT 
                    error_category,
                    severity,
                    error_count,
                    created_at
                FROM ai_error_alerts
                WHERE user_id = ? AND resolved = FALSE
                ORDER BY created_at DESC
            """, (user_id,))
            
            active_alerts = cursor.fetchall()
            conn.close()
            
            # Format results
            error_breakdown = []
            for stat in error_stats:
                error_breakdown.append({
                    "category": stat[0],
                    "severity": stat[1],
                    "count": stat[2],
                    "last_occurrence": stat[3]
                })
            
            alerts = []
            for alert in active_alerts:
                alerts.append({
                    "category": alert[0],
                    "severity": alert[1],
                    "error_count": alert[2],
                    "created_at": alert[3]
                })
            
            return {
                "user_id": user_id,
                "period_hours": hours,
                "total_errors": total_errors,
                "error_breakdown": error_breakdown,
                "active_alerts": alerts,
                "health_status": self.determine_health_status(total_errors, len(alerts)),
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get error summary: {e}")
            return {"user_id": user_id, "error": str(e)}
    
    def determine_health_status(self, total_errors: int, alert_count: int) -> str:
        """Determine system health status based on errors"""
        
        if alert_count > 0:
            return "critical"
        elif total_errors > 20:
            return "degraded"
        elif total_errors > 10:
            return "warning"
        else:
            return "healthy"
    
    async def get_error_trends(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """Get error trends over time"""
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    DATE(created_at) as error_date,
                    error_category,
                    severity,
                    COUNT(*) as error_count
                FROM ai_error_log
                WHERE user_id = ?
                AND created_at >= datetime('now', ? || ' days')
                GROUP BY DATE(created_at), error_category, severity
                ORDER BY error_date DESC
            """, (user_id, f"-{days}"))
            
            results = cursor.fetchall()
            conn.close()
            
            trends = []
            for result in results:
                trends.append({
                    "date": result[0],
                    "category": result[1],
                    "severity": result[2],
                    "count": result[3]
                })
            
            return {
                "user_id": user_id,
                "period_days": days,
                "trends": trends,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get error trends: {e}")
            return {"user_id": user_id, "error": str(e)}
    
    async def resolve_error(self, error_id: str, resolution_notes: Optional[str] = None) -> bool:
        """Mark error as resolved"""
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE ai_error_log
                SET resolved = TRUE
                WHERE id = ?
            """, (error_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Error {error_id} marked as resolved: {resolution_notes}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resolve error {error_id}: {e}")
            return False
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get error counts by severity in last hour
            cursor.execute("""
                SELECT 
                    severity,
                    COUNT(*) as error_count
                FROM ai_error_log
                WHERE created_at >= datetime('now', '-1 hour')
                GROUP BY severity
            """)
            
            error_counts = dict(cursor.fetchall())
            
            # Get active alerts count
            cursor.execute("""
                SELECT COUNT(*) FROM ai_error_alerts
                WHERE resolved = FALSE
            """)
            
            active_alerts = cursor.fetchone()[0]
            
            # Get total errors in last 24 hours
            cursor.execute("""
                SELECT COUNT(*) FROM ai_error_log
                WHERE created_at >= datetime('now', '-24 hours')
            """)
            
            total_errors_24h = cursor.fetchone()[0]
            conn.close()
            
            # Determine overall health
            critical_errors = error_counts.get("critical", 0)
            high_errors = error_counts.get("high", 0)
            
            if critical_errors > 0 or active_alerts > 5:
                health_status = "critical"
            elif high_errors > 3 or total_errors_24h > 50:
                health_status = "degraded"
            elif total_errors_24h > 20:
                health_status = "warning"
            else:
                health_status = "healthy"
            
            return {
                "health_status": health_status,
                "error_counts_1h": error_counts,
                "active_alerts": active_alerts,
                "total_errors_24h": total_errors_24h,
                "thresholds": self.error_thresholds,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return {
                "health_status": "unknown",
                "error": str(e)
            }

# Global error handler instance
error_handler = ErrorHandler()

# Convenience decorators
def handle_api_errors(severity: ErrorSeverity = ErrorSeverity.MEDIUM):
    return error_handler.error_handler_decorator(ErrorCategory.API_ERROR, severity)

def handle_database_errors(severity: ErrorSeverity = ErrorSeverity.HIGH):
    return error_handler.error_handler_decorator(ErrorCategory.DATABASE_ERROR, severity)

def handle_provider_errors(severity: ErrorSeverity = ErrorSeverity.MEDIUM):
    return error_handler.error_handler_decorator(ErrorCategory.PROVIDER_ERROR, severity)