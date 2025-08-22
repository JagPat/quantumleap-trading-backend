#!/usr/bin/env python3
"""
Simple test script for the Database Backup and Recovery System
"""

import os
import sqlite3
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# Import the system under test
from app.database.backup_recovery_system import (
    BackupRecoverySystem,
    DisasterRecoveryManager,
    BackupType,
    BackupStatus
)

def create_test_database():
    """Create a test database with sample data"""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test.db")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create test tables
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE trades (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            symbol TEXT NOT NULL,
            quantity INTEGER,
            price REAL,
            trade_type TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Insert sample data
    cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("John Doe", "john@example.com"))
    cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Jane Smith", "jane@example.com"))
    
    cursor.execute("INSERT INTO trades (user_id, symbol, quantity, price, trade_type) VALUES (?, ?, ?, ?, ?)",
                  (1, "AAPL", 100, 150.0, "BUY"))
    cursor.execute("INSERT INTO trades (user_id, symbol, quantity, price, trade_type) VALUES (?, ?, ?, ?, ?)",
                  (2, "GOOGL", 50, 2500.0, "BUY"))
    
    conn.commit()
    conn.close()
    
    return db_path, temp_dir

def test_basic_backup_functionality():
    """Test basic backup functionality"""
    print("Testing basic backup functionality...")
    
    # Create test database
    db_path, temp_dir = create_test_database()
    backup_dir = os.path.join(temp_dir, "backups")
    
    try:
        # Create backup system
        backup_system = BackupRecoverySystem(db_path, backup_dir)
        
        # Test 1: Create uncompressed backup
        print("  Creating uncompressed backup...")
        backup_system.compression_enabled = False
        backup_system.validation_enabled = False
        
        metadata = backup_system.create_full_backup()
        
        assert metadata is not None, "Backup creation failed"
        assert metadata.backup_type == BackupType.FULL, "Wrong backup type"
        assert metadata.status == BackupStatus.COMPLETED, "Backup not completed"
        assert metadata.size_bytes > 0, "Backup file is empty"
        assert Path(metadata.backup_path).exists(), "Backup file doesn't exist"
        print("  ✓ Uncompressed backup created successfully")
        
        # Test 2: Create compressed backup
        print("  Creating compressed backup...")
        backup_system.compression_enabled = True
        
        metadata2 = backup_system.create_full_backup()
        
        assert metadata2 is not None, "Compressed backup creation failed"
        assert metadata2.backup_path.endswith('.gz'), "Backup not compressed"
        print("  ✓ Compressed backup created successfully")
        
        # Test 3: Validate backup
        print("  Validating backup...")
        result = backup_system.validate_backup(metadata2.backup_id)
        
        assert result is True, "Backup validation failed"
        assert backup_system.backup_metadata[metadata2.backup_id].status == BackupStatus.VALIDATED
        print("  ✓ Backup validation successful")
        
        # Test 4: Restore from backup
        print("  Testing restore functionality...")
        
        # Modify original database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Test User", "test@example.com"))
        conn.commit()
        conn.close()
        
        # Restore from backup
        result = backup_system.restore_from_backup(metadata2.backup_id)
        
        assert result is True, "Restore failed"
        
        # Verify restoration
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        conn.close()
        
        assert user_count == 2, f"Expected 2 users after restore, got {user_count}"
        print("  ✓ Restore functionality working")
        
        # Test 5: Backup status and listing
        print("  Testing status and listing...")
        
        status = backup_system.get_backup_status()
        assert status['total_backups'] == 2, "Wrong backup count"
        assert status['valid_backups'] >= 1, "No valid backups"
        
        backups = backup_system.list_backups()
        assert len(backups) == 2, "Wrong backup list length"
        print("  ✓ Status and listing working")
        
        print("✓ All basic backup functionality tests passed!")
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)

def test_disaster_recovery():
    """Test disaster recovery functionality"""
    print("\nTesting disaster recovery functionality...")
    
    # Create test database
    db_path, temp_dir = create_test_database()
    backup_dir = os.path.join(temp_dir, "backups")
    
    try:
        # Create systems
        backup_system = BackupRecoverySystem(db_path, backup_dir)
        disaster_recovery = DisasterRecoveryManager(backup_system)
        
        # Test 1: Assess healthy database
        print("  Assessing healthy database...")
        health_status = disaster_recovery.assess_database_health()
        
        assert health_status['database_accessible'] is True, "Database should be accessible"
        assert health_status['recovery_needed'] is False, "Recovery should not be needed"
        print("  ✓ Healthy database assessment correct")
        
        # Test 2: Create backup before corruption
        print("  Creating backup before corruption...")
        backup_metadata = backup_system.create_full_backup()
        assert backup_metadata.status == BackupStatus.VALIDATED, "Backup validation failed"
        print("  ✓ Backup created successfully")
        
        # Test 3: Simulate database corruption
        print("  Simulating database corruption...")
        with open(db_path, 'w') as f:
            f.write("This is not a valid SQLite database")
        
        # Assess corrupted database
        health_status = disaster_recovery.assess_database_health()
        assert health_status['database_accessible'] is False, "Corrupted database should not be accessible"
        assert health_status['recovery_needed'] is True, "Recovery should be needed"
        print("  ✓ Corruption detected correctly")
        
        # Test 4: Perform disaster recovery
        print("  Performing disaster recovery...")
        recovery_result = disaster_recovery.initiate_disaster_recovery()
        
        assert recovery_result is True, "Disaster recovery failed"
        print("  ✓ Disaster recovery successful")
        
        # Test 5: Verify recovery
        print("  Verifying recovery...")
        health_status = disaster_recovery.assess_database_health()
        
        assert health_status['database_accessible'] is True, "Database should be accessible after recovery"
        assert health_status['recovery_needed'] is False, "Recovery should not be needed after recovery"
        
        # Verify data integrity
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM trades")
        trade_count = cursor.fetchone()[0]
        conn.close()
        
        assert user_count == 2, f"Expected 2 users after recovery, got {user_count}"
        assert trade_count == 2, f"Expected 2 trades after recovery, got {trade_count}"
        print("  ✓ Data integrity verified after recovery")
        
        print("✓ All disaster recovery tests passed!")
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)

def test_point_in_time_recovery():
    """Test point-in-time recovery"""
    print("\nTesting point-in-time recovery...")
    
    # Create test database
    db_path, temp_dir = create_test_database()
    backup_dir = os.path.join(temp_dir, "backups")
    
    try:
        backup_system = BackupRecoverySystem(db_path, backup_dir)
        
        # Create backup at T0
        print("  Creating backup at T0...")
        backup1 = backup_system.create_full_backup()
        time_t0 = datetime.now() - timedelta(hours=2)
        backup_system.backup_metadata[backup1.backup_id].timestamp = time_t0
        
        # Modify database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("New User", "new@example.com"))
        conn.commit()
        conn.close()
        
        # Create backup at T1
        print("  Creating backup at T1...")
        backup2 = backup_system.create_full_backup()
        time_t1 = datetime.now() - timedelta(hours=1)
        backup_system.backup_metadata[backup2.backup_id].timestamp = time_t1
        
        backup_system.save_metadata()
        
        # Test point-in-time recovery to T0.5 (should use T0 backup)
        print("  Performing point-in-time recovery...")
        target_time = time_t0 + timedelta(minutes=30)
        recovered_backup_id = backup_system.point_in_time_recovery(target_time)
        
        assert recovered_backup_id == backup1.backup_id, "Wrong backup selected for recovery"
        
        # Verify database state
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        conn.close()
        
        assert user_count == 2, f"Expected 2 users after point-in-time recovery, got {user_count}"
        print("  ✓ Point-in-time recovery successful")
        
        print("✓ Point-in-time recovery test passed!")
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)

def main():
    """Run all tests"""
    print("Starting Database Backup and Recovery System Tests")
    print("=" * 60)
    
    try:
        test_basic_backup_functionality()
        test_disaster_recovery()
        test_point_in_time_recovery()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED! 🎉")
        print("Database Backup and Recovery System is working correctly!")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)