"""
Portfolio Aggregation and Reporting
Advanced portfolio analytics and reporting functionality
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict
import statistics
from .models import Position, Order, Execution, OrderSide
from .position_manager import position_manager
from .order_db import order_db
from .monitoring import trading_monitor, time_async_operation

logger = logging.getLogger(__name__)

@dataclass
class PortfolioMetrics:
    """Comprehensive portfolio metrics"""
    total_value: float
    total_cost_basis: float
    total_unrealized_pnl: float
    total_realized_pnl: float
    total_pnl: float
    total_return_percent: float
    daily_pnl: float
    daily_return_percent: float
    positions_count: int
    winning_positions: int
    losing_positions: int
    win_rate: float
    largest_winner: float
    largest_loser: float
    average_position_size: float
    portfolio_beta: float
    sharpe_ratio: float
    max_drawdown: float
    volatility: float
    calculated_at: datetime

@dataclass
class SectorAnalysis:
    """Sector-wise portfolio analysis"""
    sector: str
    total_value: float
    percentage_of_portfolio: float
    positions_count: int
    unrealized_pnl: float
    realized_pnl: float
    total_pnl: float
    return_percent: float
    symbols: List[str]

@dataclass
class PerformanceAttribution:
    """Performance attribution analysis"""
    symbol: str
    sector: str
    contribution_to_return: float
    weight_in_portfolio: float
    individual_return: float
    excess_return: float  # vs benchmark
    risk_contribution: float

@dataclass
class RiskMetrics:
    """Portfolio risk metrics"""
    portfolio_var_95: float  # Value at Risk 95%
    portfolio_var_99: float  # Value at Risk 99%
    expected_shortfall: float
    beta: float
    alpha: float
    tracking_error: float
    information_ratio: float
    maximum_drawdown: float
    calmar_ratio: float
    sortino_ratio: float

class PortfolioAggregator:
    """
    Advanced portfolio aggregation and reporting system
    """
    
    def __init__(self):
        self.sector_mappings = self._load_sector_mappings()
        self.benchmark_returns = {}  # Would be loaded from market data
        
        logger.info("PortfolioAggregator initialized")
    
    def _load_sector_mappings(self) -> Dict[str, str]:
        """Load symbol to sector mappings"""
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
            'HCLTECH': 'Technology',
            'WIPRO': 'Technology',
            'ULTRACEMCO': 'Cement',
            'AXISBANK': 'Banking',
            'POWERGRID': 'Utilities',
            'NTPC': 'Utilities'
        }
    
    @time_async_operation("calculate_portfolio_metrics")
    async def calculate_portfolio_metrics(self, user_id: str) -> PortfolioMetrics:
        """
        Calculate comprehensive portfolio metrics
        
        Args:
            user_id: User ID
            
        Returns:
            PortfolioMetrics with comprehensive analysis
        """
        try:
            logger.debug(f"Calculating portfolio metrics for user {user_id}")
            
            # Get current positions
            positions = await position_manager.get_user_positions(user_id, include_closed=False)
            
            if not positions:
                return PortfolioMetrics(
                    total_value=0.0, total_cost_basis=0.0, total_unrealized_pnl=0.0,
                    total_realized_pnl=0.0, total_pnl=0.0, total_return_percent=0.0,
                    daily_pnl=0.0, daily_return_percent=0.0, positions_count=0,
                    winning_positions=0, losing_positions=0, win_rate=0.0,
                    largest_winner=0.0, largest_loser=0.0, average_position_size=0.0,
                    portfolio_beta=1.0, sharpe_ratio=0.0, max_drawdown=0.0,
                    volatility=0.0, calculated_at=datetime.now()
                )
            
            # Calculate basic metrics
            total_value = sum(pos['market_value'] for pos in positions)
            total_cost_basis = sum(pos['cost_basis'] for pos in positions)
            total_unrealized_pnl = sum(pos['unrealized_pnl'] for pos in positions)
            
            # Get realized P&L from closed positions
            closed_positions = await position_manager.get_user_positions(user_id, include_closed=True)
            closed_positions = [pos for pos in closed_positions if pos.get('is_closed', False)]
            total_realized_pnl = sum(pos['realized_pnl'] for pos in closed_positions)
            
            total_pnl = total_unrealized_pnl + total_realized_pnl
            total_return_percent = (total_pnl / total_cost_basis * 100) if total_cost_basis > 0 else 0.0
            
            # Calculate daily P&L (simplified)
            daily_pnl = await self._calculate_daily_pnl(user_id)
            daily_return_percent = (daily_pnl / total_value * 100) if total_value > 0 else 0.0
            
            # Position analysis
            winning_positions = len([pos for pos in positions if pos['unrealized_pnl'] > 0])
            losing_positions = len([pos for pos in positions if pos['unrealized_pnl'] < 0])
            win_rate = (winning_positions / len(positions) * 100) if positions else 0.0
            
            # Largest winner/loser
            pnl_values = [pos['unrealized_pnl'] for pos in positions]
            largest_winner = max(pnl_values) if pnl_values else 0.0
            largest_loser = min(pnl_values) if pnl_values else 0.0
            
            # Average position size
            average_position_size = total_value / len(positions) if positions else 0.0
            
            # Advanced metrics (simplified calculations)
            portfolio_beta = await self._calculate_portfolio_beta(positions)
            sharpe_ratio = await self._calculate_sharpe_ratio(user_id)
            max_drawdown = await self._calculate_max_drawdown(user_id)
            volatility = await self._calculate_portfolio_volatility(positions)
            
            metrics = PortfolioMetrics(
                total_value=total_value,
                total_cost_basis=total_cost_basis,
                total_unrealized_pnl=total_unrealized_pnl,
                total_realized_pnl=total_realized_pnl,
                total_pnl=total_pnl,
                total_return_percent=total_return_percent,
                daily_pnl=daily_pnl,
                daily_return_percent=daily_return_percent,
                positions_count=len(positions),
                winning_positions=winning_positions,
                losing_positions=losing_positions,
                win_rate=win_rate,
                largest_winner=largest_winner,
                largest_loser=largest_loser,
                average_position_size=average_position_size,
                portfolio_beta=portfolio_beta,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                volatility=volatility,
                calculated_at=datetime.now()
            )
            
            trading_monitor.increment_counter("portfolio_metrics_calculated")
            logger.debug(f"Portfolio metrics calculated for user {user_id}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating portfolio metrics for user {user_id}: {e}")
            trading_monitor.increment_counter("portfolio_metrics_errors")
            raise
    
    @time_async_operation("analyze_sector_allocation")
    async def analyze_sector_allocation(self, user_id: str) -> List[SectorAnalysis]:
        """
        Analyze portfolio allocation by sector
        
        Args:
            user_id: User ID
            
        Returns:
            List of SectorAnalysis objects
        """
        try:
            positions = await position_manager.get_user_positions(user_id, include_closed=False)
            
            if not positions:
                return []
            
            # Group positions by sector
            sector_data = defaultdict(lambda: {
                'total_value': 0.0,
                'positions_count': 0,
                'unrealized_pnl': 0.0,
                'realized_pnl': 0.0,
                'symbols': []
            })
            
            total_portfolio_value = sum(pos['market_value'] for pos in positions)
            
            for pos in positions:
                sector = self.sector_mappings.get(pos['symbol'], 'Other')
                sector_data[sector]['total_value'] += pos['market_value']
                sector_data[sector]['positions_count'] += 1
                sector_data[sector]['unrealized_pnl'] += pos['unrealized_pnl']
                sector_data[sector]['realized_pnl'] += pos['realized_pnl']
                sector_data[sector]['symbols'].append(pos['symbol'])
            
            # Create SectorAnalysis objects
            sector_analyses = []
            for sector, data in sector_data.items():
                total_pnl = data['unrealized_pnl'] + data['realized_pnl']
                return_percent = (total_pnl / data['total_value'] * 100) if data['total_value'] > 0 else 0.0
                percentage_of_portfolio = (data['total_value'] / total_portfolio_value * 100) if total_portfolio_value > 0 else 0.0
                
                analysis = SectorAnalysis(
                    sector=sector,
                    total_value=data['total_value'],
                    percentage_of_portfolio=percentage_of_portfolio,
                    positions_count=data['positions_count'],
                    unrealized_pnl=data['unrealized_pnl'],
                    realized_pnl=data['realized_pnl'],
                    total_pnl=total_pnl,
                    return_percent=return_percent,
                    symbols=data['symbols']
                )
                sector_analyses.append(analysis)
            
            # Sort by portfolio percentage (descending)
            sector_analyses.sort(key=lambda x: x.percentage_of_portfolio, reverse=True)
            
            trading_monitor.increment_counter("sector_analyses_calculated")
            logger.debug(f"Sector analysis calculated for user {user_id}: {len(sector_analyses)} sectors")
            
            return sector_analyses
            
        except Exception as e:
            logger.error(f"Error analyzing sector allocation for user {user_id}: {e}")
            return []
    
    @time_async_operation("calculate_performance_attribution")
    async def calculate_performance_attribution(self, user_id: str) -> List[PerformanceAttribution]:
        """
        Calculate performance attribution by position
        
        Args:
            user_id: User ID
            
        Returns:
            List of PerformanceAttribution objects
        """
        try:
            positions = await position_manager.get_user_positions(user_id, include_closed=False)
            
            if not positions:
                return []
            
            total_portfolio_value = sum(pos['market_value'] for pos in positions)
            total_portfolio_return = sum(pos['unrealized_pnl'] + pos['realized_pnl'] for pos in positions)
            
            attributions = []
            
            for pos in positions:
                symbol = pos['symbol']
                sector = self.sector_mappings.get(symbol, 'Other')
                
                # Calculate individual metrics
                position_value = pos['market_value']
                weight_in_portfolio = (position_value / total_portfolio_value) if total_portfolio_value > 0 else 0.0
                
                individual_pnl = pos['unrealized_pnl'] + pos['realized_pnl']
                individual_return = (individual_pnl / pos['cost_basis'] * 100) if pos['cost_basis'] > 0 else 0.0
                
                # Contribution to total return
                contribution_to_return = (individual_pnl / total_portfolio_value * 100) if total_portfolio_value > 0 else 0.0
                
                # Excess return (vs benchmark - simplified)
                benchmark_return = 10.0  # Assume 10% benchmark return
                excess_return = individual_return - benchmark_return
                
                # Risk contribution (simplified)
                risk_contribution = weight_in_portfolio * abs(individual_return - (total_portfolio_return / total_portfolio_value * 100))
                
                attribution = PerformanceAttribution(
                    symbol=symbol,
                    sector=sector,
                    contribution_to_return=contribution_to_return,
                    weight_in_portfolio=weight_in_portfolio * 100,
                    individual_return=individual_return,
                    excess_return=excess_return,
                    risk_contribution=risk_contribution
                )
                attributions.append(attribution)
            
            # Sort by contribution to return (descending)
            attributions.sort(key=lambda x: x.contribution_to_return, reverse=True)
            
            trading_monitor.increment_counter("performance_attributions_calculated")
            logger.debug(f"Performance attribution calculated for user {user_id}: {len(attributions)} positions")
            
            return attributions
            
        except Exception as e:
            logger.error(f"Error calculating performance attribution for user {user_id}: {e}")
            return []
    
    @time_async_operation("calculate_risk_metrics")
    async def calculate_risk_metrics(self, user_id: str) -> RiskMetrics:
        """
        Calculate comprehensive risk metrics
        
        Args:
            user_id: User ID
            
        Returns:
            RiskMetrics object
        """
        try:
            positions = await position_manager.get_user_positions(user_id, include_closed=False)
            
            if not positions:
                return RiskMetrics(
                    portfolio_var_95=0.0, portfolio_var_99=0.0, expected_shortfall=0.0,
                    beta=1.0, alpha=0.0, tracking_error=0.0, information_ratio=0.0,
                    maximum_drawdown=0.0, calmar_ratio=0.0, sortino_ratio=0.0
                )
            
            total_portfolio_value = sum(pos['market_value'] for pos in positions)
            
            # Calculate VaR (simplified Monte Carlo approach)
            portfolio_var_95 = total_portfolio_value * 0.05  # 5% VaR
            portfolio_var_99 = total_portfolio_value * 0.02  # 2% VaR
            expected_shortfall = total_portfolio_value * 0.03  # 3% Expected Shortfall
            
            # Portfolio beta (weighted average)
            portfolio_beta = await self._calculate_portfolio_beta(positions)
            
            # Alpha calculation (simplified)
            portfolio_return = sum(pos['unrealized_pnl'] + pos['realized_pnl'] for pos in positions)
            portfolio_return_percent = (portfolio_return / total_portfolio_value * 100) if total_portfolio_value > 0 else 0.0
            risk_free_rate = 6.0  # Assume 6% risk-free rate
            market_return = 12.0  # Assume 12% market return
            expected_return = risk_free_rate + portfolio_beta * (market_return - risk_free_rate)
            alpha = portfolio_return_percent - expected_return
            
            # Tracking error (simplified)
            tracking_error = abs(portfolio_return_percent - market_return)
            
            # Information ratio
            information_ratio = alpha / tracking_error if tracking_error > 0 else 0.0
            
            # Maximum drawdown
            maximum_drawdown = await self._calculate_max_drawdown(user_id)
            
            # Calmar ratio
            calmar_ratio = portfolio_return_percent / maximum_drawdown if maximum_drawdown > 0 else 0.0
            
            # Sortino ratio (simplified)
            downside_deviation = await self._calculate_downside_deviation(user_id)
            sortino_ratio = (portfolio_return_percent - risk_free_rate) / downside_deviation if downside_deviation > 0 else 0.0
            
            risk_metrics = RiskMetrics(
                portfolio_var_95=portfolio_var_95,
                portfolio_var_99=portfolio_var_99,
                expected_shortfall=expected_shortfall,
                beta=portfolio_beta,
                alpha=alpha,
                tracking_error=tracking_error,
                information_ratio=information_ratio,
                maximum_drawdown=maximum_drawdown,
                calmar_ratio=calmar_ratio,
                sortino_ratio=sortino_ratio
            )
            
            trading_monitor.increment_counter("risk_metrics_calculated")
            logger.debug(f"Risk metrics calculated for user {user_id}")
            
            return risk_metrics
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics for user {user_id}: {e}")
            return RiskMetrics(
                portfolio_var_95=0.0, portfolio_var_99=0.0, expected_shortfall=0.0,
                beta=1.0, alpha=0.0, tracking_error=0.0, information_ratio=0.0,
                maximum_drawdown=0.0, calmar_ratio=0.0, sortino_ratio=0.0
            )
    
    async def generate_portfolio_report(self, user_id: str) -> Dict[str, Any]:
        """
        Generate comprehensive portfolio report
        
        Args:
            user_id: User ID
            
        Returns:
            Comprehensive portfolio report
        """
        try:
            logger.info(f"Generating portfolio report for user {user_id}")
            
            # Calculate all metrics
            portfolio_metrics = await self.calculate_portfolio_metrics(user_id)
            sector_analysis = await self.analyze_sector_allocation(user_id)
            performance_attribution = await self.calculate_performance_attribution(user_id)
            risk_metrics = await self.calculate_risk_metrics(user_id)
            
            # Get additional data
            positions = await position_manager.get_user_positions(user_id, include_closed=False)
            position_history = await position_manager.get_position_history(user_id, days=30)
            
            # Generate summary insights
            insights = await self._generate_portfolio_insights(
                portfolio_metrics, sector_analysis, performance_attribution, risk_metrics
            )
            
            report = {
                'user_id': user_id,
                'generated_at': datetime.now().isoformat(),
                'summary': {
                    'total_value': portfolio_metrics.total_value,
                    'total_return_percent': portfolio_metrics.total_return_percent,
                    'daily_return_percent': portfolio_metrics.daily_return_percent,
                    'positions_count': portfolio_metrics.positions_count,
                    'win_rate': portfolio_metrics.win_rate
                },
                'portfolio_metrics': asdict(portfolio_metrics),
                'sector_analysis': [asdict(sector) for sector in sector_analysis],
                'performance_attribution': [asdict(attr) for attr in performance_attribution],
                'risk_metrics': asdict(risk_metrics),
                'current_positions': positions,
                'recent_history_count': len(position_history),
                'insights': insights
            }
            
            trading_monitor.increment_counter("portfolio_reports_generated")
            logger.info(f"Portfolio report generated for user {user_id}")
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating portfolio report for user {user_id}: {e}")
            return {
                'user_id': user_id,
                'generated_at': datetime.now().isoformat(),
                'error': str(e),
                'status': 'error'
            }
    
    # Helper methods for calculations
    
    async def _calculate_daily_pnl(self, user_id: str) -> float:
        """Calculate daily P&L (simplified)"""
        try:
            # This is a simplified calculation
            # In production, you'd track daily position values
            positions = await position_manager.get_user_positions(user_id)
            return sum(pos['unrealized_pnl'] * 0.1 for pos in positions)  # Assume 10% is daily
        except:
            return 0.0
    
    async def _calculate_portfolio_beta(self, positions: List[Dict[str, Any]]) -> float:
        """Calculate portfolio beta (simplified)"""
        try:
            # Simplified beta calculation
            # In production, you'd use actual stock betas and weights
            stock_betas = {
                'RELIANCE': 1.2, 'TCS': 0.8, 'INFY': 0.9, 'HDFCBANK': 1.1,
                'ICICIBANK': 1.3, 'SBIN': 1.4, 'ITC': 0.7, 'BHARTIARTL': 1.0
            }
            
            total_value = sum(pos['market_value'] for pos in positions)
            if total_value == 0:
                return 1.0
            
            weighted_beta = 0.0
            for pos in positions:
                weight = pos['market_value'] / total_value
                beta = stock_betas.get(pos['symbol'], 1.0)
                weighted_beta += weight * beta
            
            return weighted_beta
        except:
            return 1.0
    
    async def _calculate_sharpe_ratio(self, user_id: str) -> float:
        """Calculate Sharpe ratio (simplified)"""
        try:
            # Simplified Sharpe ratio calculation
            positions = await position_manager.get_user_positions(user_id)
            if not positions:
                return 0.0
            
            total_return = sum(pos['unrealized_pnl'] + pos['realized_pnl'] for pos in positions)
            total_value = sum(pos['market_value'] for pos in positions)
            
            if total_value == 0:
                return 0.0
            
            portfolio_return = (total_return / total_value) * 100
            risk_free_rate = 6.0  # Assume 6% risk-free rate
            volatility = await self._calculate_portfolio_volatility(positions)
            
            if volatility == 0:
                return 0.0
            
            return (portfolio_return - risk_free_rate) / volatility
        except:
            return 0.0
    
    async def _calculate_max_drawdown(self, user_id: str) -> float:
        """Calculate maximum drawdown (simplified)"""
        try:
            # Simplified drawdown calculation
            positions = await position_manager.get_user_positions(user_id)
            if not positions:
                return 0.0
            
            negative_pnl = [pos['unrealized_pnl'] for pos in positions if pos['unrealized_pnl'] < 0]
            if not negative_pnl:
                return 0.0
            
            total_value = sum(pos['market_value'] for pos in positions)
            max_loss = abs(min(negative_pnl))
            
            return (max_loss / total_value * 100) if total_value > 0 else 0.0
        except:
            return 0.0
    
    async def _calculate_portfolio_volatility(self, positions: List[Dict[str, Any]]) -> float:
        """Calculate portfolio volatility (simplified)"""
        try:
            # Simplified volatility calculation
            if not positions:
                return 0.0
            
            returns = []
            for pos in positions:
                if pos['cost_basis'] > 0:
                    return_pct = (pos['unrealized_pnl'] / pos['cost_basis']) * 100
                    returns.append(return_pct)
            
            if len(returns) < 2:
                return 0.0
            
            return statistics.stdev(returns)
        except:
            return 0.0
    
    async def _calculate_downside_deviation(self, user_id: str) -> float:
        """Calculate downside deviation (simplified)"""
        try:
            positions = await position_manager.get_user_positions(user_id)
            if not positions:
                return 0.0
            
            negative_returns = []
            for pos in positions:
                if pos['cost_basis'] > 0:
                    return_pct = (pos['unrealized_pnl'] / pos['cost_basis']) * 100
                    if return_pct < 0:
                        negative_returns.append(return_pct)
            
            if len(negative_returns) < 2:
                return 0.0
            
            return statistics.stdev(negative_returns)
        except:
            return 0.0
    
    async def _generate_portfolio_insights(self, metrics: PortfolioMetrics, 
                                         sectors: List[SectorAnalysis],
                                         attribution: List[PerformanceAttribution],
                                         risk: RiskMetrics) -> List[str]:
        """Generate portfolio insights and recommendations"""
        insights = []
        
        try:
            # Performance insights
            if metrics.total_return_percent > 15:
                insights.append("🎉 Excellent portfolio performance with strong returns")
            elif metrics.total_return_percent > 8:
                insights.append("✅ Good portfolio performance above market average")
            elif metrics.total_return_percent < -5:
                insights.append("⚠️ Portfolio underperforming - consider rebalancing")
            
            # Risk insights
            if risk.maximum_drawdown > 20:
                insights.append("🚨 High drawdown detected - review risk management")
            elif metrics.volatility > 25:
                insights.append("⚠️ High portfolio volatility - consider diversification")
            
            # Sector concentration insights
            if sectors:
                max_sector = max(sectors, key=lambda x: x.percentage_of_portfolio)
                if max_sector.percentage_of_portfolio > 40:
                    insights.append(f"⚠️ High concentration in {max_sector.sector} sector ({max_sector.percentage_of_portfolio:.1f}%)")
            
            # Win rate insights
            if metrics.win_rate > 70:
                insights.append("🎯 High win rate indicates good stock selection")
            elif metrics.win_rate < 40:
                insights.append("📊 Low win rate - consider improving entry strategy")
            
            # Position insights
            if metrics.positions_count < 5:
                insights.append("📈 Consider adding more positions for better diversification")
            elif metrics.positions_count > 20:
                insights.append("📊 Large number of positions - consider consolidation")
            
            # Attribution insights
            if attribution:
                top_contributor = max(attribution, key=lambda x: x.contribution_to_return)
                if top_contributor.contribution_to_return > 5:
                    insights.append(f"⭐ {top_contributor.symbol} is your top performer contributing {top_contributor.contribution_to_return:.1f}%")
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return ["📊 Portfolio analysis completed"]

# Global portfolio aggregator instance
portfolio_aggregator = PortfolioAggregator()