"""
Simple Trading Engine Monitoring
Basic monitoring without external dependencies
"""
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque
import threading

logger = logging.getLogger(__name__)

class SimpleAlert:
    """Simple alert class"""
    def __init__(self, alert_id: str, level: str, title: str, message: str, 
                 component: str, user_id: str = None, data: Dict = None):
        self.id = alert_id
        self.level = level
        self.title = title
        self.message = message
        self.component = component
        self.user_id = user_id
        self.data = data or {}
        self.created_at = datetime.now()
        self.resolved_at = None

class SimpleTradingMonitor:
    """Simple trading engine monitoring without external dependencies"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.metrics = defaultdict(int)
        self.timing_data = defaultdict(list)
        self.alerts = {}
        self.active_alerts = {}
        self.system_status = "HEALTHY"
        self.lock = threading.Lock()
        
        # Keep last 1000 metrics for each type
        self.max_metrics_history = 1000
        
    def record_metric(self, metric_name: str, value: float = 1.0):
        """Record a metric value"""
        with self.lock:
            self.metrics[metric_name] += value
            
            # Keep timing history
            if metric_name not in self.timing_data:
                self.timing_data[metric_name] = deque(maxlen=self.max_metrics_history)
            
            self.timing_data[metric_name].append({
                'value': value,
                'timestamp': datetime.now()
            })
    
    def record_timing(self, operation: str, duration_ms: float):
        """Record operation timing"""
        self.record_metric(f"{operation}_duration_ms", duration_ms)
        self.record_metric(f"{operation}_count", 1)
    
    def get_metrics_summary(self, metric_name: Optional[str] = None, 
                           time_window_minutes: int = 60) -> Dict[str, Any]:
        """Get metrics summary"""
        with self.lock:
            if metric_name and metric_name in self.metrics:
                return {
                    metric_name: self.metrics[metric_name],
                    'time_window_minutes': time_window_minutes
                }
            
            # Calculate uptime
            uptime = datetime.now() - self.start_time
            uptime_str = f"{int(uptime.total_seconds() // 3600)}h {int((uptime.total_seconds() % 3600) // 60)}m"
            
            return {
                'orders_processed': self.metrics.get('orders_processed', 0),
                'signals_processed': self.metrics.get('signals_processed', 0),
                'active_strategies': self.metrics.get('active_strategies', 0),
                'system_uptime': uptime_str,
                'errors_count': self.metrics.get('errors_count', 0),
                'api_calls_count': self.metrics.get('api_calls_count', 0),
                'last_updated': datetime.now().isoformat(),
                'time_window_minutes': time_window_minutes
            }
    
    def get_timing_summary(self) -> Dict[str, Any]:
        """Get timing summary for operations"""
        with self.lock:
            timing_summary = {}
            
            for operation, timings in self.timing_data.items():
                if operation.endswith('_duration_ms') and timings:
                    base_name = operation.replace('_duration_ms', '')
                    durations = [t['value'] for t in timings]
                    
                    timing_summary[base_name] = {
                        'avg_duration_ms': sum(durations) / len(durations),
                        'min_duration_ms': min(durations),
                        'max_duration_ms': max(durations),
                        'count': len(durations),
                        'last_updated': max(t['timestamp'] for t in timings).isoformat()
                    }
            
            return timing_summary
    
    def create_alert(self, level: str, title: str, message: str, 
                    component: str, user_id: str = None, data: Dict = None) -> str:
        """Create a new alert"""
        alert_id = f"alert_{int(time.time() * 1000)}"
        
        alert = SimpleAlert(
            alert_id=alert_id,
            level=level,
            title=title,
            message=message,
            component=component,
            user_id=user_id,
            data=data
        )
        
        with self.lock:
            self.alerts[alert_id] = alert
            self.active_alerts[alert_id] = alert
            
            # Update system status based on alert level
            if level in ['CRITICAL', 'ERROR']:
                self.system_status = 'CRITICAL'
            elif level == 'WARNING' and self.system_status == 'HEALTHY':
                self.system_status = 'WARNING'
        
        logger.warning(f"Alert created: {level} - {title}: {message}")
        return alert_id
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        with self.lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.resolved_at = datetime.now()
                del self.active_alerts[alert_id]
                
                # Recalculate system status
                self._recalculate_system_status()
                
                logger.info(f"Alert resolved: {alert_id}")
                return True
            return False
    
    def get_active_alerts(self, level: Optional[str] = None, 
                         component: Optional[str] = None) -> List[SimpleAlert]:
        """Get active alerts with optional filtering"""
        with self.lock:
            alerts = list(self.active_alerts.values())
            
            if level:
                alerts = [a for a in alerts if a.level == level]
            
            if component:
                alerts = [a for a in alerts if a.component == component]
            
            return sorted(alerts, key=lambda a: a.created_at, reverse=True)
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        with self.lock:
            uptime = datetime.now() - self.start_time
            
            return {
                'status': self.system_status,
                'uptime_seconds': int(uptime.total_seconds()),
                'active_alerts_count': len(self.active_alerts),
                'total_alerts_count': len(self.alerts),
                'last_updated': datetime.now().isoformat(),
                'components': {
                    'monitoring': 'HEALTHY',
                    'metrics': 'HEALTHY',
                    'alerts': 'HEALTHY'
                }
            }
    
    def _recalculate_system_status(self):
        """Recalculate system status based on active alerts"""
        if not self.active_alerts:
            self.system_status = 'HEALTHY'
            return
        
        alert_levels = [alert.level for alert in self.active_alerts.values()]
        
        if 'CRITICAL' in alert_levels or 'ERROR' in alert_levels:
            self.system_status = 'CRITICAL'
        elif 'WARNING' in alert_levels:
            self.system_status = 'WARNING'
        else:
            self.system_status = 'DEGRADED'

# Global monitoring instance
simple_trading_monitor = SimpleTradingMonitor()

def get_trading_monitor() -> SimpleTradingMonitor:
    """Get the global trading monitor instance"""
    return simple_trading_monitor