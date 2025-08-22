#!/usr/bin/env python3
"""
Test Schema Version Manager
Tests for schema versioning and conflict resolution functionality
"""
import os
import sqlite3
import tempfile
import shutil
import json
from datetime import datetime
import sys

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from database.schema_version_manager import (
    SchemaVersionManager, SchemaVersion, SchemaConflict, SchemaDiff,
    ConflictType, MergeStrategy
)

class TestSchemaVersionManager:
    """Test cases for SchemaVersionManager"""
    
    def setup_method(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_schema.db")
        self.migrations_dir = os.path.join(self.test_dir, "migrations")
        os.makedirs(self.migrations_dir, exist_ok=True)
        
        # Create test migration files
        self.create_test_migration_files()
        
        # Initialize manager
        self.manager = SchemaVersionManager(
            database_path=self.db_path,
            migrations_dir=self.migrations_dir
        )
    
    def teardown_method(self):
        """Clean up test environment"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def create_test_migration_files(self):
        """Create test migration files"""
        # Migration 1: Create users table
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
        
        with open(os.path.join(self.migrations_dir, "001_create_users.sql"), 'w') as f:
            f.write(migration1)
        
        # Migration 2: Create portfolio table
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
        
        with open(os.path.join(self.migrations_dir, "002_create_portfolio.sql"), 'w') as f:
            f.write(migration2)
        
        # Migration 3: Conflicting users table (different column)
        migration3 = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL,
            full_name TEXT,  -- Different from migration 1
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        
        CREATE INDEX idx_users_username ON users(username);
        """
        
        with open(os.path.join(self.migrations_dir, "003_conflicting_users.sql"), 'w') as f:
            f.write(migration3)
    
    def test_initialization(self):
        """Test manager initialization"""
        assert self.manager is not None
        assert os.path.exists(self.db_path)
        
        # Check that version tracking tables were created
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            assert "schema_versions" in tables
            assert "schema_conflicts" in tables
            assert "schema_metadata" in tables
    
    def test_register_version(self):
        """Test version registration"""
        version = self.manager.register_version(
            version="1.0.0",
            description="Initial schema",
            author="test_user",
            migration_files=["001_create_users.sql"],
            dependencies=[]
        )
        
        assert version.version == "1.0.0"
        assert version.description == "Initial schema"
        assert version.author == "test_user"
        assert not version.applied
        assert len(version.migration_files) == 1
        assert version.checksum is not None
        
        # Check that version was stored in database
        assert "1.0.0" in self.manager.versions
    
    def test_duplicate_version_registration(self):
        """Test that duplicate version registration fails"""
        self.manager.register_version(
            version="1.0.0",
            description="Initial schema",
            author="test_user",
            migration_files=["001_create_users.sql"]
        )
        
        # Try to register same version again
        try:
            self.manager.register_version(
                version="1.0.0",
                description="Duplicate schema",
                author="test_user",
                migration_files=["002_create_portfolio.sql"]
            )
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Version 1.0.0 already exists" in str(e)
    
    def test_version_dependencies(self):
        """Test version dependency management"""
        # Register base version
        self.manager.register_version(
            version="1.0.0",
            description="Base schema",
            author="test_user",
            migration_files=["001_create_users.sql"]
        )
        
        # Register dependent version
        self.manager.register_version(
            version="1.1.0",
            description="Portfolio schema",
            author="test_user",
            migration_files=["002_create_portfolio.sql"],
            dependencies=["1.0.0"]
        )
        
        # Check dependencies
        deps = self.manager.get_version_dependencies("1.1.0")
        assert "1.0.0" in deps
    
    def test_conflict_detection(self):
        """Test conflict detection between versions"""
        # Register first version
        version1 = self.manager.register_version(
            version="1.0.0",
            description="Initial users schema",
            author="test_user",
            migration_files=["001_create_users.sql"]
        )
        
        # Mark first version as applied
        version1.applied = True
        
        # Register conflicting version
        self.manager.register_version(
            version="2.0.0",
            description="Conflicting users schema",
            author="test_user",
            migration_files=["003_conflicting_users.sql"]
        )
        
        # Check for conflicts
        conflicts = self.manager.get_conflicts(resolved=False)
        assert len(conflicts) > 0
        
        # Verify conflict details
        conflict = conflicts[0]
        assert conflict.conflict_type in [ConflictType.TABLE_CONFLICT, ConflictType.COLUMN_CONFLICT]
        assert conflict.version_a in ["1.0.0", "2.0.0"]
        assert conflict.version_b in ["1.0.0", "2.0.0"]
    
    def test_schema_parsing(self):
        """Test schema parsing from migration files"""
        schema = self.manager._parse_migration_schema(["001_create_users.sql"])
        
        assert "users" in schema["tables"]
        assert "id" in schema["tables"]["users"]
        assert "username" in schema["tables"]["users"]
        assert "email" in schema["tables"]["users"]
        
        assert "idx_users_username" in schema["indexes"]
        assert "idx_users_email" in schema["indexes"]
    
    def test_schema_diff_generation(self):
        """Test schema diff generation"""
        # Register two versions
        self.manager.register_version(
            version="1.0.0",
            description="Initial schema",
            author="test_user",
            migration_files=["001_create_users.sql"]
        )
        
        self.manager.register_version(
            version="1.1.0",
            description="Add portfolio",
            author="test_user",
            migration_files=["001_create_users.sql", "002_create_portfolio.sql"]
        )
        
        # Generate diff
        diff = self.manager.generate_schema_diff("1.0.0", "1.1.0")
        
        assert "portfolio" in diff.added_tables
        assert len(diff.removed_tables) == 0
        assert "idx_portfolio_user_id" in diff.added_indexes
    
    def test_circular_dependency_detection(self):
        """Test circular dependency detection"""
        # Create circular dependencies
        self.manager.register_version(
            version="1.0.0",
            description="Version A",
            author="test_user",
            migration_files=["001_create_users.sql"],
            dependencies=["1.2.0"]  # Depends on future version
        )
        
        self.manager.register_version(
            version="1.1.0",
            description="Version B",
            author="test_user",
            migration_files=["002_create_portfolio.sql"],
            dependencies=["1.0.0"]
        )
        
        self.manager.register_version(
            version="1.2.0",
            description="Version C",
            author="test_user",
            migration_files=["003_conflicting_users.sql"],
            dependencies=["1.1.0"]
        )
        
        # Check for circular dependencies
        cycles = self.manager.detect_circular_dependencies()
        assert len(cycles) > 0
    
    def test_conflict_resolution(self):
        """Test conflict resolution"""
        # Create a conflict scenario
        version1 = self.manager.register_version(
            version="1.0.0",
            description="Initial schema",
            author="test_user",
            migration_files=["001_create_users.sql"]
        )
        version1.applied = True
        
        self.manager.register_version(
            version="2.0.0",
            description="Conflicting schema",
            author="test_user",
            migration_files=["003_conflicting_users.sql"]
        )
        
        # Get conflicts
        conflicts = self.manager.get_conflicts(resolved=False)
        if conflicts:
            conflict_id = conflicts[0].conflict_id
            
            # Resolve conflict
            success = self.manager.resolve_conflict(
                conflict_id=conflict_id,
                strategy=MergeStrategy.LATEST_WINS,
                resolution_notes="Using latest version"
            )
            
            assert success
            
            # Check that conflict is marked as resolved
            resolved_conflicts = self.manager.get_conflicts(resolved=True)
            assert len(resolved_conflicts) > 0
    
    def test_version_status(self):
        """Test version status reporting"""
        # Register some versions
        self.manager.register_version(
            version="1.0.0",
            description="Initial schema",
            author="test_user",
            migration_files=["001_create_users.sql"]
        )
        
        version2 = self.manager.register_version(
            version="1.1.0",
            description="Add portfolio",
            author="test_user",
            migration_files=["002_create_portfolio.sql"]
        )
        
        # Mark one as applied
        version2.applied = True
        version2.applied_at = datetime.now()
        
        # Get status
        status = self.manager.get_version_status()
        
        assert status["total_versions"] == 2
        assert status["applied_versions"] == 1
        assert status["pending_versions"] == 1
        assert status["latest_applied_version"] == "1.1.0"
    
    def test_export_version_history(self):
        """Test version history export"""
        # Register a version
        self.manager.register_version(
            version="1.0.0",
            description="Test version",
            author="test_user",
            migration_files=["001_create_users.sql"]
        )
        
        # Export history
        export_file = os.path.join(self.test_dir, "version_history.json")
        self.manager.export_version_history(export_file)
        
        assert os.path.exists(export_file)
        
        # Verify export content
        with open(export_file, 'r') as f:
            history = json.load(f)
        
        assert "versions" in history
        assert "conflicts" in history
        assert "dependency_graph" in history
        assert "exported_at" in history
        assert "1.0.0" in history["versions"]

def run_basic_tests():
    """Run basic functionality tests"""
    print("🧪 Testing Schema Version Manager...")
    
    # Create temporary test environment
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_schema.db")
    migrations_dir = os.path.join(test_dir, "migrations")
    os.makedirs(migrations_dir, exist_ok=True)
    
    try:
        # Create test migration file
        migration_content = """
        CREATE TABLE IF NOT EXISTS test_table (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        
        CREATE INDEX idx_test_name ON test_table(name);
        """
        
        with open(os.path.join(migrations_dir, "001_test.sql"), 'w') as f:
            f.write(migration_content)
        
        # Initialize manager
        manager = SchemaVersionManager(
            database_path=db_path,
            migrations_dir=migrations_dir
        )
        
        print("✅ Manager initialized successfully")
        
        # Test version registration
        version = manager.register_version(
            version="1.0.0",
            description="Test version",
            author="test_user",
            migration_files=["001_test.sql"]
        )
        
        print(f"✅ Version registered: {version.version}")
        
        # Test version status
        status = manager.get_version_status()
        print(f"✅ Version status: {status}")
        
        # Test schema parsing
        schema = manager._parse_migration_schema(["001_test.sql"])
        print(f"✅ Schema parsed: {len(schema['tables'])} tables, {len(schema['indexes'])} indexes")
        
        # Test export
        export_file = os.path.join(test_dir, "test_export.json")
        manager.export_version_history(export_file)
        print(f"✅ History exported to: {export_file}")
        
        print("🎉 All basic tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise
    finally:
        # Cleanup
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

if __name__ == "__main__":
    run_basic_tests()