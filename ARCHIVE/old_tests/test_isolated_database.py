"""
Isolated test for the standalone database manager
This test doesn't import from the app package to avoid conflicts.
"""

import os
import sys
import tempfile
import importlib.util

def load_standalone_manager():
    """Load the standalone manager module directly"""
    spec = importlib.util.spec_from_file_location(
        "standalone_manager", 
        "app/database/standalone_manager.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_direct_import():
    """Test direct import of standalone manager"""
    try:
        standalone = load_standalone_manager()
        print("✅ Successfully loaded standalone database manager")
        
        # Check if classes exist
        assert hasattr(standalone, 'StandaloneDatabaseManager')
        assert hasattr(standalone, 'get_standalone_database_manager')
        
        print("✅ All required classes and functions available")
        return True
    except Exception as e:
        print(f"❌ Failed to load standalone manager: {e}")
        return False

def test_manager_creation():
    """Test creating a manager instance"""
    try:
        standalone = load_standalone_manager()
        
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        # Create manager instance
        manager = standalone.StandaloneDatabaseManager(f'sqlite:///{temp_db.name}')
        
        print("✅ Successfully created manager instance")
        print(f"   Database URL: {manager.database_url}")
        print(f"   Is PostgreSQL: {manager.is_postgresql}")
        
        # Cleanup
        os.unlink(temp_db.name)
        return True
    except Exception as e:
        print(f"❌ Failed to create manager: {e}")
        return False

def test_basic_functionality():
    """Test basic database functionality"""
    try:
        standalone = load_standalone_manager()
        
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        manager = standalone.StandaloneDatabaseManager(f'sqlite:///{temp_db.name}')
        
        # Create test table
        manager.execute_query("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                value REAL NOT NULL
            )
        """)
        
        # Insert test data
        manager.execute_query(
            "INSERT INTO test_table (name, value) VALUES (?, ?)",
            ('test_item', 42.5)
        )
        
        # Query test data
        result = manager.execute_query("SELECT * FROM test_table")
        
        assert len(result) == 1
        assert result[0]['name'] == 'test_item'
        assert result[0]['value'] == 42.5
        
        print("✅ Basic database operations work")
        print(f"   Retrieved: {result[0]['name']} = {result[0]['value']}")
        
        # Cleanup
        os.unlink(temp_db.name)
        return True
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def test_health_check():
    """Test health check functionality"""
    try:
        standalone = load_standalone_manager()
        
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        manager = standalone.StandaloneDatabaseManager(f'sqlite:///{temp_db.name}')
        
        # Execute a query to generate some metrics
        manager.execute_query("CREATE TABLE health_test (id INTEGER PRIMARY KEY)")
        manager.execute_query("INSERT INTO health_test DEFAULT VALUES")
        
        # Run health check
        health = manager.health_check()
        
        assert 'status' in health
        assert 'database' in health
        assert 'performance' in health
        assert 'railway' in health
        
        print("✅ Health check works")
        print(f"   Status: {health['status']}")
        print(f"   Database type: {health['database']['type']}")
        
        # Cleanup
        os.unlink(temp_db.name)
        return True
    except Exception as e:
        print(f"❌ Health check test failed: {e}")
        return False

def test_transaction():
    """Test transaction functionality"""
    try:
        standalone = load_standalone_manager()
        
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        manager = standalone.StandaloneDatabaseManager(f'sqlite:///{temp_db.name}')
        
        # Create test table
        manager.execute_query("""
            CREATE TABLE transaction_test (
                id INTEGER PRIMARY KEY,
                data TEXT NOT NULL
            )
        """)
        
        # Test successful transaction
        operations = [
            {
                'query': "INSERT INTO transaction_test (data) VALUES (?)",
                'params': ('item1',)
            },
            {
                'query': "INSERT INTO transaction_test (data) VALUES (?)",
                'params': ('item2',)
            }
        ]
        
        success = manager.execute_transaction(operations)
        assert success is True
        
        # Verify both records were inserted
        result = manager.execute_query("SELECT COUNT(*) as count FROM transaction_test")
        assert result[0]['count'] == 2
        
        print("✅ Transaction functionality works")
        print(f"   Inserted {result[0]['count']} records in transaction")
        
        # Cleanup
        os.unlink(temp_db.name)
        return True
    except Exception as e:
        print(f"❌ Transaction test failed: {e}")
        return False

def test_performance_metrics():
    """Test performance metrics"""
    try:
        standalone = load_standalone_manager()
        
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        manager = standalone.StandaloneDatabaseManager(f'sqlite:///{temp_db.name}')
        
        # Create test table and execute queries
        manager.execute_query("CREATE TABLE perf_test (id INTEGER PRIMARY KEY, data TEXT)")
        
        for i in range(10):
            manager.execute_query(
                "INSERT INTO perf_test (data) VALUES (?)",
                (f'data_{i}',)
            )
        
        # Get performance metrics
        metrics = manager.get_performance_metrics()
        
        assert metrics['status'] == 'healthy'
        assert metrics['query_count'] > 0
        assert 'avg_execution_time_ms' in metrics
        
        print("✅ Performance metrics work")
        print(f"   Query count: {metrics['query_count']}")
        print(f"   Avg execution time: {metrics['avg_execution_time_ms']}ms")
        
        # Cleanup
        os.unlink(temp_db.name)
        return True
    except Exception as e:
        print(f"❌ Performance metrics test failed: {e}")
        return False

def test_railway_utilities():
    """Test Railway utility functions"""
    try:
        standalone = load_standalone_manager()
        
        # Test utility functions
        health = standalone.check_railway_database_health()
        assert 'status' in health
        
        success = standalone.optimize_for_railway()
        assert isinstance(success, bool)
        
        conn_info = standalone.get_railway_connection_info()
        assert 'type' in conn_info
        
        print("✅ Railway utilities work")
        print(f"   Health status: {health['status']}")
        print(f"   Optimization success: {success}")
        print(f"   Connection type: {conn_info['type']}")
        
        return True
    except Exception as e:
        print(f"❌ Railway utilities test failed: {e}")
        return False

def main():
    """Run all isolated tests"""
    print("🧪 Running Isolated Database Manager Tests")
    print("=" * 50)
    print("ℹ️  These tests load the module directly to avoid import conflicts")
    
    tests = [
        test_direct_import,
        test_manager_creation,
        test_basic_functionality,
        test_health_check,
        test_transaction,
        test_performance_metrics,
        test_railway_utilities
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
        print("\n🎉 All isolated tests passed!")
        print("\n🚀 Database Optimization System Ready for Railway:")
        print("   ✅ Standalone manager loads without conflicts")
        print("   ✅ SQLite operations work correctly")
        print("   ✅ Health monitoring functional")
        print("   ✅ Transaction handling works")
        print("   ✅ Performance metrics collection active")
        print("   ✅ Railway utilities available")
        print("\n📦 Ready for deployment to Railway!")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review issues.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)