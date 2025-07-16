"""
AI Engine Strategy Store

Enhanced storage system for AI-generated strategies with learning capabilities,
confidence scoring, tagging, and outcome tracking.
"""
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import os

logger = logging.getLogger(__name__)


class StrategyType(Enum):
    """Strategy classification types"""
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    SCALPING = "scalping"
    SWING_TRADING = "swing_trading"
    SECTOR_BET = "sector_bet"
    PAIRS_TRADING = "pairs_trading"
    ARBITRAGE = "arbitrage"
    BREAKOUT = "breakout"
    TECHNICAL_ANALYSIS = "technical_analysis"
    FUNDAMENTAL_ANALYSIS = "fundamental_analysis"


class TradeOutcome(Enum):
    """Trade outcome classifications"""
    WIN = "win"
    LOSS = "loss"
    NEUTRAL = "neutral"
    PENDING = "pending"


@dataclass
class StrategyMetadata:
    """Enhanced strategy metadata with intelligence features"""
    strategy_type: StrategyType
    confidence_score: float  # 0.0 to 1.0
    confidence_reason: str
    tags: List[str]
    symbols: List[str]
    timeframe: str
    risk_level: str  # low, medium, high
    expected_return: Optional[float] = None
    max_drawdown: Optional[float] = None


@dataclass
class TradeOutcomeData:
    """Trade outcome tracking data"""
    outcome: TradeOutcome
    actual_return: Optional[float] = None
    duration_hours: Optional[int] = None
    max_profit: Optional[float] = None
    max_loss: Optional[float] = None
    exit_reason: Optional[str] = None
    notes: Optional[str] = None


class StrategyStore:
    """
    Enhanced AI Strategy Storage System
    
    Features:
    - Confidence scoring and reasoning
    - Strategy tagging and clustering
    - Post-trade outcome tracking
    - Performance analytics
    - Cross-user anonymized insights
    - Learning from outcomes
    """
    
    def __init__(self, db_path: str = "ai_strategies.db"):
        """Initialize enhanced strategy store"""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize enhanced database schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Sessions table (existing)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS ai_sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        provider_used TEXT,
                        analysis_type TEXT,
                        portfolio_context TEXT,
                        market_context TEXT
                    )
                """)
                
                # Enhanced strategies table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS ai_strategies (
                        strategy_id TEXT PRIMARY KEY,
                        session_id TEXT,
                        user_id TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        provider_used TEXT,
                        strategy_content TEXT NOT NULL,
                        strategy_type TEXT,
                        confidence_score REAL,
                        confidence_reason TEXT,
                        tags TEXT, -- JSON array
                        symbols TEXT, -- JSON array
                        timeframe TEXT,
                        risk_level TEXT,
                        expected_return REAL,
                        max_drawdown REAL,
                        metadata TEXT, -- JSON metadata
                        FOREIGN KEY (session_id) REFERENCES ai_sessions (session_id)
                    )
                """)
                
                # Trade outcomes table (NEW)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS trade_outcomes (
                        outcome_id TEXT PRIMARY KEY,
                        strategy_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        outcome TEXT NOT NULL, -- win/loss/neutral/pending
                        actual_return REAL,
                        duration_hours INTEGER,
                        max_profit REAL,
                        max_loss REAL,
                        exit_reason TEXT,
                        notes TEXT,
                        feedback_data TEXT, -- JSON feedback
                        FOREIGN KEY (strategy_id) REFERENCES ai_strategies (strategy_id)
                    )
                """)
                
                # Strategy performance analytics (NEW)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS strategy_performance (
                        performance_id TEXT PRIMARY KEY,
                        strategy_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        total_trades INTEGER DEFAULT 0,
                        winning_trades INTEGER DEFAULT 0,
                        losing_trades INTEGER DEFAULT 0,
                        total_return REAL DEFAULT 0.0,
                        average_return REAL DEFAULT 0.0,
                        win_rate REAL DEFAULT 0.0,
                        sharpe_ratio REAL,
                        max_consecutive_wins INTEGER DEFAULT 0,
                        max_consecutive_losses INTEGER DEFAULT 0,
                        performance_score REAL DEFAULT 0.0, -- Calculated score
                        FOREIGN KEY (strategy_id) REFERENCES ai_strategies (strategy_id)
                    )
                """)
                
                # Cross-user anonymized insights (NEW)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS crowd_insights (
                        insight_id TEXT PRIMARY KEY,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        insight_type TEXT NOT NULL, -- trending_strategy, risk_pattern, etc.
                        strategy_type TEXT,
                        symbols TEXT, -- JSON array
                        tags TEXT, -- JSON array
                        performance_data TEXT, -- JSON performance stats
                        user_count INTEGER DEFAULT 1,
                        total_trades INTEGER DEFAULT 0,
                        average_performance REAL DEFAULT 0.0,
                        confidence_level REAL DEFAULT 0.0,
                        risk_score REAL DEFAULT 0.0
                    )
                """)
                
                # AI feedback and learning (NEW)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS ai_feedback (
                        feedback_id TEXT PRIMARY KEY,
                        strategy_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        feedback_type TEXT NOT NULL, -- outcome, user_rating, system_analysis
                        feedback_content TEXT NOT NULL, -- JSON feedback data
                        ai_reflection TEXT, -- AI's self-reflection on the outcome
                        learning_points TEXT, -- JSON array of learning points
                        applied_to_future BOOLEAN DEFAULT FALSE,
                        FOREIGN KEY (strategy_id) REFERENCES ai_strategies (strategy_id)
                    )
                """)
                
                # Usage tracking (existing but enhanced)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS ai_usage (
                        usage_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        provider TEXT NOT NULL,
                        operation_type TEXT NOT NULL,
                        tokens_used INTEGER,
                        cost_estimate REAL,
                        response_time_ms INTEGER,
                        success BOOLEAN DEFAULT TRUE,
                        error_message TEXT,
                        request_data TEXT, -- JSON request data
                        response_data TEXT -- JSON response data
                    )
                """)
                
                # Create indexes for performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_strategies_user_id ON ai_strategies (user_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_strategies_type ON ai_strategies (strategy_type)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_strategies_confidence ON ai_strategies (confidence_score)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_strategy ON trade_outcomes (strategy_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_user ON trade_outcomes (user_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_performance_user ON strategy_performance (user_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_crowd_type ON crowd_insights (strategy_type)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_strategy ON ai_feedback (strategy_id)")
                
                logger.info("Enhanced AI strategy database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize enhanced strategy database: {e}")
            raise
    
    def store_enhanced_strategy(
        self,
        strategy_id: str,
        session_id: str,
        user_id: str,
        strategy_content: str,
        metadata: StrategyMetadata,
        provider_used: str
    ) -> bool:
        """Store strategy with enhanced metadata and intelligence features"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO ai_strategies (
                        strategy_id, session_id, user_id, provider_used,
                        strategy_content, strategy_type, confidence_score,
                        confidence_reason, tags, symbols, timeframe,
                        risk_level, expected_return, max_drawdown, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    strategy_id, session_id, user_id, provider_used,
                    strategy_content, metadata.strategy_type.value,
                    metadata.confidence_score, metadata.confidence_reason,
                    json.dumps(metadata.tags), json.dumps(metadata.symbols),
                    metadata.timeframe, metadata.risk_level,
                    metadata.expected_return, metadata.max_drawdown,
                    json.dumps(metadata.__dict__, default=str)
                ))
                
                # Initialize performance tracking
                conn.execute("""
                    INSERT INTO strategy_performance (
                        performance_id, strategy_id, user_id
                    ) VALUES (?, ?, ?)
                """, (f"perf_{strategy_id}", strategy_id, user_id))
                
                logger.info(f"Enhanced strategy {strategy_id} stored successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to store enhanced strategy {strategy_id}: {e}")
            return False
    
    def record_trade_outcome(
        self,
        outcome_id: str,
        strategy_id: str,
        user_id: str,
        outcome_data: TradeOutcomeData
    ) -> bool:
        """Record trade outcome and update performance metrics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Store trade outcome
                conn.execute("""
                    INSERT INTO trade_outcomes (
                        outcome_id, strategy_id, user_id, outcome,
                        actual_return, duration_hours, max_profit,
                        max_loss, exit_reason, notes, feedback_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    outcome_id, strategy_id, user_id, outcome_data.outcome.value,
                    outcome_data.actual_return, outcome_data.duration_hours,
                    outcome_data.max_profit, outcome_data.max_loss,
                    outcome_data.exit_reason, outcome_data.notes,
                    json.dumps(outcome_data.__dict__, default=str)
                ))
                
                # Update performance metrics
                self._update_strategy_performance(conn, strategy_id, user_id, outcome_data)
                
                # Update crowd insights
                self._update_crowd_insights(conn, strategy_id, outcome_data)
                
                logger.info(f"Trade outcome {outcome_id} recorded for strategy {strategy_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to record trade outcome {outcome_id}: {e}")
            return False
    
    def _update_strategy_performance(
        self, 
        conn: sqlite3.Connection, 
        strategy_id: str, 
        user_id: str, 
        outcome_data: TradeOutcomeData
    ):
        """Update strategy performance metrics"""
        try:
            # Get current performance
            cursor = conn.execute("""
                SELECT total_trades, winning_trades, losing_trades, total_return
                FROM strategy_performance WHERE strategy_id = ?
            """, (strategy_id,))
            
            current = cursor.fetchone()
            if current:
                total_trades, winning_trades, losing_trades, total_return = current
                
                # Update counters
                total_trades += 1
                if outcome_data.outcome == TradeOutcome.WIN:
                    winning_trades += 1
                elif outcome_data.outcome == TradeOutcome.LOSS:
                    losing_trades += 1
                
                # Update returns
                if outcome_data.actual_return is not None:
                    total_return += outcome_data.actual_return
                
                # Calculate metrics
                win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
                average_return = total_return / total_trades if total_trades > 0 else 0.0
                
                # Calculate performance score (custom metric)
                performance_score = (win_rate * 0.4) + (average_return * 0.6)
                
                # Update database
                conn.execute("""
                    UPDATE strategy_performance SET
                        total_trades = ?, winning_trades = ?, losing_trades = ?,
                        total_return = ?, average_return = ?, win_rate = ?,
                        performance_score = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE strategy_id = ?
                """, (
                    total_trades, winning_trades, losing_trades,
                    total_return, average_return, win_rate,
                    performance_score, strategy_id
                ))
                
        except Exception as e:
            logger.error(f"Failed to update strategy performance: {e}")
    
    def _update_crowd_insights(
        self, 
        conn: sqlite3.Connection, 
        strategy_id: str, 
        outcome_data: TradeOutcomeData
    ):
        """Update anonymized crowd insights"""
        try:
            # Get strategy info
            cursor = conn.execute("""
                SELECT strategy_type, tags, symbols FROM ai_strategies 
                WHERE strategy_id = ?
            """, (strategy_id,))
            
            strategy_info = cursor.fetchone()
            if strategy_info:
                strategy_type, tags_json, symbols_json = strategy_info
                
                # Check if insight exists
                cursor = conn.execute("""
                    SELECT insight_id, user_count, total_trades, average_performance
                    FROM crowd_insights 
                    WHERE strategy_type = ? AND insight_type = 'performance_tracking'
                """, (strategy_type,))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing insight
                    insight_id, user_count, total_trades, avg_performance = existing
                    
                    new_total_trades = total_trades + 1
                    if outcome_data.actual_return is not None:
                        new_avg_performance = (
                            (avg_performance * total_trades + outcome_data.actual_return) / 
                            new_total_trades
                        )
                    else:
                        new_avg_performance = avg_performance
                    
                    conn.execute("""
                        UPDATE crowd_insights SET
                            total_trades = ?, average_performance = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE insight_id = ?
                    """, (new_total_trades, new_avg_performance, insight_id))
                    
                else:
                    # Create new insight
                    insight_id = f"crowd_{strategy_type}_{datetime.now().strftime('%Y%m%d')}"
                    conn.execute("""
                        INSERT INTO crowd_insights (
                            insight_id, insight_type, strategy_type,
                            symbols, tags, total_trades, average_performance
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        insight_id, 'performance_tracking', strategy_type,
                        symbols_json, tags_json, 1,
                        outcome_data.actual_return or 0.0
                    ))
                    
        except Exception as e:
            logger.error(f"Failed to update crowd insights: {e}")
    
    def get_strategy_performance(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive strategy performance data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT * FROM strategy_performance WHERE strategy_id = ?
                """, (strategy_id,))
                
                performance = cursor.fetchone()
                if performance:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, performance))
                    
                return None
                
        except Exception as e:
            logger.error(f"Failed to get strategy performance: {e}")
            return None
    
    def get_crowd_insights(
        self, 
        strategy_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get anonymized crowd insights"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if strategy_type:
                    cursor = conn.execute("""
                        SELECT * FROM crowd_insights 
                        WHERE strategy_type = ?
                        ORDER BY average_performance DESC, total_trades DESC
                        LIMIT ?
                    """, (strategy_type, limit))
                else:
                    cursor = conn.execute("""
                        SELECT * FROM crowd_insights 
                        ORDER BY average_performance DESC, total_trades DESC
                        LIMIT ?
                    """, (limit,))
                
                insights = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                return [dict(zip(columns, insight)) for insight in insights]
                
        except Exception as e:
            logger.error(f"Failed to get crowd insights: {e}")
            return []
    
    def get_top_performing_strategies(
        self, 
        user_id: Optional[str] = None,
        strategy_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top performing strategies with analytics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                base_query = """
                    SELECT s.*, p.win_rate, p.average_return, p.performance_score,
                           p.total_trades
                    FROM ai_strategies s
                    JOIN strategy_performance p ON s.strategy_id = p.strategy_id
                    WHERE p.total_trades > 0
                """
                
                params = []
                if user_id:
                    base_query += " AND s.user_id = ?"
                    params.append(user_id)
                
                if strategy_type:
                    base_query += " AND s.strategy_type = ?"
                    params.append(strategy_type)
                
                base_query += " ORDER BY p.performance_score DESC, p.total_trades DESC LIMIT ?"
                params.append(limit)
                
                cursor = conn.execute(base_query, params)
                strategies = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                return [dict(zip(columns, strategy)) for strategy in strategies]
                
        except Exception as e:
            logger.error(f"Failed to get top performing strategies: {e}")
            return []
    
    def store_ai_feedback(
        self,
        feedback_id: str,
        strategy_id: str,
        user_id: str,
        feedback_type: str,
        feedback_content: Dict[str, Any],
        ai_reflection: Optional[str] = None
    ) -> bool:
        """Store AI feedback and learning data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO ai_feedback (
                        feedback_id, strategy_id, user_id, feedback_type,
                        feedback_content, ai_reflection
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    feedback_id, strategy_id, user_id, feedback_type,
                    json.dumps(feedback_content), ai_reflection
                ))
                
                logger.info(f"AI feedback {feedback_id} stored successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to store AI feedback {feedback_id}: {e}")
            return False
    
    def create_session(self, session_id: str, user_id: str, session_type: str, 
                      provider: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Create a new AI session.
        
        Args:
            session_id: Unique session identifier
            user_id: User identifier
            session_type: Type of session (analysis, strategy, signals)
            provider: AI provider used
            metadata: Additional session metadata
            
        Returns:
            True if session created successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO ai_sessions (session_id, user_id, session_type, provider, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """, (session_id, user_id, session_type, provider, json.dumps(metadata) if metadata else None))
                conn.commit()
                
                logger.debug(f"Created AI session: {session_id} for user: {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            return False
    
    def log_interaction(self, session_id: str, interaction_type: str, prompt: str,
                       response: Optional[str] = None, provider: Optional[str] = None,
                       tokens_used: int = 0, processing_time_ms: int = 0,
                       metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Log an AI interaction.
        
        Args:
            session_id: Session identifier
            interaction_type: Type of interaction (prompt, response)
            prompt: Input prompt
            response: AI response
            provider: AI provider used
            tokens_used: Number of tokens consumed
            processing_time_ms: Processing time in milliseconds
            metadata: Additional interaction metadata
            
        Returns:
            True if interaction logged successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO ai_interactions 
                    (session_id, interaction_type, prompt, response, provider, tokens_used, processing_time_ms, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (session_id, interaction_type, prompt, response, provider, tokens_used, processing_time_ms,
                      json.dumps(metadata) if metadata else None))
                conn.commit()
                
                logger.debug(f"Logged interaction for session: {session_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error logging interaction: {str(e)}")
            return False
    
    def store_strategy(self, strategy_id: str, session_id: str, user_id: str,
                      strategy_name: str, strategy_data: Dict[str, Any],
                      risk_tolerance: str, provider: str) -> bool:
        """
        Store a generated strategy.
        
        Args:
            strategy_id: Unique strategy identifier
            session_id: Session that generated the strategy
            user_id: User identifier
            strategy_name: Human-readable strategy name
            strategy_data: Complete strategy data
            risk_tolerance: Risk tolerance level
            provider: AI provider that generated the strategy
            
        Returns:
            True if strategy stored successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO generated_strategies 
                    (strategy_id, session_id, user_id, strategy_name, strategy_data, risk_tolerance, provider)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (strategy_id, session_id, user_id, strategy_name, json.dumps(strategy_data), 
                      risk_tolerance, provider))
                conn.commit()
                
                logger.info(f"Stored strategy: {strategy_name} (ID: {strategy_id}) for user: {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error storing strategy: {str(e)}")
            return False
    
    def get_user_strategies(self, user_id: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all strategies for a user.
        
        Args:
            user_id: User identifier
            active_only: Only return active strategies
            
        Returns:
            List of user strategies
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT strategy_id, strategy_name, strategy_data, risk_tolerance, 
                           provider, created_at, updated_at, performance_data
                    FROM generated_strategies 
                    WHERE user_id = ?
                """
                params = [user_id]
                
                if active_only:
                    query += " AND is_active = TRUE"
                
                query += " ORDER BY created_at DESC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                strategies = []
                for row in rows:
                    strategy = {
                        "strategy_id": row[0],
                        "strategy_name": row[1],
                        "strategy_data": json.loads(row[2]) if row[2] else {},
                        "risk_tolerance": row[3],
                        "provider": row[4],
                        "created_at": row[5],
                        "updated_at": row[6],
                        "performance_data": json.loads(row[7]) if row[7] else {}
                    }
                    strategies.append(strategy)
                
                logger.debug(f"Retrieved {len(strategies)} strategies for user: {user_id}")
                return strategies
                
        except Exception as e:
            logger.error(f"Error retrieving user strategies: {str(e)}")
            return []
    
    def get_session_history(self, user_id: str, session_type: Optional[str] = None,
                           limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get session history for a user.
        
        Args:
            user_id: User identifier
            session_type: Filter by session type
            limit: Maximum number of sessions to return
            
        Returns:
            List of session records
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT session_id, session_type, provider, created_at, metadata, status
                    FROM ai_sessions 
                    WHERE user_id = ?
                """
                params = [user_id]
                
                if session_type:
                    query += " AND session_type = ?"
                    params.append(session_type)
                
                query += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                sessions = []
                for row in rows:
                    session = {
                        "session_id": row[0],
                        "session_type": row[1],
                        "provider": row[2],
                        "created_at": row[3],
                        "metadata": json.loads(row[4]) if row[4] else {},
                        "status": row[5]
                    }
                    sessions.append(session)
                
                logger.debug(f"Retrieved {len(sessions)} sessions for user: {user_id}")
                return sessions
                
        except Exception as e:
            logger.error(f"Error retrieving session history: {str(e)}")
            return []
    
    def update_strategy_performance(self, strategy_id: str, performance_data: Dict[str, Any]) -> bool:
        """
        Update strategy performance data.
        
        Args:
            strategy_id: Strategy identifier
            performance_data: Performance metrics
            
        Returns:
            True if update successful
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE generated_strategies 
                    SET performance_data = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE strategy_id = ?
                """, (json.dumps(performance_data), strategy_id))
                conn.commit()
                
                logger.debug(f"Updated performance data for strategy: {strategy_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating strategy performance: {str(e)}")
            return False
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """
        Get AI engine usage statistics.
        
        Returns:
            Usage statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Session counts by type
                cursor.execute("""
                    SELECT session_type, COUNT(*) as count
                    FROM ai_sessions 
                    GROUP BY session_type
                """)
                session_counts = dict(cursor.fetchall())
                
                # Provider usage
                cursor.execute("""
                    SELECT provider, COUNT(*) as count
                    FROM ai_sessions 
                    GROUP BY provider
                """)
                provider_counts = dict(cursor.fetchall())
                
                # Token usage
                cursor.execute("""
                    SELECT provider, SUM(tokens_used) as total_tokens
                    FROM ai_interactions 
                    GROUP BY provider
                """)
                token_usage = dict(cursor.fetchall())
                
                # Total strategies generated
                cursor.execute("SELECT COUNT(*) FROM generated_strategies")
                total_strategies = cursor.fetchone()[0]
                
                return {
                    "session_counts": session_counts,
                    "provider_counts": provider_counts,
                    "token_usage": token_usage,
                    "total_strategies": total_strategies,
                    "last_updated": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting usage statistics: {str(e)}")
            return {} 