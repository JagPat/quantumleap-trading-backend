"""
Signal Generator
AI-powered trading signal generation with multi-factor analysis
"""
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import uuid
from .orchestrator import AIOrchestrator
from .models import TradingSignal, SignalType
from ..database.service import get_db_connection

logger = logging.getLogger(__name__)

class SignalGenerator:
    """
    Core signal generation engine with multi-factor analysis
    """
    
    def __init__(self):
        self.orchestrator = AIOrchestrator()
        
    async def generate_trading_signals(
        self, 
        user_id: str, 
        symbols: List[str],
        analysis_types: Optional[List[str]] = None,
        timeframe: str = "1d"
    ) -> Dict[str, Any]:
        """Generate trading signals for specified symbols"""
        
        try:
            logger.info(f"Generating signals for user {user_id}, symbols: {symbols}")
            
            # Default to all analysis types if none specified
            if not analysis_types:
                analysis_types = ["technical", "fundamental", "sentiment"]
            
            # Get user preferences for AI provider selection
            user_preferences = await self.get_user_preferences(user_id)
            
            # Generate signals for each symbol
            signals = []
            for symbol in symbols:
                # Generate signal with multi-factor analysis
                signal = await self.generate_signal_for_symbol(
                    user_id, 
                    symbol, 
                    analysis_types,
                    timeframe,
                    user_preferences
                )
                
                if signal:
                    signals.append(signal)
            
            # Filter and rank signals
            filtered_signals = await self.filter_and_rank_signals(signals, user_preferences)
            
            # Store signals in database
            for signal in filtered_signals:
                await self.store_signal(user_id, signal)
            
            return {
                "status": "success",
                "signals": filtered_signals,
                "total_generated": len(filtered_signals),
                "analysis_types": analysis_types,
                "timeframe": timeframe,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Signal generation failed for user {user_id}: {e}")
            return {
                "status": "error",
                "message": f"Signal generation failed: {str(e)}"
            }
    
    async def generate_signal_for_symbol(
        self, 
        user_id: str, 
        symbol: str, 
        analysis_types: List[str],
        timeframe: str,
        user_preferences: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Generate signal for a specific symbol using multi-factor analysis"""
        
        try:
            # Collect analysis results
            analysis_results = {}
            
            # Perform technical analysis if requested
            if "technical" in analysis_types:
                technical_result = await self.perform_technical_analysis(
                    user_id, symbol, timeframe, user_preferences
                )
                analysis_results["technical"] = technical_result
            
            # Perform fundamental analysis if requested
            if "fundamental" in analysis_types:
                fundamental_result = await self.perform_fundamental_analysis(
                    user_id, symbol, user_preferences
                )
                analysis_results["fundamental"] = fundamental_result
            
            # Perform sentiment analysis if requested
            if "sentiment" in analysis_types:
                sentiment_result = await self.perform_sentiment_analysis(
                    user_id, symbol, user_preferences
                )
                analysis_results["sentiment"] = sentiment_result
            
            # Combine analysis results to generate signal
            signal = await self.combine_analysis_results(
                symbol, analysis_results, timeframe
            )
            
            # Validate signal
            if await self.validate_signal(signal):
                return signal
            else:
                logger.warning(f"Signal validation failed for {symbol}")
                return None
            
        except Exception as e:
            logger.error(f"Failed to generate signal for {symbol}: {e}")
            return None 
   
    async def perform_technical_analysis(
        self, 
        user_id: str, 
        symbol: str, 
        timeframe: str,
        user_preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform technical analysis for signal generation"""
        
        try:
            # Get price data
            price_data = await self.fetch_price_data(symbol, timeframe)
            
            # Build technical analysis prompt
            technical_prompt = self.build_technical_analysis_prompt(symbol, price_data)
            
            # Select optimal provider for technical analysis
            provider = await self.orchestrator.select_optimal_provider(
                "technical_analysis", user_preferences
            )
            
            # Generate technical analysis
            technical_result = await provider.generate_structured_output(
                technical_prompt, 
                self.get_technical_analysis_schema()
            )
            
            # Extract signal from technical analysis
            signal_type, confidence, reasoning = self.extract_technical_signal(technical_result)
            
            # Calculate price targets
            current_price = price_data.get("current_price", 0)
            target_price, stop_loss = self.calculate_price_targets(
                signal_type, current_price, technical_result
            )
            
            return {
                "signal_type": signal_type,
                "confidence": confidence,
                "reasoning": reasoning,
                "current_price": current_price,
                "target_price": target_price,
                "stop_loss": stop_loss,
                "indicators": technical_result.get("indicators", {}),
                "provider_used": provider.provider_name if hasattr(provider, "provider_name") else "unknown"
            }
            
        except Exception as e:
            logger.error(f"Technical analysis failed for {symbol}: {e}")
            return {
                "signal_type": "hold",
                "confidence": 0.5,
                "reasoning": f"Technical analysis failed: {str(e)}",
                "error": str(e)
            }
    
    async def perform_fundamental_analysis(
        self, 
        user_id: str, 
        symbol: str,
        user_preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform fundamental analysis for signal generation"""
        
        try:
            # Get financial data
            financial_data = await self.fetch_financial_data(symbol)
            
            # Build fundamental analysis prompt
            fundamental_prompt = self.build_fundamental_analysis_prompt(symbol, financial_data)
            
            # Select optimal provider for fundamental analysis
            provider = await self.orchestrator.select_optimal_provider(
                "fundamental_analysis", user_preferences
            )
            
            # Generate fundamental analysis
            fundamental_result = await provider.generate_structured_output(
                fundamental_prompt, 
                self.get_fundamental_analysis_schema()
            )
            
            # Extract signal from fundamental analysis
            signal_type, confidence, reasoning = self.extract_fundamental_signal(fundamental_result)
            
            # Calculate fair value
            current_price = financial_data.get("current_price", 0)
            fair_value = fundamental_result.get("valuation", {}).get("fair_value", current_price)
            
            return {
                "signal_type": signal_type,
                "confidence": confidence,
                "reasoning": reasoning,
                "current_price": current_price,
                "fair_value": fair_value,
                "valuation_metrics": fundamental_result.get("valuation_metrics", {}),
                "provider_used": provider.provider_name if hasattr(provider, "provider_name") else "unknown"
            }
            
        except Exception as e:
            logger.error(f"Fundamental analysis failed for {symbol}: {e}")
            return {
                "signal_type": "hold",
                "confidence": 0.5,
                "reasoning": f"Fundamental analysis failed: {str(e)}",
                "error": str(e)
            }
    
    async def perform_sentiment_analysis(
        self, 
        user_id: str, 
        symbol: str,
        user_preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform sentiment analysis for signal generation"""
        
        try:
            # Get sentiment data
            sentiment_data = await self.fetch_sentiment_data(symbol)
            
            # Build sentiment analysis prompt
            sentiment_prompt = self.build_sentiment_analysis_prompt(symbol, sentiment_data)
            
            # Select optimal provider for sentiment analysis
            provider = await self.orchestrator.select_optimal_provider(
                "sentiment_analysis", user_preferences
            )
            
            # Generate sentiment analysis
            sentiment_result = await provider.generate_structured_output(
                sentiment_prompt, 
                self.get_sentiment_analysis_schema()
            )
            
            # Extract signal from sentiment analysis
            signal_type, confidence, reasoning = self.extract_sentiment_signal(sentiment_result)
            
            return {
                "signal_type": signal_type,
                "confidence": confidence,
                "reasoning": reasoning,
                "sentiment_score": sentiment_result.get("sentiment_score", 0),
                "news_sentiment": sentiment_result.get("news_sentiment", {}),
                "social_sentiment": sentiment_result.get("social_sentiment", {}),
                "provider_used": provider.provider_name if hasattr(provider, "provider_name") else "unknown"
            }
            
        except Exception as e:
            logger.error(f"Sentiment analysis failed for {symbol}: {e}")
            return {
                "signal_type": "hold",
                "confidence": 0.5,
                "reasoning": f"Sentiment analysis failed: {str(e)}",
                "error": str(e)
            }    
  
  async def combine_analysis_results(
        self, 
        symbol: str, 
        analysis_results: Dict[str, Dict[str, Any]],
        timeframe: str
    ) -> Dict[str, Any]:
        """Combine multiple analysis results into a single signal"""
        
        # Initialize signal components
        signal_types = []
        confidences = []
        reasonings = []
        
        # Process technical analysis
        if "technical" in analysis_results:
            technical = analysis_results["technical"]
            signal_types.append(technical.get("signal_type", "hold"))
            confidences.append(technical.get("confidence", 0.5))
            reasonings.append(f"Technical: {technical.get('reasoning', 'No reasoning provided')}")
        
        # Process fundamental analysis
        if "fundamental" in analysis_results:
            fundamental = analysis_results["fundamental"]
            signal_types.append(fundamental.get("signal_type", "hold"))
            confidences.append(fundamental.get("confidence", 0.5))
            reasonings.append(f"Fundamental: {fundamental.get('reasoning', 'No reasoning provided')}")
        
        # Process sentiment analysis
        if "sentiment" in analysis_results:
            sentiment = analysis_results["sentiment"]
            signal_types.append(sentiment.get("signal_type", "hold"))
            confidences.append(sentiment.get("confidence", 0.5))
            reasonings.append(f"Sentiment: {sentiment.get('reasoning', 'No reasoning provided')}")
        
        # Determine final signal type using weighted voting
        final_signal_type = self.determine_final_signal_type(signal_types, confidences)
        
        # Calculate combined confidence
        combined_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        
        # Get price targets
        current_price = 0
        target_price = 0
        stop_loss = 0
        
        if "technical" in analysis_results:
            current_price = analysis_results["technical"].get("current_price", 0)
            target_price = analysis_results["technical"].get("target_price", 0)
            stop_loss = analysis_results["technical"].get("stop_loss", 0)
        elif "fundamental" in analysis_results:
            current_price = analysis_results["fundamental"].get("current_price", 0)
            fair_value = analysis_results["fundamental"].get("fair_value", 0)
            
            # Use fair value to calculate targets
            if fair_value > 0 and current_price > 0:
                if final_signal_type == "buy":
                    target_price = fair_value
                    stop_loss = current_price * 0.95  # 5% stop loss
                elif final_signal_type == "sell":
                    target_price = fair_value
                    stop_loss = current_price * 1.05  # 5% stop loss (for short)
        
        # Create combined signal
        signal = {
            "id": f"signal_{symbol}_{int(datetime.now().timestamp())}",
            "symbol": symbol,
            "signal_type": final_signal_type,
            "confidence_score": combined_confidence,
            "reasoning": " | ".join(reasonings),
            "current_price": current_price,
            "target_price": target_price,
            "stop_loss": stop_loss,
            "timeframe": timeframe,
            "analysis_types": list(analysis_results.keys()),
            "position_size": self.calculate_position_size(combined_confidence),
            "expires_at": (datetime.now() + timedelta(days=1)).isoformat(),
            "created_at": datetime.now().isoformat()
        }
        
        return signal
    
    def determine_final_signal_type(
        self, 
        signal_types: List[str], 
        confidences: List[float]
    ) -> str:
        """Determine final signal type using weighted voting"""
        
        if not signal_types:
            return "hold"
        
        # Count weighted votes for each signal type
        votes = {"buy": 0.0, "sell": 0.0, "hold": 0.0}
        
        for i, signal_type in enumerate(signal_types):
            if signal_type in votes:
                votes[signal_type] += confidences[i]
        
        # Find signal type with highest weighted votes
        max_votes = 0
        final_signal = "hold"
        
        for signal_type, vote_count in votes.items():
            if vote_count > max_votes:
                max_votes = vote_count
                final_signal = signal_type
        
        return final_signal
    
    def calculate_position_size(self, confidence: float) -> float:
        """Calculate recommended position size based on confidence"""
        
        # Base position size
        base_size = 0.02  # 2% of portfolio
        
        # Adjust based on confidence
        if confidence > 0.8:
            return min(base_size * 2, 0.05)  # Max 5%
        elif confidence > 0.6:
            return base_size * 1.5
        elif confidence < 0.4:
            return base_size * 0.5
        else:
            return base_size
    
    async def validate_signal(self, signal: Dict[str, Any]) -> bool:
        """Validate signal before storing"""
        
        try:
            # Check required fields
            required_fields = ["symbol", "signal_type", "confidence_score"]
            for field in required_fields:
                if field not in signal:
                    logger.warning(f"Signal missing required field: {field}")
                    return False
            
            # Validate confidence score
            confidence = signal.get("confidence_score", 0)
            if confidence < 0 or confidence > 1:
                logger.warning(f"Invalid confidence score: {confidence}")
                return False
            
            # Validate signal type
            signal_type = signal.get("signal_type", "")
            if signal_type not in ["buy", "sell", "hold"]:
                logger.warning(f"Invalid signal type: {signal_type}")
                return False
            
            # Validate price data
            current_price = signal.get("current_price", 0)
            if current_price <= 0:
                logger.warning(f"Invalid current price: {current_price}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Signal validation error: {e}")
            return False    
  
  async def filter_and_rank_signals(
        self, 
        signals: List[Dict[str, Any]], 
        user_preferences: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Filter and rank signals based on user preferences"""
        
        try:
            # Get user's risk tolerance
            risk_tolerance = user_preferences.get("risk_tolerance", "medium")
            
            # Filter signals based on confidence threshold
            confidence_threshold = 0.5  # Default
            
            if risk_tolerance == "low":
                confidence_threshold = 0.7
            elif risk_tolerance == "high":
                confidence_threshold = 0.4
            
            filtered_signals = [
                signal for signal in signals 
                if signal.get("confidence_score", 0) >= confidence_threshold
            ]
            
            # Sort signals by confidence score (descending)
            ranked_signals = sorted(
                filtered_signals, 
                key=lambda x: x.get("confidence_score", 0), 
                reverse=True
            )
            
            return ranked_signals
            
        except Exception as e:
            logger.error(f"Failed to filter and rank signals: {e}")
            return signals
    
    async def store_signal(self, user_id: str, signal: Dict[str, Any]) -> str:
        """Store signal in database"""
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Generate signal ID if not present
            signal_id = signal.get("id", f"signal_{int(datetime.now().timestamp())}")
            
            # In production, this would insert into ai_trading_signals table
            cursor.execute("""
                INSERT INTO ai_trading_signals 
                (user_id, symbol, signal_type, confidence_score, reasoning, 
                 target_price, stop_loss, take_profit, position_size, 
                 market_data, provider_used, is_active, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                signal.get("symbol", ""),
                signal.get("signal_type", "hold"),
                signal.get("confidence_score", 0.5),
                signal.get("reasoning", ""),
                signal.get("target_price", 0),
                signal.get("stop_loss", 0),
                signal.get("target_price", 0),  # Use target as take profit
                signal.get("position_size", 0.02),
                json.dumps({"timeframe": signal.get("timeframe", "1d")}),
                signal.get("provider_used", "unknown"),
                True,  # Active by default
                signal.get("expires_at", (datetime.now() + timedelta(days=1)).isoformat()),
                datetime.now()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Stored signal {signal_id} for user {user_id}")
            return signal_id
            
        except Exception as e:
            logger.error(f"Failed to store signal: {e}")
            return signal.get("id", f"error_{int(datetime.now().timestamp())}")
    
    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
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
            
            return {"risk_tolerance": "medium", "trading_style": "balanced"}
            
        except Exception as e:
            logger.warning(f"Failed to get preferences for user {user_id}: {e}")
            return {"risk_tolerance": "medium", "trading_style": "balanced"}   
 
    async def fetch_price_data(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Fetch price data for technical analysis"""
        
        try:
            # In production, this would fetch from market data API
            # For now, return mock data
            import random
            
            current_price = random.uniform(100, 3000)
            
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "current_price": current_price,
                "open": current_price * 0.99,
                "high": current_price * 1.02,
                "low": current_price * 0.98,
                "volume": random.randint(100000, 1000000),
                "rsi": random.uniform(30, 70),
                "macd": random.uniform(-2, 2),
                "ma_20": current_price * random.uniform(0.95, 1.05),
                "ma_50": current_price * random.uniform(0.9, 1.1),
                "ma_200": current_price * random.uniform(0.85, 1.15),
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch price data for {symbol}: {e}")
            return {"symbol": symbol, "current_price": 0}
    
    async def fetch_financial_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch financial data for fundamental analysis"""
        
        try:
            # In production, this would fetch from financial data API
            # For now, return mock data
            import random
            
            current_price = random.uniform(100, 3000)
            
            return {
                "symbol": symbol,
                "current_price": current_price,
                "pe_ratio": random.uniform(10, 30),
                "pb_ratio": random.uniform(1, 5),
                "eps": current_price / random.uniform(10, 25),
                "revenue_growth": random.uniform(-10, 30),
                "profit_margin": random.uniform(5, 25),
                "debt_to_equity": random.uniform(0.1, 2),
                "dividend_yield": random.uniform(0, 5),
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch financial data for {symbol}: {e}")
            return {"symbol": symbol, "current_price": 0}
    
    async def fetch_sentiment_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch sentiment data for sentiment analysis"""
        
        try:
            # In production, this would fetch from news and social media APIs
            # For now, return mock data
            import random
            
            return {
                "symbol": symbol,
                "news_sentiment": random.uniform(-1, 1),
                "social_sentiment": random.uniform(-1, 1),
                "news_volume": random.randint(5, 50),
                "social_volume": random.randint(100, 10000),
                "analyst_ratings": {
                    "buy": random.randint(0, 10),
                    "hold": random.randint(0, 10),
                    "sell": random.randint(0, 10)
                },
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch sentiment data for {symbol}: {e}")
            return {"symbol": symbol, "news_sentiment": 0, "social_sentiment": 0}
    
    def build_technical_analysis_prompt(self, symbol: str, price_data: Dict[str, Any]) -> str:
        """Build prompt for technical analysis"""
        
        return f"""
        Analyze the technical indicators for {symbol} and provide a trading signal.
        
        PRICE DATA:
        - Current Price: {price_data.get('current_price', 0)}
        - RSI: {price_data.get('rsi', 0)}
        - MACD: {price_data.get('macd', 0)}
        - 20-day MA: {price_data.get('ma_20', 0)}
        - 50-day MA: {price_data.get('ma_50', 0)}
        - 200-day MA: {price_data.get('ma_200', 0)}
        
        Provide a trading signal (buy, sell, or hold) with confidence score and reasoning.
        Also provide target price and stop loss levels.
        """
    
    def build_fundamental_analysis_prompt(self, symbol: str, financial_data: Dict[str, Any]) -> str:
        """Build prompt for fundamental analysis"""
        
        return f"""
        Analyze the fundamental data for {symbol} and provide a trading signal.
        
        FINANCIAL DATA:
        - Current Price: {financial_data.get('current_price', 0)}
        - P/E Ratio: {financial_data.get('pe_ratio', 0)}
        - P/B Ratio: {financial_data.get('pb_ratio', 0)}
        - EPS: {financial_data.get('eps', 0)}
        - Revenue Growth: {financial_data.get('revenue_growth', 0)}%
        - Profit Margin: {financial_data.get('profit_margin', 0)}%
        - Debt to Equity: {financial_data.get('debt_to_equity', 0)}
        - Dividend Yield: {financial_data.get('dividend_yield', 0)}%
        
        Provide a trading signal (buy, sell, or hold) with confidence score and reasoning.
        Also provide a fair value estimate for the stock.
        """
    
    def build_sentiment_analysis_prompt(self, symbol: str, sentiment_data: Dict[str, Any]) -> str:
        """Build prompt for sentiment analysis"""
        
        return f"""
        Analyze the sentiment data for {symbol} and provide a trading signal.
        
        SENTIMENT DATA:
        - News Sentiment: {sentiment_data.get('news_sentiment', 0)} (-1 to 1 scale)
        - Social Media Sentiment: {sentiment_data.get('social_sentiment', 0)} (-1 to 1 scale)
        - News Volume: {sentiment_data.get('news_volume', 0)} articles
        - Social Volume: {sentiment_data.get('social_volume', 0)} mentions
        - Analyst Ratings: {sentiment_data.get('analyst_ratings', {}).get('buy', 0)} Buy, {sentiment_data.get('analyst_ratings', {}).get('hold', 0)} Hold, {sentiment_data.get('analyst_ratings', {}).get('sell', 0)} Sell
        
        Provide a trading signal (buy, sell, or hold) with confidence score and reasoning.
        """
    
    def get_technical_analysis_schema(self) -> Dict[str, Any]:
        """Get schema for technical analysis response"""
        
        return {
            "type": "object",
            "properties": {
                "signal": {
                    "type": "string",
                    "enum": ["buy", "sell", "hold"]
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1
                },
                "reasoning": {
                    "type": "string"
                },
                "target_price": {
                    "type": "number"
                },
                "stop_loss": {
                    "type": "number"
                },
                "indicators": {
                    "type": "object"
                }
            },
            "required": ["signal", "confidence", "reasoning"]
        }
    
    def get_fundamental_analysis_schema(self) -> Dict[str, Any]:
        """Get schema for fundamental analysis response"""
        
        return {
            "type": "object",
            "properties": {
                "signal": {
                    "type": "string",
                    "enum": ["buy", "sell", "hold"]
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1
                },
                "reasoning": {
                    "type": "string"
                },
                "fair_value": {
                    "type": "number"
                },
                "valuation_metrics": {
                    "type": "object"
                }
            },
            "required": ["signal", "confidence", "reasoning"]
        }
    
    def get_sentiment_analysis_schema(self) -> Dict[str, Any]:
        """Get schema for sentiment analysis response"""
        
        return {
            "type": "object",
            "properties": {
                "signal": {
                    "type": "string",
                    "enum": ["buy", "sell", "hold"]
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1
                },
                "reasoning": {
                    "type": "string"
                },
                "sentiment_score": {
                    "type": "number",
                    "minimum": -1,
                    "maximum": 1
                }
            },
            "required": ["signal", "confidence", "reasoning"]
        }    
    de
f extract_technical_signal(self, technical_result: Dict[str, Any]) -> Tuple[str, float, str]:
        """Extract signal from technical analysis result"""
        
        signal_type = technical_result.get("signal", "hold")
        confidence = technical_result.get("confidence", 0.5)
        reasoning = technical_result.get("reasoning", "No reasoning provided")
        
        return signal_type, confidence, reasoning
    
    def extract_fundamental_signal(self, fundamental_result: Dict[str, Any]) -> Tuple[str, float, str]:
        """Extract signal from fundamental analysis result"""
        
        signal_type = fundamental_result.get("signal", "hold")
        confidence = fundamental_result.get("confidence", 0.5)
        reasoning = fundamental_result.get("reasoning", "No reasoning provided")
        
        return signal_type, confidence, reasoning
    
    def extract_sentiment_signal(self, sentiment_result: Dict[str, Any]) -> Tuple[str, float, str]:
        """Extract signal from sentiment analysis result"""
        
        signal_type = sentiment_result.get("signal", "hold")
        confidence = sentiment_result.get("confidence", 0.5)
        reasoning = sentiment_result.get("reasoning", "No reasoning provided")
        
        return signal_type, confidence, reasoning
    
    def calculate_price_targets(
        self, 
        signal_type: str, 
        current_price: float, 
        technical_result: Dict[str, Any]
    ) -> Tuple[float, float]:
        """Calculate price targets based on technical analysis"""
        
        # Try to get targets from technical analysis
        target_price = technical_result.get("target_price", 0)
        stop_loss = technical_result.get("stop_loss", 0)
        
        # If not available, calculate based on signal type
        if target_price <= 0:
            if signal_type == "buy":
                target_price = current_price * 1.1  # 10% profit target
            elif signal_type == "sell":
                target_price = current_price * 0.9  # 10% profit target (for short)
            else:
                target_price = current_price
        
        if stop_loss <= 0:
            if signal_type == "buy":
                stop_loss = current_price * 0.95  # 5% stop loss
            elif signal_type == "sell":
                stop_loss = current_price * 1.05  # 5% stop loss (for short)
            else:
                stop_loss = current_price
        
        return target_price, stop_loss
    
    async def get_user_signals(
        self, 
        user_id: str, 
        active_only: bool = True,
        symbol: Optional[str] = None,
        signal_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get user's trading signals"""
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT id, symbol, signal_type, confidence_score, reasoning, 
                       target_price, stop_loss, take_profit, position_size, 
                       market_data, provider_used, is_active, expires_at, created_at
                FROM ai_trading_signals
                WHERE user_id = ?
            """
            
            params = [user_id]
            
            if active_only:
                query += " AND is_active = 1"
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            if signal_type:
                query += " AND signal_type = ?"
                params.append(signal_type)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            
            rows = cursor.fetchall()
            conn.close()
            
            signals = []
            for row in rows:
                signals.append({
                    "id": row[0],
                    "symbol": row[1],
                    "signal_type": row[2],
                    "confidence_score": row[3],
                    "reasoning": row[4],
                    "target_price": row[5],
                    "stop_loss": row[6],
                    "take_profit": row[7],
                    "position_size": row[8],
                    "market_data": json.loads(row[9]) if row[9] else {},
                    "provider_used": row[10],
                    "is_active": bool(row[11]),
                    "expires_at": row[12],
                    "created_at": row[13]
                })
            
            return signals
            
        except Exception as e:
            logger.error(f"Failed to get signals for user {user_id}: {e}")
            return []