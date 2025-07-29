"""
Market Context Service - Real-time market intelligence for AI analysis
Provides comprehensive market data, sector trends, and sentiment analysis
"""
import logging
import asyncio
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
import json

logger = logging.getLogger(__name__)

class MarketContextService:
    """Service for fetching and analyzing market context data"""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes cache
        self.last_update = None
        
    async def get_comprehensive_market_context(self) -> Dict[str, Any]:
        """
        Get comprehensive market context for AI analysis
        Returns:
            Dictionary with complete market intelligence
        """
        try:
            # Check cache first
            cache_key = "comprehensive_context"
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]
            
            # Fetch fresh market data
            context = await self._fetch_market_intelligence()
            
            # Cache the result
            self.cache[cache_key] = context
            self.last_update = datetime.now()
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to get comprehensive market context: {e}")
            return self._get_fallback_context()
    
    async def _fetch_market_intelligence(self) -> Dict[str, Any]:
        """Fetch comprehensive market intelligence"""
        
        # Get current market data
        market_data = await self._get_current_market_data()
        
        # Get sector performance
        sector_data = await self._get_sector_performance()
        
        # Get market sentiment
        sentiment_data = await self._get_market_sentiment()
        
        # Get recent events
        events_data = await self._get_recent_market_events()
        
        # Combine all data
        return {
            "timestamp": datetime.now().isoformat(),
            "market_data": market_data,
            "sector_performance": sector_data,
            "market_sentiment": sentiment_data,
            "recent_events": events_data,
            "trading_session": self._get_trading_session(),
            "data_quality": self._calculate_data_quality(market_data, sector_data),
            "ai_context_summary": self._generate_ai_context_summary(
                market_data, sector_data, sentiment_data, events_data
            )
        } 
   
    async def _get_current_market_data(self) -> Dict[str, Any]:
        """Get current market indices and basic data"""
        try:
            # In a real implementation, this would fetch from market data APIs
            # For now, we'll simulate with realistic data
            
            # Check if we have recent data in database
            from app.database.service import get_market_context
            db_context = get_market_context()
            
            if db_context and self._is_recent_data(db_context.get('date')):
                return {
                    "nifty_50": {
                        "value": db_context.get('nifty_value', 21500),
                        "change": db_context.get('nifty_change', 0),
                        "change_percent": db_context.get('nifty_change_percent', 0),
                        "trend": db_context.get('nifty_trend', 'neutral')
                    },
                    "sensex": {
                        "value": db_context.get('sensex_value', 71000),
                        "change": db_context.get('sensex_change', 0),
                        "change_percent": db_context.get('sensex_change_percent', 0)
                    },
                    "market_status": db_context.get('market_status', 'open'),
                    "volatility_index": db_context.get('volatility_index', 15.0),
                    "market_breadth": {
                        "advances": db_context.get('advances_count', 1500),
                        "declines": db_context.get('declines_count', 1200),
                        "unchanged": db_context.get('unchanged_count', 300)
                    },
                    "volume": db_context.get('market_volume', 4000000000),
                    "data_source": "database"
                }
            
            # Fallback to simulated current data
            return await self._simulate_current_market_data()
            
        except Exception as e:
            logger.error(f"Failed to get current market data: {e}")
            return await self._simulate_current_market_data()
    
    async def _simulate_current_market_data(self) -> Dict[str, Any]:
        """Simulate realistic current market data"""
        import random
        
        # Base values with realistic variations
        base_nifty = 21500
        base_sensex = 71000
        
        # Random but realistic changes
        nifty_change = random.uniform(-200, 200)
        nifty_change_percent = (nifty_change / base_nifty) * 100
        
        sensex_change = nifty_change * 3.3  # Approximate correlation
        sensex_change_percent = (sensex_change / base_sensex) * 100
        
        return {
            "nifty_50": {
                "value": round(base_nifty + nifty_change, 2),
                "change": round(nifty_change, 2),
                "change_percent": round(nifty_change_percent, 2),
                "trend": "bullish" if nifty_change > 50 else "bearish" if nifty_change < -50 else "neutral"
            },
            "sensex": {
                "value": round(base_sensex + sensex_change, 2),
                "change": round(sensex_change, 2),
                "change_percent": round(sensex_change_percent, 2)
            },
            "market_status": self._get_market_status(),
            "volatility_index": round(random.uniform(12, 25), 2),
            "market_breadth": {
                "advances": random.randint(1200, 1800),
                "declines": random.randint(1000, 1500),
                "unchanged": random.randint(200, 400)
            },
            "volume": random.randint(3000000000, 5000000000),
            "data_source": "simulated"
        }
    
    async def _get_sector_performance(self) -> Dict[str, Any]:
        """Get sector-wise performance data"""
        try:
            # Check database for recent sector data
            from app.database.service import get_sector_performance
            db_sectors = get_sector_performance(days_back=1)
            
            if db_sectors:
                sectors = {}
                for sector in db_sectors:
                    sectors[sector['sector_name']] = {
                        "change_percent": sector['sector_change_percent'],
                        "trend": sector['sector_trend'],
                        "volume": sector['volume'],
                        "pe_ratio": sector['pe_ratio'],
                        "analyst_rating": sector['analyst_rating'],
                        "momentum_score": sector['momentum_score']
                    }
                return {
                    "sectors": sectors,
                    "data_source": "database"
                }
            
            # Fallback to simulated sector data
            return await self._simulate_sector_performance()
            
        except Exception as e:
            logger.error(f"Failed to get sector performance: {e}")
            return await self._simulate_sector_performance()
    
    async def _simulate_sector_performance(self) -> Dict[str, Any]:
        """Simulate realistic sector performance data"""
        import random
        
        sectors = {
            "Information Technology": {
                "change_percent": round(random.uniform(-2, 3), 2),
                "trend": random.choice(["bullish", "neutral", "bearish"]),
                "volume": random.randint(800000000, 1200000000),
                "pe_ratio": round(random.uniform(25, 35), 1),
                "analyst_rating": random.choice(["buy", "hold", "sell"]),
                "momentum_score": random.randint(40, 80)
            },
            "Banking": {
                "change_percent": round(random.uniform(-1.5, 2), 2),
                "trend": random.choice(["bullish", "neutral", "bearish"]),
                "volume": random.randint(1000000000, 1500000000),
                "pe_ratio": round(random.uniform(12, 20), 1),
                "analyst_rating": random.choice(["buy", "hold", "sell"]),
                "momentum_score": random.randint(35, 75)
            },
            "Pharmaceuticals": {
                "change_percent": round(random.uniform(-1, 2.5), 2),
                "trend": random.choice(["bullish", "neutral", "bearish"]),
                "volume": random.randint(400000000, 800000000),
                "pe_ratio": round(random.uniform(20, 30), 1),
                "analyst_rating": random.choice(["buy", "hold", "sell"]),
                "momentum_score": random.randint(45, 85)
            },
            "FMCG": {
                "change_percent": round(random.uniform(-0.5, 1.5), 2),
                "trend": random.choice(["bullish", "neutral", "bearish"]),
                "volume": random.randint(300000000, 600000000),
                "pe_ratio": round(random.uniform(35, 50), 1),
                "analyst_rating": random.choice(["buy", "hold", "sell"]),
                "momentum_score": random.randint(50, 70)
            },
            "Energy": {
                "change_percent": round(random.uniform(-2, 2), 2),
                "trend": random.choice(["bullish", "neutral", "bearish"]),
                "volume": random.randint(600000000, 1000000000),
                "pe_ratio": round(random.uniform(15, 25), 1),
                "analyst_rating": random.choice(["buy", "hold", "sell"]),
                "momentum_score": random.randint(30, 70)
            }
        }
        
        return {
            "sectors": sectors,
            "data_source": "simulated"
        }
    
    async def _get_market_sentiment(self) -> Dict[str, Any]:
        """Get overall market sentiment analysis"""
        try:
            import random
            
            # Simulate sentiment analysis
            sentiment_score = random.uniform(-1, 1)  # -1 to 1 scale
            
            if sentiment_score > 0.3:
                sentiment = "bullish"
            elif sentiment_score < -0.3:
                sentiment = "bearish"
            else:
                sentiment = "neutral"
            
            return {
                "overall_sentiment": sentiment,
                "sentiment_score": round(sentiment_score, 2),
                "fear_greed_index": random.randint(20, 80),
                "confidence_level": random.randint(60, 90),
                "key_factors": [
                    "Global market trends",
                    "Domestic economic indicators", 
                    "Corporate earnings outlook",
                    "Policy announcements"
                ],
                "data_source": "simulated"
            }
            
        except Exception as e:
            logger.error(f"Failed to get market sentiment: {e}")
            return {
                "overall_sentiment": "neutral",
                "sentiment_score": 0.0,
                "fear_greed_index": 50,
                "confidence_level": 70,
                "key_factors": ["Market analysis unavailable"],
                "data_source": "fallback"
            }
    
    async def _get_recent_market_events(self) -> List[Dict[str, Any]]:
        """Get recent significant market events"""
        try:
            # Check database for recent events
            from app.database.service import get_market_events
            db_events = get_market_events(days_back=7, impact_level="high")
            
            if db_events:
                return [
                    {
                        "title": event['event_title'],
                        "type": event['event_type'],
                        "impact_level": event['impact_level'],
                        "date": event['event_date'],
                        "description": event['event_description'],
                        "affected_sectors": event['affected_sectors']
                    }
                    for event in db_events[:5]  # Top 5 events
                ]
            
            # Fallback to simulated events
            return [
                {
                    "title": "RBI Policy Meeting Outcome",
                    "type": "policy",
                    "impact_level": "high",
                    "date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
                    "description": "Central bank maintains status quo on interest rates",
                    "affected_sectors": ["Banking", "NBFC", "Real Estate"]
                },
                {
                    "title": "Q3 Earnings Season Begins",
                    "type": "earnings",
                    "impact_level": "medium",
                    "date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
                    "description": "Major companies start reporting quarterly results",
                    "affected_sectors": ["All Sectors"]
                }
            ]
            
        except Exception as e:
            logger.error(f"Failed to get recent market events: {e}")
            return [] 
   
    def _get_trading_session(self) -> str:
        """Determine current trading session"""
        try:
            now = datetime.now()
            hour = now.hour
            minute = now.minute
            
            # Indian market hours (9:15 AM to 3:30 PM IST)
            if hour < 9 or (hour == 9 and minute < 15):
                return "pre_market"
            elif hour > 15 or (hour == 15 and minute > 30):
                return "post_market"
            elif now.weekday() >= 5:  # Weekend
                return "closed"
            else:
                return "regular"
                
        except Exception:
            return "unknown"
    
    def _get_market_status(self) -> str:
        """Get current market status"""
        session = self._get_trading_session()
        if session == "regular":
            return "open"
        elif session in ["pre_market", "post_market"]:
            return "closed"
        else:
            return "closed"
    
    def _is_recent_data(self, data_date: str) -> bool:
        """Check if data is recent (within last trading day)"""
        try:
            if not data_date:
                return False
            
            data_dt = datetime.strptime(data_date, "%Y-%m-%d").date()
            today = date.today()
            
            # Consider data recent if it's from today or last trading day
            if data_dt == today:
                return True
            
            # If today is Monday, accept Friday's data
            if today.weekday() == 0 and (today - data_dt).days <= 3:
                return True
            
            # Otherwise, accept yesterday's data
            return (today - data_dt).days <= 1
            
        except Exception:
            return False
    
    def _calculate_data_quality(self, market_data: Dict, sector_data: Dict) -> int:
        """Calculate overall data quality score"""
        try:
            score = 0
            
            # Market data quality
            if market_data.get('data_source') == 'database':
                score += 40
            elif market_data.get('data_source') == 'simulated':
                score += 20
            
            # Sector data quality
            if sector_data.get('data_source') == 'database':
                score += 30
            elif sector_data.get('data_source') == 'simulated':
                score += 15
            
            # Completeness check
            if market_data.get('nifty_50') and sector_data.get('sectors'):
                score += 20
            
            # Trading session bonus
            if self._get_trading_session() == 'regular':
                score += 10
            
            return min(100, score)
            
        except Exception:
            return 50
    
    def _generate_ai_context_summary(
        self, 
        market_data: Dict, 
        sector_data: Dict, 
        sentiment_data: Dict, 
        events_data: List
    ) -> str:
        """Generate AI-friendly context summary"""
        try:
            nifty = market_data.get('nifty_50', {})
            sentiment = sentiment_data.get('overall_sentiment', 'neutral')
            
            # Market direction
            market_direction = nifty.get('trend', 'neutral')
            change_pct = nifty.get('change_percent', 0)
            
            # Top performing sectors
            sectors = sector_data.get('sectors', {})
            top_sectors = sorted(
                sectors.items(), 
                key=lambda x: x[1].get('change_percent', 0), 
                reverse=True
            )[:3]
            
            # Recent events impact
            high_impact_events = [e for e in events_data if e.get('impact_level') == 'high']
            
            summary = f"""
CURRENT MARKET CONTEXT:
- Nifty 50: {market_direction.upper()} trend ({change_pct:+.2f}%)
- Overall Sentiment: {sentiment.upper()}
- Trading Session: {self._get_trading_session().replace('_', ' ').title()}

TOP PERFORMING SECTORS:
"""
            
            for sector, data in top_sectors:
                change = data.get('change_percent', 0)
                summary += f"- {sector}: {change:+.2f}%\n"
            
            if high_impact_events:
                summary += f"\nRECENT HIGH-IMPACT EVENTS:\n"
                for event in high_impact_events[:2]:
                    summary += f"- {event['title']} ({event['type']})\n"
            
            summary += f"\nRECOMMENDATION CONTEXT: Consider {market_direction} market trend and {sentiment} sentiment when making portfolio decisions."
            
            return summary.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate AI context summary: {e}")
            return "Market context analysis unavailable"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self.cache:
            return False
        
        if not self.last_update:
            return False
        
        # Cache is valid for 5 minutes
        return (datetime.now() - self.last_update).seconds < self.cache_ttl
    
    def _get_fallback_context(self) -> Dict[str, Any]:
        """Get fallback context when market data is unavailable"""
        return {
            "timestamp": datetime.now().isoformat(),
            "market_data": {
                "nifty_50": {"value": 21500, "change": 0, "change_percent": 0, "trend": "neutral"},
                "sensex": {"value": 71000, "change": 0, "change_percent": 0},
                "market_status": "unknown",
                "data_source": "fallback"
            },
            "sector_performance": {
                "sectors": {},
                "data_source": "fallback"
            },
            "market_sentiment": {
                "overall_sentiment": "neutral",
                "sentiment_score": 0.0,
                "fear_greed_index": 50,
                "data_source": "fallback"
            },
            "recent_events": [],
            "trading_session": "unknown",
            "data_quality": 20,
            "ai_context_summary": "Market context unavailable - using fallback data for analysis"
        }
    
    async def get_stock_specific_context(self, symbol: str) -> Dict[str, Any]:
        """Get market context specific to a stock symbol"""
        try:
            # Get stock market data
            from app.database.service import get_stock_market_data
            stock_data = get_stock_market_data(symbol, days_back=5)
            
            if stock_data:
                latest = stock_data[0]
                return {
                    "symbol": symbol,
                    "current_price": latest.get('close_price'),
                    "change_percent": latest.get('price_change_percent'),
                    "volume": latest.get('volume'),
                    "analyst_rating": latest.get('analyst_rating'),
                    "sector": latest.get('sector'),
                    "pe_ratio": latest.get('pe_ratio'),
                    "beta": latest.get('beta'),
                    "support_level": latest.get('support_level'),
                    "resistance_level": latest.get('resistance_level'),
                    "recent_news": latest.get('recent_news', []),
                    "data_available": True
                }
            
            # Fallback for unknown stocks
            return {
                "symbol": symbol,
                "data_available": False,
                "message": f"No market data available for {symbol}"
            }
            
        except Exception as e:
            logger.error(f"Failed to get stock context for {symbol}: {e}")
            return {
                "symbol": symbol,
                "data_available": False,
                "error": str(e)
            }
    
    async def get_sector_trend_analysis(self, sector: str) -> Dict[str, Any]:
        """Get detailed trend analysis for a specific sector"""
        try:
            # Get sector performance data
            from app.database.service import get_sector_performance
            sector_data = get_sector_performance(days_back=30, sector_name=sector)
            
            if sector_data:
                # Calculate trend metrics
                recent_performance = [s['sector_change_percent'] for s in sector_data if s['sector_change_percent']]
                
                if recent_performance:
                    avg_performance = sum(recent_performance) / len(recent_performance)
                    trend = "bullish" if avg_performance > 1 else "bearish" if avg_performance < -1 else "neutral"
                    
                    latest = sector_data[0]
                    return {
                        "sector": sector,
                        "trend": trend,
                        "average_performance_30d": round(avg_performance, 2),
                        "current_performance": latest.get('sector_change_percent'),
                        "analyst_rating": latest.get('analyst_rating'),
                        "risk_level": latest.get('risk_level'),
                        "growth_potential": latest.get('growth_potential'),
                        "momentum_score": latest.get('momentum_score'),
                        "top_performers": latest.get('top_performers', []),
                        "data_available": True
                    }
            
            # Fallback for unknown sectors
            return {
                "sector": sector,
                "trend": "neutral",
                "data_available": False,
                "message": f"No trend data available for {sector} sector"
            }
            
        except Exception as e:
            logger.error(f"Failed to get sector trend for {sector}: {e}")
            return {
                "sector": sector,
                "data_available": False,
                "error": str(e)
            }

# Global instance
market_context_service = MarketContextService()