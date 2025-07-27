"""
Simple Event Bus System
Event management without external dependencies
"""
import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Callable, Optional, Set
from collections import defaultdict, deque
from enum import Enum
import threading
import json

logger = logging.getLogger(__name__)

class EventType(Enum):
    """Event types for the trading system"""
    SIGNAL_RECEIVED = "signal_received"
    ORDER_CREATED = "order_created"
    ORDER_EXECUTED = "order_executed"
    ORDER_CANCELLED = "order_cancelled"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    RISK_ALERT = "risk_alert"
    MARKET_DATA_UPDATE = "market_data_update"
    STRATEGY_STARTED = "strategy_started"
    STRATEGY_STOPPED = "strategy_stopped"
    SYSTEM_ERROR = "system_error"
    HEALTH_CHECK = "health_check"

class EventPriority(Enum):
    """Event priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

class TradingEvent:
    """Trading system event"""
    
    def __init__(self, event_type: EventType, data: Dict[str, Any], 
                 user_id: str = None, priority: EventPriority = EventPriority.NORMAL,
                 correlation_id: str = None):
        self.id = str(uuid.uuid4())
        self.event_type = event_type
        self.data = data
        self.user_id = user_id
        self.priority = priority
        self.correlation_id = correlation_id or self.id
        self.timestamp = datetime.now()
        self.processed = False
        self.processing_time = None
        self.error = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            'id': self.id,
            'event_type': self.event_type.value,
            'data': self.data,
            'user_id': self.user_id,
            'priority': self.priority.value,
            'correlation_id': self.correlation_id,
            'timestamp': self.timestamp.isoformat(),
            'processed': self.processed,
            'processing_time': self.processing_time,
            'error': self.error
        }
    
    def mark_processed(self, processing_time: float = None, error: str = None):
        """Mark event as processed"""
        self.processed = True
        self.processing_time = processing_time
        self.error = error

class EventHandler:
    """Event handler wrapper"""
    
    def __init__(self, handler_func: Callable, handler_id: str = None, 
                 async_handler: bool = False):
        self.handler_func = handler_func
        self.handler_id = handler_id or str(uuid.uuid4())
        self.async_handler = async_handler
        self.created_at = datetime.now()
        self.call_count = 0
        self.error_count = 0
        self.last_called = None
        self.last_error = None
    
    async def handle(self, event: TradingEvent) -> bool:
        """Handle an event"""
        try:
            start_time = time.time()
            self.call_count += 1
            self.last_called = datetime.now()
            
            if self.async_handler:
                await self.handler_func(event)
            else:
                self.handler_func(event)
            
            processing_time = (time.time() - start_time) * 1000  # ms
            event.mark_processed(processing_time)
            return True
            
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            event.mark_processed(error=str(e))
            logger.error(f"Event handler {self.handler_id} failed: {e}")
            return False

class SimpleEventBus:
    """Simple event bus implementation"""
    
    def __init__(self, max_history: int = 10000):
        self.handlers: Dict[EventType, List[EventHandler]] = defaultdict(list)
        self.event_history: deque = deque(maxlen=max_history)
        self.event_queue: asyncio.Queue = None
        self.processing_task: asyncio.Task = None
        self.running = False
        self.lock = threading.Lock()
        self.statistics = {
            'events_published': 0,
            'events_processed': 0,
            'events_failed': 0,
            'handlers_registered': 0,
            'start_time': datetime.now()
        }
    
    async def start(self):
        """Start the event bus"""
        if self.running:
            return
        
        self.event_queue = asyncio.Queue()
        self.running = True
        self.processing_task = asyncio.create_task(self._process_events())
        logger.info("Event bus started")
    
    async def stop(self):
        """Stop the event bus"""
        if not self.running:
            return
        
        self.running = False
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Event bus stopped")
    
    def subscribe(self, event_type: EventType, handler: Callable, 
                 handler_id: str = None, async_handler: bool = False) -> str:
        """Subscribe to an event type"""
        event_handler = EventHandler(handler, handler_id, async_handler)
        
        with self.lock:
            self.handlers[event_type].append(event_handler)
            self.statistics['handlers_registered'] += 1
        
        logger.info(f"Handler {event_handler.handler_id} subscribed to {event_type.value}")
        return event_handler.handler_id
    
    def unsubscribe(self, event_type: EventType, handler_id: str) -> bool:
        """Unsubscribe from an event type"""
        with self.lock:
            handlers = self.handlers[event_type]
            for i, handler in enumerate(handlers):
                if handler.handler_id == handler_id:
                    del handlers[i]
                    logger.info(f"Handler {handler_id} unsubscribed from {event_type.value}")
                    return True
        return False
    
    async def publish(self, event: TradingEvent) -> str:
        """Publish an event"""
        if not self.running:
            await self.start()
        
        with self.lock:
            self.event_history.append(event)
            self.statistics['events_published'] += 1
        
        await self.event_queue.put(event)
        logger.debug(f"Event published: {event.event_type.value} ({event.id})")
        return event.id
    
    async def publish_event(self, event_type: EventType, data: Dict[str, Any], 
                           user_id: str = None, priority: EventPriority = EventPriority.NORMAL,
                           correlation_id: str = None) -> str:
        """Publish an event with parameters"""
        event = TradingEvent(event_type, data, user_id, priority, correlation_id)
        return await self.publish(event)
    
    async def _process_events(self):
        """Process events from the queue"""
        while self.running:
            try:
                # Get event with timeout to allow checking running status
                event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                await self._handle_event(event)
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing events: {e}")
    
    async def _handle_event(self, event: TradingEvent):
        """Handle a single event"""
        handlers = self.handlers.get(event.event_type, [])
        
        if not handlers:
            logger.debug(f"No handlers for event type: {event.event_type.value}")
            return
        
        # Sort handlers by priority (if needed in future)
        success_count = 0
        
        for handler in handlers:
            try:
                success = await handler.handle(event)
                if success:
                    success_count += 1
            except Exception as e:
                logger.error(f"Handler execution failed: {e}")
        
        with self.lock:
            if success_count > 0:
                self.statistics['events_processed'] += 1
            else:
                self.statistics['events_failed'] += 1
    
    def get_event_history(self, user_id: Optional[str] = None, 
                         event_type: Optional[EventType] = None, 
                         limit: int = 100) -> List[TradingEvent]:
        """Get event history with optional filtering"""
        with self.lock:
            events = list(self.event_history)
        
        # Apply filters
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        # Sort by timestamp (newest first) and limit
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        with self.lock:
            uptime = datetime.now() - self.statistics['start_time']
            
            return {
                'running': self.running,
                'events_published': self.statistics['events_published'],
                'events_processed': self.statistics['events_processed'],
                'events_failed': self.statistics['events_failed'],
                'handlers_registered': self.statistics['handlers_registered'],
                'queue_size': self.event_queue.qsize() if self.event_queue else 0,
                'history_size': len(self.event_history),
                'uptime_seconds': int(uptime.total_seconds()),
                'last_updated': datetime.now().isoformat()
            }
    
    def get_handler_stats(self) -> Dict[str, Any]:
        """Get handler statistics"""
        with self.lock:
            handler_stats = {}
            
            for event_type, handlers in self.handlers.items():
                handler_stats[event_type.value] = []
                
                for handler in handlers:
                    handler_stats[event_type.value].append({
                        'handler_id': handler.handler_id,
                        'call_count': handler.call_count,
                        'error_count': handler.error_count,
                        'last_called': handler.last_called.isoformat() if handler.last_called else None,
                        'last_error': handler.last_error,
                        'created_at': handler.created_at.isoformat()
                    })
            
            return handler_stats

# Global event bus instance
simple_event_bus = SimpleEventBus()

def get_event_bus() -> SimpleEventBus:
    """Get the global event bus instance"""
    return simple_event_bus

# Convenience functions for common events
async def publish_signal_event(signal_data: Dict[str, Any], user_id: str = None) -> str:
    """Publish a signal received event"""
    return await simple_event_bus.publish_event(
        EventType.SIGNAL_RECEIVED, signal_data, user_id, EventPriority.HIGH
    )

async def publish_order_event(order_data: Dict[str, Any], event_type: EventType, 
                             user_id: str = None) -> str:
    """Publish an order-related event"""
    priority = EventPriority.HIGH if event_type in [
        EventType.ORDER_EXECUTED, EventType.ORDER_CANCELLED
    ] else EventPriority.NORMAL
    
    return await simple_event_bus.publish_event(event_type, order_data, user_id, priority)

async def publish_risk_alert(alert_data: Dict[str, Any], user_id: str = None) -> str:
    """Publish a risk alert event"""
    return await simple_event_bus.publish_event(
        EventType.RISK_ALERT, alert_data, user_id, EventPriority.CRITICAL
    )

async def publish_system_error(error_data: Dict[str, Any], user_id: str = None) -> str:
    """Publish a system error event"""
    return await simple_event_bus.publish_event(
        EventType.SYSTEM_ERROR, error_data, user_id, EventPriority.CRITICAL
    )