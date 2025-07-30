"""
AI Provider Failover Router
Provides API endpoints for managing AI provider failover and health monitoring
"""
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel
from app.ai_engine.provider_failover import failover_manager, ProviderStatus

logger = logging.getLogger(__name__)
router = APIRouter()

class ProviderStatusUpdate(BaseModel):
    provider: str
    status: str  # "healthy", "degraded", "failed"

class FailoverTestRequest(BaseModel):
    operation_type: str = "test"
    simulate_failure: bool = False
    target_provider: Optional[str] = None

@router.get("/status")
async def get_provider_status(
    x_user_id: str = Header(default="default_user", alias="X-User-ID")
):
    """Get current status of all AI providers"""
    try:
        status = await failover_manager.get_provider_status()
        return {
            "status": "success",
            "data": status,
            "user_id": x_user_id
        }
    except Exception as e:
        logger.error(f"Error getting provider status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/health-check")
async def trigger_health_check(
    background_tasks: BackgroundTasks,
    x_user_id: str = Header(default="default_user", alias="X-User-ID")
):
    """Trigger immediate health check of all providers"""
    try:
        # Run health check in background
        background_tasks.add_task(failover_manager._perform_health_checks)
        
        return {
            "status": "success",
            "message": "Health check triggered",
            "user_id": x_user_id
        }
    except Exception as e:
        logger.error(f"Error triggering health check: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/start-monitoring")
async def start_health_monitoring(
    x_user_id: str = Header(default="default_user", alias="X-User-ID")
):
    """Start continuous health monitoring"""
    try:
        await failover_manager.start_health_monitoring()
        return {
            "status": "success",
            "message": "Health monitoring started",
            "user_id": x_user_id
        }
    except Exception as e:
        logger.error(f"Error starting health monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop-monitoring")
async def stop_health_monitoring(
    x_user_id: str = Header(default="default_user", alias="X-User-ID")
):
    """Stop continuous health monitoring"""
    try:
        await failover_manager.stop_health_monitoring()
        return {
            "status": "success",
            "message": "Health monitoring stopped",
            "user_id": x_user_id
        }
    except Exception as e:
        logger.error(f"Error stopping health monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/force-status")
async def force_provider_status(
    request: ProviderStatusUpdate,
    x_user_id: str = Header(default="default_user", alias="X-User-ID")
):
    """Manually set provider status (for testing/admin purposes)"""
    try:
        # Validate status
        valid_statuses = ["healthy", "degraded", "failed", "unknown"]
        if request.status not in valid_statuses:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid status. Must be one of: {valid_statuses}"
            )
        
        # Convert string to enum
        status_map = {
            "healthy": ProviderStatus.HEALTHY,
            "degraded": ProviderStatus.DEGRADED,
            "failed": ProviderStatus.FAILED,
            "unknown": ProviderStatus.UNKNOWN
        }
        
        await failover_manager.force_provider_status(
            request.provider, 
            status_map[request.status]
        )
        
        return {
            "status": "success",
            "message": f"Provider {request.provider} status set to {request.status}",
            "user_id": x_user_id
        }
    except Exception as e:
        logger.error(f"Error forcing provider status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/best-provider")
async def get_best_provider(
    operation_type: str = "general",
    x_user_id: str = Header(default="default_user", alias="X-User-ID")
):
    """Get the best available AI provider for a specific operation"""
    try:
        best_provider = await failover_manager.get_best_available_provider(
            x_user_id, operation_type
        )
        
        if not best_provider:
            return {
                "status": "error",
                "message": "No available AI providers",
                "user_id": x_user_id
            }
        
        return {
            "status": "success",
            "best_provider": best_provider,
            "operation_type": operation_type,
            "user_id": x_user_id
        }
    except Exception as e:
        logger.error(f"Error getting best provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-failover")
async def test_failover(
    request: FailoverTestRequest,
    x_user_id: str = Header(default="default_user", alias="X-User-ID")
):
    """Test failover functionality with a mock operation"""
    try:
        async def mock_operation(provider: str, user_id: str, *args, **kwargs):
            """Mock operation for testing failover"""
            if request.simulate_failure and provider == request.target_provider:
                raise Exception(f"Simulated failure for provider {provider}")
            
            return {
                "status": "success",
                "provider": provider,
                "operation": request.operation_type,
                "message": f"Mock operation completed successfully with {provider}"
            }
        
        # Execute with failover
        result = await failover_manager.execute_with_failover(
            x_user_id,
            request.operation_type,
            mock_operation
        )
        
        return {
            "status": "success",
            "test_result": result,
            "user_id": x_user_id
        }
        
    except Exception as e:
        logger.error(f"Error testing failover: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/failover-history")
async def get_failover_history(
    limit: int = 20,
    x_user_id: str = Header(default="default_user", alias="X-User-ID")
):
    """Get recent failover history"""
    try:
        status = await failover_manager.get_provider_status()
        history = status.get("failover_history", [])
        
        # Limit results
        limited_history = history[-limit:] if len(history) > limit else history
        
        return {
            "status": "success",
            "failover_history": limited_history,
            "total_events": len(history),
            "user_id": x_user_id
        }
    except Exception as e:
        logger.error(f"Error getting failover history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health-summary")
async def get_health_summary(
    x_user_id: str = Header(default="default_user", alias="X-User-ID")
):
    """Get a summary of provider health status"""
    try:
        status = await failover_manager.get_provider_status()
        providers = status.get("providers", {})
        
        # Calculate summary statistics
        total_providers = len(providers)
        healthy_count = sum(1 for p in providers.values() if p["status"] == "healthy")
        degraded_count = sum(1 for p in providers.values() if p["status"] == "degraded")
        failed_count = sum(1 for p in providers.values() if p["status"] == "failed")
        available_count = sum(1 for p in providers.values() if p["is_available"])
        
        avg_response_time = sum(p["response_time_ms"] for p in providers.values()) / total_providers if total_providers > 0 else 0
        avg_success_rate = sum(p["success_rate"] for p in providers.values()) / total_providers if total_providers > 0 else 0
        
        return {
            "status": "success",
            "summary": {
                "total_providers": total_providers,
                "healthy_providers": healthy_count,
                "degraded_providers": degraded_count,
                "failed_providers": failed_count,
                "available_providers": available_count,
                "average_response_time_ms": round(avg_response_time, 2),
                "average_success_rate": round(avg_success_rate, 3),
                "health_monitoring_active": status.get("health_monitoring_active", False),
                "degraded_mode_enabled": status.get("degraded_mode_enabled", True)
            },
            "providers": providers,
            "user_id": x_user_id
        }
    except Exception as e:
        logger.error(f"Error getting health summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))