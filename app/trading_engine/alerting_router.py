"""
FastAPI Router for Trading Engine Alerting System
Provides REST API endpoints for alert management
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import json

from .alerting_system import (
    alerting_system, AlertRule, AlertSeverity, AlertChannel, AlertCategory,
    send_risk_alert, send_order_alert, send_strategy_alert, send_system_alert
)

router = APIRouter(prefix="/api/trading-engine/alerts", tags=["alerts"])

# Pydantic models for API
class AlertRuleCreate(BaseModel):
    name: str = Field(..., description="Alert rule name")
    category: str = Field(..., description="Alert category")
    severity: str = Field(..., description="Alert severity")
    condition: str = Field(..., description="Alert condition as JSON string")
    channels: List[str] = Field(..., description="Alert channels")
    throttle_minutes: int = Field(5, description="Throttle time in minutes")
    max_alerts_per_hour: int = Field(10, description="Maximum alerts per hour")
    user_id: Optional[str] = Field(None, description="User ID for user-specific rules")

class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None
    throttle_minutes: Optional[int] = None
    max_alerts_per_hour: Optional[int] = None
    channels: Optional[List[str]] = None

class UserPreferences(BaseModel):
    email: Optional[str] = Field(None, description="Email address")
    sms: Optional[str] = Field(None, description="Phone number for SMS")
    webhook: Optional[str] = Field(None, description="Webhook URL")
    push_token: Optional[str] = Field(None, description="Push notification token")

class TriggerAlertRequest(BaseModel):
    rule_id: str = Field(..., description="Alert rule ID")
    data: Dict[str, Any] = Field(..., description="Alert data")
    title: Optional[str] = Field(None, description="Custom alert title")
    message: Optional[str] = Field(None, description="Custom alert message")

class RiskAlertRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    risk_type: str = Field(..., description="Type of risk")
    current_value: float = Field(..., description="Current risk value")
    threshold: float = Field(..., description="Risk threshold")
    additional_data: Optional[Dict[str, Any]] = Field(None, description="Additional data")

class OrderAlertRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    order_id: str = Field(..., description="Order ID")
    status: str = Field(..., description="Order status")
    additional_data: Optional[Dict[str, Any]] = Field(None, description="Additional data")

class StrategyAlertRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    strategy_id: str = Field(..., description="Strategy ID")
    event_type: str = Field(..., description="Event type")
    additional_data: Optional[Dict[str, Any]] = Field(None, description="Additional data")

class SystemAlertRequest(BaseModel):
    severity: str = Field(..., description="Alert severity")
    component: str = Field(..., description="System component")
    message: str = Field(..., description="Alert message")
    additional_data: Optional[Dict[str, Any]] = Field(None, description="Additional data")

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "alerting_system",
        "timestamp": datetime.now().isoformat(),
        "active_rules": len(alerting_system.rules),
        "queue_size": alerting_system.alert_queue.qsize()
    }

@router.post("/rules")
async def create_alert_rule(rule_data: AlertRuleCreate):
    """Create new alert rule"""
    try:
        # Validate enums
        try:
            category = AlertCategory(rule_data.category.upper())
            severity = AlertSeverity(rule_data.severity.upper())
            channels = [AlertChannel(c.upper()) for c in rule_data.channels]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid enum value: {e}")
        
        # Validate condition JSON
        try:
            json.loads(rule_data.condition)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid condition JSON")
        
        # Generate rule ID
        rule_id = f"{category.value.lower()}_{rule_data.name.lower().replace(' ', '_')}"
        
        # Create rule
        rule = AlertRule(
            rule_id=rule_id,
            name=rule_data.name,
            category=category,
            severity=severity,
            condition=rule_data.condition,
            channels=channels,
            throttle_minutes=rule_data.throttle_minutes,
            max_alerts_per_hour=rule_data.max_alerts_per_hour,
            user_id=rule_data.user_id
        )
        
        success = alerting_system.add_rule(rule)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create alert rule")
        
        return {
            "success": True,
            "rule_id": rule_id,
            "message": "Alert rule created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.get("/rules")
async def get_alert_rules(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    category: Optional[str] = Query(None, description="Filter by category"),
    enabled_only: bool = Query(True, description="Show only enabled rules")
):
    """Get alert rules"""
    try:
        rules = []
        for rule in alerting_system.rules.values():
            # Apply filters
            if user_id and rule.user_id != user_id:
                continue
            if category and rule.category.value.upper() != category.upper():
                continue
            if enabled_only and not rule.enabled:
                continue
            
            rule_dict = {
                "rule_id": rule.rule_id,
                "name": rule.name,
                "category": rule.category.value,
                "severity": rule.severity.value,
                "condition": rule.condition,
                "channels": [c.value for c in rule.channels],
                "enabled": rule.enabled,
                "throttle_minutes": rule.throttle_minutes,
                "max_alerts_per_hour": rule.max_alerts_per_hour,
                "user_id": rule.user_id,
                "created_at": rule.created_at.isoformat()
            }
            rules.append(rule_dict)
        
        return {
            "success": True,
            "rules": rules,
            "total": len(rules)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.put("/rules/{rule_id}")
async def update_alert_rule(rule_id: str, updates: AlertRuleUpdate):
    """Update alert rule"""
    try:
        if rule_id not in alerting_system.rules:
            raise HTTPException(status_code=404, detail="Alert rule not found")
        
        rule = alerting_system.rules[rule_id]
        
        # Apply updates
        if updates.name is not None:
            rule.name = updates.name
        if updates.enabled is not None:
            rule.enabled = updates.enabled
        if updates.throttle_minutes is not None:
            rule.throttle_minutes = updates.throttle_minutes
        if updates.max_alerts_per_hour is not None:
            rule.max_alerts_per_hour = updates.max_alerts_per_hour
        if updates.channels is not None:
            try:
                rule.channels = [AlertChannel(c.upper()) for c in updates.channels]
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid channel: {e}")
        
        # Save updated rule
        success = alerting_system.add_rule(rule)  # add_rule handles updates too
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update alert rule")
        
        return {
            "success": True,
            "message": "Alert rule updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.delete("/rules/{rule_id}")
async def delete_alert_rule(rule_id: str):
    """Delete alert rule"""
    try:
        if rule_id not in alerting_system.rules:
            raise HTTPException(status_code=404, detail="Alert rule not found")
        
        success = alerting_system.remove_rule(rule_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete alert rule")
        
        return {
            "success": True,
            "message": "Alert rule deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.post("/preferences/{user_id}")
async def update_user_preferences(user_id: str, preferences: UserPreferences):
    """Update user notification preferences"""
    try:
        prefs_dict = {}
        
        if preferences.email:
            prefs_dict[AlertChannel.EMAIL.value] = preferences.email
        if preferences.sms:
            prefs_dict[AlertChannel.SMS.value] = preferences.sms
        if preferences.webhook:
            prefs_dict[AlertChannel.WEBHOOK.value] = preferences.webhook
        if preferences.push_token:
            prefs_dict[AlertChannel.PUSH.value] = preferences.push_token
        
        success = alerting_system.update_user_preferences(user_id, prefs_dict)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update preferences")
        
        return {
            "success": True,
            "message": "User preferences updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.get("/preferences/{user_id}")
async def get_user_preferences(user_id: str):
    """Get user notification preferences"""
    try:
        preferences = alerting_system.user_preferences.get(user_id, {})
        
        return {
            "success": True,
            "user_id": user_id,
            "preferences": preferences
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.post("/trigger")
async def trigger_alert(request: TriggerAlertRequest):
    """Trigger alert manually"""
    try:
        success = await alerting_system.trigger_alert(
            rule_id=request.rule_id,
            data=request.data,
            title=request.title,
            message=request.message
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to trigger alert")
        
        return {
            "success": True,
            "message": "Alert triggered successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.post("/trigger/risk")
async def trigger_risk_alert(request: RiskAlertRequest):
    """Trigger risk management alert"""
    try:
        await send_risk_alert(
            user_id=request.user_id,
            risk_type=request.risk_type,
            current_value=request.current_value,
            threshold=request.threshold,
            additional_data=request.additional_data
        )
        
        return {
            "success": True,
            "message": "Risk alert triggered successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.post("/trigger/order")
async def trigger_order_alert(request: OrderAlertRequest):
    """Trigger order execution alert"""
    try:
        await send_order_alert(
            user_id=request.user_id,
            order_id=request.order_id,
            status=request.status,
            additional_data=request.additional_data
        )
        
        return {
            "success": True,
            "message": "Order alert triggered successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.post("/trigger/strategy")
async def trigger_strategy_alert(request: StrategyAlertRequest):
    """Trigger strategy performance alert"""
    try:
        await send_strategy_alert(
            user_id=request.user_id,
            strategy_id=request.strategy_id,
            event_type=request.event_type,
            additional_data=request.additional_data
        )
        
        return {
            "success": True,
            "message": "Strategy alert triggered successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.post("/trigger/system")
async def trigger_system_alert(request: SystemAlertRequest):
    """Trigger system health alert"""
    try:
        severity = AlertSeverity(request.severity.upper())
        
        await send_system_alert(
            severity=severity,
            component=request.component,
            message=request.message,
            additional_data=request.additional_data
        )
        
        return {
            "success": True,
            "message": "System alert triggered successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid severity: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.get("/alerts")
async def get_alerts(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    category: Optional[str] = Query(None, description="Filter by category"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(100, description="Maximum number of alerts to return")
):
    """Get alerts with optional filtering"""
    try:
        # Convert string parameters to enums
        category_enum = None
        if category:
            try:
                category_enum = AlertCategory(category.upper())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
        
        severity_enum = None
        if severity:
            try:
                severity_enum = AlertSeverity(severity.upper())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
        
        alerts = alerting_system.get_alerts(
            user_id=user_id,
            category=category_enum,
            severity=severity_enum,
            limit=limit
        )
        
        return {
            "success": True,
            "alerts": alerts,
            "total": len(alerts)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.put("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Acknowledge an alert"""
    try:
        success = alerting_system.acknowledge_alert(alert_id)
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found or already acknowledged")
        
        return {
            "success": True,
            "message": "Alert acknowledged successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.put("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """Resolve an alert"""
    try:
        success = alerting_system.resolve_alert(alert_id)
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found or already resolved")
        
        return {
            "success": True,
            "message": "Alert resolved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.get("/statistics")
async def get_alert_statistics(
    user_id: Optional[str] = Query(None, description="Filter by user ID")
):
    """Get alert statistics"""
    try:
        stats = alerting_system.get_alert_statistics(user_id=user_id)
        
        return {
            "success": True,
            "statistics": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.get("/channels")
async def get_available_channels():
    """Get available alert channels"""
    return {
        "success": True,
        "channels": [channel.value for channel in AlertChannel]
    }

@router.get("/categories")
async def get_available_categories():
    """Get available alert categories"""
    return {
        "success": True,
        "categories": [category.value for category in AlertCategory]
    }

@router.get("/severities")
async def get_available_severities():
    """Get available alert severities"""
    return {
        "success": True,
        "severities": [severity.value for severity in AlertSeverity]
    }

@router.post("/test")
async def test_alert_system():
    """Test alert system with sample alerts"""
    try:
        # Create test rule
        test_rule = AlertRule(
            rule_id="test_rule",
            name="Test Alert Rule",
            category=AlertCategory.SYSTEM_HEALTH,
            severity=AlertSeverity.INFO,
            condition='{"field": "test", "operator": "eq", "value": true}',
            channels=[AlertChannel.EMAIL, AlertChannel.PUSH],
            user_id="test_user"
        )
        
        alerting_system.add_rule(test_rule)
        
        # Set test preferences
        alerting_system.update_user_preferences("test_user", {
            AlertChannel.EMAIL.value: "test@example.com",
            AlertChannel.PUSH.value: "test_device_token"
        })
        
        # Trigger test alert
        await alerting_system.trigger_alert(
            rule_id="test_rule",
            data={"test": True, "message": "This is a test alert"},
            title="Test Alert",
            message="Alert system test completed successfully"
        )
        
        return {
            "success": True,
            "message": "Test alert triggered successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")