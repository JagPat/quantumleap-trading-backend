"""
Atomic Transaction Management System

Provides ACID-compliant transaction management with rollback capabilities,
deadlock detection, and intelligent retry mechanisms for the trading database.
"""

import os
import sqlite3
import logging
import threading
import time
import hashlib
from contextlib import contextmanager
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TransactionStatus(Enum):
    """Transaction status enumeration"""
    PENDING = "pending"
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"

class TransactionIsolationLevel(Enum):
    """Transaction isolation levels"""
    READ_UNCOMMITTED = "READ UNCOMMITTED"
    READ_COMMITTED = "READ COMMITTED"
    REPEATABLE_READ = "REPEATABLE READ"
    SERIALIZABLE = "SERIALIZABLE"

@dataclass
class TransactionOperation:
    """Represents a single database operation within a transaction"""
    query: str
    params: Optional[tuple] = None
    operation_type: str = "unknown"  # INSERT, UPDATE, DELETE, SELECT
    table_name: Optional[str] = None
    expected_rows: Optional[int] = None
    rollback_query: Optional[str] = None
    rollback_params: Optional[tuple] = None

@dataclass
class TransactionContext:
    """Transaction context with metadata and state"""
    transaction_id: str
    status: TransactionStatus
    operations: List[TransactionOperation]
    start_time: datetime
    isolation_level: TransactionIsolationLevel
    timeout_seconds: int
    retry_count: int
    max_retries: int
    last_error: Optional[str] = None
    rollback_operations: List[TransactionOperation] = None
    
    def __post_init__(self):
        if self.rollback_operations is None:
            self.rollback_operations = []

class DeadlockDetector:
    """Detects and resolves database deadlocks"""
    
    def __init__(self):
        self._active_transactions = {}
        self._lock_graph = {}
        self._lock = threading.Lock()
    
    def register_transaction(self, transaction_id: str, tables: List[str]):
        """Register a transaction and its table dependencies"""
        with self._lock:
            self._active_transactions[transaction_id] = {
                'tables': tables,
                'start_time': datetime.now(),
                'status': 'active'
            }
    
    def unregister_transaction(self, transaction_id: str):
        """Unregister a completed transaction"""
        with self._lock:
            self._active_transactions.pop(transaction_id, None)
            # Clean up lock graph
            self._lock_graph.pop(transaction_id, None)
            for tid in list(self._lock_graph.keys()):
                if transaction_id in self._lock_graph[tid]:
                    self._lock_graph[tid].remove(transaction_id)
    
    def detect_deadlock(self, transaction_id: str, waiting_for_table: str) -> bool:
        """Detect if adding this wait would create a deadlock"""
        with self._lock:
            # Simple deadlock detection: check for circular dependencies
            for other_tid, info in self._active_transactions.items():
                if other_tid != transaction_id and waiting_for_table in info['tables']:
                    # Check if other transaction is waiting for our tables
                    our_tables = self._active_transactions.get(transaction_id, {}).get('tables', [])
                    if any(table in our_tables for table in info['tables']):
                        logger.warning(f"Potential deadlock detected between {transaction_id} and {other_tid}")
                        return True
            return False
    
    def get_deadlock_victim(self, transaction_ids: List[str]) -> str:
        """Choose which transaction to rollback in case of deadlock"""
        # Choose the transaction that started most recently
        with self._lock:
            latest_start = None
            victim = None
            
            for tid in transaction_ids:
                if tid in self._active_transactions:
                    start_time = self._active_transactions[tid]['start_time']
                    if latest_start is None or start_time > latest_start:
                        latest_start = start_time
                        victim = tid
            
            return victim or transaction_ids[0]

class TransactionManager:
    """
    ACID-compliant transaction manager with advanced features:
    - Atomic operations with rollback capability
    - Deadlock detection and resolution
    - Intelligent retry with exponential backoff
    - Transaction timeout handling
    - Performance monitoring
    """
    
    def __init__(self, database_manager=None):
        self.database_manager = database_manager
        self._active_transactions = {}
        self._transaction_history = []
        self._lock = threading.Lock()
        self._deadlock_detector = DeadlockDetector()
        
        # Configuration
        self.default_timeout = 30  # seconds
        self.max_retries = 3
        self.deadlock_timeout = 5  # seconds
        self.retry_base_delay = 0.1  # seconds
        
        logger.info("🔄 Transaction Manager initialized")
    
    def _generate_transaction_id(self) -> str:
        """Generate unique transaction ID"""
        timestamp = str(int(time.time() * 1000000))
        thread_id = str(threading.get_ident())
        return hashlib.md5(f"{timestamp}_{thread_id}".encode()).hexdigest()[:16]
    
    def _extract_table_names(self, operations: List[TransactionOperation]) -> List[str]:
        """Extract table names from operations for deadlock detection"""
        tables = set()
        for op in operations:
            if op.table_name:
                tables.add(op.table_name)
            else:
                # Try to extract table name from query
                query_upper = op.query.upper().strip()
                if query_upper.startswith(('INSERT INTO', 'UPDATE', 'DELETE FROM')):
                    words = query_upper.split()
                    if len(words) >= 3:
                        table_name = words[2].split('(')[0].strip()
                        tables.add(table_name)
        return list(tables)
    
    def _create_rollback_operations(self, operations: List[TransactionOperation]) -> List[TransactionOperation]:
        """Create rollback operations for the given operations"""
        rollback_ops = []
        
        for op in reversed(operations):  # Reverse order for rollback
            if op.rollback_query:
                rollback_ops.append(TransactionOperation(
                    query=op.rollback_query,
                    params=op.rollback_params,
                    operation_type="ROLLBACK",
                    table_name=op.table_name
                ))
        
        return rollback_ops
    
    @contextmanager
    def transaction(
        self,
        operations: List[TransactionOperation],
        isolation_level: TransactionIsolationLevel = TransactionIsolationLevel.READ_COMMITTED,
        timeout_seconds: Optional[int] = None,
        max_retries: Optional[int] = None
    ):
        """
        Context manager for atomic transactions
        
        Args:
            operations: List of database operations to execute atomically
            isolation_level: Transaction isolation level
            timeout_seconds: Transaction timeout (default: 30s)
            max_retries: Maximum retry attempts (default: 3)
        
        Yields:
            TransactionContext: Transaction context for monitoring
        
        Example:
            operations = [
                TransactionOperation(
                    query="INSERT INTO trades (symbol, quantity, price) VALUES (?, ?, ?)",
                    params=("AAPL", 100, 150.0),
                    operation_type="INSERT",
                    table_name="trades"
                ),
                TransactionOperation(
                    query="UPDATE portfolio SET quantity = quantity + ? WHERE symbol = ?",
                    params=(100, "AAPL"),
                    operation_type="UPDATE",
                    table_name="portfolio"
                )
            ]
            
            with transaction_manager.transaction(operations) as tx:
                # Transaction is automatically committed or rolled back
                pass
        """
        transaction_id = self._generate_transaction_id()
        timeout = timeout_seconds or self.default_timeout
        retries = max_retries or self.max_retries
        
        # Create transaction context
        context = TransactionContext(
            transaction_id=transaction_id,
            status=TransactionStatus.PENDING,
            operations=operations,
            start_time=datetime.now(),
            isolation_level=isolation_level,
            timeout_seconds=timeout,
            retry_count=0,
            max_retries=retries
        )
        
        # Register transaction
        with self._lock:
            self._active_transactions[transaction_id] = context
        
        # Register with deadlock detector
        table_names = self._extract_table_names(operations)
        self._deadlock_detector.register_transaction(transaction_id, table_names)
        
        try:
            # Execute transaction with retry logic
            success = self._execute_transaction_with_retry(context)
            
            if success:
                context.status = TransactionStatus.COMMITTED
                logger.info(f"✅ Transaction {transaction_id} committed successfully")
            else:
                context.status = TransactionStatus.FAILED
                logger.error(f"❌ Transaction {transaction_id} failed after {context.retry_count} retries")
                raise Exception(f"Transaction failed: {context.last_error}")
            
            yield context
            
        except Exception as e:
            # Rollback transaction
            context.status = TransactionStatus.ROLLED_BACK
            context.last_error = str(e)
            
            try:
                self._rollback_transaction(context)
                logger.warning(f"🔄 Transaction {transaction_id} rolled back due to error: {e}")
            except Exception as rollback_error:
                logger.error(f"❌ Rollback failed for transaction {transaction_id}: {rollback_error}")
            
            raise
        
        finally:
            # Cleanup
            with self._lock:
                self._active_transactions.pop(transaction_id, None)
                # Add to history
                self._transaction_history.append({
                    'transaction_id': transaction_id,
                    'status': context.status.value,
                    'start_time': context.start_time.isoformat(),
                    'end_time': datetime.now().isoformat(),
                    'retry_count': context.retry_count,
                    'operation_count': len(operations),
                    'error': context.last_error
                })
                
                # Keep only last 1000 transactions in history
                if len(self._transaction_history) > 1000:
                    self._transaction_history = self._transaction_history[-1000:]
            
            self._deadlock_detector.unregister_transaction(transaction_id)
    
    def _execute_transaction_with_retry(self, context: TransactionContext) -> bool:
        """Execute transaction with intelligent retry logic"""
        for attempt in range(context.max_retries + 1):
            context.retry_count = attempt
            
            try:
                # Check for timeout
                if datetime.now() - context.start_time > timedelta(seconds=context.timeout_seconds):
                    context.last_error = f"Transaction timeout after {context.timeout_seconds} seconds"
                    return False
                
                # Execute the transaction
                success = self._execute_transaction_operations(context)
                
                if success:
                    return True
                
            except sqlite3.OperationalError as e:
                error_msg = str(e).lower()
                
                # Handle specific SQLite errors
                if "database is locked" in error_msg or "deadlock" in error_msg:
                    context.last_error = f"Database lock/deadlock detected: {e}"
                    
                    # Check for deadlock
                    table_names = self._extract_table_names(context.operations)
                    if any(self._deadlock_detector.detect_deadlock(context.transaction_id, table) 
                           for table in table_names):
                        logger.warning(f"Deadlock detected for transaction {context.transaction_id}")
                        # Don't retry deadlocks immediately
                        time.sleep(self.deadlock_timeout)
                    
                    # Exponential backoff for retries
                    if attempt < context.max_retries:
                        delay = self.retry_base_delay * (2 ** attempt)
                        logger.warning(f"Retrying transaction {context.transaction_id} in {delay}s (attempt {attempt + 1})")
                        time.sleep(delay)
                        continue
                
                elif "constraint" in error_msg:
                    context.last_error = f"Constraint violation: {e}"
                    return False  # Don't retry constraint violations
                
                else:
                    context.last_error = f"Database error: {e}"
                    if attempt < context.max_retries:
                        delay = self.retry_base_delay * (2 ** attempt)
                        time.sleep(delay)
                        continue
            
            except Exception as e:
                context.last_error = f"Unexpected error: {e}"
                if attempt < context.max_retries:
                    delay = self.retry_base_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
        
        return False
    
    def _execute_transaction_operations(self, context: TransactionContext) -> bool:
        """Execute all operations in the transaction atomically"""
        if not self.database_manager:
            raise Exception("Database manager not configured")
        
        context.status = TransactionStatus.ACTIVE
        
        # Prepare transaction operations for database manager
        db_operations = []
        for op in context.operations:
            db_operations.append({
                'query': op.query,
                'params': op.params or ()
            })
        
        # Execute transaction using database manager
        success = self.database_manager.execute_transaction(db_operations)
        
        if success:
            logger.debug(f"Transaction {context.transaction_id} executed successfully")
            return True
        else:
            logger.error(f"Transaction {context.transaction_id} execution failed")
            return False
    
    def _rollback_transaction(self, context: TransactionContext):
        """Execute rollback operations if available"""
        if not context.rollback_operations:
            logger.debug(f"No rollback operations defined for transaction {context.transaction_id}")
            return
        
        try:
            # Execute rollback operations
            db_operations = []
            for op in context.rollback_operations:
                db_operations.append({
                    'query': op.query,
                    'params': op.params or ()
                })
            
            success = self.database_manager.execute_transaction(db_operations)
            
            if success:
                logger.info(f"Rollback completed for transaction {context.transaction_id}")
            else:
                logger.error(f"Rollback failed for transaction {context.transaction_id}")
        
        except Exception as e:
            logger.error(f"Rollback error for transaction {context.transaction_id}: {e}")
    
    def execute_atomic_operation(
        self,
        query: str,
        params: Optional[tuple] = None,
        rollback_query: Optional[str] = None,
        rollback_params: Optional[tuple] = None,
        timeout_seconds: Optional[int] = None
    ) -> bool:
        """
        Execute a single operation atomically
        
        Args:
            query: SQL query to execute
            params: Query parameters
            rollback_query: Optional rollback query
            rollback_params: Optional rollback parameters
            timeout_seconds: Operation timeout
        
        Returns:
            bool: True if operation succeeded
        """
        operation = TransactionOperation(
            query=query,
            params=params,
            rollback_query=rollback_query,
            rollback_params=rollback_params
        )
        
        try:
            with self.transaction([operation], timeout_seconds=timeout_seconds):
                return True
        except Exception as e:
            logger.error(f"Atomic operation failed: {e}")
            return False
    
    def get_transaction_status(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an active transaction"""
        with self._lock:
            context = self._active_transactions.get(transaction_id)
            if context:
                return {
                    'transaction_id': transaction_id,
                    'status': context.status.value,
                    'start_time': context.start_time.isoformat(),
                    'operation_count': len(context.operations),
                    'retry_count': context.retry_count,
                    'timeout_seconds': context.timeout_seconds,
                    'last_error': context.last_error
                }
            return None
    
    def get_active_transactions(self) -> List[Dict[str, Any]]:
        """Get all active transactions"""
        with self._lock:
            return [
                {
                    'transaction_id': tid,
                    'status': context.status.value,
                    'start_time': context.start_time.isoformat(),
                    'operation_count': len(context.operations),
                    'retry_count': context.retry_count
                }
                for tid, context in self._active_transactions.items()
            ]
    
    def get_transaction_metrics(self) -> Dict[str, Any]:
        """Get transaction performance metrics"""
        with self._lock:
            if not self._transaction_history:
                return {
                    'status': 'no_data',
                    'message': 'No transaction history available'
                }
            
            # Analyze recent transactions
            recent_transactions = self._transaction_history[-100:]
            
            total_count = len(recent_transactions)
            successful_count = len([t for t in recent_transactions if t['status'] == 'committed'])
            failed_count = len([t for t in recent_transactions if t['status'] == 'failed'])
            rolled_back_count = len([t for t in recent_transactions if t['status'] == 'rolled_back'])
            
            # Calculate retry statistics
            retry_counts = [t['retry_count'] for t in recent_transactions]
            avg_retries = sum(retry_counts) / len(retry_counts) if retry_counts else 0
            
            return {
                'status': 'healthy',
                'total_transactions': total_count,
                'successful_transactions': successful_count,
                'failed_transactions': failed_count,
                'rolled_back_transactions': rolled_back_count,
                'success_rate': round(successful_count / total_count, 3) if total_count > 0 else 0,
                'average_retries': round(avg_retries, 2),
                'active_transactions': len(self._active_transactions),
                'timestamp': datetime.now().isoformat()
            }
    
    def force_rollback_transaction(self, transaction_id: str) -> bool:
        """Force rollback of an active transaction"""
        with self._lock:
            context = self._active_transactions.get(transaction_id)
            if not context:
                return False
            
            try:
                self._rollback_transaction(context)
                context.status = TransactionStatus.ROLLED_BACK
                context.last_error = "Forced rollback"
                logger.warning(f"Transaction {transaction_id} force rolled back")
                return True
            except Exception as e:
                logger.error(f"Force rollback failed for {transaction_id}: {e}")
                return False
    
    def cleanup_stale_transactions(self, max_age_minutes: int = 60) -> int:
        """Clean up stale transactions that have been running too long"""
        cutoff_time = datetime.now() - timedelta(minutes=max_age_minutes)
        cleaned_count = 0
        
        with self._lock:
            stale_transactions = [
                tid for tid, context in self._active_transactions.items()
                if context.start_time < cutoff_time
            ]
            
            for tid in stale_transactions:
                try:
                    self.force_rollback_transaction(tid)
                    cleaned_count += 1
                except Exception as e:
                    logger.error(f"Failed to cleanup stale transaction {tid}: {e}")
        
        if cleaned_count > 0:
            logger.warning(f"Cleaned up {cleaned_count} stale transactions")
        
        return cleaned_count

# Global transaction manager instance
_transaction_manager = None

def get_transaction_manager(database_manager=None) -> TransactionManager:
    """Get the global transaction manager instance"""
    global _transaction_manager
    if _transaction_manager is None:
        _transaction_manager = TransactionManager(database_manager)
    elif database_manager and not _transaction_manager.database_manager:
        _transaction_manager.database_manager = database_manager
    return _transaction_manager

# Utility functions for common transaction patterns
def execute_trade_transaction(
    trade_data: Dict[str, Any],
    portfolio_updates: List[Dict[str, Any]],
    database_manager=None
) -> bool:
    """
    Execute a complete trade transaction with portfolio updates
    
    Args:
        trade_data: Trade information (symbol, quantity, price, etc.)
        portfolio_updates: List of portfolio updates to apply
        database_manager: Database manager instance
    
    Returns:
        bool: True if transaction succeeded
    """
    tm = get_transaction_manager(database_manager)
    
    operations = []
    
    # Add trade insertion
    operations.append(TransactionOperation(
        query="INSERT INTO trades (user_id, symbol, quantity, price, side, timestamp, strategy_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        params=(
            trade_data['user_id'],
            trade_data['symbol'],
            trade_data['quantity'],
            trade_data['price'],
            trade_data['side'],
            trade_data.get('timestamp', datetime.now()),
            trade_data.get('strategy_id')
        ),
        operation_type="INSERT",
        table_name="trades"
    ))
    
    # Add portfolio updates
    for update in portfolio_updates:
        operations.append(TransactionOperation(
            query="UPDATE portfolio SET quantity = ?, average_cost = ?, last_updated = ? WHERE user_id = ? AND symbol = ?",
            params=(
                update['quantity'],
                update['average_cost'],
                datetime.now(),
                update['user_id'],
                update['symbol']
            ),
            operation_type="UPDATE",
            table_name="portfolio"
        ))
    
    try:
        with tm.transaction(operations, timeout_seconds=10):
            return True
    except Exception as e:
        logger.error(f"Trade transaction failed: {e}")
        return False

def execute_portfolio_rebalance_transaction(
    user_id: str,
    rebalance_operations: List[Dict[str, Any]],
    database_manager=None
) -> bool:
    """
    Execute portfolio rebalancing transaction
    
    Args:
        user_id: User identifier
        rebalance_operations: List of rebalancing operations
        database_manager: Database manager instance
    
    Returns:
        bool: True if transaction succeeded
    """
    tm = get_transaction_manager(database_manager)
    
    operations = []
    
    for op in rebalance_operations:
        if op['action'] == 'buy':
            # Add trade record
            operations.append(TransactionOperation(
                query="INSERT INTO trades (user_id, symbol, quantity, price, side, timestamp) VALUES (?, ?, ?, ?, 'BUY', ?)",
                params=(user_id, op['symbol'], op['quantity'], op['price'], datetime.now()),
                operation_type="INSERT",
                table_name="trades"
            ))
            
            # Update portfolio
            operations.append(TransactionOperation(
                query="""
                INSERT INTO portfolio (user_id, symbol, quantity, average_cost, last_updated)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, symbol) DO UPDATE SET
                    quantity = quantity + excluded.quantity,
                    average_cost = (average_cost * quantity + excluded.average_cost * excluded.quantity) / (quantity + excluded.quantity),
                    last_updated = excluded.last_updated
                """,
                params=(user_id, op['symbol'], op['quantity'], op['price'], datetime.now()),
                operation_type="UPSERT",
                table_name="portfolio"
            ))
        
        elif op['action'] == 'sell':
            # Add trade record
            operations.append(TransactionOperation(
                query="INSERT INTO trades (user_id, symbol, quantity, price, side, timestamp) VALUES (?, ?, ?, ?, 'SELL', ?)",
                params=(user_id, op['symbol'], op['quantity'], op['price'], datetime.now()),
                operation_type="INSERT",
                table_name="trades"
            ))
            
            # Update portfolio
            operations.append(TransactionOperation(
                query="UPDATE portfolio SET quantity = quantity - ?, last_updated = ? WHERE user_id = ? AND symbol = ?",
                params=(op['quantity'], datetime.now(), user_id, op['symbol']),
                operation_type="UPDATE",
                table_name="portfolio"
            ))
    
    try:
        with tm.transaction(operations, timeout_seconds=30):
            return True
    except Exception as e:
        logger.error(f"Portfolio rebalance transaction failed: {e}")
        return False      
              columns = [description[0] for description in cursor.description]
                    old_values = dict(zip(columns, row))
            except Exception as e:
                logger.warning(f"Could not capture old values for audit: {e}")
        
        # Execute the query
        result = cursor.execute(query, params or ())
        
        # Capture new values for INSERT/UPDATE operations
        new_values = None
        if operation_type in ["INSERT", "UPDATE"] and table_name and record_id:
            try:
                cursor.execute(f"SELECT * FROM {table_name} WHERE id = ?", (record_id,))
                row = cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    new_values = dict(zip(columns, row))
            except Exception as e:
                logger.warning(f"Could not capture new values for audit: {e}")
        
        # Log the operation in audit trail
        if table_name and operation_type:
            self._log_audit_operation(
                table_name, operation_type, record_id, old_values, new_values
            )
        
        return result
    
    def _log_audit_operation(self, table_name: str, operation_type: str, record_id: str = None, 
                           old_values: Dict[str, Any] = None, new_values: Dict[str, Any] = None):
        """Log operation in audit trail"""
        try:
            self.operation_sequence += 1
            
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO transaction_audit_trail 
                (transaction_id, operation_sequence, table_name, operation_type, record_id, old_values, new_values)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                self.transaction_id,
                self.operation_sequence,
                table_name,
                operation_type,
                record_id,
                json.dumps(old_values) if old_values else None,
                json.dumps(new_values) if new_values else None
            ))
            
            # Update transaction log with operation details
            transaction_log = self.manager.transaction_logs.get(self.transaction_id)
            if transaction_log:
                transaction_log.operations.append({
                    "sequence": self.operation_sequence,
                    "table": table_name,
                    "operation": operation_type,
                    "record_id": record_id,
                    "timestamp": datetime.now().isoformat()
                })
            
        except Exception as e:
            logger.error(f"Failed to log audit operation: {e}")

class TransactionValidationError(Exception):
    """Exception raised when transaction validation fails"""
    pass

class DeadlockDetector:
    """Deadlock detection and resolution system"""
    
    def __init__(self):
        self.lock_graph: Dict[str, List[str]] = {}
        self.transaction_locks: Dict[str, List[str]] = {}
        self.lock = threading.RLock()
    
    def add_lock_request(self, transaction_id: str, resource_id: str, waiting_for: List[str] = None):
        """Add a lock request to the deadlock detection system"""
        with self.lock:
            if transaction_id not in self.transaction_locks:
                self.transaction_locks[transaction_id] = []
            
            self.transaction_locks[transaction_id].append(resource_id)
            
            if waiting_for:
                self.lock_graph[transaction_id] = waiting_for
            
            # Check for deadlocks
            if self._detect_deadlock():
                victim_transaction = self._select_deadlock_victim()
                raise DeadlockError(f"Deadlock detected. Victim transaction: {victim_transaction}")
    
    def remove_transaction(self, transaction_id: str):
        """Remove transaction from deadlock detection"""
        with self.lock:
            self.transaction_locks.pop(transaction_id, None)
            self.lock_graph.pop(transaction_id, None)
    
    def _detect_deadlock(self) -> bool:
        """Detect if there's a deadlock in the lock graph"""
        visited = set()
        rec_stack = set()
        
        def has_cycle(node):
            if node in rec_stack:
                return True
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in self.lock_graph.get(node, []):
                if has_cycle(neighbor):
                    return True
            
            rec_stack.remove(node)
            return False
        
        for transaction in self.lock_graph:
            if transaction not in visited:
                if has_cycle(transaction):
                    return True
        
        return False
    
    def _select_deadlock_victim(self) -> str:
        """Select which transaction to abort in case of deadlock"""
        # Simple strategy: select transaction with fewest locks
        if not self.transaction_locks:
            return ""
        
        victim = min(self.transaction_locks.keys(), 
                    key=lambda t: len(self.transaction_locks[t]))
        return victim

class DeadlockError(Exception):
    """Exception raised when a deadlock is detected"""
    pass

class TransactionRetryManager:
    """Manages transaction retry logic with exponential backoff"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 0.1, max_delay: float = 5.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def execute_with_retry(self, transaction_func: Callable, *args, **kwargs):
        """Execute transaction function with retry logic"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return transaction_func(*args, **kwargs)
            
            except (DeadlockError, sqlite3.OperationalError) as e:
                last_exception = e
                
                if attempt == self.max_retries:
                    logger.error(f"Transaction failed after {self.max_retries} retries: {e}")
                    raise
                
                # Calculate delay with exponential backoff
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                
                logger.warning(f"Transaction attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s")
                time.sleep(delay)
            
            except Exception as e:
                # Don't retry for non-transient errors
                logger.error(f"Non-retryable transaction error: {e}")
                raise
        
        raise last_exception

# Utility functions for transaction management
def create_transaction_manager(database_path: str = None) -> TransactionManager:
    """Factory function to create a transaction manager"""
    return TransactionManager(database_path)

def with_transaction(transaction_type: TransactionType, user_id: str = None, 
                    validation_level: ValidationLevel = ValidationLevel.STANDARD):
    """Decorator for automatic transaction management"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            manager = create_transaction_manager()
            try:
                with manager.transaction(transaction_type, user_id, validation_level) as tx:
                    return func(tx, *args, **kwargs)
            finally:
                manager.close()
        return wrapper
    return decorator

# Example usage and testing functions
def example_trading_transaction():
    """Example of how to use the transaction manager for trading operations"""
    manager = TransactionManager()
    
    try:
        with manager.transaction(
            TransactionType.TRADE_EXECUTION, 
            user_id="user123", 
            validation_level=ValidationLevel.STRICT
        ) as tx:
            # Execute trade
            tx.execute(
                "INSERT INTO trades (user_id, symbol, quantity, price, timestamp) VALUES (?, ?, ?, ?, ?)",
                ("user123", "AAPL", 100, 150.50, datetime.now()),
                table_name="trades",
                operation_type="INSERT",
                record_id="trade_001"
            )
            
            # Update portfolio
            tx.execute(
                "UPDATE portfolio SET quantity = quantity + ?, average_price = ? WHERE user_id = ? AND symbol = ?",
                (100, 150.50, "user123", "AAPL"),
                table_name="portfolio",
                operation_type="UPDATE",
                record_id="portfolio_001"
            )
            
            # Update order status
            tx.execute(
                "UPDATE orders SET status = 'filled', filled_quantity = quantity WHERE order_id = ?",
                ("order_001",),
                table_name="orders",
                operation_type="UPDATE",
                record_id="order_001"
            )
            
            logger.info("✅ Trading transaction completed successfully")
    
    except Exception as e:
        logger.error(f"❌ Trading transaction failed: {e}")
        raise
    
    finally:
        manager.close()

def test_transaction_manager():
    """Test function for transaction manager functionality"""
    manager = TransactionManager()
    
    try:
        # Test successful transaction
        with manager.transaction(TransactionType.PORTFOLIO_UPDATE, "test_user") as tx:
            tx.execute("SELECT 1", table_name="test", operation_type="SELECT")
        
        # Test transaction rollback
        try:
            with manager.transaction(TransactionType.ORDER_MANAGEMENT, "test_user") as tx:
                tx.execute("SELECT 1", table_name="test", operation_type="SELECT")
                raise Exception("Intentional error for rollback test")
        except Exception:
            pass  # Expected
        
        # Test validation levels
        with manager.transaction(
            TransactionType.STRATEGY_OPERATION, 
            "test_user", 
            ValidationLevel.PARANOID
        ) as tx:
            tx.execute("SELECT 1", table_name="test", operation_type="SELECT")
        
        # Get transaction history
        history = manager.get_transaction_history(user_id="test_user", limit=10)
        logger.info(f"Transaction history: {len(history)} transactions")
        
        # Generate integrity report
        report = manager.get_data_integrity_report()
        logger.info(f"Data integrity report: {report.get('timestamp', 'N/A')}")
        
        logger.info("✅ Transaction manager tests completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Transaction manager test failed: {e}")
        raise
    
    finally:
        manager.close()

if __name__ == "__main__":
    # Run example and tests
    print("🔄 Testing Transaction Management System...")
    
    try:
        test_transaction_manager()
        print("✅ All transaction manager tests passed!")
        
        print("\n🔄 Running example trading transaction...")
        example_trading_transaction()
        print("✅ Example trading transaction completed!")
        
    except Exception as e:
        print(f"❌ Transaction management system test failed: {e}")
        import traceback
        traceback.print_exc()