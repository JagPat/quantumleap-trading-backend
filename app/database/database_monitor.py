#!/usr/bin/env python3
"""
Database Health Monitor
Real-time monitoring of database performance and health indicators
"""
import os
import sqlite3
import threading
import time
import logging
import json
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import statistics
import queue
import weakref

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Database health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    OFFLINE = "offline"

class MetricType(Enum):
    """Types of metrics to monitor"""
    RESPONSE_TIME = "response_time"
    CONNECTION_COUNT = "connection_count"
    QUERY_RATE = "query_rate"
    ERROR_RATE = "error_rate"
    DISK_USAGE = "disk_usage"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    LOCK_CONTENTION = "lock_contention"
    CACHE_HIT_RATIO = "cache_hit_ratio"

@dataclass
class HealthMetric:
    """Individual health metric"""
    metric_type: MetricType
    value: float
    timestamp: datetime
    threshold_warning: float
    threshold_critical: float
    unit: str
    description: str
    
    @property
    def status(self) -> HealthStatus:
        """Get status based on thresholds"""
        if self.value >= self.threshold_critical:
            return HealthStatus.CRITICAL
        elif self.value >= self.threshold_warning:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY

@dataclass
class HealthReport:
    """Complete health report"""
    timestamp: datetime
    overall_status: HealthStatus
    metrics: Dict[str, HealthMetric]
    alerts: List[str]
    recommendations: List[str]
    uptime: float
    database_size: int
    active_connections: int

@dataclass
class PerformanceTrend:
    """Performance trend analysis"""
    metric_type: MetricType
    current_value: float
    trend_direction: str  # "improving", "degrading", "stable"
    trend_percentage: float
    prediction: Optional[float]
    confidence: float

class DatabaseMonitor:
    """Real-time database health monitoring system"""
    
    def __init__(self, database_path: str = None, monitoring_interval: int = 30,
                 history_retention_hours: int = 24):
        self.database_path = database_path or os.getenv("DATABASE_PATH", "trading_monitor.db")
        self.monitoring_interval = monitoring_interval
        self.history_retention_hours = history_retention_hours
        
        # Monitoring state
        self.is_monitoring = False
        self.monitor_thread = None
        self.monitor_lock = threading.RLock()
        
        # Metrics storage
        self.metrics_history: List[HealthReport] = []
        self.current_metrics: Dict[str, HealthMetric] = {}
        self.alert_callbacks: List[Callable[[HealthReport], None]] = []
        
        # Performance tracking
        self.start_time = datetime.now()
        self.query_count = 0
        self.error_count = 0
        self.connection_count = 0
        self.last_query_time = 0.0
        
        # Thresholds (configurable)
        self.thresholds = {
            MetricType.RESPONSE_TIME: {"warning": 100.0, "critical": 500.0, "unit": "ms"},
            MetricType.CONNECTION_COUNT: {"warning": 80, "critical": 95, "unit": "count"},
            MetricType.QUERY_RATE: {"warning": 1000, "critical": 2000, "unit": "queries/min"},
            MetricType.ERROR_RATE: {"warning": 5.0, "critical": 10.0, "unit": "%"},
            MetricType.DISK_USAGE: {"warning": 80.0, "critical": 95.0, "unit": "%"},
            MetricType.MEMORY_USAGE: {"warning": 80.0, "critical": 95.0, "unit": "%"},
            MetricType.CPU_USAGE: {"warning": 80.0, "critical": 95.0, "unit": "%"},
            MetricType.LOCK_CONTENTION: {"warning": 10.0, "critical": 25.0, "unit": "%"},
            MetricType.CACHE_HIT_RATIO: {"warning": 80.0, "critical": 60.0, "unit": "%"}
        }
        
        # Initialize monitoring database
        self._initialize_monitoring_db()
    
    def _initialize_monitoring_db(self):
        """Initialize monitoring database tables"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Create health metrics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS health_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        metric_type TEXT NOT NULL,
                        value REAL NOT NULL,
                        status TEXT NOT NULL,
                        unit TEXT NOT NULL,
                        description TEXT
                    )
                """)
                
                # Create health reports table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS health_reports (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        overall_status TEXT NOT NULL,
                        uptime REAL NOT NULL,
                        database_size INTEGER NOT NULL,
                        active_connections INTEGER NOT NULL,
                        alerts TEXT,
                        recommendations TEXT
                    )
                """)
                
                # Create performance trends table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS performance_trends (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        metric_type TEXT NOT NULL,
                        current_value REAL NOT NULL,
                        trend_direction TEXT NOT NULL,
                        trend_percentage REAL NOT NULL,
                        prediction REAL,
                        confidence REAL NOT NULL
                    )
                """)
                
                # Create indexes for better query performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_health_metrics_timestamp ON health_metrics(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_health_metrics_type ON health_metrics(metric_type)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_health_reports_timestamp ON health_reports(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_trends_timestamp ON performance_trends(timestamp)")
                
                conn.commit()
                logger.info("✅ Database monitoring tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize monitoring database: {e}")
            raise
    
    def start_monitoring(self):
        """Start real-time monitoring"""
        try:
            with self.monitor_lock:
                if self.is_monitoring:
                    logger.warning("Monitoring is already running")
                    return
                
                self.is_monitoring = True
                self.monitor_thread = threading.Thread(
                    target=self._monitoring_loop,
                    daemon=True,
                    name="DatabaseHealthMonitor"
                )
                self.monitor_thread.start()
                
                logger.info(f"✅ Database monitoring started (interval: {self.monitoring_interval}s)")
                
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            self.is_monitoring = False
            raise
    
    def stop_monitoring(self):
        """Stop monitoring"""
        try:
            with self.monitor_lock:
                if not self.is_monitoring:
                    logger.warning("Monitoring is not running")
                    return
                
                self.is_monitoring = False
                
                if self.monitor_thread and self.monitor_thread.is_alive():
                    self.monitor_thread.join(timeout=10)
                
                logger.info("✅ Database monitoring stopped")
                
        except Exception as e:
            logger.error(f"Failed to stop monitoring: {e}")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                # Collect current metrics
                report = self._collect_health_metrics()
                
                # Store metrics
                self._store_health_report(report)
                
                # Update in-memory storage
                with self.monitor_lock:
                    self.metrics_history.append(report)
                    self.current_metrics = report.metrics
                    
                    # Cleanup old metrics
                    cutoff_time = datetime.now() - timedelta(hours=self.history_retention_hours)
                    self.metrics_history = [
                        r for r in self.metrics_history 
                        if r.timestamp > cutoff_time
                    ]
                
                # Trigger alerts if needed
                self._check_alerts(report)
                
                # Analyze trends
                self._analyze_trends()
                
                # Sleep until next monitoring cycle
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)  # Short sleep on error
    
    def _collect_health_metrics(self) -> HealthReport:
        """Collect current health metrics"""
        try:
            timestamp = datetime.now()
            metrics = {}
            alerts = []
            recommendations = []
            
            # Database connectivity and response time
            response_time = self._measure_response_time()
            metrics["response_time"] = HealthMetric(
                metric_type=MetricType.RESPONSE_TIME,
                value=response_time * 1000,  # Convert to milliseconds
                timestamp=timestamp,
                threshold_warning=self.thresholds[MetricType.RESPONSE_TIME]["warning"],
                threshold_critical=self.thresholds[MetricType.RESPONSE_TIME]["critical"],
                unit="ms",
                description="Database query response time"
            )
            
            # Connection count
            connection_count = self._get_connection_count()
            metrics["connection_count"] = HealthMetric(
                metric_type=MetricType.CONNECTION_COUNT,
                value=connection_count,
                timestamp=timestamp,
                threshold_warning=self.thresholds[MetricType.CONNECTION_COUNT]["warning"],
                threshold_critical=self.thresholds[MetricType.CONNECTION_COUNT]["critical"],
                unit="count",
                description="Active database connections"
            )
            
            # Query rate
            query_rate = self._calculate_query_rate()
            metrics["query_rate"] = HealthMetric(
                metric_type=MetricType.QUERY_RATE,
                value=query_rate,
                timestamp=timestamp,
                threshold_warning=self.thresholds[MetricType.QUERY_RATE]["warning"],
                threshold_critical=self.thresholds[MetricType.QUERY_RATE]["critical"],
                unit="queries/min",
                description="Database queries per minute"
            )
            
            # Error rate
            error_rate = self._calculate_error_rate()
            metrics["error_rate"] = HealthMetric(
                metric_type=MetricType.ERROR_RATE,
                value=error_rate,
                timestamp=timestamp,
                threshold_warning=self.thresholds[MetricType.ERROR_RATE]["warning"],
                threshold_critical=self.thresholds[MetricType.ERROR_RATE]["critical"],
                unit="%",
                description="Database error rate percentage"
            )
            
            # System metrics
            disk_usage = self._get_disk_usage()
            metrics["disk_usage"] = HealthMetric(
                metric_type=MetricType.DISK_USAGE,
                value=disk_usage,
                timestamp=timestamp,
                threshold_warning=self.thresholds[MetricType.DISK_USAGE]["warning"],
                threshold_critical=self.thresholds[MetricType.DISK_USAGE]["critical"],
                unit="%",
                description="Database disk usage percentage"
            )
            
            memory_usage = self._get_memory_usage()
            metrics["memory_usage"] = HealthMetric(
                metric_type=MetricType.MEMORY_USAGE,
                value=memory_usage,
                timestamp=timestamp,
                threshold_warning=self.thresholds[MetricType.MEMORY_USAGE]["warning"],
                threshold_critical=self.thresholds[MetricType.MEMORY_USAGE]["critical"],
                unit="%",
                description="System memory usage percentage"
            )
            
            cpu_usage = self._get_cpu_usage()
            metrics["cpu_usage"] = HealthMetric(
                metric_type=MetricType.CPU_USAGE,
                value=cpu_usage,
                timestamp=timestamp,
                threshold_warning=self.thresholds[MetricType.CPU_USAGE]["warning"],
                threshold_critical=self.thresholds[MetricType.CPU_USAGE]["critical"],
                unit="%",
                description="System CPU usage percentage"
            )
            
            # Database-specific metrics
            cache_hit_ratio = self._get_cache_hit_ratio()
            metrics["cache_hit_ratio"] = HealthMetric(
                metric_type=MetricType.CACHE_HIT_RATIO,
                value=cache_hit_ratio,
                timestamp=timestamp,
                threshold_warning=self.thresholds[MetricType.CACHE_HIT_RATIO]["warning"],
                threshold_critical=self.thresholds[MetricType.CACHE_HIT_RATIO]["critical"],
                unit="%",
                description="Database cache hit ratio"
            )
            
            # Determine overall status
            overall_status = self._determine_overall_status(metrics)
            
            # Generate alerts and recommendations
            alerts, recommendations = self._generate_alerts_and_recommendations(metrics)
            
            # Calculate uptime
            uptime = (timestamp - self.start_time).total_seconds()
            
            # Get database size
            database_size = self._get_database_size()
            
            return HealthReport(
                timestamp=timestamp,
                overall_status=overall_status,
                metrics=metrics,
                alerts=alerts,
                recommendations=recommendations,
                uptime=uptime,
                database_size=database_size,
                active_connections=connection_count
            )
            
        except Exception as e:
            logger.error(f"Failed to collect health metrics: {e}")
            # Return minimal report on error
            return HealthReport(
                timestamp=datetime.now(),
                overall_status=HealthStatus.OFFLINE,
                metrics={},
                alerts=[f"Failed to collect metrics: {str(e)}"],
                recommendations=["Check database connectivity"],
                uptime=0.0,
                database_size=0,
                active_connections=0
            )
    
    def _measure_response_time(self) -> float:
        """Measure database response time"""
        try:
            start_time = time.time()
            with sqlite3.connect(self.database_path, timeout=5) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
            end_time = time.time()
            return end_time - start_time
        except Exception as e:
            logger.error(f"Failed to measure response time: {e}")
            return 999.0  # Return high value on error
    
    def _get_connection_count(self) -> int:
        """Get current connection count"""
        # For SQLite, this is always 1 for the current connection
        # In a real multi-connection scenario, this would query the connection pool
        return self.connection_count
    
    def _calculate_query_rate(self) -> float:
        """Calculate queries per minute"""
        uptime_minutes = max((datetime.now() - self.start_time).total_seconds() / 60, 1)
        return self.query_count / uptime_minutes
    
    def _calculate_error_rate(self) -> float:
        """Calculate error rate percentage"""
        if self.query_count == 0:
            return 0.0
        return (self.error_count / self.query_count) * 100
    
    def _get_disk_usage(self) -> float:
        """Get disk usage percentage for database directory"""
        try:
            db_dir = os.path.dirname(os.path.abspath(self.database_path))
            total, used, free = shutil.disk_usage(db_dir)
            return (used / total) * 100
        except Exception as e:
            logger.error(f"Failed to get disk usage: {e}")
            return 0.0
    
    def _get_memory_usage(self) -> float:
        """Get system memory usage percentage (simplified)"""
        try:
            # Simplified memory usage - in production, use psutil
            # For now, return a reasonable default
            return 45.0  # Simulate 45% memory usage
        except Exception as e:
            logger.error(f"Failed to get memory usage: {e}")
            return 0.0
    
    def _get_cpu_usage(self) -> float:
        """Get system CPU usage percentage (simplified)"""
        try:
            # Simplified CPU usage - in production, use psutil
            # For now, return a reasonable default
            return 25.0  # Simulate 25% CPU usage
        except Exception as e:
            logger.error(f"Failed to get CPU usage: {e}")
            return 0.0
    
    def _get_cache_hit_ratio(self) -> float:
        """Get database cache hit ratio"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA cache_size")
                cache_size = cursor.fetchone()[0]
                
                # For SQLite, we'll simulate cache hit ratio based on query patterns
                # In a real database, this would query actual cache statistics
                if hasattr(self, '_cache_hits') and hasattr(self, '_cache_misses'):
                    total_requests = self._cache_hits + self._cache_misses
                    if total_requests > 0:
                        return (self._cache_hits / total_requests) * 100
                
                # Default to a reasonable cache hit ratio
                return 85.0
        except Exception as e:
            logger.error(f"Failed to get cache hit ratio: {e}")
            return 0.0
    
    def _get_database_size(self) -> int:
        """Get database file size in bytes"""
        try:
            if os.path.exists(self.database_path):
                return os.path.getsize(self.database_path)
            return 0
        except Exception as e:
            logger.error(f"Failed to get database size: {e}")
            return 0
    
    def _determine_overall_status(self, metrics: Dict[str, HealthMetric]) -> HealthStatus:
        """Determine overall health status from individual metrics"""
        if not metrics:
            return HealthStatus.OFFLINE
        
        critical_count = sum(1 for m in metrics.values() if m.status == HealthStatus.CRITICAL)
        warning_count = sum(1 for m in metrics.values() if m.status == HealthStatus.WARNING)
        
        if critical_count > 0:
            return HealthStatus.CRITICAL
        elif warning_count > 0:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
    
    def _generate_alerts_and_recommendations(self, metrics: Dict[str, HealthMetric]) -> Tuple[List[str], List[str]]:
        """Generate alerts and recommendations based on metrics"""
        alerts = []
        recommendations = []
        
        for metric_name, metric in metrics.items():
            if metric.status == HealthStatus.CRITICAL:
                alerts.append(f"CRITICAL: {metric.description} is {metric.value:.2f}{metric.unit} (threshold: {metric.threshold_critical}{metric.unit})")
                
                # Add specific recommendations
                if metric.metric_type == MetricType.RESPONSE_TIME:
                    recommendations.append("Consider optimizing slow queries or adding indexes")
                elif metric.metric_type == MetricType.DISK_USAGE:
                    recommendations.append("Free up disk space or archive old data")
                elif metric.metric_type == MetricType.MEMORY_USAGE:
                    recommendations.append("Increase system memory or optimize memory usage")
                elif metric.metric_type == MetricType.ERROR_RATE:
                    recommendations.append("Investigate and fix database errors")
                    
            elif metric.status == HealthStatus.WARNING:
                alerts.append(f"WARNING: {metric.description} is {metric.value:.2f}{metric.unit} (threshold: {metric.threshold_warning}{metric.unit})")
        
        return alerts, recommendations
    
    def _store_health_report(self, report: HealthReport):
        """Store health report in database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Store individual metrics
                for metric_name, metric in report.metrics.items():
                    cursor.execute("""
                        INSERT INTO health_metrics 
                        (timestamp, metric_type, value, status, unit, description)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        metric.timestamp.isoformat(),
                        metric.metric_type.value,
                        metric.value,
                        metric.status.value,
                        metric.unit,
                        metric.description
                    ))
                
                # Store overall report
                cursor.execute("""
                    INSERT INTO health_reports 
                    (timestamp, overall_status, uptime, database_size, active_connections, alerts, recommendations)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    report.timestamp.isoformat(),
                    report.overall_status.value,
                    report.uptime,
                    report.database_size,
                    report.active_connections,
                    json.dumps(report.alerts),
                    json.dumps(report.recommendations)
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to store health report: {e}")
    
    def _check_alerts(self, report: HealthReport):
        """Check for alerts and notify callbacks"""
        if report.alerts:
            for callback in self.alert_callbacks:
                try:
                    callback(report)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")
    
    def _analyze_trends(self):
        """Analyze performance trends"""
        try:
            if len(self.metrics_history) < 2:
                return
            
            # Analyze trends for each metric type
            for metric_type in MetricType:
                trend = self._calculate_trend(metric_type)
                if trend:
                    self._store_trend(trend)
                    
        except Exception as e:
            logger.error(f"Failed to analyze trends: {e}")
    
    def _calculate_trend(self, metric_type: MetricType) -> Optional[PerformanceTrend]:
        """Calculate trend for a specific metric type"""
        try:
            # Get recent values for this metric
            values = []
            timestamps = []
            
            for report in self.metrics_history[-10:]:  # Last 10 reports
                metric_key = metric_type.value
                if metric_key in report.metrics:
                    values.append(report.metrics[metric_key].value)
                    timestamps.append(report.timestamp)
            
            if len(values) < 2:
                return None
            
            # Calculate trend
            current_value = values[-1]
            previous_value = values[0]
            
            if previous_value == 0:
                trend_percentage = 0.0
            else:
                trend_percentage = ((current_value - previous_value) / previous_value) * 100
            
            # Determine trend direction
            if abs(trend_percentage) < 5:  # Less than 5% change
                trend_direction = "stable"
            elif trend_percentage > 0:
                trend_direction = "increasing"
            else:
                trend_direction = "decreasing"
            
            # Simple linear prediction (next value)
            if len(values) >= 3:
                recent_slope = (values[-1] - values[-3]) / 2
                prediction = current_value + recent_slope
            else:
                prediction = current_value
            
            # Calculate confidence based on data consistency
            if len(values) >= 3:
                variance = statistics.variance(values)
                confidence = max(0.0, min(1.0, 1.0 - (variance / (current_value + 1))))
            else:
                confidence = 0.5
            
            return PerformanceTrend(
                metric_type=metric_type,
                current_value=current_value,
                trend_direction=trend_direction,
                trend_percentage=trend_percentage,
                prediction=prediction,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate trend for {metric_type}: {e}")
            return None
    
    def _store_trend(self, trend: PerformanceTrend):
        """Store performance trend in database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO performance_trends 
                    (timestamp, metric_type, current_value, trend_direction, 
                     trend_percentage, prediction, confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(),
                    trend.metric_type.value,
                    trend.current_value,
                    trend.trend_direction,
                    trend.trend_percentage,
                    trend.prediction,
                    trend.confidence
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to store trend: {e}")
    
    def get_current_health(self) -> Optional[HealthReport]:
        """Get current health status"""
        with self.monitor_lock:
            if self.metrics_history:
                return self.metrics_history[-1]
            return None
    
    def get_health_history(self, hours: int = 1) -> List[HealthReport]:
        """Get health history for specified time period"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        with self.monitor_lock:
            return [
                report for report in self.metrics_history 
                if report.timestamp > cutoff_time
            ]
    
    def get_metric_history(self, metric_type: MetricType, hours: int = 1) -> List[Tuple[datetime, float]]:
        """Get history for a specific metric"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        history = []
        
        with self.monitor_lock:
            for report in self.metrics_history:
                if report.timestamp > cutoff_time:
                    metric_key = metric_type.value
                    if metric_key in report.metrics:
                        history.append((report.timestamp, report.metrics[metric_key].value))
        
        return history
    
    def get_performance_trends(self, hours: int = 24) -> List[PerformanceTrend]:
        """Get performance trends from database"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            trends = []
            
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT metric_type, current_value, trend_direction, 
                           trend_percentage, prediction, confidence, timestamp
                    FROM performance_trends 
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                """, (cutoff_time.isoformat(),))
                
                for row in cursor.fetchall():
                    trend = PerformanceTrend(
                        metric_type=MetricType(row[0]),
                        current_value=row[1],
                        trend_direction=row[2],
                        trend_percentage=row[3],
                        prediction=row[4],
                        confidence=row[5]
                    )
                    trends.append(trend)
            
            return trends
            
        except Exception as e:
            logger.error(f"Failed to get performance trends: {e}")
            return []
    
    def add_alert_callback(self, callback: Callable[[HealthReport], None]):
        """Add alert callback function"""
        self.alert_callbacks.append(callback)
    
    def remove_alert_callback(self, callback: Callable[[HealthReport], None]):
        """Remove alert callback function"""
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)
    
    def update_thresholds(self, metric_type: MetricType, warning: float, critical: float):
        """Update thresholds for a metric type"""
        if metric_type in self.thresholds:
            self.thresholds[metric_type]["warning"] = warning
            self.thresholds[metric_type]["critical"] = critical
            logger.info(f"Updated thresholds for {metric_type.value}: warning={warning}, critical={critical}")
    
    def record_query(self, execution_time: float, success: bool = True):
        """Record query execution for metrics"""
        self.query_count += 1
        self.last_query_time = execution_time
        if not success:
            self.error_count += 1
    
    def record_connection(self, active: bool = True):
        """Record connection activity"""
        if active:
            self.connection_count += 1
        else:
            self.connection_count = max(0, self.connection_count - 1)
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for monitoring dashboard"""
        current_health = self.get_current_health()
        if not current_health:
            return {"status": "no_data", "message": "No monitoring data available"}
        
        # Get recent trends
        trends = self.get_performance_trends(hours=1)
        
        # Prepare dashboard data
        dashboard_data = {
            "status": current_health.overall_status.value,
            "timestamp": current_health.timestamp.isoformat(),
            "uptime": current_health.uptime,
            "database_size": current_health.database_size,
            "active_connections": current_health.active_connections,
            "metrics": {
                name: {
                    "value": metric.value,
                    "unit": metric.unit,
                    "status": metric.status.value,
                    "description": metric.description
                }
                for name, metric in current_health.metrics.items()
            },
            "alerts": current_health.alerts,
            "recommendations": current_health.recommendations,
            "trends": [
                {
                    "metric_type": trend.metric_type.value,
                    "current_value": trend.current_value,
                    "trend_direction": trend.trend_direction,
                    "trend_percentage": trend.trend_percentage,
                    "confidence": trend.confidence
                }
                for trend in trends[:5]  # Top 5 trends
            ]
        }
        
        return dashboard_data
    
    def cleanup_old_data(self, days: int = 7):
        """Clean up old monitoring data"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Clean up old metrics
                cursor.execute("DELETE FROM health_metrics WHERE timestamp < ?", (cutoff_time.isoformat(),))
                metrics_deleted = cursor.rowcount
                
                # Clean up old reports
                cursor.execute("DELETE FROM health_reports WHERE timestamp < ?", (cutoff_time.isoformat(),))
                reports_deleted = cursor.rowcount
                
                # Clean up old trends
                cursor.execute("DELETE FROM performance_trends WHERE timestamp < ?", (cutoff_time.isoformat(),))
                trends_deleted = cursor.rowcount
                
                conn.commit()
                
                logger.info(f"✅ Cleaned up old data: {metrics_deleted} metrics, {reports_deleted} reports, {trends_deleted} trends")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
    
    def __del__(self):
        """Cleanup on destruction"""
        try:
            self.stop_monitoring()
        except:
            pass

# Example usage and testing
if __name__ == "__main__":
    # Initialize database monitor
    monitor = DatabaseMonitor(monitoring_interval=10)
    
    # Add alert callback
    def alert_handler(report: HealthReport):
        print(f"🚨 ALERT: {report.overall_status.value}")
        for alert in report.alerts:
            print(f"   - {alert}")
    
    monitor.add_alert_callback(alert_handler)
    
    try:
        # Start monitoring
        monitor.start_monitoring()
        print("✅ Monitoring started")
        
        # Simulate some activity
        for i in range(5):
            monitor.record_query(0.05, success=True)
            time.sleep(2)
        
        # Get current health
        health = monitor.get_current_health()
        if health:
            print(f"Current status: {health.overall_status.value}")
            print(f"Active connections: {health.active_connections}")
            print(f"Database size: {health.database_size} bytes")
        
        # Get dashboard data
        dashboard = monitor.get_dashboard_data()
        print(f"Dashboard status: {dashboard['status']}")
        
        # Wait a bit more
        time.sleep(15)
        
    except KeyboardInterrupt:
        print("\n⏹️ Stopping monitoring...")
    finally:
        monitor.stop_monitoring()
        print("✅ Monitoring stopped")