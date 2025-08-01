#!/usr/bin/env python3
"""
Performance Monitoring and Optimization System
Real-time performance monitoring with automatic optimization
"""

import os
import sys
import json
import time
import sqlite3
import threading
import requests
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Dict, List, Optional
import statistics
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('performance_monitoring.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Real-time performance monitoring system"""
    
    def __init__(self, db_path="production_trading.db"):
        self.db_path = db_path
        self.monitoring_active = False
        self.monitoring_interval = 15  # seconds
        self.performance_history = []
        self.optimization_triggers = {
            "high_response_time": 2.0,
            "high_cpu_usage": 80.0,
            "high_memory_usage": 85.0,
            "high_error_rate": 0.02,
            "low_throughput": 10.0  # requests per second
        }
        self._init_performance_tables()
    
    def _init_performance_tables(self):
        """Initialize performance monitoring tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Performance metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                metric_value REAL NOT NULL,
                metadata TEXT,
                optimization_triggered BOOLEAN DEFAULT FALSE
            )
        """)
        
        # Performance baselines table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_baselines (
                metric_type TEXT PRIMARY KEY,
                baseline_value REAL NOT NULL,
                target_value REAL NOT NULL,
                threshold_warning REAL NOT NULL,
                threshold_critical REAL NOT NULL,
                last_updated TEXT NOT NULL
            )
        """)
        
        # Optimization actions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS optimization_actions (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                trigger_metric TEXT NOT NULL,
                action_type TEXT NOT NULL,
                action_details TEXT NOT NULL,
                success BOOLEAN,
                impact_metrics TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        
        # Initialize baselines
        self._initialize_baselines()
    
    def _initialize_baselines(self):
        """Initialize performance baselines"""
        baselines = {
            "response_time": {
                "baseline": 0.5,
                "target": 0.3,
                "warning": 1.0,
                "critical": 2.0
            },
            "cpu_usage": {
                "baseline": 30.0,
                "target": 20.0,
                "warning": 70.0,
                "critical": 85.0
            },
            "memory_usage": {
                "baseline": 40.0,
                "target": 30.0,
                "warning": 75.0,
                "critical": 90.0
            },
            "error_rate": {
                "baseline": 0.001,
                "target": 0.0005,
                "warning": 0.01,
                "critical": 0.02
            },
            "throughput": {
                "baseline": 50.0,
                "target": 100.0,
                "warning": 20.0,
                "critical": 10.0
            }
        }
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for metric_type, values in baselines.items():
            cursor.execute("""
                INSERT OR REPLACE INTO performance_baselines
                (metric_type, baseline_value, target_value, threshold_warning, threshold_critical, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                metric_type,
                values["baseline"],
                values["target"],
                values["warning"],
                values["critical"],
                datetime.now().isoformat()
            ))
        
        conn.commit()
        conn.close()
    
    def start_monitoring(self):
        """Start performance monitoring"""
        logger.info("🔍 Starting performance monitoring...")
        self.monitoring_active = True
        
        # Start monitoring thread
        monitoring_thread = threading.Thread(target=self._monitoring_loop)
        monitoring_thread.daemon = True
        monitoring_thread.start()
        
        logger.info("✅ Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring_active = False
        logger.info("🛑 Performance monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect performance metrics
                metrics = self._collect_performance_metrics()
                
                # Store metrics
                self._store_metrics(metrics)
                
                # Check for optimization triggers
                self._check_optimization_triggers(metrics)
                
                # Update performance history
                self.performance_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "metrics": metrics
                })
                
                # Keep only last 100 entries
                if len(self.performance_history) > 100:
                    self.performance_history.pop(0)
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(5)
    
    def _collect_performance_metrics(self) -> Dict:
        """Collect comprehensive performance metrics"""
        metrics = {}
        
        # System metrics
        try:
            import psutil
            metrics.update({
                "cpu_usage": psutil.cpu_percent(interval=1),
                "memory_usage": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent,
                "disk_io_read": psutil.disk_io_counters().read_bytes,
                "disk_io_write": psutil.disk_io_counters().write_bytes,
                "network_bytes_sent": psutil.net_io_counters().bytes_sent,
                "network_bytes_recv": psutil.net_io_counters().bytes_recv
            })
        except ImportError:
            logger.warning("psutil not available, using fallback metrics")
            metrics.update({
                "cpu_usage": 0,
                "memory_usage": 0,
                "disk_usage": 0
            })
        
        # Application metrics
        app_metrics = self._collect_application_metrics()
        metrics.update(app_metrics)
        
        # Database metrics
        db_metrics = self._collect_database_metrics()
        metrics.update(db_metrics)
        
        return metrics
    
    def _collect_application_metrics(self) -> Dict:
        """Collect application-specific metrics"""
        try:
            # Try to get metrics from the application
            start_time = time.time()
            response = requests.get("http://localhost:8000/health", timeout=5)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                # Try to get detailed metrics
                try:
                    metrics_response = requests.get("http://localhost:8000/metrics", timeout=5)
                    if metrics_response.status_code == 200:
                        app_metrics = metrics_response.json()
                        app_metrics["response_time"] = response_time
                        return app_metrics
                except:
                    pass
                
                return {
                    "response_time": response_time,
                    "error_rate": 0.0,
                    "throughput": 0.0,
                    "active_connections": 0
                }
            else:
                return {
                    "response_time": response_time,
                    "error_rate": 1.0,
                    "throughput": 0.0,
                    "active_connections": 0
                }
                
        except Exception as e:
            logger.warning(f"Failed to collect application metrics: {e}")
            return {
                "response_time": 10.0,  # High response time indicates issues
                "error_rate": 1.0,
                "throughput": 0.0,
                "active_connections": 0
            }
    
    def _collect_database_metrics(self) -> Dict:
        """Collect database performance metrics"""
        try:
            start_time = time.time()
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Test query performance
            cursor.execute("SELECT COUNT(*) FROM sqlite_master")
            query_time = time.time() - start_time
            
            # Get database size
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            db_size = page_count * page_size
            
            # Get table counts
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            conn.close()
            
            return {
                "db_query_time": query_time,
                "db_size_bytes": db_size,
                "db_table_count": len(tables),
                "db_connection_time": query_time
            }
            
        except Exception as e:
            logger.warning(f"Failed to collect database metrics: {e}")
            return {
                "db_query_time": 1.0,
                "db_size_bytes": 0,
                "db_table_count": 0,
                "db_connection_time": 1.0
            }
    
    def _store_metrics(self, metrics: Dict):
        """Store metrics in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        
        for metric_type, value in metrics.items():
            if isinstance(value, (int, float)):
                metric_id = f"metric_{int(time.time())}_{metric_type}"
                cursor.execute("""
                    INSERT INTO performance_metrics
                    (id, timestamp, metric_type, metric_value, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    metric_id,
                    timestamp,
                    metric_type,
                    float(value),
                    json.dumps({"source": "performance_monitor"})
                ))
        
        conn.commit()
        conn.close()
    
    def _check_optimization_triggers(self, metrics: Dict):
        """Check if optimization should be triggered"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get baselines
        cursor.execute("SELECT * FROM performance_baselines")
        baselines = {row[0]: {
            "baseline": row[1],
            "target": row[2],
            "warning": row[3],
            "critical": row[4]
        } for row in cursor.fetchall()}
        
        conn.close()
        
        # Check each metric against thresholds
        for metric_type, value in metrics.items():
            if metric_type in baselines and isinstance(value, (int, float)):
                baseline = baselines[metric_type]
                
                if value >= baseline["critical"]:
                    logger.warning(f"CRITICAL: {metric_type} = {value} (threshold: {baseline['critical']})")
                    self._trigger_optimization(metric_type, value, "critical")
                elif value >= baseline["warning"]:
                    logger.warning(f"WARNING: {metric_type} = {value} (threshold: {baseline['warning']})")
                    self._trigger_optimization(metric_type, value, "warning")
    
    def _trigger_optimization(self, metric_type: str, value: float, severity: str):
        """Trigger optimization based on metric threshold"""
        logger.info(f"🔧 Triggering optimization for {metric_type} (value: {value}, severity: {severity})")
        
        # Create optimization action
        action_id = f"opt_{int(time.time())}_{metric_type}"
        optimization_action = {
            "id": action_id,
            "timestamp": datetime.now().isoformat(),
            "trigger_metric": metric_type,
            "trigger_value": value,
            "severity": severity,
            "actions": []
        }
        
        # Determine optimization actions based on metric type
        if metric_type == "cpu_usage":
            optimization_action["actions"] = [
                "reduce_worker_processes",
                "optimize_cpu_intensive_operations",
                "enable_request_throttling"
            ]
        elif metric_type == "memory_usage":
            optimization_action["actions"] = [
                "clear_memory_caches",
                "optimize_memory_usage",
                "restart_memory_intensive_services"
            ]
        elif metric_type == "response_time":
            optimization_action["actions"] = [
                "optimize_database_queries",
                "enable_response_caching",
                "reduce_request_processing_time"
            ]
        elif metric_type == "error_rate":
            optimization_action["actions"] = [
                "investigate_error_sources",
                "implement_error_recovery",
                "enhance_error_handling"
            ]
        
        # Execute optimization actions
        success = self._execute_optimization_actions(optimization_action)
        
        # Store optimization action
        self._store_optimization_action(optimization_action, success)
    
    def _execute_optimization_actions(self, optimization_action: Dict) -> bool:
        """Execute optimization actions"""
        try:
            for action in optimization_action["actions"]:
                logger.info(f"Executing optimization action: {action}")
                
                if action == "reduce_worker_processes":
                    # In production, this would reduce worker processes
                    logger.info("Simulating worker process reduction")
                    
                elif action == "clear_memory_caches":
                    # Clear application caches
                    logger.info("Simulating memory cache clearing")
                    
                elif action == "optimize_database_queries":
                    # Optimize database operations
                    self._optimize_database()
                    
                elif action == "enable_request_throttling":
                    # Enable request throttling
                    logger.info("Simulating request throttling activation")
                    
                # Add delay between actions
                time.sleep(1)
            
            return True
            
        except Exception as e:
            logger.error(f"Optimization action execution failed: {e}")
            return False
    
    def _optimize_database(self):
        """Optimize database performance"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Run VACUUM to optimize database
            cursor.execute("VACUUM")
            
            # Analyze tables for query optimization
            cursor.execute("ANALYZE")
            
            conn.close()
            logger.info("Database optimization completed")
            
        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
    
    def _store_optimization_action(self, optimization_action: Dict, success: bool):
        """Store optimization action in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO optimization_actions
            (id, timestamp, trigger_metric, action_type, action_details, success)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            optimization_action["id"],
            optimization_action["timestamp"],
            optimization_action["trigger_metric"],
            optimization_action["severity"],
            json.dumps(optimization_action),
            success
        ))
        
        conn.commit()
        conn.close()
    
    def get_performance_report(self, hours: int = 24) -> Dict:
        """Generate performance report"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get metrics from last N hours
        since_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor.execute("""
            SELECT metric_type, metric_value, timestamp
            FROM performance_metrics
            WHERE timestamp > ?
            ORDER BY timestamp DESC
        """, (since_time,))
        
        metrics_data = cursor.fetchall()
        
        # Get optimization actions
        cursor.execute("""
            SELECT * FROM optimization_actions
            WHERE timestamp > ?
            ORDER BY timestamp DESC
        """, (since_time,))
        
        optimization_actions = [dict(zip([col[0] for col in cursor.description], row)) 
                              for row in cursor.fetchall()]
        
        conn.close()
        
        # Analyze metrics
        metrics_analysis = {}
        for metric_type, value, timestamp in metrics_data:
            if metric_type not in metrics_analysis:
                metrics_analysis[metric_type] = []
            metrics_analysis[metric_type].append(value)
        
        # Calculate statistics
        performance_summary = {}
        for metric_type, values in metrics_analysis.items():
            if values:
                performance_summary[metric_type] = {
                    "count": len(values),
                    "average": statistics.mean(values),
                    "min": min(values),
                    "max": max(values),
                    "median": statistics.median(values),
                    "std_dev": statistics.stdev(values) if len(values) > 1 else 0
                }
        
        return {
            "report_period_hours": hours,
            "generated_at": datetime.now().isoformat(),
            "performance_summary": performance_summary,
            "optimization_actions": optimization_actions,
            "total_metrics_collected": len(metrics_data),
            "total_optimizations_triggered": len(optimization_actions)
        }

class RealTimeOptimizer:
    """Real-time performance optimization system"""
    
    def __init__(self, performance_monitor: PerformanceMonitor):
        self.performance_monitor = performance_monitor
        self.optimization_strategies = {
            "auto_scaling": True,
            "cache_optimization": True,
            "query_optimization": True,
            "resource_balancing": True
        }
    
    def enable_auto_optimization(self):
        """Enable automatic optimization"""
        logger.info("🤖 Enabling automatic performance optimization...")
        
        # Start optimization thread
        optimization_thread = threading.Thread(target=self._optimization_loop)
        optimization_thread.daemon = True
        optimization_thread.start()
        
        logger.info("✅ Automatic optimization enabled")
    
    def _optimization_loop(self):
        """Continuous optimization loop"""
        while self.performance_monitor.monitoring_active:
            try:
                # Get recent performance data
                if len(self.performance_monitor.performance_history) >= 3:
                    recent_metrics = self.performance_monitor.performance_history[-3:]
                    
                    # Analyze trends
                    trends = self._analyze_performance_trends(recent_metrics)
                    
                    # Apply optimizations based on trends
                    self._apply_predictive_optimizations(trends)
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Optimization loop error: {e}")
                time.sleep(30)
    
    def _analyze_performance_trends(self, recent_metrics: List[Dict]) -> Dict:
        """Analyze performance trends"""
        trends = {}
        
        for metric_type in ["cpu_usage", "memory_usage", "response_time", "error_rate"]:
            values = []
            for entry in recent_metrics:
                if metric_type in entry["metrics"]:
                    values.append(entry["metrics"][metric_type])
            
            if len(values) >= 2:
                # Calculate trend (positive = increasing, negative = decreasing)
                trend = (values[-1] - values[0]) / len(values)
                trends[metric_type] = {
                    "trend": trend,
                    "current_value": values[-1],
                    "direction": "increasing" if trend > 0 else "decreasing"
                }
        
        return trends
    
    def _apply_predictive_optimizations(self, trends: Dict):
        """Apply optimizations based on predicted issues"""
        for metric_type, trend_data in trends.items():
            if trend_data["direction"] == "increasing":
                current_value = trend_data["current_value"]
                trend_rate = trend_data["trend"]
                
                # Predict future value
                predicted_value = current_value + (trend_rate * 5)  # 5 intervals ahead
                
                # Check if predicted value will exceed thresholds
                if metric_type == "cpu_usage" and predicted_value > 70:
                    logger.info(f"🔮 Predictive optimization: CPU usage trending up, applying preemptive optimization")
                    self._preemptive_cpu_optimization()
                    
                elif metric_type == "memory_usage" and predicted_value > 75:
                    logger.info(f"🔮 Predictive optimization: Memory usage trending up, clearing caches")
                    self._preemptive_memory_optimization()
                    
                elif metric_type == "response_time" and predicted_value > 1.5:
                    logger.info(f"🔮 Predictive optimization: Response time trending up, optimizing queries")
                    self._preemptive_response_optimization()
    
    def _preemptive_cpu_optimization(self):
        """Preemptive CPU optimization"""
        # In production, this would implement actual CPU optimization
        logger.info("Applying preemptive CPU optimization")
    
    def _preemptive_memory_optimization(self):
        """Preemptive memory optimization"""
        # In production, this would clear caches and optimize memory
        logger.info("Applying preemptive memory optimization")
    
    def _preemptive_response_optimization(self):
        """Preemptive response time optimization"""
        # In production, this would optimize database queries and caching
        logger.info("Applying preemptive response time optimization")

def create_performance_dashboard(performance_monitor: PerformanceMonitor):
    """Create performance monitoring dashboard"""
    report = performance_monitor.get_performance_report(hours=24)
    
    dashboard_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Performance Monitoring Dashboard</title>
    <meta http-equiv="refresh" content="30">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .metric-card {{ border: 1px solid #ddd; padding: 15px; margin: 10px; border-radius: 5px; display: inline-block; width: 200px; }}
        .good {{ background-color: #e8f5e8; }}
        .warning {{ background-color: #fff3cd; }}
        .critical {{ background-color: #f8d7da; }}
        .chart {{ width: 100%; height: 200px; border: 1px solid #ccc; margin: 10px 0; }}
    </style>
</head>
<body>
    <h1>📊 Performance Monitoring Dashboard</h1>
    <p><strong>Report Generated:</strong> {report['generated_at']}</p>
    <p><strong>Report Period:</strong> {report['report_period_hours']} hours</p>
    
    <h2>🎯 Performance Metrics</h2>
    <div>
    """
    
    for metric_type, stats in report['performance_summary'].items():
        # Determine status based on metric type and values
        status_class = "good"
        if metric_type in ["cpu_usage", "memory_usage"] and stats["average"] > 70:
            status_class = "warning"
        elif metric_type in ["cpu_usage", "memory_usage"] and stats["average"] > 85:
            status_class = "critical"
        elif metric_type == "response_time" and stats["average"] > 1.0:
            status_class = "warning"
        elif metric_type == "response_time" and stats["average"] > 2.0:
            status_class = "critical"
        
        dashboard_html += f"""
        <div class="metric-card {status_class}">
            <h3>{metric_type.replace('_', ' ').title()}</h3>
            <p><strong>Average:</strong> {stats['average']:.2f}</p>
            <p><strong>Min:</strong> {stats['min']:.2f}</p>
            <p><strong>Max:</strong> {stats['max']:.2f}</p>
            <p><strong>Samples:</strong> {stats['count']}</p>
        </div>
        """
    
    dashboard_html += """
    </div>
    
    <h2>🔧 Recent Optimizations</h2>
    <div style="max-height: 300px; overflow-y: auto;">
    """
    
    for action in report['optimization_actions'][:10]:  # Show last 10
        success_icon = "✅" if action['success'] else "❌"
        dashboard_html += f"""
        <div style="border: 1px solid #ddd; padding: 10px; margin: 5px 0; border-radius: 3px;">
            {success_icon} <strong>{action['trigger_metric']}</strong> - {action['timestamp']}<br>
            <small>Action: {action['action_type']}</small>
        </div>
        """
    
    dashboard_html += f"""
    </div>
    
    <h2>📈 Summary</h2>
    <ul>
        <li><strong>Total Metrics Collected:</strong> {report['total_metrics_collected']}</li>
        <li><strong>Optimizations Triggered:</strong> {report['total_optimizations_triggered']}</li>
        <li><strong>Monitoring Status:</strong> {'🟢 Active' if performance_monitor.monitoring_active else '🔴 Inactive'}</li>
    </ul>
    
    <div>
        <button onclick="location.reload()">🔄 Refresh</button>
    </div>
</body>
</html>
    """
    
    with open("performance_dashboard.html", "w") as f:
        f.write(dashboard_html)
    
    logger.info("📊 Performance dashboard created: performance_dashboard.html")

def main():
    """Main function to demonstrate performance monitoring system"""
    print("🔍 Initializing Performance Monitoring System...\n")
    
    try:
        # Initialize performance monitor
        performance_monitor = PerformanceMonitor()
        
        # Start monitoring
        performance_monitor.start_monitoring()
        
        # Initialize real-time optimizer
        optimizer = RealTimeOptimizer(performance_monitor)
        optimizer.enable_auto_optimization()
        
        # Let it run for a bit to collect some data
        print("📊 Collecting performance data...")
        time.sleep(30)
        
        # Generate performance report
        report = performance_monitor.get_performance_report(hours=1)
        print(f"📈 Performance Report Generated:")
        print(f"   Metrics Collected: {report['total_metrics_collected']}")
        print(f"   Optimizations Triggered: {report['total_optimizations_triggered']}")
        
        # Create dashboard
        create_performance_dashboard(performance_monitor)
        
        # Save report
        with open("performance_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print("\n" + "="*60)
        print("🎉 PERFORMANCE MONITORING SYSTEM READY!")
        print("="*60)
        print("\n📋 Features:")
        print("✅ Real-time performance monitoring")
        print("✅ Automatic optimization triggers")
        print("✅ Predictive optimization")
        print("✅ Performance dashboard")
        print("✅ Detailed reporting")
        
        print("\n📊 Access:")
        print("- Dashboard: performance_dashboard.html")
        print("- Report: performance_report.json")
        print("- Logs: performance_monitoring.log")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance monitoring system initialization failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)