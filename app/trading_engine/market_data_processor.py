"""
Market Data Processor
Handles price update processing with sub-second latency, data validation, and historical data integration
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import statistics
from collections import deque, defaultdict

from app.database.service import get_db_connection
from app.trading_engine.models import PriceData, MarketStatus
from app.trading_engine.event_bus import EventManager, TradingEvent, EventType, EventPriority

logger = logging.getLogger(__name__)

class DataQuality(Enum):
    """Data quality levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INVALID = "invalid"

class ValidationResult(Enum):
    """Price validation results"""
    VALID = "valid"
    STALE = "stale"
    OUTLIER = "outlier"
    DUPLICATE = "duplicate"
    INVALID_FORMAT = "invalid_format"
    MISSING_DATA = "missing_data"

@dataclass
class PriceValidation:
    """Price validation result"""
    result: ValidationResult
    quality: DataQuality
    confidence: float
    issues: List[str] = field(default_factory=list)
    corrected_price: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ProcessingMetrics:
    """Market data processing metrics"""
    total_updates: int = 0
    valid_updates: int = 0
    invalid_updates: int = 0
    average_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    updates_per_second: float = 0.0
    last_reset: datetime = field(default_factory=datetime.utcnow)

@dataclass
class HistoricalDataPoint:
    """Historical price data point"""
    symbol: str
    timestamp: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    vwap: Optional[float] = None  # Volume Weighted Average Price
    trades_count: Optional[int] = None

class MarketDataProcessor:
    """
    Processes market data with sub-second latency, validation, and historical integration
    """
    
    def __init__(self, event_manager: EventManager):
        self.event_manager = event_manager
        
        # Processing configuration
        self.max_latency_ms = 500  # Maximum acceptable latency
        self.validation_enabled = True
        self.outlier_detection_enabled = True
        self.historical_data_enabled = True
        
        # Data storage
        self.price_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.validation_cache: Dict[str, PriceValidation] = {}
        self.processing_metrics: Dict[str, ProcessingMetrics] = defaultdict(ProcessingMetrics)
        
        # Validation parameters
        self.max_price_change_percent = 10.0  # Maximum price change per update
        self.min_price_threshold = 0.01  # Minimum valid price
        self.max_price_threshold = 1000000.0  # Maximum valid price
        self.stale_data_threshold_ms = 5000  # 5 seconds
        
        # Performance tracking
        self.latency_samples: deque = deque(maxlen=1000)
        self.throughput_counter = 0
        self.last_throughput_reset = datetime.utcnow()
        
        # Overall metrics
        self.metrics = ProcessingMetrics()
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._metrics_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the market data processor"""
        logger.info("Starting Market Data Processor")
        
        # Start background tasks
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_data())
        self._metrics_task = asyncio.create_task(self._update_metrics())
        
        logger.info("Market Data Processor started successfully")
    
    async def stop(self):
        """Stop the market data processor"""
        logger.info("Stopping Market Data Processor")
        
        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._metrics_task:
            self._metrics_task.cancel()
        
        logger.info("Market Data Processor stopped")
    
    def get_metrics(self) -> ProcessingMetrics:
        """Get current processing metrics"""
        return self.metrics
    
    async def get_historical_data(self, symbol: str, hours: int = 24) -> List[PriceData]:
        """
        Get historical price data for a symbol
        
        Args:
            symbol: Symbol to get data for
            hours: Number of hours of historical data
            
        Returns:
            List of PriceData objects
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            if symbol in self.price_history:
                # Filter data within time range
                historical_data = [
                    price_data for price_data in self.price_history[symbol]
                    if price_data.timestamp >= cutoff_time
                ]
                
                # Sort by timestamp (newest first)
                historical_data.sort(key=lambda x: x.timestamp, reverse=True)
                return historical_data
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return []
    
    async def process_price_data(self, price_data: PriceData) -> PriceData:
        """
        Process a PriceData object directly
        
        Args:
            price_data: PriceData object to process
            
        Returns:
            Processed PriceData object
        """
        try:
            # Convert PriceData to dict for internal processing
            raw_data = price_data.to_dict()
            
            # Process using internal method
            success, processed_data = await self.process_price_update(raw_data)
            
            if success and processed_data:
                return processed_data
            else:
                # Return original data if processing failed
                return price_data
                
        except Exception as e:
            logger.error(f"Error processing PriceData object: {e}")
            return price_data
    
    async def validate_price_data(self, price_data: PriceData) -> PriceValidation:
        """
        Validate a PriceData object
        
        Args:
            price_data: PriceData object to validate
            
        Returns:
            PriceValidation result
        """
        try:
            raw_data = price_data.to_dict()
            return await self._validate_price_data(price_data.symbol, raw_data)
        except Exception as e:
            logger.error(f"Error validating PriceData object: {e}")
            return PriceValidation(
                result=ValidationResult.INVALID_FORMAT,
                quality=DataQuality.INVALID,
                confidence=0.0,
                issues=[str(e)]
            )

    async def process_price_update(self, raw_data: Dict[str, Any], 
                                 received_at: Optional[datetime] = None) -> Tuple[bool, Optional[PriceData]]:
        """
        Process incoming price update with validation and latency tracking
        
        Args:
            raw_data: Raw price data from feed
            received_at: When the data was received (for latency calculation)
            
        Returns:
            Tuple of (success, processed_price_data)
        """
        start_time = time.time()
        processing_start = datetime.utcnow()
        
        try:
            # Extract symbol
            symbol = raw_data.get("symbol")
            if not symbol:
                logger.warning("Received price update without symbol")
                return False, None
            
            # Calculate latency if received_at provided
            latency_ms = 0.0
            if received_at:
                latency_ms = (processing_start - received_at).total_seconds() * 1000
                self.latency_samples.append(latency_ms)
                
                # Check latency threshold
                if latency_ms > self.max_latency_ms:
                    logger.warning(f"High latency detected for {symbol}: {latency_ms:.2f}ms")
            
            # Validate price data
            validation_result = await self._validate_price_data(symbol, raw_data)
            
            if validation_result.result == ValidationResult.INVALID_FORMAT:
                logger.error(f"Invalid price data format for {symbol}: {validation_result.issues}")
                self._update_processing_metrics(symbol, False, latency_ms)
                return False, None
            
            # Create price data object
            price_data = await self._create_price_data(symbol, raw_data, validation_result)
            if not price_data:
                self._update_processing_metrics(symbol, False, latency_ms)
                return False, None
            
            # Store in history
            await self._store_price_history(symbol, price_data)
            
            # Update processing metrics
            self._update_processing_metrics(symbol, True, latency_ms)
            
            # Publish processing event
            await self._publish_processing_event(symbol, price_data, validation_result, latency_ms)
            
            processing_time = (time.time() - start_time) * 1000
            logger.debug(f"Processed price update for {symbol} in {processing_time:.2f}ms")
            
            return True, price_data
            
        except Exception as e:
            logger.error(f"Error processing price update: {e}")
            if 'symbol' in locals():
                self._update_processing_metrics(symbol, False, 0.0)
            return False, None
    
    async def _validate_price_data(self, symbol: str, raw_data: Dict[str, Any]) -> PriceValidation:
        """Validate incoming price data"""
        try:
            issues = []
            quality = DataQuality.HIGH
            confidence = 1.0
            
            # Check required fields
            required_fields = ["price", "timestamp"]
            for field in required_fields:
                if field not in raw_data or raw_data[field] is None:
                    issues.append(f"Missing required field: {field}")
                    return PriceValidation(
                        result=ValidationResult.INVALID_FORMAT,
                        quality=DataQuality.INVALID,
                        confidence=0.0,
                        issues=issues
                    )
            
            # Validate price value
            try:
                price = float(raw_data["price"])
                if price <= self.min_price_threshold or price >= self.max_price_threshold:
                    issues.append(f"Price {price} outside valid range")
                    quality = DataQuality.LOW
                    confidence *= 0.5
            except (ValueError, TypeError):
                issues.append("Invalid price format")
                return PriceValidation(
                    result=ValidationResult.INVALID_FORMAT,
                    quality=DataQuality.INVALID,
                    confidence=0.0,
                    issues=issues
                )
            
            # Check timestamp freshness
            try:
                if isinstance(raw_data["timestamp"], str):
                    timestamp = datetime.fromisoformat(raw_data["timestamp"].replace('Z', '+00:00'))
                else:
                    timestamp = raw_data["timestamp"]
                
                age_ms = (datetime.utcnow() - timestamp).total_seconds() * 1000
                if age_ms > self.stale_data_threshold_ms:
                    issues.append(f"Stale data: {age_ms:.0f}ms old")
                    return PriceValidation(
                        result=ValidationResult.STALE,
                        quality=DataQuality.LOW,
                        confidence=0.3,
                        issues=issues
                    )
            except (ValueError, TypeError):
                issues.append("Invalid timestamp format")
                quality = DataQuality.MEDIUM
                confidence *= 0.7
            
            # Outlier detection
            if self.outlier_detection_enabled:
                outlier_result = await self._detect_price_outlier(symbol, price)
                if outlier_result:
                    issues.append(f"Potential outlier: {outlier_result}")
                    return PriceValidation(
                        result=ValidationResult.OUTLIER,
                        quality=DataQuality.LOW,
                        confidence=0.4,
                        issues=issues,
                        corrected_price=await self._get_corrected_price(symbol, price)
                    )
            
            # Check for duplicates
            if await self._is_duplicate_update(symbol, raw_data):
                return PriceValidation(
                    result=ValidationResult.DUPLICATE,
                    quality=DataQuality.MEDIUM,
                    confidence=0.8,
                    issues=["Duplicate price update"]
                )
            
            # Determine final validation result
            if issues:
                result = ValidationResult.VALID if quality != DataQuality.INVALID else ValidationResult.INVALID_FORMAT
            else:
                result = ValidationResult.VALID
            
            return PriceValidation(
                result=result,
                quality=quality,
                confidence=confidence,
                issues=issues
            )
            
        except Exception as e:
            logger.error(f"Error validating price data for {symbol}: {e}")
            return PriceValidation(
                result=ValidationResult.INVALID_FORMAT,
                quality=DataQuality.INVALID,
                confidence=0.0,
                issues=[f"Validation error: {str(e)}"]
            )
    
    async def _detect_price_outlier(self, symbol: str, price: float) -> Optional[str]:
        """Detect if price is an outlier based on recent history"""
        try:
            history = self.price_history.get(symbol)
            if not history or len(history) < 10:
                return None  # Not enough data for outlier detection
            
            # Get recent prices
            recent_prices = [p.price for p in list(history)[-10:]]
            
            # Calculate statistics
            mean_price = statistics.mean(recent_prices)
            std_dev = statistics.stdev(recent_prices) if len(recent_prices) > 1 else 0
            
            # Check if price is more than 3 standard deviations away
            if std_dev > 0:
                z_score = abs(price - mean_price) / std_dev
                if z_score > 3:
                    return f"Z-score: {z_score:.2f}, Mean: {mean_price:.2f}, StdDev: {std_dev:.2f}"
            
            # Check percentage change from last price
            last_price = recent_prices[-1]
            change_percent = abs(price - last_price) / last_price * 100
            if change_percent > self.max_price_change_percent:
                return f"Price change: {change_percent:.2f}% from {last_price:.2f} to {price:.2f}"
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting outlier for {symbol}: {e}")
            return None
    
    async def _get_corrected_price(self, symbol: str, outlier_price: float) -> Optional[float]:
        """Get corrected price for outlier"""
        try:
            history = self.price_history.get(symbol)
            if not history or len(history) < 3:
                return None
            
            # Use median of recent prices as correction
            recent_prices = [p.price for p in list(history)[-5:]]
            return statistics.median(recent_prices)
            
        except Exception as e:
            logger.error(f"Error getting corrected price for {symbol}: {e}")
            return None
    
    async def _is_duplicate_update(self, symbol: str, raw_data: Dict[str, Any]) -> bool:
        """Check if this is a duplicate price update"""
        try:
            history = self.price_history.get(symbol)
            if not history:
                return False
            
            # Check last update
            last_update = history[-1] if history else None
            if not last_update:
                return False
            
            # Compare price and timestamp
            current_price = float(raw_data["price"])
            current_timestamp = raw_data.get("timestamp")
            
            if (abs(last_update.price - current_price) < 0.001 and 
                str(last_update.timestamp) == str(current_timestamp)):
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking duplicate for {symbol}: {e}")
            return False
    
    async def _create_price_data(self, symbol: str, raw_data: Dict[str, Any], 
                               validation: PriceValidation) -> Optional[PriceData]:
        """Create PriceData object from validated raw data"""
        try:
            # Use corrected price if available
            price = validation.corrected_price if validation.corrected_price else float(raw_data["price"])
            
            # Parse timestamp
            timestamp = datetime.utcnow()
            if "timestamp" in raw_data:
                try:
                    if isinstance(raw_data["timestamp"], str):
                        timestamp = datetime.fromisoformat(raw_data["timestamp"].replace('Z', '+00:00'))
                    else:
                        timestamp = raw_data["timestamp"]
                except:
                    pass  # Use current time as fallback
            
            return PriceData(
                symbol=symbol,
                price=price,
                bid=float(raw_data.get("bid", price - 0.01)),
                ask=float(raw_data.get("ask", price + 0.01)),
                volume=int(raw_data.get("volume", 0)),
                timestamp=timestamp,
                change=float(raw_data.get("change", 0.0)),
                change_percent=float(raw_data.get("change_percent", 0.0)),
                high=float(raw_data.get("high", price)),
                low=float(raw_data.get("low", price)),
                open_price=float(raw_data.get("open", price))
            )
            
        except Exception as e:
            logger.error(f"Error creating price data for {symbol}: {e}")
            return None
    
    async def _store_price_history(self, symbol: str, price_data: PriceData):
        """Store price data in history"""
        try:
            self.price_history[symbol].append(price_data)
            
            # Store in database for persistence (async)
            if self.historical_data_enabled:
                asyncio.create_task(self._store_historical_data(symbol, price_data))
                
        except Exception as e:
            logger.error(f"Error storing price history for {symbol}: {e}")
    
    async def _store_historical_data(self, symbol: str, price_data: PriceData):
        """Store historical price data in database"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Create table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_data_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    price REAL NOT NULL,
                    bid REAL,
                    ask REAL,
                    volume INTEGER,
                    change_amount REAL,
                    change_percent REAL,
                    high REAL,
                    low REAL,
                    open_price REAL,
                    timestamp TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert price data
            cursor.execute("""
                INSERT INTO market_data_history 
                (symbol, price, bid, ask, volume, change_amount, change_percent, 
                 high, low, open_price, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol, price_data.price, price_data.bid, price_data.ask,
                price_data.volume, price_data.change, price_data.change_percent,
                price_data.high, price_data.low, price_data.open_price,
                price_data.timestamp
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing historical data for {symbol}: {e}")
    
    def _update_processing_metrics(self, symbol: str, success: bool, latency_ms: float):
        """Update processing metrics for symbol"""
        try:
            metrics = self.processing_metrics[symbol]
            metrics.total_updates += 1
            
            if success:
                metrics.valid_updates += 1
            else:
                metrics.invalid_updates += 1
            
            # Update latency metrics
            if latency_ms > 0:
                if metrics.min_latency_ms == float('inf'):
                    metrics.min_latency_ms = latency_ms
                else:
                    metrics.min_latency_ms = min(metrics.min_latency_ms, latency_ms)
                
                metrics.max_latency_ms = max(metrics.max_latency_ms, latency_ms)
                
                # Update average latency (exponential moving average)
                alpha = 0.1  # Smoothing factor
                if metrics.average_latency_ms == 0:
                    metrics.average_latency_ms = latency_ms
                else:
                    metrics.average_latency_ms = (alpha * latency_ms + 
                                                (1 - alpha) * metrics.average_latency_ms)
            
            # Update throughput counter
            self.throughput_counter += 1
            
        except Exception as e:
            logger.error(f"Error updating processing metrics for {symbol}: {e}")
    
    async def _publish_processing_event(self, symbol: str, price_data: PriceData, 
                                      validation: PriceValidation, latency_ms: float):
        """Publish processing event"""
        try:
            import uuid
            
            event_data = {
                "symbol": symbol,
                "price": price_data.price,
                "validation_result": validation.result.value,
                "data_quality": validation.quality.value,
                "confidence": validation.confidence,
                "latency_ms": latency_ms,
                "issues": validation.issues,
                "timestamp": price_data.timestamp.isoformat()
            }
            
            event = TradingEvent(
                id=str(uuid.uuid4()),
                event_type=EventType.MARKET_DATA_UPDATE,
                user_id="system",
                data=event_data,
                priority=EventPriority.HIGH if validation.quality == DataQuality.HIGH else EventPriority.NORMAL
            )
            
            await self.event_manager.publish_event(event)
            
        except Exception as e:
            logger.error(f"Error publishing processing event for {symbol}: {e}")
    
    async def get_historical_data(self, symbol: str, start_time: datetime, 
                                end_time: datetime, interval: str = "1m") -> List[HistoricalDataPoint]:
        """
        Get historical price data for backtesting
        
        Args:
            symbol: Trading symbol
            start_time: Start time for data
            end_time: End time for data
            interval: Data interval (1m, 5m, 1h, 1d)
            
        Returns:
            List of historical data points
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Query historical data
            cursor.execute("""
                SELECT symbol, timestamp, open_price, high, low, price as close_price, volume
                FROM market_data_history
                WHERE symbol = ? AND timestamp BETWEEN ? AND ?
                ORDER BY timestamp ASC
            """, (symbol, start_time, end_time))
            
            results = cursor.fetchall()
            conn.close()
            
            # Convert to HistoricalDataPoint objects
            historical_data = []
            for row in results:
                historical_data.append(HistoricalDataPoint(
                    symbol=row[0],
                    timestamp=datetime.fromisoformat(row[1]) if isinstance(row[1], str) else row[1],
                    open_price=row[2] or 0.0,
                    high_price=row[3] or 0.0,
                    low_price=row[4] or 0.0,
                    close_price=row[5] or 0.0,
                    volume=row[6] or 0
                ))
            
            # Aggregate data based on interval if needed
            if interval != "1m":
                historical_data = await self._aggregate_historical_data(historical_data, interval)
            
            logger.info(f"Retrieved {len(historical_data)} historical data points for {symbol}")
            return historical_data
            
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return []
    
    async def _aggregate_historical_data(self, data: List[HistoricalDataPoint], 
                                       interval: str) -> List[HistoricalDataPoint]:
        """Aggregate historical data to specified interval"""
        try:
            if not data:
                return []
            
            # Determine interval in minutes
            interval_minutes = {
                "1m": 1, "5m": 5, "15m": 15, "30m": 30,
                "1h": 60, "4h": 240, "1d": 1440
            }.get(interval, 1)
            
            aggregated = []
            current_bucket = []
            bucket_start = None
            
            for point in data:
                # Determine bucket start time
                if bucket_start is None:
                    bucket_start = point.timestamp.replace(second=0, microsecond=0)
                    # Round down to interval boundary
                    minutes_since_hour = bucket_start.minute
                    bucket_start = bucket_start.replace(
                        minute=(minutes_since_hour // interval_minutes) * interval_minutes
                    )
                
                # Check if point belongs to current bucket
                bucket_end = bucket_start + timedelta(minutes=interval_minutes)
                
                if point.timestamp < bucket_end:
                    current_bucket.append(point)
                else:
                    # Process current bucket
                    if current_bucket:
                        aggregated_point = self._create_aggregated_point(current_bucket, bucket_start)
                        aggregated.append(aggregated_point)
                    
                    # Start new bucket
                    current_bucket = [point]
                    bucket_start = bucket_end
            
            # Process final bucket
            if current_bucket:
                aggregated_point = self._create_aggregated_point(current_bucket, bucket_start)
                aggregated.append(aggregated_point)
            
            return aggregated
            
        except Exception as e:
            logger.error(f"Error aggregating historical data: {e}")
            return data
    
    def _create_aggregated_point(self, bucket: List[HistoricalDataPoint], 
                               bucket_start: datetime) -> HistoricalDataPoint:
        """Create aggregated data point from bucket"""
        if not bucket:
            return None
        
        symbol = bucket[0].symbol
        open_price = bucket[0].open_price
        close_price = bucket[-1].close_price
        high_price = max(point.high_price for point in bucket)
        low_price = min(point.low_price for point in bucket)
        total_volume = sum(point.volume for point in bucket)
        
        # Calculate VWAP if possible
        vwap = None
        if total_volume > 0:
            weighted_sum = sum(point.close_price * point.volume for point in bucket)
            vwap = weighted_sum / total_volume
        
        return HistoricalDataPoint(
            symbol=symbol,
            timestamp=bucket_start,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            volume=total_volume,
            vwap=vwap,
            trades_count=len(bucket)
        )
    
    async def get_processing_metrics(self) -> Dict[str, Any]:
        """Get processing performance metrics"""
        try:
            # Calculate overall metrics
            total_updates = sum(m.total_updates for m in self.processing_metrics.values())
            total_valid = sum(m.valid_updates for m in self.processing_metrics.values())
            total_invalid = sum(m.invalid_updates for m in self.processing_metrics.values())
            
            # Calculate average latency
            avg_latency = 0.0
            if self.latency_samples:
                avg_latency = statistics.mean(self.latency_samples)
            
            # Calculate throughput
            now = datetime.utcnow()
            time_diff = (now - self.last_throughput_reset).total_seconds()
            throughput = self.throughput_counter / time_diff if time_diff > 0 else 0
            
            return {
                "overall_metrics": {
                    "total_updates": total_updates,
                    "valid_updates": total_valid,
                    "invalid_updates": total_invalid,
                    "success_rate": (total_valid / total_updates * 100) if total_updates > 0 else 0,
                    "average_latency_ms": avg_latency,
                    "max_latency_ms": max(self.latency_samples) if self.latency_samples else 0,
                    "min_latency_ms": min(self.latency_samples) if self.latency_samples else 0,
                    "throughput_per_second": throughput,
                    "active_symbols": len(self.processing_metrics)
                },
                "symbol_metrics": {
                    symbol: {
                        "total_updates": metrics.total_updates,
                        "valid_updates": metrics.valid_updates,
                        "invalid_updates": metrics.invalid_updates,
                        "success_rate": (metrics.valid_updates / metrics.total_updates * 100) 
                                      if metrics.total_updates > 0 else 0,
                        "average_latency_ms": metrics.average_latency_ms,
                        "max_latency_ms": metrics.max_latency_ms,
                        "min_latency_ms": metrics.min_latency_ms if metrics.min_latency_ms != float('inf') else 0,
                        "last_reset": metrics.last_reset.isoformat()
                    }
                    for symbol, metrics in self.processing_metrics.items()
                },
                "validation_cache_size": len(self.validation_cache),
                "history_symbols": len(self.price_history),
                "total_history_points": sum(len(history) for history in self.price_history.values())
            }
            
        except Exception as e:
            logger.error(f"Error getting processing metrics: {e}")
            return {}
    
    async def _cleanup_expired_data(self):
        """Clean up expired data and reset metrics"""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                now = datetime.utcnow()
                
                # Clean up validation cache (older than 1 hour)
                expired_validations = []
                for key, validation in self.validation_cache.items():
                    # Validation cache doesn't have timestamp, so clean based on size
                    pass
                
                # Limit validation cache size
                if len(self.validation_cache) > 10000:
                    # Remove oldest entries (simplified - in production use LRU)
                    keys_to_remove = list(self.validation_cache.keys())[:1000]
                    for key in keys_to_remove:
                        del self.validation_cache[key]
                
                # Reset throughput counter periodically
                time_since_reset = (now - self.last_throughput_reset).total_seconds()
                if time_since_reset > 3600:  # Reset every hour
                    self.throughput_counter = 0
                    self.last_throughput_reset = now
                
                logger.debug("Completed data cleanup cycle")
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
    
    async def _update_metrics(self):
        """Update processing metrics periodically"""
        while True:
            try:
                await asyncio.sleep(60)  # Update every minute
                
                # Update throughput calculations
                now = datetime.utcnow()
                for symbol, metrics in self.processing_metrics.items():
                    time_diff = (now - metrics.last_reset).total_seconds()
                    if time_diff > 0:
                        metrics.updates_per_second = metrics.total_updates / time_diff
                
                logger.debug("Updated processing metrics")
                
            except Exception as e:
                logger.error(f"Error updating metrics: {e}")

# Global market data processor instance
_market_data_processor: Optional[MarketDataProcessor] = None

def get_market_data_processor() -> Optional[MarketDataProcessor]:
    """Get the global market data processor instance"""
    return _market_data_processor

def set_market_data_processor(processor: MarketDataProcessor):
    """Set the global market data processor instance"""
    global _market_data_processor
    _market_data_processor = processor