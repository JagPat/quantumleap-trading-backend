"""
Portfolio Analyzer
Comprehensive portfolio analysis, risk assessment, and health scoring
"""
import logging
import math
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import json

from .portfolio_models import (
    PortfolioData, PortfolioHolding, PortfolioHealthScore, 
    DiversificationMetrics, RiskAnalysisResult, VolatilityMetrics,
    RiskFactor, PerformanceMetrics, RiskLevel, HealthGrade,
    ValidationResult, CalculationResult
)

logger = logging.getLogger(__name__)

class PortfolioAnalyzer:
    """
    Comprehensive portfolio analyzer for health scoring, risk assessment,
    and diversification analysis
    """
    
    # Sector mapping for Indian stocks (simplified)
    SECTOR_MAPPING = {
        "RELIANCE": "Energy",
        "TCS": "Technology", 
        "HDFCBANK": "Banking",
        "INFY": "Technology",
        "HINDUNILVR": "Consumer Goods",
        "ICICIBANK": "Banking",
        "KOTAKBANK": "Banking",
        "SBIN": "Banking",
        "BHARTIARTL": "Telecom",
        "ITC": "Consumer Goods",
        "ASIANPAINT": "Consumer Goods",
        "MARUTI": "Automotive",
        "AXISBANK": "Banking",
        "LT": "Infrastructure",
        "WIPRO": "Technology",
        "HCLTECH": "Technology",
        "BAJFINANCE": "Financial Services",
        "TITAN": "Consumer Goods",
        "NESTLEIND": "Consumer Goods",
        "ULTRACEMCO": "Cement",
        "POWERGRID": "Utilities",
        "NTPC": "Utilities",
        "ONGC": "Energy",
        "COALINDIA": "Mining",
        "TATASTEEL": "Metals",
        "JSWSTEEL": "Metals",
        "HINDALCO": "Metals",
        "GRASIM": "Textiles",
        "DRREDDY": "Pharma",
        "SUNPHARMA": "Pharma",
        "CIPLA": "Pharma",
        "DIVISLAB": "Pharma"
    }
    
    def __init__(self):
        """Initialize portfolio analyzer"""
        pass
    
    def validate_portfolio_data(self, portfolio_data: Dict[str, Any]) -> ValidationResult:
        """Validate portfolio data for analysis"""
        errors = []
        warnings = []
        suggestions = []
        
        try:
            # Check required fields
            if not portfolio_data.get('holdings'):
                errors.append("Portfolio must contain holdings data")
                return ValidationResult(is_valid=False, errors=errors)
            
            holdings = portfolio_data['holdings']
            if not isinstance(holdings, list) or len(holdings) == 0:
                errors.append("Holdings must be a non-empty list")
                return ValidationResult(is_valid=False, errors=errors)
            
            # Validate individual holdings
            total_value = 0
            for i, holding in enumerate(holdings):
                if not isinstance(holding, dict):
                    errors.append(f"Holding {i} must be a dictionary")
                    continue
                
                # Check required fields
                required_fields = ['symbol', 'current_value']
                for field in required_fields:
                    if field not in holding:
                        errors.append(f"Holding {i} missing required field: {field}")
                
                # Validate numeric fields
                numeric_fields = ['current_value', 'quantity', 'investment_value', 'pnl']
                for field in numeric_fields:
                    if field in holding:
                        try:
                            value = float(holding[field])
                            if field == 'current_value' and value <= 0:
                                warnings.append(f"Holding {holding.get('symbol', i)} has non-positive current value")
                        except (ValueError, TypeError):
                            errors.append(f"Holding {i} field {field} must be numeric")
                
                if 'current_value' in holding:
                    total_value += abs(float(holding.get('current_value', 0)))
            
            # Portfolio level validations
            if total_value == 0:
                errors.append("Portfolio total value cannot be zero")
            
            if len(holdings) < 3:
                warnings.append("Portfolio has fewer than 3 holdings - consider diversification")
            
            if len(holdings) > 50:
                warnings.append("Portfolio has many holdings - consider consolidation")
            
            # Check for concentration
            if holdings:
                max_holding = max(abs(float(h.get('current_value', 0))) for h in holdings)
                if total_value > 0 and (max_holding / total_value) > 0.3:
                    warnings.append("Portfolio may be over-concentrated in single position")
            
            is_valid = len(errors) == 0
            
            if is_valid and len(warnings) == 0:
                suggestions.append("Portfolio data looks good for comprehensive analysis")
            
            return ValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"Portfolio validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=warnings,
                suggestions=suggestions
            )
    
    def calculate_portfolio_health(self, portfolio_data: Dict[str, Any]) -> CalculationResult:
        """Calculate comprehensive portfolio health score"""
        try:
            holdings = portfolio_data.get('holdings', [])
            if not holdings:
                return CalculationResult(
                    success=False,
                    error_message="No holdings data available for health calculation"
                )
            
            # Calculate individual health factors
            performance_score = self._calculate_performance_score(holdings)
            diversification_score = self._calculate_diversification_score(holdings)
            risk_score = self._calculate_risk_score(holdings)
            liquidity_score = self._calculate_liquidity_score(holdings)
            
            # Weight the factors
            weights = {
                'performance': 0.35,
                'diversification': 0.25,
                'risk': 0.25,
                'liquidity': 0.15
            }
            
            overall_score = (
                performance_score * weights['performance'] +
                diversification_score * weights['diversification'] +
                risk_score * weights['risk'] +
                liquidity_score * weights['liquidity']
            )
            
            # Determine improvement areas and strengths
            improvement_areas = []
            strengths = []
            
            if performance_score < 60:
                improvement_areas.append("Portfolio performance needs attention")
            elif performance_score > 80:
                strengths.append("Strong portfolio performance")
            
            if diversification_score < 60:
                improvement_areas.append("Increase portfolio diversification")
            elif diversification_score > 80:
                strengths.append("Well-diversified portfolio")
            
            if risk_score < 60:
                improvement_areas.append("Reduce portfolio risk exposure")
            elif risk_score > 80:
                strengths.append("Good risk management")
            
            if liquidity_score < 60:
                improvement_areas.append("Improve portfolio liquidity")
            elif liquidity_score > 80:
                strengths.append("High portfolio liquidity")
            
            health_score = PortfolioHealthScore(
                overall_score=overall_score,
                performance_score=performance_score,
                diversification_score=diversification_score,
                risk_score=risk_score,
                liquidity_score=liquidity_score,
                factors={
                    'performance': performance_score,
                    'diversification': diversification_score,
                    'risk': risk_score,
                    'liquidity': liquidity_score
                },
                grade=self._score_to_grade(overall_score),
                improvement_areas=improvement_areas,
                strengths=strengths
            )
            
            return CalculationResult(success=True, result=health_score)
            
        except Exception as e:
            logger.error(f"Health calculation failed: {e}")
            return CalculationResult(
                success=False,
                error_message=f"Health calculation error: {str(e)}"
            )
    
    def calculate_diversification_metrics(self, portfolio_data: Dict[str, Any]) -> CalculationResult:
        """Calculate comprehensive diversification metrics"""
        try:
            holdings = portfolio_data.get('holdings', [])
            if not holdings:
                return CalculationResult(
                    success=False,
                    error_message="No holdings data available for diversification calculation"
                )
            
            # Calculate total value
            total_value = sum(abs(float(h.get('current_value', 0))) for h in holdings)
            if total_value == 0:
                return CalculationResult(
                    success=False,
                    error_message="Portfolio total value is zero"
                )
            
            # Calculate sector allocations
            sector_allocations = {}
            for holding in holdings:
                symbol = holding.get('symbol', '').upper()
                sector = self.SECTOR_MAPPING.get(symbol, 'Other')
                value = abs(float(holding.get('current_value', 0)))
                allocation_pct = (value / total_value) * 100
                
                if sector not in sector_allocations:
                    sector_allocations[sector] = 0.0
                sector_allocations[sector] += allocation_pct
            
            # Calculate position concentrations
            position_weights = [abs(float(h.get('current_value', 0))) / total_value for h in holdings]
            position_weights.sort(reverse=True)
            
            largest_position_pct = position_weights[0] * 100 if position_weights else 0
            top5_concentration = sum(position_weights[:5]) * 100
            top10_concentration = sum(position_weights[:10]) * 100
            
            # Calculate Herfindahl-Hirschman Index for sectors
            hhi = sum((allocation / 100) ** 2 for allocation in sector_allocations.values())
            
            # Calculate diversification score (0-1, higher is better)
            diversification_score = 1.0 - hhi
            
            # Determine concentration risk level
            if largest_position_pct > 30:
                concentration_risk = RiskLevel.HIGH
            elif largest_position_pct > 15:
                concentration_risk = RiskLevel.MEDIUM
            else:
                concentration_risk = RiskLevel.LOW
            
            metrics = DiversificationMetrics(
                sector_count=len(sector_allocations),
                holding_count=len(holdings),
                largest_position_pct=largest_position_pct,
                top5_concentration=top5_concentration,
                top10_concentration=top10_concentration,
                herfindahl_index=hhi,
                diversification_score=diversification_score,
                sector_allocations=sector_allocations,
                concentration_risk_level=concentration_risk
            )
            
            return CalculationResult(success=True, result=metrics)
            
        except Exception as e:
            logger.error(f"Diversification calculation failed: {e}")
            return CalculationResult(
                success=False,
                error_message=f"Diversification calculation error: {str(e)}"
            )
    
    def calculate_risk_analysis(self, portfolio_data: Dict[str, Any], market_context: Optional[Dict[str, Any]] = None) -> CalculationResult:
        """Calculate comprehensive risk analysis"""
        try:
            holdings = portfolio_data.get('holdings', [])
            if not holdings:
                return CalculationResult(
                    success=False,
                    error_message="No holdings data available for risk analysis"
                )
            
            # Calculate concentration risk
            concentration_risk = self._calculate_concentration_risk(holdings)
            
            # Calculate sector exposure
            sector_exposure = self._calculate_sector_exposure(holdings)
            
            # Calculate volatility metrics
            volatility_result = self._calculate_volatility_metrics(holdings)
            
            # Identify risk factors
            risk_factors = self._identify_risk_factors(holdings, concentration_risk, sector_exposure)
            
            # Calculate overall risk score
            risk_components = [
                concentration_risk,
                volatility_result.risk_score,
                min(1.0, max(sector_exposure.values()) / 50) if sector_exposure else 0.5  # Sector concentration risk
            ]
            
            overall_risk_score = sum(risk_components) / len(risk_components)
            
            # Determine overall risk level
            if overall_risk_score > 0.7:
                overall_risk_level = RiskLevel.HIGH
            elif overall_risk_score > 0.4:
                overall_risk_level = RiskLevel.MEDIUM
            else:
                overall_risk_level = RiskLevel.LOW
            
            # Identify overexposed sectors (>25% allocation)
            overexposed_sectors = {
                sector: allocation 
                for sector, allocation in sector_exposure.items() 
                if allocation > 25.0
            }
            
            risk_analysis = RiskAnalysisResult(
                overall_risk_level=overall_risk_level,
                overall_risk_score=overall_risk_score,
                concentration_risk=concentration_risk,
                sector_exposure=sector_exposure,
                overexposed_sectors=overexposed_sectors,
                volatility_metrics=volatility_result,
                risk_factors=risk_factors,
                market_risk=self._assess_market_risk(market_context) if market_context else None
            )
            
            return CalculationResult(success=True, result=risk_analysis)
            
        except Exception as e:
            logger.error(f"Risk analysis calculation failed: {e}")
            return CalculationResult(
                success=False,
                error_message=f"Risk analysis error: {str(e)}"
            )
    
    def calculate_performance_metrics(self, portfolio_data: Dict[str, Any]) -> CalculationResult:
        """Calculate portfolio performance metrics"""
        try:
            holdings = portfolio_data.get('holdings', [])
            if not holdings:
                return CalculationResult(
                    success=False,
                    error_message="No holdings data available for performance calculation"
                )
            
            # Calculate total returns
            total_investment = sum(abs(float(h.get('investment_value', 0))) for h in holdings)
            total_current_value = sum(abs(float(h.get('current_value', 0))) for h in holdings)
            total_pnl = sum(float(h.get('pnl', 0)) for h in holdings)
            
            if total_investment == 0:
                return CalculationResult(
                    success=False,
                    error_message="Total investment value is zero"
                )
            
            total_return = total_pnl
            total_return_percentage = (total_pnl / total_investment) * 100
            
            # Find best and worst performers
            best_performer = None
            worst_performer = None
            best_return = float('-inf')
            worst_return = float('inf')
            
            for holding in holdings:
                pnl = float(holding.get('pnl', 0))
                investment = abs(float(holding.get('investment_value', 0)))
                
                if investment > 0:
                    return_pct = (pnl / investment) * 100
                    
                    if return_pct > best_return:
                        best_return = return_pct
                        best_performer = {
                            'symbol': holding.get('symbol'),
                            'return_percentage': return_pct,
                            'pnl': pnl
                        }
                    
                    if return_pct < worst_return:
                        worst_return = return_pct
                        worst_performer = {
                            'symbol': holding.get('symbol'),
                            'return_percentage': return_pct,
                            'pnl': pnl
                        }
            
            performance_metrics = PerformanceMetrics(
                total_return=total_return,
                total_return_percentage=total_return_percentage,
                best_performer=best_performer,
                worst_performer=worst_performer
            )
            
            return CalculationResult(success=True, result=performance_metrics)
            
        except Exception as e:
            logger.error(f"Performance calculation failed: {e}")
            return CalculationResult(
                success=False,
                error_message=f"Performance calculation error: {str(e)}"
            )
    
    # Private helper methods
    
    def _calculate_performance_score(self, holdings: List[Dict[str, Any]]) -> float:
        """Calculate performance component of health score"""
        try:
            total_investment = sum(abs(float(h.get('investment_value', 0))) for h in holdings)
            total_pnl = sum(float(h.get('pnl', 0)) for h in holdings)
            
            if total_investment == 0:
                return 50.0  # Neutral score
            
            return_pct = (total_pnl / total_investment) * 100
            
            # Score based on return percentage (-20% to +20% range)
            if return_pct >= 20:
                return 100.0
            elif return_pct >= 10:
                return 80.0 + (return_pct - 10) * 2
            elif return_pct >= 0:
                return 60.0 + (return_pct * 2)
            elif return_pct >= -10:
                return 40.0 + ((return_pct + 10) * 2)
            elif return_pct >= -20:
                return 20.0 + ((return_pct + 20) * 2)
            else:
                return 0.0
                
        except Exception:
            return 50.0  # Neutral score on error
    
    def _calculate_diversification_score(self, holdings: List[Dict[str, Any]]) -> float:
        """Calculate diversification component of health score"""
        try:
            if len(holdings) < 3:
                return 20.0  # Poor diversification
            
            total_value = sum(abs(float(h.get('current_value', 0))) for h in holdings)
            if total_value == 0:
                return 50.0
            
            # Calculate sector diversity
            sector_values = {}
            for holding in holdings:
                symbol = holding.get('symbol', '').upper()
                sector = self.SECTOR_MAPPING.get(symbol, 'Other')
                value = abs(float(holding.get('current_value', 0)))
                
                if sector not in sector_values:
                    sector_values[sector] = 0.0
                sector_values[sector] += value
            
            # Calculate HHI for sectors
            hhi = sum((value / total_value) ** 2 for value in sector_values.values())
            diversification_score = (1.0 - hhi) * 100
            
            # Adjust for number of holdings
            holding_bonus = min(20, len(holdings) * 2)  # Up to 20 points for holdings count
            
            return min(100.0, diversification_score + holding_bonus)
            
        except Exception:
            return 50.0  # Neutral score on error
    
    def _calculate_risk_score(self, holdings: List[Dict[str, Any]]) -> float:
        """Calculate risk component of health score (higher score = lower risk)"""
        try:
            concentration_risk = self._calculate_concentration_risk(holdings)
            volatility_risk = self._calculate_volatility_risk(holdings)
            
            # Combine risks (lower risk = higher score)
            combined_risk = (concentration_risk + volatility_risk) / 2
            risk_score = (1.0 - combined_risk) * 100
            
            return max(0.0, min(100.0, risk_score))
            
        except Exception:
            return 50.0  # Neutral score on error
    
    def _calculate_liquidity_score(self, holdings: List[Dict[str, Any]]) -> float:
        """Calculate liquidity component of health score"""
        try:
            # Simple liquidity assessment based on instrument types
            liquid_instruments = ['EQ', 'ETF']
            
            total_value = sum(abs(float(h.get('current_value', 0))) for h in holdings)
            if total_value == 0:
                return 50.0
            
            liquid_value = sum(
                abs(float(h.get('current_value', 0))) 
                for h in holdings 
                if h.get('instrument_type', 'EQ') in liquid_instruments
            )
            
            liquidity_ratio = liquid_value / total_value
            return liquidity_ratio * 100
            
        except Exception:
            return 75.0  # Assume good liquidity on error
    
    def _calculate_concentration_risk(self, holdings: List[Dict[str, Any]]) -> float:
        """Calculate portfolio concentration risk (0-1, higher = more risk)"""
        try:
            total_value = sum(abs(float(h.get('current_value', 0))) for h in holdings)
            if total_value == 0:
                return 1.0
            
            # Calculate position weights
            weights = [abs(float(h.get('current_value', 0))) / total_value for h in holdings]
            weights.sort(reverse=True)
            
            # Risk based on top positions
            top_3_concentration = sum(weights[:3])
            return min(1.0, top_3_concentration)
            
        except Exception:
            return 0.5  # Medium risk on error
    
    def _calculate_sector_exposure(self, holdings: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate sector exposure percentages"""
        try:
            sector_values = {}
            total_value = sum(abs(float(h.get('current_value', 0))) for h in holdings)
            
            if total_value == 0:
                return {}
            
            for holding in holdings:
                symbol = holding.get('symbol', '').upper()
                sector = self.SECTOR_MAPPING.get(symbol, 'Other')
                value = abs(float(holding.get('current_value', 0)))
                allocation_pct = (value / total_value) * 100
                
                if sector not in sector_values:
                    sector_values[sector] = 0.0
                sector_values[sector] += allocation_pct
            
            return sector_values
            
        except Exception:
            return {}
    
    def _calculate_volatility_metrics(self, holdings: List[Dict[str, Any]]) -> VolatilityMetrics:
        """Calculate portfolio volatility metrics"""
        try:
            pnl_values = [float(h.get('pnl', 0)) for h in holdings]
            
            if not pnl_values:
                return VolatilityMetrics(
                    portfolio_volatility=0.5,
                    risk_score=0.5,
                    coefficient_of_variation=0.0,
                    mean_return=0.0,
                    standard_deviation=0.0,
                    assessment="insufficient_data"
                )
            
            mean_pnl = sum(pnl_values) / len(pnl_values)
            
            if mean_pnl == 0:
                return VolatilityMetrics(
                    portfolio_volatility=0.5,
                    risk_score=0.5,
                    coefficient_of_variation=0.0,
                    mean_return=0.0,
                    standard_deviation=0.0,
                    assessment="neutral_performance"
                )
            
            variance = sum((pnl - mean_pnl) ** 2 for pnl in pnl_values) / len(pnl_values)
            std_dev = math.sqrt(variance)
            
            coefficient_of_variation = abs(std_dev / mean_pnl) if mean_pnl != 0 else 0
            risk_score = min(1.0, coefficient_of_variation / 2.0)
            
            assessment = "low" if risk_score < 0.3 else "medium" if risk_score < 0.7 else "high"
            
            return VolatilityMetrics(
                portfolio_volatility=risk_score,
                risk_score=risk_score,
                coefficient_of_variation=coefficient_of_variation,
                mean_return=mean_pnl,
                standard_deviation=std_dev,
                assessment=assessment
            )
            
        except Exception as e:
            logger.warning(f"Volatility calculation failed: {e}")
            return VolatilityMetrics(
                portfolio_volatility=0.5,
                risk_score=0.5,
                coefficient_of_variation=0.0,
                mean_return=0.0,
                standard_deviation=0.0,
                assessment="error"
            )
    
    def _calculate_volatility_risk(self, holdings: List[Dict[str, Any]]) -> float:
        """Calculate volatility risk component (0-1)"""
        volatility_metrics = self._calculate_volatility_metrics(holdings)
        return volatility_metrics.risk_score
    
    def _identify_risk_factors(self, holdings: List[Dict[str, Any]], concentration_risk: float, sector_exposure: Dict[str, float]) -> List[RiskFactor]:
        """Identify portfolio risk factors"""
        risk_factors = []
        
        # Concentration risk factor
        if concentration_risk > 0.7:
            risk_factors.append(RiskFactor(
                factor_name="High Concentration Risk",
                risk_level=RiskLevel.HIGH,
                impact_score=concentration_risk,
                description="Portfolio is heavily concentrated in few positions",
                mitigation_suggestions=[
                    "Consider reducing position sizes in largest holdings",
                    "Diversify into additional sectors or asset classes",
                    "Implement position size limits (e.g., max 10% per position)"
                ]
            ))
        
        # Sector concentration risk
        for sector, allocation in sector_exposure.items():
            if allocation > 40:
                risk_factors.append(RiskFactor(
                    factor_name=f"Sector Concentration - {sector}",
                    risk_level=RiskLevel.HIGH if allocation > 50 else RiskLevel.MEDIUM,
                    impact_score=min(1.0, allocation / 50),
                    description=f"Over-exposure to {sector} sector ({allocation:.1f}%)",
                    mitigation_suggestions=[
                        f"Reduce allocation to {sector} sector",
                        "Diversify into underrepresented sectors",
                        "Consider sector rotation strategies"
                    ]
                ))
        
        # Insufficient diversification
        if len(holdings) < 5:
            risk_factors.append(RiskFactor(
                factor_name="Insufficient Diversification",
                risk_level=RiskLevel.MEDIUM,
                impact_score=0.6,
                description=f"Portfolio has only {len(holdings)} holdings",
                mitigation_suggestions=[
                    "Increase number of holdings for better diversification",
                    "Consider index funds or ETFs for instant diversification",
                    "Add holdings from different sectors"
                ]
            ))
        
        return risk_factors
    
    def _assess_market_risk(self, market_context: Dict[str, Any]) -> Dict[str, Any]:
        """Assess market-related risks"""
        try:
            market_sentiment = market_context.get('market_sentiment', 'neutral')
            volatility = market_context.get('volatility_index', 0.5)
            
            risk_score = 0.5  # Base risk
            
            if market_sentiment == 'bearish':
                risk_score += 0.2
            elif market_sentiment == 'bullish':
                risk_score -= 0.1
            
            risk_score += volatility * 0.3
            risk_score = max(0.0, min(1.0, risk_score))
            
            return {
                "risk_score": risk_score,
                "market_sentiment": market_sentiment,
                "volatility": volatility,
                "assessment": "low" if risk_score < 0.3 else "medium" if risk_score < 0.7 else "high"
            }
            
        except Exception as e:
            logger.warning(f"Market risk assessment failed: {e}")
            return {"assessment": "unknown", "error": str(e)}
    
    def _score_to_grade(self, score: float) -> HealthGrade:
        """Convert numeric score to letter grade"""
        if score >= 90:
            return HealthGrade.A
        elif score >= 80:
            return HealthGrade.B
        elif score >= 70:
            return HealthGrade.C
        elif score >= 60:
            return HealthGrade.D
        else:
            return HealthGrade.F