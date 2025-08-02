#!/usr/bin/env python3
"""
Data Validation and Consistency Checking System
Provides comprehensive data validation, business rule enforcement, and consistency monitoring
"""

import os
import sqlite3
import logging
import json
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from decimal import Decimal, InvalidOperation
import re
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ValidationSeverity(Enum):
    """Validation severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ValidationCategory(Enum):
    """Validation rule categories"""
    DATA_TYPE = "data_type"
    RANGE = "range"
    FORMAT = "format"
    BUSINESS_RULE = "business_rule"
    REFERENTIAL_INTEGRITY = "referential_integrity"
    CONSISTENCY = "consistency"
    TEMPORAL = "temporal"
    FINANCIAL = "financial"

class ValidationStatus(Enum):
    """Validation execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ValidationRule:
    """Data validation rule definition"""
    rule_id: str
    name: str
    description: str
    category: ValidationCategory
    severity: ValidationSeverity
    table_name: str
    column_name: Optional[str] = None
    condition: str = ""
    expected_value: Optional[Any] = None
    error_message: str = ""
    repair_action: Optional[str] = None
    is_active: bool = True
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class ValidationResult:
    """Validation result for a specific rule"""
    rule_id: str
    rule_name: str
    status: ValidationStatus
    severity: ValidationSeverity
    violations_count: int = 0
    violations_details: List[Dict[str, Any]] = None
    execution_time: float = 0.0
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.violations_details is None:
            self.violations_details = []
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class ConsistencyCheck:
    """Cross-table consistency check definition"""
    check_id: str
    name: str
    description: str
    tables: List[str]
    check_query: str
    expected_result: Any
    severity: ValidationSeverity
    repair_query: Optional[str] = None
    is_active: bool = True

class DataValidator:
    """Comprehensive data validation and consistency checking system"""
    
    def __init__(self, database_path: str = None):
        self.database_path = database_path or os.getenv("DATABASE_PATH", "trading_validation.db")
        self.connection = None
        self.validation_rules: Dict[str, ValidationRule] = {}
        self.consistency_checks: Dict[str, ConsistencyCheck] = {}
        self.lock = threading.RLock()
        self._initialize_validation_system()
        self._load_predefined_rules()
        self._load_consistency_checks()
    
    def _initialize_validation_system(self):
        """Initialize validation system database tables"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Create validation rules table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS validation_rules (
                    rule_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    category TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    table_name TEXT NOT NULL,
                    column_name TEXT,
                    condition TEXT,
                    expected_value TEXT,
                    error_message TEXT,
                    repair_action TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    CHECK (category IN ('data_type', 'range', 'format', 'business_rule', 'referential_integrity', 'consistency', 'temporal', 'financial')),
                    CHECK (severity IN ('info', 'warning', 'error', 'critical'))
                )
            """)
            
            # Create validation results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS validation_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_id TEXT NOT NULL,
                    rule_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    violations_count INTEGER DEFAULT 0,
                    violations_details TEXT, -- JSON array
                    execution_time REAL DEFAULT 0.0,
                    error_message TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (rule_id) REFERENCES validation_rules(rule_id),
                    CHECK (status IN ('pending', 'running', 'completed', 'failed')),
                    CHECK (severity IN ('info', 'warning', 'error', 'critical'))
                )
            """)
            
            # Create consistency checks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS consistency_checks (
                    check_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    tables TEXT NOT NULL, -- JSON array
                    check_query TEXT NOT NULL,
                    expected_result TEXT,
                    severity TEXT NOT NULL,
                    repair_query TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    CHECK (severity IN ('info', 'warning', 'error', 'critical'))
                )
            """)
            
            # Create data quality metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS data_quality_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    table_name TEXT,
                    column_name TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    details TEXT -- JSON object
                )
            """)
            
            # Create data repair log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS data_repair_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_id TEXT NOT NULL,
                    repair_action TEXT NOT NULL,
                    affected_records INTEGER DEFAULT 0,
                    success BOOLEAN DEFAULT 0,
                    error_message TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (rule_id) REFERENCES validation_rules(rule_id)
                )
            """)
            
            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_validation_results_rule_id ON validation_results(rule_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_validation_results_timestamp ON validation_results(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_validation_results_severity ON validation_results(severity)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_data_quality_metrics_table ON data_quality_metrics(table_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_data_quality_metrics_timestamp ON data_quality_metrics(timestamp)")
            
            conn.commit()
            logger.info("✅ Data validation system initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize validation system: {e}")
            raise
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with optimal settings"""
        if self.connection is None:
            self.connection = sqlite3.connect(
                self.database_path,
                check_same_thread=False,
                isolation_level=None
            )
            
            # Configure for optimal performance
            cursor = self.connection.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("PRAGMA journal_mode = WAL")
            cursor.execute("PRAGMA synchronous = NORMAL")
            cursor.execute("PRAGMA cache_size = -16000")  # 16MB cache
            cursor.execute("PRAGMA temp_store = memory")
            
        return self.connection
    
    def _load_predefined_rules(self):
        """Load predefined validation rules for trading system"""
        predefined_rules = [
            # User validation rules
            ValidationRule(
                rule_id="user_balance_non_negative",
                name="User Balance Non-Negative",
                description="User account balance should not be negative beyond credit limit",
                category=ValidationCategory.BUSINESS_RULE,
                severity=ValidationSeverity.ERROR,
                table_name="users",
                column_name="balance",
                condition="balance >= COALESCE(credit_limit, 0) * -1",
                error_message="User balance exceeds credit limit"
            ),
            
            ValidationRule(
                rule_id="user_email_format",
                name="User Email Format",
                description="User email should be in valid format",
                category=ValidationCategory.FORMAT,
                severity=ValidationSeverity.ERROR,
                table_name="users",
                column_name="email",
                condition="email REGEXP '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'",
                error_message="Invalid email format"
            ),
            
            ValidationRule(
                rule_id="user_risk_limits_positive",
                name="User Risk Limits Positive",
                description="User risk limits should be positive values",
                category=ValidationCategory.RANGE,
                severity=ValidationSeverity.ERROR,
                table_name="users",
                condition="max_position_size > 0 AND max_daily_loss > 0",
                error_message="Risk limits must be positive"
            ),
            
            # Portfolio validation rules
            ValidationRule(
                rule_id="portfolio_quantity_non_negative",
                name="Portfolio Quantity Non-Negative",
                description="Portfolio quantity cannot be negative",
                category=ValidationCategory.RANGE,
                severity=ValidationSeverity.ERROR,
                table_name="portfolio",
                column_name="quantity",
                condition="quantity >= 0",
                error_message="Portfolio quantity cannot be negative",
                repair_action="UPDATE portfolio SET quantity = 0 WHERE quantity < 0"
            ),
            
            ValidationRule(
                rule_id="portfolio_price_positive",
                name="Portfolio Price Positive",
                description="Portfolio average price must be positive when quantity > 0",
                category=ValidationCategory.BUSINESS_RULE,
                severity=ValidationSeverity.ERROR,
                table_name="portfolio",
                condition="(quantity = 0) OR (quantity > 0 AND average_price > 0)",
                error_message="Average price must be positive when holding positions"
            ),
            
            ValidationRule(
                rule_id="portfolio_market_value_calculation",
                name="Portfolio Market Value Calculation",
                description="Market value should equal quantity * current_price",
                category=ValidationCategory.CONSISTENCY,
                severity=ValidationSeverity.WARNING,
                table_name="portfolio",
                condition="ABS(market_value - (quantity * current_price)) < 0.01",
                error_message="Market value calculation inconsistent",
                repair_action="UPDATE portfolio SET market_value = quantity * current_price WHERE ABS(market_value - (quantity * current_price)) >= 0.01"
            ),
            
            # Order validation rules
            ValidationRule(
                rule_id="order_quantity_positive",
                name="Order Quantity Positive",
                description="Order quantity must be positive",
                category=ValidationCategory.RANGE,
                severity=ValidationSeverity.ERROR,
                table_name="orders",
                column_name="quantity",
                condition="quantity > 0",
                error_message="Order quantity must be positive"
            ),
            
            ValidationRule(
                rule_id="order_price_positive",
                name="Order Price Positive",
                description="Order price must be positive",
                category=ValidationCategory.RANGE,
                severity=ValidationSeverity.ERROR,
                table_name="orders",
                column_name="price",
                condition="price > 0",
                error_message="Order price must be positive"
            ),
            
            ValidationRule(
                rule_id="order_filled_quantity_valid",
                name="Order Filled Quantity Valid",
                description="Filled quantity cannot exceed order quantity",
                category=ValidationCategory.BUSINESS_RULE,
                severity=ValidationSeverity.ERROR,
                table_name="orders",
                condition="filled_quantity <= quantity",
                error_message="Filled quantity cannot exceed order quantity"
            ),
            
            ValidationRule(
                rule_id="order_remaining_quantity_calculation",
                name="Order Remaining Quantity Calculation",
                description="Remaining quantity should equal quantity - filled_quantity",
                category=ValidationCategory.CONSISTENCY,
                severity=ValidationSeverity.WARNING,
                table_name="orders",
                condition="remaining_quantity = (quantity - filled_quantity)",
                error_message="Remaining quantity calculation incorrect",
                repair_action="UPDATE orders SET remaining_quantity = quantity - filled_quantity WHERE remaining_quantity != (quantity - filled_quantity)"
            ),
            
            ValidationRule(
                rule_id="order_status_consistency",
                name="Order Status Consistency",
                description="Order status should be consistent with filled quantity",
                category=ValidationCategory.BUSINESS_RULE,
                severity=ValidationSeverity.WARNING,
                table_name="orders",
                condition="""
                    (status = 'pending' AND filled_quantity = 0) OR
                    (status = 'partial' AND filled_quantity > 0 AND filled_quantity < quantity) OR
                    (status = 'filled' AND filled_quantity = quantity) OR
                    (status IN ('cancelled', 'rejected'))
                """,
                error_message="Order status inconsistent with filled quantity"
            ),
            
            # Trade validation rules
            ValidationRule(
                rule_id="trade_positive_values",
                name="Trade Positive Values",
                description="Trade quantity and price must be positive",
                category=ValidationCategory.RANGE,
                severity=ValidationSeverity.ERROR,
                table_name="trades",
                condition="quantity > 0 AND price > 0",
                error_message="Trade quantity and price must be positive"
            ),
            
            ValidationRule(
                rule_id="trade_value_calculation",
                name="Trade Value Calculation",
                description="Trade value should equal quantity * price",
                category=ValidationCategory.CONSISTENCY,
                severity=ValidationSeverity.ERROR,
                table_name="trades",
                condition="ABS(value - (quantity * price)) < 0.01",
                error_message="Trade value calculation incorrect",
                repair_action="UPDATE trades SET value = quantity * price WHERE ABS(value - (quantity * price)) >= 0.01"
            ),
            
            ValidationRule(
                rule_id="trade_commission_non_negative",
                name="Trade Commission Non-Negative",
                description="Trade commission cannot be negative",
                category=ValidationCategory.RANGE,
                severity=ValidationSeverity.ERROR,
                table_name="trades",
                column_name="commission",
                condition="commission >= 0",
                error_message="Trade commission cannot be negative"
            ),
            
            ValidationRule(
                rule_id="trade_timestamp_recent",
                name="Trade Timestamp Recent",
                description="Trade timestamp should be within reasonable time range",
                category=ValidationCategory.TEMPORAL,
                severity=ValidationSeverity.WARNING,
                table_name="trades",
                column_name="timestamp",
                condition="timestamp >= datetime('now', '-1 year') AND timestamp <= datetime('now', '+1 hour')",
                error_message="Trade timestamp outside reasonable range"
            ),
            
            # Strategy validation rules
            ValidationRule(
                rule_id="strategy_performance_metrics",
                name="Strategy Performance Metrics",
                description="Strategy performance metrics should be within valid ranges",
                category=ValidationCategory.RANGE,
                severity=ValidationSeverity.WARNING,
                table_name="strategies",
                condition="win_rate >= 0 AND win_rate <= 100 AND sharpe_ratio >= -5 AND sharpe_ratio <= 10",
                error_message="Strategy performance metrics outside valid ranges"
            ),
            
            ValidationRule(
                rule_id="strategy_risk_limits",
                name="Strategy Risk Limits",
                description="Strategy risk limits should be positive",
                category=ValidationCategory.RANGE,
                severity=ValidationSeverity.ERROR,
                table_name="strategies",
                condition="max_position_size > 0 AND max_daily_loss > 0",
                error_message="Strategy risk limits must be positive"
            ),
            
            # Market data validation rules
            ValidationRule(
                rule_id="market_data_price_positive",
                name="Market Data Price Positive",
                description="Market data prices should be positive",
                category=ValidationCategory.RANGE,
                severity=ValidationSeverity.ERROR,
                table_name="market_data",
                condition="open_price > 0 AND high_price > 0 AND low_price > 0 AND close_price > 0",
                error_message="Market data prices must be positive"
            ),
            
            ValidationRule(
                rule_id="market_data_ohlc_consistency",
                name="Market Data OHLC Consistency",
                description="OHLC data should be consistent (high >= low, etc.)",
                category=ValidationCategory.CONSISTENCY,
                severity=ValidationSeverity.ERROR,
                table_name="market_data",
                condition="high_price >= low_price AND high_price >= open_price AND high_price >= close_price AND low_price <= open_price AND low_price <= close_price",
                error_message="OHLC data inconsistent"
            ),
            
            ValidationRule(
                rule_id="market_data_volume_non_negative",
                name="Market Data Volume Non-Negative",
                description="Trading volume cannot be negative",
                category=ValidationCategory.RANGE,
                severity=ValidationSeverity.ERROR,
                table_name="market_data",
                column_name="volume",
                condition="volume >= 0",
                error_message="Trading volume cannot be negative"
            )
        ]
        
        # Store rules in memory
        for rule in predefined_rules:
            self.validation_rules[rule.rule_id] = rule
        
        # Persist rules to database
        self._persist_validation_rules(predefined_rules)
        
        logger.info(f"✅ Loaded {len(predefined_rules)} predefined validation rules")
    
    def _load_consistency_checks(self):
        """Load predefined consistency checks"""
        consistency_checks = [
            ConsistencyCheck(
                check_id="portfolio_trade_consistency",
                name="Portfolio-Trade Consistency",
                description="Portfolio quantities should match cumulative trade quantities",
                tables=["portfolio", "trades"],
                check_query="""
                    SELECT p.user_id, p.symbol, p.quantity as portfolio_qty,
                           COALESCE(SUM(CASE WHEN t.side = 'buy' THEN t.quantity ELSE -t.quantity END), 0) as trade_qty
                    FROM portfolio p
                    LEFT JOIN trades t ON p.user_id = t.user_id AND p.symbol = t.symbol
                    GROUP BY p.user_id, p.symbol
                    HAVING ABS(p.quantity - COALESCE(SUM(CASE WHEN t.side = 'buy' THEN t.quantity ELSE -t.quantity END), 0)) > 0.001
                """,
                expected_result=0,  # Should return no rows
                severity=ValidationSeverity.ERROR,
                repair_query="""
                    UPDATE portfolio SET quantity = (
                        SELECT COALESCE(SUM(CASE WHEN t.side = 'buy' THEN t.quantity ELSE -t.quantity END), 0)
                        FROM trades t 
                        WHERE t.user_id = portfolio.user_id AND t.symbol = portfolio.symbol
                    )
                """
            ),
            
            ConsistencyCheck(
                check_id="order_trade_consistency",
                name="Order-Trade Consistency",
                description="Order filled quantities should match sum of related trades",
                tables=["orders", "trades"],
                check_query="""
                    SELECT o.order_id, o.filled_quantity as order_filled,
                           COALESCE(SUM(t.quantity), 0) as trade_total
                    FROM orders o
                    LEFT JOIN trades t ON o.order_id = t.order_id
                    GROUP BY o.order_id, o.filled_quantity
                    HAVING ABS(o.filled_quantity - COALESCE(SUM(t.quantity), 0)) > 0.001
                """,
                expected_result=0,
                severity=ValidationSeverity.ERROR
            ),
            
            ConsistencyCheck(
                check_id="user_balance_consistency",
                name="User Balance Consistency",
                description="User balance should reflect all transactions",
                tables=["users", "trades", "deposits", "withdrawals"],
                check_query="""
                    SELECT u.user_id, u.balance as current_balance,
                           (u.initial_balance + 
                            COALESCE(SUM(d.amount), 0) - 
                            COALESCE(SUM(w.amount), 0) - 
                            COALESCE(SUM(t.value + t.commission), 0)) as calculated_balance
                    FROM users u
                    LEFT JOIN deposits d ON u.user_id = d.user_id
                    LEFT JOIN withdrawals w ON u.user_id = w.user_id
                    LEFT JOIN trades t ON u.user_id = t.user_id
                    GROUP BY u.user_id, u.balance, u.initial_balance
                    HAVING ABS(u.balance - (u.initial_balance + 
                                           COALESCE(SUM(d.amount), 0) - 
                                           COALESCE(SUM(w.amount), 0) - 
                                           COALESCE(SUM(t.value + t.commission), 0))) > 0.01
                """,
                expected_result=0,
                severity=ValidationSeverity.CRITICAL
            ),
            
            ConsistencyCheck(
                check_id="referential_integrity_users_portfolio",
                name="Referential Integrity: Users-Portfolio",
                description="All portfolio records should have valid user references",
                tables=["portfolio", "users"],
                check_query="""
                    SELECT p.user_id, COUNT(*) as orphaned_records
                    FROM portfolio p
                    LEFT JOIN users u ON p.user_id = u.user_id
                    WHERE u.user_id IS NULL
                    GROUP BY p.user_id
                """,
                expected_result=0,
                severity=ValidationSeverity.ERROR
            ),
            
            ConsistencyCheck(
                check_id="referential_integrity_trades_orders",
                name="Referential Integrity: Trades-Orders",
                description="All trades should have valid order references",
                tables=["trades", "orders"],
                check_query="""
                    SELECT t.order_id, COUNT(*) as orphaned_trades
                    FROM trades t
                    LEFT JOIN orders o ON t.order_id = o.order_id
                    WHERE o.order_id IS NULL
                    GROUP BY t.order_id
                """,
                expected_result=0,
                severity=ValidationSeverity.ERROR
            ),
            
            ConsistencyCheck(
                check_id="temporal_consistency_orders_trades",
                name="Temporal Consistency: Orders-Trades",
                description="Trade timestamps should be after order creation",
                tables=["orders", "trades"],
                check_query="""
                    SELECT t.trade_id, o.created_at as order_time, t.timestamp as trade_time
                    FROM trades t
                    JOIN orders o ON t.order_id = o.order_id
                    WHERE t.timestamp < o.created_at
                """,
                expected_result=0,
                severity=ValidationSeverity.WARNING
            )
        ]
        
        # Store checks in memory
        for check in consistency_checks:
            self.consistency_checks[check.check_id] = check
        
        # Persist checks to database
        self._persist_consistency_checks(consistency_checks)
        
        logger.info(f"✅ Loaded {len(consistency_checks)} consistency checks")
    
    def _persist_validation_rules(self, rules: List[ValidationRule]):
        """Persist validation rules to database"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            for rule in rules:
                cursor.execute("""
                    INSERT OR REPLACE INTO validation_rules 
                    (rule_id, name, description, category, severity, table_name, column_name, 
                     condition, expected_value, error_message, repair_action, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rule.rule_id, rule.name, rule.description, rule.category.value,
                    rule.severity.value, rule.table_name, rule.column_name,
                    rule.condition, str(rule.expected_value) if rule.expected_value else None,
                    rule.error_message, rule.repair_action, rule.is_active
                ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to persist validation rules: {e}")
            raise
    
    def _persist_consistency_checks(self, checks: List[ConsistencyCheck]):
        """Persist consistency checks to database"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            for check in checks:
                cursor.execute("""
                    INSERT OR REPLACE INTO consistency_checks 
                    (check_id, name, description, tables, check_query, expected_result, severity, repair_query, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    check.check_id, check.name, check.description, json.dumps(check.tables),
                    check.check_query, str(check.expected_result), check.severity.value,
                    check.repair_query, check.is_active
                ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to persist consistency checks: {e}")
            raise
    
    def validate_single_rule(self, rule_id: str) -> ValidationResult:
        """Execute a single validation rule"""
        if rule_id not in self.validation_rules:
            raise ValueError(f"Validation rule '{rule_id}' not found")
        
        rule = self.validation_rules[rule_id]
        start_time = time.time()
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Build validation query
            if rule.column_name:
                # Column-specific validation
                query = f"""
                    SELECT rowid, {rule.column_name}
                    FROM {rule.table_name}
                    WHERE NOT ({rule.condition})
                """
            else:
                # Table-level validation
                query = f"""
                    SELECT rowid, *
                    FROM {rule.table_name}
                    WHERE NOT ({rule.condition})
                """
            
            cursor.execute(query)
            violations = cursor.fetchall()
            
            # Process violations
            violations_details = []
            for violation in violations:
                violation_detail = {
                    "rowid": violation[0],
                    "values": violation[1:] if len(violation) > 1 else None,
                    "timestamp": datetime.now().isoformat()
                }
                violations_details.append(violation_detail)
            
            execution_time = time.time() - start_time
            
            result = ValidationResult(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                status=ValidationStatus.COMPLETED,
                severity=rule.severity,
                violations_count=len(violations),
                violations_details=violations_details,
                execution_time=execution_time
            )
            
            # Log result to database
            self._log_validation_result(result)
            
            if violations:
                logger.warning(f"⚠️ Validation rule '{rule.name}' found {len(violations)} violations")
            else:
                logger.info(f"✅ Validation rule '{rule.name}' passed")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            result = ValidationResult(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                status=ValidationStatus.FAILED,
                severity=rule.severity,
                execution_time=execution_time,
                error_message=str(e)
            )
            
            self._log_validation_result(result)
            logger.error(f"❌ Validation rule '{rule.name}' failed: {e}")
            
            return result
    
    def validate_all_rules(self, severity_filter: ValidationSeverity = None) -> Dict[str, ValidationResult]:
        """Execute all active validation rules"""
        results = {}
        
        rules_to_validate = [
            rule for rule in self.validation_rules.values()
            if rule.is_active and (severity_filter is None or rule.severity == severity_filter)
        ]
        
        logger.info(f"🔄 Running {len(rules_to_validate)} validation rules...")
        
        for rule in rules_to_validate:
            try:
                result = self.validate_single_rule(rule.rule_id)
                results[rule.rule_id] = result
            except Exception as e:
                logger.error(f"Failed to execute rule '{rule.rule_id}': {e}")
                results[rule.rule_id] = ValidationResult(
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    status=ValidationStatus.FAILED,
                    severity=rule.severity,
                    error_message=str(e)
                )
        
        return results
    
    def check_consistency(self, check_id: str = None) -> Dict[str, Any]:
        """Execute consistency checks"""
        if check_id:
            if check_id not in self.consistency_checks:
                raise ValueError(f"Consistency check '{check_id}' not found")
            checks_to_run = [self.consistency_checks[check_id]]
        else:
            checks_to_run = [check for check in self.consistency_checks.values() if check.is_active]
        
        results = {}
        
        logger.info(f"🔄 Running {len(checks_to_run)} consistency checks...")
        
        for check in checks_to_run:
            try:
                start_time = time.time()
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute(check.check_query)
                inconsistencies = cursor.fetchall()
                
                execution_time = time.time() - start_time
                
                result = {
                    "check_id": check.check_id,
                    "name": check.name,
                    "status": "completed",
                    "severity": check.severity.value,
                    "inconsistencies_count": len(inconsistencies),
                    "inconsistencies": inconsistencies,
                    "execution_time": execution_time,
                    "timestamp": datetime.now().isoformat()
                }
                
                if inconsistencies:
                    logger.warning(f"⚠️ Consistency check '{check.name}' found {len(inconsistencies)} inconsistencies")
                else:
                    logger.info(f"✅ Consistency check '{check.name}' passed")
                
                results[check.check_id] = result
                
            except Exception as e:
                logger.error(f"❌ Consistency check '{check.name}' failed: {e}")
                results[check.check_id] = {
                    "check_id": check.check_id,
                    "name": check.name,
                    "status": "failed",
                    "error_message": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        
        return results
    
    def repair_data(self, rule_id: str, dry_run: bool = True) -> Dict[str, Any]:
        """Attempt to repair data violations"""
        if rule_id not in self.validation_rules:
            raise ValueError(f"Validation rule '{rule_id}' not found")
        
        rule = self.validation_rules[rule_id]
        
        if not rule.repair_action:
            return {
                "success": False,
                "message": f"No repair action defined for rule '{rule.name}'"
            }
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if dry_run:
                # Simulate repair to count affected records
                # This is a simplified approach - in practice, you'd want more sophisticated dry-run logic
                cursor.execute(f"""
                    SELECT COUNT(*) FROM {rule.table_name} WHERE NOT ({rule.condition})
                """)
                affected_count = cursor.fetchone()[0]
                
                return {
                    "success": True,
                    "dry_run": True,
                    "affected_records": affected_count,
                    "repair_action": rule.repair_action,
                    "message": f"Dry run: {affected_count} records would be affected"
                }
            else:
                # Execute actual repair
                cursor.execute(rule.repair_action)
                affected_count = cursor.rowcount
                conn.commit()
                
                # Log repair action
                self._log_repair_action(rule_id, rule.repair_action, affected_count, True)
                
                logger.info(f"✅ Repaired {affected_count} records for rule '{rule.name}'")
                
                return {
                    "success": True,
                    "dry_run": False,
                    "affected_records": affected_count,
                    "repair_action": rule.repair_action,
                    "message": f"Successfully repaired {affected_count} records"
                }
                
        except Exception as e:
            # Log failed repair
            self._log_repair_action(rule_id, rule.repair_action, 0, False, str(e))
            
            logger.error(f"❌ Failed to repair data for rule '{rule.name}': {e}")
            
            return {
                "success": False,
                "error_message": str(e),
                "message": f"Failed to repair data: {e}"
            }
    
    def _log_validation_result(self, result: ValidationResult):
        """Log validation result to database"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO validation_results 
                (rule_id, rule_name, status, severity, violations_count, violations_details, 
                 execution_time, error_message, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.rule_id, result.rule_name, result.status.value, result.severity.value,
                result.violations_count, json.dumps(result.violations_details) if result.violations_details else None,
                result.execution_time, result.error_message, result.timestamp
            ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to log validation result: {e}")
    
    def _log_repair_action(self, rule_id: str, repair_action: str, affected_records: int, 
                          success: bool, error_message: str = None):
        """Log data repair action"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO data_repair_log 
                (rule_id, repair_action, affected_records, success, error_message)
                VALUES (?, ?, ?, ?, ?)
            """, (rule_id, repair_action, affected_records, success, error_message))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to log repair action: {e}")
    
    def calculate_data_quality_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive data quality metrics"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "overall_score": 0.0,
                "table_metrics": {},
                "rule_compliance": {},
                "consistency_score": 0.0,
                "recommendations": []
            }
            
            # Get table-level metrics
            tables = ["users", "portfolio", "orders", "trades", "strategies", "market_data"]
            
            for table in tables:
                try:
                    # Count total records
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    total_records = cursor.fetchone()[0]
                    
                    if total_records == 0:
                        continue
                    
                    # Count null values in key columns
                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = cursor.fetchall()
                    
                    null_counts = {}
                    for column in columns:
                        column_name = column[1]
                        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {column_name} IS NULL")
                        null_count = cursor.fetchone()[0]
                        null_counts[column_name] = null_count
                    
                    # Calculate completeness score
                    total_cells = total_records * len(columns)
                    total_nulls = sum(null_counts.values())
                    completeness_score = ((total_cells - total_nulls) / total_cells) * 100 if total_cells > 0 else 100
                    
                    metrics["table_metrics"][table] = {
                        "total_records": total_records,
                        "completeness_score": round(completeness_score, 2),
                        "null_counts": null_counts
                    }
                    
                except Exception as e:
                    logger.warning(f"Failed to calculate metrics for table {table}: {e}")
            
            # Calculate rule compliance
            validation_results = self.validate_all_rules()
            total_rules = len(validation_results)
            passed_rules = sum(1 for result in validation_results.values() if result.violations_count == 0)
            
            rule_compliance_score = (passed_rules / total_rules) * 100 if total_rules > 0 else 100
            metrics["rule_compliance"] = {
                "total_rules": total_rules,
                "passed_rules": passed_rules,
                "compliance_score": round(rule_compliance_score, 2),
                "violations_by_severity": {}
            }
            
            # Group violations by severity
            for severity in ValidationSeverity:
                violations = sum(
                    result.violations_count for result in validation_results.values()
                    if result.severity == severity
                )
                metrics["rule_compliance"]["violations_by_severity"][severity.value] = violations
            
            # Calculate consistency score
            consistency_results = self.check_consistency()
            total_checks = len(consistency_results)
            passed_checks = sum(1 for result in consistency_results.values() if result.get("inconsistencies_count", 0) == 0)
            
            consistency_score = (passed_checks / total_checks) * 100 if total_checks > 0 else 100
            metrics["consistency_score"] = round(consistency_score, 2)
            
            # Calculate overall score (weighted average)
            overall_score = (
                rule_compliance_score * 0.4 +
                consistency_score * 0.3 +
                sum(table_metrics.get("completeness_score", 0) for table_metrics in metrics["table_metrics"].values()) / len(metrics["table_metrics"]) * 0.3
            ) if metrics["table_metrics"] else (rule_compliance_score * 0.7 + consistency_score * 0.3)
            
            metrics["overall_score"] = round(overall_score, 2)
            
            # Generate recommendations
            if overall_score < 80:
                metrics["recommendations"].append("Overall data quality is below acceptable threshold (80%)")
            
            if rule_compliance_score < 90:
                metrics["recommendations"].append("Multiple validation rule violations detected - review and fix data issues")
            
            if consistency_score < 95:
                metrics["recommendations"].append("Data consistency issues found - run consistency checks and repairs")
            
            for table, table_metrics in metrics["table_metrics"].items():
                if table_metrics["completeness_score"] < 95:
                    metrics["recommendations"].append(f"Table '{table}' has data completeness issues")
            
            if not metrics["recommendations"]:
                metrics["recommendations"].append("Data quality is excellent - no immediate action required")
            
            # Store metrics in database
            self._store_quality_metrics(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to calculate data quality metrics: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _store_quality_metrics(self, metrics: Dict[str, Any]):
        """Store data quality metrics in database"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Store overall metrics
            cursor.execute("""
                INSERT INTO data_quality_metrics 
                (metric_name, metric_value, details)
                VALUES (?, ?, ?)
            """, ("overall_score", metrics["overall_score"], json.dumps(metrics)))
            
            # Store table-specific metrics
            for table, table_metrics in metrics.get("table_metrics", {}).items():
                cursor.execute("""
                    INSERT INTO data_quality_metrics 
                    (metric_name, metric_value, table_name, details)
                    VALUES (?, ?, ?, ?)
                """, ("completeness_score", table_metrics["completeness_score"], table, json.dumps(table_metrics)))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to store quality metrics: {e}")
    
    def get_validation_history(self, rule_id: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get validation history"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = "SELECT * FROM validation_results WHERE 1=1"
            params = []
            
            if rule_id:
                query += " AND rule_id = ?"
                params.append(rule_id)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            
            columns = [description[0] for description in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                result = dict(zip(columns, row))
                # Parse JSON fields
                if result.get('violations_details'):
                    result['violations_details'] = json.loads(result['violations_details'])
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get validation history: {e}")
            return []
    
    def generate_data_quality_report(self) -> Dict[str, Any]:
        """Generate comprehensive data quality report"""
        logger.info("🔄 Generating comprehensive data quality report...")
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {},
            "validation_results": {},
            "consistency_results": {},
            "quality_metrics": {},
            "recommendations": [],
            "repair_suggestions": []
        }
        
        try:
            # Run all validations
            validation_results = self.validate_all_rules()
            report["validation_results"] = {
                rule_id: asdict(result) for rule_id, result in validation_results.items()
            }
            
            # Run consistency checks
            consistency_results = self.check_consistency()
            report["consistency_results"] = consistency_results
            
            # Calculate quality metrics
            quality_metrics = self.calculate_data_quality_metrics()
            report["quality_metrics"] = quality_metrics
            
            # Generate summary
            total_violations = sum(result.violations_count for result in validation_results.values())
            total_inconsistencies = sum(result.get("inconsistencies_count", 0) for result in consistency_results.values())
            
            report["summary"] = {
                "overall_score": quality_metrics.get("overall_score", 0),
                "total_rules_checked": len(validation_results),
                "total_violations": total_violations,
                "total_consistency_checks": len(consistency_results),
                "total_inconsistencies": total_inconsistencies,
                "critical_issues": sum(1 for result in validation_results.values() 
                                     if result.severity == ValidationSeverity.CRITICAL and result.violations_count > 0),
                "error_issues": sum(1 for result in validation_results.values() 
                                  if result.severity == ValidationSeverity.ERROR and result.violations_count > 0),
                "warning_issues": sum(1 for result in validation_results.values() 
                                    if result.severity == ValidationSeverity.WARNING and result.violations_count > 0)
            }
            
            # Generate recommendations
            if total_violations == 0 and total_inconsistencies == 0:
                report["recommendations"].append("✅ Excellent data quality - no issues detected")
            else:
                if report["summary"]["critical_issues"] > 0:
                    report["recommendations"].append("🚨 CRITICAL: Immediate attention required for critical data issues")
                
                if report["summary"]["error_issues"] > 0:
                    report["recommendations"].append("❌ ERROR: Fix data validation errors before proceeding")
                
                if report["summary"]["warning_issues"] > 0:
                    report["recommendations"].append("⚠️ WARNING: Review and address data quality warnings")
                
                if total_inconsistencies > 0:
                    report["recommendations"].append("🔄 CONSISTENCY: Fix data consistency issues")
            
            # Generate repair suggestions
            for rule_id, result in validation_results.items():
                if result.violations_count > 0 and self.validation_rules[rule_id].repair_action:
                    report["repair_suggestions"].append({
                        "rule_id": rule_id,
                        "rule_name": result.rule_name,
                        "violations": result.violations_count,
                        "repair_action": self.validation_rules[rule_id].repair_action,
                        "severity": result.severity.value
                    })
            
            logger.info("✅ Data quality report generated successfully")
            
        except Exception as e:
            logger.error(f"Failed to generate data quality report: {e}")
            report["error"] = str(e)
        
        return report
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Data validator connection closed")

# Utility functions
def create_data_validator(database_path: str = None) -> DataValidator:
    """Factory function to create a data validator"""
    return DataValidator(database_path)

def validate_trading_data(database_path: str = None) -> Dict[str, Any]:
    """Quick validation of trading data"""
    validator = create_data_validator(database_path)
    try:
        return validator.generate_data_quality_report()
    finally:
        validator.close()

# Example usage
if __name__ == "__main__":
    print("🚀 Testing Data Validation and Consistency System...")
    
    try:
        validator = DataValidator()
        
        # Generate comprehensive report
        report = validator.generate_data_quality_report()
        
        print(f"\n📊 Data Quality Report Summary:")
        print(f"Overall Score: {report['summary']['overall_score']:.1f}%")
        print(f"Total Violations: {report['summary']['total_violations']}")
        print(f"Critical Issues: {report['summary']['critical_issues']}")
        print(f"Error Issues: {report['summary']['error_issues']}")
        print(f"Warning Issues: {report['summary']['warning_issues']}")
        
        print(f"\n📋 Recommendations:")
        for recommendation in report['recommendations']:
            print(f"  - {recommendation}")
        
        validator.close()
        print("\n✅ Data validation system test completed!")
        
    except Exception as e:
        print(f"❌ Data validation system test failed: {e}")
        import traceback
        traceback.print_exc()