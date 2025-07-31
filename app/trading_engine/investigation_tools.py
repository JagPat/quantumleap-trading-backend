"""
Trading Engine Investigation and Replay Tools
Provides decision tree reconstruction, event replay, and performance attribution analysis
"""
import json
import logging
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import uuid
import pickle
import gzip
from collections import defaultdict, deque

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EventType(Enum):
    """Types of events that can be replayed"""
    SIGNAL_GENERATED = "SIGNAL_GENERATED"
    ORDER_PLACED = "ORDER_PLACED"
    ORDER_EXECUTED = "ORDER_EXECUTED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    POSITION_UPDATED = "POSITION_UPDATED"
    RISK_CHECK = "RISK_CHECK"
    COMPLIANCE_CHECK = "COMPLIANCE_CHECK"
    STRATEGY_DEPLOYED = "STRATEGY_DEPLOYED"
    STRATEGY_PAUSED = "STRATEGY_PAUSED"
    MARKET_DATA_UPDATE = "MARKET_DATA_UPDATE"
    PERFORMANCE_UPDATE = "PERFORMANCE_UPDATE"

class DecisionNodeType(Enum):
    """Types of decision nodes in the decision tree"""
    ROOT = "ROOT"
    SIGNAL_ANALYSIS = "SIGNAL_ANALYSIS"
    RISK_ASSESSMENT = "RISK_ASSESSMENT"
    COMPLIANCE_CHECK = "COMPLIANCE_CHECK"
    POSITION_SIZING = "POSITION_SIZING"
    ORDER_EXECUTION = "ORDER_EXECUTION"
    PERFORMANCE_ATTRIBUTION = "PERFORMANCE_ATTRIBUTION"
    FINAL_OUTCOME = "FINAL_OUTCOME"

@dataclass
class ReplayEvent:
    """Event that can be replayed"""
    event_id: str
    event_type: EventType
    timestamp: datetime
    user_id: str
    session_id: str
    data: Dict[str, Any]
    context: Dict[str, Any]
    metadata: Dict[str, Any]
    sequence_number: int
    parent_event_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'session_id': self.session_id,
            'data': self.data,
            'context': self.context,
            'metadata': self.metadata,
            'sequence_number': self.sequence_number,
            'parent_event_id': self.parent_event_id
        }

@dataclass
class DecisionNode:
    """Node in the decision tree"""
    node_id: str
    node_type: DecisionNodeType
    timestamp: datetime
    description: str
    input_data: Dict[str, Any]
    decision_logic: str
    output_data: Dict[str, Any]
    confidence_score: float
    execution_time_ms: float
    parent_node_id: Optional[str] = None
    child_node_ids: List[str] = None
    
    def __post_init__(self):
        if self.child_node_ids is None:
            self.child_node_ids = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'node_id': self.node_id,
            'node_type': self.node_type.value,
            'timestamp': self.timestamp.isoformat(),
            'description': self.description,
            'input_data': self.input_data,
            'decision_logic': self.decision_logic,
            'output_data': self.output_data,
            'confidence_score': self.confidence_score,
            'execution_time_ms': self.execution_time_ms,
            'parent_node_id': self.parent_node_id,
            'child_node_ids': self.child_node_ids
        }

@dataclass
class DecisionTree:
    """Complete decision tree for a trading decision"""
    tree_id: str
    root_node_id: str
    session_id: str
    user_id: str
    created_at: datetime
    completed_at: Optional[datetime]
    nodes: Dict[str, DecisionNode]
    final_outcome: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'tree_id': self.tree_id,
            'root_node_id': self.root_node_id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'nodes': {node_id: node.to_dict() for node_id, node in self.nodes.items()},
            'final_outcome': self.final_outcome,
            'performance_metrics': self.performance_metrics
        }

@dataclass
class PerformanceAttribution:
    """Performance attribution analysis"""
    attribution_id: str
    session_id: str
    user_id: str
    strategy_id: str
    period_start: datetime
    period_end: datetime
    total_return: float
    benchmark_return: float
    alpha: float
    beta: float
    sharpe_ratio: float
    max_drawdown: float
    attribution_factors: Dict[str, float]
    trade_contributions: List[Dict[str, Any]]
    risk_contributions: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'attribution_id': self.attribution_id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'strategy_id': self.strategy_id,
            'period_start': self.period_start.isoformat(),
            'period_end': self.period_end.isoformat(),
            'total_return': self.total_return,
            'benchmark_return': self.benchmark_return,
            'alpha': self.alpha,
            'beta': self.beta,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'attribution_factors': self.attribution_factors,
            'trade_contributions': self.trade_contributions,
            'risk_contributions': self.risk_contributions
        }

class EventRecorder:
    """Records events for replay functionality"""
    
    def __init__(self, db_path: str = "investigation.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize investigation database"""
        with sqlite3.connect(self.db_path) as conn:
            # Replay events table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS replay_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    context TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    sequence_number INTEGER NOT NULL,
                    parent_event_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Decision trees table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS decision_trees (
                    tree_id TEXT PRIMARY KEY,
                    root_node_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    nodes TEXT NOT NULL,
                    final_outcome TEXT NOT NULL,
                    performance_metrics TEXT NOT NULL,
                    created_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Performance attribution table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_attribution (
                    attribution_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    strategy_id TEXT NOT NULL,
                    period_start TIMESTAMP NOT NULL,
                    period_end TIMESTAMP NOT NULL,
                    total_return REAL NOT NULL,
                    benchmark_return REAL NOT NULL,
                    alpha REAL NOT NULL,
                    beta REAL NOT NULL,
                    sharpe_ratio REAL NOT NULL,
                    max_drawdown REAL NOT NULL,
                    attribution_factors TEXT NOT NULL,
                    trade_contributions TEXT NOT NULL,
                    risk_contributions TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_events_session ON replay_events(session_id, timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_events_user ON replay_events(user_id, timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_events_type ON replay_events(event_type, timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_trees_session ON decision_trees(session_id, created_at)",
                "CREATE INDEX IF NOT EXISTS idx_attribution_strategy ON performance_attribution(strategy_id, period_start)"
            ]
            
            for index_sql in indexes:
                conn.execute(index_sql)
    
    def record_event(self, event: ReplayEvent) -> bool:
        """Record an event for replay"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO replay_events
                        (event_id, event_type, timestamp, user_id, session_id,
                         data, context, metadata, sequence_number, parent_event_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        event.event_id,
                        event.event_type.value,
                        event.timestamp.isoformat(),
                        event.user_id,
                        event.session_id,
                        json.dumps(event.data),
                        json.dumps(event.context),
                        json.dumps(event.metadata),
                        event.sequence_number,
                        event.parent_event_id
                    ))
                
                logger.info(f"Recorded event: {event.event_type.value} for session {event.session_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to record event: {e}")
            return False
    
    def get_session_events(self, session_id: str, 
                          start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None) -> List[ReplayEvent]:
        """Get all events for a session"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conditions = ["session_id = ?"]
                params = [session_id]
                
                if start_time:
                    conditions.append("timestamp >= ?")
                    params.append(start_time.isoformat())
                
                if end_time:
                    conditions.append("timestamp <= ?")
                    params.append(end_time.isoformat())
                
                where_clause = " AND ".join(conditions)
                
                cursor = conn.execute(f"""
                    SELECT event_id, event_type, timestamp, user_id, session_id,
                           data, context, metadata, sequence_number, parent_event_id
                    FROM replay_events 
                    WHERE {where_clause}
                    ORDER BY sequence_number
                """, params)
                
                events = []
                for row in cursor.fetchall():
                    event = ReplayEvent(
                        event_id=row[0],
                        event_type=EventType(row[1]),
                        timestamp=datetime.fromisoformat(row[2]),
                        user_id=row[3],
                        session_id=row[4],
                        data=json.loads(row[5]),
                        context=json.loads(row[6]),
                        metadata=json.loads(row[7]),
                        sequence_number=row[8],
                        parent_event_id=row[9]
                    )
                    events.append(event)
                
                return events
                
        except Exception as e:
            logger.error(f"Failed to get session events: {e}")
            return []

class DecisionTreeBuilder:
    """Builds decision trees for trade investigation"""
    
    def __init__(self, event_recorder: EventRecorder):
        self.event_recorder = event_recorder
        self.lock = threading.Lock()
    
    def build_decision_tree(self, session_id: str, 
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None) -> Optional[DecisionTree]:
        """Build decision tree from session events"""
        try:
            # Get session events
            events = self.event_recorder.get_session_events(session_id, start_time, end_time)
            
            if not events:
                logger.warning(f"No events found for session {session_id}")
                return None
            
            # Create decision tree
            tree_id = str(uuid.uuid4())
            user_id = events[0].user_id
            created_at = events[0].timestamp
            completed_at = events[-1].timestamp
            
            # Build nodes from events
            nodes = {}
            root_node_id = None
            
            for i, event in enumerate(events):
                node_id = str(uuid.uuid4())
                
                # Determine node type based on event type
                node_type = self._get_node_type_from_event(event.event_type)
                
                # Create decision node
                node = DecisionNode(
                    node_id=node_id,
                    node_type=node_type,
                    timestamp=event.timestamp,
                    description=self._generate_node_description(event),
                    input_data=event.context,
                    decision_logic=self._extract_decision_logic(event),
                    output_data=event.data,
                    confidence_score=event.metadata.get('confidence', 1.0),
                    execution_time_ms=event.metadata.get('execution_time_ms', 0.0),
                    parent_node_id=None if i == 0 else nodes[list(nodes.keys())[-1]].node_id
                )
                
                # Set parent-child relationships
                if i > 0:
                    parent_node = nodes[list(nodes.keys())[-1]]
                    parent_node.child_node_ids.append(node_id)
                else:
                    root_node_id = node_id
                
                nodes[node_id] = node
            
            # Calculate performance metrics
            performance_metrics = self._calculate_tree_performance_metrics(events)
            
            # Determine final outcome
            final_outcome = self._determine_final_outcome(events)
            
            # Create decision tree
            decision_tree = DecisionTree(
                tree_id=tree_id,
                root_node_id=root_node_id,
                session_id=session_id,
                user_id=user_id,
                created_at=created_at,
                completed_at=completed_at,
                nodes=nodes,
                final_outcome=final_outcome,
                performance_metrics=performance_metrics
            )
            
            # Save decision tree
            self._save_decision_tree(decision_tree)
            
            return decision_tree
            
        except Exception as e:
            logger.error(f"Failed to build decision tree: {e}")
            return None
    
    def _get_node_type_from_event(self, event_type: EventType) -> DecisionNodeType:
        """Map event type to decision node type"""
        mapping = {
            EventType.SIGNAL_GENERATED: DecisionNodeType.SIGNAL_ANALYSIS,
            EventType.RISK_CHECK: DecisionNodeType.RISK_ASSESSMENT,
            EventType.COMPLIANCE_CHECK: DecisionNodeType.COMPLIANCE_CHECK,
            EventType.ORDER_PLACED: DecisionNodeType.ORDER_EXECUTION,
            EventType.ORDER_EXECUTED: DecisionNodeType.ORDER_EXECUTION,
            EventType.POSITION_UPDATED: DecisionNodeType.POSITION_SIZING,
            EventType.PERFORMANCE_UPDATE: DecisionNodeType.PERFORMANCE_ATTRIBUTION
        }
        return mapping.get(event_type, DecisionNodeType.ROOT)
    
    def _generate_node_description(self, event: ReplayEvent) -> str:
        """Generate human-readable description for decision node"""
        descriptions = {
            EventType.SIGNAL_GENERATED: f"AI signal generated for {event.data.get('symbol', 'unknown')}",
            EventType.ORDER_PLACED: f"Order placed: {event.data.get('side', '')} {event.data.get('quantity', 0)} {event.data.get('symbol', '')}",
            EventType.ORDER_EXECUTED: f"Order executed at {event.data.get('price', 0)}",
            EventType.RISK_CHECK: f"Risk assessment: {event.data.get('risk_level', 'unknown')}",
            EventType.COMPLIANCE_CHECK: f"Compliance check: {'PASSED' if event.data.get('compliant', False) else 'FAILED'}",
            EventType.POSITION_UPDATED: f"Position updated: {event.data.get('position_size', 0)} shares"
        }
        return descriptions.get(event.event_type, f"Event: {event.event_type.value}")
    
    def _extract_decision_logic(self, event: ReplayEvent) -> str:
        """Extract decision logic from event"""
        logic_patterns = {
            EventType.SIGNAL_GENERATED: "AI model prediction based on market data analysis",
            EventType.RISK_CHECK: "Risk assessment using portfolio metrics and volatility",
            EventType.COMPLIANCE_CHECK: "Regulatory compliance validation against rules",
            EventType.ORDER_PLACED: "Order placement based on signal confidence and risk limits",
            EventType.POSITION_UPDATED: "Position sizing based on risk tolerance and signal strength"
        }
        
        base_logic = logic_patterns.get(event.event_type, "Standard processing logic")
        
        # Add specific parameters if available
        if 'logic' in event.metadata:
            return f"{base_logic}: {event.metadata['logic']}"
        
        return base_logic
    
    def _calculate_tree_performance_metrics(self, events: List[ReplayEvent]) -> Dict[str, Any]:
        """Calculate performance metrics for the decision tree"""
        metrics = {
            'total_events': len(events),
            'execution_time_ms': sum(event.metadata.get('execution_time_ms', 0) for event in events),
            'success_rate': 0.0,
            'error_count': 0,
            'decision_accuracy': 0.0
        }
        
        # Count successful vs failed events
        successful_events = sum(1 for event in events if event.metadata.get('success', True))
        metrics['success_rate'] = (successful_events / len(events)) * 100 if events else 0
        metrics['error_count'] = len(events) - successful_events
        
        # Calculate decision accuracy based on final outcomes
        final_events = [e for e in events if e.event_type in [EventType.ORDER_EXECUTED, EventType.PERFORMANCE_UPDATE]]
        if final_events:
            positive_outcomes = sum(1 for event in final_events if event.data.get('pnl', 0) > 0)
            metrics['decision_accuracy'] = (positive_outcomes / len(final_events)) * 100
        
        return metrics
    
    def _determine_final_outcome(self, events: List[ReplayEvent]) -> Dict[str, Any]:
        """Determine the final outcome of the decision sequence"""
        outcome = {
            'status': 'COMPLETED',
            'total_pnl': 0.0,
            'orders_executed': 0,
            'positions_opened': 0,
            'risk_violations': 0,
            'compliance_violations': 0
        }
        
        for event in events:
            if event.event_type == EventType.ORDER_EXECUTED:
                outcome['orders_executed'] += 1
                outcome['total_pnl'] += event.data.get('pnl', 0.0)
            
            elif event.event_type == EventType.POSITION_UPDATED:
                if event.data.get('position_size', 0) > 0:
                    outcome['positions_opened'] += 1
            
            elif event.event_type == EventType.RISK_CHECK:
                if not event.data.get('passed', True):
                    outcome['risk_violations'] += 1
            
            elif event.event_type == EventType.COMPLIANCE_CHECK:
                if not event.data.get('compliant', True):
                    outcome['compliance_violations'] += 1
        
        # Determine overall status
        if outcome['risk_violations'] > 0 or outcome['compliance_violations'] > 0:
            outcome['status'] = 'FAILED_COMPLIANCE'
        elif outcome['total_pnl'] < 0:
            outcome['status'] = 'COMPLETED_LOSS'
        elif outcome['total_pnl'] > 0:
            outcome['status'] = 'COMPLETED_PROFIT'
        
        return outcome
    
    def _save_decision_tree(self, tree: DecisionTree):
        """Save decision tree to database"""
        try:
            with sqlite3.connect(self.event_recorder.db_path) as conn:
                conn.execute("""
                    INSERT INTO decision_trees
                    (tree_id, root_node_id, session_id, user_id, created_at,
                     completed_at, nodes, final_outcome, performance_metrics)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tree.tree_id,
                    tree.root_node_id,
                    tree.session_id,
                    tree.user_id,
                    tree.created_at.isoformat(),
                    tree.completed_at.isoformat() if tree.completed_at else None,
                    json.dumps({node_id: node.to_dict() for node_id, node in tree.nodes.items()}),
                    json.dumps(tree.final_outcome),
                    json.dumps(tree.performance_metrics)
                ))
        except Exception as e:
            logger.error(f"Failed to save decision tree: {e}")

class EventReplayer:
    """Replays events for debugging and analysis"""
    
    def __init__(self, event_recorder: EventRecorder):
        self.event_recorder = event_recorder
        self.replay_handlers = {}
        self.lock = threading.Lock()
    
    def register_replay_handler(self, event_type: EventType, handler: callable):
        """Register a handler for replaying specific event types"""
        with self.lock:
            self.replay_handlers[event_type] = handler
    
    def replay_session(self, session_id: str, 
                      start_time: Optional[datetime] = None,
                      end_time: Optional[datetime] = None,
                      speed_multiplier: float = 1.0) -> Dict[str, Any]:
        """Replay all events in a session"""
        try:
            # Get session events
            events = self.event_recorder.get_session_events(session_id, start_time, end_time)
            
            if not events:
                return {'status': 'NO_EVENTS', 'events_replayed': 0}
            
            replay_results = {
                'session_id': session_id,
                'events_replayed': 0,
                'successful_replays': 0,
                'failed_replays': 0,
                'replay_duration_ms': 0,
                'event_results': []
            }
            
            start_replay_time = datetime.now()
            
            for event in events:
                try:
                    # Simulate timing if speed_multiplier is not 1.0
                    if speed_multiplier != 1.0 and len(replay_results['event_results']) > 0:
                        import time
                        prev_event = events[len(replay_results['event_results']) - 1]
                        time_diff = (event.timestamp - prev_event.timestamp).total_seconds()
                        time.sleep(time_diff / speed_multiplier)
                    
                    # Replay the event
                    result = self._replay_event(event)
                    
                    replay_results['event_results'].append({
                        'event_id': event.event_id,
                        'event_type': event.event_type.value,
                        'timestamp': event.timestamp.isoformat(),
                        'replay_result': result,
                        'success': result.get('success', False)
                    })
                    
                    if result.get('success', False):
                        replay_results['successful_replays'] += 1
                    else:
                        replay_results['failed_replays'] += 1
                    
                    replay_results['events_replayed'] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to replay event {event.event_id}: {e}")
                    replay_results['failed_replays'] += 1
                    replay_results['event_results'].append({
                        'event_id': event.event_id,
                        'event_type': event.event_type.value,
                        'error': str(e),
                        'success': False
                    })
            
            end_replay_time = datetime.now()
            replay_results['replay_duration_ms'] = (end_replay_time - start_replay_time).total_seconds() * 1000
            replay_results['status'] = 'COMPLETED'
            
            return replay_results
            
        except Exception as e:
            logger.error(f"Failed to replay session: {e}")
            return {'status': 'ERROR', 'error': str(e)}
    
    def _replay_event(self, event: ReplayEvent) -> Dict[str, Any]:
        """Replay a single event"""
        try:
            # Check if we have a specific handler for this event type
            handler = self.replay_handlers.get(event.event_type)
            
            if handler:
                # Use custom handler
                result = handler(event)
            else:
                # Use default replay logic
                result = self._default_replay_handler(event)
            
            return {
                'success': True,
                'result': result,
                'replayed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'replayed_at': datetime.now().isoformat()
            }
    
    def _default_replay_handler(self, event: ReplayEvent) -> Dict[str, Any]:
        """Default handler for replaying events"""
        return {
            'event_type': event.event_type.value,
            'data_processed': len(event.data),
            'context_items': len(event.context),
            'metadata_items': len(event.metadata),
            'replay_method': 'default'
        }

class PerformanceAttributionAnalyzer:
    """Analyzes performance attribution with complete audit trails"""
    
    def __init__(self, event_recorder: EventRecorder):
        self.event_recorder = event_recorder
        self.lock = threading.Lock()
    
    def analyze_performance_attribution(self, strategy_id: str, user_id: str,
                                      period_start: datetime, period_end: datetime,
                                      benchmark_return: float = 0.0) -> PerformanceAttribution:
        """Perform comprehensive performance attribution analysis"""
        try:
            attribution_id = str(uuid.uuid4())
            
            # Get all relevant events for the period
            events = self._get_strategy_events(strategy_id, user_id, period_start, period_end)
            
            # Calculate basic performance metrics
            total_return = self._calculate_total_return(events)
            alpha = total_return - benchmark_return
            beta = self._calculate_beta(events, benchmark_return)
            sharpe_ratio = self._calculate_sharpe_ratio(events)
            max_drawdown = self._calculate_max_drawdown(events)
            
            # Analyze attribution factors
            attribution_factors = self._analyze_attribution_factors(events)
            
            # Analyze individual trade contributions
            trade_contributions = self._analyze_trade_contributions(events)
            
            # Analyze risk contributions
            risk_contributions = self._analyze_risk_contributions(events)
            
            # Create performance attribution
            attribution = PerformanceAttribution(
                attribution_id=attribution_id,
                session_id=f"attribution_{strategy_id}_{int(period_start.timestamp())}",
                user_id=user_id,
                strategy_id=strategy_id,
                period_start=period_start,
                period_end=period_end,
                total_return=total_return,
                benchmark_return=benchmark_return,
                alpha=alpha,
                beta=beta,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                attribution_factors=attribution_factors,
                trade_contributions=trade_contributions,
                risk_contributions=risk_contributions
            )
            
            # Save attribution analysis
            self._save_performance_attribution(attribution)
            
            return attribution
            
        except Exception as e:
            logger.error(f"Failed to analyze performance attribution: {e}")
            raise
    
    def _get_strategy_events(self, strategy_id: str, user_id: str,
                           period_start: datetime, period_end: datetime) -> List[ReplayEvent]:
        """Get all events related to a strategy in the given period"""
        try:
            with sqlite3.connect(self.event_recorder.db_path) as conn:
                cursor = conn.execute("""
                    SELECT event_id, event_type, timestamp, user_id, session_id,
                           data, context, metadata, sequence_number, parent_event_id
                    FROM replay_events 
                    WHERE user_id = ? 
                    AND timestamp BETWEEN ? AND ?
                    AND (JSON_EXTRACT(data, '$.strategy_id') = ? OR JSON_EXTRACT(context, '$.strategy_id') = ?)
                    ORDER BY timestamp
                """, (user_id, period_start.isoformat(), period_end.isoformat(), strategy_id, strategy_id))
                
                events = []
                for row in cursor.fetchall():
                    event = ReplayEvent(
                        event_id=row[0],
                        event_type=EventType(row[1]),
                        timestamp=datetime.fromisoformat(row[2]),
                        user_id=row[3],
                        session_id=row[4],
                        data=json.loads(row[5]),
                        context=json.loads(row[6]),
                        metadata=json.loads(row[7]),
                        sequence_number=row[8],
                        parent_event_id=row[9]
                    )
                    events.append(event)
                
                return events
                
        except Exception as e:
            logger.error(f"Failed to get strategy events: {e}")
            return []
    
    def _calculate_total_return(self, events: List[ReplayEvent]) -> float:
        """Calculate total return from events"""
        total_pnl = 0.0
        initial_capital = 100000.0  # Default initial capital
        
        for event in events:
            if event.event_type == EventType.ORDER_EXECUTED:
                pnl = event.data.get('pnl', 0.0)
                total_pnl += pnl
            elif event.event_type == EventType.PERFORMANCE_UPDATE:
                total_pnl = event.data.get('total_pnl', total_pnl)
                initial_capital = event.data.get('initial_capital', initial_capital)
        
        return (total_pnl / initial_capital) * 100 if initial_capital > 0 else 0.0
    
    def _calculate_beta(self, events: List[ReplayEvent], benchmark_return: float) -> float:
        """Calculate beta relative to benchmark"""
        # Simplified beta calculation
        # In a real implementation, this would use covariance with benchmark
        returns = []
        for event in events:
            if event.event_type == EventType.PERFORMANCE_UPDATE:
                returns.append(event.data.get('period_return', 0.0))
        
        if not returns or benchmark_return == 0:
            return 1.0
        
        # Simple correlation-based beta approximation
        avg_return = sum(returns) / len(returns)
        return avg_return / benchmark_return if benchmark_return != 0 else 1.0
    
    def _calculate_sharpe_ratio(self, events: List[ReplayEvent]) -> float:
        """Calculate Sharpe ratio"""
        returns = []
        for event in events:
            if event.event_type == EventType.PERFORMANCE_UPDATE:
                returns.append(event.data.get('period_return', 0.0))
        
        if len(returns) < 2:
            return 0.0
        
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = variance ** 0.5
        
        return avg_return / std_dev if std_dev > 0 else 0.0
    
    def _calculate_max_drawdown(self, events: List[ReplayEvent]) -> float:
        """Calculate maximum drawdown"""
        portfolio_values = []
        current_value = 100000.0  # Starting value
        
        for event in events:
            if event.event_type == EventType.PERFORMANCE_UPDATE:
                current_value = event.data.get('portfolio_value', current_value)
                portfolio_values.append(current_value)
        
        if len(portfolio_values) < 2:
            return 0.0
        
        peak = portfolio_values[0]
        max_drawdown = 0.0
        
        for value in portfolio_values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak * 100
            max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown
    
    def _analyze_attribution_factors(self, events: List[ReplayEvent]) -> Dict[str, float]:
        """Analyze performance attribution factors"""
        factors = {
            'signal_quality': 0.0,
            'execution_efficiency': 0.0,
            'risk_management': 0.0,
            'market_timing': 0.0,
            'position_sizing': 0.0
        }
        
        signal_events = [e for e in events if e.event_type == EventType.SIGNAL_GENERATED]
        execution_events = [e for e in events if e.event_type == EventType.ORDER_EXECUTED]
        risk_events = [e for e in events if e.event_type == EventType.RISK_CHECK]
        
        # Signal quality factor
        if signal_events:
            avg_confidence = sum(e.metadata.get('confidence', 0.5) for e in signal_events) / len(signal_events)
            factors['signal_quality'] = (avg_confidence - 0.5) * 100  # Convert to percentage contribution
        
        # Execution efficiency factor
        if execution_events:
            avg_slippage = sum(abs(e.data.get('slippage', 0.0)) for e in execution_events) / len(execution_events)
            factors['execution_efficiency'] = max(0, (1 - avg_slippage) * 50)  # Inverse of slippage
        
        # Risk management factor
        if risk_events:
            risk_passed = sum(1 for e in risk_events if e.data.get('passed', True))
            factors['risk_management'] = (risk_passed / len(risk_events)) * 30
        
        # Market timing factor (simplified)
        factors['market_timing'] = 20.0  # Placeholder
        
        # Position sizing factor (simplified)
        factors['position_sizing'] = 15.0  # Placeholder
        
        return factors
    
    def _analyze_trade_contributions(self, events: List[ReplayEvent]) -> List[Dict[str, Any]]:
        """Analyze individual trade contributions"""
        contributions = []
        
        execution_events = [e for e in events if e.event_type == EventType.ORDER_EXECUTED]
        
        for event in execution_events:
            contribution = {
                'trade_id': event.event_id,
                'symbol': event.data.get('symbol', 'UNKNOWN'),
                'timestamp': event.timestamp.isoformat(),
                'pnl': event.data.get('pnl', 0.0),
                'quantity': event.data.get('quantity', 0),
                'price': event.data.get('price', 0.0),
                'contribution_percent': 0.0  # Will be calculated relative to total
            }
            contributions.append(contribution)
        
        # Calculate contribution percentages
        total_pnl = sum(c['pnl'] for c in contributions)
        if total_pnl != 0:
            for contribution in contributions:
                contribution['contribution_percent'] = (contribution['pnl'] / total_pnl) * 100
        
        return contributions
    
    def _analyze_risk_contributions(self, events: List[ReplayEvent]) -> Dict[str, float]:
        """Analyze risk contributions"""
        contributions = {
            'market_risk': 0.0,
            'specific_risk': 0.0,
            'liquidity_risk': 0.0,
            'operational_risk': 0.0
        }
        
        risk_events = [e for e in events if e.event_type == EventType.RISK_CHECK]
        
        for event in risk_events:
            risk_data = event.data
            contributions['market_risk'] += risk_data.get('market_risk', 0.0)
            contributions['specific_risk'] += risk_data.get('specific_risk', 0.0)
            contributions['liquidity_risk'] += risk_data.get('liquidity_risk', 0.0)
            contributions['operational_risk'] += risk_data.get('operational_risk', 0.0)
        
        # Normalize contributions
        total_risk = sum(contributions.values())
        if total_risk > 0:
            for key in contributions:
                contributions[key] = (contributions[key] / total_risk) * 100
        
        return contributions
    
    def _save_performance_attribution(self, attribution: PerformanceAttribution):
        """Save performance attribution to database"""
        try:
            with sqlite3.connect(self.event_recorder.db_path) as conn:
                conn.execute("""
                    INSERT INTO performance_attribution
                    (attribution_id, session_id, user_id, strategy_id, period_start,
                     period_end, total_return, benchmark_return, alpha, beta,
                     sharpe_ratio, max_drawdown, attribution_factors,
                     trade_contributions, risk_contributions)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    attribution.attribution_id,
                    attribution.session_id,
                    attribution.user_id,
                    attribution.strategy_id,
                    attribution.period_start.isoformat(),
                    attribution.period_end.isoformat(),
                    attribution.total_return,
                    attribution.benchmark_return,
                    attribution.alpha,
                    attribution.beta,
                    attribution.sharpe_ratio,
                    attribution.max_drawdown,
                    json.dumps(attribution.attribution_factors),
                    json.dumps(attribution.trade_contributions),
                    json.dumps(attribution.risk_contributions)
                ))
        except Exception as e:
            logger.error(f"Failed to save performance attribution: {e}")

class InvestigationToolsManager:
    """Main manager for investigation and replay tools"""
    
    def __init__(self, db_path: str = "investigation.db"):
        self.event_recorder = EventRecorder(db_path)
        self.decision_tree_builder = DecisionTreeBuilder(self.event_recorder)
        self.event_replayer = EventReplayer(self.event_recorder)
        self.performance_analyzer = PerformanceAttributionAnalyzer(self.event_recorder)
    
    def record_trading_event(self, event_type: EventType, user_id: str, session_id: str,
                           data: Dict[str, Any], context: Dict[str, Any] = None,
                           metadata: Dict[str, Any] = None) -> str:
        """Record a trading event for investigation"""
        event_id = str(uuid.uuid4())
        
        event = ReplayEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=datetime.now(),
            user_id=user_id,
            session_id=session_id,
            data=data,
            context=context or {},
            metadata=metadata or {},
            sequence_number=self._get_next_sequence_number(session_id)
        )
        
        self.event_recorder.record_event(event)
        return event_id
    
    def investigate_trading_session(self, session_id: str) -> Dict[str, Any]:
        """Perform complete investigation of a trading session"""
        try:
            # Build decision tree
            decision_tree = self.decision_tree_builder.build_decision_tree(session_id)
            
            # Get session events
            events = self.event_recorder.get_session_events(session_id)
            
            # Create investigation report
            investigation_report = {
                'session_id': session_id,
                'investigation_timestamp': datetime.now().isoformat(),
                'total_events': len(events),
                'decision_tree': decision_tree.to_dict() if decision_tree else None,
                'event_summary': self._create_event_summary(events),
                'performance_summary': self._create_performance_summary(events),
                'recommendations': self._generate_investigation_recommendations(events, decision_tree)
            }
            
            return investigation_report
            
        except Exception as e:
            logger.error(f"Failed to investigate trading session: {e}")
            return {'error': str(e), 'session_id': session_id}
    
    def replay_trading_session(self, session_id: str, speed_multiplier: float = 1.0) -> Dict[str, Any]:
        """Replay a complete trading session"""
        return self.event_replayer.replay_session(session_id, speed_multiplier=speed_multiplier)
    
    def analyze_strategy_performance(self, strategy_id: str, user_id: str,
                                   period_start: datetime, period_end: datetime,
                                   benchmark_return: float = 0.0) -> PerformanceAttribution:
        """Analyze strategy performance with attribution"""
        return self.performance_analyzer.analyze_performance_attribution(
            strategy_id, user_id, period_start, period_end, benchmark_return
        )
    
    def _get_next_sequence_number(self, session_id: str) -> int:
        """Get the next sequence number for a session"""
        try:
            with sqlite3.connect(self.event_recorder.db_path) as conn:
                cursor = conn.execute("""
                    SELECT MAX(sequence_number) FROM replay_events WHERE session_id = ?
                """, (session_id,))
                
                result = cursor.fetchone()
                return (result[0] or 0) + 1
                
        except Exception as e:
            logger.error(f"Failed to get sequence number: {e}")
            return 1
    
    def _create_event_summary(self, events: List[ReplayEvent]) -> Dict[str, Any]:
        """Create summary of events"""
        summary = {
            'total_events': len(events),
            'event_types': {},
            'time_span': None,
            'success_rate': 0.0
        }
        
        if events:
            # Count event types
            for event in events:
                event_type = event.event_type.value
                summary['event_types'][event_type] = summary['event_types'].get(event_type, 0) + 1
            
            # Calculate time span
            start_time = min(event.timestamp for event in events)
            end_time = max(event.timestamp for event in events)
            summary['time_span'] = {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'duration_seconds': (end_time - start_time).total_seconds()
            }
            
            # Calculate success rate
            successful_events = sum(1 for event in events if event.metadata.get('success', True))
            summary['success_rate'] = (successful_events / len(events)) * 100
        
        return summary
    
    def _create_performance_summary(self, events: List[ReplayEvent]) -> Dict[str, Any]:
        """Create performance summary from events"""
        summary = {
            'total_pnl': 0.0,
            'orders_executed': 0,
            'positions_opened': 0,
            'avg_execution_time_ms': 0.0,
            'risk_violations': 0,
            'compliance_violations': 0
        }
        
        execution_times = []
        
        for event in events:
            if event.event_type == EventType.ORDER_EXECUTED:
                summary['orders_executed'] += 1
                summary['total_pnl'] += event.data.get('pnl', 0.0)
            
            elif event.event_type == EventType.POSITION_UPDATED:
                if event.data.get('position_size', 0) > 0:
                    summary['positions_opened'] += 1
            
            elif event.event_type == EventType.RISK_CHECK:
                if not event.data.get('passed', True):
                    summary['risk_violations'] += 1
            
            elif event.event_type == EventType.COMPLIANCE_CHECK:
                if not event.data.get('compliant', True):
                    summary['compliance_violations'] += 1
            
            # Collect execution times
            exec_time = event.metadata.get('execution_time_ms', 0.0)
            if exec_time > 0:
                execution_times.append(exec_time)
        
        if execution_times:
            summary['avg_execution_time_ms'] = sum(execution_times) / len(execution_times)
        
        return summary
    
    def _generate_investigation_recommendations(self, events: List[ReplayEvent], 
                                              decision_tree: Optional[DecisionTree]) -> List[str]:
        """Generate recommendations based on investigation"""
        recommendations = []
        
        if not events:
            recommendations.append("No events found for analysis")
            return recommendations
        
        # Analyze performance
        total_pnl = sum(event.data.get('pnl', 0.0) for event in events 
                       if event.event_type == EventType.ORDER_EXECUTED)
        
        if total_pnl < 0:
            recommendations.append("Review trading strategy - negative PnL detected")
            recommendations.append("Analyze signal quality and market conditions")
        
        # Analyze execution efficiency
        execution_events = [e for e in events if e.event_type == EventType.ORDER_EXECUTED]
        if execution_events:
            avg_slippage = sum(abs(e.data.get('slippage', 0.0)) for e in execution_events) / len(execution_events)
            if avg_slippage > 0.01:  # 1% slippage threshold
                recommendations.append("High slippage detected - review execution venues")
        
        # Analyze risk management
        risk_events = [e for e in events if e.event_type == EventType.RISK_CHECK]
        if risk_events:
            failed_risk_checks = sum(1 for e in risk_events if not e.data.get('passed', True))
            if failed_risk_checks > 0:
                recommendations.append("Risk management violations detected - review risk parameters")
        
        # Analyze compliance
        compliance_events = [e for e in events if e.event_type == EventType.COMPLIANCE_CHECK]
        if compliance_events:
            failed_compliance = sum(1 for e in compliance_events if not e.data.get('compliant', True))
            if failed_compliance > 0:
                recommendations.append("Compliance violations detected - review regulatory requirements")
        
        # Decision tree analysis
        if decision_tree and decision_tree.performance_metrics:
            accuracy = decision_tree.performance_metrics.get('decision_accuracy', 0)
            if accuracy < 60:  # 60% accuracy threshold
                recommendations.append("Low decision accuracy - consider model retraining")
        
        # Default recommendations
        if not recommendations:
            recommendations.extend([
                "Continue monitoring trading performance",
                "Regular review of decision trees and event patterns",
                "Maintain comprehensive audit trails"
            ])
        
        return recommendations

# Global investigation tools manager
investigation_tools = InvestigationToolsManager()

# Convenience functions
def record_trading_event(event_type: EventType, user_id: str, session_id: str,
                        data: Dict[str, Any], context: Dict[str, Any] = None,
                        metadata: Dict[str, Any] = None) -> str:
    """Record a trading event for investigation"""
    return investigation_tools.record_trading_event(event_type, user_id, session_id, data, context, metadata)

def investigate_session(session_id: str) -> Dict[str, Any]:
    """Investigate a trading session"""
    return investigation_tools.investigate_trading_session(session_id)

def replay_session(session_id: str, speed_multiplier: float = 1.0) -> Dict[str, Any]:
    """Replay a trading session"""
    return investigation_tools.replay_trading_session(session_id, speed_multiplier)

def analyze_performance(strategy_id: str, user_id: str, period_start: datetime, 
                       period_end: datetime, benchmark_return: float = 0.0) -> PerformanceAttribution:
    """Analyze strategy performance"""
    return investigation_tools.analyze_strategy_performance(strategy_id, user_id, period_start, period_end, benchmark_return)