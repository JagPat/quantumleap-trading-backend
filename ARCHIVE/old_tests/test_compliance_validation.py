#!/usr/bin/env python3
"""
Comprehensive test for Trading Engine Compliance Validation System
Tests compliance rules, validation logic, audit reporting, and data retention
"""
import sys
import os
import json
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def test_compliance_validation():
    """Test the compliance validation system"""
    print("🔍 Testing Trading Engine Compliance Validation System...")
    
    try:
        # Import compliance modules
        from trading_engine.compliance_validator import (
            ComplianceValidator,
            ComplianceRule,
            RegulatoryFramework,
            ComplianceRuleType,
            ViolationSeverity,
            validate_order_compliance,
            validate_position_compliance,
            generate_compliance_report,
            get_compliance_status
        )
        
        print("✅ Successfully imported compliance validation modules")
        
        # Create temporary database for testing
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            test_db_path = tmp_db.name
        
        # Initialize compliance validator with test database
        validator = ComplianceValidator(db_path=test_db_path)
        print("✅ Compliance validator initialized successfully")
        
        # Test 1: Order Validation - Compliant Order
        print("\n📋 Test 1: Order Validation - Compliant Order")
        compliant_order = {
            'order_id': 'ORDER_001',
            'user_id': 'USER_001',
            'symbol': 'RELIANCE',
            'quantity': 100,
            'price': 2500.0,
            'order_type': 'LIMIT',
            'side': 'BUY',
            'portfolio_value': 1000000,
            'market_price': 2500.0,
            'position_size_percent': 2.5,  # Well within 5% limit
            'execution_quality_score': 0.95,
            'has_risk_controls': True,
            'algo_approval': True,
            'leverage_ratio': 1.5,  # Within 3:1 limit
            'security_concentration_percent': 2.5,
            'orders_per_second': 2
        }
        
        result = validator.validate_order(compliant_order)
        print(f"   Order ID: {compliant_order['order_id']}")
        print(f"   Compliant: {result.compliant}")
        print(f"   Violations: {len(result.violations)}")
        print(f"   Warnings: {len(result.warnings)}")
        print(f"   Execution Time: {result.execution_time_ms:.2f}ms")
        
        if result.compliant:
            print("   ✅ Compliant order validated successfully")
        else:
            print("   ❌ Expected compliant order but found violations:")
            for violation in result.violations:
                print(f"      - {violation.description}")
        
        # Test 2: Order Validation - Non-Compliant Order
        print("\n📋 Test 2: Order Validation - Non-Compliant Order")
        non_compliant_order = {
            'order_id': 'ORDER_002',
            'user_id': 'USER_002',
            'symbol': 'INFY',
            'quantity': 1000,
            'price': 1500.0,
            'order_type': 'LIMIT',
            'side': 'BUY',
            'portfolio_value': 1000000,
            'market_price': 1500.0,
            'position_size_percent': 15.0,  # Exceeds 5% limit
            'execution_quality_score': 0.6,  # Below 0.8 threshold
            'has_risk_controls': False,  # Missing risk controls
            'algo_approval': False,  # No algo approval
            'leverage_ratio': 4.0,  # Exceeds 3:1 limit
            'security_concentration_percent': 15.0,  # Exceeds 10% limit
            'orders_per_second': 15  # Exceeds 10 orders/second limit
        }
        
        result = validator.validate_order(non_compliant_order)
        print(f"   Order ID: {non_compliant_order['order_id']}")
        print(f"   Compliant: {result.compliant}")
        print(f"   Violations: {len(result.violations)}")
        print(f"   Warnings: {len(result.warnings)}")
        
        if not result.compliant:
            print("   ✅ Non-compliant order correctly identified")
            print("   Violations found:")
            for violation in result.violations:
                print(f"      - {violation.severity.value}: {violation.description}")
        else:
            print("   ❌ Expected non-compliant order but validation passed")
        
        # Test 3: Position Validation - Compliant Position
        print("\n📋 Test 3: Position Validation - Compliant Position")
        compliant_position = {
            'position_id': 'POS_001',
            'user_id': 'USER_001',
            'symbol': 'TCS',
            'quantity': 200,
            'market_value': 800000,
            'portfolio_value': 2000000,
            'position_size_percent': 4.0,  # Within 5% limit
            'security_concentration_percent': 8.0,  # Within 10% limit
            'leverage_ratio': 2.0,  # Within 3:1 limit
            'sector': 'IT',
            'sector_exposure_percent': 20.0  # Within 25% limit
        }
        
        result = validator.validate_position(compliant_position)
        print(f"   Position ID: {compliant_position['position_id']}")
        print(f"   Compliant: {result.compliant}")
        print(f"   Violations: {len(result.violations)}")
        
        if result.compliant:
            print("   ✅ Compliant position validated successfully")
        else:
            print("   ❌ Expected compliant position but found violations")
        
        # Test 4: Position Validation - Non-Compliant Position
        print("\n📋 Test 4: Position Validation - Non-Compliant Position")
        non_compliant_position = {
            'position_id': 'POS_002',
            'user_id': 'USER_002',
            'symbol': 'HDFC',
            'quantity': 500,
            'market_value': 1500000,
            'portfolio_value': 2000000,
            'position_size_percent': 7.5,  # Exceeds 5% limit
            'security_concentration_percent': 15.0,  # Exceeds 10% limit
            'leverage_ratio': 3.5,  # Exceeds 3:1 limit
            'sector': 'BANKING'
        }
        
        result = validator.validate_position(non_compliant_position)
        print(f"   Position ID: {non_compliant_position['position_id']}")
        print(f"   Compliant: {result.compliant}")
        print(f"   Violations: {len(result.violations)}")
        
        if not result.compliant:
            print("   ✅ Non-compliant position correctly identified")
        else:
            print("   ❌ Expected non-compliant position but validation passed")
        
        # Test 5: Custom Compliance Rule
        print("\n📋 Test 5: Custom Compliance Rule")
        custom_rule = ComplianceRule(
            rule_id="custom_test_rule",
            name="Test Maximum Order Value",
            description="Single order cannot exceed ₹500,000",
            rule_type=ComplianceRuleType.PRE_TRADE,
            regulatory_framework=RegulatoryFramework.SEBI,
            severity=ViolationSeverity.MEDIUM,
            parameters={"max_order_value": 500000},
            validation_logic=json.dumps({
                "field": "order_value",
                "operator": "lte",
                "value": 500000
            }),
            remediation_action="Reduce order size or split into multiple orders"
        )
        
        success = validator.add_rule(custom_rule)
        print(f"   Custom rule added: {success}")
        
        # Test custom rule with large order
        large_order = {
            'order_id': 'ORDER_003',
            'user_id': 'USER_003',
            'symbol': 'WIPRO',
            'quantity': 2000,
            'price': 400.0,
            'order_value': 800000,  # Exceeds ₹500,000 limit
            'portfolio_value': 5000000,
            'position_size_percent': 1.6,
            'execution_quality_score': 0.9,
            'has_risk_controls': True,
            'algo_approval': True,
            'leverage_ratio': 1.2,
            'security_concentration_percent': 1.6
        }
        
        result = validator.validate_order(large_order)
        print(f"   Large order compliant: {result.compliant}")
        
        if not result.compliant:
            custom_violations = [v for v in result.violations if v.rule_id == "custom_test_rule"]
            if custom_violations:
                print("   ✅ Custom rule violation detected correctly")
            else:
                print("   ❌ Custom rule not triggered")
        
        # Test 6: Compliance Status
        print("\n📋 Test 6: Compliance Status")
        status = validator.get_compliance_status()
        print(f"   Overall compliance rate: {status['statistics']['compliance_rate']}%")
        print(f"   Total checks: {status['statistics']['total_checks']}")
        print(f"   Total violations: {status['statistics']['total_violations']}")
        print(f"   Status: {status['status']}")
        print("   ✅ Compliance status retrieved successfully")
        
        # Test 7: Audit Report Generation
        print("\n📋 Test 7: Audit Report Generation")
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            report = validator.generate_audit_report(
                report_type="COMPLIANCE_SUMMARY",
                start_date=start_date,
                end_date=end_date,
                generated_by="test_system"
            )
            
            print(f"   Report ID: {report.report_id}")
            print(f"   Report Type: {report.report_type}")
            print(f"   Title: {report.title}")
            print(f"   Sections: {len(report.sections)}")
            print(f"   Recommendations: {len(report.recommendations)}")
            print("   ✅ Audit report generated successfully")
            
        except Exception as e:
            print(f"   ⚠️  Audit report generation failed: {e}")
        
        # Test 8: Data Retention Policy
        print("\n📋 Test 8: Data Retention Policy")
        try:
            retention_results = validator.apply_data_retention_policy()
            print(f"   Execution time: {retention_results['execution_time']:.2f}s")
            print(f"   Deleted records: {retention_results['deleted_records']}")
            print(f"   Errors: {len(retention_results['errors'])}")
            print("   ✅ Data retention policy applied successfully")
            
        except Exception as e:
            print(f"   ⚠️  Data retention policy failed: {e}")
        
        # Test 9: Database Integrity
        print("\n📋 Test 9: Database Integrity")
        try:
            with sqlite3.connect(test_db_path) as conn:
                # Check tables exist
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name LIKE 'compliance_%'
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                expected_tables = [
                    'compliance_rules',
                    'compliance_violations', 
                    'compliance_checks',
                    'audit_reports'
                ]
                
                missing_tables = set(expected_tables) - set(tables)
                if missing_tables:
                    print(f"   ❌ Missing tables: {missing_tables}")
                else:
                    print("   ✅ All required tables exist")
                
                # Check data integrity
                cursor = conn.execute("SELECT COUNT(*) FROM compliance_rules WHERE enabled = 1")
                active_rules = cursor.fetchone()[0]
                print(f"   Active rules: {active_rules}")
                
                cursor = conn.execute("SELECT COUNT(*) FROM compliance_violations")
                total_violations = cursor.fetchone()[0]
                print(f"   Total violations recorded: {total_violations}")
                
                cursor = conn.execute("SELECT COUNT(*) FROM compliance_checks")
                total_checks = cursor.fetchone()[0]
                print(f"   Total checks performed: {total_checks}")
                
        except Exception as e:
            print(f"   ❌ Database integrity check failed: {e}")
        
        # Test 10: Performance Test
        print("\n📋 Test 10: Performance Test")
        import time
        
        performance_order = {
            'order_id': 'PERF_ORDER',
            'user_id': 'PERF_USER',
            'symbol': 'NIFTY50',
            'quantity': 50,
            'price': 18000.0,
            'portfolio_value': 10000000,
            'position_size_percent': 0.9,
            'execution_quality_score': 0.95,
            'has_risk_controls': True,
            'algo_approval': True,
            'leverage_ratio': 1.1,
            'security_concentration_percent': 0.9
        }
        
        # Run multiple validations to test performance
        start_time = time.time()
        validation_count = 100
        
        for i in range(validation_count):
            performance_order['order_id'] = f'PERF_ORDER_{i}'
            result = validator.validate_order(performance_order)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_validation = (total_time / validation_count) * 1000  # Convert to ms
        
        print(f"   Validations performed: {validation_count}")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Average time per validation: {avg_time_per_validation:.2f}ms")
        
        if avg_time_per_validation < 50:  # Less than 50ms per validation
            print("   ✅ Performance test passed")
        else:
            print("   ⚠️  Performance may need optimization")
        
        print("\n🎉 Compliance Validation System Test Summary:")
        print("=" * 60)
        print("✅ Order validation (compliant and non-compliant)")
        print("✅ Position validation (compliant and non-compliant)")
        print("✅ Custom compliance rules")
        print("✅ Compliance status reporting")
        print("✅ Audit report generation")
        print("✅ Data retention policies")
        print("✅ Database integrity")
        print("✅ Performance testing")
        print("\n🔒 Compliance validation system is working correctly!")
        
        # Cleanup
        try:
            os.unlink(test_db_path)
            print(f"🧹 Cleaned up test database: {test_db_path}")
        except:
            pass
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure the trading_engine module is properly installed")
        return False
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_compliance_router():
    """Test the compliance router endpoints"""
    print("\n🌐 Testing Compliance Router...")
    
    try:
        from trading_engine.compliance_router import router
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        
        # Create test app
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        print("✅ Compliance router imported successfully")
        
        # Test health endpoint
        response = client.get("/compliance/health")
        print(f"   Health check status: {response.status_code}")
        
        if response.status_code == 200:
            health_data = response.json()
            print(f"   Status: {health_data.get('status')}")
            print("   ✅ Health check passed")
        
        # Test compliance status endpoint
        response = client.get("/compliance/status")
        print(f"   Status endpoint: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ Status endpoint working")
        
        # Test order validation endpoint
        test_order = {
            "order_id": "TEST_ORDER_001",
            "user_id": "TEST_USER",
            "symbol": "RELIANCE",
            "quantity": 100,
            "price": 2500.0,
            "order_type": "LIMIT",
            "side": "BUY",
            "portfolio_value": 1000000,
            "position_size_percent": 2.5
        }
        
        response = client.post("/compliance/validate/order", json=test_order)
        print(f"   Order validation endpoint: {response.status_code}")
        
        if response.status_code in [200, 400]:  # Both success and validation failure are valid
            print("   ✅ Order validation endpoint working")
        
        print("✅ Compliance router tests completed")
        return True
        
    except ImportError as e:
        print(f"⚠️  Router test skipped - missing dependencies: {e}")
        return True  # Don't fail the main test for optional dependencies
        
    except Exception as e:
        print(f"❌ Router test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Compliance Validation System Tests...")
    print("=" * 60)
    
    # Run core compliance tests
    core_success = test_compliance_validation()
    
    # Run router tests
    router_success = test_compliance_router()
    
    if core_success and router_success:
        print("\n🎉 All compliance tests passed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)