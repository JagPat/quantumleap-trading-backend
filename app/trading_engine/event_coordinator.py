"""
Event Processing Coordinator
Manages event-driven state and coordinates between trading system components
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from collections import defaultdict
import threading

from .simple_event_bus import TradingEvent, EventType, EventPriority, get_event_bus
from .simple_monitoring import get_trading_monitor
from .core_config import get_trading_config

logger = logging.getLogger(__name__)

class TradingState:
    """Manages trading system state"""
    
    def __init__(self):
        self.active_orders: Dict[str, Dict[str, Any]] = {}
        self.active_positions: Dict[str, Dict[str, Any]] = {}
        self.active_strategies: Dict[str, Dict[str, Any]] = {}
        self.user_sessions: Dict[str, Dict[str, Any]] = {}
        self.system_status = "INITIALIZING"
        self.lock = threading.Lock()
    
    def update_order_state(self, order_id: str, order_data: Dict[str, Any]):
        """Update order state"""
        with self.lock:
            self.active_orders[order_id] = {
                **order_data,
                "last_updated": datetime.now().isoformat()
            }
    
    def remove_order(self, order_id: str):
        """Remove order from active state"""
        with self.lock:
            self.active_orders.pop(order_id, None)
    
    def update_position_state(self, position_id: str, position_data: Dict[str, Any]):
        """Update position state"""
        with self.lock:
            self.active_positions[position_id] = {
                **position_data,
                "last_updated": datetime.now().isoformat()
            }
    
    def remove_position(self, position_id: str):
        """Remove position from active state"""
        with self.lock:
            self.active_positions.pop(position_id, None)
    
    def update_strategy_state(self, strategy_id: str, strategy_data: Dict[str, Any]):
        """Update strategy state"""
        with self.lock:
            self.active_strategies[strategy_id] = {
                **strategy_data,
                "last_updated": datetime.now().isoformat()
            }
    
    def remove_strategy(self, strategy_id: str):
        """Remove strategy from active state"""
        with self.lock:
            self.active_strategies.pop(strategy_id, None)
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get current state summary"""
        with self.lock:
            return {
                "system_status": self.system_status,
                "active_orders_count": len(self.active_orders),
                "active_positions_count": len(self.active_positions),
                "active_strategies_count": len(self.active_strategies),
                "active_users_count": len(self.user_sessions),
                "last_updated": datetime.now().isoformat()
            }

class EventCoordinator:
    """Coordinates event processing and manages system state"""
    
    def __init__(self):
        self.event_bus = get_event_bus()
        self.monitor = get_trading_monitor()
        self.config = get_trading_config()
        self.state = TradingState()
        self.processing_queues: Dict[str, asyncio.Queue] = {}
        self.worker_tasks: Dict[str, asyncio.Task] = {}
        self.coordination_rules: Dict[EventType, List[Callable]] = defaultdict(list)
        self.running = False
        
        # Event correlation tracking
        self.event_correlations: Dict[str, List[str]] = defaultdict(list)
        self.workflow_states: Dict[str, Dict[str, Any]] = {}
    
    async def start(self):
        """Start the event coordinator"""
        if self.running:
            return
        
        try:
            # Create processing queues for different event types
            self.processing_queues = {
                "high_priority": asyncio.Queue(),
                "order_processing": asyncio.Queue(),
                "position_management": asyncio.Queue(),
                "risk_monitoring": asyncio.Queue(),
                "market_data": asyncio.Queue(),
                "system_events": asyncio.Queue()
            }
            
            # Start worker tasks
            self.worker_tasks = {
                "high_priority": asyncio.create_task(self._process_high_priority_events()),
                "order_processing": asyncio.create_task(self._process_order_events()),
                "position_management": asyncio.create_task(self._process_position_events()),
                "risk_monitoring": asyncio.create_task(self._process_risk_events()),
                "market_data": asyncio.create_task(self._process_market_data_events()),
                "system_events": asyncio.create_task(self._process_system_events())
            }
            
            # Register coordination handlers
            await self._register_coordination_handlers()
            
            self.running = True
            self.state.system_status = "RUNNING"
            
            logger.info("Event coordinator started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start event coordinator: {e}")
            raise
    
    async def stop(self):
        """Stop the event coordinator"""
        if not self.running:
            return
        
        try:
            self.running = False
            self.state.system_status = "STOPPING"
            
            # Cancel all worker tasks
            for task_name, task in self.worker_tasks.items():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                logger.info(f"Worker task {task_name} stopped")
            
            self.state.system_status = "STOPPED"
            logger.info("Event coordinator stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping event coordinator: {e}")
    
    async def _register_coordination_handlers(self):
        """Register event coordination handlers"""
        try:
            # Register handlers for state management
            self.event_bus.subscribe(
                EventType.ORDER_CREATED,
                self._coordinate_order_created,
                "order_coordinator",
                async_handler=True
            )
            
            self.event_bus.subscribe(
                EventType.ORDER_EXECUTED,
                self._coordinate_order_executed,
                "order_execution_coordinator",
                async_handler=True
            )
            
            self.event_bus.subscribe(
                EventType.ORDER_CANCELLED,
                self._coordinate_order_cancelled,
                "order_cancellation_coordinator",
                async_handler=True
            )
            
            self.event_bus.subscribe(
                EventType.POSITION_OPENED,
                self._coordinate_position_opened,
                "position_coordinator",
                async_handler=True
            )
            
            self.event_bus.subscribe(
                EventType.POSITION_CLOSED,
                self._coordinate_position_closed,
                "position_close_coordinator",
                async_handler=True
            )
            
            self.event_bus.subscribe(
                EventType.RISK_ALERT,
                self._coordinate_risk_alert,
                "risk_coordinator",
                async_handler=True
            )
            
            logger.info("Event coordination handlers registered")
            
        except Exception as e:
            logger.error(f"Failed to register coordination handlers: {e}")
            raise
    
    async def _coordinate_order_created(self, event: TradingEvent):
        """Coordinate order creation workflow"""
        try:
            order_data = event.data
            order_id = event.id
            
            # Update state
            self.state.update_order_state(order_id, {
                **order_data,
                "status": "CREATED",
                "created_at": event.timestamp.isoformat()
            })
            
            # Track correlation
            correlation_id = event.correlation_id
            self.event_correlations[correlation_id].append(event.id)
            
            # Initialize workflow state
            self.workflow_states[correlation_id] = {
                "workflow_type": "ORDER_PROCESSING",
                "current_stage": "CREATED",
                "order_id": order_id,
                "started_at": datetime.now().isoformat(),
                "events": [event.id]
            }
            
            # Route to appropriate processing queue
            await self.processing_queues["order_processing"].put(event)
            
            logger.info(f"Order creation coordinated: {order_id}")
            
        except Exception as e:
            logger.error(f"Error coordinating order creation: {e}")
    
    async def _coordinate_order_executed(self, event: TradingEvent):
        """Coordinate order execution workflow"""
        try:
            order_data = event.data
            order_id = order_data.get('order_id')
            
            # Update state
            self.state.update_order_state(order_id, {
                **order_data,
                "status": "EXECUTED",
                "executed_at": event.timestamp.isoformat()
            })
            
            # Update workflow state
            correlation_id = event.correlation_id
            if correlation_id in self.workflow_states:
                self.workflow_states[correlation_id].update({
                    "current_stage": "EXECUTED",
                    "executed_at": datetime.now().isoformat()
                })
                self.workflow_states[correlation_id]["events"].append(event.id)
            
            # Remove from active orders (now it's a position)
            self.state.remove_order(order_id)
            
            # Route to position management
            await self.processing_queues["position_management"].put(event)
            
            logger.info(f"Order execution coordinated: {order_id}")
            
        except Exception as e:
            logger.error(f"Error coordinating order execution: {e}")
    
    async def _coordinate_order_cancelled(self, event: TradingEvent):
        """Coordinate order cancellation workflow"""
        try:
            order_data = event.data
            order_id = order_data.get('order_id')
            
            # Update workflow state
            correlation_id = event.correlation_id
            if correlation_id in self.workflow_states:
                self.workflow_states[correlation_id].update({
                    "current_stage": "CANCELLED",
                    "cancelled_at": datetime.now().isoformat(),
                    "cancellation_reason": order_data.get('cancellation_reason')
                })
                self.workflow_states[correlation_id]["events"].append(event.id)
            
            # Remove from active orders
            self.state.remove_order(order_id)
            
            logger.info(f"Order cancellation coordinated: {order_id}")
            
        except Exception as e:
            logger.error(f"Error coordinating order cancellation: {e}")
    
    async def _coordinate_position_opened(self, event: TradingEvent):
        """Coordinate position opening workflow"""
        try:
            position_data = event.data
            position_id = f"{position_data.get('symbol')}_{event.user_id}_{int(datetime.now().timestamp())}"
            
            # Update state
            self.state.update_position_state(position_id, {
                **position_data,
                "position_id": position_id,
                "status": "OPEN"
            })
            
            # Start risk monitoring for this position
            risk_monitoring_data = {
                "position_id": position_id,
                "symbol": position_data.get('symbol'),
                "position_size": position_data.get('position_size'),
                "entry_price": position_data.get('entry_price'),
                "monitoring_started": datetime.now().isoformat()
            }
            
            await self.event_bus.publish_event(
                EventType.RISK_ALERT,
                {
                    "alert_type": "POSITION_MONITORING_STARTED",
                    **risk_monitoring_data
                },
                event.user_id,
                EventPriority.NORMAL
            )
            
            logger.info(f"Position opening coordinated: {position_id}")
            
        except Exception as e:
            logger.error(f"Error coordinating position opening: {e}")
    
    async def _coordinate_position_closed(self, event: TradingEvent):
        """Coordinate position closing workflow"""
        try:
            position_data = event.data
            position_id = position_data.get('position_id')
            
            # Remove from active positions
            if position_id:
                self.state.remove_position(position_id)
            
            # Record performance metrics
            pnl = position_data.get('pnl', 0)
            if pnl > 0:
                self.monitor.record_metric("profitable_positions", 1)
            else:
                self.monitor.record_metric("losing_positions", 1)
            
            logger.info(f"Position closing coordinated: {position_id}")
            
        except Exception as e:
            logger.error(f"Error coordinating position closing: {e}")
    
    async def _coordinate_risk_alert(self, event: TradingEvent):
        """Coordinate risk alert workflow"""
        try:
            alert_data = event.data
            alert_type = alert_data.get('alert_type')
            
            # Route to high priority queue for immediate processing
            await self.processing_queues["high_priority"].put(event)
            
            # If critical risk alert, trigger emergency procedures
            if alert_type in ['MARGIN_CALL', 'POSITION_LIMIT_EXCEEDED', 'PORTFOLIO_RISK_HIGH']:
                await self._trigger_emergency_procedures(event)
            
            logger.warning(f"Risk alert coordinated: {alert_type}")
            
        except Exception as e:
            logger.error(f"Error coordinating risk alert: {e}")
    
    async def _trigger_emergency_procedures(self, event: TradingEvent):
        """Trigger emergency risk management procedures"""
        try:
            alert_data = event.data
            
            # Create emergency alert
            emergency_alert_id = self.monitor.create_alert(
                level="CRITICAL",
                title="Emergency Risk Procedure Triggered",
                message=f"Emergency procedures activated due to: {alert_data.get('alert_type')}",
                component="risk_coordinator",
                user_id=event.user_id,
                data=alert_data
            )
            
            # Publish emergency system event
            await self.event_bus.publish_event(
                EventType.SYSTEM_ERROR,
                {
                    "error_type": "EMERGENCY_RISK_PROCEDURE",
                    "trigger_event": event.id,
                    "alert_id": emergency_alert_id,
                    "procedures_activated": ["POSITION_REVIEW", "ORDER_HALT", "RISK_ASSESSMENT"]
                },
                event.user_id,
                EventPriority.CRITICAL
            )
            
            logger.critical(f"Emergency procedures triggered for user {event.user_id}")
            
        except Exception as e:
            logger.error(f"Error triggering emergency procedures: {e}")
    
    async def _process_high_priority_events(self):
        """Process high priority events"""
        while self.running:
            try:
                event = await asyncio.wait_for(
                    self.processing_queues["high_priority"].get(), 
                    timeout=1.0
                )
                
                # Process immediately
                await self._handle_high_priority_event(event)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing high priority events: {e}")
    
    async def _process_order_events(self):
        """Process order-related events"""
        while self.running:
            try:
                event = await asyncio.wait_for(
                    self.processing_queues["order_processing"].get(),
                    timeout=1.0
                )
                
                await self._handle_order_event(event)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing order events: {e}")
    
    async def _process_position_events(self):
        """Process position-related events"""
        while self.running:
            try:
                event = await asyncio.wait_for(
                    self.processing_queues["position_management"].get(),
                    timeout=1.0
                )
                
                await self._handle_position_event(event)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing position events: {e}")
    
    async def _process_risk_events(self):
        """Process risk-related events"""
        while self.running:
            try:
                event = await asyncio.wait_for(
                    self.processing_queues["risk_monitoring"].get(),
                    timeout=1.0
                )
                
                await self._handle_risk_event(event)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing risk events: {e}")
    
    async def _process_market_data_events(self):
        """Process market data events"""
        while self.running:
            try:
                event = await asyncio.wait_for(
                    self.processing_queues["market_data"].get(),
                    timeout=1.0
                )
                
                await self._handle_market_data_event(event)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing market data events: {e}")
    
    async def _process_system_events(self):
        """Process system events"""
        while self.running:
            try:
                event = await asyncio.wait_for(
                    self.processing_queues["system_events"].get(),
                    timeout=1.0
                )
                
                await self._handle_system_event(event)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing system events: {e}")
    
    async def _handle_high_priority_event(self, event: TradingEvent):
        """Handle high priority event"""
        logger.info(f"Processing high priority event: {event.event_type.value}")
        # Immediate processing logic here
    
    async def _handle_order_event(self, event: TradingEvent):
        """Handle order event"""
        logger.debug(f"Processing order event: {event.event_type.value}")
        # Order processing logic here
    
    async def _handle_position_event(self, event: TradingEvent):
        """Handle position event"""
        logger.debug(f"Processing position event: {event.event_type.value}")
        # Position management logic here
    
    async def _handle_risk_event(self, event: TradingEvent):
        """Handle risk event"""
        logger.info(f"Processing risk event: {event.event_type.value}")
        # Risk management logic here
    
    async def _handle_market_data_event(self, event: TradingEvent):
        """Handle market data event"""
        logger.debug(f"Processing market data event: {event.event_type.value}")
        # Market data processing logic here
    
    async def _handle_system_event(self, event: TradingEvent):
        """Handle system event"""
        logger.info(f"Processing system event: {event.event_type.value}")
        # System event processing logic here
    
    def get_coordination_status(self) -> Dict[str, Any]:
        """Get event coordination status"""
        queue_sizes = {
            name: queue.qsize() 
            for name, queue in self.processing_queues.items()
        }
        
        return {
            "running": self.running,
            "system_status": self.state.system_status,
            "queue_sizes": queue_sizes,
            "active_workflows": len(self.workflow_states),
            "state_summary": self.state.get_state_summary(),
            "worker_tasks": {
                name: not task.done() 
                for name, task in self.worker_tasks.items()
            }
        }

# Global event coordinator instance
event_coordinator = EventCoordinator()

async def initialize_event_coordinator():
    """Initialize the event coordinator"""
    try:
        await event_coordinator.start()
        logger.info("Event coordinator initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize event coordinator: {e}")
        raise

def get_event_coordinator() -> EventCoordinator:
    """Get the global event coordinator instance"""
    return event_coordinator