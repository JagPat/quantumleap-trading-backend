"""
Database Backup and Recovery System
Implements automated backup procedures with configurable schedules,
backup validation, point-in-time recovery, and disaster recovery procedures.
"""

import os
import json
import gzip
import shutil
import sqlite3
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import time
import schedule

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
        
        # Scheduler for automated backups
        self.scheduler_thread = None
        self.scheduler_running = False
        
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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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
        """
        Create a full database backup
        """
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
            
            self.logger.info(f"Starting full backup: {backup_id}")
            
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
                
                self.logger.info(f"Full backup completed: {backup_id}, Size: {metadata.size_bytes} bytes")
            else:
                metadata.status = BackupStatus.FAILED
                metadata.error_message = "Backup file not created"
                self.logger.error(f"Full backup failed: {backup_id}")
            
            self.save_metadata()
            
            # Validate backup if enabled
            if self.validation_enabled and metadata.status == BackupStatus.COMPLETED:
                self.validate_backup(backup_id)
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to create full backup {backup_id}: {e}")
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
        """
        Validate backup integrity and consistency
        """
        if backup_id not in self.backup_metadata:
            self.logger.error(f"Backup {backup_id} not found in metadata")
            return False
        
        metadata = self.backup_metadata[backup_id]
        
        try:
            self.logger.info(f"Validating backup: {backup_id}")
            
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
                validation_result['error'] = f"Checksum mismatch: expected {metadata.checksum}, got {current_checksum}"
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
                
                self.logger.info(f"Backup validation successful: {backup_id}")
                return True
                
            except Exception as e:
                validation_result['error'] = f"Database validation failed: {str(e)}"
                metadata.status = BackupStatus.CORRUPTED
                metadata.validation_result = validation_result
                self.save_metadata()
                
                # Clean up temporary file if it exists
                if temp_db_path.exists():
                    temp_db_path.unlink()
                
                self.logger.error(f"Backup validation failed: {backup_id}, Error: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to validate backup {backup_id}: {e}")
            metadata.status = BackupStatus.FAILED
            metadata.error_message = f"Validation error: {str(e)}"
            self.save_metadata()
            return False
    
    def restore_from_backup(self, backup_id: str, target_path: Optional[str] = None) -> bool:
        """
        Restore database from backup
        """
        if backup_id not in self.backup_metadata:
            self.logger.error(f"Backup {backup_id} not found")
            return False
        
        metadata = self.backup_metadata[backup_id]
        
        if metadata.status not in [BackupStatus.COMPLETED, BackupStatus.VALIDATED]:
            self.logger.error(f"Backup {backup_id} is not in a restorable state: {metadata.status}")
            return False
        
        target_path = target_path or self.database_path
        
        try:
            self.logger.info(f"Restoring database from backup: {backup_id}")
            
            # Create backup of current database before restore
            current_backup_id = self.generate_backup_id()
            current_backup_path = self.backup_directory / f"{current_backup_id}_pre_restore.db"
            
            if Path(target_path).exists():
                shutil.copy2(target_path, current_backup_path)
                self.logger.info(f"Created pre-restore backup: {current_backup_path}")
            
            # Restore from backup
            if metadata.backup_path.endswith('.gz'):
                # Decompress and restore
                with gzip.open(metadata.backup_path, 'rb') as f_in:
                    with open(target_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                # Direct copy
                shutil.copy2(metadata.backup_path, target_path)
            
            self.logger.info(f"Database restored successfully from backup: {backup_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore from backup {backup_id}: {e}")
            return False
    
    def point_in_time_recovery(self, target_timestamp: datetime) -> Optional[str]:
        """
        Perform point-in-time recovery to the closest backup before target timestamp
        """
        # Find the most recent backup before target timestamp
        suitable_backups = []
        
        for backup_id, metadata in self.backup_metadata.items():
            if (metadata.timestamp <= target_timestamp and 
                metadata.status in [BackupStatus.COMPLETED, BackupStatus.VALIDATED]):
                suitable_backups.append((backup_id, metadata))
        
        if not suitable_backups:
            self.logger.error(f"No suitable backup found for point-in-time recovery to {target_timestamp}")
            return None
        
        # Sort by timestamp (most recent first)
        suitable_backups.sort(key=lambda x: x[1].timestamp, reverse=True)
        backup_id, metadata = suitable_backups[0]
        
        self.logger.info(f"Performing point-in-time recovery using backup: {backup_id} from {metadata.timestamp}")
        
        if self.restore_from_backup(backup_id):
            return backup_id
        else:
            return None
    
    def cleanup_old_backups(self):
        """
        Clean up old backups based on retention policy
        """
        cutoff_date = datetime.now() - timedelta(days=self.max_backup_age_days)
        backups_to_remove = []
        
        # Find backups to remove based on age
        for backup_id, metadata in self.backup_metadata.items():
            if metadata.timestamp < cutoff_date:
                backups_to_remove.append(backup_id)
        
        # Also remove excess backups if we have too many
        if len(self.backup_metadata) > self.max_backup_count:
            sorted_backups = sorted(
                self.backup_metadata.items(),
                key=lambda x: x[1].timestamp
            )
            excess_count = len(self.backup_metadata) - self.max_backup_count
            for i in range(excess_count):
                backup_id = sorted_backups[i][0]
                if backup_id not in backups_to_remove:
                    backups_to_remove.append(backup_id)
        
        # Remove old backups
        for backup_id in backups_to_remove:
            self._remove_backup(backup_id)
        
        if backups_to_remove:
            self.logger.info(f"Cleaned up {len(backups_to_remove)} old backups")
    
    def _remove_backup(self, backup_id: str):
        """Remove a backup and its metadata"""
        if backup_id not in self.backup_metadata:
            return
        
        metadata = self.backup_metadata[backup_id]
        
        try:
            # Remove backup file
            backup_path = Path(metadata.backup_path)
            if backup_path.exists():
                backup_path.unlink()
            
            # Remove from metadata
            del self.backup_metadata[backup_id]
            self.save_metadata()
            
            self.logger.info(f"Removed backup: {backup_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to remove backup {backup_id}: {e}")
    
    def schedule_automated_backups(self, schedule_config: Dict[str, Any]):
        """
        Schedule automated backups
        
        schedule_config example:
        {
            'full_backup_time': '02:00',  # Daily at 2 AM
            'full_backup_days': ['sunday'],  # Weekly on Sunday
            'cleanup_time': '03:00'  # Daily cleanup at 3 AM
        }
        """
        if self.scheduler_running:
            self.stop_automated_backups()
        
        # Schedule full backups
        if 'full_backup_time' in schedule_config:
            if 'full_backup_days' in schedule_config:
                # Weekly backups
                for day in schedule_config['full_backup_days']:
                    getattr(schedule.every(), day.lower()).at(
                        schedule_config['full_backup_time']
                    ).do(self.create_full_backup)
            else:
                # Daily backups
                schedule.every().day.at(
                    schedule_config['full_backup_time']
                ).do(self.create_full_backup)
        
        # Schedule cleanup
        if 'cleanup_time' in schedule_config:
            schedule.every().day.at(
                schedule_config['cleanup_time']
            ).do(self.cleanup_old_backups)
        
        # Start scheduler thread
        self.scheduler_running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        self.logger.info("Automated backup scheduling started")
    
    def _run_scheduler(self):
        """Run the backup scheduler"""
        while self.scheduler_running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def stop_automated_backups(self):
        """Stop automated backup scheduling"""
        self.scheduler_running = False
        schedule.clear()
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        self.logger.info("Automated backup scheduling stopped")
    
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
            'scheduler_running': self.scheduler_running,
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

# Disaster Recovery Procedures
class DisasterRecoveryManager:
    """
    Manages disaster recovery procedures with automated failover
    """
    
    def __init__(self, backup_system: BackupRecoverySystem):
        self.backup_system = backup_system
        self.logger = logging.getLogger(__name__)
        
        # Recovery configuration
        self.recovery_timeout = 300  # 5 minutes
        self.max_recovery_attempts = 3
        
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
            self.logger.error(f"Database health assessment failed: {e}")
        
        return health_status
    
    def initiate_disaster_recovery(self) -> bool:
        """
        Initiate automated disaster recovery procedure
        """
        self.logger.critical("Initiating disaster recovery procedure")
        
        # Assess current situation
        health_status = self.assess_database_health()
        
        if not health_status['recovery_needed']:
            self.logger.info("Database appears healthy, recovery not needed")
            return True
        
        # Find the most recent valid backup
        valid_backups = [
            (backup_id, metadata) for backup_id, metadata in self.backup_system.backup_metadata.items()
            if metadata.status in [BackupStatus.COMPLETED, BackupStatus.VALIDATED]
        ]
        
        if not valid_backups:
            self.logger.critical("No valid backups available for disaster recovery")
            return False
        
        # Sort by timestamp (most recent first)
        valid_backups.sort(key=lambda x: x[1].timestamp, reverse=True)
        
        # Attempt recovery with each backup until successful
        for attempt in range(min(self.max_recovery_attempts, len(valid_backups))):
            backup_id, metadata = valid_backups[attempt]
            
            self.logger.info(f"Disaster recovery attempt {attempt + 1}: using backup {backup_id}")
            
            try:
                # Create emergency backup of current state if possible
                emergency_backup_path = self.backup_system.backup_directory / f"emergency_pre_recovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                
                if Path(self.backup_system.database_path).exists():
                    try:
                        shutil.copy2(self.backup_system.database_path, emergency_backup_path)
                        self.logger.info(f"Created emergency backup: {emergency_backup_path}")
                    except Exception as e:
                        self.logger.warning(f"Could not create emergency backup: {e}")
                
                # Perform recovery
                if self.backup_system.restore_from_backup(backup_id):
                    # Verify recovery success
                    recovery_health = self.assess_database_health()
                    
                    if recovery_health['database_accessible'] and not recovery_health['corruption_detected']:
                        self.logger.info(f"Disaster recovery successful using backup: {backup_id}")
                        return True
                    else:
                        self.logger.warning(f"Recovery attempt {attempt + 1} failed health check")
                else:
                    self.logger.warning(f"Recovery attempt {attempt + 1} failed to restore backup")
                    
            except Exception as e:
                self.logger.error(f"Recovery attempt {attempt + 1} failed with exception: {e}")
        
        self.logger.critical("All disaster recovery attempts failed")
        return False