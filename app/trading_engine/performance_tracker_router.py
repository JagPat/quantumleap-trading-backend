"""
Performance Tracker Router
API endpoints for strategy performance tracking and analysis
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from .performance_tracker import performance_tracker
from .monitoring import trading_monitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/performance", tags=["Performance Tracking"])

@router.get("/strategy/{strategy_id}")
async def get_strategy_performance(
    strategy_id: str,
    user_id: str = Query(..., description="User ID"),
    period_days: int = Query(30, description="Analysis period in days", ge=1, le=365)
) -> Dict[str, Any]:
    """
    Get comprehensive performance metrics for a strategy
    
    Args:
        strategy_id: Strategy ID to analyze
        user_id: User ID
        period_days: Period to analyze (1-365 days)
        
    Returns:
        Comprehensive performance metrics
    """
    try:
        logger.info(f"Getting performance for strategy {strategy_id}, user {user_id}, period {period_days} days")
        
        performance_data = await performance_tracker.get_strategy_performance(
            strategy_id, user_id, period_days
        )
        
        if not performance_data:
            raise HTTPException(
                status_code=404,
                detail=f"No performance data found for strategy {strategy_id}"
            )
        
        trading_monitor.increment_counter("performance_api_requests")
        
        return {
            "success": True,
            "strategy_id": strategy_id,
            "user_id": user_id,
            "period_days": period_days,
            "performance": performance_data,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting strategy performance: {e}")
        trading_monitor.increment_counter("performance_api_errors")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/strategy/{strategy_id}/summary")
async def get_performance_summary(
    strategy_id: str,
    user_id: str = Query(..., description="User ID")
) -> Dict[str, Any]:
    """
    Get performance summary with key metrics
    
    Args:
        strategy_id: Strategy ID
        user_id: User ID
        
    Returns:
        Performance summary with key metrics
    """
    try:
        performance_data = await performance_tracker.get_strategy_performance(
            strategy_id, user_id, period_days=30
        )
        
        if not performance_data:
            raise HTTPException(
                status_code=404,
                detail=f"No performance data found for strategy {strategy_id}"
            )
        
        # Extract key metrics for summary
        summary = {
            "strategy_id": strategy_id,
            "total_trades": performance_data.get("total_trades", 0),
            "win_rate": performance_data.get("win_rate", 0),
            "total_pnl": performance_data.get("total_pnl", 0),
            "max_drawdown_percent": performance_data.get("max_drawdown_percent", 0),
            "sharpe_ratio": performance_data.get("sharpe_ratio", 0),
            "profit_factor": performance_data.get("profit_factor", 0),
            "current_win_streak": performance_data.get("current_win_streak", 0),
            "current_loss_streak": performance_data.get("current_loss_streak", 0),
            "best_trade": performance_data.get("best_trade", 0),
            "worst_trade": performance_data.get("worst_trade", 0),
            "performance_status": _get_performance_status(performance_data),
            "last_updated": performance_data.get("calculated_at")
        }
        
        return {
            "success": True,
            "summary": summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/strategy/{strategy_id}/alerts")
async def get_performance_alerts(
    strategy_id: str,
    user_id: str = Query(..., description="User ID"),
    include_acknowledged: bool = Query(False, description="Include acknowledged alerts")
) -> Dict[str, Any]:
    """
    Get performance alerts for a strategy
    
    Args:
        strategy_id: Strategy ID
        user_id: User ID
        include_acknowledged: Whether to include acknowledged alerts
        
    Returns:
        List of performance alerts
    """
    try:
        alerts = await performance_tracker.get_performance_alerts(strategy_id)
        
        if not include_acknowledged:
            alerts = [alert for alert in alerts if not alert.get("acknowledged", False)]
        
        # Categorize alerts by severity
        alert_summary = {
            "critical": [a for a in alerts if a.get("severity") == "CRITICAL"],
            "high": [a for a in alerts if a.get("severity") == "HIGH"],
            "medium": [a for a in alerts if a.get("severity") == "MEDIUM"],
            "low": [a for a in alerts if a.get("severity") == "LOW"]
        }
        
        return {
            "success": True,
            "strategy_id": strategy_id,
            "total_alerts": len(alerts),
            "alerts": alerts,
            "alert_summary": alert_summary,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting performance alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategy/{strategy_id}/alerts/{alert_id}/acknowledge")
async def acknowledge_performance_alert(
    strategy_id: str,
    alert_id: str,
    user_id: str = Query(..., description="User ID")
) -> Dict[str, Any]:
    """
    Acknowledge a performance alert
    
    Args:
        strategy_id: Strategy ID
        alert_id: Alert ID to acknowledge
        user_id: User ID
        
    Returns:
        Acknowledgment result
    """
    try:
        success = await performance_tracker.acknowledge_alert(alert_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Alert {alert_id} not found"
            )
        
        return {
            "success": True,
            "alert_id": alert_id,
            "acknowledged_at": datetime.now().isoformat(),
            "acknowledged_by": user_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategy/{strategy_id}/backtest-comparison")
async def compare_with_backtest(
    strategy_id: str,
    user_id: str = Query(..., description="User ID"),
    backtest_results: Dict[str, Any] = Body(..., description="Backtest results to compare against")
) -> Dict[str, Any]:
    """
    Compare live performance with backtest results
    
    Args:
        strategy_id: Strategy ID
        user_id: User ID
        backtest_results: Backtest results for comparison
        
    Returns:
        Comparison analysis
    """
    try:
        # Validate backtest results format
        required_fields = ["win_rate", "sharpe_ratio", "max_drawdown", "profit_factor"]
        missing_fields = [field for field in required_fields if field not in backtest_results]
        
        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required backtest fields: {missing_fields}"
            )
        
        comparison = await performance_tracker.compare_with_backtest(
            strategy_id, backtest_results
        )
        
        if "error" in comparison:
            raise HTTPException(status_code=400, detail=comparison["error"])
        
        return {
            "success": True,
            "strategy_id": strategy_id,
            "comparison": comparison,
            "compared_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing with backtest: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/strategy/{strategy_id}/trades")
async def get_strategy_trades(
    strategy_id: str,
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(100, description="Maximum number of trades to return", ge=1, le=1000),
    offset: int = Query(0, description="Number of trades to skip", ge=0)
) -> Dict[str, Any]:
    """
    Get trade history for a strategy
    
    Args:
        strategy_id: Strategy ID
        user_id: User ID
        limit: Maximum number of trades to return
        offset: Number of trades to skip
        
    Returns:
        Trade history with performance metrics
    """
    try:
        # Get trade history from performance tracker
        if strategy_id not in performance_tracker.trade_history:
            return {
                "success": True,
                "strategy_id": strategy_id,
                "trades": [],
                "total_trades": 0,
                "limit": limit,
                "offset": offset
            }
        
        all_trades = performance_tracker.trade_history[strategy_id]
        
        # Apply pagination
        total_trades = len(all_trades)
        trades = all_trades[offset:offset + limit]
        
        # Convert to dictionaries
        trade_data = [trade.to_dict() for trade in trades]
        
        # Add summary statistics
        if trades:
            winning_trades = [t for t in trades if t.is_winner]
            losing_trades = [t for t in trades if not t.is_winner]
            
            summary = {
                "total_trades": len(trades),
                "winning_trades": len(winning_trades),
                "losing_trades": len(losing_trades),
                "win_rate": len(winning_trades) / len(trades) * 100,
                "total_pnl": sum(t.pnl for t in trades),
                "avg_pnl": sum(t.pnl for t in trades) / len(trades),
                "best_trade": max(t.pnl for t in trades),
                "worst_trade": min(t.pnl for t in trades),
                "avg_holding_period_hours": sum(t.holding_period_hours for t in trades) / len(trades)
            }
        else:
            summary = {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "avg_pnl": 0,
                "best_trade": 0,
                "worst_trade": 0,
                "avg_holding_period_hours": 0
            }
        
        return {
            "success": True,
            "strategy_id": strategy_id,
            "trades": trade_data,
            "total_trades": total_trades,
            "returned_trades": len(trades),
            "limit": limit,
            "offset": offset,
            "summary": summary,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting strategy trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/{user_id}/strategies")
async def get_user_performance_overview(
    user_id: str,
    period_days: int = Query(30, description="Analysis period in days", ge=1, le=365)
) -> Dict[str, Any]:
    """
    Get performance overview for all user strategies
    
    Args:
        user_id: User ID
        period_days: Analysis period in days
        
    Returns:
        Performance overview for all strategies
    """
    try:
        # This would typically get all strategies for the user
        # For now, we'll return cached performance data
        
        user_strategies = []
        total_pnl = 0
        total_trades = 0
        
        for strategy_id, metrics in performance_tracker.performance_cache.items():
            if metrics.user_id == user_id:
                strategy_summary = {
                    "strategy_id": strategy_id,
                    "total_trades": metrics.total_trades,
                    "win_rate": metrics.win_rate,
                    "total_pnl": metrics.total_pnl,
                    "max_drawdown_percent": metrics.max_drawdown_percent,
                    "sharpe_ratio": metrics.sharpe_ratio,
                    "profit_factor": metrics.profit_factor,
                    "performance_status": _get_performance_status(metrics.to_dict()),
                    "last_updated": metrics.calculated_at.isoformat()
                }
                
                user_strategies.append(strategy_summary)
                total_pnl += metrics.total_pnl
                total_trades += metrics.total_trades
        
        # Calculate portfolio-level metrics
        portfolio_summary = {
            "total_strategies": len(user_strategies),
            "total_trades": total_trades,
            "total_pnl": total_pnl,
            "profitable_strategies": len([s for s in user_strategies if s["total_pnl"] > 0]),
            "avg_win_rate": sum(s["win_rate"] for s in user_strategies) / len(user_strategies) if user_strategies else 0,
            "best_performing_strategy": max(user_strategies, key=lambda x: x["total_pnl"]) if user_strategies else None,
            "worst_performing_strategy": min(user_strategies, key=lambda x: x["total_pnl"]) if user_strategies else None
        }
        
        return {
            "success": True,
            "user_id": user_id,
            "period_days": period_days,
            "portfolio_summary": portfolio_summary,
            "strategies": user_strategies,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting user performance overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/strategy/{strategy_id}/benchmark-comparison")
async def get_benchmark_comparison(
    strategy_id: str,
    user_id: str = Query(..., description="User ID"),
    benchmark: str = Query("NIFTY50", description="Benchmark to compare against")
) -> Dict[str, Any]:
    """
    Compare strategy performance against benchmark
    
    Args:
        strategy_id: Strategy ID
        user_id: User ID
        benchmark: Benchmark to compare against
        
    Returns:
        Benchmark comparison analysis
    """
    try:
        if strategy_id not in performance_tracker.performance_cache:
            raise HTTPException(
                status_code=404,
                detail=f"No performance data found for strategy {strategy_id}"
            )
        
        metrics = performance_tracker.performance_cache[strategy_id]
        
        # This is a simplified benchmark comparison
        # In production, you would fetch actual benchmark data
        benchmark_data = {
            "NIFTY50": {"annual_return": 12.0, "volatility": 18.0, "sharpe_ratio": 0.6},
            "SENSEX": {"annual_return": 11.5, "volatility": 19.0, "sharpe_ratio": 0.55},
            "SP500": {"annual_return": 10.0, "volatility": 16.0, "sharpe_ratio": 0.65}
        }
        
        if benchmark not in benchmark_data:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported benchmark: {benchmark}"
            )
        
        bench_data = benchmark_data[benchmark]
        
        # Calculate comparison metrics
        period_days = (metrics.period_end - metrics.period_start).days
        annualized_return = metrics.total_pnl / metrics.total_trades * 365 / period_days if metrics.total_trades > 0 and period_days > 0 else 0
        
        comparison = {
            "strategy_id": strategy_id,
            "benchmark": benchmark,
            "comparison_period_days": period_days,
            "strategy_metrics": {
                "annualized_return": annualized_return,
                "volatility": metrics.volatility,
                "sharpe_ratio": metrics.sharpe_ratio,
                "max_drawdown": metrics.max_drawdown_percent
            },
            "benchmark_metrics": bench_data,
            "relative_performance": {
                "excess_return": annualized_return - bench_data["annual_return"],
                "volatility_difference": metrics.volatility - bench_data["volatility"],
                "sharpe_difference": metrics.sharpe_ratio - bench_data["sharpe_ratio"],
                "information_ratio": metrics.information_ratio or 0
            },
            "performance_attribution": {
                "alpha": metrics.alpha or 0,
                "beta": metrics.beta or 1.0,
                "tracking_error": abs(annualized_return - bench_data["annual_return"])
            }
        }
        
        return {
            "success": True,
            "comparison": comparison,
            "compared_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting benchmark comparison: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def get_performance_tracker_health() -> Dict[str, Any]:
    """
    Get performance tracker system health
    
    Returns:
        System health information
    """
    try:
        health_info = {
            "status": "healthy",
            "cached_strategies": len(performance_tracker.performance_cache),
            "active_alerts": sum(len(alerts) for alerts in performance_tracker.active_alerts.values()),
            "monitoring_active": performance_tracker.monitoring_active,
            "last_health_check": datetime.now().isoformat()
        }
        
        return {
            "success": True,
            "health": health_info
        }
        
    except Exception as e:
        logger.error(f"Error getting performance tracker health: {e}")
        return {
            "success": False,
            "error": str(e),
            "status": "unhealthy"
        }

def _get_performance_status(performance_data: Dict[str, Any]) -> str:
    """Get overall performance status"""
    try:
        win_rate = performance_data.get("win_rate", 0)
        sharpe_ratio = performance_data.get("sharpe_ratio", 0)
        max_drawdown = performance_data.get("max_drawdown_percent", 0)
        total_pnl = performance_data.get("total_pnl", 0)
        
        # Define performance criteria
        if (win_rate >= 60 and sharpe_ratio >= 1.0 and max_drawdown <= 10 and total_pnl > 0):
            return "EXCELLENT"
        elif (win_rate >= 50 and sharpe_ratio >= 0.7 and max_drawdown <= 15 and total_pnl > 0):
            return "GOOD"
        elif (win_rate >= 40 and sharpe_ratio >= 0.5 and max_drawdown <= 20):
            return "AVERAGE"
        elif (win_rate >= 30 and max_drawdown <= 25):
            return "BELOW_AVERAGE"
        else:
            return "POOR"
            
    except Exception as e:
        logger.error(f"Error getting performance status: {e}")
        return "UNKNOWN"