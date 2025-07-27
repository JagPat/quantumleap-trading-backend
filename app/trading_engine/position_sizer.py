"""
Position Sizing and Risk Calculations
Advanced position sizing algorithms based on risk tolerance and market conditions
"""
import logging
import math
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from .models import TradingSignal, SignalType, RiskParameters, Position
from .risk_engine import risk_engine
from .position_manager import position_manager
from .monitoring import trading_monitor, time_async_operation

logger = logging.getLogger(__name__)

@dataclass
class PositionSizeResult:
    """Result of position sizing calculation"""
    recommended_quantity: int
    recommended_value: float
    risk_amount: float
    risk_percentage: float
    confidence_adjustment: float
    volatility_adjustment: float
    correlation_adjustment: float
    final_adjustment_factor: float
    reasoning: List[str]
    warnings: List[str]

@dataclass
class VolatilityMetrics:
    """Volatility metrics for a symbol"""
    symbol: str
    daily_volatility: float
    weekly_volatility: float
    monthly_volatility: float
    beta: float  # Market beta
    sharpe_ratio: float
    max_drawdown: float
    calculated_at: datetime

@dataclass
class CorrelationMatrix:
    """Correlation matrix for portfolio optimization"""
    symbols: List[str]
    correlations: Dict[Tuple[str, str], float]
    calculated_at: datetime

class PositionSizer:
    """
    Advanced position sizing engine with risk-based calculations
    """
    
    def __init__(self):
        self.volatility_cache = {}  # symbol -> VolatilityMetrics
        self.correlation_cache = {}  # Cache for correlation calculations
        self.market_regime = 'NORMAL'  # BULL, BEAR, NORMAL, VOLATILE
        
        # Position sizing models
        self.sizing_models = {
            'FIXED_FRACTIONAL': self._fixed_fractional_sizing,
            'KELLY_CRITERION': self._kelly_criterion_sizing,
            'VOLATILITY_ADJUSTED': self._volatility_adjusted_sizing,
            'RISK_PARITY': self._risk_parity_sizing,
            'CONFIDENCE_WEIGHTED': self._confidence_weighted_sizing
        }
        
        logger.info("PositionSizer initialized")
    
    @time_async_operation("calculate_position_size")
    async def calculate_position_size(self, signal: TradingSignal, 
                                    portfolio_value: float,
                                    model: str = 'VOLATILITY_ADJUSTED') -> PositionSizeResult:
        """
        Calculate optimal position size based on signal and risk parameters
        
        Args:
            signal: Trading signal to size
            portfolio_value: Current portfolio value
            model: Sizing model to use
            
        Returns:
            PositionSizeResult with sizing recommendation
        """
        try:
            logger.debug(f"Calculating position size for signal {signal.id} using {model} model")
            
            # Get user risk parameters
            risk_params = risk_engine.get_user_risk_params(signal.user_id)
            
            # Get volatility metrics
            volatility = await self._get_volatility_metrics(signal.symbol)
            
            # Get current portfolio positions for correlation analysis
            positions = await position_manager.get_user_positions(signal.user_id)
            
            # Calculate base position size using selected model
            sizing_func = self.sizing_models.get(model, self._volatility_adjusted_sizing)
            base_result = await sizing_func(signal, portfolio_value, risk_params, volatility)
            
            # Apply adjustments
            adjusted_result = await self._apply_adjustments(
                base_result, signal, positions, volatility, risk_params
            )
            
            # Validate final position size
            final_result = await self._validate_position_size(
                adjusted_result, signal, portfolio_value, risk_params
            )
            
            trading_monitor.increment_counter("position_sizes_calculated")
            logger.info(f"Position size calculated for {signal.symbol}: {final_result.recommended_quantity} shares")
            
            return final_result
            
        except Exception as e:
            error_msg = f"Error calculating position size for signal {signal.id}: {str(e)}"
            logger.error(error_msg)
            trading_monitor.increment_counter("position_sizing_errors")
            
            # Return conservative fallback
            return PositionSizeResult(
                recommended_quantity=1,
                recommended_value=100.0,
                risk_amount=100.0,
                risk_percentage=0.1,
                confidence_adjustment=0.5,
                volatility_adjustment=0.5,
                correlation_adjustment=1.0,
                final_adjustment_factor=0.25,
                reasoning=[f"Error in position sizing: {str(e)}", "Using conservative fallback"],
                warnings=["Position sizing error - using minimal position"]
            )
    
    async def _fixed_fractional_sizing(self, signal: TradingSignal, portfolio_value: float,
                                     risk_params: RiskParameters, 
                                     volatility: VolatilityMetrics) -> PositionSizeResult:
        """Fixed fractional position sizing"""
        try:
            # Use fixed percentage of portfolio
            base_percentage = risk_params.max_position_size_percent / 100
            position_value = portfolio_value * base_percentage
            
            # Estimate price
            estimated_price = signal.target_price or 100.0
            quantity = int(position_value / estimated_price)
            
            return PositionSizeResult(
                recommended_quantity=max(1, quantity),
                recommended_value=position_value,
                risk_amount=position_value * 0.05,  # Assume 5% risk
                risk_percentage=base_percentage * 100,
                confidence_adjustment=1.0,
                volatility_adjustment=1.0,
                correlation_adjustment=1.0,
                final_adjustment_factor=1.0,
                reasoning=[f"Fixed fractional sizing: {base_percentage*100:.1f}% of portfolio"],
                warnings=[]
            )
            
        except Exception as e:
            logger.error(f"Error in fixed fractional sizing: {e}")
            raise
    
    async def _kelly_criterion_sizing(self, signal: TradingSignal, portfolio_value: float,
                                    risk_params: RiskParameters,
                                    volatility: VolatilityMetrics) -> PositionSizeResult:
        """Kelly Criterion position sizing"""
        try:
            # Kelly formula: f = (bp - q) / b
            # where f = fraction to bet, b = odds, p = probability of win, q = probability of loss
            
            # Estimate win probability from confidence score
            win_probability = signal.confidence_score
            loss_probability = 1 - win_probability
            
            # Estimate odds from target price and stop loss
            if signal.target_price and signal.stop_loss:
                estimated_price = signal.target_price
                upside = abs(signal.target_price - estimated_price) / estimated_price
                downside = abs(estimated_price - signal.stop_loss) / estimated_price
                odds = upside / downside if downside > 0 else 2.0
            else:
                odds = 2.0  # Default 2:1 risk-reward
                upside = 0.1  # 10% upside assumption
                downside = 0.05  # 5% downside assumption
            
            # Kelly fraction
            kelly_fraction = (odds * win_probability - loss_probability) / odds
            
            # Cap Kelly fraction to prevent over-leveraging
            max_kelly = risk_params.max_position_size_percent / 100
            kelly_fraction = max(0, min(kelly_fraction, max_kelly))
            
            # Apply fractional Kelly (typically 25-50% of full Kelly)
            fractional_kelly = kelly_fraction * 0.25  # Use 25% of Kelly
            
            position_value = portfolio_value * fractional_kelly
            estimated_price = signal.target_price or 100.0
            quantity = int(position_value / estimated_price)
            
            return PositionSizeResult(
                recommended_quantity=max(1, quantity),
                recommended_value=position_value,
                risk_amount=position_value * downside,
                risk_percentage=fractional_kelly * 100,
                confidence_adjustment=signal.confidence_score,
                volatility_adjustment=1.0,
                correlation_adjustment=1.0,
                final_adjustment_factor=fractional_kelly / max_kelly if max_kelly > 0 else 0.25,
                reasoning=[
                    f"Kelly Criterion sizing: {kelly_fraction*100:.1f}% (full Kelly)",
                    f"Fractional Kelly (25%): {fractional_kelly*100:.1f}%",
                    f"Win probability: {win_probability:.2f}",
                    f"Risk-reward ratio: 1:{odds:.1f}"
                ],
                warnings=[] if kelly_fraction > 0 else ["Negative Kelly fraction - signal may not be favorable"]
            )
            
        except Exception as e:
            logger.error(f"Error in Kelly criterion sizing: {e}")
            raise
    
    async def _volatility_adjusted_sizing(self, signal: TradingSignal, portfolio_value: float,
                                        risk_params: RiskParameters,
                                        volatility: VolatilityMetrics) -> PositionSizeResult:
        """Volatility-adjusted position sizing"""
        try:
            # Base position size
            base_percentage = risk_params.max_position_size_percent / 100
            
            # Adjust for volatility (inverse relationship)
            # Higher volatility = smaller position
            target_volatility = 0.02  # 2% daily volatility target
            volatility_adjustment = min(target_volatility / volatility.daily_volatility, 2.0)
            
            # Adjust for confidence
            confidence_adjustment = signal.confidence_score
            
            # Combined adjustment
            adjusted_percentage = base_percentage * volatility_adjustment * confidence_adjustment
            
            # Cap at maximum position size
            adjusted_percentage = min(adjusted_percentage, base_percentage)
            
            position_value = portfolio_value * adjusted_percentage
            estimated_price = signal.target_price or 100.0
            quantity = int(position_value / estimated_price)
            
            # Calculate risk amount based on volatility
            risk_amount = position_value * volatility.daily_volatility * 2  # 2-sigma risk
            
            return PositionSizeResult(
                recommended_quantity=max(1, quantity),
                recommended_value=position_value,
                risk_amount=risk_amount,
                risk_percentage=adjusted_percentage * 100,
                confidence_adjustment=confidence_adjustment,
                volatility_adjustment=volatility_adjustment,
                correlation_adjustment=1.0,
                final_adjustment_factor=adjusted_percentage / base_percentage,
                reasoning=[
                    f"Base position size: {base_percentage*100:.1f}%",
                    f"Volatility adjustment: {volatility_adjustment:.2f}x (daily vol: {volatility.daily_volatility*100:.1f}%)",
                    f"Confidence adjustment: {confidence_adjustment:.2f}x",
                    f"Final position size: {adjusted_percentage*100:.1f}%"
                ],
                warnings=[] if volatility_adjustment > 0.5 else ["High volatility detected - position size reduced significantly"]
            )
            
        except Exception as e:
            logger.error(f"Error in volatility adjusted sizing: {e}")
            raise
    
    async def _risk_parity_sizing(self, signal: TradingSignal, portfolio_value: float,
                                risk_params: RiskParameters,
                                volatility: VolatilityMetrics) -> PositionSizeResult:
        """Risk parity position sizing"""
        try:
            # Target risk contribution per position
            target_risk_contribution = 0.02  # 2% portfolio risk per position
            
            # Calculate position size to achieve target risk contribution
            # Risk contribution = position_weight * volatility * correlation
            # For simplicity, assume correlation = 1 for individual position sizing
            
            position_weight = target_risk_contribution / volatility.daily_volatility
            position_value = portfolio_value * position_weight
            
            # Apply confidence adjustment
            confidence_adjustment = signal.confidence_score
            position_value *= confidence_adjustment
            
            # Cap at maximum position size
            max_position_value = portfolio_value * (risk_params.max_position_size_percent / 100)
            position_value = min(position_value, max_position_value)
            
            estimated_price = signal.target_price or 100.0
            quantity = int(position_value / estimated_price)
            
            actual_risk_contribution = (position_value / portfolio_value) * volatility.daily_volatility
            
            return PositionSizeResult(
                recommended_quantity=max(1, quantity),
                recommended_value=position_value,
                risk_amount=actual_risk_contribution * portfolio_value,
                risk_percentage=(position_value / portfolio_value) * 100,
                confidence_adjustment=confidence_adjustment,
                volatility_adjustment=1.0,
                correlation_adjustment=1.0,
                final_adjustment_factor=position_weight,
                reasoning=[
                    f"Risk parity sizing for {target_risk_contribution*100:.1f}% risk contribution",
                    f"Position weight: {position_weight*100:.1f}%",
                    f"Actual risk contribution: {actual_risk_contribution*100:.2f}%",
                    f"Confidence adjustment: {confidence_adjustment:.2f}x"
                ],
                warnings=[]
            )
            
        except Exception as e:
            logger.error(f"Error in risk parity sizing: {e}")
            raise
    
    async def _confidence_weighted_sizing(self, signal: TradingSignal, portfolio_value: float,
                                        risk_params: RiskParameters,
                                        volatility: VolatilityMetrics) -> PositionSizeResult:
        """Confidence-weighted position sizing"""
        try:
            # Base position size
            base_percentage = risk_params.max_position_size_percent / 100
            
            # Confidence-based scaling
            # High confidence = larger position, low confidence = smaller position
            confidence_factor = signal.confidence_score ** 2  # Square for more aggressive scaling
            
            # Signal strength adjustment
            signal_strength = 1.0
            if signal.signal_type in [SignalType.STRONG_BUY, SignalType.STRONG_SELL]:
                signal_strength = 1.5
            elif signal.signal_type in [SignalType.BUY, SignalType.SELL]:
                signal_strength = 1.0
            else:
                signal_strength = 0.5
            
            # Volatility adjustment (inverse)
            volatility_factor = min(0.02 / volatility.daily_volatility, 2.0)
            
            # Combined adjustment
            total_adjustment = confidence_factor * signal_strength * volatility_factor
            adjusted_percentage = base_percentage * total_adjustment
            
            # Cap at maximum
            adjusted_percentage = min(adjusted_percentage, base_percentage)
            
            position_value = portfolio_value * adjusted_percentage
            estimated_price = signal.target_price or 100.0
            quantity = int(position_value / estimated_price)
            
            return PositionSizeResult(
                recommended_quantity=max(1, quantity),
                recommended_value=position_value,
                risk_amount=position_value * volatility.daily_volatility,
                risk_percentage=adjusted_percentage * 100,
                confidence_adjustment=confidence_factor,
                volatility_adjustment=volatility_factor,
                correlation_adjustment=1.0,
                final_adjustment_factor=total_adjustment,
                reasoning=[
                    f"Base position size: {base_percentage*100:.1f}%",
                    f"Confidence factor: {confidence_factor:.2f}x (confidence: {signal.confidence_score:.2f})",
                    f"Signal strength: {signal_strength:.1f}x ({signal.signal_type})",
                    f"Volatility factor: {volatility_factor:.2f}x",
                    f"Total adjustment: {total_adjustment:.2f}x",
                    f"Final position size: {adjusted_percentage*100:.1f}%"
                ],
                warnings=[]
            )
            
        except Exception as e:
            logger.error(f"Error in confidence weighted sizing: {e}")
            raise
    
    async def _apply_adjustments(self, base_result: PositionSizeResult, signal: TradingSignal,
                               positions: List[Dict[str, Any]], volatility: VolatilityMetrics,
                               risk_params: RiskParameters) -> PositionSizeResult:
        """Apply additional adjustments to base position size"""
        try:
            # Correlation adjustment
            correlation_adjustment = await self._calculate_correlation_adjustment(
                signal.symbol, positions
            )
            
            # Market regime adjustment
            regime_adjustment = self._get_market_regime_adjustment()
            
            # Time-based adjustment (avoid overtrading)
            time_adjustment = await self._calculate_time_adjustment(signal.user_id)
            
            # Apply all adjustments
            total_adjustment = (
                base_result.final_adjustment_factor * 
                correlation_adjustment * 
                regime_adjustment * 
                time_adjustment
            )
            
            # Recalculate position size
            adjusted_quantity = int(base_result.recommended_quantity * total_adjustment)
            adjusted_value = base_result.recommended_value * total_adjustment
            
            # Update result
            base_result.recommended_quantity = max(1, adjusted_quantity)
            base_result.recommended_value = adjusted_value
            base_result.correlation_adjustment = correlation_adjustment
            base_result.final_adjustment_factor = total_adjustment
            
            # Add adjustment reasoning
            base_result.reasoning.extend([
                f"Correlation adjustment: {correlation_adjustment:.2f}x",
                f"Market regime adjustment: {regime_adjustment:.2f}x",
                f"Time-based adjustment: {time_adjustment:.2f}x",
                f"Final total adjustment: {total_adjustment:.2f}x"
            ])
            
            return base_result
            
        except Exception as e:
            logger.error(f"Error applying adjustments: {e}")
            return base_result  # Return base result if adjustments fail
    
    async def _calculate_correlation_adjustment(self, symbol: str, 
                                              positions: List[Dict[str, Any]]) -> float:
        """Calculate correlation-based position size adjustment"""
        try:
            if not positions:
                return 1.0  # No correlation adjustment if no positions
            
            # Simplified correlation calculation
            # In production, this would use actual correlation data
            
            # Check for same-sector concentration
            from .risk_engine import risk_engine
            symbol_sector = risk_engine.sector_mappings.get(symbol, 'Unknown')
            
            if symbol_sector == 'Unknown':
                return 1.0
            
            # Calculate sector exposure
            sector_exposure = 0.0
            total_exposure = sum(abs(pos['market_value']) for pos in positions)
            
            for pos in positions:
                pos_sector = risk_engine.sector_mappings.get(pos['symbol'], 'Unknown')
                if pos_sector == symbol_sector:
                    sector_exposure += abs(pos['market_value'])
            
            if total_exposure == 0:
                return 1.0
            
            sector_percentage = (sector_exposure / total_exposure) * 100
            
            # Reduce position size if high sector concentration
            if sector_percentage > 30:
                return 0.5  # 50% reduction for high concentration
            elif sector_percentage > 20:
                return 0.75  # 25% reduction for medium concentration
            else:
                return 1.0  # No adjustment for low concentration
            
        except Exception as e:
            logger.error(f"Error calculating correlation adjustment: {e}")
            return 1.0
    
    def _get_market_regime_adjustment(self) -> float:
        """Get position size adjustment based on market regime"""
        try:
            regime_adjustments = {
                'BULL': 1.2,      # Increase position sizes in bull market
                'NORMAL': 1.0,    # Normal position sizes
                'BEAR': 0.7,      # Reduce position sizes in bear market
                'VOLATILE': 0.6   # Significantly reduce in volatile markets
            }
            
            return regime_adjustments.get(self.market_regime, 1.0)
            
        except Exception as e:
            logger.error(f"Error getting market regime adjustment: {e}")
            return 1.0
    
    async def _calculate_time_adjustment(self, user_id: str) -> float:
        """Calculate time-based adjustment to prevent overtrading"""
        try:
            # Get recent orders to check trading frequency
            from .order_db import order_db
            
            recent_orders = order_db.get_orders_by_user(user_id, limit=50)
            
            # Count orders in last 24 hours
            cutoff_time = datetime.now() - timedelta(hours=24)
            recent_count = len([o for o in recent_orders if o.created_at >= cutoff_time])
            
            # Reduce position size if overtrading
            if recent_count > 20:
                return 0.5  # 50% reduction for excessive trading
            elif recent_count > 10:
                return 0.75  # 25% reduction for high trading
            else:
                return 1.0  # No adjustment for normal trading
            
        except Exception as e:
            logger.error(f"Error calculating time adjustment: {e}")
            return 1.0
    
    async def _validate_position_size(self, result: PositionSizeResult, signal: TradingSignal,
                                    portfolio_value: float, 
                                    risk_params: RiskParameters) -> PositionSizeResult:
        """Final validation and adjustment of position size"""
        try:
            warnings = result.warnings.copy()
            
            # Minimum position size
            if result.recommended_quantity < 1:
                result.recommended_quantity = 1
                result.recommended_value = signal.target_price or 100.0
                warnings.append("Position size increased to minimum of 1 share")
            
            # Maximum position value check
            max_position_value = portfolio_value * (risk_params.max_position_size_percent / 100)
            if result.recommended_value > max_position_value:
                adjustment_factor = max_position_value / result.recommended_value
                result.recommended_quantity = int(result.recommended_quantity * adjustment_factor)
                result.recommended_value = max_position_value
                warnings.append(f"Position size capped at maximum {risk_params.max_position_size_percent}% of portfolio")
            
            # Risk amount validation
            max_risk_amount = portfolio_value * (risk_params.stop_loss_percent / 100)
            if result.risk_amount > max_risk_amount:
                warnings.append(f"Estimated risk ({result.risk_amount:.0f}) exceeds maximum risk tolerance")
            
            # Update warnings
            result.warnings = warnings
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating position size: {e}")
            return result
    
    async def _get_volatility_metrics(self, symbol: str) -> VolatilityMetrics:
        """Get or calculate volatility metrics for a symbol"""
        try:
            # Check cache first
            if symbol in self.volatility_cache:
                cached = self.volatility_cache[symbol]
                if (datetime.now() - cached.calculated_at).total_seconds() < 3600:  # 1 hour cache
                    return cached
            
            # Calculate volatility metrics (simplified)
            # In production, this would use actual price data
            volatility = VolatilityMetrics(
                symbol=symbol,
                daily_volatility=0.025,  # 2.5% daily volatility (default)
                weekly_volatility=0.055,  # ~2.5% * sqrt(5)
                monthly_volatility=0.11,  # ~2.5% * sqrt(20)
                beta=1.0,  # Market beta
                sharpe_ratio=0.8,  # Sharpe ratio
                max_drawdown=0.15,  # 15% max drawdown
                calculated_at=datetime.now()
            )
            
            # Adjust volatility based on symbol characteristics
            # This is a simplified approach - production would use real data
            high_vol_symbols = ['RELIANCE', 'BHARTIARTL', 'ITC']
            low_vol_symbols = ['HDFCBANK', 'TCS', 'INFY']
            
            if symbol in high_vol_symbols:
                volatility.daily_volatility *= 1.5
                volatility.weekly_volatility *= 1.5
                volatility.monthly_volatility *= 1.5
            elif symbol in low_vol_symbols:
                volatility.daily_volatility *= 0.7
                volatility.weekly_volatility *= 0.7
                volatility.monthly_volatility *= 0.7
            
            # Cache the result
            self.volatility_cache[symbol] = volatility
            
            return volatility
            
        except Exception as e:
            logger.error(f"Error getting volatility metrics for {symbol}: {e}")
            # Return default volatility
            return VolatilityMetrics(
                symbol=symbol,
                daily_volatility=0.03,
                weekly_volatility=0.067,
                monthly_volatility=0.13,
                beta=1.0,
                sharpe_ratio=0.5,
                max_drawdown=0.2,
                calculated_at=datetime.now()
            )
    
    async def get_position_size_recommendation(self, signal: TradingSignal,
                                             model: str = 'VOLATILITY_ADJUSTED') -> Dict[str, Any]:
        """
        Get position size recommendation with detailed breakdown
        
        Args:
            signal: Trading signal
            model: Sizing model to use
            
        Returns:
            Dictionary with recommendation details
        """
        try:
            # Get portfolio value (simplified)
            positions = await position_manager.get_user_positions(signal.user_id)
            portfolio_value = sum(abs(pos['market_value']) for pos in positions) + 100000  # Add cash
            
            if portfolio_value <= 0:
                portfolio_value = 100000  # Default portfolio value
            
            # Calculate position size
            result = await self.calculate_position_size(signal, portfolio_value, model)
            
            return {
                'signal_id': signal.id,
                'symbol': signal.symbol,
                'model_used': model,
                'portfolio_value': portfolio_value,
                'recommendation': {
                    'quantity': result.recommended_quantity,
                    'value': result.recommended_value,
                    'percentage_of_portfolio': (result.recommended_value / portfolio_value) * 100
                },
                'risk_analysis': {
                    'risk_amount': result.risk_amount,
                    'risk_percentage': result.risk_percentage,
                    'risk_reward_ratio': result.recommended_value / result.risk_amount if result.risk_amount > 0 else 0
                },
                'adjustments': {
                    'confidence_adjustment': result.confidence_adjustment,
                    'volatility_adjustment': result.volatility_adjustment,
                    'correlation_adjustment': result.correlation_adjustment,
                    'final_adjustment_factor': result.final_adjustment_factor
                },
                'reasoning': result.reasoning,
                'warnings': result.warnings,
                'calculated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting position size recommendation: {e}")
            return {
                'error': str(e),
                'recommendation': {'quantity': 1, 'value': 100.0, 'percentage_of_portfolio': 0.1}
            }
    
    def update_market_regime(self, regime: str):
        """Update market regime for position sizing adjustments"""
        if regime in ['BULL', 'BEAR', 'NORMAL', 'VOLATILE']:
            self.market_regime = regime
            logger.info(f"Market regime updated to: {regime}")
        else:
            logger.warning(f"Invalid market regime: {regime}")
    
    def clear_cache(self):
        """Clear volatility and correlation caches"""
        self.volatility_cache.clear()
        self.correlation_cache.clear()
        logger.info("Position sizer caches cleared")

# Global position sizer instance
position_sizer = PositionSizer()