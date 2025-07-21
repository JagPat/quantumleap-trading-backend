"""
Technical Analyzer
Advanced technical analysis with chart pattern recognition and indicator analysis
"""
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import random
import math
from .orchestrator import AIOrchestrator
from .models import AnalysisResponse, AnalysisType
from ..database.service import get_db_connection

logger = logging.getLogger(__name__)

class TechnicalAnalyzer:
    """
    Technical analysis engine with AI-powered chart pattern recognition
    """
    
    def __init__(self):
        self.orchestrator = AIOrchestrator()
        
    async def generate_technical_analysis(
        self, 
        user_id: str, 
        symbol: str,
        timeframe: str = "1d"
    ) -> AnalysisResponse:
        """Generate technical analysis for a specific symbol"""
        
        try:
            logger.info(f"Starting technical analysis for {symbol}")
            
            # Get user preferences for provider selection
            user_preferences = await self.get_user_preferences(user_id)
            
            # Fetch price data and technical indicators
            price_data = await self.fetch_price_data(symbol, timeframe)
            
            # Build technical analysis prompt
            technical_prompt = self.build_technical_analysis_prompt(symbol, price_data)
            
            # Select optimal provider for technical analysis
            provider = await self.orchestrator.select_optimal_provider("technical_analysis", user_preferences)
            
            # Generate analysis using AI
            ai_response = await provider.generate_analysis(technical_prompt, price_data)
            
            # Process and structure the technical results
            technical_results = await self.process_technical_analysis_results(ai_response, symbol, price_data)
            
            # Store analysis results
            await self.store_analysis_result(
                user_id, 
                AnalysisType.TECHNICAL,
                [symbol],
                price_data,
                technical_results,
                provider.provider_name,
                technical_results.get('confidence_score', 0.8)
            )
            
            return AnalysisResponse(
                status="success",
                analysis_type=AnalysisType.TECHNICAL,
                symbols=[symbol],
                results=technical_results,
                confidence_score=technical_results.get('confidence_score', 0.8),
                provider_used=provider.provider_name,
                created_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Technical analysis failed for {symbol}: {e}")
            return AnalysisResponse(
                status="error",
                analysis_type=AnalysisType.TECHNICAL,
                symbols=[symbol],
                results={"error": str(e), "message": "Technical analysis failed"},
                confidence_score=0.0,
                provider_used="none",
                created_at=datetime.now()
            )
    
    async def fetch_price_data(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Fetch price data and calculate technical indicators"""
        
        # Generate sample OHLCV data for the last 50 periods
        base_price = 1000 + random.randint(-200, 200)
        price_data = {
            "symbol": symbol,
            "timeframe": timeframe,
            "ohlcv": [],
            "technical_indicators": {},
            "last_updated": datetime.now().isoformat()
        }
        
        # Generate sample OHLCV data
        current_price = base_price
        for i in range(50):
            # Simulate price movement
            change = random.uniform(-0.05, 0.05)  # ±5% change
            open_price = current_price
            high_price = open_price * (1 + abs(change) + random.uniform(0, 0.02))
            low_price = open_price * (1 - abs(change) - random.uniform(0, 0.02))
            close_price = open_price * (1 + change)
            volume = random.randint(100000, 1000000)
            
            price_data["ohlcv"].append({
                "timestamp": (datetime.now() - timedelta(days=49-i)).isoformat(),
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "volume": volume
            })
            
            current_price = close_price
        
        # Calculate technical indicators
        closes = [candle["close"] for candle in price_data["ohlcv"]]
        volumes = [candle["volume"] for candle in price_data["ohlcv"]]
        
        price_data["technical_indicators"] = {
            "sma_20": self.calculate_sma(closes, 20),
            "sma_50": self.calculate_sma(closes, 50),
            "ema_12": self.calculate_ema(closes, 12),
            "ema_26": self.calculate_ema(closes, 26),
            "rsi": self.calculate_rsi(closes),
            "macd": self.calculate_macd(closes),
            "bollinger_bands": self.calculate_bollinger_bands(closes),
            "volume_sma": self.calculate_sma(volumes, 20),
            "current_price": closes[-1],
            "price_change_24h": ((closes[-1] - closes[-2]) / closes[-2] * 100) if len(closes) > 1 else 0,
            "support_resistance": self.identify_support_resistance_levels(price_data["ohlcv"])
        }
        
        return price_data
    
    def build_technical_analysis_prompt(self, symbol: str, price_data: Dict[str, Any]) -> str:
        """Build AI prompt for technical analysis"""
        
        indicators = price_data.get('technical_indicators', {})
        current_price = indicators.get('current_price', 0)
        sma_20 = indicators.get('sma_20', 0)
        sma_50 = indicators.get('sma_50', 0)
        rsi = indicators.get('rsi', 50)
        macd = indicators.get('macd', {})
        bb = indicators.get('bollinger_bands', {})
        
        prompt = f"""
        As an expert technical analyst, analyze the technical setup for {symbol} based on the following data:
        
        CURRENT PRICE DATA:
        - Current Price: ₹{current_price:.2f}
        - 24h Change: {indicators.get('price_change_24h', 0):.2f}%
        - Timeframe: {price_data.get('timeframe', '1d')}
        
        TECHNICAL INDICATORS:
        - SMA 20: ₹{sma_20:.2f}
        - SMA 50: ₹{sma_50:.2f}
        - EMA 12: ₹{indicators.get('ema_12', 0):.2f}
        - EMA 26: ₹{indicators.get('ema_26', 0):.2f}
        - RSI: {rsi:.2f}
        - MACD Line: {macd.get('macd_line', 0):.2f}
        - MACD Signal: {macd.get('signal_line', 0):.2f}
        - MACD Histogram: {macd.get('histogram', 0):.2f}
        - Bollinger Upper: ₹{bb.get('upper', 0):.2f}
        - Bollinger Middle: ₹{bb.get('middle', 0):.2f}
        - Bollinger Lower: ₹{bb.get('lower', 0):.2f}
        
        PRICE POSITION:
        - Price vs SMA20: {"Above" if current_price > sma_20 else "Below"} ({((current_price - sma_20) / sma_20 * 100):.2f}%)
        - Price vs SMA50: {"Above" if current_price > sma_50 else "Below"} ({((current_price - sma_50) / sma_50 * 100):.2f}%)
        - SMA20 vs SMA50: {"Golden Cross" if sma_20 > sma_50 else "Death Cross"}
        
        SUPPORT & RESISTANCE:
        """
        
        support_resistance = indicators.get('support_resistance', {})
        for level_type, levels in support_resistance.items():
            prompt += f"- {level_type.title()}: {', '.join([f'₹{level:.2f}' for level in levels[:3]])}\n"
        
        prompt += f"""
        
        ANALYSIS REQUIREMENTS:
        Please provide a comprehensive technical analysis covering:
        
        1. TREND ANALYSIS:
           - Primary trend direction (bullish/bearish/sideways)
           - Trend strength and momentum
           - Key support and resistance levels
           - Moving average analysis and crossovers
        
        2. MOMENTUM INDICATORS:
           - RSI interpretation and overbought/oversold conditions
           - MACD analysis and signal line crossovers
           - Momentum divergences if any
        
        3. VOLATILITY ANALYSIS:
           - Bollinger Bands position and squeeze/expansion
           - Price volatility assessment
           - Volume analysis and confirmation
        
        4. CHART PATTERNS:
           - Identify any chart patterns forming
           - Breakout or breakdown potential
           - Pattern targets and implications
        
        5. TRADING SIGNALS:
           - Entry and exit levels
           - Stop loss recommendations
           - Target price projections
           - Risk-reward assessment
        
        6. TIME HORIZON OUTLOOK:
           - Short-term (1-5 days) outlook
           - Medium-term (1-4 weeks) outlook
           - Key levels to watch
        
        Please provide specific price levels and actionable trading insights.
        Rate the overall technical setup as: Very Bullish, Bullish, Neutral, Bearish, or Very Bearish.
        """
        
        return prompt    
 
   def calculate_sma(self, prices: List[float], period: int) -> float:
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return 0
        return sum(prices[-period:]) / period
    
    def calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return sum(prices) / len(prices) if prices else 0
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return round(ema, 2)
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return 50  # Neutral RSI
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        if len(gains) < period:
            return 50
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    def calculate_macd(self, prices: List[float]) -> Dict[str, float]:
        """Calculate MACD indicator"""
        if len(prices) < 26:
            return {"macd_line": 0, "signal_line": 0, "histogram": 0}
        
        # Calculate EMAs
        ema_12 = self.calculate_ema(prices, 12)
        ema_26 = self.calculate_ema(prices, 26)
        macd_line = ema_12 - ema_26
        
        # Signal line (9-period EMA of MACD line) - simplified
        signal_line = macd_line * 0.8  # Simplified calculation
        histogram = macd_line - signal_line
        
        return {
            "macd_line": round(macd_line, 2),
            "signal_line": round(signal_line, 2),
            "histogram": round(histogram, 2)
        }
    
    def calculate_bollinger_bands(self, prices: List[float], period: int = 20, std_dev: int = 2) -> Dict[str, float]:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            current_price = prices[-1] if prices else 0
            return {"upper": current_price, "middle": current_price, "lower": current_price}
        
        sma = self.calculate_sma(prices, period)
        
        # Calculate standard deviation
        variance = sum((price - sma) ** 2 for price in prices[-period:]) / period
        std = math.sqrt(variance)
        
        return {
            "upper": round(sma + (std * std_dev), 2),
            "middle": round(sma, 2),
            "lower": round(sma - (std * std_dev), 2)
        }
    
    def identify_support_resistance_levels(self, ohlcv_data: List[Dict[str, Any]]) -> Dict[str, List[float]]:
        """Identify key support and resistance levels"""
        
        if len(ohlcv_data) < 10:
            return {"support": [], "resistance": []}
        
        highs = [candle["high"] for candle in ohlcv_data[-20:]]  # Last 20 periods
        lows = [candle["low"] for candle in ohlcv_data[-20:]]
        
        # Simplified support/resistance identification
        resistance_levels = sorted(set(highs), reverse=True)[:3]  # Top 3 highs
        support_levels = sorted(set(lows))[:3]  # Bottom 3 lows
        
        return {
            "resistance": resistance_levels,
            "support": support_levels
        }
    
    async def process_technical_analysis_results(
        self, 
        ai_response: str, 
        symbol: str,
        price_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process and structure technical analysis results"""
        
        indicators = price_data.get('technical_indicators', {})
        
        # Calculate technical signals
        technical_signals = self.calculate_technical_signals(indicators)
        
        # Structure the results
        results = {
            "ai_analysis": ai_response,
            "symbol": symbol,
            "current_price": indicators.get('current_price', 0),
            "technical_indicators": indicators,
            "technical_signals": technical_signals,
            "support_resistance": indicators.get('support_resistance', {}),
            "trend_analysis": self.analyze_trend(indicators),
            "trading_signals": self.generate_trading_signals(indicators),
            "confidence_score": 0.8,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        return results
    
    def calculate_technical_signals(self, indicators: Dict[str, Any]) -> Dict[str, str]:
        """Calculate technical trading signals"""
        
        current_price = indicators.get('current_price', 0)
        sma_20 = indicators.get('sma_20', 0)
        sma_50 = indicators.get('sma_50', 0)
        rsi = indicators.get('rsi', 50)
        macd = indicators.get('macd', {})
        bb = indicators.get('bollinger_bands', {})
        
        signals = {}
        
        # Moving Average Signal
        if current_price > sma_20 > sma_50:
            signals["ma_signal"] = "Bullish"
        elif current_price < sma_20 < sma_50:
            signals["ma_signal"] = "Bearish"
        else:
            signals["ma_signal"] = "Neutral"
        
        # RSI Signal
        if rsi > 70:
            signals["rsi_signal"] = "Overbought"
        elif rsi < 30:
            signals["rsi_signal"] = "Oversold"
        else:
            signals["rsi_signal"] = "Neutral"
        
        # MACD Signal
        macd_line = macd.get('macd_line', 0)
        signal_line = macd.get('signal_line', 0)
        if macd_line > signal_line:
            signals["macd_signal"] = "Bullish"
        else:
            signals["macd_signal"] = "Bearish"
        
        # Bollinger Bands Signal
        bb_upper = bb.get('upper', 0)
        bb_lower = bb.get('lower', 0)
        if current_price > bb_upper:
            signals["bb_signal"] = "Overbought"
        elif current_price < bb_lower:
            signals["bb_signal"] = "Oversold"
        else:
            signals["bb_signal"] = "Normal"
        
        return signals
    
    def analyze_trend(self, indicators: Dict[str, Any]) -> Dict[str, str]:
        """Analyze overall trend direction"""
        
        current_price = indicators.get('current_price', 0)
        sma_20 = indicators.get('sma_20', 0)
        sma_50 = indicators.get('sma_50', 0)
        
        if current_price > sma_20 > sma_50:
            trend = "Strong Uptrend"
        elif current_price > sma_20 and sma_20 < sma_50:
            trend = "Weak Uptrend"
        elif current_price < sma_20 < sma_50:
            trend = "Strong Downtrend"
        elif current_price < sma_20 and sma_20 > sma_50:
            trend = "Weak Downtrend"
        else:
            trend = "Sideways"
        
        return {
            "primary_trend": trend,
            "trend_strength": "Strong" if "Strong" in trend else "Weak" if "Weak" in trend else "Neutral"
        }
    
    def generate_trading_signals(self, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Generate specific trading signals and levels"""
        
        current_price = indicators.get('current_price', 0)
        bb = indicators.get('bollinger_bands', {})
        
        # Calculate key levels
        stop_loss = current_price * 0.95  # 5% stop loss
        target_1 = current_price * 1.05   # 5% target
        target_2 = current_price * 1.10   # 10% target
        
        return {
            "entry_level": current_price,
            "stop_loss": round(stop_loss, 2),
            "target_1": round(target_1, 2),
            "target_2": round(target_2, 2),
            "risk_reward_ratio": round((target_1 - current_price) / (current_price - stop_loss), 2),
            "key_resistance": bb.get('upper', current_price * 1.02),
            "key_support": bb.get('lower', current_price * 0.98)
        }    
  
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
            
            logger.debug(f"Stored technical analysis result for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to store technical analysis result: {e}")