"""
Portfolio Analyzer Integration with Trading Engine
Creates feedback loop between execution results and AI analysis
"""
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from app.trading_engine.models import Position, Order, Execution
from app.trading_engine.position_manager import PositionManager
from app.database.service import get_db_connection
from app.ai_engine.service import AIService
from app.ai_engine.provider_failover import failover_manager

logger = logging.getLogger(__name__)

@dataclass
class ExecutionFeedback:
    """Feedback data from trade execution"""
    order_id: str
    symbol: str
    execution_price: float
    predicted_price: float
    execution_time: datetime
    slippage: float
    market_impact: float
    success_score: float

@dataclass
class PerformanceMetrics:
    """Performance metrics for AI recommendations"""
    total_recommendations: int
    successful_recommendations: int
    average_return: float
    hit_rate: float
    average_holding_period: float
    risk_adjusted_return: float

class PortfolioAnalyzerIntegration:
    """
    Integrates portfolio analyzer with trading engine for continuous improvement
    """
    
    def __init__(self):
        self.ai_service = AIService()
        self.position_manager = PositionManager()
        
    async def update_portfolio_with_execution_data(self, user_id: str, execution: Execution) -> Dict[str, Any]:
        """
        Update portfolio analysis with real-time execution data
        """
        try:
            logger.info(f"Updating portfolio analysis with execution data - User: {user_id}, Symbol: {execution.symbol}")
            
            # Get current portfolio state
            current_positions = await self.position_manager.get_current_positions(user_id)
            
            # Create updated portfolio data including the new execution
            portfolio_data = await self._create_portfolio_snapshot(user_id, current_positions, execution)
            
            # Get updated AI analysis with failover support
            async def portfolio_analysis_operation(provider: str, user_id: str, portfolio_data: Dict[str, Any]):
                """Portfolio analysis operation with specific provider"""
                return await self.ai_service.analyze_portfolio(user_id, portfolio_data)
            
            updated_analysis = await failover_manager.execute_with_failover(
                user_id, 
                "portfolio_analysis", 
                portfolio_analysis_operation,
                portfolio_data
            )
            
            # Store execution feedback for learning
            await self._store_execution_feedback(user_id, execution, updated_analysis)
            
            # Update recommendation performance tracking
            await self._update_recommendation_performance(user_id, execution)
            
            return {
                'status': 'success',
                'updated_analysis': updated_analysis,
                'portfolio_impact': await self._calculate_portfolio_impact(user_id, execution),
                'performance_metrics': await self._get_performance_metrics(user_id)
            }
            
        except Exception as e:
            logger.error(f"Error updating portfolio with execution data: {e}")
            return {'status': 'error', 'error': str(e)}
    
    async def create_feedback_loop(self, user_id: str, recommendation_id: str, outcome_data: Dict[str, Any]) -> None:
        """
        Create feedback loop from execution results to AI analysis
        """
        try:
            # Store outcome data
            await self._store_recommendation_outcome(user_id, recommendation_id, outcome_data)
            
            # Analyze recommendation performance
            performance_analysis = await self._analyze_recommendation_performance(user_id, recommendation_id)
            
            # Update AI model weights/preferences based on performance
            await self._update_ai_preferences(user_id, performance_analysis)
            
            # Generate insights for future recommendations
            insights = await self._generate_performance_insights(user_id, performance_analysis)
            
            logger.info(f"Feedback loop completed for recommendation {recommendation_id}")
            
        except Exception as e:
            logger.error(f"Error creating feedback loop: {e}")
    
    async def get_portfolio_optimization_suggestions(self, user_id: str) -> Dict[str, Any]:
        """
        Get portfolio optimization suggestions based on execution performance
        """
        try:
            # Get execution history
            execution_history = await self._get_execution_history(user_id)
            
            # Analyze execution patterns
            execution_analysis = await self._analyze_execution_patterns(execution_history)
            
            # Get current portfolio state
            current_positions = await self.position_manager.get_current_positions(user_id)
            
            # Generate optimization suggestions
            suggestions = await self._generate_optimization_suggestions(
                user_id, current_positions, execution_analysis
            )
            
            return {
                'status': 'success',
                'optimization_suggestions': suggestions,
                'execution_analysis': execution_analysis,
                'performance_summary': await self._get_performance_summary(user_id)
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio optimization suggestions: {e}")
            return {'status': 'error', 'error': str(e)}
    
    async def _create_portfolio_snapshot(self, user_id: str, positions: List[Position], execution: Execution) -> Dict[str, Any]:
        """Create portfolio snapshot including new execution"""
        try:
            # Convert positions to portfolio format
            holdings = []
            total_value = 0
            
            for position in positions:
                holding_value = position.quantity * position.current_price
                total_value += holding_value
                
                holdings.append({
                    'tradingsymbol': position.symbol,
                    'quantity': position.quantity,
                    'average_price': position.average_price,
                    'current_price': position.current_price,
                    'current_value': holding_value,
                    'pnl': position.unrealized_pnl,
                    'pnl_percentage': (position.unrealized_pnl / (position.quantity * position.average_price)) * 100 if position.quantity > 0 else 0
                })
            
            return {
                'total_value': total_value,
                'holdings': holdings,
                'positions': [],  # Positions are included in holdings
                'last_updated': datetime.utcnow().isoformat(),
                'execution_context': {
                    'latest_execution': {
                        'symbol': execution.symbol,
                        'side': execution.side,
                        'quantity': execution.quantity,
                        'price': execution.price,
                        'executed_at': execution.executed_at.isoformat()
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating portfolio snapshot: {e}")
            return {}
    
    async def _store_execution_feedback(self, user_id: str, execution: Execution, analysis: Dict[str, Any]) -> None:
        """Store execution feedback for AI learning"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Find related recommendation
            cursor.execute("""
                SELECT id, target_price, confidence_score FROM enhanced_recommendations
                WHERE user_id = ? AND stock_symbol = ? 
                AND implementation_status = 'PENDING'
                ORDER BY created_at DESC LIMIT 1
            """, (user_id, execution.symbol))
            
            recommendation = cursor.fetchone()
            if recommendation:
                rec_id, target_price, confidence = recommendation
                
                # Calculate feedback metrics
                slippage = abs(execution.price - target_price) / target_price if target_price else 0
                success_score = 1.0 - min(slippage, 1.0)  # Simple success metric
                
                feedback = ExecutionFeedback(
                    order_id=execution.order_id,
                    symbol=execution.symbol,
                    execution_price=execution.price,
                    predicted_price=target_price or execution.price,
                    execution_time=execution.executed_at,
                    slippage=slippage,
                    market_impact=0.0,  # Would need market data to calculate
                    success_score=success_score
                )
                
                # Store feedback
                cursor.execute("""
                    INSERT INTO ai_execution_feedback (
                        user_id, recommendation_id, order_id, symbol,
                        execution_price, predicted_price, slippage,
                        success_score, feedback_data, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, rec_id, execution.order_id, execution.symbol,
                    execution.price, target_price, slippage,
                    success_score, json.dumps(analysis), datetime.utcnow()
                ))
                
                conn.commit()
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing execution feedback: {e}")
    
    async def _update_recommendation_performance(self, user_id: str, execution: Execution) -> None:
        """Update recommendation performance tracking"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Find and update related recommendation performance
            cursor.execute("""
                SELECT rp.id, rp.recommendation_id, er.target_price
                FROM recommendation_performance rp
                JOIN enhanced_recommendations er ON rp.recommendation_id = er.id
                WHERE rp.user_id = ? AND rp.stock_symbol = ?
                AND rp.implementation_date IS NULL
                ORDER BY rp.created_at DESC LIMIT 1
            """, (user_id, execution.symbol))
            
            performance_record = cursor.fetchone()
            if performance_record:
                perf_id, rec_id, target_price = performance_record
                
                # Update performance record
                cursor.execute("""
                    UPDATE recommendation_performance SET
                        implementation_date = ?,
                        implementation_method = 'AUTO_TRADING',
                        implementation_price = ?,
                        predicted_price = ?
                    WHERE id = ?
                """, (execution.executed_at, execution.price, target_price, perf_id))
                
                # Update recommendation status
                cursor.execute("""
                    UPDATE enhanced_recommendations SET
                        implementation_status = 'IMPLEMENTED',
                        implementation_date = ?,
                        implementation_method = 'AUTO_TRADING'
                    WHERE id = ?
                """, (execution.executed_at, rec_id))
                
                conn.commit()
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating recommendation performance: {e}")
    
    async def _calculate_portfolio_impact(self, user_id: str, execution: Execution) -> Dict[str, Any]:
        """Calculate the impact of execution on portfolio"""
        try:
            # Get portfolio before and after execution
            positions = await self.position_manager.get_current_positions(user_id)
            
            # Calculate impact metrics
            total_portfolio_value = sum(pos.quantity * pos.current_price for pos in positions)
            execution_value = execution.quantity * execution.price
            
            impact = {
                'execution_value': execution_value,
                'portfolio_percentage': (execution_value / total_portfolio_value) * 100 if total_portfolio_value > 0 else 0,
                'position_change': execution.quantity,
                'price_impact': 0.0,  # Would need market data to calculate
                'liquidity_impact': 'low'  # Simplified assessment
            }
            
            return impact
            
        except Exception as e:
            logger.error(f"Error calculating portfolio impact: {e}")
            return {}
    
    async def _get_performance_metrics(self, user_id: str) -> PerformanceMetrics:
        """Get performance metrics for user's AI recommendations"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get recommendation performance data
            cursor.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN recommendation_success = 1 THEN 1 ELSE 0 END) as successful,
                       AVG(portfolio_impact) as avg_return,
                       AVG(accuracy_score_7d) as hit_rate
                FROM recommendation_performance
                WHERE user_id = ? AND implementation_date IS NOT NULL
            """, (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                total, successful, avg_return, hit_rate = result
                return PerformanceMetrics(
                    total_recommendations=total or 0,
                    successful_recommendations=successful or 0,
                    average_return=avg_return or 0.0,
                    hit_rate=hit_rate or 0.0,
                    average_holding_period=7.0,  # Simplified
                    risk_adjusted_return=0.0  # Would need more complex calculation
                )
            
            return PerformanceMetrics(0, 0, 0.0, 0.0, 0.0, 0.0)
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return PerformanceMetrics(0, 0, 0.0, 0.0, 0.0, 0.0)
    
    async def _store_recommendation_outcome(self, user_id: str, recommendation_id: str, outcome_data: Dict[str, Any]) -> None:
        """Store recommendation outcome for learning"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO ai_recommendation_outcomes (
                    user_id, recommendation_id, outcome_data,
                    success_score, created_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                user_id, recommendation_id, json.dumps(outcome_data),
                outcome_data.get('success_score', 0.0), datetime.utcnow()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing recommendation outcome: {e}")
    
    async def _analyze_recommendation_performance(self, user_id: str, recommendation_id: str) -> Dict[str, Any]:
        """Analyze performance of specific recommendation"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM recommendation_performance
                WHERE user_id = ? AND recommendation_id = ?
            """, (user_id, recommendation_id))
            
            performance_data = cursor.fetchone()
            conn.close()
            
            if performance_data:
                # Analyze performance patterns
                analysis = {
                    'accuracy': performance_data[12] if len(performance_data) > 12 else 0.0,  # accuracy_score_7d
                    'return': performance_data[16] if len(performance_data) > 16 else 0.0,    # portfolio_impact
                    'success': performance_data[17] if len(performance_data) > 17 else False, # recommendation_success
                    'lessons_learned': performance_data[19] if len(performance_data) > 19 else ''
                }
                return analysis
            
            return {}
            
        except Exception as e:
            logger.error(f"Error analyzing recommendation performance: {e}")
            return {}
    
    async def _update_ai_preferences(self, user_id: str, performance_analysis: Dict[str, Any]) -> None:
        """Update AI preferences based on performance"""
        try:
            # This would update AI model weights or user preferences
            # based on what's working well for this specific user
            
            # For now, we'll update user preferences in the database
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get current preferences
            cursor.execute("""
                SELECT provider_priorities, cost_limits FROM ai_user_preferences
                WHERE user_id = ?
            """, (user_id,))
            
            result = cursor.fetchone()
            if result:
                # Update preferences based on performance
                # This is a simplified implementation
                success_rate = performance_analysis.get('accuracy', 0.0)
                if success_rate > 0.8:
                    # Increase confidence in current provider
                    logger.info(f"High success rate for user {user_id}, maintaining current preferences")
                elif success_rate < 0.4:
                    # Consider adjusting preferences
                    logger.info(f"Low success rate for user {user_id}, may need preference adjustment")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating AI preferences: {e}")
    
    async def _generate_performance_insights(self, user_id: str, performance_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights for future recommendations"""
        try:
            insights = {
                'success_patterns': [],
                'failure_patterns': [],
                'optimization_suggestions': [],
                'risk_adjustments': []
            }
            
            # Analyze success patterns
            if performance_analysis.get('success', False):
                insights['success_patterns'].append({
                    'pattern': 'successful_execution',
                    'confidence_boost': 0.1,
                    'recommendation': 'Continue similar analysis approach'
                })
            
            # Analyze failure patterns
            if not performance_analysis.get('success', True):
                insights['failure_patterns'].append({
                    'pattern': 'execution_failure',
                    'confidence_reduction': 0.1,
                    'recommendation': 'Review market conditions and timing'
                })
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating performance insights: {e}")
            return {}
    
    async def _get_execution_history(self, user_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get execution history for analysis"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM trading_executions
                WHERE user_id = ? AND executed_at > datetime('now', '-{} days')
                ORDER BY executed_at DESC
            """.format(days), (user_id,))
            
            executions = cursor.fetchall()
            conn.close()
            
            # Convert to list of dictionaries
            execution_history = []
            for execution in executions:
                execution_history.append({
                    'id': execution[0],
                    'order_id': execution[1],
                    'symbol': execution[3],
                    'side': execution[4],
                    'quantity': execution[5],
                    'price': execution[6],
                    'executed_at': execution[8]
                })
            
            return execution_history
            
        except Exception as e:
            logger.error(f"Error getting execution history: {e}")
            return []
    
    async def _analyze_execution_patterns(self, execution_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patterns in execution history"""
        try:
            if not execution_history:
                return {}
            
            # Analyze execution patterns
            symbols = [ex['symbol'] for ex in execution_history]
            sides = [ex['side'] for ex in execution_history]
            
            analysis = {
                'total_executions': len(execution_history),
                'unique_symbols': len(set(symbols)),
                'buy_sell_ratio': sides.count('BUY') / len(sides) if sides else 0,
                'most_traded_symbols': self._get_most_frequent(symbols, 5),
                'execution_frequency': len(execution_history) / 30,  # per day
                'average_execution_size': sum(ex['quantity'] for ex in execution_history) / len(execution_history)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing execution patterns: {e}")
            return {}
    
    def _get_most_frequent(self, items: List[str], limit: int) -> List[Dict[str, Any]]:
        """Get most frequent items from list"""
        from collections import Counter
        counter = Counter(items)
        return [{'item': item, 'count': count} for item, count in counter.most_common(limit)]
    
    async def _generate_optimization_suggestions(self, user_id: str, positions: List[Position], execution_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate portfolio optimization suggestions"""
        try:
            suggestions = []
            
            # Analyze position concentration
            if positions:
                total_value = sum(pos.quantity * pos.current_price for pos in positions)
                for position in positions:
                    position_pct = (position.quantity * position.current_price) / total_value * 100
                    if position_pct > 20:  # High concentration
                        suggestions.append({
                            'type': 'diversification',
                            'symbol': position.symbol,
                            'current_allocation': position_pct,
                            'suggested_allocation': 15.0,
                            'reasoning': 'Reduce concentration risk',
                            'priority': 'medium'
                        })
            
            # Analyze execution frequency
            exec_freq = execution_analysis.get('execution_frequency', 0)
            if exec_freq > 2:  # More than 2 executions per day
                suggestions.append({
                    'type': 'trading_frequency',
                    'current_frequency': exec_freq,
                    'suggested_frequency': 1.0,
                    'reasoning': 'Reduce trading costs and improve performance',
                    'priority': 'low'
                })
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating optimization suggestions: {e}")
            return []
    
    async def _get_performance_summary(self, user_id: str) -> Dict[str, Any]:
        """Get performance summary for user"""
        try:
            metrics = await self._get_performance_metrics(user_id)
            
            return {
                'total_recommendations': metrics.total_recommendations,
                'success_rate': metrics.hit_rate,
                'average_return': metrics.average_return,
                'risk_adjusted_return': metrics.risk_adjusted_return,
                'performance_grade': self._calculate_performance_grade(metrics)
            }
            
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {}
    
    def _calculate_performance_grade(self, metrics: PerformanceMetrics) -> str:
        """Calculate performance grade based on metrics"""
        if metrics.hit_rate >= 0.8 and metrics.average_return > 0.1:
            return 'A'
        elif metrics.hit_rate >= 0.6 and metrics.average_return > 0.05:
            return 'B'
        elif metrics.hit_rate >= 0.4:
            return 'C'
        else:
            return 'D'

# Integration functions
async def update_portfolio_analysis_with_execution(user_id: str, execution: Execution) -> Dict[str, Any]:
    """
    Update portfolio analysis with execution data
    Called from trading engine after successful execution
    """
    integration = PortfolioAnalyzerIntegration()
    return await integration.update_portfolio_with_execution_data(user_id, execution)

async def create_ai_feedback_loop(user_id: str, recommendation_id: str, outcome_data: Dict[str, Any]) -> None:
    """
    Create feedback loop for AI learning
    Called when recommendation outcomes are available
    """
    integration = PortfolioAnalyzerIntegration()
    await integration.create_feedback_loop(user_id, recommendation_id, outcome_data)