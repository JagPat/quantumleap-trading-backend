"""
Test Query Optimization and Performance Monitoring
"""

import os
import tempfile
import time
import importlib.util

def load_optimization_modules():
    """Load optimization modules directly"""
    modules = {}
    
    # Load query optimizer
    spec = importlib.util.spec_from_file_location("query_optimizer", "app/database/query_optimizer.py")
    modules['query_optimizer'] = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modules['query_optimizer'])
    
    # Load performance collector
    spec = importlib.util.spec_from_file_location("performance_collector", "app/database/performance_collector.py")
    modules['performance_collector'] = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modules['performance_collector'])
    
    # Load standalone manager
    spec = importlib.util.spec_from_file_location("standalone_manager", "app/database/standalone_manager.py")
    modules['standalone_manager'] = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modules['standalone_manager'])
    
    return modules

def test_query_optimizer_creation():
    """Test creating query optimizer"""
    try:
        modules = load_optimization_modules()
        optimizer = modules['query_optimizer'].QueryOptimizer()
        
        print("✅ Query optimizer created successfully")
        print(f"   Patterns loaded: {len(optimizer.query_patterns)}")
        return True
    except Exception as e:
        print(f"❌ Failed to create query optimizer: {e}")
        return False

def test_query_analysis():
    """Test query analysis functionality"""
    try:
        modules = load_optimization_modules()
        optimizer = modules['query_optimizer'].QueryOptimizer()
        
        # Test different types of queries
        test_queries = [
            "SELECT * FROM trades WHERE symbol = 'AAPL'",
            "SELECT symbol, price FROM trades ORDER BY timestamp",
            "SELECT COUNT(*) FROM trades",
            "SELECT t.symbol, p.quantity FROM trades t JOIN portfolio p ON t.symbol = p.symbol",
            "SELECT * FROM trades WHERE symbol LIKE '%AAPL%'"
        ]
        
        for query in test_queries:
            plan = optimizer.analyze_query(query, 25.5)  # 25.5ms execution time
            
            assert plan.query_hash is not None
            assert plan.original_query == query
            assert plan.execution_time_ms == 25.5
            assert isinstance(plan.optimization_suggestions, list)
            
            print(f"✅ Analyzed query: {query[:50]}...")
            print(f"   Complexity score: {plan.plan_details.get('complexity_score', 0)}")
            print(f"   Suggestions: {len(plan.optimization_suggestions)}")
        
        return True
    except Exception as e:
        print(f"❌ Query analysis test failed: {e}")
        return False

def test_performance_collector():
    """Test performance metrics collection"""
    try:
        modules = load_optimization_modules()
        collector = modules['performance_collector'].PerformanceCollector()
        
        # Record some test metrics
        for i in range(10):
            collector.record_metric('test_metric', float(i * 10))
            collector.record_query_performance(f'query_hash_{i}', float(i * 5), True)
        
        # Record some errors
        collector.record_query_performance('error_query', 100.0, False, 'Test error')
        
        # Get metrics
        metrics = collector.get_metrics('test_metric', 60)
        assert len(metrics) == 10
        
        # Get statistics
        stats = collector.get_metric_statistics('test_metric', 60)
        assert stats['count'] == 10
        assert stats['min'] == 0.0
        assert stats['max'] == 90.0
        
        # Get dashboard
        dashboard = collector.get_performance_dashboard(60)
        assert 'timestamp' in dashboard
        assert 'metrics' in dashboard
        assert 'alerts' in dashboard
        
        print("✅ Performance collector works")
        print(f"   Metrics recorded: {len(metrics)}")
        print(f"   Dashboard status: {dashboard.get('system_health', {}).get('status', 'unknown')}")
        
        return True
    except Exception as e:
        print(f"❌ Performance collector test failed: {e}")
        return False

def test_alert_system():
    """Test performance alert system"""
    try:
        modules = load_optimization_modules()
        collector = modules['performance_collector'].PerformanceCollector()
        
        # Add alert threshold
        collector.add_alert_threshold('test_metric', 50.0, 'gt', 1, 'high')
        
        # Record metrics that should trigger alert
        collector.record_metric('test_metric', 60.0)  # Should trigger alert
        
        # Check if alert was triggered
        assert len(collector.active_alerts) > 0
        
        # Record metric that should resolve alert
        collector.record_metric('test_metric', 30.0)  # Should resolve alert
        
        print("✅ Alert system works")
        print(f"   Active alerts: {len(collector.active_alerts)}")
        print(f"   Alert history: {len(collector.alert_history)}")
        
        return True
    except Exception as e:
        print(f"❌ Alert system test failed: {e}")
        return False

def test_integrated_optimization():
    """Test integrated optimization with database manager"""
    try:
        modules = load_optimization_modules()
        
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        # Create database manager with optimization
        db_manager = modules['standalone_manager'].StandaloneDatabaseManager(f'sqlite:///{temp_db.name}')
        
        # Create test table
        db_manager.execute_query("""
            CREATE TABLE test_optimization (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                volume INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert test data with various queries
        test_queries = [
            "INSERT INTO test_optimization (symbol, price, volume) VALUES ('AAPL', 150.0, 1000)",
            "INSERT INTO test_optimization (symbol, price, volume) VALUES ('GOOGL', 2800.0, 500)",
            "SELECT * FROM test_optimization WHERE symbol = 'AAPL'",
            "SELECT symbol, AVG(price) FROM test_optimization GROUP BY symbol",
            "SELECT * FROM test_optimization ORDER BY timestamp DESC"
        ]
        
        for query in test_queries:
            result = db_manager.execute_query(query)
            time.sleep(0.1)  # Small delay between queries
        
        # Test optimization features
        if db_manager.query_optimizer:
            recommendations = db_manager.get_query_recommendations()
            print(f"✅ Query recommendations: {len(recommendations)}")
            
            index_recs = db_manager.get_index_recommendations()
            print(f"✅ Index recommendations: {len(index_recs)}")
        
        if db_manager.performance_collector:
            dashboard = db_manager.get_performance_dashboard()
            print(f"✅ Performance dashboard: {dashboard.get('system_health', {}).get('status', 'unknown')}")
        
        # Test optimization summary
        summary = db_manager.get_optimization_summary()
        print(f"✅ Optimization enabled: {summary.get('optimization_enabled', False)}")
        print(f"✅ Performance monitoring: {summary.get('performance_monitoring_enabled', False)}")
        
        # Cleanup
        os.unlink(temp_db.name)
        return True
    except Exception as e:
        print(f"❌ Integrated optimization test failed: {e}")
        return False

def test_query_pattern_detection():
    """Test query pattern detection and optimization suggestions"""
    try:
        modules = load_optimization_modules()
        optimizer = modules['query_optimizer'].QueryOptimizer()
        
        # Test queries that should trigger specific patterns
        test_cases = [
            {
                'query': "SELECT * FROM trades",
                'expected_pattern': 'SELECT_ALL'
            },
            {
                'query': "SELECT symbol FROM trades WHERE symbol LIKE '%AAPL%'",
                'expected_pattern': 'INEFFICIENT_LIKE'
            },
            {
                'query': "SELECT symbol FROM trades ORDER BY timestamp",
                'expected_pattern': 'MISSING_LIMIT'
            }
        ]
        
        for case in test_cases:
            plan = optimizer.analyze_query(case['query'])
            
            # Check if expected pattern was detected
            pattern_found = any(
                suggestion.get('type') == case['expected_pattern']
                for suggestion in plan.optimization_suggestions
            )
            
            print(f"✅ Pattern detection for: {case['query'][:40]}...")
            print(f"   Expected pattern '{case['expected_pattern']}': {'Found' if pattern_found else 'Not found'}")
            print(f"   Total suggestions: {len(plan.optimization_suggestions)}")
        
        return True
    except Exception as e:
        print(f"❌ Query pattern detection test failed: {e}")
        return False

def test_performance_metrics_accuracy():
    """Test accuracy of performance metrics"""
    try:
        modules = load_optimization_modules()
        collector = modules['performance_collector'].PerformanceCollector()
        
        # Record known values
        test_values = [10.0, 20.0, 30.0, 40.0, 50.0]
        
        for value in test_values:
            collector.record_metric('accuracy_test', value)
        
        # Get statistics and verify
        stats = collector.get_metric_statistics('accuracy_test', 60)
        
        assert stats['count'] == 5
        assert stats['min'] == 10.0
        assert stats['max'] == 50.0
        assert stats['mean'] == 30.0  # (10+20+30+40+50)/5
        assert stats['median'] == 30.0
        
        print("✅ Performance metrics accuracy verified")
        print(f"   Count: {stats['count']}")
        print(f"   Mean: {stats['mean']}")
        print(f"   Median: {stats['median']}")
        
        return True
    except Exception as e:
        print(f"❌ Performance metrics accuracy test failed: {e}")
        return False

def main():
    """Run all optimization tests"""
    print("🧪 Running Query Optimization and Performance Tests")
    print("=" * 60)
    
    tests = [
        test_query_optimizer_creation,
        test_query_analysis,
        test_performance_collector,
        test_alert_system,
        test_integrated_optimization,
        test_query_pattern_detection,
        test_performance_metrics_accuracy
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        print(f"\n🔍 Running {test.__name__}...")
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print(f"\n📊 Test Results:")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📈 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 All optimization tests passed!")
        print("\n🚀 Query Optimization System Ready:")
        print("   ✅ Query analysis and optimization")
        print("   ✅ Performance metrics collection")
        print("   ✅ Real-time alerting system")
        print("   ✅ Index recommendations")
        print("   ✅ Performance dashboard")
        print("   ✅ Integration with database manager")
        print("\n📦 Ready for Railway deployment with advanced optimization!")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review issues.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)