"""
Monitoring Router
FastAPI endpoints for system monitoring and error tracking
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional, Dict, Any
from .error_handler import ErrorHandler, ErrorCategory, ErrorSeverity
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai/monitoring", tags=["System Monitoring"])

# Initialize error handler
error_handler = ErrorHandler()

def get_user_id_from_headers(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> str:
    """Extract user ID from headers"""
    if x_user_id:
        return x_user_id
    return "default_user"

# Request Models
class ErrorLogRequest(BaseModel):
    error_category: ErrorCategory
    error_message: str
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    context: Optional[Dict[str, Any]] = None

class ErrorResolutionRequest(BaseModel):
    error_id: str
    resolution_notes: Optional[str] = None

# Error Logging Endpoints

@router.post("/errors/log")
async def log_error(
    request: ErrorLogRequest,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Log an error manually"""
    try:
        error_id = await error_handler.log_error(
            user_id=user_id,
            error_category=request.error_category,
            error_message=request.error_message,
            severity=request.severity,
            context=request.context
        )
        
        return {
            "status": "success",
            "error_id": error_id,
            "message": "Error logged successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to log error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to log error: {str(e)}"
        )

@router.post("/errors/{error_id}/resolve")
async def resolve_error(
    error_id: str,
    request: ErrorResolutionRequest,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Mark an error as resolved"""
    try:
        success = await error_handler.resolve_error(
            error_id,
            request.resolution_notes
        )
        
        if success:
            return {
                "status": "success",
                "error_id": error_id,
                "message": "Error marked as resolved"
            }
        else:
            raise HTTPException(
                status_code=404,
                detail="Error not found or could not be resolved"
            )
        
    except Exception as e:
        logger.error(f"Failed to resolve error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resolve error: {str(e)}"
        )

# Monitoring Endpoints

@router.get("/errors/summary")
async def get_error_summary(
    hours: int = 24,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get error summary for monitoring"""
    try:
        summary = await error_handler.get_error_summary(user_id, hours)
        return summary
        
    except Exception as e:
        logger.error(f"Failed to get error summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get error summary: {str(e)}"
        )

@router.get("/errors/trends")
async def get_error_trends(
    days: int = 7,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get error trends over time"""
    try:
        trends = await error_handler.get_error_trends(user_id, days)
        return trends
        
    except Exception as e:
        logger.error(f"Failed to get error trends: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get error trends: {str(e)}"
        )

@router.get("/health/system")
async def get_system_health():
    """Get overall system health status"""
    try:
        health = await error_handler.get_system_health()
        return health
        
    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get system health: {str(e)}"
        )

@router.get("/health/user")
async def get_user_health(
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get user-specific health status"""
    try:
        summary = await error_handler.get_error_summary(user_id, hours=1)
        
        return {
            "user_id": user_id,
            "health_status": summary.get("health_status", "unknown"),
            "recent_errors": summary.get("total_errors", 0),
            "active_alerts": len(summary.get("active_alerts", [])),
            "timestamp": summary.get("generated_at")
        }
        
    except Exception as e:
        logger.error(f"Failed to get user health: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get user health: {str(e)}"
        )

# Performance Monitoring

@router.get("/performance/database")
async def get_database_performance():
    """Get database performance metrics"""
    try:
        from ..database.service import get_db_connection
        import time
        
        # Test database connection speed
        start_time = time.time()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Simple query to test responsiveness
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        
        # Test write performance
        write_start = time.time()
        cursor.execute("CREATE TEMP TABLE test_perf (id INTEGER)")
        cursor.execute("INSERT INTO test_perf VALUES (1)")
        cursor.execute("DROP TABLE test_perf")
        write_time = (time.time() - write_start) * 1000
        
        conn.close()
        connection_time = (time.time() - start_time) * 1000
        
        return {
            "status": "healthy",
            "connection_time_ms": round(connection_time, 2),
            "write_performance_ms": round(write_time, 2),
            "table_count": table_count,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Database performance check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }

@router.get("/performance/ai-providers")
async def get_ai_provider_performance(
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get AI provider performance metrics"""
    try:
        from ..database.service import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get recent usage statistics
        cursor.execute("""
            SELECT 
                provider,
                COUNT(*) as requests,
                AVG(response_time_ms) as avg_response_time,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate,
                AVG(cost_cents) as avg_cost
            FROM ai_usage_tracking
            WHERE user_id = ?
            AND created_at >= datetime('now', '-1 hour')
            GROUP BY provider
        """, (user_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        provider_metrics = []
        for result in results:
            provider_metrics.append({
                "provider": result[0],
                "requests": result[1],
                "avg_response_time_ms": round(result[2] or 0, 2),
                "success_rate": round(result[3] or 0, 2),
                "avg_cost_cents": round(result[4] or 0, 2)
            })
        
        return {
            "user_id": user_id,
            "period": "last_hour",
            "provider_metrics": provider_metrics,
            "timestamp": "2025-07-21T10:30:00Z"
        }
        
    except Exception as e:
        logger.error(f"AI provider performance check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get provider performance: {str(e)}"
        )

# Alert Management

@router.get("/alerts/active")
async def get_active_alerts(
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get active alerts for user"""
    try:
        from ..database.service import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id,
                error_category,
                severity,
                error_count,
                threshold_exceeded,
                created_at
            FROM ai_error_alerts
            WHERE user_id = ? AND resolved = FALSE
            ORDER BY created_at DESC
        """, (user_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        alerts = []
        for result in results:
            alerts.append({
                "id": result[0],
                "category": result[1],
                "severity": result[2],
                "error_count": result[3],
                "threshold_exceeded": result[4],
                "created_at": result[5]
            })
        
        return {
            "user_id": user_id,
            "active_alerts": alerts,
            "alert_count": len(alerts)
        }
        
    except Exception as e:
        logger.error(f"Failed to get active alerts: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get active alerts: {str(e)}"
        )

# Test Endpoints

@router.post("/test/error")
async def create_test_error(
    user_id: str = Depends(get_user_id_from_headers)
):
    """Create a test error for monitoring testing"""
    try:
        import random
        
        categories = list(ErrorCategory)
        severities = list(ErrorSeverity)
        
        test_category = random.choice(categories)
        test_severity = random.choice(severities)
        
        error_id = await error_handler.log_error(
            user_id=user_id,
            error_category=test_category,
            error_message=f"Test error - {test_category.value}",
            severity=test_severity,
            context={"test": True, "timestamp": "2025-07-21T10:30:00Z"}
        )
        
        return {
            "message": "Test error created",
            "error_id": error_id,
            "category": test_category,
            "severity": test_severity
        }
        
    except Exception as e:
        logger.error(f"Failed to create test error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create test error: {str(e)}"
        )

# Health check
@router.get("/health")
async def monitoring_health_check():
    """Health check for monitoring system"""
    try:
        return {
            "status": "healthy",
            "components": {
                "error_handler": "operational",
                "database_logging": "active",
                "alert_system": "active",
                "performance_monitoring": "active"
            },
            "timestamp": "2025-07-21T10:30:00Z"
        }
        
    except Exception as e:
        logger.error(f"Monitoring health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }