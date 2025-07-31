"""
Manual Override API Router
FastAPI endpoints for manual override functionality
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from .manual_override import (
    manual_override_system,
    ManualOverrideRequest,
    OverrideType,
    OverrideReason
)
from .monitoring import trading_monitor

router = APIRouter(prefix="/manual-override", tags=["Manual Override"])

# Request/Response Models

class ManualOrderRequest(BaseModel):
    """Manual order placement request"""
    symbol: str = Field(..., description="Trading symbol")
    side: str = Field(..., description="Order side (BUY/SELL)")
    quantity: int = Field(..., gt=0, description="Order quantity")
    order_type: str = Field(default="MARKET", description="Order type (MARKET/LIMIT/STOP_LOSS)")
    price: Optional[float] = Field(None, description="Limit price (for limit orders)")
    stop_price: Optional[float] = Field(None, description="Stop price (for stop orders)")
    reason: str = Field(default="Manual order placement", description="Reason for manual order")
    risk_override: bool = Field(default=False, description="Override risk validation")

class StrategyControlRequest(BaseModel):
    """Strategy control request"""
    strategy_id: str = Field(..., description="Strategy ID to control")
    action: str = Field(..., description="Action to take (pause/resume/stop)")
    close_positions: bool = Field(default=False, description="Close positions when stopping")
    reason: str = Field(default="Manual strategy control", description="Reason for control action")

class PositionClosureRequest(BaseModel):
    """Position closure request"""
    symbol: str = Field(..., description="Symbol to close")
    price: Optional[float] = Field(None, description="Optional limit price for closure")
    quantity: Optional[int] = Field(None, description="Optional quantity for partial closure")
    reason: str = Field(default="Manual position closure", description="Reason for closure")

class RiskAdjustmentRequest(BaseModel):
    """Risk parameter adjustment request"""
    max_position_size: Optional[float] = Field(None, description="Maximum position size")
    stop_loss_percentage: Optional[float] = Field(None, description="Stop loss percentage")
    max_drawdown: Optional[float] = Field(None, description="Maximum drawdown")
    reason: str = Field(default="Manual risk adjustment", description="Reason for adjustment")

class SignalOverrideRequest(BaseModel):
    """Signal override request"""
    signal_id: str = Field(..., description="Signal ID to override")
    action: str = Field(..., description="Action to take (ignore/force_execute)")
    reason: str = Field(default="Manual signal override", description="Reason for override")

class ManualOverrideResponse(BaseModel):
    """Manual override response"""
    success: bool
    override_id: str
    actions_taken: List[str]
    warnings: List[str]
    errors: List[str]
    execution_time_ms: float
    risk_validation: Dict[str, Any]

class OverrideHistoryResponse(BaseModel):
    """Override history response"""
    override_id: str
    user_id: str
    override_type: str
    reason: str
    description: str
    success: bool
    actions_taken: List[str]
    warnings: List[str]
    errors: List[str]
    execution_time_ms: float
    created_at: str
    completed_at: str

# Dependency to get user ID (simplified for now)
async def get_current_user_id() -> str:
    """Get current user ID - simplified implementation"""
    # In production, this would extract user ID from JWT token
    return "default_user"

# API Endpoints

@router.post("/order/place", response_model=ManualOverrideResponse)
async def place_manual_order(
    request: ManualOrderRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Place a manual order with automatic risk validation
    
    This endpoint allows users to place orders manually while still
    applying risk validation and tracking.
    """
    try:
        result = await manual_override_system.place_manual_order(
            user_id=user_id,
            symbol=request.symbol,
            side=request.side.upper(),
            quantity=request.quantity,
            order_type=request.order_type.upper(),
            price=request.price,
            stop_price=request.stop_price,
            reason=request.reason
        )
        
        response = ManualOverrideResponse(
            success=result.success,
            override_id=result.request.id,
            actions_taken=result.actions_taken,
            warnings=result.warnings,
            errors=result.errors,
            execution_time_ms=result.execution_time_ms,
            risk_validation=result.risk_validation
        )
        
        # Log the manual order
        trading_monitor.create_alert(
            "INFO" if result.success else "WARNING",
            "Manual Order Placed" if result.success else "Manual Order Failed",
            f"User {user_id} placed manual order: {request.symbol} {request.side} {request.quantity}",
            "manual_override",
            user_id
        )
        
        return response
        
    except Exception as e:
        error_msg = f"Error placing manual order: {str(e)}"
        trading_monitor.create_alert(
            "ERROR",
            "Manual Order Error",
            error_msg,
            "manual_override",
            user_id
        )
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/strategy/control", response_model=ManualOverrideResponse)
async def control_strategy(
    request: StrategyControlRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Control strategy manually (pause/resume/stop)
    
    Allows users to manually control their automated strategies
    """
    try:
        # Validate action
        valid_actions = ['pause', 'resume', 'stop']
        if request.action.lower() not in valid_actions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action: {request.action}. Must be one of: {valid_actions}"
            )
        
        result = await manual_override_system.control_strategy(
            user_id=user_id,
            strategy_id=request.strategy_id,
            action=request.action.lower(),
            close_positions=request.close_positions,
            reason=request.reason
        )
        
        response = ManualOverrideResponse(
            success=result.success,
            override_id=result.request.id,
            actions_taken=result.actions_taken,
            warnings=result.warnings,
            errors=result.errors,
            execution_time_ms=result.execution_time_ms,
            risk_validation=result.risk_validation
        )
        
        # Log the strategy control
        trading_monitor.create_alert(
            "INFO" if result.success else "WARNING",
            "Manual Strategy Control" if result.success else "Strategy Control Failed",
            f"User {user_id} {request.action}ed strategy {request.strategy_id}",
            "manual_override",
            user_id
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error controlling strategy: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/position/close", response_model=ManualOverrideResponse)
async def close_position(
    request: PositionClosureRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Close position manually with proper tracking
    
    Allows users to manually close positions while maintaining
    proper audit trails and risk tracking.
    """
    try:
        result = await manual_override_system.close_position_manually(
            user_id=user_id,
            symbol=request.symbol,
            price=request.price,
            reason=request.reason
        )
        
        response = ManualOverrideResponse(
            success=result.success,
            override_id=result.request.id,
            actions_taken=result.actions_taken,
            warnings=result.warnings,
            errors=result.errors,
            execution_time_ms=result.execution_time_ms,
            risk_validation=result.risk_validation
        )
        
        # Log the position closure
        trading_monitor.create_alert(
            "INFO" if result.success else "WARNING",
            "Manual Position Closure" if result.success else "Position Closure Failed",
            f"User {user_id} manually closed position: {request.symbol}",
            "manual_override",
            user_id
        )
        
        return response
        
    except Exception as e:
        error_msg = f"Error closing position: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/risk/adjust", response_model=ManualOverrideResponse)
async def adjust_risk_parameters(
    request: RiskAdjustmentRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Adjust risk parameters manually
    
    Allows users to modify their risk parameters with proper validation
    and audit trails.
    """
    try:
        # Build parameters dict
        parameters = {}
        if request.max_position_size is not None:
            parameters['max_position_size'] = request.max_position_size
        if request.stop_loss_percentage is not None:
            parameters['stop_loss_percentage'] = request.stop_loss_percentage
        if request.max_drawdown is not None:
            parameters['max_drawdown'] = request.max_drawdown
        
        if not parameters:
            raise HTTPException(
                status_code=400,
                detail="At least one risk parameter must be provided"
            )
        
        # Create manual override request
        override_request = ManualOverrideRequest(
            id=f"risk_adj_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            user_id=user_id,
            override_type=OverrideType.RISK_ADJUSTMENT,
            reason=OverrideReason.RISK_MANAGEMENT,
            description=request.reason,
            parameters=parameters,
            initiated_by=user_id
        )
        
        result = await manual_override_system.execute_override(override_request)
        
        response = ManualOverrideResponse(
            success=result.success,
            override_id=result.request.id,
            actions_taken=result.actions_taken,
            warnings=result.warnings,
            errors=result.errors,
            execution_time_ms=result.execution_time_ms,
            risk_validation=result.risk_validation
        )
        
        # Log the risk adjustment
        trading_monitor.create_alert(
            "WARNING",  # Risk adjustments are always warnings
            "Manual Risk Adjustment",
            f"User {user_id} manually adjusted risk parameters",
            "manual_override",
            user_id
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error adjusting risk parameters: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/signal/override", response_model=ManualOverrideResponse)
async def override_signal(
    request: SignalOverrideRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Override AI signal (ignore or force execute)
    
    Allows users to manually override AI-generated signals
    """
    try:
        # Validate action
        valid_actions = ['ignore', 'force_execute']
        if request.action.lower() not in valid_actions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action: {request.action}. Must be one of: {valid_actions}"
            )
        
        # Create manual override request
        override_request = ManualOverrideRequest(
            id=f"signal_override_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            user_id=user_id,
            override_type=OverrideType.SIGNAL_OVERRIDE,
            reason=OverrideReason.USER_DECISION,
            description=request.reason,
            parameters={
                'signal_id': request.signal_id,
                'action': request.action.lower()
            },
            initiated_by=user_id
        )
        
        result = await manual_override_system.execute_override(override_request)
        
        response = ManualOverrideResponse(
            success=result.success,
            override_id=result.request.id,
            actions_taken=result.actions_taken,
            warnings=result.warnings,
            errors=result.errors,
            execution_time_ms=result.execution_time_ms,
            risk_validation=result.risk_validation
        )
        
        # Log the signal override
        trading_monitor.create_alert(
            "WARNING",  # Signal overrides are warnings
            "Manual Signal Override",
            f"User {user_id} {request.action}d signal {request.signal_id}",
            "manual_override",
            user_id
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error overriding signal: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/history", response_model=List[OverrideHistoryResponse])
async def get_override_history(
    limit: int = 50,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get manual override history for the current user
    """
    try:
        history = manual_override_system.get_override_history(user_id=user_id, limit=limit)
        
        return [
            OverrideHistoryResponse(**override_data)
            for override_data in history
        ]
        
    except Exception as e:
        error_msg = f"Error retrieving override history: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/pending", response_model=List[Dict[str, Any]])
async def get_pending_overrides(
    user_id: str = Depends(get_current_user_id)
):
    """
    Get pending manual overrides for the current user
    """
    try:
        pending = manual_override_system.get_pending_overrides(user_id=user_id)
        return pending
        
    except Exception as e:
        error_msg = f"Error retrieving pending overrides: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/status")
async def get_override_system_status(
    user_id: str = Depends(get_current_user_id)
):
    """
    Get manual override system status and statistics
    """
    try:
        # Get recent history
        recent_overrides = manual_override_system.get_override_history(user_id=user_id, limit=10)
        pending_overrides = manual_override_system.get_pending_overrides(user_id=user_id)
        
        # Calculate statistics
        total_overrides = len(manual_override_system.override_history)
        user_overrides = len([o for o in manual_override_system.override_history 
                             if o.request.user_id == user_id])
        successful_overrides = len([o for o in manual_override_system.override_history 
                                   if o.success and o.request.user_id == user_id])
        
        # Calculate success rate
        success_rate = (successful_overrides / user_overrides * 100) if user_overrides > 0 else 100
        
        # Get override types breakdown
        override_types = {}
        for override in manual_override_system.override_history:
            if override.request.user_id == user_id:
                override_type = override.request.override_type.value
                override_types[override_type] = override_types.get(override_type, 0) + 1
        
        return {
            "system_status": "operational",
            "risk_validation_enabled": manual_override_system.risk_validation_enabled,
            "total_overrides": total_overrides,
            "user_overrides": user_overrides,
            "successful_overrides": successful_overrides,
            "success_rate": round(success_rate, 2),
            "pending_overrides": len(pending_overrides),
            "recent_overrides": len(recent_overrides),
            "override_types": override_types,
            "last_override": recent_overrides[0]['completed_at'] if recent_overrides else None
        }
        
    except Exception as e:
        error_msg = f"Error retrieving override system status: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)

# Health check endpoint
@router.get("/health")
async def manual_override_health():
    """
    Health check for manual override system
    """
    try:
        # Basic health checks
        pending_count = len(manual_override_system.get_pending_overrides())
        history_size = len(manual_override_system.override_history)
        
        return {
            "status": "healthy",
            "pending_overrides": pending_count,
            "history_size": history_size,
            "risk_validation_enabled": manual_override_system.risk_validation_enabled,
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