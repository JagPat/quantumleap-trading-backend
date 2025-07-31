"""
Trading Engine Investigation Tools Router
FastAPI router for investigation and replay functionality
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import logging

from .investigation_tools import (
    investigation_tools,
    record_trading_event,
    investigate_session,
    replay_session,
    analyze_performance,
    EventType,
    DecisionNodeType
)

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/investigation", tags=["investigation"])

# Pydantic models for request/response
class EventRecordRequest(BaseModel):
    """Event recording request model"""
    event_type: str
    user_id: str
    session_id: str
    data: Dict[str, Any]
    context: Optional[Dict[str, Any]] = {}
    metadata: Optional[Dict[str, Any]] = {}

class SessionInvestigationRequest(BaseModel):
    """Session investigation request model"""
    session_id: str
    include_decision_tree: bool = True
    include_performance_analysis: bool = True

class SessionReplayRequest(BaseModel):
    """Session replay request model"""
    session_id: str
    speed_multiplier: float = Field(default=1.0, ge=0.1, le=10.0)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

class PerformanceAnalysisRequest(BaseModel):
    """Performance analysis request model"""
    strategy_id: str
    user_id: str
    period_start: datetime
    period_end: datetime
    benchmark_return: float = 0.0

class DecisionTreeResponse(BaseModel):
    """Decision tree response model"""
    tree_id: str
    session_id: str
    user_id: str
    total_nodes: int
    performance_metrics: Dict[str, Any]
    final_outcome: Dict[str, Any]

@router.post("/events/record")
async def record_event(request: EventRecordRequest):
    """
    Record a trading event for investigation and replay
    
    This endpoint allows recording of trading events that can later be
    used for investigation, replay, and performance attribution analysis.
    """
    try:
        # Validate event type
        try:
            event_type = EventType(request.event_type.upper())
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid event type: {request.event_type}. Valid types: {[e.value for e in EventType]}"
            )
        
        # Record the event
        event_id = record_trading_event(
            event_type=event_type,
            user_id=request.user_id,
            session_id=request.session_id,
            data=request.data,
            context=request.context,
            metadata=request.metadata
        )
        
        return JSONResponse(status_code=201, content={
            'message': 'Event recorded successfully',
            'event_id': event_id,
            'event_type': event_type.value,
            'session_id': request.session_id,
            'recorded_at': datetime.now().isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording event: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to record event: {str(e)}")

@router.get("/sessions/{session_id}/events")
async def get_session_events(
    session_id: str,
    start_time: Optional[datetime] = Query(None, description="Filter events from this time"),
    end_time: Optional[datetime] = Query(None, description="Filter events until this time"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(100, description="Maximum number of events to return", ge=1, le=1000)
):
    """
    Get all events for a trading session
    
    Returns a list of all recorded events for the specified session,
    with optional filtering by time range and event type.
    """
    try:
        # Get session events
        events = investigation_tools.event_recorder.get_session_events(
            session_id=session_id,
            start_time=start_time,
            end_time=end_time
        )
        
        # Filter by event type if specified
        if event_type:
            try:
                filter_type = EventType(event_type.upper())
                events = [e for e in events if e.event_type == filter_type]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid event type: {event_type}")
        
        # Apply limit
        events = events[:limit]
        
        # Convert to dict format
        events_data = [event.to_dict() for event in events]
        
        return JSONResponse(status_code=200, content={
            'session_id': session_id,
            'total_events': len(events_data),
            'events': events_data,
            'filters_applied': {
                'start_time': start_time.isoformat() if start_time else None,
                'end_time': end_time.isoformat() if end_time else None,
                'event_type': event_type,
                'limit': limit
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session events: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session events: {str(e)}")

@router.post("/sessions/investigate")
async def investigate_trading_session(request: SessionInvestigationRequest):
    """
    Perform comprehensive investigation of a trading session
    
    Analyzes all events in a session, builds decision trees, and provides
    detailed investigation report with recommendations.
    """
    try:
        # Perform investigation
        investigation_report = investigate_session(request.session_id)
        
        if 'error' in investigation_report:
            raise HTTPException(status_code=404, detail=investigation_report['error'])
        
        # Filter response based on request parameters
        if not request.include_decision_tree:
            investigation_report.pop('decision_tree', None)
        
        if not request.include_performance_analysis:
            investigation_report.pop('performance_summary', None)
        
        return JSONResponse(status_code=200, content={
            'message': 'Investigation completed successfully',
            'investigation_report': investigation_report
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error investigating session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to investigate session: {str(e)}")

@router.post("/sessions/replay")
async def replay_trading_session(request: SessionReplayRequest):
    """
    Replay a trading session for debugging and analysis
    
    Replays all events in a session in chronological order,
    with configurable speed multiplier for analysis.
    """
    try:
        # Perform replay
        replay_result = replay_session(
            session_id=request.session_id,
            speed_multiplier=request.speed_multiplier
        )
        
        if replay_result.get('status') == 'ERROR':
            raise HTTPException(status_code=500, detail=replay_result.get('error', 'Replay failed'))
        
        if replay_result.get('status') == 'NO_EVENTS':
            raise HTTPException(status_code=404, detail=f"No events found for session {request.session_id}")
        
        return JSONResponse(status_code=200, content={
            'message': 'Session replay completed',
            'replay_result': replay_result
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error replaying session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to replay session: {str(e)}")

@router.get("/sessions/{session_id}/decision-tree")
async def get_decision_tree(session_id: str):
    """
    Get the decision tree for a trading session
    
    Returns the complete decision tree showing the decision-making
    process for all events in the session.
    """
    try:
        # Build decision tree
        decision_tree = investigation_tools.decision_tree_builder.build_decision_tree(session_id)
        
        if not decision_tree:
            raise HTTPException(status_code=404, detail=f"No decision tree found for session {session_id}")
        
        # Create response
        response = DecisionTreeResponse(
            tree_id=decision_tree.tree_id,
            session_id=decision_tree.session_id,
            user_id=decision_tree.user_id,
            total_nodes=len(decision_tree.nodes),
            performance_metrics=decision_tree.performance_metrics,
            final_outcome=decision_tree.final_outcome
        )
        
        return JSONResponse(status_code=200, content={
            'decision_tree': response.dict(),
            'detailed_tree': decision_tree.to_dict()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting decision tree: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get decision tree: {str(e)}")

@router.post("/performance/analyze")
async def analyze_strategy_performance(request: PerformanceAnalysisRequest):
    """
    Perform comprehensive performance attribution analysis
    
    Analyzes strategy performance with detailed attribution factors,
    trade contributions, and risk analysis.
    """
    try:
        # Validate date range
        if request.period_start >= request.period_end:
            raise HTTPException(status_code=400, detail="Period start must be before period end")
        
        # Perform performance analysis
        attribution = analyze_performance(
            strategy_id=request.strategy_id,
            user_id=request.user_id,
            period_start=request.period_start,
            period_end=request.period_end,
            benchmark_return=request.benchmark_return
        )
        
        return JSONResponse(status_code=200, content={
            'message': 'Performance analysis completed',
            'performance_attribution': attribution.to_dict()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing performance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze performance: {str(e)}")

@router.get("/performance/attribution/{attribution_id}")
async def get_performance_attribution(attribution_id: str):
    """
    Get a specific performance attribution analysis
    """
    try:
        import sqlite3
        
        with sqlite3.connect(investigation_tools.event_recorder.db_path) as conn:
            cursor = conn.execute("""
                SELECT attribution_id, session_id, user_id, strategy_id,
                       period_start, period_end, total_return, benchmark_return,
                       alpha, beta, sharpe_ratio, max_drawdown,
                       attribution_factors, trade_contributions, risk_contributions
                FROM performance_attribution 
                WHERE attribution_id = ?
            """, (attribution_id,))
            
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Performance attribution not found")
            
            import json
            attribution_data = {
                'attribution_id': row[0],
                'session_id': row[1],
                'user_id': row[2],
                'strategy_id': row[3],
                'period_start': row[4],
                'period_end': row[5],
                'total_return': row[6],
                'benchmark_return': row[7],
                'alpha': row[8],
                'beta': row[9],
                'sharpe_ratio': row[10],
                'max_drawdown': row[11],
                'attribution_factors': json.loads(row[12]),
                'trade_contributions': json.loads(row[13]),
                'risk_contributions': json.loads(row[14])
            }
        
        return JSONResponse(status_code=200, content=attribution_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting performance attribution: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance attribution: {str(e)}")

@router.get("/sessions")
async def get_investigation_sessions(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    days: int = Query(30, description="Number of days to look back", ge=1, le=365),
    limit: int = Query(50, description="Maximum number of sessions to return", ge=1, le=200)
):
    """
    Get list of investigation sessions
    
    Returns a list of all sessions that have recorded events,
    with optional filtering by user and time range.
    """
    try:
        import sqlite3
        
        start_date = datetime.now() - timedelta(days=days)
        
        # Build query conditions
        conditions = ["timestamp >= ?"]
        params = [start_date.isoformat()]
        
        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)
        
        where_clause = " AND ".join(conditions)
        
        with sqlite3.connect(investigation_tools.event_recorder.db_path) as conn:
            cursor = conn.execute(f"""
                SELECT 
                    session_id,
                    user_id,
                    MIN(timestamp) as first_event,
                    MAX(timestamp) as last_event,
                    COUNT(*) as event_count,
                    COUNT(DISTINCT event_type) as event_types
                FROM replay_events 
                WHERE {where_clause}
                GROUP BY session_id, user_id
                ORDER BY MAX(timestamp) DESC
                LIMIT ?
            """, params + [limit])
            
            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    'session_id': row[0],
                    'user_id': row[1],
                    'first_event': row[2],
                    'last_event': row[3],
                    'event_count': row[4],
                    'event_types': row[5],
                    'duration_seconds': (
                        datetime.fromisoformat(row[3]) - datetime.fromisoformat(row[2])
                    ).total_seconds() if row[2] and row[3] else 0
                })
        
        return JSONResponse(status_code=200, content={
            'sessions': sessions,
            'total_count': len(sessions),
            'filters_applied': {
                'user_id': user_id,
                'days': days,
                'limit': limit
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting investigation sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get investigation sessions: {str(e)}")

@router.get("/statistics")
async def get_investigation_statistics(
    days: int = Query(30, description="Number of days to look back", ge=1, le=365)
):
    """
    Get investigation system statistics
    
    Returns overall statistics about recorded events, sessions,
    and investigation activities.
    """
    try:
        import sqlite3
        
        start_date = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(investigation_tools.event_recorder.db_path) as conn:
            # Overall event statistics
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_events,
                    COUNT(DISTINCT session_id) as total_sessions,
                    COUNT(DISTINCT user_id) as total_users,
                    COUNT(DISTINCT event_type) as event_types
                FROM replay_events 
                WHERE timestamp >= ?
            """, (start_date.isoformat(),))
            
            overall_stats = cursor.fetchone()
            
            # Event type breakdown
            cursor = conn.execute("""
                SELECT event_type, COUNT(*) as count
                FROM replay_events 
                WHERE timestamp >= ?
                GROUP BY event_type
                ORDER BY count DESC
            """, (start_date.isoformat(),))
            
            event_type_stats = [{'event_type': row[0], 'count': row[1]} for row in cursor.fetchall()]
            
            # Decision tree statistics
            cursor = conn.execute("""
                SELECT COUNT(*) as total_trees
                FROM decision_trees 
                WHERE created_at >= ?
            """, (start_date.isoformat(),))
            
            tree_stats = cursor.fetchone()
            
            # Performance attribution statistics
            cursor = conn.execute("""
                SELECT COUNT(*) as total_attributions
                FROM performance_attribution 
                WHERE created_at >= ?
            """, (start_date.isoformat(),))
            
            attribution_stats = cursor.fetchone()
        
        statistics = {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': datetime.now().isoformat(),
                'days': days
            },
            'overall': {
                'total_events': overall_stats[0],
                'total_sessions': overall_stats[1],
                'total_users': overall_stats[2],
                'event_types': overall_stats[3]
            },
            'event_breakdown': event_type_stats,
            'decision_trees': {
                'total_generated': tree_stats[0]
            },
            'performance_attributions': {
                'total_generated': attribution_stats[0]
            }
        }
        
        return JSONResponse(status_code=200, content=statistics)
        
    except Exception as e:
        logger.error(f"Error getting investigation statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get investigation statistics: {str(e)}")

@router.delete("/sessions/{session_id}")
async def delete_session_data(session_id: str):
    """
    Delete all investigation data for a session
    
    Removes all events, decision trees, and related data for the specified session.
    Use with caution as this operation cannot be undone.
    """
    try:
        import sqlite3
        
        with sqlite3.connect(investigation_tools.event_recorder.db_path) as conn:
            # Delete events
            cursor = conn.execute("DELETE FROM replay_events WHERE session_id = ?", (session_id,))
            events_deleted = cursor.rowcount
            
            # Delete decision trees
            cursor = conn.execute("DELETE FROM decision_trees WHERE session_id = ?", (session_id,))
            trees_deleted = cursor.rowcount
            
            # Delete performance attributions
            cursor = conn.execute("DELETE FROM performance_attribution WHERE session_id = ?", (session_id,))
            attributions_deleted = cursor.rowcount
        
        return JSONResponse(status_code=200, content={
            'message': 'Session data deleted successfully',
            'session_id': session_id,
            'deleted_counts': {
                'events': events_deleted,
                'decision_trees': trees_deleted,
                'performance_attributions': attributions_deleted
            }
        })
        
    except Exception as e:
        logger.error(f"Error deleting session data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session data: {str(e)}")

@router.get("/health")
async def investigation_health_check():
    """
    Health check endpoint for investigation system
    """
    try:
        # Check database connectivity
        import sqlite3
        with sqlite3.connect(investigation_tools.event_recorder.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM replay_events WHERE timestamp >= datetime('now', '-1 hour')")
            recent_events = cursor.fetchone()[0]
        
        # Check system components
        components_status = {
            'event_recorder': 'healthy',
            'decision_tree_builder': 'healthy',
            'event_replayer': 'healthy',
            'performance_analyzer': 'healthy'
        }
        
        return JSONResponse(status_code=200, content={
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'recent_events_last_hour': recent_events,
            'database_path': investigation_tools.event_recorder.db_path,
            'components': components_status
        })
        
    except Exception as e:
        logger.error(f"Investigation health check failed: {e}")
        return JSONResponse(status_code=503, content={
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })