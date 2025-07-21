"""
Learning and Adaptation System
AI system that learns from user feedback and trading outcomes
"""
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from ..database.service import get_db_connection

logger = logging.getLogger(__name__)

class FeedbackType(str, Enum):
    """Types of user feedback"""
    SIGNAL_ACCURACY = "signal_accuracy"
    STRATEGY_PERFORMANCE = "strategy_performance"
    ANALYSIS_QUALITY = "analysis_quality"
    RECOMMENDATION_USEFULNESS = "recommendation_usefulness"

class OutcomeType(str, Enum):
    """Types of trading outcomes"""
    PROFIT = "profit"
    LOSS = "loss"
    BREAKEVEN = "breakeven"
    PARTIAL_FILL = "partial_fill"
    CANCELLED = "cancelled"

class LearningSystem:
    """
    Learning and adaptation system for AI recommendations
    """
    
    def __init__(self):
        self.min_feedback_count = 5  # Minimum feedback needed for adaptation
        self.learning_rate = 0.1  # How quickly to adapt
        self.confidence_threshold = 0.7  # Minimum confidence for recommendations
        
    async def record_feedback(
        self, 
        user_id: str, 
        feedback_type: FeedbackType,
        item_id: str,
        rating: int,  # 1-5 scale
        comments: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Record user feedback on AI recommendations"""
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Create feedback table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    feedback_type TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    rating INTEGER NOT NULL,
                    comments TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            cursor.execute("""
                INSERT INTO ai_feedback 
                (user_id, feedback_type, item_id, rating, comments, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id, 
                feedback_type.value, 
                item_id, 
                rating, 
                comments,
                json.dumps(metadata) if metadata else None
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Recorded feedback for user {user_id}: {feedback_type} - {rating}/5")
            
            # Trigger learning update
            await self.update_user_preferences(user_id, feedback_type, rating, metadata)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to record feedback: {e}")
            return False
    
    async def record_trade_outcome(
        self,
        user_id: str,
        signal_id: str,
        outcome_type: OutcomeType,
        pnl_amount: float,
        execution_price: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Record actual trading outcome for learning"""
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Create outcomes table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_trade_outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    signal_id TEXT NOT NULL,
                    outcome_type TEXT NOT NULL,
                    pnl_amount REAL NOT NULL,
                    execution_price REAL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            cursor.execute("""
                INSERT INTO ai_trade_outcomes 
                (user_id, signal_id, outcome_type, pnl_amount, execution_price, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                signal_id,
                outcome_type.value,
                pnl_amount,
                execution_price,
                json.dumps(metadata) if metadata else None
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Recorded trade outcome for user {user_id}: {outcome_type} - PnL: {pnl_amount}")
            
            # Update signal accuracy metrics
            await self.update_signal_accuracy(user_id, signal_id, outcome_type, pnl_amount)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to record trade outcome: {e}")
            return False
    
    async def update_user_preferences(
        self,
        user_id: str,
        feedback_type: FeedbackType,
        rating: int,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Update user preferences based on feedback"""
        
        try:
            # Get current user preferences
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT provider_priorities, risk_tolerance, trading_style
                FROM ai_user_preferences
                WHERE user_id = ?
            """, (user_id,))
            
            result = cursor.fetchone()
            if not result:
                conn.close()
                return
            
            provider_priorities = json.loads(result[0]) if result[0] else {}
            risk_tolerance = result[1] or "medium"
            trading_style = result[2] or "balanced"
            
            # Adapt based on feedback type and rating
            if feedback_type == FeedbackType.SIGNAL_ACCURACY and metadata:
                provider_used = metadata.get("provider_used")
                if provider_used and rating >= 4:
                    # Increase priority for well-performing provider
                    if "signals" not in provider_priorities:
                        provider_priorities["signals"] = []
                    
                    if provider_used in provider_priorities["signals"]:
                        # Move to front
                        provider_priorities["signals"].remove(provider_used)
                    provider_priorities["signals"].insert(0, provider_used)
                
                elif provider_used and rating <= 2:
                    # Decrease priority for poor-performing provider
                    if "signals" in provider_priorities and provider_used in provider_priorities["signals"]:
                        provider_priorities["signals"].remove(provider_used)
                        provider_priorities["signals"].append(provider_used)
            
            # Update preferences in database
            cursor.execute("""
                UPDATE ai_user_preferences
                SET provider_priorities = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (json.dumps(provider_priorities), user_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated preferences for user {user_id} based on {feedback_type} feedback")
            
        except Exception as e:
            logger.error(f"Failed to update user preferences: {e}")
    
    async def update_signal_accuracy(
        self,
        user_id: str,
        signal_id: str,
        outcome_type: OutcomeType,
        pnl_amount: float
    ):
        """Update signal accuracy metrics"""
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get original signal details
            cursor.execute("""
                SELECT confidence_score, provider_used, signal_type
                FROM ai_trading_signals
                WHERE id = ? AND user_id = ?
            """, (signal_id, user_id))
            
            signal_result = cursor.fetchone()
            if not signal_result:
                conn.close()
                return
            
            confidence_score = signal_result[0]
            provider_used = signal_result[1]
            signal_type = signal_result[2]
            
            # Calculate accuracy score based on outcome
            accuracy_score = self.calculate_accuracy_score(outcome_type, pnl_amount, signal_type)
            
            # Create or update accuracy tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_accuracy_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    predicted_confidence REAL NOT NULL,
                    actual_accuracy REAL NOT NULL,
                    pnl_amount REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            cursor.execute("""
                INSERT INTO ai_accuracy_tracking
                (user_id, provider, signal_type, predicted_confidence, actual_accuracy, pnl_amount)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, provider_used, signal_type, confidence_score, accuracy_score, pnl_amount))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated accuracy tracking for signal {signal_id}: {accuracy_score}")
            
        except Exception as e:
            logger.error(f"Failed to update signal accuracy: {e}")
    
    def calculate_accuracy_score(
        self, 
        outcome_type: OutcomeType, 
        pnl_amount: float, 
        signal_type: str
    ) -> float:
        """Calculate accuracy score based on trade outcome"""
        
        if outcome_type == OutcomeType.CANCELLED:
            return 0.5  # Neutral score for cancelled trades
        
        if signal_type == "buy":
            if pnl_amount > 0:
                return min(1.0, 0.5 + (pnl_amount / 1000))  # Scale based on profit
            else:
                return max(0.0, 0.5 + (pnl_amount / 1000))  # Scale based on loss
        
        elif signal_type == "sell":
            if pnl_amount > 0:
                return min(1.0, 0.5 + (pnl_amount / 1000))
            else:
                return max(0.0, 0.5 + (pnl_amount / 1000))
        
        else:  # hold
            return 0.7 if abs(pnl_amount) < 100 else 0.3  # Good if minimal movement
    
    async def get_provider_performance(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get provider performance metrics for learning"""
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get accuracy data
            cursor.execute("""
                SELECT 
                    provider,
                    signal_type,
                    AVG(actual_accuracy) as avg_accuracy,
                    AVG(predicted_confidence) as avg_confidence,
                    COUNT(*) as signal_count,
                    SUM(pnl_amount) as total_pnl
                FROM ai_accuracy_tracking
                WHERE user_id = ? 
                AND created_at >= datetime('now', ? || ' days')
                GROUP BY provider, signal_type
            """, (user_id, f"-{days}"))
            
            accuracy_results = cursor.fetchall()
            
            # Get feedback data
            cursor.execute("""
                SELECT 
                    feedback_type,
                    AVG(rating) as avg_rating,
                    COUNT(*) as feedback_count
                FROM ai_feedback
                WHERE user_id = ?
                AND created_at >= datetime('now', ? || ' days')
                GROUP BY feedback_type
            """, (user_id, f"-{days}"))
            
            feedback_results = cursor.fetchall()
            conn.close()
            
            # Process results
            provider_performance = {}
            
            for result in accuracy_results:
                provider = result[0]
                if provider not in provider_performance:
                    provider_performance[provider] = {
                        "signal_types": {},
                        "overall_accuracy": 0,
                        "total_signals": 0,
                        "total_pnl": 0
                    }
                
                provider_performance[provider]["signal_types"][result[1]] = {
                    "avg_accuracy": result[2],
                    "avg_confidence": result[3],
                    "signal_count": result[4],
                    "total_pnl": result[5]
                }
                
                provider_performance[provider]["total_signals"] += result[4]
                provider_performance[provider]["total_pnl"] += result[5] or 0
            
            # Calculate overall accuracy for each provider
            for provider in provider_performance:
                total_accuracy = 0
                total_signals = 0
                for signal_type_data in provider_performance[provider]["signal_types"].values():
                    total_accuracy += signal_type_data["avg_accuracy"] * signal_type_data["signal_count"]
                    total_signals += signal_type_data["signal_count"]
                
                if total_signals > 0:
                    provider_performance[provider]["overall_accuracy"] = total_accuracy / total_signals
            
            # Add feedback data
            feedback_summary = {}
            for result in feedback_results:
                feedback_summary[result[0]] = {
                    "avg_rating": result[1],
                    "feedback_count": result[2]
                }
            
            return {
                "user_id": user_id,
                "analysis_period_days": days,
                "provider_performance": provider_performance,
                "feedback_summary": feedback_summary,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get provider performance: {e}")
            return {"user_id": user_id, "error": str(e)}
    
    async def get_learning_insights(self, user_id: str) -> Dict[str, Any]:
        """Get insights from learning data"""
        
        try:
            performance_data = await self.get_provider_performance(user_id)
            
            insights = []
            recommendations = []
            
            # Analyze provider performance
            provider_performance = performance_data.get("provider_performance", {})
            
            if len(provider_performance) > 1:
                # Find best performing provider
                best_provider = max(
                    provider_performance.items(),
                    key=lambda x: x[1]["overall_accuracy"]
                )
                
                insights.append({
                    "type": "best_provider",
                    "message": f"{best_provider[0]} has the highest accuracy ({best_provider[1]['overall_accuracy']:.1%})",
                    "data": best_provider[1]
                })
                
                recommendations.append(f"Consider using {best_provider[0]} more frequently for better results")
            
            # Analyze signal type performance
            signal_type_performance = {}
            for provider, data in provider_performance.items():
                for signal_type, type_data in data["signal_types"].items():
                    if signal_type not in signal_type_performance:
                        signal_type_performance[signal_type] = []
                    signal_type_performance[signal_type].append({
                        "provider": provider,
                        "accuracy": type_data["avg_accuracy"],
                        "count": type_data["signal_count"]
                    })
            
            # Find best signal types
            for signal_type, providers in signal_type_performance.items():
                if len(providers) > 1:
                    best_for_type = max(providers, key=lambda x: x["accuracy"])
                    insights.append({
                        "type": "signal_type_performance",
                        "message": f"For {signal_type} signals, {best_for_type['provider']} performs best ({best_for_type['accuracy']:.1%})",
                        "signal_type": signal_type,
                        "best_provider": best_for_type
                    })
            
            # Check for learning opportunities
            total_feedback = sum(
                data["feedback_count"] 
                for data in performance_data.get("feedback_summary", {}).values()
            )
            
            if total_feedback < self.min_feedback_count:
                recommendations.append("Provide more feedback to improve AI recommendations")
            
            return {
                "user_id": user_id,
                "insights": insights,
                "recommendations": recommendations,
                "learning_status": {
                    "total_feedback": total_feedback,
                    "learning_active": total_feedback >= self.min_feedback_count,
                    "providers_analyzed": len(provider_performance)
                },
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get learning insights: {e}")
            return {"user_id": user_id, "error": str(e)}
    
    async def adapt_confidence_thresholds(self, user_id: str) -> Dict[str, Any]:
        """Adapt confidence thresholds based on user success patterns"""
        
        try:
            performance_data = await self.get_provider_performance(user_id)
            provider_performance = performance_data.get("provider_performance", {})
            
            adapted_thresholds = {}
            
            for provider, data in provider_performance.items():
                if data["total_signals"] >= self.min_feedback_count:
                    overall_accuracy = data["overall_accuracy"]
                    
                    # Adapt threshold based on accuracy
                    if overall_accuracy > 0.8:
                        # High accuracy - can lower threshold
                        adapted_thresholds[provider] = max(0.5, self.confidence_threshold - 0.1)
                    elif overall_accuracy < 0.6:
                        # Low accuracy - raise threshold
                        adapted_thresholds[provider] = min(0.9, self.confidence_threshold + 0.1)
                    else:
                        # Average accuracy - keep default
                        adapted_thresholds[provider] = self.confidence_threshold
                else:
                    # Not enough data - use default
                    adapted_thresholds[provider] = self.confidence_threshold
            
            return {
                "user_id": user_id,
                "adapted_thresholds": adapted_thresholds,
                "default_threshold": self.confidence_threshold,
                "adaptation_reason": "Based on historical accuracy patterns"
            }
            
        except Exception as e:
            logger.error(f"Failed to adapt confidence thresholds: {e}")
            return {"user_id": user_id, "error": str(e)}