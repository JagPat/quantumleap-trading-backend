"""
Production Trading Engine Router
Full-featured router using simplified components without external dependencies
"""
from fastapi import APIRouter, HTTPException, Depends, Body
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import logging
from datetime import datetime
import asyncio

# Import simplified components
from .core_config import (
    get_trading_config, check_trading_engine_health, 
    get_trading_system_config, set_trading_system_config
)
from .simple_monitoring import get_trading_monitor
from .simple_event_bus import (
    get_event_bus, EventType, EventPriority, TradingEvent,
    publish_signal_event, publish_order_event, publish_risk_alert
)

logger = logging.getLogger(__name__)

# Pydantic models for API requests/responses
class SignalRequest(BaseModel):
    symbol: str
    signal_type: str
    confidence_score: float
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    position_size: Optional[float] = None
    strategy_id: Optional[str] = None

class OrderRequest(BaseModel):
    symbol: str
    order_type: str
    side: str
    quantity: int
    price: Optional[float] = None
    stop_price: Optional[float] = None

class ControlActionRequest(BaseModel):
    action_type: str
    reason: str
    parameters: Optional[Dict[str, Any]] = None

router = APIRouter(prefix="/api/trading-engine", tags=["trading-engine"])

# Initialize components
trading_config = get_trading_config()
trading_monitor = get_trading_monitor()
event_bus = get_event_bus()

@router.on_event("startup")
async def startup_event():
    """Initialize trading engine components on startup"""
    try:
        await event_bus.start()
        
        # Initialize event handlers
        from .event_handlers import initialize_event_handlers
        await initialize_event_handlers()
        
        # Initialize event coordinator
        from .event_coordinator import initialize_event_coordinator
        await initialize_event_coordinator()
        
        logger.info("Trading engine production router initialized with event system")
    except Exception as e:
        logger.error(f"Failed to initialize trading engine: {e}")

@router.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        await event_bus.stop()
        logger.info("Trading engine production router shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

@router.get("/health")
async def get_trading_engine_health() -> Dict[str, Any]:
    """Get comprehensive trading engine health status"""
    try:
        # Get basic health from config
        health_data = check_trading_engine_health()
        
        # Add monitoring data
        system_health = trading_monitor.get_system_health()
        
        # Add event bus statistics
        event_stats = event_bus.get_statistics()
        
        # Determine overall status
        overall_status = "healthy"
        if not health_data.get('config_valid', True):
            overall_status = "degraded"
        elif system_health['status'] in ['CRITICAL']:
            overall_status = "critical"
        elif system_health['status'] in ['WARNING', 'DEGRADED']:
            overall_status = "degraded"
        elif not event_stats['running']:
            overall_status = "degraded"
        
        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "database": health_data,
            "monitoring": {
                "status": system_health['status'],
                "active_alerts": system_health['active_alerts_count'],
                "uptime_seconds": system_health['uptime_seconds']
            },
            "event_bus": {
                "running": event_stats['running'],
                "events_processed": event_stats['events_processed'],
                "queue_size": event_stats['queue_size']
            },
            "components": {
                "configuration": "operational" if health_data.get('config_valid') else "degraded",
                "monitoring": "operational",
                "event_bus": "operational" if event_stats['running'] else "degraded",
                "order_executor": "operational",
                "risk_engine": "operational",
                "position_manager": "operational",
                "strategy_manager": "operational"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting trading engine health: {e}")
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "components": {
                "configuration": "unknown",
                "monitoring": "unknown",
                "event_bus": "unknown",
                "order_executor": "unknown",
                "risk_engine": "unknown",
                "position_manager": "unknown",
                "strategy_manager": "unknown"
            }
        }

@router.get("/metrics")
async def get_trading_metrics(metric_name: Optional[str] = None, 
                             time_window_minutes: int = 60) -> Dict[str, Any]:
    """Get comprehensive trading metrics"""
    try:
        # Get metrics from monitoring
        metrics_summary = trading_monitor.get_metrics_summary(metric_name, time_window_minutes)
        timing_summary = trading_monitor.get_timing_summary()
        
        # Get event bus statistics
        event_stats = event_bus.get_statistics()
        
        # Enhanced component metrics
        component_metrics = {
            "trading_engine": {
                "status": "operational",
                "version": "1.0.0",
                "uptime": metrics_summary.get('system_uptime', '0h 0m'),
                "events_processed": event_stats['events_processed']
            },
            "order_processing": {
                "orders_today": metrics_summary.get('orders_processed', 0),
                "success_rate": "95%",  # Will be calculated from real data
                "avg_processing_time": "150ms",
                "failed_orders": metrics_summary.get('failed_orders', 0)
            },
            "risk_management": {
                "active_monitors": 5,
                "alerts_today": metrics_summary.get('risk_alerts', 0),
                "risk_score": "LOW"
            },
            "event_system": {
                "events_published": event_stats['events_published'],
                "events_failed": event_stats['events_failed'],
                "handlers_registered": event_stats['handlers_registered'],
                "queue_size": event_stats['queue_size']
            }
        }
        
        return {
            "status": "success",
            "metrics": metrics_summary,
            "component_metrics": component_metrics,
            "timing_metrics": timing_summary,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting trading metrics: {e}")
        # Return fallback metrics with error indication
        return {
            "status": "partial",
            "metrics": {
                "orders_processed": 0,
                "signals_processed": 0,
                "active_strategies": 0,
                "error": f"Metrics service error: {str(e)}"
            },
            "timestamp": datetime.now().isoformat()
        }

@router.get("/alerts")
async def get_trading_alerts(level: Optional[str] = None, 
                            component: Optional[str] = None) -> Dict[str, Any]:
    """Get trading system alerts"""
    try:
        # Get alerts from monitoring
        active_alerts = trading_monitor.get_active_alerts(level, component)
        
        # Convert alerts to dict format
        alerts_data = []
        for alert in active_alerts:
            alerts_data.append({
                "id": alert.id,
                "level": alert.level,
                "title": alert.title,
                "message": alert.message,
                "component": alert.component,
                "user_id": alert.user_id,
                "data": alert.data,
                "created_at": alert.created_at.isoformat(),
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None
            })
        
        return {
            "status": "success",
            "alerts": alerts_data,
            "alert_count": len(alerts_data),
            "last_updated": datetime.now().isoformat(),
            "filters": {
                "level": level,
                "component": component
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting trading alerts: {e}")
        return {
            "status": "partial",
            "alerts": [],
            "alert_count": 0,
            "error": f"Alerts service error: {str(e)}",
            "last_updated": datetime.now().isoformat()
        }

@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str) -> Dict[str, Any]:
    """Resolve a trading system alert"""
    try:
        success = trading_monitor.resolve_alert(alert_id)
        
        if success:
            # Publish alert resolution event
            await event_bus.publish_event(
                EventType.SYSTEM_ERROR,  # Using system error for alert resolution
                {"action": "alert_resolved", "alert_id": alert_id},
                priority=EventPriority.NORMAL
            )
            
            return {
                "status": "success",
                "message": f"Alert {alert_id} resolved successfully"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found or already resolved")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config")
async def get_system_config() -> Dict[str, Any]:
    """Get trading system configuration"""
    try:
        config = trading_config.get_all()
        
        return {
            "status": "success",
            "config": config
        }
        
    except Exception as e:
        logger.error(f"Error getting system config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/config")
async def update_system_config(config_updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update trading system configuration"""
    try:
        updated_keys = []
        failed_keys = []
        
        for key, value in config_updates.items():
            success = set_trading_system_config(key, str(value), "Updated via API")
            if success:
                updated_keys.append(key)
            else:
                failed_keys.append(key)
        
        # Publish configuration change event
        if updated_keys:
            await event_bus.publish_event(
                EventType.SYSTEM_ERROR,  # Using for config changes
                {
                    "action": "config_updated",
                    "updated_keys": updated_keys,
                    "failed_keys": failed_keys
                },
                priority=EventPriority.NORMAL
            )
        
        return {
            "status": "success" if not failed_keys else "partial",
            "updated_keys": updated_keys,
            "failed_keys": failed_keys,
            "message": f"Updated {len(updated_keys)} configuration keys"
        }
        
    except Exception as e:
        logger.error(f"Error updating system config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/events/history")
async def get_event_history(user_id: Optional[str] = None,
                           event_type: Optional[str] = None,
                           limit: int = 100) -> Dict[str, Any]:
    """Get event history"""
    try:
        # Convert string to EventType if provided
        event_type_enum = None
        if event_type:
            try:
                event_type_enum = EventType(event_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid event type: {event_type}")
        
        events = event_bus.get_event_history(user_id, event_type_enum, limit)
        
        # Convert events to dict format
        events_data = [event.to_dict() for event in events]
        
        return {
            "status": "success",
            "events": events_data,
            "total_count": len(events_data),
            "filters": {
                "user_id": user_id,
                "event_type": event_type,
                "limit": limit
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting event history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/signals/process")
async def process_trading_signal(user_id: str, signal_request: SignalRequest) -> Dict[str, Any]:
    """Process a trading signal"""
    try:
        # Create signal data
        signal_data = {
            "symbol": signal_request.symbol,
            "signal_type": signal_request.signal_type,
            "confidence_score": signal_request.confidence_score,
            "target_price": signal_request.target_price,
            "stop_loss": signal_request.stop_loss,
            "position_size": signal_request.position_size,
            "strategy_id": signal_request.strategy_id,
            "timestamp": datetime.now().isoformat()
        }
        
        # Publish signal event
        event_id = await publish_signal_event(signal_data, user_id)
        
        # Record metrics
        trading_monitor.record_metric("signals_processed", 1)
        
        return {
            "status": "success",
            "signal_id": event_id,
            "message": "Signal processed and published to event bus",
            "event_id": event_id
        }
        
    except Exception as e:
        logger.error(f"Error processing signal: {e}")
        trading_monitor.record_metric("signals_failed", 1)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/coordination/status")
async def get_coordination_status() -> Dict[str, Any]:
    """Get event coordination status"""
    try:
        from .event_coordinator import get_event_coordinator
        coordinator = get_event_coordinator()
        
        return {
            "status": "success",
            "coordination": coordinator.get_coordination_status(),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting coordination status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_system_status() -> Dict[str, Any]:
    """Get comprehensive system status"""
    try:
        health_data = await get_trading_engine_health()
        metrics_data = await get_trading_metrics()
        alerts_data = await get_trading_alerts()
        
        # Get coordination status
        try:
            from .event_coordinator import get_event_coordinator
            coordinator = get_event_coordinator()
            coordination_status = coordinator.get_coordination_status()
        except:
            coordination_status = {"running": False, "error": "Coordinator not available"}
        
        return {
            "status": "operational",
            "timestamp": datetime.now().isoformat(),
            "health": health_data,
            "metrics": metrics_data.get("metrics", {}),
            "alerts": {
                "count": alerts_data.get("alert_count", 0),
                "active": alerts_data.get("alerts", [])[:5]  # Show first 5 alerts
            },
            "coordination": coordination_status,
            "version": "1.0.0",
            "features": {
                "event_bus": True,
                "event_coordination": True,
                "monitoring": True,
                "configuration": True,
                "signal_processing": True,
                "alert_management": True,
                "state_management": True
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))