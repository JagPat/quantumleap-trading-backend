"""
Simple AI Engine Router - BYOAI (Bring Your Own AI)
DEBUG VERSION: 2024-07-18-3 - Preferences save fix applied
"""
import time
from fastapi import APIRouter, Depends, Header
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

# Import enhanced models with fallback for missing dependencies
try:
    from .models import (
        AIPreferencesRequest, AIPreferencesResponse,
        APIKeyValidationRequest, APIKeyValidationResponse,
        SignalsResponse as AISignalsResponse,
        StrategyResponse as AIStrategyResponse,
        ChatRequest, ChatResponse,
        ErrorResponse
    )
    print("✅ Enhanced models imported successfully")
except ImportError as e:
    print(f"⚠️ Enhanced models not available, using fallback: {e}")
    # Fallback to simple models for Railway compatibility
    class AIPreferencesRequest(BaseModel):
        preferred_ai_provider: str = "auto"
        openai_api_key: Optional[str] = None
        claude_api_key: Optional[str] = None
        gemini_api_key: Optional[str] = None
        grok_api_key: Optional[str] = None
        provider_priorities: Optional[Dict[str, Any]] = None
        cost_limits: Optional[Dict[str, Any]] = None
        risk_tolerance: str = "medium"
        trading_style: str = "balanced"

    class AIPreferencesResponse(BaseModel):
        status: str
        preferences: Optional[Dict[str, Any]] = None
        message: Optional[str] = None

    class APIKeyValidationRequest(BaseModel):
        provider: str
        api_key: str

    class APIKeyValidationResponse(BaseModel):
        valid: bool
        provider: str
        message: Optional[str] = None

    class AISignalsResponse(BaseModel):
        status: str
        signals: List[Dict[str, Any]] = []
        message: Optional[str] = None

    class AIStrategyResponse(BaseModel):
        status: str
        strategy: Optional[Dict[str, Any]] = None
        message: Optional[str] = None

router = APIRouter(prefix="/api/ai", tags=["AI Engine - BYOAI"])

def get_user_id_from_headers(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> str:
    if x_user_id:
        return x_user_id
    return "default_user"

@router.get("/status")
async def ai_engine_status(user_id: str = Depends(get_user_id_from_headers)):
    """Get AI engine status based on user's configured preferences"""
    try:
        # Import database service
        from app.database.service import get_ai_preferences
        
        preferences = get_ai_preferences(user_id)
        
        if preferences and (preferences.get("openai_api_key") or preferences.get("claude_api_key") or preferences.get("gemini_api_key") or preferences.get("grok_api_key")):
            # User has configured API keys
            configured_providers = []
            if preferences.get("openai_api_key"):
                configured_providers.append("openai")
            if preferences.get("claude_api_key"):
                configured_providers.append("claude")
            if preferences.get("gemini_api_key"):
                configured_providers.append("gemini")
            if preferences.get("grok_api_key"):
                configured_providers.append("grok")
            
            return {
                "status": "configured",
                "engine": "BYOAI (Bring Your Own AI)",
                "configured_providers": configured_providers,
                "preferred_provider": preferences.get("preferred_provider", "auto"),
                "message": f"AI engine configured with {len(configured_providers)} provider(s)",
                "endpoints": [
                    "/api/ai/preferences",
                    "/api/ai/validate-key", 
                    "/api/ai/signals",
                    "/api/ai/strategy"
                ]
            }
        else:
            # No API keys configured
            return {
                "status": "no_key",
                "engine": "BYOAI (Bring Your Own AI)",
                "providers": ["openai", "claude", "gemini", "grok"],
                "message": "No API key configured. Add your AI key to enable features.",
                "endpoints": [
                    "/api/ai/preferences",
                    "/api/ai/validate-key", 
                    "/api/ai/signals",
                    "/api/ai/strategy"
                ]
            }
    except Exception as e:
        return {
            "status": "error",
            "engine": "BYOAI (Bring Your Own AI)",
            "message": f"Error checking AI status: {str(e)}",
            "endpoints": [
                "/api/ai/preferences",
                "/api/ai/validate-key", 
                "/api/ai/signals",
                "/api/ai/strategy"
            ]
        }

@router.get("/preferences", response_model=AIPreferencesResponse)
async def get_ai_preferences(user_id: str = Depends(get_user_id_from_headers)):
    """Get user AI preferences from database"""
    try:
        # Import database service
        from app.database.service import get_ai_preferences as db_get_preferences
        
        preferences = db_get_preferences(user_id)
        if preferences:
            # Format response for frontend compatibility
            openai_key = preferences.get("openai_api_key")
            claude_key = preferences.get("claude_api_key")
            gemini_key = preferences.get("gemini_api_key")
            grok_key = preferences.get("grok_api_key")
            
            # Create key previews (first 8 chars + "...")
            openai_preview = f"{openai_key[:8]}..." if openai_key and len(openai_key) > 8 else "***"
            claude_preview = f"{claude_key[:8]}..." if claude_key and len(claude_key) > 8 else "***"
            gemini_preview = f"{gemini_key[:8]}..." if gemini_key and len(gemini_key) > 8 else "***"
            grok_preview = f"{grok_key[:8]}..." if grok_key and len(grok_key) > 8 else "***"
            
            # Parse JSON fields
            import json
            provider_priorities = None
            if preferences.get("provider_priorities"):
                try:
                    provider_priorities = json.loads(preferences["provider_priorities"])
                except json.JSONDecodeError:
                    provider_priorities = None
            
            cost_limits = None
            if preferences.get("cost_limits"):
                try:
                    cost_limits = json.loads(preferences["cost_limits"])
                except json.JSONDecodeError:
                    cost_limits = None
            
            return AIPreferencesResponse(
                status="success",
                preferences={
                    "preferred_ai_provider": preferences.get("preferred_provider", "auto"),
                    "has_openai_key": bool(openai_key),
                    "has_claude_key": bool(claude_key),
                    "has_gemini_key": bool(gemini_key),
                    "has_grok_key": bool(grok_key),
                    "openai_key_preview": openai_preview,
                    "claude_key_preview": claude_preview,
                    "gemini_key_preview": gemini_preview,
                    "grok_key_preview": grok_preview,
                    "provider_priorities": provider_priorities,
                    "cost_limits": cost_limits,
                    "risk_tolerance": preferences.get("risk_tolerance", "medium"),
                    "trading_style": preferences.get("trading_style", "balanced")
                },
                message="Preferences retrieved successfully"
            )
        else:
            return AIPreferencesResponse(
                status="no_key",
                preferences={
                    "preferred_ai_provider": "auto",
                    "has_openai_key": False,
                    "has_claude_key": False,
                    "has_gemini_key": False,
                    "has_grok_key": False,
                    "openai_key_preview": "",
                    "claude_key_preview": "",
                    "gemini_key_preview": "",
                    "grok_key_preview": "",
                    "provider_priorities": None,
                    "cost_limits": None,
                    "risk_tolerance": "medium",
                    "trading_style": "balanced"
                },
                message="No preferences found. Add your AI key."
            )
    except Exception as e:
        return AIPreferencesResponse(
            status="error",
            preferences={
                "preferred_ai_provider": "auto",
                "has_openai_key": False,
                "has_claude_key": False,
                "has_gemini_key": False,
                "has_grok_key": False,
                "openai_key_preview": "",
                "claude_key_preview": "",
                "gemini_key_preview": "",
                "grok_key_preview": "",
                "provider_priorities": None,
                "cost_limits": None,
                "risk_tolerance": "medium",
                "trading_style": "balanced"
            },
            message=f"Error retrieving preferences: {str(e)}"
        )
@router.post("/preferences", response_model=AIPreferencesResponse)
async def save_ai_preferences(
    preferences: AIPreferencesRequest,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Save user AI preferences to database"""
    print("DEBUG: save_ai_preferences called - using database service")
    
    # Check if at least one API key is provided
    has_valid_key = (
        preferences.openai_api_key and preferences.openai_api_key.strip() or
        preferences.claude_api_key and preferences.claude_api_key.strip() or
        preferences.gemini_api_key and preferences.gemini_api_key.strip() or
        preferences.grok_api_key and preferences.grok_api_key.strip()
    )
    
    if not has_valid_key:
        return AIPreferencesResponse(
            status="error",
            message="Preferences not saved. No AI key configured."
        )
    
    try:
        # Import database service
        from app.database.service import store_ai_preferences
        import json
        
        # Convert provider priorities and cost limits to JSON strings
        provider_priorities_json = None
        if preferences.provider_priorities:
            provider_priorities_json = json.dumps(preferences.provider_priorities)
        
        cost_limits_json = None
        if preferences.cost_limits:
            cost_limits_json = json.dumps(preferences.cost_limits)
        
        # Store preferences in database
        success = store_ai_preferences(
            user_id=user_id,
            openai_api_key=preferences.openai_api_key.strip() if preferences.openai_api_key else None,
            claude_api_key=preferences.claude_api_key.strip() if preferences.claude_api_key else None,
            gemini_api_key=preferences.gemini_api_key.strip() if preferences.gemini_api_key else None,
            grok_api_key=preferences.grok_api_key.strip() if preferences.grok_api_key else None,
            preferred_provider=preferences.preferred_ai_provider,
            provider_priorities=provider_priorities_json,
            cost_limits=cost_limits_json,
            risk_tolerance=preferences.risk_tolerance,
            trading_style=preferences.trading_style
        )
        
        if success:
            return AIPreferencesResponse(
                status="success",
                message="Preferences saved successfully"
            )
        else:
            return AIPreferencesResponse(
                status="error",
                message="Failed to save preferences to database"
            )
    except Exception as e:
        return AIPreferencesResponse(
            status="error",
            message=f"Error saving preferences: {str(e)}"
        )
@router.get("/strategy", response_model=AIStrategyResponse)
async def get_ai_strategy(user_id: str = Depends(get_user_id_from_headers)):
    return AIStrategyResponse(
        status="no_key",
        strategy=None,
        message="No AI key configured. Cannot generate strategy."
    )

# ========================================
# PENDING BACKEND FEATURES (Frontend Support)
# ========================================

@router.post("/message")
async def send_ai_message(
    message_data: dict,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Send message to AI assistant - Basic implementation"""
    try:
        message = message_data.get("message", "")
        thread_id = message_data.get("thread_id")
        context = message_data.get("context", {})
        
        if not message.strip():
            return {
                "status": "error",
                "message": "Message cannot be empty"
            }
        
        # Get user's AI preferences
        from app.database.service import get_ai_preferences
        preferences = get_ai_preferences(user_id)
        
        if not preferences:
            return {
                "status": "error",
                "message": "No AI preferences configured. Please set up your AI keys in settings."
            }
        
        # Simple AI response based on message content
        response = generate_simple_ai_response(message, context, preferences)
        
        return {
            "status": "success",
            "message": response,
            "thread_id": thread_id or f"thread_{user_id}_{int(time.time())}",
            "timestamp": time.time()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to process message: {str(e)}"
        }

def generate_simple_ai_response(message: str, context: dict, preferences: dict) -> str:
    """Generate a simple AI response based on message content"""
    message_lower = message.lower()
    
    # Trading-related responses
    if any(word in message_lower for word in ["portfolio", "holdings", "investments"]):
        return """Based on your portfolio query, here are some general insights:

📊 **Portfolio Analysis Tips:**
• Diversify across sectors (Technology, Finance, Healthcare, etc.)
• Consider your risk tolerance and investment horizon
• Regularly rebalance your portfolio
• Monitor for over-concentration in any single stock

💡 **Next Steps:**
• Review your current asset allocation
• Check if your portfolio aligns with your goals
• Consider adding defensive stocks in volatile markets

Would you like me to analyze specific aspects of your portfolio or suggest improvements?"""
    
    elif any(word in message_lower for word in ["market", "trend", "opportunity"]):
        return """📈 **Current Market Analysis:**

🔍 **Key Trends to Watch:**
• Technology sector showing resilience
• Healthcare innovations driving growth
• Energy sector volatility due to geopolitical factors
• Financial sector benefiting from rate changes

🎯 **Opportunities:**
• Look for undervalued stocks in beaten-down sectors
• Consider defensive plays in uncertain markets
• Focus on companies with strong fundamentals
• Monitor earnings season for surprises

⚠️ **Risks:**
• Geopolitical tensions affecting global markets
• Inflation concerns impacting valuations
• Interest rate uncertainty

Remember: This is general advice. Always do your own research and consider consulting a financial advisor."""
    
    elif any(word in message_lower for word in ["strategy", "strategy", "trading"]):
        return """🎯 **Trading Strategy Suggestions:**

📋 **Strategy Types:**
1. **Value Investing**: Buy undervalued stocks with strong fundamentals
2. **Growth Investing**: Focus on companies with high growth potential
3. **Dividend Investing**: Build income through dividend-paying stocks
4. **Momentum Trading**: Follow market trends and momentum
5. **Contrarian**: Go against market sentiment when you see opportunities

🔧 **Strategy Framework:**
• Set clear entry and exit points
• Use stop-loss orders to manage risk
• Diversify across different strategies
• Keep a trading journal to track performance
• Review and adjust strategies regularly

💡 **Current Market Strategy:**
Given current market conditions, consider a balanced approach combining value and growth stocks with proper risk management.

Would you like me to elaborate on any specific strategy?"""
    
    elif any(word in message_lower for word in ["risk", "danger", "safe"]):
        return """⚠️ **Risk Assessment & Management:**

🛡️ **Key Risk Factors:**
• **Market Risk**: Overall market volatility
• **Sector Risk**: Industry-specific challenges
• **Company Risk**: Individual company performance
• **Liquidity Risk**: Ability to sell quickly
• **Currency Risk**: Exchange rate fluctuations

📊 **Risk Management Strategies:**
• Diversify across sectors and asset classes
• Use stop-loss orders to limit downside
• Don't invest more than you can afford to lose
• Regularly review and rebalance your portfolio
• Consider defensive stocks in volatile markets

🎯 **Risk Tolerance Assessment:**
• Conservative: 20-40% stocks, 60-80% bonds
• Moderate: 40-60% stocks, 40-60% bonds
• Aggressive: 60-80% stocks, 20-40% bonds

Remember: Higher potential returns usually come with higher risk."""
    
    else:
        return """🤖 **AI Trading Assistant Response:**

Thank you for your message! I'm here to help with your trading and investment questions.

💡 **I can help you with:**
• Portfolio analysis and optimization
• Market trends and opportunities
• Trading strategy development
• Risk assessment and management
• Investment research guidance

📋 **Try asking about:**
• "Analyze my portfolio and suggest improvements"
• "What are the current market trends?"
• "Generate a trading strategy for current conditions"
• "What risks should I consider?"

🔧 **Note:** This is a basic AI assistant. For more advanced features, I'll be enhanced with real AI integration soon!

How can I help you with your trading goals today?"""

@router.get("/insights/crowd")
async def get_crowd_insights(user_id: str = Depends(get_user_id_from_headers)):
    """Get crowd insights - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "Crowd intelligence features are planned but not yet implemented",
        "feature": "crowd_insights",
        "frontend_expectation": "Collective market sentiment and crowd wisdom",
        "planned_features": [
            "Social sentiment analysis",
            "Crowd wisdom aggregation",
            "Market mood indicators"
        ]
    }

@router.get("/insights/trending")
async def get_trending_insights(user_id: str = Depends(get_user_id_from_headers)):
    """Get trending insights - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "Trending insights are planned but not yet implemented",
        "feature": "trending_insights",
        "frontend_expectation": "Real-time trending market analysis",
        "planned_features": [
            "Trend detection",
            "Momentum indicators",
            "Viral market movements"
        ]
    }

@router.post("/copilot/analyze")
async def copilot_analysis(
    analysis_data: dict,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Copilot analysis - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "AI Copilot analysis is planned but not yet implemented",
        "feature": "copilot_analysis",
        "frontend_expectation": "Intelligent trading assistant analysis",
        "planned_features": [
            "Real-time market analysis",
            "Trading suggestions",
            "Risk assessment"
        ],
        "received_data": analysis_data
    }

@router.get("/copilot/recommendations")
async def get_copilot_recommendations(user_id: str = Depends(get_user_id_from_headers)):
    """Get copilot recommendations - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "Copilot recommendations are planned but not yet implemented",
        "feature": "copilot_recommendations",
        "frontend_expectation": "AI-powered trading recommendations",
        "planned_features": [
            "Personalized recommendations",
            "Portfolio optimization",
            "Risk-adjusted suggestions"
        ]
    }

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ✅ AI Key Validation Endpoint – Supports OpenAI & Claude
#    - POST /api/ai/validate-key
#    - Live validation with actual API calls
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/validate-key", response_model=APIKeyValidationResponse)
async def validate_api_key(request: APIKeyValidationRequest):
    """Validate API key against the actual provider with live API calls"""
    provider = request.provider.lower()
    api_key = request.api_key.strip()

    if not api_key:
        return APIKeyValidationResponse(
            valid=False,
            provider=provider,
            message="API key is required"
        )

    if provider == "openai":
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=api_key)
            # Test with a simple completion
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5,
            )
            return APIKeyValidationResponse(
                valid=True,
                provider=provider,
                message="OpenAI key is valid"
            )
        except Exception as e:
            return APIKeyValidationResponse(
                valid=False,
                provider=provider,
                message=f"OpenAI validation failed: {str(e)}"
            )

    elif provider == "claude":
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=api_key)
            # Test with a simple message
            response = await client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=5,
                messages=[{"role": "user", "content": "Hello"}],
            )
            return APIKeyValidationResponse(
                valid=True,
                provider=provider,
                message="Claude key is valid"
            )
        except Exception as e:
            return APIKeyValidationResponse(
                valid=False,
                provider=provider,
                message=f"Claude validation failed: {str(e)}"
            )

    elif provider == "gemini":
        try:
            import google.generativeai as genai
            import asyncio
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-pro')
            # Test with a simple generation
            response = await asyncio.to_thread(
                model.generate_content, 
                "Hello",
                generation_config=genai.types.GenerationConfig(max_output_tokens=5)
            )
            return APIKeyValidationResponse(
                valid=True,
                provider=provider,
                message="Gemini key is valid"
            )
        except Exception as e:
            return APIKeyValidationResponse(
                valid=False,
                provider=provider,
                message=f"Gemini validation failed: {str(e)}"
            )

    elif provider == "grok":
        try:
            import httpx
            # Test Grok API key with xAI API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "grok-beta",
                        "messages": [{"role": "user", "content": "Hello"}],
                        "max_tokens": 5
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return APIKeyValidationResponse(
                        valid=True,
                        provider=provider,
                        message="Grok key is valid"
                    )
                else:
                    error_detail = response.text
                    return APIKeyValidationResponse(
                        valid=False,
                        provider=provider,
                        message=f"Grok validation failed: HTTP {response.status_code} - {error_detail}"
                    )
        except Exception as e:
            return APIKeyValidationResponse(
                valid=False,
                provider=provider,
                message=f"Grok validation failed: {str(e)}"
            )

    else:
        return APIKeyValidationResponse(
            valid=False,
            provider=provider,
            message="Unsupported provider. Supported: openai, claude, gemini, grok"
        )


# ========================================
# ADDITIONAL MISSING ENDPOINTS (Frontend Support)
# ========================================

@router.post("/strategy/generate")
async def generate_strategy(
    strategy_data: dict,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Generate trading strategy - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "Strategy generation is planned but not yet implemented",
        "feature": "strategy_generation",
        "frontend_expectation": "AI-powered trading strategy generation",
        "planned_features": [
            "Technical analysis-based strategies",
            "Risk-adjusted position sizing",
            "Backtesting capabilities"
        ],
        "received_data": strategy_data
    }

@router.get("/signals")
async def get_ai_signals(user_id: str = Depends(get_user_id_from_headers)):
    """Get AI trading signals - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "AI trading signals are planned but not yet implemented",
        "feature": "ai_signals",
        "signals": [],
        "planned_features": [
            "Real-time market signals",
            "Technical analysis signals",
            "Sentiment-based signals",
            "Risk assessment signals"
        ]
    }

@router.get("/strategy/list")
async def get_strategies(user_id: str = Depends(get_user_id_from_headers)):
    """Get user strategies - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "Strategy management is planned but not yet implemented",
        "feature": "strategy_management",
        "strategies": [],
        "planned_features": [
            "Strategy library",
            "Performance tracking",
            "Strategy sharing"
        ]
    }

@router.get("/strategy/{strategy_id}")
async def get_strategy(strategy_id: str, user_id: str = Depends(get_user_id_from_headers)):
    """Get specific strategy - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "Strategy details are planned but not yet implemented",
        "feature": "strategy_details",
        "strategy_id": strategy_id,
        "planned_features": [
            "Strategy parameters",
            "Performance metrics",
            "Risk analysis"
        ]
    }

@router.post("/analysis/market")
async def generate_market_analysis(
    analysis_data: dict,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Generate market analysis - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "Market analysis is planned but not yet implemented",
        "feature": "market_analysis",
        "frontend_expectation": "Comprehensive market analysis and insights",
        "planned_features": [
            "Market trend analysis",
            "Sector performance",
            "Economic indicators"
        ],
        "received_data": analysis_data
    }

@router.post("/analysis/technical")
async def generate_technical_analysis(
    analysis_data: dict,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Generate technical analysis - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "Technical analysis is planned but not yet implemented",
        "feature": "technical_analysis",
        "frontend_expectation": "Advanced technical indicators and patterns",
        "planned_features": [
            "Chart pattern recognition",
            "Indicator analysis",
            "Support/resistance levels"
        ],
        "received_data": analysis_data
    }

@router.post("/analysis/sentiment")
async def generate_sentiment_analysis(
    analysis_data: dict,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Generate sentiment analysis - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "Sentiment analysis is planned but not yet implemented",
        "feature": "sentiment_analysis",
        "frontend_expectation": "Market sentiment and social media analysis",
        "planned_features": [
            "News sentiment analysis",
            "Social media monitoring",
            "Fear/greed indicators"
        ],
        "received_data": analysis_data
    }

@router.post("/feedback/outcome")
async def record_trade_outcome(
    feedback_data: dict,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Record trade outcome for learning - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "Trade feedback system is planned but not yet implemented",
        "feature": "trade_feedback",
        "frontend_expectation": "Learn from trade outcomes to improve strategies",
        "planned_features": [
            "Trade result tracking",
            "Strategy performance analysis",
            "Machine learning improvements"
        ],
        "received_data": feedback_data
    }

@router.get("/feedback/learning/{strategy_id}")
async def get_learning_insights(strategy_id: str, user_id: str = Depends(get_user_id_from_headers)):
    """Get learning insights for strategy - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "Learning insights are planned but not yet implemented",
        "feature": "learning_insights",
        "strategy_id": strategy_id,
        "planned_features": [
            "Performance analytics",
            "Improvement suggestions",
            "Risk assessment"
        ]
    }

@router.get("/clustering/strategies")
async def get_strategy_clustering(user_id: str = Depends(get_user_id_from_headers)):
    """Get strategy clustering analysis - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "Strategy clustering is planned but not yet implemented",
        "feature": "strategy_clustering",
        "planned_features": [
            "Strategy similarity analysis",
            "Performance clustering",
            "Risk profile grouping"
        ]
    }

@router.get("/analytics/strategy/{strategy_id}")
async def get_strategy_analytics(strategy_id: str, user_id: str = Depends(get_user_id_from_headers)):
    """Get strategy analytics - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "Strategy analytics are planned but not yet implemented",
        "feature": "strategy_analytics",
        "strategy_id": strategy_id,
        "planned_features": [
            "Performance metrics",
            "Risk analysis",
            "Sharpe ratio calculation"
        ]
    }

@router.get("/health")
async def get_ai_health(user_id: str = Depends(get_user_id_from_headers)):
    """Get AI engine health status based on user's configuration"""
    try:
        # Import database service
        from app.database.service import get_ai_preferences
        
        preferences = get_ai_preferences(user_id)
        
        if preferences and (preferences.get("openai_api_key") or preferences.get("claude_api_key") or preferences.get("gemini_api_key")):
            # User has configured API keys
            provider_status = {}
            if preferences.get("openai_api_key"):
                provider_status["openai"] = "configured"
            else:
                provider_status["openai"] = "available"
                
            if preferences.get("claude_api_key"):
                provider_status["claude"] = "configured"
            else:
                provider_status["claude"] = "available"
                
            if preferences.get("gemini_api_key"):
                provider_status["gemini"] = "configured"
            else:
                provider_status["gemini"] = "available"
            
            return {
                "status": "healthy",
                "engine": "BYOAI (Bring Your Own AI)",
                "providers": provider_status,
                "endpoints": {
                    "preferences": "operational",
                    "validate_key": "operational",
                    "signals": "operational",
                    "strategy": "operational"
                },
                "message": f"AI engine operational with {len([p for p in provider_status.values() if p == 'configured'])} configured provider(s)"
            }
        else:
            # No API keys configured
            return {
                "status": "healthy",
                "engine": "BYOAI (Bring Your Own AI)",
                "providers": {
                    "openai": "available",
                    "claude": "available", 
                    "gemini": "available"
                },
                "endpoints": {
                    "preferences": "operational",
                    "validate_key": "operational",
                    "signals": "operational",
                    "strategy": "operational"
                },
                "message": "AI engine is operational. Configure your API keys to enable features."
            }
    except Exception as e:
        return {
            "status": "error",
            "engine": "BYOAI (Bring Your Own AI)",
            "providers": {
                "openai": "error",
                "claude": "error", 
                "gemini": "error"
            },
            "endpoints": {
                "preferences": "error",
                "validate_key": "error",
                "signals": "error",
                "strategy": "error"
            },
            "message": f"AI engine error: {str(e)}"
        }
# FORCE REDEPLOY - Fri Jul 18 20:47:55 IST 2025

@router.get("/debug-db")
async def debug_database():
    """Debug endpoint to test database functions"""
    try:
        from app.database.service import init_database, store_ai_preferences, get_ai_preferences
        
        # Initialize database
        init_database()
        
        # Test storing preferences
        test_user_id = "DEBUG_USER"
        success = store_ai_preferences(
            user_id=test_user_id,
            openai_api_key="sk-debug-key",
            preferred_provider="openai"
        )
        
        # Test retrieving preferences
        preferences = get_ai_preferences(test_user_id)
        
        return {
            "status": "success",
            "database_initialized": True,
            "store_success": success,
            "retrieved_preferences": preferences is not None,
            "preferences": preferences
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }

@router.get("/debug-db")
async def debug_database():
    """Debug endpoint to test database functions"""
    try:
        from app.database.service import init_database, store_ai_preferences, get_ai_preferences
        from app.core.config import settings
        
        # Initialize database
        init_database()
        
        # Test storing preferences
        test_user_id = "DEBUG_USER"
        success = store_ai_preferences(
            user_id=test_user_id,
            openai_api_key="sk-debug-key",
            preferred_provider="openai"
        )
        
        # Test retrieving preferences
        preferences = get_ai_preferences(test_user_id)
        
        return {
            "status": "success",
            "database_path": settings.database_path,
            "database_initialized": True,
            "store_success": success,
            "retrieved_preferences": preferences is not None,
            "preferences": preferences
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }
