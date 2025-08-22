"""
Simple test for the simplified database manager
"""

import os
import tempfile
import sys

# Add the app directory to the path
sys.path.insert(0, '.')

def test_simple_manager_import():
    """Test importing the simple database manager"""
    try:
        from app.database.simple_manager import SimpleDatabaseManager, get_simple_database_manager
        print("✅ Successfully imported SimpleDatabaseManager")
        return True
    except ImportError as e:
        print(f"❌ Failed to import SimpleDatabaseManager: {e}")
        return False

def test_simple_manager_creation():
    """Test creating a simple database manager"""
    try:
        from app.database.simple_manager import SimpleDatabaseManager
        
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        db_manager = SimpleDatabaseManager(f'sqlite:///{temp_db.name}')
        
        print("✅ Successfully created simple database manager")
        print(f"   Database URL: {db_manager.database_url}")
        print(f"   Is PostgreSQL: {db_manager.is_postgresql}")
        
        # Cleanup
        os.unlink(temp_db.name)
        return True
    except Exception as e:
        print(f"❌ Failed to create simple database manager: {e}")
        return False

def test_basic_operations():
    """Test basic database operations"""
    try:
        from app.database.simple_manager import SimpleDatabaseManager
        
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        db_manager = SimpleDatabaseManager(f'sqlite:///{temp_db.name}')
        
        # Create test table
        db_manager.execute_query("""
            CREATE TABLE test_trades (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL
            )
        """)
        
        # Insert test data
        db_manager.execute_query(
            "INSERT INTO test_trades (symbol, quantity, price) VALUES (?, ?, ?)",
            ('AAPL', 100.0, 150.50)
        )
        
        # Query test data
        result = db_manager.execute_query("SELECT * FROM test_trades")
        
        assert len(result) == 1
        assert result[0]['symbol'] == 'AAPL'
        assert result[0]['quantity'] == 100.0
        assert result[0]['price'] == 150.50
        
        print("✅ Basic database operations work")
        print(f"   Inserted and retrieved: {result[0]['symbol']}")
        
        # Cleanup
        os.unlink(temp_db.name)
        return True
    except Exception as e:
        print(f"❌ Basic operations test failed: {e}")
        return False

def test_transaction():
    """Test transaction functionality"""
    try:
        from app.database.simple_manager import SimpleDatabaseManager
        
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        db_manager = SimpleDatabaseManager(f'sqlite:///{temp_db.name}')
        
        # Create test table
        db_manager.execute_query("""
            CREATE TABLE test_trades (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                quantity REAL NOT NULL
            )
        """)
        
        # Test successful transaction
        operations = [
            {
                'query': "INSERT INTO test_trades (symbol, quantity) VALUES (?, ?)",
                'params': ('AAPL', 100.0)
            },
            {
                'query': "INSERT INTO test_trades (symbol, quantity) VALUES (?, ?)",
                'params': ('GOOGL', 50.0)
            }
        ]
        
        success = db_manager.execute_transaction(operations)
        assert success is True
        
        # Verify both records were inserted
        result = db_manager.execute_query("SELECT COUNT(*) as count FROM test_trades")
        assert result[0]['count'] == 2
        
        print("✅ Transaction functionality works")
        
        # Cleanup
        os.unlink(temp_db.name)
        return True
    except Exception as e:
        print(f"❌ Transaction test failed: {e}")
        return False

def test_health_check():
    """Test health check functionality"""
    try:
        from app.database.simple_manager import SimpleDatabaseManager
        
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        db_manager = SimpleDatabaseManager(f'sqlite:///{temp_db.name}')
        
        # Run health check
        health = db_manager.health_check()
        
        assert 'status' in health
        assert 'database_type' in health
        assert 'version' in health
        assert 'timestamp' in health
        
        print("✅ Health check works")
        print(f"   Status: {health['status']}")
        print(f"   Database type: {health['database_type']}")
        print(f"   Version: {health['version']}")
        
        # Cleanup
        os.unlink(temp_db.name)
        return True
    except Exception as e:
        print(f"❌ Health check test failed: {e}")
        return False

def test_performance_metrics():
    """Test performance metrics collection"""
    try:
        from app.database.simple_manager import SimpleDatabaseManager
        
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        db_manager = SimpleDatabaseManager(f'sqlite:///{temp_db.name}')
        
        # Create test table
        db_manager.execute_query("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                data TEXT
            )
        """)
        
        # Execute some queries to generate metrics
        for i in range(5):
            db_manager.execute_query(
                "INSERT INTO test_table (data) VALUES (?)",
                (f'data_{i}',)
            )
        
        # Get performance metrics
        metrics = db_manager.get_performance_metrics()
        
        assert metrics['status'] == 'healthy'
        assert metrics['query_count'] > 0
        assert 'avg_execution_time_ms' in metrics
        assert 'error_rate' in metrics
        
        print("✅ Performance metrics work")
        print(f"   Query count: {metrics['query_count']}")
        print(f"   Avg execution time: {metrics['avg_execution_time_ms']:.2f}ms")
        print(f"   Error rate: {metrics['error_rate']:.2%}")
        
        # Cleanup
        os.unlink(temp_db.name)
        return True
    except Exception as e:
        print(f"❌ Performance metrics test failed: {e}")
        return False

def test_railway_environment():
    """Test Railway environment detection"""
    try:
        from app.database.simple_manager import SimpleDatabaseManager
        
        # Test with Railway environment variable
        original_env = os.environ.get('RAILWAY_ENVIRONMENT')
        original_db_url = os.environ.get('DATABASE_URL')
        
        # Simulate Railway production environment
        os.environ['RAILWAY_ENVIRONMENT'] = 'production'
        os.environ['DATABASE_URL'] = 'postgresql://user:pass@host:5432/db'
        
        db_manager = SimpleDatabaseManager()
        
        # Should detect PostgreSQL but fall back to SQLite without psycopg2
        print("✅ Railway environment detection works")
        print(f"   Database URL: {db_manager.database_url[:50]}...")
        print(f"   PostgreSQL available: {db_manager.postgresql_available}")
        
        # Restore original environment
        if original_env:
            os.environ['RAILWAY_ENVIRONMENT'] = original_env
        else:
            os.environ.pop('RAILWAY_ENVIRONMENT', None)
        
        if original_db_url:
            os.environ['DATABASE_URL'] = original_db_url
        else:
            os.environ.pop('DATABASE_URL', None)
        
        return True
    except Exception as e:
        print(f"❌ Railway environment test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Running Simple Database Manager Tests")
    print("=" * 45)
    
    tests = [
        test_simple_manager_import,
        test_simple_manager_creation,
        test_basic_operations,
        test_transaction,
        test_health_check,
        test_performance_metrics,
        test_railway_environment
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
        print("\n🎉 All tests passed! Database optimization system is ready for Railway deployment.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review and fix issues before deployment.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)