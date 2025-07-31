"""
FastAPI Router for Trading Engine Audit Logging System
Provides REST API endpoints for audit trail access and regulatory reporting
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import json

from .audit_logger import (
    audit_logger, AuditEventType, AuditSeverity, ComplianceStatus,
    DecisionContext, AuditEvent, log_signal_received, log_order_placed,
    log_risk_violation, log_emergency_stop
)

router = APIRouter(prefix="/api/trading-engine/audit", tags=["audit"])

# Pydantic models for API
class DecisionContextRequest(BaseModel):
    decision_id: str
    user_id: str
    strategy_id: Optional[str] = None
    market_data: Dict[str, Any]
    risk_parameters: Dict[str, Any]
    ai_signals: List[Dict[str, Any]]
    external_factors: Dict[str, Any]
    decision_rationale: str
    confidence_score: float

class AuditEventRequest(BaseModel):
    event_type: str = Field(..., description="Type of audit event")
    severity: str = Field(..., description="Event severity")
    user_id: str = Field(..., description="User ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    component: str = Field(..., description="System component")
    action: str = Field(..., description="Action performed")
    resource: str = Field(..., description="Resource affected")
    outcome: str = Field(..., description="Action outcome")
    decision_context: Optional[DecisionContextRequest] = None
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    compliance_status: str = Field("COMPLIANT", description="Compliance status")
    regulatory_tags: List[str] = Field(default_factory=list)
    data_classification: str = Field("INTERNAL", description="Data classification")
    retention_period_days: int = Field(2555, description="Retention period in days")

class TradingDecisionRequest(BaseModel):
    decision_context: DecisionContextRequest
    symbol: str
    decision_type: str
    outcome: Optional[str] = None
    performance_impact: Optional[float] = None

class OrderExecutionRequest(BaseModel):
    order_id: str
    decision_id: Optional[str] = None
    user_id: str
    symbol: str
    side: str
    quantity: float
    price: Optional[float] = None
    order_type: str
    execution_price: Optional[float] = None
    execution_quantity: Optional[float] = None
    execution_time: Optional[str] = None
    broker_order_id: Optional[str] = None
    commission: Optional[float] = None
    fees: Optional[float] = None
    slippage: Optional[float] = None
    market_impact: Optional[float] = None
    execution_quality: Optional[str] = None
    regulatory_flags: List[str] = Field(default_factory=list)

class RiskEventRequest(BaseModel):
    user_id: str
    risk_type: str
    severity: str
    description: str
    risk_value: Optional[float] = None
    threshold_value: Optional[float] = None
    portfolio_impact: Optional[float] = None
    mitigation_action: Optional[str] = None
    resolution_time: Optional[str] = None
    regulatory_impact: Optional[str] = None

class ComplianceCheckRequest(BaseModel):
    user_id: str
    check_type: str
    resource: str
    rule_set: str
    status: str
    violations: List[str] = Field(default_factory=list)
    remediation_required: bool = False
    remediation_actions: List[str] = Field(default_factory=list)
    officer_review_required: bool = False

class DataAccessRequest(BaseModel):
    user_id: str
    resource_type: str
    resource_id: str
    access_type: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool = True
    failure_reason: Optional[str] = None
    data_classification: str = "INTERNAL"
    purpose: Optional[str] = None

class RegulatoryReportRequest(BaseModel):
    report_type: str
    start_date: str
    end_date: str
    compliance_officer: str

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "audit_logger",
        "timestamp": datetime.now().isoformat(),
        "database_path": audit_logger.db_path
    }

@router.post("/events")
async def log_audit_event(request: AuditEventRequest):
    """Log a comprehensive audit event"""
    try:
        # Convert request to DecisionContext if provided
        decision_context = None
        if request.decision_context:
            decision_context = DecisionContext(
                decision_id=request.decision_context.decision_id,
                timestamp=datetime.now(),
                user_id=request.decision_context.user_id,
                strategy_id=request.decision_context.strategy_id,
                market_data=request.decision_context.market_data,
                risk_parameters=request.decision_context.risk_parameters,
                ai_signals=request.decision_context.ai_signals,
                external_factors=request.decision_context.external_factors,
                decision_rationale=request.decision_context.decision_rationale,
                confidence_score=request.decision_context.confidence_score
            )
        
        # Create audit event
        event = AuditEvent(
            event_id=f"evt_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{request.user_id}",
            event_type=AuditEventType(request.event_type),
            severity=AuditSeverity(request.severity),
            timestamp=datetime.now(),
            user_id=request.user_id,
            session_id=request.session_id,
            component=request.component,
            action=request.action,
            resource=request.resource,
            outcome=request.outcome,
            decision_context=decision_context,
            before_state=request.before_state,
            after_state=request.after_state,
            metadata=request.metadata,
            compliance_status=ComplianceStatus(request.compliance_status),
            regulatory_tags=request.regulatory_tags,
            data_classification=request.data_classification,
            retention_period_days=request.retention_period_days
        )
        
        success = audit_logger.log_audit_event(event)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to log audit event")
        
        return {
            "success": True,
            "event_id": event.event_id,
            "message": "Audit event logged successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid enum value: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.post("/trading-decisions")
async def log_trading_decision(request: TradingDecisionRequest):
    """Log a trading decision with full context"""
    try:
        # Create decision context
        decision_context = DecisionContext(
            decision_id=request.decision_context.decision_id,
            timestamp=datetime.now(),
            user_id=request.decision_context.user_id,
            strategy_id=request.decision_context.strategy_id,
            market_data=request.decision_context.market_data,
            risk_parameters=request.decision_context.risk_parameters,
            ai_signals=request.decision_context.ai_signals,
            external_factors=request.decision_context.external_factors,
            decision_rationale=request.decision_context.decision_rationale,
            confidence_score=request.decision_context.confidence_score
        )
        
        success = audit_logger.log_trading_decision(
            decision_context=decision_context,
            symbol=request.symbol,
            decision_type=request.decision_type,
            outcome=request.outcome,
            performance_impact=request.performance_impact
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to log trading decision")
        
        return {
            "success": True,
            "decision_id": decision_context.decision_id,
            "message": "Trading decision logged successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.post("/order-executions")
async def log_order_execution(request: OrderExecutionRequest):
    """Log order execution details"""
    try:
        execution_data = {
            'order_id': request.order_id,
            'decision_id': request.decision_id,
            'timestamp': datetime.now().isoformat(),
            'user_id': request.user_id,
            'symbol': request.symbol,
            'side': request.side,
            'quantity': request.quantity,
            'price': request.price,
            'order_type': request.order_type,
            'execution_price': request.execution_price,
            'execution_quantity': request.execution_quantity,
            'execution_time': request.execution_time,
            'broker_order_id': request.broker_order_id,
            'commission': request.commission,
            'fees': request.fees,
            'slippage': request.slippage,
            'market_impact': request.market_impact,
            'execution_quality': request.execution_quality,
            'regulatory_flags': request.regulatory_flags
        }
        
        success = audit_logger.log_order_execution(execution_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to log order execution")
        
        return {
            "success": True,
            "order_id": request.order_id,
            "message": "Order execution logged successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.post("/risk-events")
async def log_risk_event(request: RiskEventRequest):
    """Log risk management events"""
    try:
        risk_data = {
            'timestamp': datetime.now().isoformat(),
            'user_id': request.user_id,
            'risk_type': request.risk_type,
            'severity': request.severity,
            'description': request.description,
            'risk_value': request.risk_value,
            'threshold_value': request.threshold_value,
            'portfolio_impact': request.portfolio_impact,
            'mitigation_action': request.mitigation_action,
            'resolution_time': request.resolution_time,
            'regulatory_impact': request.regulatory_impact
        }
        
        success = audit_logger.log_risk_event(risk_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to log risk event")
        
        return {
            "success": True,
            "message": "Risk event logged successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.post("/compliance-checks")
async def log_compliance_check(request: ComplianceCheckRequest):
    """Log compliance validation checks"""
    try:
        compliance_data = {
            'timestamp': datetime.now().isoformat(),
            'user_id': request.user_id,
            'check_type': request.check_type,
            'resource': request.resource,
            'rule_set': request.rule_set,
            'status': request.status,
            'violations': request.violations,
            'remediation_required': request.remediation_required,
            'remediation_actions': request.remediation_actions,
            'officer_review_required': request.officer_review_required
        }
        
        success = audit_logger.log_compliance_check(compliance_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to log compliance check")
        
        return {
            "success": True,
            "message": "Compliance check logged successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.post("/data-access")
async def log_data_access(request: DataAccessRequest):
    """Log data access for privacy and security compliance"""
    try:
        access_data = {
            'timestamp': datetime.now().isoformat(),
            'user_id': request.user_id,
            'resource_type': request.resource_type,
            'resource_id': request.resource_id,
            'access_type': request.access_type,
            'ip_address': request.ip_address,
            'user_agent': request.user_agent,
            'success': request.success,
            'failure_reason': request.failure_reason,
            'data_classification': request.data_classification,
            'purpose': request.purpose
        }
        
        success = audit_logger.log_data_access(access_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to log data access")
        
        return {
            "success": True,
            "message": "Data access logged successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.get("/trail")
async def get_audit_trail(
    resource: Optional[str] = Query(None, description="Filter by resource"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    limit: int = Query(1000, description="Maximum number of records")
):
    """Get audit trail with filtering options"""
    try:
        # Parse dates if provided
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        audit_trail = audit_logger.get_audit_trail(
            resource=resource,
            user_id=user_id,
            start_date=start_dt,
            end_date=end_dt,
            limit=limit
        )
        
        return {
            "success": True,
            "audit_trail": audit_trail,
            "total_records": len(audit_trail),
            "filters": {
                "resource": resource,
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.get("/compliance-summary")
async def get_compliance_summary(
    start_date: str = Query(..., description="Start date (ISO format)"),
    end_date: str = Query(..., description="End date (ISO format)")
):
    """Get compliance summary for reporting period"""
    try:
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
        
        summary = audit_logger.get_compliance_summary(start_dt, end_dt)
        
        return {
            "success": True,
            "compliance_summary": summary
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.post("/regulatory-reports")
async def generate_regulatory_report(request: RegulatoryReportRequest):
    """Generate regulatory compliance report"""
    try:
        start_dt = datetime.fromisoformat(request.start_date)
        end_dt = datetime.fromisoformat(request.end_date)
        
        report = audit_logger.generate_regulatory_report(
            report_type=request.report_type,
            start_date=start_dt,
            end_date=end_dt,
            compliance_officer=request.compliance_officer
        )
        
        return {
            "success": True,
            "report": report.to_dict(),
            "message": "Regulatory report generated successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.get("/regulatory-reports")
async def list_regulatory_reports(
    report_type: Optional[str] = Query(None, description="Filter by report type"),
    limit: int = Query(100, description="Maximum number of reports")
):
    """List generated regulatory reports"""
    try:
        # This would query the regulatory_reports table
        # For now, return a placeholder response
        return {
            "success": True,
            "reports": [],
            "message": "Regulatory reports list retrieved"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.get("/regulatory-reports/{report_id}")
async def get_regulatory_report(report_id: str):
    """Get specific regulatory report"""
    try:
        # This would query the specific report from database
        # For now, return a placeholder response
        return {
            "success": True,
            "report_id": report_id,
            "message": "Regulatory report retrieved"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.post("/archive")
async def archive_old_data(
    cutoff_date: str = Query(..., description="Archive data older than this date")
):
    """Archive old audit data for long-term storage"""
    try:
        cutoff_dt = datetime.fromisoformat(cutoff_date)
        
        success = audit_logger.archive_old_data(cutoff_dt)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to archive data")
        
        return {
            "success": True,
            "cutoff_date": cutoff_date,
            "message": "Data archived successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.get("/statistics")
async def get_audit_statistics():
    """Get audit logging statistics"""
    try:
        # Get basic statistics from the database
        import sqlite3
        
        stats = {}
        
        with sqlite3.connect(audit_logger.db_path) as conn:
            # Total audit events
            cursor = conn.execute("SELECT COUNT(*) FROM audit_events")
            stats['total_audit_events'] = cursor.fetchone()[0]
            
            # Events by type
            cursor = conn.execute("""
                SELECT event_type, COUNT(*) as count 
                FROM audit_events 
                GROUP BY event_type 
                ORDER BY count DESC
            """)
            stats['events_by_type'] = dict(cursor.fetchall())
            
            # Events by severity
            cursor = conn.execute("""
                SELECT severity, COUNT(*) as count 
                FROM audit_events 
                GROUP BY severity
            """)
            stats['events_by_severity'] = dict(cursor.fetchall())
            
            # Recent events (last 24 hours)
            cursor = conn.execute("""
                SELECT COUNT(*) FROM audit_events 
                WHERE timestamp >= datetime('now', '-1 day')
            """)
            stats['recent_events_24h'] = cursor.fetchone()[0]
            
            # Trading decisions count
            cursor = conn.execute("SELECT COUNT(*) FROM trading_decisions")
            stats['total_trading_decisions'] = cursor.fetchone()[0]
            
            # Order executions count
            cursor = conn.execute("SELECT COUNT(*) FROM order_executions")
            stats['total_order_executions'] = cursor.fetchone()[0]
            
            # Risk events count
            cursor = conn.execute("SELECT COUNT(*) FROM risk_events")
            stats['total_risk_events'] = cursor.fetchone()[0]
            
            # Compliance checks count
            cursor = conn.execute("SELECT COUNT(*) FROM compliance_checks")
            stats['total_compliance_checks'] = cursor.fetchone()[0]
        
        return {
            "success": True,
            "statistics": stats,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.get("/event-types")
async def get_event_types():
    """Get available audit event types"""
    return {
        "success": True,
        "event_types": [event_type.value for event_type in AuditEventType],
        "severities": [severity.value for severity in AuditSeverity],
        "compliance_statuses": [status.value for status in ComplianceStatus]
    }

@router.post("/test")
async def test_audit_logging():
    """Test audit logging system with sample data"""
    try:
        # Create test decision context
        decision_context = DecisionContext(
            decision_id="test_decision_001",
            timestamp=datetime.now(),
            user_id="test_user",
            strategy_id="test_strategy",
            market_data={"symbol": "RELIANCE", "price": 2500.0, "volume": 1000},
            risk_parameters={"max_position_size": 10.0, "stop_loss": 5.0},
            ai_signals=[{"type": "BUY", "confidence": 0.85, "source": "momentum_model"}],
            external_factors={"market_sentiment": "BULLISH", "volatility": "LOW"},
            decision_rationale="Strong momentum signal with low risk",
            confidence_score=0.85
        )
        
        # Test signal received logging
        signal_data = {
            "signal_id": "sig_001",
            "type": "BUY",
            "confidence": 0.85,
            "symbol": "RELIANCE"
        }
        
        success1 = log_signal_received("test_user", signal_data, decision_context)
        
        # Test order placement logging
        order_data = {
            "order_id": "ord_001",
            "session_id": "sess_001",
            "symbol": "RELIANCE",
            "quantity": 100,
            "side": "BUY",
            "order_type": "MARKET"
        }
        
        success2 = log_order_placed("test_user", order_data, decision_context)
        
        # Test risk violation logging
        risk_data = {
            "risk_type": "POSITION_SIZE",
            "severity": "HIGH",
            "before_state": {"position_size": 8.0},
            "after_state": {"position_size": 12.0}
        }
        
        success3 = log_risk_violation("test_user", risk_data)
        
        return {
            "success": True,
            "test_results": {
                "signal_logged": success1,
                "order_logged": success2,
                "risk_violation_logged": success3
            },
            "message": "Audit logging test completed"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")