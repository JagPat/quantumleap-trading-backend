"""
Risk Management Engine
Core component for validating orders and monitoring portfolio risk
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from .models import Order, OrderType, OrderSide, RiskParameters, Position
from .order_db import order_db
from .position_manager import position_manager
from .event_bus import event_bus, EventType, publish_order_event
from .monitoring import trading_monitor, time_async_operation

logger = logging.getLogger(__name__)

@dataclass
class RiskValidationResult:
    """Result of risk validation"""
    valid: bool
    risk_score: float  # 0.0 to 1.0, higher is riskier
    violations: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]

@dataclass
class PortfolioRisk:
    """Portfolio risk metrics"""
    total_exposure: float
    exposure_percentage: float
    max_drawdown: float
    current_drawdown: float
    var_95: float  # Value at Risk 95%
    sector_exposures: Dict[str, float]
    position_concentrations: Dict[str, float]
    leverage_ratio: float
    risk_score: float

class RiskEngine:
    """
    Core risk management engine for order validation and portfolio monitoring
    """
    
    def __init__(self):
        self.default_risk_params = RiskParameters()
        self.user_risk_params = {}  # Cache for user-specific risk parameters
        self.sector_mappings = self._load_sector_mappings()
        
        # Risk monitoring state
        self.portfolio_risks = {}  # Cache for portfolio risk calculations
        self.risk_alerts = {}  # Active risk alerts by user
        
        logger.info("RiskEngine initialized")
    
    def _load_sector_mappings(self) -> Dict[str, str]:
        """Load symbol to sector mappings"""
        # In production, this would load from a database or external service
        # For now, using a simple mapping
        return {
            'RELIANCE': 'Energy',
            'TCS': 'Technology',
            'INFY': 'Technology',
            'HDFCBANK': 'Banking',
            'ICICIBANK': 'Banking',
            'SBIN': 'Banking',
            'ITC': 'Consumer Goods',
            'HINDUNILVR': 'Consumer Goods',
            'BHARTIARTL': 'Telecom',
            'KOTAKBANK': 'Banking',
            'LT': 'Infrastructure',
            'ASIANPAINT': 'Consumer Goods',
            'MARUTI': 'Automotive',
            'BAJFINANCE': 'Financial Services',
            'HCLTECH': 'Technology'
        }
    
    def get_user_risk_params(self, user_id: str) -> RiskParameters:
        """Get risk parameters for a user"""
        if user_id not in self.user_risk_params:
            # In production, load from database
            self.user_risk_params[user_id] = self.default_risk_params
        return self.user_risk_params[user_id]
    
    def update_user_risk_params(self, user_id: str, risk_params: RiskParameters) -> bool:
        """Update risk parameters for a user"""
        try:
            self.user_risk_params[user_id] = risk_params
            # In production, save to database
            logger.info(f"Updated risk parameters for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating risk parameters for user {user_id}: {e}")
            return False
    
    @time_async_operation("validate_order")
    async def validate_order(self, order: Order) -> RiskValidationResult:
        """
        Comprehensive order validation against risk parameters
        
        Args:
            order: Order to validate
            
        Returns:
            RiskValidationResult with validation details
        """
        try:
            logger.debug(f"Validating order {order.id} for user {order.user_id}")
            
            risk_params = self.get_user_risk_params(order.user_id)
            violations = []
            warnings = []
            risk_score = 0.0
            
            # Basic order validation
            basic_validation = self._validate_basic_order(order)
            if not basic_validation['valid']:
                violations.extend(basic_validation['violations'])
                risk_score += 0.5
            
            # Position size validation
            position_validation = await self._validate_position_size(order, risk_params)
            if not position_validation['valid']:
                violations.extend(position_validation['violations'])
                risk_score += 0.3
            else:
                risk_score += position_validation['risk_score']
            
            # Portfolio exposure validation
            exposure_validation = await self._validate_portfolio_exposure(order, risk_params)
            if not exposure_validation['valid']:
                violations.extend(exposure_validation['violations'])
                risk_score += 0.4
            else:
                risk_score += exposure_validation['risk_score']
            
            # Sector concentration validation
            sector_validation = await self._validate_sector_exposure(order, risk_params)
            if not sector_validation['valid']:
                violations.extend(sector_validation['violations'])
                risk_score += 0.3
            else:
                warnings.extend(sector_validation['warnings'])
                risk_score += sector_validation['risk_score']
            
            # Daily trading limits
            daily_validation = await self._validate_daily_limits(order, risk_params)
            if not daily_validation['valid']:
                violations.extend(daily_validation['violations'])
                risk_score += 0.2
            
            # Market conditions validation
            market_validation = await self._validate_market_conditions(order)
            if not market_validation['valid']:
                warnings.extend(market_validation['warnings'])
                risk_score += market_validation['risk_score']
            
            # Calculate final risk score (0.0 to 1.0)
            risk_score = min(risk_score, 1.0)
            
            # Determine if order is valid
            is_valid = len(violations) == 0
            
            result = RiskValidationResult(
                valid=is_valid,
                risk_score=risk_score,
                violations=violations,
                warnings=warnings,
                metadata={
                    'user_id': order.user_id,
                    'order_id': order.id,
                    'symbol': order.symbol,
                    'validation_timestamp': datetime.now().isoformat(),
                    'risk_params_used': risk_params.to_dict()
                }
            )
            
            # Log validation result
            if is_valid:
                trading_monitor.increment_counter("risk_validations_passed")
                logger.info(f"Order {order.id} passed risk validation (risk score: {risk_score:.3f})")
            else:
                trading_monitor.increment_counter("risk_validations_failed")
                logger.warning(f"Order {order.id} failed risk validation: {violations}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error validating order {order.id}: {str(e)}"
            logger.error(error_msg)
            trading_monitor.increment_counter("risk_validation_errors")
            
            return RiskValidationResult(
                valid=False,
                risk_score=1.0,
                violations=[f"Risk validation error: {str(e)}"],
                warnings=[],
                metadata={'error': error_msg}
            )
    
    def _validate_basic_order(self, order: Order) -> Dict[str, Any]:
        """Basic order field validation"""
        violations = []
        
        if order.quantity <= 0:
            violations.append("Order quantity must be positive")
        
        if order.order_type == OrderType.LIMIT and not order.price:
            violations.append("Limit order requires a price")
        
        if order.order_type == OrderType.LIMIT and order.price <= 0:
            violations.append("Order price must be positive")
        
        if order.order_type in [OrderType.STOP_LOSS, OrderType.STOP_LIMIT] and not order.stop_price:
            violations.append("Stop order requires a stop price")
        
        if order.order_type in [OrderType.STOP_LOSS, OrderType.STOP_LIMIT] and order.stop_price <= 0:
            violations.append("Stop price must be positive")
        
        return {
            'valid': len(violations) == 0,
            'violations': violations
        }
    
    async def _validate_position_size(self, order: Order, risk_params: RiskParameters) -> Dict[str, Any]:
        """Validate position size against limits"""
        try:
            violations = []
            risk_score = 0.0
            
            # Calculate order value
            estimated_price = order.price or 100.0  # Default price for market orders
            order_value = order.quantity * estimated_price
            
            # Get user's portfolio value (simplified calculation)
            positions = await position_manager.get_user_positions(order.user_id)
            portfolio_value = sum(pos['market_value'] for pos in positions) + 100000  # Add cash estimate
            
            if portfolio_value <= 0:
                portfolio_value = 100000  # Default portfolio value
            
            # Calculate position size percentage
            position_size_percent = (order_value / portfolio_value) * 100
            
            # Check against maximum position size
            if position_size_percent > risk_params.max_position_size_percent:
                violations.append(
                    f"Position size {position_size_percent:.1f}% exceeds maximum allowed "
                    f"{risk_params.max_position_size_percent}%"
                )
            elif position_size_percent > risk_params.max_position_size_percent * 0.8:
                # Warning if close to limit
                risk_score += 0.3
            
            # Check absolute position value limits
            max_position_value = 50000  # ₹50,000 limit for now
            if order_value > max_position_value:
                violations.append(f"Order value ₹{order_value:,.0f} exceeds maximum ₹{max_position_value:,.0f}")
            
            return {
                'valid': len(violations) == 0,
                'violations': violations,
                'risk_score': risk_score,
                'position_size_percent': position_size_percent,
                'order_value': order_value
            }
            
        except Exception as e:
            logger.error(f"Error validating position size: {e}")
            return {
                'valid': False,
                'violations': [f"Position size validation error: {str(e)}"],
                'risk_score': 0.5
            }
    
    async def _validate_portfolio_exposure(self, order: Order, risk_params: RiskParameters) -> Dict[str, Any]:
        """Validate total portfolio exposure"""
        try:
            violations = []
            risk_score = 0.0
            
            # Get current positions
            positions = await position_manager.get_user_positions(order.user_id)
            current_exposure = sum(abs(pos['market_value']) for pos in positions)
            
            # Calculate new exposure after order
            estimated_price = order.price or 100.0
            order_value = order.quantity * estimated_price
            new_exposure = current_exposure + order_value
            
            # Estimate portfolio value
            portfolio_value = current_exposure + 100000  # Add cash estimate
            if portfolio_value <= 0:
                portfolio_value = 100000
            
            exposure_percent = (new_exposure / portfolio_value) * 100
            
            # Check against maximum portfolio exposure
            if exposure_percent > risk_params.max_portfolio_exposure_percent:
                violations.append(
                    f"Total portfolio exposure {exposure_percent:.1f}% would exceed maximum "
                    f"{risk_params.max_portfolio_exposure_percent}%"
                )
            elif exposure_percent > risk_params.max_portfolio_exposure_percent * 0.9:
                risk_score += 0.2
            
            return {
                'valid': len(violations) == 0,
                'violations': violations,
                'risk_score': risk_score,
                'current_exposure': current_exposure,
                'new_exposure': new_exposure,
                'exposure_percent': exposure_percent
            }
            
        except Exception as e:
            logger.error(f"Error validating portfolio exposure: {e}")
            return {
                'valid': False,
                'violations': [f"Portfolio exposure validation error: {str(e)}"],
                'risk_score': 0.3
            }
    
    async def _validate_sector_exposure(self, order: Order, risk_params: RiskParameters) -> Dict[str, Any]:
        """Validate sector concentration limits"""
        try:
            violations = []
            warnings = []
            risk_score = 0.0
            
            # Get sector for the symbol
            sector = self.sector_mappings.get(order.symbol, 'Unknown')
            
            if sector == 'Unknown':
                warnings.append(f"Unknown sector for symbol {order.symbol}")
                risk_score += 0.1
                return {
                    'valid': True,
                    'violations': violations,
                    'warnings': warnings,
                    'risk_score': risk_score
                }
            
            # Get current positions by sector
            positions = await position_manager.get_user_positions(order.user_id)
            sector_exposures = {}
            total_exposure = 0
            
            for pos in positions:
                pos_sector = self.sector_mappings.get(pos['symbol'], 'Unknown')
                if pos_sector != 'Unknown':
                    sector_exposures[pos_sector] = sector_exposures.get(pos_sector, 0) + abs(pos['market_value'])
                    total_exposure += abs(pos['market_value'])
            
            # Add new order to sector exposure
            estimated_price = order.price or 100.0
            order_value = order.quantity * estimated_price
            sector_exposures[sector] = sector_exposures.get(sector, 0) + order_value
            total_exposure += order_value
            
            # Calculate sector exposure percentage
            if total_exposure > 0:
                sector_percent = (sector_exposures[sector] / total_exposure) * 100
                
                if sector_percent > risk_params.max_sector_exposure_percent:
                    violations.append(
                        f"Sector exposure for {sector} would be {sector_percent:.1f}%, "
                        f"exceeding maximum {risk_params.max_sector_exposure_percent}%"
                    )
                elif sector_percent > risk_params.max_sector_exposure_percent * 0.8:
                    warnings.append(f"High sector concentration in {sector}: {sector_percent:.1f}%")
                    risk_score += 0.15
            
            return {
                'valid': len(violations) == 0,
                'violations': violations,
                'warnings': warnings,
                'risk_score': risk_score,
                'sector': sector,
                'sector_exposures': sector_exposures
            }
            
        except Exception as e:
            logger.error(f"Error validating sector exposure: {e}")
            return {
                'valid': True,  # Don't block orders on sector validation errors
                'violations': [],
                'warnings': [f"Sector validation error: {str(e)}"],
                'risk_score': 0.2
            }
    
    async def _validate_daily_limits(self, order: Order, risk_params: RiskParameters) -> Dict[str, Any]:
        """Validate daily trading limits"""
        try:
            violations = []
            
            # Get today's orders for the user
            today = datetime.now().date()
            user_orders = order_db.get_orders_by_user(order.user_id, limit=1000)
            today_orders = [o for o in user_orders if o.created_at.date() == today]
            
            # Check order count limit
            if len(today_orders) >= risk_params.max_orders_per_day:
                violations.append(
                    f"Daily order limit of {risk_params.max_orders_per_day} orders exceeded "
                    f"({len(today_orders)} orders today)"
                )
            
            # Check daily loss limit (simplified)
            daily_pnl = 0.0
            for order_record in today_orders:
                if order_record.status.value in ['FILLED', 'PARTIALLY_FILLED']:
                    # Simplified P&L calculation
                    if order_record.side == OrderSide.SELL:
                        daily_pnl += (order_record.average_fill_price or 0) * order_record.filled_quantity
                    else:
                        daily_pnl -= (order_record.average_fill_price or 0) * order_record.filled_quantity
            
            # Estimate portfolio value for percentage calculation
            positions = await position_manager.get_user_positions(order.user_id)
            portfolio_value = sum(abs(pos['market_value']) for pos in positions) + 100000
            
            if portfolio_value > 0:
                daily_loss_percent = abs(min(daily_pnl, 0)) / portfolio_value * 100
                if daily_loss_percent > risk_params.daily_loss_limit_percent:
                    violations.append(
                        f"Daily loss limit of {risk_params.daily_loss_limit_percent}% exceeded "
                        f"(current: {daily_loss_percent:.1f}%)"
                    )
            
            return {
                'valid': len(violations) == 0,
                'violations': violations,
                'today_orders_count': len(today_orders),
                'daily_pnl': daily_pnl
            }
            
        except Exception as e:
            logger.error(f"Error validating daily limits: {e}")
            return {
                'valid': True,  # Don't block on daily limit validation errors
                'violations': [],
                'warnings': [f"Daily limits validation error: {str(e)}"]
            }
    
    async def _validate_market_conditions(self, order: Order) -> Dict[str, Any]:
        """Validate market conditions and timing"""
        try:
            warnings = []
            risk_score = 0.0
            
            # Check market hours (simplified - assume market is open 9:15 AM to 3:30 PM IST)
            now = datetime.now()
            market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
            market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
            
            if not (market_open <= now <= market_close):
                warnings.append("Order placed outside market hours")
                risk_score += 0.1
            
            # Check for volatile market conditions (placeholder)
            # In production, this would check actual volatility indicators
            if order.order_type == OrderType.MARKET:
                warnings.append("Market order during potentially volatile conditions")
                risk_score += 0.05
            
            return {
                'valid': True,  # Market conditions don't block orders, just warn
                'violations': [],
                'warnings': warnings,
                'risk_score': risk_score
            }
            
        except Exception as e:
            logger.error(f"Error validating market conditions: {e}")
            return {
                'valid': True,
                'violations': [],
                'warnings': [f"Market conditions validation error: {str(e)}"],
                'risk_score': 0.1
            }
    
    @time_async_operation("calculate_portfolio_risk")
    async def calculate_portfolio_risk(self, user_id: str) -> PortfolioRisk:
        """
        Calculate comprehensive portfolio risk metrics
        
        Args:
            user_id: User ID
            
        Returns:
            PortfolioRisk object with risk metrics
        """
        try:
            logger.debug(f"Calculating portfolio risk for user {user_id}")
            
            # Get user positions
            positions = await position_manager.get_user_positions(user_id)
            
            if not positions:
                return PortfolioRisk(
                    total_exposure=0.0,
                    exposure_percentage=0.0,
                    max_drawdown=0.0,
                    current_drawdown=0.0,
                    var_95=0.0,
                    sector_exposures={},
                    position_concentrations={},
                    leverage_ratio=0.0,
                    risk_score=0.0
                )
            
            # Calculate total exposure
            total_exposure = sum(abs(pos['market_value']) for pos in positions)
            portfolio_value = total_exposure + 100000  # Add estimated cash
            exposure_percentage = (total_exposure / portfolio_value) * 100 if portfolio_value > 0 else 0
            
            # Calculate sector exposures
            sector_exposures = {}
            for pos in positions:
                sector = self.sector_mappings.get(pos['symbol'], 'Unknown')
                sector_exposures[sector] = sector_exposures.get(sector, 0) + abs(pos['market_value'])
            
            # Convert to percentages
            for sector in sector_exposures:
                sector_exposures[sector] = (sector_exposures[sector] / total_exposure) * 100 if total_exposure > 0 else 0
            
            # Calculate position concentrations
            position_concentrations = {}
            for pos in positions:
                symbol = pos['symbol']
                concentration = (abs(pos['market_value']) / total_exposure) * 100 if total_exposure > 0 else 0
                position_concentrations[symbol] = concentration
            
            # Calculate drawdown (simplified)
            total_unrealized_pnl = sum(pos['unrealized_pnl'] for pos in positions)
            total_realized_pnl = sum(pos['realized_pnl'] for pos in positions)
            total_pnl = total_unrealized_pnl + total_realized_pnl
            
            current_drawdown = abs(min(total_pnl, 0)) / portfolio_value * 100 if portfolio_value > 0 else 0
            max_drawdown = current_drawdown  # Simplified - would track historical max in production
            
            # Calculate VaR (simplified - would use proper statistical methods in production)
            var_95 = total_exposure * 0.05  # Assume 5% daily VaR
            
            # Calculate leverage ratio
            leverage_ratio = total_exposure / portfolio_value if portfolio_value > 0 else 0
            
            # Calculate overall risk score
            risk_score = self._calculate_risk_score(
                exposure_percentage, max(sector_exposures.values()) if sector_exposures else 0,
                max(position_concentrations.values()) if position_concentrations else 0,
                current_drawdown, leverage_ratio
            )
            
            portfolio_risk = PortfolioRisk(
                total_exposure=total_exposure,
                exposure_percentage=exposure_percentage,
                max_drawdown=max_drawdown,
                current_drawdown=current_drawdown,
                var_95=var_95,
                sector_exposures=sector_exposures,
                position_concentrations=position_concentrations,
                leverage_ratio=leverage_ratio,
                risk_score=risk_score
            )
            
            # Cache the result
            self.portfolio_risks[user_id] = {
                'risk': portfolio_risk,
                'timestamp': datetime.now()
            }
            
            trading_monitor.increment_counter("portfolio_risk_calculations")
            logger.debug(f"Portfolio risk calculated for user {user_id}: risk score = {risk_score:.3f}")
            
            return portfolio_risk
            
        except Exception as e:
            error_msg = f"Error calculating portfolio risk for user {user_id}: {str(e)}"
            logger.error(error_msg)
            trading_monitor.increment_counter("portfolio_risk_calculation_errors")
            
            # Return default risk object
            return PortfolioRisk(
                total_exposure=0.0,
                exposure_percentage=0.0,
                max_drawdown=0.0,
                current_drawdown=0.0,
                var_95=0.0,
                sector_exposures={},
                position_concentrations={},
                leverage_ratio=0.0,
                risk_score=1.0  # High risk score on error
            )
    
    def _calculate_risk_score(self, exposure_pct: float, max_sector_pct: float, 
                            max_position_pct: float, drawdown_pct: float, 
                            leverage: float) -> float:
        """Calculate overall portfolio risk score"""
        try:
            risk_params = self.default_risk_params
            
            # Normalize each component to 0-1 scale
            exposure_risk = min(exposure_pct / risk_params.max_portfolio_exposure_percent, 1.0)
            sector_risk = min(max_sector_pct / risk_params.max_sector_exposure_percent, 1.0)
            position_risk = min(max_position_pct / risk_params.max_position_size_percent, 1.0)
            drawdown_risk = min(drawdown_pct / risk_params.max_drawdown_percent, 1.0)
            leverage_risk = min(leverage / 2.0, 1.0)  # Assume 2.0 as max acceptable leverage
            
            # Weighted average of risk components
            weights = {
                'exposure': 0.25,
                'sector': 0.20,
                'position': 0.20,
                'drawdown': 0.25,
                'leverage': 0.10
            }
            
            risk_score = (
                exposure_risk * weights['exposure'] +
                sector_risk * weights['sector'] +
                position_risk * weights['position'] +
                drawdown_risk * weights['drawdown'] +
                leverage_risk * weights['leverage']
            )
            
            return min(risk_score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating risk score: {e}")
            return 0.5  # Default moderate risk

# Global risk engine instance
risk_engine = RiskEngine()