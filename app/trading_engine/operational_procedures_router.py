"""
Operational Procedures Router

FastAPI router for operational procedures, system monitoring,
and automated recovery management.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from .operational_procedures import operational_procedures, SystemStatus, AlertLevel

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

@router.get("/status")
async def get_operational_status():
    """Get current operational status"""
    try:
        status = operational_procedures.get_system_status()
        return {
            "status": "success",
            "data": status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting operational status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/runbook")
async def get_operational_runbook():
    """Get operational runbook and procedures"""
    try:
        runbook = operational_procedures.get_operational_runbook()
        return {
            "status": "success",
            "data": runbook,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting operational runbook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics")
async def get_system_metrics():
    """Get recent system metrics"""
    try:
        recent_metrics = operational_procedures.metrics_history[-10:] if operational_procedures.metrics_history else []
        
        metrics_data = []
        for metric in recent_metrics:
            metrics_data.append({
                "timestamp": metric.timestamp.isoformat(),
                "cpu_usage": metric.cpu_usage,
                "memory_usage": metric.memory_usage,
                "disk_usage": metric.disk_usage,
                "network_io": metric.network_io,
                "active_connections": metric.active_connections,
                "database_connections": metric.database_connections,
                "queue_depth": metric.queue_depth,
                "response_time_ms": metric.response_time_ms,
                "error_rate": metric.error_rate,
                "throughput_per_second": metric.throughput_per_second
            })
        
        return {
            "status": "success",
            "data": {
                "metrics": metrics_data,
                "count": len(metrics_data),
                "monitoring_active": operational_procedures.monitoring_active
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts")
async def get_active_alerts():
    """Get active system alerts"""
    try:
        active_alerts = [a for a in operational_procedures.active_alerts if not a.resolved]
        
        alerts_data = []
        for alert in active_alerts:
            alerts_data.append({
                "id": alert.id,
                "timestamp": alert.timestamp.isoformat(),
                "level": alert.level.value,
                "component": alert.component,
                "message": alert.message,
                "details": alert.details,
                "resolved": alert.resolved
            })
        
        # Sort by timestamp (newest first)
        alerts_data.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return {
            "status": "success",
            "data": {
                "alerts": alerts_data,
                "count": len(alerts_data),
                "critical_count": len([a for a in alerts_data if a["level"] == "critical"]),
                "warning_count": len([a for a in alerts_data if a["level"] == "warning"])
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting active alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts/history")
async def get_alerts_history():
    """Get alerts history"""
    try:
        all_alerts = operational_procedures.active_alerts
        
        alerts_data = []
        for alert in all_alerts:
            alerts_data.append({
                "id": alert.id,
                "timestamp": alert.timestamp.isoformat(),
                "level": alert.level.value,
                "component": alert.component,
                "message": alert.message,
                "details": alert.details,
                "resolved": alert.resolved,
                "resolution_time": alert.resolution_time.isoformat() if alert.resolution_time else None
            })
        
        # Sort by timestamp (newest first)
        alerts_data.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return {
            "status": "success",
            "data": {
                "alerts": alerts_data,
                "count": len(alerts_data),
                "resolved_count": len([a for a in alerts_data if a["resolved"]]),
                "active_count": len([a for a in alerts_data if not a["resolved"]])
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting alerts history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/monitoring/start")
async def start_monitoring(background_tasks: BackgroundTasks):
    """Start system monitoring"""
    try:
        if operational_procedures.monitoring_active:
            return {
                "status": "info",
                "message": "Monitoring is already active",
                "timestamp": datetime.now().isoformat()
            }
        
        # Start monitoring in background
        background_tasks.add_task(operational_procedures.start_monitoring)
        
        return {
            "status": "success",
            "message": "System monitoring started",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error starting monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/monitoring/stop")
async def stop_monitoring():
    """Stop system monitoring"""
    try:
        operational_procedures.stop_monitoring()
        
        return {
            "status": "success",
            "message": "System monitoring stopped",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error stopping monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recovery/actions")
async def get_recovery_actions():
    """Get available recovery actions"""
    try:
        actions_data = {}
        for action_name, action in operational_procedures.recovery_actions.items():
            actions_data[action_name] = {
                "name": action.name,
                "description": action.description,
                "conditions": action.conditions,
                "timeout_seconds": action.timeout_seconds,
                "retry_count": action.retry_count,
                "escalation_level": action.escalation_level.value
            }
        
        return {
            "status": "success",
            "data": {
                "recovery_actions": actions_data,
                "count": len(actions_data),
                "recovery_in_progress": operational_procedures.recovery_in_progress
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting recovery actions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/recovery/execute/{action_name}")
async def execute_recovery_action(action_name: str, background_tasks: BackgroundTasks):
    """Execute a specific recovery action"""
    try:
        if action_name not in operational_procedures.recovery_actions:
            raise HTTPException(status_code=404, detail=f"Recovery action '{action_name}' not found")
        
        if operational_procedures.recovery_in_progress:
            raise HTTPException(status_code=409, detail="Another recovery action is already in progress")
        
        action = operational_procedures.recovery_actions[action_name]
        
        # Execute recovery action in background
        background_tasks.add_task(operational_procedures._execute_recovery_action, action)
        
        return {
            "status": "success",
            "message": f"Recovery action '{action.name}' started",
            "action": {
                "name": action.name,
                "description": action.description,
                "timeout_seconds": action.timeout_seconds
            },
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing recovery action: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """Resolve a specific alert"""
    try:
        # Find the alert
        alert = None
        for a in operational_procedures.active_alerts:
            if a.id == alert_id:
                alert = a
                break
        
        if not alert:
            raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")
        
        if alert.resolved:
            return {
                "status": "info",
                "message": f"Alert '{alert_id}' is already resolved",
                "timestamp": datetime.now().isoformat()
            }
        
        # Resolve the alert
        alert.resolved = True
        alert.resolution_time = datetime.now()
        
        logger.info(f"Alert {alert_id} resolved manually")
        
        return {
            "status": "success",
            "message": f"Alert '{alert_id}' resolved",
            "alert": {
                "id": alert.id,
                "level": alert.level.value,
                "component": alert.component,
                "message": alert.message,
                "resolution_time": alert.resolution_time.isoformat()
            },
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/capacity/planning")
async def get_capacity_planning():
    """Get capacity planning information"""
    try:
        # Get recent metrics for capacity analysis
        recent_metrics = operational_procedures.metrics_history[-100:] if operational_procedures.metrics_history else []
        
        if not recent_metrics:
            return {
                "status": "info",
                "message": "No metrics available for capacity planning",
                "timestamp": datetime.now().isoformat()
            }
        
        # Calculate capacity metrics
        avg_cpu = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
        max_cpu = max(m.cpu_usage for m in recent_metrics)
        avg_memory = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
        max_memory = max(m.memory_usage for m in recent_metrics)
        avg_queue_depth = sum(m.queue_depth for m in recent_metrics) / len(recent_metrics)
        max_queue_depth = max(m.queue_depth for m in recent_metrics)
        avg_throughput = sum(m.throughput_per_second for m in recent_metrics) / len(recent_metrics)
        max_throughput = max(m.throughput_per_second for m in recent_metrics)
        
        # Capacity recommendations
        recommendations = []
        
        if avg_cpu > 60:
            recommendations.append({
                "type": "cpu",
                "priority": "high" if avg_cpu > 80 else "medium",
                "message": f"Average CPU usage is {avg_cpu:.1f}%. Consider scaling CPU resources.",
                "action": "Scale CPU allocation or add more instances"
            })
        
        if avg_memory > 70:
            recommendations.append({
                "type": "memory",
                "priority": "high" if avg_memory > 85 else "medium",
                "message": f"Average memory usage is {avg_memory:.1f}%. Consider scaling memory resources.",
                "action": "Increase memory allocation or optimize memory usage"
            })
        
        if avg_queue_depth > 500:
            recommendations.append({
                "type": "processing",
                "priority": "high" if avg_queue_depth > 1000 else "medium",
                "message": f"Average queue depth is {avg_queue_depth:.0f}. Consider scaling processing capacity.",
                "action": "Add more worker processes or optimize processing speed"
            })
        
        return {
            "status": "success",
            "data": {
                "metrics_analyzed": len(recent_metrics),
                "time_period_hours": len(recent_metrics) * 0.5 / 60,  # 30-second intervals
                "current_capacity": {
                    "cpu": {
                        "average": round(avg_cpu, 1),
                        "peak": round(max_cpu, 1),
                        "utilization_level": "high" if avg_cpu > 70 else "medium" if avg_cpu > 40 else "low"
                    },
                    "memory": {
                        "average": round(avg_memory, 1),
                        "peak": round(max_memory, 1),
                        "utilization_level": "high" if avg_memory > 70 else "medium" if avg_memory > 40 else "low"
                    },
                    "processing": {
                        "average_queue_depth": round(avg_queue_depth, 0),
                        "peak_queue_depth": max_queue_depth,
                        "average_throughput": round(avg_throughput, 1),
                        "peak_throughput": round(max_throughput, 1)
                    }
                },
                "recommendations": recommendations,
                "scaling_thresholds": {
                    "cpu_scale_up": 70,
                    "memory_scale_up": 80,
                    "queue_depth_scale_up": 1000,
                    "auto_scaling_enabled": True
                }
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting capacity planning: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        status = operational_procedures.get_system_status()
        
        return {
            "status": "operational",
            "message": "Operational procedures system is running",
            "system_status": status["status"],
            "monitoring_active": status["monitoring_active"],
            "recovery_in_progress": status["recovery_in_progress"],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "message": f"Operational procedures system error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }