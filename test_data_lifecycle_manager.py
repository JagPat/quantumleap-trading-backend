#!/usr/bin/env python3
"""
Test Data Lifecycle Manager
Tests for automated data archival and lifecycle management functionality
"""
import os
import sqlite3
import tempfile
import shutil
import time
from datetime import datetime, timedelta
import sys

# Add the app directory to the path
sys.path.append('app/database')

# Mock the schedule module since it might not be available
class MockScheduleJob:
    def __init__(self):
        pass
    
    @property
    def day(self):
        return self
    
    @property
    def week(self):
        return self
    
    @property
    def month(self):
        return self
    
    def at(self, time_str):
        return self
    
    def do(self, func):
        return self

class MockSchedule:
    def every(self):
        return MockScheduleJob()
    
    def run_pending(self):
        pass
    
    def clear(self):
        pass

# Replace schedule import
sys.modules['schedule'] = MockSchedule()

from data_lifecycle_manager import (
    DataLifecycleManager, ArchivalRule, ArchivalJob, ArchivalStats,
    ArchivalStatus, RetentionPolicy
)

def test_data_lifecycle_manager():
    """Test data lifecycle manager basic functionality"""
    print("🧪 Testing Data Lifecycle Manager...")
    
    # Create temporary test environment
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_lifecycle.db")
    archive_path = os.path.join(test_dir, "archives")
    
    try:
        # Initialize lifecycle manager
        lifecycle_manager = DataLifecycleManager(
            database_path=db_path,
            archive_base_path=archive_path
        )
        
        print("✅ Lifecycle manager initialized successfully")
        
        # Test 1: Check archive directories were created
        assert os.path.exists(archive_path)
        assert os.path.exists(os.path.join(archive_path, "daily"))
        assert os.path.exists(os.path.join(archive_path, "monthly"))
        assert os.path.exists(os.path.join(archive_path, "compressed"))
        print("✅ Archive directories created")
        
        # Test 2: Create archival rule
        rule = ArchivalRule(
            rule_id="test_archive_rule",
            name="Test Archive Rule",
            description="Test archival functionality",
            table_name="test_table",
            date_column="created_at",
            retention_policy=RetentionPolicy.ARCHIVE_AFTER_DAYS,
            retention_days=30,
            archive_location="daily"
        )
        
        success = lifecycle_manager.create_archival_rule(rule)
        assert success
        assert "test_archive_rule" in lifecycle_manager.archival_rules
        print("✅ Archival rule creation works")
        
        # Test 3: Update archival rule
        updates = {"retention_days": 60, "compression_enabled": False}
        success = lifecycle_manager.update_archival_rule("test_archive_rule", updates)
        assert success
        assert lifecycle_manager.archival_rules["test_archive_rule"].retention_days == 60
        assert not lifecycle_manager.archival_rules["test_archive_rule"].compression_enabled
        print("✅ Archival rule updates work")
        
        # Test 4: Get archival rules
        rules = lifecycle_manager.get_archival_rules()
        assert len(rules) >= 1  # At least our test rule plus any defaults
        print("✅ Archival rules retrieval works")
        
        # Test 5: Get statistics
        stats = lifecycle_manager.get_archival_statistics()
        assert isinstance(stats, ArchivalStats)
        assert stats.total_rules >= 1
        print("✅ Statistics retrieval works")
        
        # Test 6: Delete archival rule
        success = lifecycle_manager.delete_archival_rule("test_archive_rule")
        assert success
        assert "test_archive_rule" not in lifecycle_manager.archival_rules
        print("✅ Archival rule deletion works")
        
        print("🎉 All basic tests passed!")
        
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

def test_archival_execution():
    """Test archival execution functionality"""
    print("\n🧪 Testing Archival Execution...")
    
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_archival.db")
    archive_path = os.path.join(test_dir, "archives")
    
    try:
        # Initialize lifecycle manager
        lifecycle_manager = DataLifecycleManager(
            database_path=db_path,
            archive_base_path=archive_path
        )
        
        # Create test table with data
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Create test table
            cursor.execute("""
                CREATE TABLE test_data (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            
            # Insert test data (some old, some new)
            old_date = (datetime.now() - timedelta(days=45)).isoformat()
            new_date = (datetime.now() - timedelta(days=15)).isoformat()
            
            test_data = [
                (1, "Old Record 1", old_date),
                (2, "Old Record 2", old_date),
                (3, "New Record 1", new_date),
                (4, "New Record 2", new_date)
            ]
            
            cursor.executemany("""
                INSERT INTO test_data (id, name, created_at) VALUES (?, ?, ?)
            """, test_data)
            
            conn.commit()
        
        print("✅ Test data created")
        
        # Create archival rule for test data
        rule = ArchivalRule(
            rule_id="test_data_archive",
            name="Test Data Archive",
            description="Archive old test data",
            table_name="test_data",
            date_column="created_at",
            retention_policy=RetentionPolicy.ARCHIVE_AFTER_DAYS,
            retention_days=30,
            archive_location="daily",
            compression_enabled=False  # Disable compression for easier testing
        )
        
        lifecycle_manager.create_archival_rule(rule)
        
        # Execute archival rule
        job = lifecycle_manager.execute_archival_rule("test_data_archive")
        assert job is not None
        assert job.status == "completed"
        assert job.records_processed == 2  # Should process 2 old records
        assert job.records_archived == 2   # Should archive 2 old records
        print("✅ Archival execution works")
        
        # Check that old data was removed from main table
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM test_data")
            remaining_count = cursor.fetchone()[0]
            assert remaining_count == 2  # Only new records should remain
        
        print("✅ Old data removed from main table")
        
        # Check that archive file was created
        assert job.archive_file_path is not None
        assert os.path.exists(job.archive_file_path)
        print("✅ Archive file created")
        
        return True
        
    except Exception as e:
        print(f"❌ Archival execution test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

def test_data_deletion():
    """Test data deletion functionality"""
    print("\n🧪 Testing Data Deletion...")
    
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_deletion.db")
    archive_path = os.path.join(test_dir, "archives")
    
    try:
        # Initialize lifecycle manager
        lifecycle_manager = DataLifecycleManager(
            database_path=db_path,
            archive_base_path=archive_path
        )
        
        # Create test table with data
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Create test table
            cursor.execute("""
                CREATE TABLE temp_logs (
                    id INTEGER PRIMARY KEY,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            
            # Insert test data
            old_date = (datetime.now() - timedelta(days=35)).isoformat()
            new_date = (datetime.now() - timedelta(days=10)).isoformat()
            
            test_data = [
                (1, "Old Log 1", old_date),
                (2, "Old Log 2", old_date),
                (3, "New Log 1", new_date),
                (4, "New Log 2", new_date)
            ]
            
            cursor.executemany("""
                INSERT INTO temp_logs (id, message, timestamp) VALUES (?, ?, ?)
            """, test_data)
            
            conn.commit()
        
        # Create deletion rule
        rule = ArchivalRule(
            rule_id="temp_logs_cleanup",
            name="Temp Logs Cleanup",
            description="Delete old temporary logs",
            table_name="temp_logs",
            date_column="timestamp",
            retention_policy=RetentionPolicy.DELETE_AFTER_DAYS,
            retention_days=30,
            archive_location="temp"
        )
        
        lifecycle_manager.create_archival_rule(rule)
        
        # Execute deletion rule
        job = lifecycle_manager.execute_archival_rule("temp_logs_cleanup")
        assert job is not None
        assert job.status == "completed"
        assert job.records_processed == 2  # Should process 2 old records
        print("✅ Data deletion works")
        
        # Check that old data was deleted
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM temp_logs")
            remaining_count = cursor.fetchone()[0]
            assert remaining_count == 2  # Only new records should remain
        
        print("✅ Old data deleted from table")
        
        return True
        
    except Exception as e:
        print(f"❌ Data deletion test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

def test_archive_retrieval():
    """Test archived data retrieval"""
    print("\n🧪 Testing Archive Retrieval...")
    
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_retrieval.db")
    archive_path = os.path.join(test_dir, "archives")
    
    try:
        # Initialize lifecycle manager
        lifecycle_manager = DataLifecycleManager(
            database_path=db_path,
            archive_base_path=archive_path
        )
        
        # Create and populate test table
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE historical_data (
                    id INTEGER PRIMARY KEY,
                    value REAL NOT NULL,
                    recorded_at TEXT NOT NULL
                )
            """)
            
            # Insert old data that will be archived
            old_date = (datetime.now() - timedelta(days=40)).isoformat()
            
            test_data = [
                (1, 100.5, old_date),
                (2, 200.7, old_date)
            ]
            
            cursor.executemany("""
                INSERT INTO historical_data (id, value, recorded_at) VALUES (?, ?, ?)
            """, test_data)
            
            conn.commit()
        
        # Create and execute archival rule
        rule = ArchivalRule(
            rule_id="historical_data_archive",
            name="Historical Data Archive",
            description="Archive old historical data",
            table_name="historical_data",
            date_column="recorded_at",
            retention_policy=RetentionPolicy.ARCHIVE_AFTER_DAYS,
            retention_days=30,
            archive_location="daily",
            compression_enabled=False
        )
        
        lifecycle_manager.create_archival_rule(rule)
        job = lifecycle_manager.execute_archival_rule("historical_data_archive")
        
        assert job is not None
        assert job.status == "completed"
        print("✅ Data archived successfully")
        
        # Test retrieval
        start_date = datetime.now() - timedelta(days=50)
        end_date = datetime.now() - timedelta(days=30)
        
        retrieved_file = lifecycle_manager.retrieve_archived_data(
            "historical_data", start_date, end_date
        )
        
        assert retrieved_file is not None
        assert os.path.exists(retrieved_file)
        print("✅ Archived data retrieved successfully")
        
        # Verify retrieved data contains expected content
        with open(retrieved_file, 'r') as f:
            content = f.read()
            assert "historical_data" in content
            assert "100.5" in content
            assert "200.7" in content
        
        print("✅ Retrieved data contains expected content")
        
        # Cleanup retrieved file
        os.unlink(retrieved_file)
        
        return True
        
    except Exception as e:
        print(f"❌ Archive retrieval test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

def test_lifecycle_management():
    """Test lifecycle management start/stop"""
    print("\n🧪 Testing Lifecycle Management...")
    
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_lifecycle_mgmt.db")
    archive_path = os.path.join(test_dir, "archives")
    
    try:
        # Initialize lifecycle manager
        lifecycle_manager = DataLifecycleManager(
            database_path=db_path,
            archive_base_path=archive_path
        )
        
        # Test start
        assert not lifecycle_manager.is_running
        lifecycle_manager.start_lifecycle_management()
        assert lifecycle_manager.is_running
        assert lifecycle_manager.scheduler_thread is not None
        print("✅ Lifecycle management started")
        
        # Wait a moment
        time.sleep(1)
        
        # Test stop
        lifecycle_manager.stop_lifecycle_management()
        assert not lifecycle_manager.is_running
        print("✅ Lifecycle management stopped")
        
        return True
        
    except Exception as e:
        print(f"❌ Lifecycle management test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            if 'lifecycle_manager' in locals():
                lifecycle_manager.stop_lifecycle_management()
        except:
            pass
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

def test_data_persistence():
    """Test data persistence across restarts"""
    print("\n🧪 Testing Data Persistence...")
    
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_persistence.db")
    archive_path = os.path.join(test_dir, "archives")
    
    try:
        # Create first instance and add data
        lifecycle_manager1 = DataLifecycleManager(
            database_path=db_path,
            archive_base_path=archive_path
        )
        
        rule = ArchivalRule(
            rule_id="persistent_rule",
            name="Persistent Rule",
            description="Test persistence",
            table_name="test_table",
            date_column="created_at",
            retention_policy=RetentionPolicy.ARCHIVE_AFTER_DAYS,
            retention_days=90,
            archive_location="daily"
        )
        
        lifecycle_manager1.create_archival_rule(rule)
        
        initial_rules_count = len(lifecycle_manager1.archival_rules)
        assert initial_rules_count >= 1
        print("✅ Data created in first instance")
        
        # Create second instance (simulating restart)
        lifecycle_manager2 = DataLifecycleManager(
            database_path=db_path,
            archive_base_path=archive_path
        )
        
        # Check that data was loaded
        assert len(lifecycle_manager2.archival_rules) == initial_rules_count
        assert "persistent_rule" in lifecycle_manager2.archival_rules
        print("✅ Data persisted across restart")
        
        # Verify rule details
        loaded_rule = lifecycle_manager2.archival_rules["persistent_rule"]
        assert loaded_rule.name == "Persistent Rule"
        assert loaded_rule.retention_days == 90
        assert loaded_rule.retention_policy == RetentionPolicy.ARCHIVE_AFTER_DAYS
        print("✅ Rule details preserved correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Data persistence test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

if __name__ == "__main__":
    print("🚀 Starting Data Lifecycle Manager Tests\n")
    
    success1 = test_data_lifecycle_manager()
    success2 = test_archival_execution()
    success3 = test_data_deletion()
    success4 = test_archive_retrieval()
    success5 = test_lifecycle_management()
    success6 = test_data_persistence()
    
    if all([success1, success2, success3, success4, success5, success6]):
        print("\n🎉 All tests completed successfully!")
        print("✅ Data Lifecycle Manager is working correctly")
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)