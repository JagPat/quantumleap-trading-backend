"""
AI Signal Generator Integration with Trading Engine
Connects AI analysis to automated trading execution
"""
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from app.trading_engine.event_bus import EventManager, SignalEvent
from app.trading_engine.models import Signal, SignalType, SignalPriority
from app.ai_engine.service import AIService
from app.ai_engine.provider_failover import failover_manager
from app.database.service import get_db_connection

logger = logging.getLogger(__name__)

class SignalConfidenceLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

@dataclass
class AISignalMetadata:
    """Metadata for AI-generated signals"""
    provider_used: str
    analysis_id: str
    confidence_score: float
    reasoning: str
    market_context: Dict[str, Any]
    risk_factors: List[str]
    expected_timeframe: str
    supporting_indicators: List[str]

class AISignalGenerator:
    """
    Integrates AI analysis with trading engine signal generation
    """
    
    def __init__(self, event_manager: EventManager):
        self.event_manager = event_manager
        self.ai_service = AIService()
        self.min_confidence_threshold = 0.6  # Minimum confidence for signal generation
        
    async def process_portfolio_analysis(self, user_id: str, portfolio_data: Dict[str, Any]) -> List[SignalEvent]:
        """
        Process portfolio analysis and generate trading signals
        """
        try:
            logger.info(f"Processing portfolio analysis for signal generation - User: {user_id}")
            
            # Get AI analysis
            analysis_result = await self._get_ai_analysis(user_id, portfolio_data)
            if not analysis_result:
                logger.warning(f"No AI analysis available for user {user_id}")
                return []
            
            # Extract signals from analysis
            signals = await self._extract_signals_from_analysis(user_id, analysis_result)
            
            # Validate and filter signals
            validated_signals = await self._validate_signals(user_id, signals)
            
            # Convert to signal events
            signal_events = []
            for signal in validated_signals:
                event = await self._create_signal_event(user_id, signal)
                if event:
                    signal_events.append(event)
            
            logger.info(f"Generated {len(signal_events)} trading signals for user {user_id}")
            return signal_events
            
        except Exception as e:
            logger.error(f"Error processing portfolio analysis for signals: {e}")
            return []
    
    async def _get_ai_analysis(self, user_id: str, portfolio_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get AI analysis for portfolio with failover support"""
        try:
            # Use failover manager for robust AI analysis
            async def portfolio_analysis_operation(provider: str, user_id: str, portfolio_data: Dict[str, Any]):
                """Portfolio analysis operation with specific provider"""
                return await self.ai_service.analyze_portfolio(user_id, portfolio_data)
            
            analysis = await failover_manager.execute_with_failover(
                user_id, 
                "signal_generation", 
                portfolio_analysis_operation,
                portfolio_data
            )
            return analysis
        except Exception as e:
            logger.error(f"Error getting AI analysis: {e}")
            return None
    
    async def _extract_signals_from_analysis(self, user_id: str, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract trading signals from AI analysis"""
        signals = []
        
        try:
            # Extract from recommendations
            recommendations = analysis.get('recommendations', {})
            
            # Process stock-specific recommendations
            stock_recommendations = recommendations.get('stock_specific', [])
            for rec in stock_recommendations:
                signal = await self._convert_recommendation_to_signal(user_id, rec, analysis)
                if signal:
                    signals.append(signal)
            
            # Process portfolio optimization recommendations
            portfolio_recs = recommendations.get('portfolio_optimization', [])
            for rec in portfolio_recs:
                signal = await self._convert_portfolio_rec_to_signal(user_id, rec, analysis)
                if signal:
                    signals.append(signal)
            
            # Process risk management recommendations
            risk_recs = recommendations.get('risk_management', [])
            for rec in risk_recs:
                signal = await self._convert_risk_rec_to_signal(user_id, rec, analysis)
                if signal:
                    signals.append(signal)
                    
        except Exception as e:
            logger.error(f"Error extracting signals from analysis: {e}")
        
        return signals
    
    async def _convert_recommendation_to_signal(self, user_id: str, recommendation: Dict[str, Any], analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert stock recommendation to trading signal"""
        try:
            symbol = recommendation.get('symbol')
            action = recommendation.get('action', '').upper()
            confidence = recommendation.get('confidence', 0)
            reasoning = recommendation.get('reasoning', '')
            
            if not symbol or not action or confidence < self.min_confidence_threshold:
                return None
            
            # Map recommendation action to signal type
            signal_type_mapping = {
                'BUY': SignalType.BUY,
                'SELL': SignalType.SELL,
                'HOLD': SignalType.HOLD,
                'REDUCE': SignalType.SELL,
                'INCREASE': SignalType.BUY
            }
            
            signal_type = signal_type_mapping.get(action)
            if not signal_type:
                return None
            
            # Determine priority based on confidence and urgency
            priority = self._determine_signal_priority(confidence, recommendation.get('urgency', 'medium'))
            
            # Create signal metadata
            metadata = AISignalMetadata(
                provider_used=analysis.get('provider_used', 'unknown'),
                analysis_id=analysis.get('analysis_id', ''),
                confidence_score=confidence,
                reasoning=reasoning,
                market_context=analysis.get('market_context', {}),
                risk_factors=recommendation.get('risk_factors', []),
                expected_timeframe=recommendation.get('timeframe', 'medium_term'),
                supporting_indicators=recommendation.get('supporting_indicators', [])
            )
            
            signal = {
                'symbol': symbol,
                'signal_type': signal_type,
                'confidence_score': confidence,
                'priority': priority,
                'target_price': recommendation.get('target_price'),
                'stop_loss': recommendation.get('stop_loss'),
                'take_profit': recommendation.get('take_profit'),
                'position_size_pct': recommendation.get('position_size', 5.0),
                'reasoning': reasoning,
                'metadata': asdict(metadata),
                'expires_at': datetime.utcnow() + timedelta(hours=24)  # Default 24h expiry
            }
            
            return signal
            
        except Exception as e:
            logger.error(f"Error converting recommendation to signal: {e}")
            return None
    
    async def _convert_portfolio_rec_to_signal(self, user_id: str, recommendation: Dict[str, Any], analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert portfolio optimization recommendation to signal"""
        try:
            rec_type = recommendation.get('type', '').lower()
            
            # Handle rebalancing recommendations
            if rec_type == 'rebalance':
                return await self._create_rebalancing_signal(user_id, recommendation, analysis)
            
            # Handle sector allocation recommendations
            elif rec_type == 'sector_allocation':
                return await self._create_sector_signal(user_id, recommendation, analysis)
            
            # Handle diversification recommendations
            elif rec_type == 'diversification':
                return await self._create_diversification_signal(user_id, recommendation, analysis)
            
            return None
            
        except Exception as e:
            logger.error(f"Error converting portfolio recommendation to signal: {e}")
            return None
    
    async def _convert_risk_rec_to_signal(self, user_id: str, recommendation: Dict[str, Any], analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert risk management recommendation to signal"""
        try:
            risk_type = recommendation.get('type', '').lower()
            
            # Handle position size reduction
            if risk_type == 'reduce_position':
                symbol = recommendation.get('symbol')
                if symbol:
                    metadata = AISignalMetadata(
                        provider_used=analysis.get('provider_used', 'unknown'),
                        analysis_id=analysis.get('analysis_id', ''),
                        confidence_score=0.8,  # High confidence for risk management
                        reasoning=recommendation.get('reasoning', 'Risk management recommendation'),
                        market_context=analysis.get('market_context', {}),
                        risk_factors=recommendation.get('risk_factors', []),
                        expected_timeframe='immediate',
                        supporting_indicators=['risk_management']
                    )
                    
                    return {
                        'symbol': symbol,
                        'signal_type': SignalType.SELL,
                        'confidence_score': 0.8,
                        'priority': SignalPriority.HIGH,
                        'position_size_pct': recommendation.get('reduction_percentage', 50.0),
                        'reasoning': recommendation.get('reasoning', 'Risk management: Position size reduction'),
                        'metadata': asdict(metadata),
                        'expires_at': datetime.utcnow() + timedelta(hours=4)  # Urgent expiry
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error converting risk recommendation to signal: {e}")
            return None
    
    async def _validate_signals(self, user_id: str, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate signals before execution"""
        validated_signals = []
        
        for signal in signals:
            try:
                # Basic validation
                if not signal.get('symbol') or not signal.get('signal_type'):
                    continue
                
                # Confidence threshold check
                if signal.get('confidence_score', 0) < self.min_confidence_threshold:
                    continue
                
                # Check for duplicate signals
                if await self._is_duplicate_signal(user_id, signal):
                    continue
                
                # Validate against user preferences
                if await self._validate_against_user_preferences(user_id, signal):
                    validated_signals.append(signal)
                    
            except Exception as e:
                logger.error(f"Error validating signal: {e}")
                continue
        
        return validated_signals
    
    async def _is_duplicate_signal(self, user_id: str, signal: Dict[str, Any]) -> bool:
        """Check if signal is duplicate of recent signal"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check for similar signals in last 4 hours
            cursor.execute("""
                SELECT COUNT(*) FROM ai_trading_signals 
                WHERE user_id = ? AND symbol = ? AND signal_type = ? 
                AND created_at > datetime('now', '-4 hours')
                AND is_active = TRUE
            """, (user_id, signal['symbol'], signal['signal_type'].value))
            
            count = cursor.fetchone()[0]
            conn.close()
            
            return count > 0
            
        except Exception as e:
            logger.error(f"Error checking duplicate signal: {e}")
            return False
    
    async def _validate_against_user_preferences(self, user_id: str, signal: Dict[str, Any]) -> bool:
        """Validate signal against user preferences"""
        try:
            # Get user investment profile
            user_preferences = await self.ai_service.get_user_preferences(user_id)
            if not user_preferences:
                return True  # Allow if no preferences set
            
            # Check if auto trading is enabled
            if not user_preferences.get('auto_trading_enabled', False):
                return False
            
            # Check position size limits
            max_position = user_preferences.get('max_position_size', 15.0)
            if signal.get('position_size_pct', 0) > max_position:
                signal['position_size_pct'] = max_position
            
            # Check sector preferences
            # This would require additional market data integration
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating against user preferences: {e}")
            return True
    
    async def _create_signal_event(self, user_id: str, signal: Dict[str, Any]) -> Optional[SignalEvent]:
        """Create signal event for trading engine"""
        try:
            # Store signal in database first
            signal_id = await self._store_signal(user_id, signal)
            if not signal_id:
                return None
            
            # Create signal event
            event = SignalEvent(
                signal_id=signal_id,
                user_id=user_id,
                symbol=signal['symbol'],
                signal_type=signal['signal_type'],
                confidence_score=signal['confidence_score'],
                priority=signal['priority'],
                metadata=signal.get('metadata', {}),
                created_at=datetime.utcnow()
            )
            
            return event
            
        except Exception as e:
            logger.error(f"Error creating signal event: {e}")
            return None
    
    async def _store_signal(self, user_id: str, signal: Dict[str, Any]) -> Optional[str]:
        """Store signal in database"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            signal_id = f"ai_signal_{user_id}_{int(datetime.utcnow().timestamp())}"
            
            cursor.execute("""
                INSERT INTO ai_trading_signals (
                    id, user_id, symbol, signal_type, confidence_score,
                    reasoning, target_price, stop_loss, take_profit,
                    position_size, market_data, provider_used,
                    is_active, expires_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal_id, user_id, signal['symbol'], signal['signal_type'].value,
                signal['confidence_score'], signal['reasoning'],
                signal.get('target_price'), signal.get('stop_loss'),
                signal.get('take_profit'), signal.get('position_size_pct'),
                json.dumps(signal.get('metadata', {})),
                signal.get('metadata', {}).get('provider_used', 'unknown'),
                True, signal.get('expires_at'), datetime.utcnow()
            ))
            
            conn.commit()
            conn.close()
            
            return signal_id
            
        except Exception as e:
            logger.error(f"Error storing signal: {e}")
            return None
    
    def _determine_signal_priority(self, confidence: float, urgency: str) -> SignalPriority:
        """Determine signal priority based on confidence and urgency"""
        if confidence >= 0.9 or urgency == 'high':
            return SignalPriority.HIGH
        elif confidence >= 0.7 or urgency == 'medium':
            return SignalPriority.MEDIUM
        else:
            return SignalPriority.LOW
    
    async def _create_rebalancing_signal(self, user_id: str, recommendation: Dict[str, Any], analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create rebalancing signal from portfolio recommendation"""
        # Implementation for rebalancing signals
        # This would create multiple signals for portfolio rebalancing
        return None
    
    async def _create_sector_signal(self, user_id: str, recommendation: Dict[str, Any], analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create sector allocation signal"""
        # Implementation for sector allocation signals
        return None
    
    async def _create_diversification_signal(self, user_id: str, recommendation: Dict[str, Any], analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create diversification signal"""
        # Implementation for diversification signals
        return None

# Integration function to be called from the analysis router
async def generate_trading_signals_from_analysis(user_id: str, portfolio_data: Dict[str, Any], analysis_result: Dict[str, Any]) -> List[SignalEvent]:
    """
    Generate trading signals from AI analysis result
    This function integrates with the existing analysis pipeline
    """
    try:
        # Initialize event manager (this would be injected in production)
        from app.trading_engine.event_bus import get_event_manager
        event_manager = get_event_manager()
        
        # Create signal generator
        signal_generator = AISignalGenerator(event_manager)
        
        # Process analysis and generate signals
        signals = await signal_generator.process_portfolio_analysis(user_id, portfolio_data)
        
        # Publish signals to event bus
        for signal in signals:
            await event_manager.publish_event(signal)
        
        logger.info(f"Published {len(signals)} trading signals for user {user_id}")
        return signals
        
    except Exception as e:
        logger.error(f"Error generating trading signals from analysis: {e}")
        return []