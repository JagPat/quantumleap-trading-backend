#!/usr/bin/env python3
"""
AI Components Router

Comprehensive API endpoints for all restored AI components:
- AI Chat
- Strategy Templates  
- Market Intelligence
- Performance Analytics
- Risk Management
- Learning Insights
- Optimization Recommendations
- AI Analysis
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import json
import logging
from enum import Enum

# Configure logging first
logger = logging.getLogger(__name__)

# Import authentication middleware
try:
    from app.core.auth import get_current_user_id, get_current_user_optional, verify_jwt_token
    AUTH_AVAILABLE = True
    logger.info("✅ Authentication middleware imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ Authentication middleware not available: {str(e)}")
    AUTH_AVAILABLE = False
    
    # Create dummy dependency for development
    async def get_current_user_id():
        return "dev_user_123"
    
    async def get_current_user_optional():
        return "dev_user_123"
    
    async def verify_jwt_token():
        return "dev_user_123"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Components"])

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ChatMessage(BaseModel):
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Chat session ID")
    context: Optional[str] = Field("trading", description="Chat context")

class ChatResponse(BaseModel):
    response: str
    suggestions: List[str] = []
    session_id: str
    timestamp: datetime
    data: Optional[Dict[str, Any]] = None

class StrategyTemplate(BaseModel):
    id: str
    name: str
    category: str
    description: str
    risk_level: str
    timeframe: str
    success_rate: float
    avg_return: float
    parameters: Dict[str, Any]
    tags: List[str]

class StrategyDeployment(BaseModel):
    template_id: str
    name: str
    parameters: Dict[str, Any]
    risk_level: str
    timeframe: str

class MarketIntelligenceRequest(BaseModel):
    symbol: Optional[str] = "NIFTY50"
    timeframe: Optional[str] = "1D"

class PerformanceAnalyticsRequest(BaseModel):
    timeframe: Optional[str] = "1M"
    metrics: Optional[List[str]] = ["returns", "risk", "sharpe"]

class RiskSettings(BaseModel):
    max_position_size: float = Field(5.0, ge=1.0, le=25.0)
    stop_loss_percentage: float = Field(2.0, ge=0.5, le=10.0)
    daily_loss_limit: float = Field(10.0, ge=5.0, le=20.0)
    max_drawdown_limit: float = Field(15.0, ge=10.0, le=30.0)
    risk_per_trade: float = Field(1.0, ge=0.1, le=5.0)
    correlation_limit: float = Field(0.7, ge=0.1, le=1.0)
    volatility_threshold: float = Field(20.0, ge=10.0, le=50.0)
    auto_risk_adjustment: bool = True
    emergency_stop_enabled: bool = True

class OptimizationAction(BaseModel):
    recommendation_id: int
    action: str = Field(..., pattern="^(apply|dismiss)$")

# ============================================================================
# AI CHAT ENDPOINTS
# ============================================================================

@router.post("/chat", response_model=ChatResponse)
async def ai_chat(chat_request: ChatMessage, user_id: str = Depends(get_current_user_id)):
    """
    AI Chat endpoint for trading assistance and insights
    Requires authentication: JWT token in Authorization header
    """
    try:
        logger.info(f"AI Chat request from user: {user_id}")
        
        # Mock AI chat response - replace with actual AI integration
        response_text = generate_ai_response(chat_request.message, user_id)
        
        suggestions = [
            "Analyze current market conditions",
            "Show me portfolio risk analysis", 
            "What are the best trading opportunities?",
            "Explain this market trend"
        ]
        
        # Generate or use existing session ID
        session_id = chat_request.session_id or f"session_{user_id}_{datetime.now().timestamp()}"
        
        return ChatResponse(
            response=response_text,
            suggestions=suggestions,
            session_id=session_id,
            timestamp=datetime.now(),
            data={"user_id": user_id, "authenticated": True}
        )
        
    except Exception as e:
        logger.error(f"AI Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI Chat failed: {str(e)}")

def generate_ai_response(message: str, user_id: str = None) -> str:
    """Generate AI response based on user message and context"""
    message_lower = message.lower()
    
    if "market" in message_lower or "condition" in message_lower:
        return """Based on current market analysis, the NIFTY is showing mixed signals. The index is trading near key resistance levels around 18,200. Here's what I'm observing:

• **Technical Analysis**: RSI at 58, indicating neutral momentum
• **Market Sentiment**: Slightly bullish with FII buying support  
• **Volatility**: VIX at 18.5, suggesting moderate volatility
• **Key Levels**: Support at 17,800, Resistance at 18,350

Would you like me to analyze any specific sectors or stocks?"""
    
    elif "risk" in message_lower or "portfolio" in message_lower:
        return """Let me analyze your portfolio risk profile:

**Current Risk Assessment:**
• Portfolio Beta: 1.15 (slightly aggressive)
• Diversification Score: 7.2/10 (good)
• Maximum Drawdown: -8.3% (acceptable)
• Sharpe Ratio: 1.42 (excellent)

**Risk Recommendations:**
✅ Your diversification is good across sectors
⚠️ Consider reducing position size in high-beta stocks
✅ Stop-loss discipline is being followed
⚠️ Cash allocation could be increased to 10-15%

Would you like specific recommendations for risk optimization?"""
    
    elif "strategy" in message_lower or "trading" in message_lower:
        return """Here are some AI-recommended trading strategies for current market conditions:

**1. Momentum Strategy**
• Focus on stocks breaking above 20-day highs
• Target: 3-5% gains with 2% stop-loss
• Suitable for: Intraday to short-term

**2. Mean Reversion**  
• Look for oversold stocks in strong sectors
• Entry: RSI below 30, Exit: RSI above 70
• Risk: 1.5% per trade

**3. Sector Rotation**
• Current favorites: IT, Pharma, FMCG
• Avoid: Real Estate, Metals (cyclical weakness)

Which strategy interests you most?"""
    
    else:
        return """I'm here to help with your trading and investment questions. I can assist you with:

• **Market Analysis** - Current conditions, trends, and forecasts
• **Stock Research** - Individual stock analysis and recommendations  
• **Trading Strategies** - Entry/exit strategies and risk management
• **Portfolio Review** - Risk assessment and optimization
• **Technical Analysis** - Chart patterns and indicators
• **Sector Analysis** - Industry trends and opportunities

What specific area would you like to explore?"""

# ============================================================================
# STRATEGY TEMPLATES ENDPOINTS
# ============================================================================

@router.get("/strategy-templates", response_model=List[StrategyTemplate])
async def get_strategy_templates(user_id: Optional[str] = Depends(get_current_user_optional)):
    """
    Get all available AI strategy templates
    Optional authentication: JWT token in Authorization header
    """
    try:
        # Use default user if not authenticated
        if not user_id:
            user_id = "anonymous_user"
        # Mock strategy templates - replace with database query
        templates = [
            {
                "id": "momentum-scalper",
                "name": "Momentum Scalper",
                "category": "scalping",
                "description": "High-frequency trading strategy that capitalizes on short-term price momentum",
                "risk_level": "high",
                "timeframe": "1m-5m",
                "success_rate": 78.0,
                "avg_return": 2.4,
                "parameters": {
                    "momentum_threshold": 0.02,
                    "stop_loss": 0.01,
                    "take_profit": 0.015,
                    "max_positions": 5
                },
                "tags": ["momentum", "scalping", "high-frequency"]
            },
            {
                "id": "trend-follower",
                "name": "Trend Follower",
                "category": "trend",
                "description": "Medium-term strategy that identifies and follows strong market trends",
                "risk_level": "medium",
                "timeframe": "1h-4h",
                "success_rate": 65.0,
                "avg_return": 8.2,
                "parameters": {
                    "trend_strength": 0.7,
                    "entry_confirmation": 2,
                    "stop_loss": 0.03,
                    "take_profit": 0.06
                },
                "tags": ["trend", "medium-term", "momentum"]
            },
            {
                "id": "mean-reversion",
                "name": "Mean Reversion",
                "category": "reversion",
                "description": "Conservative strategy that profits from price returning to statistical mean",
                "risk_level": "low",
                "timeframe": "4h-1d",
                "success_rate": 72.0,
                "avg_return": 5.8,
                "parameters": {
                    "deviation_threshold": 2.0,
                    "reversion_period": 20,
                    "stop_loss": 0.02,
                    "take_profit": 0.025
                },
                "tags": ["mean-reversion", "conservative", "statistical"]
            },
            {
                "id": "ai-sentiment",
                "name": "AI Sentiment Analyzer",
                "category": "ai",
                "description": "Advanced AI strategy that analyzes market sentiment and news impact",
                "risk_level": "medium",
                "timeframe": "15m-1h",
                "success_rate": 69.0,
                "avg_return": 6.7,
                "parameters": {
                    "sentiment_threshold": 0.6,
                    "news_impact_weight": 0.3,
                    "confidence_minimum": 0.75,
                    "position_size": 0.02
                },
                "tags": ["ai", "sentiment", "news", "nlp"]
            }
        ]
        
        return [StrategyTemplate(**template) for template in templates]
        
    except Exception as e:
        logger.error(f"Strategy templates error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load strategy templates: {str(e)}")

@router.post("/strategy-templates/deploy")
async def deploy_strategy(deployment: StrategyDeployment, user_id: str = Depends(get_current_user_id)):
    """
    Deploy a strategy template
    Requires authentication: JWT token in Authorization header with custom parameters
    """
    try:
        # Mock deployment - replace with actual strategy deployment logic
        deployment_id = f"deploy_{datetime.now().timestamp()}"
        
        return {
            "success": True,
            "deployment_id": deployment_id,
            "message": f"Strategy '{deployment.name}' deployed successfully",
            "template_id": deployment.template_id,
            "parameters": deployment.parameters
        }
        
    except Exception as e:
        logger.error(f"Strategy deployment error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Strategy deployment failed: {str(e)}")

@router.post("/strategy-templates/{template_id}/backtest")
async def backtest_strategy(template_id: str, user_id: str = Depends(get_current_user_id)):
    """
    Run backtest for a strategy template
    """
    try:
        # Mock backtest - replace with actual backtesting logic
        return {
            "success": True,
            "template_id": template_id,
            "backtest_id": f"backtest_{datetime.now().timestamp()}",
            "message": "Backtest started successfully",
            "estimated_completion": (datetime.now() + timedelta(minutes=5)).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Backtest error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")

# ============================================================================
# MARKET INTELLIGENCE ENDPOINTS
# ============================================================================

@router.post("/market-intelligence")
async def get_market_intelligence(request: MarketIntelligenceRequest, user_id: str = Depends(get_current_user_id)):
    """
    Get AI-powered market intelligence and analysis
    """
    try:
        # Mock market intelligence data - replace with actual market analysis
        intelligence_data = {
            "overall_sentiment": 0.65,
            "market_condition": "bullish",
            "volatility_index": 18.5,
            "fear_greed_index": 72,
            "trend_strength": 0.78,
            "support_levels": [17800, 17650, 17500],
            "resistance_levels": [18200, 18350, 18500],
            "key_levels": {
                "current": 17950,
                "daily_high": 18020,
                "daily_low": 17880,
                "weekly_high": 18150,
                "weekly_low": 17650
            },
            "sentiment_history": [
                {"time": "09:00", "sentiment": 0.45, "volume": 1200},
                {"time": "10:00", "sentiment": 0.52, "volume": 1450},
                {"time": "11:00", "sentiment": 0.48, "volume": 1380},
                {"time": "12:00", "sentiment": 0.65, "volume": 1600},
                {"time": "13:00", "sentiment": 0.72, "volume": 1750},
                {"time": "14:00", "sentiment": 0.68, "volume": 1650},
                {"time": "15:00", "sentiment": 0.75, "volume": 1800}
            ],
            "news_analysis": [
                {
                    "id": 1,
                    "headline": "RBI maintains repo rate at 6.5%, signals cautious optimism",
                    "sentiment": 0.7,
                    "impact": "high",
                    "relevance": 0.9,
                    "timestamp": "2 hours ago",
                    "summary": "Central bank decision supports market stability with positive outlook for growth."
                },
                {
                    "id": 2,
                    "headline": "IT sector shows strong Q3 earnings growth",
                    "sentiment": 0.8,
                    "impact": "medium",
                    "relevance": 0.75,
                    "timestamp": "4 hours ago",
                    "summary": "Technology companies report better-than-expected quarterly results."
                }
            ]
        }
        
        return {
            "success": True,
            "symbol": request.symbol,
            "timeframe": request.timeframe,
            "data": intelligence_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Market intelligence error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Market intelligence failed: {str(e)}")

# ============================================================================
# PERFORMANCE ANALYTICS ENDPOINTS
# ============================================================================

@router.post("/performance-analytics")
async def get_performance_analytics(request: PerformanceAnalyticsRequest, user_id: str = Depends(get_current_user_id)):
    """
    Get AI performance analytics and metrics
    """
    try:
        # Mock performance data - replace with actual analytics
        performance_data = {
            "overview": {
                "total_return": 12.5,
                "win_rate": 68.5,
                "sharpe_ratio": 1.42,
                "max_drawdown": -8.3,
                "total_trades": 156,
                "profitable_trades": 107,
                "avg_trade_duration": "2.3 hours",
                "best_strategy": "Momentum Scalper"
            },
            "returns_history": [
                {"date": "2024-01-01", "cumulative": 0, "daily": 0},
                {"date": "2024-01-02", "cumulative": 1.2, "daily": 1.2},
                {"date": "2024-01-03", "cumulative": 2.1, "daily": 0.9},
                {"date": "2024-01-04", "cumulative": 1.8, "daily": -0.3},
                {"date": "2024-01-05", "cumulative": 3.2, "daily": 1.4},
                {"date": "2024-01-06", "cumulative": 4.1, "daily": 0.9},
                {"date": "2024-01-07", "cumulative": 3.8, "daily": -0.3},
                {"date": "2024-01-08", "cumulative": 5.2, "daily": 1.4}
            ],
            "strategy_performance": [
                {"name": "Momentum Scalper", "return": 15.2, "trades": 45, "winRate": 72},
                {"name": "Trend Follower", "return": 11.8, "trades": 38, "winRate": 65},
                {"name": "Mean Reversion", "return": 8.9, "trades": 42, "winRate": 71},
                {"name": "AI Sentiment", "return": 13.4, "trades": 31, "winRate": 68}
            ],
            "risk_metrics": {
                "value_at_risk": -2.1,
                "expected_shortfall": -3.2,
                "beta": 0.85,
                "alpha": 0.08,
                "correlation_market": 0.72,
                "volatility": 12.4
            }
        }
        
        return {
            "success": True,
            "timeframe": request.timeframe,
            "metrics": request.metrics,
            "data": performance_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Performance analytics error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Performance analytics failed: {str(e)}")

# ============================================================================
# RISK MANAGEMENT ENDPOINTS
# ============================================================================

@router.get("/risk-metrics")
async def get_risk_metrics(user_id: Optional[str] = Depends(get_current_user_optional)):
    """
    Get current risk metrics
    Optional authentication: JWT token in Authorization header
    """
    try:
        # Use default user if not authenticated
        if not user_id:
            user_id = "anonymous_user"
        # Mock risk metrics - replace with actual risk calculation
        risk_data = {
            "current_risk_level": "medium",
            "portfolio_var": -2.8,
            "current_drawdown": -5.2,
            "daily_pnl": 1.2,
            "position_concentration": 0.65,
            "correlation_risk": 0.72,
            "volatility_index": 18.5,
            "risk_score": 6.5,
            "positions": [
                {"symbol": "RELIANCE", "exposure": 15, "risk_contribution": 0.8, "status": "normal"},
                {"symbol": "TCS", "exposure": 12, "risk_contribution": 0.6, "status": "normal"},
                {"symbol": "HDFC", "exposure": 18, "risk_contribution": 1.2, "status": "warning"},
                {"symbol": "INFY", "exposure": 10, "risk_contribution": 0.5, "status": "normal"}
            ],
            "risk_limits": {
                "position_size": {"current": 18, "limit": 20, "status": "warning"},
                "daily_loss": {"current": -1.2, "limit": -10, "status": "normal"},
                "drawdown": {"current": -5.2, "limit": -15, "status": "normal"},
                "correlation": {"current": 0.72, "limit": 0.7, "status": "breach"}
            }
        }
        
        return {
            "success": True,
            "data": risk_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Risk metrics error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Risk metrics failed: {str(e)}")

@router.post("/risk-settings")
async def update_risk_settings(settings: RiskSettings, user_id: str = Depends(get_current_user_id)):
    """
    Update risk management settings
    Requires authentication: JWT token in Authorization header
    """
    try:
        # Mock settings update - replace with actual database update
        return {
            "success": True,
            "message": "Risk settings updated successfully",
            "settings": settings.dict(),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Risk settings update error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Risk settings update failed: {str(e)}")

@router.post("/emergency-stop")
async def trigger_emergency_stop(user_id: str = Depends(get_current_user_id)):
    """
    Trigger emergency stop for all trading
    Requires authentication: JWT token in Authorization header activities
    """
    try:
        # Mock emergency stop - replace with actual emergency stop logic
        return {
            "success": True,
            "message": "Emergency stop activated successfully",
            "timestamp": datetime.now().isoformat(),
            "actions_taken": [
                "All active trades halted",
                "New order placement disabled",
                "Risk monitoring increased",
                "Notifications sent to administrators"
            ]
        }
        
    except Exception as e:
        logger.error(f"Emergency stop error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Emergency stop failed: {str(e)}")

# ============================================================================
# LEARNING INSIGHTS ENDPOINTS
# ============================================================================

@router.get("/learning-insights")
async def get_learning_insights(timeframe: str = "1M", user_id: str = Depends(get_current_user_id)):
    """
    Get AI learning insights and progress
    Requires authentication: JWT token in Authorization header metrics
    """
    try:
        # Mock learning data - replace with actual AI learning metrics
        learning_data = {
            "model_performance": {
                "accuracy": 78.5,
                "precision": 82.1,
                "recall": 75.3,
                "f1_score": 78.6,
                "improvement_rate": 12.3,
                "learning_velocity": "high",
                "confidence_level": 85.2
            },
            "learning_progress": [
                {"date": "2024-01-01", "accuracy": 65.2, "trades": 45},
                {"date": "2024-01-02", "accuracy": 67.1, "trades": 52},
                {"date": "2024-01-03", "accuracy": 69.8, "trades": 48},
                {"date": "2024-01-04", "accuracy": 71.2, "trades": 56},
                {"date": "2024-01-05", "accuracy": 73.5, "trades": 61},
                {"date": "2024-01-06", "accuracy": 75.1, "trades": 58},
                {"date": "2024-01-07", "accuracy": 76.8, "trades": 63},
                {"date": "2024-01-08", "accuracy": 78.5, "trades": 67}
            ],
            "insights": [
                {
                    "id": 1,
                    "category": "pattern_recognition",
                    "title": "Improved Trend Detection",
                    "description": "AI model has learned to better identify trend reversals in volatile markets",
                    "impact": "high",
                    "confidence": 92,
                    "learned_from": 156,
                    "timestamp": "2 hours ago"
                },
                {
                    "id": 2,
                    "category": "risk_management",
                    "title": "Enhanced Stop-Loss Timing",
                    "description": "Model optimized stop-loss placement based on volatility patterns",
                    "impact": "medium",
                    "confidence": 87,
                    "learned_from": 89,
                    "timestamp": "6 hours ago"
                }
            ],
            "knowledge_areas": [
                {"area": "Technical Analysis", "proficiency": 85, "recent_improvement": 8},
                {"area": "Market Sentiment", "proficiency": 78, "recent_improvement": 12},
                {"area": "Risk Management", "proficiency": 92, "recent_improvement": 5},
                {"area": "Pattern Recognition", "proficiency": 88, "recent_improvement": 15}
            ],
            "training_metrics": {
                "total_trades_analyzed": 12456,
                "successful_predictions": 9778,
                "model_updates": 45,
                "data_points_processed": 2400000,
                "learning_sessions": 128,
                "knowledge_base_size": "15.2 GB"
            }
        }
        
        return {
            "success": True,
            "timeframe": timeframe,
            "data": learning_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Learning insights error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Learning insights failed: {str(e)}")

# ============================================================================
# OPTIMIZATION RECOMMENDATIONS ENDPOINTS
# ============================================================================

@router.get("/optimization-recommendations")
async def get_optimization_recommendations(user_id: str = Depends(get_current_user_id)):
    """
    Get AI-generated optimization recommendations
    """
    try:
        # Mock optimization recommendations - replace with actual AI recommendations
        recommendations = [
            {
                "id": 1,
                "title": "Optimize Position Sizing Strategy",
                "category": "risk_management",
                "priority": "high",
                "impact_score": 8.5,
                "confidence": 92,
                "description": "Current position sizing is too conservative. Increasing position sizes by 15% could improve returns while maintaining acceptable risk levels.",
                "expected_improvement": {
                    "return_increase": 12.3,
                    "risk_increase": 3.2,
                    "sharpe_improvement": 0.15
                },
                "implementation_steps": [
                    "Increase base position size from 2% to 2.3% of portfolio",
                    "Apply dynamic sizing based on confidence levels",
                    "Implement stricter stop-loss rules for larger positions",
                    "Monitor performance for 2 weeks before full implementation"
                ],
                "estimated_time": "2-3 days",
                "complexity": "medium",
                "status": "pending"
            },
            {
                "id": 2,
                "title": "Enhance Market Timing Algorithm",
                "category": "strategy",
                "priority": "high",
                "impact_score": 9.2,
                "confidence": 88,
                "description": "Market entry timing can be improved by incorporating additional volatility indicators and sentiment analysis.",
                "expected_improvement": {
                    "return_increase": 18.7,
                    "risk_increase": 1.8,
                    "sharpe_improvement": 0.22
                },
                "implementation_steps": [
                    "Integrate VIX volatility indicators",
                    "Add real-time news sentiment analysis",
                    "Implement adaptive entry thresholds",
                    "Backtest with 6 months of historical data"
                ],
                "estimated_time": "1 week",
                "complexity": "high",
                "status": "pending"
            }
        ]
        
        return {
            "success": True,
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Optimization recommendations error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Optimization recommendations failed: {str(e)}")

@router.post("/optimization-recommendations/action")
async def handle_optimization_action(action: OptimizationAction, user_id: str = Depends(get_current_user_id)):
    """
    Apply or dismiss an optimization recommendation
    """
    try:
        if action.action == "apply":
            # Mock apply logic - replace with actual implementation
            return {
                "success": True,
                "message": f"Optimization recommendation {action.recommendation_id} applied successfully",
                "recommendation_id": action.recommendation_id,
                "action": action.action,
                "timestamp": datetime.now().isoformat()
            }
        elif action.action == "dismiss":
            # Mock dismiss logic - replace with actual implementation
            return {
                "success": True,
                "message": f"Optimization recommendation {action.recommendation_id} dismissed",
                "recommendation_id": action.recommendation_id,
                "action": action.action,
                "timestamp": datetime.now().isoformat()
            }
        
    except Exception as e:
        logger.error(f"Optimization action error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Optimization action failed: {str(e)}")

# ============================================================================
# AI ANALYSIS ENDPOINTS (Enhanced)
# ============================================================================

@router.post("/analysis/comprehensive")
async def get_comprehensive_analysis(timeframe: str = "1M", user_id: str = Depends(get_current_user_id)):
    """
    Get comprehensive AI analysis
    Requires authentication: JWT token in Authorization header combining market, portfolio, and performance data
    """
    try:
        # Mock comprehensive analysis - replace with actual AI analysis
        analysis_data = {
            "overall_score": 7.8,
            "market_sentiment": "bullish",
            "risk_level": "medium",
            "recommendations": [
                {
                    "id": 1,
                    "type": "buy",
                    "symbol": "RELIANCE",
                    "confidence": 85,
                    "target_price": 2750,
                    "current_price": 2650,
                    "reason": "Strong technical breakout with volume confirmation",
                    "timeframe": "short_term"
                },
                {
                    "id": 2,
                    "type": "sell",
                    "symbol": "ADANIPORTS",
                    "confidence": 78,
                    "target_price": 720,
                    "current_price": 750,
                    "reason": "Overbought conditions, profit booking expected",
                    "timeframe": "short_term"
                }
            ],
            "market_analysis": {
                "trend": "upward",
                "volatility": 18.5,
                "support_level": 17800,
                "resistance_level": 18350,
                "key_events": [
                    "RBI policy meeting next week",
                    "Q3 earnings season ongoing",
                    "FII buying continues"
                ]
            },
            "portfolio_insights": {
                "diversification_score": 72,
                "risk_adjusted_return": 1.42,
                "sector_allocation": [
                    {"sector": "IT", "allocation": 25, "recommendation": "optimal"},
                    {"sector": "Banking", "allocation": 20, "recommendation": "increase"},
                    {"sector": "Pharma", "allocation": 15, "recommendation": "optimal"}
                ]
            },
            "ai_signals": [
                {
                    "signal": "momentum_breakout",
                    "strength": "strong",
                    "symbols": ["RELIANCE", "ICICIBANK", "HDFCBANK"],
                    "description": "Multiple large-cap stocks showing momentum breakout patterns"
                }
            ]
        }
        
        return {
            "success": True,
            "timeframe": timeframe,
            "data": analysis_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Comprehensive analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Comprehensive analysis failed: {str(e)}")

# ============================================================================
# PORTFOLIO AI ANALYSIS ENDPOINTS
# ============================================================================

@router.post("/copilot/analyze")
async def analyze_portfolio(portfolio_data: Dict[str, Any], user_id: str = Depends(get_current_user_id)):
    """
    Analyze portfolio using AI copilot
    Requires authentication: JWT token in Authorization header
    """
    try:
        # Mock portfolio analysis - replace with actual AI analysis
        analysis_result = {
            "success": True,
            "analysis": {
                "overall_score": 7.5,
                "risk_level": "moderate",
                "diversification_score": 8.2,
                "performance_rating": "good",
                "recommendations": [
                    {
                        "type": "rebalance",
                        "description": "Consider reducing IT sector exposure from 35% to 25%",
                        "priority": "medium",
                        "impact": "positive"
                    },
                    {
                        "type": "add_position",
                        "description": "Add pharma sector exposure for better diversification",
                        "priority": "low",
                        "impact": "neutral"
                    }
                ],
                "risk_metrics": {
                    "beta": 1.15,
                    "sharpe_ratio": 1.42,
                    "max_drawdown": -8.3,
                    "volatility": 12.4
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return analysis_result
        
    except Exception as e:
        logger.error(f"Portfolio analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Portfolio analysis failed: {str(e)}")

@router.post("/analysis/portfolio")
async def analyze_portfolio_frontend(portfolio_data: Dict[str, Any]):
    """
    Portfolio analysis endpoint for frontend integration
    This is the endpoint that the frontend railwayApiClient.js calls
    """
    try:
        logger.info(f"Frontend portfolio analysis request received: {portfolio_data}")
        
        # Extract portfolio data
        user_id = portfolio_data.get('user_id', 'unknown')
        holdings = portfolio_data.get('holdings', [])
        total_value = portfolio_data.get('total_value', 0)
        day_pnl = portfolio_data.get('day_pnl', 0)
        
        # Perform AI analysis (mock for now, replace with real AI)
        analysis_result = {
            "success": True,
            "user_id": user_id,
            "analysis": {
                "overall_score": 7.8,
                "risk_level": "moderate",
                "diversification_score": 8.1,
                "performance_rating": "good",
                "total_value": total_value,
                "day_pnl": day_pnl,
                "holdings_count": len(holdings),
                "key_insights": [
                    "Portfolio shows good diversification across sectors",
                    f"Current value of ₹{total_value:,.2f} with day P&L of ₹{day_pnl:,.2f}",
                    "Consider rebalancing if any single stock exceeds 15% allocation"
                ],
                "recommendations": [
                    {
                        "type": "diversification",
                        "title": "Sector Rebalancing",
                        "description": "Consider reducing concentration in top performing sectors",
                        "priority": "medium",
                        "impact": "risk_reduction"
                    },
                    {
                        "type": "performance",
                        "title": "Profit Booking",
                        "description": "Book profits in stocks with >20% gains",
                        "priority": "low",
                        "impact": "profit_optimization"
                    }
                ],
                "risk_metrics": {
                    "portfolio_beta": 1.12,
                    "sharpe_ratio": 1.35,
                    "max_drawdown": -7.8,
                    "volatility": 14.2,
                    "var_95": -2.1
                },
                "sector_analysis": {
                    "top_sectors": ["Technology", "Finance", "Healthcare"],
                    "concentration_risk": "moderate",
                    "diversification_score": 8.1
                }
            },
            "timestamp": datetime.now().isoformat(),
            "analysis_type": "comprehensive"
        }
        
        logger.info(f"Portfolio analysis completed for user {user_id}")
        return analysis_result
        
    except Exception as e:
        logger.error(f"Frontend portfolio analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Portfolio analysis failed: {str(e)}")

@router.post("/copilot/recommendations")
async def get_portfolio_recommendations(request_data: Dict[str, Any], user_id: str = Depends(get_current_user_id)):
    """
    Get AI portfolio recommendations
    """
    try:
        # Mock recommendations - replace with actual AI recommendations
        recommendations = {
            "success": True,
            "recommendations": [
                {
                    "id": 1,
                    "type": "buy",
                    "symbol": "RELIANCE",
                    "quantity": 10,
                    "target_price": 2750,
                    "confidence": 85,
                    "reason": "Strong fundamentals and technical breakout"
                },
                {
                    "id": 2,
                    "type": "sell",
                    "symbol": "ADANIPORTS",
                    "quantity": 5,
                    "target_price": 720,
                    "confidence": 78,
                    "reason": "Overbought conditions, profit booking recommended"
                }
            ],
            "timestamp": datetime.now().isoformat()
        }
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Portfolio recommendations error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Portfolio recommendations failed: {str(e)}")

# ============================================================================
# AI COST TRACKING
# ============================================================================

@router.get("/cost-tracking")
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
        
        return {
            "current_month": current_month,
            "breakdown": breakdown,
            "usage_analytics": usage_analytics,
            "budget_status": budget_status,
            "alerts": alerts
        }
        
    except Exception as e:
        logger.error(f"Cost tracking error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cost tracking failed: {str(e)}")

# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================

@router.get("/health")
async def ai_health_check():
    """
    Health check for AI components
    """
    return {
        "status": "healthy",
        "components": {
            "ai_chat": "operational",
            "strategy_templates": "operational",
            "market_intelligence": "operational",
            "performance_analytics": "operational",
            "risk_management": "operational",
            "learning_insights": "operational",
            "optimization_recommendations": "operational",
            "ai_analysis": "operational",
            "cost_tracking": "operational"
        },
        "authentication": "enabled" if AUTH_AVAILABLE else "disabled",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/status")
async def ai_status():
    """
    AI system status endpoint for frontend integration
    """
    return {
        "status": "operational",
        "service": "ai_components",
        "version": "1.0.0",
        "uptime": "operational",
        "providers": {
            "openai": "available",
            "anthropic": "available",
            "google": "available"
        },
        "features": {
            "portfolio_analysis": True,
            "market_intelligence": True,
            "strategy_generation": True,
            "risk_management": True,
            "cost_tracking": True
        },
        "timestamp": datetime.now().isoformat()
    }

@router.get("/preferences")
async def get_ai_preferences():
    """
    Get AI preferences for frontend
    """
    return {
        "success": True,
        "preferences": {
            "default_provider": "openai",
            "analysis_depth": "comprehensive",
            "risk_tolerance": "moderate",
            "update_frequency": "real_time",
            "notifications": {
                "portfolio_alerts": True,
                "market_updates": True,
                "strategy_recommendations": True
            }
        },
        "timestamp": datetime.now().isoformat()
    }

@router.post("/preferences")
async def save_ai_preferences(preferences: Dict[str, Any]):
    """
    Save AI preferences from frontend
    """
    try:
        logger.info(f"Saving AI preferences: {preferences}")
        
        # Mock save - replace with actual database save
        return {
            "success": True,
            "message": "AI preferences saved successfully",
            "preferences": preferences,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to save AI preferences: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save preferences: {str(e)}")

@router.post("/validate-key")
async def validate_ai_key(request: Dict[str, Any]):
    """
    Validate AI API key for frontend
    """
    try:
        provider = request.get('provider', '')
        api_key = request.get('api_key', '')
        
        logger.info(f"Validating API key for provider: {provider}")
        
        # Mock validation - replace with actual API key validation
        if not provider or not api_key:
            return {
                "valid": False,
                "message": "Provider and API key are required",
                "provider": provider
            }
        
        # Simulate validation
        is_valid = len(api_key) > 10  # Simple mock validation
        
        return {
            "valid": is_valid,
            "message": "API key is valid" if is_valid else "Invalid API key format",
            "provider": provider,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"API key validation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

@router.post("/message")
async def send_ai_message(request: Dict[str, Any]):
    """
    Send message to AI for frontend chat integration
    """
    try:
        message = request.get('message', '')
        context = request.get('context', {})
        
        logger.info(f"AI message request: {message[:100]}...")
        
        # Mock AI response - replace with actual AI integration
        ai_response = {
            "success": True,
            "response": f"AI Response: I understand you're asking about '{message}'. Based on the current market conditions and your portfolio, here's my analysis...",
            "message_id": f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "context": context,
            "timestamp": datetime.now().isoformat()
        }
        
        return ai_response
        
    except Exception as e:
        logger.error(f"AI message error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI message failed: {str(e)}")

@router.post("/strategy/generate")
async def generate_strategy(parameters: Dict[str, Any]):
    """
    Generate trading strategy using AI
    """
    try:
        logger.info(f"Strategy generation request: {parameters}")
        
        # Mock strategy generation - replace with actual AI strategy generation
        strategy = {
            "success": True,
            "strategy": {
                "name": "AI Generated Strategy",
                "type": "momentum",
                "description": "AI-generated momentum strategy based on your parameters",
                "parameters": parameters,
                "expected_return": 12.5,
                "risk_level": "moderate",
                "timeframe": "medium_term",
                "entry_conditions": [
                    "RSI < 30 (oversold)",
                    "Volume > 1.5x average",
                    "Price above 20-day MA"
                ],
                "exit_conditions": [
                    "RSI > 70 (overbought)",
                    "Stop loss at -5%",
                    "Take profit at +15%"
                ]
            },
            "strategy_id": f"strat_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat()
        }
        
        return strategy
        
    except Exception as e:
        logger.error(f"Strategy generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Strategy generation failed: {str(e)}")

@router.get("/market/analyze")
async def get_market_analysis(symbol: str):
    """
    Get AI market analysis for a symbol
    """
    try:
        logger.info(f"Market analysis request for symbol: {symbol}")
        
        # Mock market analysis - replace with actual AI analysis
        analysis = {
            "success": True,
            "symbol": symbol,
            "analysis": {
                "sentiment": "bullish",
                "confidence": 0.75,
                "price_target": 2650.00,
                "support_levels": [2400, 2350, 2300],
                "resistance_levels": [2550, 2600, 2650],
                "technical_indicators": {
                    "rsi": 58.5,
                    "macd": "bullish_crossover",
                    "moving_averages": "above_20_50_200"
                },
                "news_sentiment": "positive",
                "recommendation": "BUY",
                "risk_factors": [
                    "Market volatility",
                    "Sector rotation risk"
                ]
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return analysis
        
    except Exception as e:
        logger.error(f"Market analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Market analysis failed: {str(e)}")

@router.get("/signals/get")
async def get_trading_signals(user_id: str):
    """
    Get AI trading signals for user
    """
    try:
        logger.info(f"Trading signals request for user: {user_id}")
        
        # Mock trading signals - replace with actual AI signals
        signals = {
            "success": True,
            "user_id": user_id,
            "signals": [
                {
                    "signal_id": "sig_001",
                    "symbol": "RELIANCE",
                    "action": "BUY",
                    "confidence": 0.85,
                    "entry_price": 2480.00,
                    "target_price": 2650.00,
                    "stop_loss": 2350.00,
                    "quantity": 50,
                    "reason": "Strong momentum with volume breakout",
                    "generated_at": datetime.now().isoformat()
                },
                {
                    "signal_id": "sig_002", 
                    "symbol": "TCS",
                    "action": "SELL",
                    "confidence": 0.72,
                    "entry_price": 3920.00,
                    "target_price": 3650.00,
                    "stop_loss": 4050.00,
                    "quantity": 25,
                    "reason": "Overbought conditions with resistance at current levels",
                    "generated_at": datetime.now().isoformat()
                }
            ],
            "total_signals": 2,
            "timestamp": datetime.now().isoformat()
        }
        
        return signals
        
    except Exception as e:
        logger.error(f"Trading signals error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Trading signals failed: {str(e)}")

if __name__ == "__main__":
    print("AI Components Router loaded successfully")
    print("Available endpoints:")
    for route in router.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            print(f"  {list(route.methods)[0]} {route.path}")