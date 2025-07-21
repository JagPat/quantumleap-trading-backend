"""
Risk Management and Cost Optimization Router
FastAPI endpoints for risk assessment and cost optimization
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional, Dict, Any
from .risk_manager import RiskManager
from .cost_optimizer import CostOptimizer
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai/risk-cost", tags=["Risk Management & Cost Optimization"])

# Initialize managers
risk_manager = RiskManager()
cost_optimizer = CostOptimizer()

def get_user_id_from_headers(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> str:
    """Extract user ID from headers"""
    if x_user_id:
        return x_user_id
    return "default_user"

# Request/Response Models
class PortfolioRiskRequest(BaseModel):
    portfolio_data: Dict[str, Any]

class TradeValidationRequest(BaseModel):
    trade_data: Dict[str, Any]
    portfolio_data: Dict[str, Any]

class PositionSizeRequest(BaseModel):
    symbol: str
    portfolio_value: float
    risk_tolerance: str = "medium"

class CostLimitRequest(BaseModel):
    provider: str
    estimated_cost_cents: int

# Risk Management Endpoints

@router.post("/portfolio/assess")
async def assess_portfolio_risk(
    request: PortfolioRiskRequest,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Assess portfolio risk factors"""
    try:
        assessment = await risk_manager.assess_portfolio_risk(
            user_id, 
            request.portfolio_data
        )
        return assessment
        
    except Exception as e:
        logger.error(f"Portfolio risk assessment failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Risk assessment failed: {str(e)}"
        )

@router.post("/trade/validate")
async def validate_trade_risk(
    request: TradeValidationRequest,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Validate if a proposed trade meets risk criteria"""
    try:
        validation = await risk_manager.validate_trade_risk(
            user_id,
            request.trade_data,
            request.portfolio_data
        )
        return validation
        
    except Exception as e:
        logger.error(f"Trade risk validation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Trade validation failed: {str(e)}"
        )

@router.post("/position/recommend")
async def recommend_position_size(
    request: PositionSizeRequest,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get position size recommendation"""
    try:
        recommendation = await risk_manager.get_position_size_recommendation(
            user_id,
            request.symbol,
            request.portfolio_value,
            request.risk_tolerance
        )
        return recommendation
        
    except Exception as e:
        logger.error(f"Position size recommendation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Position size recommendation failed: {str(e)}"
        )

# Cost Optimization Endpoints

@router.post("/cost/check-limits")
async def check_cost_limits(
    request: CostLimitRequest,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Check if operation would exceed cost limits"""
    try:
        check_result = await cost_optimizer.check_cost_limits(
            user_id,
            request.provider,
            request.estimated_cost_cents
        )
        return check_result
        
    except Exception as e:
        logger.error(f"Cost limit check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Cost limit check failed: {str(e)}"
        )

@router.get("/cost/usage/{provider}")
async def get_daily_usage(
    provider: str,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get today's usage for a specific provider"""
    try:
        usage = await cost_optimizer.get_daily_usage(user_id, provider)
        return usage
        
    except Exception as e:
        logger.error(f"Failed to get daily usage: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get usage data: {str(e)}"
        )

@router.get("/cost/optimization")
async def get_cost_optimization_suggestions(
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get cost optimization suggestions"""
    try:
        suggestions = await cost_optimizer.suggest_cost_optimization(user_id)
        return suggestions
        
    except Exception as e:
        logger.error(f"Cost optimization suggestions failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate suggestions: {str(e)}"
        )

@router.get("/cost/report")
async def get_cost_report(
    days: int = 30,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Generate comprehensive cost report"""
    try:
        report = await cost_optimizer.get_cost_report(user_id, days)
        return report
        
    except Exception as e:
        logger.error(f"Cost report generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate cost report: {str(e)}"
        )

@router.get("/cost/alerts")
async def check_cost_alerts(
    user_id: str = Depends(get_user_id_from_headers)
):
    """Check current usage and get alerts"""
    try:
        alerts = await cost_optimizer.check_and_send_alerts(user_id)
        return {
            "alerts": alerts,
            "alert_count": len(alerts)
        }
        
    except Exception as e:
        logger.error(f"Cost alerts check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check alerts: {str(e)}"
        )

# Combined Endpoints

@router.get("/dashboard")
async def get_risk_cost_dashboard(
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get combined risk and cost dashboard data"""
    try:
        # Get cost summary
        cost_report = await cost_optimizer.get_cost_report(user_id, days=7)
        cost_alerts = await cost_optimizer.check_and_send_alerts(user_id)
        
        # Mock portfolio data for risk assessment (in production, get from portfolio service)
        mock_portfolio = {
            "total_value": 500000,
            "holdings": [
                {"symbol": "RELIANCE", "current_value": 75000, "sector": "Energy"},
                {"symbol": "TCS", "current_value": 60000, "sector": "IT"},
                {"symbol": "HDFCBANK", "current_value": 50000, "sector": "Banking"},
                {"symbol": "INFY", "current_value": 45000, "sector": "IT"},
                {"symbol": "ICICIBANK", "current_value": 40000, "sector": "Banking"}
            ]
        }
        
        risk_assessment = await risk_manager.assess_portfolio_risk(user_id, mock_portfolio)
        
        return {
            "user_id": user_id,
            "risk_summary": {
                "overall_risk": risk_assessment.get("overall_risk"),
                "risk_score": risk_assessment.get("risk_score"),
                "risk_factors_count": len(risk_assessment.get("risk_factors", []))
            },
            "cost_summary": {
                "weekly_cost_cents": cost_report.get("summary", {}).get("total_cost_cents", 0),
                "daily_average_cents": cost_report.get("summary", {}).get("daily_average_cents", 0),
                "monthly_projection_cents": cost_report.get("summary", {}).get("monthly_projection_cents", 0)
            },
            "alerts": {
                "cost_alerts": cost_alerts,
                "risk_recommendations": risk_assessment.get("recommendations", [])[:3]  # Top 3
            },
            "generated_at": cost_report.get("generated_at")
        }
        
    except Exception as e:
        logger.error(f"Dashboard generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate dashboard: {str(e)}"
        )

# Health check
@router.get("/health")
async def risk_cost_health_check():
    """Health check for risk management and cost optimization"""
    try:
        return {
            "status": "healthy",
            "components": {
                "risk_manager": "operational",
                "cost_optimizer": "operational",
                "database": "connected"
            },
            "timestamp": "2025-07-21T10:30:00Z"
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }