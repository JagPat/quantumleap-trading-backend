"""
Emergency Stop API Router
FastAPI endpoints for emergency stop functionality
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from .emergency_stop import (
    emergency_stop_system, 
    EmergencyStopRequest, 
    EmergencyStopReason, 
    EmergencyStopScope
)
from .monitoring import trading_monitor
from app.database.service import get_user_credentials

router = APIRouter(prefix="/emergency-stop", tags=["Emergency Stop"])

# Request/Response Models

class EmergencyStopRequestModel(BaseModel):
    """Emergency stop request model"""
    reason: str = Field(..., description="Reason for emergency stop")
    scope: str = Field(default="USER", description="Scope of emergency stop (USER, STRATEGY, SYMBOL)")
    target_id: Optional[str] = Field(None, description="Target ID (strategy_id, symbol, etc.)")
    cancel_orders: bool = Field(True, description="Cancel all active orders")
    pause_strategies: bool = Field(True, description="Pause all active strategies")
    close_positions: bool = Field(False, description="Close all open positions")

class EmergencyStopResponseModel(BaseModel):
    """Emergency stop response model"""
    success: bool
    message: str
    orders_cancelled: int
    strategies_paused: int
    positions_closed: int
    execution_time_ms: float
    errors: List[str]
    stop_id: str

class EmergencyStopHistoryModel(BaseModel):
    """Emergency stop history model"""
    user_id: str
    reason: str
    scope: str
    target_id: Optional[str]
    message: str
    initiated_by: str
    success: bool
    orders_cancelled: int
    strategies_paused: int
    positions_closed: int
    execution_time_ms: float
    errors: List[str]
    created_at: str
    completed_at: str

# Dependency to get user ID (simplified for now)
async def get_current_user_id() -> str:
    """Get current user ID - simplified implementation"""
    # In production, this would extract user ID from JWT token
    return "default_user"

# API Endpoints

@router.post("/execute", response_model=EmergencyStopResponseModel)
async def execute_emergency_stop(
    request: EmergencyStopRequestModel,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id)
):
    """
    Execute emergency stop for the current user
    
    This endpoint immediately cancels all orders and pauses strategies
    """
    try:
        # Validate scope
        try:
            scope = EmergencyStopScope(request.scope.upper())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid scope: {request.scope}. Must be one of: USER, STRATEGY, SYMBOL, SYSTEM"
            )
        
        # Determine reason
        reason = EmergencyStopReason.USER_INITIATED
        if "risk" in request.reason.lower():
            reason = EmergencyStopReason.RISK_VIOLATION
        elif "system" in request.reason.lower():
            reason = EmergencyStopReason.SYSTEM_ERROR
        elif "market" in request.reason.lower():
            reason = EmergencyStopReason.MARKET_CONDITION
        
        # Create emergency stop request
        stop_request = EmergencyStopRequest(
            user_id=user_id,
            reason=reason,
            scope=scope,
            target_id=request.target_id,
            message=request.reason,
            initiated_by=user_id,
            cancel_orders=request.cancel_orders,
            pause_strategies=request.pause_strategies,
            close_positions=request.close_positions
        )
        
        # Execute emergency stop
        result = await emergency_stop_system.execute_emergency_stop(stop_request)
        
        # Create response
        stop_id = f"{user_id}_{scope.value}_{result.completed_at.timestamp()}"
        
        response = EmergencyStopResponseModel(
            success=result.success,
            message="Emergency stop executed successfully" if result.success else "Emergency stop completed with errors",
            orders_cancelled=result.orders_cancelled,
            strategies_paused=result.strategies_paused,
            positions_closed=result.positions_closed,
            execution_time_ms=result.execution_time_ms,
            errors=result.errors,
            stop_id=stop_id
        )
        
        # Log the emergency stop
        trading_monitor.create_alert(
            "CRITICAL" if result.success else "ERROR",
            "Emergency Stop Executed",
            f"User {user_id} executed emergency stop: {request.reason}",
            "emergency_stop",
            user_id
        )
        
        return response
        
    except Exception as e:
        error_msg = f"Error executing emergency stop: {str(e)}"
        trading_monitor.create_alert(
            "ERROR",
            "Emergency Stop Failed",
            error_msg,
            "emergency_stop",
            user_id
        )
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/panic", response_model=EmergencyStopResponseModel)
async def panic_button(
    user_id: str = Depends(get_current_user_id)
):
    """
    Panic button - immediate emergency stop with position closure
    
    This is the most aggressive emergency stop that:
    - Cancels all orders immediately
    - Pauses all strategies
    - Closes all positions
    """
    try:
        result = await emergency_stop_system.user_emergency_stop(
            user_id=user_id,
            reason="PANIC BUTTON - Immediate stop requested",
            close_positions=True
        )
        
        stop_id = f"{user_id}_PANIC_{result.completed_at.timestamp()}"
        
        response = EmergencyStopResponseModel(
            success=result.success,
            message="PANIC STOP executed - All trading activity halted",
            orders_cancelled=result.orders_cancelled,
            strategies_paused=result.strategies_paused,
            positions_closed=result.positions_closed,
            execution_time_ms=result.execution_time_ms,
            errors=result.errors,
            stop_id=stop_id
        )
        
        # Critical alert for panic button
        trading_monitor.create_alert(
            "CRITICAL",
            "PANIC BUTTON ACTIVATED",
            f"User {user_id} activated panic button - all trading halted",
            "emergency_stop",
            user_id
        )
        
        return response
        
    except Exception as e:
        error_msg = f"Error executing panic stop: {str(e)}"
        trading_monitor.create_alert(
            "ERROR",
            "Panic Button Failed",
            error_msg,
            "emergency_stop",
            user_id
        )
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/strategy/{strategy_id}/stop", response_model=EmergencyStopResponseModel)
async def stop_strategy(
    strategy_id: str,
    reason: str = "Strategy emergency stop",
    user_id: str = Depends(get_current_user_id)
):
    """
    Emergency stop for a specific strategy
    
    Cancels orders and pauses the specified strategy only
    """
    try:
        result = await emergency_stop_system.strategy_emergency_stop(
            user_id=user_id,
            strategy_id=strategy_id,
            reason=reason
        )
        
        stop_id = f"{user_id}_STRATEGY_{strategy_id}_{result.completed_at.timestamp()}"
        
        response = EmergencyStopResponseModel(
            success=result.success,
            message=f"Strategy {strategy_id} emergency stop executed",
            orders_cancelled=result.orders_cancelled,
            strategies_paused=result.strategies_paused,
            positions_closed=result.positions_closed,
            execution_time_ms=result.execution_time_ms,
            errors=result.errors,
            stop_id=stop_id
        )
        
        trading_monitor.create_alert(
            "WARNING",
            "Strategy Emergency Stop",
            f"Strategy {strategy_id} emergency stopped by user {user_id}: {reason}",
            "emergency_stop",
            user_id
        )
        
        return response
        
    except Exception as e:
        error_msg = f"Error stopping strategy {strategy_id}: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/history", response_model=List[EmergencyStopHistoryModel])
async def get_emergency_stop_history(
    limit: int = 50,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get emergency stop history for the current user
    """
    try:
        history = emergency_stop_system.get_stop_history(user_id=user_id, limit=limit)
        
        return [
            EmergencyStopHistoryModel(**stop_data)
            for stop_data in history
        ]
        
    except Exception as e:
        error_msg = f"Error retrieving emergency stop history: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/active", response_model=List[Dict[str, Any]])
async def get_active_emergency_stops(
    user_id: str = Depends(get_current_user_id)
):
    """
    Get currently active emergency stops
    """
    try:
        active_stops = emergency_stop_system.get_active_stops()
        
        # Filter by user
        user_stops = [
            stop for stop in active_stops 
            if stop['user_id'] == user_id
        ]
        
        return user_stops
        
    except Exception as e:
        error_msg = f"Error retrieving active emergency stops: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/status")
async def get_emergency_stop_status(
    user_id: str = Depends(get_current_user_id)
):
    """
    Get emergency stop system status
    """
    try:
        # Get recent history
        recent_stops = emergency_stop_system.get_stop_history(user_id=user_id, limit=5)
        active_stops = emergency_stop_system.get_active_stops()
        
        # Calculate statistics
        total_stops = len(emergency_stop_system.stop_history)
        user_stops = len([s for s in emergency_stop_system.stop_history if s.request.user_id == user_id])
        successful_stops = len([s for s in emergency_stop_system.stop_history if s.success])
        
        return {
            "system_status": "operational",
            "total_emergency_stops": total_stops,
            "user_emergency_stops": user_stops,
            "successful_stops": successful_stops,
            "success_rate": (successful_stops / total_stops * 100) if total_stops > 0 else 100,
            "active_stops": len([s for s in active_stops if s['user_id'] == user_id]),
            "recent_stops": len(recent_stops),
            "last_stop": recent_stops[0]['completed_at'] if recent_stops else None
        }
        
    except Exception as e:
        error_msg = f"Error retrieving emergency stop status: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)

# Health check endpoint
@router.get("/health")
async def emergency_stop_health():
    """
    Health check for emergency stop system
    """
    try:
        # Basic health checks
        active_stops_count = len(emergency_stop_system.get_active_stops())
        history_size = len(emergency_stop_system.stop_history)
        
        return {
            "status": "healthy",
            "active_stops": active_stops_count,
            "history_size": history_size,
            "system_ready": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "system_ready": False,
            "timestamp": datetime.now().isoformat()
        }