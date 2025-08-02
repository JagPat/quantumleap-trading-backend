#!/usr/bin/env python3
"""
Comprehensive Test Suite for Transaction Management System
Tests ACID compliance, rollback mechanisms, data integrity, and audit logging
"""

import os
import sys
import sqlite3
import threading
import time
import tempfile
import unittest
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from database.transaction_manager import (
    TransactionManager, TransactionType, ValidationLevel, TransactionStatus,
    TransactionValidationError, DeadlockError, DeadlockDetector, 
    TransactionRetryManager, with_transaction
)

class TestTransactionManager(unittest.TestCase):
    """Test cases for TransactionManager"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.db_path = self.test_db.name
        self.manager = TransactionManager(self.db_path)
        
        # Create test tables
        self._create_test_tables()
    
    def tearDown(self):
        """Clean up test environment"""
        self.manager.close()
        try:
            os.unlink(self.db_path)
        except:
            pass
    
    def _create_test_tables(self):
        """Create test tables for transaction testing"""
        conn = self.manager._get_connection()
        cursor = conn.cursor()
        
        # Create test tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_users (
                id INTEGER PRIMARY KEY,
                user_id TEXT UNIQUE NOT NULL,
                balance DECIMAL(15,2) DEFAULT 0,
                max_position_size DECIMAL(15,2) DEFAULT 10000,
                max_daily_loss DECIMAL(15,2) DEFAULT 1000,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_portfolio (
                id INTEGER PRIMARY KEY,
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                quantity INTEGER DEFAULT 0,
                average_price DECIMAL(10,2) DEFAULT 0,
                current_price DECIMAL(10,2) DEFAULT 0,
                market_value DECIMAL(15,2) DEFAULT 0,
                UNIQUE(user_id, symbol),
                FOREIGN KEY (user_id) REFERENCES test_users(user_id),
                CHECK (quantity >= 0),
                CHECK (average_price > 0 OR quantity = 0),
                CHECK (current_price >= 0)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_orders (
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
                FOREIGN KEY (user_id) REFERENCES test_users(user_id),
                CHECK (quantity > 0),
                CHECK (filled_quantity >= 0),
                CHECK (filled_quantity <= quantity),
                CHECK (price > 0),
                CHECK (status IN ('pending', 'partial', 'filled', 'cancelled', 'rejected'))
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_trades (
                id INTEGER PRIMARY KEY,
                trade_id TEXT UNIQUE NOT NULL,
                order_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                value DECIMAL(15,2) NOT NULL,
                commission DECIMAL(10,2) DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES test_orders(order_id),
                FOREIGN KEY (user_id) REFERENCES test_users(user_id),
                CHECK (quantity > 0),
                CHECK (price > 0),
                CHECK (commission >= 0)
            )
        """)
        
        conn.commit()
        
        # Insert test data
        cursor.execute("INSERT OR IGNORE INTO test_users (user_id, balance) VALUES ('user1', 10000)")
        cursor.execute("INSERT OR IGNORE INTO test_users (user_id, balance) VALUES ('user2', 5000)")
        cursor.execute("INSERT OR IGNORE INTO test_portfolio (user_id, symbol, quantity, average_price, current_price) VALUES ('user1', 'AAPL', 100, 150.0, 155.0)")
        cursor.execute("INSERT OR IGNORE INTO test_orders (order_id, user_id, symbol, quantity, price) VALUES ('order1', 'user1', 'AAPL', 50, 160.0)")
        
        conn.commit()
    
    def test_successful_transaction(self):
        """Test successful transaction execution"""
        with self.manager.transaction(TransactionType.TRADE_EXECUTION, "user1") as tx:
            # Insert a new trade
            tx.execute(
                "INSERT INTO test_trades (trade_id, order_id, user_id, symbol, quantity, price, value) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("trade1", "order1", "user1", "AAPL", 50, 160.0, 8000.0),
                table_name="test_trades",
                operation_type="INSERT",
                record_id="trade1"
            )
            
            # Update order status
            tx.execute(
                "UPDATE test_orders SET status = 'filled', filled_quantity = quantity WHERE order_id = ?",
                ("order1",),
                table_name="test_orders",
                operation_type="UPDATE",
                record_id="order1"
            )
        
        # Verify transaction was committed
        conn = self.manager._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM test_trades WHERE trade_id = 'trade1'")
        self.assertEqual(cursor.fetchone()[0], 1)
        
        cursor.execute("SELECT status FROM test_orders WHERE order_id = 'order1'")
        self.assertEqual(cursor.fetchone()[0], 'filled')
    
    def test_transaction_rollback(self):
        """Test transaction rollback on error"""
        try:
            with self.manager.transaction(TransactionType.TRADE_EXECUTION, "user1") as tx:
                # Insert a trade
                tx.execute(
                    "INSERT INTO test_trades (trade_id, order_id, user_id, symbol, quantity, price, value) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    ("trade2", "order1", "user1", "AAPL", 50, 160.0, 8000.0),
                    table_name="test_trades",
                    operation_type="INSERT",
                    record_id="trade2"
                )
                
                # Cause an intentional error
                raise Exception("Intentional error for rollback test")
        
        except Exception:
            pass  # Expected
        
        # Verify transaction was rolled back
        conn = self.manager._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM test_trades WHERE trade_id = 'trade2'")
        self.assertEqual(cursor.fetchone()[0], 0)
    
    def test_validation_levels(self):
        """Test different validation levels"""
        # Test basic validation (should pass)
        with self.manager.transaction(
            TransactionType.PORTFOLIO_UPDATE, 
            "user1", 
            ValidationLevel.BASIC
        ) as tx:
            tx.execute("SELECT 1")
        
        # Test strict validation
        with self.manager.transaction(
            TransactionType.PORTFOLIO_UPDATE, 
            "user1", 
            ValidationLevel.STRICT
        ) as tx:
            tx.execute("SELECT 1")
        
        # Test paranoid validation
        with self.manager.transaction(
            TransactionType.PORTFOLIO_UPDATE, 
            "user1", 
            ValidationLevel.PARANOID
        ) as tx:
            tx.execute("SELECT 1")
    
    def test_data_validation_errors(self):
        """Test data validation error detection"""
        # Insert invalid data that should trigger validation errors
        conn = self.manager._get_connection()
        cursor = conn.cursor()
        
        # Insert negative quantity (should be caught by validation)
        cursor.execute("INSERT INTO test_portfolio (user_id, symbol, quantity, average_price) VALUES ('user1', 'INVALID', -10, 100)")
        conn.commit()
        
        # Test validation with strict level
        with self.assertRaises(TransactionValidationError):
            with self.manager.transaction(
                TransactionType.PORTFOLIO_UPDATE, 
                "user1", 
                ValidationLevel.STRICT
            ) as tx:
                tx.execute("SELECT 1")
    
    def test_audit_logging(self):
        """Test audit trail logging"""
        with self.manager.transaction(TransactionType.TRADE_EXECUTION, "user1") as tx:
            tx.execute(
                "INSERT INTO test_trades (trade_id, order_id, user_id, symbol, quantity, price, value) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("trade3", "order1", "user1", "AAPL", 25, 155.0, 3875.0),
                table_name="test_trades",
                operation_type="INSERT",
                record_id="trade3"
            )
        
        # Check audit trail
        conn = self.manager._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM transaction_audit_trail WHERE table_name = 'test_trades'")
        audit_count = cursor.fetchone()[0]
        self.assertGreater(audit_count, 0)
    
    def test_transaction_history(self):
        """Test transaction history retrieval"""
        # Execute a few transactions
        for i in range(3):
            with self.manager.transaction(TransactionType.PORTFOLIO_UPDATE, "user1") as tx:
                tx.execute("SELECT 1")
        
        # Get transaction history
        history = self.manager.get_transaction_history(user_id="user1", limit=5)
        self.assertGreaterEqual(len(history), 3)
        
        # Check history structure
        for record in history:
            self.assertIn('transaction_id', record)
            self.assertIn('transaction_type', record)
            self.assertIn('status', record)
            self.assertIn('user_id', record)
    
    def test_data_integrity_report(self):
        """Test data integrity report generation"""
        report = self.manager.get_data_integrity_report()
        
        self.assertIn('timestamp', report)
        self.assertIn('validation_rules_checked', report)
        self.assertIn('integrity_violations', report)
        self.assertIn('transaction_statistics', report)
        self.assertIn('recommendations', report)
        
        self.assertIsInstance(report['validation_rules_checked'], int)
        self.assertIsInstance(report['integrity_violations'], list)
        self.assertIsInstance(report['recommendations'], list)
    
    def test_concurrent_transactions(self):
        """Test concurrent transaction handling"""
        def execute_transaction(user_id, trade_id):
            try:
                with self.manager.transaction(TransactionType.TRADE_EXECUTION, user_id) as tx:
                    tx.execute(
                        "INSERT INTO test_trades (trade_id, order_id, user_id, symbol, quantity, price, value) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (trade_id, "order1", user_id, "AAPL", 10, 150.0, 1500.0),
                        table_name="test_trades",
                        operation_type="INSERT",
                        record_id=trade_id
                    )
                    # Small delay to increase chance of concurrency
                    time.sleep(0.01)
                return True
            except Exception as e:
                print(f"Transaction {trade_id} failed: {e}")
                return False
        
        # Execute multiple concurrent transactions
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(10):
                future = executor.submit(execute_transaction, "user1", f"concurrent_trade_{i}")
                futures.append(future)
            
            # Wait for all transactions to complete
            results = [future.result() for future in as_completed(futures)]
        
        # Verify some transactions succeeded
        successful_transactions = sum(results)
        self.assertGreater(successful_transactions, 0)
        
        # Verify data consistency
        conn = self.manager._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM test_trades WHERE trade_id LIKE 'concurrent_trade_%'")
        trade_count = cursor.fetchone()[0]
        self.assertEqual(trade_count, successful_transactions)

class TestDeadlockDetector(unittest.TestCase):
    """Test cases for DeadlockDetector"""
    
    def setUp(self):
        self.detector = DeadlockDetector()
    
    def test_no_deadlock(self):
        """Test normal operation without deadlock"""
        self.detector.add_lock_request("tx1", "resource1")
        self.detector.add_lock_request("tx2", "resource2")
        # Should not raise any exception
    
    def test_deadlock_detection(self):
        """Test deadlock detection"""
        # Create a circular dependency
        self.detector.add_lock_request("tx1", "resource1", ["tx2"])
        
        with self.assertRaises(DeadlockError):
            self.detector.add_lock_request("tx2", "resource2", ["tx1"])
    
    def test_deadlock_victim_selection(self):
        """Test deadlock victim selection"""
        self.detector.transaction_locks = {
            "tx1": ["resource1", "resource2", "resource3"],
            "tx2": ["resource4"],
            "tx3": ["resource5", "resource6"]
        }
        
        victim = self.detector._select_deadlock_victim()
        self.assertEqual(victim, "tx2")  # Transaction with fewest locks

class TestTransactionRetryManager(unittest.TestCase):
    """Test cases for TransactionRetryManager"""
    
    def setUp(self):
        self.retry_manager = TransactionRetryManager(max_retries=3, base_delay=0.01, max_delay=0.1)
    
    def test_successful_execution(self):
        """Test successful execution without retries"""
        def successful_function():
            return "success"
        
        result = self.retry_manager.execute_with_retry(successful_function)
        self.assertEqual(result, "success")
    
    def test_retry_on_deadlock(self):
        """Test retry on deadlock error"""
        attempt_count = 0
        
        def failing_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise DeadlockError("Simulated deadlock")
            return "success after retries"
        
        result = self.retry_manager.execute_with_retry(failing_function)
        self.assertEqual(result, "success after retries")
        self.assertEqual(attempt_count, 3)
    
    def test_max_retries_exceeded(self):
        """Test behavior when max retries are exceeded"""
        def always_failing_function():
            raise DeadlockError("Always fails")
        
        with self.assertRaises(DeadlockError):
            self.retry_manager.execute_with_retry(always_failing_function)
    
    def test_non_retryable_error(self):
        """Test that non-retryable errors are not retried"""
        attempt_count = 0
        
        def non_retryable_error():
            nonlocal attempt_count
            attempt_count += 1
            raise ValueError("Non-retryable error")
        
        with self.assertRaises(ValueError):
            self.retry_manager.execute_with_retry(non_retryable_error)
        
        self.assertEqual(attempt_count, 1)  # Should not retry

class TestTransactionDecorator(unittest.TestCase):
    """Test cases for transaction decorator"""
    
    def setUp(self):
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.db_path = self.test_db.name
        
        # Set environment variable for database path
        os.environ['DATABASE_PATH'] = self.db_path
    
    def tearDown(self):
        try:
            os.unlink(self.db_path)
        except:
            pass
    
    def test_transaction_decorator(self):
        """Test transaction decorator functionality"""
        @with_transaction(TransactionType.TRADE_EXECUTION, "user1")
        def decorated_function(tx):
            tx.execute("SELECT 1")
            return "decorated success"
        
        result = decorated_function()
        self.assertEqual(result, "decorated success")

def run_comprehensive_tests():
    """Run all transaction management tests"""
    print("🔄 Running Comprehensive Transaction Management Tests...")
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestTransactionManager))
    test_suite.addTest(unittest.makeSuite(TestDeadlockDetector))
    test_suite.addTest(unittest.makeSuite(TestTransactionRetryManager))
    test_suite.addTest(unittest.makeSuite(TestTransactionDecorator))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    if result.wasSuccessful():
        print("✅ All transaction management tests passed!")
        return True
    else:
        print(f"❌ {len(result.failures)} test(s) failed, {len(result.errors)} error(s)")
        return False

def run_performance_tests():
    """Run performance tests for transaction management"""
    print("\n🔄 Running Transaction Performance Tests...")
    
    test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    test_db.close()
    db_path = test_db.name
    
    try:
        manager = TransactionManager(db_path)
        
        # Create test table
        conn = manager._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE performance_test (
                id INTEGER PRIMARY KEY,
                data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        
        # Test transaction throughput
        start_time = time.time()
        transaction_count = 100
        
        for i in range(transaction_count):
            with manager.transaction(TransactionType.PORTFOLIO_UPDATE, "perf_user") as tx:
                tx.execute(
                    "INSERT INTO performance_test (data) VALUES (?)",
                    (f"test_data_{i}",),
                    table_name="performance_test",
                    operation_type="INSERT",
                    record_id=f"perf_{i}"
                )
        
        end_time = time.time()
        duration = end_time - start_time
        throughput = transaction_count / duration
        
        print(f"📊 Transaction Performance Results:")
        print(f"   - Transactions: {transaction_count}")
        print(f"   - Duration: {duration:.2f} seconds")
        print(f"   - Throughput: {throughput:.2f} transactions/second")
        
        # Test concurrent transaction performance
        print("\n🔄 Testing Concurrent Transaction Performance...")
        
        def concurrent_transaction(tx_id):
            with manager.transaction(TransactionType.TRADE_EXECUTION, f"user_{tx_id}") as tx:
                tx.execute(
                    "INSERT INTO performance_test (data) VALUES (?)",
                    (f"concurrent_data_{tx_id}",),
                    table_name="performance_test",
                    operation_type="INSERT",
                    record_id=f"concurrent_{tx_id}"
                )
        
        start_time = time.time()
        concurrent_count = 50
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(concurrent_transaction, i) for i in range(concurrent_count)]
            for future in as_completed(futures):
                future.result()
        
        end_time = time.time()
        concurrent_duration = end_time - start_time
        concurrent_throughput = concurrent_count / concurrent_duration
        
        print(f"📊 Concurrent Transaction Performance Results:")
        print(f"   - Concurrent Transactions: {concurrent_count}")
        print(f"   - Duration: {concurrent_duration:.2f} seconds")
        print(f"   - Throughput: {concurrent_throughput:.2f} transactions/second")
        
        manager.close()
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
    print("🚀 Starting Transaction Management System Tests...")
    
    # Run comprehensive tests
    tests_passed = run_comprehensive_tests()
    
    # Run performance tests
    run_performance_tests()
    
    if tests_passed:
        print("\n🎉 All transaction management tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the output above.")
        sys.exit(1)