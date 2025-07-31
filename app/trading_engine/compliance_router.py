"""
Trading Engine Compliance Router
FastAPI router for compliance validation endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import logging

from .compliance_validator import (
    compliance_validator,
    validate_order_compliance,
    validate_position_compliance,
    generate_compliance_report,
    get_compliance_status,
    ComplianceRule,
    RegulatoryFramework,
    ComplianceRuleType,
    ViolationSeverity
)

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/compliance", tags=["compliance"])

# Pydantic models for request/response
class OrderValidationRequest(BaseModel):
    """Order validation request model"""
    order_id: str
    user_id: str
    symbol: str
    quantity: int
    price: float
    order_type: str
    side: str  # BUY or SELL
    portfolio_value: Optional[float] = None
    market_price: Optional[float] = None
    position_size_percent: Optional[float] = None
    execution_quality_score: Optional[float] = None
    has_risk_controls: Optional[bool] = True
    algo_approval: Optional[bool] = True
    leverage_ratio: Optional[float] = 1.0
    security_concentration_percent: Optional[float] = None
    orders_per_second: Optional[int] = 1

class PositionValidationRequest(BaseModel):
    """Position validation request model"""
    position_id: str
    user_id: str
    symbol: str
    quantity: int
    market_value: float
    portfolio_value: float
    position_size_percent: float
    security_concentration_percent: float
    leverage_ratio: float
    sector: Optional[str] = None

class ComplianceRuleRequest(BaseModel):
    """Compliance rule creation request"""
    name: str
    description: str
    regulatory_framework: str
    rule_type: str
    severity: str
    condition: str  # JSON string
    remediation_action: str
    enabled: bool = True

class AuditReportRequest(BaseModel):
    """Audit report generation request"""
    report_type: str = Field(..., description="Type of report: COMPLIANCE_SUMMARY, VIOLATION_ANALYSIS, REGULATORY_FILING")
    start_date: datetime
    end_date: datetime
    generated_by: str
    regulatory_framework: Optional[str] = "SEBI"

class ComplianceStatusResponse(BaseModel):
    """Compliance status response model"""
    period: Dict[str, str]
    user_id: Optional[str]
    statistics: Dict[str, Any]
    violations_by_severity: Dict[str, int]
    status: str

@router.post("/validate/order")
async def validate_order(request: OrderValidationRequest):
    """
    Validate order against compliance rules
    
    Performs pre-trade compliance checks including:
    - Position limits
    - Risk limits
    - Regulatory requirements
    - Best execution criteria
    """
    try:
        # Convert request to dict for validation
        order_data = request.dict()
        
        # Add calculated fields if not provided
        if not order_data.get('market_price'):
            order_data['market_price'] = order_data['price']
        
        if not order_data.get('position_size_percent') and order_data.get('portfolio_value'):
            order_value = order_data['quantity'] * order_data['price']
            order_data['position_size_percent'] = (order_value / order_data['portfolio_value']) * 100
        
        if not order_data.get('execution_quality_score'):
            order_data['execution_quality_score'] = 0.9  # Default good execution score
        
        # Validate order
        result = validate_order_compliance(order_data)
        
        # Convert result to dict for JSON response
        response_data = result.to_dict()
        
        # Add compliance decision
        response_data['compliance_decision'] = {
            'approved': result.compliant,
            'requires_review': len([v for v in result.violations if v.officer_review_required]) > 0,
            'critical_violations': len([v for v in result.violations if v.severity == ViolationSeverity.CRITICAL]) > 0
        }
        
        return JSONResponse(
            status_code=200 if result.compliant else 400,
            content=response_data
        )
        
    except Exception as e:
        logger.error(f"Error validating order: {e}")
        raise HTTPException(status_code=500, detail=f"Order validation failed: {str(e)}")

@router.post("/validate/position")
async def validate_position(request: PositionValidationRequest):
    """
    Validate position against compliance rules
    
    Performs position-level compliance checks including:
    - Position size limits
    - Concentration limits
    - Leverage limits
    - Sector exposure limits
    """
    try:
        # Convert request to dict for validation
        position_data = request.dict()
        
        # Validate position
        result = validate_position_compliance(position_data)
        
        # Convert result to dict for JSON response
        response_data = result.to_dict()
        
        # Add compliance decision
        response_data['compliance_decision'] = {
            'compliant': result.compliant,
            'requires_action': len([v for v in result.violations if v.remediation_required]) > 0,
            'critical_violations': len([v for v in result.violations if v.severity == ViolationSeverity.CRITICAL]) > 0
        }
        
        return JSONResponse(
            status_code=200 if result.compliant else 400,
            content=response_data
        )
        
    except Exception as e:
        logger.error(f"Error validating position: {e}")
        raise HTTPException(status_code=500, detail=f"Position validation failed: {str(e)}")

@router.get("/status")
async def get_compliance_status_endpoint(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    days: int = Query(30, description="Number of days to look back", ge=1, le=365)
):
    """
    Get current compliance status and statistics
    
    Returns:
    - Overall compliance rate
    - Violation counts by severity
    - Recent compliance trends
    """
    try:
        start_date = datetime.now() - timedelta(days=days)
        end_date = datetime.now()
        
        status = compliance_validator.get_compliance_status(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return JSONResponse(status_code=200, content=status)
        
    except Exception as e:
        logger.error(f"Error getting compliance status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get compliance status: {str(e)}")

@router.get("/violations")
async def get_violations(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    resolved: Optional[bool] = Query(None, description="Filter by resolution status"),
    days: int = Query(30, description="Number of days to look back", ge=1, le=365),
    limit: int = Query(100, description="Maximum number of violations to return", ge=1, le=1000)
):
    """
    Get compliance violations with filtering options
    """
    try:
        import sqlite3
        
        start_date = datetime.now() - timedelta(days=days)
        
        # Build query conditions
        conditions = ["detected_at >= ?"]
        params = [start_date.isoformat()]
        
        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)
        
        if severity:
            conditions.append("severity = ?")
            params.append(severity.upper())
        
        if resolved is not None:
            if resolved:
                conditions.append("resolved_at IS NOT NULL")
            else:
                conditions.append("resolved_at IS NULL")
        
        where_clause = " AND ".join(conditions)
        
        with sqlite3.connect(compliance_validator.db_path) as conn:
            cursor = conn.execute(f"""
                SELECT 
                    violation_id, rule_id, user_id, resource_id, violation_type,
                    severity, description, detected_at, remediation_required,
                    remediation_actions, officer_review_required, resolved_at,
                    resolution_notes
                FROM compliance_violations 
                WHERE {where_clause}
                ORDER BY detected_at DESC
                LIMIT ?
            """, params + [limit])
            
            violations = []
            for row in cursor.fetchall():
                violations.append({
                    'violation_id': row[0],
                    'rule_id': row[1],
                    'user_id': row[2],
                    'resource_id': row[3],
                    'violation_type': row[4],
                    'severity': row[5],
                    'description': row[6],
                    'detected_at': row[7],
                    'remediation_required': bool(row[8]),
                    'remediation_actions': row[9].split(',') if row[9] else [],
                    'officer_review_required': bool(row[10]),
                    'resolved_at': row[11],
                    'resolution_notes': row[12],
                    'resolved': row[11] is not None
                })
        
        return JSONResponse(status_code=200, content={
            'violations': violations,
            'total_count': len(violations),
            'filters_applied': {
                'user_id': user_id,
                'severity': severity,
                'resolved': resolved,
                'days': days
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting violations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get violations: {str(e)}")

@router.post("/violations/{violation_id}/resolve")
async def resolve_violation(
    violation_id: str,
    resolution_notes: str = Body(..., embed=True)
):
    """
    Mark a compliance violation as resolved
    """
    try:
        import sqlite3
        
        with sqlite3.connect(compliance_validator.db_path) as conn:
            # Check if violation exists
            cursor = conn.execute(
                "SELECT violation_id FROM compliance_violations WHERE violation_id = ?",
                (violation_id,)
            )
            
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Violation not found")
            
            # Update violation
            conn.execute("""
                UPDATE compliance_violations 
                SET resolved_at = ?, resolution_notes = ?
                WHERE violation_id = ?
            """, (datetime.now().isoformat(), resolution_notes, violation_id))
            
            return JSONResponse(status_code=200, content={
                'message': 'Violation resolved successfully',
                'violation_id': violation_id,
                'resolved_at': datetime.now().isoformat()
            })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving violation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to resolve violation: {str(e)}")

@router.post("/rules")
async def add_compliance_rule(request: ComplianceRuleRequest):
    """
    Add a new compliance rule
    """
    try:
        # Validate enums
        try:
            regulatory_framework = RegulatoryFramework(request.regulatory_framework.upper())
            rule_type = ComplianceRuleType(request.rule_type.upper())
            severity = ViolationSeverity(request.severity.upper())
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid enum value: {str(e)}")
        
        # Validate condition JSON
        import json
        try:
            json.loads(request.condition)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in condition field")
        
        # Create rule
        rule = ComplianceRule(
            rule_id=f"custom_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name=request.name,
            description=request.description,
            regulatory_framework=regulatory_framework,
            rule_type=rule_type,
            severity=severity,
            condition=request.condition,
            remediation_action=request.remediation_action,
            enabled=request.enabled
        )
        
        # Add rule to validator
        success = compliance_validator.add_rule(rule)
        
        if success:
            return JSONResponse(status_code=201, content={
                'message': 'Compliance rule added successfully',
                'rule_id': rule.rule_id,
                'rule': {
                    'rule_id': rule.rule_id,
                    'name': rule.name,
                    'description': rule.description,
                    'regulatory_framework': rule.regulatory_framework.value,
                    'rule_type': rule.rule_type.value,
                    'severity': rule.severity.value,
                    'enabled': rule.enabled
                }
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to add compliance rule")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding compliance rule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add compliance rule: {str(e)}")

@router.get("/rules")
async def get_compliance_rules(
    regulatory_framework: Optional[str] = Query(None, description="Filter by regulatory framework"),
    rule_type: Optional[str] = Query(None, description="Filter by rule type"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status")
):
    """
    Get compliance rules with filtering options
    """
    try:
        import sqlite3
        
        # Build query conditions
        conditions = []
        params = []
        
        if regulatory_framework:
            conditions.append("regulatory_framework = ?")
            params.append(regulatory_framework.upper())
        
        if rule_type:
            conditions.append("rule_type = ?")
            params.append(rule_type.upper())
        
        if enabled is not None:
            conditions.append("enabled = ?")
            params.append(enabled)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        with sqlite3.connect(compliance_validator.db_path) as conn:
            cursor = conn.execute(f"""
                SELECT 
                    rule_id, name, description, regulatory_framework, rule_type,
                    severity, condition, remediation_action, enabled, created_at
                FROM compliance_rules 
                WHERE {where_clause}
                ORDER BY created_at DESC
            """, params)
            
            rules = []
            for row in cursor.fetchall():
                rules.append({
                    'rule_id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'regulatory_framework': row[3],
                    'rule_type': row[4],
                    'severity': row[5],
                    'condition': row[6],
                    'remediation_action': row[7],
                    'enabled': bool(row[8]),
                    'created_at': row[9]
                })
        
        return JSONResponse(status_code=200, content={
            'rules': rules,
            'total_count': len(rules),
            'filters_applied': {
                'regulatory_framework': regulatory_framework,
                'rule_type': rule_type,
                'enabled': enabled
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting compliance rules: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get compliance rules: {str(e)}")

@router.post("/reports/generate")
async def generate_audit_report(request: AuditReportRequest):
    """
    Generate compliance audit report
    
    Supported report types:
    - COMPLIANCE_SUMMARY: Overall compliance statistics and trends
    - VIOLATION_ANALYSIS: Detailed violation analysis and patterns
    - REGULATORY_FILING: Regulatory-specific compliance report
    """
    try:
        # Validate regulatory framework
        try:
            regulatory_framework = RegulatoryFramework(request.regulatory_framework.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid regulatory framework: {request.regulatory_framework}")
        
        # Validate report type
        valid_report_types = ["COMPLIANCE_SUMMARY", "VIOLATION_ANALYSIS", "REGULATORY_FILING"]
        if request.report_type not in valid_report_types:
            raise HTTPException(status_code=400, detail=f"Invalid report type. Must be one of: {valid_report_types}")
        
        # Generate report
        report = generate_compliance_report(
            report_type=request.report_type,
            start_date=request.start_date,
            end_date=request.end_date,
            generated_by=request.generated_by
        )
        
        return JSONResponse(status_code=200, content=report.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating audit report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate audit report: {str(e)}")

@router.get("/reports")
async def get_audit_reports(
    report_type: Optional[str] = Query(None, description="Filter by report type"),
    generated_by: Optional[str] = Query(None, description="Filter by generator"),
    days: int = Query(90, description="Number of days to look back", ge=1, le=365),
    limit: int = Query(50, description="Maximum number of reports to return", ge=1, le=200)
):
    """
    Get audit reports with filtering options
    """
    try:
        import sqlite3
        
        start_date = datetime.now() - timedelta(days=days)
        
        # Build query conditions
        conditions = ["generated_at >= ?"]
        params = [start_date.isoformat()]
        
        if report_type:
            conditions.append("report_type = ?")
            params.append(report_type)
        
        if generated_by:
            conditions.append("generated_by = ?")
            params.append(generated_by)
        
        where_clause = " AND ".join(conditions)
        
        with sqlite3.connect(compliance_validator.db_path) as conn:
            cursor = conn.execute(f"""
                SELECT 
                    report_id, report_type, title, description, 
                    reporting_period_start, reporting_period_end,
                    generated_at, generated_by, regulatory_framework, status
                FROM audit_reports 
                WHERE {where_clause}
                ORDER BY generated_at DESC
                LIMIT ?
            """, params + [limit])
            
            reports = []
            for row in cursor.fetchall():
                reports.append({
                    'report_id': row[0],
                    'report_type': row[1],
                    'title': row[2],
                    'description': row[3],
                    'reporting_period_start': row[4],
                    'reporting_period_end': row[5],
                    'generated_at': row[6],
                    'generated_by': row[7],
                    'regulatory_framework': row[8],
                    'status': row[9]
                })
        
        return JSONResponse(status_code=200, content={
            'reports': reports,
            'total_count': len(reports),
            'filters_applied': {
                'report_type': report_type,
                'generated_by': generated_by,
                'days': days
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting audit reports: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get audit reports: {str(e)}")

@router.get("/reports/{report_id}")
async def get_audit_report(report_id: str):
    """
    Get detailed audit report by ID
    """
    try:
        import sqlite3
        
        with sqlite3.connect(compliance_validator.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    report_id, report_type, title, description,
                    reporting_period_start, reporting_period_end,
                    generated_at, generated_by, regulatory_framework,
                    sections, summary, recommendations, status
                FROM audit_reports 
                WHERE report_id = ?
            """, (report_id,))
            
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Report not found")
            
            import json
            report = {
                'report_id': row[0],
                'report_type': row[1],
                'title': row[2],
                'description': row[3],
                'reporting_period_start': row[4],
                'reporting_period_end': row[5],
                'generated_at': row[6],
                'generated_by': row[7],
                'regulatory_framework': row[8],
                'sections': json.loads(row[9]),
                'summary': json.loads(row[10]),
                'recommendations': json.loads(row[11]),
                'status': row[12]
            }
        
        return JSONResponse(status_code=200, content=report)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audit report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get audit report: {str(e)}")

@router.post("/data-retention/apply")
async def apply_data_retention():
    """
    Apply data retention policies and clean up old data
    
    This endpoint should be called periodically (e.g., daily) to maintain
    compliance with data retention requirements.
    """
    try:
        results = compliance_validator.apply_data_retention_policy()
        
        return JSONResponse(status_code=200, content={
            'message': 'Data retention policy applied successfully',
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error applying data retention policy: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to apply data retention policy: {str(e)}")

@router.get("/health")
async def compliance_health_check():
    """
    Health check endpoint for compliance system
    """
    try:
        # Check database connectivity
        import sqlite3
        with sqlite3.connect(compliance_validator.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM compliance_rules WHERE enabled = 1")
            active_rules = cursor.fetchone()[0]
        
        # Check recent activity
        cursor = conn.execute("""
            SELECT COUNT(*) FROM compliance_checks 
            WHERE timestamp >= datetime('now', '-1 hour')
        """)
        recent_checks = cursor.fetchone()[0]
        
        return JSONResponse(status_code=200, content={
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'active_rules': active_rules,
            'recent_checks_last_hour': recent_checks,
            'database_path': compliance_validator.db_path
        })
        
    except Exception as e:
        logger.error(f"Compliance health check failed: {e}")
        return JSONResponse(status_code=503, content={
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })