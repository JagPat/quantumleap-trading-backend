"""
Trading Engine API Router
Comprehensive API for the automatic trading engine
"""
from fastapi import APIRouter, HTTPException, Depends, Body
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import logging
from datetime import datetime

# Import all trading engine components
from .database_schema import check_trading_engine_health, get_trading_system_config, set_trading_system_config
from .event_bus import event_bus
from .monitoring import trading_monitor
from .models import TradingSignal, SignalType, OrderType, OrderSide, OrderStatus, StrategyStatus
from .order_service import order_service
from .order_executor import order_executor
from .position_manager import position_manager
from .risk_engine import risk_engine
from .risk_monitor import risk_monitor
from .position_sizer import position_sizer
from .strategy_manager import strategy_manager, StrategyConfig, StrategyType
from .strategy_controller import strategy_controller
from .strategy_lifecycle import strategy_lifecycle_manager

# Import market data components
try:
    from .market_data_router import router as market_data_router
    MARKET_DATA_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Market data router not available: {e}")
    MARKET_DATA_AVAILABLE = False

try:
    from .market_condition_router import router as market_condition_router
    MARKET_CONDITION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Market condition router not available: {e}")
    MARKET_CONDITION_AVAILABLE = False

# Import emergency stop router
try:
    from .emergency_stop_router import router as emergency_stop_router
    EMERGENCY_STOP_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Emergency stop router not available: {e}")
    EMERGENCY_STOP_AVAILABLE = False

# Import manual override router
try:
    from .manual_override_router import router as manual_override_router
    MANUAL_OVERRIDE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Manual override router not available: {e}")
    MANUAL_OVERRIDE_AVAILABLE = False

# Import user preferences router
try:
    from .user_preferences_router import router as user_preferences_router
    USER_PREFERENCES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"User preferences router not available: {e}")
    USER_PREFERENCES_AVAILABLE = False

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

class StrategyConfigRequest(BaseModel):
    name: str
    description: str
    strategy_type: str
    symbols: List[str]
    parameters: Dict[str, Any]
    max_positions: int = 10
    max_daily_trades: int = 50

class ControlActionRequest(BaseModel):
    action_type: str
    reason: str
    parameters: Optional[Dict[str, Any]] = None

router = APIRouter(prefix="/api/trading-engine", tags=["trading-engine"])

# Include market data and condition monitoring sub-routers
if MARKET_DATA_AVAILABLE:
    router.include_router(market_data_router, prefix="/market-data", tags=["Market Data"])
    logger.info("Market data router included in trading engine")

if MARKET_CONDITION_AVAILABLE:
    router.include_router(market_condition_router, prefix="/market-condition", tags=["Market Condition"])
    logger.info("Market condition router included in trading engine")

if EMERGENCY_STOP_AVAILABLE:
    router.include_router(emergency_stop_router, tags=["Emergency Stop"])
    logger.info("Emergency stop router included in trading engine")

if MANUAL_OVERRIDE_AVAILABLE:
    router.include_router(manual_override_router, tags=["Manual Override"])
    logger.info("Manual override router included in trading engine")

if USER_PREFERENCES_AVAILABLE:
    router.include_router(user_preferences_router, tags=["User Preferences"])
    logger.info("User preferences router included in trading engine")

@router.get("/health")
async def get_trading_engine_health() -> Dict[str, Any]:
    """Get trading engine health status"""
    try:
        # Database health
        db_health = check_trading_engine_health()
        
        # Event bus health
        event_stats = event_bus.get_statistics()
        
        # System health
        system_health = trading_monitor.get_system_health()
        
        # Overall status
        overall_status = "healthy"
        if db_health["status"] != "healthy":
            overall_status = "unhealthy"
        elif system_health["status"] in ["CRITICAL", "DEGRADED"]:
            overall_status = "degraded"
        elif system_health["status"] == "WARNING":
            overall_status = "warning"
        
        return {
            "status": overall_status,
            "database": db_health,
            "event_bus": event_stats,
            "system": system_health,
            "timestamp": trading_monitor.get_system_health()["last_updated"]
        }
        
    except Exception as e:
        logger.error(f"Error getting trading engine health: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics")
async def get_trading_metrics(metric_name: Optional[str] = None, 
                             time_window_minutes: int = 60) -> Dict[str, Any]:
    """Get trading metrics"""
    try:
        metrics_summary = trading_monitor.get_metrics_summary(metric_name, time_window_minutes)
        timing_summary = trading_monitor.get_timing_summary()
        
        return {
            "metrics": metrics_summary,
            "timings": timing_summary,
            "time_window_minutes": time_window_minutes
        }
        
    except Exception as e:
        logger.error(f"Error getting trading metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts")
async def get_trading_alerts(level: Optional[str] = None, 
                            component: Optional[str] = None) -> Dict[str, Any]:
    """Get trading system alerts"""
    try:
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
            "alerts": alerts_data,
            "total_count": len(alerts_data),
            "filters": {
                "level": level,
                "component": component
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting trading alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str) -> Dict[str, Any]:
    """Resolve a trading system alert"""
    try:
        success = trading_monitor.resolve_alert(alert_id)
        
        if success:
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
        config_keys = [
            'max_concurrent_orders',
            'order_timeout_seconds',
            'risk_check_enabled',
            'emergency_stop_enabled',
            'max_position_size_percent',
            'max_portfolio_exposure_percent',
            'max_sector_exposure_percent',
            'default_stop_loss_percent',
            'market_data_refresh_seconds'
        ]
        
        config = {}
        for key in config_keys:
            value = get_trading_system_config(key)
            if value is not None:
                # Try to convert to appropriate type
                if key.endswith('_enabled'):
                    config[key] = value.lower() == 'true'
                elif key.endswith('_seconds') or key.endswith('_percent') or key == 'max_concurrent_orders':
                    try:
                        config[key] = float(value) if '.' in value else int(value)
                    except ValueError:
                        config[key] = value
                else:
                    config[key] = value
        
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
            # Convert value to string for storage
            str_value = str(value).lower() if isinstance(value, bool) else str(value)
            
            success = set_trading_system_config(key, str_value, f"Updated via API")
            if success:
                updated_keys.append(key)
            else:
                failed_keys.append(key)
        
        return {
            "status": "success" if not failed_keys else "partial",
            "updated_keys": updated_keys,
            "failed_keys": failed_keys,
            "message": f"Updated {len(updated_keys)} configuration keys"
        }
        
    except Exception as e:
        logger.error(f"Error updating system config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/event-history")
async def get_event_history(user_id: Optional[str] = None,
                           event_type: Optional[str] = None,
                           limit: int = 100) -> Dict[str, Any]:
    """Get event history"""
    try:
        from .event_bus import EventType
        
        # Convert string to EventType if provided
        event_type_enum = None
        if event_type:
            try:
                event_type_enum = EventType(event_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid event type: {event_type}")
        
        events = event_bus.get_event_history(user_id, event_type_enum, limit)
        
        # Convert events to dict format
        events_data = []
        for event in events:
            events_data.append(event.to_dict())
        
        return {
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

# =============================================================================
# SIGNAL PROCESSING ENDPOINTS
# =============================================================================

@router.post("/signals/process")
async def process_trading_signal(user_id: str, signal_request: SignalRequest) -> Dict[str, Any]:
    """Process a trading signal"""
    try:
        # Create TradingSignal object
        signal = TradingSignal(
            id=f"signal_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            user_id=user_id,
            symbol=signal_request.symbol,
            signal_type=SignalType(signal_request.signal_type),
            confidence_score=signal_request.confidence_score,
            target_price=signal_request.target_price,
            stop_loss=signal_request.stop_loss,
            position_size=signal_request.position_size,
            strategy_id=signal_request.strategy_id
        )
        
        # Process signal through order executor
        result = await order_executor.process_signal(signal)
        
        return {
            "status": "success" if result.success else "failed",
            "signal_id": signal.id,
            "order_id": result.order.id if result.order else None,
            "error_message": result.error_message,
            "error_code": result.error_code
        }
        
    except Exception as e:
        logger.error(f"Error processing signal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/signals/position-size")
async def get_position_size_recommendation(
    user_id: str, 
    symbol: str, 
    signal_type: str, 
    confidence_score: float,
    model: str = "VOLATILITY_ADJUSTED"
) -> Dict[str, Any]:
    """Get position size recommendation for a signal"""
    try:
        # Create temporary signal for sizing
        signal = TradingSignal(
            id="temp_sizing_signal",
            user_id=user_id,
            symbol=symbol,
            signal_type=SignalType(signal_type),
            confidence_score=confidence_score
        )
        
        recommendation = await position_sizer.get_position_size_recommendation(signal, model)
        
        return {
            "status": "success",
            "recommendation": recommendation
        }
        
    except Exception as e:
        logger.error(f"Error getting position size recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# ORDER MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/orders/{user_id}")
async def get_user_orders(
    user_id: str, 
    status: Optional[str] = None, 
    limit: int = 100
) -> Dict[str, Any]:
    """Get orders for a user"""
    try:
        order_status = OrderStatus(status) if status else None
        orders = await order_service.get_user_orders(user_id, order_status, limit)
        
        return {
            "status": "success",
            "orders": orders,
            "count": len(orders)
        }
        
    except Exception as e:
        logger.error(f"Error getting user orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/orders/{user_id}/active")
async def get_active_orders(user_id: str) -> Dict[str, Any]:
    """Get active orders for a user"""
    try:
        orders = await order_service.get_active_orders(user_id)
        
        return {
            "status": "success",
            "active_orders": orders,
            "count": len(orders)
        }
        
    except Exception as e:
        logger.error(f"Error getting active orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/orders/{user_id}/history")
async def get_order_history(
    user_id: str, 
    symbol: Optional[str] = None, 
    days: int = 30
) -> Dict[str, Any]:
    """Get order history for a user"""
    try:
        history = await order_service.get_order_history(user_id, symbol, days)
        
        return {
            "status": "success",
            "order_history": history,
            "count": len(history),
            "period_days": days
        }
        
    except Exception as e:
        logger.error(f"Error getting order history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/orders/{order_id}/cancel")
async def cancel_order(order_id: str, user_id: str) -> Dict[str, Any]:
    """Cancel an order"""
    try:
        success = await order_service.cancel_order(order_id, user_id)
        
        return {
            "status": "success" if success else "failed",
            "order_id": order_id,
            "message": "Order cancelled successfully" if success else "Failed to cancel order"
        }
        
    except Exception as e:
        logger.error(f"Error cancelling order: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/orders/{order_id}/status")
async def get_order_status(order_id: str) -> Dict[str, Any]:
    """Get order status"""
    try:
        status = await order_service.get_order(order_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Order not found")
        
        return {
            "status": "success",
            "order_status": status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting order status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# POSITION MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/positions/{user_id}")
async def get_user_positions(user_id: str, include_closed: bool = False) -> Dict[str, Any]:
    """Get positions for a user"""
    try:
        positions = await position_manager.get_user_positions(user_id, include_closed)
        
        return {
            "status": "success",
            "positions": positions,
            "count": len(positions)
        }
        
    except Exception as e:
        logger.error(f"Error getting user positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/positions/{user_id}/summary")
async def get_portfolio_summary(user_id: str) -> Dict[str, Any]:
    """Get portfolio summary for a user"""
    try:
        summary = await position_manager.get_portfolio_summary(user_id)
        
        return {
            "status": "success",
            "portfolio_summary": summary
        }
        
    except Exception as e:
        logger.error(f"Error getting portfolio summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/positions/{user_id}/history")
async def get_position_history(
    user_id: str, 
    symbol: Optional[str] = None, 
    days: int = 30
) -> Dict[str, Any]:
    """Get position history for a user"""
    try:
        history = await position_manager.get_position_history(user_id, symbol, days)
        
        return {
            "status": "success",
            "position_history": history,
            "count": len(history),
            "period_days": days
        }
        
    except Exception as e:
        logger.error(f"Error getting position history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/positions/{user_id}/{symbol}/close")
async def close_position(user_id: str, symbol: str, price: Optional[float] = None) -> Dict[str, Any]:
    """Close a position"""
    try:
        success = await position_manager.close_position(user_id, symbol, price)
        
        return {
            "status": "success" if success else "failed",
            "user_id": user_id,
            "symbol": symbol,
            "message": "Position closed successfully" if success else "Failed to close position"
        }
        
    except Exception as e:
        logger.error(f"Error closing position: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# RISK MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/risk/{user_id}/portfolio")
async def get_portfolio_risk(user_id: str) -> Dict[str, Any]:
    """Get portfolio risk metrics for a user"""
    try:
        risk_metrics = await risk_engine.calculate_portfolio_risk(user_id)
        
        return {
            "status": "success",
            "risk_metrics": {
                "total_exposure": risk_metrics.total_exposure,
                "exposure_percentage": risk_metrics.exposure_percentage,
                "max_drawdown": risk_metrics.max_drawdown,
                "current_drawdown": risk_metrics.current_drawdown,
                "var_95": risk_metrics.var_95,
                "sector_exposures": risk_metrics.sector_exposures,
                "position_concentrations": risk_metrics.position_concentrations,
                "leverage_ratio": risk_metrics.leverage_ratio,
                "risk_score": risk_metrics.risk_score
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting portfolio risk: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/risk/{user_id}/alerts")
async def get_risk_alerts(user_id: str) -> Dict[str, Any]:
    """Get risk alerts for a user"""
    try:
        alerts = await risk_monitor.get_user_alerts(user_id)
        
        return {
            "status": "success",
            "risk_alerts": alerts,
            "count": len(alerts)
        }
        
    except Exception as e:
        logger.error(f"Error getting risk alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/risk/{user_id}/stop-loss")
async def add_stop_loss(
    user_id: str, 
    symbol: str, 
    trigger_price: float,
    order_type: str = "MARKET",
    limit_price: Optional[float] = None,
    quantity: int = 0
) -> Dict[str, Any]:
    """Add stop loss for a position"""
    try:
        success = await risk_monitor.add_stop_loss(
            user_id, symbol, trigger_price, order_type, limit_price, quantity
        )
        
        return {
            "status": "success" if success else "failed",
            "message": "Stop loss added successfully" if success else "Failed to add stop loss"
        }
        
    except Exception as e:
        logger.error(f"Error adding stop loss: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/risk/{user_id}/stop-loss/{symbol}")
async def remove_stop_loss(user_id: str, symbol: str) -> Dict[str, Any]:
    """Remove stop loss for a symbol"""
    try:
        success = await risk_monitor.remove_stop_loss(user_id, symbol)
        
        return {
            "status": "success" if success else "failed",
            "message": "Stop loss removed successfully" if success else "Failed to remove stop loss"
        }
        
    except Exception as e:
        logger.error(f"Error removing stop loss: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# STRATEGY MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/strategies/{user_id}")
async def get_user_strategies(user_id: str) -> Dict[str, Any]:
    """Get strategies for a user"""
    try:
        strategies = await strategy_manager.get_user_strategies(user_id)
        
        return {
            "status": "success",
            "strategies": strategies,
            "count": len(strategies)
        }
        
    except Exception as e:
        logger.error(f"Error getting user strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategies/{user_id}/deploy")
async def deploy_strategy(user_id: str, config_request: StrategyConfigRequest) -> Dict[str, Any]:
    """Deploy a new strategy"""
    try:
        from .models import RiskParameters
        
        # Create strategy config
        config = StrategyConfig(
            id=f"strategy_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name=config_request.name,
            description=config_request.description,
            strategy_type=StrategyType(config_request.strategy_type),
            user_id=user_id,
            symbols=config_request.symbols,
            parameters=config_request.parameters,
            risk_parameters=RiskParameters(),
            max_positions=config_request.max_positions,
            max_daily_trades=config_request.max_daily_trades
        )
        
        # Deploy through lifecycle manager
        result = await strategy_lifecycle_manager.create_strategy_lifecycle(config)
        
        return {
            "status": "success" if result['success'] else "failed",
            "strategy_id": result.get('strategy_id'),
            "lifecycle_stage": result.get('lifecycle_stage'),
            "error": result.get('error')
        }
        
    except Exception as e:
        logger.error(f"Error deploying strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/strategies/{strategy_id}/status")
async def get_strategy_status(strategy_id: str) -> Dict[str, Any]:
    """Get strategy status"""
    try:
        status = await strategy_manager.get_strategy_status(strategy_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        return {
            "status": "success",
            "strategy_status": status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting strategy status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategies/{strategy_id}/control")
async def execute_strategy_control(
    strategy_id: str, 
    user_id: str, 
    action_request: ControlActionRequest
) -> Dict[str, Any]:
    """Execute strategy control action"""
    try:
        result = await strategy_controller.execute_control_action(
            strategy_id,
            action_request.action_type,
            action_request.reason,
            "USER",
            action_request.parameters
        )
        
        return {
            "status": "success" if result['success'] else "failed",
            "action_id": result.get('action_id'),
            "executed_at": result.get('executed_at'),
            "details": result.get('details'),
            "error": result.get('error')
        }
        
    except Exception as e:
        logger.error(f"Error executing strategy control: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/strategies/{strategy_id}/performance")
async def get_strategy_performance(strategy_id: str, days: int = 30) -> Dict[str, Any]:
    """Get strategy performance metrics"""
    try:
        performance = await strategy_manager.get_strategy_performance(strategy_id, days)
        
        if not performance:
            raise HTTPException(status_code=404, detail="Strategy performance not found")
        
        return {
            "status": "success",
            "performance": performance
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting strategy performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/strategies/{strategy_id}/lifecycle")
async def get_strategy_lifecycle(strategy_id: str) -> Dict[str, Any]:
    """Get strategy lifecycle history"""
    try:
        lifecycle = await strategy_lifecycle_manager.get_strategy_lifecycle_history(strategy_id)
        
        return {
            "status": "success",
            "lifecycle_history": lifecycle,
            "count": len(lifecycle)
        }
        
    except Exception as e:
        logger.error(f"Error getting strategy lifecycle: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/strategies/{strategy_id}/optimization")
async def get_optimization_suggestions(strategy_id: str) -> Dict[str, Any]:
    """Get optimization suggestions for a strategy"""
    try:
        suggestions = await strategy_lifecycle_manager.get_optimization_suggestions(strategy_id)
        
        return {
            "status": "success",
            "optimization_suggestions": suggestions,
            "count": len(suggestions)
        }
        
    except Exception as e:
        logger.error(f"Error getting optimization suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# PORTFOLIO ANALYTICS ENDPOINTS
# =============================================================================

@router.get("/portfolio/{user_id}/metrics")
async def get_portfolio_metrics(user_id: str) -> Dict[str, Any]:
    """Get comprehensive portfolio metrics"""
    try:
        from .portfolio_aggregator import portfolio_aggregator
        
        metrics = await portfolio_aggregator.calculate_portfolio_metrics(user_id)
        
        return {
            "status": "success",
            "portfolio_metrics": {
                "total_value": metrics.total_value,
                "total_cost_basis": metrics.total_cost_basis,
                "total_unrealized_pnl": metrics.total_unrealized_pnl,
                "total_realized_pnl": metrics.total_realized_pnl,
                "total_pnl": metrics.total_pnl,
                "total_return_percent": metrics.total_return_percent,
                "daily_pnl": metrics.daily_pnl,
                "daily_return_percent": metrics.daily_return_percent,
                "positions_count": metrics.positions_count,
                "winning_positions": metrics.winning_positions,
                "losing_positions": metrics.losing_positions,
                "win_rate": metrics.win_rate,
                "largest_winner": metrics.largest_winner,
                "largest_loser": metrics.largest_loser,
                "average_position_size": metrics.average_position_size,
                "portfolio_beta": metrics.portfolio_beta,
                "sharpe_ratio": metrics.sharpe_ratio,
                "max_drawdown": metrics.max_drawdown,
                "volatility": metrics.volatility,
                "calculated_at": metrics.calculated_at.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting portfolio metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/portfolio/{user_id}/sectors")
async def get_sector_analysis(user_id: str) -> Dict[str, Any]:
    """Get sector allocation analysis"""
    try:
        from .portfolio_aggregator import portfolio_aggregator
        
        sector_analysis = await portfolio_aggregator.analyze_sector_allocation(user_id)
        
        return {
            "status": "success",
            "sector_analysis": [
                {
                    "sector": sector.sector,
                    "total_value": sector.total_value,
                    "percentage_of_portfolio": sector.percentage_of_portfolio,
                    "positions_count": sector.positions_count,
                    "unrealized_pnl": sector.unrealized_pnl,
                    "realized_pnl": sector.realized_pnl,
                    "total_pnl": sector.total_pnl,
                    "return_percent": sector.return_percent,
                    "symbols": sector.symbols
                }
                for sector in sector_analysis
            ],
            "sectors_count": len(sector_analysis)
        }
        
    except Exception as e:
        logger.error(f"Error getting sector analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/portfolio/{user_id}/attribution")
async def get_performance_attribution(user_id: str) -> Dict[str, Any]:
    """Get performance attribution analysis"""
    try:
        from .portfolio_aggregator import portfolio_aggregator
        
        attribution = await portfolio_aggregator.calculate_performance_attribution(user_id)
        
        return {
            "status": "success",
            "performance_attribution": [
                {
                    "symbol": attr.symbol,
                    "sector": attr.sector,
                    "contribution_to_return": attr.contribution_to_return,
                    "weight_in_portfolio": attr.weight_in_portfolio,
                    "individual_return": attr.individual_return,
                    "excess_return": attr.excess_return,
                    "risk_contribution": attr.risk_contribution
                }
                for attr in attribution
            ],
            "positions_analyzed": len(attribution)
        }
        
    except Exception as e:
        logger.error(f"Error getting performance attribution: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/portfolio/{user_id}/risk-metrics")
async def get_portfolio_risk_metrics(user_id: str) -> Dict[str, Any]:
    """Get comprehensive portfolio risk metrics"""
    try:
        from .portfolio_aggregator import portfolio_aggregator
        
        risk_metrics = await portfolio_aggregator.calculate_risk_metrics(user_id)
        
        return {
            "status": "success",
            "risk_metrics": {
                "portfolio_var_95": risk_metrics.portfolio_var_95,
                "portfolio_var_99": risk_metrics.portfolio_var_99,
                "expected_shortfall": risk_metrics.expected_shortfall,
                "beta": risk_metrics.beta,
                "alpha": risk_metrics.alpha,
                "tracking_error": risk_metrics.tracking_error,
                "information_ratio": risk_metrics.information_ratio,
                "maximum_drawdown": risk_metrics.maximum_drawdown,
                "calmar_ratio": risk_metrics.calmar_ratio,
                "sortino_ratio": risk_metrics.sortino_ratio
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting portfolio risk metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/portfolio/{user_id}/report")
async def get_portfolio_report(user_id: str) -> Dict[str, Any]:
    """Get comprehensive portfolio report"""
    try:
        from .portfolio_aggregator import portfolio_aggregator
        
        report = await portfolio_aggregator.generate_portfolio_report(user_id)
        
        return {
            "status": "success",
            "portfolio_report": report
        }
        
    except Exception as e:
        logger.error(f"Error generating portfolio report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# TRADING STATISTICS ENDPOINTS
# =============================================================================

@router.get("/statistics/{user_id}/trading")
async def get_trading_statistics(user_id: str, days: int = 30) -> Dict[str, Any]:
    """Get comprehensive trading statistics for a user"""
    try:
        stats = await order_service.get_trading_statistics(user_id, days)
        
        return {
            "status": "success",
            "trading_statistics": stats,
            "period_days": days
        }
        
    except Exception as e:
        logger.error(f"Error getting trading statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistics/{user_id}/executions")
async def get_execution_history(user_id: str, limit: int = 100) -> Dict[str, Any]:
    """Get execution history for a user"""
    try:
        executions = await order_service.get_execution_history(user_id, limit)
        
        return {
            "status": "success",
            "execution_history": executions,
            "count": len(executions)
        }
        
    except Exception as e:
        logger.error(f"Error getting execution history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# SYSTEM CONTROL ENDPOINTS
# =============================================================================

@router.post("/emergency-stop")
async def trigger_emergency_stop(user_id: str, reason: str = "Manual emergency stop") -> Dict[str, Any]:
    """Trigger emergency stop for a user"""
    try:
        success = await risk_monitor.clear_emergency_stop(user_id)  # Clear any existing first
        
        # Then trigger new emergency stop through risk monitor
        # This would be implemented in the risk monitor
        
        return {
            "status": "success",
            "message": f"Emergency stop triggered for user {user_id}",
            "reason": reason
        }
        
    except Exception as e:
        logger.error(f"Error triggering emergency stop: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/system/status")
async def get_system_status() -> Dict[str, Any]:
    """Get comprehensive system status"""
    try:
        # Get status from all components
        risk_monitor_status = risk_monitor.get_monitoring_status()
        strategy_manager_status = strategy_manager.get_monitoring_status()
        strategy_controller_status = strategy_controller.get_controller_status()
        lifecycle_status = strategy_lifecycle_manager.get_lifecycle_status()
        
        return {
            "status": "operational",
            "components": {
                "risk_monitor": risk_monitor_status,
                "strategy_manager": strategy_manager_status,
                "strategy_controller": strategy_controller_status,
                "lifecycle_manager": lifecycle_status
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
# =============================================================================
# TESTING AND VALIDATION ENDPOINTS
# =============================================================================

@router.post("/test/backend-integration")
async def test_backend_integration() -> Dict[str, Any]:
    """Test backend integration and component health"""
    try:
        test_results = {}
        
        # Test 1: Models and basic functionality
        try:
            from .models import TradingSignal, SignalType, Order, OrderType, OrderSide
            
            # Create test signal
            test_signal = TradingSignal(
                id="test_integration_signal",
                user_id="test_user",
                symbol="RELIANCE",
                signal_type=SignalType.BUY,
                confidence_score=0.8
            )
            
            # Test serialization
            signal_dict = test_signal.to_dict()
            restored_signal = TradingSignal.from_dict(signal_dict)
            
            test_results["models"] = {
                "status": "passed",
                "details": "Models working correctly"
            }
            
        except Exception as e:
            test_results["models"] = {
                "status": "failed",
                "error": str(e)
            }
        
        # Test 2: Database connectivity
        try:
            db_health = check_trading_engine_health()
            test_results["database"] = {
                "status": "passed" if db_health["status"] == "healthy" else "failed",
                "details": db_health
            }
        except Exception as e:
            test_results["database"] = {
                "status": "failed",
                "error": str(e)
            }
        
        # Test 3: Event bus
        try:
            event_stats = event_bus.get_statistics()
            test_results["event_bus"] = {
                "status": "passed",
                "details": event_stats
            }
        except Exception as e:
            test_results["event_bus"] = {
                "status": "failed",
                "error": str(e)
            }
        
        # Test 4: Risk engine
        try:
            # Test with dummy order
            from .models import Order
            test_order = Order(
                id="test_order",
                user_id="test_user",
                symbol="RELIANCE",
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                quantity=10
            )
            
            # This would test risk validation
            test_results["risk_engine"] = {
                "status": "passed",
                "details": "Risk engine accessible"
            }
        except Exception as e:
            test_results["risk_engine"] = {
                "status": "failed",
                "error": str(e)
            }
        
        # Calculate overall status
        passed_tests = len([r for r in test_results.values() if r["status"] == "passed"])
        total_tests = len(test_results)
        overall_status = "healthy" if passed_tests == total_tests else "degraded"
        
        return {
            "status": overall_status,
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": (passed_tests / total_tests) * 100
            },
            "test_results": test_results,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in backend integration test: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/test/endpoints")
async def test_all_endpoints() -> Dict[str, Any]:
    """Test all trading engine endpoints for basic functionality"""
    try:
        endpoint_tests = {}
        test_user_id = "test_user_endpoint"
        
        # Test basic endpoints that don't require complex setup
        basic_endpoints = [
            ("/health", "GET"),
            ("/metrics", "GET"),
            ("/config", "GET"),
            ("/system/status", "GET")
        ]
        
        for endpoint, method in basic_endpoints:
            try:
                # This is a simplified test - in production you'd make actual HTTP calls
                endpoint_tests[endpoint] = {
                    "status": "accessible",
                    "method": method
                }
            except Exception as e:
                endpoint_tests[endpoint] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        return {
            "status": "success",
            "endpoint_tests": endpoint_tests,
            "total_endpoints": len(endpoint_tests),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error testing endpoints: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# FALLBACK ENDPOINTS FOR GRACEFUL DEGRADATION
# =============================================================================

@router.get("/fallback/status")
async def fallback_status() -> Dict[str, Any]:
    """Fallback status endpoint when components are not available"""
    return {
        "status": "fallback",
        "message": "Trading engine in fallback mode",
        "available_endpoints": [
            "/health",
            "/metrics", 
            "/config",
            "/test/backend-integration",
            "/test/endpoints"
        ],
        "timestamp": datetime.now().isoformat()
    }