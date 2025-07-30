"""
Event Bus Infrastructure for Automatic Trading Engine
Handles event publishing, subscription, and processing
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class EventType(str, Enum):
    """Event types for the trading system"""
    SIGNAL_GENERATED = "signal_generated"
    ORDER_CREATED = "order_created"
    ORDER_SUBMITTED = "order_submitted"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_REJECTED = "order_rejected"
    POSITION_OPENED = "position_opened"
    POSITION_UPDATED = "position_updated"
    POSITION_CLOSED = "position_closed"
    STRATEGY_DEPLOYED = "strategy_deployed"
    STRATEGY_PAUSED = "strategy_paused"
    STRATEGY_STOPPED = "strategy_stopped"
    RISK_VIOLATION = "risk_violation"
    EMERGENCY_STOP = "emergency_stop"
    MARKET_DATA_UPDATE = "market_data_update"
    MARKET_CONDITION_UPDATE = "market_condition_update"
    SYSTEM_ERROR = "system_error"
    USER_ACTION = "user_action"

class EventPriority(int, Enum):
    """Event priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class TradingEvent:
    """Base trading event structure"""
    id: str
    event_type: EventType
    user_id: str
    data: Dict[str, Any]
    priority: EventPriority = EventPriority.NORMAL
    created_at: datetime = None
    processed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "user_id": self.user_id,
            "data": self.data,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradingEvent':
        """Create event from dictionary"""
        return cls(
            id=data["id"],
            event_type=EventType(data["event_type"]),
            user_id=data["user_id"],
            data=data["data"],
            priority=EventPriority(data["priority"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            processed_at=datetime.fromisoformat(data["processed_at"]) if data["processed_at"] else None,
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3)
        )

class EventHandler:
    """Base event handler interface"""
    
    def __init__(self, handler_id: str, event_types: List[EventType]):
        self.handler_id = handler_id
        self.event_types = event_types
        self.is_active = True
    
    async def handle_event(self, event: TradingEvent) -> bool:
        """Handle an event. Return True if successful, False to retry"""
        raise NotImplementedError("Subclasses must implement handle_event")
    
    def can_handle(self, event_type: EventType) -> bool:
        """Check if this handler can process the given event type"""
        return event_type in self.event_types

class EventBus:
    """
    In-memory event bus for trading system
    Can be easily replaced with Redis or other message brokers
    """
    
    def __init__(self):
        self.handlers: Dict[EventType, List[EventHandler]] = defaultdict(list)
        self.event_queue: deque = deque()
        self.priority_queues: Dict[EventPriority, deque] = {
            priority: deque() for priority in EventPriority
        }
        self.event_history: List[TradingEvent] = []
        self.processing_lock = threading.Lock()
        self.is_processing = False
        self.max_history_size = 10000
        
        # Statistics
        self.stats = {
            "events_published": 0,
            "events_processed": 0,
            "events_failed": 0,
            "handlers_registered": 0
        }
    
    def register_handler(self, handler: EventHandler) -> bool:
        """Register an event handler"""
        try:
            for event_type in handler.event_types:
                self.handlers[event_type].append(handler)
            
            self.stats["handlers_registered"] += 1
            logger.info(f"Registered handler {handler.handler_id} for events: {handler.event_types}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering handler {handler.handler_id}: {e}")
            return False
    
    def unregister_handler(self, handler_id: str) -> bool:
        """Unregister an event handler"""
        try:
            removed_count = 0
            for event_type, handler_list in self.handlers.items():
                self.handlers[event_type] = [
                    h for h in handler_list if h.handler_id != handler_id
                ]
                removed_count += len(handler_list) - len(self.handlers[event_type])
            
            if removed_count > 0:
                self.stats["handlers_registered"] -= 1
                logger.info(f"Unregistered handler {handler_id}")
                return True
            else:
                logger.warning(f"Handler {handler_id} not found for unregistration")
                return False
                
        except Exception as e:
            logger.error(f"Error unregistering handler {handler_id}: {e}")
            return False
    
    async def publish_event(self, event: TradingEvent) -> bool:
        """Publish an event to the bus"""
        try:
            # Add to appropriate priority queue
            self.priority_queues[event.priority].append(event)
            
            # Add to history
            self.event_history.append(event)
            if len(self.event_history) > self.max_history_size:
                self.event_history.pop(0)
            
            self.stats["events_published"] += 1
            
            logger.debug(f"Published event {event.id} of type {event.event_type}")
            
            # Start processing if not already running
            if not self.is_processing:
                asyncio.create_task(self.process_events())
            
            return True
            
        except Exception as e:
            logger.error(f"Error publishing event {event.id}: {e}")
            return False
    
    async def process_events(self):
        """Process events from priority queues"""
        with self.processing_lock:
            if self.is_processing:
                return
            self.is_processing = True
        
        try:
            while True:
                event = self._get_next_event()
                if not event:
                    break
                
                await self._process_single_event(event)
                
        except Exception as e:
            logger.error(f"Error in event processing loop: {e}")
        finally:
            self.is_processing = False
    
    def _get_next_event(self) -> Optional[TradingEvent]:
        """Get next event from priority queues (highest priority first)"""
        for priority in sorted(EventPriority, key=lambda x: x.value, reverse=True):
            if self.priority_queues[priority]:
                return self.priority_queues[priority].popleft()
        return None
    
    async def _process_single_event(self, event: TradingEvent):
        """Process a single event"""
        try:
            handlers = self.handlers.get(event.event_type, [])
            if not handlers:
                logger.warning(f"No handlers registered for event type {event.event_type}")
                return
            
            # Process event with all registered handlers
            success_count = 0
            for handler in handlers:
                if not handler.is_active:
                    continue
                
                try:
                    success = await handler.handle_event(event)
                    if success:
                        success_count += 1
                    else:
                        logger.warning(f"Handler {handler.handler_id} failed to process event {event.id}")
                        
                except Exception as e:
                    logger.error(f"Handler {handler.handler_id} threw exception processing event {event.id}: {e}")
            
            if success_count > 0:
                event.processed_at = datetime.now()
                self.stats["events_processed"] += 1
                logger.debug(f"Successfully processed event {event.id} with {success_count} handlers")
            else:
                # Retry logic
                if event.retry_count < event.max_retries:
                    event.retry_count += 1
                    logger.info(f"Retrying event {event.id} (attempt {event.retry_count})")
                    await asyncio.sleep(2 ** event.retry_count)  # Exponential backoff
                    self.priority_queues[event.priority].append(event)
                else:
                    logger.error(f"Event {event.id} failed after {event.max_retries} retries")
                    self.stats["events_failed"] += 1
                    
        except Exception as e:
            logger.error(f"Error processing event {event.id}: {e}")
            self.stats["events_failed"] += 1
    
    def get_event_history(self, 
                         user_id: Optional[str] = None,
                         event_type: Optional[EventType] = None,
                         limit: int = 100) -> List[TradingEvent]:
        """Get event history with optional filtering"""
        filtered_events = self.event_history
        
        if user_id:
            filtered_events = [e for e in filtered_events if e.user_id == user_id]
        
        if event_type:
            filtered_events = [e for e in filtered_events if e.event_type == event_type]
        
        return filtered_events[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        queue_sizes = {
            priority.name: len(queue) 
            for priority, queue in self.priority_queues.items()
        }
        
        handler_counts = {
            event_type.value: len(handlers)
            for event_type, handlers in self.handlers.items()
        }
        
        return {
            **self.stats,
            "queue_sizes": queue_sizes,
            "handler_counts": handler_counts,
            "total_queue_size": sum(queue_sizes.values()),
            "history_size": len(self.event_history),
            "is_processing": self.is_processing
        }
    
    def clear_history(self):
        """Clear event history"""
        self.event_history.clear()
        logger.info("Event history cleared")
    
    async def subscribe_to_events(self, event_types: List[str], handler_func: Callable) -> bool:
        """Subscribe to events with a callback function"""
        try:
            # Create a handler wrapper
            class CallbackHandler(EventHandler):
                def __init__(self, handler_id: str, event_types: List[EventType], callback):
                    super().__init__(handler_id, event_types)
                    self.callback = callback
                
                async def handle_event(self, event: TradingEvent) -> bool:
                    try:
                        await self.callback(event)
                        return True
                    except Exception as e:
                        logger.error(f"Callback handler error: {e}")
                        return False
            
            # Convert string event types to EventType enums
            enum_event_types = []
            for event_type_str in event_types:
                try:
                    enum_event_types.append(EventType(event_type_str))
                except ValueError:
                    # Handle custom event types
                    logger.warning(f"Unknown event type: {event_type_str}")
            
            if not enum_event_types:
                return False
            
            # Create and register handler
            handler_id = f"callback_handler_{len(self.handlers)}"
            handler = CallbackHandler(handler_id, enum_event_types, handler_func)
            return self.register_handler(handler)
            
        except Exception as e:
            logger.error(f"Error subscribing to events: {e}")
            return False

# Global event bus instance
event_bus = EventBus()

# Convenience functions for common event types
async def publish_signal_event(user_id: str, signal_data: Dict[str, Any]) -> bool:
    """Publish a signal generated event"""
    event = TradingEvent(
        id=str(uuid.uuid4()),
        event_type=EventType.SIGNAL_GENERATED,
        user_id=user_id,
        data=signal_data,
        priority=EventPriority.HIGH
    )
    return await event_bus.publish_event(event)

async def publish_order_event(user_id: str, event_type: EventType, order_data: Dict[str, Any]) -> bool:
    """Publish an order-related event"""
    event = TradingEvent(
        id=str(uuid.uuid4()),
        event_type=event_type,
        user_id=user_id,
        data=order_data,
        priority=EventPriority.HIGH
    )
    return await event_bus.publish_event(event)

async def publish_risk_event(user_id: str, risk_data: Dict[str, Any]) -> bool:
    """Publish a risk violation event"""
    event = TradingEvent(
        id=str(uuid.uuid4()),
        event_type=EventType.RISK_VIOLATION,
        user_id=user_id,
        data=risk_data,
        priority=EventPriority.CRITICAL
    )
    return await event_bus.publish_event(event)

async def publish_emergency_stop(user_id: str, reason: str) -> bool:
    """Publish an emergency stop event"""
    event = TradingEvent(
        id=str(uuid.uuid4()),
        event_type=EventType.EMERGENCY_STOP,
        user_id=user_id,
        data={"reason": reason, "timestamp": datetime.now().isoformat()},
        priority=EventPriority.CRITICAL
    )
    return await event_bus.publish_event(event)

async def publish_market_data_event(symbol: str, price_data: Dict[str, Any]) -> bool:
    """Publish a market data update event"""
    event = TradingEvent(
        id=str(uuid.uuid4()),
        event_type=EventType.MARKET_DATA_UPDATE,
        user_id="system",  # System-wide event
        data={"symbol": symbol, **price_data},
        priority=EventPriority.NORMAL
    )
    return await event_bus.publish_event(event)

# Market-specific event classes
@dataclass
class MarketEvent:
    """Market-specific event for price updates and status changes"""
    event_type: str
    symbol: str
    data: Dict[str, Any]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "event_type": self.event_type,
            "symbol": self.symbol,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }

@dataclass
class SignalEvent:
    """Signal event for trading signals"""
    signal_id: str
    user_id: str
    symbol: str
    signal_type: Any  # Will be SignalType enum
    confidence_score: float
    priority: Any  # Will be SignalPriority enum
    metadata: Dict[str, Any]
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "signal_id": self.signal_id,
            "user_id": self.user_id,
            "symbol": self.symbol,
            "signal_type": str(self.signal_type),
            "confidence_score": self.confidence_score,
            "priority": str(self.priority),
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }

# Event Manager alias for compatibility
EventManager = EventBus

# Function to get global event manager
def get_event_manager() -> EventBus:
    """Get the global event manager instance"""
    return event_bus