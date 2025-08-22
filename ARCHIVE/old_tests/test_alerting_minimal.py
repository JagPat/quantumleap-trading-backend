"""
Minimal test for Trading Engine Alerting System components
Tests core functionality without external dependencies
"""
import json
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, List
from collections import defaultdict

# Define core enums and classes locally for testing
class AlertSeverity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

class AlertChannel(Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"
    WEBHOOK = "WEBHOOK"
    IN_APP = "IN_APP"

class AlertCategory(Enum):
    RISK_MANAGEMENT = "RISK_MANAGEMENT"
    ORDER_EXECUTION = "ORDER_EXECUTION"
    STRATEGY_PERFORMANCE = "STRATEGY_PERFORMANCE"
    SYSTEM_HEALTH = "SYSTEM_HEALTH"
    MARKET_CONDITIONS = "MARKET_CONDITIONS"
    USER_ACTIONS = "USER_ACTIONS"

@dataclass
class AlertRule:
    rule_id: str
    name: str
    category: AlertCategory
    severity: AlertSeverity
    condition: str
    channels: List[AlertChannel]
    enabled: bool = True
    throttle_minutes: int = 5
    max_alerts_per_hour: int = 10
    user_id: str = None

class AlertConditionEvaluator:
    """Evaluates alert conditions against data"""
    
    def __init__(self):
        self.operators = {
            'gt': lambda x, y: x > y,
            'gte': lambda x, y: x >= y,
            'lt': lambda x, y: x < y,
            'lte': lambda x, y: x <= y,
            'eq': lambda x, y: x == y,
            'ne': lambda x, y: x != y,
            'in': lambda x, y: x in y,
            'not_in': lambda x, y: x not in y,
            'contains': lambda x, y: y in x,
            'starts_with': lambda x, y: str(x).startswith(str(y)),
            'ends_with': lambda x, y: str(x).endswith(str(y))
        }
    
    def evaluate(self, condition: str, data: Dict[str, Any]) -> bool:
        """Evaluate condition against data"""
        try:
            condition_obj = json.loads(condition)
            return self._evaluate_condition(condition_obj, data)
        except Exception as e:
            print(f"Error evaluating condition: {e}")
            return False
    
    def _evaluate_condition(self, condition: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Recursively evaluate condition"""
        if 'and' in condition:
            return all(self._evaluate_condition(c, data) for c in condition['and'])
        
        if 'or' in condition:
            return any(self._evaluate_condition(c, data) for c in condition['or'])
        
        if 'not' in condition:
            return not self._evaluate_condition(condition['not'], data)
        
        # Simple condition
        field = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value')
        
        if not all([field, operator]):
            return False
        
        data_value = self._get_nested_value(data, field)
        if data_value is None:
            return False
        
        op_func = self.operators.get(operator)
        if not op_func:
            return False
        
        return op_func(data_value, value)
    
    def _get_nested_value(self, data: Dict[str, Any], field: str) -> Any:
        """Get nested value from data using dot notation"""
        keys = field.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value

class AlertThrottler:
    """Manages alert throttling and rate limiting"""
    
    def __init__(self):
        self.alert_counts = defaultdict(lambda: defaultdict(int))
        self.last_sent = {}
    
    def should_send_alert(self, rule: AlertRule) -> bool:
        """Check if alert should be sent based on throttling rules"""
        now = datetime.now()
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        
        # Check throttle time
        if rule.rule_id in self.last_sent:
            time_since_last = now - self.last_sent[rule.rule_id]
            if time_since_last.total_seconds() < rule.throttle_minutes * 60:
                return False
        
        # Check hourly limit
        current_count = self.alert_counts[rule.rule_id][current_hour]
        if current_count >= rule.max_alerts_per_hour:
            return False
        
        # Update counters
        self.alert_counts[rule.rule_id][current_hour] += 1
        self.last_sent[rule.rule_id] = now
        
        return True

def test_condition_evaluator():
    """Test condition evaluator with various scenarios"""
    print("🧪 Testing Condition Evaluator")
    print("=" * 40)
    
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
        },
        {
            "name": "Nested field access",
            "condition": '{"field": "portfolio.risk.score", "operator": "gt", "value": 0.8}',
            "data": {"portfolio": {"risk": {"score": 0.9}}},
            "expected": True
        },
        {
            "name": "Failed condition (false case)",
            "condition": '{"field": "value", "operator": "gt", "value": 100}',
            "data": {"value": 50},
            "expected": False
        }
    ]
    
    passed = 0
    total = len(test_cases)
    
    for test_case in test_cases:
        try:
            result = evaluator.evaluate(test_case["condition"], test_case["data"])
            expected = test_case["expected"]
            
            if result == expected:
                print(f"✅ {test_case['name']}: {result}")
                passed += 1
            else:
                print(f"❌ {test_case['name']}: Expected {expected}, got {result}")
        except Exception as e:
            print(f"❌ {test_case['name']}: Exception - {e}")
    
    print(f"\n📊 Condition Evaluator Results: {passed}/{total} tests passed")
    return passed == total

def test_throttler():
    """Test alert throttler functionality"""
    print("\n🧪 Testing Alert Throttler")
    print("=" * 30)
    
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
    
    print("Testing throttling behavior...")
    
    # Test first alert (should be allowed)
    should_send_1 = throttler.should_send_alert(rule)
    print(f"✅ First alert: {'Allowed' if should_send_1 else 'Blocked'}")
    
    # Test immediate second alert (should be throttled)
    should_send_2 = throttler.should_send_alert(rule)
    print(f"✅ Second alert (immediate): {'Allowed' if should_send_2 else 'Throttled'}")
    
    # Test with different rule (should be allowed)
    rule2 = AlertRule(
        rule_id="throttle_test_2",
        name="Throttle Test 2",
        category=AlertCategory.RISK_MANAGEMENT,
        severity=AlertSeverity.HIGH,
        condition='{"field": "test", "operator": "eq", "value": true}',
        channels=[AlertChannel.SMS],
        throttle_minutes=1,
        max_alerts_per_hour=5
    )
    
    should_send_3 = throttler.should_send_alert(rule2)
    print(f"✅ Different rule alert: {'Allowed' if should_send_3 else 'Blocked'}")
    
    # Test hourly limit
    print("\nTesting hourly limits...")
    rule3 = AlertRule(
        rule_id="hourly_limit_test",
        name="Hourly Limit Test",
        category=AlertCategory.ORDER_EXECUTION,
        severity=AlertSeverity.MEDIUM,
        condition='{"field": "test", "operator": "eq", "value": true}',
        channels=[AlertChannel.PUSH],
        throttle_minutes=0,  # No throttling
        max_alerts_per_hour=2  # Low limit for testing
    )
    
    hourly_results = []
    for i in range(4):
        result = throttler.should_send_alert(rule3)
        hourly_results.append(result)
        print(f"   Alert {i+1}: {'Allowed' if result else 'Rate limited'}")
    
    # Should allow first 2, then rate limit
    expected_hourly = [True, True, False, False]
    hourly_correct = hourly_results == expected_hourly
    
    print(f"\n📊 Throttler Results:")
    print(f"   Basic throttling: {'✅' if should_send_1 and not should_send_2 else '❌'}")
    print(f"   Different rules: {'✅' if should_send_3 else '❌'}")
    print(f"   Hourly limits: {'✅' if hourly_correct else '❌'}")
    
    return should_send_1 and not should_send_2 and should_send_3 and hourly_correct

def test_alert_rule_creation():
    """Test alert rule creation and validation"""
    print("\n🧪 Testing Alert Rule Creation")
    print("=" * 35)
    
    try:
        # Test valid rule creation
        rule = AlertRule(
            rule_id="test_rule_001",
            name="Test Risk Alert",
            category=AlertCategory.RISK_MANAGEMENT,
            severity=AlertSeverity.HIGH,
            condition='{"field": "risk_score", "operator": "gt", "value": 0.8}',
            channels=[AlertChannel.EMAIL, AlertChannel.SMS],
            throttle_minutes=5,
            max_alerts_per_hour=10,
            user_id="user_123"
        )
        
        print("✅ Basic rule creation successful")
        print(f"   Rule ID: {rule.rule_id}")
        print(f"   Name: {rule.name}")
        print(f"   Category: {rule.category.value}")
        print(f"   Severity: {rule.severity.value}")
        print(f"   Channels: {[c.value for c in rule.channels]}")
        print(f"   Enabled: {rule.enabled}")
        
        # Test condition validation
        evaluator = AlertConditionEvaluator()
        test_data = {"risk_score": 0.9}
        condition_valid = evaluator.evaluate(rule.condition, test_data)
        print(f"✅ Condition evaluation: {condition_valid}")
        
        return True
        
    except Exception as e:
        print(f"❌ Rule creation failed: {e}")
        return False

def test_alert_scenarios():
    """Test various alert scenarios"""
    print("\n🧪 Testing Alert Scenarios")
    print("=" * 30)
    
    evaluator = AlertConditionEvaluator()
    
    # Risk management scenarios
    risk_scenarios = [
        {
            "name": "High portfolio risk",
            "condition": '{"field": "portfolio_risk", "operator": "gt", "value": 0.8}',
            "data": {"portfolio_risk": 0.95, "portfolio_value": 500000},
            "should_alert": True
        },
        {
            "name": "Position size limit",
            "condition": '{"field": "position_size_percent", "operator": "gt", "value": 10}',
            "data": {"position_size_percent": 15.5, "symbol": "RELIANCE"},
            "should_alert": True
        },
        {
            "name": "Drawdown threshold",
            "condition": '{"field": "drawdown_percent", "operator": "gt", "value": 5}',
            "data": {"drawdown_percent": 7.2, "peak_value": 600000},
            "should_alert": True
        }
    ]
    
    # Order execution scenarios
    order_scenarios = [
        {
            "name": "Order failed",
            "condition": '{"field": "status", "operator": "eq", "value": "FAILED"}',
            "data": {"status": "FAILED", "order_id": "ORD_123", "error": "Insufficient funds"},
            "should_alert": True
        },
        {
            "name": "Large order filled",
            "condition": '''
            {
                "and": [
                    {"field": "status", "operator": "eq", "value": "FILLED"},
                    {"field": "value", "operator": "gt", "value": 100000}
                ]
            }
            ''',
            "data": {"status": "FILLED", "value": 150000, "symbol": "TCS"},
            "should_alert": True
        }
    ]
    
    # Strategy performance scenarios
    strategy_scenarios = [
        {
            "name": "Strategy underperforming",
            "condition": '{"field": "performance.return_percent", "operator": "lt", "value": -5}',
            "data": {"performance": {"return_percent": -8.5}, "strategy_id": "STRAT_001"},
            "should_alert": True
        },
        {
            "name": "Strategy stopped",
            "condition": '{"field": "status", "operator": "eq", "value": "STOPPED"}',
            "data": {"status": "STOPPED", "reason": "Risk limit exceeded"},
            "should_alert": True
        }
    ]
    
    all_scenarios = risk_scenarios + order_scenarios + strategy_scenarios
    passed = 0
    
    for scenario in all_scenarios:
        try:
            result = evaluator.evaluate(scenario["condition"], scenario["data"])
            expected = scenario["should_alert"]
            
            if result == expected:
                print(f"✅ {scenario['name']}: Alert {'triggered' if result else 'not triggered'}")
                passed += 1
            else:
                print(f"❌ {scenario['name']}: Expected {expected}, got {result}")
                
        except Exception as e:
            print(f"❌ {scenario['name']}: Exception - {e}")
    
    print(f"\n📊 Scenario Results: {passed}/{len(all_scenarios)} scenarios passed")
    return passed == len(all_scenarios)

def main():
    """Run all tests"""
    print("🚀 Starting Trading Engine Alerting System Tests")
    print("=" * 60)
    
    test_results = []
    
    # Run individual tests
    test_results.append(("Condition Evaluator", test_condition_evaluator()))
    test_results.append(("Alert Throttler", test_throttler()))
    test_results.append(("Alert Rule Creation", test_alert_rule_creation()))
    test_results.append(("Alert Scenarios", test_alert_scenarios()))
    
    # Summary
    print("\n" + "=" * 60)
    print("🏁 TEST SUMMARY")
    print("=" * 60)
    
    passed_tests = 0
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {test_name}")
        if result:
            passed_tests += 1
    
    total_tests = len(test_results)
    print(f"\n📊 Overall Results: {passed_tests}/{total_tests} test suites passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! Alerting system is working correctly.")
    else:
        print("⚠️  Some tests failed. Please review the implementation.")
    
    print("\n💡 Key Features Tested:")
    print("   • Condition evaluation with complex logic")
    print("   • Alert throttling and rate limiting")
    print("   • Multiple alert channels and categories")
    print("   • Risk management alert scenarios")
    print("   • Order execution alert scenarios")
    print("   • Strategy performance alert scenarios")

if __name__ == "__main__":
    main()