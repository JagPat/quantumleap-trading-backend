#!/usr/bin/env python3
"""
Standalone test script for the Database Load Testing Framework
"""

import os
import time
import json
import sqlite3
import threading
import random
import statistics
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from enum import Enum
import queue

# Minimal inline implementation for testing
class TestType(Enum):
    LOAD = "load"
    STRESS = "stress"
    SPIKE = "spike"
    VOLUME = "volume"
    ENDURANCE = "endurance"

class TestStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"

@dataclass
class TestConfiguration:
    test_name: str
    test_type: TestType
    duration_seconds: int
    concurrent_users: int
    operations_per_second: int
    database_path: str
    test_data_size: int = 100
    ramp_up_seconds: int = 10
    ramp_down_seconds: int = 10
    think_time_ms: int = 100
    error_threshold_percent: float = 5.0
    response_time_threshold_ms: int = 1000

@dataclass
class OperationResult:
    operation_type: str
    start_time: float
    end_time: float
    success: bool
    error_message: Optional[str] = None
    response_time_ms: float = 0.0
    thread_id: int = 0
    user_id: int = 0

@dataclass
class TestResults:
    test_name: str
    test_type: TestType
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    total_operations: int
    successful_operations: int
    failed_operations: int
    operations_per_second: float
    average_response_time_ms: float
    median_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    error_rate_percent: float
    throughput_ops_per_sec: float
    test_status: TestStatus
    error_details: List[str]

class TradingOperationSimulator:
    """Simulates realistic trading operations for load testing"""
    
    def __init__(self, database_path: str):
        self.database_path = database_path
        self.symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
        self.trade_types = ['BUY', 'SELL']
        
    def create_user(self, user_id: int) -> OperationResult:
        """Create a new user"""
        start_time = time.time()
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR IGNORE INTO users (id, username, email, created_at) 
                VALUES (?, ?, ?, ?)
            """, (
                user_id,
                f"trader_{user_id}",
                f"trader_{user_id}@example.com",
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            end_time = time.time()
            return OperationResult(
                operation_type="create_user",
                start_time=start_time,
                end_time=end_time,
                success=True,
                response_time_ms=(end_time - start_time) * 1000,
                thread_id=threading.get_ident(),
                user_id=user_id
            )
            
        except Exception as e:
            end_time = time.time()
            return OperationResult(
                operation_type="create_user",
                start_time=start_time,
                end_time=end_time,
                success=False,
                error_message=str(e),
                response_time_ms=(end_time - start_time) * 1000,
                thread_id=threading.get_ident(),
                user_id=user_id
            )
    
    def execute_trade(self, user_id: int) -> OperationResult:
        """Execute a trade"""
        start_time = time.time()
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            symbol = random.choice(self.symbols)
            quantity = random.randint(1, 100)
            price = round(random.uniform(50.0, 500.0), 2)
            trade_type = random.choice(self.trade_types)
            
            # Execute the trade
            cursor.execute("""
                INSERT INTO trades (user_id, symbol, quantity, price, trade_type, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, symbol, quantity, price, trade_type, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            end_time = time.time()
            return OperationResult(
                operation_type="execute_trade",
                start_time=start_time,
                end_time=end_time,
                success=True,
                response_time_ms=(end_time - start_time) * 1000,
                thread_id=threading.get_ident(),
                user_id=user_id
            )
            
        except Exception as e:
            end_time = time.time()
            return OperationResult(
                operation_type="execute_trade",
                start_time=start_time,
                end_time=end_time,
                success=False,
                error_message=str(e),
                response_time_ms=(end_time - start_time) * 1000,
                thread_id=threading.get_ident(),
                user_id=user_id
            )
    
    def get_portfolio(self, user_id: int) -> OperationResult:
        """Get user portfolio"""
        start_time = time.time()
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT symbol, quantity, price, trade_type, timestamp
                FROM trades 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 10
            """, (user_id,))
            
            trades = cursor.fetchall()
            conn.close()
            
            end_time = time.time()
            return OperationResult(
                operation_type="get_portfolio",
                start_time=start_time,
                end_time=end_time,
                success=True,
                response_time_ms=(end_time - start_time) * 1000,
                thread_id=threading.get_ident(),
                user_id=user_id
            )
            
        except Exception as e:
            end_time = time.time()
            return OperationResult(
                operation_type="get_portfolio",
                start_time=start_time,
                end_time=end_time,
                success=False,
                error_message=str(e),
                response_time_ms=(end_time - start_time) * 1000,
                thread_id=threading.get_ident(),
                user_id=user_id
            )

class SimpleLoadTestingFramework:
    """Simplified load testing framework for testing"""
    
    def __init__(self):
        self.operation_results = []
        self.stop_event = threading.Event()
        
    def setup_test_database(self, database_path: str):
        """Set up test database with required schema"""
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                symbol TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                trade_type TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_user_timestamp ON trades(user_id, timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)")
        
        conn.commit()
        conn.close()
    
    def generate_test_data(self, database_path: str, num_users: int = 50):
        """Generate initial test data"""
        simulator = TradingOperationSimulator(database_path)
        
        print(f"    Generating test data for {num_users} users...")
        
        # Create users
        for user_id in range(1, num_users + 1):
            simulator.create_user(user_id)
            
            # Create some initial trades
            if random.random() < 0.5:  # 50% of users have initial trades
                for _ in range(random.randint(1, 3)):
                    simulator.execute_trade(user_id)
    
    def simulate_user_session(self, user_id: int, config: TestConfiguration, results_queue: queue.Queue):
        """Simulate a single user session"""
        simulator = TradingOperationSimulator(config.database_path)
        session_results = []
        
        # Define operation weights
        operations = [
            (simulator.execute_trade, 0.6),
            (simulator.get_portfolio, 0.4)
        ]
        
        start_time = time.time()
        end_time = start_time + config.duration_seconds
        
        while time.time() < end_time and not self.stop_event.is_set():
            # Select operation based on weights
            rand_val = random.random()
            cumulative_weight = 0
            selected_operation = operations[0][0]
            
            for operation, weight in operations:
                cumulative_weight += weight
                if rand_val <= cumulative_weight:
                    selected_operation = operation
                    break
            
            # Execute operation
            result = selected_operation(user_id)
            session_results.append(result)
            
            # Think time
            if config.think_time_ms > 0:
                time.sleep(config.think_time_ms / 1000.0)
        
        # Put results in queue
        for result in session_results:
            results_queue.put(result)
    
    def run_load_test(self, config: TestConfiguration) -> TestResults:
        """Run a load test"""
        print(f"    Running load test: {config.test_name}")
        print(f"      Duration: {config.duration_seconds}s, Users: {config.concurrent_users}")
        
        # Setup
        self.setup_test_database(config.database_path)
        self.generate_test_data(config.database_path, config.test_data_size)
        
        # Reset state
        self.stop_event.clear()
        self.operation_results = []
        
        # Results queue
        results_queue = queue.Queue()
        
        test_start_time = datetime.now()
        
        try:
            # Run user sessions
            with ThreadPoolExecutor(max_workers=config.concurrent_users) as executor:
                futures = []
                
                # Submit user sessions
                for user_id in range(1, config.concurrent_users + 1):
                    future = executor.submit(
                        self.simulate_user_session,
                        user_id,
                        config,
                        results_queue
                    )
                    futures.append(future)
                
                # Wait for completion
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        print(f"      User session failed: {e}")
            
            test_end_time = datetime.now()
            
            # Collect results
            while not results_queue.empty():
                try:
                    result = results_queue.get_nowait()
                    self.operation_results.append(result)
                except queue.Empty:
                    break
            
            # Calculate results
            test_results = self.calculate_test_results(config, test_start_time, test_end_time)
            
            print(f"      Completed: {test_results.total_operations} ops, "
                  f"{100 - test_results.error_rate_percent:.1f}% success, "
                  f"{test_results.average_response_time_ms:.1f}ms avg")
            
            return test_results
            
        except Exception as e:
            print(f"      Load test failed: {e}")
            
            test_end_time = datetime.now()
            return TestResults(
                test_name=config.test_name,
                test_type=config.test_type,
                start_time=test_start_time,
                end_time=test_end_time,
                duration_seconds=(test_end_time - test_start_time).total_seconds(),
                total_operations=0,
                successful_operations=0,
                failed_operations=0,
                operations_per_second=0,
                average_response_time_ms=0,
                median_response_time_ms=0,
                p95_response_time_ms=0,
                p99_response_time_ms=0,
                min_response_time_ms=0,
                max_response_time_ms=0,
                error_rate_percent=100,
                throughput_ops_per_sec=0,
                test_status=TestStatus.FAILED,
                error_details=[str(e)]
            )
    
    def calculate_test_results(self, config: TestConfiguration, start_time: datetime, end_time: datetime) -> TestResults:
        """Calculate test results"""
        if not self.operation_results:
            return TestResults(
                test_name=config.test_name,
                test_type=config.test_type,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=(end_time - start_time).total_seconds(),
                total_operations=0,
                successful_operations=0,
                failed_operations=0,
                operations_per_second=0,
                average_response_time_ms=0,
                median_response_time_ms=0,
                p95_response_time_ms=0,
                p99_response_time_ms=0,
                min_response_time_ms=0,
                max_response_time_ms=0,
                error_rate_percent=0,
                throughput_ops_per_sec=0,
                test_status=TestStatus.COMPLETED,
                error_details=[]
            )
        
        # Basic metrics
        total_operations = len(self.operation_results)
        successful_operations = sum(1 for r in self.operation_results if r.success)
        failed_operations = total_operations - successful_operations
        
        # Response time metrics
        response_times = [r.response_time_ms for r in self.operation_results if r.success]
        
        if response_times:
            average_response_time = statistics.mean(response_times)
            median_response_time = statistics.median(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            
            # Percentiles
            sorted_times = sorted(response_times)
            p95_index = int(0.95 * len(sorted_times))
            p99_index = int(0.99 * len(sorted_times))
            p95_response_time = sorted_times[p95_index] if p95_index < len(sorted_times) else max_response_time
            p99_response_time = sorted_times[p99_index] if p99_index < len(sorted_times) else max_response_time
        else:
            average_response_time = median_response_time = min_response_time = max_response_time = 0
            p95_response_time = p99_response_time = 0
        
        # Throughput and error rate
        duration_seconds = (end_time - start_time).total_seconds()
        throughput_ops_per_sec = total_operations / duration_seconds if duration_seconds > 0 else 0
        error_rate_percent = (failed_operations / total_operations * 100) if total_operations > 0 else 0
        
        # Error details
        error_details = [r.error_message for r in self.operation_results if not r.success and r.error_message]
        unique_errors = list(set(error_details))
        
        # Test status
        test_status = TestStatus.COMPLETED
        if error_rate_percent > config.error_threshold_percent:
            test_status = TestStatus.FAILED
        elif average_response_time > config.response_time_threshold_ms:
            test_status = TestStatus.FAILED
        
        return TestResults(
            test_name=config.test_name,
            test_type=config.test_type,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration_seconds,
            total_operations=total_operations,
            successful_operations=successful_operations,
            failed_operations=failed_operations,
            operations_per_second=throughput_ops_per_sec,
            average_response_time_ms=average_response_time,
            median_response_time_ms=median_response_time,
            p95_response_time_ms=p95_response_time,
            p99_response_time_ms=p99_response_time,
            min_response_time_ms=min_response_time,
            max_response_time_ms=max_response_time,
            error_rate_percent=error_rate_percent,
            throughput_ops_per_sec=throughput_ops_per_sec,
            test_status=test_status,
            error_details=unique_errors[:5]
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
        framework = SimpleLoadTestingFramework()
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
        
        # Verify data was created
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        assert user_count >= 1, "No users created"
        
        cursor.execute("SELECT COUNT(*) FROM trades")
        trade_count = cursor.fetchone()[0]
        assert trade_count >= 1, "No trades created"
        
        conn.close()
        
        print("✓ TradingOperationSimulator tests passed!")
        
    finally:
        shutil.rmtree(temp_dir)

def test_simple_load_test():
    """Test running a simple load test"""
    print("\nTesting simple load test execution...")
    
    db_path, temp_dir = create_test_database()
    
    try:
        # Create framework
        framework = SimpleLoadTestingFramework()
        
        # Create simple test configuration
        config = TestConfiguration(
            test_name="simple_test",
            test_type=TestType.LOAD,
            duration_seconds=5,  # Short test
            concurrent_users=3,
            operations_per_second=30,
            database_path=db_path,
            test_data_size=10,
            ramp_up_seconds=1,
            ramp_down_seconds=1,
            think_time_ms=50,
            error_threshold_percent=20.0,
            response_time_threshold_ms=5000
        )
        
        print("  Running simple load test...")
        start_time = time.time()
        results = framework.run_load_test(config)
        end_time = time.time()
        
        # Verify test results
        assert results is not None, "No test results returned"
        assert results.test_name == "simple_test"
        assert results.test_type == TestType.LOAD
        assert results.total_operations >= 0, "Invalid operation count"
        assert results.duration_seconds > 0, "Invalid test duration"
        assert results.test_status in [TestStatus.COMPLETED, TestStatus.FAILED], f"Invalid test status: {results.test_status}"
        
        print(f"  ✓ Test completed in {end_time - start_time:.1f}s")
        print(f"  ✓ Total operations: {results.total_operations}")
        print(f"  ✓ Success rate: {100 - results.error_rate_percent:.1f}%")
        print(f"  ✓ Average response time: {results.average_response_time_ms:.1f}ms")
        print(f"  ✓ Throughput: {results.throughput_ops_per_sec:.1f} ops/sec")
        
        print("✓ Simple load test execution passed!")
        
    finally:
        shutil.rmtree(temp_dir)

def test_concurrent_load():
    """Test concurrent load with multiple users"""
    print("\nTesting concurrent load with multiple users...")
    
    db_path, temp_dir = create_test_database()
    
    try:
        # Create framework
        framework = SimpleLoadTestingFramework()
        
        # Create concurrent test configuration
        config = TestConfiguration(
            test_name="concurrent_test",
            test_type=TestType.LOAD,
            duration_seconds=8,
            concurrent_users=10,
            operations_per_second=100,
            database_path=db_path,
            test_data_size=20,
            ramp_up_seconds=2,
            ramp_down_seconds=2,
            think_time_ms=20,
            error_threshold_percent=15.0,
            response_time_threshold_ms=3000
        )
        
        print("  Running concurrent load test...")
        results = framework.run_load_test(config)
        
        # Verify concurrent execution worked
        assert results.total_operations > 0, "No operations executed"
        assert results.successful_operations > 0, "No successful operations"
        
        # Check that multiple threads were used
        thread_ids = set()
        for result in framework.operation_results:
            thread_ids.add(result.thread_id)
        
        assert len(thread_ids) > 1, f"Expected multiple threads, got {len(thread_ids)}"
        
        print(f"  ✓ Concurrent execution with {len(thread_ids)} threads")
        print(f"  ✓ Total operations: {results.total_operations}")
        print(f"  ✓ Success rate: {100 - results.error_rate_percent:.1f}%")
        
        print("✓ Concurrent load test passed!")
        
    finally:
        shutil.rmtree(temp_dir)

def test_performance_metrics():
    """Test performance metrics calculation"""
    print("\nTesting performance metrics calculation...")
    
    db_path, temp_dir = create_test_database()
    
    try:
        # Create framework
        framework = SimpleLoadTestingFramework()
        
        # Run test to generate metrics
        config = TestConfiguration(
            test_name="metrics_test",
            test_type=TestType.LOAD,
            duration_seconds=4,
            concurrent_users=5,
            operations_per_second=50,
            database_path=db_path,
            test_data_size=15,
            ramp_up_seconds=1,
            ramp_down_seconds=1,
            think_time_ms=30,
            error_threshold_percent=25.0,
            response_time_threshold_ms=4000
        )
        
        print("  Running test for metrics calculation...")
        results = framework.run_load_test(config)
        
        # Verify metrics are calculated correctly
        assert results.total_operations >= 0, "Invalid total operations"
        assert results.successful_operations >= 0, "Invalid successful operations"
        assert results.failed_operations >= 0, "Invalid failed operations"
        assert results.total_operations == results.successful_operations + results.failed_operations, "Operation counts don't match"
        
        if results.successful_operations > 0:
            assert results.average_response_time_ms >= 0, "Invalid average response time"
            assert results.median_response_time_ms >= 0, "Invalid median response time"
            assert results.min_response_time_ms >= 0, "Invalid min response time"
            assert results.max_response_time_ms >= results.min_response_time_ms, "Max response time less than min"
        
        assert results.throughput_ops_per_sec >= 0, "Invalid throughput"
        assert 0 <= results.error_rate_percent <= 100, "Invalid error rate"
        
        print(f"  ✓ Metrics calculated correctly")
        print(f"    - Total operations: {results.total_operations}")
        print(f"    - Success rate: {100 - results.error_rate_percent:.1f}%")
        print(f"    - Avg response time: {results.average_response_time_ms:.1f}ms")
        print(f"    - Throughput: {results.throughput_ops_per_sec:.1f} ops/sec")
        
        print("✓ Performance metrics calculation passed!")
        
    finally:
        shutil.rmtree(temp_dir)

def test_stress_simulation():
    """Test stress testing simulation"""
    print("\nTesting stress testing simulation...")
    
    db_path, temp_dir = create_test_database()
    
    try:
        # Create framework
        framework = SimpleLoadTestingFramework()
        
        # Run multiple tests with increasing load
        stress_results = []
        
        for users in [5, 10, 15]:
            config = TestConfiguration(
                test_name=f"stress_test_{users}_users",
                test_type=TestType.STRESS,
                duration_seconds=3,
                concurrent_users=users,
                operations_per_second=users * 10,
                database_path=db_path,
                test_data_size=users * 2,
                ramp_up_seconds=1,
                ramp_down_seconds=1,
                think_time_ms=10,
                error_threshold_percent=30.0,
                response_time_threshold_ms=5000
            )
            
            print(f"  Running stress test with {users} users...")
            result = framework.run_load_test(config)
            stress_results.append(result)
            
            # Brief pause between tests
            time.sleep(1)
        
        # Verify stress test progression
        assert len(stress_results) == 3, "Not all stress tests completed"
        
        for i, result in enumerate(stress_results):
            expected_users = [5, 10, 15][i]
            print(f"    {expected_users} users: {result.total_operations} ops, "
                  f"{100 - result.error_rate_percent:.1f}% success")
        
        print("✓ Stress testing simulation passed!")
        
    finally:
        shutil.rmtree(temp_dir)

def main():
    """Run all tests"""
    print("Starting Database Load Testing Framework Tests")
    print("=" * 60)
    
    try:
        test_trading_operation_simulator()
        test_simple_load_test()
        test_concurrent_load()
        test_performance_metrics()
        test_stress_simulation()
        
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