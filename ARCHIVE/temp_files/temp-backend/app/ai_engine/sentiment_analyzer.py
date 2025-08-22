"""
Sentiment Analyzer
Market sentiment analysis with news data integration and social media sentiment tracking
"""
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio
from .orchestrator import AIOrchestrator
from .models import AnalysisResponse, AnalysisType
from ..database.service import get_db_connection

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    """
    Market sentiment analysis engine with news and social media integration
    """
    
    def __init__(self):
        self.orchestrator = AIOrchestrator()
        
    async def generate_market_sentiment_analysis(
        self, 
        user_id: str, 
        symbols: List[str],
        timeframe: str = "1d"
    ) -> AnalysisResponse:
        """Generate market sentiment analysis for given symbols"""
        
        try:
            logger.info(f"Starting sentiment analysis for symbols: {symbols}")
            
            # Get user preferences for provider selection
            user_preferences = await self.get_user_preferences(user_id)
            
            # Fetch news and market data
            market_data = await self.fetch_market_sentiment_data(symbols, timeframe)
            
            # Build sentiment analysis prompt
            sentiment_prompt = self.build_sentiment_analysis_prompt(symbols, market_data)
            
            # Select optimal provider for sentiment analysis
            provider = await self.orchestrator.select_optimal_provider("sentiment_analysis", user_preferences)
            
            # Generate analysis using AI
            ai_response = await provider.generate_analysis(sentiment_prompt, market_data)
            
            # Process and structure the sentiment results
            sentiment_results = await self.process_sentiment_analysis_results(ai_response, symbols, market_data)
            
            # Store analysis results
            await self.store_analysis_result(
                user_id, 
                AnalysisType.SENTIMENT,
                symbols,
                market_data,
                sentiment_results,
                provider.provider_name,
                sentiment_results.get('confidence_score', 0.75)
            )
            
            return AnalysisResponse(
                status="success",
                analysis_type=AnalysisType.SENTIMENT,
                symbols=symbols,
                results=sentiment_results,
                confidence_score=sentiment_results.get('confidence_score', 0.75),
                provider_used=provider.provider_name,
                created_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Sentiment analysis failed for symbols {symbols}: {e}")
            return AnalysisResponse(
                status="error",
                analysis_type=AnalysisType.SENTIMENT,
                symbols=symbols,
                results={"error": str(e), "message": "Sentiment analysis failed"},
                confidence_score=0.0,
                provider_used="none",
                created_at=datetime.now()
            )
    
    async def fetch_market_sentiment_data(self, symbols: List[str], timeframe: str) -> Dict[str, Any]:
        """Fetch market sentiment data including news and social media"""
        
        # Placeholder implementation - in real system would fetch from news APIs
        sentiment_data = {
            "news_headlines": [],
            "social_sentiment": {},
            "market_indicators": {},
            "sector_sentiment": {},
            "timeframe": timeframe,
            "last_updated": datetime.now().isoformat()
        }
        
        # Simulate news headlines for each symbol
        for symbol in symbols:
            sentiment_data["news_headlines"].extend([
                f"{symbol} reports strong quarterly earnings beat expectations",
                f"Analysts upgrade {symbol} target price on positive outlook",
                f"Market volatility affects {symbol} trading volume",
                f"{symbol} announces new strategic partnership",
                f"Institutional investors increase stake in {symbol}"
            ])
            
            # Simulate social sentiment scores
            import random
            sentiment_data["social_sentiment"][symbol] = {
                "score": round(random.uniform(-0.5, 0.8), 2),  # Range: -1 to 1
                "volume": random.randint(50, 500),
                "trending": random.choice([True, False]),
                "mentions_24h": random.randint(100, 1000)
            }
            
            # Simulate market indicators
            sentiment_data["market_indicators"][symbol] = {
                "rsi": round(random.uniform(30, 70), 1),
                "moving_average_signal": random.choice(["bullish", "bearish", "neutral"]),
                "volume_trend": random.choice(["increasing", "decreasing", "stable"]),
                "price_momentum": random.choice(["positive", "negative", "neutral"])
            }
        
        # Overall market sentiment
        sentiment_data["overall_sentiment"] = {
            "fear_greed_index": random.randint(20, 80),  # 0-100 scale
            "market_mood": random.choice(["bullish", "bearish", "neutral"]),
            "volatility_index": round(random.uniform(12, 25), 1),
            "news_sentiment_score": round(random.uniform(-0.3, 0.6), 2)
        }
        
        return sentiment_data
    
    def build_sentiment_analysis_prompt(self, symbols: List[str], market_data: Dict[str, Any]) -> str:
        """Build AI prompt for sentiment analysis"""
        
        prompt = f"""
        As an expert market sentiment analyst, analyze the current sentiment for the following stocks: {', '.join(symbols)}
        
        MARKET DATA AVAILABLE:
        - News Headlines: {len(market_data.get('news_headlines', []))} recent headlines
        - Social Media Sentiment Scores available for each symbol
        - Technical Indicators: RSI, Moving Averages, Volume Trends
        - Overall Market Mood: {market_data.get('overall_sentiment', {}).get('market_mood', 'neutral')}
        - Fear & Greed Index: {market_data.get('overall_sentiment', {}).get('fear_greed_index', 50)}
        
        NEWS HEADLINES (Recent):
        """
        
        for headline in market_data.get('news_headlines', [])[:10]:  # Limit to 10 headlines
            prompt += f"- {headline}\n"
        
        prompt += f"""
        
        SOCIAL SENTIMENT SCORES:
        """
        
        for symbol in symbols:
            social_data = market_data.get('social_sentiment', {}).get(symbol, {})
            score = social_data.get('score', 0)
            volume = social_data.get('volume', 0)
            trending = social_data.get('trending', False)
            prompt += f"- {symbol}: Score {score:.2f} (Volume: {volume} mentions, Trending: {trending})\n"
        
        prompt += f"""
        
        ANALYSIS REQUIREMENTS:
        Please provide a comprehensive sentiment analysis covering:
        
        1. OVERALL MARKET SENTIMENT:
           - Current market mood and key drivers
           - Fear & Greed Index interpretation ({market_data.get('overall_sentiment', {}).get('fear_greed_index', 50)}/100)
           - Sector-specific sentiment trends
        
        2. INDIVIDUAL STOCK SENTIMENT:
           - Sentiment score for each symbol (-1 to +1 scale)
           - Key positive and negative factors
           - News impact assessment
           - Social media sentiment trends
        
        3. SENTIMENT INDICATORS:
           - Bullish vs Bearish signals
           - Sentiment momentum (improving/deteriorating)
           - Contrarian opportunities
        
        4. RISK FACTORS:
           - Sentiment-based risks to watch
           - Potential sentiment reversals
           - Market volatility implications
        
        5. TRADING IMPLICATIONS:
           - How sentiment affects short-term price action
           - Entry/exit timing considerations
           - Risk management based on sentiment
        
        Please provide specific sentiment scores and actionable insights.
        Format your response with clear sections and quantitative assessments where possible.
        """
        
        return prompt    

    async def process_sentiment_analysis_results(
        self, 
        ai_response: str, 
        symbols: List[str],
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process and structure sentiment analysis results"""
        
        # Calculate quantitative sentiment metrics
        sentiment_metrics = self.calculate_sentiment_metrics(symbols, market_data)
        
        # Structure the results
        results = {
            "ai_analysis": ai_response,
            "sentiment_metrics": sentiment_metrics,
            "individual_scores": self.extract_individual_sentiment_scores(symbols, market_data),
            "market_mood": market_data.get('overall_sentiment', {}).get('market_mood', 'neutral'),
            "fear_greed_index": market_data.get('overall_sentiment', {}).get('fear_greed_index', 50),
            "sentiment_summary": self.generate_sentiment_summary(sentiment_metrics),
            "confidence_score": 0.75,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        return results
    
    def calculate_sentiment_metrics(self, symbols: List[str], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate quantitative sentiment metrics"""
        
        social_sentiment = market_data.get('social_sentiment', {})
        
        # Calculate average sentiment
        sentiment_scores = [
            social_sentiment.get(symbol, {}).get('score', 0) 
            for symbol in symbols
        ]
        
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        
        # Count bullish vs bearish
        bullish_count = sum(1 for score in sentiment_scores if score > 0.1)
        bearish_count = sum(1 for score in sentiment_scores if score < -0.1)
        neutral_count = len(sentiment_scores) - bullish_count - bearish_count
        
        return {
            "average_sentiment": round(avg_sentiment, 3),
            "bullish_stocks": bullish_count,
            "bearish_stocks": bearish_count,
            "neutral_stocks": neutral_count,
            "sentiment_range": {
                "min": min(sentiment_scores) if sentiment_scores else 0,
                "max": max(sentiment_scores) if sentiment_scores else 0
            },
            "total_social_volume": sum(
                social_sentiment.get(symbol, {}).get('volume', 0) 
                for symbol in symbols
            )
        }
    
    def extract_individual_sentiment_scores(self, symbols: List[str], market_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Extract individual sentiment scores for each symbol"""
        
        scores = {}
        social_sentiment = market_data.get('social_sentiment', {})
        
        for symbol in symbols:
            social_data = social_sentiment.get(symbol, {})
            scores[symbol] = {
                "sentiment_score": social_data.get('score', 0),
                "social_volume": social_data.get('volume', 0),
                "trending": social_data.get('trending', False),
                "mentions_24h": social_data.get('mentions_24h', 0),
                "sentiment_label": self.get_sentiment_label(social_data.get('score', 0))
            }
        
        return scores
    
    def get_sentiment_label(self, score: float) -> str:
        """Convert sentiment score to label"""
        if score > 0.5:
            return "Very Bullish"
        elif score > 0.2:
            return "Bullish"
        elif score > -0.2:
            return "Neutral"
        elif score > -0.5:
            return "Bearish"
        else:
            return "Very Bearish"
    
    def generate_sentiment_summary(self, sentiment_metrics: Dict[str, Any]) -> str:
        """Generate a summary of sentiment analysis"""
        
        avg_sentiment = sentiment_metrics.get('average_sentiment', 0)
        bullish_count = sentiment_metrics.get('bullish_stocks', 0)
        bearish_count = sentiment_metrics.get('bearish_stocks', 0)
        
        if avg_sentiment > 0.2:
            mood = "predominantly bullish"
        elif avg_sentiment < -0.2:
            mood = "predominantly bearish"
        else:
            mood = "mixed to neutral"
        
        return f"Market sentiment is {mood} with {bullish_count} bullish and {bearish_count} bearish signals detected."
    
    async def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's AI preferences"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT preferred_provider, provider_priorities, cost_limits, 
                       risk_tolerance, trading_style, openai_api_key, 
                       claude_api_key, gemini_api_key, grok_api_key
                FROM ai_user_preferences
                WHERE user_id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    "preferred_ai_provider": row[0] or "auto",
                    "provider_priorities": json.loads(row[1]) if row[1] else None,
                    "cost_limits": json.loads(row[2]) if row[2] else None,
                    "risk_tolerance": row[3] or "medium",
                    "trading_style": row[4] or "balanced",
                    "openai_api_key": row[5],
                    "claude_api_key": row[6],
                    "gemini_api_key": row[7],
                    "grok_api_key": row[8]
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get preferences for user {user_id}: {e}")
            return None
    
    async def store_analysis_result(
        self,
        user_id: str,
        analysis_type: AnalysisType,
        symbols: List[str],
        input_data: Dict[str, Any],
        analysis_result: Dict[str, Any],
        provider_used: str,
        confidence_score: float
    ):
        """Store analysis results in database"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO ai_analysis_results 
                (user_id, analysis_type, symbols, input_data, analysis_result, 
                 provider_used, confidence_score, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                analysis_type.value,
                json.dumps(symbols),
                json.dumps(input_data),
                json.dumps(analysis_result),
                provider_used,
                confidence_score,
                datetime.now()
            ))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Stored sentiment analysis result for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to store sentiment analysis result: {e}")