"""
AI Portfolio Co-Pilot

Intelligent portfolio management assistant that provides rebalancing recommendations,
allocation optimization, and risk management insights.
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import json
import math

from .memory.strategy_store import StrategyStore
from .schemas.responses import (
    PortfolioCopilotResponse, PortfolioCopilotRecommendation
)
from .providers.base_provider import BaseAIProvider
from .providers import OpenAIClient, ClaudeClient

logger = logging.getLogger(__name__)


class PortfolioCopilot:
    """
    AI Portfolio Co-Pilot
    
    Responsibilities:
    - Portfolio health assessment
    - Rebalancing recommendations
    - Allocation optimization
    - Risk analysis and diversification
    - Market-aware portfolio adjustments
    """
    
    def __init__(self, strategy_store: StrategyStore):
        """Initialize portfolio co-pilot"""
        self.strategy_store = strategy_store
        
        # Use Claude for portfolio analysis (excellent at complex reasoning)
        self.analysis_provider = ClaudeClient()
    
    async def analyze_portfolio(
        self,
        user_id: str,
        portfolio_data: Dict[str, Any],
        market_context: Optional[Dict[str, Any]] = None
    ) -> PortfolioCopilotResponse:
        """
        Comprehensive portfolio analysis and recommendations
        
        Args:
            user_id: User identifier
            portfolio_data: Current portfolio holdings and performance
            market_context: Current market conditions and trends
            
        Returns:
            PortfolioCopilotResponse with analysis and recommendations
        """
        try:
            # Calculate portfolio health score
            health_score = self._calculate_portfolio_health(portfolio_data)
            
            # Assess diversification
            diversification_score = self._assess_diversification(portfolio_data)
            
            # Analyze risk exposure
            risk_analysis = self._analyze_portfolio_risk(portfolio_data, market_context)
            
            # Generate AI-powered recommendations
            recommendations = await self._generate_ai_recommendations(
                user_id, portfolio_data, market_context, health_score, diversification_score
            )
            
            # Suggest optimal allocations
            suggested_allocations = self._suggest_allocations(portfolio_data, risk_analysis)
            
            # Generate market context summary
            market_summary = self._generate_market_context_summary(market_context)
            
            return PortfolioCopilotResponse(
                success=True,
                portfolio_health_score=health_score,
                recommendations=recommendations,
                risk_analysis=risk_analysis,
                diversification_score=diversification_score,
                suggested_allocations=suggested_allocations,
                market_context=market_summary,
                generated_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze portfolio: {e}")
            return PortfolioCopilotResponse(
                success=False,
                portfolio_health_score=0.0,
                recommendations=[],
                risk_analysis={"error": str(e)},
                diversification_score=0.0,
                market_context="Analysis failed",
                generated_at=datetime.now()
            )
    
    def _calculate_portfolio_health(self, portfolio_data: Dict[str, Any]) -> float:
        """Calculate overall portfolio health score (0.0 to 1.0)"""
        try:
            holdings = portfolio_data.get('holdings', [])
            if not holdings:
                return 0.0
            
            health_factors = []
            
            # Performance factor
            total_pnl = sum(holding.get('pnl', 0.0) for holding in holdings)
            total_investment = sum(holding.get('investment_value', 0.0) for holding in holdings)
            
            if total_investment > 0:
                performance_ratio = total_pnl / total_investment
                performance_score = max(0.0, min(1.0, (performance_ratio + 0.2) / 0.4))  # -20% to +20% range
                health_factors.append(performance_score * 0.4)  # 40% weight
            
            # Diversification factor
            sector_diversity = self._calculate_sector_diversity(holdings)
            health_factors.append(sector_diversity * 0.3)  # 30% weight
            
            # Risk factor (inverse of concentration)
            concentration_risk = self._calculate_concentration_risk(holdings)
            risk_score = 1.0 - concentration_risk
            health_factors.append(risk_score * 0.2)  # 20% weight
            
            # Liquidity factor
            liquidity_score = self._assess_liquidity(holdings)
            health_factors.append(liquidity_score * 0.1)  # 10% weight
            
            return sum(health_factors) if health_factors else 0.0
            
        except Exception as e:
            logger.error(f"Failed to calculate portfolio health: {e}")
            return 0.0
    
    def _calculate_sector_diversity(self, holdings: List[Dict[str, Any]]) -> float:
        """Calculate sector diversification score"""
        try:
            if not holdings:
                return 0.0
            
            # Group by sector (use instrument type as proxy if sector not available)
            sector_values = {}
            total_value = 0.0
            
            for holding in holdings:
                sector = holding.get('sector', holding.get('instrument_type', 'unknown'))
                value = abs(holding.get('investment_value', 0.0))
                
                if sector not in sector_values:
                    sector_values[sector] = 0.0
                
                sector_values[sector] += value
                total_value += value
            
            if total_value == 0:
                return 0.0
            
            # Calculate Herfindahl-Hirschman Index (lower is more diversified)
            hhi = sum((value / total_value) ** 2 for value in sector_values.values())
            
            # Convert to diversification score (0 to 1, higher is better)
            # Perfect diversification (many equal sectors) approaches 0 HHI
            # Complete concentration (one sector) = 1 HHI
            diversification_score = 1.0 - hhi
            
            return diversification_score
            
        except Exception as e:
            logger.error(f"Failed to calculate sector diversity: {e}")
            return 0.0
    
    def _calculate_concentration_risk(self, holdings: List[Dict[str, Any]]) -> float:
        """Calculate portfolio concentration risk"""
        try:
            if not holdings:
                return 1.0  # Maximum risk
            
            total_value = sum(abs(holding.get('investment_value', 0.0)) for holding in holdings)
            
            if total_value == 0:
                return 1.0
            
            # Calculate concentration of top holdings
            holding_weights = [abs(holding.get('investment_value', 0.0)) / total_value for holding in holdings]
            holding_weights.sort(reverse=True)
            
            # Risk based on top 3 holdings concentration
            top_3_concentration = sum(holding_weights[:3])
            
            # Risk score: 0.0 (no concentration) to 1.0 (high concentration)
            concentration_risk = min(1.0, top_3_concentration)
            
            return concentration_risk
            
        except Exception as e:
            logger.error(f"Failed to calculate concentration risk: {e}")
            return 1.0
    
    def _assess_liquidity(self, holdings: List[Dict[str, Any]]) -> float:
        """Assess portfolio liquidity"""
        try:
            if not holdings:
                return 0.0
            
            # Simple liquidity assessment based on instrument types
            liquid_instruments = ['EQ', 'ETF']  # Equity and ETFs are generally liquid
            
            total_value = sum(abs(holding.get('investment_value', 0.0)) for holding in holdings)
            liquid_value = sum(
                abs(holding.get('investment_value', 0.0)) 
                for holding in holdings 
                if holding.get('instrument_type', '') in liquid_instruments
            )
            
            if total_value == 0:
                return 0.0
            
            liquidity_ratio = liquid_value / total_value
            return liquidity_ratio
            
        except Exception as e:
            logger.error(f"Failed to assess liquidity: {e}")
            return 0.0
    
    def _assess_diversification(self, portfolio_data: Dict[str, Any]) -> float:
        """Assess overall portfolio diversification"""
        holdings = portfolio_data.get('holdings', [])
        
        if not holdings:
            return 0.0
        
        # Combine sector diversity with holding count diversity
        sector_diversity = self._calculate_sector_diversity(holdings)
        
        # Holding count factor (more holdings generally better, up to a point)
        holding_count = len(holdings)
        count_score = min(1.0, holding_count / 20.0)  # Optimal around 20 holdings
        
        # Weight sector diversity more heavily
        diversification_score = sector_diversity * 0.7 + count_score * 0.3
        
        return diversification_score
    
    def _analyze_portfolio_risk(
        self, 
        portfolio_data: Dict[str, Any],
        market_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Comprehensive portfolio risk analysis"""
        try:
            holdings = portfolio_data.get('holdings', [])
            
            # Concentration risk
            concentration_risk = self._calculate_concentration_risk(holdings)
            
            # Sector exposure analysis
            sector_exposure = self._analyze_sector_exposure(holdings)
            
            # Volatility assessment
            volatility_assessment = self._assess_portfolio_volatility(holdings)
            
            # Market risk (if market context available)
            market_risk = self._assess_market_risk(portfolio_data, market_context)
            
            # Overall risk score
            risk_factors = [concentration_risk, volatility_assessment.get('risk_score', 0.5)]
            if market_risk.get('risk_score') is not None:
                risk_factors.append(market_risk['risk_score'])
            
            overall_risk = sum(risk_factors) / len(risk_factors)
            
            return {
                "overall_risk_score": overall_risk,
                "concentration_risk": concentration_risk,
                "sector_exposure": sector_exposure,
                "volatility_assessment": volatility_assessment,
                "market_risk": market_risk,
                "risk_level": "low" if overall_risk < 0.3 else "medium" if overall_risk < 0.7 else "high"
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze portfolio risk: {e}")
            return {"error": str(e)}
    
    def _analyze_sector_exposure(self, holdings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze sector exposure and concentration"""
        sector_allocation = {}
        total_value = sum(abs(holding.get('investment_value', 0.0)) for holding in holdings)
        
        if total_value == 0:
            return {"error": "No portfolio value to analyze"}
        
        for holding in holdings:
            sector = holding.get('sector', holding.get('instrument_type', 'unknown'))
            value = abs(holding.get('investment_value', 0.0))
            allocation = value / total_value
            
            if sector not in sector_allocation:
                sector_allocation[sector] = 0.0
            
            sector_allocation[sector] += allocation
        
        # Identify overexposed sectors (>30% allocation)
        overexposed_sectors = {
            sector: allocation 
            for sector, allocation in sector_allocation.items() 
            if allocation > 0.3
        }
        
        return {
            "sector_allocations": sector_allocation,
            "overexposed_sectors": overexposed_sectors,
            "sector_count": len(sector_allocation)
        }
    
    def _assess_portfolio_volatility(self, holdings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess portfolio volatility based on holdings"""
        try:
            # Simple volatility assessment based on P&L variation
            pnl_values = [holding.get('pnl', 0.0) for holding in holdings]
            
            if not pnl_values:
                return {"risk_score": 0.5, "assessment": "insufficient_data"}
            
            # Calculate coefficient of variation as proxy for volatility
            mean_pnl = sum(pnl_values) / len(pnl_values)
            
            if mean_pnl == 0:
                return {"risk_score": 0.5, "assessment": "neutral_performance"}
            
            variance = sum((pnl - mean_pnl) ** 2 for pnl in pnl_values) / len(pnl_values)
            std_dev = math.sqrt(variance)
            
            coefficient_of_variation = abs(std_dev / mean_pnl) if mean_pnl != 0 else 0
            
            # Convert to risk score (0 to 1)
            risk_score = min(1.0, coefficient_of_variation / 2.0)  # Normalize to reasonable range
            
            return {
                "risk_score": risk_score,
                "coefficient_of_variation": coefficient_of_variation,
                "mean_pnl": mean_pnl,
                "std_deviation": std_dev,
                "assessment": "low" if risk_score < 0.3 else "medium" if risk_score < 0.7 else "high"
            }
            
        except Exception as e:
            logger.error(f"Failed to assess portfolio volatility: {e}")
            return {"risk_score": 0.5, "assessment": "error", "error": str(e)}
    
    def _assess_market_risk(
        self, 
        portfolio_data: Dict[str, Any],
        market_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Assess market-related risks"""
        if not market_context:
            return {"assessment": "no_market_data"}
        
        try:
            # Analyze market sentiment impact
            market_sentiment = market_context.get('sentiment', 'neutral')
            volatility = market_context.get('volatility', 0.5)
            
            # Simple market risk scoring
            risk_score = 0.5  # Base risk
            
            if market_sentiment == 'bearish':
                risk_score += 0.2
            elif market_sentiment == 'bullish':
                risk_score -= 0.1
            
            risk_score += volatility * 0.3  # Add volatility component
            
            risk_score = max(0.0, min(1.0, risk_score))  # Clamp to [0, 1]
            
            return {
                "risk_score": risk_score,
                "market_sentiment": market_sentiment,
                "volatility": volatility,
                "assessment": "low" if risk_score < 0.3 else "medium" if risk_score < 0.7 else "high"
            }
            
        except Exception as e:
            logger.error(f"Failed to assess market risk: {e}")
            return {"assessment": "error", "error": str(e)}
    
    async def _generate_ai_recommendations(
        self,
        user_id: str,
        portfolio_data: Dict[str, Any],
        market_context: Optional[Dict[str, Any]],
        health_score: float,
        diversification_score: float
    ) -> List[PortfolioCopilotRecommendation]:
        """Generate AI-powered portfolio recommendations"""
        recommendations = []
        
        try:
            # Generate rule-based recommendations first
            rule_based_recs = self._generate_rule_based_recommendations(
                portfolio_data, health_score, diversification_score
            )
            recommendations.extend(rule_based_recs)
            
            # Generate AI-powered recommendations if provider available
            if self.analysis_provider and await self.analysis_provider.is_available():
                ai_recs = await self._generate_ai_powered_recommendations(
                    user_id, portfolio_data, market_context, health_score
                )
                recommendations.extend(ai_recs)
            
            # Prioritize and limit recommendations
            recommendations = self._prioritize_recommendations(recommendations)
            
            return recommendations[:10]  # Limit to top 10 recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate AI recommendations: {e}")
            return []
    
    def _generate_rule_based_recommendations(
        self,
        portfolio_data: Dict[str, Any],
        health_score: float,
        diversification_score: float
    ) -> List[PortfolioCopilotRecommendation]:
        """Generate rule-based recommendations"""
        recommendations = []
        holdings = portfolio_data.get('holdings', [])
        
        # Low health score recommendations
        if health_score < 0.5:
            recommendations.append(PortfolioCopilotRecommendation(
                recommendation_id=f"health_{uuid.uuid4().hex[:8]}",
                recommendation_type="portfolio_health",
                priority="high",
                title="Improve Portfolio Health",
                description="Portfolio health score is below optimal levels",
                rationale=f"Current health score: {health_score:.1%}. Consider reviewing underperforming positions and risk management.",
                implementation_steps=[
                    "Review positions with negative P&L",
                    "Consider reducing position sizes in volatile stocks",
                    "Evaluate stop-loss strategies"
                ],
                confidence=0.8
            ))
        
        # Low diversification recommendations
        if diversification_score < 0.6:
            recommendations.append(PortfolioCopilotRecommendation(
                recommendation_id=f"diversify_{uuid.uuid4().hex[:8]}",
                recommendation_type="diversification",
                priority="medium",
                title="Increase Portfolio Diversification",
                description="Portfolio shows concentration risk",
                rationale=f"Diversification score: {diversification_score:.1%}. Spreading investments across sectors reduces risk.",
                implementation_steps=[
                    "Identify overweight sectors",
                    "Research underrepresented sectors",
                    "Consider sector ETFs for instant diversification"
                ],
                confidence=0.9
            ))
        
        # High concentration recommendations
        concentration_risk = self._calculate_concentration_risk(holdings)
        if concentration_risk > 0.7:
            recommendations.append(PortfolioCopilotRecommendation(
                recommendation_id=f"concentration_{uuid.uuid4().hex[:8]}",
                recommendation_type="rebalance",
                priority="high",
                title="Reduce Concentration Risk",
                description="Portfolio is heavily concentrated in few positions",
                rationale="High concentration increases portfolio volatility and risk.",
                implementation_steps=[
                    "Identify top 3 largest positions",
                    "Consider trimming oversized positions",
                    "Reinvest proceeds in underweight areas"
                ],
                risk_impact="Reduces portfolio volatility",
                confidence=0.85
            ))
        
        return recommendations
    
    async def _generate_ai_powered_recommendations(
        self,
        user_id: str,
        portfolio_data: Dict[str, Any],
        market_context: Optional[Dict[str, Any]],
        health_score: float
    ) -> List[PortfolioCopilotRecommendation]:
        """Generate AI-powered recommendations using LLM"""
        try:
            # Create context for AI analysis
            analysis_prompt = self._create_portfolio_analysis_prompt(
                portfolio_data, market_context, health_score
            )
            
            # Get AI analysis
            response = await self.analysis_provider.generate_analysis(
                prompt=analysis_prompt,
                analysis_type="portfolio_optimization",
                context={
                    "user_id": user_id,
                    "health_score": health_score,
                    "portfolio_size": len(portfolio_data.get('holdings', []))
                }
            )
            
            if response.success:
                # Parse AI recommendations
                ai_recs = self._parse_ai_recommendations(response.analysis)
                return ai_recs
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to generate AI-powered recommendations: {e}")
            return []
    
    def _create_portfolio_analysis_prompt(
        self,
        portfolio_data: Dict[str, Any],
        market_context: Optional[Dict[str, Any]],
        health_score: float
    ) -> str:
        """Create prompt for AI portfolio analysis"""
        
        holdings = portfolio_data.get('holdings', [])
        total_value = sum(abs(h.get('investment_value', 0.0)) for h in holdings)
        total_pnl = sum(h.get('pnl', 0.0) for h in holdings)
        
        prompt = f"""
PORTFOLIO OPTIMIZATION ANALYSIS

You are an expert portfolio manager analyzing a client's investment portfolio.
Provide specific, actionable recommendations for optimization.

CURRENT PORTFOLIO:
- Total Holdings: {len(holdings)}
- Total Investment Value: ₹{total_value:,.2f}
- Total P&L: ₹{total_pnl:,.2f}
- Portfolio Health Score: {health_score:.1%}

TOP HOLDINGS:
"""
        
        # Add top 10 holdings
        sorted_holdings = sorted(holdings, key=lambda x: abs(x.get('investment_value', 0.0)), reverse=True)
        for i, holding in enumerate(sorted_holdings[:10]):
            symbol = holding.get('symbol', 'Unknown')
            value = holding.get('investment_value', 0.0)
            pnl = holding.get('pnl', 0.0)
            pnl_percent = (pnl / abs(value)) * 100 if value != 0 else 0
            
            prompt += f"\n{i+1}. {symbol}: ₹{value:,.2f} (P&L: {pnl_percent:+.1f}%)"
        
        if market_context:
            prompt += f"""

MARKET CONTEXT:
- Sentiment: {market_context.get('sentiment', 'Unknown')}
- Volatility: {market_context.get('volatility', 'Unknown')}
"""
        
        prompt += """

ANALYSIS REQUIRED:
1. REBALANCING OPPORTUNITIES:
   - Which positions are oversized and should be trimmed?
   - Which sectors/themes are underrepresented?
   - Any position sizing recommendations?

2. RISK MANAGEMENT:
   - What are the main risk factors?
   - How can portfolio volatility be reduced?
   - Any stop-loss or hedging recommendations?

3. OPTIMIZATION STRATEGIES:
   - How can returns be improved while managing risk?
   - Any tax-loss harvesting opportunities?
   - Portfolio allocation improvements?

Provide 3-5 specific, actionable recommendations with clear rationale and implementation steps.
Focus on practical advice that can be executed immediately.
"""
        
        return prompt
    
    def _parse_ai_recommendations(self, ai_analysis: str) -> List[PortfolioCopilotRecommendation]:
        """Parse AI analysis into structured recommendations"""
        recommendations = []
        
        try:
            # Simple parsing - look for numbered recommendations
            lines = ai_analysis.split('\n')
            current_rec = None
            
            for line in lines:
                line = line.strip()
                
                # Look for recommendation headers (numbers, bullets, etc.)
                if any(line.startswith(prefix) for prefix in ['1.', '2.', '3.', '4.', '5.', '-', '•']):
                    if current_rec:
                        recommendations.append(current_rec)
                    
                    # Extract title from line
                    title = line
                    for prefix in ['1.', '2.', '3.', '4.', '5.', '-', '•']:
                        title = title.replace(prefix, '').strip()
                    
                    current_rec = PortfolioCopilotRecommendation(
                        recommendation_id=f"ai_{uuid.uuid4().hex[:8]}",
                        recommendation_type="ai_generated",
                        priority="medium",
                        title=title[:100],  # Limit title length
                        description=title,
                        rationale="AI-generated recommendation based on portfolio analysis",
                        implementation_steps=[],
                        confidence=0.7
                    )
                
                elif current_rec and line:
                    # Add content to current recommendation
                    if len(current_rec.description) < 500:  # Limit description length
                        current_rec.description += f" {line}"
                    
                    if 'step' in line.lower() or 'action' in line.lower():
                        current_rec.implementation_steps.append(line)
            
            # Add final recommendation
            if current_rec:
                recommendations.append(current_rec)
            
        except Exception as e:
            logger.error(f"Failed to parse AI recommendations: {e}")
        
        return recommendations
    
    def _prioritize_recommendations(
        self, 
        recommendations: List[PortfolioCopilotRecommendation]
    ) -> List[PortfolioCopilotRecommendation]:
        """Prioritize recommendations by importance and confidence"""
        
        priority_weights = {"high": 3, "medium": 2, "low": 1}
        
        def recommendation_score(rec):
            priority_score = priority_weights.get(rec.priority, 1)
            confidence_score = rec.confidence
            return priority_score * confidence_score
        
        return sorted(recommendations, key=recommendation_score, reverse=True)
    
    def _suggest_allocations(
        self, 
        portfolio_data: Dict[str, Any],
        risk_analysis: Dict[str, Any]
    ) -> Optional[Dict[str, float]]:
        """Suggest optimal portfolio allocations"""
        try:
            holdings = portfolio_data.get('holdings', [])
            if not holdings:
                return None
            
            # Current allocations
            total_value = sum(abs(h.get('investment_value', 0.0)) for h in holdings)
            if total_value == 0:
                return None
            
            current_allocations = {}
            for holding in holdings:
                sector = holding.get('sector', holding.get('instrument_type', 'unknown'))
                value = abs(holding.get('investment_value', 0.0))
                allocation = value / total_value
                
                if sector not in current_allocations:
                    current_allocations[sector] = 0.0
                current_allocations[sector] += allocation
            
            # Suggest balanced allocations based on risk level
            risk_level = risk_analysis.get('risk_level', 'medium')
            
            if risk_level == 'low':
                # Conservative allocation
                target_allocations = self._get_conservative_allocation(current_allocations)
            elif risk_level == 'high':
                # Aggressive rebalancing
                target_allocations = self._get_aggressive_allocation(current_allocations)
            else:
                # Moderate rebalancing
                target_allocations = self._get_moderate_allocation(current_allocations)
            
            return target_allocations
            
        except Exception as e:
            logger.error(f"Failed to suggest allocations: {e}")
            return None
    
    def _get_conservative_allocation(self, current_allocations: Dict[str, float]) -> Dict[str, float]:
        """Get conservative allocation suggestions"""
        # Aim for balanced distribution with slight overweight to stable sectors
        target = {}
        
        for sector in current_allocations:
            if sector.lower() in ['banking', 'fmcg', 'pharma']:
                target[sector] = 0.25  # Stable sectors
            else:
                target[sector] = 0.15  # Other sectors
        
        # Normalize to 100%
        total = sum(target.values())
        if total > 0:
            target = {k: v / total for k, v in target.items()}
        
        return target
    
    def _get_moderate_allocation(self, current_allocations: Dict[str, float]) -> Dict[str, float]:
        """Get moderate allocation suggestions"""
        # Aim for equal weighting with minor adjustments
        sector_count = len(current_allocations)
        equal_weight = 1.0 / sector_count if sector_count > 0 else 0.0
        
        target = {}
        for sector in current_allocations:
            target[sector] = equal_weight
        
        return target
    
    def _get_aggressive_allocation(self, current_allocations: Dict[str, float]) -> Dict[str, float]:
        """Get aggressive allocation suggestions"""
        # Focus on growth sectors with higher concentration
        target = {}
        
        for sector in current_allocations:
            if sector.lower() in ['technology', 'auto', 'energy']:
                target[sector] = 0.30  # Growth sectors
            else:
                target[sector] = 0.10  # Conservative sectors
        
        # Normalize to 100%
        total = sum(target.values())
        if total > 0:
            target = {k: v / total for k, v in target.items()}
        
        return target
    
    def _generate_market_context_summary(self, market_context: Optional[Dict[str, Any]]) -> str:
        """Generate human-readable market context summary"""
        if not market_context:
            return "Market context not available"
        
        try:
            sentiment = market_context.get('sentiment', 'neutral')
            volatility = market_context.get('volatility', 0.5)
            trend = market_context.get('trend', 'sideways')
            
            summary = f"Market sentiment is {sentiment} with "
            
            if volatility > 0.7:
                summary += "high volatility. "
            elif volatility < 0.3:
                summary += "low volatility. "
            else:
                summary += "moderate volatility. "
            
            summary += f"Overall trend appears {trend}. "
            
            if sentiment == 'bearish' and volatility > 0.6:
                summary += "Consider defensive positioning and risk management."
            elif sentiment == 'bullish' and volatility < 0.4:
                summary += "Good environment for strategic position building."
            else:
                summary += "Mixed signals suggest balanced approach."
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate market context summary: {e}")
            return "Market analysis unavailable" 