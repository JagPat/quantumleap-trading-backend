#!/usr/bin/env python3
"""
Standalone test script for the Database Backup and Recovery System
"""

import os
import json
import gzip
import shutil
import sqlite3
import hashlib
import logging
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import time

# Inline implementation for testing
class BackupType(Enum):
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"

class BackupStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VALIDATED = "validated"
    CORRUPTED = "corrupted"

@dataclass
class BackupMetadata:
    backup_id: str
    backup_type: BackupType
    timestamp: datetime
    database_path: str
    backup_path: str
    size_bytes: int
    checksum: str
    status: BackupStatus
    validation_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class BackupRecoverySystem:
    """
    Comprehensive backup and recovery system for database operations
    """
    
    def __init__(self, database_path: str, backup_directory: str = "backups"):
        self.database_path = database_path
        self.backup_directory = Path(backup_directory)
        self.backup_directory.mkdir(exist_ok=True)
        
        # Configuration
        self.max_backup_age_days = 30
        self.max_backup_count = 100
        self.compression_enabled = True
        self.validation_enabled = True
        
        # Metadata storage
        self.metadata_file = self.backup_directory / "backup_metadata.json"
        self.backup_metadata: Dict[str, BackupMetadata] = {}
        self.load_metadata()
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
    def load_metadata(self):
        """Load backup metadata from storage"""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r') as f:
                    data = json.load(f)
                    for backup_id, metadata_dict in data.items():
                        # Convert string timestamp back to datetime
                        metadata_dict['timestamp'] = datetime.fromisoformat(metadata_dict['timestamp'])
                        metadata_dict['backup_type'] = BackupType(metadata_dict['backup_type'])
                        metadata_dict['status'] = BackupStatus(metadata_dict['status'])
                        self.backup_metadata[backup_id] = BackupMetadata(**metadata_dict)
        except Exception as e:
            self.logger.error(f"Failed to load backup metadata: {e}")
            self.backup_metadata = {}
    
    def save_metadata(self):
        """Save backup metadata to storage"""
        try:
            # Convert metadata to serializable format
            serializable_data = {}
            for backup_id, metadata in self.backup_metadata.items():
                metadata_dict = asdict(metadata)
                metadata_dict['timestamp'] = metadata.timestamp.isoformat()
                metadata_dict['backup_type'] = metadata.backup_type.value
                metadata_dict['status'] = metadata.status.value
                serializable_data[backup_id] = metadata_dict
            
            with open(self.metadata_file, 'w') as f:
                json.dump(serializable_data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save backup metadata: {e}")
    
    def generate_backup_id(self) -> str:
        """Generate unique backup ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")  # Include microseconds for uniqueness
        return f"backup_{timestamp}_{os.getpid()}"
    
    def calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of a file"""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            self.logger.error(f"Failed to calculate checksum for {file_path}: {e}")
            return ""
    
    def create_full_backup(self) -> Optional[BackupMetadata]:
        """Create a full database backup"""
        backup_id = self.generate_backup_id()
        timestamp = datetime.now()
        
        try:
            # Create backup filename
            backup_filename = f"{backup_id}_full.db"
            if self.compression_enabled:
                backup_filename += ".gz"
            
            backup_path = self.backup_directory / backup_filename
            
            # Create metadata entry
            metadata = BackupMetadata(
                backup_id=backup_id,
                backup_type=BackupType.FULL,
                timestamp=timestamp,
                database_path=self.database_path,
                backup_path=str(backup_path),
                size_bytes=0,
                checksum="",
                status=BackupStatus.IN_PROGRESS
            )
            
            self.backup_metadata[backup_id] = metadata
            self.save_metadata()
            
            print(f"Starting full backup: {backup_id}")
            
            # Perform backup using SQLite backup API
            if self.compression_enabled:
                self._create_compressed_backup(backup_path)
            else:
                self._create_uncompressed_backup(backup_path)
            
            # Update metadata with file information
            if backup_path.exists():
                metadata.size_bytes = backup_path.stat().st_size
                metadata.checksum = self.calculate_checksum(str(backup_path))
                metadata.status = BackupStatus.COMPLETED
                
                print(f"Full backup completed: {backup_id}, Size: {metadata.size_bytes} bytes")
            else:
                metadata.status = BackupStatus.FAILED
                metadata.error_message = "Backup file not created"
                print(f"Full backup failed: {backup_id}")
            
            self.save_metadata()
            
            # Validate backup if enabled
            if self.validation_enabled and metadata.status == BackupStatus.COMPLETED:
                self.validate_backup(backup_id)
            
            return metadata
            
        except Exception as e:
            print(f"Failed to create full backup {backup_id}: {e}")
            if backup_id in self.backup_metadata:
                self.backup_metadata[backup_id].status = BackupStatus.FAILED
                self.backup_metadata[backup_id].error_message = str(e)
                self.save_metadata()
            return None
    
    def _create_compressed_backup(self, backup_path: Path):
        """Create compressed backup using gzip"""
        temp_path = backup_path.with_suffix('')
        
        # First create uncompressed backup
        self._create_uncompressed_backup(temp_path)
        
        # Then compress it
        with open(temp_path, 'rb') as f_in:
            with gzip.open(backup_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Remove temporary uncompressed file
        temp_path.unlink()
    
    def _create_uncompressed_backup(self, backup_path: Path):
        """Create uncompressed backup using SQLite backup API"""
        source_conn = sqlite3.connect(self.database_path)
        backup_conn = sqlite3.connect(str(backup_path))
        
        try:
            # Use SQLite backup API for consistent backup
            source_conn.backup(backup_conn)
        finally:
            source_conn.close()
            backup_conn.close()
    
    def validate_backup(self, backup_id: str) -> bool:
        """Validate backup integrity and consistency"""
        if backup_id not in self.backup_metadata:
            print(f"Backup {backup_id} not found in metadata")
            return False
        
        metadata = self.backup_metadata[backup_id]
        
        try:
            print(f"Validating backup: {backup_id}")
            
            validation_result = {
                'file_exists': False,
                'checksum_valid': False,
                'database_readable': False,
                'table_count': 0,
                'record_count': 0,
                'validation_timestamp': datetime.now().isoformat()
            }
            
            backup_path = Path(metadata.backup_path)
            
            # Check if backup file exists
            if not backup_path.exists():
                validation_result['error'] = "Backup file does not exist"
                metadata.status = BackupStatus.CORRUPTED
                metadata.validation_result = validation_result
                self.save_metadata()
                return False
            
            validation_result['file_exists'] = True
            
            # Validate checksum
            current_checksum = self.calculate_checksum(metadata.backup_path)
            if current_checksum == metadata.checksum:
                validation_result['checksum_valid'] = True
            else:
                validation_result['error'] = f"Checksum mismatch"
                metadata.status = BackupStatus.CORRUPTED
                metadata.validation_result = validation_result
                self.save_metadata()
                return False
            
            # Test database readability
            temp_db_path = self.backup_directory / f"temp_validation_{backup_id}.db"
            
            try:
                # Extract backup if compressed
                if metadata.backup_path.endswith('.gz'):
                    with gzip.open(metadata.backup_path, 'rb') as f_in:
                        with open(temp_db_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                else:
                    shutil.copy2(metadata.backup_path, temp_db_path)
                
                # Test database connection and basic queries
                conn = sqlite3.connect(str(temp_db_path))
                cursor = conn.cursor()
                
                # Count tables
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                validation_result['table_count'] = cursor.fetchone()[0]
                
                # Count total records (approximate)
                total_records = 0
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                for (table_name,) in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                        count = cursor.fetchone()[0]
                        total_records += count
                    except sqlite3.Error:
                        # Skip tables that can't be counted
                        pass
                
                validation_result['record_count'] = total_records
                validation_result['database_readable'] = True
                
                conn.close()
                
                # Clean up temporary file
                temp_db_path.unlink()
                
                # Update metadata
                metadata.status = BackupStatus.VALIDATED
                metadata.validation_result = validation_result
                self.save_metadata()
                
                print(f"Backup validation successful: {backup_id}")
                return True
                
            except Exception as e:
                validation_result['error'] = f"Database validation failed: {str(e)}"
                metadata.status = BackupStatus.CORRUPTED
                metadata.validation_result = validation_result
                self.save_metadata()
                
                # Clean up temporary file if it exists
                if temp_db_path.exists():
                    temp_db_path.unlink()
                
                print(f"Backup validation failed: {backup_id}, Error: {e}")
                return False
                
        except Exception as e:
            print(f"Failed to validate backup {backup_id}: {e}")
            metadata.status = BackupStatus.FAILED
            metadata.error_message = f"Validation error: {str(e)}"
            self.save_metadata()
            return False
    
    def restore_from_backup(self, backup_id: str, target_path: Optional[str] = None) -> bool:
        """Restore database from backup"""
        if backup_id not in self.backup_metadata:
            print(f"Backup {backup_id} not found")
            return False
        
        metadata = self.backup_metadata[backup_id]
        
        if metadata.status not in [BackupStatus.COMPLETED, BackupStatus.VALIDATED]:
            print(f"Backup {backup_id} is not in a restorable state: {metadata.status}")
            return False
        
        target_path = target_path or self.database_path
        
        try:
            print(f"Restoring database from backup: {backup_id}")
            
            # Create backup of current database before restore
            current_backup_id = self.generate_backup_id()
            current_backup_path = self.backup_directory / f"{current_backup_id}_pre_restore.db"
            
            if Path(target_path).exists():
                shutil.copy2(target_path, current_backup_path)
                print(f"Created pre-restore backup: {current_backup_path}")
            
            # Restore from backup
            if metadata.backup_path.endswith('.gz'):
                # Decompress and restore
                with gzip.open(metadata.backup_path, 'rb') as f_in:
                    with open(target_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                # Direct copy
                shutil.copy2(metadata.backup_path, target_path)
            
            print(f"Database restored successfully from backup: {backup_id}")
            return True
            
        except Exception as e:
            print(f"Failed to restore from backup {backup_id}: {e}")
            return False
    
    def point_in_time_recovery(self, target_timestamp: datetime) -> Optional[str]:
        """Perform point-in-time recovery to the closest backup before target timestamp"""
        # Find the most recent backup before target timestamp
        suitable_backups = []
        
        for backup_id, metadata in self.backup_metadata.items():
            if (metadata.timestamp <= target_timestamp and 
                metadata.status in [BackupStatus.COMPLETED, BackupStatus.VALIDATED]):
                suitable_backups.append((backup_id, metadata))
        
        if not suitable_backups:
            print(f"No suitable backup found for point-in-time recovery to {target_timestamp}")
            return None
        
        # Sort by timestamp (most recent first)
        suitable_backups.sort(key=lambda x: x[1].timestamp, reverse=True)
        backup_id, metadata = suitable_backups[0]
        
        print(f"Performing point-in-time recovery using backup: {backup_id} from {metadata.timestamp}")
        
        if self.restore_from_backup(backup_id):
            return backup_id
        else:
            return None
    
    def get_backup_status(self) -> Dict[str, Any]:
        """Get comprehensive backup system status"""
        total_backups = len(self.backup_metadata)
        valid_backups = sum(1 for m in self.backup_metadata.values() 
                           if m.status in [BackupStatus.COMPLETED, BackupStatus.VALIDATED])
        failed_backups = sum(1 for m in self.backup_metadata.values() 
                            if m.status == BackupStatus.FAILED)
        
        total_size = sum(m.size_bytes for m in self.backup_metadata.values())
        
        latest_backup = None
        if self.backup_metadata:
            latest_backup = max(self.backup_metadata.values(), key=lambda x: x.timestamp)
        
        return {
            'total_backups': total_backups,
            'valid_backups': valid_backups,
            'failed_backups': failed_backups,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'latest_backup': {
                'backup_id': latest_backup.backup_id,
                'timestamp': latest_backup.timestamp.isoformat(),
                'status': latest_backup.status.value,
                'size_mb': round(latest_backup.size_bytes / (1024 * 1024), 2)
            } if latest_backup else None,
            'backup_directory': str(self.backup_directory)
        }
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List all backups with their metadata"""
        backups = []
        for backup_id, metadata in sorted(
            self.backup_metadata.items(),
            key=lambda x: x[1].timestamp,
            reverse=True
        ):
            backup_info = {
                'backup_id': backup_id,
                'backup_type': metadata.backup_type.value,
                'timestamp': metadata.timestamp.isoformat(),
                'status': metadata.status.value,
                'size_bytes': metadata.size_bytes,
                'size_mb': round(metadata.size_bytes / (1024 * 1024), 2),
                'checksum': metadata.checksum[:16] + '...' if metadata.checksum else '',
                'validation_result': metadata.validation_result
            }
            
            if metadata.error_message:
                backup_info['error_message'] = metadata.error_message
            
            backups.append(backup_info)
        
        return backups

class DisasterRecoveryManager:
    """Manages disaster recovery procedures with automated failover"""
    
    def __init__(self, backup_system: BackupRecoverySystem):
        self.backup_system = backup_system
        
    def assess_database_health(self) -> Dict[str, Any]:
        """Assess current database health"""
        health_status = {
            'database_accessible': False,
            'corruption_detected': False,
            'performance_degraded': False,
            'recovery_needed': False,
            'assessment_timestamp': datetime.now().isoformat()
        }
        
        try:
            # Test database connection
            conn = sqlite3.connect(self.backup_system.database_path)
            cursor = conn.cursor()
            
            # Basic connectivity test
            cursor.execute("SELECT 1")
            health_status['database_accessible'] = True
            
            # Integrity check
            cursor.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()[0]
            
            if integrity_result != "ok":
                health_status['corruption_detected'] = True
                health_status['recovery_needed'] = True
                health_status['integrity_check_result'] = integrity_result
            
            conn.close()
            
        except Exception as e:
            health_status['database_accessible'] = False
            health_status['recovery_needed'] = True
            health_status['error'] = str(e)
            print(f"Database health assessment failed: {e}")
        
        return health_status
    
    def initiate_disaster_recovery(self) -> bool:
        """Initiate automated disaster recovery procedure"""
        print("Initiating disaster recovery procedure")
        
        # Assess current situation
        health_status = self.assess_database_health()
        
        if not health_status['recovery_needed']:
            print("Database appears healthy, recovery not needed")
            return True
        
        # Find the most recent valid backup
        valid_backups = [
            (backup_id, metadata) for backup_id, metadata in self.backup_system.backup_metadata.items()
            if metadata.status in [BackupStatus.COMPLETED, BackupStatus.VALIDATED]
        ]
        
        if not valid_backups:
            print("No valid backups available for disaster recovery")
            return False
        
        # Sort by timestamp (most recent first)
        valid_backups.sort(key=lambda x: x[1].timestamp, reverse=True)
        
        # Attempt recovery with the most recent backup
        backup_id, metadata = valid_backups[0]
        
        print(f"Disaster recovery attempt: using backup {backup_id}")
        
        try:
            # Perform recovery
            if self.backup_system.restore_from_backup(backup_id):
                # Verify recovery success
                recovery_health = self.assess_database_health()
                
                if recovery_health['database_accessible'] and not recovery_health['corruption_detected']:
                    print(f"Disaster recovery successful using backup: {backup_id}")
                    return True
                else:
                    print("Recovery failed health check")
            else:
                print("Recovery failed to restore backup")
                
        except Exception as e:
            print(f"Recovery failed with exception: {e}")
        
        print("Disaster recovery failed")
        return False

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
        print(f"    Total backups: {status['total_backups']}")
        assert status['total_backups'] >= 1, "No backups found"
        assert status['valid_backups'] >= 1, "No valid backups"
        
        backups = backup_system.list_backups()
        print(f"    Listed backups: {len(backups)}")
        assert len(backups) >= 1, "No backups in list"
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