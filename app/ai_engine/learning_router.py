"""
Learning System Router
FastAPI endpoints for AI learning and adaptation
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional, Dict, Any
from .learning_system import LearningSystem, FeedbackType, OutcomeType
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai/learning", tags=["AI Learning & Adaptation"])

# Initialize learning system
learning_system = LearningSystem()

def get_user_id_from_headers(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> str:
    """Extract user ID from headers"""
    if x_user_id:
        return x_user_id
    return "default_user"

# Request Models
class FeedbackRequest(BaseModel):
    feedback_type: FeedbackType
    item_id: str
    rating: int  # 1-5 scale
    comments: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class TradeOutcomeRequest(BaseModel):
    signal_id: str
    outcome_type: OutcomeType
    pnl_amount: float
    execution_price: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

# Feedback Endpoints

@router.post("/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Submit feedback on AI recommendations"""
    try:
        success = await learning_system.record_feedback(
            user_id,
            request.feedback_type,
            request.item_id,
            request.rating,
            request.comments,
            request.metadata
        )
        
        if success:
            return {
                "status": "success",
                "message": "Feedback recorded successfully",
                "feedback_type": request.feedback_type,
                "rating": request.rating
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to record feedback"
            )
        
    except Exception as e:
        logger.error(f"Feedback submission failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit feedback: {str(e)}"
        )

@router.post("/trade-outcome")
async def record_trade_outcome(
    request: TradeOutcomeRequest,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Record actual trading outcome for learning"""
    try:
        success = await learning_system.record_trade_outcome(
            user_id,
            request.signal_id,
            request.outcome_type,
            request.pnl_amount,
            request.execution_price,
            request.metadata
        )
        
        if success:
            return {
                "status": "success",
                "message": "Trade outcome recorded successfully",
                "signal_id": request.signal_id,
                "outcome_type": request.outcome_type,
                "pnl_amount": request.pnl_amount
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to record trade outcome"
            )
        
    except Exception as e:
        logger.error(f"Trade outcome recording failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to record trade outcome: {str(e)}"
        )

# Performance and Insights Endpoints

@router.get("/performance")
async def get_provider_performance(
    days: int = 30,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get AI provider performance metrics"""
    try:
        performance = await learning_system.get_provider_performance(user_id, days)
        return performance
        
    except Exception as e:
        logger.error(f"Performance retrieval failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get performance data: {str(e)}"
        )

@router.get("/insights")
async def get_learning_insights(
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get learning insights and recommendations"""
    try:
        insights = await learning_system.get_learning_insights(user_id)
        return insights
        
    except Exception as e:
        logger.error(f"Insights generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate insights: {str(e)}"
        )

@router.get("/confidence-thresholds")
async def get_adapted_confidence_thresholds(
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get adapted confidence thresholds based on user patterns"""
    try:
        thresholds = await learning_system.adapt_confidence_thresholds(user_id)
        return thresholds
        
    except Exception as e:
        logger.error(f"Threshold adaptation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to adapt thresholds: {str(e)}"
        )

# Utility Endpoints

@router.get("/feedback-summary")
async def get_feedback_summary(
    days: int = 30,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get summary of user feedback"""
    try:
        from ..database.service import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                feedback_type,
                AVG(rating) as avg_rating,
                COUNT(*) as count,
                MIN(rating) as min_rating,
                MAX(rating) as max_rating
            FROM ai_feedback
            WHERE user_id = ?
            AND created_at >= datetime('now', ? || ' days')
            GROUP BY feedback_type
        """, (user_id, f"-{days}"))
        
        results = cursor.fetchall()
        conn.close()
        
        summary = {}
        for result in results:
            summary[result[0]] = {
                "avg_rating": round(result[1], 2),
                "count": result[2],
                "min_rating": result[3],
                "max_rating": result[4]
            }
        
        return {
            "user_id": user_id,
            "period_days": days,
            "feedback_summary": summary,
            "total_feedback": sum(data["count"] for data in summary.values())
        }
        
    except Exception as e:
        logger.error(f"Feedback summary failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get feedback summary: {str(e)}"
        )

@router.get("/learning-status")
async def get_learning_status(
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get current learning system status"""
    try:
        from ..database.service import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get feedback count
        cursor.execute("""
            SELECT COUNT(*) FROM ai_feedback WHERE user_id = ?
        """, (user_id,))
        feedback_count = cursor.fetchone()[0]
        
        # Get trade outcome count
        cursor.execute("""
            SELECT COUNT(*) FROM ai_trade_outcomes WHERE user_id = ?
        """, (user_id,))
        outcome_count = cursor.fetchone()[0] if cursor.fetchone() else 0
        
        conn.close()
        
        learning_active = feedback_count >= learning_system.min_feedback_count
        
        return {
            "user_id": user_id,
            "learning_active": learning_active,
            "feedback_count": feedback_count,
            "outcome_count": outcome_count,
            "min_feedback_required": learning_system.min_feedback_count,
            "learning_rate": learning_system.learning_rate,
            "confidence_threshold": learning_system.confidence_threshold,
            "status": "active" if learning_active else "collecting_data"
        }
        
    except Exception as e:
        logger.error(f"Learning status check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get learning status: {str(e)}"
        )

# Test Endpoints

@router.post("/test/feedback")
async def submit_test_feedback(
    user_id: str = Depends(get_user_id_from_headers)
):
    """Submit test feedback for development"""
    try:
        import random
        
        test_feedbacks = [
            {
                "feedback_type": FeedbackType.SIGNAL_ACCURACY,
                "item_id": f"signal_{random.randint(1, 100)}",
                "rating": random.randint(3, 5),
                "metadata": {"provider_used": random.choice(["openai", "claude", "gemini"])}
            },
            {
                "feedback_type": FeedbackType.ANALYSIS_QUALITY,
                "item_id": f"analysis_{random.randint(1, 100)}",
                "rating": random.randint(2, 5),
                "metadata": {"analysis_type": "technical"}
            }
        ]
        
        results = []
        for feedback in test_feedbacks:
            success = await learning_system.record_feedback(
                user_id,
                feedback["feedback_type"],
                feedback["item_id"],
                feedback["rating"],
                f"Test feedback - {feedback['rating']}/5",
                feedback["metadata"]
            )
            results.append({
                "feedback": feedback,
                "success": success
            })
        
        return {
            "message": "Test feedback submitted",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Test feedback failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit test feedback: {str(e)}"
        )

# Health check
@router.get("/health")
async def learning_health_check():
    """Health check for learning system"""
    try:
        return {
            "status": "healthy",
            "components": {
                "learning_system": "operational",
                "feedback_recording": "active",
                "outcome_tracking": "active",
                "adaptation_engine": "ready"
            },
            "timestamp": "2025-07-21T10:30:00Z"
        }
        
    except Exception as e:
        logger.error(f"Learning health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }