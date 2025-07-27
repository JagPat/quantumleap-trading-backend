"""
Trading Engine Event Handlers
Comprehensive event handling for trading system events
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import asyncio

from .simple_event_bus import TradingEvent, EventType, get_event_bus
from .simple_monitoring import get_trading_monitor

logger = logging.getLogger(__name__)

class TradingEventHandlers:
    """Collection of event handlers for the trading system"""
    
    def __init__(self):
        self.monitor = get_trading_monitor()
        self.event_bus = get_event_bus()
        self.handlers_registered = False
    
    async def register_all_handlers(self):
        """Register all event handlers with the event bus"""
        if self.handlers_registered:
            return
        
        try:
            # Signal processing handlers
            self.event_bus.subscribe(
                EventType.SIGNAL_RECEIVED, 
                self.handle_signal_received, 
                "signal_processor",
                async_handler=True
            )
            
            # Order management handlers
            self.event_bus.subscribe(
                EventType.ORDER_CREATED,
                self.handle_order_created,
                "order_tracker",
                async_handler=True
            )
            
            self.event_bus.subscribe(
                EventType.ORDER_EXECUTED,
                self.handle_order_executed,
                "order_executor_handler",
                async_handler=True
            )
            
            self.event_bus.subscribe(
                EventType.ORDER_CANCELLED,
                self.handle_order_cancelled,
                "order_cancellation_handler",
                async_handler=True
            )
            
            # Position management handlers
            self.event_bus.subscribe(
                EventType.POSITION_OPENED,
                self.handle_position_opened,
                "position_tracker",
                async_handler=True
            )
            
            self.event_bus.subscribe(
                EventType.POSITION_CLOSED,
                self.handle_position_closed,
                "position_closer",
                async_handler=True
            )
            
            # Risk management handlers
            self.event_bus.subscribe(
                EventType.RISK_ALERT,
                self.handle_risk_alert,
                "risk_manager",
                async_handler=True
            )
            
            # Market data handlers
            self.event_bus.subscribe(
                EventType.MARKET_DATA_UPDATE,
                self.handle_market_data_update,
                "market_data_processor",
                async_handler=True
            )
            
            # Strategy management handlers
            self.event_bus.subscribe(
                EventType.STRATEGY_STARTED,
                self.handle_strategy_started,
                "strategy_lifecycle",
                async_handler=True
            )
            
            self.event_bus.subscribe(
                EventType.STRATEGY_STOPPED,
                self.handle_strategy_stopped,
                "strategy_lifecycle",
                async_handler=True
            )
            
            # System handlers
            self.event_bus.subscribe(
                EventType.SYSTEM_ERROR,
                self.handle_system_error,
                "system_error_handler",
                async_handler=True
            )
            
            self.event_bus.subscribe(
                EventType.HEALTH_CHECK,
                self.handle_health_check,
                "health_monitor",
                async_handler=True
            )
            
            self.handlers_registered = True
            logger.info("All trading event handlers registered successfully")
            
        except Exception as e:
            logger.error(f"Failed to register event handlers: {e}")
            raise
    
    async def handle_signal_received(self, event: TradingEvent):
        """Handle signal received events"""
        try:
            signal_data = event.data
            symbol = signal_data.get('symbol')
            signal_type = signal_data.get('signal_type')
            confidence = signal_data.get('confidence_score', 0)
            
            logger.info(f"Processing signal: {signal_type} for {symbol} (confidence: {confidence})")
            
            # Record metrics
            self.monitor.record_metric("signals_processed", 1)
            self.monitor.record_metric(f"signals_{signal_type.lower()}", 1)
            
            # Validate signal
            if confidence < 0.6:
                logger.warning(f"Low confidence signal ignored: {confidence}")
                self.monitor.record_metric("signals_low_confidence", 1)
                return
            
            # Create order event based on signal
            order_data = {
                "symbol": symbol,
                "signal_id": event.id,
                "signal_type": signal_type,
                "confidence_score": confidence,
                "target_price": signal_data.get('target_price'),
                "stop_loss": signal_data.get('stop_loss'),
                "position_size": signal_data.get('position_size'),
                "strategy_id": signal_data.get('strategy_id'),
                "created_from": "signal_processing",
                "timestamp": datetime.now().isoformat()
            }
            
            # Publish order creation event
            await self.event_bus.publish_event(
                EventType.ORDER_CREATED,
                order_data,
                event.user_id
            )
            
            logger.info(f"Order creation event published for signal {event.id}")
            
        except Exception as e:
            logger.error(f"Error handling signal received event: {e}")
            self.monitor.record_metric("signal_processing_errors", 1)
    
    async def handle_order_created(self, event: TradingEvent):
        """Handle order created events"""
        try:
            order_data = event.data
            symbol = order_data.get('symbol')
            order_id = event.id
            
            logger.info(f"Order created: {order_id} for {symbol}")
            
            # Record metrics
            self.monitor.record_metric("orders_created", 1)
            self.monitor.record_timing("order_creation", 100)  # Mock timing
            
            # Simulate order validation and execution
            await asyncio.sleep(0.1)  # Simulate processing time
            
            # For demo purposes, assume 90% success rate
            import random
            if random.random() < 0.9:
                # Publish order executed event
                execution_data = {
                    **order_data,
                    "order_id": order_id,
                    "executed_price": order_data.get('target_price', 100.0),
                    "executed_quantity": order_data.get('position_size', 10),
                    "execution_time": datetime.now().isoformat(),
                    "broker_order_id": f"BRK_{order_id[:8]}"
                }
                
                await self.event_bus.publish_event(
                    EventType.ORDER_EXECUTED,
                    execution_data,
                    event.user_id
                )
            else:
                # Publish order cancelled event
                cancellation_data = {
                    **order_data,
                    "order_id": order_id,
                    "cancellation_reason": "Risk check failed",
                    "cancelled_at": datetime.now().isoformat()
                }
                
                await self.event_bus.publish_event(
                    EventType.ORDER_CANCELLED,
                    cancellation_data,
                    event.user_id
                )
            
        except Exception as e:
            logger.error(f"Error handling order created event: {e}")
            self.monitor.record_metric("order_processing_errors", 1)
    
    async def handle_order_executed(self, event: TradingEvent):
        """Handle order executed events"""
        try:
            order_data = event.data
            symbol = order_data.get('symbol')
            order_id = order_data.get('order_id')
            
            logger.info(f"Order executed: {order_id} for {symbol}")
            
            # Record metrics
            self.monitor.record_metric("orders_executed", 1)
            self.monitor.record_metric("orders_processed", 1)
            
            # Create position opened event
            position_data = {
                "symbol": symbol,
                "order_id": order_id,
                "position_size": order_data.get('executed_quantity'),
                "entry_price": order_data.get('executed_price'),
                "position_type": "LONG",  # Simplified
                "opened_at": datetime.now().isoformat(),
                "strategy_id": order_data.get('strategy_id')
            }
            
            await self.event_bus.publish_event(
                EventType.POSITION_OPENED,
                position_data,
                event.user_id
            )
            
        except Exception as e:
            logger.error(f"Error handling order executed event: {e}")
            self.monitor.record_metric("order_execution_errors", 1)
    
    async def handle_order_cancelled(self, event: TradingEvent):
        """Handle order cancelled events"""
        try:
            order_data = event.data
            order_id = order_data.get('order_id')
            reason = order_data.get('cancellation_reason', 'Unknown')
            
            logger.info(f"Order cancelled: {order_id}, reason: {reason}")
            
            # Record metrics
            self.monitor.record_metric("orders_cancelled", 1)
            self.monitor.record_metric("orders_processed", 1)
            
            # Create alert if cancellation was due to risk
            if "risk" in reason.lower():
                alert_data = {
                    "alert_type": "ORDER_RISK_CANCELLATION",
                    "order_id": order_id,
                    "reason": reason,
                    "symbol": order_data.get('symbol'),
                    "timestamp": datetime.now().isoformat()
                }
                
                await self.event_bus.publish_event(
                    EventType.RISK_ALERT,
                    alert_data,
                    event.user_id
                )
            
        except Exception as e:
            logger.error(f"Error handling order cancelled event: {e}")
    
    async def handle_position_opened(self, event: TradingEvent):
        """Handle position opened events"""
        try:
            position_data = event.data
            symbol = position_data.get('symbol')
            position_size = position_data.get('position_size')
            
            logger.info(f"Position opened: {symbol}, size: {position_size}")
            
            # Record metrics
            self.monitor.record_metric("positions_opened", 1)
            self.monitor.record_metric("active_positions", 1)
            
            # Monitor position for risk
            # This would typically trigger risk monitoring
            
        except Exception as e:
            logger.error(f"Error handling position opened event: {e}")
    
    async def handle_position_closed(self, event: TradingEvent):
        """Handle position closed events"""
        try:
            position_data = event.data
            symbol = position_data.get('symbol')
            pnl = position_data.get('pnl', 0)
            
            logger.info(f"Position closed: {symbol}, PnL: {pnl}")
            
            # Record metrics
            self.monitor.record_metric("positions_closed", 1)
            self.monitor.record_metric("active_positions", -1)
            
            if pnl > 0:
                self.monitor.record_metric("profitable_trades", 1)
            else:
                self.monitor.record_metric("losing_trades", 1)
            
        except Exception as e:
            logger.error(f"Error handling position closed event: {e}")
    
    async def handle_risk_alert(self, event: TradingEvent):
        """Handle risk alert events"""
        try:
            alert_data = event.data
            alert_type = alert_data.get('alert_type')
            
            logger.warning(f"Risk alert: {alert_type}")
            
            # Create monitoring alert
            alert_id = self.monitor.create_alert(
                level="WARNING",
                title=f"Risk Alert: {alert_type}",
                message=alert_data.get('reason', 'Risk threshold exceeded'),
                component="risk_engine",
                user_id=event.user_id,
                data=alert_data
            )
            
            # Record metrics
            self.monitor.record_metric("risk_alerts", 1)
            
            logger.info(f"Risk alert created: {alert_id}")
            
        except Exception as e:
            logger.error(f"Error handling risk alert event: {e}")
    
    async def handle_market_data_update(self, event: TradingEvent):
        """Handle market data update events"""
        try:
            market_data = event.data
            symbol = market_data.get('symbol')
            price = market_data.get('price')
            
            logger.debug(f"Market data update: {symbol} @ {price}")
            
            # Record metrics
            self.monitor.record_metric("market_data_updates", 1)
            
            # This would typically trigger strategy evaluations
            
        except Exception as e:
            logger.error(f"Error handling market data update event: {e}")
    
    async def handle_strategy_started(self, event: TradingEvent):
        """Handle strategy started events"""
        try:
            strategy_data = event.data
            strategy_id = strategy_data.get('strategy_id')
            
            logger.info(f"Strategy started: {strategy_id}")
            
            # Record metrics
            self.monitor.record_metric("strategies_started", 1)
            self.monitor.record_metric("active_strategies", 1)
            
        except Exception as e:
            logger.error(f"Error handling strategy started event: {e}")
    
    async def handle_strategy_stopped(self, event: TradingEvent):
        """Handle strategy stopped events"""
        try:
            strategy_data = event.data
            strategy_id = strategy_data.get('strategy_id')
            
            logger.info(f"Strategy stopped: {strategy_id}")
            
            # Record metrics
            self.monitor.record_metric("strategies_stopped", 1)
            self.monitor.record_metric("active_strategies", -1)
            
        except Exception as e:
            logger.error(f"Error handling strategy stopped event: {e}")
    
    async def handle_system_error(self, event: TradingEvent):
        """Handle system error events"""
        try:
            error_data = event.data
            error_type = error_data.get('error_type', 'UNKNOWN')
            
            logger.error(f"System error: {error_type}")
            
            # Create critical alert
            alert_id = self.monitor.create_alert(
                level="CRITICAL",
                title=f"System Error: {error_type}",
                message=error_data.get('message', 'System error occurred'),
                component="system",
                user_id=event.user_id,
                data=error_data
            )
            
            # Record metrics
            self.monitor.record_metric("system_errors", 1)
            
        except Exception as e:
            logger.error(f"Error handling system error event: {e}")
    
    async def handle_health_check(self, event: TradingEvent):
        """Handle health check events"""
        try:
            health_data = event.data
            component = health_data.get('component', 'system')
            
            logger.debug(f"Health check: {component}")
            
            # Record metrics
            self.monitor.record_metric("health_checks", 1)
            
        except Exception as e:
            logger.error(f"Error handling health check event: {e}")

# Global event handlers instance
trading_event_handlers = TradingEventHandlers()

async def initialize_event_handlers():
    """Initialize and register all event handlers"""
    try:
        await trading_event_handlers.register_all_handlers()
        logger.info("Trading event handlers initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize event handlers: {e}")
        raise

def get_event_handlers() -> TradingEventHandlers:
    """Get the global event handlers instance"""
    return trading_event_handlers