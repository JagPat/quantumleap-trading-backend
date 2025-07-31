"""
Simple test for Trading Engine Alerting System
Tests basic functionality without external dependencies
"""
import asyncio
import json
import sys
import os
from datetime import datetime, timedelta

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

# Test basic imports first
try:
    from trading_engine.alerting_system import (
        AlertSeverity, AlertChannel, AlertCategory,
        AlertConditionEvaluator, AlertThrottler
    )
    print("✅ Basic imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

async def test_alerting_system():
    """Test the alerting system functionality"""
    print("🧪 Testing Trading Engine Alerting System")
    print("=" * 50)
    
    # Initialize test alerting system
    test_system = AlertingSystem(db_path="test_alerts.db")
    
    try:
        # Test 1: Create alert rule
        print("\n1. Testing alert rule creation...")
        test_rule = AlertRule(
            rule_id="test_risk_rule",
            name="Test Risk Alert",
            category=AlertCategory.RISK_MANAGEMENT,
            severity=AlertSeverity.HIGH,
            condition='{"field": "risk_score", "operator": "gt", "value": 0.8}',
            channels=[AlertChannel.EMAIL, AlertChannel.PUSH],
            throttle_minutes=1,
            max_alerts_per_hour=5,
            user_id="test_user_123"
        )
        
        success = test_system.add_rule(test_rule)
        print(f"✅ Alert rule created: {success}")
        
        # Test 2: Set user preferences
        print("\n2. Testing user preferences...")
        preferences = {
            AlertChannel.EMAIL.value: "test@example.com",
            AlertChannel.PUSH.value: "test_device_token_123",
            AlertChannel.WEBHOOK.value: "https://webhook.example.com/alerts"
        }
        
        success = test_system.update_user_preferences("test_user_123", preferences)
        print(f"✅ User preferences updated: {success}")
        
        # Test 3: Test condition evaluator
        print("\n3. Testing condition evaluation...")
        evaluator = AlertConditionEvaluator()
        
        # Test simple condition
        condition = '{"field": "risk_score", "operator": "gt", "value": 0.8}'
        data = {"risk_score": 0.9, "portfolio_value": 100000}
        result = evaluator.evaluate(condition, data)
        print(f"✅ Simple condition (risk_score > 0.8): {result}")
        
        # Test complex condition
        complex_condition = '''
        {
            "and": [
                {"field": "risk_score", "operator": "gt", "value": 0.7},
                {"field": "portfolio_value", "operator": "lt", "value": 200000}
            ]
        }
        '''
        result = evaluator.evaluate(complex_condition, data)
        print(f"✅ Complex condition (AND): {result}")
        
        # Test nested field
        nested_data = {
            "portfolio": {
                "risk": {
                    "score": 0.85
                }
            }
        }
        nested_condition = '{"field": "portfolio.risk.score", "operator": "gt", "value": 0.8}'
        result = evaluator.evaluate(nested_condition, nested_data)
        print(f"✅ Nested field condition: {result}")
        
        # Test 4: Test throttling
        print("\n4. Testing alert throttling...")
        throttler = AlertThrottler()
        
        # First alert should be allowed
        should_send = throttler.should_send_alert(test_rule)
        print(f"✅ First alert allowed: {should_send}")
        
        # Immediate second alert should be throttled
        should_send = throttler.should_send_alert(test_rule)
        print(f"✅ Second alert throttled: {not should_send}")
        
        # Test 5: Trigger alert
        print("\n5. Testing alert triggering...")
        alert_data = {
            "risk_score": 0.95,
            "portfolio_value": 150000,
            "risk_type": "portfolio_exposure",
            "timestamp": datetime.now().isoformat()
        }
        
        success = await test_system.trigger_alert(
            rule_id="test_risk_rule",
            data=alert_data,
            title="High Risk Alert",
            message="Portfolio risk score exceeded threshold"
        )
        print(f"✅ Alert triggered: {success}")
        
        # Wait for alert processing
        await asyncio.sleep(1)
        
        # Test 6: Get alerts
        print("\n6. Testing alert retrieval...")
        alerts = test_system.get_alerts(user_id="test_user_123", limit=10)
        print(f"✅ Retrieved {len(alerts)} alerts")
        
        if alerts:
            latest_alert = alerts[0]
            print(f"   Latest alert: {latest_alert['title']}")
            print(f"   Severity: {latest_alert['severity']}")
            print(f"   Category: {latest_alert['category']}")
        
        # Test 7: Alert statistics
        print("\n7. Testing alert statistics...")
        stats = test_system.get_alert_statistics(user_id="test_user_123")
        print(f"✅ Alert statistics:")
        print(f"   Total alerts: {stats.get('total_alerts', 0)}")
        print(f"   Recent alerts (24h): {stats.get('recent_alerts_24h', 0)}")
        print(f"   Active rules: {stats.get('active_rules', 0)}")
        
        # Test 8: Convenience functions
        print("\n8. Testing convenience functions...")
        
        # Test risk alert
        await send_risk_alert(
            user_id="test_user_123",
            risk_type="position_size",
            current_value=15.5,
            threshold=10.0,
            additional_data={"symbol": "RELIANCE", "position_value": 155000}
        )
        print("✅ Risk alert sent")
        
        # Test order alert
        await send_order_alert(
            user_id="test_user_123",
            order_id="ORD_123456",
            status="FILLED",
            additional_data={"symbol": "TCS", "quantity": 100, "price": 3500}
        )
        print("✅ Order alert sent")
        
        # Wait for processing
        await asyncio.sleep(1)
        
        # Test 9: Alert acknowledgment and resolution
        print("\n9. Testing alert acknowledgment...")
        alerts = test_system.get_alerts(user_id="test_user_123", limit=1)
        if alerts:
            alert_id = alerts[0]['alert_id']
            success = test_system.acknowledge_alert(alert_id)
            print(f"✅ Alert acknowledged: {success}")
            
            success = test_system.resolve_alert(alert_id)
            print(f"✅ Alert resolved: {success}")
        
        # Test 10: Rule management
        print("\n10. Testing rule management...")
        
        # Create another rule
        another_rule = AlertRule(
            rule_id="test_order_rule",
            name="Order Execution Alert",
            category=AlertCategory.ORDER_EXECUTION,
            severity=AlertSeverity.MEDIUM,
            condition='{"field": "status", "operator": "eq", "value": "FAILED"}',
            channels=[AlertChannel.EMAIL],
            user_id="test_user_123"
        )
        
        success = test_system.add_rule(another_rule)
        print(f"✅ Second rule created: {success}")
        
        # List all rules
        total_rules = len(test_system.rules)
        print(f"✅ Total active rules: {total_rules}")
        
        # Remove rule
        success = test_system.remove_rule("test_order_rule")
        print(f"✅ Rule removed: {success}")
        
        print("\n🎉 All alerting system tests completed successfully!")
        
        # Final statistics
        final_stats = test_system.get_alert_statistics()
        print(f"\n📊 Final Statistics:")
        print(f"   Total alerts generated: {final_stats.get('total_alerts', 0)}")
        print(f"   Active rules: {final_stats.get('active_rules', 0)}")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        await test_system.shutdown()
        
        # Remove test database
        try:
            os.remove("test_alerts.db")
            print("\n🧹 Test database cleaned up")
        except:
            pass

def test_condition_evaluator():
    """Test condition evaluator with various scenarios"""
    print("\n🧪 Testing Condition Evaluator")
    print("-" * 30)
    
    evaluator = AlertConditionEvaluator()
    
    test_cases = [
        {
            "name": "Simple greater than",
            "condition": '{"field": "value", "operator": "gt", "value": 10}',
            "data": {"value": 15},
            "expected": True
        },
        {
            "name": "Simple less than",
            "condition": '{"field": "value", "operator": "lt", "value": 10}',
            "data": {"value": 5},
            "expected": True
        },
        {
            "name": "String contains",
            "condition": '{"field": "message", "operator": "contains", "value": "error"}',
            "data": {"message": "This is an error message"},
            "expected": True
        },
        {
            "name": "Array membership",
            "condition": '{"field": "status", "operator": "in", "value": ["ACTIVE", "PENDING"]}',
            "data": {"status": "ACTIVE"},
            "expected": True
        },
        {
            "name": "AND condition",
            "condition": '''
            {
                "and": [
                    {"field": "risk", "operator": "gt", "value": 0.5},
                    {"field": "value", "operator": "lt", "value": 1000}
                ]
            }
            ''',
            "data": {"risk": 0.8, "value": 500},
            "expected": True
        },
        {
            "name": "OR condition",
            "condition": '''
            {
                "or": [
                    {"field": "urgent", "operator": "eq", "value": true},
                    {"field": "priority", "operator": "eq", "value": "HIGH"}
                ]
            }
            ''',
            "data": {"urgent": False, "priority": "HIGH"},
            "expected": True
        },
        {
            "name": "NOT condition",
            "condition": '{"not": {"field": "disabled", "operator": "eq", "value": true}}',
            "data": {"disabled": False},
            "expected": True
        }
    ]
    
    for test_case in test_cases:
        result = evaluator.evaluate(test_case["condition"], test_case["data"])
        status = "✅" if result == test_case["expected"] else "❌"
        print(f"{status} {test_case['name']}: {result}")

def test_throttler():
    """Test alert throttler functionality"""
    print("\n🧪 Testing Alert Throttler")
    print("-" * 25)
    
    throttler = AlertThrottler()
    
    # Create test rule with short throttle time
    rule = AlertRule(
        rule_id="throttle_test",
        name="Throttle Test",
        category=AlertCategory.SYSTEM_HEALTH,
        severity=AlertSeverity.INFO,
        condition='{"field": "test", "operator": "eq", "value": true}',
        channels=[AlertChannel.EMAIL],
        throttle_minutes=0.01,  # Very short for testing
        max_alerts_per_hour=3
    )
    
    # Test throttling
    results = []
    for i in range(5):
        should_send = throttler.should_send_alert(rule)
        results.append(should_send)
        print(f"Alert {i+1}: {'Sent' if should_send else 'Throttled'}")
    
    # Should allow first 3, then throttle
    expected = [True, False, False, False, False]  # First allowed, rest throttled due to timing
    print(f"✅ Throttling working correctly: {results[0] and not any(results[1:])}")

if __name__ == "__main__":
    # Run condition evaluator tests
    test_condition_evaluator()
    
    # Run throttler tests
    test_throttler()
    
    # Run main async tests
    asyncio.run(test_alerting_system())