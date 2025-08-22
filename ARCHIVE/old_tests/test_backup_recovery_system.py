"""
Comprehensive tests for the Database Backup and Recovery System
"""

import os
import json
import gzip
import sqlite3
import tempfile
import shutil
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import the system under test
from app.database.backup_recovery_system import (
    BackupRecoverySystem,
    DisasterRecoveryManager,
    BackupType,
    BackupStatus,
    BackupMetadata
)

class TestBackupRecoverySystem:
    """Test suite for BackupRecoverySystem"""
    
    @pytest.fixture
    def temp_database(self):
        """Create a temporary test database"""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test.db")
        
        # Create test database with sample data
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
        
        yield db_path, temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def backup_system(self, temp_database):
        """Create BackupRecoverySystem instance"""
        db_path, temp_dir = temp_database
        backup_dir = os.path.join(temp_dir, "backups")
        return BackupRecoverySystem(db_path, backup_dir)
    
    def test_initialization(self, backup_system):
        """Test system initialization"""
        assert backup_system.database_path
        assert backup_system.backup_directory.exists()
        assert backup_system.max_backup_age_days == 30
        assert backup_system.max_backup_count == 100
        assert backup_system.compression_enabled is True
        assert backup_system.validation_enabled is True
    
    def test_generate_backup_id(self, backup_system):
        """Test backup ID generation"""
        backup_id1 = backup_system.generate_backup_id()
        backup_id2 = backup_system.generate_backup_id()
        
        assert backup_id1 != backup_id2
        assert backup_id1.startswith("backup_")
        assert backup_id2.startswith("backup_")
    
    def test_calculate_checksum(self, backup_system, temp_database):
        """Test checksum calculation"""
        db_path, _ = temp_database
        checksum = backup_system.calculate_checksum(db_path)
        
        assert checksum
        assert len(checksum) == 64  # SHA256 hex length
        
        # Same file should produce same checksum
        checksum2 = backup_system.calculate_checksum(db_path)
        assert checksum == checksum2
    
    def test_create_full_backup_uncompressed(self, backup_system):
        """Test creating uncompressed full backup"""
        backup_system.compression_enabled = False
        backup_system.validation_enabled = False
        
        metadata = backup_system.create_full_backup()
        
        assert metadata is not None
        assert metadata.backup_type == BackupType.FULL
        assert metadata.status == BackupStatus.COMPLETED
        assert metadata.size_bytes > 0
        assert metadata.checksum
        assert Path(metadata.backup_path).exists()
        assert not metadata.backup_path.endswith('.gz')
    
    def test_create_full_backup_compressed(self, backup_system):
        """Test creating compressed full backup"""
        backup_system.compression_enabled = True
        backup_system.validation_enabled = False
        
        metadata = backup_system.create_full_backup()
        
        assert metadata is not None
        assert metadata.backup_type == BackupType.FULL
        assert metadata.status == BackupStatus.COMPLETED
        assert metadata.size_bytes > 0
        assert metadata.checksum
        assert Path(metadata.backup_path).exists()
        assert metadata.backup_path.endswith('.gz')
    
    def test_validate_backup_success(self, backup_system):
        """Test successful backup validation"""
        # Create backup first
        metadata = backup_system.create_full_backup()
        backup_id = metadata.backup_id
        
        # Validate backup
        result = backup_system.validate_backup(backup_id)
        
        assert result is True
        assert backup_system.backup_metadata[backup_id].status == BackupStatus.VALIDATED
        assert backup_system.backup_metadata[backup_id].validation_result is not None
        
        validation_result = backup_system.backup_metadata[backup_id].validation_result
        assert validation_result['file_exists'] is True
        assert validation_result['checksum_valid'] is True
        assert validation_result['database_readable'] is True
        assert validation_result['table_count'] >= 2  # users and trades tables
        assert validation_result['record_count'] >= 4  # 2 users + 2 trades
    
    def test_validate_backup_corrupted_checksum(self, backup_system):
        """Test validation with corrupted checksum"""
        # Create backup first
        metadata = backup_system.create_full_backup()
        backup_id = metadata.backup_id
        
        # Corrupt the checksum in metadata
        backup_system.backup_metadata[backup_id].checksum = "invalid_checksum"
        
        # Validate backup
        result = backup_system.validate_backup(backup_id)
        
        assert result is False
        assert backup_system.backup_metadata[backup_id].status == BackupStatus.CORRUPTED
    
    def test_validate_backup_missing_file(self, backup_system):
        """Test validation with missing backup file"""
        # Create backup first
        metadata = backup_system.create_full_backup()
        backup_id = metadata.backup_id
        
        # Remove the backup file
        Path(metadata.backup_path).unlink()
        
        # Validate backup
        result = backup_system.validate_backup(backup_id)
        
        assert result is False
        assert backup_system.backup_metadata[backup_id].status == BackupStatus.CORRUPTED
    
    def test_restore_from_backup_uncompressed(self, backup_system, temp_database):
        """Test restoring from uncompressed backup"""
        db_path, temp_dir = temp_database
        backup_system.compression_enabled = False
        
        # Create backup
        metadata = backup_system.create_full_backup()
        backup_id = metadata.backup_id
        
        # Modify original database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Test User", "test@example.com"))
        conn.commit()
        conn.close()
        
        # Restore from backup
        result = backup_system.restore_from_backup(backup_id)
        
        assert result is True
        
        # Verify restoration
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        conn.close()
        
        assert user_count == 2  # Original 2 users, not 3
    
    def test_restore_from_backup_compressed(self, backup_system, temp_database):
        """Test restoring from compressed backup"""
        db_path, temp_dir = temp_database
        backup_system.compression_enabled = True
        
        # Create backup
        metadata = backup_system.create_full_backup()
        backup_id = metadata.backup_id
        
        # Modify original database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Test User", "test@example.com"))
        conn.commit()
        conn.close()
        
        # Restore from backup
        result = backup_system.restore_from_backup(backup_id)
        
        assert result is True
        
        # Verify restoration
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        conn.close()
        
        assert user_count == 2  # Original 2 users, not 3
    
    def test_restore_from_invalid_backup(self, backup_system):
        """Test restoring from invalid backup"""
        result = backup_system.restore_from_backup("nonexistent_backup")
        assert result is False
    
    def test_point_in_time_recovery(self, backup_system):
        """Test point-in-time recovery"""
        # Create multiple backups at different times
        backup1 = backup_system.create_full_backup()
        
        # Simulate time passing
        backup_system.backup_metadata[backup1.backup_id].timestamp = datetime.now() - timedelta(hours=2)
        
        backup2 = backup_system.create_full_backup()
        backup_system.backup_metadata[backup2.backup_id].timestamp = datetime.now() - timedelta(hours=1)
        
        # Test recovery to a point between backups
        target_time = datetime.now() - timedelta(minutes=30)
        recovered_backup_id = backup_system.point_in_time_recovery(target_time)
        
        assert recovered_backup_id == backup2.backup_id
    
    def test_point_in_time_recovery_no_suitable_backup(self, backup_system):
        """Test point-in-time recovery with no suitable backup"""
        # Create backup
        backup_system.create_full_backup()
        
        # Try to recover to a time before any backup
        target_time = datetime.now() - timedelta(days=1)
        recovered_backup_id = backup_system.point_in_time_recovery(target_time)
        
        assert recovered_backup_id is None
    
    def test_cleanup_old_backups_by_age(self, backup_system):
        """Test cleanup of old backups by age"""
        backup_system.max_backup_age_days = 1  # 1 day retention
        
        # Create backup and make it old
        metadata = backup_system.create_full_backup()
        backup_id = metadata.backup_id
        
        # Make backup appear old
        old_timestamp = datetime.now() - timedelta(days=2)
        backup_system.backup_metadata[backup_id].timestamp = old_timestamp
        backup_system.save_metadata()
        
        # Run cleanup
        backup_system.cleanup_old_backups()
        
        # Verify backup was removed
        assert backup_id not in backup_system.backup_metadata
        assert not Path(metadata.backup_path).exists()
    
    def test_cleanup_old_backups_by_count(self, backup_system):
        """Test cleanup of excess backups by count"""
        backup_system.max_backup_count = 2
        backup_system.max_backup_age_days = 365  # Don't remove by age
        
        # Create 3 backups
        backup_ids = []
        for i in range(3):
            metadata = backup_system.create_full_backup()
            backup_ids.append(metadata.backup_id)
            # Make each backup slightly older
            timestamp = datetime.now() - timedelta(minutes=i)
            backup_system.backup_metadata[metadata.backup_id].timestamp = timestamp
        
        backup_system.save_metadata()
        
        # Run cleanup
        backup_system.cleanup_old_backups()
        
        # Verify only 2 backups remain (newest ones)
        assert len(backup_system.backup_metadata) == 2
        assert backup_ids[0] not in backup_system.backup_metadata  # Oldest removed
        assert backup_ids[1] in backup_system.backup_metadata
        assert backup_ids[2] in backup_system.backup_metadata
    
    def test_metadata_persistence(self, backup_system):
        """Test backup metadata persistence"""
        # Create backup
        metadata = backup_system.create_full_backup()
        backup_id = metadata.backup_id
        
        # Create new instance (simulating restart)
        new_backup_system = BackupRecoverySystem(
            backup_system.database_path,
            str(backup_system.backup_directory)
        )
        
        # Verify metadata was loaded
        assert backup_id in new_backup_system.backup_metadata
        loaded_metadata = new_backup_system.backup_metadata[backup_id]
        assert loaded_metadata.backup_type == metadata.backup_type
        assert loaded_metadata.status == metadata.status
        assert loaded_metadata.checksum == metadata.checksum
    
    def test_get_backup_status(self, backup_system):
        """Test backup status reporting"""
        # Create some backups
        backup_system.create_full_backup()
        backup_system.create_full_backup()
        
        status = backup_system.get_backup_status()
        
        assert status['total_backups'] == 2
        assert status['valid_backups'] >= 2
        assert status['failed_backups'] == 0
        assert status['total_size_bytes'] > 0
        assert status['total_size_mb'] > 0
        assert status['latest_backup'] is not None
        assert status['scheduler_running'] is False
        assert 'backup_directory' in status
    
    def test_list_backups(self, backup_system):
        """Test backup listing"""
        # Create backups
        backup_system.create_full_backup()
        backup_system.create_full_backup()
        
        backups = backup_system.list_backups()
        
        assert len(backups) == 2
        for backup in backups:
            assert 'backup_id' in backup
            assert 'backup_type' in backup
            assert 'timestamp' in backup
            assert 'status' in backup
            assert 'size_bytes' in backup
            assert 'size_mb' in backup
            assert 'checksum' in backup
    
    @patch('schedule.every')
    def test_schedule_automated_backups(self, mock_schedule, backup_system):
        """Test automated backup scheduling"""
        schedule_config = {
            'full_backup_time': '02:00',
            'full_backup_days': ['sunday'],
            'cleanup_time': '03:00'
        }
        
        backup_system.schedule_automated_backups(schedule_config)
        
        assert backup_system.scheduler_running is True
        assert backup_system.scheduler_thread is not None
        
        # Stop scheduler
        backup_system.stop_automated_backups()
        assert backup_system.scheduler_running is False


class TestDisasterRecoveryManager:
    """Test suite for DisasterRecoveryManager"""
    
    @pytest.fixture
    def temp_database(self):
        """Create a temporary test database"""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test.db")
        
        # Create test database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, data TEXT)")
        cursor.execute("INSERT INTO test (data) VALUES (?)", ("test_data",))
        conn.commit()
        conn.close()
        
        yield db_path, temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def disaster_recovery_manager(self, temp_database):
        """Create DisasterRecoveryManager instance"""
        db_path, temp_dir = temp_database
        backup_dir = os.path.join(temp_dir, "backups")
        backup_system = BackupRecoverySystem(db_path, backup_dir)
        return DisasterRecoveryManager(backup_system)
    
    def test_assess_database_health_healthy(self, disaster_recovery_manager):
        """Test database health assessment for healthy database"""
        health_status = disaster_recovery_manager.assess_database_health()
        
        assert health_status['database_accessible'] is True
        assert health_status['corruption_detected'] is False
        assert health_status['recovery_needed'] is False
        assert 'assessment_timestamp' in health_status
    
    def test_assess_database_health_corrupted(self, disaster_recovery_manager, temp_database):
        """Test database health assessment for corrupted database"""
        db_path, _ = temp_database
        
        # Corrupt the database by writing invalid data
        with open(db_path, 'w') as f:
            f.write("This is not a valid SQLite database")
        
        health_status = disaster_recovery_manager.assess_database_health()
        
        assert health_status['database_accessible'] is False
        assert health_status['recovery_needed'] is True
        assert 'error' in health_status
    
    def test_initiate_disaster_recovery_success(self, disaster_recovery_manager):
        """Test successful disaster recovery"""
        # Create a backup first
        backup_metadata = disaster_recovery_manager.backup_system.create_full_backup()
        
        # Corrupt the database
        with open(disaster_recovery_manager.backup_system.database_path, 'w') as f:
            f.write("corrupted")
        
        # Initiate disaster recovery
        result = disaster_recovery_manager.initiate_disaster_recovery()
        
        assert result is True
        
        # Verify database is accessible again
        health_status = disaster_recovery_manager.assess_database_health()
        assert health_status['database_accessible'] is True
    
    def test_initiate_disaster_recovery_no_backups(self, disaster_recovery_manager):
        """Test disaster recovery with no available backups"""
        # Corrupt the database
        with open(disaster_recovery_manager.backup_system.database_path, 'w') as f:
            f.write("corrupted")
        
        # Initiate disaster recovery (no backups available)
        result = disaster_recovery_manager.initiate_disaster_recovery()
        
        assert result is False
    
    def test_initiate_disaster_recovery_healthy_database(self, disaster_recovery_manager):
        """Test disaster recovery on healthy database"""
        result = disaster_recovery_manager.initiate_disaster_recovery()
        
        # Should return True without doing anything
        assert result is True


class TestIntegration:
    """Integration tests for the complete backup and recovery system"""
    
    @pytest.fixture
    def complete_system(self):
        """Create complete system with database and backups"""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "trading.db")
        backup_dir = os.path.join(temp_dir, "backups")
        
        # Create realistic trading database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create trading schema
        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE portfolio (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                symbol TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                avg_price REAL NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE trades (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                symbol TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                trade_type TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Insert sample data
        cursor.execute("INSERT INTO users (username, email) VALUES (?, ?)", ("trader1", "trader1@example.com"))
        cursor.execute("INSERT INTO users (username, email) VALUES (?, ?)", ("trader2", "trader2@example.com"))
        
        cursor.execute("INSERT INTO portfolio (user_id, symbol, quantity, avg_price) VALUES (?, ?, ?, ?)",
                      (1, "AAPL", 100, 150.0))
        cursor.execute("INSERT INTO portfolio (user_id, symbol, quantity, avg_price) VALUES (?, ?, ?, ?, ?)",
                      (2, "GOOGL", 50, 2500.0))
        
        cursor.execute("INSERT INTO trades (user_id, symbol, quantity, price, trade_type) VALUES (?, ?, ?, ?, ?)",
                      (1, "AAPL", 100, 150.0, "BUY"))
        cursor.execute("INSERT INTO trades (user_id, symbol, quantity, price, trade_type) VALUES (?, ?, ?, ?, ?)",
                      (2, "GOOGL", 50, 2500.0, "BUY"))
        
        conn.commit()
        conn.close()
        
        # Create systems
        backup_system = BackupRecoverySystem(db_path, backup_dir)
        disaster_recovery = DisasterRecoveryManager(backup_system)
        
        yield db_path, backup_system, disaster_recovery, temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_complete_backup_and_recovery_workflow(self, complete_system):
        """Test complete backup and recovery workflow"""
        db_path, backup_system, disaster_recovery, temp_dir = complete_system
        
        # 1. Create initial backup
        backup1 = backup_system.create_full_backup()
        assert backup1.status == BackupStatus.VALIDATED
        
        # 2. Simulate trading activity
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO trades (user_id, symbol, quantity, price, trade_type) VALUES (?, ?, ?, ?, ?)",
                      (1, "MSFT", 75, 300.0, "BUY"))
        cursor.execute("UPDATE portfolio SET quantity = quantity + 75, avg_price = 225.0 WHERE user_id = 1 AND symbol = 'AAPL'")
        conn.commit()
        conn.close()
        
        # 3. Create second backup
        backup2 = backup_system.create_full_backup()
        assert backup2.status == BackupStatus.VALIDATED
        
        # 4. Simulate database corruption
        with open(db_path, 'w') as f:
            f.write("CORRUPTED DATABASE")
        
        # 5. Verify corruption detected
        health_status = disaster_recovery.assess_database_health()
        assert health_status['recovery_needed'] is True
        
        # 6. Perform disaster recovery
        recovery_result = disaster_recovery.initiate_disaster_recovery()
        assert recovery_result is True
        
        # 7. Verify recovery success
        health_status = disaster_recovery.assess_database_health()
        assert health_status['database_accessible'] is True
        assert health_status['recovery_needed'] is False
        
        # 8. Verify data integrity after recovery
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        assert cursor.fetchone()[0] == 2
        
        cursor.execute("SELECT COUNT(*) FROM trades")
        trade_count = cursor.fetchone()[0]
        assert trade_count >= 2  # At least original trades
        
        conn.close()
    
    def test_backup_validation_and_cleanup(self, complete_system):
        """Test backup validation and cleanup procedures"""
        db_path, backup_system, disaster_recovery, temp_dir = complete_system
        
        # Configure for testing
        backup_system.max_backup_count = 3
        backup_system.max_backup_age_days = 1
        
        # Create multiple backups
        backups = []
        for i in range(5):
            backup = backup_system.create_full_backup()
            backups.append(backup)
            
            # Make some backups appear older
            if i < 2:
                old_timestamp = datetime.now() - timedelta(days=2)
                backup_system.backup_metadata[backup.backup_id].timestamp = old_timestamp
        
        backup_system.save_metadata()
        
        # Verify all backups are validated
        for backup in backups:
            assert backup.status == BackupStatus.VALIDATED
        
        # Run cleanup
        backup_system.cleanup_old_backups()
        
        # Verify cleanup worked
        remaining_backups = len(backup_system.backup_metadata)
        assert remaining_backups <= backup_system.max_backup_count
        
        # Verify backup status reporting
        status = backup_system.get_backup_status()
        assert status['total_backups'] == remaining_backups
        assert status['valid_backups'] == remaining_backups
        assert status['failed_backups'] == 0
    
    def test_point_in_time_recovery_scenario(self, complete_system):
        """Test realistic point-in-time recovery scenario"""
        db_path, backup_system, disaster_recovery, temp_dir = complete_system
        
        # Create backup at T0
        backup_t0 = backup_system.create_full_backup()
        time_t0 = datetime.now()
        backup_system.backup_metadata[backup_t0.backup_id].timestamp = time_t0
        
        # Simulate trading activity at T1
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO trades (user_id, symbol, quantity, price, trade_type) VALUES (?, ?, ?, ?, ?)",
                      (1, "TSLA", 25, 800.0, "BUY"))
        conn.commit()
        conn.close()
        
        # Create backup at T1
        backup_t1 = backup_system.create_full_backup()
        time_t1 = time_t0 + timedelta(hours=1)
        backup_system.backup_metadata[backup_t1.backup_id].timestamp = time_t1
        
        # More trading activity at T2
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO trades (user_id, symbol, quantity, price, trade_type) VALUES (?, ?, ?, ?, ?)",
                      (2, "NVDA", 10, 500.0, "BUY"))
        conn.commit()
        conn.close()
        
        # Create backup at T2
        backup_t2 = backup_system.create_full_backup()
        time_t2 = time_t1 + timedelta(hours=1)
        backup_system.backup_metadata[backup_t2.backup_id].timestamp = time_t2
        
        backup_system.save_metadata()
        
        # Perform point-in-time recovery to T1.5 (should use T1 backup)
        target_time = time_t1 + timedelta(minutes=30)
        recovered_backup_id = backup_system.point_in_time_recovery(target_time)
        
        assert recovered_backup_id == backup_t1.backup_id
        
        # Verify database state matches T1
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Should have TSLA trade (from T1) but not NVDA trade (from T2)
        cursor.execute("SELECT COUNT(*) FROM trades WHERE symbol = 'TSLA'")
        tsla_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM trades WHERE symbol = 'NVDA'")
        nvda_count = cursor.fetchone()[0]
        
        conn.close()
        
        assert tsla_count >= 1  # TSLA trade should be present
        assert nvda_count == 0  # NVDA trade should not be present


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])