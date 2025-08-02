#!/usr/bin/env python3
"""
Comprehensive Test Suite for Data Validation and Consistency System
Tests validation rules, consistency checks, data repair, and quality metrics
"""

import os
import sys
import sqlite3
import tempfile
import unittest
import json
from datetime import datetime, timedelta
from decimal import Decimal

# Add the app directory to the path
sys.path.append('app')

try:
    from database.data_validator import (
        DataValidator, ValidationRule, ValidationResult, ConsistencyCheck,
        ValidationSeverity, ValidationCategory, ValidationStatus,
        create_data_validator, validate_trading_data
    )
    print("✅ Successfully imported data validation components")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

class TestDataValidator(unittest.TestCase):
    """Test cases for DataValidator"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.db_path = self.test_db.name
        self.validator = DataValidator(self.db_path)
        
        # Create test tables and data
        self._create_test_tables()
        self._insert_test_data()
    
    def tearDown(self):
        """Clean up test environment"""
        self.validator.close()
        try:
            os.unlink(self.db_path)
        except:
            pass
    
    def _create_test_tables(self):
        """Create test tables for validation testing"""
        conn = self.validator._get_connection()
        cursor = conn.cursor()
        
        # Create test tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                user_id TEXT UNIQUE NOT NULL,
                email TEXT,
                balance DECIMAL(15,2) DEFAULT 0,
                initial_balance DECIMAL(15,2) DEFAULT 0,
                credit_limit DECIMAL(15,2) DEFAULT 0,
                max_position_size DECIMAL(15,2) DEFAULT 10000,
                max_daily_loss DECIMAL(15,2) DEFAULT 1000,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY,
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                quantity INTEGER DEFAULT 0,
                average_price DECIMAL(10,2) DEFAULT 0,
                current_price DECIMAL(10,2) DEFAULT 0,
                market_value DECIMAL(15,2) DEFAULT 0,
                UNIQUE(user_id, symbol),
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                CHECK (quantity >= 0),
                CHECK (average_price >= 0),
                CHECK (current_price >= 0)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                order_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                filled_quantity INTEGER DEFAULT 0,
                remaining_quantity INTEGER DEFAULT 0,
                price DECIMAL(10,2) NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                CHECK (quantity > 0),
                CHECK (filled_quantity >= 0),
                CHECK (price > 0),
                CHECK (status IN ('pending', 'partial', 'filled', 'cancelled', 'rejected'))
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY,
                trade_id TEXT UNIQUE NOT NULL,
                order_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                value DECIMAL(15,2) NOT NULL,
                commission DECIMAL(10,2) DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(order_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                CHECK (quantity > 0),
                CHECK (price > 0),
                CHECK (commission >= 0),
                CHECK (side IN ('buy', 'sell'))
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY,
                strategy_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                win_rate DECIMAL(5,2) DEFAULT 0,
                sharpe_ratio DECIMAL(8,4) DEFAULT 0,
                max_position_size DECIMAL(15,2) DEFAULT 10000,
                max_daily_loss DECIMAL(15,2) DEFAULT 1000,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_data (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                open_price DECIMAL(10,2) NOT NULL,
                high_price DECIMAL(10,2) NOT NULL,
                low_price DECIMAL(10,2) NOT NULL,
                close_price DECIMAL(10,2) NOT NULL,
                volume INTEGER DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CHECK (open_price > 0),
                CHECK (high_price > 0),
                CHECK (low_price > 0),
                CHECK (close_price > 0),
                CHECK (volume >= 0)
            )
        """)
        
        conn.commit()
    
    def _insert_test_data(self):
        """Insert test data including some invalid records"""
        conn = self.validator._get_connection()
        cursor = conn.cursor()
        
        # Insert valid users
        cursor.execute("INSERT INTO users (user_id, email, balance, initial_balance, credit_limit) VALUES ('user1', 'user1@example.com', 10000, 10000, 5000)")
        cursor.execute("INSERT INTO users (user_id, email, balance, initial_balance, credit_limit) VALUES ('user2', 'user2@example.com', 5000, 5000, 2000)")
        
        # Insert invalid user (negative balance beyond credit limit)
        cursor.execute("INSERT INTO users (user_id, email, balance, initial_balance, credit_limit) VALUES ('user3', 'invalid-email', -10000, 5000, 2000)")
        
        # Insert valid portfolio
        cursor.execute("INSERT INTO portfolio (user_id, symbol, quantity, average_price, current_price, market_value) VALUES ('user1', 'AAPL', 100, 150.0, 155.0, 15500)")
        cursor.execute("INSERT INTO portfolio (user_id, symbol, quantity, average_price, current_price, market_value) VALUES ('user2', 'GOOGL', 50, 2000.0, 2100.0, 105000)")
        
        # Insert invalid portfolio (negative quantity)
        cursor.execute("INSERT INTO portfolio (user_id, symbol, quantity, average_price, current_price, market_value) VALUES ('user1', 'TSLA', -10, 800.0, 850.0, -8500)")
        
        # Insert invalid portfolio (wrong market value calculation)
        cursor.execute("INSERT INTO portfolio (user_id, symbol, quantity, average_price, current_price, market_value) VALUES ('user2', 'MSFT', 25, 300.0, 320.0, 7000)")  # Should be 8000
        
        # Insert valid orders
        cursor.execute("INSERT INTO orders (order_id, user_id, symbol, quantity, filled_quantity, remaining_quantity, price, status) VALUES ('order1', 'user1', 'AAPL', 50, 50, 0, 160.0, 'filled')")
        cursor.execute("INSERT INTO orders (order_id, user_id, symbol, quantity, filled_quantity, remaining_quantity, price, status) VALUES ('order2', 'user2', 'GOOGL', 25, 10, 15, 2050.0, 'partial')")
        
        # Insert invalid order (filled > quantity)
        cursor.execute("INSERT INTO orders (order_id, user_id, symbol, quantity, filled_quantity, remaining_quantity, price, status) VALUES ('order3', 'user1', 'TSLA', 20, 25, -5, 850.0, 'partial')")
        
        # Insert valid trades
        cursor.execute("INSERT INTO trades (trade_id, order_id, user_id, symbol, side, quantity, price, value, commission) VALUES ('trade1', 'order1', 'user1', 'AAPL', 'buy', 50, 160.0, 8000.0, 10.0)")
        cursor.execute("INSERT INTO trades (trade_id, order_id, user_id, symbol, side, quantity, price, value, commission) VALUES ('trade2', 'order2', 'user2', 'GOOGL', 'buy', 10, 2050.0, 20500.0, 15.0)")
        
        # Insert invalid trade (wrong value calculation)
        cursor.execute("INSERT INTO trades (trade_id, order_id, user_id, symbol, side, quantity, price, value, commission) VALUES ('trade3', 'order1', 'user1', 'AAPL', 'sell', 25, 155.0, 4000.0, 8.0)")  # Should be 3875.0
        
        # Insert valid strategies
        cursor.execute("INSERT INTO strategies (strategy_id, name, win_rate, sharpe_ratio, max_position_size, max_daily_loss) VALUES ('strat1', 'Mean Reversion', 65.5, 1.2, 50000, 2000)")
        
        # Insert invalid strategy (win rate > 100)
        cursor.execute("INSERT INTO strategies (strategy_id, name, win_rate, sharpe_ratio, max_position_size, max_daily_loss) VALUES ('strat2', 'Invalid Strategy', 150.0, 15.0, 100000, 5000)")
        
        # Insert valid market data
        cursor.execute("INSERT INTO market_data (symbol, open_price, high_price, low_price, close_price, volume) VALUES ('AAPL', 150.0, 160.0, 148.0, 155.0, 1000000)")
        
        # Insert invalid market data (high < low)
        cursor.execute("INSERT INTO market_data (symbol, open_price, high_price, low_price, close_price, volume) VALUES ('GOOGL', 2000.0, 1950.0, 2100.0, 2050.0, 500000)")
        
        conn.commit()
    
    def test_single_rule_validation(self):
        """Test validation of a single rule"""
        # Test a rule that should find violations
        result = self.validator.validate_single_rule("portfolio_quantity_non_negative")
        
        self.assertEqual(result.status, ValidationStatus.COMPLETED)
        self.assertEqual(result.severity, ValidationSeverity.ERROR)
        self.assertGreater(result.violations_count, 0)  # Should find the negative quantity
        self.assertIsInstance(result.violations_details, list)
        self.assertGreater(result.execution_time, 0)
        
        # Test a rule that should pass
        result = self.validator.validate_single_rule("user_email_format")
        self.assertEqual(result.status, ValidationStatus.COMPLETED)
        # Note: This might find violations due to our invalid email test data
    
    def test_all_rules_validation(self):
        """Test validation of all rules"""
        results = self.validator.validate_all_rules()
        
        self.assertIsInstance(results, dict)
        self.assertGreater(len(results), 0)
        
        # Check that we have results for key rules
        self.assertIn("portfolio_quantity_non_negative", results)
        self.assertIn("order_filled_quantity_valid", results)
        self.assertIn("trade_value_calculation", results)
        
        # Check that some rules found violations
        violation_count = sum(result.violations_count for result in results.values())
        self.assertGreater(violation_count, 0)
    
    def test_severity_filtering(self):
        """Test validation with severity filtering"""
        # Test only error-level rules
        error_results = self.validator.validate_all_rules(ValidationSeverity.ERROR)
        
        for result in error_results.values():
            self.assertEqual(result.severity, ValidationSeverity.ERROR)
        
        # Test only warning-level rules
        warning_results = self.validator.validate_all_rules(ValidationSeverity.WARNING)
        
        for result in warning_results.values():
            self.assertEqual(result.severity, ValidationSeverity.WARNING)
    
    def test_consistency_checks(self):
        """Test consistency checking"""
        # Test all consistency checks
        results = self.validator.check_consistency()
        
        self.assertIsInstance(results, dict)
        self.assertGreater(len(results), 0)
        
        # Check specific consistency checks
        for check_id, result in results.items():
            self.assertIn("check_id", result)
            self.assertIn("name", result)
            self.assertIn("status", result)
            self.assertIn("inconsistencies_count", result)
            self.assertIn("timestamp", result)
    
    def test_single_consistency_check(self):
        """Test single consistency check"""
        # Test a specific consistency check
        results = self.validator.check_consistency("referential_integrity_users_portfolio")
        
        self.assertEqual(len(results), 1)
        self.assertIn("referential_integrity_users_portfolio", results)
        
        result = results["referential_integrity_users_portfolio"]
        self.assertEqual(result["status"], "completed")
    
    def test_data_repair_dry_run(self):
        """Test data repair in dry-run mode"""
        # Test repair for a rule with repair action
        result = self.validator.repair_data("portfolio_quantity_non_negative", dry_run=True)
        
        self.assertTrue(result["success"])
        self.assertTrue(result["dry_run"])
        self.assertIn("affected_records", result)
        self.assertIn("repair_action", result)
        self.assertGreater(result["affected_records"], 0)  # Should find records to repair
    
    def test_data_repair_execution(self):
        """Test actual data repair execution"""
        # First, verify there are violations
        validation_result = self.validator.validate_single_rule("portfolio_market_value_calculation")
        initial_violations = validation_result.violations_count
        
        if initial_violations > 0:
            # Execute repair
            repair_result = self.validator.repair_data("portfolio_market_value_calculation", dry_run=False)
            
            self.assertTrue(repair_result["success"])
            self.assertFalse(repair_result["dry_run"])
            self.assertGreater(repair_result["affected_records"], 0)
            
            # Verify violations are reduced
            validation_result_after = self.validator.validate_single_rule("portfolio_market_value_calculation")
            self.assertLessEqual(validation_result_after.violations_count, initial_violations)
    
    def test_data_quality_metrics(self):
        """Test data quality metrics calculation"""
        metrics = self.validator.calculate_data_quality_metrics()
        
        self.assertIn("timestamp", metrics)
        self.assertIn("overall_score", metrics)
        self.assertIn("table_metrics", metrics)
        self.assertIn("rule_compliance", metrics)
        self.assertIn("consistency_score", metrics)
        self.assertIn("recommendations", metrics)
        
        # Check overall score is a valid percentage
        self.assertGreaterEqual(metrics["overall_score"], 0)
        self.assertLessEqual(metrics["overall_score"], 100)
        
        # Check table metrics
        self.assertIsInstance(metrics["table_metrics"], dict)
        for table_name, table_metrics in metrics["table_metrics"].items():
            self.assertIn("total_records", table_metrics)
            self.assertIn("completeness_score", table_metrics)
            self.assertIn("null_counts", table_metrics)
        
        # Check rule compliance
        self.assertIn("total_rules", metrics["rule_compliance"])
        self.assertIn("passed_rules", metrics["rule_compliance"])
        self.assertIn("compliance_score", metrics["rule_compliance"])
        self.assertIn("violations_by_severity", metrics["rule_compliance"])
    
    def test_validation_history(self):
        """Test validation history retrieval"""
        # Run some validations first
        self.validator.validate_single_rule("portfolio_quantity_non_negative")
        self.validator.validate_single_rule("order_filled_quantity_valid")
        
        # Get history
        history = self.validator.get_validation_history(limit=10)
        
        self.assertIsInstance(history, list)
        self.assertGreater(len(history), 0)
        
        # Check history structure
        for record in history:
            self.assertIn("rule_id", record)
            self.assertIn("rule_name", record)
            self.assertIn("status", record)
            self.assertIn("severity", record)
            self.assertIn("violations_count", record)
            self.assertIn("timestamp", record)
        
        # Test filtered history
        filtered_history = self.validator.get_validation_history(
            rule_id="portfolio_quantity_non_negative", 
            limit=5
        )
        
        for record in filtered_history:
            self.assertEqual(record["rule_id"], "portfolio_quantity_non_negative")
    
    def test_comprehensive_report(self):
        """Test comprehensive data quality report generation"""
        report = self.validator.generate_data_quality_report()
        
        self.assertIn("timestamp", report)
        self.assertIn("summary", report)
        self.assertIn("validation_results", report)
        self.assertIn("consistency_results", report)
        self.assertIn("quality_metrics", report)
        self.assertIn("recommendations", report)
        self.assertIn("repair_suggestions", report)
        
        # Check summary
        summary = report["summary"]
        self.assertIn("overall_score", summary)
        self.assertIn("total_rules_checked", summary)
        self.assertIn("total_violations", summary)
        self.assertIn("critical_issues", summary)
        self.assertIn("error_issues", summary)
        self.assertIn("warning_issues", summary)
        
        # Check that we have some violations (due to our test data)
        self.assertGreater(summary["total_violations"], 0)
        
        # Check recommendations
        self.assertIsInstance(report["recommendations"], list)
        self.assertGreater(len(report["recommendations"]), 0)
        
        # Check repair suggestions
        self.assertIsInstance(report["repair_suggestions"], list)
    
    def test_custom_validation_rule(self):
        """Test adding and using custom validation rules"""
        # Create a custom rule
        custom_rule = ValidationRule(
            rule_id="custom_test_rule",
            name="Custom Test Rule",
            description="Test custom validation rule",
            category=ValidationCategory.BUSINESS_RULE,
            severity=ValidationSeverity.WARNING,
            table_name="users",
            condition="balance > 0",
            error_message="User balance should be positive"
        )
        
        # Add rule to validator
        self.validator.validation_rules[custom_rule.rule_id] = custom_rule
        self.validator._persist_validation_rules([custom_rule])
        
        # Test the custom rule
        result = self.validator.validate_single_rule("custom_test_rule")
        
        self.assertEqual(result.rule_id, "custom_test_rule")
        self.assertEqual(result.status, ValidationStatus.COMPLETED)
        self.assertEqual(result.severity, ValidationSeverity.WARNING)
    
    def test_error_handling(self):
        """Test error handling in validation system"""
        # Test invalid rule ID
        with self.assertRaises(ValueError):
            self.validator.validate_single_rule("nonexistent_rule")
        
        # Test invalid consistency check ID
        with self.assertRaises(ValueError):
            self.validator.check_consistency("nonexistent_check")
        
        # Test repair for rule without repair action
        result = self.validator.repair_data("user_email_format", dry_run=True)
        self.assertFalse(result["success"])
        self.assertIn("No repair action defined", result["message"])

class TestDataValidatorUtilities(unittest.TestCase):
    """Test utility functions"""
    
    def test_create_data_validator(self):
        """Test data validator factory function"""
        test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        test_db.close()
        
        try:
            validator = create_data_validator(test_db.name)
            self.assertIsInstance(validator, DataValidator)
            validator.close()
        finally:
            try:
                os.unlink(test_db.name)
            except:
                pass
    
    def test_validate_trading_data(self):
        """Test quick trading data validation function"""
        test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        test_db.close()
        
        try:
            # Create a validator to set up the database
            validator = DataValidator(test_db.name)
            validator.close()
            
            # Test the utility function
            report = validate_trading_data(test_db.name)
            
            self.assertIsInstance(report, dict)
            self.assertIn("summary", report)
            self.assertIn("validation_results", report)
            
        finally:
            try:
                os.unlink(test_db.name)
            except:
                pass

def run_comprehensive_tests():
    """Run all data validation tests"""
    print("🔄 Running Comprehensive Data Validation Tests...")
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestDataValidator))
    test_suite.addTest(unittest.makeSuite(TestDataValidatorUtilities))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    if result.wasSuccessful():
        print("✅ All data validation tests passed!")
        return True
    else:
        print(f"❌ {len(result.failures)} test(s) failed, {len(result.errors)} error(s)")
        return False

def run_performance_tests():
    """Run performance tests for data validation"""
    print("\n🔄 Running Data Validation Performance Tests...")
    
    test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    test_db.close()
    db_path = test_db.name
    
    try:
        validator = DataValidator(db_path)
        
        # Create larger test dataset
        conn = validator._get_connection()
        cursor = conn.cursor()
        
        # Create test table
        cursor.execute("""
            CREATE TABLE performance_test (
                id INTEGER PRIMARY KEY,
                value INTEGER,
                price DECIMAL(10,2),
                status TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert test data
        print("  📝 Inserting test data...")
        test_records = 10000
        for i in range(test_records):
            # Insert some invalid records
            value = i if i % 100 != 0 else -i  # 1% negative values
            price = i * 0.01 if i % 200 != 0 else 0  # 0.5% zero prices
            status = "valid" if i % 150 != 0 else "invalid_status"  # Some invalid statuses
            
            cursor.execute("""
                INSERT INTO performance_test (value, price, status) 
                VALUES (?, ?, ?)
            """, (value, price, status))
        
        conn.commit()
        
        # Create validation rule for performance testing
        perf_rule = ValidationRule(
            rule_id="perf_test_rule",
            name="Performance Test Rule",
            description="Test rule for performance",
            category=ValidationCategory.RANGE,
            severity=ValidationSeverity.ERROR,
            table_name="performance_test",
            condition="value >= 0 AND price > 0 AND status = 'valid'",
            error_message="Invalid test data"
        )
        
        validator.validation_rules[perf_rule.rule_id] = perf_rule
        
        # Test validation performance
        import time
        start_time = time.time()
        
        result = validator.validate_single_rule("perf_test_rule")
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"📊 Performance Test Results:")
        print(f"   - Records processed: {test_records:,}")
        print(f"   - Violations found: {result.violations_count:,}")
        print(f"   - Execution time: {duration:.3f} seconds")
        print(f"   - Records per second: {test_records/duration:,.0f}")
        
        # Test batch validation performance
        start_time = time.time()
        
        # Create multiple rules for batch testing
        batch_rules = []
        for i in range(5):
            rule = ValidationRule(
                rule_id=f"batch_rule_{i}",
                name=f"Batch Rule {i}",
                description=f"Batch test rule {i}",
                category=ValidationCategory.RANGE,
                severity=ValidationSeverity.WARNING,
                table_name="performance_test",
                condition=f"value >= {i * 1000}",
                error_message=f"Value below {i * 1000}"
            )
            validator.validation_rules[rule.rule_id] = rule
            batch_rules.append(rule)
        
        # Run batch validation
        batch_results = {}
        for rule in batch_rules:
            batch_results[rule.rule_id] = validator.validate_single_rule(rule.rule_id)
        
        end_time = time.time()
        batch_duration = end_time - start_time
        
        total_violations = sum(result.violations_count for result in batch_results.values())
        
        print(f"\n📊 Batch Validation Results:")
        print(f"   - Rules executed: {len(batch_rules)}")
        print(f"   - Total violations: {total_violations:,}")
        print(f"   - Batch execution time: {batch_duration:.3f} seconds")
        print(f"   - Rules per second: {len(batch_rules)/batch_duration:.1f}")
        
        validator.close()
        print("✅ Performance tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        try:
            os.unlink(db_path)
        except:
            pass

if __name__ == "__main__":
    print("🚀 Starting Data Validation System Tests...")
    
    # Run comprehensive tests
    tests_passed = run_comprehensive_tests()
    
    # Run performance tests
    run_performance_tests()
    
    if tests_passed:
        print("\n🎉 All data validation tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the output above.")
        sys.exit(1)