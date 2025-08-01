"""
Monitoring and Logging System for Automatic Trading Engine
"""
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import threading
import sqlite3
from app.core.config import settings

# Configure trading-specific logger
trading_logger = logging.getLogger("trading_engine")
trading_logger.setLevel(logging.INFO)

# Create file handler for trading logs with error handling
try:
    import os
    os.makedirs("logs", exist_ok=True)
    trading_handler = logging.FileHandler("logs/trading_engine.log")
    trading_handler.setLevel(logging.INFO)
except Exception as e:
    # Fallback to console logging if file logging fails
    trading_handler = logging.StreamHandler()
    trading_handler.setLevel(logging.INFO)
    print(f"Warning: Could not create log file, using console logging: {e}")

# Create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
trading_handler.setFormatter(formatter)
trading_logger.addHandler(trading_handler)

@dataclass
class PerformanceMetric:
    """Performance metric data structure"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}

@dataclass
class SystemAlert:
    """System alert data structure"""
    id: str
    level: str  # INFO, WARNING, ERROR, CRITICAL
    title: str
    message: str
    component: str
    user_id: Optional[str] = None
    data: Dict[str, Any] = None
    created_at: datetime = None
    resolved_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.data is None:
            self.data = {}

class TradingMonitor:
    """
    Comprehensive monitoring system for the trading engine
    """
    
    def __init__(self):
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.alerts: List[SystemAlert] = []
        self.performance_counters: Dict[str, int] = defaultdict(int)
        self.timing_data: Dict[str, List[float]] = defaultdict(list)
        self.system_health: Dict[str, Any] = {}
        self.lock = threading.Lock()
        
        # Start background monitoring
        self._start_background_monitoring()
    
    def record_metric(self, name: str, value: float, unit: str = "", tags: Dict[str, str] = None):
        """Record a performance metric"""
        with self.lock:
            metric = PerformanceMetric(
                name=name,
                value=value,
                unit=unit,
                timestamp=datetime.now(),
                tags=tags or {}
            )
            self.metrics[name].append(metric)
            trading_logger.debug(f"Recorded metric {name}: {value} {unit}")
    
    def increment_counter(self, counter_name: str, increment: int = 1):
        """Increment a performance counter"""
        with self.lock:
            self.performance_counters[counter_name] += increment
            trading_logger.debug(f"Incremented counter {counter_name} by {increment}")
    
    def record_timing(self, operation: str, duration_ms: float):
        """Record operation timing"""
        with self.lock:
            self.timing_data[operation].append(duration_ms)
            # Keep only last 100 timings per operation
            if len(self.timing_data[operation]) > 100:
                self.timing_data[operation].pop(0)
            
            # Record as metric too
            self.record_metric(f"{operation}_duration", duration_ms, "ms")
    
    def create_alert(self, level: str, title: str, message: str, component: str, 
                    user_id: str = None, data: Dict[str, Any] = None) -> SystemAlert:
        """Create a system alert"""
        alert = SystemAlert(
            id=f"alert_{int(time.time() * 1000)}",
            level=level,
            title=title,
            message=message,
            component=component,
            user_id=user_id,
            data=data or {}
        )
        
        with self.lock:
            self.alerts.append(alert)
            # Keep only last 1000 alerts
            if len(self.alerts) > 1000:
                self.alerts.pop(0)
        
        # Log alert
        log_level = getattr(logging, level.upper(), logging.INFO)
        trading_logger.log(log_level, f"ALERT [{component}] {title}: {message}")
        
        # Store in database
        self._store_alert_in_db(alert)
        
        return alert
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        with self.lock:
            for alert in self.alerts:
                if alert.id == alert_id and alert.resolved_at is None:
                    alert.resolved_at = datetime.now()
                    trading_logger.info(f"Resolved alert {alert_id}")
                    return True
        return False
    
    def get_metrics_summary(self, metric_name: str = None, 
                           time_window_minutes: int = 60) -> Dict[str, Any]:
        """Get metrics summary"""
        cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
        
        with self.lock:
            if metric_name:
                metrics = [m for m in self.metrics[metric_name] if m.timestamp >= cutoff_time]
                if not metrics:
                    return {"metric": metric_name, "count": 0}
                
                values = [m.value for m in metrics]
                return {
                    "metric": metric_name,
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "latest": values[-1] if values else 0,
                    "time_window_minutes": time_window_minutes
                }
            else:
                # Summary of all metrics
                summary = {}
                for name, metric_list in self.metrics.items():
                    recent_metrics = [m for m in metric_list if m.timestamp >= cutoff_time]
                    if recent_metrics:
                        values = [m.value for m in recent_metrics]
                        summary[name] = {
                            "count": len(values),
                            "latest": values[-1],
                            "avg": sum(values) / len(values)
                        }
                return summary
    
    def get_timing_summary(self, operation: str = None) -> Dict[str, Any]:
        """Get timing summary"""
        with self.lock:
            if operation:
                timings = self.timing_data.get(operation, [])
                if not timings:
                    return {"operation": operation, "count": 0}
                
                return {
                    "operation": operation,
                    "count": len(timings),
                    "min_ms": min(timings),
                    "max_ms": max(timings),
                    "avg_ms": sum(timings) / len(timings),
                    "p95_ms": sorted(timings)[int(len(timings) * 0.95)] if len(timings) > 20 else max(timings)
                }
            else:
                # Summary of all operations
                summary = {}
                for op, timings in self.timing_data.items():
                    if timings:
                        summary[op] = {
                            "count": len(timings),
                            "avg_ms": sum(timings) / len(timings),
                            "latest_ms": timings[-1]
                        }
                return summary
    
    def get_active_alerts(self, level: str = None, component: str = None) -> List[SystemAlert]:
        """Get active (unresolved) alerts"""
        with self.lock:
            alerts = [a for a in self.alerts if a.resolved_at is None]
            
            if level:
                alerts = [a for a in alerts if a.level == level]
            
            if component:
                alerts = [a for a in alerts if a.component == component]
            
            return sorted(alerts, key=lambda x: x.created_at, reverse=True)
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        with self.lock:
            # Count alerts by level
            active_alerts = [a for a in self.alerts if a.resolved_at is None]
            alert_counts = defaultdict(int)
            for alert in active_alerts:
                alert_counts[alert.level] += 1
            
            # Calculate health score (0-100)
            health_score = 100
            health_score -= alert_counts.get("CRITICAL", 0) * 30
            health_score -= alert_counts.get("ERROR", 0) * 10
            health_score -= alert_counts.get("WARNING", 0) * 5
            health_score = max(0, health_score)
            
            # Determine overall status
            if health_score >= 90:
                status = "HEALTHY"
            elif health_score >= 70:
                status = "WARNING"
            elif health_score >= 50:
                status = "DEGRADED"
            else:
                status = "CRITICAL"
            
            return {
                "status": status,
                "health_score": health_score,
                "alert_counts": dict(alert_counts),
                "total_active_alerts": len(active_alerts),
                "performance_counters": dict(self.performance_counters),
                "last_updated": datetime.now().isoformat()
            }
    
    def _store_alert_in_db(self, alert: SystemAlert):
        """Store alert in database"""
        try:
            conn = sqlite3.connect(settings.database_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO trading_events (id, user_id, event_type, event_data, severity, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                alert.id,
                alert.user_id or "system",
                "SYSTEM_ALERT",
                json.dumps({
                    "title": alert.title,
                    "message": alert.message,
                    "component": alert.component,
                    "data": alert.data
                }),
                alert.level,
                alert.created_at.isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            trading_logger.error(f"Failed to store alert in database: {e}")
    
    def _start_background_monitoring(self):
        """Start background monitoring tasks"""
        def monitor_system_resources():
            """Monitor system resources periodically"""
            import psutil
            import threading
            
            def resource_monitor():
                while True:
                    try:
                        # CPU usage
                        cpu_percent = psutil.cpu_percent(interval=1)
                        self.record_metric("system_cpu_percent", cpu_percent, "%")
                        
                        # Memory usage
                        memory = psutil.virtual_memory()
                        self.record_metric("system_memory_percent", memory.percent, "%")
                        self.record_metric("system_memory_used_mb", memory.used / 1024 / 1024, "MB")
                        
                        # Disk usage
                        disk = psutil.disk_usage('/')
                        self.record_metric("system_disk_percent", disk.percent, "%")
                        
                        # Create alerts for high resource usage
                        if cpu_percent > 90:
                            self.create_alert("WARNING", "High CPU Usage", 
                                            f"CPU usage is {cpu_percent}%", "system")
                        
                        if memory.percent > 90:
                            self.create_alert("WARNING", "High Memory Usage", 
                                            f"Memory usage is {memory.percent}%", "system")
                        
                        if disk.percent > 90:
                            self.create_alert("WARNING", "High Disk Usage", 
                                            f"Disk usage is {disk.percent}%", "system")
                        
                        time.sleep(60)  # Check every minute
                        
                    except Exception as e:
                        trading_logger.error(f"Error in resource monitoring: {e}")
                        time.sleep(60)
            
            # Start in background thread
            monitor_thread = threading.Thread(target=resource_monitor, daemon=True)
            monitor_thread.start()
        
        try:
            monitor_system_resources()
        except ImportError:
            trading_logger.warning("psutil not available, system resource monitoring disabled")

# Global monitor instance
trading_monitor = TradingMonitor()

# Timing decorator
def time_operation(operation_name: str):
    """Decorator to time operations"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                trading_monitor.record_timing(operation_name, duration_ms)
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                trading_monitor.record_timing(f"{operation_name}_error", duration_ms)
                raise
        return wrapper
    return decorator

# Async timing decorator
def time_async_operation(operation_name: str):
    """Decorator to time async operations"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                trading_monitor.record_timing(operation_name, duration_ms)
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                trading_monitor.record_timing(f"{operation_name}_error", duration_ms)
                raise
        return wrapper
    return decorator

# Convenience functions
def log_trade_execution(user_id: str, symbol: str, side: str, quantity: int, price: float):
    """Log trade execution"""
    trading_logger.info(f"TRADE_EXECUTED - User: {user_id}, Symbol: {symbol}, "
                       f"Side: {side}, Quantity: {quantity}, Price: {price}")
    trading_monitor.increment_counter("trades_executed")
    trading_monitor.record_metric("trade_value", quantity * price, "INR", 
                                 {"user_id": user_id, "symbol": symbol})

def log_order_placement(user_id: str, order_id: str, symbol: str, order_type: str):
    """Log order placement"""
    trading_logger.info(f"ORDER_PLACED - User: {user_id}, Order: {order_id}, "
                       f"Symbol: {symbol}, Type: {order_type}")
    trading_monitor.increment_counter("orders_placed")

def log_risk_violation(user_id: str, violation_type: str, details: str):
    """Log risk violation"""
    trading_logger.warning(f"RISK_VIOLATION - User: {user_id}, Type: {violation_type}, "
                          f"Details: {details}")
    trading_monitor.increment_counter("risk_violations")
    trading_monitor.create_alert("WARNING", "Risk Violation", details, "risk_engine", user_id)

def log_strategy_deployment(user_id: str, strategy_id: str, strategy_name: str):
    """Log strategy deployment"""
    trading_logger.info(f"STRATEGY_DEPLOYED - User: {user_id}, Strategy: {strategy_id}, "
                       f"Name: {strategy_name}")
    trading_monitor.increment_counter("strategies_deployed")

def log_emergency_stop(user_id: str, reason: str):
    """Log emergency stop"""
    trading_logger.critical(f"EMERGENCY_STOP - User: {user_id}, Reason: {reason}")
    trading_monitor.increment_counter("emergency_stops")
    trading_monitor.create_alert("CRITICAL", "Emergency Stop Triggered", reason, 
                                "emergency_system", user_id)