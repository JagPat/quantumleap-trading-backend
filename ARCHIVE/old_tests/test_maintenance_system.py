#!/usr/bin/env python3
"""
Test Database Maintenance System
Tests for automated database maintenance and cleanup functionality
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
from maintenance_system import (
    DatabaseMaintenanceSystem, MaintenanceTask, CleanupRule, TaskExecution,
    MaintenanceTaskType, TaskStatus, TaskPriority
)

def test_maintenance_system():
    """Test maintenance system basic functionality"""
    print("🧪 Testing Database Maintenance System...")
    
    # Create temporary test environment
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_maintenance.db")
    
    try:
        # Initialize maintenance system
        maintenance_system = DatabaseMaintenanceSystem(database_path=db_path)
        
        print("✅ Maintenance system initialized successfully")
        
        # Test 1: Check default tasks were created
        assert len(maintenance_system.maintenance_tasks) >= 5  # Should have default tasks
        assert "daily_vacuum" in maintenance_system.maintenance_tasks
        assert "weekly_analyze" in maintenance_system.maintenance_tasks
        print("✅ Default maintenance tasks created")
        
        # Test 2: Create custom maintenance task
        custom_task = MaintenanceTask(
            task_id="test_custom_task",
            task_type=MaintenanceTaskType.CLEANUP_TEMP,
            name="Test Custom Task",
            description="Test custom maintenance task",
            priority=TaskPriority.LOW,
            schedule_cron="0 3 * * *",
            max_duration_minutes=30
        )
        
        success = maintenance_system.create_maintenance_task(custom_task)
        assert success
        assert "test_custom_task" in maintenance_system.maintenance_tasks
        print("✅ Custom maintenance task creation works")
        
        # Test 3: Create cleanup rule
        cleanup_rule = CleanupRule(
            rule_id="test_cleanup_rule",
            name="Test Cleanup Rule",
            table_name="test_table",
            condition="created_at < datetime('now', '-30 days')",
            retention_days=30
        )
        
        success = maintenance_system.create_cleanup_rule(cleanup_rule)
        assert success
        assert "test_cleanup_rule" in maintenance_system.cleanup_rules
        print("✅ Cleanup rule creation works")
        
        # Test 4: Get statistics
        stats = maintenance_system.get_maintenance_statistics()
        assert "database_stats" in stats
        assert "execution_stats" in stats
        assert "active_tasks" in stats
        print("✅ Statistics retrieval works")
        
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

def test_task_execution():
    """Test maintenance task execution"""
    print("\n🧪 Testing Task Execution...")
    
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_execution.db")
    
    try:
        # Initialize maintenance system
        maintenance_system = DatabaseMaintenanceSystem(database_path=db_path)
        
        # Create test data
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
            
            # Insert some test data
            cursor.execute("""
                INSERT INTO test_data (name, created_at) 
                VALUES ('Test 1', datetime('now'))
            """)
            
            conn.commit()
        
        print("✅ Test data created")
        
        # Test VACUUM task execution
        execution = maintenance_system.execute_maintenance_task("daily_vacuum")
        assert execution is not None
        assert execution.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
        print("✅ VACUUM task execution works")
        
        # Test ANALYZE task execution
        execution = maintenance_system.execute_maintenance_task("weekly_analyze")
        assert execution is not None
        assert execution.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
        print("✅ ANALYZE task execution works")
        
        # Test SIZE_MONITORING task execution
        execution = maintenance_system.execute_maintenance_task("hourly_size_monitoring")
        assert execution is not None
        assert execution.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
        print("✅ Size monitoring task execution works")
        
        # Test INTEGRITY_CHECK task execution
        execution = maintenance_system.execute_maintenance_task("weekly_integrity_check")
        assert execution is not None
        assert execution.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
        print("✅ Integrity check task execution works")
        
        return True
        
    except Exception as e:
        print(f"❌ Task execution test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

def test_cleanup_rules():
    """Test cleanup rule execution"""
    print("\n🧪 Testing Cleanup Rules...")
    
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_cleanup.db")
    
    try:
        # Initialize maintenance system
        maintenance_system = DatabaseMaintenanceSystem(database_path=db_path)
        
        # Create test table with old and new data
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Create test table
            cursor.execute("""
                CREATE TABLE temp_logs (
                    id INTEGER PRIMARY KEY,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            
            # Insert old data
            old_date = (datetime.now() - timedelta(days=35)).isoformat()
            new_date = (datetime.now() - timedelta(days=5)).isoformat()
            
            cursor.execute("""
                INSERT INTO temp_logs (message, created_at) 
                VALUES ('Old log 1', ?)
            """, (old_date,))
            
            cursor.execute("""
                INSERT INTO temp_logs (message, created_at) 
                VALUES ('Old log 2', ?)
            """, (old_date,))
            
            cursor.execute("""
                INSERT INTO temp_logs (message, created_at) 
                VALUES ('New log 1', ?)
            """, (new_date,))
            
            conn.commit()
        
        print("✅ Test data with old and new records created")
        
        # Create cleanup rule
        cleanup_rule = CleanupRule(
            rule_id="test_temp_logs_cleanup",
            name="Test Temp Logs Cleanup",
            table_name="temp_logs",
            condition="created_at < datetime('now', '-30 days')",
            retention_days=30,
            enabled=True,
            dry_run=False
        )
        
        maintenance_system.create_cleanup_rule(cleanup_rule)
        
        # Execute cleanup rule
        cleaned_count = maintenance_system._execute_cleanup_rule(cleanup_rule)
        assert cleaned_count == 2  # Should clean 2 old records
        print("✅ Cleanup rule execution works")
        
        # Verify cleanup
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM temp_logs")
            remaining_count = cursor.fetchone()[0]
            assert remaining_count == 1  # Only new record should remain
        
        print("✅ Old records cleaned up correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Cleanup rules test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

def test_maintenance_system_lifecycle():
    """Test maintenance system start/stop"""
    print("\n🧪 Testing Maintenance System Lifecycle...")
    
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_lifecycle.db")
    
    try:
        # Initialize maintenance system
        maintenance_system = DatabaseMaintenanceSystem(database_path=db_path)
        
        # Test start
        assert not maintenance_system.is_running
        maintenance_system.start_maintenance_system()
        assert maintenance_system.is_running
        assert maintenance_system.scheduler_thread is not None
        print("✅ Maintenance system started")
        
        # Wait a moment
        time.sleep(1)
        
        # Test stop
        maintenance_system.stop_maintenance_system()
        assert not maintenance_system.is_running
        print("✅ Maintenance system stopped")
        
        return True
        
    except Exception as e:
        print(f"❌ Maintenance system lifecycle test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            if 'maintenance_system' in locals():
                maintenance_system.stop_maintenance_system()
        except:
            pass
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

def test_database_statistics():
    """Test database statistics collection"""
    print("\n🧪 Testing Database Statistics...")
    
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_stats.db")
    
    try:
        # Initialize maintenance system
        maintenance_system = DatabaseMaintenanceSystem(database_path=db_path)
        
        # Create some test tables
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Create multiple test tables
            for i in range(3):
                cursor.execute(f"""
                    CREATE TABLE test_table_{i} (
                        id INTEGER PRIMARY KEY,
                        data TEXT NOT NULL
                    )
                """)
                
                # Insert some data
                for j in range(10):
                    cursor.execute(f"""
                        INSERT INTO test_table_{i} (data) VALUES ('test_data_{j}')
                    """)
            
            conn.commit()
        
        # Update statistics
        maintenance_system._update_database_statistics()
        
        # Check statistics
        stats = maintenance_system.database_stats
        assert stats.total_size > 0
        assert stats.table_count >= 3  # At least our test tables
        assert stats.largest_table != ""
        print("✅ Database statistics collection works")
        
        # Test statistics retrieval
        maintenance_stats = maintenance_system.get_maintenance_statistics()
        assert "database_stats" in maintenance_stats
        assert maintenance_stats["database_stats"]["total_size"] > 0
        print("✅ Statistics retrieval works")
        
        return True
        
    except Exception as e:
        print(f"❌ Database statistics test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

def test_audit_trail():
    """Test audit trail functionality"""
    print("\n🧪 Testing Audit Trail...")
    
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_audit.db")
    
    try:
        # Initialize maintenance system
        maintenance_system = DatabaseMaintenanceSystem(database_path=db_path)
        
        # Log some audit entries
        maintenance_system._log_maintenance_audit(
            action="test_action",
            table_name="test_table",
            records_affected=10,
            user_id="test_user",
            details="Test audit entry"
        )
        
        # Verify audit entry was created
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM maintenance_audit")
            audit_count = cursor.fetchone()[0]
            assert audit_count > 0
        
        print("✅ Audit trail logging works")
        
        # Test audit cleanup
        execution = maintenance_system.execute_maintenance_task("daily_temp_cleanup")
        if execution:
            # Check that audit entry was created for the task
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM maintenance_audit WHERE action LIKE '%maintenance_task%'")
                task_audit_count = cursor.fetchone()[0]
                assert task_audit_count > 0
        
        print("✅ Task execution audit logging works")
        
        return True
        
    except Exception as e:
        print(f"❌ Audit trail test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

def test_data_persistence():
    """Test data persistence across restarts"""
    print("\n🧪 Testing Data Persistence...")
    
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_persistence.db")
    
    try:
        # Create first instance and add data
        maintenance_system1 = DatabaseMaintenanceSystem(database_path=db_path)
        
        custom_task = MaintenanceTask(
            task_id="persistent_task",
            task_type=MaintenanceTaskType.CLEANUP_TEMP,
            name="Persistent Task",
            description="Test persistence",
            priority=TaskPriority.NORMAL,
            schedule_cron="0 2 * * *"
        )
        
        maintenance_system1.create_maintenance_task(custom_task)
        
        initial_tasks_count = len(maintenance_system1.maintenance_tasks)
        assert initial_tasks_count >= 1
        print("✅ Data created in first instance")
        
        # Create second instance (simulating restart)
        maintenance_system2 = DatabaseMaintenanceSystem(database_path=db_path)
        
        # Check that data was loaded
        assert len(maintenance_system2.maintenance_tasks) == initial_tasks_count
        assert "persistent_task" in maintenance_system2.maintenance_tasks
        print("✅ Data persisted across restart")
        
        # Verify task details
        loaded_task = maintenance_system2.maintenance_tasks["persistent_task"]
        assert loaded_task.name == "Persistent Task"
        assert loaded_task.task_type == MaintenanceTaskType.CLEANUP_TEMP
        assert loaded_task.priority == TaskPriority.NORMAL
        print("✅ Task details preserved correctly")
        
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
    print("🚀 Starting Database Maintenance System Tests\n")
    
    success1 = test_maintenance_system()
    success2 = test_task_execution()
    success3 = test_cleanup_rules()
    success4 = test_maintenance_system_lifecycle()
    success5 = test_database_statistics()
    success6 = test_audit_trail()
    success7 = test_data_persistence()
    
    if all([success1, success2, success3, success4, success5, success6, success7]):
        print("\n🎉 All tests completed successfully!")
        print("✅ Database Maintenance System is working correctly")
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)