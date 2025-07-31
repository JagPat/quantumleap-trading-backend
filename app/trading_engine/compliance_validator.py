"""
Trading Engine Compliance Validation System
Provides real-time compliance rule validation and regulatory requirement checking
"""
import json
import logging
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import uuid
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComplianceRuleType(Enum):
    """Types of compliance rules"""
    POSITION_LIMIT = "POSITION_LIMIT"
    CONCENTRATION_LIMIT = "CONCENTRATION_LIMIT"
    TRADING_HOURS = "TRADING_HOURS"
    BEST_EXECUTION = "BEST_EXECUTION"
    MARKET_ABUSE = "MARKET_ABUSE"
    SUITABILITY = "SUITABILITY"
    LIQUIDITY_RISK = "LIQUIDITY_RISK"
    LEVERAGE_LIMIT = "LEVERAGE_LIMIT"
    SECTOR_EXPOSURE = "SECTOR_EXPOSURE"
    INSTRUMENT_RESTRICTION = "INSTRUMENT_RESTRICTION"
    CLIENT_CLASSIFICATION = "CLIENT_CLASSIFICATION"
    TRANSACTION_REPORTING = "TRANSACTION_REPORTING"
    RECORD_KEEPING = "RECORD_KEEPING"
    RISK_DISCLOSURE = "RISK_DISCLOSURE"
    ALGO_TRADING = "ALGO_TRADING"
    PRE_TRADE = "PRE_TRADE"
    POST_TRADE = "POST_TRADE"
    RISK_LIMIT = "RISK_LIMIT"
    REPORTING = "REPORTING"

class ComplianceStatus(Enum):
    """Compliance validation status"""
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    WARNING = "WARNING"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    EXEMPTED = "EXEMPTED"

class RegulatoryFramework(Enum):
    """Regulatory frameworks"""
    MIFID_II = "MIFID_II"
    SEBI = "SEBI"
    SEC = "SEC"
    FCA = "FCA"
    CFTC = "CFTC"
    ESMA = "ESMA"
    RBI = "RBI"
    IOSCO = "IOSCO"

class ViolationSeverity(Enum):
    """Violation severity levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class ComplianceRule:
    """Compliance rule definition"""
    rule_id: str
    name: str
    description: str
    rule_type: ComplianceRuleType
    regulatory_framework: RegulatoryFramework
    severity: ViolationSeverity
    parameters: Dict[str, Any]
    validation_logic: str  # JSON string with validation logic
    remediation_action: str
    enabled: bool = True
    mandatory: bool = True
    effective_date: datetime = None
    expiry_date: datetime = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.effective_date is None:
            self.effective_date = datetime.now()

@dataclass
class ComplianceViolation:
    """Compliance violation record"""
    violation_id: str
    rule_id: str
    user_id: str
    resource_id: str
    violation_type: str
    timestamp: datetime
    severity: ViolationSeverity
    description: str
    current_value: Any
    threshold_value: Any
    context_data: Dict[str, Any]
    remediation_required: bool
    remediation_actions: List[str]
    officer_review_required: bool
    resolved: bool = False
    resolution_timestamp: datetime = None
    resolution_notes: str = ""
    data_snapshot: Dict[str, Any] = None
    detected_at: datetime = None
    
    def __post_init__(self):
        if self.detected_at is None:
            self.detected_at = self.timestamp
        if self.data_snapshot is None:
            self.data_snapshot = self.context_data
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'violation_id': self.violation_id,
            'rule_id': self.rule_id,
            'user_id': self.user_id,
            'resource_id': self.resource_id,
            'violation_type': self.violation_type,
            'timestamp': self.timestamp.isoformat(),
            'severity': self.severity.value,
            'description': self.description,
            'current_value': self.current_value,
            'threshold_value': self.threshold_value,
            'context_data': self.context_data,
            'remediation_required': self.remediation_required,
            'remediation_actions': self.remediation_actions,
            'officer_review_required': self.officer_review_required,
            'resolved': self.resolved,
            'resolution_timestamp': self.resolution_timestamp.isoformat() if self.resolution_timestamp else None,
            'resolution_notes': self.resolution_notes
        }

@dataclass
class ComplianceCheckResult:
    """Result of compliance validation"""
    check_id: str
    rule_id: str
    resource_id: str
    user_id: str = "unknown"
    compliant: bool = True
    violations: List[ComplianceViolation] = None
    warnings: List[str] = None
    timestamp: datetime = None
    execution_time_ms: float = 0.0
    
    def __post_init__(self):
        if self.violations is None:
            self.violations = []
        if self.warnings is None:
            self.warnings = []
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'check_id': self.check_id,
            'rule_id': self.rule_id,
            'resource_id': self.resource_id,
            'user_id': self.user_id,
            'compliant': self.compliant,
            'violations': [v.to_dict() for v in self.violations],
            'warnings': self.warnings,
            'timestamp': self.timestamp.isoformat(),
            'execution_time_ms': self.execution_time_ms
        }

@dataclass
class AuditReport:
    """Structured audit report"""
    report_id: str
    report_type: str
    title: str
    description: str
    reporting_period_start: datetime
    reporting_period_end: datetime
    generated_at: datetime
    generated_by: str
    regulatory_framework: RegulatoryFramework
    sections: List[Dict[str, Any]]
    summary: Dict[str, Any]
    recommendations: List[str]
    status: str = "DRAFT"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'report_id': self.report_id,
            'report_type': self.report_type,
            'title': self.title,
            'description': self.description,
            'reporting_period_start': self.reporting_period_start.isoformat(),
            'reporting_period_end': self.reporting_period_end.isoformat(),
            'generated_at': self.generated_at.isoformat(),
            'generated_by': self.generated_by,
            'regulatory_framework': self.regulatory_framework.value,
            'sections': self.sections,
            'summary': self.summary,
            'recommendations': self.recommendations,
            'status': self.status
        }

class ComplianceRuleEngine:
    """Rule engine for compliance validation"""
    
    def __init__(self):
        self.operators = {
            'gt': lambda x, y: float(x) > float(y),
            'gte': lambda x, y: float(x) >= float(y),
            'lt': lambda x, y: float(x) < float(y),
            'lte': lambda x, y: float(x) <= float(y),
            'eq': lambda x, y: x == y,
            'ne': lambda x, y: x != y,
            'in': lambda x, y: x in y,
            'not_in': lambda x, y: x not in y,
            'contains': lambda x, y: y in str(x),
            'regex': lambda x, y: bool(re.match(y, str(x))),
            'between': lambda x, y: y[0] <= float(x) <= y[1],
            'percentage_of': lambda x, y: (float(x) / float(y[0])) * 100 if y[0] != 0 else 0
        }
    
    def evaluate_rule(self, rule: ComplianceRule, data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a compliance rule against data"""
        try:
            validation_logic = json.loads(rule.validation_logic)
            result = self._evaluate_condition(validation_logic, data)
            
            return {
                'rule_id': rule.rule_id,
                'rule_name': rule.name,
                'rule_type': rule.rule_type.value,
                'regulatory_framework': rule.regulatory_framework.value,
                'compliant': result,
                'mandatory': rule.mandatory,
                'evaluation_data': data,
                'parameters': rule.parameters
            }
            
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.rule_id}: {e}")
            return {
                'rule_id': rule.rule_id,
                'rule_name': rule.name,
                'compliant': False,
                'error': str(e)
            }
    
    def _evaluate_condition(self, condition: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Recursively evaluate condition"""
        if 'and' in condition:
            return all(self._evaluate_condition(c, data) for c in condition['and'])
        
        if 'or' in condition:
            return any(self._evaluate_condition(c, data) for c in condition['or'])
        
        if 'not' in condition:
            return not self._evaluate_condition(condition['not'], data)
        
        # Simple condition
        field = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value')
        
        if not all([field, operator]):
            return False
        
        data_value = self._get_nested_value(data, field)
        if data_value is None:
            return False
        
        op_func = self.operators.get(operator)
        if not op_func:
            return False
        
        return op_func(data_value, value)
    
    def _get_nested_value(self, data: Dict[str, Any], field: str) -> Any:
        """Get nested value from data using dot notation"""
        keys = field.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value

class ComplianceValidator:
    """Main compliance validation system"""
    
    def __init__(self, db_path: str = "compliance.db"):
        self.db_path = db_path
        self.rules: Dict[str, ComplianceRule] = {}
        self.rule_engine = ComplianceRuleEngine()
        self.violation_handlers: Dict[ComplianceRuleType, Callable] = {}
        self.lock = threading.Lock()
        
        # Data retention policies (in days)
        self.retention_policies = {
            'audit_logs': 2555,      # 7 years
            'trade_records': 2555,   # 7 years
            'compliance_checks': 1825, # 5 years
            'violation_records': 2555, # 7 years
            'user_data': 2190,       # 6 years
            'market_data': 365       # 1 year
        }
        
        self._init_database()
        self._load_default_rules()
    
    def _init_database(self):
        """Initialize compliance database"""
        with sqlite3.connect(self.db_path) as conn:
            # Compliance rules table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS compliance_rules (
                    rule_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    rule_type TEXT NOT NULL,
                    regulatory_framework TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    parameters TEXT NOT NULL,
                    validation_logic TEXT NOT NULL,
                    remediation_action TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT 1,
                    mandatory BOOLEAN DEFAULT 1,
                    effective_date TIMESTAMP,
                    expiry_date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Compliance violations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS compliance_violations (
                    violation_id TEXT PRIMARY KEY,
                    rule_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    violation_type TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    severity TEXT NOT NULL,
                    description TEXT NOT NULL,
                    current_value TEXT,
                    threshold_value TEXT,
                    context_data TEXT,
                    remediation_required BOOLEAN DEFAULT 0,
                    remediation_actions TEXT,
                    officer_review_required BOOLEAN DEFAULT 0,
                    resolved BOOLEAN DEFAULT 0,
                    resolution_timestamp TIMESTAMP,
                    resolution_notes TEXT,
                    data_snapshot TEXT,
                    detected_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Compliance checks table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS compliance_checks (
                    check_id TEXT PRIMARY KEY,
                    rule_id TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    compliant BOOLEAN NOT NULL,
                    violations_count INTEGER DEFAULT 0,
                    warnings_count INTEGER DEFAULT 0,
                    timestamp TIMESTAMP NOT NULL,
                    execution_time_ms REAL,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Audit reports table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_reports (
                    report_id TEXT PRIMARY KEY,
                    report_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    reporting_period_start TIMESTAMP NOT NULL,
                    reporting_period_end TIMESTAMP NOT NULL,
                    generated_at TIMESTAMP NOT NULL,
                    generated_by TEXT NOT NULL,
                    regulatory_framework TEXT NOT NULL,
                    sections TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    recommendations TEXT,
                    status TEXT DEFAULT 'DRAFT',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # User compliance profiles
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_compliance_profiles (
                    user_id TEXT PRIMARY KEY,
                    client_classification TEXT NOT NULL,
                    risk_tolerance TEXT NOT NULL,
                    investment_objectives TEXT,
                    regulatory_status TEXT,
                    exemptions TEXT,
                    special_requirements TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_violations_user ON compliance_violations(user_id, timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_violations_rule ON compliance_violations(rule_id, timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_checks_resource ON compliance_checks(resource_id, timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_checks_user ON compliance_checks(user_id, timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_rules_type ON compliance_rules(rule_type, enabled)"
            ]
            
            for index_sql in indexes:
                conn.execute(index_sql)
    
    def _load_default_rules(self):
        """Load default compliance rules"""
        default_rules = [
            # Position Limit Rules
            ComplianceRule(
                rule_id="pos_limit_single_stock",
                name="Single Stock Position Limit",
                description="Maximum position size in a single stock",
                rule_type=ComplianceRuleType.POSITION_LIMIT,
                regulatory_framework=RegulatoryFramework.SEBI,
                severity=ViolationSeverity.HIGH,
                parameters={"max_position_percent": 5.0},
                validation_logic=json.dumps({
                    "field": "position_size_percent",
                    "operator": "lte",
                    "value": 5.0
                }),
                remediation_action="Reduce position size to comply with limit"
            ),
            
            # Concentration Limit Rules
            ComplianceRule(
                rule_id="concentration_sector",
                name="Sector Concentration Limit",
                description="Maximum exposure to a single sector",
                rule_type=ComplianceRuleType.CONCENTRATION_LIMIT,
                regulatory_framework=RegulatoryFramework.SEBI,
                severity=ViolationSeverity.MEDIUM,
                parameters={"max_sector_percent": 25.0},
                validation_logic=json.dumps({
                    "field": "sector_exposure_percent",
                    "operator": "lte",
                    "value": 25.0
                }),
                remediation_action="Diversify portfolio to reduce sector concentration"
            ),
            
            # Best Execution Rules
            ComplianceRule(
                rule_id="best_execution_price",
                name="Best Execution Price Check",
                description="Order price within acceptable range of market price",
                rule_type=ComplianceRuleType.BEST_EXECUTION,
                regulatory_framework=RegulatoryFramework.MIFID_II,
                severity=ViolationSeverity.MEDIUM,
                parameters={"max_deviation_percent": 0.5},
                validation_logic=json.dumps({
                    "field": "price_deviation_percent",
                    "operator": "lte",
                    "value": 0.5
                }),
                remediation_action="Review execution venue and improve execution quality"
            ),
            
            # Leverage Limit Rules
            ComplianceRule(
                rule_id="leverage_limit_retail",
                name="Retail Client Leverage Limit",
                description="Maximum leverage for retail clients",
                rule_type=ComplianceRuleType.LEVERAGE_LIMIT,
                regulatory_framework=RegulatoryFramework.SEBI,
                severity=ViolationSeverity.CRITICAL,
                parameters={"max_leverage": 3.0},
                validation_logic=json.dumps({
                    "field": "leverage_ratio",
                    "operator": "lte",
                    "value": 3.0
                }),
                remediation_action="Reduce leverage by closing positions or adding capital"
            ),
            
            # Risk Management Rules
            ComplianceRule(
                rule_id="risk_concentration",
                name="Portfolio Concentration Risk",
                description="Single security cannot exceed 10% of portfolio",
                rule_type=ComplianceRuleType.RISK_LIMIT,
                regulatory_framework=RegulatoryFramework.SEBI,
                severity=ViolationSeverity.HIGH,
                parameters={"max_concentration_percent": 10.0},
                validation_logic=json.dumps({
                    "field": "security_concentration_percent",
                    "operator": "lte",
                    "value": 10.0
                }),
                remediation_action="Diversify portfolio to reduce concentration"
            ),
            
            # Algorithmic Trading Rules
            ComplianceRule(
                rule_id="algo_trading_risk_controls",
                name="Algorithmic Trading Risk Controls",
                description="Risk controls for algorithmic trading",
                rule_type=ComplianceRuleType.ALGO_TRADING,
                regulatory_framework=RegulatoryFramework.SEBI,
                severity=ViolationSeverity.HIGH,
                parameters={"max_order_value": 1000000, "max_orders_per_second": 10},
                validation_logic=json.dumps({
                    "and": [
                        {"field": "order_value", "operator": "lte", "value": 1000000},
                        {"field": "orders_per_second", "operator": "lte", "value": 10}
                    ]
                }),
                remediation_action="Implement proper risk controls and reduce order frequency"
            )
        ]
        
        for rule in default_rules:
            self.add_rule(rule)
    
    def add_rule(self, rule: ComplianceRule) -> bool:
        """Add a compliance rule"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO compliance_rules
                        (rule_id, name, description, rule_type, regulatory_framework,
                         severity, parameters, validation_logic, remediation_action,
                         enabled, mandatory, effective_date, expiry_date, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        rule.rule_id, rule.name, rule.description,
                        rule.rule_type.value, rule.regulatory_framework.value,
                        rule.severity.value, json.dumps(rule.parameters),
                        rule.validation_logic, rule.remediation_action,
                        rule.enabled, rule.mandatory,
                        rule.effective_date.isoformat() if rule.effective_date else None,
                        rule.expiry_date.isoformat() if rule.expiry_date else None,
                        rule.created_at.isoformat()
                    ))
                
                self.rules[rule.rule_id] = rule
                logger.info(f"Added compliance rule: {rule.name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to add compliance rule: {e}")
            return False
    
    def validate_order(self, order_data: Dict[str, Any]) -> ComplianceCheckResult:
        """Validate order against compliance rules"""
        start_time = datetime.now()
        check_id = str(uuid.uuid4())
        
        # Prepare validation data
        validation_data = {
            **order_data,
            'current_time': datetime.now().strftime('%H:%M'),
            'validation_timestamp': start_time.isoformat()
        }
        
        # Calculate additional metrics if not provided
        if 'price_deviation_percent' not in validation_data:
            order_price = validation_data.get('price', 0)
            market_price = validation_data.get('market_price', order_price)
            if market_price > 0:
                validation_data['price_deviation_percent'] = abs((order_price - market_price) / market_price) * 100
        
        if 'order_value' not in validation_data:
            validation_data['order_value'] = validation_data.get('quantity', 0) * validation_data.get('price', 0)
        
        # Validate against all applicable rules
        violations = []
        warnings = []
        
        applicable_rule_types = [
            ComplianceRuleType.PRE_TRADE,
            ComplianceRuleType.POSITION_LIMIT,
            ComplianceRuleType.RISK_LIMIT,
            ComplianceRuleType.BEST_EXECUTION,
            ComplianceRuleType.ALGO_TRADING
        ]
        
        for rule in self.rules.values():
            if not rule.enabled or rule.rule_type not in applicable_rule_types:
                continue
            
            # Check if rule is currently effective
            now = datetime.now()
            if rule.effective_date and now < rule.effective_date:
                continue
            if rule.expiry_date and now > rule.expiry_date:
                continue
            
            # Evaluate rule
            result = self.rule_engine.evaluate_rule(rule, validation_data)
            
            # Handle non-compliance
            if not result.get('compliant', False):
                violation = ComplianceViolation(
                    violation_id=str(uuid.uuid4()),
                    rule_id=rule.rule_id,
                    user_id=order_data.get('user_id', 'unknown'),
                    resource_id=order_data.get('order_id', 'unknown'),
                    violation_type=rule.rule_type.value,
                    timestamp=datetime.now(),
                    severity=rule.severity,
                    description=f"Order violates {rule.name}: {rule.description}",
                    current_value=validation_data.get(result.get('field', 'unknown'), 'N/A'),
                    threshold_value=rule.parameters,
                    context_data=validation_data,
                    remediation_required=rule.severity in [ViolationSeverity.HIGH, ViolationSeverity.CRITICAL],
                    remediation_actions=[rule.remediation_action],
                    officer_review_required=rule.severity == ViolationSeverity.CRITICAL
                )
                
                if rule.mandatory:
                    violations.append(violation)
                else:
                    warnings.append(f"Non-mandatory rule violation: {rule.name}")
                
                # Log violation
                self._log_violation(violation)
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Create validation result
        result = ComplianceCheckResult(
            check_id=check_id,
            rule_id="order_validation",
            resource_id=order_data.get('order_id', 'unknown'),
            user_id=order_data.get('user_id', 'unknown'),
            compliant=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            timestamp=datetime.now(),
            execution_time_ms=processing_time
        )
        
        # Log compliance check
        self._log_compliance_check(result)
        
        return result
    
    def validate_position(self, position_data: Dict[str, Any]) -> ComplianceCheckResult:
        """Validate position against compliance rules"""
        start_time = datetime.now()
        check_id = str(uuid.uuid4())
        
        # Validate against position-specific rules
        applicable_rule_types = [
            ComplianceRuleType.POSITION_LIMIT,
            ComplianceRuleType.CONCENTRATION_LIMIT,
            ComplianceRuleType.LEVERAGE_LIMIT,
            ComplianceRuleType.SECTOR_EXPOSURE,
            ComplianceRuleType.RISK_LIMIT
        ]
        
        violations = []
        warnings = []
        
        for rule in self.rules.values():
            if not rule.enabled or rule.rule_type not in applicable_rule_types:
                continue
            
            result = self.rule_engine.evaluate_rule(rule, position_data)
            
            if not result.get('compliant', False):
                violation = ComplianceViolation(
                    violation_id=str(uuid.uuid4()),
                    rule_id=rule.rule_id,
                    user_id=position_data.get('user_id', 'unknown'),
                    resource_id=position_data.get('position_id', 'unknown'),
                    violation_type=rule.rule_type.value,
                    timestamp=datetime.now(),
                    severity=rule.severity,
                    description=f"Position violates {rule.name}: {rule.description}",
                    current_value=position_data.get(result.get('field', 'unknown'), 'N/A'),
                    threshold_value=rule.parameters,
                    context_data=position_data,
                    remediation_required=rule.severity in [ViolationSeverity.HIGH, ViolationSeverity.CRITICAL],
                    remediation_actions=[rule.remediation_action],
                    officer_review_required=rule.severity == ViolationSeverity.CRITICAL
                )
                
                if rule.mandatory:
                    violations.append(violation)
                else:
                    warnings.append(f"Position warning: {rule.name}")
                
                self._log_violation(violation)
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        result = ComplianceCheckResult(
            check_id=check_id,
            rule_id="position_validation",
            resource_id=position_data.get('position_id', 'unknown'),
            user_id=position_data.get('user_id', 'unknown'),
            compliant=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            timestamp=datetime.now(),
            execution_time_ms=processing_time
        )
        
        self._log_compliance_check(result)
        return result
    
    def _log_violation(self, violation: ComplianceViolation):
        """Log compliance violation to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO compliance_violations
                    (violation_id, rule_id, user_id, resource_id, violation_type,
                     timestamp, severity, description, current_value, threshold_value,
                     context_data, remediation_required, remediation_actions,
                     officer_review_required, data_snapshot, detected_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    violation.violation_id, violation.rule_id, violation.user_id,
                    violation.resource_id, violation.violation_type,
                    violation.timestamp.isoformat(), violation.severity.value,
                    violation.description, str(violation.current_value),
                    str(violation.threshold_value), json.dumps(violation.context_data),
                    violation.remediation_required, json.dumps(violation.remediation_actions),
                    violation.officer_review_required, json.dumps(violation.data_snapshot),
                    violation.detected_at.isoformat()
                ))
        except Exception as e:
            logger.error(f"Failed to log violation: {e}")
    
    def _log_compliance_check(self, result: ComplianceCheckResult):
        """Log compliance check to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO compliance_checks
                    (check_id, rule_id, resource_id, user_id, compliant,
                     violations_count, warnings_count, timestamp, execution_time_ms, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    result.check_id, result.rule_id, result.resource_id, result.user_id,
                    result.compliant, len(result.violations), len(result.warnings),
                    result.timestamp.isoformat(), result.execution_time_ms,
                    json.dumps(result.to_dict())
                ))
        except Exception as e:
            logger.error(f"Failed to log compliance check: {e}")
    
    def generate_audit_report(self, report_type: str, start_date: datetime, 
                             end_date: datetime, generated_by: str,
                             regulatory_framework: RegulatoryFramework = RegulatoryFramework.SEBI) -> AuditReport:
        """Generate comprehensive audit report"""
        try:
            report_id = str(uuid.uuid4())
            
            # Generate basic sections
            sections = [{
                'title': 'Report Summary',
                'type': 'summary',
                'data': {
                    'report_type': report_type,
                    'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                    'generated_at': datetime.now().isoformat(),
                    'regulatory_framework': regulatory_framework.value
                }
            }]
            
            # Generate summary and recommendations
            summary = {
                'total_sections': len(sections),
                'generated_at': datetime.now().isoformat(),
                'status': 'GENERATED'
            }
            
            recommendations = [
                'Continue monitoring compliance metrics',
                'Regular review of compliance procedures',
                'Maintain comprehensive audit trails'
            ]
            
            report = AuditReport(
                report_id=report_id,
                report_type=report_type,
                title=f"{report_type} Report",
                description=f"Compliance report for period {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                reporting_period_start=start_date,
                reporting_period_end=end_date,
                generated_at=datetime.now(),
                generated_by=generated_by,
                regulatory_framework=regulatory_framework,
                sections=sections,
                summary=summary,
                recommendations=recommendations,
                status="GENERATED"
            )
            
            # Save report to database
            self._save_audit_report(report)
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate audit report: {e}")
            raise
    
    def _save_audit_report(self, report: AuditReport):
        """Save audit report to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO audit_reports
                    (report_id, report_type, title, description, reporting_period_start,
                     reporting_period_end, generated_at, generated_by, regulatory_framework,
                     sections, summary, recommendations, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    report.report_id, report.report_type, report.title, report.description,
                    report.reporting_period_start.isoformat(),
                    report.reporting_period_end.isoformat(),
                    report.generated_at.isoformat(), report.generated_by,
                    report.regulatory_framework.value, json.dumps(report.sections),
                    json.dumps(report.summary), json.dumps(report.recommendations),
                    report.status
                ))
        except Exception as e:
            logger.error(f"Failed to save audit report: {e}")
    
    def get_compliance_status(self, user_id: Optional[str] = None, 
                            start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get current compliance status"""
        try:
            if not start_date:
                start_date = datetime.now() - timedelta(days=30)
            if not end_date:
                end_date = datetime.now()
            
            with sqlite3.connect(self.db_path) as conn:
                # Base query conditions
                conditions = ["timestamp BETWEEN ? AND ?"]
                params = [start_date.isoformat(), end_date.isoformat()]
                
                if user_id:
                    conditions.append("user_id = ?")
                    params.append(user_id)
                
                where_clause = " AND ".join(conditions)
                
                # Overall statistics
                cursor = conn.execute(f"""
                    SELECT 
                        COUNT(*) as total_checks,
                        SUM(CASE WHEN compliant = 1 THEN 1 ELSE 0 END) as compliant_checks,
                        SUM(violations_count) as total_violations
                    FROM compliance_checks 
                    WHERE {where_clause}
                """, params)
                
                stats = cursor.fetchone()
                compliance_rate = (stats[1] / stats[0] * 100) if stats[0] > 0 else 100
                
                # Recent violations by severity
                violation_conditions = ["detected_at BETWEEN ? AND ?"]
                violation_params = [start_date.isoformat(), end_date.isoformat()]
                
                if user_id:
                    violation_conditions.append("user_id = ?")
                    violation_params.append(user_id)
                
                violation_where = " AND ".join(violation_conditions)
                
                cursor = conn.execute(f"""
                    SELECT severity, COUNT(*) as count
                    FROM compliance_violations 
                    WHERE {violation_where}
                    GROUP BY severity
                """, violation_params)
                
                violations_by_severity = {row[0]: row[1] for row in cursor.fetchall()}
                
                return {
                    'period': {
                        'start_date': start_date.isoformat(),
                        'end_date': end_date.isoformat()
                    },
                    'user_id': user_id,
                    'statistics': {
                        'total_checks': stats[0],
                        'compliant_checks': stats[1],
                        'compliance_rate': round(compliance_rate, 2),
                        'total_violations': stats[2]
                    },
                    'violations_by_severity': violations_by_severity,
                    'status': 'COMPLIANT' if compliance_rate >= 95 and violations_by_severity.get('CRITICAL', 0) == 0 else 'NON_COMPLIANT'
                }
                
        except Exception as e:
            logger.error(f"Error getting compliance status: {e}")
            return {
                'error': str(e),
                'status': 'ERROR'
            }
    
    def apply_data_retention_policy(self) -> Dict[str, Any]:
        """Apply data retention policies and clean up old data"""
        results = {
            'deleted_records': {},
            'errors': [],
            'execution_time': None
        }
        
        start_time = datetime.now()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                for data_type, retention_days in self.retention_policies.items():
                    try:
                        cutoff_date = datetime.now() - timedelta(days=retention_days)
                        
                        if data_type == 'compliance_checks':
                            cursor = conn.execute("""
                                DELETE FROM compliance_checks 
                                WHERE created_at < ?
                            """, (cutoff_date.isoformat(),))
                            
                        elif data_type == 'violation_records':
                            cursor = conn.execute("""
                                DELETE FROM compliance_violations 
                                WHERE created_at < ? AND resolved = 1
                            """, (cutoff_date.isoformat(),))
                        
                        results['deleted_records'][data_type] = cursor.rowcount
                        
                    except Exception as e:
                        results['errors'].append(f"Error cleaning {data_type}: {str(e)}")
                
                # Vacuum database to reclaim space
                conn.execute("VACUUM")
                
        except Exception as e:
            results['errors'].append(f"Database error: {str(e)}")
        
        results['execution_time'] = (datetime.now() - start_time).total_seconds()
        
        return results

# Global compliance validator instance
compliance_validator = ComplianceValidator()

# Convenience functions for common compliance checks
def validate_order_compliance(order_data: Dict[str, Any]) -> ComplianceCheckResult:
    """Validate order compliance"""
    return compliance_validator.validate_order(order_data)

def validate_position_compliance(position_data: Dict[str, Any]) -> ComplianceCheckResult:
    """Validate position compliance"""
    return compliance_validator.validate_position(position_data)

def generate_compliance_report(report_type: str, start_date: datetime, 
                             end_date: datetime, generated_by: str,
                             regulatory_framework: RegulatoryFramework = RegulatoryFramework.SEBI) -> AuditReport:
    """Generate compliance audit report"""
    return compliance_validator.generate_audit_report(report_type, start_date, end_date, generated_by, regulatory_framework)

def get_compliance_status(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Get current compliance status"""
    return compliance_validator.get_compliance_status(user_id)