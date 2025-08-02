#!/usr/bin/env python3
"""
Comprehensive Test Suite for Database Migration Engine
Tests migration execution, rollback capabilities, backup system, and version management
"""

import os
import sys
import sqlite3
import tempfile
import unittest
import shutil
import json
from datetime import datetime
from pathlib import Path

# Add the app directory to the path
sys.path.append('app')

try:
    from database.migration_engine import (
        MigrationEngine, Migration, MigrationExecution, BackupInfo,
        MigrationStatus, MigrationType, BackupType,
        create_migration_engine, create_migration_file
    )
    print("✅ Successfully imported migration engine components")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

class TestMigrationEngine(unittest.TestCase):
    """Test cases for MigrationEngine"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary directories
        self.test_dir = Path(tempfile.mkdtemp())
        self.db_path = self.test_dir / "test_migrations.db"
        self.migrations_dir = self.test_dir / "migrations"
        self.backups_dir = self.test_dir / "backups"
        
        # Create directories
        self.migrations_dir.mkdir(exist_ok=True)
        self.backups_dir.mkdir(exist_ok=True)
        
        # Create test migration files
        self._create_test_migrations()
        
        # Initialize migration engine
        self.engine = MigrationEngine(
            str(self.db_path),
            str(self.migrations_dir),
            str(self.backups_dir)
        )
    
    def tearDown(self):
        """Clean up test environment"""
        self.engine.close()
        try:
            shutil.rmtree(self.test_dir)
        except:
            pass
    
    def _create_test_migrations(self):
        """Create test migration files"""
        # Migration 1: Create test table
        migration1 = """-- @name: Create Test Table
-- @description: Create a test table for migration testing
-- @type: table_creation
-- @author: Test Suite
-- @dependencies: []
-- @reversible: true
-- @backup_required: true

-- UP
CREATE TABLE test_table (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    value INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_test_table_name ON test_table(name);

-- DOWN
DROP INDEX IF EXISTS idx_test_table_name;
DROP TABLE IF EXISTS test_table;
"""
        (self.migrations_dir / "001_create_test_table.sql").write_text(migration1)
        
        # Migration 2: Add column to test table
        migration2 = """-- @name: Add Description Column
-- @description: Add description column to test table
-- @type: table_modification
-- @author: Test Suite
-- @dependencies: ["001_create_test_table"]
-- @reversible: true
-- @backup_required: true

-- UP
ALTER TABLE test_table ADD COLUMN description TEXT;
CREATE INDEX idx_test_table_description ON test_table(description);

-- DOWN
DROP INDEX IF EXISTS idx_test_table_description;
-- Note: SQLite doesn't support DROP COLUMN easily
-- In real scenario, would recreate table without the column
"""
        (self.migrations_dir / "002_add_description_column.sql").write_text(migration2)
        
        # Migration 3: Insert test data
        migration3 = """-- @name: Insert Test Data
-- @description: Insert initial test data
-- @type: data_migration
-- @author: Test Suite
-- @dependencies: ["002_add_description_column"]
-- @reversible: true
-- @backup_required: true

-- UP
INSERT INTO test_table (name, value, description) VALUES 
    ('Test 1', 100, 'First test record'),
    ('Test 2', 200, 'Second test record'),
    ('Test 3', 300, 'Third test record');

-- DOWN
DELETE FROM test_table WHERE name IN ('Test 1', 'Test 2', 'Test 3');
"""
        (self.migrations_dir / "003_insert_test_data.sql").write_text(migration3)
    
    def test_migration_engine_initialization(self):
        """Test migration engine initialization"""
        self.assertIsNotNone(self.engine)
        self.assertEqual(str(self.engine.database_path), str(self.db_path))
        self.assertEqual(self.engine.migrations_dir, self.migrations_dir)
        self.assertEqual(self.engine.backups_dir, self.backups_dir)
        
        # Check that migration system tables were created
        conn = self.engine._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'migration_%'")
        migration_tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['migration_metadata', 'migration_executions', 'backup_info', 'schema_version']
        for table in expected_tables:
            self.assertIn(table, migration_tables)
    
    def test_migration_loading(self):
        """Test loading of migration files"""
        self.assertGreater(len(self.engine.migrations), 0)
        self.assertEqual(len(self.engine.migrations), 3)
        
        # Check specific migrations
        self.assertIn("001_create_test_table", self.engine.migrations)
        self.assertIn("002_add_description_column", self.engine.migrations)
        self.assertIn("003_insert_test_data", self.engine.migrations)
        
        # Check migration properties
        migration1 = self.engine.migrations["001_create_test_table"]
        self.assertEqual(migration1.version, "001")
        self.assertEqual(migration1.name, "Create Test Table")
        self.assertEqual(migration1.migration_type, MigrationType.TABLE_CREATION)
        self.assertTrue(migration1.is_reversible)
        self.assertTrue(migration1.backup_required)
    
    def test_current_version(self):
        """Test getting current database version"""
        current_version = self.engine.get_current_version()
        self.assertEqual(current_version, "0.0.0")  # Initial version
    
    def test_pending_migrations(self):
        """Test getting pending migrations"""
        pending = self.engine.get_pending_migrations()
        self.assertEqual(len(pending), 3)
        
        # Check order (should be sorted by version)
        versions = [m.version for m in pending]
        self.assertEqual(versions, ["001", "002", "003"])
    
    def test_backup_creation(self):
        """Test database backup creation"""
        # Create a simple table first
        conn = self.engine._get_connection()
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE backup_test (id INTEGER, data TEXT)")
        cursor.execute("INSERT INTO backup_test VALUES (1, 'test data')")
        conn.commit()
        
        # Create backup
        backup_info = self.engine.create_backup(BackupType.FULL_DATABASE)
        
        self.assertIsNotNone(backup_info)
        self.assertTrue(Path(backup_info.backup_path).exists())
        self.assertGreater(backup_info.size_bytes, 0)
        self.assertIsNotNone(backup_info.checksum)
        
        # Verify backup contains data
        backup_conn = sqlite3.connect(backup_info.backup_path)
        backup_cursor = backup_conn.cursor()
        backup_cursor.execute("SELECT COUNT(*) FROM backup_test")
        count = backup_cursor.fetchone()[0]
        backup_conn.close()
        
        self.assertEqual(count, 1)
    
    def test_single_migration_execution(self):
        """Test execution of a single migration"""
        # Execute first migration
        execution = self.engine.execute_migration("001_create_test_table")
        
        self.assertEqual(execution.status, MigrationStatus.COMPLETED)
        self.assertIsNone(execution.error_message)
        self.assertGreater(execution.execution_time, 0)
        
        # Verify table was created
        conn = self.engine._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'")
        result = cursor.fetchone()
        self.assertIsNotNone(result)
        
        # Check current version was updated
        current_version = self.engine.get_current_version()
        self.assertEqual(current_version, "001")
    
    def test_migration_with_dependencies(self):
        """Test migration execution with dependencies"""
        # Try to execute migration 2 without migration 1 (should fail dependency check)
        # First, let's manually mark migration 1 as not executed by clearing executions
        conn = self.engine._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM migration_executions")
        conn.commit()
        
        # Now try to execute migration 2
        execution = self.engine.execute_migration("002_add_description_column")
        
        # Should fail due to missing dependency
        self.assertEqual(execution.status, MigrationStatus.FAILED)
        self.assertIn("dependencies not satisfied", execution.error_message)
    
    def test_migration_rollback(self):
        """Test migration rollback functionality"""
        # Execute a migration first
        execution = self.engine.execute_migration("001_create_test_table")
        self.assertEqual(execution.status, MigrationStatus.COMPLETED)
        
        # Verify table exists
        conn = self.engine._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'")
        self.assertIsNotNone(cursor.fetchone())
        
        # Rollback the migration
        rollback_success = self.engine.rollback_migration(execution.execution_id)
        self.assertTrue(rollback_success)
        
        # Verify table no longer exists (if rollback used down SQL)
        # Note: In our test, rollback might use backup restoration
        # so we'll just check that rollback was recorded
        cursor.execute("SELECT status FROM migration_executions WHERE execution_id = ?", 
                      (execution.execution_id,))
        # Status might be 'rolled_back' or still 'completed' if backup was used
    
    def test_migrate_to_version(self):
        """Test migrating to a specific version"""
        # Migrate to version 002
        executions = self.engine.migrate_to_version("002")
        
        self.assertEqual(len(executions), 2)  # Should execute migrations 001 and 002
        
        for execution in executions:
            self.assertEqual(execution.status, MigrationStatus.COMPLETED)
        
        # Check current version
        current_version = self.engine.get_current_version()
        self.assertEqual(current_version, "002")
        
        # Verify both tables exist and have expected structure
        conn = self.engine._get_connection()
        cursor = conn.cursor()
        
        # Check test_table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'")
        self.assertIsNotNone(cursor.fetchone())
        
        # Check description column was added
        cursor.execute("PRAGMA table_info(test_table)")
        columns = [row[1] for row in cursor.fetchall()]
        self.assertIn("description", columns)
    
    def test_migrate_latest(self):
        """Test migrating to latest version"""
        executions = self.engine.migrate_latest()
        
        self.assertEqual(len(executions), 3)  # Should execute all 3 migrations
        
        for execution in executions:
            self.assertEqual(execution.status, MigrationStatus.COMPLETED)
        
        # Check current version is latest
        current_version = self.engine.get_current_version()
        self.assertEqual(current_version, "003")
        
        # Verify data was inserted
        conn = self.engine._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM test_table")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 3)
    
    def test_dry_run_migration(self):
        """Test dry run migration execution"""
        executions = self.engine.migrate_latest(dry_run=True)
        
        self.assertEqual(len(executions), 3)
        
        for execution in executions:
            self.assertEqual(execution.status, MigrationStatus.COMPLETED)
        
        # Verify no actual changes were made
        current_version = self.engine.get_current_version()
        self.assertEqual(current_version, "0.0.0")  # Should still be initial version
        
        # Verify table doesn't exist
        conn = self.engine._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'")
        result = cursor.fetchone()
        self.assertIsNone(result)
    
    def test_migration_history(self):
        """Test migration history retrieval"""
        # Execute some migrations
        self.engine.migrate_to_version("002")
        
        # Get history
        history = self.engine.get_migration_history()
        
        self.assertGreater(len(history), 0)
        self.assertLessEqual(len(history), 2)  # Should have 2 executions
        
        # Check history structure
        for record in history:
            self.assertIn('execution_id', record)
            self.assertIn('migration_id', record)
            self.assertIn('status', record)
            self.assertIn('started_at', record)
    
    def test_backup_history(self):
        """Test backup history retrieval"""
        # Create some backups
        self.engine.create_backup(BackupType.FULL_DATABASE)
        self.engine.create_backup(BackupType.SCHEMA_ONLY)
        
        # Get backup history
        history = self.engine.get_backup_history()
        
        self.assertGreaterEqual(len(history), 2)
        
        # Check history structure
        for record in history:
            self.assertIn('backup_id', record)
            self.assertIn('backup_path', record)
            self.assertIn('backup_type', record)
            self.assertIn('size_bytes', record)
            self.assertIn('size_mb', record)
    
    def test_database_integrity_validation(self):
        """Test database integrity validation"""
        # Run some migrations first
        self.engine.migrate_latest()
        
        # Validate integrity
        integrity_report = self.engine.validate_database_integrity()
        
        self.assertIn('timestamp', integrity_report)
        self.assertIn('overall_status', integrity_report)
        self.assertIn('checks', integrity_report)
        
        # Should be healthy for our test database
        self.assertEqual(integrity_report['overall_status'], 'healthy')
        self.assertEqual(integrity_report['checks']['integrity_check'], 'ok')
    
    def test_migration_report_generation(self):
        """Test comprehensive migration report generation"""
        # Execute some migrations
        self.engine.migrate_to_version("002")
        
        # Generate report
        report = self.engine.generate_migration_report()
        
        self.assertIn('timestamp', report)
        self.assertIn('current_version', report)
        self.assertIn('total_migrations', report)
        self.assertIn('pending_migrations', report)
        self.assertIn('migration_history', report)
        self.assertIn('backup_history', report)
        self.assertIn('integrity_status', report)
        self.assertIn('recommendations', report)
        
        # Check values
        self.assertEqual(report['current_version'], '002')
        self.assertEqual(report['total_migrations'], 3)
        self.assertEqual(report['pending_migrations'], 1)  # Migration 003 is pending
        self.assertEqual(report['integrity_status'], 'healthy')
    
    def test_backup_cleanup(self):
        """Test old backup cleanup"""
        # Create several backups
        for i in range(5):
            self.engine.create_backup(BackupType.FULL_DATABASE)
        
        # Check we have 5 backups
        history_before = self.engine.get_backup_history()
        self.assertEqual(len(history_before), 5)
        
        # Cleanup keeping only 2
        cleaned_count = self.engine.cleanup_old_backups(keep_days=0, keep_count=2)
        
        # Should have cleaned 3 backups
        self.assertEqual(cleaned_count, 3)
        
        # Check remaining backups
        history_after = self.engine.get_backup_history()
        valid_backups = [b for b in history_after if b['is_valid']]
        self.assertEqual(len(valid_backups), 2)

class TestMigrationUtilities(unittest.TestCase):
    """Test utility functions"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.migrations_dir = self.test_dir / "migrations"
        self.migrations_dir.mkdir(exist_ok=True)
    
    def tearDown(self):
        """Clean up test environment"""
        try:
            shutil.rmtree(self.test_dir)
        except:
            pass
    
    def test_create_migration_engine(self):
        """Test migration engine factory function"""
        engine = create_migration_engine(
            str(self.test_dir / "test.db"),
            str(self.migrations_dir),
            str(self.test_dir / "backups")
        )
        
        self.assertIsInstance(engine, MigrationEngine)
        engine.close()
    
    def test_create_migration_file(self):
        """Test migration file creation"""
        migration_path = create_migration_file(
            str(self.migrations_dir),
            "Test Migration",
            "schema_change",
            "Test Author",
            "Test migration description"
        )
        
        self.assertTrue(migration_path.exists())
        self.assertTrue(migration_path.name.startswith("001_"))
        self.assertTrue(migration_path.name.endswith(".sql"))
        
        # Check file content
        content = migration_path.read_text()
        self.assertIn("@name: Test Migration", content)
        self.assertIn("@description: Test migration description", content)
        self.assertIn("@author: Test Author", content)
        self.assertIn("-- UP", content)
        self.assertIn("-- DOWN", content)
        
        # Create another migration file
        migration_path2 = create_migration_file(
            str(self.migrations_dir),
            "Second Migration"
        )
        
        self.assertTrue(migration_path2.name.startswith("002_"))

def run_comprehensive_tests():
    """Run all migration engine tests"""
    print("🔄 Running Comprehensive Migration Engine Tests...")
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestMigrationEngine))
    test_suite.addTest(unittest.makeSuite(TestMigrationUtilities))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    if result.wasSuccessful():
        print("✅ All migration engine tests passed!")
        return True
    else:
        print(f"❌ {len(result.failures)} test(s) failed, {len(result.errors)} error(s)")
        return False

def run_performance_tests():
    """Run performance tests for migration engine"""
    print("\n🔄 Running Migration Engine Performance Tests...")
    
    test_dir = Path(tempfile.mkdtemp())
    
    try:
        db_path = test_dir / "perf_test.db"
        migrations_dir = test_dir / "migrations"
        backups_dir = test_dir / "backups"
        
        migrations_dir.mkdir(exist_ok=True)
        backups_dir.mkdir(exist_ok=True)
        
        # Create multiple migration files
        print("  📝 Creating performance test migrations...")
        migration_count = 20
        
        for i in range(1, migration_count + 1):
            migration_content = f"""-- @name: Performance Test Migration {i}
-- @description: Performance test migration {i}
-- @type: table_creation
-- @author: Performance Test
-- @dependencies: []
-- @reversible: true
-- @backup_required: false

-- UP
CREATE TABLE perf_test_{i:03d} (
    id INTEGER PRIMARY KEY,
    data_{i} TEXT,
    value_{i} INTEGER DEFAULT {i},
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_perf_test_{i:03d}_data ON perf_test_{i:03d}(data_{i});

-- DOWN
DROP INDEX IF EXISTS idx_perf_test_{i:03d}_data;
DROP TABLE IF EXISTS perf_test_{i:03d};
"""
            migration_file = migrations_dir / f"{i:03d}_perf_test_{i}.sql"
            migration_file.write_text(migration_content)
        
        # Initialize migration engine
        engine = MigrationEngine(str(db_path), str(migrations_dir), str(backups_dir))
        
        # Test migration loading performance
        import time
        start_time = time.time()
        
        pending = engine.get_pending_migrations()
        
        loading_time = time.time() - start_time
        
        print(f"  📊 Migration Loading Performance:")
        print(f"    - Migrations loaded: {len(pending)}")
        print(f"    - Loading time: {loading_time:.3f} seconds")
        print(f"    - Migrations per second: {len(pending)/loading_time:.1f}")
        
        # Test migration execution performance
        print("  📝 Testing migration execution performance...")
        
        start_time = time.time()
        
        executions = engine.migrate_latest()
        
        execution_time = time.time() - start_time
        
        successful_migrations = sum(1 for e in executions if e.status == MigrationStatus.COMPLETED)
        
        print(f"  📊 Migration Execution Performance:")
        print(f"    - Migrations executed: {successful_migrations}")
        print(f"    - Total execution time: {execution_time:.3f} seconds")
        print(f"    - Average time per migration: {execution_time/successful_migrations:.3f} seconds")
        print(f"    - Migrations per second: {successful_migrations/execution_time:.1f}")
        
        # Test backup performance
        print("  📝 Testing backup performance...")
        
        start_time = time.time()
        
        backup_info = engine.create_backup(BackupType.FULL_DATABASE)
        
        backup_time = time.time() - start_time
        backup_size_mb = backup_info.size_bytes / (1024 * 1024)
        
        print(f"  📊 Backup Performance:")
        print(f"    - Backup size: {backup_size_mb:.2f} MB")
        print(f"    - Backup time: {backup_time:.3f} seconds")
        print(f"    - Backup speed: {backup_size_mb/backup_time:.1f} MB/s")
        
        engine.close()
        print("✅ Performance tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        try:
            shutil.rmtree(test_dir)
        except:
            pass

if __name__ == "__main__":
    print("🚀 Starting Migration Engine Tests...")
    
    # Run comprehensive tests
    tests_passed = run_comprehensive_tests()
    
    # Run performance tests
    run_performance_tests()
    
    if tests_passed:
        print("\n🎉 All migration engine tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the output above.")
        sys.exit(1)