"""
Strategy Lifecycle Management
Manages the complete lifecycle of trading strategies from creation to retirement
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from .strategy_manager import strategy_manager, StrategyConfig, StrategyInstance, StrategyStatus
from .strategy_controller import strategy_controller
from .event_bus import event_bus, EventType, publish_order_event
from .monitoring import trading_monitor, time_async_operation
from .position_manager import position_manager
from .order_service import order_service

logger = logging.getLogger(__name__)

class LifecycleStage(str, Enum):
    """Strategy lifecycle stages"""
    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    DEPLOYED = "DEPLOYED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    RETIRED = "RETIRED"
    ARCHIVED = "ARCHIVED"

@dataclass
class LifecycleEvent:
    """Strategy lifecycle event"""
    event_id: str
    strategy_id: str
    stage: LifecycleStage
    previous_stage: Optional[LifecycleStage]
    timestamp: datetime
    triggered_by: str
    reason: str
    metadata: Dict[str, Any]

@dataclass
class StrategyAnalysis:
    """Strategy performance analysis"""
    strategy_id: str
    analysis_period: int  # days
    total_trades: int
    profitable_trades: int
    loss_trades: int
    win_rate: float
    total_return: float
    max_drawdown: float
    sharpe_ratio: float
    volatility: float
    avg_trade_duration: float
    risk_adjusted_return: float
    consistency_score: float
    recommendation: str  # CONTINUE, OPTIMIZE, PAUSE, RETIRE
    analysis_date: datetime

@dataclass
class OptimizationSuggestion:
    """Strategy optimization suggestion"""
    suggestion_id: str
    strategy_id: str
    category: str  # PARAMETERS, RISK, TIMING, SYMBOLS
    priority: str  # HIGH, MEDIUM, LOW
    description: str
    current_value: Any
    suggested_value: Any
    expected_improvement: str
    confidence: float
    created_at: datetime

class StrategyLifecycleManager:
    """
    Manages the complete lifecycle of trading strategies
    """
    
    def __init__(self):
        self.lifecycle_events = {}  # strategy_id -> List[LifecycleEvent]
        self.strategy_analyses = {}  # strategy_id -> List[StrategyAnalysis]
        self.optimization_suggestions = {}  # strategy_id -> List[OptimizationSuggestion]
        self.retirement_candidates = set()  # Set of strategy IDs
        
        # Lifecycle management settings
        self.lifecycle_settings = {
            'auto_analysis_interval_days': 7,
            'min_trades_for_analysis': 20,
            'retirement_criteria': {
                'min_age_days': 30,
                'max_drawdown_threshold': 0.25,
                'min_win_rate_threshold': 0.35,
                'min_sharpe_ratio': -0.5,
                'consecutive_loss_days': 14
            },
            'optimization_criteria': {
                'performance_decline_threshold': 0.1,
                'volatility_increase_threshold': 0.2,
                'drawdown_increase_threshold': 0.05
            }
        }
        
        # Start lifecycle monitoring
        self._monitoring_task = None
        self._start_lifecycle_monitoring()
        
        logger.info("StrategyLifecycleManager initialized")
    
    def _start_lifecycle_monitoring(self):
        """Start background lifecycle monitoring"""
        if self._monitoring_task is None or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(self._lifecycle_monitoring_loop())
    
    async def _lifecycle_monitoring_loop(self):
        """Background lifecycle monitoring loop"""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                
                # Get all deployed strategies
                deployed_strategies = strategy_manager.deployed_strategies
                
                for strategy_id in deployed_strategies.keys():
                    await self._check_strategy_lifecycle(strategy_id)
                
                # Clean up old events and analyses
                await self._cleanup_old_data()
                
            except Exception as e:
                logger.error(f"Error in lifecycle monitoring loop: {e}")
                await asyncio.sleep(1800)  # Wait 30 minutes on error
    
    async def _check_strategy_lifecycle(self, strategy_id: str):
        """Check if strategy needs lifecycle actions"""
        try:
            # Check if analysis is needed
            if await self._needs_analysis(strategy_id):
                await self.analyze_strategy_performance(strategy_id)
            
            # Check for retirement candidates
            if await self._should_consider_retirement(strategy_id):
                await self._add_retirement_candidate(strategy_id)
            
            # Check for optimization opportunities
            if await self._needs_optimization_review(strategy_id):
                await self.generate_optimization_suggestions(strategy_id)
            
        except Exception as e:
            logger.error(f"Error checking lifecycle for strategy {strategy_id}: {e}")
    
    @time_async_operation("create_strategy_lifecycle")
    async def create_strategy_lifecycle(self, config: StrategyConfig) -> Dict[str, Any]:
        """
        Create a new strategy with full lifecycle tracking
        
        Args:
            config: Strategy configuration
            
        Returns:
            Creation result with lifecycle information
        """
        try:
            logger.info(f"Creating strategy lifecycle for {config.id}")
            
            # Record creation event
            await self._record_lifecycle_event(
                config.id, LifecycleStage.CREATED, None,
                "USER", "Strategy created", {'config': asdict(config)}
            )
            
            # Validate configuration
            validation_result = await self._validate_strategy_for_lifecycle(config)
            if not validation_result['valid']:
                await self._record_lifecycle_event(
                    config.id, LifecycleStage.CREATED, LifecycleStage.CREATED,
                    "SYSTEM", f"Validation failed: {validation_result['errors']}", {}
                )
                return {
                    'success': False,
                    'error': 'Strategy validation failed',
                    'details': validation_result['errors']
                }
            
            # Record validation success
            await self._record_lifecycle_event(
                config.id, LifecycleStage.VALIDATED, LifecycleStage.CREATED,
                "SYSTEM", "Strategy validated successfully", validation_result
            )
            
            # Deploy strategy
            deployment_result = await strategy_manager.deploy_strategy(config)
            
            if deployment_result['success']:
                await self._record_lifecycle_event(
                    config.id, LifecycleStage.DEPLOYED, LifecycleStage.VALIDATED,
                    "SYSTEM", "Strategy deployed successfully", deployment_result
                )
                
                await self._record_lifecycle_event(
                    config.id, LifecycleStage.ACTIVE, LifecycleStage.DEPLOYED,
                    "SYSTEM", "Strategy activated", {}
                )
                
                # Initialize lifecycle tracking
                await self._initialize_lifecycle_tracking(config.id)
                
                trading_monitor.increment_counter("strategy_lifecycles_created")
                
                return {
                    'success': True,
                    'strategy_id': config.id,
                    'lifecycle_stage': LifecycleStage.ACTIVE.value,
                    'deployment_result': deployment_result
                }
            else:
                await self._record_lifecycle_event(
                    config.id, LifecycleStage.CREATED, LifecycleStage.VALIDATED,
                    "SYSTEM", f"Deployment failed: {deployment_result.get('error', 'Unknown error')}", 
                    deployment_result
                )
                
                return {
                    'success': False,
                    'error': 'Strategy deployment failed',
                    'details': deployment_result
                }
                
        except Exception as e:
            error_msg = f"Error creating strategy lifecycle for {config.id}: {str(e)}"
            logger.error(error_msg)
            
            await self._record_lifecycle_event(
                config.id, LifecycleStage.CREATED, None,
                "SYSTEM", f"Creation error: {str(e)}", {'error': error_msg}
            )
            
            return {
                'success': False,
                'error': error_msg
            }
    
    async def _validate_strategy_for_lifecycle(self, config: StrategyConfig) -> Dict[str, Any]:
        """Enhanced validation for lifecycle management"""
        try:
            # Use existing validation from strategy manager
            base_validation = await strategy_manager._validate_strategy_config(config)
            
            # Add lifecycle-specific validations
            lifecycle_errors = []
            lifecycle_warnings = []
            
            # Check for reasonable parameter ranges
            if config.max_positions > 50:
                lifecycle_warnings.append("High max_positions may impact performance monitoring")
            
            if config.max_daily_trades > 200:
                lifecycle_warnings.append("Very high daily trade limit may indicate overtrading")
            
            # Check risk parameters for lifecycle management
            if config.risk_parameters.max_drawdown_percent > 30:
                lifecycle_errors.append("Max drawdown too high for automated lifecycle management")
            
            # Combine validations
            all_errors = base_validation['errors'] + lifecycle_errors
            all_warnings = base_validation['warnings'] + lifecycle_warnings
            
            return {
                'valid': len(all_errors) == 0,
                'errors': all_errors,
                'warnings': all_warnings,
                'lifecycle_specific': {
                    'errors': lifecycle_errors,
                    'warnings': lifecycle_warnings
                }
            }
            
        except Exception as e:
            logger.error(f"Error in lifecycle validation: {e}")
            return {
                'valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': []
            }
    
    async def _initialize_lifecycle_tracking(self, strategy_id: str):
        """Initialize lifecycle tracking for a strategy"""
        try:
            # Initialize event tracking
            if strategy_id not in self.lifecycle_events:
                self.lifecycle_events[strategy_id] = []
            
            # Initialize analysis tracking
            if strategy_id not in self.strategy_analyses:
                self.strategy_analyses[strategy_id] = []
            
            # Initialize optimization tracking
            if strategy_id not in self.optimization_suggestions:
                self.optimization_suggestions[strategy_id] = []
            
            logger.debug(f"Initialized lifecycle tracking for strategy {strategy_id}")
            
        except Exception as e:
            logger.error(f"Error initializing lifecycle tracking for {strategy_id}: {e}")
    
    async def _record_lifecycle_event(self, strategy_id: str, stage: LifecycleStage,
                                    previous_stage: Optional[LifecycleStage],
                                    triggered_by: str, reason: str, 
                                    metadata: Dict[str, Any]):
        """Record a lifecycle event"""
        try:
            event_id = f"{strategy_id}_{stage.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            event = LifecycleEvent(
                event_id=event_id,
                strategy_id=strategy_id,
                stage=stage,
                previous_stage=previous_stage,
                timestamp=datetime.now(),
                triggered_by=triggered_by,
                reason=reason,
                metadata=metadata
            )
            
            if strategy_id not in self.lifecycle_events:
                self.lifecycle_events[strategy_id] = []
            
            self.lifecycle_events[strategy_id].append(event)
            
            # Publish lifecycle event
            strategy_status = await strategy_manager.get_strategy_status(strategy_id)
            if strategy_status:
                await publish_order_event(strategy_status.get('user_id'), EventType.STRATEGY_LIFECYCLE, {
                    'event_id': event_id,
                    'strategy_id': strategy_id,
                    'stage': stage.value,
                    'previous_stage': previous_stage.value if previous_stage else None,
                    'triggered_by': triggered_by,
                    'reason': reason,
                    'timestamp': event.timestamp.isoformat()
                })
            
            logger.debug(f"Recorded lifecycle event for {strategy_id}: {stage.value}")
            
        except Exception as e:
            logger.error(f"Error recording lifecycle event for {strategy_id}: {e}")
    
    @time_async_operation("analyze_strategy_performance")
    async def analyze_strategy_performance(self, strategy_id: str, 
                                         analysis_period: int = 30) -> Optional[StrategyAnalysis]:
        """
        Perform comprehensive strategy performance analysis
        
        Args:
            strategy_id: Strategy ID to analyze
            analysis_period: Analysis period in days
            
        Returns:
            Strategy analysis result
        """
        try:
            logger.info(f"Analyzing performance for strategy {strategy_id}")
            
            # Get strategy performance data
            performance = await strategy_manager.get_strategy_performance(strategy_id, analysis_period)
            if not performance:
                logger.warning(f"No performance data available for strategy {strategy_id}")
                return None
            
            # Get strategy status for additional metrics
            status = await strategy_manager.get_strategy_status(strategy_id)
            if not status:
                return None
            
            # Calculate advanced metrics
            win_rate = performance['win_rate']
            total_return = performance['total_pnl']
            max_drawdown = performance['max_drawdown']
            sharpe_ratio = performance['sharpe_ratio']
            volatility = performance.get('volatility', 0.0)
            
            # Calculate consistency score (simplified)
            consistency_score = self._calculate_consistency_score(performance, status)
            
            # Calculate risk-adjusted return
            risk_adjusted_return = total_return / max(max_drawdown, 0.01)  # Avoid division by zero
            
            # Generate recommendation
            recommendation = self._generate_performance_recommendation(
                win_rate, total_return, max_drawdown, sharpe_ratio, consistency_score
            )
            
            # Create analysis
            analysis = StrategyAnalysis(
                strategy_id=strategy_id,
                analysis_period=analysis_period,
                total_trades=performance['total_trades'],
                profitable_trades=performance['winning_trades'],
                loss_trades=performance['losing_trades'],
                win_rate=win_rate,
                total_return=total_return,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                volatility=volatility,
                avg_trade_duration=performance.get('avg_trade_duration', 0.0),
                risk_adjusted_return=risk_adjusted_return,
                consistency_score=consistency_score,
                recommendation=recommendation,
                analysis_date=datetime.now()
            )
            
            # Store analysis
            if strategy_id not in self.strategy_analyses:
                self.strategy_analyses[strategy_id] = []
            self.strategy_analyses[strategy_id].append(analysis)
            
            # Record lifecycle event
            await self._record_lifecycle_event(
                strategy_id, LifecycleStage.ACTIVE, LifecycleStage.ACTIVE,
                "SYSTEM", f"Performance analysis completed: {recommendation}",
                asdict(analysis)
            )
            
            # Take action based on recommendation
            await self._act_on_analysis_recommendation(strategy_id, analysis)
            
            trading_monitor.increment_counter("strategy_analyses_completed")
            logger.info(f"Performance analysis completed for strategy {strategy_id}: {recommendation}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing strategy performance {strategy_id}: {e}")
            return None
    
    def _calculate_consistency_score(self, performance: Dict[str, Any], 
                                   status: Dict[str, Any]) -> float:
        """Calculate strategy consistency score (0.0 to 1.0)"""
        try:
            # Simplified consistency calculation
            # In production, this would analyze trade distribution, timing, etc.
            
            win_rate = performance['win_rate']
            total_trades = performance['total_trades']
            
            # Base score from win rate
            base_score = min(win_rate * 2, 1.0)  # Scale win rate
            
            # Adjust for trade frequency consistency
            if total_trades > 0:
                expected_daily_trades = status.get('max_daily_trades', 10) * 0.3  # 30% of max
                actual_daily_trades = total_trades / max(performance.get('analysis_period', 30), 1)
                frequency_consistency = 1.0 - abs(actual_daily_trades - expected_daily_trades) / expected_daily_trades
                frequency_consistency = max(0.0, min(1.0, frequency_consistency))
            else:
                frequency_consistency = 0.0
            
            # Combine scores
            consistency_score = (base_score * 0.7) + (frequency_consistency * 0.3)
            
            return max(0.0, min(1.0, consistency_score))
            
        except Exception as e:
            logger.error(f"Error calculating consistency score: {e}")
            return 0.5  # Default moderate score
    
    def _generate_performance_recommendation(self, win_rate: float, total_return: float,
                                           max_drawdown: float, sharpe_ratio: float,
                                           consistency_score: float) -> str:
        """Generate performance-based recommendation"""
        try:
            # Define thresholds
            good_win_rate = 0.55
            acceptable_win_rate = 0.45
            good_sharpe = 1.0
            acceptable_sharpe = 0.5
            max_acceptable_drawdown = 0.15
            
            # Count positive indicators
            positive_indicators = 0
            negative_indicators = 0
            
            if win_rate >= good_win_rate:
                positive_indicators += 2
            elif win_rate >= acceptable_win_rate:
                positive_indicators += 1
            else:
                negative_indicators += 2
            
            if sharpe_ratio >= good_sharpe:
                positive_indicators += 2
            elif sharpe_ratio >= acceptable_sharpe:
                positive_indicators += 1
            else:
                negative_indicators += 1
            
            if max_drawdown <= max_acceptable_drawdown:
                positive_indicators += 1
            else:
                negative_indicators += 2
            
            if total_return > 0:
                positive_indicators += 1
            else:
                negative_indicators += 1
            
            if consistency_score >= 0.7:
                positive_indicators += 1
            elif consistency_score < 0.4:
                negative_indicators += 1
            
            # Generate recommendation
            if positive_indicators >= 5 and negative_indicators <= 1:
                return "CONTINUE"
            elif positive_indicators >= 3 and negative_indicators <= 2:
                return "OPTIMIZE"
            elif negative_indicators >= 4:
                return "RETIRE"
            else:
                return "PAUSE"
                
        except Exception as e:
            logger.error(f"Error generating recommendation: {e}")
            return "OPTIMIZE"  # Default to optimization
    
    async def _act_on_analysis_recommendation(self, strategy_id: str, analysis: StrategyAnalysis):
        """Take action based on analysis recommendation"""
        try:
            recommendation = analysis.recommendation
            
            if recommendation == "RETIRE":
                await self._add_retirement_candidate(strategy_id)
                
                # Auto-pause if performance is very poor
                if analysis.max_drawdown > 0.2 or analysis.win_rate < 0.3:
                    await strategy_controller.execute_control_action(
                        strategy_id, 'PAUSE',
                        f"Auto-pause: Poor performance (win rate: {analysis.win_rate*100:.1f}%, drawdown: {analysis.max_drawdown*100:.1f}%)",
                        'SYSTEM'
                    )
                    
            elif recommendation == "PAUSE":
                await strategy_controller.execute_control_action(
                    strategy_id, 'PAUSE',
                    f"Auto-pause: Performance analysis recommendation",
                    'SYSTEM'
                )
                
            elif recommendation == "OPTIMIZE":
                # Generate optimization suggestions
                await self.generate_optimization_suggestions(strategy_id)
            
            # CONTINUE requires no immediate action
            
        except Exception as e:
            logger.error(f"Error acting on analysis recommendation for {strategy_id}: {e}")
    
    async def generate_optimization_suggestions(self, strategy_id: str) -> List[OptimizationSuggestion]:
        """
        Generate optimization suggestions for a strategy
        
        Args:
            strategy_id: Strategy ID
            
        Returns:
            List of optimization suggestions
        """
        try:
            logger.info(f"Generating optimization suggestions for strategy {strategy_id}")
            
            suggestions = []
            
            # Get strategy data
            status = await strategy_manager.get_strategy_status(strategy_id)
            performance = await strategy_manager.get_strategy_performance(strategy_id)
            
            if not status or not performance:
                return suggestions
            
            # Analyze performance metrics for optimization opportunities
            
            # Win rate optimization
            if performance['win_rate'] < 0.5 and performance['total_trades'] > 20:
                suggestion = OptimizationSuggestion(
                    suggestion_id=f"{strategy_id}_winrate_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    strategy_id=strategy_id,
                    category="PARAMETERS",
                    priority="HIGH",
                    description="Consider tightening entry criteria to improve win rate",
                    current_value=performance['win_rate'],
                    suggested_value="Increase signal confidence threshold",
                    expected_improvement="5-10% win rate improvement",
                    confidence=0.7,
                    created_at=datetime.now()
                )
                suggestions.append(suggestion)
            
            # Drawdown optimization
            if performance['max_drawdown'] > 0.12:
                suggestion = OptimizationSuggestion(
                    suggestion_id=f"{strategy_id}_drawdown_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    strategy_id=strategy_id,
                    category="RISK",
                    priority="HIGH",
                    description="Reduce position sizes to limit drawdown",
                    current_value=performance['max_drawdown'],
                    suggested_value="Reduce max position size by 20-30%",
                    expected_improvement="Reduce drawdown to <10%",
                    confidence=0.8,
                    created_at=datetime.now()
                )
                suggestions.append(suggestion)
            
            # Trading frequency optimization
            if status['total_signals'] > 0:
                daily_signals = status['total_signals'] / 30  # Assume 30-day period
                if daily_signals > status['max_daily_trades'] * 0.8:
                    suggestion = OptimizationSuggestion(
                        suggestion_id=f"{strategy_id}_frequency_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        strategy_id=strategy_id,
                        category="TIMING",
                        priority="MEDIUM",
                        description="High signal frequency may indicate overtrading",
                        current_value=daily_signals,
                        suggested_value="Add signal filtering or cooldown periods",
                        expected_improvement="Better signal quality and reduced costs",
                        confidence=0.6,
                        created_at=datetime.now()
                    )
                    suggestions.append(suggestion)
            
            # Symbol diversification
            config = strategy_manager.strategy_configs.get(strategy_id)
            if config and len(config.symbols) < 3:
                suggestion = OptimizationSuggestion(
                    suggestion_id=f"{strategy_id}_symbols_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    strategy_id=strategy_id,
                    category="SYMBOLS",
                    priority="LOW",
                    description="Consider adding more symbols for diversification",
                    current_value=len(config.symbols),
                    suggested_value="Add 2-3 more symbols from different sectors",
                    expected_improvement="Reduced correlation risk",
                    confidence=0.5,
                    created_at=datetime.now()
                )
                suggestions.append(suggestion)
            
            # Store suggestions
            if suggestions:
                if strategy_id not in self.optimization_suggestions:
                    self.optimization_suggestions[strategy_id] = []
                self.optimization_suggestions[strategy_id].extend(suggestions)
                
                # Record lifecycle event
                await self._record_lifecycle_event(
                    strategy_id, LifecycleStage.ACTIVE, LifecycleStage.ACTIVE,
                    "SYSTEM", f"Generated {len(suggestions)} optimization suggestions",
                    {'suggestion_count': len(suggestions)}
                )
                
                trading_monitor.increment_counter("optimization_suggestions_generated", len(suggestions))
                logger.info(f"Generated {len(suggestions)} optimization suggestions for strategy {strategy_id}")
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating optimization suggestions for {strategy_id}: {e}")
            return []
    
    async def retire_strategy(self, strategy_id: str, reason: str = "Performance-based retirement") -> bool:
        """
        Retire a strategy with proper cleanup
        
        Args:
            strategy_id: Strategy ID to retire
            reason: Reason for retirement
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Retiring strategy {strategy_id}: {reason}")
            
            # Stop the strategy and close positions
            stop_result = await strategy_controller.execute_control_action(
                strategy_id, 'STOP', reason, 'SYSTEM', {'close_positions': True}
            )
            
            if not stop_result['success']:
                logger.error(f"Failed to stop strategy {strategy_id} for retirement")
                return False
            
            # Record retirement event
            await self._record_lifecycle_event(
                strategy_id, LifecycleStage.RETIRED, LifecycleStage.STOPPED,
                "SYSTEM", reason, {'retirement_date': datetime.now().isoformat()}
            )
            
            # Remove from retirement candidates
            self.retirement_candidates.discard(strategy_id)
            
            # Generate final analysis report
            final_analysis = await self.analyze_strategy_performance(strategy_id)
            
            # Publish retirement event
            strategy_status = await strategy_manager.get_strategy_status(strategy_id)
            if strategy_status:
                await publish_order_event(strategy_status.get('user_id'), EventType.STRATEGY_RETIRED, {
                    'strategy_id': strategy_id,
                    'reason': reason,
                    'retired_at': datetime.now().isoformat(),
                    'final_analysis': asdict(final_analysis) if final_analysis else None
                })
            
            trading_monitor.increment_counter("strategies_retired")
            logger.info(f"Strategy {strategy_id} retired successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Error retiring strategy {strategy_id}: {e}")
            return False
    
    async def _add_retirement_candidate(self, strategy_id: str):
        """Add strategy to retirement candidates"""
        try:
            self.retirement_candidates.add(strategy_id)
            
            await self._record_lifecycle_event(
                strategy_id, LifecycleStage.ACTIVE, LifecycleStage.ACTIVE,
                "SYSTEM", "Added to retirement candidates", {}
            )
            
            logger.warning(f"Strategy {strategy_id} added to retirement candidates")
            
        except Exception as e:
            logger.error(f"Error adding retirement candidate {strategy_id}: {e}")
    
    async def _needs_analysis(self, strategy_id: str) -> bool:
        """Check if strategy needs performance analysis"""
        try:
            if strategy_id not in self.strategy_analyses:
                return True
            
            analyses = self.strategy_analyses[strategy_id]
            if not analyses:
                return True
            
            # Check if enough time has passed since last analysis
            last_analysis = max(analyses, key=lambda x: x.analysis_date)
            days_since_analysis = (datetime.now() - last_analysis.analysis_date).days
            
            return days_since_analysis >= self.lifecycle_settings['auto_analysis_interval_days']
            
        except Exception as e:
            logger.error(f"Error checking analysis need for {strategy_id}: {e}")
            return False
    
    async def _should_consider_retirement(self, strategy_id: str) -> bool:
        """Check if strategy should be considered for retirement"""
        try:
            if strategy_id in self.retirement_candidates:
                return False  # Already a candidate
            
            # Get strategy age
            if strategy_id not in self.lifecycle_events:
                return False
            
            creation_event = next(
                (e for e in self.lifecycle_events[strategy_id] if e.stage == LifecycleStage.CREATED),
                None
            )
            
            if not creation_event:
                return False
            
            strategy_age = (datetime.now() - creation_event.timestamp).days
            min_age = self.lifecycle_settings['retirement_criteria']['min_age_days']
            
            if strategy_age < min_age:
                return False
            
            # Check performance criteria
            if strategy_id not in self.strategy_analyses:
                return False
            
            analyses = self.strategy_analyses[strategy_id]
            if not analyses:
                return False
            
            latest_analysis = max(analyses, key=lambda x: x.analysis_date)
            criteria = self.lifecycle_settings['retirement_criteria']
            
            # Check retirement criteria
            if (latest_analysis.max_drawdown > criteria['max_drawdown_threshold'] or
                latest_analysis.win_rate < criteria['min_win_rate_threshold'] or
                latest_analysis.sharpe_ratio < criteria['min_sharpe_ratio']):
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking retirement consideration for {strategy_id}: {e}")
            return False
    
    async def _needs_optimization_review(self, strategy_id: str) -> bool:
        """Check if strategy needs optimization review"""
        try:
            if strategy_id not in self.optimization_suggestions:
                return True
            
            suggestions = self.optimization_suggestions[strategy_id]
            if not suggestions:
                return True
            
            # Check if enough time has passed since last optimization review
            last_suggestion = max(suggestions, key=lambda x: x.created_at)
            days_since_suggestion = (datetime.now() - last_suggestion.created_at).days
            
            return days_since_suggestion >= 14  # Review every 2 weeks
            
        except Exception as e:
            logger.error(f"Error checking optimization need for {strategy_id}: {e}")
            return False
    
    async def _cleanup_old_data(self):
        """Clean up old lifecycle data"""
        try:
            cutoff_date = datetime.now() - timedelta(days=90)  # Keep 90 days of data
            
            # Clean up old events
            for strategy_id in list(self.lifecycle_events.keys()):
                events = self.lifecycle_events[strategy_id]
                recent_events = [e for e in events if e.timestamp > cutoff_date]
                
                if len(recent_events) != len(events):
                    self.lifecycle_events[strategy_id] = recent_events
                    logger.debug(f"Cleaned up {len(events) - len(recent_events)} old events for {strategy_id}")
            
            # Clean up old analyses (keep last 10)
            for strategy_id in list(self.strategy_analyses.keys()):
                analyses = self.strategy_analyses[strategy_id]
                if len(analyses) > 10:
                    sorted_analyses = sorted(analyses, key=lambda x: x.analysis_date, reverse=True)
                    self.strategy_analyses[strategy_id] = sorted_analyses[:10]
            
            # Clean up old suggestions (keep last 20)
            for strategy_id in list(self.optimization_suggestions.keys()):
                suggestions = self.optimization_suggestions[strategy_id]
                if len(suggestions) > 20:
                    sorted_suggestions = sorted(suggestions, key=lambda x: x.created_at, reverse=True)
                    self.optimization_suggestions[strategy_id] = sorted_suggestions[:20]
            
        except Exception as e:
            logger.error(f"Error cleaning up old lifecycle data: {e}")
    
    # Public API methods
    
    async def get_strategy_lifecycle_history(self, strategy_id: str) -> List[Dict[str, Any]]:
        """Get lifecycle history for a strategy"""
        try:
            if strategy_id not in self.lifecycle_events:
                return []
            
            events = self.lifecycle_events[strategy_id]
            
            return [
                {
                    'event_id': event.event_id,
                    'stage': event.stage.value,
                    'previous_stage': event.previous_stage.value if event.previous_stage else None,
                    'timestamp': event.timestamp.isoformat(),
                    'triggered_by': event.triggered_by,
                    'reason': event.reason,
                    'metadata': event.metadata
                }
                for event in sorted(events, key=lambda x: x.timestamp, reverse=True)
            ]
            
        except Exception as e:
            logger.error(f"Error getting lifecycle history for {strategy_id}: {e}")
            return []
    
    async def get_strategy_analyses(self, strategy_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get performance analyses for a strategy"""
        try:
            if strategy_id not in self.strategy_analyses:
                return []
            
            analyses = self.strategy_analyses[strategy_id]
            sorted_analyses = sorted(analyses, key=lambda x: x.analysis_date, reverse=True)
            limited_analyses = sorted_analyses[:limit]
            
            return [asdict(analysis) for analysis in limited_analyses]
            
        except Exception as e:
            logger.error(f"Error getting analyses for {strategy_id}: {e}")
            return []
    
    async def get_optimization_suggestions(self, strategy_id: str, 
                                        include_implemented: bool = False) -> List[Dict[str, Any]]:
        """Get optimization suggestions for a strategy"""
        try:
            if strategy_id not in self.optimization_suggestions:
                return []
            
            suggestions = self.optimization_suggestions[strategy_id]
            
            # Filter by implementation status if needed
            # For now, we don't track implementation status
            
            return [asdict(suggestion) for suggestion in suggestions]
            
        except Exception as e:
            logger.error(f"Error getting optimization suggestions for {strategy_id}: {e}")
            return []
    
    def get_retirement_candidates(self) -> List[str]:
        """Get list of strategies being considered for retirement"""
        return list(self.retirement_candidates)
    
    def get_lifecycle_status(self) -> Dict[str, Any]:
        """Get lifecycle manager status"""
        try:
            total_strategies = len(self.lifecycle_events)
            total_analyses = sum(len(analyses) for analyses in self.strategy_analyses.values())
            total_suggestions = sum(len(suggestions) for suggestions in self.optimization_suggestions.values())
            
            return {
                'total_strategies_tracked': total_strategies,
                'total_analyses_performed': total_analyses,
                'total_optimization_suggestions': total_suggestions,
                'retirement_candidates': len(self.retirement_candidates),
                'lifecycle_settings': self.lifecycle_settings
            }
            
        except Exception as e:
            logger.error(f"Error getting lifecycle status: {e}")
            return {}

# Global strategy lifecycle manager instance
strategy_lifecycle_manager = StrategyLifecycleManager()