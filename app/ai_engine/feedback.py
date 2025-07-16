"""
AI Engine Feedback System

Handles post-trade feedback, outcome tracking, and AI learning from results.
Enables the system to learn from wins/losses and improve strategy generation over time.
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
import json

from .memory.strategy_store import StrategyStore, TradeOutcome, TradeOutcomeData
from .schemas.requests import AIProvider
from .schemas.responses import FeedbackResponse, LearningInsight
from .providers.base_provider import BaseAIProvider
from .providers import OpenAIClient, ClaudeClient, GeminiClient

logger = logging.getLogger(__name__)


class FeedbackSystem:
    """
    AI Feedback and Learning System
    
    Responsibilities:
    - Process trade outcomes and update performance metrics
    - Generate AI reflections on strategy performance
    - Extract learning insights from outcomes
    - Trigger self-improvement prompts
    - Update strategy confidence scores based on performance
    """
    
    def __init__(self, strategy_store: StrategyStore):
        """Initialize feedback system with strategy store"""
        self.strategy_store = strategy_store
        
        # Initialize AI providers for reflection
        self.providers = {
            AIProvider.OPENAI: OpenAIClient(),
            AIProvider.CLAUDE: ClaudeClient(),
            AIProvider.GEMINI: GeminiClient()
        }
        
        # Use Claude for reflections (good at analysis)
        self.reflection_provider = self.providers[AIProvider.CLAUDE]
    
    async def record_trade_outcome(
        self,
        strategy_id: str,
        user_id: str,
        outcome: TradeOutcome,
        actual_return: Optional[float] = None,
        duration_hours: Optional[int] = None,
        max_profit: Optional[float] = None,
        max_loss: Optional[float] = None,
        exit_reason: Optional[str] = None,
        notes: Optional[str] = None,
        trigger_reflection: bool = True
    ) -> FeedbackResponse:
        """
        Record trade outcome and optionally trigger AI reflection
        
        Args:
            strategy_id: ID of the strategy that was executed
            user_id: User who executed the strategy
            outcome: Win, loss, neutral, or pending
            actual_return: Actual percentage return achieved
            duration_hours: How long the trade was held
            max_profit: Maximum profit achieved during trade
            max_loss: Maximum loss during trade
            exit_reason: Why the trade was closed
            notes: Additional notes about the trade
            trigger_reflection: Whether to generate AI reflection
            
        Returns:
            FeedbackResponse with outcome data and any AI insights
        """
        try:
            # Create outcome data
            outcome_data = TradeOutcomeData(
                outcome=outcome,
                actual_return=actual_return,
                duration_hours=duration_hours,
                max_profit=max_profit,
                max_loss=max_loss,
                exit_reason=exit_reason,
                notes=notes
            )
            
            # Generate unique outcome ID
            outcome_id = f"outcome_{uuid.uuid4().hex[:8]}"
            
            # Store outcome in database
            success = self.strategy_store.record_trade_outcome(
                outcome_id, strategy_id, user_id, outcome_data
            )
            
            if not success:
                return FeedbackResponse(
                    success=False,
                    message="Failed to record trade outcome",
                    outcome_id=outcome_id
                )
            
            ai_reflection = None
            learning_insights = []
            
            # Generate AI reflection if requested
            if trigger_reflection:
                reflection_result = await self._generate_ai_reflection(
                    strategy_id, outcome_data
                )
                ai_reflection = reflection_result.get("reflection")
                learning_insights = reflection_result.get("insights", [])
                
                # Store AI feedback
                if ai_reflection:
                    feedback_id = f"feedback_{uuid.uuid4().hex[:8]}"
                    self.strategy_store.store_ai_feedback(
                        feedback_id=feedback_id,
                        strategy_id=strategy_id,
                        user_id=user_id,
                        feedback_type="outcome_reflection",
                        feedback_content={
                            "outcome_data": outcome_data.__dict__,
                            "reflection": ai_reflection,
                            "insights": learning_insights
                        },
                        ai_reflection=ai_reflection
                    )
            
            # Update strategy confidence based on outcome
            await self._update_strategy_confidence(strategy_id, outcome_data)
            
            return FeedbackResponse(
                success=True,
                message="Trade outcome recorded successfully",
                outcome_id=outcome_id,
                ai_reflection=ai_reflection,
                learning_insights=learning_insights
            )
            
        except Exception as e:
            logger.error(f"Failed to record trade outcome: {e}")
            return FeedbackResponse(
                success=False,
                message=f"Error recording outcome: {str(e)}",
                outcome_id=outcome_id if 'outcome_id' in locals() else None
            )
    
    async def _generate_ai_reflection(
        self, 
        strategy_id: str, 
        outcome_data: TradeOutcomeData
    ) -> Dict[str, Any]:
        """Generate AI reflection on strategy performance"""
        try:
            # Get original strategy data
            strategy_data = self._get_strategy_context(strategy_id)
            if not strategy_data:
                return {"reflection": None, "insights": []}
            
            # Create reflection prompt
            reflection_prompt = self._create_reflection_prompt(strategy_data, outcome_data)
            
            # Get AI reflection
            if self.reflection_provider and await self.reflection_provider.is_available():
                response = await self.reflection_provider.generate_analysis(
                    prompt=reflection_prompt,
                    analysis_type="strategy_reflection",
                    context={
                        "strategy_id": strategy_id,
                        "outcome": outcome_data.outcome.value,
                        "return": outcome_data.actual_return
                    }
                )
                
                if response.success:
                    # Parse reflection and extract insights
                    reflection_text = response.analysis
                    insights = self._extract_learning_insights(reflection_text, outcome_data)
                    
                    return {
                        "reflection": reflection_text,
                        "insights": insights
                    }
            
            return {"reflection": None, "insights": []}
            
        except Exception as e:
            logger.error(f"Failed to generate AI reflection: {e}")
            return {"reflection": None, "insights": []}
    
    def _get_strategy_context(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Get strategy context for reflection"""
        try:
            with self.strategy_store.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT strategy_content, strategy_type, confidence_score,
                           confidence_reason, tags, symbols, timeframe,
                           risk_level, expected_return, metadata
                    FROM ai_strategies WHERE strategy_id = ?
                """, (strategy_id,))
                
                result = cursor.fetchone()
                if result:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, result))
                    
                return None
                
        except Exception as e:
            logger.error(f"Failed to get strategy context: {e}")
            return None
    
    def _create_reflection_prompt(
        self, 
        strategy_data: Dict[str, Any], 
        outcome_data: TradeOutcomeData
    ) -> str:
        """Create reflection prompt for AI analysis"""
        
        # Parse strategy metadata
        try:
            metadata = json.loads(strategy_data.get('metadata', '{}'))
            tags = json.loads(strategy_data.get('tags', '[]'))
            symbols = json.loads(strategy_data.get('symbols', '[]'))
        except:
            metadata = {}
            tags = []
            symbols = []
        
        prompt = f"""
STRATEGY PERFORMANCE REFLECTION

You are an AI trading analyst reflecting on the performance of a strategy you previously generated.
Your goal is to learn from this outcome and improve future strategy generation.

ORIGINAL STRATEGY:
- Type: {strategy_data.get('strategy_type', 'Unknown')}
- Confidence Score: {strategy_data.get('confidence_score', 'N/A')}
- Confidence Reason: {strategy_data.get('confidence_reason', 'N/A')}
- Risk Level: {strategy_data.get('risk_level', 'N/A')}
- Expected Return: {strategy_data.get('expected_return', 'N/A')}%
- Timeframe: {strategy_data.get('timeframe', 'N/A')}
- Symbols: {', '.join(symbols)}
- Tags: {', '.join(tags)}

STRATEGY CONTENT:
{strategy_data.get('strategy_content', 'N/A')}

ACTUAL OUTCOME:
- Result: {outcome_data.outcome.value.upper()}
- Actual Return: {outcome_data.actual_return}%
- Duration: {outcome_data.duration_hours} hours
- Max Profit: {outcome_data.max_profit}%
- Max Loss: {outcome_data.max_loss}%
- Exit Reason: {outcome_data.exit_reason or 'N/A'}
- Notes: {outcome_data.notes or 'N/A'}

REFLECTION ANALYSIS:
Please provide a detailed reflection covering:

1. OUTCOME ANALYSIS:
   - Was the outcome expected based on your original confidence?
   - How did actual performance compare to expected return?
   - What factors might have contributed to this outcome?

2. STRATEGY EVALUATION:
   - Were the entry/exit criteria appropriate?
   - Was the risk assessment accurate?
   - Did the timeframe match the strategy type?

3. LEARNING INSIGHTS:
   - What would you do differently next time?
   - What patterns or signals should be weighted more/less?
   - How should confidence scoring be adjusted for similar strategies?

4. FUTURE IMPROVEMENTS:
   - What specific improvements would enhance similar strategies?
   - Should any tags or classifications be reconsidered?
   - What additional context would have been helpful?

Provide specific, actionable insights that can improve future strategy generation.
"""
        return prompt
    
    def _extract_learning_insights(
        self, 
        reflection_text: str, 
        outcome_data: TradeOutcomeData
    ) -> List[LearningInsight]:
        """Extract structured learning insights from reflection text"""
        insights = []
        
        try:
            # Define insight categories and patterns
            insight_patterns = {
                "confidence_adjustment": [
                    "confidence", "overconfident", "underconfident", "score"
                ],
                "risk_management": [
                    "risk", "stop loss", "position size", "drawdown"
                ],
                "timing": [
                    "timing", "entry", "exit", "timeframe", "duration"
                ],
                "market_conditions": [
                    "market", "volatility", "trend", "conditions"
                ],
                "technical_analysis": [
                    "technical", "indicator", "signal", "pattern"
                ],
                "fundamental_analysis": [
                    "fundamental", "earnings", "news", "economic"
                ]
            }
            
            # Extract insights based on patterns and outcome
            for category, keywords in insight_patterns.items():
                if any(keyword.lower() in reflection_text.lower() for keyword in keywords):
                    # Determine insight based on outcome and category
                    if outcome_data.outcome == TradeOutcome.WIN:
                        insight_type = f"successful_{category}"
                        confidence = 0.8
                    elif outcome_data.outcome == TradeOutcome.LOSS:
                        insight_type = f"failed_{category}"
                        confidence = 0.9  # Higher confidence in learning from failures
                    else:
                        insight_type = f"neutral_{category}"
                        confidence = 0.6
                    
                    insights.append(LearningInsight(
                        insight_type=insight_type,
                        category=category,
                        description=f"Learning from {outcome_data.outcome.value} outcome in {category}",
                        confidence=confidence,
                        applicable_strategies=[category]
                    ))
            
            # Add outcome-specific insights
            if outcome_data.actual_return is not None:
                if outcome_data.actual_return > 5.0:
                    insights.append(LearningInsight(
                        insight_type="high_return_strategy",
                        category="performance",
                        description="Strategy achieved high returns - analyze for replication",
                        confidence=0.9,
                        applicable_strategies=["momentum", "breakout"]
                    ))
                elif outcome_data.actual_return < -5.0:
                    insights.append(LearningInsight(
                        insight_type="high_loss_strategy",
                        category="risk_management",
                        description="Strategy had significant losses - review risk controls",
                        confidence=0.9,
                        applicable_strategies=["all"]
                    ))
            
        except Exception as e:
            logger.error(f"Failed to extract learning insights: {e}")
        
        return insights
    
    async def _update_strategy_confidence(
        self, 
        strategy_id: str, 
        outcome_data: TradeOutcomeData
    ):
        """Update strategy confidence score based on outcome"""
        try:
            # Get current strategy performance
            performance = self.strategy_store.get_strategy_performance(strategy_id)
            
            if performance and performance['total_trades'] >= 3:  # Need some history
                # Calculate new confidence based on performance
                win_rate = performance['win_rate']
                avg_return = performance['average_return']
                total_trades = performance['total_trades']
                
                # Confidence formula: weighted average of win rate and returns
                # More trades = more reliable confidence
                trade_weight = min(1.0, total_trades / 10.0)  # Max weight at 10 trades
                base_confidence = (win_rate * 0.6) + (max(0, avg_return / 10.0) * 0.4)
                new_confidence = base_confidence * trade_weight
                
                # Clamp between 0.1 and 0.95
                new_confidence = max(0.1, min(0.95, new_confidence))
                
                # Update strategy confidence in database
                with self.strategy_store.get_connection() as conn:
                    conn.execute("""
                        UPDATE ai_strategies 
                        SET confidence_score = ?
                        WHERE strategy_id = ?
                    """, (new_confidence, strategy_id))
                
                logger.info(f"Updated confidence for strategy {strategy_id}: {new_confidence:.2f}")
                
        except Exception as e:
            logger.error(f"Failed to update strategy confidence: {e}")
    
    def get_strategy_learning_history(
        self, 
        strategy_id: str
    ) -> List[Dict[str, Any]]:
        """Get learning history for a specific strategy"""
        try:
            with self.strategy_store.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT f.*, t.outcome, t.actual_return, t.recorded_at
                    FROM ai_feedback f
                    JOIN trade_outcomes t ON f.strategy_id = t.strategy_id
                    WHERE f.strategy_id = ?
                    ORDER BY f.created_at DESC
                """, (strategy_id,))
                
                results = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                return [dict(zip(columns, result)) for result in results]
                
        except Exception as e:
            logger.error(f"Failed to get learning history: {e}")
            return []
    
    def get_learning_insights_summary(
        self, 
        user_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get summary of learning insights over time period"""
        try:
            with self.strategy_store.get_connection() as conn:
                # Get feedback data
                base_query = """
                    SELECT f.feedback_content, f.created_at, t.outcome, t.actual_return
                    FROM ai_feedback f
                    JOIN trade_outcomes t ON f.strategy_id = t.strategy_id
                    WHERE f.created_at >= datetime('now', '-{} days')
                """.format(days)
                
                params = []
                if user_id:
                    base_query += " AND f.user_id = ?"
                    params.append(user_id)
                
                cursor = conn.execute(base_query, params)
                feedback_data = cursor.fetchall()
                
                # Analyze insights
                total_trades = len(feedback_data)
                wins = sum(1 for row in feedback_data if row[2] == 'win')
                losses = sum(1 for row in feedback_data if row[2] == 'loss')
                avg_return = sum(row[3] for row in feedback_data if row[3] is not None) / max(1, total_trades)
                
                # Extract common learning themes
                learning_themes = self._extract_common_themes(feedback_data)
                
                return {
                    "period_days": days,
                    "total_trades": total_trades,
                    "wins": wins,
                    "losses": losses,
                    "win_rate": wins / max(1, total_trades),
                    "average_return": avg_return,
                    "learning_themes": learning_themes,
                    "generated_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to get learning insights summary: {e}")
            return {}
    
    def _extract_common_themes(self, feedback_data: List[tuple]) -> List[Dict[str, Any]]:
        """Extract common learning themes from feedback data"""
        themes = {}
        
        try:
            for row in feedback_data:
                feedback_content = json.loads(row[0])
                insights = feedback_content.get('insights', [])
                
                for insight in insights:
                    if isinstance(insight, dict):
                        category = insight.get('category', 'general')
                        if category not in themes:
                            themes[category] = {
                                "count": 0,
                                "examples": [],
                                "avg_confidence": 0.0
                            }
                        
                        themes[category]["count"] += 1
                        themes[category]["examples"].append(insight.get('description', ''))
                        themes[category]["avg_confidence"] += insight.get('confidence', 0.0)
            
            # Calculate averages and format
            formatted_themes = []
            for category, data in themes.items():
                if data["count"] > 0:
                    formatted_themes.append({
                        "category": category,
                        "frequency": data["count"],
                        "avg_confidence": data["avg_confidence"] / data["count"],
                        "top_examples": data["examples"][:3]  # Top 3 examples
                    })
            
            # Sort by frequency
            return sorted(formatted_themes, key=lambda x: x["frequency"], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to extract common themes: {e}")
            return [] 