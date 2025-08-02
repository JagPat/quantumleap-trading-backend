#!/usr/bin/env python3
"""
Data Lifecycle Manager
Automated data archival, compression, and lifecycle management system
"""
import os
import sqlite3
import threading
import time
import logging
import json
import gzip
import shutil
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
import schedule
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ArchivalStatus(Enum):
    """Data archival status"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    COMPRESSED = "compressed"
    DELETED = "deleted"

class RetentionPolicy(Enum):
    """Data retention policies"""
    KEEP_FOREVER = "keep_forever"
    ARCHIVE_AFTER_DAYS = "archive_after_days"
    DELETE_AFTER_DAYS = "delete_after_days"
    COMPRESS_AFTER_DAYS = "compress_after_days"

@dataclass
class ArchivalRule:
    """Data archival rule configuration"""
    rule_id: str
    name: str
    description: str
    table_name: str
    date_column: str
    retention_policy: RetentionPolicy
    retention_days: int
    archive_location: str
    compression_enabled: bool = True
    enabled: bool = True
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class ArchivalJob:
    """Individual archival job"""
    job_id: str
    rule_id: str
    table_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "running"
    records_processed: int = 0
    records_archived: int = 0
    archive_file_path: Optional[str] = None
    compression_ratio: Optional[float] = None
    error_message: Optional[str] = None

@dataclass
class ArchivalStats:
    """Archival statistics"""
    total_rules: int
    active_rules: int
    total_jobs: int
    successful_jobs: int
    failed_jobs: int
    total_records_archived: int
    total_space_saved: int
    average_compression_ratio: float

class DataLifecycleManager:
    """Automated data lifecycle management system"""
    
    def __init__(self, database_path: str = None, archive_base_path: str = None):
        self.database_path = database_path or os.getenv("DATABASE_PATH", "trading_lifecycle.db")
        self.archive_base_path = archive_base_path or os.path.join(os.path.dirname(self.database_path), "archives")
        
        # Lifecycle management
        self.archival_rules: Dict[str, ArchivalRule] = {}
        self.active_jobs: Dict[str, ArchivalJob] = {}
        self.lifecycle_lock = threading.RLock()
        
        # Scheduling
        self.scheduler_thread = None
        self.is_running = False
        
        # Statistics
        self.stats = ArchivalStats(0, 0, 0, 0, 0, 0, 0, 0.0)
        
        # Initialize system
        self._initialize_lifecycle_db()
        self._create_archive_directories()
        self._load_existing_rules()
        self._setup_default_rules()
    
    def _initialize_lifecycle_db(self):
        """Initialize lifecycle management database tables"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Create archival rules table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS archival_rules (
                        rule_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        table_name TEXT NOT NULL,
                        date_column TEXT NOT NULL,
                        retention_policy TEXT NOT NULL,
                        retention_days INTEGER NOT NULL,
                        archive_location TEXT NOT NULL,
                        compression_enabled BOOLEAN DEFAULT TRUE,
                        enabled BOOLEAN DEFAULT TRUE,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                
                # Create archival jobs table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS archival_jobs (
                        job_id TEXT PRIMARY KEY,
                        rule_id TEXT NOT NULL,
                        table_name TEXT NOT NULL,
                        start_time TEXT NOT NULL,
                        end_time TEXT,
                        status TEXT NOT NULL,
                        records_processed INTEGER DEFAULT 0,
                        records_archived INTEGER DEFAULT 0,
                        archive_file_path TEXT,
                        compression_ratio REAL,
                        error_message TEXT,
                        FOREIGN KEY (rule_id) REFERENCES archival_rules(rule_id)
                    )
                """)
                
                # Create archived data metadata table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS archived_data_metadata (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        table_name TEXT NOT NULL,
                        archive_file_path TEXT NOT NULL,
                        original_size INTEGER NOT NULL,
                        compressed_size INTEGER NOT NULL,
                        record_count INTEGER NOT NULL,
                        date_range_start TEXT NOT NULL,
                        date_range_end TEXT NOT NULL,
                        checksum TEXT NOT NULL,
                        archived_at TEXT NOT NULL,
                        accessible BOOLEAN DEFAULT TRUE
                    )
                """)
                
                # Create data access log table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS data_access_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        table_name TEXT NOT NULL,
                        access_type TEXT NOT NULL,
                        date_range_start TEXT,
                        date_range_end TEXT,
                        records_accessed INTEGER DEFAULT 0,
                        access_time TEXT NOT NULL,
                        user_id TEXT,
                        query_hash TEXT
                    )
                """)
                
                # Create indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_archival_jobs_rule_id ON archival_jobs(rule_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_archival_jobs_status ON archival_jobs(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_archived_metadata_table ON archived_data_metadata(table_name)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_data_access_log_table ON data_access_log(table_name)")
                
                conn.commit()
                logger.info("✅ Data lifecycle database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize lifecycle database: {e}")
            raise
    
    def _create_archive_directories(self):
        """Create archive directory structure"""
        try:
            os.makedirs(self.archive_base_path, exist_ok=True)
            
            # Create subdirectories for different types of archives
            subdirs = ['daily', 'monthly', 'yearly', 'compressed', 'temp']
            for subdir in subdirs:
                os.makedirs(os.path.join(self.archive_base_path, subdir), exist_ok=True)
            
            logger.info(f"✅ Archive directories created at: {self.archive_base_path}")
            
        except Exception as e:
            logger.error(f"Failed to create archive directories: {e}")
            raise
    
    def _load_existing_rules(self):
        """Load existing archival rules from database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM archival_rules")
                
                for row in cursor.fetchall():
                    rule = ArchivalRule(
                        rule_id=row[0],
                        name=row[1],
                        description=row[2],
                        table_name=row[3],
                        date_column=row[4],
                        retention_policy=RetentionPolicy(row[5]),
                        retention_days=row[6],
                        archive_location=row[7],
                        compression_enabled=bool(row[8]),
                        enabled=bool(row[9]),
                        created_at=datetime.fromisoformat(row[10])
                    )
                    self.archival_rules[rule.rule_id] = rule
                
                logger.info(f"✅ Loaded {len(self.archival_rules)} archival rules")
                
        except Exception as e:
            logger.error(f"Failed to load existing rules: {e}")
    
    def _setup_default_rules(self):
        """Setup default archival rules for common tables"""
        default_rules = [
            {
                "rule_id": "trades_archive",
                "name": "Trades Archive",
                "description": "Archive old trade records after 90 days",
                "table_name": "trades",
                "date_column": "created_at",
                "retention_policy": RetentionPolicy.ARCHIVE_AFTER_DAYS,
                "retention_days": 90,
                "archive_location": "daily"
            },
            {
                "rule_id": "orders_archive",
                "name": "Orders Archive", 
                "description": "Archive old order records after 60 days",
                "table_name": "orders",
                "date_column": "created_at",
                "retention_policy": RetentionPolicy.ARCHIVE_AFTER_DAYS,
                "retention_days": 60,
                "archive_location": "daily"
            },
            {
                "rule_id": "logs_cleanup",
                "name": "Logs Cleanup",
                "description": "Delete old log entries after 30 days",
                "table_name": "system_logs",
                "date_column": "timestamp",
                "retention_policy": RetentionPolicy.DELETE_AFTER_DAYS,
                "retention_days": 30,
                "archive_location": "temp"
            }
        ]
        
        for rule_config in default_rules:
            if rule_config["rule_id"] not in self.archival_rules:
                rule = ArchivalRule(**rule_config)
                self.create_archival_rule(rule)
    
    def create_archival_rule(self, rule: ArchivalRule) -> bool:
        """Create a new archival rule"""
        try:
            with self.lifecycle_lock:
                if rule.rule_id in self.archival_rules:
                    raise ValueError(f"Archival rule {rule.rule_id} already exists")
                
                # Store in database
                with sqlite3.connect(self.database_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO archival_rules 
                        (rule_id, name, description, table_name, date_column, 
                         retention_policy, retention_days, archive_location, 
                         compression_enabled, enabled, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        rule.rule_id,
                        rule.name,
                        rule.description,
                        rule.table_name,
                        rule.date_column,
                        rule.retention_policy.value,
                        rule.retention_days,
                        rule.archive_location,
                        rule.compression_enabled,
                        rule.enabled,
                        rule.created_at.isoformat(),
                        datetime.now().isoformat()
                    ))
                    conn.commit()
                
                # Store in memory
                self.archival_rules[rule.rule_id] = rule
                
                logger.info(f"✅ Created archival rule: {rule.rule_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create archival rule: {e}")
            return False
    
    def update_archival_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing archival rule"""
        try:
            with self.lifecycle_lock:
                if rule_id not in self.archival_rules:
                    raise ValueError(f"Archival rule {rule_id} not found")
                
                rule = self.archival_rules[rule_id]
                
                # Apply updates
                for key, value in updates.items():
                    if hasattr(rule, key):
                        setattr(rule, key, value)
                
                # Update in database
                with sqlite3.connect(self.database_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE archival_rules SET 
                        name=?, description=?, table_name=?, date_column=?, 
                        retention_policy=?, retention_days=?, archive_location=?, 
                        compression_enabled=?, enabled=?, updated_at=?
                        WHERE rule_id=?
                    """, (
                        rule.name,
                        rule.description,
                        rule.table_name,
                        rule.date_column,
                        rule.retention_policy.value,
                        rule.retention_days,
                        rule.archive_location,
                        rule.compression_enabled,
                        rule.enabled,
                        datetime.now().isoformat(),
                        rule_id
                    ))
                    conn.commit()
                
                logger.info(f"✅ Updated archival rule: {rule_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update archival rule: {e}")
            return False
    
    def delete_archival_rule(self, rule_id: str) -> bool:
        """Delete an archival rule"""
        try:
            with self.lifecycle_lock:
                if rule_id not in self.archival_rules:
                    raise ValueError(f"Archival rule {rule_id} not found")
                
                # Delete from database
                with sqlite3.connect(self.database_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM archival_rules WHERE rule_id=?", (rule_id,))
                    conn.commit()
                
                # Remove from memory
                del self.archival_rules[rule_id]
                
                logger.info(f"✅ Deleted archival rule: {rule_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete archival rule: {e}")
            return False
    
    def start_lifecycle_management(self):
        """Start automated lifecycle management"""
        try:
            if self.is_running:
                logger.warning("Lifecycle management is already running")
                return
            
            self.is_running = True
            
            # Schedule daily archival jobs
            schedule.every().day.at("02:00").do(self._run_daily_archival)
            schedule.every().week.at("03:00").do(self._run_weekly_maintenance)
            schedule.every().month.at("04:00").do(self._run_monthly_cleanup)
            
            # Start scheduler thread
            self.scheduler_thread = threading.Thread(
                target=self._scheduler_loop,
                daemon=True,
                name="DataLifecycleScheduler"
            )
            self.scheduler_thread.start()
            
            logger.info("✅ Data lifecycle management started")
            
        except Exception as e:
            logger.error(f"Failed to start lifecycle management: {e}")
            self.is_running = False
            raise
    
    def stop_lifecycle_management(self):
        """Stop lifecycle management"""
        try:
            if not self.is_running:
                logger.warning("Lifecycle management is not running")
                return
            
            self.is_running = False
            
            # Clear scheduled jobs
            schedule.clear()
            
            # Wait for scheduler thread to stop
            if self.scheduler_thread and self.scheduler_thread.is_alive():
                self.scheduler_thread.join(timeout=10)
            
            logger.info("✅ Data lifecycle management stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop lifecycle management: {e}")
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)
    
    def _run_daily_archival(self):
        """Run daily archival jobs"""
        logger.info("🔄 Running daily archival jobs...")
        
        for rule_id, rule in self.archival_rules.items():
            if rule.enabled and rule.retention_policy in [RetentionPolicy.ARCHIVE_AFTER_DAYS, RetentionPolicy.DELETE_AFTER_DAYS]:
                try:
                    self.execute_archival_rule(rule_id)
                except Exception as e:
                    logger.error(f"Failed to execute archival rule {rule_id}: {e}")
    
    def _run_weekly_maintenance(self):
        """Run weekly maintenance tasks"""
        logger.info("🔄 Running weekly maintenance...")
        
        try:
            # Compress old archives
            self._compress_old_archives()
            
            # Validate archive integrity
            self._validate_archive_integrity()
            
            # Update statistics
            self._update_statistics()
            
        except Exception as e:
            logger.error(f"Failed to run weekly maintenance: {e}")
    
    def _run_monthly_cleanup(self):
        """Run monthly cleanup tasks"""
        logger.info("🔄 Running monthly cleanup...")
        
        try:
            # Clean up old job records
            self._cleanup_old_jobs()
            
            # Clean up temporary files
            self._cleanup_temp_files()
            
            # Generate monthly report
            self._generate_monthly_report()
            
        except Exception as e:
            logger.error(f"Failed to run monthly cleanup: {e}")
    
    def execute_archival_rule(self, rule_id: str) -> Optional[ArchivalJob]:
        """Execute a specific archival rule"""
        try:
            if rule_id not in self.archival_rules:
                raise ValueError(f"Archival rule {rule_id} not found")
            
            rule = self.archival_rules[rule_id]
            
            if not rule.enabled:
                logger.info(f"Archival rule {rule_id} is disabled, skipping")
                return None
            
            # Create archival job
            job = ArchivalJob(
                job_id=self._generate_job_id(rule_id),
                rule_id=rule_id,
                table_name=rule.table_name,
                start_time=datetime.now()
            )
            
            # Store job
            self.active_jobs[job.job_id] = job
            self._store_archival_job(job)
            
            logger.info(f"🔄 Starting archival job: {job.job_id} for rule: {rule_id}")
            
            # Execute archival based on policy
            if rule.retention_policy == RetentionPolicy.ARCHIVE_AFTER_DAYS:
                success = self._archive_old_data(job, rule)
            elif rule.retention_policy == RetentionPolicy.DELETE_AFTER_DAYS:
                success = self._delete_old_data(job, rule)
            elif rule.retention_policy == RetentionPolicy.COMPRESS_AFTER_DAYS:
                success = self._compress_old_data(job, rule)
            else:
                logger.warning(f"Unsupported retention policy: {rule.retention_policy}")
                success = False
            
            # Update job status
            job.end_time = datetime.now()
            job.status = "completed" if success else "failed"
            
            # Update in database
            self._update_archival_job(job)
            
            # Remove from active jobs
            if job.job_id in self.active_jobs:
                del self.active_jobs[job.job_id]
            
            logger.info(f"✅ Archival job completed: {job.job_id} - Status: {job.status}")
            return job
            
        except Exception as e:
            logger.error(f"Failed to execute archival rule {rule_id}: {e}")
            if 'job' in locals():
                job.status = "failed"
                job.error_message = str(e)
                job.end_time = datetime.now()
                self._update_archival_job(job)
            return None
    
    def _generate_job_id(self, rule_id: str) -> str:
        """Generate unique job ID"""
        timestamp = datetime.now().isoformat()
        content = f"{rule_id}_{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _store_archival_job(self, job: ArchivalJob):
        """Store archival job in database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO archival_jobs 
                    (job_id, rule_id, table_name, start_time, status)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    job.job_id,
                    job.rule_id,
                    job.table_name,
                    job.start_time.isoformat(),
                    job.status
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to store archival job: {e}")
    
    def _update_archival_job(self, job: ArchivalJob):
        """Update archival job in database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE archival_jobs SET 
                    end_time=?, status=?, records_processed=?, records_archived=?, 
                    archive_file_path=?, compression_ratio=?, error_message=?
                    WHERE job_id=?
                """, (
                    job.end_time.isoformat() if job.end_time else None,
                    job.status,
                    job.records_processed,
                    job.records_archived,
                    job.archive_file_path,
                    job.compression_ratio,
                    job.error_message,
                    job.job_id
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update archival job: {e}")
    
    def _archive_old_data(self, job: ArchivalJob, rule: ArchivalRule) -> bool:
        """Archive old data based on retention policy"""
        try:
            cutoff_date = datetime.now() - timedelta(days=rule.retention_days)
            
            # Check if table exists
            if not self._table_exists(rule.table_name):
                logger.warning(f"Table {rule.table_name} does not exist, skipping archival")
                return True
            
            # Get data to archive
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Count records to archive
                cursor.execute(f"""
                    SELECT COUNT(*) FROM {rule.table_name} 
                    WHERE {rule.date_column} < ?
                """, (cutoff_date.isoformat(),))
                
                record_count = cursor.fetchone()[0]
                job.records_processed = record_count
                
                if record_count == 0:
                    logger.info(f"No records to archive for table {rule.table_name}")
                    return True
                
                # Export data to archive file
                archive_filename = f"{rule.table_name}_{cutoff_date.strftime('%Y%m%d')}.sql"
                archive_path = os.path.join(self.archive_base_path, rule.archive_location, archive_filename)
                
                # Create archive directory if it doesn't exist
                os.makedirs(os.path.dirname(archive_path), exist_ok=True)
                
                # Get column names first
                cursor.execute(f"PRAGMA table_info({rule.table_name})")
                columns = [col[1] for col in cursor.fetchall()]
                
                # Export data
                with open(archive_path, 'w') as archive_file:
                    # Write table schema
                    cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{rule.table_name}'")
                    schema = cursor.fetchone()
                    if schema:
                        archive_file.write(f"{schema[0]};\n\n")
                    
                    # Write data
                    cursor.execute(f"""
                        SELECT * FROM {rule.table_name} 
                        WHERE {rule.date_column} < ?
                        ORDER BY {rule.date_column}
                    """, (cutoff_date.isoformat(),))
                    
                    rows = cursor.fetchall()
                    archived_count = 0
                    
                    for row in rows:
                        # Create INSERT statement
                        values = []
                        for value in row:
                            if value is None:
                                values.append("NULL")
                            elif isinstance(value, str):
                                escaped_value = value.replace("'", "''")
                                values.append(f"'{escaped_value}'")
                            else:
                                values.append(str(value))
                        
                        insert_sql = f"INSERT INTO {rule.table_name} ({', '.join(columns)}) VALUES ({', '.join(values)});\n"
                        archive_file.write(insert_sql)
                        archived_count += 1
                
                job.records_archived = archived_count
                job.archive_file_path = archive_path
                
                # Compress archive if enabled
                if rule.compression_enabled:
                    compressed_path = f"{archive_path}.gz"
                    original_size = os.path.getsize(archive_path)
                    
                    with open(archive_path, 'rb') as f_in:
                        with gzip.open(compressed_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    
                    compressed_size = os.path.getsize(compressed_path)
                    job.compression_ratio = compressed_size / original_size if original_size > 0 else 0
                    
                    # Remove uncompressed file
                    os.remove(archive_path)
                    job.archive_file_path = compressed_path
                
                # Store archive metadata
                self._store_archive_metadata(rule.table_name, job.archive_file_path, 
                                           original_size if rule.compression_enabled else os.path.getsize(archive_path),
                                           compressed_size if rule.compression_enabled else 0,
                                           archived_count, cutoff_date)
                
                # Delete archived data from main table
                cursor.execute(f"""
                    DELETE FROM {rule.table_name} 
                    WHERE {rule.date_column} < ?
                """, (cutoff_date.isoformat(),))
                
                conn.commit()
                
                logger.info(f"✅ Archived {archived_count} records from {rule.table_name} to {job.archive_file_path}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to archive data: {e}")
            job.error_message = str(e)
            return False
    
    def _delete_old_data(self, job: ArchivalJob, rule: ArchivalRule) -> bool:
        """Delete old data based on retention policy"""
        try:
            cutoff_date = datetime.now() - timedelta(days=rule.retention_days)
            
            # Check if table exists
            if not self._table_exists(rule.table_name):
                logger.warning(f"Table {rule.table_name} does not exist, skipping deletion")
                return True
            
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Count records to delete
                cursor.execute(f"""
                    SELECT COUNT(*) FROM {rule.table_name} 
                    WHERE {rule.date_column} < ?
                """, (cutoff_date.isoformat(),))
                
                record_count = cursor.fetchone()[0]
                job.records_processed = record_count
                
                if record_count == 0:
                    logger.info(f"No records to delete for table {rule.table_name}")
                    return True
                
                # Delete old records
                cursor.execute(f"""
                    DELETE FROM {rule.table_name} 
                    WHERE {rule.date_column} < ?
                """, (cutoff_date.isoformat(),))
                
                deleted_count = cursor.rowcount
                job.records_archived = deleted_count  # Using archived field for deleted count
                
                conn.commit()
                
                logger.info(f"✅ Deleted {deleted_count} old records from {rule.table_name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete old data: {e}")
            job.error_message = str(e)
            return False
    
    def _compress_old_data(self, job: ArchivalJob, rule: ArchivalRule) -> bool:
        """Compress old data in place"""
        try:
            # This is a placeholder for in-place compression
            # In a real implementation, this might involve moving data to compressed storage
            logger.info(f"Compression policy not yet implemented for {rule.table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to compress old data: {e}")
            job.error_message = str(e)
            return False
    
    def _table_exists(self, table_name: str) -> bool:
        """Check if table exists in database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name=?
                """, (table_name,))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Failed to check table existence: {e}")
            return False
    
    def _store_archive_metadata(self, table_name: str, archive_path: str, 
                               original_size: int, compressed_size: int, 
                               record_count: int, cutoff_date: datetime):
        """Store archive metadata"""
        try:
            # Calculate checksum
            checksum = self._calculate_file_checksum(archive_path)
            
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO archived_data_metadata 
                    (table_name, archive_file_path, original_size, compressed_size, 
                     record_count, date_range_start, date_range_end, checksum, archived_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    table_name,
                    archive_path,
                    original_size,
                    compressed_size,
                    record_count,
                    "1900-01-01",  # Placeholder for start date
                    cutoff_date.isoformat(),
                    checksum,
                    datetime.now().isoformat()
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to store archive metadata: {e}")
    
    def _calculate_file_checksum(self, file_path: str) -> str:
        """Calculate MD5 checksum of file"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate checksum: {e}")
            return ""
    
    def retrieve_archived_data(self, table_name: str, date_range_start: datetime, 
                              date_range_end: datetime) -> Optional[str]:
        """Retrieve archived data for specified date range"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT archive_file_path, compressed_size FROM archived_data_metadata 
                    WHERE table_name = ? AND date_range_start <= ? AND date_range_end >= ?
                    ORDER BY archived_at
                """, (table_name, date_range_end.isoformat(), date_range_start.isoformat()))
                
                archives = cursor.fetchall()
                
                if not archives:
                    logger.info(f"No archived data found for {table_name} in specified date range")
                    return None
                
                # Create temporary file to combine archives
                temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False)
                
                for archive_path, compressed_size in archives:
                    if archive_path.endswith('.gz'):
                        # Decompress and read
                        with gzip.open(archive_path, 'rt') as f:
                            temp_file.write(f.read())
                    else:
                        # Read directly
                        with open(archive_path, 'r') as f:
                            temp_file.write(f.read())
                    
                    temp_file.write('\n')
                
                temp_file.close()
                
                # Log access
                self._log_data_access(table_name, "retrieve", date_range_start, date_range_end, len(archives))
                
                logger.info(f"✅ Retrieved archived data for {table_name}: {temp_file.name}")
                return temp_file.name
                
        except Exception as e:
            logger.error(f"Failed to retrieve archived data: {e}")
            return None
    
    def _log_data_access(self, table_name: str, access_type: str, 
                        date_range_start: datetime, date_range_end: datetime, 
                        records_accessed: int, user_id: str = None):
        """Log data access for audit purposes"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO data_access_log 
                    (table_name, access_type, date_range_start, date_range_end, 
                     records_accessed, access_time, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    table_name,
                    access_type,
                    date_range_start.isoformat(),
                    date_range_end.isoformat(),
                    records_accessed,
                    datetime.now().isoformat(),
                    user_id
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to log data access: {e}")
    
    def _compress_old_archives(self):
        """Compress old uncompressed archives"""
        try:
            # Find uncompressed archives older than 7 days
            cutoff_date = datetime.now() - timedelta(days=7)
            
            for root, dirs, files in os.walk(self.archive_base_path):
                for file in files:
                    if file.endswith('.sql'):
                        file_path = os.path.join(root, file)
                        file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                        
                        if file_time < cutoff_date:
                            # Compress the file
                            compressed_path = f"{file_path}.gz"
                            
                            with open(file_path, 'rb') as f_in:
                                with gzip.open(compressed_path, 'wb') as f_out:
                                    shutil.copyfileobj(f_in, f_out)
                            
                            # Remove original file
                            os.remove(file_path)
                            
                            # Update metadata
                            with sqlite3.connect(self.database_path) as conn:
                                cursor = conn.cursor()
                                cursor.execute("""
                                    UPDATE archived_data_metadata 
                                    SET archive_file_path = ?, compressed_size = ?
                                    WHERE archive_file_path = ?
                                """, (compressed_path, os.path.getsize(compressed_path), file_path))
                                conn.commit()
                            
                            logger.info(f"✅ Compressed archive: {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to compress old archives: {e}")
    
    def _validate_archive_integrity(self):
        """Validate integrity of archived files"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT archive_file_path, checksum FROM archived_data_metadata WHERE accessible = 1")
                
                for archive_path, stored_checksum in cursor.fetchall():
                    if os.path.exists(archive_path):
                        current_checksum = self._calculate_file_checksum(archive_path)
                        
                        if current_checksum != stored_checksum:
                            logger.error(f"❌ Archive integrity check failed: {archive_path}")
                            # Mark as inaccessible
                            cursor.execute("""
                                UPDATE archived_data_metadata 
                                SET accessible = 0 
                                WHERE archive_file_path = ?
                            """, (archive_path,))
                        else:
                            logger.debug(f"✅ Archive integrity verified: {archive_path}")
                    else:
                        logger.error(f"❌ Archive file missing: {archive_path}")
                        # Mark as inaccessible
                        cursor.execute("""
                            UPDATE archived_data_metadata 
                            SET accessible = 0 
                            WHERE archive_file_path = ?
                        """, (archive_path,))
                
                conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to validate archive integrity: {e}")
    
    def _update_statistics(self):
        """Update archival statistics"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Count rules
                cursor.execute("SELECT COUNT(*) FROM archival_rules")
                total_rules = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM archival_rules WHERE enabled = 1")
                active_rules = cursor.fetchone()[0]
                
                # Count jobs
                cursor.execute("SELECT COUNT(*) FROM archival_jobs")
                total_jobs = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM archival_jobs WHERE status = 'completed'")
                successful_jobs = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM archival_jobs WHERE status = 'failed'")
                failed_jobs = cursor.fetchone()[0]
                
                # Sum archived records
                cursor.execute("SELECT SUM(records_archived) FROM archival_jobs WHERE status = 'completed'")
                total_records = cursor.fetchone()[0] or 0
                
                # Calculate space saved
                cursor.execute("SELECT SUM(original_size - compressed_size) FROM archived_data_metadata")
                space_saved = cursor.fetchone()[0] or 0
                
                # Calculate average compression ratio
                cursor.execute("SELECT AVG(compression_ratio) FROM archival_jobs WHERE compression_ratio IS NOT NULL")
                avg_compression = cursor.fetchone()[0] or 0.0
                
                self.stats = ArchivalStats(
                    total_rules=total_rules,
                    active_rules=active_rules,
                    total_jobs=total_jobs,
                    successful_jobs=successful_jobs,
                    failed_jobs=failed_jobs,
                    total_records_archived=total_records,
                    total_space_saved=space_saved,
                    average_compression_ratio=avg_compression
                )
                
        except Exception as e:
            logger.error(f"Failed to update statistics: {e}")
    
    def _cleanup_old_jobs(self):
        """Clean up old job records"""
        try:
            cutoff_date = datetime.now() - timedelta(days=90)
            
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM archival_jobs 
                    WHERE start_time < ? AND status IN ('completed', 'failed')
                """, (cutoff_date.isoformat(),))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"✅ Cleaned up {deleted_count} old job records")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old jobs: {e}")
    
    def _cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            temp_dir = os.path.join(self.archive_base_path, "temp")
            if os.path.exists(temp_dir):
                for file in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, file)
                    if os.path.isfile(file_path):
                        file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(file_path))
                        if file_age.days > 7:  # Remove files older than 7 days
                            os.remove(file_path)
                            logger.debug(f"Removed temp file: {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup temp files: {e}")
    
    def _generate_monthly_report(self):
        """Generate monthly archival report"""
        try:
            report_date = datetime.now()
            report_path = os.path.join(self.archive_base_path, f"monthly_report_{report_date.strftime('%Y%m')}.json")
            
            # Collect report data
            report_data = {
                "report_date": report_date.isoformat(),
                "statistics": asdict(self.stats),
                "active_rules": len([r for r in self.archival_rules.values() if r.enabled]),
                "total_archive_size": self._calculate_total_archive_size(),
                "recent_jobs": self._get_recent_jobs(30)
            }
            
            with open(report_path, 'w') as f:
                json.dump(report_data, f, indent=2)
            
            logger.info(f"✅ Generated monthly report: {report_path}")
            
        except Exception as e:
            logger.error(f"Failed to generate monthly report: {e}")
    
    def _calculate_total_archive_size(self) -> int:
        """Calculate total size of all archives"""
        total_size = 0
        try:
            for root, dirs, files in os.walk(self.archive_base_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.isfile(file_path):
                        total_size += os.path.getsize(file_path)
        except Exception as e:
            logger.error(f"Failed to calculate archive size: {e}")
        
        return total_size
    
    def _get_recent_jobs(self, days: int) -> List[Dict[str, Any]]:
        """Get recent archival jobs"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT job_id, rule_id, table_name, start_time, end_time, 
                           status, records_processed, records_archived
                    FROM archival_jobs 
                    WHERE start_time > ?
                    ORDER BY start_time DESC
                """, (cutoff_date.isoformat(),))
                
                jobs = []
                for row in cursor.fetchall():
                    jobs.append({
                        "job_id": row[0],
                        "rule_id": row[1],
                        "table_name": row[2],
                        "start_time": row[3],
                        "end_time": row[4],
                        "status": row[5],
                        "records_processed": row[6],
                        "records_archived": row[7]
                    })
                
                return jobs
                
        except Exception as e:
            logger.error(f"Failed to get recent jobs: {e}")
            return []
    
    def get_archival_statistics(self) -> ArchivalStats:
        """Get current archival statistics"""
        self._update_statistics()
        return self.stats
    
    def get_active_jobs(self) -> List[ArchivalJob]:
        """Get currently active archival jobs"""
        with self.lifecycle_lock:
            return list(self.active_jobs.values())
    
    def get_archival_rules(self) -> List[ArchivalRule]:
        """Get all archival rules"""
        with self.lifecycle_lock:
            return list(self.archival_rules.values())
    
    def __del__(self):
        """Cleanup on destruction"""
        try:
            self.stop_lifecycle_management()
        except:
            pass

# Example usage and testing
if __name__ == "__main__":
    # Initialize data lifecycle manager
    lifecycle_manager = DataLifecycleManager()
    
    try:
        # Create a test archival rule
        rule = ArchivalRule(
            rule_id="test_archive",
            name="Test Archive Rule",
            description="Test archival functionality",
            table_name="test_data",
            date_column="created_at",
            retention_policy=RetentionPolicy.ARCHIVE_AFTER_DAYS,
            retention_days=30,
            archive_location="daily"
        )
        
        lifecycle_manager.create_archival_rule(rule)
        print(f"✅ Created archival rule: {rule.rule_id}")
        
        # Get statistics
        stats = lifecycle_manager.get_archival_statistics()
        print(f"Statistics: {stats}")
        
        # Start lifecycle management
        lifecycle_manager.start_lifecycle_management()
        print("✅ Lifecycle management started")
        
        # Wait a bit
        time.sleep(5)
        
        # Stop lifecycle management
        lifecycle_manager.stop_lifecycle_management()
        print("✅ Lifecycle management stopped")
        
    except KeyboardInterrupt:
        print("\n⏹️ Stopping lifecycle manager...")
    finally:
        lifecycle_manager.stop_lifecycle_management()
        print("✅ Lifecycle manager stopped")