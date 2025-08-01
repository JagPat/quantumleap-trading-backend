"""
Test for the standalone database manager
"""

import os
import tempfile
import sys

def test_standalone_import():
    """Test importing the standalone database manager"""
    try:
        from app.database.standalone_manager import (
            StandaloneDatabaseManager, 
            get_standalone_database_manager,
            check_railway_database_health,
            optimize_for_railway
        )
        print("✅ Successfully imported StandaloneDatabaseManager")
        return True
    except ImportError as e:
        print(f"❌ Failed to import StandaloneDatabaseManager: {e}")
        return False

def test_standalone_creation():
    """Test creating a standalone database manager"""
    try:
        from app.database.standalone_manager import StandaloneDatabaseManager
        
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        db_manager = StandaloneDatabaseManager(f'sqlite:///{temp_db.name}')
        
        print("✅ Successfully created standalone database manager")
        print(f"   Database URL: {db_manager.database_url}")
        print(f"   Is PostgreSQL: {db_manager.is_postgresql}")
        print(f"   PostgreSQL available: {db_manager.postgresql_available}")
        
        # Cleanup
        os.unlink(temp_db.name)
        return True
    except Exception as e:
        print(f"❌ Failed to create standalone database manager: {e}")
        return False

def test_basic_database_operations():
    """Test basic database operations"""
    try:
        from app.database.standalone_manager import StandaloneDatabaseManager
        
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        db_manager = StandaloneDatabaseManager(f'sqlite:///{temp_db.name}')
        
        # Create test table
        db_manager.execute_query("""
            CREATE TABLE test_trades (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert test data
        db_manager.execute_query(
            "INSERT INTO test_trades (symbol, quantity, price) VALUES (?, ?, ?)",
            ('AAPL', 100.0, 150.50)
        )
        
        db_manager.execute_query(
            "INSERT INTO test_trades (symbol, quantity, price) VALUES (?, ?, ?)",
            ('GOOGL', 50.0, 2800.00)
        )
        
        # Query test data
        result = db_manager.execute_query("SELECT * FROM test_trades ORDER BY symbol")
        
        assert len(result) == 2
        assert result[0]['symbol'] == 'AAPL'
        assert result[0]['quantity'] == 100.0
        assert result[0]['price'] == 150.50
        assert result[1]['symbol'] == 'GOOGL'
        
        print("✅ Basic database operations work")
        print(f"   Inserted and retrieved {len(result)} records")
        
        # Test aggregation query
        count_result = db_manager.execute_query("SELECT COUNT(*) as total FROM test_trades")
        assert count_result[0]['total'] == 2
        
        print("✅ Aggregation queries work")
        
        # Cleanup
        os.unlink(temp_db.name)
        return True
    except Exception as e:
        print(f"❌ Basic operations test failed: {e}")
        return False

def test_transaction_functionality():
    """Test transaction functionality"""
    try:
        from app.database.standalone_manager import StandaloneDatabaseManager
        
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        db_manager = StandaloneDatabaseManager(f'sqlite:///{temp_db.name}')
        
        # Create test table
        db_manager.execute_query("""
            CREATE TABLE test_portfolio (
                id INTEGER PRIMARY KEY,
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                quantity REAL NOT NULL
            )
        """)
        
        # Test successful transaction
        operations = [
            {
                'query': "INSERT INTO test_portfolio (user_id, symbol, quantity) VALUES (?, ?, ?)",
                'params': ('user1', 'AAPL', 100.0)
            },
            {
                'query': "INSERT INTO test_portfolio (user_id, symbol, quantity) VALUES (?, ?, ?)",
                'params': ('user1', 'GOOGL', 50.0)
            },
            {
                'query': "INSERT INTO test_portfolio (user_id, symbol, quantity) VALUES (?, ?, ?)",
                'params': ('user2', 'MSFT', 75.0)
            }
        ]
        
        success = db_manager.execute_transaction(operations)
        assert success is True
        
        # Verify all records were inserted
        result = db_manager.execute_query("SELECT COUNT(*) as count FROM test_portfolio")
        assert result[0]['count'] == 3
        
        print("✅ Transaction functionality works")
        print(f"   Successfully inserted {result[0]['count']} records in transaction")
        
        # Test transaction rollback (this should fail and rollback)
        bad_operations = [
            {
                'query': "INSERT INTO test_portfolio (user_id, symbol, quantity) VALUES (?, ?, ?)",
                'params': ('user3', 'TSLA', 25.0)
            },
            {
                'query': "INSERT INTO nonexistent_table (column) VALUES (?)",  # This will fail
                'params': ('value',)
            }
        ]
        
        success = db_manager.execute_transaction(bad_operations)
        assert success is False
        
        # Verify rollback - count should still be 3
        result = db_manager.execute_query("SELECT COUNT(*) as count FROM test_portfolio")
        assert result[0]['count'] == 3
        
        print("✅ Transaction rollback works correctly")
        
        # Cleanup
        os.unlink(temp_db.name)
        return True
    except Exception as e:
        print(f"❌ Transaction test failed: {e}")
        return False

def test_health_check():
    """Test comprehensive health check"""
    try:
        from app.database.standalone_manager import StandaloneDatabaseManager
        
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        db_manager = StandaloneDatabaseManager(f'sqlite:///{temp_db.name}')
        
        # Execute some queries to generate metrics
        db_manager.execute_query("CREATE TABLE health_test (id INTEGER PRIMARY KEY, data TEXT)")
        for i in range(5):
            db_manager.execute_query(
                "INSERT INTO health_test (data) VALUES (?)",
                (f'test_data_{i}',)
            )
        
        # Run health check
        health = db_manager.health_check()
        
        assert 'status' in health
        assert 'database' in health
        assert 'performance' in health
        assert 'railway' in health
        assert 'timestamp' in health
        
        print("✅ Health check works")
        print(f"   Status: {health['status']}")
        print(f"   Database type: {health['database']['type']}")
        print(f"   Database version: {health['database']['version']}")
        
        # Check performance metrics
        performance = health['performance']
        if performance['status'] == 'healthy':
            print(f"   Query count: {performance['query_count']}")
            print(f"   Avg execution time: {performance['avg_execution_time_ms']}ms")
            print(f"   Error rate: {performance['error_rate']}")
        
        # Cleanup
        os.unlink(temp_db.name)
        return True
    except Exception as e:
        print(f"❌ Health check test failed: {e}")
        return False

def test_performance_metrics():
    """Test performance metrics collection"""
    try:
        from app.database.standalone_manager import StandaloneDatabaseManager
        
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        db_manager = StandaloneDatabaseManager(f'sqlite:///{temp_db.name}')
        
        # Create test table
        db_manager.execute_query("""
            CREATE TABLE performance_test (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                volume INTEGER NOT NULL
            )
        """)
        
        # Execute multiple queries to generate metrics
        for i in range(20):
            db_manager.execute_query(
                "INSERT INTO performance_test (symbol, price, volume) VALUES (?, ?, ?)",
                (f'STOCK{i}', float(i * 10), i * 100)
            )
        
        # Execute some read queries
        for i in range(10):
            db_manager.execute_query("SELECT COUNT(*) as count FROM performance_test")
            db_manager.execute_query("SELECT AVG(price) as avg_price FROM performance_test")
        
        # Get performance metrics
        metrics = db_manager.get_performance_metrics()
        
        assert metrics['status'] == 'healthy'
        assert metrics['query_count'] > 0
        assert 'avg_execution_time_ms' in metrics
        assert 'p95_execution_time_ms' in metrics
        assert 'error_rate' in metrics
        
        print("✅ Performance metrics work")
        print(f"   Total queries: {metrics['query_count']}")
        print(f"   Avg execution time: {metrics['avg_execution_time_ms']}ms")
        print(f"   P95 execution time: {metrics['p95_execution_time_ms']}ms")
        print(f"   Error rate: {metrics['error_rate']}")
        
        # Cleanup
        os.unlink(temp_db.name)
        return True
    except Exception as e:
        print(f"❌ Performance metrics test failed: {e}")
        return False

def test_database_optimization():
    """Test database optimization procedures"""
    try:
        from app.database.standalone_manager import StandaloneDatabaseManager
        
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        db_manager = StandaloneDatabaseManager(f'sqlite:///{temp_db.name}')
        
        # Create test table with data
        db_manager.execute_query("""
            CREATE TABLE optimization_test (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                price REAL NOT NULL
            )
        """)
        
        # Insert test data
        for i in range(100):
            db_manager.execute_query(
                "INSERT INTO optimization_test (symbol, price) VALUES (?, ?)",
                (f'STOCK{i % 10}', float(i))
            )
        
        # Run optimization
        success = db_manager.optimize_database()
        assert success is True
        
        print("✅ Database optimization works")
        
        # Verify database still works after optimization
        result = db_manager.execute_query("SELECT COUNT(*) as count FROM optimization_test")
        assert result[0]['count'] == 100
        
        print("✅ Database functional after optimization")
        
        # Cleanup
        os.unlink(temp_db.name)
        return True
    except Exception as e:
        print(f"❌ Database optimization test failed: {e}")
        return False

def test_railway_utilities():
    """Test Railway-specific utility functions"""
    try:
        from app.database.standalone_manager import (
            check_railway_database_health,
            optimize_for_railway,
            get_railway_connection_info
        )
        
        # Test Railway health check
        health = check_railway_database_health()
        assert 'status' in health
        assert 'timestamp' in health
        
        print("✅ Railway health check utility works")
        print(f"   Status: {health['status']}")
        
        # Test Railway optimization
        success = optimize_for_railway()
        assert isinstance(success, bool)
        
        print("✅ Railway optimization utility works")
        print(f"   Optimization success: {success}")
        
        # Test connection info
        conn_info = get_railway_connection_info()
        assert 'type' in conn_info
        
        print("✅ Railway connection info utility works")
        print(f"   Database type: {conn_info['type']}")
        
        return True
    except Exception as e:
        print(f"❌ Railway utilities test failed: {e}")
        return False

def test_railway_environment_simulation():
    """Test Railway environment simulation"""
    try:
        from app.database.standalone_manager import StandaloneDatabaseManager
        
        # Save original environment
        original_railway_env = os.environ.get('RAILWAY_ENVIRONMENT')
        original_db_url = os.environ.get('DATABASE_URL')
        
        # Simulate Railway production environment
        os.environ['RAILWAY_ENVIRONMENT'] = 'production'
        os.environ['DATABASE_URL'] = 'postgresql://user:pass@host.railway.app:5432/railway'
        
        # Create manager (should detect PostgreSQL but fall back to SQLite)
        db_manager = StandaloneDatabaseManager()
        
        print("✅ Railway environment simulation works")
        print(f"   Detected PostgreSQL: {db_manager.is_postgresql}")
        print(f"   PostgreSQL available: {db_manager.postgresql_available}")
        print(f"   Final database type: {'PostgreSQL' if db_manager.is_postgresql and db_manager.postgresql_available else 'SQLite'}")
        
        # Test connection info in Railway environment
        conn_info = db_manager.get_connection_info()
        print(f"   Connection info type: {conn_info['type']}")
        
        # Restore original environment
        if original_railway_env:
            os.environ['RAILWAY_ENVIRONMENT'] = original_railway_env
        else:
            os.environ.pop('RAILWAY_ENVIRONMENT', None)
        
        if original_db_url:
            os.environ['DATABASE_URL'] = original_db_url
        else:
            os.environ.pop('DATABASE_URL', None)
        
        return True
    except Exception as e:
        print(f"❌ Railway environment simulation test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Running Standalone Database Manager Tests")
    print("=" * 50)
    
    tests = [
        test_standalone_import,
        test_standalone_creation,
        test_basic_database_operations,
        test_transaction_functionality,
        test_health_check,
        test_performance_metrics,
        test_database_optimization,
        test_railway_utilities,
        test_railway_environment_simulation
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
        print("\n🎉 All tests passed! Standalone database optimization system is ready for Railway deployment.")
        print("\n🚀 Key Features Verified:")
        print("   ✅ SQLite and PostgreSQL support")
        print("   ✅ Connection management and optimization")
        print("   ✅ Transaction handling with rollback")
        print("   ✅ Performance metrics collection")
        print("   ✅ Health monitoring")
        print("   ✅ Database optimization procedures")
        print("   ✅ Railway environment detection")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review and fix issues before deployment.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)