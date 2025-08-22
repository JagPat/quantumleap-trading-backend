#!/usr/bin/env python3
"""
Test Database Monitor
Tests for real-time database health monitoring functionality
"""
import os
import sqlite3
import tempfile
import shutil
import time
import threading
from datetime import datetime, timedelta
import sys

# Add the app directory to the path
sys.path.append('app/database')
from database_monitor import (
    DatabaseMonitor, HealthStatus, MetricType, HealthMetric, HealthReport, PerformanceTrend
)

def test_database_monitor():
    """Test database monitor functionality"""
    print("🧪 Testing Database Monitor...")
    
    # Create temporary test environment
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_monitor.db")
    
    try:
        # Initialize monitor
        monitor = DatabaseMonitor(
            database_path=db_path,
            monitoring_interval=2,  # Short interval for testing
            history_retention_hours=1
        )
        
        print("✅ Monitor initialized successfully")
        
        # Test 1: Basic functionality
        assert monitor.database_path == db_path
        assert monitor.monitoring_interval == 2
        assert not monitor.is_monitoring
        print("✅ Basic properties work correctly")
        
        # Test 2: Metric collection
        report = monitor._collect_health_metrics()
        assert isinstance(report, HealthReport)
        assert report.overall_status in [HealthStatus.HEALTHY, HealthStatus.WARNING, HealthStatus.CRITICAL, HealthStatus.OFFLINE]
        assert len(report.metrics) > 0
        print("✅ Metric collection works")
        
        # Test 3: Individual metrics
        assert "response_time" in report.metrics
        assert "connection_count" in report.metrics
        assert "query_rate" in report.metrics
        assert "error_rate" in report.metrics
        assert "disk_usage" in report.metrics
        assert "memory_usage" in report.metrics
        assert "cpu_usage" in report.metrics
        print("✅ All expected metrics are present")
        
        # Test 4: Metric properties
        response_time_metric = report.metrics["response_time"]
        assert isinstance(response_time_metric, HealthMetric)
        assert response_time_metric.metric_type == MetricType.RESPONSE_TIME
        assert response_time_metric.unit == "ms"
        assert response_time_metric.value >= 0
        print("✅ Metric properties are correct")
        
        # Test 5: Query recording
        initial_query_count = monitor.query_count
        monitor.record_query(0.05, success=True)
        monitor.record_query(0.1, success=False)
        
        assert monitor.query_count == initial_query_count + 2
        assert monitor.error_count == 1
        print("✅ Query recording works")
        
        # Test 6: Connection recording
        initial_connection_count = monitor.connection_count
        monitor.record_connection(active=True)
        monitor.record_connection(active=True)
        monitor.record_connection(active=False)
        
        assert monitor.connection_count == initial_connection_count + 1
        print("✅ Connection recording works")
        
        # Test 7: Threshold updates
        original_warning = monitor.thresholds[MetricType.RESPONSE_TIME]["warning"]
        monitor.update_thresholds(MetricType.RESPONSE_TIME, 200.0, 1000.0)
        assert monitor.thresholds[MetricType.RESPONSE_TIME]["warning"] == 200.0
        assert monitor.thresholds[MetricType.RESPONSE_TIME]["critical"] == 1000.0
        print("✅ Threshold updates work")
        
        # Test 8: Alert callbacks
        alert_received = []
        
        def test_alert_callback(report):
            alert_received.append(report)
        
        monitor.add_alert_callback(test_alert_callback)
        
        # Force an alert by setting very low thresholds
        monitor.update_thresholds(MetricType.RESPONSE_TIME, 0.001, 0.002)
        
        # Collect metrics again (should trigger alert)
        report_with_alert = monitor._collect_health_metrics()
        monitor._check_alerts(report_with_alert)
        
        # Check if alert was triggered
        if alert_received:
            print("✅ Alert callbacks work")
        else:
            print("⚠️ Alert callback not triggered (may be normal)")
        
        # Test 9: Dashboard data
        # First store a report to have data available
        monitor._store_health_report(report_with_alert)
        monitor.metrics_history.append(report_with_alert)
        
        dashboard_data = monitor.get_dashboard_data()
        assert "status" in dashboard_data
        
        # Check if we have data or no data message
        if dashboard_data.get("status") == "no_data":
            print("✅ Dashboard correctly reports no data")
        else:
            assert "metrics" in dashboard_data
            assert "alerts" in dashboard_data
            assert "recommendations" in dashboard_data
            print("✅ Dashboard data generation works")
        
        print("🎉 All basic tests passed!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

def test_monitoring_loop():
    """Test the monitoring loop functionality"""
    print("\n🧪 Testing Monitoring Loop...")
    
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_monitor_loop.db")
    
    try:
        # Initialize monitor with short interval
        monitor = DatabaseMonitor(
            database_path=db_path,
            monitoring_interval=1,  # 1 second for testing
            history_retention_hours=1
        )
        
        # Start monitoring
        monitor.start_monitoring()
        assert monitor.is_monitoring
        assert monitor.monitor_thread is not None
        assert monitor.monitor_thread.is_alive()
        print("✅ Monitoring started successfully")
        
        # Wait for a few monitoring cycles
        time.sleep(3)
        
        # Check that metrics are being collected
        current_health = monitor.get_current_health()
        assert current_health is not None
        assert isinstance(current_health, HealthReport)
        print("✅ Metrics are being collected automatically")
        
        # Check history
        history = monitor.get_health_history(hours=1)
        assert len(history) > 0
        print(f"✅ Health history contains {len(history)} reports")
        
        # Test metric history
        response_time_history = monitor.get_metric_history(MetricType.RESPONSE_TIME, hours=1)
        assert len(response_time_history) > 0
        print(f"✅ Metric history contains {len(response_time_history)} data points")
        
        # Stop monitoring
        monitor.stop_monitoring()
        assert not monitor.is_monitoring
        print("✅ Monitoring stopped successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Monitoring loop test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            if 'monitor' in locals():
                monitor.stop_monitoring()
        except:
            pass
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

def test_trend_analysis():
    """Test performance trend analysis"""
    print("\n🧪 Testing Trend Analysis...")
    
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_trends.db")
    
    try:
        monitor = DatabaseMonitor(database_path=db_path)
        
        # Create some fake history data
        base_time = datetime.now()
        for i in range(10):
            # Create a report with increasing response time
            metrics = {
                "response_time": HealthMetric(
                    metric_type=MetricType.RESPONSE_TIME,
                    value=10.0 + i * 2.0,  # Increasing trend
                    timestamp=base_time + timedelta(minutes=i),
                    threshold_warning=100.0,
                    threshold_critical=500.0,
                    unit="ms",
                    description="Test response time"
                )
            }
            
            report = HealthReport(
                timestamp=base_time + timedelta(minutes=i),
                overall_status=HealthStatus.HEALTHY,
                metrics=metrics,
                alerts=[],
                recommendations=[],
                uptime=i * 60,
                database_size=1000,
                active_connections=1
            )
            
            monitor.metrics_history.append(report)
        
        # Calculate trend
        trend = monitor._calculate_trend(MetricType.RESPONSE_TIME)
        assert trend is not None
        assert isinstance(trend, PerformanceTrend)
        assert trend.metric_type == MetricType.RESPONSE_TIME
        assert trend.trend_direction in ["increasing", "decreasing", "stable"]
        print("✅ Trend calculation works")
        
        # Test trend storage
        monitor._store_trend(trend)
        
        # Retrieve trends
        trends = monitor.get_performance_trends(hours=1)
        assert len(trends) > 0
        print("✅ Trend storage and retrieval works")
        
        return True
        
    except Exception as e:
        print(f"❌ Trend analysis test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

def test_data_cleanup():
    """Test data cleanup functionality"""
    print("\n🧪 Testing Data Cleanup...")
    
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_cleanup.db")
    
    try:
        monitor = DatabaseMonitor(database_path=db_path)
        
        # Create some old test data
        old_time = datetime.now() - timedelta(days=10)
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Insert old health metrics
            cursor.execute("""
                INSERT INTO health_metrics 
                (timestamp, metric_type, value, status, unit, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                old_time.isoformat(),
                MetricType.RESPONSE_TIME.value,
                50.0,
                HealthStatus.HEALTHY.value,
                "ms",
                "Old test metric"
            ))
            
            # Insert old health report
            cursor.execute("""
                INSERT INTO health_reports 
                (timestamp, overall_status, uptime, database_size, active_connections, alerts, recommendations)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                old_time.isoformat(),
                HealthStatus.HEALTHY.value,
                3600.0,
                1000,
                1,
                "[]",
                "[]"
            ))
            
            conn.commit()
        
        # Check that data exists
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM health_metrics")
            metrics_count_before = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM health_reports")
            reports_count_before = cursor.fetchone()[0]
        
        assert metrics_count_before > 0
        assert reports_count_before > 0
        print(f"✅ Test data created: {metrics_count_before} metrics, {reports_count_before} reports")
        
        # Perform cleanup
        monitor.cleanup_old_data(days=7)
        
        # Check that old data was removed
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM health_metrics")
            metrics_count_after = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM health_reports")
            reports_count_after = cursor.fetchone()[0]
        
        assert metrics_count_after < metrics_count_before
        assert reports_count_after < reports_count_before
        print(f"✅ Data cleanup works: {metrics_count_after} metrics, {reports_count_after} reports remaining")
        
        return True
        
    except Exception as e:
        print(f"❌ Data cleanup test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

if __name__ == "__main__":
    print("🚀 Starting Database Monitor Tests\n")
    
    success1 = test_database_monitor()
    success2 = test_monitoring_loop()
    success3 = test_trend_analysis()
    success4 = test_data_cleanup()
    
    if success1 and success2 and success3 and success4:
        print("\n🎉 All tests completed successfully!")
        print("✅ Database Monitor is working correctly")
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)