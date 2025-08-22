"""
Signal Router
FastAPI endpoints for AI-powered trading signal generation and management
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from .models import TradingSignal, SignalType, AnalysisResponse
from .signal_notifier import SignalNotifier, NotificationType
from .signal_generator import SignalGenerator
from .signal_notifier import SignalNotifier, NotificationType
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai/signals", tags=["AI Signals"])

# Initialize signal components
signal_notifier = SignalNotifier()
signal_generator = SignalGenerator()

# Initialize signal notifier
signal_notifier = SignalNotifier()

def get_user_id_from_headers(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> str:
    """Extract user ID from headers"""
    if x_user_id:
        return x_user_id
    return "default_user"

@router.get("/")
async def get_current_signals(
    symbols: Optional[List[str]] = None,
    signal_type: Optional[str] = None,
    min_confidence: float = 0.5,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get current trading signals for the user"""
    try:
        # Get signals from the database
        signals = await signal_generator.get_user_signals(
            user_id,
            active_only=True,
            symbol=symbols[0] if symbols and len(symbols) == 1 else None,
            signal_type=signal_type
        )
        
        # Filter by confidence
        filtered_signals = [
            signal for signal in signals
            if signal.get("confidence_score", 0) >= min_confidence
        ]
        
        # Filter by symbols if multiple
        if symbols and len(symbols) > 1:
            filtered_signals = [
                signal for signal in filtered_signals
                if signal.get("symbol") in symbols
            ]
        
        return {
            "status": "success",
            "signals": filtered_signals,
            "total_count": len(filtered_signals),
            "filters_applied": {
                "symbols": symbols,
                "signal_type": signal_type,
                "min_confidence": min_confidence
            },
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get current signals: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve signals: {str(e)}"
        )

@router.post("/generate")
async def generate_signals(
    request: Dict[str, Any],
    user_id: str = Depends(get_user_id_from_headers)
):
    """Generate trading signals on-demand"""
    try:
        symbols = request.get("symbols", ["RELIANCE", "TCS", "HDFCBANK"])
        analysis_types = request.get("analysis_types", ["technical", "fundamental", "sentiment"])
        timeframe = request.get("timeframe", "1d")
        
        # Validate symbols
        if not symbols or len(symbols) == 0:
            raise HTTPException(
                status_code=400,
                detail="At least one symbol is required"
            )
        
        # Limit symbols to prevent timeout
        if len(symbols) > 10:
            symbols = symbols[:10]
        
        # Generate signals using the signal generator
        generation_result = await signal_generator.generate_trading_signals(
            user_id,
            symbols,
            analysis_types,
            timeframe
        )
        
        # Check if generation was successful
        if generation_result.get("status") != "success":
            raise HTTPException(
                status_code=500,
                detail=generation_result.get("message", "Signal generation failed")
            )
        
        # Send notifications for high-confidence signals
        for signal in generation_result.get("signals", []):
            if signal.get("confidence_score", 0) >= 0.7:
                await signal_notifier.send_signal_notification(
                    user_id,
                    signal,
                    [NotificationType.IN_APP]
                )
        
        return generation_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate signals: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate signals: {str(e)}"
        )

@router.get("/history")
async def get_signal_history(
    days: int = 7,
    symbol: Optional[str] = None,
    signal_type: Optional[str] = None,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get signal performance history"""
    try:
        # Mock signal history - in production, would query database
        import random
        
        history_signals = []
        test_symbols = [symbol] if symbol else ["RELIANCE", "TCS", "HDFCBANK", "INFY"]
        
        for i in range(min(days * 2, 20)):  # Generate up to 20 historical signals
            symbol_choice = random.choice(test_symbols)
            signal_type_choice = random.choice(["buy", "sell", "hold"])
            
            # Filter by signal type if specified
            if signal_type and signal_type_choice != signal_type:
                continue
            
            # Generate random outcome
            outcome = random.choice(["profitable", "loss", "breakeven"])
            actual_return = 0
            
            if outcome == "profitable":
                actual_return = round(random.uniform(1, 15), 2)
            elif outcome == "loss":
                actual_return = round(random.uniform(-8, -0.5), 2)
            else:
                actual_return = round(random.uniform(-0.5, 0.5), 2)
            
            historical_signal = {
                "id": f"hist_{symbol_choice}_{i}",
                "symbol": symbol_choice,
                "signal_type": signal_type_choice,
                "confidence_score": round(random.uniform(0.4, 0.9), 2),
                "target_price": round(random.uniform(100, 3000), 2),
                "actual_return": actual_return,
                "outcome": outcome,
                "created_at": (datetime.now() - timedelta(days=random.randint(1, days))).isoformat(),
                "closed_at": (datetime.now() - timedelta(days=random.randint(0, days-1))).isoformat()
            }
            
            history_signals.append(historical_signal)
        
        # Calculate performance metrics
        profitable_signals = [s for s in history_signals if s["outcome"] == "profitable"]
        loss_signals = [s for s in history_signals if s["outcome"] == "loss"]
        
        performance_metrics = {
            "total_signals": len(history_signals),
            "profitable_signals": len(profitable_signals),
            "loss_signals": len(loss_signals),
            "win_rate": round((len(profitable_signals) / len(history_signals) * 100), 2) if history_signals else 0,
            "avg_return": round(sum(s["actual_return"] for s in history_signals) / len(history_signals), 2) if history_signals else 0,
            "best_signal": max(history_signals, key=lambda x: x["actual_return"])["actual_return"] if history_signals else 0,
            "worst_signal": min(history_signals, key=lambda x: x["actual_return"])["actual_return"] if history_signals else 0
        }
        
        return {
            "status": "success",
            "signals": sorted(history_signals, key=lambda x: x["created_at"], reverse=True),
            "performance_metrics": performance_metrics,
            "period_days": days,
            "filters": {
                "symbol": symbol,
                "signal_type": signal_type
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get signal history: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve signal history: {str(e)}"
        )

@router.post("/{signal_id}/feedback")
async def submit_signal_feedback(
    signal_id: str,
    feedback: Dict[str, Any],
    user_id: str = Depends(get_user_id_from_headers)
):
    """Submit feedback on signal outcome for performance tracking"""
    try:
        # Validate feedback data
        required_fields = ["outcome", "actual_return"]
        missing_fields = [field for field in required_fields if field not in feedback]
        
        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required fields: {missing_fields}"
            )
        
        outcome = feedback.get("outcome")
        actual_return = feedback.get("actual_return")
        notes = feedback.get("notes", "")
        
        # Validate outcome
        valid_outcomes = ["profitable", "loss", "breakeven", "not_executed"]
        if outcome not in valid_outcomes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid outcome. Must be one of: {valid_outcomes}"
            )
        
        # In production, this would update the database
        feedback_record = {
            "signal_id": signal_id,
            "user_id": user_id,
            "outcome": outcome,
            "actual_return": actual_return,
            "notes": notes,
            "feedback_date": datetime.now().isoformat()
        }
        
        logger.info(f"Signal feedback recorded: {feedback_record}")
        
        return {
            "status": "success",
            "message": "Feedback recorded successfully",
            "feedback_id": f"feedback_{signal_id}_{int(datetime.now().timestamp())}",
            "signal_id": signal_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit feedback for signal {signal_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to record feedback: {str(e)}"
        )

@router.get("/performance")
async def get_signal_performance(
    period_days: int = 30,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get overall signal performance analytics"""
    try:
        # Mock performance data - in production, would calculate from actual data
        import random
        
        performance_data = {
            "period_days": period_days,
            "total_signals_generated": random.randint(50, 200),
            "signals_with_feedback": random.randint(30, 150),
            "overall_metrics": {
                "win_rate": round(random.uniform(55, 75), 2),
                "avg_return": round(random.uniform(2, 8), 2),
                "total_return": round(random.uniform(15, 45), 2),
                "sharpe_ratio": round(random.uniform(0.8, 2.2), 2),
                "max_drawdown": round(random.uniform(5, 15), 2)
            },
            "by_signal_type": {
                "buy": {
                    "count": random.randint(20, 80),
                    "win_rate": round(random.uniform(60, 80), 2),
                    "avg_return": round(random.uniform(3, 10), 2)
                },
                "sell": {
                    "count": random.randint(10, 40),
                    "win_rate": round(random.uniform(50, 70), 2),
                    "avg_return": round(random.uniform(1, 6), 2)
                },
                "hold": {
                    "count": random.randint(5, 20),
                    "accuracy": round(random.uniform(70, 90), 2)
                }
            },
            "top_performing_symbols": [
                {"symbol": "TCS", "win_rate": 78.5, "avg_return": 6.2},
                {"symbol": "HDFCBANK", "win_rate": 72.1, "avg_return": 5.8},
                {"symbol": "RELIANCE", "win_rate": 68.9, "avg_return": 4.9}
            ],
            "last_updated": datetime.now().isoformat()
        }
        
        return {
            "status": "success",
            "performance": performance_data
        }
        
    except Exception as e:
        logger.error(f"Failed to get signal performance: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve performance data: {str(e)}"
        )

@router.get("/health")
async def signal_health_check():
    """Health check for signal system"""
    try:
        return {
            "status": "healthy",
            "components": {
                "signal_generator": "operational",
                "signal_database": "connected",
                "api_endpoints": "ready"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Signal health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }# Not
ification Endpoints

@router.post("/{signal_id}/notify")
async def send_signal_notification(
    signal_id: str,
    notification_request: Dict[str, Any],
    user_id: str = Depends(get_user_id_from_headers)
):
    """Send notification for a specific signal"""
    try:
        # Get notification types
        notification_types_str = notification_request.get("notification_types", ["in_app"])
        notification_types = [NotificationType(t) for t in notification_types_str]
        
        # Get signal data (mock for now)
        # In production, this would fetch from database
        signal = {
            "id": signal_id,
            "symbol": notification_request.get("symbol", "UNKNOWN"),
            "signal_type": notification_request.get("signal_type", "buy"),
            "confidence_score": notification_request.get("confidence_score", 0.7),
            "target_price": notification_request.get("target_price", 1000.0),
            "created_at": datetime.now().isoformat()
        }
        
        # Send notification
        notification_result = await signal_notifier.send_signal_notification(
            user_id,
            signal,
            notification_types
        )
        
        return notification_result
        
    except Exception as e:
        logger.error(f"Failed to send notification for signal {signal_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send notification: {str(e)}"
        )

@router.get("/notifications")
async def get_user_notifications(
    unread_only: bool = False,
    limit: int = 50,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get user's signal notifications"""
    try:
        notifications = await signal_notifier.get_user_notifications(
            user_id,
            limit,
            unread_only
        )
        
        return {
            "status": "success",
            "notifications": notifications,
            "total_count": len(notifications),
            "unread_count": len([n for n in notifications if not n.get("read", False)])
        }
        
    except Exception as e:
        logger.error(f"Failed to get notifications: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve notifications: {str(e)}"
        )

@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Mark notification as read"""
    try:
        success = await signal_notifier.mark_notification_read(
            user_id,
            notification_id
        )
        
        if success:
            return {
                "status": "success",
                "message": "Notification marked as read",
                "notification_id": notification_id
            }
        else:
            raise HTTPException(
                status_code=404,
                detail="Notification not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to mark notification as read: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update notification: {str(e)}"
        )

@router.get("/notifications/preferences")
async def get_notification_preferences(
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get user's notification preferences"""
    try:
        preferences = await signal_notifier.get_user_notification_preferences(user_id)
        
        return {
            "status": "success",
            "preferences": preferences
        }
        
    except Exception as e:
        logger.error(f"Failed to get notification preferences: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve preferences: {str(e)}"
        )

@router.put("/notifications/preferences")
async def update_notification_preferences(
    preferences: Dict[str, Any],
    user_id: str = Depends(get_user_id_from_headers)
):
    """Update user's notification preferences"""
    try:
        # In production, this would update the database
        # For now, just return success
        
        return {
            "status": "success",
            "message": "Notification preferences updated",
            "preferences": preferences
        }
        
    except Exception as e:
        logger.error(f"Failed to update notification preferences: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update preferences: {str(e)}"
        )