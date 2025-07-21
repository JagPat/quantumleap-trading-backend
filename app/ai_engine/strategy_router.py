"""
Strategy Router
FastAPI endpoints for AI-powered trading strategy generation and management
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional, List, Dict, Any
from .strategy_templates import StrategyTemplateManager, StrategyType, RiskLevel
from .strategy_monitor import StrategyMonitor
from .strategy_generator import StrategyGenerator
from .models import StrategyRequest, StrategyResponse, TradingStrategy, StrategyParameters
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai/strategy", tags=["AI Strategy"])

# Initialize strategy components
template_manager = StrategyTemplateManager()
strategy_monitor = StrategyMonitor()
strategy_generator = StrategyGenerator()

def get_user_id_from_headers(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> str:
    """Extract user ID from headers"""
    if x_user_id:
        return x_user_id
    # Fallback to a default for testing
    return "default_user"

@router.get("/templates")
async def get_strategy_templates(
    risk_level: Optional[str] = None,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get all available strategy templates, optionally filtered by risk level"""
    try:
        if risk_level:
            # Validate risk level
            try:
                risk_enum = RiskLevel(risk_level.lower())
                templates = template_manager.get_templates_by_risk_level(risk_enum)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid risk level. Must be one of: {[r.value for r in RiskLevel]}"
                )
        else:
            templates = template_manager.get_all_templates()
        
        return {
            "status": "success",
            "templates": templates,
            "total_count": len(templates)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get strategy templates: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve templates: {str(e)}"
        )

@router.get("/templates/{strategy_type}")
async def get_strategy_template(
    strategy_type: str,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get a specific strategy template by type"""
    try:
        # Validate strategy type
        try:
            strategy_enum = StrategyType(strategy_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid strategy type. Must be one of: {[s.value for s in StrategyType]}"
            )
        
        template = template_manager.get_template(strategy_enum)
        
        if not template:
            raise HTTPException(
                status_code=404,
                detail=f"Template for {strategy_type} not found"
            )
        
        return {
            "status": "success",
            "template": template
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get strategy template {strategy_type}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve template: {str(e)}"
        )

@router.post("/templates/{strategy_type}/customize")
async def customize_strategy_template(
    strategy_type: str,
    customizations: Dict[str, Any],
    user_id: str = Depends(get_user_id_from_headers)
):
    """Customize a strategy template with user-specific parameters"""
    try:
        # Validate strategy type
        try:
            strategy_enum = StrategyType(strategy_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid strategy type. Must be one of: {[s.value for s in StrategyType]}"
            )
        
        customized_template = template_manager.customize_template(
            strategy_enum, 
            customizations
        )
        
        if not customized_template:
            raise HTTPException(
                status_code=404,
                detail=f"Template for {strategy_type} not found"
            )
        
        return {
            "status": "success",
            "customized_template": customized_template,
            "message": "Template customized successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to customize template {strategy_type}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to customize template: {str(e)}"
        )

@router.get("/recommendations")
async def get_strategy_recommendations(
    market_condition: str = "trending_markets",
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get strategy recommendations based on market conditions and user profile"""
    try:
        # Mock user profile - in production, this would come from user preferences
        user_profile = {
            "risk_tolerance": "medium",
            "trading_experience": "intermediate",
            "preferred_timeframe": "1d"
        }
        
        suitable_templates = template_manager.get_suitable_templates(
            market_condition, 
            user_profile
        )
        
        return {
            "status": "success",
            "recommendations": suitable_templates,
            "market_condition": market_condition,
            "user_profile": user_profile,
            "total_recommendations": len(suitable_templates)
        }
        
    except Exception as e:
        logger.error(f"Failed to get strategy recommendations: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get recommendations: {str(e)}"
        )

@router.post("/generate")
async def generate_strategy(
    strategy_request: Dict[str, Any],
    user_id: str = Depends(get_user_id_from_headers)
):
    """Generate a new trading strategy using AI"""
    try:
        # Create strategy parameters from request
        parameters = StrategyParameters(
            strategy_type=strategy_request.get("strategy_type", "momentum"),
            risk_tolerance=strategy_request.get("risk_tolerance", "medium"),
            time_horizon=strategy_request.get("time_horizon", "medium"),
            target_symbols=strategy_request.get("target_symbols"),
            capital_allocation=strategy_request.get("capital_allocation"),
            max_drawdown=strategy_request.get("max_drawdown")
        )
        
        # Get portfolio data if provided
        portfolio_data = strategy_request.get("portfolio_data")
        
        # Generate strategy using AI
        generation_result = await strategy_generator.generate_strategy(
            user_id, 
            parameters, 
            portfolio_data
        )
        
        return generation_result
        
    except Exception as e:
        logger.error(f"Failed to generate strategy: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate strategy: {str(e)}"
        )

@router.get("/list")
async def list_user_strategies(
    user_id: str = Depends(get_user_id_from_headers)
):
    """List all strategies for the user"""
    try:
        # In production, this would query the database
        # For now, return a mock response
        mock_strategies = [
            {
                "id": f"strategy_{user_id}_1",
                "name": "My Momentum Strategy",
                "type": "momentum",
                "status": "active",
                "created_at": "2025-01-21T10:00:00Z",
                "performance": {
                    "total_return": 12.5,
                    "win_rate": 65.0,
                    "max_drawdown": 8.2
                }
            },
            {
                "id": f"strategy_{user_id}_2",
                "name": "Mean Reversion Setup",
                "type": "mean_reversion",
                "status": "paused",
                "created_at": "2025-01-20T15:30:00Z",
                "performance": {
                    "total_return": 8.3,
                    "win_rate": 58.0,
                    "max_drawdown": 5.1
                }
            }
        ]
        
        return {
            "status": "success",
            "strategies": mock_strategies,
            "total_count": len(mock_strategies)
        }
        
    except Exception as e:
        logger.error(f"Failed to list strategies: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list strategies: {str(e)}"
        )

@router.get("/{strategy_id}")
async def get_strategy(
    strategy_id: str,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get a specific strategy by ID"""
    try:
        # In production, this would query the database
        # For now, return a mock strategy
        mock_strategy = {
            "id": strategy_id,
            "name": "Sample Strategy",
            "type": "momentum",
            "description": "A momentum-based trading strategy",
            "status": "active",
            "created_at": "2025-01-21T10:00:00Z",
            "configuration": template_manager.get_template(StrategyType.MOMENTUM),
            "performance": {
                "total_return": 12.5,
                "win_rate": 65.0,
                "max_drawdown": 8.2,
                "total_trades": 23,
                "avg_trade_duration": "3.2 days"
            }
        }
        
        return {
            "status": "success",
            "strategy": mock_strategy
        }
        
    except Exception as e:
        logger.error(f"Failed to get strategy {strategy_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve strategy: {str(e)}"
        )

@router.put("/{strategy_id}")
async def update_strategy(
    strategy_id: str,
    updates: Dict[str, Any],
    user_id: str = Depends(get_user_id_from_headers)
):
    """Update a strategy configuration"""
    try:
        # In production, this would update the database
        # For now, return a mock response
        
        updated_strategy = {
            "id": strategy_id,
            "name": updates.get("name", "Updated Strategy"),
            "status": updates.get("status", "active"),
            "updated_at": datetime.now().isoformat(),
            "message": "Strategy updated successfully"
        }
        
        return {
            "status": "success",
            "strategy": updated_strategy
        }
        
    except Exception as e:
        logger.error(f"Failed to update strategy {strategy_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update strategy: {str(e)}"
        )

@router.delete("/{strategy_id}")
async def delete_strategy(
    strategy_id: str,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Delete a strategy"""
    try:
        # In production, this would delete from database
        # For now, return a mock response
        
        return {
            "status": "success",
            "message": f"Strategy {strategy_id} deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to delete strategy {strategy_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete strategy: {str(e)}"
        )

@router.get("/health")
async def strategy_health_check():
    """Health check for strategy system"""
    try:
        template_count = len(template_manager.get_all_templates())
        
        return {
            "status": "healthy",
            "components": {
                "strategy_templates": "operational",
                "template_count": template_count,
                "api_endpoints": "ready"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Strategy health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }#
 Strategy Execution and Monitoring Endpoints

@router.post("/{strategy_id}/deploy")
async def deploy_strategy(
    strategy_id: str,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Deploy a strategy for live execution"""
    try:
        # Get strategy configuration (mock for now)
        strategy_config = {
            "id": strategy_id,
            "name": "Sample Strategy",
            "type": "momentum",
            "configuration": template_manager.get_template(StrategyType.MOMENTUM)
        }
        
        deployment_result = await strategy_monitor.deploy_strategy(
            user_id, 
            strategy_config
        )
        
        return deployment_result
        
    except Exception as e:
        logger.error(f"Failed to deploy strategy {strategy_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to deploy strategy: {str(e)}"
        )

@router.get("/{strategy_id}/performance")
async def get_strategy_performance(
    strategy_id: str,
    period_days: int = 30,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get strategy performance metrics"""
    try:
        performance_result = await strategy_monitor.get_strategy_performance(
            user_id, 
            strategy_id, 
            period_days
        )
        
        return performance_result
        
    except Exception as e:
        logger.error(f"Failed to get performance for strategy {strategy_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve performance: {str(e)}"
        )

@router.get("/monitor/active")
async def monitor_active_strategies(
    user_id: str = Depends(get_user_id_from_headers)
):
    """Monitor all active strategies for the user"""
    try:
        monitoring_result = await strategy_monitor.monitor_active_strategies(user_id)
        
        return monitoring_result
        
    except Exception as e:
        logger.error(f"Failed to monitor active strategies: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to monitor strategies: {str(e)}"
        )

@router.post("/{strategy_id}/pause")
async def pause_strategy(
    strategy_id: str,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Pause strategy execution"""
    try:
        pause_result = await strategy_monitor.pause_strategy(user_id, strategy_id)
        
        return pause_result
        
    except Exception as e:
        logger.error(f"Failed to pause strategy {strategy_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to pause strategy: {str(e)}"
        )

@router.post("/{strategy_id}/resume")
async def resume_strategy(
    strategy_id: str,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Resume paused strategy execution"""
    try:
        resume_result = await strategy_monitor.resume_strategy(user_id, strategy_id)
        
        return resume_result
        
    except Exception as e:
        logger.error(f"Failed to resume strategy {strategy_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resume strategy: {str(e)}"
        )

@router.post("/{strategy_id}/stop")
async def stop_strategy(
    strategy_id: str,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Stop strategy execution permanently"""
    try:
        stop_result = await strategy_monitor.stop_strategy(user_id, strategy_id)
        
        return stop_result
        
    except Exception as e:
        logger.error(f"Failed to stop strategy {strategy_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop strategy: {str(e)}"
        )

@router.get("/{strategy_id}/alerts")
async def get_strategy_alerts(
    strategy_id: str,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get alerts and notifications for a strategy"""
    try:
        alerts_result = await strategy_monitor.get_strategy_alerts(user_id, strategy_id)
        
        return alerts_result
        
    except Exception as e:
        logger.error(f"Failed to get alerts for strategy {strategy_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve alerts: {str(e)}"
        )