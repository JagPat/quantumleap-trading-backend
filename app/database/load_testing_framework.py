"""
Database Load Testing Framework
Implements comprehensive load testing suite that simulates high-frequency trading operations
with concurrent user simulation, performance benchmarking, and stress testing scenarios.
"""

import os
import time
import json
import sqlite3
import threading
import multiprocessing
import random
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from pathlib import Path
import logging
from enum import Enum
import queue
import psutil

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
    test_data_size: int = 1000
    ramp_up_seconds: int = 30
    ramp_down_seconds: int = 30
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
    cpu_usage_percent: float
    memory_usage_mb: float
    database_size_mb: float
    test_status: TestStatus
    error_details: List[str]

class TradingOperationSimulator:
    """
    Simulates realistic trading operations for load testing
    """
    
    def __init__(self, database_path: str):
        self.database_path = database_path
        self.symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 'CRM', 'ORCL']
        self.trade_types = ['BUY', 'SELL']
        self.order_types = ['MARKET', 'LIMIT', 'STOP']
        
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
    
    def place_order(self, user_id: int) -> OperationResult:
        """Place a trading order"""
        start_time = time.time()
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            symbol = random.choice(self.symbols)
            quantity = random.randint(1, 1000)
            price = round(random.uniform(50.0, 500.0), 2)
            order_type = random.choice(self.order_types)
            trade_type = random.choice(self.trade_types)
            
            cursor.execute("""
                INSERT INTO orders (user_id, symbol, quantity, price, order_type, trade_type, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?)
            """, (user_id, symbol, quantity, price, order_type, trade_type, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            end_time = time.time()
            return OperationResult(
                operation_type="place_order",
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
                operation_type="place_order",
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
            
            # Get a pending order
            cursor.execute("""
                SELECT id, symbol, quantity, price, trade_type 
                FROM orders 
                WHERE user_id = ? AND status = 'PENDING' 
                ORDER BY created_at ASC 
                LIMIT 1
            """, (user_id,))
            
            order = cursor.fetchone()
            if not order:
                # Create a new order if none exists
                symbol = random.choice(self.symbols)
                quantity = random.randint(1, 100)
                price = round(random.uniform(50.0, 500.0), 2)
                trade_type = random.choice(self.trade_types)
                
                cursor.execute("""
                    INSERT INTO orders (user_id, symbol, quantity, price, order_type, trade_type, status, created_at)
                    VALUES (?, ?, ?, ?, 'MARKET', ?, 'PENDING', ?)
                """, (user_id, symbol, quantity, price, trade_type, datetime.now().isoformat()))
                
                order_id = cursor.lastrowid
            else:
                order_id, symbol, quantity, price, trade_type = order
            
            # Execute the trade
            cursor.execute("""
                INSERT INTO trades (user_id, symbol, quantity, price, trade_type, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, symbol, quantity, price, trade_type, datetime.now().isoformat()))
            
            # Update order status
            cursor.execute("""
                UPDATE orders SET status = 'FILLED', updated_at = ? WHERE id = ?
            """, (datetime.now().isoformat(), order_id if 'order_id' in locals() else order[0]))
            
            # Update portfolio
            cursor.execute("""
                INSERT OR REPLACE INTO portfolio (user_id, symbol, quantity, avg_price, updated_at)
                VALUES (?, ?, 
                    COALESCE((SELECT quantity FROM portfolio WHERE user_id = ? AND symbol = ?), 0) + ?,
                    ?, ?)
            """, (user_id, symbol, user_id, symbol, quantity if trade_type == 'BUY' else -quantity, price, datetime.now().isoformat()))
            
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
                SELECT symbol, quantity, avg_price, updated_at
                FROM portfolio 
                WHERE user_id = ? AND quantity > 0
            """, (user_id,))
            
            portfolio = cursor.fetchall()
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
    
    def get_trade_history(self, user_id: int) -> OperationResult:
        """Get user trade history"""
        start_time = time.time()
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT symbol, quantity, price, trade_type, timestamp
                FROM trades 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 100
            """, (user_id,))
            
            trades = cursor.fetchall()
            conn.close()
            
            end_time = time.time()
            return OperationResult(
                operation_type="get_trade_history",
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
                operation_type="get_trade_history",
                start_time=start_time,
                end_time=end_time,
                success=False,
                error_message=str(e),
                response_time_ms=(end_time - start_time) * 1000,
                thread_id=threading.get_ident(),
                user_id=user_id
            )

class LoadTestingFramework:
    """
    Comprehensive load testing framework for database operations
    """
    
    def __init__(self, results_directory: str = "load_test_results"):
        self.results_directory = Path(results_directory)
        self.results_directory.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        self.current_test = None
        self.test_results = []
        self.operation_results = []
        self.stop_event = threading.Event()
        
        # Performance monitoring
        self.cpu_samples = []
        self.memory_samples = []
        
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
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                symbol TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                avg_price REAL NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, symbol)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                symbol TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                order_type TEXT NOT NULL,
                trade_type TEXT NOT NULL,
                status TEXT DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
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
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_user_symbol ON portfolio(user_id, symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_user_status ON orders(user_id, status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_user_timestamp ON trades(user_id, timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)")
        
        conn.commit()
        conn.close()
    
    def generate_test_data(self, database_path: str, num_users: int = 1000):
        """Generate initial test data"""
        simulator = TradingOperationSimulator(database_path)
        
        print(f"Generating test data for {num_users} users...")
        
        # Create users
        for user_id in range(1, num_users + 1):
            simulator.create_user(user_id)
            
            # Create some initial portfolio positions
            if random.random() < 0.7:  # 70% of users have initial positions
                for _ in range(random.randint(1, 5)):
                    simulator.execute_trade(user_id)
        
        print(f"Test data generation completed for {num_users} users")
    
    def simulate_user_session(self, user_id: int, config: TestConfiguration, results_queue: queue.Queue):
        """Simulate a single user session"""
        simulator = TradingOperationSimulator(config.database_path)
        session_results = []
        
        # Define operation weights (probability distribution)
        operations = [
            (simulator.place_order, 0.3),
            (simulator.execute_trade, 0.4),
            (simulator.get_portfolio, 0.2),
            (simulator.get_trade_history, 0.1)
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
    
    def monitor_system_resources(self, duration_seconds: int):
        """Monitor system resources during test"""
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        while time.time() < end_time and not self.stop_event.is_set():
            # Sample CPU and memory usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_info = psutil.virtual_memory()
            
            self.cpu_samples.append(cpu_percent)
            self.memory_samples.append(memory_info.used / (1024 * 1024))  # MB
            
            time.sleep(1)
    
    def run_load_test(self, config: TestConfiguration) -> TestResults:
        """Run a comprehensive load test"""
        print(f"Starting load test: {config.test_name}")
        print(f"Test type: {config.test_type.value}")
        print(f"Duration: {config.duration_seconds}s")
        print(f"Concurrent users: {config.concurrent_users}")
        print(f"Target ops/sec: {config.operations_per_second}")
        
        # Setup
        self.setup_test_database(config.database_path)
        self.generate_test_data(config.database_path, config.test_data_size)
        
        # Reset state
        self.stop_event.clear()
        self.operation_results = []
        self.cpu_samples = []
        self.memory_samples = []
        
        # Results queue for collecting operation results
        results_queue = queue.Queue()
        
        # Start system monitoring
        monitor_thread = threading.Thread(
            target=self.monitor_system_resources,
            args=(config.duration_seconds + config.ramp_up_seconds + config.ramp_down_seconds,)
        )
        monitor_thread.start()
        
        test_start_time = datetime.now()
        
        try:
            # Ramp up phase
            print("Ramp up phase...")
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
                    
                    # Gradual ramp up
                    if config.ramp_up_seconds > 0:
                        time.sleep(config.ramp_up_seconds / config.concurrent_users)
                
                # Wait for all sessions to complete
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        self.logger.error(f"User session failed: {e}")
            
            test_end_time = datetime.now()
            
            # Collect results from queue
            while not results_queue.empty():
                try:
                    result = results_queue.get_nowait()
                    self.operation_results.append(result)
                except queue.Empty:
                    break
            
            # Stop monitoring
            self.stop_event.set()
            monitor_thread.join()
            
            # Calculate test results
            test_results = self.calculate_test_results(
                config, test_start_time, test_end_time
            )
            
            # Save results
            self.save_test_results(test_results)
            
            print(f"Load test completed: {config.test_name}")
            print(f"Total operations: {test_results.total_operations}")
            print(f"Success rate: {100 - test_results.error_rate_percent:.2f}%")
            print(f"Average response time: {test_results.average_response_time_ms:.2f}ms")
            print(f"Throughput: {test_results.throughput_ops_per_sec:.2f} ops/sec")
            
            return test_results
            
        except Exception as e:
            self.stop_event.set()
            self.logger.error(f"Load test failed: {e}")
            
            test_end_time = datetime.now()
            test_results = TestResults(
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
                cpu_usage_percent=0,
                memory_usage_mb=0,
                database_size_mb=0,
                test_status=TestStatus.FAILED,
                error_details=[str(e)]
            )
            
            return test_results
    
    def calculate_test_results(self, config: TestConfiguration, start_time: datetime, end_time: datetime) -> TestResults:
        """Calculate comprehensive test results"""
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
                cpu_usage_percent=0,
                memory_usage_mb=0,
                database_size_mb=0,
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
        
        # System resource usage
        avg_cpu_usage = statistics.mean(self.cpu_samples) if self.cpu_samples else 0
        avg_memory_usage = statistics.mean(self.memory_samples) if self.memory_samples else 0
        
        # Database size
        database_size_mb = 0
        try:
            if os.path.exists(config.database_path):
                database_size_mb = os.path.getsize(config.database_path) / (1024 * 1024)
        except Exception:
            pass
        
        # Error details
        error_details = [r.error_message for r in self.operation_results if not r.success and r.error_message]
        unique_errors = list(set(error_details))
        
        # Determine test status
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
            cpu_usage_percent=avg_cpu_usage,
            memory_usage_mb=avg_memory_usage,
            database_size_mb=database_size_mb,
            test_status=test_status,
            error_details=unique_errors[:10]  # Limit to first 10 unique errors
        )
    
    def save_test_results(self, results: TestResults):
        """Save test results to file"""
        timestamp = results.start_time.strftime("%Y%m%d_%H%M%S")
        filename = f"{results.test_name}_{timestamp}.json"
        filepath = self.results_directory / filename
        
        # Convert to serializable format
        results_dict = asdict(results)
        results_dict['start_time'] = results.start_time.isoformat()
        results_dict['end_time'] = results.end_time.isoformat()
        results_dict['test_type'] = results.test_type.value
        results_dict['test_status'] = results.test_status.value
        
        with open(filepath, 'w') as f:
            json.dump(results_dict, f, indent=2)
        
        print(f"Test results saved to: {filepath}")
    
    def run_stress_test(self, database_path: str, max_users: int = 1000, step_size: int = 50) -> List[TestResults]:
        """Run progressive stress test with increasing load"""
        print(f"Starting stress test with max {max_users} users")
        
        stress_results = []
        
        for concurrent_users in range(step_size, max_users + 1, step_size):
            config = TestConfiguration(
                test_name=f"stress_test_{concurrent_users}_users",
                test_type=TestType.STRESS,
                duration_seconds=60,  # 1 minute per step
                concurrent_users=concurrent_users,
                operations_per_second=concurrent_users * 10,  # 10 ops per user per second
                database_path=database_path,
                test_data_size=concurrent_users,
                ramp_up_seconds=10,
                ramp_down_seconds=5,
                think_time_ms=50,
                error_threshold_percent=10.0,  # Higher threshold for stress test
                response_time_threshold_ms=2000
            )
            
            print(f"Running stress test with {concurrent_users} concurrent users...")
            result = self.run_load_test(config)
            stress_results.append(result)
            
            # Stop if error rate is too high
            if result.error_rate_percent > 50:
                print(f"Stopping stress test due to high error rate: {result.error_rate_percent:.2f}%")
                break
            
            # Brief pause between tests
            time.sleep(5)
        
        return stress_results
    
    def run_endurance_test(self, database_path: str, duration_hours: int = 1) -> TestResults:
        """Run endurance test for extended duration"""
        config = TestConfiguration(
            test_name=f"endurance_test_{duration_hours}h",
            test_type=TestType.ENDURANCE,
            duration_seconds=duration_hours * 3600,
            concurrent_users=50,
            operations_per_second=500,
            database_path=database_path,
            test_data_size=1000,
            ramp_up_seconds=60,
            ramp_down_seconds=60,
            think_time_ms=100,
            error_threshold_percent=5.0,
            response_time_threshold_ms=1000
        )
        
        print(f"Starting endurance test for {duration_hours} hour(s)")
        return self.run_load_test(config)
    
    def run_spike_test(self, database_path: str) -> TestResults:
        """Run spike test with sudden load increase"""
        config = TestConfiguration(
            test_name="spike_test",
            test_type=TestType.SPIKE,
            duration_seconds=300,  # 5 minutes
            concurrent_users=200,
            operations_per_second=2000,
            database_path=database_path,
            test_data_size=500,
            ramp_up_seconds=5,  # Very fast ramp up
            ramp_down_seconds=5,
            think_time_ms=10,  # Very low think time
            error_threshold_percent=15.0,
            response_time_threshold_ms=3000
        )
        
        print("Starting spike test with sudden load increase")
        return self.run_load_test(config)
    
    def generate_performance_report(self, results_list: List[TestResults]) -> str:
        """Generate comprehensive performance report"""
        if not results_list:
            return "No test results available for report generation."
        
        report = []
        report.append("=" * 80)
        report.append("DATABASE LOAD TESTING PERFORMANCE REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total Tests: {len(results_list)}")
        report.append("")
        
        # Summary table
        report.append("TEST SUMMARY")
        report.append("-" * 80)
        report.append(f"{'Test Name':<30} {'Status':<12} {'Ops/Sec':<10} {'Avg RT(ms)':<12} {'Error %':<10}")
        report.append("-" * 80)
        
        for result in results_list:
            report.append(f"{result.test_name:<30} {result.test_status.value:<12} "
                         f"{result.throughput_ops_per_sec:<10.1f} {result.average_response_time_ms:<12.1f} "
                         f"{result.error_rate_percent:<10.2f}")
        
        report.append("")
        
        # Detailed results
        for result in results_list:
            report.append(f"DETAILED RESULTS: {result.test_name}")
            report.append("-" * 50)
            report.append(f"Test Type: {result.test_type.value}")
            report.append(f"Duration: {result.duration_seconds:.1f} seconds")
            report.append(f"Total Operations: {result.total_operations:,}")
            report.append(f"Successful Operations: {result.successful_operations:,}")
            report.append(f"Failed Operations: {result.failed_operations:,}")
            report.append(f"Success Rate: {100 - result.error_rate_percent:.2f}%")
            report.append(f"Throughput: {result.throughput_ops_per_sec:.2f} ops/sec")
            report.append("")
            report.append("Response Time Statistics:")
            report.append(f"  Average: {result.average_response_time_ms:.2f}ms")
            report.append(f"  Median: {result.median_response_time_ms:.2f}ms")
            report.append(f"  95th Percentile: {result.p95_response_time_ms:.2f}ms")
            report.append(f"  99th Percentile: {result.p99_response_time_ms:.2f}ms")
            report.append(f"  Min: {result.min_response_time_ms:.2f}ms")
            report.append(f"  Max: {result.max_response_time_ms:.2f}ms")
            report.append("")
            report.append("System Resources:")
            report.append(f"  Average CPU Usage: {result.cpu_usage_percent:.1f}%")
            report.append(f"  Average Memory Usage: {result.memory_usage_mb:.1f} MB")
            report.append(f"  Database Size: {result.database_size_mb:.2f} MB")
            report.append("")
            
            if result.error_details:
                report.append("Error Details:")
                for error in result.error_details[:5]:  # Show first 5 errors
                    report.append(f"  - {error}")
                report.append("")
            
            report.append("")
        
        # Performance recommendations
        report.append("PERFORMANCE RECOMMENDATIONS")
        report.append("-" * 50)
        
        avg_response_time = statistics.mean([r.average_response_time_ms for r in results_list])
        avg_throughput = statistics.mean([r.throughput_ops_per_sec for r in results_list])
        avg_error_rate = statistics.mean([r.error_rate_percent for r in results_list])
        
        if avg_response_time > 1000:
            report.append("⚠️  High average response time detected. Consider:")
            report.append("   - Adding database indexes")
            report.append("   - Optimizing query performance")
            report.append("   - Increasing database connection pool size")
        
        if avg_error_rate > 5:
            report.append("⚠️  High error rate detected. Consider:")
            report.append("   - Reviewing database connection handling")
            report.append("   - Implementing better error recovery")
            report.append("   - Checking database resource limits")
        
        if avg_throughput < 100:
            report.append("⚠️  Low throughput detected. Consider:")
            report.append("   - Database performance tuning")
            report.append("   - Connection pooling optimization")
            report.append("   - Hardware resource scaling")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)

# Predefined test configurations
class StandardTestSuites:
    """Standard test suite configurations"""
    
    @staticmethod
    def get_basic_load_test(database_path: str) -> TestConfiguration:
        return TestConfiguration(
            test_name="basic_load_test",
            test_type=TestType.LOAD,
            duration_seconds=300,  # 5 minutes
            concurrent_users=50,
            operations_per_second=500,
            database_path=database_path,
            test_data_size=1000,
            ramp_up_seconds=30,
            ramp_down_seconds=30,
            think_time_ms=100,
            error_threshold_percent=5.0,
            response_time_threshold_ms=1000
        )
    
    @staticmethod
    def get_high_frequency_trading_test(database_path: str) -> TestConfiguration:
        return TestConfiguration(
            test_name="hft_simulation",
            test_type=TestType.LOAD,
            duration_seconds=600,  # 10 minutes
            concurrent_users=100,
            operations_per_second=2000,
            database_path=database_path,
            test_data_size=2000,
            ramp_up_seconds=60,
            ramp_down_seconds=60,
            think_time_ms=10,  # Very low latency
            error_threshold_percent=2.0,  # Strict error tolerance
            response_time_threshold_ms=500  # Strict response time
        )
    
    @staticmethod
    def get_volume_test(database_path: str) -> TestConfiguration:
        return TestConfiguration(
            test_name="volume_test",
            test_type=TestType.VOLUME,
            duration_seconds=1800,  # 30 minutes
            concurrent_users=200,
            operations_per_second=1000,
            database_path=database_path,
            test_data_size=5000,
            ramp_up_seconds=120,
            ramp_down_seconds=120,
            think_time_ms=50,
            error_threshold_percent=5.0,
            response_time_threshold_ms=1500
        )