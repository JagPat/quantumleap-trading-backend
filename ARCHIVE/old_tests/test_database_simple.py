"""
Simple test for database optimization system
"""

import os
import tempfile
import sys

# Add the app directory to the path
sys.path.insert(0, '.')

def test_database_manager_import():
    """Test that we can import the database manager"""
    try:
        from app.database.optimized_manager import OptimizedDatabaseManager, DatabaseConfig
        print("✅ Successfully imported OptimizedDatabaseManager")
        return True
    except ImportError as e:
        print(f"❌ Failed to import OptimizedDatabaseManager: {e}")
        return False

def test_railway_config_import():
    """Test that we can import Railway configuration"""
    try:
        from app.database.railway_config import get_railway_database_config, RailwayDatabaseUtils
        print("✅ Successfully imported Railway configuration")
        return True
    except ImportError as e:
        print(f"❌ Failed to import Railway configuration: {e}")
        return False

def test_database_manager_creation():
    """Test creating a database manager instance"""
    try:
        from app.database.optimized_manager import OptimizedDatabaseManager, DatabaseConfig
        
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        config = DatabaseConfig(database_url=f'sqlite:///{temp_db.name}')
        db_manager = OptimizedDatabaseManager(config)
        
        print("✅ Successfully created database manager")
        
        # Cleanup
        os.unlink(temp_db.name)
        return True
    except Exception as e:
        print(f"❌ Failed to create database manager: {e}")
        return False

def test_basic_query():
    """Test basic query execution"""
    try:
        from app.database.optimized_manager import OptimizedDatabaseManager, DatabaseConfig
        
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        config = DatabaseConfig(database_url=f'sqlite:///{temp_db.name}')
        db_manager = OptimizedDatabaseManager(config)
        
        # Create test table
        db_manager.execute_query("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)
        
        # Insert test data
        db_manager.execute_query(
            "INSERT INTO test_table (name) VALUES (?)",
            ('test_name',)
        )
        
        # Query test data
        result = db_manager.execute_query("SELECT * FROM test_table")
        
        assert len(result) == 1
        assert result[0]['name'] == 'test_name'
        
        print("✅ Basic query execution works")
        
        # Cleanup
        os.unlink(temp_db.name)
        return True
    except Exception as e:
        print(f"❌ Basic query test failed: {e}")
        return False

def test_health_check():
    """Test health check functionality"""
    try:
        from app.database.optimized_manager import OptimizedDatabaseManager, DatabaseConfig
        
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        config = DatabaseConfig(database_url=f'sqlite:///{temp_db.name}')
        db_manager = OptimizedDatabaseManager(config)
        
        # Run health check
        health = db_manager.health_check()
        
        assert 'status' in health
        assert 'database' in health
        assert 'timestamp' in health
        
        print("✅ Health check works")
        print(f"   Status: {health['status']}")
        
        # Cleanup
        os.unlink(temp_db.name)
        return True
    except Exception as e:
        print(f"❌ Health check test failed: {e}")
        return False

def test_railway_config():
    """Test Railway configuration"""
    try:
        from app.database.railway_config import get_railway_database_config, validate_railway_environment
        
        config = get_railway_database_config()
        print(f"✅ Railway config created")
        print(f"   Database URL: {config.database_url[:50]}...")
        print(f"   Max connections: {config.max_connections}")
        print(f"   Is Railway: {config.is_railway}")
        
        # Test environment validation
        validation = validate_railway_environment()
        print(f"✅ Environment validation completed")
        print(f"   Valid: {validation['valid']}")
        print(f"   Warnings: {len(validation['warnings'])}")
        
        return True
    except Exception as e:
        print(f"❌ Railway config test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Running Database Optimization Tests")
    print("=" * 40)
    
    tests = [
        test_database_manager_import,
        test_railway_config_import,
        test_database_manager_creation,
        test_basic_query,
        test_health_check,
        test_railway_config
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
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)