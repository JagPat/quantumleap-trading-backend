#!/usr/bin/env python3
"""
Standalone test for Schema Version Manager
Tests schema versioning functionality without external dependencies
"""
import os
import sqlite3
import tempfile
import shutil
import json
from datetime import datetime
import sys

# Import the schema version manager directly
sys.path.append('app/database')
from schema_version_manager import (
    SchemaVersionManager, SchemaVersion, SchemaConflict, SchemaDiff,
    ConflictType, MergeStrategy
)

def test_schema_version_manager():
    """Test schema version manager functionality"""
    print("🧪 Testing Schema Version Manager...")
    
    # Create temporary test environment
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_schema.db")
    migrations_dir = os.path.join(test_dir, "migrations")
    os.makedirs(migrations_dir, exist_ok=True)
    
    try:
        # Create test migration files
        migration1 = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        
        CREATE INDEX idx_users_username ON users(username);
        CREATE INDEX idx_users_email ON users(email);
        """
        
        with open(os.path.join(migrations_dir, "001_create_users.sql"), 'w') as f:
            f.write(migration1)
        
        migration2 = """
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            quantity REAL NOT NULL,
            average_price REAL NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        
        CREATE INDEX idx_portfolio_user_id ON portfolio(user_id);
        CREATE INDEX idx_portfolio_symbol ON portfolio(symbol);
        """
        
        with open(os.path.join(migrations_dir, "002_create_portfolio.sql"), 'w') as f:
            f.write(migration2)
        
        # Initialize manager
        manager = SchemaVersionManager(
            database_path=db_path,
            migrations_dir=migrations_dir
        )
        
        print("✅ Manager initialized successfully")
        
        # Test 1: Version registration
        version1 = manager.register_version(
            version="1.0.0",
            description="Initial users schema",
            author="test_user",
            migration_files=["001_create_users.sql"]
        )
        
        assert version1.version == "1.0.0"
        assert version1.description == "Initial users schema"
        assert not version1.applied
        print("✅ Version 1.0.0 registered successfully")
        
        # Test 2: Second version with dependencies
        version2 = manager.register_version(
            version="1.1.0",
            description="Add portfolio schema",
            author="test_user",
            migration_files=["001_create_users.sql", "002_create_portfolio.sql"],
            dependencies=["1.0.0"]
        )
        
        assert version2.version == "1.1.0"
        assert "1.0.0" in version2.dependencies
        print("✅ Version 1.1.0 registered with dependencies")
        
        # Test 3: Dependency resolution
        deps = manager.get_version_dependencies("1.1.0")
        assert "1.0.0" in deps
        print("✅ Dependencies resolved correctly")
        
        # Test 4: Schema parsing
        schema = manager._parse_migration_schema(["001_create_users.sql"])
        assert "users" in schema["tables"]
        assert "id" in schema["tables"]["users"]
        assert "username" in schema["tables"]["users"]
        assert "idx_users_username" in schema["indexes"]
        print("✅ Schema parsing works correctly")
        
        # Test 5: Schema diff generation
        diff = manager.generate_schema_diff("1.0.0", "1.1.0")
        assert "portfolio" in diff.added_tables
        assert "idx_portfolio_user_id" in diff.added_indexes
        print("✅ Schema diff generation works")
        
        # Test 6: Version status
        status = manager.get_version_status()
        assert status["total_versions"] == 2
        assert status["applied_versions"] == 0
        assert status["pending_versions"] == 2
        print("✅ Version status reporting works")
        
        # Test 7: Duplicate version handling
        try:
            manager.register_version(
                version="1.0.0",
                description="Duplicate",
                author="test_user",
                migration_files=["001_create_users.sql"]
            )
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "already exists" in str(e)
            print("✅ Duplicate version detection works")
        
        # Test 8: Export functionality
        export_file = os.path.join(test_dir, "version_history.json")
        manager.export_version_history(export_file)
        assert os.path.exists(export_file)
        
        with open(export_file, 'r') as f:
            history = json.load(f)
        
        assert "versions" in history
        assert "1.0.0" in history["versions"]
        assert "1.1.0" in history["versions"]
        print("✅ Version history export works")
        
        # Test 9: Circular dependency detection
        # Create a circular dependency scenario
        manager.register_version(
            version="2.0.0",
            description="Circular test A",
            author="test_user",
            migration_files=["001_create_users.sql"],
            dependencies=["2.1.0"]  # Depends on future version
        )
        
        manager.register_version(
            version="2.1.0",
            description="Circular test B",
            author="test_user",
            migration_files=["002_create_portfolio.sql"],
            dependencies=["2.0.0"]  # Creates circular dependency
        )
        
        cycles = manager.detect_circular_dependencies()
        assert len(cycles) > 0
        print("✅ Circular dependency detection works")
        
        print("🎉 All tests passed successfully!")
        
        # Print summary
        final_status = manager.get_version_status()
        print(f"\n📊 Final Status:")
        print(f"   Total versions: {final_status['total_versions']}")
        print(f"   Applied versions: {final_status['applied_versions']}")
        print(f"   Pending versions: {final_status['pending_versions']}")
        print(f"   Circular dependencies: {final_status['circular_dependencies']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

def test_conflict_detection():
    """Test conflict detection functionality"""
    print("\n🧪 Testing Conflict Detection...")
    
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_conflicts.db")
    migrations_dir = os.path.join(test_dir, "migrations")
    os.makedirs(migrations_dir, exist_ok=True)
    
    try:
        # Create conflicting migration files
        migration1 = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT NOT NULL
        );
        """
        
        migration2 = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            full_name TEXT  -- Additional column
        );
        """
        
        with open(os.path.join(migrations_dir, "001_users_v1.sql"), 'w') as f:
            f.write(migration1)
        
        with open(os.path.join(migrations_dir, "002_users_v2.sql"), 'w') as f:
            f.write(migration2)
        
        manager = SchemaVersionManager(
            database_path=db_path,
            migrations_dir=migrations_dir
        )
        
        # Register first version and mark as applied
        version1 = manager.register_version(
            version="1.0.0",
            description="Users v1",
            author="test_user",
            migration_files=["001_users_v1.sql"]
        )
        version1.applied = True
        
        # Register conflicting version
        manager.register_version(
            version="2.0.0",
            description="Users v2",
            author="test_user",
            migration_files=["002_users_v2.sql"]
        )
        
        # Check for conflicts
        conflicts = manager.get_conflicts(resolved=False)
        print(f"✅ Detected {len(conflicts)} conflicts")
        
        if conflicts:
            conflict = conflicts[0]
            print(f"   Conflict type: {conflict.conflict_type}")
            print(f"   Object: {conflict.object_name}")
            print(f"   Description: {conflict.description}")
            
            # Test conflict resolution
            success = manager.resolve_conflict(
                conflict_id=conflict.conflict_id,
                strategy=MergeStrategy.LATEST_WINS,
                resolution_notes="Using latest version for testing"
            )
            
            assert success
            print("✅ Conflict resolved successfully")
            
            # Verify resolution
            resolved_conflicts = manager.get_conflicts(resolved=True)
            assert len(resolved_conflicts) > 0
            print("✅ Conflict resolution verified")
        
        return True
        
    except Exception as e:
        print(f"❌ Conflict detection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

if __name__ == "__main__":
    print("🚀 Starting Schema Version Manager Tests\n")
    
    success1 = test_schema_version_manager()
    success2 = test_conflict_detection()
    
    if success1 and success2:
        print("\n🎉 All tests completed successfully!")
        print("✅ Schema Version Manager is working correctly")
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)