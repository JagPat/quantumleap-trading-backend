"""
Advanced Performance Metrics Collection System

Real-time performance monitoring with time-series data collection,
alerting, and trend analysis for Railway deployment.
"""

import os
import time
import threading
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import deque, defaultdict
import json
import statistics

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Individual performance metric data point"""
    timestamp: datetime
    metric_name: str
    value: float
    tags: Dict[str, str]
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class AlertThreshold:
    """Performance alert threshold configuration"""
    metric_name: str
    threshold_value: float
    comparison: str  # 'gt', 'lt', 'eq'
    duration_seconds: int
    severity: str  # 'low', 'medium', 'high', 'critical'
    callback: Optional[Callable] = None

@dataclass
class PerformanceAlert:
    """Performance alert instance"""
    alert_id: str
    metric_name: str
    current_value: float
    threshold_value: float
    severity: str
    message: str
    triggered_at: datetime
    resolved_at: Optional[datetime] = None

class PerformanceCollector:
    """Advanced performance metrics collection system"""
    
    def __init__(self, max_metrics_per_type: int = 10000, collection_interval: float = 1.0):
        self.max_metrics_per_type = max_metrics_per_type
        self.collection_interval = collection_interval
        
        # Storage
        self.metrics_storage = defaultdict(lambda: deque(maxlen=max_metrics_per_type))
        self.alert_thresholds = {}
        self.active_alerts = {}
        self.alert_history = deque(maxlen=1000)
        
        # Threading
        self._lock = threading.Lock()
        self._collection_thread = None
        self._stop_collection = threading.Event()
        self._running = False
        
        # Callbacks
        self.alert_callbacks = []
        
        # Railway-specific metrics
        self.railway_metrics = {
            'database_connections': 0,
            'query_queue_depth': 0,
            'memory_usage_mb': 0,
            'cpu_usage_percent': 0
        }
        
        logger.info("📊 Performance collector initialized for Railway")
    
    def record_metric(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None, 
                     metadata: Optional[Dict[str, Any]] = None):
        """Record a performance metric"""
        metric = PerformanceMetric(
            timestamp=datetime.now(),
            metric_name=metric_name,
            value=value,
            tags=tags or {},
            metadata=metadata
        )
        
        with self._lock:
            self.metrics_storage[metric_name].append(metric)
        
        # Check for alerts
        self._check_alert_thresholds(metric)
        
        logger.debug(f"📈 Recorded metric: {metric_name} = {value}")
    
    def record_query_performance(self, query_hash: str, execution_time_ms: float, 
                                success: bool, error: Optional[str] = None):
        """Record query performance metrics"""
        tags = {
            'query_hash': query_hash[:8],  # Short hash for grouping
            'success': str(success)
        }
        
        metadata = {
            'query_hash': query_hash,
            'error': error
        }
        
        # Record execution time
        self.record_metric('query_execution_time_ms', execution_time_ms, tags, metadata)
        
        # Record success/failure
        self.record_metric('query_success_rate', 1.0 if success else 0.0, tags, metadata)
        
        # Record error rate
        self.record_metric('query_error_rate', 0.0 if success else 1.0, tags, metadata)
    
    def record_connection_metrics(self, active_connections: int, pool_size: int, 
                                 wait_time_ms: float = 0):
        """Record database connection metrics"""
        self.record_metric('db_active_connections', active_connections)
        self.record_metric('db_pool_utilization', (active_connections / pool_size) * 100 if pool_size > 0 else 0)
        
        if wait_time_ms > 0:
            self.record_metric('db_connection_wait_time_ms', wait_time_ms)
    
    def record_system_metrics(self, cpu_percent: float = 0, memory_mb: float = 0, 
                             disk_usage_percent: float = 0):
        """Record system-level metrics"""
        if cpu_percent > 0:
            self.record_metric('system_cpu_percent', cpu_percent)
        
        if memory_mb > 0:
            self.record_metric('system_memory_mb', memory_mb)
        
        if disk_usage_percent > 0:
            self.record_metric('system_disk_percent', disk_usage_percent)
    
    def add_alert_threshold(self, metric_name: str, threshold_value: float, 
                           comparison: str = 'gt', duration_seconds: int = 60,
                           severity: str = 'medium', callback: Optional[Callable] = None):
        """Add performance alert threshold"""
        threshold = AlertThreshold(
            metric_name=metric_name,
            threshold_value=threshold_value,
            comparison=comparison,
            duration_seconds=duration_seconds,
            severity=severity,
            callback=callback
        )
        
        self.alert_thresholds[f"{metric_name}_{comparison}_{threshold_value}"] = threshold
        logger.info(f"🚨 Added alert threshold: {metric_name} {comparison} {threshold_value}")
    
    def _check_alert_thresholds(self, metric: PerformanceMetric):
        """Check if metric triggers any alert thresholds"""
        for threshold_id, threshold in self.alert_thresholds.items():
            if threshold.metric_name != metric.metric_name:
                continue
            
            # Check threshold condition
            triggered = False
            if threshold.comparison == 'gt' and metric.value > threshold.threshold_value:
                triggered = True
            elif threshold.comparison == 'lt' and metric.value < threshold.threshold_value:
                triggered = True
            elif threshold.comparison == 'eq' and abs(metric.value - threshold.threshold_value) < 0.001:
                triggered = True
            
            if triggered:
                self._handle_alert_trigger(threshold, metric)
            else:
                # Check if we should resolve an existing alert
                if threshold_id in self.active_alerts:
                    self._resolve_alert(threshold_id)
    
    def _handle_alert_trigger(self, threshold: AlertThreshold, metric: PerformanceMetric):
        """Handle alert threshold trigger"""
        threshold_id = f"{threshold.metric_name}_{threshold.comparison}_{threshold.threshold_value}"
        
        # Check if alert is already active
        if threshold_id in self.active_alerts:
            return
        
        # Create new alert
        alert = PerformanceAlert(
            alert_id=threshold_id,
            metric_name=threshold.metric_name,
            current_value=metric.value,
            threshold_value=threshold.threshold_value,
            severity=threshold.severity,
            message=f"{threshold.metric_name} is {metric.value} (threshold: {threshold.comparison} {threshold.threshold_value})",
            triggered_at=datetime.now()
        )
        
        self.active_alerts[threshold_id] = alert
        self.alert_history.append(alert)
        
        # Execute callback if provided
        if threshold.callback:
            try:
                threshold.callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
        
        # Execute global callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Global alert callback failed: {e}")
        
        logger.warning(f"🚨 ALERT TRIGGERED: {alert.message}")
    
    def _resolve_alert(self, threshold_id: str):
        """Resolve an active alert"""
        if threshold_id in self.active_alerts:
            alert = self.active_alerts[threshold_id]
            alert.resolved_at = datetime.now()
            del self.active_alerts[threshold_id]
            
            logger.info(f"✅ ALERT RESOLVED: {alert.message}")
    
    def get_metrics(self, metric_name: str, time_window_minutes: int = 60) -> List[Dict[str, Any]]:
        """Get metrics for a specific metric name within time window"""
        cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
        
        with self._lock:
            if metric_name not in self.metrics_storage:
                return []
            
            metrics = []
            for metric in self.metrics_storage[metric_name]:
                if metric.timestamp >= cutoff_time:
                    metrics.append({
                        'timestamp': metric.timestamp.isoformat(),
                        'value': metric.value,
                        'tags': metric.tags,
                        'metadata': metric.metadata
                    })
            
            return metrics
    
    def get_metric_statistics(self, metric_name: str, time_window_minutes: int = 60) -> Dict[str, Any]:
        """Get statistical summary for a metric"""
        metrics = self.get_metrics(metric_name, time_window_minutes)
        
        if not metrics:
            return {
                'metric_name': metric_name,
                'count': 0,
                'time_window_minutes': time_window_minutes
            }
        
        values = [m['value'] for m in metrics]
        
        return {
            'metric_name': metric_name,
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'std_dev': statistics.stdev(values) if len(values) > 1 else 0,
            'p95': self._percentile(values, 95),
            'p99': self._percentile(values, 99),
            'time_window_minutes': time_window_minutes,
            'latest_value': values[-1] if values else 0,
            'latest_timestamp': metrics[-1]['timestamp'] if metrics else None
        }
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value"""
        if not values:
            return 0
        
        sorted_values = sorted(values)
        index = int((percentile / 100) * len(sorted_values))
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]
    
    def get_performance_dashboard(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """Get comprehensive performance dashboard data"""
        dashboard = {
            'timestamp': datetime.now().isoformat(),
            'time_window_minutes': time_window_minutes,
            'metrics': {},
            'alerts': {
                'active_count': len(self.active_alerts),
                'active_alerts': [asdict(alert) for alert in self.active_alerts.values()],
                'recent_alerts': [asdict(alert) for alert in list(self.alert_history)[-10:]]
            },
            'system_health': self._calculate_system_health()
        }
        
        # Key metrics to include in dashboard
        key_metrics = [
            'query_execution_time_ms',
            'query_success_rate',
            'query_error_rate',
            'db_active_connections',
            'db_pool_utilization',
            'system_cpu_percent',
            'system_memory_mb'
        ]
        
        for metric_name in key_metrics:
            stats = self.get_metric_statistics(metric_name, time_window_minutes)
            if stats['count'] > 0:
                dashboard['metrics'][metric_name] = stats
        
        return dashboard
    
    def _calculate_system_health(self) -> Dict[str, Any]:
        """Calculate overall system health score"""
        health_score = 100
        issues = []
        
        # Check recent query performance
        query_stats = self.get_metric_statistics('query_execution_time_ms', 5)  # Last 5 minutes
        if query_stats['count'] > 0:
            if query_stats['p95'] > 100:  # 95th percentile > 100ms
                health_score -= 20
                issues.append('Slow query performance detected')
            elif query_stats['p95'] > 50:
                health_score -= 10
                issues.append('Moderate query performance degradation')
        
        # Check error rate
        error_stats = self.get_metric_statistics('query_error_rate', 5)
        if error_stats['count'] > 0 and error_stats['mean'] > 0.05:  # > 5% error rate
            health_score -= 30
            issues.append('High error rate detected')
        
        # Check connection pool utilization
        pool_stats = self.get_metric_statistics('db_pool_utilization', 5)
        if pool_stats['count'] > 0 and pool_stats['mean'] > 90:  # > 90% utilization
            health_score -= 15
            issues.append('High database connection pool utilization')
        
        # Check active alerts
        critical_alerts = sum(1 for alert in self.active_alerts.values() if alert.severity == 'critical')
        high_alerts = sum(1 for alert in self.active_alerts.values() if alert.severity == 'high')
        
        health_score -= critical_alerts * 25
        health_score -= high_alerts * 15
        
        if critical_alerts > 0:
            issues.append(f'{critical_alerts} critical alerts active')
        if high_alerts > 0:
            issues.append(f'{high_alerts} high severity alerts active')
        
        health_score = max(0, health_score)  # Don't go below 0
        
        # Determine health status
        if health_score >= 90:
            status = 'excellent'
        elif health_score >= 75:
            status = 'good'
        elif health_score >= 50:
            status = 'fair'
        elif health_score >= 25:
            status = 'poor'
        else:
            status = 'critical'
        
        return {
            'score': health_score,
            'status': status,
            'issues': issues,
            'active_alerts_count': len(self.active_alerts)
        }
    
    def start_collection(self):
        """Start automatic metrics collection"""
        if self._running:
            return
        
        self._running = True
        self._stop_collection.clear()
        self._collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
        self._collection_thread.start()
        
        logger.info("🔄 Performance collection started")
    
    def stop_collection(self):
        """Stop automatic metrics collection"""
        if not self._running:
            return
        
        self._running = False
        self._stop_collection.set()
        
        if self._collection_thread:
            self._collection_thread.join(timeout=5)
        
        logger.info("⏹️ Performance collection stopped")
    
    def _collection_loop(self):
        """Main collection loop for automatic metrics"""
        while not self._stop_collection.wait(self.collection_interval):
            try:
                self._collect_system_metrics()
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
    
    def _collect_system_metrics(self):
        """Collect system-level metrics"""
        try:
            # Try to get system metrics if psutil is available
            try:
                import psutil
                
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=None)
                self.record_metric('system_cpu_percent', cpu_percent)
                
                # Memory usage
                memory = psutil.virtual_memory()
                self.record_metric('system_memory_mb', memory.used / 1024 / 1024)
                self.record_metric('system_memory_percent', memory.percent)
                
                # Disk usage
                disk = psutil.disk_usage('/')
                disk_percent = (disk.used / disk.total) * 100
                self.record_metric('system_disk_percent', disk_percent)
                
            except ImportError:
                # Fallback metrics without psutil
                self.record_metric('system_uptime_seconds', time.time())
        
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
    
    def add_alert_callback(self, callback: Callable[[PerformanceAlert], None]):
        """Add global alert callback"""
        self.alert_callbacks.append(callback)
    
    def export_metrics(self, format: str = 'json', time_window_minutes: int = 60) -> str:
        """Export metrics in specified format"""
        if format.lower() == 'json':
            dashboard = self.get_performance_dashboard(time_window_minutes)
            return json.dumps(dashboard, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def clear_metrics(self, older_than_hours: int = 24):
        """Clear old metrics to free memory"""
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        
        with self._lock:
            for metric_name in self.metrics_storage:
                # Filter out old metrics
                filtered_metrics = deque(
                    (m for m in self.metrics_storage[metric_name] if m.timestamp >= cutoff_time),
                    maxlen=self.max_metrics_per_type
                )
                self.metrics_storage[metric_name] = filtered_metrics
        
        logger.info(f"🧹 Cleared metrics older than {older_than_hours} hours")

# Global performance collector instance
_performance_collector = None

def get_performance_collector() -> PerformanceCollector:
    """Get the global performance collector instance"""
    global _performance_collector
    if _performance_collector is None:
        _performance_collector = PerformanceCollector()
        
        # Set up default Railway alert thresholds
        _performance_collector.add_alert_threshold('query_execution_time_ms', 100, 'gt', 60, 'medium')
        _performance_collector.add_alert_threshold('query_error_rate', 0.05, 'gt', 30, 'high')
        _performance_collector.add_alert_threshold('db_pool_utilization', 90, 'gt', 60, 'high')
        _performance_collector.add_alert_threshold('system_cpu_percent', 80, 'gt', 120, 'medium')
        _performance_collector.add_alert_threshold('system_memory_percent', 85, 'gt', 120, 'high')
        
        # Start collection if in Railway environment
        if os.getenv('RAILWAY_ENVIRONMENT'):
            _performance_collector.start_collection()
    
    return _performance_collector