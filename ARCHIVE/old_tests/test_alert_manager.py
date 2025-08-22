#!/usr/bin/env python3
"""
Test Alert Manager
Tests for database alerting system functionality
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
from alert_manager import (
    AlertManager, AlertRule, Alert, EscalationRule, NotificationConfig,
    AlertSeverity, AlertStatus, NotificationChannel
)

def test_alert_manager():
    """Test alert manager basic functionality"""
    print("🧪 Testing Alert Manager...")
    
    # Create temporary test environment
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_alerts.db")
    
    try:
        # Initialize alert manager
        alert_manager = AlertManager(database_path=db_path)
        
        print("✅ Alert manager initialized successfully")
        
        # Test 1: Create alert rule
        rule = AlertRule(
            rule_id="test_response_time",
            name="High Response Time",
            description="Database response time is too high",
            metric_type="response_time",
            condition="greater_than",
            threshold=100.0,
            severity=AlertSeverity.WARNING,
            notification_channels=[NotificationChannel.LOG, NotificationChannel.CONSOLE]
        )
        
        success = alert_manager.create_alert_rule(rule)
        assert success
        assert "test_response_time" in alert_manager.alert_rules
        print("✅ Alert rule creation works")
        
        # Test 2: Update alert rule
        updates = {"threshold": 150.0, "severity": AlertSeverity.CRITICAL}
        success = alert_manager.update_alert_rule("test_response_time", updates)
        assert success
        assert alert_manager.alert_rules["test_response_time"].threshold == 150.0
        assert alert_manager.alert_rules["test_response_time"].severity == AlertSeverity.CRITICAL
        print("✅ Alert rule updates work")
        
        # Test 3: Evaluate metrics (should not trigger)
        metrics = {"response_time": 120.0}  # Below threshold
        alert_manager.evaluate_metrics(metrics)
        assert len(alert_manager.active_alerts) == 0
        print("✅ Metrics evaluation works (no trigger)")
        
        # Test 4: Evaluate metrics (should trigger)
        metrics = {"response_time": 200.0}  # Above threshold
        alert_manager.evaluate_metrics(metrics)
        assert len(alert_manager.active_alerts) == 1
        print("✅ Metrics evaluation works (trigger)")
        
        # Test 5: Get active alerts
        active_alerts = alert_manager.get_active_alerts()
        assert len(active_alerts) == 1
        alert = active_alerts[0]
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.status == AlertStatus.ACTIVE
        print("✅ Active alerts retrieval works")
        
        # Test 6: Acknowledge alert
        success = alert_manager.acknowledge_alert(alert.alert_id, "test_user")
        assert success
        assert alert.status == AlertStatus.ACKNOWLEDGED
        assert alert.acknowledged_by == "test_user"
        print("✅ Alert acknowledgment works")
        
        # Test 7: Resolve alert
        success = alert_manager.resolve_alert(alert.alert_id, "test_user")
        assert success
        assert alert.status == AlertStatus.RESOLVED
        assert alert.resolved_by == "test_user"
        assert len(alert_manager.active_alerts) == 0
        print("✅ Alert resolution works")
        
        # Test 8: Delete alert rule
        success = alert_manager.delete_alert_rule("test_response_time")
        assert success
        assert "test_response_time" not in alert_manager.alert_rules
        print("✅ Alert rule deletion works")
        
        # Test 9: Alert statistics
        stats = alert_manager.get_alert_statistics()
        assert "total_alerts" in stats
        assert "active_alerts" in stats
        print("✅ Alert statistics work")
        
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

def test_notification_system():
    """Test notification system"""
    print("\n🧪 Testing Notification System...")
    
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_notifications.db")
    
    try:
        alert_manager = AlertManager(database_path=db_path)
        
        # Create alert rule with multiple notification channels
        rule = AlertRule(
            rule_id="test_notifications",
            name="Test Notifications",
            description="Test notification system",
            metric_type="test_metric",
            condition="greater_than",
            threshold=50.0,
            severity=AlertSeverity.WARNING,
            notification_channels=[NotificationChannel.LOG, NotificationChannel.CONSOLE]
        )
        
        alert_manager.create_alert_rule(rule)
        
        # Start notification processing
        alert_manager.start_notification_processing()
        assert alert_manager.is_processing
        print("✅ Notification processing started")
        
        # Trigger alert
        metrics = {"test_metric": 75.0}
        alert_manager.evaluate_metrics(metrics)
        
        # Wait for notifications to be processed
        time.sleep(2)
        
        # Check that alert was created and notifications sent
        active_alerts = alert_manager.get_active_alerts()
        assert len(active_alerts) == 1
        
        alert = active_alerts[0]
        assert alert.notification_count > 0
        print("✅ Notifications were sent")
        
        # Stop notification processing
        alert_manager.stop_notification_processing()
        assert not alert_manager.is_processing
        print("✅ Notification processing stopped")
        
        return True
        
    except Exception as e:
        print(f"❌ Notification test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            if 'alert_manager' in locals():
                alert_manager.stop_notification_processing()
        except:
            pass
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

def test_rate_limiting():
    """Test alert rate limiting"""
    print("\n🧪 Testing Rate Limiting...")
    
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_rate_limiting.db")
    
    try:
        alert_manager = AlertManager(database_path=db_path)
        
        # Create rule with low rate limit
        rule = AlertRule(
            rule_id="test_rate_limit",
            name="Rate Limited Rule",
            description="Test rate limiting",
            metric_type="test_metric",
            condition="greater_than",
            threshold=50.0,
            severity=AlertSeverity.WARNING,
            max_alerts_per_hour=2,  # Low limit for testing
            cooldown_minutes=0  # No cooldown for this test
        )
        
        alert_manager.create_alert_rule(rule)
        
        # Trigger multiple alerts
        initial_count = len(alert_manager.active_alerts)
        
        for i in range(5):
            metrics = {"test_metric": 75.0 + i}  # Different values to create different alerts
            alert_manager.evaluate_metrics(metrics)
        
        # Should only create 2 alerts due to rate limiting
        final_count = len(alert_manager.active_alerts)
        alerts_created = final_count - initial_count
        
        assert alerts_created <= 2, f"Expected max 2 alerts, got {alerts_created}"
        print(f"✅ Rate limiting works: {alerts_created} alerts created (max 2)")
        
        return True
        
    except Exception as e:
        print(f"❌ Rate limiting test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

def test_cooldown_period():
    """Test alert cooldown period"""
    print("\n🧪 Testing Cooldown Period...")
    
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_cooldown.db")
    
    try:
        alert_manager = AlertManager(database_path=db_path)
        
        # Create rule with short cooldown
        rule = AlertRule(
            rule_id="test_cooldown",
            name="Cooldown Test Rule",
            description="Test cooldown period",
            metric_type="test_metric",
            condition="greater_than",
            threshold=50.0,
            severity=AlertSeverity.WARNING,
            cooldown_minutes=1,  # 1 minute cooldown
            max_alerts_per_hour=100  # High limit to test cooldown specifically
        )
        
        alert_manager.create_alert_rule(rule)
        
        # Trigger first alert
        metrics = {"test_metric": 75.0}
        alert_manager.evaluate_metrics(metrics)
        
        initial_count = len(alert_manager.active_alerts)
        assert initial_count == 1
        print("✅ First alert created")
        
        # Try to trigger another alert immediately (should be blocked by cooldown)
        metrics = {"test_metric": 80.0}
        alert_manager.evaluate_metrics(metrics)
        
        current_count = len(alert_manager.active_alerts)
        assert current_count == initial_count, "Second alert should be blocked by cooldown"
        print("✅ Cooldown period blocks duplicate alerts")
        
        return True
        
    except Exception as e:
        print(f"❌ Cooldown test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

def test_condition_evaluation():
    """Test different alert conditions"""
    print("\n🧪 Testing Condition Evaluation...")
    
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_conditions.db")
    
    try:
        alert_manager = AlertManager(database_path=db_path)
        
        # Test different conditions
        test_cases = [
            ("greater_than", 100.0, 150.0, True),   # 150 > 100
            ("greater_than", 100.0, 50.0, False),   # 50 > 100
            ("less_than", 100.0, 50.0, True),       # 50 < 100
            ("less_than", 100.0, 150.0, False),     # 150 < 100
            ("equals", 100.0, 100.0, True),         # 100 == 100
            ("equals", 100.0, 99.0, False),         # 99 == 100
            ("not_equals", 100.0, 99.0, True),      # 99 != 100
            ("not_equals", 100.0, 100.0, False),    # 100 != 100
        ]
        
        for i, (condition, threshold, value, expected) in enumerate(test_cases):
            result = alert_manager._evaluate_condition(value, condition, threshold)
            assert result == expected, f"Condition {condition} failed: {value} vs {threshold} = {result}, expected {expected}"
        
        print("✅ All condition evaluations work correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Condition evaluation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

def test_notification_configuration():
    """Test notification channel configuration"""
    print("\n🧪 Testing Notification Configuration...")
    
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_notification_config.db")
    
    try:
        alert_manager = AlertManager(database_path=db_path)
        
        # Test webhook configuration
        webhook_config = {
            "url": "https://example.com/webhook",
            "method": "POST",
            "headers": {"Authorization": "Bearer token123"},
            "timeout": 30
        }
        
        success = alert_manager.configure_notification_channel(
            NotificationChannel.WEBHOOK, 
            webhook_config
        )
        assert success
        
        # Verify configuration was stored
        config = alert_manager.notification_configs[NotificationChannel.WEBHOOK]
        assert config.enabled
        assert config.config["url"] == "https://example.com/webhook"
        assert config.config["headers"]["Authorization"] == "Bearer token123"
        print("✅ Webhook configuration works")
        
        # Test email configuration
        email_config = {
            "smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "username": "test@example.com",
            "password": "password123",
            "from_email": "alerts@example.com",
            "to_emails": ["admin@example.com", "ops@example.com"]
        }
        
        success = alert_manager.configure_notification_channel(
            NotificationChannel.EMAIL,
            email_config
        )
        assert success
        
        config = alert_manager.notification_configs[NotificationChannel.EMAIL]
        assert config.enabled
        assert config.config["smtp_server"] == "smtp.example.com"
        assert len(config.config["to_emails"]) == 2
        print("✅ Email configuration works")
        
        return True
        
    except Exception as e:
        print(f"❌ Notification configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

def test_data_persistence():
    """Test data persistence across restarts"""
    print("\n🧪 Testing Data Persistence...")
    
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_persistence.db")
    
    try:
        # Create first instance and add data
        alert_manager1 = AlertManager(database_path=db_path)
        
        rule = AlertRule(
            rule_id="persistent_rule",
            name="Persistent Rule",
            description="Test persistence",
            metric_type="test_metric",
            condition="greater_than",
            threshold=100.0,
            severity=AlertSeverity.CRITICAL
        )
        
        alert_manager1.create_alert_rule(rule)
        
        # Trigger an alert
        metrics = {"test_metric": 150.0}
        alert_manager1.evaluate_metrics(metrics)
        
        initial_rules_count = len(alert_manager1.alert_rules)
        initial_alerts_count = len(alert_manager1.active_alerts)
        
        assert initial_rules_count == 1
        assert initial_alerts_count == 1
        print("✅ Data created in first instance")
        
        # Create second instance (simulating restart)
        alert_manager2 = AlertManager(database_path=db_path)
        
        # Check that data was loaded
        assert len(alert_manager2.alert_rules) == initial_rules_count
        assert len(alert_manager2.active_alerts) == initial_alerts_count
        assert "persistent_rule" in alert_manager2.alert_rules
        print("✅ Data persisted across restart")
        
        # Verify rule details
        loaded_rule = alert_manager2.alert_rules["persistent_rule"]
        assert loaded_rule.name == "Persistent Rule"
        assert loaded_rule.threshold == 100.0
        assert loaded_rule.severity == AlertSeverity.CRITICAL
        print("✅ Rule details preserved correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Data persistence test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

if __name__ == "__main__":
    print("🚀 Starting Alert Manager Tests\n")
    
    success1 = test_alert_manager()
    success2 = test_notification_system()
    success3 = test_rate_limiting()
    success4 = test_cooldown_period()
    success5 = test_condition_evaluation()
    success6 = test_notification_configuration()
    success7 = test_data_persistence()
    
    if all([success1, success2, success3, success4, success5, success6, success7]):
        print("\n🎉 All tests completed successfully!")
        print("✅ Alert Manager is working correctly")
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)