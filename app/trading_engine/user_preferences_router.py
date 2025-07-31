"""
User Preferences API Router
FastAPI endpoints for user preference management
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from .user_preferences import (
    user_preferences_manager,
    PreferenceCategory,
    NotificationChannel,
    NotificationPriority,
    NotificationPreference,
    TradingPreferences,
    StrategyPreferences,
    MarketDataPreferences,
    PerformancePreferences
)
from .models import RiskParameters
from .monitoring import trading_monitor

router = APIRouter(prefix="/preferences", tags=["User Preferences"])

# Request/Response Models

class TradingPreferencesRequest(BaseModel):
    """Trading preferences update request"""
    auto_execute_signals: Optional[bool] = None
    min_confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    max_daily_trades: Optional[int] = Field(None, gt=0)
    max_concurrent_positions: Optional[int] = Field(None, gt=0)
    preferred_order_type: Optional[str] = None
    enable_after_hours_trading: Optional[bool] = None
    enable_pre_market_trading: Optional[bool] = None
    default_position_size_percent: Optional[float] = Field(None, gt=0.0, le=100.0)
    enable_partial_fills: Optional[bool] = None
    order_timeout_minutes: Optional[int] = Field(None, gt=0)

class RiskPreferencesRequest(BaseModel):
    """Risk management preferences update request"""
    max_position_size_percent: Optional[float] = Field(None, gt=0.0, le=100.0)
    max_portfolio_exposure_percent: Optional[float] = Field(None, gt=0.0, le=100.0)
    max_sector_exposure_percent: Optional[float] = Field(None, gt=0.0, le=100.0)
    stop_loss_percent: Optional[float] = Field(None, gt=0.0, le=100.0)
    take_profit_percent: Optional[float] = Field(None, gt=0.0)
    max_drawdown_percent: Optional[float] = Field(None, gt=0.0, le=100.0)
    daily_loss_limit_percent: Optional[float] = Field(None, gt=0.0, le=100.0)

class NotificationPreferenceRequest(BaseModel):
    """Notification preference request"""
    event_type: str = Field(..., description="Event type for notification")
    channels: List[str] = Field(..., description="Notification channels")
    priority: str = Field(..., description="Notification priority")
    enabled: bool = Field(True, description="Whether notification is enabled")
    throttle_minutes: int = Field(0, ge=0, description="Throttle time in minutes")
    conditions: Dict[str, Any] = Field(default_factory=dict, description="Notification conditions")

class NotificationPreferencesRequest(BaseModel):
    """Notification preferences update request"""
    add: Optional[NotificationPreferenceRequest] = None
    update: Optional[Dict[str, Any]] = None
    remove: Optional[str] = None

class StrategyPreferencesRequest(BaseModel):
    """Strategy preferences update request"""
    auto_deploy_optimized_strategies: Optional[bool] = None
    enable_strategy_suggestions: Optional[bool] = None
    max_strategies_per_user: Optional[int] = Field(None, gt=0)
    strategy_performance_review_days: Optional[int] = Field(None, gt=0)
    auto_pause_underperforming: Optional[bool] = None
    underperformance_threshold: Optional[float] = Field(None, ge=-1.0, le=1.0)
    enable_strategy_diversification: Optional[bool] = None
    max_sector_concentration: Optional[float] = Field(None, gt=0.0, le=1.0)

class MarketDataPreferencesRequest(BaseModel):
    """Market data preferences update request"""
    enable_real_time_data: Optional[bool] = None
    data_refresh_interval_seconds: Optional[int] = Field(None, gt=0)
    enable_extended_hours_data: Optional[bool] = None
    preferred_data_sources: Optional[List[str]] = None
    enable_level2_data: Optional[bool] = None
    enable_options_data: Optional[bool] = None
    enable_futures_data: Optional[bool] = None

class PerformancePreferencesRequest(BaseModel):
    """Performance preferences update request"""
    enable_real_time_pnl: Optional[bool] = None
    pnl_update_interval_seconds: Optional[int] = Field(None, gt=0)
    enable_performance_alerts: Optional[bool] = None
    daily_pnl_alert_threshold: Optional[float] = Field(None, gt=0.0)
    enable_drawdown_alerts: Optional[bool] = None
    max_drawdown_alert_threshold: Optional[float] = Field(None, gt=0.0, le=1.0)
    enable_benchmark_comparison: Optional[bool] = None
    benchmark_symbol: Optional[str] = None

class PreferenceUpdateResponse(BaseModel):
    """Preference update response"""
    success: bool
    message: str
    category: str
    updated_fields: List[str]
    timestamp: str

# Dependency to get user ID (simplified for now)
async def get_current_user_id() -> str:
    """Get current user ID - simplified implementation"""
    # In production, this would extract user ID from JWT token
    return "default_user"

# API Endpoints

@router.get("/")
async def get_all_preferences(
    user_id: str = Depends(get_current_user_id)
):
    """
    Get all user preferences
    """
    try:
        preferences = await user_preferences_manager.get_user_preferences(user_id)
        return preferences.to_dict()
        
    except Exception as e:
        error_msg = f"Error retrieving preferences: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/summary")
async def get_preferences_summary(
    user_id: str = Depends(get_current_user_id)
):
    """
    Get summary of user preferences
    """
    try:
        summary = user_preferences_manager.get_preference_summary(user_id)
        return summary
        
    except Exception as e:
        error_msg = f"Error retrieving preference summary: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/trading")
async def get_trading_preferences(
    user_id: str = Depends(get_current_user_id)
):
    """
    Get trading preferences
    """
    try:
        trading_prefs = await user_preferences_manager.get_trading_preferences(user_id)
        return trading_prefs.to_dict()
        
    except Exception as e:
        error_msg = f"Error retrieving trading preferences: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)

@router.put("/trading", response_model=PreferenceUpdateResponse)
async def update_trading_preferences(
    request: TradingPreferencesRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Update trading preferences
    """
    try:
        # Convert request to updates dict, excluding None values
        updates = {k: v for k, v in request.dict().items() if v is not None}
        
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        success = await user_preferences_manager.update_trading_preferences(user_id, updates)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update trading preferences")
        
        response = PreferenceUpdateResponse(
            success=True,
            message="Trading preferences updated successfully",
            category="TRADING",
            updated_fields=list(updates.keys()),
            timestamp=datetime.now().isoformat()
        )
        
        # Log the update
        trading_monitor.create_alert(
            "INFO",
            "Trading Preferences Updated",
            f"User {user_id} updated trading preferences: {', '.join(updates.keys())}",
            "user_preferences",
            user_id
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error updating trading preferences: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/risk")
async def get_risk_preferences(
    user_id: str = Depends(get_current_user_id)
):
    """
    Get risk management preferences
    """
    try:
        risk_prefs = await user_preferences_manager.get_risk_preferences(user_id)
        return risk_prefs.__dict__
        
    except Exception as e:
        error_msg = f"Error retrieving risk preferences: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)

@router.put("/risk", response_model=PreferenceUpdateResponse)
async def update_risk_preferences(
    request: RiskPreferencesRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Update risk management preferences
    """
    try:
        # Convert request to updates dict, excluding None values
        updates = {k: v for k, v in request.dict().items() if v is not None}
        
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        success = await user_preferences_manager.update_risk_preferences(user_id, updates)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update risk preferences")
        
        response = PreferenceUpdateResponse(
            success=True,
            message="Risk management preferences updated successfully",
            category="RISK_MANAGEMENT",
            updated_fields=list(updates.keys()),
            timestamp=datetime.now().isoformat()
        )
        
        # Log the update (risk changes are always warnings)
        trading_monitor.create_alert(
            "WARNING",
            "Risk Preferences Updated",
            f"User {user_id} updated risk preferences: {', '.join(updates.keys())}",
            "user_preferences",
            user_id
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error updating risk preferences: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/notifications")
async def get_notification_preferences(
    user_id: str = Depends(get_current_user_id)
):
    """
    Get notification preferences
    """
    try:
        notification_prefs = await user_preferences_manager.get_notification_preferences(user_id)
        return [pref.to_dict() for pref in notification_prefs]
        
    except Exception as e:
        error_msg = f"Error retrieving notification preferences: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)

@router.put("/notifications", response_model=PreferenceUpdateResponse)
async def update_notification_preferences(
    request: NotificationPreferencesRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Update notification preferences
    """
    try:
        # Convert request to updates dict
        updates = {}
        updated_fields = []
        
        if request.add:
            # Validate channels and priority
            try:
                channels = [NotificationChannel(c) for c in request.add.channels]
                priority = NotificationPriority(request.add.priority)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid channel or priority: {str(e)}")
            
            updates['add'] = request.add.dict()
            updated_fields.append(f"add_{request.add.event_type}")
        
        if request.update:
            updates['update'] = request.update
            updated_fields.append(f"update_{request.update.get('event_type', 'unknown')}")
        
        if request.remove:
            updates['remove'] = request.remove
            updated_fields.append(f"remove_{request.remove}")
        
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        success = await user_preferences_manager.update_notification_preferences(user_id, updates)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update notification preferences")
        
        response = PreferenceUpdateResponse(
            success=True,
            message="Notification preferences updated successfully",
            category="NOTIFICATIONS",
            updated_fields=updated_fields,
            timestamp=datetime.now().isoformat()
        )
        
        # Log the update
        trading_monitor.create_alert(
            "INFO",
            "Notification Preferences Updated",
            f"User {user_id} updated notification preferences: {', '.join(updated_fields)}",
            "user_preferences",
            user_id
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error updating notification preferences: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)

@router.put("/strategy", response_model=PreferenceUpdateResponse)
async def update_strategy_preferences(
    request: StrategyPreferencesRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Update strategy preferences
    """
    try:
        # Convert request to updates dict, excluding None values
        updates = {k: v for k, v in request.dict().items() if v is not None}
        
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        success = await user_preferences_manager.update_preferences(
            user_id, PreferenceCategory.STRATEGY.value, updates
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update strategy preferences")
        
        response = PreferenceUpdateResponse(
            success=True,
            message="Strategy preferences updated successfully",
            category="STRATEGY",
            updated_fields=list(updates.keys()),
            timestamp=datetime.now().isoformat()
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error updating strategy preferences: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)

@router.put("/market-data", response_model=PreferenceUpdateResponse)
async def update_market_data_preferences(
    request: MarketDataPreferencesRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Update market data preferences
    """
    try:
        # Convert request to updates dict, excluding None values
        updates = {k: v for k, v in request.dict().items() if v is not None}
        
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        success = await user_preferences_manager.update_preferences(
            user_id, PreferenceCategory.MARKET_DATA.value, updates
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update market data preferences")
        
        response = PreferenceUpdateResponse(
            success=True,
            message="Market data preferences updated successfully",
            category="MARKET_DATA",
            updated_fields=list(updates.keys()),
            timestamp=datetime.now().isoformat()
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error updating market data preferences: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)

@router.put("/performance", response_model=PreferenceUpdateResponse)
async def update_performance_preferences(
    request: PerformancePreferencesRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Update performance preferences
    """
    try:
        # Convert request to updates dict, excluding None values
        updates = {k: v for k, v in request.dict().items() if v is not None}
        
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        success = await user_preferences_manager.update_preferences(
            user_id, PreferenceCategory.PERFORMANCE.value, updates
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update performance preferences")
        
        response = PreferenceUpdateResponse(
            success=True,
            message="Performance preferences updated successfully",
            category="PERFORMANCE",
            updated_fields=list(updates.keys()),
            timestamp=datetime.now().isoformat()
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error updating performance preferences: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/notification/check")
async def check_notification_preference(
    event_type: str,
    event_data: Dict[str, Any],
    user_id: str = Depends(get_current_user_id)
):
    """
    Check if notification should be sent for an event
    """
    try:
        result = await user_preferences_manager.should_send_notification(
            user_id, event_type, event_data
        )
        return result
        
    except Exception as e:
        error_msg = f"Error checking notification preference: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/defaults")
async def get_default_preferences():
    """
    Get default preference values
    """
    try:
        return {
            "trading": TradingPreferences().to_dict(),
            "risk_management": RiskParameters().__dict__,
            "strategy": StrategyPreferences().to_dict(),
            "market_data": MarketDataPreferences().to_dict(),
            "performance": PerformancePreferences().to_dict(),
            "notification_channels": [channel.value for channel in NotificationChannel],
            "notification_priorities": [priority.value for priority in NotificationPriority]
        }
        
    except Exception as e:
        error_msg = f"Error retrieving default preferences: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/reset/{category}")
async def reset_preferences_category(
    category: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Reset a preference category to defaults
    """
    try:
        # Validate category
        try:
            pref_category = PreferenceCategory(category.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
        
        # Get default values based on category
        if pref_category == PreferenceCategory.TRADING:
            defaults = TradingPreferences().to_dict()
        elif pref_category == PreferenceCategory.RISK_MANAGEMENT:
            defaults = RiskParameters().__dict__
        elif pref_category == PreferenceCategory.STRATEGY:
            defaults = StrategyPreferences().to_dict()
        elif pref_category == PreferenceCategory.MARKET_DATA:
            defaults = MarketDataPreferences().to_dict()
        elif pref_category == PreferenceCategory.PERFORMANCE:
            defaults = PerformancePreferences().to_dict()
        elif pref_category == PreferenceCategory.NOTIFICATIONS:
            # Reset to default notifications
            defaults = {'reset_to_defaults': True}
        else:
            raise HTTPException(status_code=400, detail=f"Reset not supported for category: {category}")
        
        # Apply defaults
        success = await user_preferences_manager.update_preferences(
            user_id, pref_category.value, defaults
        )
        
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to reset {category} preferences")
        
        # Log the reset
        trading_monitor.create_alert(
            "INFO",
            "Preferences Reset",
            f"User {user_id} reset {category} preferences to defaults",
            "user_preferences",
            user_id
        )
        
        return {
            "success": True,
            "message": f"{category} preferences reset to defaults",
            "category": category.upper(),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error resetting {category} preferences: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)

# Health check endpoint
@router.get("/health")
async def preferences_health():
    """
    Health check for user preferences system
    """
    try:
        # Basic health checks
        total_users = len(user_preferences_manager.user_preferences)
        cached_users = len(user_preferences_manager.preference_cache)
        
        return {
            "status": "healthy",
            "total_users": total_users,
            "cached_users": cached_users,
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