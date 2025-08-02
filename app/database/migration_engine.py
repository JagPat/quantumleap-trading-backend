#!/usr/bin/env python3
"""
Database Migration Engine with Rollback Capabilities
Provides version-controlled database schema migrations with automatic backup and rollback support
"""

import os
import sqlite3
import logging
import json
import shutil
import hashlib
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import re
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MigrationStatus(Enum):
    """Migration execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

class MigrationType(Enum):
    """Migration operation types"""
    SCHEMA_CHANGE = "schema_change"
    DATA_MIGRATION = "data_migration"
    INDEX_CREATION = "index_creation"
    CONSTRAINT_ADDITION = "constraint_addition"
    TABLE_CREATION = "table_creation"
    TABLE_MODIFICATION = "table_modification"
    TABLE_DELETION = "table_deletion"

class BackupType(Enum):
    """Backup types for migration safety"""
    FULL_DATABASE = "full_database"
    SCHEMA_ONLY = "schema_only"
    DATA_ONLY = "data_only"
    INCREMENTAL = "incremental"

@dataclass
class Migration:
    """Database migration definition"""
    migration_id: str
    version: str
    name: str
    description: str
    migration_type: MigrationType
    up_sql: str
    down_sql: str
    dependencies: List[str] = None
    checksum: str = ""
    created_at: datetime = None
    author: str = ""
    is_reversible: bool = True
    backup_required: bool = True
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if not self.checksum:
            self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        """Calculate checksum for migration integrity"""
        content = f"{self.up_sql}{self.down_sql}{self.version}"
        return hashlib.sha256(content.encode()).hexdigest()

@dataclass
class MigrationExecution:
    """Migration execution record"""
    execution_id: str
    migration_id: str
    version: str
    status: MigrationStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    backup_path: Optional[str] = None
    rollback_available: bool = True
    execution_time: float = 0.0
    
    def __post_init__(self):
        if not self.execution_id:
            self.execution_id = str(uuid.uuid4())

@dataclass
class BackupInfo:
    """Database backup information"""
    backup_id: str
    backup_path: str
    backup_type: BackupType
    database_path: str
    created_at: datetime
    size_bytes: int
    checksum: str
    migration_id: Optional[str] = None
    is_valid: bool = True

class MigrationEngine:
    """Comprehensive database migration engine with rollback capabilities"""
    
    def __init__(self, database_path: str = None, migrations_dir: str = None, backups_dir: str = None):
        self.database_path = database_path or os.getenv("DATABASE_PATH", "trading_migrations.db")
        self.migrations_dir = Path(migrations_dir or "migrations")
        self.backups_dir = Path(backups_dir or "backups")
        self.connection = None
        self.migrations: Dict[str, Migration] = {}
        self.lock = threading.RLock()
        
        # Ensure directories exist
        self.migrations_dir.mkdir(exist_ok=True)
        self.backups_dir.mkdir(exist_ok=True)
        
        self._initialize_migration_system()
        self._load_migrations()
    
    def _initialize_migration_system(self):
        """Initialize migration system database tables"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Create migration metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS migration_metadata (
                    migration_id TEXT PRIMARY KEY,
                    version TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    migration_type TEXT NOT NULL,
                    up_sql TEXT NOT NULL,
                    down_sql TEXT NOT NULL,
                    dependencies TEXT, -- JSON array
                    checksum TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    author TEXT,
                    is_reversible BOOLEAN DEFAULT 1,
                    backup_required BOOLEAN DEFAULT 1,
                    
                    CHECK (migration_type IN ('schema_change', 'data_migration', 'index_creation', 'constraint_addition', 'table_creation', 'table_modification', 'table_deletion'))
                )
            """)
            
            # Create migration execution history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS migration_executions (
                    execution_id TEXT PRIMARY KEY,
                    migration_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    error_message TEXT,
                    backup_path TEXT,
                    rollback_available BOOLEAN DEFAULT 1,
                    execution_time REAL DEFAULT 0.0,
                    
                    FOREIGN KEY (migration_id) REFERENCES migration_metadata(migration_id),
                    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'rolled_back'))
                )
            """)
            
            # Create backup information table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS backup_info (
                    backup_id TEXT PRIMARY KEY,
                    backup_path TEXT NOT NULL,
                    backup_type TEXT NOT NULL,
                    database_path TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    checksum TEXT NOT NULL,
                    migration_id TEXT,
                    is_valid BOOLEAN DEFAULT 1,
                    
                    CHECK (backup_type IN ('full_database', 'schema_only', 'data_only', 'incremental'))
                )
            """)
            
            # Create schema version table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    current_version TEXT NOT NULL,
                    last_migration_id TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (last_migration_id) REFERENCES migration_metadata(migration_id)
                )
            """)
            
            # Initialize schema version if not exists
            cursor.execute("SELECT COUNT(*) FROM schema_version")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO schema_version (current_version, updated_at)
                    VALUES ('0.0.0', CURRENT_TIMESTAMP)
                """)
            
            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_migration_executions_migration_id ON migration_executions(migration_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_migration_executions_status ON migration_executions(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_migration_executions_started_at ON migration_executions(started_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_backup_info_migration_id ON backup_info(migration_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_backup_info_created_at ON backup_info(created_at)")
            
            conn.commit()
            logger.info("✅ Migration system initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize migration system: {e}")
            raise
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with optimal settings"""
        if self.connection is None:
            self.connection = sqlite3.connect(
                self.database_path,
                check_same_thread=False,
                isolation_level=None
            )
            
            # Configure for migration safety
            cursor = self.connection.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("PRAGMA journal_mode = WAL")
            cursor.execute("PRAGMA synchronous = FULL")  # Full synchronous for safety
            cursor.execute("PRAGMA cache_size = -16000")  # 16MB cache
            cursor.execute("PRAGMA temp_store = memory")
            cursor.execute("PRAGMA busy_timeout = 30000")  # 30 second timeout
            
        return self.connection
    
    def _load_migrations(self):
        """Load migration files from migrations directory"""
        try:
            migration_files = list(self.migrations_dir.glob("*.sql"))
            migration_files.sort()  # Sort by filename for version ordering
            
            for migration_file in migration_files:
                try:
                    migration = self._parse_migration_file(migration_file)
                    if migration:
                        self.migrations[migration.migration_id] = migration
                        self._store_migration_metadata(migration)
                except Exception as e:
                    logger.warning(f"Failed to load migration {migration_file}: {e}")
            
            logger.info(f"✅ Loaded {len(self.migrations)} migrations")
            
        except Exception as e:
            logger.error(f"Failed to load migrations: {e}")
    
    def _parse_migration_file(self, migration_file: Path) -> Optional[Migration]:
        """Parse migration file and extract metadata"""
        try:
            content = migration_file.read_text(encoding='utf-8')
            
            # Extract metadata from comments
            metadata = {}
            up_sql = ""
            down_sql = ""
            
            lines = content.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                
                # Parse metadata comments
                if line.startswith('-- @'):
                    key_value = line[4:].split(':', 1)
                    if len(key_value) == 2:
                        key, value = key_value
                        metadata[key.strip()] = value.strip()
                
                # Parse section markers
                elif line.startswith('-- UP'):
                    current_section = 'up'
                    continue
                elif line.startswith('-- DOWN'):
                    current_section = 'down'
                    continue
                
                # Add SQL to appropriate section
                elif current_section == 'up' and line and not line.startswith('--'):
                    up_sql += line + '\n'
                elif current_section == 'down' and line and not line.startswith('--'):
                    down_sql += line + '\n'
            
            # Extract version from filename (e.g., 001_create_users_table.sql)
            filename = migration_file.stem
            version_match = re.match(r'^(\d+)_(.+)$', filename)
            if not version_match:
                logger.warning(f"Invalid migration filename format: {filename}")
                return None
            
            version = version_match.group(1)
            name = version_match.group(2).replace('_', ' ').title()
            
            # Create migration object
            migration = Migration(
                migration_id=filename,
                version=version,
                name=metadata.get('name', name),
                description=metadata.get('description', ''),
                migration_type=MigrationType(metadata.get('type', 'schema_change')),
                up_sql=up_sql.strip(),
                down_sql=down_sql.strip(),
                dependencies=json.loads(metadata.get('dependencies', '[]')),
                author=metadata.get('author', ''),
                is_reversible=metadata.get('reversible', 'true').lower() == 'true',
                backup_required=metadata.get('backup_required', 'true').lower() == 'true'
            )
            
            return migration
            
        except Exception as e:
            logger.error(f"Failed to parse migration file {migration_file}: {e}")
            return None
    
    def _store_migration_metadata(self, migration: Migration):
        """Store migration metadata in database"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO migration_metadata 
                (migration_id, version, name, description, migration_type, up_sql, down_sql, 
                 dependencies, checksum, created_at, author, is_reversible, backup_required)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                migration.migration_id, migration.version, migration.name, migration.description,
                migration.migration_type.value, migration.up_sql, migration.down_sql,
                json.dumps(migration.dependencies), migration.checksum, migration.created_at,
                migration.author, migration.is_reversible, migration.backup_required
            ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to store migration metadata: {e}")
    
    def create_backup(self, backup_type: BackupType = BackupType.FULL_DATABASE, 
                     migration_id: str = None) -> BackupInfo:
        """Create database backup before migration"""
        try:
            backup_id = str(uuid.uuid4())
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{backup_id}_{timestamp}.db"
            backup_path = self.backups_dir / backup_filename
            
            if backup_type == BackupType.FULL_DATABASE:
                # Create full database backup
                shutil.copy2(self.database_path, backup_path)
            else:
                # For other backup types, we'll use SQLite's backup API
                source_conn = sqlite3.connect(self.database_path)
                backup_conn = sqlite3.connect(str(backup_path))
                
                if backup_type == BackupType.SCHEMA_ONLY:
                    # Backup schema only
                    for line in source_conn.iterdump():
                        if not line.startswith('INSERT'):
                            backup_conn.execute(line)
                elif backup_type == BackupType.DATA_ONLY:
                    # Backup data only (this is complex, simplified here)
                    source_conn.backup(backup_conn)
                else:
                    # Full backup using SQLite backup API
                    source_conn.backup(backup_conn)
                
                source_conn.close()
                backup_conn.close()
            
            # Calculate backup size and checksum
            backup_size = backup_path.stat().st_size
            backup_checksum = self._calculate_file_checksum(backup_path)
            
            # Create backup info
            backup_info = BackupInfo(
                backup_id=backup_id,
                backup_path=str(backup_path),
                backup_type=backup_type,
                database_path=self.database_path,
                created_at=datetime.now(),
                size_bytes=backup_size,
                checksum=backup_checksum,
                migration_id=migration_id
            )
            
            # Store backup info in database
            self._store_backup_info(backup_info)
            
            logger.info(f"✅ Created backup: {backup_path} ({backup_size} bytes)")
            return backup_info
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate file checksum for integrity verification"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _store_backup_info(self, backup_info: BackupInfo):
        """Store backup information in database"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO backup_info 
                (backup_id, backup_path, backup_type, database_path, created_at, 
                 size_bytes, checksum, migration_id, is_valid)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                backup_info.backup_id, backup_info.backup_path, backup_info.backup_type.value,
                backup_info.database_path, backup_info.created_at, backup_info.size_bytes,
                backup_info.checksum, backup_info.migration_id, backup_info.is_valid
            ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to store backup info: {e}")
    
    def get_current_version(self) -> str:
        """Get current database schema version"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT current_version FROM schema_version WHERE id = 1")
            result = cursor.fetchone()
            
            return result[0] if result else "0.0.0"
            
        except Exception as e:
            logger.error(f"Failed to get current version: {e}")
            return "0.0.0"
    
    def get_pending_migrations(self, target_version: str = None) -> List[Migration]:
        """Get list of pending migrations"""
        try:
            current_version = self.get_current_version()
            
            # Get executed migrations
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT migration_id FROM migration_executions 
                WHERE status = 'completed'
            """)
            executed_migrations = {row[0] for row in cursor.fetchall()}
            
            # Filter pending migrations
            pending = []
            for migration in self.migrations.values():
                if migration.migration_id not in executed_migrations:
                    if target_version is None or migration.version <= target_version:
                        pending.append(migration)
            
            # Sort by version
            pending.sort(key=lambda m: m.version)
            
            return pending
            
        except Exception as e:
            logger.error(f"Failed to get pending migrations: {e}")
            return []
    
    def validate_migration_dependencies(self, migration: Migration) -> bool:
        """Validate that migration dependencies are satisfied"""
        try:
            if not migration.dependencies:
                return True
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            for dependency in migration.dependencies:
                cursor.execute("""
                    SELECT COUNT(*) FROM migration_executions 
                    WHERE migration_id = ? AND status = 'completed'
                """, (dependency,))
                
                if cursor.fetchone()[0] == 0:
                    logger.error(f"Migration dependency not satisfied: {dependency}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate dependencies: {e}")
            return False
    
    def execute_migration(self, migration_id: str, dry_run: bool = False) -> MigrationExecution:
        """Execute a single migration with backup and rollback support"""
        if migration_id not in self.migrations:
            raise ValueError(f"Migration not found: {migration_id}")
        
        migration = self.migrations[migration_id]
        execution_id = str(uuid.uuid4())
        
        execution = MigrationExecution(
            execution_id=execution_id,
            migration_id=migration_id,
            version=migration.version,
            status=MigrationStatus.PENDING,
            started_at=datetime.now()
        )
        
        with self.lock:
            try:
                # Validate dependencies
                if not self.validate_migration_dependencies(migration):
                    execution.status = MigrationStatus.FAILED
                    execution.error_message = "Migration dependencies not satisfied"
                    return execution
                
                # Create backup if required
                backup_info = None
                if migration.backup_required and not dry_run:
                    backup_info = self.create_backup(
                        BackupType.FULL_DATABASE, 
                        migration_id
                    )
                    execution.backup_path = backup_info.backup_path
                
                # Start migration execution
                execution.status = MigrationStatus.RUNNING
                self._log_migration_execution(execution)
                
                if dry_run:
                    logger.info(f"🔄 DRY RUN: Would execute migration {migration_id}")
                    execution.status = MigrationStatus.COMPLETED
                    execution.completed_at = datetime.now()
                    return execution
                
                # Execute migration SQL
                start_time = time.time()
                conn = self._get_connection()
                
                # Begin transaction
                conn.execute("BEGIN IMMEDIATE")
                
                try:
                    # Execute migration SQL
                    cursor = conn.cursor()
                    
                    # Split SQL into individual statements
                    statements = [stmt.strip() for stmt in migration.up_sql.split(';') if stmt.strip()]
                    
                    for statement in statements:
                        cursor.execute(statement)
                    
                    # Update schema version
                    cursor.execute("""
                        UPDATE schema_version 
                        SET current_version = ?, last_migration_id = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = 1
                    """, (migration.version, migration_id))
                    
                    # Commit transaction
                    conn.commit()
                    
                    execution.status = MigrationStatus.COMPLETED
                    execution.completed_at = datetime.now()
                    execution.execution_time = time.time() - start_time
                    
                    logger.info(f"✅ Migration {migration_id} completed successfully")
                    
                except Exception as sql_error:
                    # Rollback transaction
                    conn.rollback()
                    raise sql_error
                
            except Exception as e:
                execution.status = MigrationStatus.FAILED
                execution.error_message = str(e)
                execution.completed_at = datetime.now()
                execution.execution_time = time.time() - start_time if 'start_time' in locals() else 0
                
                logger.error(f"❌ Migration {migration_id} failed: {e}")
                
                # Attempt automatic rollback if backup exists
                if execution.backup_path and migration.is_reversible:
                    try:
                        self.rollback_migration(execution_id)
                        execution.status = MigrationStatus.ROLLED_BACK
                        logger.info(f"🔄 Migration {migration_id} automatically rolled back")
                    except Exception as rollback_error:
                        logger.error(f"Failed to rollback migration: {rollback_error}")
            
            finally:
                # Log final execution state
                self._log_migration_execution(execution)
        
        return execution
    
    def rollback_migration(self, execution_id: str) -> bool:
        """Rollback a migration using backup or down SQL"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get execution info
            cursor.execute("""
                SELECT migration_id, backup_path, status FROM migration_executions 
                WHERE execution_id = ?
            """, (execution_id,))
            
            result = cursor.fetchone()
            if not result:
                raise ValueError(f"Migration execution not found: {execution_id}")
            
            migration_id, backup_path, status = result
            
            if status not in ['completed', 'failed']:
                raise ValueError(f"Cannot rollback migration in status: {status}")
            
            migration = self.migrations.get(migration_id)
            if not migration:
                raise ValueError(f"Migration not found: {migration_id}")
            
            # Method 1: Restore from backup
            if backup_path and Path(backup_path).exists():
                logger.info(f"🔄 Rolling back using backup: {backup_path}")
                
                # Close current connection
                if self.connection:
                    self.connection.close()
                    self.connection = None
                
                # Restore from backup
                shutil.copy2(backup_path, self.database_path)
                
                # Reconnect
                self._get_connection()
                
                logger.info(f"✅ Migration {migration_id} rolled back from backup")
                return True
            
            # Method 2: Execute down SQL
            elif migration.is_reversible and migration.down_sql:
                logger.info(f"🔄 Rolling back using down SQL")
                
                conn.execute("BEGIN IMMEDIATE")
                
                try:
                    # Execute down SQL
                    statements = [stmt.strip() for stmt in migration.down_sql.split(';') if stmt.strip()]
                    
                    for statement in statements:
                        cursor.execute(statement)
                    
                    # Update migration execution status
                    cursor.execute("""
                        UPDATE migration_executions 
                        SET status = 'rolled_back' 
                        WHERE execution_id = ?
                    """, (execution_id,))
                    
                    conn.commit()
                    
                    logger.info(f"✅ Migration {migration_id} rolled back using down SQL")
                    return True
                    
                except Exception as e:
                    conn.rollback()
                    raise e
            
            else:
                raise ValueError("No rollback method available (no backup or down SQL)")
                
        except Exception as e:
            logger.error(f"Failed to rollback migration: {e}")
            return False
    
    def migrate_to_version(self, target_version: str, dry_run: bool = False) -> List[MigrationExecution]:
        """Migrate database to specific version"""
        logger.info(f"🔄 Migrating to version {target_version} (dry_run={dry_run})")
        
        pending_migrations = self.get_pending_migrations(target_version)
        executions = []
        
        if not pending_migrations:
            logger.info("✅ No pending migrations found")
            return executions
        
        logger.info(f"📋 Found {len(pending_migrations)} pending migrations")
        
        for migration in pending_migrations:
            try:
                execution = self.execute_migration(migration.migration_id, dry_run)
                executions.append(execution)
                
                if execution.status == MigrationStatus.FAILED:
                    logger.error(f"❌ Migration failed, stopping: {migration.migration_id}")
                    break
                    
            except Exception as e:
                logger.error(f"❌ Failed to execute migration {migration.migration_id}: {e}")
                break
        
        successful_migrations = sum(1 for e in executions if e.status == MigrationStatus.COMPLETED)
        logger.info(f"✅ Migration complete: {successful_migrations}/{len(executions)} successful")
        
        return executions
    
    def migrate_latest(self, dry_run: bool = False) -> List[MigrationExecution]:
        """Migrate to latest version"""
        if not self.migrations:
            logger.info("✅ No migrations found")
            return []
        
        latest_version = max(migration.version for migration in self.migrations.values())
        return self.migrate_to_version(latest_version, dry_run)
    
    def _log_migration_execution(self, execution: MigrationExecution):
        """Log migration execution to database"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO migration_executions 
                (execution_id, migration_id, version, status, started_at, completed_at, 
                 error_message, backup_path, rollback_available, execution_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution.execution_id, execution.migration_id, execution.version,
                execution.status.value, execution.started_at, execution.completed_at,
                execution.error_message, execution.backup_path, execution.rollback_available,
                execution.execution_time
            ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to log migration execution: {e}")
    
    def get_migration_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get migration execution history"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT me.*, mm.name, mm.description 
                FROM migration_executions me
                LEFT JOIN migration_metadata mm ON me.migration_id = mm.migration_id
                ORDER BY me.started_at DESC
                LIMIT ?
            """, (limit,))
            
            columns = [description[0] for description in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                result = dict(zip(columns, row))
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get migration history: {e}")
            return []
    
    def get_backup_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get backup history"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM backup_info 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,))
            
            columns = [description[0] for description in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                result = dict(zip(columns, row))
                # Add human-readable size
                result['size_mb'] = round(result['size_bytes'] / (1024 * 1024), 2)
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get backup history: {e}")
            return []
    
    def cleanup_old_backups(self, keep_days: int = 30, keep_count: int = 10) -> int:
        """Clean up old backup files"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get old backups
            cutoff_date = datetime.now() - timedelta(days=keep_days)
            
            cursor.execute("""
                SELECT backup_id, backup_path FROM backup_info 
                WHERE created_at < ? 
                ORDER BY created_at DESC 
                OFFSET ?
            """, (cutoff_date, keep_count))
            
            old_backups = cursor.fetchall()
            cleaned_count = 0
            
            for backup_id, backup_path in old_backups:
                try:
                    # Remove backup file
                    if Path(backup_path).exists():
                        Path(backup_path).unlink()
                    
                    # Mark as invalid in database
                    cursor.execute("""
                        UPDATE backup_info 
                        SET is_valid = 0 
                        WHERE backup_id = ?
                    """, (backup_id,))
                    
                    cleaned_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to clean backup {backup_path}: {e}")
            
            conn.commit()
            
            logger.info(f"✅ Cleaned up {cleaned_count} old backups")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
            return 0
    
    def validate_database_integrity(self) -> Dict[str, Any]:
        """Validate database integrity after migrations"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            integrity_report = {
                "timestamp": datetime.now().isoformat(),
                "overall_status": "healthy",
                "checks": {},
                "issues": [],
                "recommendations": []
            }
            
            # Check 1: PRAGMA integrity_check
            cursor.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()[0]
            integrity_report["checks"]["integrity_check"] = integrity_result
            
            if integrity_result != "ok":
                integrity_report["overall_status"] = "corrupted"
                integrity_report["issues"].append(f"Database integrity check failed: {integrity_result}")
            
            # Check 2: Foreign key check
            cursor.execute("PRAGMA foreign_key_check")
            fk_violations = cursor.fetchall()
            integrity_report["checks"]["foreign_key_violations"] = len(fk_violations)
            
            if fk_violations:
                integrity_report["overall_status"] = "issues"
                integrity_report["issues"].append(f"Found {len(fk_violations)} foreign key violations")
            
            # Check 3: Schema consistency
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            integrity_report["checks"]["table_count"] = len(tables)
            
            # Check 4: Migration consistency
            cursor.execute("SELECT COUNT(*) FROM migration_executions WHERE status = 'completed'")
            completed_migrations = cursor.fetchone()[0]
            integrity_report["checks"]["completed_migrations"] = completed_migrations
            
            # Generate recommendations
            if integrity_report["overall_status"] == "healthy":
                integrity_report["recommendations"].append("Database integrity is good")
            else:
                integrity_report["recommendations"].append("Consider running database repair or restoration from backup")
            
            return integrity_report
            
        except Exception as e:
            logger.error(f"Failed to validate database integrity: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "overall_status": "error",
                "error": str(e)
            }
    
    def generate_migration_report(self) -> Dict[str, Any]:
        """Generate comprehensive migration status report"""
        try:
            current_version = self.get_current_version()
            pending_migrations = self.get_pending_migrations()
            migration_history = self.get_migration_history(10)
            backup_history = self.get_backup_history(5)
            integrity_report = self.validate_database_integrity()
            
            report = {
                "timestamp": datetime.now().isoformat(),
                "current_version": current_version,
                "total_migrations": len(self.migrations),
                "pending_migrations": len(pending_migrations),
                "migration_history": migration_history,
                "backup_history": backup_history,
                "integrity_status": integrity_report["overall_status"],
                "recommendations": []
            }
            
            # Generate recommendations
            if pending_migrations:
                report["recommendations"].append(f"Consider running {len(pending_migrations)} pending migrations")
            
            if not backup_history:
                report["recommendations"].append("No recent backups found - consider creating a backup")
            
            if integrity_report["overall_status"] != "healthy":
                report["recommendations"].append("Database integrity issues detected - review and repair")
            
            if not report["recommendations"]:
                report["recommendations"].append("Migration system is healthy and up to date")
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate migration report: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Migration engine connection closed")

# Utility functions
def create_migration_engine(database_path: str = None, migrations_dir: str = None, 
                          backups_dir: str = None) -> MigrationEngine:
    """Factory function to create a migration engine"""
    return MigrationEngine(database_path, migrations_dir, backups_dir)

def create_migration_file(migrations_dir: str, name: str, migration_type: str = "schema_change",
                         author: str = "", description: str = "") -> Path:
    """Create a new migration file template"""
    migrations_path = Path(migrations_dir)
    migrations_path.mkdir(exist_ok=True)
    
    # Find next version number
    existing_files = list(migrations_path.glob("*.sql"))
    if existing_files:
        versions = []
        for file in existing_files:
            match = re.match(r'^(\d+)_', file.stem)
            if match:
                versions.append(int(match.group(1)))
        next_version = max(versions) + 1 if versions else 1
    else:
        next_version = 1
    
    # Create filename
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower())
    filename = f"{next_version:03d}_{safe_name}.sql"
    file_path = migrations_path / filename
    
    # Create migration template
    template = f"""-- @name: {name}
-- @description: {description}
-- @type: {migration_type}
-- @author: {author}
-- @dependencies: []
-- @reversible: true
-- @backup_required: true

-- UP
-- Add your migration SQL here


-- DOWN
-- Add your rollback SQL here

"""
    
    file_path.write_text(template, encoding='utf-8')
    logger.info(f"✅ Created migration file: {file_path}")
    
    return file_path

# Example usage
if __name__ == "__main__":
    print("🚀 Testing Database Migration Engine...")
    
    try:
        # Create migration engine
        engine = MigrationEngine()
        
        # Generate migration report
        report = engine.generate_migration_report()
        
        print(f"\n📊 Migration Report:")
        print(f"Current Version: {report['current_version']}")
        print(f"Total Migrations: {report['total_migrations']}")
        print(f"Pending Migrations: {report['pending_migrations']}")
        print(f"Integrity Status: {report['integrity_status']}")
        
        print(f"\n📋 Recommendations:")
        for recommendation in report['recommendations']:
            print(f"  - {recommendation}")
        
        engine.close()
        print("\n✅ Migration engine test completed!")
        
    except Exception as e:
        print(f"❌ Migration engine test failed: {e}")
        import traceback
        traceback.print_exc()