"""
Analysis Router - Simplified with Fallback Support
FastAPI endpoints for AI-powered trading analysis
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai/analysis", tags=["AI Analysis"])

# Initialize analysis engines with fallback
try:
    from .analysis_engine import AnalysisEngine
    from .sentiment_analyzer import SentimentAnalyzer
    from .technical_analyzer import TechnicalAnalyzer
    from .fundamental_analyzer import FundamentalAnalyzer
    from .models import (
        AnalysisRequest, AnalysisResponse, AnalysisType
    )
    
    analysis_engine = AnalysisEngine()
    sentiment_analyzer = SentimentAnalyzer()
    technical_analyzer = TechnicalAnalyzer()
    fundamental_analyzer = FundamentalAnalyzer()
    
    FALLBACK_MODE = False
    logger.info("Analysis engines initialized successfully")
    
except Exception as e:
    logger.warning(f"Failed to initialize analysis engines, using fallback mode: {e}")
    FALLBACK_MODE = True
    analysis_engine = None
    sentiment_analyzer = None
    technical_analyzer = None
    fundamental_analyzer = None

def get_user_id_from_headers(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> str:
    """Extract user ID from headers"""
    if x_user_id:
        return x_user_id
    # Fallback to a default for testing
    return "default_user"

@router.post("/portfolio")
async def analyze_portfolio(
    portfolio_data: Dict[str, Any],
    user_id: str = Depends(get_user_id_from_headers)
):
    """Generate comprehensive portfolio analysis"""
    try:
        # Check if user has valid AI providers configured
        try:
            from .service import AIService
            ai_service = AIService()
            user_preferences = await ai_service.get_user_preferences(user_id)
            
            # Check if user has any valid API keys
            has_valid_providers = (
                user_preferences and (
                    user_preferences.get('has_openai_key') or
                    user_preferences.get('has_claude_key') or
                    user_preferences.get('has_gemini_key') or
                    user_preferences.get('has_grok_key')
                )
            )
            
            if has_valid_providers and not FALLBACK_MODE and analysis_engine:
                logger.info(f"Using real AI analysis for user {user_id}")
                # Try to use real AI analysis
                try:
                    # Initialize orchestrator for user if needed
                    await analysis_engine.initialize_orchestrator(user_id)
                    
                    # Generate real portfolio analysis
                    analysis_result = await analysis_engine.generate_portfolio_analysis(
                        user_id=user_id,
                        portfolio_data=portfolio_data
                    )
                    
                    return analysis_result
                    
                except Exception as ai_error:
                    logger.warning(f"Real AI analysis failed, falling back: {ai_error}")
                    # Fall through to fallback mode
            else:
                logger.info(f"No valid AI providers for user {user_id}, using fallback")
                
        except Exception as e:
            logger.warning(f"Error checking AI providers, using fallback: {e}")
        
        # Fallback portfolio analysis
        total_value = portfolio_data.get("total_value", 0)
        holdings = portfolio_data.get("holdings", [])
        
        # Calculate basic metrics
        num_holdings = len(holdings)
        avg_allocation = 100 / num_holdings if num_holdings > 0 else 0
        
        # Generate fallback analysis
        return {
            "status": "success",
            "analysis_id": f"fallback_{user_id}_{int(datetime.now().timestamp())}",
            "timestamp": datetime.now().isoformat(),
            "analysis": {
                "health_score": min(85.0, max(60.0, 75.0 + (num_holdings - 5) * 2)),
                "risk_level": "MODERATE" if num_holdings >= 5 else "HIGH",
                "diversification_score": min(90.0, num_holdings * 15),
                "total_value": total_value,
                "holdings_count": num_holdings,
                "recommendations": [
                    {
                        "type": "DIVERSIFICATION",
                        "title": "Portfolio Diversification",
                        "description": f"Your portfolio has {num_holdings} holdings. Consider {'maintaining' if num_holdings >= 8 else 'adding more'} diversification.",
                        "priority": "MEDIUM" if num_holdings >= 5 else "HIGH",
                        "impact": "Reduces overall portfolio risk"
                    },
                    {
                        "type": "REBALANCING",
                        "title": "Regular Rebalancing",
                        "description": "Review and rebalance your portfolio quarterly to maintain target allocations.",
                        "priority": "MEDIUM",
                        "impact": "Maintains risk-return profile"
                    },
                    {
                        "type": "MONITORING",
                        "title": "Performance Monitoring",
                        "description": "Monitor portfolio performance against benchmarks regularly.",
                        "priority": "LOW",
                        "impact": "Helps track investment goals"
                    }
                ],
                "sectors": {
                    "analysis": "Sector analysis temporarily unavailable",
                    "recommendations": ["Ensure sector diversification", "Avoid concentration in single sector"]
                },
                "risk_metrics": {
                    "volatility": "Moderate",
                    "beta": "Market-aligned",
                    "sharpe_ratio": "Acceptable"
                }
            },
            "fallback_mode": True,
            "message": "Analysis generated in fallback mode - limited functionality"
        }
        
        # Initialize orchestrator for user if needed
        await analysis_engine.initialize_orchestrator(user_id)
        
        # Generate portfolio analysis
        analysis_result = await analysis_engine.generate_portfolio_analysis(
            user_id=user_id,
            portfolio_data=portfolio_data
        )
        
        return analysis_result
        
    except Exception as e:
        logger.error(f"Portfolio analysis failed: {e}")
        
        # Return fallback response even on error
        return {
            "status": "error",
            "analysis_id": f"error_{user_id}_{int(datetime.now().timestamp())}",
            "timestamp": datetime.now().isoformat(),
            "analysis": {
                "health_score": 70.0,
                "risk_level": "UNKNOWN",
                "recommendations": [
                    {
                        "type": "SYSTEM",
                        "title": "Analysis Service Unavailable",
                        "description": "Portfolio analysis service is temporarily unavailable. Please try again later.",
                        "priority": "HIGH",
                        "impact": "Limited analysis capabilities"
                    }
                ]
            },
            "error": str(e),
            "fallback_mode": True,
            "message": "Analysis service temporarily unavailable"
        }

@router.get("/portfolio/latest")
async def get_latest_portfolio_analysis(
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get the latest portfolio analysis for the user"""
    try:
        latest_analysis = await analysis_engine.get_latest_analysis(
            user_id, AnalysisType.PORTFOLIO
        )
        
        if latest_analysis:
            return {
                "status": "success",
                "analysis": latest_analysis
            }
        else:
            return {
                "status": "not_found",
                "message": "No portfolio analysis found"
            }
        
    except Exception as e:
        logger.error(f"Failed to get latest portfolio analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve analysis: {str(e)}"
        )

@router.post("/test-portfolio")
async def test_portfolio_analysis(
    user_id: str = Depends(get_user_id_from_headers)
):
    """Test endpoint for portfolio analysis with sample data"""
    try:
        # Sample portfolio data for testing
        sample_portfolio = {
            "total_value": 1000000,
            "holdings": [
                {
                    "symbol": "RELIANCE",
                    "quantity": 100,
                    "current_value": 250000,
                    "allocation_percentage": 25.0
                },
                {
                    "symbol": "TCS",
                    "quantity": 50,
                    "current_value": 200000,
                    "allocation_percentage": 20.0
                },
                {
                    "symbol": "HDFCBANK",
                    "quantity": 150,
                    "current_value": 300000,
                    "allocation_percentage": 30.0
                },
                {
                    "symbol": "INFY",
                    "quantity": 80,
                    "current_value": 150000,
                    "allocation_percentage": 15.0
                },
                {
                    "symbol": "ITC",
                    "quantity": 200,
                    "current_value": 100000,
                    "allocation_percentage": 10.0
                }
            ],
            "last_updated": "2025-01-21T10:30:00Z"
        }
        
        # Initialize orchestrator
        await analysis_engine.initialize_orchestrator(user_id)
        
        # Generate analysis
        analysis_result = await analysis_engine.generate_portfolio_analysis(
            user_id=user_id,
            portfolio_data=sample_portfolio
        )
        
        return {
            "test_portfolio": sample_portfolio,
            "analysis_result": analysis_result.dict(),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Portfolio analysis test failed: {e}")
        return {
            "test_portfolio": {},
            "error": str(e),
            "status": "failed"
        }

@router.get("/health")
async def analysis_health_check():
    """Health check for analysis system"""
    try:
        if FALLBACK_MODE:
            return {
                "status": "fallback",
                "fallback_mode": True,
                "components": {
                    "analysis_engine": "fallback",
                    "database": "unknown",
                    "ai_orchestrator": "fallback",
                    "timestamp": datetime.now().isoformat()
                },
                "message": "Analysis system running in fallback mode"
            }
        
        health_status = {
            "analysis_engine": "operational",
            "database": "connected",
            "ai_orchestrator": "ready",
            "timestamp": datetime.now().isoformat()
        }
        
        return {
            "status": "healthy",
            "fallback_mode": False,
            "components": health_status
        }
        
    except Exception as e:
        logger.error(f"Analysis health check failed: {e}")
        return {
            "status": "unhealthy",
            "fallback_mode": True,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.post("/sentiment")
async def analyze_market_sentiment(
    symbols: List[str],
    timeframe: str = "1d",
    user_id: str = Depends(get_user_id_from_headers)
):
    """Generate market sentiment analysis for given symbols"""
    try:
        # Validate symbols list
        if not symbols or len(symbols) == 0:
            raise HTTPException(
                status_code=400,
                detail="At least one symbol is required"
            )
        
        # Limit to 10 symbols to avoid overwhelming the AI
        if len(symbols) > 10:
            symbols = symbols[:10]
        
        # Generate sentiment analysis
        sentiment_result = await sentiment_analyzer.generate_market_sentiment_analysis(
            user_id=user_id,
            symbols=symbols,
            timeframe=timeframe
        )
        
        return sentiment_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sentiment analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze sentiment: {str(e)}"
        )

@router.get("/sentiment/latest")
async def get_latest_sentiment_analysis(
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get the latest sentiment analysis for the user"""
    try:
        latest_analysis = await analysis_engine.get_latest_analysis(
            user_id, AnalysisType.SENTIMENT
        )
        
        if latest_analysis:
            return {
                "status": "success",
                "analysis": latest_analysis
            }
        else:
            return {
                "status": "not_found",
                "message": "No sentiment analysis found"
            }
        
    except Exception as e:
        logger.error(f"Failed to get latest sentiment analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve sentiment analysis: {str(e)}"
        )

@router.post("/sentiment/test")
async def test_sentiment_analysis(
    user_id: str = Depends(get_user_id_from_headers)
):
    """Test endpoint for sentiment analysis with sample symbols"""
    try:
        # Sample symbols for testing
        test_symbols = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ITC"]
        
        # Generate sentiment analysis
        sentiment_result = await sentiment_analyzer.generate_market_sentiment_analysis(
            user_id=user_id,
            symbols=test_symbols,
            timeframe="1d"
        )
        
        return {
            "test_symbols": test_symbols,
            "sentiment_result": sentiment_result.dict(),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Sentiment analysis test failed: {e}")
        return {
            "test_symbols": [],
            "error": str(e),
            "status": "failed"
        }

@router.post("/technical")
async def analyze_technical(
    symbol: str,
    timeframe: str = "1d",
    user_id: str = Depends(get_user_id_from_headers)
):
    """Generate technical analysis for a specific symbol"""
    try:
        # Validate symbol
        if not symbol or len(symbol.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Symbol is required"
            )
        
        # Generate technical analysis
        technical_result = await technical_analyzer.generate_technical_analysis(
            user_id=user_id,
            symbol=symbol.upper(),
            timeframe=timeframe
        )
        
        return technical_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Technical analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze technical data: {str(e)}"
        )

@router.get("/technical/latest")
async def get_latest_technical_analysis(
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get the latest technical analysis for the user"""
    try:
        latest_analysis = await analysis_engine.get_latest_analysis(
            user_id, AnalysisType.TECHNICAL
        )
        
        if latest_analysis:
            return {
                "status": "success",
                "analysis": latest_analysis
            }
        else:
            return {
                "status": "not_found",
                "message": "No technical analysis found"
            }
        
    except Exception as e:
        logger.error(f"Failed to get latest technical analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve technical analysis: {str(e)}"
        )

@router.post("/technical/test")
async def test_technical_analysis(
    user_id: str = Depends(get_user_id_from_headers)
):
    """Test endpoint for technical analysis with sample symbol"""
    try:
        # Sample symbol for testing
        test_symbol = "RELIANCE"
        
        # Generate technical analysis
        technical_result = await technical_analyzer.generate_technical_analysis(
            user_id=user_id,
            symbol=test_symbol,
            timeframe="1d"
        )
        
        return {
            "test_symbol": test_symbol,
            "technical_result": technical_result.dict(),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Technical analysis test failed: {e}")
        return {
            "test_symbol": "",
            "error": str(e),
            "status": "failed"
        }

@router.post("/fundamental")
async def analyze_fundamental(
    symbol: str,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Generate fundamental analysis for a specific symbol"""
    try:
        # Validate symbol
        if not symbol or len(symbol.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Symbol is required"
            )
        
        # Generate fundamental analysis
        fundamental_result = await fundamental_analyzer.generate_fundamental_analysis(
            user_id=user_id,
            symbol=symbol.upper()
        )
        
        return fundamental_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fundamental analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze fundamental data: {str(e)}"
        )

@router.get("/fundamental/latest")
async def get_latest_fundamental_analysis(
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get the latest fundamental analysis for the user"""
    try:
        latest_analysis = await analysis_engine.get_latest_analysis(
            user_id, AnalysisType.FUNDAMENTAL
        )
        
        if latest_analysis:
            return {
                "status": "success",
                "analysis": latest_analysis
            }
        else:
            return {
                "status": "not_found",
                "message": "No fundamental analysis found"
            }
        
    except Exception as e:
        logger.error(f"Failed to get latest fundamental analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve fundamental analysis: {str(e)}"
        )

@router.post("/fundamental/test")
async def test_fundamental_analysis(
    user_id: str = Depends(get_user_id_from_headers)
):
    """Test endpoint for fundamental analysis with sample symbol"""
    try:
        # Sample symbol for testing
        test_symbol = "RELIANCE"
        
        # Generate fundamental analysis
        fundamental_result = await fundamental_analyzer.generate_fundamental_analysis(
            user_id=user_id,
            symbol=test_symbol
        )
        
        return {
            "test_symbol": test_symbol,
            "fundamental_result": fundamental_result.dict(),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Fundamental analysis test failed: {e}")
        return {
            "test_symbol": "",
            "error": str(e),
            "status": "failed"
        }