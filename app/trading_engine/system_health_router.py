"""
FastAPI Router for Trading Engine System Health Monitoring
Provides REST API endpoints for system health monitoring and management
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from .system_health_monitor import (
    system_health_monitor, HealthStatus, ComponentType,
    DatabaseHealthChecker, APIServerHealthChecker, ExternalAPIHealthChecker
)

router = APIRouter(prefix="/api/trading-engine/health", tags=["system-health"])

# Pydantic models for API
class HealthMetricResponse(BaseModel):
    name: str
    value: float
    unit: str
    status: str
    threshold_warning: float
    threshold_critical: float
    timestamp: str
    details: Dict[str, Any] = {}

class ComponentHealthResponse(BaseModel):
    component_id: str
    component_type: str
    status: str
    metrics: List[HealthMetricResponse]
    last_check: str
    uptime_seconds: float
    error_count: int = 0
    last_error: str = ""
    recovery_attempts: int = 0

class SystemHealthResponse(BaseModel):
    overall_status: str
    components: List[ComponentHealthResponse]
    timestamp: str
    total_components: int
    healthy_components: int
    warning_components: int
    critical_components: int
    down_components: int

class HealthStatisticsResponse(BaseModel):
    overall_status: str
    total_components: int
    healthy_components: int
    warning_components: int
    critical_components: int
    down_components: int
    uptime_percentage_24h: float
    recent_critical_events: int
    monitoring_active: bool
    last_check: str

class SystemEventResponse(BaseModel):
    timestamp: str
    event_type: str
    component_id: Optional[str]
    severity: str
    message: str
    details: Optional[Dict[str, Any]]

class AddHealthCheckerRequest(BaseModel):
    checker_type: str = Field(..., description="Type of health checker")
    component_id: str = Field(..., description="Component ID")
    config: Dict[str, Any] = Field(..., description="Checker configuration")

class MonitoringConfigRequest(BaseModel):
    check_interval: int = Field(30, description="Check interval in seconds")
    enable_monitoring: bool = Field(True, description="Enable/disable monitoring")

@router.get("/status")
async def get_system_health():
    """Get current system health status"""
    try:
        health = await system_health_monitor.check_all_components()
        
        return {
            "success": True,
            "health": health.to_dict()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system health: {str(e)}")

@router.get("/current")
async def get_current_health():
    """Get current cached system health"""
    try:
        health = system_health_monitor.get_current_health()
        
        if not health:
            # If no cached health, perform a check
            health = await system_health_monitor.check_all_components()
        
        return {
            "success": True,
            "health": health.to_dict()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get current health: {str(e)}")

@router.get("/statistics")
async def get_health_statistics():
    """Get system health statistics"""
    try:
        stats = system_health_monitor.get_health_statistics()
        
        return {
            "success": True,
            "statistics": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get health statistics: {str(e)}")

@router.get("/history")
async def get_health_history(
    hours: int = Query(24, description="Hours of history to retrieve"),
    component_id: Optional[str] = Query(None, description="Filter by component ID")
):
    """Get system health history"""
    try:
        if component_id:
            # Get specific component metrics
            metrics = system_health_monitor.get_component_metrics(component_id, hours)
            return {
                "success": True,
                "component_id": component_id,
                "metrics": metrics
            }
        else:
            # Get overall system health history
            history = system_health_monitor.get_health_history(hours)
            return {
                "success": True,
                "history": [h.to_dict() for h in history],
                "total_records": len(history)
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get health history: {str(e)}")

@router.get("/events")
async def get_system_events(
    hours: int = Query(24, description="Hours of events to retrieve"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    component_id: Optional[str] = Query(None, description="Filter by component ID")
):
    """Get system events"""
    try:
        events = system_health_monitor.get_system_events(hours, severity)
        
        # Filter by component_id if specified
        if component_id:
            events = [e for e in events if e.get('component_id') == component_id]
        
        return {
            "success": True,
            "events": events,
            "total_events": len(events)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system events: {str(e)}")

@router.get("/components")
async def get_components():
    """Get list of monitored components"""
    try:
        components = []
        for component_id, checker in system_health_monitor.health_checkers.items():
            components.append({
                "component_id": component_id,
                "component_type": checker.component_type.value,
                "uptime_seconds": (datetime.now() - checker.start_time).total_seconds(),
                "error_count": checker.error_count,
                "last_error": checker.last_error
            })
        
        return {
            "success": True,
            "components": components,
            "total_components": len(components)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get components: {str(e)}")

@router.get("/components/{component_id}")
async def get_component_health(component_id: str):
    """Get health status of specific component"""
    try:
        if component_id not in system_health_monitor.health_checkers:
            raise HTTPException(status_code=404, detail="Component not found")
        
        checker = system_health_monitor.health_checkers[component_id]
        health = await checker.check_health()
        
        return {
            "success": True,
            "component": health.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get component health: {str(e)}")

@router.get("/components/{component_id}/metrics")
async def get_component_metrics(
    component_id: str,
    hours: int = Query(24, description="Hours of metrics to retrieve")
):
    """Get metrics for specific component"""
    try:
        if component_id not in system_health_monitor.health_checkers:
            raise HTTPException(status_code=404, detail="Component not found")
        
        metrics = system_health_monitor.get_component_metrics(component_id, hours)
        
        return {
            "success": True,
            "component_id": component_id,
            "metrics": metrics,
            "total_records": len(metrics)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get component metrics: {str(e)}")

@router.post("/checkers")
async def add_health_checker(request: AddHealthCheckerRequest):
    """Add new health checker"""
    try:
        checker_type = request.checker_type.lower()
        
        if checker_type == "database":
            db_path = request.config.get("db_path", "trading_engine.db")
            checker = DatabaseHealthChecker(db_path)
            
        elif checker_type == "api_server":
            base_url = request.config.get("base_url")
            endpoints = request.config.get("endpoints", ["/health"])
            if not base_url:
                raise HTTPException(status_code=400, detail="base_url is required for API server checker")
            checker = APIServerHealthChecker(base_url, endpoints)
            
        elif checker_type == "external_api":
            api_name = request.config.get("api_name")
            api_url = request.config.get("api_url")
            api_key = request.config.get("api_key")
            if not api_name or not api_url:
                raise HTTPException(status_code=400, detail="api_name and api_url are required for external API checker")
            checker = ExternalAPIHealthChecker(api_name, api_url, api_key)
            
        else:
            raise HTTPException(status_code=400, detail=f"Unknown checker type: {checker_type}")
        
        # Override component_id if provided
        if request.component_id:
            checker.component_id = request.component_id
        
        system_health_monitor.add_health_checker(checker)
        
        return {
            "success": True,
            "message": f"Health checker added for {checker.component_id}",
            "component_id": checker.component_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add health checker: {str(e)}")

@router.delete("/checkers/{component_id}")
async def remove_health_checker(component_id: str):
    """Remove health checker"""
    try:
        if component_id not in system_health_monitor.health_checkers:
            raise HTTPException(status_code=404, detail="Component not found")
        
        system_health_monitor.remove_health_checker(component_id)
        
        return {
            "success": True,
            "message": f"Health checker removed for {component_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove health checker: {str(e)}")

@router.post("/monitoring/start")
async def start_monitoring(background_tasks: BackgroundTasks):
    """Start continuous health monitoring"""
    try:
        if system_health_monitor.monitoring_active:
            return {
                "success": True,
                "message": "Health monitoring is already active"
            }
        
        background_tasks.add_task(system_health_monitor.start_monitoring)
        
        return {
            "success": True,
            "message": "Health monitoring started"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start monitoring: {str(e)}")

@router.post("/monitoring/stop")
async def stop_monitoring():
    """Stop continuous health monitoring"""
    try:
        await system_health_monitor.stop_monitoring()
        
        return {
            "success": True,
            "message": "Health monitoring stopped"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop monitoring: {str(e)}")

@router.get("/monitoring/status")
async def get_monitoring_status():
    """Get monitoring status"""
    try:
        return {
            "success": True,
            "monitoring_active": system_health_monitor.monitoring_active,
            "check_interval": system_health_monitor.check_interval,
            "total_checkers": len(system_health_monitor.health_checkers),
            "history_size": len(system_health_monitor.health_history)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get monitoring status: {str(e)}")

@router.put("/monitoring/config")
async def update_monitoring_config(request: MonitoringConfigRequest):
    """Update monitoring configuration"""
    try:
        # Update check interval
        system_health_monitor.check_interval = request.check_interval
        
        # Enable/disable monitoring
        if request.enable_monitoring and not system_health_monitor.monitoring_active:
            await system_health_monitor.start_monitoring()
        elif not request.enable_monitoring and system_health_monitor.monitoring_active:
            await system_health_monitor.stop_monitoring()
        
        return {
            "success": True,
            "message": "Monitoring configuration updated",
            "config": {
                "check_interval": system_health_monitor.check_interval,
                "monitoring_active": system_health_monitor.monitoring_active
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update monitoring config: {str(e)}")

@router.post("/check")
async def trigger_health_check():
    """Trigger immediate health check"""
    try:
        health = await system_health_monitor.check_all_components()
        
        return {
            "success": True,
            "message": "Health check completed",
            "health": health.to_dict()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger health check: {str(e)}")

@router.get("/dashboard")
async def get_health_dashboard():
    """Get comprehensive health dashboard data"""
    try:
        # Get current health
        current_health = system_health_monitor.get_current_health()
        if not current_health:
            current_health = await system_health_monitor.check_all_components()
        
        # Get statistics
        stats = system_health_monitor.get_health_statistics()
        
        # Get recent events
        recent_events = system_health_monitor.get_system_events(1)  # Last hour
        
        # Get component summary
        component_summary = []
        for component in current_health.components:
            summary = {
                "component_id": component.component_id,
                "component_type": component.component_type.value,
                "status": component.status.value,
                "uptime_seconds": component.uptime_seconds,
                "error_count": component.error_count,
                "key_metrics": []
            }
            
            # Add key metrics
            for metric in component.metrics[:3]:  # Top 3 metrics
                summary["key_metrics"].append({
                    "name": metric.name,
                    "value": metric.value,
                    "unit": metric.unit,
                    "status": metric.status.value
                })
            
            component_summary.append(summary)
        
        return {
            "success": True,
            "dashboard": {
                "overall_status": current_health.overall_status.value,
                "statistics": stats,
                "components": component_summary,
                "recent_events": recent_events[:10],  # Last 10 events
                "monitoring_active": system_health_monitor.monitoring_active,
                "last_update": current_health.timestamp.isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get health dashboard: {str(e)}")

@router.get("/alerts")
async def get_health_alerts():
    """Get health-related alerts"""
    try:
        # Get critical and warning events from last 24 hours
        events = system_health_monitor.get_system_events(24)
        alerts = [e for e in events if e['severity'] in ['CRITICAL', 'WARNING']]
        
        return {
            "success": True,
            "alerts": alerts,
            "total_alerts": len(alerts)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get health alerts: {str(e)}")

@router.get("/metrics/summary")
async def get_metrics_summary():
    """Get summary of key system metrics"""
    try:
        current_health = system_health_monitor.get_current_health()
        if not current_health:
            current_health = await system_health_monitor.check_all_components()
        
        # Aggregate key metrics across all components
        cpu_usage = []
        memory_usage = []
        response_times = []
        error_rates = []
        
        for component in current_health.components:
            for metric in component.metrics:
                if "cpu" in metric.name.lower():
                    cpu_usage.append(metric.value)
                elif "memory" in metric.name.lower():
                    memory_usage.append(metric.value)
                elif "response_time" in metric.name.lower():
                    response_times.append(metric.value)
                elif "error" in metric.name.lower():
                    error_rates.append(metric.value)
        
        summary = {
            "cpu_usage": {
                "avg": sum(cpu_usage) / len(cpu_usage) if cpu_usage else 0,
                "max": max(cpu_usage) if cpu_usage else 0,
                "count": len(cpu_usage)
            },
            "memory_usage": {
                "avg": sum(memory_usage) / len(memory_usage) if memory_usage else 0,
                "max": max(memory_usage) if memory_usage else 0,
                "count": len(memory_usage)
            },
            "response_times": {
                "avg": sum(response_times) / len(response_times) if response_times else 0,
                "max": max(response_times) if response_times else 0,
                "count": len(response_times)
            },
            "error_rates": {
                "avg": sum(error_rates) / len(error_rates) if error_rates else 0,
                "max": max(error_rates) if error_rates else 0,
                "count": len(error_rates)
            }
        }
        
        return {
            "success": True,
            "metrics_summary": summary,
            "timestamp": current_health.timestamp.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics summary: {str(e)}")

@router.get("/health")
async def health_check():
    """Health check endpoint for the health monitoring system itself"""
    try:
        return {
            "status": "healthy",
            "service": "system_health_monitor",
            "timestamp": datetime.now().isoformat(),
            "monitoring_active": system_health_monitor.monitoring_active,
            "total_components": len(system_health_monitor.health_checkers),
            "version": "1.0.0"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@router.get("/test")
async def test_health_monitoring():
    """Test health monitoring system"""
    try:
        # Perform a comprehensive test
        test_results = {
            "database_test": False,
            "api_server_test": False,
            "system_resources_test": False,
            "monitoring_test": False
        }
        
        # Test health check
        try:
            health = await system_health_monitor.check_all_components()
            test_results["monitoring_test"] = True
            
            # Check individual components
            for component in health.components:
                if component.component_type == ComponentType.DATABASE:
                    test_results["database_test"] = component.status != HealthStatus.DOWN
                elif component.component_type == ComponentType.API_SERVER:
                    test_results["api_server_test"] = component.status != HealthStatus.DOWN
                elif component.component_type == ComponentType.SYSTEM_RESOURCES:
                    test_results["system_resources_test"] = component.status != HealthStatus.DOWN
            
        except Exception as e:
            logger.error(f"Health monitoring test failed: {e}")
        
        success_count = sum(test_results.values())
        total_tests = len(test_results)
        
        return {
            "success": success_count > 0,
            "test_results": test_results,
            "summary": f"{success_count}/{total_tests} tests passed",
            "overall_health": "healthy" if success_count == total_tests else "degraded"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")