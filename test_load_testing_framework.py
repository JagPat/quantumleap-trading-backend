#!/usr/bin/env python3
"""
Comprehensive tests for the Database Load Testing Framework
"""

import os
import time
import tempfile
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# Import the system under test
from app.database.load_testing_framework import (
    LoadTestingFramework,
    TradingOperationSimulator,
    TestConfiguration,
    TestType,
    TestStatus,
    StandardTestSuites
)

def create_test_database():
    """Create a temporary test database"""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_load.db")
    return db_path, temp_dir

def test_trading_operation_simulator():
    """Test the trading operation simulator"""
    print("Testing TradingOperationSimulator...")
    
    db_path, temp_dir = create_test_database()
    
    try:
        # Initialize framework and setup database
        framework = LoadTestingFramework()
        framework.setup_test_database(db_path)
        
        # Create simulator
        simulator = TradingOperationSimulator(db_path)
        
        # Test user creation
        print("  Testing user creation...")
        result = simulator.create_user(1)
        assert result.success, f"User creation failed: {result.error_message}"
        assert result.operation_type == "create_user"
        assert result.response_time_ms > 0
        print("  ✓ User creation working")
        
        # Test order placement
        print("  Testing order placement...")
        result = simulator.place_order(1)
        assert result.success, f"Order placement failed: {result.error_message}"
        assert result.operation_type == "place_order"
        assert result.response_time_ms > 0
        print("  ✓ Order placement working")
        
        # Test trade execution
        print("  Testing trade execution...")
        result = simulator.execute_trade(1)
        assert result.success, f"Trade execution failed: {result.error_message}"
        assert result.operation_type == "execute_trade"
        assert result.response_time_ms > 0
        print("  ✓ Trade execution working")
        
        # Test portfolio retrieval
        print("  Testing portfolio retrieval...")
        result = simulator.get_portfolio(1)
        assert result.success, f"Portfolio retrieval failed: {result.error_message}"
        assert result.operation_type == "get_portfolio"
        assert result.response_time_ms > 0
        print("  ✓ Portfolio retrieval working")
        
        # Test trade history retrieval
        print("  Testing trade history retrieval...")
        result = simulator.get_trade_history(1)
        assert result.success, f"Trade history retrieval failed: {result.error_message}"
        assert result.operation_type == "get_trade_history"
        assert result.response_time_ms > 0
        print("  ✓ Trade history retrieval working")
        
        # Verify data was created
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        assert user_count >= 1, "No users created"
        
        cursor.execute("SELECT COUNT(*) FROM orders")
        order_count = cursor.fetchone()[0]
        assert order_count >= 1, "No orders created"
        
        cursor.execute("SELECT COUNT(*) FROM trades")
        trade_count = cursor.fetchone()[0]
        assert trade_count >= 1, "No trades created"
        
        conn.close()
        
        print("✓ TradingOperationSimulator tests passed!")
        
    finally:
        shutil.rmtree(temp_dir)

def test_load_testing_framework_basic():
    """Test basic load testing framework functionality"""
    print("\nTesting LoadTestingFramework basic functionality...")
    
    db_path, temp_dir = create_test_database()
    results_dir = os.path.join(temp_dir, "results")
    
    try:
        # Create framework
        framework = LoadTestingFramework(results_dir)
        
        # Test database setup
        print("  Testing database setup...")
        framework.setup_test_database(db_path)
        
        # Verify tables were created
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['users', 'portfolio', 'orders', 'trades']
        for table in expected_tables:
            assert table in tables, f"Table {table} not created"
        
        conn.close()
        print("  ✓ Database setup working")
        
        # Test data generation
        print("  Testing test data generation...")
        framework.generate_test_data(db_path, 10)
        
        # Verify data was generated
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        assert user_count >= 10, f"Expected at least 10 users, got {user_count}"
        
        conn.close()
        print("  ✓ Test data generation working")
        
        print("✓ LoadTestingFramework basic functionality tests passed!")
        
    finally:
        shutil.rmtree(temp_dir)

def test_simple_load_test():
    """Test running a simple load test"""
    print("\nTesting simple load test execution...")
    
    db_path, temp_dir = create_test_database()
    results_dir = os.path.join(temp_dir, "results")
    
    try:
        # Create framework
        framework = LoadTestingFramework(results_dir)
        
        # Create simple test configuration
        config = TestConfiguration(
            test_name="simple_test",
            test_type=TestType.LOAD,
            duration_seconds=10,  # Short test
            concurrent_users=5,
            operations_per_second=50,
            database_path=db_path,
            test_data_size=20,
            ramp_up_seconds=2,
            ramp_down_seconds=2,
            think_time_ms=50,
            error_threshold_percent=10.0,
            response_time_threshold_ms=2000
        )
        
        print("  Running simple load test...")
        start_time = time.time()
        results = framework.run_load_test(config)
        end_time = time.time()
        
        # Verify test results
        assert results is not None, "No test results returned"
        assert results.test_name == "simple_test"
        assert results.test_type == TestType.LOAD
        assert results.total_operations > 0, "No operations executed"
        assert results.duration_seconds > 0, "Invalid test duration"
        assert results.test_status in [TestStatus.COMPLETED, TestStatus.FAILED], f"Invalid test status: {results.test_status}"
        
        # Verify timing
        actual_duration = end_time - start_time
        expected_duration = config.duration_seconds + config.ramp_up_seconds + config.ramp_down_seconds
        assert actual_duration >= expected_duration * 0.8, f"Test too short: {actual_duration}s vs expected {expected_duration}s"
        assert actual_duration <= expected_duration * 1.5, f"Test too long: {actual_duration}s vs expected {expected_duration}s"
        
        print(f"  ✓ Test completed in {actual_duration:.1f}s")
        print(f"  ✓ Total operations: {results.total_operations}")
        print(f"  ✓ Success rate: {100 - results.error_rate_percent:.1f}%")
        print(f"  ✓ Average response time: {results.average_response_time_ms:.1f}ms")
        print(f"  ✓ Throughput: {results.throughput_ops_per_sec:.1f} ops/sec")
        
        # Verify results file was created
        results_files = list(Path(results_dir).glob("*.json"))
        assert len(results_files) > 0, "No results file created"
        
        print("✓ Simple load test execution passed!")
        
    finally:
        shutil.rmtree(temp_dir)

def test_standard_test_suites():
    """Test standard test suite configurations"""
    print("\nTesting standard test suite configurations...")
    
    db_path, temp_dir = create_test_database()
    
    try:
        # Test basic load test configuration
        print("  Testing basic load test configuration...")
        config = StandardTestSuites.get_basic_load_test(db_path)
        
        assert config.test_name == "basic_load_test"
        assert config.test_type == TestType.LOAD
        assert config.duration_seconds == 300
        assert config.concurrent_users == 50
        assert config.operations_per_second == 500
        assert config.database_path == db_path
        print("  ✓ Basic load test configuration correct")
        
        # Test HFT simulation configuration
        print("  Testing HFT simulation configuration...")
        config = StandardTestSuites.get_high_frequency_trading_test(db_path)
        
        assert config.test_name == "hft_simulation"
        assert config.test_type == TestType.LOAD
        assert config.concurrent_users == 100
        assert config.operations_per_second == 2000
        assert config.think_time_ms == 10  # Low latency
        assert config.response_time_threshold_ms == 500  # Strict threshold
        print("  ✓ HFT simulation configuration correct")
        
        # Test volume test configuration
        print("  Testing volume test configuration...")
        config = StandardTestSuites.get_volume_test(db_path)
        
        assert config.test_name == "volume_test"
        assert config.test_type == TestType.VOLUME
        assert config.duration_seconds == 1800
        assert config.concurrent_users == 200
        assert config.test_data_size == 5000
        print("  ✓ Volume test configuration correct")
        
        print("✓ Standard test suite configurations passed!")
        
    finally:
        shutil.rmtree(temp_dir)

def test_performance_metrics():
    """Test performance metrics calculation"""
    print("\nTesting performance metrics calculation...")
    
    db_path, temp_dir = create_test_database()
    results_dir = os.path.join(temp_dir, "results")
    
    try:
        # Create framework
        framework = LoadTestingFramework(results_dir)
        
        # Run a quick test to generate metrics
        config = TestConfiguration(
            test_name="metrics_test",
            test_type=TestType.LOAD,
            duration_seconds=5,
            concurrent_users=3,
            operations_per_second=30,
            database_path=db_path,
            test_data_size=10,
            ramp_up_seconds=1,
            ramp_down_seconds=1,
            think_time_ms=10,
            error_threshold_percent=20.0,
            response_time_threshold_ms=5000
        )
        
        print("  Running test for metrics calculation...")
        results = framework.run_load_test(config)
        
        # Verify metrics are calculated
        assert results.total_operations > 0, "No operations recorded"
        assert results.successful_operations >= 0, "Invalid successful operations count"
        assert results.failed_operations >= 0, "Invalid failed operations count"
        assert results.total_operations == results.successful_operations + results.failed_operations, "Operation counts don't match"
        
        if results.successful_operations > 0:
            assert results.average_response_time_ms >= 0, "Invalid average response time"
            assert results.median_response_time_ms >= 0, "Invalid median response time"
            assert results.min_response_time_ms >= 0, "Invalid min response time"
            assert results.max_response_time_ms >= results.min_response_time_ms, "Max response time less than min"
            assert results.p95_response_time_ms >= results.median_response_time_ms, "P95 less than median"
            assert results.p99_response_time_ms >= results.p95_response_time_ms, "P99 less than P95"
        
        assert results.throughput_ops_per_sec >= 0, "Invalid throughput"
        assert 0 <= results.error_rate_percent <= 100, "Invalid error rate"
        assert results.cpu_usage_percent >= 0, "Invalid CPU usage"
        assert results.memory_usage_mb >= 0, "Invalid memory usage"
        assert results.database_size_mb >= 0, "Invalid database size"
        
        print(f"  ✓ Metrics calculated correctly")
        print(f"    - Total operations: {results.total_operations}")
        print(f"    - Success rate: {100 - results.error_rate_percent:.1f}%")
        print(f"    - Avg response time: {results.average_response_time_ms:.1f}ms")
        print(f"    - Throughput: {results.throughput_ops_per_sec:.1f} ops/sec")
        print(f"    - CPU usage: {results.cpu_usage_percent:.1f}%")
        print(f"    - Memory usage: {results.memory_usage_mb:.1f} MB")
        
        print("✓ Performance metrics calculation passed!")
        
    finally:
        shutil.rmtree(temp_dir)

def test_error_handling():
    """Test error handling in load testing"""
    print("\nTesting error handling...")
    
    db_path, temp_dir = create_test_database()
    results_dir = os.path.join(temp_dir, "results")
    
    try:
        # Create framework
        framework = LoadTestingFramework(results_dir)
        
        # Test with invalid database path
        print("  Testing with invalid database path...")
        config = TestConfiguration(
            test_name="error_test",
            test_type=TestType.LOAD,
            duration_seconds=2,
            concurrent_users=2,
            operations_per_second=10,
            database_path="/invalid/path/database.db",
            test_data_size=5,
            ramp_up_seconds=1,
            ramp_down_seconds=1,
            think_time_ms=10,
            error_threshold_percent=50.0,
            response_time_threshold_ms=5000
        )
        
        results = framework.run_load_test(config)
        
        # Should handle errors gracefully
        assert results is not None, "No results returned for error case"
        assert results.test_status == TestStatus.FAILED, "Test should have failed"
        assert len(results.error_details) > 0, "No error details recorded"
        
        print("  ✓ Error handling working correctly")
        print(f"    - Test status: {results.test_status.value}")
        print(f"    - Error details: {len(results.error_details)} errors recorded")
        
        print("✓ Error handling tests passed!")
        
    finally:
        shutil.rmtree(temp_dir)

def test_report_generation():
    """Test performance report generation"""
    print("\nTesting performance report generation...")
    
    db_path, temp_dir = create_test_database()
    results_dir = os.path.join(temp_dir, "results")
    
    try:
        # Create framework
        framework = LoadTestingFramework(results_dir)
        
        # Run multiple small tests
        test_results = []
        
        for i in range(2):
            config = TestConfiguration(
                test_name=f"report_test_{i+1}",
                test_type=TestType.LOAD,
                duration_seconds=3,
                concurrent_users=2,
                operations_per_second=20,
                database_path=db_path,
                test_data_size=5,
                ramp_up_seconds=1,
                ramp_down_seconds=1,
                think_time_ms=10,
                error_threshold_percent=20.0,
                response_time_threshold_ms=2000
            )
            
            result = framework.run_load_test(config)
            test_results.append(result)
        
        # Generate report
        print("  Generating performance report...")
        report = framework.generate_performance_report(test_results)
        
        # Verify report content
        assert len(report) > 0, "Empty report generated"
        assert "DATABASE LOAD TESTING PERFORMANCE REPORT" in report, "Missing report header"
        assert "TEST SUMMARY" in report, "Missing test summary"
        assert "DETAILED RESULTS" in report, "Missing detailed results"
        assert "PERFORMANCE RECOMMENDATIONS" in report, "Missing recommendations"
        
        # Verify test names appear in report
        for result in test_results:
            assert result.test_name in report, f"Test {result.test_name} not in report"
        
        print("  ✓ Report generated successfully")
        print(f"    - Report length: {len(report)} characters")
        print(f"    - Tests included: {len(test_results)}")
        
        # Test empty report
        empty_report = framework.generate_performance_report([])
        assert "No test results available" in empty_report, "Empty report not handled"
        
        print("✓ Report generation tests passed!")
        
    finally:
        shutil.rmtree(temp_dir)

def main():
    """Run all tests"""
    print("Starting Database Load Testing Framework Tests")
    print("=" * 60)
    
    try:
        test_trading_operation_simulator()
        test_load_testing_framework_basic()
        test_simple_load_test()
        test_standard_test_suites()
        test_performance_metrics()
        test_error_handling()
        test_report_generation()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED! 🎉")
        print("Database Load Testing Framework is working correctly!")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)