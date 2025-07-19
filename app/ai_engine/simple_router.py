"""
Simple AI Engine Router - BYOAI (Bring Your Own AI)
DEBUG VERSION: 2024-07-18-3 - Preferences save fix applied
"""
from fastapi import APIRouter, Depends, Header
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

# Simple models for BYOAI
class AIPreferencesRequest(BaseModel):
    preferred_ai_provider: str = "auto"
    openai_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

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
async def ai_engine_status():
    return {
        "status": "no_key",
        "engine": "BYOAI (Bring Your Own AI)",
        "providers": ["openai", "claude", "gemini"],
        "message": "No API key configured. Add your AI key to enable features.",
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
            
            # Create key previews (first 8 chars + "...")
            openai_preview = f"{openai_key[:8]}..." if openai_key and len(openai_key) > 8 else "***"
            claude_preview = f"{claude_key[:8]}..." if claude_key and len(claude_key) > 8 else "***"
            gemini_preview = f"{gemini_key[:8]}..." if gemini_key and len(gemini_key) > 8 else "***"
            
            return AIPreferencesResponse(
                status="success",
                preferences={
                    "preferred_ai_provider": preferences.get("preferred_provider", "auto"),
                    "has_openai_key": bool(openai_key),
                    "has_claude_key": bool(claude_key),
                    "has_gemini_key": bool(gemini_key),
                    "openai_key_preview": openai_preview,
                    "claude_key_preview": claude_preview,
                    "gemini_key_preview": gemini_preview
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
                    "openai_key_preview": "",
                    "claude_key_preview": "",
                    "gemini_key_preview": ""
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
                "openai_key_preview": "",
                "claude_key_preview": "",
                "gemini_key_preview": ""
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
        preferences.gemini_api_key and preferences.gemini_api_key.strip()
    )
    
    if not has_valid_key:
        return AIPreferencesResponse(
            status="error",
            message="Preferences not saved. No AI key configured."
        )
    
    try:
        # Import database service
        from app.database.service import store_ai_preferences
        
        # Store preferences in database
        success = store_ai_preferences(
            user_id=user_id,
            openai_api_key=preferences.openai_api_key.strip() if preferences.openai_api_key else None,
            claude_api_key=preferences.claude_api_key.strip() if preferences.claude_api_key else None,
            gemini_api_key=preferences.gemini_api_key.strip() if preferences.gemini_api_key else None,
            preferred_provider=preferences.preferred_ai_provider
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
    """Send message to AI assistant - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "OpenAI Assistants API integration is planned but not yet implemented",
        "feature": "ai_message",
        "frontend_expectation": "Chat with AI trading assistant",
        "planned_features": [
            "OpenAI Assistants API integration",
            "Persistent conversation threads",
            "Context-aware responses",
            "Trading-specific assistance"
        ],
        "received_data": message_data
    }

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

    else:
        return APIKeyValidationResponse(
            valid=False,
            provider=provider,
            message="Unsupported provider. Supported: openai, claude, gemini"
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
    """Get AI engine health status"""
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
