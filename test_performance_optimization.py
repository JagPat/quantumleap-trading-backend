#!/usr/bin/env python3
"""
Performance Optimization Testing for Automated Trading Engine
Tests specific performance scenarios and provides optimization recommendations
"""

import time
import threading
import sqlite3
import tempfile
import os
import json
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request
import urllib.error
import random
import statistics
import psutil
import gc

# Configuration
RAILWAY_URL = "https://quantum-leap-backend-production.up.railway.app"

class PerformanceProfiler:
    """Profile system performance during tests"""
    
    def __init__(self):
        self.cpu_usage = []
        self.memory_usage = []
        self.monitoring = False
        self.monitor_thread = None
    
    def start_monitoring(self):
        """Start system monitoring"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_system)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop system monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
    
    def _monitor_system(self):
        """Monitor system resources"""
        while self.monitoring:
            try:
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_info = psutil.virtual_memory()
                
                self.cpu_usage.append(cpu_percent)
                self.memory_usage.append(memory_info.percent)
            except:
                pass  # Ignore monitoring errors
    
    def get_stats(self):
        """Get monitoring statistics"""
        if not self.cpu_usage or not self.memory_usage:
            return {"error": "No monitoring data available"}
        
        return {
            "avg_cpu_usage": statistics.mean(self.cpu_usage),
            "max_cpu_usage": max(self.cpu_usage),
            "avg_memory_usage": statistics.mean(self.memory_usage),
            "max_memory_usage": max(self.memory_usage)
        }

class PerformanceOptimizer:
    """Performance optimization testing and recommendations"""
    
    def __init__(self, base_url=None):
        self.base_url = base_url or RAILWAY_URL
        self.profiler = PerformanceProfiler()
    
    def test_response_time_optimization(self):
        """Test response time optimization techniques"""
        print("⚡ Testing Response Time Optimization...")
        
        endpoints = [
            "/api/trading-engine/status",
            "/api/portfolio/holdings",
            "/api/ai/analyze",
            "/api/trading-engine/strategies"
        ]
        
        results = {}
        
        for endpoint in endpoints:
            print(f"  Testing {endpoint}...")
            response_times = []
            
            # Test multiple requests to get average
            for _ in range(10):
                start_time = time.time()
                try:
                    url = f"{self.base_url}{endpoint}"
                    req = urllib.request.Request(url)
                    req.add_header('Content-Type', 'application/json')
                    
                    with urllib.request.urlopen(req, timeout=10) as response:
                        response_time = time.time() - start_time
                        response_times.append(response_time)
                except:
                    response_time = time.time() - start_time
                    response_times.append(response_time)
            
            if response_times:
                results[endpoint] = {
                    "avg_response_time": statistics.mean(response_times),
                    "min_response_time": min(response_times),
                    "max_response_time": max(response_times),
                    "median_response_time": statistics.median(response_times)
                }
        
        return results
    
    def test_memory_optimization(self):
        """Test memory usage optimization"""
        print("🧠 Testing Memory Optimization...")
        
        # Start monitoring
        self.profiler.start_monitoring()
        
        # Simulate memory-intensive operations
        large_data_sets = []
        
        try:
            # Create large data structures
            for i in range(100):
                data_set = {
                    "portfolio_data": [
                        {
                            "symbol": f"STOCK_{j}",
                            "price": random.uniform(100, 3000),
                            "quantity": random.randint(1, 1000),
                            "timestamp": datetime.now().isoformat()
                        }
                        for j in range(1000)
                    ],
                    "market_data": [random.uniform(0, 1) for _ in range(10000)],
                    "signals": [
                        {
                            "signal": random.choice(["BUY", "SELL", "HOLD"]),
                            "confidence": random.uniform(0.5, 1.0),
                            "timestamp": datetime.now().isoformat()
                        }
                        for _ in range(500)
                    ]
                }
                large_data_sets.append(data_set)
            
            # Simulate processing
            time.sleep(5)
            
            # Test garbage collection
            gc.collect()
            
            # Clear data
            large_data_sets.clear()
            gc.collect()
            
        finally:
            # Stop monitoring
            self.profiler.stop_monitoring()
        
        return self.profiler.get_stats()
    
    def test_database_optimization(self):
        """Test database optimization techniques"""
        print("💾 Testing Database Optimization...")
        
        # Create temporary database
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_db:
            db_path = tmp_db.name
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Test 1: Table creation with indexes
            start_time = time.time()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS optimized_portfolio (
                    id INTEGER PRIMARY KEY,
                    user_id TEXT,
                    symbol TEXT,
                    price REAL,
                    quantity INTEGER,
                    timestamp TEXT
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_symbol ON optimized_portfolio(user_id, symbol)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON optimized_portfolio(timestamp)')
            conn.commit()
            
            table_creation_time = time.time() - start_time
            
            # Test 2: Bulk insert performance
            start_time = time.time()
            
            # Prepare bulk data
            bulk_data = [
                (f'user_{i % 100}', f'STOCK_{i % 50}', random.uniform(100, 3000), 
                 random.randint(1, 1000), datetime.now().isoformat())
                for i in range(10000)
            ]
            
            cursor.executemany(
                'INSERT INTO optimized_portfolio (user_id, symbol, price, quantity, timestamp) VALUES (?, ?, ?, ?, ?)',
                bulk_data
            )
            conn.commit()
            
            bulk_insert_time = time.time() - start_time
            
            # Test 3: Query performance with indexes
            start_time = time.time()
            
            # Test indexed queries
            cursor.execute('SELECT COUNT(*) FROM optimized_portfolio WHERE user_id = ?', ('user_1',))
            cursor.fetchone()
            
            cursor.execute('SELECT * FROM optimized_portfolio WHERE user_id = ? AND symbol = ?', ('user_1', 'STOCK_1'))
            cursor.fetchall()
            
            cursor.execute('SELECT symbol, SUM(quantity) FROM optimized_portfolio GROUP BY symbol LIMIT 10')
            cursor.fetchall()
            
            indexed_query_time = time.time() - start_time
            
            # Test 4: Query performance without indexes (create new table)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS unoptimized_portfolio (
                    id INTEGER PRIMARY KEY,
                    user_id TEXT,
                    symbol TEXT,
                    price REAL,
                    quantity INTEGER,
                    timestamp TEXT
                )
            ''')
            
            cursor.executemany(
                'INSERT INTO unoptimized_portfolio (user_id, symbol, price, quantity, timestamp) VALUES (?, ?, ?, ?, ?)',
                bulk_data[:1000]  # Smaller dataset for comparison
            )
            conn.commit()
            
            start_time = time.time()
            cursor.execute('SELECT COUNT(*) FROM unoptimized_portfolio WHERE user_id = ?', ('user_1',))
            cursor.fetchone()
            unindexed_query_time = time.time() - start_time
            
            conn.close()
            
            return {
                "table_creation_time": table_creation_time,
                "bulk_insert_time": bulk_insert_time,
                "bulk_insert_rate": len(bulk_data) / bulk_insert_time,
                "indexed_query_time": indexed_query_time,
                "unindexed_query_time": unindexed_query_time,
                "query_optimization_factor": unindexed_query_time / indexed_query_time if indexed_query_time > 0 else 1
            }
            
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_concurrent_optimization(self):
        """Test concurrent processing optimization"""
        print("🔄 Testing Concurrent Processing Optimization...")
        
        def cpu_intensive_task(task_id):
            """Simulate CPU-intensive task"""
            start_time = time.time()
            
            # Simulate complex calculations
            result = 0
            for i in range(100000):
                result += i * i * 0.001
            
            return {
                "task_id": task_id,
                "result": result,
                "execution_time": time.time() - start_time
            }
        
        # Test 1: Sequential execution
        start_time = time.time()
        sequential_results = []
        for i in range(10):
            result = cpu_intensive_task(i)
            sequential_results.append(result)
        sequential_time = time.time() - start_time
        
        # Test 2: Concurrent execution
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(cpu_intensive_task, i) for i in range(10)]
            concurrent_results = [future.result() for future in as_completed(futures)]
        concurrent_time = time.time() - start_time
        
        return {
            "sequential_time": sequential_time,
            "concurrent_time": concurrent_time,
            "speedup_factor": sequential_time / concurrent_time if concurrent_time > 0 else 1,
            "efficiency": (sequential_time / concurrent_time) / 4 if concurrent_time > 0 else 0  # 4 workers
        }
    
    def generate_optimization_recommendations(self, test_results):
        """Generate optimization recommendations based on test results"""
        recommendations = []
        
        # Response time recommendations
        if "response_time" in test_results:
            rt_results = test_results["response_time"]
            slow_endpoints = [ep for ep, data in rt_results.items() if data["avg_response_time"] > 1.0]
            
            if slow_endpoints:
                recommendations.append({
                    "category": "Response Time",
                    "issue": f"Slow endpoints detected: {', '.join(slow_endpoints)}",
                    "recommendation": "Implement caching, optimize database queries, or add CDN",
                    "priority": "High"
                })
        
        # Memory recommendations
        if "memory" in test_results:
            mem_results = test_results["memory"]
            if mem_results.get("max_memory_usage", 0) > 80:
                recommendations.append({
                    "category": "Memory Usage",
                    "issue": f"High memory usage detected: {mem_results['max_memory_usage']:.1f}%",
                    "recommendation": "Implement memory pooling, optimize data structures, add garbage collection",
                    "priority": "Medium"
                })
        
        # Database recommendations
        if "database" in test_results:
            db_results = test_results["database"]
            if db_results.get("query_optimization_factor", 1) > 2:
                recommendations.append({
                    "category": "Database Performance",
                    "issue": f"Queries {db_results['query_optimization_factor']:.1f}x faster with indexes",
                    "recommendation": "Add database indexes, optimize query patterns, implement connection pooling",
                    "priority": "High"
                })
        
        # Concurrency recommendations
        if "concurrency" in test_results:
            conc_results = test_results["concurrency"]
            if conc_results.get("efficiency", 0) < 0.7:
                recommendations.append({
                    "category": "Concurrency",
                    "issue": f"Low concurrency efficiency: {conc_results['efficiency']:.1f}",
                    "recommendation": "Optimize thread pool size, reduce lock contention, use async processing",
                    "priority": "Medium"
                })
        
        if not recommendations:
            recommendations.append({
                "category": "Overall",
                "issue": "No significant performance issues detected",
                "recommendation": "Continue monitoring and maintain current optimization levels",
                "priority": "Low"
            })
        
        return recommendations

def run_performance_optimization_tests():
    """Run all performance optimization tests"""
    print("🚀 Starting Performance Optimization Testing Suite...\n")
    
    optimizer = PerformanceOptimizer(RAILWAY_URL)
    test_results = {}
    
    # Test 1: Response Time Optimization
    print("1️⃣ Response Time Optimization Test")
    test_results["response_time"] = optimizer.test_response_time_optimization()
    
    # Test 2: Memory Optimization
    print("\n2️⃣ Memory Optimization Test")
    test_results["memory"] = optimizer.test_memory_optimization()
    
    # Test 3: Database Optimization
    print("\n3️⃣ Database Optimization Test")
    test_results["database"] = optimizer.test_database_optimization()
    
    # Test 4: Concurrent Processing Optimization
    print("\n4️⃣ Concurrent Processing Optimization Test")
    test_results["concurrency"] = optimizer.test_concurrent_optimization()
    
    # Generate recommendations
    recommendations = optimizer.generate_optimization_recommendations(test_results)
    
    return test_results, recommendations

def create_optimization_summary(test_results, recommendations):
    """Create performance optimization summary"""
    print("\n📄 Creating Performance Optimization Summary...")
    
    summary = {
        "test_name": "Performance Optimization Testing Suite",
        "test_date": datetime.now().isoformat(),
        "results": test_results,
        "recommendations": recommendations
    }
    
    with open('PERFORMANCE_OPTIMIZATION_SUMMARY.md', 'w') as f:
        f.write("# Performance Optimization Testing Summary\n\n")
        f.write(f"**Test Date:** {summary['test_date']}\n")
        f.write(f"**Target System:** {RAILWAY_URL}\n\n")
        
        f.write("## Test Results\n\n")
        
        # Response Time Results
        if "response_time" in test_results:
            f.write("### Response Time Analysis\n")
            for endpoint, data in test_results["response_time"].items():
                f.write(f"**{endpoint}**\n")
                f.write(f"- Average: {data['avg_response_time']:.3f}s\n")
                f.write(f"- Median: {data['median_response_time']:.3f}s\n")
                f.write(f"- Range: {data['min_response_time']:.3f}s - {data['max_response_time']:.3f}s\n\n")
        
        # Memory Results
        if "memory" in test_results and "error" not in test_results["memory"]:
            f.write("### Memory Usage Analysis\n")
            mem = test_results["memory"]
            f.write(f"- Average CPU Usage: {mem['avg_cpu_usage']:.1f}%\n")
            f.write(f"- Peak CPU Usage: {mem['max_cpu_usage']:.1f}%\n")
            f.write(f"- Average Memory Usage: {mem['avg_memory_usage']:.1f}%\n")
            f.write(f"- Peak Memory Usage: {mem['max_memory_usage']:.1f}%\n\n")
        
        # Database Results
        if "database" in test_results:
            f.write("### Database Performance Analysis\n")
            db = test_results["database"]
            f.write(f"- Bulk Insert Rate: {db['bulk_insert_rate']:.0f} records/second\n")
            f.write(f"- Query Optimization Factor: {db['query_optimization_factor']:.1f}x faster with indexes\n")
            f.write(f"- Indexed Query Time: {db['indexed_query_time']:.3f}s\n")
            f.write(f"- Unindexed Query Time: {db['unindexed_query_time']:.3f}s\n\n")
        
        # Concurrency Results
        if "concurrency" in test_results:
            f.write("### Concurrency Performance Analysis\n")
            conc = test_results["concurrency"]
            f.write(f"- Sequential Execution: {conc['sequential_time']:.2f}s\n")
            f.write(f"- Concurrent Execution: {conc['concurrent_time']:.2f}s\n")
            f.write(f"- Speedup Factor: {conc['speedup_factor']:.1f}x\n")
            f.write(f"- Efficiency: {conc['efficiency']:.1f}\n\n")
        
        # Recommendations
        f.write("## Optimization Recommendations\n\n")
        for rec in recommendations:
            priority_emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(rec["priority"], "⚪")
            f.write(f"### {priority_emoji} {rec['category']} ({rec['priority']} Priority)\n")
            f.write(f"**Issue:** {rec['issue']}\n\n")
            f.write(f"**Recommendation:** {rec['recommendation']}\n\n")
        
        f.write("## Performance Optimization Guidelines\n\n")
        f.write("### Response Time Optimization\n")
        f.write("- Implement caching strategies (Redis, in-memory caching)\n")
        f.write("- Optimize database queries and add appropriate indexes\n")
        f.write("- Use CDN for static assets\n")
        f.write("- Implement request/response compression\n\n")
        
        f.write("### Memory Optimization\n")
        f.write("- Implement object pooling for frequently used objects\n")
        f.write("- Use streaming for large data processing\n")
        f.write("- Optimize data structures and algorithms\n")
        f.write("- Implement proper garbage collection strategies\n\n")
        
        f.write("### Database Optimization\n")
        f.write("- Add indexes on frequently queried columns\n")
        f.write("- Implement connection pooling\n")
        f.write("- Use prepared statements\n")
        f.write("- Optimize query patterns and avoid N+1 queries\n\n")
        
        f.write("### Concurrency Optimization\n")
        f.write("- Use appropriate thread pool sizes\n")
        f.write("- Implement async/await patterns\n")
        f.write("- Minimize lock contention\n")
        f.write("- Use lock-free data structures where possible\n")
    
    print(f"📄 Optimization summary saved to PERFORMANCE_OPTIMIZATION_SUMMARY.md")

if __name__ == "__main__":
    print("🧪 Starting Performance Optimization Testing Suite...\n")
    
    try:
        # Run optimization tests
        test_results, recommendations = run_performance_optimization_tests()
        
        # Create summary
        create_optimization_summary(test_results, recommendations)
        
        # Print results
        print(f"\n📊 Performance Optimization Results:")
        
        high_priority_recs = [r for r in recommendations if r["priority"] == "High"]
        medium_priority_recs = [r for r in recommendations if r["priority"] == "Medium"]
        
        if high_priority_recs:
            print(f"   🔴 High Priority Issues: {len(high_priority_recs)}")
        if medium_priority_recs:
            print(f"   🟡 Medium Priority Issues: {len(medium_priority_recs)}")
        
        if not high_priority_recs and not medium_priority_recs:
            print("   🟢 No significant performance issues detected")
        
        print("\n🎉 Performance optimization testing completed!")
        print("✅ Check PERFORMANCE_OPTIMIZATION_SUMMARY.md for detailed recommendations")
        
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ Performance optimization testing failed: {e}")
        sys.exit(1)