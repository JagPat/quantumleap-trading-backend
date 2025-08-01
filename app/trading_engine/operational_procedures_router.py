#!/usr/bin/env python3
"""
Operational Procedures API Router
FastAPI router for operational procedures and system management
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, Optional
import logging
from datetime import datetime

from .operational_procedures import get_operational_procedures

# Configure logging
logger = logging.getLogger(__name__)

# Create router
operational_procedures_router = APIRouter()

@operational_procedures_router.get("/health")
async def operational_health():
    """Get operational system health status"""
    try:
        ops = get_operational_procedures()
        health = ops.check_system_health()
        return health
    except Exception as e:
        logger.error(f"Operational health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@operational_procedures_router.get("/status")
async def operational_status():
    """Get comprehensive operational status"""
    try:
        ops = get_operational_procedures()
        status = ops.get_operational_status()
        return status
    except Exception as e:
        logger.error(f"Operational status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@operational_procedures_router.get("/metrics")
async def system_metrics():
    """Get current system metrics"""
    try:
        ops = get_operational_procedures()
        metrics = ops.collect_system_metrics()
        return {
            "cpu_usage": metrics.cpu_usage,
            "memory_usage": metrics.memory_usage,
            "disk_usage": metrics.disk_usage,
            "network_io": metrics.network_io,
            "active_connections": metrics.active_connections,
            "response_time": metrics.response_time,
            "error_rate": metrics.error_rate,
            "timestamp": metrics.timestamp.isoformat()
        }
    except Exception as e:
        logger.error(f"System metrics collection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@operational_procedures_router.get("/capacity-planning")
async def capacity_planning():
    """Get capacity planning report"""
    try:
        ops = get_operational_procedures()
        report = ops.get_capacity_planning_report()
        return report
    except Exception as e:
        logger.error(f"Capacity planning failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@operational_procedures_router.post("/recovery/{issue_type}")
async def trigger_recovery(issue_type: str, background_tasks: BackgroundTasks):
    """Trigger automated recovery procedure"""
    try:
        ops = get_operational_procedures()
        
        # Run recovery in background
        background_tasks.add_task(ops.trigger_automated_recovery, issue_type)
        
        return {
            "message": f"Automated recovery triggered for {issue_type}",
            "timestamp": datetime.now().isoformat(),
            "status": "initiated"
        }
    except Exception as e:
        logger.error(f"Recovery trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@operational_procedures_router.get("/runbooks")
async def list_runbooks():
    """List available operational runbooks"""
    try:
        import os
        runbooks_path = "operational_runbooks"
        
        if not os.path.exists(runbooks_path):
            return {"runbooks": [], "message": "No runbooks directory found"}
        
        runbooks = []
        for filename in os.listdir(runbooks_path):
            if filename.endswith('.json'):
                runbooks.append({
                    "name": filename.replace('.json', ''),
                    "filename": filename,
                    "path": f"{runbooks_path}/{filename}"
                })
        
        return {
            "runbooks": runbooks,
            "count": len(runbooks),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Runbooks listing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@operational_procedures_router.get("/runbooks/{runbook_name}")
async def get_runbook(runbook_name: str):
    """Get specific operational runbook"""
    try:
        import json
        import os
        
        runbook_path = f"operational_runbooks/{runbook_name}.json"
        
        if not os.path.exists(runbook_path):
            raise HTTPException(status_code=404, detail=f"Runbook {runbook_name} not found")
        
        with open(runbook_path, 'r') as f:
            runbook = json.load(f)
        
        return runbook
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Runbook {runbook_name} not found")
    except Exception as e:
        logger.error(f"Runbook retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@operational_procedures_router.get("/alerts")
async def get_alerts(limit: Optional[int] = 10):
    """Get recent operational alerts"""
    try:
        ops = get_operational_procedures()
        
        # Get recent alerts
        recent_alerts = ops.alerts[-limit:] if ops.alerts else []
        
        alerts_data = []
        for alert in recent_alerts:
            alerts_data.append({
                "level": alert.level.value,
                "component": alert.component,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "resolved": alert.resolved,
                "resolution_time": alert.resolution_time.isoformat() if alert.resolution_time else None
            })
        
        return {
            "alerts": alerts_data,
            "count": len(alerts_data),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Alerts retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@operational_procedures_router.post("/alerts/{alert_index}/resolve")
async def resolve_alert(alert_index: int):
    """Mark an alert as resolved"""
    try:
        ops = get_operational_procedures()
        
        if alert_index >= len(ops.alerts) or alert_index < 0:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        alert = ops.alerts[alert_index]
        alert.resolved = True
        alert.resolution_time = datetime.now()
        
        return {
            "message": "Alert marked as resolved",
            "alert_index": alert_index,
            "resolution_time": alert.resolution_time.isoformat()
        }
    except Exception as e:
        logger.error(f"Alert resolution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@operational_procedures_router.get("/procedures")
async def list_procedures():
    """List available recovery procedures"""
    try:
        ops = get_operational_procedures()
        
        procedures = list(ops.recovery_procedures.keys())
        
        return {
            "procedures": procedures,
            "count": len(procedures),
            "description": "Available automated recovery procedures",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Procedures listing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@operational_procedures_router.get("/thresholds")
async def get_scaling_thresholds():
    """Get current scaling thresholds"""
    try:
        ops = get_operational_procedures()
        
        return {
            "thresholds": ops.scaling_thresholds,
            "description": "Current system scaling thresholds",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Thresholds retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@operational_procedures_router.put("/thresholds")
async def update_scaling_thresholds(thresholds: Dict[str, float]):
    """Update scaling thresholds"""
    try:
        ops = get_operational_procedures()
        
        # Validate threshold values
        valid_keys = set(ops.scaling_thresholds.keys())
        provided_keys = set(thresholds.keys())
        
        if not provided_keys.issubset(valid_keys):
            invalid_keys = provided_keys - valid_keys
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid threshold keys: {list(invalid_keys)}"
            )
        
        # Update thresholds
        ops.scaling_thresholds.update(thresholds)
        
        return {
            "message": "Scaling thresholds updated",
            "updated_thresholds": thresholds,
            "current_thresholds": ops.scaling_thresholds,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Thresholds update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))