#!/usr/bin/env python3
"""
Database Maintenance System
Automated cleanup procedures, maintenance tasks, and audit trail management
"""
import os
import sqlite3
import threading
import time
import logging
import json
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MaintenanceTaskType(Enum):
    """Types of maintenance tasks"""
    VACUUM = "vacuum"
    ANALYZE = "analyze"
    REINDEX = "reindex"
    CLEANUP_TEMP = "cleanup_temp"
    CLEANUP_LOGS = "cleanup_logs"
    OPTIMIZE = "optimize"
    INTEGRITY_CHECK = "integrity_check"
    SIZE_MONITORING = "size_monitoring"
    AUDIT_CLEANUP = "audit_cleanup"

class TaskStatus(Enum):
    """Maintenance task status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class TaskPriority(Enum):
    """Task priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class MaintenanceTask:
    """Individual maintenance task"""
    task_id: str
    task_type: MaintenanceTaskType
    name: str
    description: str
    priority: TaskPriority
    schedule_cron: str  # Cron-like schedule
    enabled: bool = True
    max_duration_minutes: int = 60
    retry_count: int = 3
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class TaskExecution:
    """Task execution record"""
    execution_id: str
    task_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    result_message: str = ""
    error_message: str = ""
    records_processed: int = 0
    space_freed: int = 0
    duration_seconds: float = 0.0

@dataclass
class DatabaseStats:
    """Database statistics"""
    total_size: int
    table_count: int
    index_count: int
    largest_table: str
    largest_table_size: int
    fragmentation_ratio: float
    last_vacuum: Optional[datetime]
    last_analyze: Optional[datetime]

@dataclass
class CleanupRule:
    """Data cleanup rule"""
    rule_id: str
    name: str
    table_name: str
    condition: str  # SQL WHERE condition
    retention_days: int
    enabled: bool = True
    dry_run: bool = False

class DatabaseMaintenanceSystem:
    """Automated database maintenance and cleanup system"""
    
    def __init__(self, database_path: str = None):
        self.database_path = database_path or os.getenv("DATABASE_PATH", "trading_maintenance.db")
        
        # Maintenance management
        self.maintenance_tasks: Dict[str, MaintenanceTask] = {}
        self.cleanup_rules: Dict[str, CleanupRule] = {}
        self.active_executions: Dict[str, TaskExecution] = {}
        self.maintenance_lock = threading.RLock()
        
        # Scheduling and execution
        self.scheduler_thread = None
        self.is_running = False
        self.last_maintenance_check = datetime.now()
        
        # Statistics and monitoring
        self.database_stats = DatabaseStats(0, 0, 0, "", 0, 0.0, None, None)
        self.size_thresholds = {
            "warning_mb": 1000,  # 1GB
            "critical_mb": 5000,  # 5GB
            "max_mb": 10000      # 10GB
        }
        
        # Initialize system
        self._initialize_maintenance_db()
        self._setup_default_tasks()
        self._setup_default_cleanup_rules()
        self._load_existing_tasks()
    
    def _initialize_maintenance_db(self):
        """Initialize maintenance database tables"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Create maintenance tasks table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS maintenance_tasks (
                        task_id TEXT PRIMARY KEY,
                        task_type TEXT NOT NULL,
                        name TEXT NOT NULL,
                        description TEXT,
                        priority TEXT NOT NULL,
                        schedule_cron TEXT NOT NULL,
                        enabled BOOLEAN DEFAULT TRUE,
                        max_duration_minutes INTEGER DEFAULT 60,
                        retry_count INTEGER DEFAULT 3,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                
                # Create task executions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS task_executions (
                        execution_id TEXT PRIMARY KEY,
                        task_id TEXT NOT NULL,
                        start_time TEXT NOT NULL,
                        end_time TEXT,
                        status TEXT NOT NULL,
                        result_message TEXT,
                        error_message TEXT,
                        records_processed INTEGER DEFAULT 0,
                        space_freed INTEGER DEFAULT 0,
                        duration_seconds REAL DEFAULT 0.0,
                        FOREIGN KEY (task_id) REFERENCES maintenance_tasks(task_id)
                    )
                """)
                
                # Create cleanup rules table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS cleanup_rules (
                        rule_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        table_name TEXT NOT NULL,
                        condition TEXT NOT NULL,
                        retention_days INTEGER NOT NULL,
                        enabled BOOLEAN DEFAULT TRUE,
                        dry_run BOOLEAN DEFAULT FALSE,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                
                # Create database statistics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS database_statistics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        total_size INTEGER NOT NULL,
                        table_count INTEGER NOT NULL,
                        index_count INTEGER NOT NULL,
                        largest_table TEXT,
                        largest_table_size INTEGER,
                        fragmentation_ratio REAL,
                        maintenance_notes TEXT
                    )
                """)
                
                # Create audit trail table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS maintenance_audit (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        action TEXT NOT NULL,
                        table_name TEXT,
                        records_affected INTEGER DEFAULT 0,
                        user_id TEXT,
                        details TEXT,
                        checksum TEXT
                    )
                """)
                
                # Create indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_executions_task_id ON task_executions(task_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_executions_start_time ON task_executions(start_time)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_database_statistics_timestamp ON database_statistics(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_maintenance_audit_timestamp ON maintenance_audit(timestamp)")
                
                conn.commit()
                logger.info("✅ Database maintenance tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize maintenance database: {e}")
            raise
    
    def _setup_default_tasks(self):
        """Setup default maintenance tasks"""
        default_tasks = [
            {
                "task_id": "daily_vacuum",
                "task_type": MaintenanceTaskType.VACUUM,
                "name": "Daily VACUUM",
                "description": "Daily database vacuum to reclaim space",
                "priority": TaskPriority.NORMAL,
                "schedule_cron": "0 2 * * *",  # Daily at 2 AM
                "max_duration_minutes": 30
            },
            {
                "task_id": "weekly_analyze",
                "task_type": MaintenanceTaskType.ANALYZE,
                "name": "Weekly ANALYZE",
                "description": "Weekly statistics update for query optimization",
                "priority": TaskPriority.NORMAL,
                "schedule_cron": "0 3 * * 0",  # Weekly on Sunday at 3 AM
                "max_duration_minutes": 45
            },
            {
                "task_id": "daily_temp_cleanup",
                "task_type": MaintenanceTaskType.CLEANUP_TEMP,
                "name": "Daily Temp Cleanup",
                "description": "Clean up temporary files and data",
                "priority": TaskPriority.LOW,
                "schedule_cron": "0 1 * * *",  # Daily at 1 AM
                "max_duration_minutes": 15
            },
            {
                "task_id": "weekly_integrity_check",
                "task_type": MaintenanceTaskType.INTEGRITY_CHECK,
                "name": "Weekly Integrity Check",
                "description": "Check database integrity",
                "priority": TaskPriority.HIGH,
                "schedule_cron": "0 4 * * 0",  # Weekly on Sunday at 4 AM
                "max_duration_minutes": 60
            },
            {
                "task_id": "hourly_size_monitoring",
                "task_type": MaintenanceTaskType.SIZE_MONITORING,
                "name": "Hourly Size Monitoring",
                "description": "Monitor database size and growth",
                "priority": TaskPriority.LOW,
                "schedule_cron": "0 * * * *",  # Every hour
                "max_duration_minutes": 5
            }
        ]
        
        for task_config in default_tasks:
            if task_config["task_id"] not in self.maintenance_tasks:
                task = MaintenanceTask(**task_config)
                self.create_maintenance_task(task)
    
    def _setup_default_cleanup_rules(self):
        """Setup default cleanup rules"""
        default_rules = [
            {
                "rule_id": "old_sessions",
                "name": "Old Sessions Cleanup",
                "table_name": "user_sessions",
                "condition": "last_activity < datetime('now', '-7 days')",
                "retention_days": 7
            },
            {
                "rule_id": "old_logs",
                "name": "Old System Logs Cleanup",
                "table_name": "system_logs",
                "condition": "timestamp < datetime('now', '-30 days')",
                "retention_days": 30
            },
            {
                "rule_id": "temp_data",
                "name": "Temporary Data Cleanup",
                "table_name": "temp_calculations",
                "condition": "created_at < datetime('now', '-1 day')",
                "retention_days": 1
            }
        ]
        
        for rule_config in default_rules:
            if rule_config["rule_id"] not in self.cleanup_rules:
                rule = CleanupRule(**rule_config)
                self.create_cleanup_rule(rule)
    
    def _load_existing_tasks(self):
        """Load existing tasks and rules from database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Load maintenance tasks
                cursor.execute("SELECT * FROM maintenance_tasks")
                for row in cursor.fetchall():
                    task = MaintenanceTask(
                        task_id=row[0],
                        task_type=MaintenanceTaskType(row[1]),
                        name=row[2],
                        description=row[3],
                        priority=TaskPriority(row[4]),
                        schedule_cron=row[5],
                        enabled=bool(row[6]),
                        max_duration_minutes=row[7],
                        retry_count=row[8],
                        created_at=datetime.fromisoformat(row[9])
                    )
                    self.maintenance_tasks[task.task_id] = task
                
                # Load cleanup rules
                cursor.execute("SELECT * FROM cleanup_rules")
                for row in cursor.fetchall():
                    rule = CleanupRule(
                        rule_id=row[0],
                        name=row[1],
                        table_name=row[2],
                        condition=row[3],
                        retention_days=row[4],
                        enabled=bool(row[5]),
                        dry_run=bool(row[6])
                    )
                    self.cleanup_rules[rule.rule_id] = rule
                
                logger.info(f"✅ Loaded {len(self.maintenance_tasks)} maintenance tasks, {len(self.cleanup_rules)} cleanup rules")
                
        except Exception as e:
            logger.error(f"Failed to load existing tasks: {e}")
    
    def create_maintenance_task(self, task: MaintenanceTask) -> bool:
        """Create a new maintenance task"""
        try:
            with self.maintenance_lock:
                if task.task_id in self.maintenance_tasks:
                    raise ValueError(f"Maintenance task {task.task_id} already exists")
                
                # Store in database
                with sqlite3.connect(self.database_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO maintenance_tasks 
                        (task_id, task_type, name, description, priority, schedule_cron, 
                         enabled, max_duration_minutes, retry_count, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        task.task_id,
                        task.task_type.value,
                        task.name,
                        task.description,
                        task.priority.value,
                        task.schedule_cron,
                        task.enabled,
                        task.max_duration_minutes,
                        task.retry_count,
                        task.created_at.isoformat(),
                        datetime.now().isoformat()
                    ))
                    conn.commit()
                
                # Store in memory
                self.maintenance_tasks[task.task_id] = task
                
                logger.info(f"✅ Created maintenance task: {task.task_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create maintenance task: {e}")
            return False
    
    def create_cleanup_rule(self, rule: CleanupRule) -> bool:
        """Create a new cleanup rule"""
        try:
            with self.maintenance_lock:
                if rule.rule_id in self.cleanup_rules:
                    raise ValueError(f"Cleanup rule {rule.rule_id} already exists")
                
                # Store in database
                with sqlite3.connect(self.database_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO cleanup_rules 
                        (rule_id, name, table_name, condition, retention_days, 
                         enabled, dry_run, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        rule.rule_id,
                        rule.name,
                        rule.table_name,
                        rule.condition,
                        rule.retention_days,
                        rule.enabled,
                        rule.dry_run,
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))
                    conn.commit()
                
                # Store in memory
                self.cleanup_rules[rule.rule_id] = rule
                
                logger.info(f"✅ Created cleanup rule: {rule.rule_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create cleanup rule: {e}")
            return False
    
    def start_maintenance_system(self):
        """Start automated maintenance system"""
        try:
            if self.is_running:
                logger.warning("Maintenance system is already running")
                return
            
            self.is_running = True
            
            # Start scheduler thread
            self.scheduler_thread = threading.Thread(
                target=self._maintenance_loop,
                daemon=True,
                name="DatabaseMaintenanceScheduler"
            )
            self.scheduler_thread.start()
            
            logger.info("✅ Database maintenance system started")
            
        except Exception as e:
            logger.error(f"Failed to start maintenance system: {e}")
            self.is_running = False
            raise
    
    def stop_maintenance_system(self):
        """Stop maintenance system"""
        try:
            if not self.is_running:
                logger.warning("Maintenance system is not running")
                return
            
            self.is_running = False
            
            # Wait for scheduler thread to stop
            if self.scheduler_thread and self.scheduler_thread.is_alive():
                self.scheduler_thread.join(timeout=10)
            
            logger.info("✅ Database maintenance system stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop maintenance system: {e}")
    
    def _maintenance_loop(self):
        """Main maintenance loop"""
        while self.is_running:
            try:
                current_time = datetime.now()
                
                # Check if it's time for maintenance tasks
                if (current_time - self.last_maintenance_check).total_seconds() >= 60:  # Check every minute
                    self._check_scheduled_tasks(current_time)
                    self.last_maintenance_check = current_time
                
                # Update database statistics periodically
                if current_time.minute % 15 == 0:  # Every 15 minutes
                    self._update_database_statistics()
                
                time.sleep(30)  # Sleep for 30 seconds
                
            except Exception as e:
                logger.error(f"Error in maintenance loop: {e}")
                time.sleep(60)
    
    def _check_scheduled_tasks(self, current_time: datetime):
        """Check for scheduled tasks that need to run"""
        for task_id, task in self.maintenance_tasks.items():
            if not task.enabled:
                continue
            
            # Simple schedule check (in production, use proper cron parsing)
            if self._should_run_task(task, current_time):
                try:
                    self.execute_maintenance_task(task_id)
                except Exception as e:
                    logger.error(f"Failed to execute scheduled task {task_id}: {e}")
    
    def _should_run_task(self, task: MaintenanceTask, current_time: datetime) -> bool:
        """Check if task should run based on schedule"""
        # Simplified schedule checking - in production, use proper cron parsing
        # For now, just check if we haven't run this task recently
        
        # Get last execution
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT MAX(start_time) FROM task_executions 
                    WHERE task_id = ? AND status = 'completed'
                """, (task.task_id,))
                
                result = cursor.fetchone()
                if result and result[0]:
                    last_run = datetime.fromisoformat(result[0])
                    
                    # Simple interval checking based on task type
                    if task.task_type == MaintenanceTaskType.SIZE_MONITORING:
                        return (current_time - last_run).total_seconds() >= 3600  # Hourly
                    elif task.task_type in [MaintenanceTaskType.VACUUM, MaintenanceTaskType.CLEANUP_TEMP]:
                        return (current_time - last_run).total_seconds() >= 86400  # Daily
                    elif task.task_type in [MaintenanceTaskType.ANALYZE, MaintenanceTaskType.INTEGRITY_CHECK]:
                        return (current_time - last_run).total_seconds() >= 604800  # Weekly
                
                return True  # Run if never executed
                
        except Exception as e:
            logger.error(f"Failed to check task schedule: {e}")
            return False
    
    def execute_maintenance_task(self, task_id: str) -> Optional[TaskExecution]:
        """Execute a specific maintenance task"""
        try:
            if task_id not in self.maintenance_tasks:
                raise ValueError(f"Maintenance task {task_id} not found")
            
            task = self.maintenance_tasks[task_id]
            
            if not task.enabled:
                logger.info(f"Maintenance task {task_id} is disabled, skipping")
                return None
            
            # Create execution record
            execution = TaskExecution(
                execution_id=self._generate_execution_id(task_id),
                task_id=task_id,
                start_time=datetime.now(),
                status=TaskStatus.RUNNING
            )
            
            # Store execution
            self.active_executions[execution.execution_id] = execution
            self._store_task_execution(execution)
            
            logger.info(f"🔄 Starting maintenance task: {execution.execution_id} ({task.name})")
            
            # Execute task based on type
            success = False
            if task.task_type == MaintenanceTaskType.VACUUM:
                success = self._execute_vacuum_task(execution)
            elif task.task_type == MaintenanceTaskType.ANALYZE:
                success = self._execute_analyze_task(execution)
            elif task.task_type == MaintenanceTaskType.REINDEX:
                success = self._execute_reindex_task(execution)
            elif task.task_type == MaintenanceTaskType.CLEANUP_TEMP:
                success = self._execute_cleanup_temp_task(execution)
            elif task.task_type == MaintenanceTaskType.CLEANUP_LOGS:
                success = self._execute_cleanup_logs_task(execution)
            elif task.task_type == MaintenanceTaskType.OPTIMIZE:
                success = self._execute_optimize_task(execution)
            elif task.task_type == MaintenanceTaskType.INTEGRITY_CHECK:
                success = self._execute_integrity_check_task(execution)
            elif task.task_type == MaintenanceTaskType.SIZE_MONITORING:
                success = self._execute_size_monitoring_task(execution)
            elif task.task_type == MaintenanceTaskType.AUDIT_CLEANUP:
                success = self._execute_audit_cleanup_task(execution)
            else:
                execution.error_message = f"Unknown task type: {task.task_type}"
                success = False
            
            # Update execution status
            execution.end_time = datetime.now()
            execution.duration_seconds = (execution.end_time - execution.start_time).total_seconds()
            execution.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
            
            # Update in database
            self._update_task_execution(execution)
            
            # Remove from active executions
            if execution.execution_id in self.active_executions:
                del self.active_executions[execution.execution_id]
            
            # Log audit trail
            self._log_maintenance_audit(
                action=f"maintenance_task_{task.task_type.value}",
                details=f"Task: {task.name}, Status: {execution.status.value}, Duration: {execution.duration_seconds:.2f}s"
            )
            
            logger.info(f"✅ Maintenance task completed: {execution.execution_id} - Status: {execution.status.value}")
            return execution
            
        except Exception as e:
            logger.error(f"Failed to execute maintenance task {task_id}: {e}")
            if 'execution' in locals():
                execution.status = TaskStatus.FAILED
                execution.error_message = str(e)
                execution.end_time = datetime.now()
                execution.duration_seconds = (execution.end_time - execution.start_time).total_seconds()
                self._update_task_execution(execution)
            return None
    
    def _generate_execution_id(self, task_id: str) -> str:
        """Generate unique execution ID"""
        timestamp = datetime.now().isoformat()
        content = f"{task_id}_{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _store_task_execution(self, execution: TaskExecution):
        """Store task execution in database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO task_executions 
                    (execution_id, task_id, start_time, status)
                    VALUES (?, ?, ?, ?)
                """, (
                    execution.execution_id,
                    execution.task_id,
                    execution.start_time.isoformat(),
                    execution.status.value
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to store task execution: {e}")
    
    def _update_task_execution(self, execution: TaskExecution):
        """Update task execution in database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE task_executions SET 
                    end_time=?, status=?, result_message=?, error_message=?, 
                    records_processed=?, space_freed=?, duration_seconds=?
                    WHERE execution_id=?
                """, (
                    execution.end_time.isoformat() if execution.end_time else None,
                    execution.status.value,
                    execution.result_message,
                    execution.error_message,
                    execution.records_processed,
                    execution.space_freed,
                    execution.duration_seconds,
                    execution.execution_id
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update task execution: {e}")
    
    def _execute_vacuum_task(self, execution: TaskExecution) -> bool:
        """Execute VACUUM task"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                # Get database size before vacuum
                size_before = self._get_database_size()
                
                # Execute VACUUM
                conn.execute("VACUUM")
                
                # Get database size after vacuum
                size_after = self._get_database_size()
                
                execution.space_freed = size_before - size_after
                execution.result_message = f"VACUUM completed. Space freed: {execution.space_freed} bytes"
                
                return True
                
        except Exception as e:
            execution.error_message = f"VACUUM failed: {str(e)}"
            return False
    
    def _execute_analyze_task(self, execution: TaskExecution) -> bool:
        """Execute ANALYZE task"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Get list of tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                # Analyze each table
                analyzed_count = 0
                for table in tables:
                    try:
                        cursor.execute(f"ANALYZE {table}")
                        analyzed_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to analyze table {table}: {e}")
                
                execution.records_processed = analyzed_count
                execution.result_message = f"ANALYZE completed for {analyzed_count} tables"
                
                return True
                
        except Exception as e:
            execution.error_message = f"ANALYZE failed: {str(e)}"
            return False
    
    def _execute_reindex_task(self, execution: TaskExecution) -> bool:
        """Execute REINDEX task"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Get list of indexes
                cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")
                indexes = [row[0] for row in cursor.fetchall()]
                
                # Reindex each index
                reindexed_count = 0
                for index in indexes:
                    try:
                        cursor.execute(f"REINDEX {index}")
                        reindexed_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to reindex {index}: {e}")
                
                execution.records_processed = reindexed_count
                execution.result_message = f"REINDEX completed for {reindexed_count} indexes"
                
                return True
                
        except Exception as e:
            execution.error_message = f"REINDEX failed: {str(e)}"
            return False
    
    def _execute_cleanup_temp_task(self, execution: TaskExecution) -> bool:
        """Execute temporary data cleanup task"""
        try:
            cleaned_count = 0
            
            # Execute cleanup rules for temporary data
            for rule_id, rule in self.cleanup_rules.items():
                if rule.enabled and "temp" in rule.table_name.lower():
                    count = self._execute_cleanup_rule(rule)
                    cleaned_count += count
            
            # Clean up temporary files
            temp_files_cleaned = self._cleanup_temp_files()
            
            execution.records_processed = cleaned_count + temp_files_cleaned
            execution.result_message = f"Cleaned {cleaned_count} temp records and {temp_files_cleaned} temp files"
            
            return True
            
        except Exception as e:
            execution.error_message = f"Temp cleanup failed: {str(e)}"
            return False
    
    def _execute_cleanup_logs_task(self, execution: TaskExecution) -> bool:
        """Execute log cleanup task"""
        try:
            cleaned_count = 0
            
            # Execute cleanup rules for log data
            for rule_id, rule in self.cleanup_rules.items():
                if rule.enabled and "log" in rule.table_name.lower():
                    count = self._execute_cleanup_rule(rule)
                    cleaned_count += count
            
            execution.records_processed = cleaned_count
            execution.result_message = f"Cleaned {cleaned_count} log records"
            
            return True
            
        except Exception as e:
            execution.error_message = f"Log cleanup failed: {str(e)}"
            return False
    
    def _execute_optimize_task(self, execution: TaskExecution) -> bool:
        """Execute database optimization task"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Run PRAGMA optimize
                cursor.execute("PRAGMA optimize")
                
                # Update statistics
                self._update_database_statistics()
                
                execution.result_message = "Database optimization completed"
                
                return True
                
        except Exception as e:
            execution.error_message = f"Optimization failed: {str(e)}"
            return False
    
    def _execute_integrity_check_task(self, execution: TaskExecution) -> bool:
        """Execute database integrity check task"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Run integrity check
                cursor.execute("PRAGMA integrity_check")
                results = cursor.fetchall()
                
                # Check results
                if len(results) == 1 and results[0][0] == "ok":
                    execution.result_message = "Database integrity check passed"
                    return True
                else:
                    execution.error_message = f"Integrity check found issues: {results}"
                    return False
                
        except Exception as e:
            execution.error_message = f"Integrity check failed: {str(e)}"
            return False
    
    def _execute_size_monitoring_task(self, execution: TaskExecution) -> bool:
        """Execute database size monitoring task"""
        try:
            # Update database statistics
            self._update_database_statistics()
            
            # Check size thresholds
            size_mb = self.database_stats.total_size / (1024 * 1024)
            
            if size_mb > self.size_thresholds["critical_mb"]:
                execution.result_message = f"CRITICAL: Database size {size_mb:.2f}MB exceeds critical threshold"
                # Could trigger alerts here
            elif size_mb > self.size_thresholds["warning_mb"]:
                execution.result_message = f"WARNING: Database size {size_mb:.2f}MB exceeds warning threshold"
            else:
                execution.result_message = f"Database size {size_mb:.2f}MB is within normal limits"
            
            return True
            
        except Exception as e:
            execution.error_message = f"Size monitoring failed: {str(e)}"
            return False
    
    def _execute_audit_cleanup_task(self, execution: TaskExecution) -> bool:
        """Execute audit trail cleanup task"""
        try:
            # Clean up old audit records (keep last 90 days)
            cutoff_date = datetime.now() - timedelta(days=90)
            
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Count records to be deleted
                cursor.execute("""
                    SELECT COUNT(*) FROM maintenance_audit 
                    WHERE timestamp < ?
                """, (cutoff_date.isoformat(),))
                
                count_to_delete = cursor.fetchone()[0]
                
                # Delete old audit records
                cursor.execute("""
                    DELETE FROM maintenance_audit 
                    WHERE timestamp < ?
                """, (cutoff_date.isoformat(),))
                
                conn.commit()
                
                execution.records_processed = count_to_delete
                execution.result_message = f"Cleaned {count_to_delete} old audit records"
                
                return True
                
        except Exception as e:
            execution.error_message = f"Audit cleanup failed: {str(e)}"
            return False
    
    def _execute_cleanup_rule(self, rule: CleanupRule) -> int:
        """Execute a specific cleanup rule"""
        try:
            if not self._table_exists(rule.table_name):
                logger.warning(f"Table {rule.table_name} does not exist, skipping cleanup rule {rule.rule_id}")
                return 0
            
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                if rule.dry_run:
                    # Count records that would be deleted
                    cursor.execute(f"SELECT COUNT(*) FROM {rule.table_name} WHERE {rule.condition}")
                    count = cursor.fetchone()[0]
                    logger.info(f"DRY RUN: Would delete {count} records from {rule.table_name}")
                    return count
                else:
                    # Delete records
                    cursor.execute(f"DELETE FROM {rule.table_name} WHERE {rule.condition}")
                    deleted_count = cursor.rowcount
                    conn.commit()
                    
                    logger.info(f"Deleted {deleted_count} records from {rule.table_name}")
                    return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to execute cleanup rule {rule.rule_id}: {e}")
            return 0
    
    def _cleanup_temp_files(self) -> int:
        """Clean up temporary files"""
        try:
            temp_dir = tempfile.gettempdir()
            cleaned_count = 0
            
            # Look for old temporary files related to our application
            for file in os.listdir(temp_dir):
                if file.startswith("trading_") and file.endswith(".tmp"):
                    file_path = os.path.join(temp_dir, file)
                    try:
                        # Remove files older than 1 day
                        file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(file_path))
                        if file_age.days >= 1:
                            os.remove(file_path)
                            cleaned_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to remove temp file {file_path}: {e}")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup temp files: {e}")
            return 0
    
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
    
    def _get_database_size(self) -> int:
        """Get database file size in bytes"""
        try:
            if os.path.exists(self.database_path):
                return os.path.getsize(self.database_path)
            return 0
        except Exception as e:
            logger.error(f"Failed to get database size: {e}")
            return 0
    
    def _update_database_statistics(self):
        """Update database statistics"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Get total size
                total_size = self._get_database_size()
                
                # Count tables
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cursor.fetchone()[0]
                
                # Count indexes
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index'")
                index_count = cursor.fetchone()[0]
                
                # Find largest table
                largest_table = ""
                largest_table_size = 0
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        row_count = cursor.fetchone()[0]
                        if row_count > largest_table_size:
                            largest_table_size = row_count
                            largest_table = table
                    except:
                        pass
                
                # Calculate fragmentation (simplified)
                cursor.execute("PRAGMA freelist_count")
                free_pages = cursor.fetchone()[0]
                cursor.execute("PRAGMA page_count")
                total_pages = cursor.fetchone()[0]
                
                fragmentation_ratio = (free_pages / max(total_pages, 1)) * 100
                
                # Update statistics
                self.database_stats = DatabaseStats(
                    total_size=total_size,
                    table_count=table_count,
                    index_count=index_count,
                    largest_table=largest_table,
                    largest_table_size=largest_table_size,
                    fragmentation_ratio=fragmentation_ratio,
                    last_vacuum=self._get_last_task_execution(MaintenanceTaskType.VACUUM),
                    last_analyze=self._get_last_task_execution(MaintenanceTaskType.ANALYZE)
                )
                
                # Store statistics in database
                cursor.execute("""
                    INSERT INTO database_statistics 
                    (timestamp, total_size, table_count, index_count, largest_table, 
                     largest_table_size, fragmentation_ratio)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(),
                    total_size,
                    table_count,
                    index_count,
                    largest_table,
                    largest_table_size,
                    fragmentation_ratio
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update database statistics: {e}")
    
    def _get_last_task_execution(self, task_type: MaintenanceTaskType) -> Optional[datetime]:
        """Get last execution time for a task type"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT MAX(te.start_time) 
                    FROM task_executions te
                    JOIN maintenance_tasks mt ON te.task_id = mt.task_id
                    WHERE mt.task_type = ? AND te.status = 'completed'
                """, (task_type.value,))
                
                result = cursor.fetchone()
                if result and result[0]:
                    return datetime.fromisoformat(result[0])
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get last task execution: {e}")
            return None
    
    def _log_maintenance_audit(self, action: str, table_name: str = None, 
                              records_affected: int = 0, user_id: str = None, 
                              details: str = None):
        """Log maintenance action to audit trail"""
        try:
            # Calculate checksum for audit integrity
            audit_data = f"{action}_{table_name}_{records_affected}_{datetime.now().isoformat()}"
            checksum = hashlib.md5(audit_data.encode()).hexdigest()
            
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO maintenance_audit 
                    (timestamp, action, table_name, records_affected, user_id, details, checksum)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(),
                    action,
                    table_name,
                    records_affected,
                    user_id,
                    details,
                    checksum
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to log maintenance audit: {e}")
    
    def get_maintenance_statistics(self) -> Dict[str, Any]:
        """Get maintenance system statistics"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Count executions by status
                cursor.execute("""
                    SELECT status, COUNT(*) FROM task_executions 
                    GROUP BY status
                """)
                execution_stats = dict(cursor.fetchall())
                
                # Get recent executions
                cursor.execute("""
                    SELECT COUNT(*) FROM task_executions 
                    WHERE start_time > datetime('now', '-24 hours')
                """)
                recent_executions = cursor.fetchone()[0]
                
                # Get average execution time
                cursor.execute("""
                    SELECT AVG(duration_seconds) FROM task_executions 
                    WHERE status = 'completed' AND duration_seconds > 0
                """)
                avg_duration = cursor.fetchone()[0] or 0
                
                return {
                    "database_stats": asdict(self.database_stats),
                    "execution_stats": execution_stats,
                    "recent_executions_24h": recent_executions,
                    "average_execution_time": avg_duration,
                    "active_tasks": len(self.maintenance_tasks),
                    "enabled_tasks": len([t for t in self.maintenance_tasks.values() if t.enabled]),
                    "active_cleanup_rules": len([r for r in self.cleanup_rules.values() if r.enabled]),
                    "system_running": self.is_running
                }
                
        except Exception as e:
            logger.error(f"Failed to get maintenance statistics: {e}")
            return {}
    
    def get_recent_executions(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent task executions"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT te.execution_id, te.task_id, mt.name, te.start_time, 
                           te.end_time, te.status, te.duration_seconds, te.result_message
                    FROM task_executions te
                    JOIN maintenance_tasks mt ON te.task_id = mt.task_id
                    WHERE te.start_time > ?
                    ORDER BY te.start_time DESC
                """, (cutoff_time.isoformat(),))
                
                executions = []
                for row in cursor.fetchall():
                    executions.append({
                        "execution_id": row[0],
                        "task_id": row[1],
                        "task_name": row[2],
                        "start_time": row[3],
                        "end_time": row[4],
                        "status": row[5],
                        "duration_seconds": row[6],
                        "result_message": row[7]
                    })
                
                return executions
                
        except Exception as e:
            logger.error(f"Failed to get recent executions: {e}")
            return []
    
    def force_maintenance_task(self, task_id: str) -> Optional[TaskExecution]:
        """Force execution of a maintenance task"""
        logger.info(f"🔄 Force executing maintenance task: {task_id}")
        return self.execute_maintenance_task(task_id)
    
    def __del__(self):
        """Cleanup on destruction"""
        try:
            self.stop_maintenance_system()
        except:
            pass

# Example usage and testing
if __name__ == "__main__":
    # Initialize maintenance system
    maintenance_system = DatabaseMaintenanceSystem()
    
    try:
        # Start maintenance system
        maintenance_system.start_maintenance_system()
        print("✅ Maintenance system started")
        
        # Get statistics
        stats = maintenance_system.get_maintenance_statistics()
        print(f"Statistics: {stats}")
        
        # Force a maintenance task
        execution = maintenance_system.force_maintenance_task("daily_vacuum")
        if execution:
            print(f"Forced execution: {execution.execution_id} - {execution.status.value}")
        
        # Wait a bit
        time.sleep(5)
        
        # Stop maintenance system
        maintenance_system.stop_maintenance_system()
        print("✅ Maintenance system stopped")
        
    except KeyboardInterrupt:
        print("\n⏹️ Stopping maintenance system...")
    finally:
        maintenance_system.stop_maintenance_system()
        print("✅ Maintenance system stopped")