"""
Market Condition Monitor
Monitors market conditions including volatility, gaps, and market hours for trading decisions
"""
import asyncio
import logging
import time
import statistics
from datetime import datetime, timedelta, time as dt_time
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict
import json

from app.trading_engine.models import PriceData, MarketStatus
from app.trading_engine.event_bus import EventManager, TradingEvent, EventType, EventPriority

logger = logging.getLogger(__name__)

class MarketCondition(Enum):
    """Market condition types"""
    NORMAL = "normal"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    GAP_UP = "gap_up"
    GAP_DOWN = "gap_down"
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SIDEWAYS = "sideways"
    CIRCUIT_BREAKER = "circuit_breaker"

class MarketSession(Enum):
    """Market session types"""
    PRE_MARKET = "pre_market"
    REGULAR = "regular"
    AFTER_HOURS = "after_hours"
    CLOSED = "closed"

class VolatilityLevel(Enum):
    """Volatility levels"""
    VERY_LOW = "very_low"
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    VERY_HIGH = "very_high"
    EXTREME = "extreme"

@dataclass
class MarketConditionData:
    """Market condition analysis data"""
    symbol: str
    condition: MarketCondition
    volatility_level: VolatilityLevel
    volatility_score: float
    price_change_percent: float
    volume_ratio: float
    gap_percent: float = 0.0
    trend_strength: float = 0.0
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MarketHours:
    """Market hours configuration"""
    pre_market_start: dt_time = dt_time(4, 0)  # 4:00 AM
    market_open: dt_time = dt_time(9, 30)      # 9:30 AM
    market_close: dt_time = dt_time(16, 0)     # 4:00 PM
    after_hours_end: dt_time = dt_time(20, 0)  # 8:00 PM
    timezone: str = "US/Eastern"

@dataclass
class VolatilityMetrics:
    """Volatility calculation metrics"""
    symbol: str
    current_volatility: float
    historical_volatility: float
    volatility_percentile: float
    price_range_percent: float
    volume_volatility: float
    timestamp: datetime = field(default_factory=datetime.utcnow)

class MarketConditionMonitor:
    """
    Monitors market conditions and provides real-time analysis
    """
    
    def __init__(self, event_manager: EventManager):
        self.event_manager = event_manager
        
        # Configuration
        self.market_hours = MarketHours()
        self.volatility_window = 20  # Number of periods for volatility calculation
        self.gap_threshold_percent = 2.0  # Minimum gap percentage
        self.high_volatility_threshold = 2.0  # Standard deviations
        self.circuit_breaker_threshold = 10.0  # Percentage for circuit breaker
        
        # Data storage
        self.price_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.volume_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.volatility_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=50))
        self.condition_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=20))
        
        # Current market conditions
        self.current_conditions: Dict[str, MarketConditionData] = {}
        self.market_session = MarketSession.CLOSED
        self.global_market_condition = MarketCondition.NORMAL
        
        # Callbacks for condition changes
        self.condition_callbacks: List[Callable[[str, MarketConditionData], None]] = []
        
        # Background tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the market condition monitor"""
        logger.info("Starting Market Condition Monitor")
        
        # Start background monitoring tasks
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        # Update market session
        await self._update_market_session()
        
        logger.info("Market Condition Monitor started successfully")
    
    async def stop(self):
        """Stop the market condition monitor"""
        logger.info("Stopping Market Condition Monitor")
        
        # Cancel background tasks
        if self._monitoring_task:
            self._monitoring_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(
            self._monitoring_task, self._cleanup_task,
            return_exceptions=True
        )
        
        logger.info("Market Condition Monitor stopped")
    
    async def analyze_price_update(self, price_data: PriceData) -> MarketConditionData:
        """
        Analyze a price update and determine market conditions
        
        Args:
            price_data: Price data to analyze
            
        Returns:
            MarketConditionData: Analysis results
        """
        try:
            symbol = price_data.symbol
            
            # Store price data
            self.price_history[symbol].append(price_data)
            self.volume_history[symbol].append(price_data.volume)
            
            # Calculate volatility
            volatility_metrics = await self._calculate_volatility(symbol)
            
            # Detect gaps
            gap_percent = await self._detect_price_gap(symbol)
            
            # Determine market condition
            condition = await self._determine_market_condition(symbol, volatility_metrics, gap_percent)
            
            # Calculate trend strength
            trend_strength = await self._calculate_trend_strength(symbol)
            
            # Find support/resistance levels
            support, resistance = await self._find_support_resistance(symbol)
            
            # Create condition data
            condition_data = MarketConditionData(
                symbol=symbol,
                condition=condition,
                volatility_level=self._get_volatility_level(volatility_metrics.current_volatility),
                volatility_score=volatility_metrics.current_volatility,
                price_change_percent=price_data.change_percent,
                volume_ratio=await self._calculate_volume_ratio(symbol),
                gap_percent=gap_percent,
                trend_strength=trend_strength,
                support_level=support,
                resistance_level=resistance,
                confidence=await self._calculate_confidence(symbol, volatility_metrics)
            )
            
            # Store current condition
            self.current_conditions[symbol] = condition_data
            self.condition_history[symbol].append(condition_data)
            
            # Publish condition update event
            await self._publish_condition_event(condition_data)
            
            # Notify callbacks
            for callback in self.condition_callbacks:
                try:
                    callback(symbol, condition_data)
                except Exception as e:
                    logger.error(f"Error in condition callback: {e}")
            
            return condition_data
            
        except Exception as e:
            logger.error(f"Error analyzing price update for {price_data.symbol}: {e}")
            # Return default condition data
            return MarketConditionData(
                symbol=price_data.symbol,
                condition=MarketCondition.NORMAL,
                volatility_level=VolatilityLevel.NORMAL,
                volatility_score=0.0,
                price_change_percent=0.0,
                volume_ratio=1.0
            )
    
    async def _calculate_volatility(self, symbol: str) -> VolatilityMetrics:
        """Calculate volatility metrics for a symbol"""
        try:
            prices = [p.price for p in list(self.price_history[symbol])]
            
            if len(prices) < 2:
                return VolatilityMetrics(
                    symbol=symbol,
                    current_volatility=0.0,
                    historical_volatility=0.0,
                    volatility_percentile=50.0,
                    price_range_percent=0.0,
                    volume_volatility=0.0
                )
            
            # Calculate price returns
            returns = []
            for i in range(1, len(prices)):
                if prices[i-1] > 0:
                    returns.append((prices[i] - prices[i-1]) / prices[i-1])
            
            if not returns:
                return VolatilityMetrics(
                    symbol=symbol,
                    current_volatility=0.0,
                    historical_volatility=0.0,
                    volatility_percentile=50.0,
                    price_range_percent=0.0,
                    volume_volatility=0.0
                )
            
            # Current volatility (standard deviation of returns)
            current_volatility = statistics.stdev(returns) if len(returns) > 1 else 0.0
            
            # Historical volatility (longer term average)
            historical_volatility = current_volatility  # Simplified for now
            
            # Price range percentage
            if prices:
                price_range_percent = ((max(prices) - min(prices)) / min(prices)) * 100
            else:
                price_range_percent = 0.0
            
            # Volume volatility
            volumes = list(self.volume_history[symbol])
            volume_volatility = statistics.stdev(volumes) if len(volumes) > 1 else 0.0
            
            # Store volatility history
            self.volatility_history[symbol].append(current_volatility)
            
            # Calculate percentile
            volatility_percentile = self._calculate_percentile(
                current_volatility, 
                list(self.volatility_history[symbol])
            )
            
            return VolatilityMetrics(
                symbol=symbol,
                current_volatility=current_volatility,
                historical_volatility=historical_volatility,
                volatility_percentile=volatility_percentile,
                price_range_percent=price_range_percent,
                volume_volatility=volume_volatility
            )
            
        except Exception as e:
            logger.error(f"Error calculating volatility for {symbol}: {e}")
            return VolatilityMetrics(
                symbol=symbol,
                current_volatility=0.0,
                historical_volatility=0.0,
                volatility_percentile=50.0,
                price_range_percent=0.0,
                volume_volatility=0.0
            )
    
    async def _detect_price_gap(self, symbol: str) -> float:
        """Detect price gaps between sessions"""
        try:
            prices = list(self.price_history[symbol])
            
            if len(prices) < 2:
                return 0.0
            
            # Check for gap between current and previous close
            current_price = prices[-1].price
            previous_close = prices[-2].price
            
            if previous_close > 0:
                gap_percent = ((current_price - previous_close) / previous_close) * 100
                
                # Only consider significant gaps
                if abs(gap_percent) >= self.gap_threshold_percent:
                    return gap_percent
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error detecting price gap for {symbol}: {e}")
            return 0.0
    
    async def _determine_market_condition(self, symbol: str, volatility_metrics: VolatilityMetrics, gap_percent: float) -> MarketCondition:
        """Determine the current market condition"""
        try:
            # Check for circuit breaker conditions
            if abs(gap_percent) >= self.circuit_breaker_threshold:
                return MarketCondition.CIRCUIT_BREAKER
            
            # Check for gaps
            if gap_percent >= self.gap_threshold_percent:
                return MarketCondition.GAP_UP
            elif gap_percent <= -self.gap_threshold_percent:
                return MarketCondition.GAP_DOWN
            
            # Check volatility levels
            if volatility_metrics.current_volatility >= self.high_volatility_threshold:
                return MarketCondition.HIGH_VOLATILITY
            elif volatility_metrics.current_volatility <= 0.5:
                return MarketCondition.LOW_VOLATILITY
            
            # Check for trending conditions
            trend_strength = await self._calculate_trend_strength(symbol)
            if trend_strength > 0.7:
                return MarketCondition.TRENDING_UP
            elif trend_strength < -0.7:
                return MarketCondition.TRENDING_DOWN
            elif abs(trend_strength) < 0.3:
                return MarketCondition.SIDEWAYS
            
            return MarketCondition.NORMAL
            
        except Exception as e:
            logger.error(f"Error determining market condition for {symbol}: {e}")
            return MarketCondition.NORMAL
    
    async def _calculate_trend_strength(self, symbol: str) -> float:
        """Calculate trend strength (-1 to 1, where 1 is strong uptrend)"""
        try:
            prices = [p.price for p in list(self.price_history[symbol])]
            
            if len(prices) < 5:
                return 0.0
            
            # Simple trend calculation using linear regression slope
            n = len(prices)
            x_values = list(range(n))
            
            # Calculate slope
            x_mean = statistics.mean(x_values)
            y_mean = statistics.mean(prices)
            
            numerator = sum((x_values[i] - x_mean) * (prices[i] - y_mean) for i in range(n))
            denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
            
            if denominator == 0:
                return 0.0
            
            slope = numerator / denominator
            
            # Normalize slope to -1 to 1 range
            # This is a simplified normalization
            max_price = max(prices)
            if max_price > 0:
                normalized_slope = slope / max_price * n
                return max(-1.0, min(1.0, normalized_slope))
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating trend strength for {symbol}: {e}")
            return 0.0
    
    async def _find_support_resistance(self, symbol: str) -> Tuple[Optional[float], Optional[float]]:
        """Find support and resistance levels"""
        try:
            prices = [p.price for p in list(self.price_history[symbol])]
            
            if len(prices) < 10:
                return None, None
            
            # Simple support/resistance calculation
            # Support: lowest price in recent history
            # Resistance: highest price in recent history
            recent_prices = prices[-20:]  # Last 20 prices
            
            support = min(recent_prices)
            resistance = max(recent_prices)
            
            # Only return if there's meaningful difference
            if (resistance - support) / support > 0.02:  # 2% difference
                return support, resistance
            
            return None, None
            
        except Exception as e:
            logger.error(f"Error finding support/resistance for {symbol}: {e}")
            return None, None
    
    async def _calculate_volume_ratio(self, symbol: str) -> float:
        """Calculate current volume ratio to average"""
        try:
            volumes = list(self.volume_history[symbol])
            
            if len(volumes) < 2:
                return 1.0
            
            current_volume = volumes[-1]
            avg_volume = statistics.mean(volumes[:-1])
            
            if avg_volume > 0:
                return current_volume / avg_volume
            
            return 1.0
            
        except Exception as e:
            logger.error(f"Error calculating volume ratio for {symbol}: {e}")
            return 1.0
    
    async def _calculate_confidence(self, symbol: str, volatility_metrics: VolatilityMetrics) -> float:
        """Calculate confidence in the market condition analysis"""
        try:
            # Base confidence
            confidence = 1.0
            
            # Reduce confidence for high volatility
            if volatility_metrics.current_volatility > self.high_volatility_threshold:
                confidence *= 0.8
            
            # Reduce confidence for insufficient data
            data_points = len(self.price_history[symbol])
            if data_points < 10:
                confidence *= (data_points / 10)
            
            # Reduce confidence for extreme conditions
            if volatility_metrics.volatility_percentile > 95 or volatility_metrics.volatility_percentile < 5:
                confidence *= 0.7
            
            return max(0.1, min(1.0, confidence))
            
        except Exception as e:
            logger.error(f"Error calculating confidence for {symbol}: {e}")
            return 0.5
    
    def _get_volatility_level(self, volatility: float) -> VolatilityLevel:
        """Convert volatility score to level"""
        if volatility >= 3.0:
            return VolatilityLevel.EXTREME
        elif volatility >= 2.0:
            return VolatilityLevel.VERY_HIGH
        elif volatility >= 1.5:
            return VolatilityLevel.HIGH
        elif volatility >= 0.5:
            return VolatilityLevel.NORMAL
        elif volatility >= 0.2:
            return VolatilityLevel.LOW
        else:
            return VolatilityLevel.VERY_LOW
    
    def _calculate_percentile(self, value: float, data: List[float]) -> float:
        """Calculate percentile of value in data"""
        if not data:
            return 50.0
        
        sorted_data = sorted(data)
        n = len(sorted_data)
        
        # Find position of value
        position = 0
        for i, v in enumerate(sorted_data):
            if v <= value:
                position = i + 1
        
        return (position / n) * 100
    
    async def _update_market_session(self):
        """Update current market session"""
        try:
            now = datetime.now().time()
            
            if self.market_hours.pre_market_start <= now < self.market_hours.market_open:
                self.market_session = MarketSession.PRE_MARKET
            elif self.market_hours.market_open <= now < self.market_hours.market_close:
                self.market_session = MarketSession.REGULAR
            elif self.market_hours.market_close <= now < self.market_hours.after_hours_end:
                self.market_session = MarketSession.AFTER_HOURS
            else:
                self.market_session = MarketSession.CLOSED
            
        except Exception as e:
            logger.error(f"Error updating market session: {e}")
            self.market_session = MarketSession.CLOSED
    
    async def _publish_condition_event(self, condition_data: MarketConditionData):
        """Publish market condition event"""
        try:
            event_data = {
                "symbol": condition_data.symbol,
                "condition": condition_data.condition.value,
                "volatility_level": condition_data.volatility_level.value,
                "volatility_score": condition_data.volatility_score,
                "price_change_percent": condition_data.price_change_percent,
                "volume_ratio": condition_data.volume_ratio,
                "gap_percent": condition_data.gap_percent,
                "trend_strength": condition_data.trend_strength,
                "support_level": condition_data.support_level,
                "resistance_level": condition_data.resistance_level,
                "confidence": condition_data.confidence,
                "market_session": self.market_session.value,
                "timestamp": condition_data.timestamp.isoformat()
            }
            
            event = TradingEvent(
                id=f"market_condition_{condition_data.symbol}_{int(time.time() * 1000)}",
                event_type=EventType.MARKET_CONDITION_UPDATE,
                user_id="system",
                data=event_data,
                priority=EventPriority.HIGH if condition_data.condition in [
                    MarketCondition.CIRCUIT_BREAKER, MarketCondition.HIGH_VOLATILITY
                ] else EventPriority.NORMAL
            )
            
            await self.event_manager.publish_event(event)
            
        except Exception as e:
            logger.error(f"Error publishing condition event: {e}")
    
    async def _monitoring_loop(self):
        """Background monitoring loop"""
        while True:
            try:
                # Update market session every minute
                await self._update_market_session()
                
                # Update global market condition
                await self._update_global_condition()
                
                # Sleep for 60 seconds
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(10)
    
    async def _update_global_condition(self):
        """Update global market condition based on all symbols"""
        try:
            if not self.current_conditions:
                self.global_market_condition = MarketCondition.NORMAL
                return
            
            # Count condition types
            condition_counts = defaultdict(int)
            for condition_data in self.current_conditions.values():
                condition_counts[condition_data.condition] += 1
            
            # Determine global condition
            total_symbols = len(self.current_conditions)
            
            # Check for critical conditions
            if condition_counts[MarketCondition.CIRCUIT_BREAKER] > 0:
                self.global_market_condition = MarketCondition.CIRCUIT_BREAKER
            elif condition_counts[MarketCondition.HIGH_VOLATILITY] / total_symbols > 0.5:
                self.global_market_condition = MarketCondition.HIGH_VOLATILITY
            elif condition_counts[MarketCondition.GAP_UP] / total_symbols > 0.3:
                self.global_market_condition = MarketCondition.GAP_UP
            elif condition_counts[MarketCondition.GAP_DOWN] / total_symbols > 0.3:
                self.global_market_condition = MarketCondition.GAP_DOWN
            else:
                self.global_market_condition = MarketCondition.NORMAL
            
        except Exception as e:
            logger.error(f"Error updating global condition: {e}")
            self.global_market_condition = MarketCondition.NORMAL
    
    async def _cleanup_loop(self):
        """Background cleanup loop"""
        while True:
            try:
                # Run cleanup every 30 minutes
                await asyncio.sleep(1800)
                
                # Clean up old data
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                
                for symbol in list(self.condition_history.keys()):
                    # Remove old condition data
                    recent_conditions = deque(maxlen=20)
                    for condition in self.condition_history[symbol]:
                        if condition.timestamp > cutoff_time:
                            recent_conditions.append(condition)
                    
                    self.condition_history[symbol] = recent_conditions
                    
                    # If no recent data, remove the symbol
                    if not recent_conditions:
                        del self.condition_history[symbol]
                        if symbol in self.current_conditions:
                            del self.current_conditions[symbol]
                
                logger.debug(f"Cleanup completed. Monitoring {len(self.current_conditions)} symbols")
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    def add_condition_callback(self, callback: Callable[[str, MarketConditionData], None]):
        """Add a callback for condition changes"""
        self.condition_callbacks.append(callback)
    
    def remove_condition_callback(self, callback: Callable[[str, MarketConditionData], None]):
        """Remove a condition callback"""
        if callback in self.condition_callbacks:
            self.condition_callbacks.remove(callback)
    
    def get_current_condition(self, symbol: str) -> Optional[MarketConditionData]:
        """Get current market condition for a symbol"""
        return self.current_conditions.get(symbol)
    
    def get_market_session(self) -> MarketSession:
        """Get current market session"""
        return self.market_session
    
    def get_global_condition(self) -> MarketCondition:
        """Get global market condition"""
        return self.global_market_condition
    
    def is_market_open(self) -> bool:
        """Check if market is currently open"""
        return self.market_session == MarketSession.REGULAR
    
    def is_trading_hours(self) -> bool:
        """Check if it's trading hours (including pre/after market)"""
        return self.market_session in [
            MarketSession.PRE_MARKET, 
            MarketSession.REGULAR, 
            MarketSession.AFTER_HOURS
        ]
    
    def should_halt_trading(self, symbol: str) -> bool:
        """Check if trading should be halted for a symbol"""
        condition = self.get_current_condition(symbol)
        if not condition:
            return False
        
        # Halt trading for extreme conditions
        return condition.condition in [
            MarketCondition.CIRCUIT_BREAKER
        ] or condition.volatility_level == VolatilityLevel.EXTREME
    
    def get_condition_summary(self) -> Dict[str, Any]:
        """Get summary of all market conditions"""
        try:
            summary = {
                "global_condition": self.global_market_condition.value,
                "market_session": self.market_session.value,
                "symbols_monitored": len(self.current_conditions),
                "conditions_by_type": {},
                "volatility_distribution": {},
                "trading_halted_symbols": []
            }
            
            # Count conditions by type
            condition_counts = defaultdict(int)
            volatility_counts = defaultdict(int)
            
            for symbol, condition_data in self.current_conditions.items():
                condition_counts[condition_data.condition.value] += 1
                volatility_counts[condition_data.volatility_level.value] += 1
                
                if self.should_halt_trading(symbol):
                    summary["trading_halted_symbols"].append(symbol)
            
            summary["conditions_by_type"] = dict(condition_counts)
            summary["volatility_distribution"] = dict(volatility_counts)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting condition summary: {e}")
            return {
                "global_condition": "normal",
                "market_session": "closed",
                "symbols_monitored": 0,
                "conditions_by_type": {},
                "volatility_distribution": {},
                "trading_halted_symbols": []
            }

# Global market condition monitor instance
_market_condition_monitor: Optional[MarketConditionMonitor] = None

def get_market_condition_monitor() -> Optional[MarketConditionMonitor]:
    """Get the global market condition monitor instance"""
    return _market_condition_monitor

def set_market_condition_monitor(monitor: MarketConditionMonitor):
    """Set the global market condition monitor instance"""
    global _market_condition_monitor
    _market_condition_monitor = monitor