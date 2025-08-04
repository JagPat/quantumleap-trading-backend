"""
AI Cost Tracking Router
Handles AI usage cost tracking and budget management
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import logging

# Import authentication
try:
    from app.core.auth import get_current_user_id
    AUTH_AVAILABLE = True
except ImportError:
    async def get_current_user_id():
        return "dev_user_123"
    AUTH_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Cost Tracking"])

# Models
class CostTrackingResponse(BaseModel):
    current_month: Dict[str, Any]
    breakdown: Dict[str, Dict[str, Any]]
    usage_analytics: Dict[str, Any]
    budget_status: Dict[str, Any]
    alerts: List[Dict[str, Any]]

class BudgetSettings(BaseModel):
    monthly_budget: float = Field(..., ge=0)
    alert_thresholds: Dict[str, float] = Field(default={"warning": 80, "critical": 95})
    auto_stop_enabled: bool = False

@router.get("/cost-tracking", response_model=CostTrackingResponse)
async def get_cost_tracking(user_id: str = Depends(get_current_user_id)):
    """
    Get AI usage cost tracking and budget information
    Requires authentication: JWT token in Authorization header
    """
    try:
        logger.info(f"Cost tracking request from user: {user_id}")
        
        # Mock cost tracking data
        current_month = {
            "total_cost": 45.67,
            "budget": 100.00,
            "usage_percentage": 45.67,
            "days_remaining": 12,
            "projected_cost": 78.50
        }
        
        breakdown = {
            "openai": {
                "cost": 28.50,
                "requests": 1250,
                "tokens": 125000,
                "percentage": 62.4
            },
            "anthropic": {
                "cost": 12.30,
                "requests": 450,
                "tokens": 45000,
                "percentage": 26.9
            },
            "google": {
                "cost": 4.87,
                "requests": 200,
                "tokens": 20000,
                "percentage": 10.7
            }
        }
        
        usage_analytics = {
            "daily_average": 2.28,
            "peak_usage_day": "2025-01-02",
            "peak_cost": 5.67,
            "most_used_service": "openai",
            "efficiency_score": 8.2
        }
        
        budget_status = {
            "status": "on_track",
            "budget_remaining": 54.33,
            "days_until_reset": 12,
            "projected_overage": 0.00
        }
        
        alerts = [
            {
                "type": "info",
                "message": "You're on track to stay within budget this month",
                "timestamp": datetime.now().isoformat()
            }
        ]
        
        return CostTrackingResponse(
            current_month=current_month,
            breakdown=breakdown,
            usage_analytics=usage_analytics,
            budget_status=budget_status,
            alerts=alerts
        )
        
    except Exception as e:
        logger.error(f"Cost tracking error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cost tracking failed: {str(e)}")

@router.post("/cost-tracking/budget")
async def update_budget_settings(
    settings: BudgetSettings, 
    user_id: str = Depends(get_current_user_id)
):
    """
    Update AI cost budget settings
    Requires authentication: JWT token in Authorization header
    """
    try:
        logger.info(f"Budget settings update from user: {user_id}")
        
        # Mock budget update
        return {
            "status": "success",
            "message": "Budget settings updated successfully",
            "settings": settings.dict(),
            "user_id": user_id,
            "updated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Budget settings update error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Budget update failed: {str(e)}")

# Add this router to the main AI components router
__all__ = ["router"]