"""
Trading Engine Comprehensive Audit Logging System
Provides detailed logging of all trading decisions, executions, and regulatory compliance
"""
import json
import logging
import sqlite3
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import uuid
import gzip
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuditEventType(Enum):
    """Types of audit events"""
    SIGNAL_RECEIVED = "SIGNAL_RECEIVED"
    SIGNAL_PROCESSED = "SIGNAL_PROCESSED"
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_SUBMITTED = "ORDER_SUBMITTED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_REJECTED = "ORDER_REJECTED"
    POSITION_OPENED = "POSITION_OPENED"
    POSITION_CLOSED = "POSITION_CLOSED"
    POSITION_MODIFIED = "POSITION_MODIFIED"
    RISK_CHECK_PERFORMED = "RISK_CHECK_PERFORMED"
    RISK_VIOLATION = "RISK_VIOLATION"
    STRATEGY_DEPLOYED = "STRATEGY_DEPLOYED"
    STRATEGY_PAUSED = "STRATEGY_PAUSED"
    STRATEGY_STOPPED = "STRATEGY_STOPPED"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"
    SYSTEM_EVENT = "SYSTEM_EVENT"
    COMPLIANCE_CHECK = "COMPLIANCE_CHECK"
    DATA_ACCESS = "DATA_ACCESS"
    USER_ACTION = "USER_ACTION"

class AuditSeverity(Enum):
    """Audit event severity levels"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class ComplianceStatus(Enum):
    """Compliance check status"""
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    EXEMPTED = "EXEMPTED"

@dataclass
class DecisionContext:
    """Context information for trading decisions"""
    decision_id: str
    timestamp: datetime
    user_id: str
    strategy_id: Optional[str]
    market_data: Dict[str, Any]
    risk_parameters: Dict[str, Any]
    ai_signals: List[Dict[str, Any]]
    external_factors: Dict[str, Any]
    decision_rationale: str
    confidence_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'decision_id': self.decision_id,
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'strategy_id': self.strategy_id,
            'market_data': self.market_data,
            'risk_parameters': self.risk_parameters,
            'ai_signals': self.ai_signals,
            'external_factors': self.external_factors,
            'decision_rationale': self.decision_rationale,
            'confidence_score': self.confidence_score
        }

@dataclass
class AuditEvent:
    """Comprehensive audit event record"""
    event_id: str
    event_type: AuditEventType
    severity: AuditSeverity
    timestamp: datetime
    user_id: str
    session_id: Optional[str]
    component: str
    action: str
    resource: str
    outcome: str
    decision_context: Optional[DecisionContext]
    before_state: Optional[Dict[str, Any]]
    after_state: Optional[Dict[str, Any]]
    metadata: Dict[str, Any]
    compliance_status: ComplianceStatus
    regulatory_tags: List[str]
    data_classification: str
    retention_period_days: int
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.regulatory_tags is None:
            self.regulatory_tags = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'severity': self.severity.value,
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'session_id': self.session_id,
            'component': self.component,
            'action': self.action,
            'resource': self.resource,
            'outcome': self.outcome,
            'decision_context': self.decision_context.to_dict() if self.decision_context else None,
            'before_state': self.before_state,
            'after_state': self.after_state,
            'metadata': self.metadata,
            'compliance_status': self.compliance_status.value,
            'regulatory_tags': self.regulatory_tags,
            'data_classification': self.data_classification,
            'retention_period_days': self.retention_period_days
        }

@dataclass
class RegulatoryReport:
    """Regulatory reporting data structure"""
    report_id: str
    report_type: str
    reporting_period_start: datetime
    reporting_period_end: datetime
    generated_at: datetime
    data: Dict[str, Any]
    format_version: str
    compliance_officer: str
    status: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'report_id': self.report_id,
            'report_type': self.report_type,
            'reporting_period_start': self.reporting_period_start.isoformat(),
            'reporting_period_end': self.reporting_period_end.isoformat(),
            'generated_at': self.generated_at.isoformat(),
            'data': self.data,
            'format_version': self.format_version,
            'compliance_officer': self.compliance_officer,
            'status': self.status
        }

class AuditLogger:
    """Comprehensive audit logging system"""
    
    def __init__(self, db_path: str = "trading_audit.db", 
                 archive_path: str = "audit_archives"):
        self.db_path = db_path
        self.archive_path = Path(archive_path)
        self.archive_path.mkdir(exist_ok=True)
        self.lock = threading.Lock()
        
        # Regulatory configuration
        self.regulatory_config = {
            'mifid_ii': True,
            'sebi_regulations': True,
            'data_retention_days': 2555,  # 7 years
            'real_time_reporting': True,
            'encryption_required': True
        }
        
        self._init_database()
        self._setup_retention_policy()
    
    def _init_database(self):
        """Initialize audit database with comprehensive schema"""
        with sqlite3.connect(self.db_path) as conn:
            # Main audit events table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    user_id TEXT NOT NULL,
                    session_id TEXT,
                    component TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    decision_context TEXT,
                    before_state TEXT,
                    after_state TEXT,
                    metadata TEXT,
                    compliance_status TEXT NOT NULL,
                    regulatory_tags TEXT,
                    data_classification TEXT NOT NULL,
                    retention_period_days INTEGER NOT NULL,
                    archived BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Trading decisions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trading_decisions (
                    decision_id TEXT PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    user_id TEXT NOT NULL,
                    strategy_id TEXT,
                    symbol TEXT NOT NULL,
                    decision_type TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    confidence_score REAL,
                    market_data TEXT,
                    risk_parameters TEXT,
                    ai_signals TEXT,
                    external_factors TEXT,
                    outcome TEXT,
                    performance_impact REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Order execution audit
            conn.execute("""
                CREATE TABLE IF NOT EXISTS order_executions (
                    execution_id TEXT PRIMARY KEY,
                    order_id TEXT NOT NULL,
                    decision_id TEXT,
                    timestamp TIMESTAMP NOT NULL,
                    user_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL,
                    order_type TEXT NOT NULL,
                    execution_price REAL,
                    execution_quantity REAL,
                    execution_time TIMESTAMP,
                    broker_order_id TEXT,
                    commission REAL,
                    fees REAL,
                    slippage REAL,
                    market_impact REAL,
                    execution_quality TEXT,
                    regulatory_flags TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Risk events table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS risk_events (
                    risk_event_id TEXT PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    user_id TEXT NOT NULL,
                    risk_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    description TEXT NOT NULL,
                    risk_value REAL,
                    threshold_value REAL,
                    portfolio_impact REAL,
                    mitigation_action TEXT,
                    resolution_time TIMESTAMP,
                    regulatory_impact TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Compliance checks table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS compliance_checks (
                    check_id TEXT PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    user_id TEXT NOT NULL,
                    check_type TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    rule_set TEXT NOT NULL,
                    status TEXT NOT NULL,
                    violations TEXT,
                    remediation_required BOOLEAN,
                    remediation_actions TEXT,
                    officer_review_required BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Regulatory reports table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS regulatory_reports (
                    report_id TEXT PRIMARY KEY,
                    report_type TEXT NOT NULL,
                    reporting_period_start TIMESTAMP NOT NULL,
                    reporting_period_end TIMESTAMP NOT NULL,
                    generated_at TIMESTAMP NOT NULL,
                    data TEXT NOT NULL,
                    format_version TEXT NOT NULL,
                    compliance_officer TEXT NOT NULL,
                    status TEXT NOT NULL,
                    submitted_at TIMESTAMP,
                    acknowledgment_received BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Data access logs
            conn.execute("""
                CREATE TABLE IF NOT EXISTS data_access_logs (
                    access_id TEXT PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    user_id TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    access_type TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    success BOOLEAN NOT NULL,
                    failure_reason TEXT,
                    data_classification TEXT,
                    purpose TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON audit_events(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_audit_events_user ON audit_events(user_id, timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_audit_events_type ON audit_events(event_type, timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_trading_decisions_user ON trading_decisions(user_id, timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_order_executions_order ON order_executions(order_id)",
                "CREATE INDEX IF NOT EXISTS idx_risk_events_user ON risk_events(user_id, timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_compliance_checks_user ON compliance_checks(user_id, timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_data_access_user ON data_access_logs(user_id, timestamp)"
            ]
            
            for index_sql in indexes:
                conn.execute(index_sql)
    
    def _setup_retention_policy(self):
        """Setup data retention and archival policies"""
        # This would typically be run as a scheduled job
        pass
    
    def log_audit_event(self, event: AuditEvent) -> bool:
        """Log a comprehensive audit event"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO audit_events 
                        (event_id, event_type, severity, timestamp, user_id, session_id,
                         component, action, resource, outcome, decision_context,
                         before_state, after_state, metadata, compliance_status,
                         regulatory_tags, data_classification, retention_period_days)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        event.event_id,
                        event.event_type.value,
                        event.severity.value,
                        event.timestamp.isoformat(),
                        event.user_id,
                        event.session_id,
                        event.component,
                        event.action,
                        event.resource,
                        event.outcome,
                        json.dumps(event.decision_context.to_dict()) if event.decision_context else None,
                        json.dumps(event.before_state) if event.before_state else None,
                        json.dumps(event.after_state) if event.after_state else None,
                        json.dumps(event.metadata),
                        event.compliance_status.value,
                        json.dumps(event.regulatory_tags),
                        event.data_classification,
                        event.retention_period_days
                    ))
            
            # Real-time regulatory reporting if required
            if self.regulatory_config.get('real_time_reporting') and \
               event.severity in [AuditSeverity.ERROR, AuditSeverity.CRITICAL]:
                self._trigger_real_time_report(event)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            return False
    
    def log_trading_decision(self, decision_context: DecisionContext, 
                           symbol: str, decision_type: str, outcome: str = None,
                           performance_impact: float = None) -> bool:
        """Log a trading decision with full context"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO trading_decisions
                        (decision_id, timestamp, user_id, strategy_id, symbol,
                         decision_type, rationale, confidence_score, market_data,
                         risk_parameters, ai_signals, external_factors, outcome,
                         performance_impact)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        decision_context.decision_id,
                        decision_context.timestamp.isoformat(),
                        decision_context.user_id,
                        decision_context.strategy_id,
                        symbol,
                        decision_type,
                        decision_context.decision_rationale,
                        decision_context.confidence_score,
                        json.dumps(decision_context.market_data),
                        json.dumps(decision_context.risk_parameters),
                        json.dumps(decision_context.ai_signals),
                        json.dumps(decision_context.external_factors),
                        outcome,
                        performance_impact
                    ))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to log trading decision: {e}")
            return False
    
    def log_order_execution(self, execution_data: Dict[str, Any]) -> bool:
        """Log order execution details"""
        try:
            execution_id = str(uuid.uuid4())
            
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO order_executions
                        (execution_id, order_id, decision_id, timestamp, user_id,
                         symbol, side, quantity, price, order_type, execution_price,
                         execution_quantity, execution_time, broker_order_id,
                         commission, fees, slippage, market_impact, execution_quality,
                         regulatory_flags)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        execution_id,
                        execution_data.get('order_id'),
                        execution_data.get('decision_id'),
                        execution_data.get('timestamp', datetime.now().isoformat()),
                        execution_data.get('user_id'),
                        execution_data.get('symbol'),
                        execution_data.get('side'),
                        execution_data.get('quantity'),
                        execution_data.get('price'),
                        execution_data.get('order_type'),
                        execution_data.get('execution_price'),
                        execution_data.get('execution_quantity'),
                        execution_data.get('execution_time'),
                        execution_data.get('broker_order_id'),
                        execution_data.get('commission'),
                        execution_data.get('fees'),
                        execution_data.get('slippage'),
                        execution_data.get('market_impact'),
                        execution_data.get('execution_quality'),
                        json.dumps(execution_data.get('regulatory_flags', []))
                    ))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to log order execution: {e}")
            return False
    
    def log_risk_event(self, risk_data: Dict[str, Any]) -> bool:
        """Log risk management events"""
        try:
            risk_event_id = str(uuid.uuid4())
            
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO risk_events
                        (risk_event_id, timestamp, user_id, risk_type, severity,
                         description, risk_value, threshold_value, portfolio_impact,
                         mitigation_action, resolution_time, regulatory_impact)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        risk_event_id,
                        risk_data.get('timestamp', datetime.now().isoformat()),
                        risk_data.get('user_id'),
                        risk_data.get('risk_type'),
                        risk_data.get('severity'),
                        risk_data.get('description'),
                        risk_data.get('risk_value'),
                        risk_data.get('threshold_value'),
                        risk_data.get('portfolio_impact'),
                        risk_data.get('mitigation_action'),
                        risk_data.get('resolution_time'),
                        risk_data.get('regulatory_impact')
                    ))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to log risk event: {e}")
            return False
    
    def log_compliance_check(self, compliance_data: Dict[str, Any]) -> bool:
        """Log compliance validation checks"""
        try:
            check_id = str(uuid.uuid4())
            
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO compliance_checks
                        (check_id, timestamp, user_id, check_type, resource,
                         rule_set, status, violations, remediation_required,
                         remediation_actions, officer_review_required)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        check_id,
                        compliance_data.get('timestamp', datetime.now().isoformat()),
                        compliance_data.get('user_id'),
                        compliance_data.get('check_type'),
                        compliance_data.get('resource'),
                        compliance_data.get('rule_set'),
                        compliance_data.get('status'),
                        json.dumps(compliance_data.get('violations', [])),
                        compliance_data.get('remediation_required', False),
                        json.dumps(compliance_data.get('remediation_actions', [])),
                        compliance_data.get('officer_review_required', False)
                    ))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to log compliance check: {e}")
            return False
    
    def log_data_access(self, access_data: Dict[str, Any]) -> bool:
        """Log data access for privacy and security compliance"""
        try:
            access_id = str(uuid.uuid4())
            
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO data_access_logs
                        (access_id, timestamp, user_id, resource_type, resource_id,
                         access_type, ip_address, user_agent, success, failure_reason,
                         data_classification, purpose)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        access_id,
                        access_data.get('timestamp', datetime.now().isoformat()),
                        access_data.get('user_id'),
                        access_data.get('resource_type'),
                        access_data.get('resource_id'),
                        access_data.get('access_type'),
                        access_data.get('ip_address'),
                        access_data.get('user_agent'),
                        access_data.get('success', True),
                        access_data.get('failure_reason'),
                        access_data.get('data_classification', 'INTERNAL'),
                        access_data.get('purpose')
                    ))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to log data access: {e}")
            return False
    
    def generate_regulatory_report(self, report_type: str, 
                                 start_date: datetime, end_date: datetime,
                                 compliance_officer: str) -> RegulatoryReport:
        """Generate regulatory compliance report"""
        try:
            report_id = str(uuid.uuid4())
            
            # Collect relevant data based on report type
            report_data = self._collect_regulatory_data(report_type, start_date, end_date)
            
            report = RegulatoryReport(
                report_id=report_id,
                report_type=report_type,
                reporting_period_start=start_date,
                reporting_period_end=end_date,
                generated_at=datetime.now(),
                data=report_data,
                format_version="1.0",
                compliance_officer=compliance_officer,
                status="GENERATED"
            )
            
            # Save report to database
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO regulatory_reports
                        (report_id, report_type, reporting_period_start,
                         reporting_period_end, generated_at, data, format_version,
                         compliance_officer, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        report.report_id,
                        report.report_type,
                        report.reporting_period_start.isoformat(),
                        report.reporting_period_end.isoformat(),
                        report.generated_at.isoformat(),
                        json.dumps(report.data),
                        report.format_version,
                        report.compliance_officer,
                        report.status
                    ))
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate regulatory report: {e}")
            raise
    
    def _collect_regulatory_data(self, report_type: str, 
                               start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Collect data for regulatory reporting"""
        data = {}
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                if report_type == "MIFID_II_TRANSACTION_REPORT":
                    # Collect transaction data for MiFID II reporting
                    cursor = conn.execute("""
                        SELECT * FROM order_executions 
                        WHERE timestamp BETWEEN ? AND ?
                        ORDER BY timestamp
                    """, (start_date.isoformat(), end_date.isoformat()))
                    
                    transactions = []
                    for row in cursor.fetchall():
                        transactions.append({
                            'execution_id': row[0],
                            'order_id': row[1],
                            'timestamp': row[3],
                            'symbol': row[5],
                            'side': row[6],
                            'quantity': row[7],
                            'price': row[8],
                            'execution_price': row[10],
                            'execution_quantity': row[11]
                        })
                    
                    data['transactions'] = transactions
                    data['total_transactions'] = len(transactions)
                
                elif report_type == "RISK_MANAGEMENT_REPORT":
                    # Collect risk events and violations
                    cursor = conn.execute("""
                        SELECT * FROM risk_events 
                        WHERE timestamp BETWEEN ? AND ?
                        ORDER BY severity DESC, timestamp
                    """, (start_date.isoformat(), end_date.isoformat()))
                    
                    risk_events = []
                    for row in cursor.fetchall():
                        risk_events.append({
                            'risk_event_id': row[0],
                            'timestamp': row[1],
                            'risk_type': row[3],
                            'severity': row[4],
                            'description': row[5],
                            'risk_value': row[6],
                            'threshold_value': row[7]
                        })
                    
                    data['risk_events'] = risk_events
                    data['total_risk_events'] = len(risk_events)
                
                elif report_type == "COMPLIANCE_SUMMARY":
                    # Collect compliance check results
                    cursor = conn.execute("""
                        SELECT status, COUNT(*) as count FROM compliance_checks 
                        WHERE timestamp BETWEEN ? AND ?
                        GROUP BY status
                    """, (start_date.isoformat(), end_date.isoformat()))
                    
                    compliance_summary = {}
                    for row in cursor.fetchall():
                        compliance_summary[row[0]] = row[1]
                    
                    data['compliance_summary'] = compliance_summary
                
                # Add common metadata
                data['report_metadata'] = {
                    'reporting_period': {
                        'start': start_date.isoformat(),
                        'end': end_date.isoformat()
                    },
                    'generated_at': datetime.now().isoformat(),
                    'system_version': '1.0',
                    'data_integrity_hash': self._calculate_data_hash(data)
                }
        
        except Exception as e:
            logger.error(f"Failed to collect regulatory data: {e}")
            raise
        
        return data
    
    def _calculate_data_hash(self, data: Dict[str, Any]) -> str:
        """Calculate hash for data integrity verification"""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _trigger_real_time_report(self, event: AuditEvent):
        """Trigger real-time regulatory reporting for critical events"""
        try:
            # This would integrate with regulatory reporting systems
            logger.info(f"Real-time report triggered for event: {event.event_id}")
            
            # Example: Send to regulatory API
            # regulatory_api.submit_real_time_event(event.to_dict())
            
        except Exception as e:
            logger.error(f"Failed to trigger real-time report: {e}")
    
    def get_audit_trail(self, resource: str = None, user_id: str = None,
                       start_date: datetime = None, end_date: datetime = None,
                       limit: int = 1000) -> List[Dict[str, Any]]:
        """Get audit trail with filtering options"""
        try:
            query = "SELECT * FROM audit_events WHERE 1=1"
            params = []
            
            if resource:
                query += " AND resource = ?"
                params.append(resource)
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(query, params)
                
                audit_trail = []
                for row in cursor.fetchall():
                    audit_trail.append({
                        'event_id': row[0],
                        'event_type': row[1],
                        'severity': row[2],
                        'timestamp': row[3],
                        'user_id': row[4],
                        'session_id': row[5],
                        'component': row[6],
                        'action': row[7],
                        'resource': row[8],
                        'outcome': row[9],
                        'decision_context': json.loads(row[10]) if row[10] else None,
                        'before_state': json.loads(row[11]) if row[11] else None,
                        'after_state': json.loads(row[12]) if row[12] else None,
                        'metadata': json.loads(row[13]) if row[13] else {},
                        'compliance_status': row[14],
                        'regulatory_tags': json.loads(row[15]) if row[15] else [],
                        'data_classification': row[16]
                    })
                
                return audit_trail
        
        except Exception as e:
            logger.error(f"Failed to get audit trail: {e}")
            return []
    
    def archive_old_data(self, cutoff_date: datetime) -> bool:
        """Archive old audit data for long-term storage"""
        try:
            # Export data to compressed archive
            archive_file = self.archive_path / f"audit_archive_{cutoff_date.strftime('%Y%m%d')}.json.gz"
            
            # Get data to archive
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT * FROM audit_events WHERE timestamp < ?
                """, (cutoff_date.isoformat(),))
                
                archive_data = []
                for row in cursor.fetchall():
                    archive_data.append({
                        'event_id': row[0],
                        'event_type': row[1],
                        'timestamp': row[3],
                        'user_id': row[4],
                        'component': row[6],
                        'action': row[7],
                        'resource': row[8],
                        'outcome': row[9]
                    })
                
                # Compress and save
                with gzip.open(archive_file, 'wt') as f:
                    json.dump(archive_data, f)
                
                # Mark as archived
                conn.execute("""
                    UPDATE audit_events SET archived = 1 WHERE timestamp < ?
                """, (cutoff_date.isoformat(),))
            
            logger.info(f"Archived {len(archive_data)} audit records to {archive_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to archive audit data: {e}")
            return False
    
    def get_compliance_summary(self, start_date: datetime, 
                             end_date: datetime) -> Dict[str, Any]:
        """Get compliance summary for reporting period"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Compliance check summary
                cursor = conn.execute("""
                    SELECT status, COUNT(*) as count 
                    FROM compliance_checks 
                    WHERE timestamp BETWEEN ? AND ?
                    GROUP BY status
                """, (start_date.isoformat(), end_date.isoformat()))
                
                compliance_stats = {}
                for row in cursor.fetchall():
                    compliance_stats[row[0]] = row[1]
                
                # Risk events summary
                cursor = conn.execute("""
                    SELECT severity, COUNT(*) as count 
                    FROM risk_events 
                    WHERE timestamp BETWEEN ? AND ?
                    GROUP BY severity
                """, (start_date.isoformat(), end_date.isoformat()))
                
                risk_stats = {}
                for row in cursor.fetchall():
                    risk_stats[row[0]] = row[1]
                
                # Audit events summary
                cursor = conn.execute("""
                    SELECT event_type, COUNT(*) as count 
                    FROM audit_events 
                    WHERE timestamp BETWEEN ? AND ?
                    GROUP BY event_type
                """, (start_date.isoformat(), end_date.isoformat()))
                
                audit_stats = {}
                for row in cursor.fetchall():
                    audit_stats[row[0]] = row[1]
                
                return {
                    'reporting_period': {
                        'start': start_date.isoformat(),
                        'end': end_date.isoformat()
                    },
                    'compliance_checks': compliance_stats,
                    'risk_events': risk_stats,
                    'audit_events': audit_stats,
                    'generated_at': datetime.now().isoformat()
                }
        
        except Exception as e:
            logger.error(f"Failed to get compliance summary: {e}")
            return {}

# Global audit logger instance
audit_logger = AuditLogger()

# Convenience functions for common audit events
def log_signal_received(user_id: str, signal_data: Dict[str, Any], 
                       decision_context: DecisionContext):
    """Log AI signal reception"""
    event = AuditEvent(
        event_id=str(uuid.uuid4()),
        event_type=AuditEventType.SIGNAL_RECEIVED,
        severity=AuditSeverity.INFO,
        timestamp=datetime.now(),
        user_id=user_id,
        session_id=None,
        component="signal_processor",
        action="receive_signal",
        resource=f"signal_{signal_data.get('signal_id')}",
        outcome="SUCCESS",
        decision_context=decision_context,
        before_state=None,
        after_state=signal_data,
        metadata={"signal_type": signal_data.get("type"), "confidence": signal_data.get("confidence")},
        compliance_status=ComplianceStatus.COMPLIANT,
        regulatory_tags=["MIFID_II", "ALGO_TRADING"],
        data_classification="CONFIDENTIAL",
        retention_period_days=2555
    )
    
    return audit_logger.log_audit_event(event)

def log_order_placed(user_id: str, order_data: Dict[str, Any], 
                    decision_context: DecisionContext):
    """Log order placement"""
    event = AuditEvent(
        event_id=str(uuid.uuid4()),
        event_type=AuditEventType.ORDER_CREATED,
        severity=AuditSeverity.INFO,
        timestamp=datetime.now(),
        user_id=user_id,
        session_id=order_data.get('session_id'),
        component="order_executor",
        action="place_order",
        resource=f"order_{order_data.get('order_id')}",
        outcome="SUCCESS",
        decision_context=decision_context,
        before_state=None,
        after_state=order_data,
        metadata={"symbol": order_data.get("symbol"), "quantity": order_data.get("quantity")},
        compliance_status=ComplianceStatus.COMPLIANT,
        regulatory_tags=["MIFID_II", "BEST_EXECUTION"],
        data_classification="CONFIDENTIAL",
        retention_period_days=2555
    )
    
    return audit_logger.log_audit_event(event)

def log_risk_violation(user_id: str, risk_data: Dict[str, Any]):
    """Log risk management violation"""
    event = AuditEvent(
        event_id=str(uuid.uuid4()),
        event_type=AuditEventType.RISK_VIOLATION,
        severity=AuditSeverity.ERROR,
        timestamp=datetime.now(),
        user_id=user_id,
        session_id=None,
        component="risk_engine",
        action="risk_check",
        resource=f"portfolio_{user_id}",
        outcome="VIOLATION",
        decision_context=None,
        before_state=risk_data.get('before_state'),
        after_state=risk_data.get('after_state'),
        metadata={"risk_type": risk_data.get("risk_type"), "severity": risk_data.get("severity")},
        compliance_status=ComplianceStatus.NON_COMPLIANT,
        regulatory_tags=["RISK_MANAGEMENT", "SEBI"],
        data_classification="CONFIDENTIAL",
        retention_period_days=2555
    )
    
    return audit_logger.log_audit_event(event)

def log_emergency_stop(user_id: str, stop_data: Dict[str, Any]):
    """Log emergency stop event"""
    event = AuditEvent(
        event_id=str(uuid.uuid4()),
        event_type=AuditEventType.EMERGENCY_STOP,
        severity=AuditSeverity.CRITICAL,
        timestamp=datetime.now(),
        user_id=user_id,
        session_id=stop_data.get('session_id'),
        component="emergency_stop",
        action="emergency_stop",
        resource=f"system_{user_id}",
        outcome="SUCCESS",
        decision_context=None,
        before_state=stop_data.get('before_state'),
        after_state=stop_data.get('after_state'),
        metadata={"reason": stop_data.get("reason"), "scope": stop_data.get("scope")},
        compliance_status=ComplianceStatus.COMPLIANT,
        regulatory_tags=["EMERGENCY_PROCEDURES", "RISK_MANAGEMENT"],
        data_classification="CONFIDENTIAL",
        retention_period_days=2555
    )
    
    return audit_logger.log_audit_event(event)