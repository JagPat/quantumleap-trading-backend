"""
Market Data Manager
Handles real-time market data processing, distribution, and market status monitoring
"""
import asyncio
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
try:
    import websockets
except ImportError:
    websockets = None

from concurrent.futures import ThreadPoolExecutor

try:
    import aiohttp
except ImportError:
    aiohttp = None

from app.database.service import get_db_connection
from app.trading_engine.models import MarketStatus, PriceData, MarketHours
from app.trading_engine.event_bus import EventManager, MarketEvent

logger = logging.getLogger(__name__)

class MarketState(Enum):
    CLOSED = "closed"
    PRE_MARKET = "pre_market"
    OPEN = "open"
    POST_MARKET = "post_market"
    HOLIDAY = "holiday"

class DataFeedStatus(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    ERROR = "error"

@dataclass
class PriceUpdate:
    """Real-time price update data"""
    symbol: str
    price: float
    bid: float
    ask: float
    volume: int
    timestamp: datetime
    change: float = 0.0
    change_percent: float = 0.0
    high: float = 0.0
    low: float = 0.0
    open_price: float = 0.0

@dataclass
class MarketDataSubscription:
    """Market data subscription details"""
    symbol: str
    subscriber_id: str
    callback: Callable[[PriceUpdate], None]
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_update: Optional[datetime] = None
    is_active: bool = True

@dataclass
class DataFeedConnection:
    """Data feed connection details"""
    feed_name: str
    url: str
    status: DataFeedStatus
    websocket: Optional[Any] = None
    last_heartbeat: Optional[datetime] = None
    reconnect_attempts: int = 0
    max_reconnect_attempts: int = 5
    reconnect_delay: float = 1.0

class MarketDataManager:
    """
    Manages real-time market data feeds, subscriptions, and distribution
    """
    
    def __init__(self, event_manager: EventManager):
        self.event_manager = event_manager
        self.subscriptions: Dict[str, List[MarketDataSubscription]] = {}
        self.price_cache: Dict[str, PriceUpdate] = {}
        self.data_feeds: Dict[str, DataFeedConnection] = {}
        self.market_status = MarketState.CLOSED
        self.market_hours: Optional[MarketHours] = None
        
        # Configuration
        self.price_update_threshold = 0.01  # Minimum price change to trigger update
        self.heartbeat_interval = 30  # seconds
        self.cache_expiry = 300  # 5 minutes
        self.max_price_age = 60  # 1 minute
        
        # Background tasks
        self._market_status_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Thread pool for blocking operations
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Initialize data feeds
        self._initialize_data_feeds()
    
    def _initialize_data_feeds(self):
        """Initialize available data feed connections"""
        # Primary data feed (would be configured based on broker)
        self.data_feeds["primary"] = DataFeedConnection(
            feed_name="primary",
            url="wss://api.example.com/market-data",  # Would be actual broker WebSocket
            status=DataFeedStatus.DISCONNECTED
        )
        
        # Backup data feed
        self.data_feeds["backup"] = DataFeedConnection(
            feed_name="backup",
            url="wss://backup-api.example.com/market-data",
            status=DataFeedStatus.DISCONNECTED
        )
    
    async def start(self):
        """Start the market data manager"""
        logger.info("Starting Market Data Manager")
        
        # Start background tasks
        self._market_status_task = asyncio.create_task(self._monitor_market_status())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_monitor())
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_data())
        
        # Connect to data feeds
        await self._connect_data_feeds()
        
        logger.info("Market Data Manager started successfully")
    
    async def stop(self):
        """Stop the market data manager"""
        logger.info("Stopping Market Data Manager")
        
        # Cancel background tasks
        if self._market_status_task:
            self._market_status_task.cancel()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Disconnect data feeds
        await self._disconnect_data_feeds()
        
        # Shutdown thread pool
        self.executor.shutdown(wait=True)
        
        logger.info("Market Data Manager stopped")
    
    async def subscribe_to_symbol(self, symbol: str, subscriber_id: str, 
                                callback: Callable[[PriceUpdate], None]) -> bool:
        """
        Subscribe to real-time price updates for a symbol
        
        Args:
            symbol: Trading symbol to subscribe to
            subscriber_id: Unique identifier for the subscriber
            callback: Function to call when price updates are received
            
        Returns:
            bool: True if subscription successful, False otherwise
        """
        try:
            logger.info(f"Subscribing {subscriber_id} to {symbol}")
            
            # Create subscription
            subscription = MarketDataSubscription(
                symbol=symbol,
                subscriber_id=subscriber_id,
                callback=callback
            )
            
            # Add to subscriptions
            if symbol not in self.subscriptions:
                self.subscriptions[symbol] = []
            
            # Check if subscriber already exists
            existing = next((s for s in self.subscriptions[symbol] 
                           if s.subscriber_id == subscriber_id), None)
            if existing:
                existing.callback = callback
                existing.is_active = True
                logger.info(f"Updated existing subscription for {subscriber_id} to {symbol}")
            else:
                self.subscriptions[symbol].append(subscription)
                logger.info(f"Created new subscription for {subscriber_id} to {symbol}")
            
            # Subscribe to symbol in data feed
            await self._subscribe_to_feed(symbol)
            
            # Send current price if available
            if symbol in self.price_cache:
                try:
                    callback(self.price_cache[symbol])
                except Exception as e:
                    logger.error(f"Error calling callback for {subscriber_id}: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error subscribing to {symbol}: {e}")
            return False
    
    async def unsubscribe_from_symbol(self, symbol: str, subscriber_id: str) -> bool:
        """
        Unsubscribe from price updates for a symbol
        
        Args:
            symbol: Trading symbol to unsubscribe from
            subscriber_id: Unique identifier for the subscriber
            
        Returns:
            bool: True if unsubscription successful, False otherwise
        """
        try:
            logger.info(f"Unsubscribing {subscriber_id} from {symbol}")
            
            if symbol not in self.subscriptions:
                return True
            
            # Remove subscription
            self.subscriptions[symbol] = [
                s for s in self.subscriptions[symbol] 
                if s.subscriber_id != subscriber_id
            ]
            
            # If no more subscribers, unsubscribe from feed
            if not self.subscriptions[symbol]:
                await self._unsubscribe_from_feed(symbol)
                del self.subscriptions[symbol]
            
            logger.info(f"Unsubscribed {subscriber_id} from {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error unsubscribing from {symbol}: {e}")
            return False
    
    async def get_current_price(self, symbol: str) -> Optional[PriceUpdate]:
        """
        Get current price for a symbol
        
        Args:
            symbol: Trading symbol
            
        Returns:
            PriceUpdate: Current price data or None if not available
        """
        try:
            if symbol in self.price_cache:
                price_data = self.price_cache[symbol]
                
                # Check if price is too old
                age = (datetime.utcnow() - price_data.timestamp).total_seconds()
                if age <= self.max_price_age:
                    return price_data
                else:
                    logger.warning(f"Price data for {symbol} is {age}s old")
            
            # Try to fetch fresh price
            fresh_price = await self._fetch_current_price(symbol)
            if fresh_price:
                self.price_cache[symbol] = fresh_price
                return fresh_price
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            return None
    
    async def get_market_status(self) -> Dict[str, Any]:
        """
        Get current market status
        
        Returns:
            Dict containing market status information
        """
        try:
            return {
                "status": self.market_status.value,
                "is_open": self.market_status == MarketState.OPEN,
                "market_hours": {
                    "open": self.market_hours.open_time.isoformat() if self.market_hours else None,
                    "close": self.market_hours.close_time.isoformat() if self.market_hours else None,
                    "timezone": self.market_hours.timezone if self.market_hours else None
                } if self.market_hours else None,
                "data_feeds": {
                    name: {
                        "status": feed.status.value,
                        "last_heartbeat": feed.last_heartbeat.isoformat() if feed.last_heartbeat else None,
                        "reconnect_attempts": feed.reconnect_attempts
                    }
                    for name, feed in self.data_feeds.items()
                },
                "active_subscriptions": len(self.subscriptions),
                "cached_symbols": len(self.price_cache),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting market status: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def handle_price_update(self, price_data: Dict[str, Any]) -> bool:
        """
        Handle incoming price update from data feed
        
        Args:
            price_data: Raw price data from feed
            
        Returns:
            bool: True if update processed successfully
        """
        try:
            # Parse price data
            symbol = price_data.get("symbol")
            if not symbol:
                logger.warning("Received price update without symbol")
                return False
            
            # Create price update object
            price_update = PriceUpdate(
                symbol=symbol,
                price=float(price_data.get("price", 0)),
                bid=float(price_data.get("bid", 0)),
                ask=float(price_data.get("ask", 0)),
                volume=int(price_data.get("volume", 0)),
                timestamp=datetime.utcnow(),
                change=float(price_data.get("change", 0)),
                change_percent=float(price_data.get("change_percent", 0)),
                high=float(price_data.get("high", 0)),
                low=float(price_data.get("low", 0)),
                open_price=float(price_data.get("open", 0))
            )
            
            # Check if update is significant enough
            if not self._is_significant_update(symbol, price_update):
                return True
            
            # Update cache
            self.price_cache[symbol] = price_update
            
            # Distribute to subscribers
            await self._distribute_price_update(symbol, price_update)
            
            # Publish market event
            from app.trading_engine.event_bus import TradingEvent, EventType, EventPriority
            import uuid
            
            trading_event = TradingEvent(
                id=str(uuid.uuid4()),
                event_type=EventType.MARKET_DATA_UPDATE,
                user_id="system",
                data={"symbol": symbol, **price_data},
                priority=EventPriority.NORMAL
            )
            await self.event_manager.publish_event(trading_event)
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling price update: {e}")
            return False
    
    def _is_significant_update(self, symbol: str, new_price: PriceUpdate) -> bool:
        """Check if price update is significant enough to distribute"""
        if symbol not in self.price_cache:
            return True
        
        old_price = self.price_cache[symbol]
        price_change = abs(new_price.price - old_price.price) / old_price.price
        
        return price_change >= self.price_update_threshold
    
    async def _distribute_price_update(self, symbol: str, price_update: PriceUpdate):
        """Distribute price update to all subscribers"""
        if symbol not in self.subscriptions:
            return
        
        # Update subscription timestamps and call callbacks
        for subscription in self.subscriptions[symbol]:
            if not subscription.is_active:
                continue
            
            try:
                subscription.last_update = datetime.utcnow()
                subscription.callback(price_update)
            except Exception as e:
                logger.error(f"Error calling callback for {subscription.subscriber_id}: {e}")
                # Mark subscription as inactive if callback fails repeatedly
                subscription.is_active = False
    
    async def _connect_data_feeds(self):
        """Connect to all configured data feeds"""
        for feed_name, feed in self.data_feeds.items():
            try:
                await self._connect_single_feed(feed)
            except Exception as e:
                logger.error(f"Failed to connect to {feed_name}: {e}")
    
    async def _connect_single_feed(self, feed: DataFeedConnection):
        """Connect to a single data feed"""
        try:
            logger.info(f"Connecting to {feed.feed_name} data feed")
            feed.status = DataFeedStatus.RECONNECTING
            
            # For demo purposes, we'll simulate a connection
            # In production, this would establish a real WebSocket connection
            await asyncio.sleep(1)  # Simulate connection time
            
            feed.status = DataFeedStatus.CONNECTED
            feed.last_heartbeat = datetime.utcnow()
            feed.reconnect_attempts = 0
            
            logger.info(f"Connected to {feed.feed_name} data feed")
            
            # Start listening for data (would be actual WebSocket listener)
            asyncio.create_task(self._listen_to_feed(feed))
            
        except Exception as e:
            logger.error(f"Error connecting to {feed.feed_name}: {e}")
            feed.status = DataFeedStatus.ERROR
            
            # Schedule reconnection
            if feed.reconnect_attempts < feed.max_reconnect_attempts:
                feed.reconnect_attempts += 1
                delay = feed.reconnect_delay * (2 ** feed.reconnect_attempts)
                asyncio.create_task(self._reconnect_feed(feed, delay))
    
    async def _listen_to_feed(self, feed: DataFeedConnection):
        """Listen to data feed for price updates"""
        try:
            while feed.status == DataFeedStatus.CONNECTED:
                # Simulate receiving price data
                # In production, this would read from WebSocket
                await asyncio.sleep(1)
                
                # Generate mock price updates for subscribed symbols
                for symbol in self.subscriptions.keys():
                    mock_price_data = self._generate_mock_price_data(symbol)
                    await self.handle_price_update(mock_price_data)
                
                # Update heartbeat
                feed.last_heartbeat = datetime.utcnow()
                
        except Exception as e:
            logger.error(f"Error listening to {feed.feed_name}: {e}")
            feed.status = DataFeedStatus.ERROR
    
    def _generate_mock_price_data(self, symbol: str) -> Dict[str, Any]:
        """Generate mock price data for testing"""
        import random
        
        # Get base price or use default
        base_price = 100.0
        if symbol in self.price_cache:
            base_price = self.price_cache[symbol].price
        
        # Generate small random price movement
        change_percent = random.uniform(-0.02, 0.02)  # ±2%
        new_price = base_price * (1 + change_percent)
        
        return {
            "symbol": symbol,
            "price": round(new_price, 2),
            "bid": round(new_price - 0.01, 2),
            "ask": round(new_price + 0.01, 2),
            "volume": random.randint(1000, 10000),
            "change": round(new_price - base_price, 2),
            "change_percent": round(change_percent * 100, 2),
            "high": round(new_price * 1.01, 2),
            "low": round(new_price * 0.99, 2),
            "open": round(base_price, 2)
        }
    
    async def _reconnect_feed(self, feed: DataFeedConnection, delay: float):
        """Reconnect to a data feed after delay"""
        await asyncio.sleep(delay)
        await self._connect_single_feed(feed)
    
    async def _disconnect_data_feeds(self):
        """Disconnect from all data feeds"""
        for feed in self.data_feeds.values():
            try:
                if feed.websocket:
                    await feed.websocket.close()
                feed.status = DataFeedStatus.DISCONNECTED
            except Exception as e:
                logger.error(f"Error disconnecting from {feed.feed_name}: {e}")
    
    async def _subscribe_to_feed(self, symbol: str):
        """Subscribe to symbol in data feed"""
        # In production, this would send subscription message to WebSocket
        logger.debug(f"Subscribed to {symbol} in data feed")
    
    async def _unsubscribe_from_feed(self, symbol: str):
        """Unsubscribe from symbol in data feed"""
        # In production, this would send unsubscription message to WebSocket
        logger.debug(f"Unsubscribed from {symbol} in data feed")
    
    async def _fetch_current_price(self, symbol: str) -> Optional[PriceUpdate]:
        """Fetch current price from REST API"""
        try:
            # In production, this would make HTTP request to broker API
            # For now, generate mock data
            mock_data = self._generate_mock_price_data(symbol)
            
            return PriceUpdate(
                symbol=symbol,
                price=mock_data["price"],
                bid=mock_data["bid"],
                ask=mock_data["ask"],
                volume=mock_data["volume"],
                timestamp=datetime.utcnow(),
                change=mock_data["change"],
                change_percent=mock_data["change_percent"],
                high=mock_data["high"],
                low=mock_data["low"],
                open_price=mock_data["open"]
            )
            
        except Exception as e:
            logger.error(f"Error fetching current price for {symbol}: {e}")
            return None
    
    async def _monitor_market_status(self):
        """Monitor and update market status"""
        while True:
            try:
                # Check current market status
                current_status = await self._get_current_market_status()
                
                if current_status != self.market_status:
                    old_status = self.market_status
                    self.market_status = current_status
                    
                    logger.info(f"Market status changed: {old_status.value} -> {current_status.value}")
                    
                    # Publish market status event
                    from app.trading_engine.event_bus import TradingEvent, EventType, EventPriority
                    import uuid
                    
                    trading_event = TradingEvent(
                        id=str(uuid.uuid4()),
                        event_type=EventType.MARKET_DATA_UPDATE,
                        user_id="system",
                        data={
                            "symbol": "MARKET",
                            "old_status": old_status.value,
                            "new_status": current_status.value,
                            "timestamp": datetime.utcnow().isoformat()
                        },
                        priority=EventPriority.HIGH
                    )
                    await self.event_manager.publish_event(trading_event)
                
                # Check every minute
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error monitoring market status: {e}")
                await asyncio.sleep(60)
    
    async def _get_current_market_status(self) -> MarketState:
        """Get current market status based on time"""
        try:
            now = datetime.utcnow()
            
            # Simple market hours logic (9:30 AM - 4:00 PM EST)
            # In production, this would use actual market calendar
            market_open = now.replace(hour=14, minute=30, second=0, microsecond=0)  # 9:30 AM EST in UTC
            market_close = now.replace(hour=21, minute=0, second=0, microsecond=0)  # 4:00 PM EST in UTC
            
            # Check if weekend
            if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
                return MarketState.CLOSED
            
            # Check market hours
            if now < market_open:
                return MarketState.PRE_MARKET
            elif now > market_close:
                return MarketState.POST_MARKET
            else:
                return MarketState.OPEN
                
        except Exception as e:
            logger.error(f"Error getting market status: {e}")
            return MarketState.CLOSED
    
    async def _heartbeat_monitor(self):
        """Monitor data feed heartbeats"""
        while True:
            try:
                now = datetime.utcnow()
                
                for feed_name, feed in self.data_feeds.items():
                    if feed.status == DataFeedStatus.CONNECTED and feed.last_heartbeat:
                        time_since_heartbeat = (now - feed.last_heartbeat).total_seconds()
                        
                        if time_since_heartbeat > self.heartbeat_interval * 2:
                            logger.warning(f"No heartbeat from {feed_name} for {time_since_heartbeat}s")
                            feed.status = DataFeedStatus.ERROR
                            
                            # Attempt reconnection
                            asyncio.create_task(self._connect_single_feed(feed))
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Error in heartbeat monitor: {e}")
                await asyncio.sleep(self.heartbeat_interval)
    
    async def _cleanup_expired_data(self):
        """Clean up expired price data and inactive subscriptions"""
        while True:
            try:
                now = datetime.utcnow()
                
                # Clean up expired price cache
                expired_symbols = []
                for symbol, price_data in self.price_cache.items():
                    age = (now - price_data.timestamp).total_seconds()
                    if age > self.cache_expiry:
                        expired_symbols.append(symbol)
                
                for symbol in expired_symbols:
                    del self.price_cache[symbol]
                    logger.debug(f"Removed expired price data for {symbol}")
                
                # Clean up inactive subscriptions
                for symbol in list(self.subscriptions.keys()):
                    active_subs = [s for s in self.subscriptions[symbol] if s.is_active]
                    if not active_subs:
                        await self._unsubscribe_from_feed(symbol)
                        del self.subscriptions[symbol]
                        logger.debug(f"Removed inactive subscriptions for {symbol}")
                    else:
                        self.subscriptions[symbol] = active_subs
                
                # Run cleanup every 5 minutes
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(300)

# Global market data manager instance
_market_data_manager: Optional[MarketDataManager] = None

def get_market_data_manager() -> Optional[MarketDataManager]:
    """Get the global market data manager instance"""
    return _market_data_manager

def set_market_data_manager(manager: MarketDataManager):
    """Set the global market data manager instance"""
    global _market_data_manager
    _market_data_manager = manager