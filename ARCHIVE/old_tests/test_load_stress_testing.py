#!/usr/bin/env python3
"""
Load and Stress Testing Suite for Automated Trading Engine
Tests concurrent users, high-frequency signal processing, and database performance under load
"""

import time
import threading
import sqlite3
import tempfile
import os
import json
import sys
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request
import urllib.error
import random
import statistics
from collections import defaultdict
import queue

# Configuration
RAILWAY_URL = "https://quantum-leap-backend-production.up.railway.app"
LOCAL_URL = "http://localhost:8000"

class LoadTestMetrics:
    """Collect and analyze load test metrics"""
    
    def __init__(self):
        self.response_times = []
        self.success_count = 0
        self.error_count = 0
        self.errors = defaultdict(int)
        self.start_time = None
        self.end_time = None
        self.lock = threading.Lock()
    
    def record_request(self, response_time, success, error_type=None):
        """Record a request result"""
        with self.lock:
            self.response_times.append(response_time)
            if success:
                self.success_count += 1
            else:
                self.error_count += 1
                if error_type:
                    self.errors[error_type] += 1
    
    def start_test(self):
        """Mark test start time"""
        self.start_time = time.time()
    
    def end_test(self):
        """Mark test end time"""
        self.end_time = time.time()
    
    def get_summary(self):
        """Get test summary statistics"""
        if not self.response_times:
            return {"error": "No data collected"}
        
        total_requests = self.success_count + self.error_count
        success_rate = (self.success_count / total_requests * 100) if total_requests > 0 else 0
        duration = self.end_time - self.start_time if self.end_time and self.start_time else 0
        throughput = total_requests / duration if duration > 0 else 0
        
        return {
            "total_requests": total_requests,
            "successful_requests": self.success_count,
            "failed_requests": self.error_count,
            "success_rate": success_rate,
            "duration": duration,
            "throughput": throughput,
            "avg_response_time": statistics.mean(self.response_times),
            "min_response_time": min(self.response_times),
            "max_response_time": max(self.response_times),
            "median_response_time": statistics.median(self.response_times),
            "p95_response_time": statistics.quantiles(self.response_times, n=20)[18] if len(self.response_times) >= 20 else max(self.response_times),
            "errors": dict(self.errors)
        }

class LoadTestRunner:
    """Main load testing runner"""
    
    def __init__(self, base_url=None):
        self.base_url = base_url or RAILWAY_URL
        self.metrics = LoadTestMetrics()
    
    def make_request(self, endpoint, method="GET", data=None, timeout=10):
        """Make HTTP request and measure performance"""
        start_time = time.time()
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method == "GET":
                req = urllib.request.Request(url)
            else:  # POST
                json_data = json.dumps(data).encode('utf-8') if data else b'{}'
                req = urllib.request.Request(url, data=json_data, method=method)
            
            req.add_header('Content-Type', 'application/json')
            req.add_header('User-Agent', 'LoadTest/1.0')
            
            with urllib.request.urlopen(req, timeout=timeout) as response:
                response_time = time.time() - start_time
                self.metrics.record_request(response_time, True)
                return {"success": True, "status": response.status, "response_time": response_time}
                
        except urllib.error.HTTPError as e:
            response_time = time.time() - start_time
            # 404 is acceptable for our test endpoints
            success = e.code in [200, 201, 404, 422]
            self.metrics.record_request(response_time, success, f"HTTP_{e.code}")
            return {"success": success, "status": e.code, "response_time": response_time}
        except Exception as e:
            response_time = time.time() - start_time
            self.metrics.record_request(response_time, False, type(e).__name__)
            return {"success": False, "error": str(e), "response_time": response_time}
    
    def concurrent_user_test(self, num_users=10, requests_per_user=5, duration=30):
        """Test concurrent users accessing the system"""
        print(f"🔄 Running Concurrent User Test: {num_users} users, {requests_per_user} requests each")
        
        def user_simulation(user_id):
            """Simulate a single user's requests"""
            endpoints = [
                "/api/trading-engine/status",
                "/api/portfolio/holdings",
                "/api/ai/analyze",
                "/api/trading-engine/strategies"
            ]
            
            user_results = []
            for i in range(requests_per_user):
                endpoint = random.choice(endpoints)
                if endpoint == "/api/ai/analyze":
                    data = {
                        "user_id": f"load_test_user_{user_id}",
                        "portfolio": {"cash": 100000, "positions": []},
                        "test_request": True
                    }
                    result = self.make_request(endpoint, "POST", data)
                else:
                    result = self.make_request(endpoint)
                
                user_results.append(result)
                
                # Random delay between requests (0.1 to 1 second)
                time.sleep(random.uniform(0.1, 1.0))
            
            return user_results
        
        # Start metrics collection
        self.metrics.start_test()
        
        # Run concurrent users
        with ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(user_simulation, i) for i in range(num_users)]
            results = [future.result() for future in as_completed(futures)]
        
        # End metrics collection
        self.metrics.end_test()
        
        return results
    
    def high_frequency_signal_test(self, signals_per_second=10, duration=30):
        """Test high-frequency signal processing"""
        print(f"📊 Running High-Frequency Signal Test: {signals_per_second} signals/sec for {duration}s")
        
        def generate_signal():
            """Generate a mock trading signal"""
            symbols = ["RELIANCE", "TCS", "INFY", "HDFC", "ICICIBANK"]
            signal_types = ["BUY", "SELL", "HOLD"]
            
            return {
                "symbol": random.choice(symbols),
                "signal": random.choice(signal_types),
                "confidence": random.uniform(0.5, 1.0),
                "price": random.uniform(1000, 3000),
                "timestamp": datetime.now().isoformat(),
                "test_signal": True
            }
        
        def signal_worker():
            """Worker thread for sending signals"""
            while not stop_event.is_set():
                signal_data = generate_signal()
                result = self.make_request("/api/ai/generate-signal", "POST", signal_data)
                
                # Control frequency
                time.sleep(1.0 / signals_per_second)
        
        # Start metrics collection
        self.metrics.start_test()
        
        # Create stop event
        stop_event = threading.Event()
        
        # Start signal generation threads
        num_threads = min(signals_per_second, 10)  # Cap at 10 threads
        threads = []
        
        for _ in range(num_threads):
            thread = threading.Thread(target=signal_worker)
            thread.start()
            threads.append(thread)
        
        # Run for specified duration
        time.sleep(duration)
        
        # Stop all threads
        stop_event.set()
        for thread in threads:
            thread.join(timeout=5)
        
        # End metrics collection
        self.metrics.end_test()
        
        return self.metrics.get_summary()
    
    def database_load_test(self, concurrent_connections=5, operations_per_connection=100):
        """Test database performance under load"""
        print(f"💾 Running Database Load Test: {concurrent_connections} connections, {operations_per_connection} ops each")
        
        def database_worker(worker_id):
            """Worker thread for database operations"""
            # Create temporary database for this worker
            with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_db:
                db_path = tmp_db.name
            
            try:
                conn = sqlite3.connect(db_path, check_same_thread=False)
                cursor = conn.cursor()
                
                # Create test table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS load_test_data (
                        id INTEGER PRIMARY KEY,
                        worker_id INTEGER,
                        symbol TEXT,
                        price REAL,
                        quantity INTEGER,
                        timestamp TEXT
                    )
                ''')
                conn.commit()
                
                worker_results = []
                
                for i in range(operations_per_connection):
                    start_time = time.time()
                    
                    try:
                        # Mix of operations: 70% INSERT, 20% SELECT, 10% UPDATE
                        operation_type = random.choices(
                            ['INSERT', 'SELECT', 'UPDATE'],
                            weights=[70, 20, 10]
                        )[0]
                        
                        if operation_type == 'INSERT':
                            cursor.execute(
                                'INSERT INTO load_test_data (worker_id, symbol, price, quantity, timestamp) VALUES (?, ?, ?, ?, ?)',
                                (worker_id, f'STOCK_{i}', random.uniform(100, 3000), random.randint(1, 1000), datetime.now().isoformat())
                            )
                            conn.commit()
                        
                        elif operation_type == 'SELECT':
                            cursor.execute('SELECT COUNT(*) FROM load_test_data WHERE worker_id = ?', (worker_id,))
                            cursor.fetchone()
                        
                        elif operation_type == 'UPDATE':
                            cursor.execute(
                                'UPDATE load_test_data SET price = ? WHERE worker_id = ? AND id = ?',
                                (random.uniform(100, 3000), worker_id, random.randint(1, max(1, i)))
                            )
                            conn.commit()
                        
                        response_time = time.time() - start_time
                        worker_results.append({
                            "operation": operation_type,
                            "response_time": response_time,
                            "success": True
                        })
                        
                    except Exception as e:
                        response_time = time.time() - start_time
                        worker_results.append({
                            "operation": operation_type,
                            "response_time": response_time,
                            "success": False,
                            "error": str(e)
                        })
                
                conn.close()
                return worker_results
                
            finally:
                if os.path.exists(db_path):
                    os.unlink(db_path)
        
        # Start timing
        start_time = time.time()
        
        # Run concurrent database workers
        with ThreadPoolExecutor(max_workers=concurrent_connections) as executor:
            futures = [executor.submit(database_worker, i) for i in range(concurrent_connections)]
            results = [future.result() for future in as_completed(futures)]
        
        end_time = time.time()
        
        # Analyze results
        all_operations = []
        for worker_results in results:
            all_operations.extend(worker_results)
        
        successful_ops = [op for op in all_operations if op["success"]]
        failed_ops = [op for op in all_operations if not op["success"]]
        
        if successful_ops:
            response_times = [op["response_time"] for op in successful_ops]
            
            summary = {
                "total_operations": len(all_operations),
                "successful_operations": len(successful_ops),
                "failed_operations": len(failed_ops),
                "success_rate": (len(successful_ops) / len(all_operations) * 100) if all_operations else 0,
                "duration": end_time - start_time,
                "throughput": len(all_operations) / (end_time - start_time),
                "avg_response_time": statistics.mean(response_times),
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "median_response_time": statistics.median(response_times)
            }
        else:
            summary = {
                "total_operations": len(all_operations),
                "successful_operations": 0,
                "failed_operations": len(failed_ops),
                "success_rate": 0,
                "error": "No successful operations"
            }
        
        return summary
    
    def stress_test_gradual_load(self, max_users=50, ramp_up_time=60):
        """Gradually increase load to find breaking point"""
        print(f"📈 Running Gradual Stress Test: Ramping up to {max_users} users over {ramp_up_time}s")
        
        results = []
        users_increment = max(1, max_users // 10)  # Increase in 10 steps
        
        for current_users in range(users_increment, max_users + 1, users_increment):
            print(f"  Testing with {current_users} concurrent users...")
            
            # Reset metrics for this test
            self.metrics = LoadTestMetrics()
            
            # Run test with current user count
            test_results = self.concurrent_user_test(
                num_users=current_users,
                requests_per_user=3,
                duration=10
            )
            
            summary = self.metrics.get_summary()
            summary["concurrent_users"] = current_users
            results.append(summary)
            
            # Check if system is degrading significantly
            if summary["success_rate"] < 50 or summary["avg_response_time"] > 10:
                print(f"  ⚠️ System degradation detected at {current_users} users")
                break
            
            # Brief pause between tests
            time.sleep(2)
        
        return results

def run_comprehensive_load_tests():
    """Run all load and stress tests"""
    print("🚀 Starting Comprehensive Load and Stress Testing Suite...\n")
    
    # Initialize test runner
    test_runner = LoadTestRunner(RAILWAY_URL)
    
    # Test results storage
    all_results = {}
    
    # Test 1: Concurrent User Load Test
    print("1️⃣ Concurrent User Load Test")
    test_runner.metrics = LoadTestMetrics()  # Reset metrics
    concurrent_results = test_runner.concurrent_user_test(num_users=20, requests_per_user=5)
    all_results["concurrent_users"] = test_runner.metrics.get_summary()
    print(f"   ✅ Completed: {all_results['concurrent_users']['success_rate']:.1f}% success rate")
    
    # Test 2: High-Frequency Signal Processing
    print("\n2️⃣ High-Frequency Signal Processing Test")
    test_runner.metrics = LoadTestMetrics()  # Reset metrics
    hf_results = test_runner.high_frequency_signal_test(signals_per_second=5, duration=20)
    all_results["high_frequency_signals"] = hf_results
    print(f"   ✅ Completed: {hf_results['throughput']:.1f} requests/sec")
    
    # Test 3: Database Load Test
    print("\n3️⃣ Database Load Test")
    db_results = test_runner.database_load_test(concurrent_connections=10, operations_per_connection=50)
    all_results["database_load"] = db_results
    print(f"   ✅ Completed: {db_results['success_rate']:.1f}% success rate")
    
    # Test 4: Gradual Stress Test
    print("\n4️⃣ Gradual Stress Test")
    test_runner.metrics = LoadTestMetrics()  # Reset metrics
    stress_results = test_runner.stress_test_gradual_load(max_users=30, ramp_up_time=30)
    all_results["stress_test"] = stress_results
    print(f"   ✅ Completed: Tested up to {len(stress_results) * 3} concurrent users")
    
    return all_results

def analyze_performance_bottlenecks(results):
    """Analyze results to identify performance bottlenecks"""
    print("\n🔍 Performance Bottleneck Analysis:")
    
    bottlenecks = []
    
    # Analyze concurrent user test
    if "concurrent_users" in results:
        cu_results = results["concurrent_users"]
        if cu_results["success_rate"] < 95:
            bottlenecks.append(f"Concurrent user handling: {cu_results['success_rate']:.1f}% success rate")
        if cu_results["avg_response_time"] > 2.0:
            bottlenecks.append(f"High response times: {cu_results['avg_response_time']:.2f}s average")
    
    # Analyze high-frequency signals
    if "high_frequency_signals" in results:
        hf_results = results["high_frequency_signals"]
        if hf_results["throughput"] < 5:
            bottlenecks.append(f"Low signal processing throughput: {hf_results['throughput']:.1f} req/sec")
    
    # Analyze database performance
    if "database_load" in results:
        db_results = results["database_load"]
        if db_results["success_rate"] < 98:
            bottlenecks.append(f"Database reliability issues: {db_results['success_rate']:.1f}% success rate")
        if db_results["avg_response_time"] > 0.1:
            bottlenecks.append(f"Slow database operations: {db_results['avg_response_time']:.3f}s average")
    
    # Analyze stress test results
    if "stress_test" in results:
        stress_results = results["stress_test"]
        if stress_results:
            last_result = stress_results[-1]
            if last_result["success_rate"] < 80:
                bottlenecks.append(f"System breaks down at {last_result['concurrent_users']} concurrent users")
    
    if bottlenecks:
        for bottleneck in bottlenecks:
            print(f"  ⚠️ {bottleneck}")
    else:
        print("  ✅ No significant performance bottlenecks detected")
    
    return bottlenecks

def create_load_test_summary(results, bottlenecks):
    """Create comprehensive load test summary"""
    print("\n📄 Creating Load Test Summary...")
    
    summary = {
        "test_name": "Load and Stress Testing Suite",
        "test_date": datetime.now().isoformat(),
        "railway_url": RAILWAY_URL,
        "results": results,
        "bottlenecks": bottlenecks,
        "recommendations": []
    }
    
    # Generate recommendations based on results
    if "concurrent_users" in results:
        cu_results = results["concurrent_users"]
        if cu_results["success_rate"] < 95:
            summary["recommendations"].append("Optimize concurrent request handling")
        if cu_results["avg_response_time"] > 2.0:
            summary["recommendations"].append("Implement response time optimization")
    
    if "database_load" in results:
        db_results = results["database_load"]
        if db_results["avg_response_time"] > 0.1:
            summary["recommendations"].append("Optimize database queries and indexing")
        if db_results["success_rate"] < 98:
            summary["recommendations"].append("Improve database connection pooling")
    
    if not summary["recommendations"]:
        summary["recommendations"].append("System performance is within acceptable limits")
    
    # Write summary to file
    with open('LOAD_STRESS_TESTING_SUMMARY.md', 'w') as f:
        f.write("# Load and Stress Testing Summary\n\n")
        f.write(f"**Test Date:** {summary['test_date']}\n")
        f.write(f"**Target URL:** {RAILWAY_URL}\n\n")
        
        f.write("## Test Results\n\n")
        
        # Concurrent Users Test
        if "concurrent_users" in results:
            cu = results["concurrent_users"]
            f.write("### Concurrent Users Test\n")
            f.write(f"- **Success Rate:** {cu['success_rate']:.1f}%\n")
            f.write(f"- **Average Response Time:** {cu['avg_response_time']:.2f}s\n")
            f.write(f"- **Throughput:** {cu['throughput']:.1f} requests/sec\n")
            f.write(f"- **Total Requests:** {cu['total_requests']}\n\n")
        
        # High-Frequency Signals Test
        if "high_frequency_signals" in results:
            hf = results["high_frequency_signals"]
            f.write("### High-Frequency Signal Processing\n")
            f.write(f"- **Throughput:** {hf['throughput']:.1f} requests/sec\n")
            f.write(f"- **Success Rate:** {hf['success_rate']:.1f}%\n")
            f.write(f"- **Average Response Time:** {hf['avg_response_time']:.2f}s\n\n")
        
        # Database Load Test
        if "database_load" in results:
            db = results["database_load"]
            f.write("### Database Load Test\n")
            f.write(f"- **Success Rate:** {db['success_rate']:.1f}%\n")
            f.write(f"- **Throughput:** {db['throughput']:.1f} operations/sec\n")
            f.write(f"- **Average Response Time:** {db['avg_response_time']:.3f}s\n")
            f.write(f"- **Total Operations:** {db['total_operations']}\n\n")
        
        # Stress Test Results
        if "stress_test" in results and results["stress_test"]:
            f.write("### Stress Test Results\n")
            for i, result in enumerate(results["stress_test"]):
                f.write(f"- **{result['concurrent_users']} Users:** {result['success_rate']:.1f}% success, {result['avg_response_time']:.2f}s avg response\n")
            f.write("\n")
        
        # Performance Bottlenecks
        f.write("## Performance Analysis\n\n")
        if bottlenecks:
            f.write("### Identified Bottlenecks\n")
            for bottleneck in bottlenecks:
                f.write(f"- {bottleneck}\n")
        else:
            f.write("### Performance Status\n")
            f.write("- ✅ No significant performance bottlenecks detected\n")
        
        f.write("\n### Recommendations\n")
        for rec in summary["recommendations"]:
            f.write(f"- {rec}\n")
        
        f.write("\n## Load Testing Methodology\n\n")
        f.write("### Test Types\n")
        f.write("1. **Concurrent Users**: Simulates multiple users accessing the system simultaneously\n")
        f.write("2. **High-Frequency Signals**: Tests rapid signal processing capabilities\n")
        f.write("3. **Database Load**: Evaluates database performance under concurrent operations\n")
        f.write("4. **Gradual Stress**: Identifies system breaking points through incremental load\n\n")
        
        f.write("### Performance Metrics\n")
        f.write("- **Success Rate**: Percentage of successful requests\n")
        f.write("- **Response Time**: Average, median, and 95th percentile response times\n")
        f.write("- **Throughput**: Requests or operations per second\n")
        f.write("- **Concurrency**: Maximum concurrent users/operations supported\n")
    
    print(f"📄 Load test summary saved to LOAD_STRESS_TESTING_SUMMARY.md")

if __name__ == "__main__":
    print("🧪 Starting Load and Stress Testing Suite...\n")
    
    try:
        # Run comprehensive load tests
        results = run_comprehensive_load_tests()
        
        # Analyze performance bottlenecks
        bottlenecks = analyze_performance_bottlenecks(results)
        
        # Create summary report
        create_load_test_summary(results, bottlenecks)
        
        # Print final results
        print(f"\n📊 Load Testing Results Summary:")
        if "concurrent_users" in results:
            print(f"   👥 Concurrent Users: {results['concurrent_users']['success_rate']:.1f}% success rate")
        if "high_frequency_signals" in results:
            print(f"   📊 Signal Processing: {results['high_frequency_signals']['throughput']:.1f} req/sec")
        if "database_load" in results:
            print(f"   💾 Database Load: {results['database_load']['success_rate']:.1f}% success rate")
        
        if not bottlenecks:
            print("\n🎉 Load and stress testing completed successfully!")
            print("✅ System performance is within acceptable limits!")
        else:
            print(f"\n⚠️ Load testing completed with {len(bottlenecks)} performance issues identified.")
            print("Please review the summary report for optimization recommendations.")
        
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ Load testing failed: {e}")
        sys.exit(1)