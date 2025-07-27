"""
Portfolio Recommendation Engine
Generates actionable portfolio optimization recommendations using rule-based and AI-powered analysis
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
import json

from .portfolio_models import (
    PortfolioRecommendation, RecommendationType, Priority, RiskLevel,
    PortfolioHealthScore, RiskAnalysisResult, DiversificationMetrics,
    PerformanceMetrics, CalculationResult
)

logger = logging.getLogger(__name__)

class RecommendationEngine:
    """
    Portfolio recommendation engine that generates actionable optimization suggestions
    """
    
    def __init__(self):
        """Initialize recommendation engine"""
        pass
    
    def generate_recommendations(
        self,
        portfolio_data: Dict[str, Any],
        health_score: PortfolioHealthScore,
        risk_analysis: RiskAnalysisResult,
        diversification_metrics: DiversificationMetrics,
        performance_metrics: PerformanceMetrics,
        ai_recommendations: Optional[List[Dict[str, Any]]] = None
    ) -> CalculationResult:
        """Generate comprehensive portfolio recommendations"""
        try:
            recommendations = []
            
            # Generate rule-based recommendations
            rule_based_recs = self._generate_rule_based_recommendations(
                portfolio_data, health_score, risk_analysis, 
                diversification_metrics, performance_metrics
            )
            recommendations.extend(rule_based_recs)
            
            # Integrate AI recommendations if available
            if ai_recommendations:
                ai_recs = self._process_ai_recommendations(ai_recommendations)
                recommendations.extend(ai_recs)
            
            # Prioritize and limit recommendations
            prioritized_recs = self._prioritize_recommendations(recommendations)
            final_recs = prioritized_recs[:10]  # Limit to top 10
            
            return CalculationResult(success=True, result=final_recs)
            
        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
            return CalculationResult(
                success=False,
                error_message=f"Recommendation generation error: {str(e)}"
            )
    
    def _generate_rule_based_recommendations(
        self,
        portfolio_data: Dict[str, Any],
        health_score: PortfolioHealthScore,
        risk_analysis: RiskAnalysisResult,
        diversification_metrics: DiversificationMetrics,
        performance_metrics: PerformanceMetrics
    ) -> List[PortfolioRecommendation]:
        """Generate rule-based recommendations"""
        recommendations = []
        holdings = portfolio_data.get('holdings', [])
        
        # Health-based recommendations
        if health_score.overall_score < 60:
            recommendations.append(self._create_health_improvement_recommendation(health_score))
        
        # Diversification recommendations
        if diversification_metrics.diversification_score < 0.6:
            recommendations.extend(self._create_diversification_recommendations(
                diversification_metrics, holdings
            ))
        
        # Risk management recommendations
        if risk_analysis.overall_risk_level == RiskLevel.HIGH:
            recommendations.extend(self._create_risk_management_recommendations(
                risk_analysis, holdings
            ))
        
        # Concentration risk recommendations
        if diversification_metrics.largest_position_pct > 25:
            recommendations.append(self._create_concentration_reduction_recommendation(
                diversification_metrics, holdings
            ))
        
        # Sector exposure recommendations
        if risk_analysis.overexposed_sectors:
            recommendations.extend(self._create_sector_rebalancing_recommendations(
                risk_analysis.overexposed_sectors
            ))
        
        # Performance optimization recommendations
        if performance_metrics.total_return_percentage < -5:
            recommendations.extend(self._create_performance_improvement_recommendations(
                performance_metrics, holdings
            ))
        
        # Liquidity recommendations
        if health_score.liquidity_score < 60:
            recommendations.append(self._create_liquidity_improvement_recommendation())
        
        return recommendations
    
    def _create_health_improvement_recommendation(self, health_score: PortfolioHealthScore) -> PortfolioRecommendation:
        """Create recommendation for improving overall portfolio health"""
        return PortfolioRecommendation(
            recommendation_id=f"health_{uuid.uuid4().hex[:8]}",
            type=RecommendationType.OPTIMIZE,
            priority=Priority.HIGH,
            title="Improve Overall Portfolio Health",
            description=f"Portfolio health score is {health_score.overall_score:.1f}/100 (Grade: {health_score.grade.value})",
            rationale=f"Current health factors: Performance ({health_score.performance_score:.1f}), "
                     f"Diversification ({health_score.diversification_score:.1f}), "
                     f"Risk ({health_score.risk_score:.1f}), Liquidity ({health_score.liquidity_score:.1f})",
            implementation_steps=[
                "Focus on improvement areas: " + ", ".join(health_score.improvement_areas),
                "Review underperforming positions",
                "Consider rebalancing based on risk tolerance",
                "Evaluate portfolio alignment with investment goals"
            ],
            expected_impact="Improve overall portfolio health score and risk-adjusted returns",
            confidence_score=0.85,
            timeframe="1-3 months"
        )
    
    def _create_diversification_recommendations(
        self, 
        diversification_metrics: DiversificationMetrics,
        holdings: List[Dict[str, Any]]
    ) -> List[PortfolioRecommendation]:
        """Create diversification improvement recommendations"""
        recommendations = []
        
        # Sector diversification
        if diversification_metrics.sector_count < 5:
            recommendations.append(PortfolioRecommendation(
                recommendation_id=f"diversify_sector_{uuid.uuid4().hex[:8]}",
                type=RecommendationType.DIVERSIFY,
                priority=Priority.MEDIUM,
                title="Increase Sector Diversification",
                description=f"Portfolio is concentrated in {diversification_metrics.sector_count} sectors",
                rationale="Diversifying across sectors reduces portfolio volatility and correlation risk",
                implementation_steps=[
                    "Identify underrepresented sectors (Technology, Healthcare, Consumer Goods)",
                    "Research sector ETFs for instant diversification",
                    "Gradually add positions in 2-3 new sectors",
                    "Maintain sector allocation limits (max 25% per sector)"
                ],
                expected_impact="Reduce portfolio volatility and improve risk-adjusted returns",
                confidence_score=0.9,
                timeframe="2-4 months"
            ))
        
        # Holdings count diversification
        if diversification_metrics.holding_count < 8:
            recommendations.append(PortfolioRecommendation(
                recommendation_id=f"diversify_holdings_{uuid.uuid4().hex[:8]}",
                type=RecommendationType.DIVERSIFY,
                priority=Priority.MEDIUM,
                title="Increase Number of Holdings",
                description=f"Portfolio has only {diversification_metrics.holding_count} holdings",
                rationale="More holdings provide better diversification and reduce single-stock risk",
                implementation_steps=[
                    "Target 10-15 holdings for optimal diversification",
                    "Add quality stocks from different sectors",
                    "Consider index funds for instant diversification",
                    "Maintain position size discipline (max 10% per holding)"
                ],
                expected_impact="Reduce single-stock risk and improve portfolio stability",
                confidence_score=0.8,
                timeframe="1-2 months"
            ))
        
        return recommendations
    
    def _create_risk_management_recommendations(
        self,
        risk_analysis: RiskAnalysisResult,
        holdings: List[Dict[str, Any]]
    ) -> List[PortfolioRecommendation]:
        """Create risk management recommendations"""
        recommendations = []
        
        # High overall risk
        recommendations.append(PortfolioRecommendation(
            recommendation_id=f"risk_mgmt_{uuid.uuid4().hex[:8]}",
            type=RecommendationType.RISK_MANAGEMENT,
            priority=Priority.HIGH,
            title="Reduce Portfolio Risk Exposure",
            description=f"Portfolio risk level is {risk_analysis.overall_risk_level.value} "
                       f"(Risk Score: {risk_analysis.overall_risk_score:.2f})",
            rationale="High risk exposure may lead to significant losses during market downturns",
            implementation_steps=[
                "Review and reduce position sizes in high-risk holdings",
                "Consider adding defensive stocks (utilities, consumer staples)",
                "Implement stop-loss orders for volatile positions",
                "Diversify across asset classes (bonds, gold, REITs)"
            ],
            expected_impact="Reduce portfolio volatility and downside risk",
            confidence_score=0.85,
            risk_impact="Significantly reduces portfolio risk",
            timeframe="Immediate to 1 month"
        ))
        
        # Specific risk factors
        for risk_factor in risk_analysis.risk_factors:
            if risk_factor.risk_level == RiskLevel.HIGH:
                recommendations.append(PortfolioRecommendation(
                    recommendation_id=f"risk_factor_{uuid.uuid4().hex[:8]}",
                    type=RecommendationType.RISK_MANAGEMENT,
                    priority=Priority.HIGH,
                    title=f"Address {risk_factor.factor_name}",
                    description=risk_factor.description,
                    rationale=f"High impact risk factor (Impact Score: {risk_factor.impact_score:.2f})",
                    implementation_steps=risk_factor.mitigation_suggestions,
                    expected_impact="Reduce specific risk exposure",
                    confidence_score=0.8,
                    timeframe="1-2 months"
                ))
        
        return recommendations
    
    def _create_concentration_reduction_recommendation(
        self,
        diversification_metrics: DiversificationMetrics,
        holdings: List[Dict[str, Any]]
    ) -> PortfolioRecommendation:
        """Create recommendation to reduce concentration risk"""
        
        # Find the largest position
        largest_holding = max(holdings, key=lambda h: abs(float(h.get('current_value', 0))))
        largest_symbol = largest_holding.get('symbol', 'Unknown')
        
        return PortfolioRecommendation(
            recommendation_id=f"concentration_{uuid.uuid4().hex[:8]}",
            type=RecommendationType.REBALANCE,
            priority=Priority.HIGH,
            title="Reduce Position Concentration",
            description=f"Largest position ({largest_symbol}) represents "
                       f"{diversification_metrics.largest_position_pct:.1f}% of portfolio",
            rationale="High concentration increases portfolio volatility and single-stock risk",
            implementation_steps=[
                f"Consider reducing {largest_symbol} position to 10-15% of portfolio",
                "Reinvest proceeds in underweight sectors or holdings",
                "Implement position size limits for future investments",
                "Use systematic rebalancing approach"
            ],
            expected_impact="Reduce concentration risk and improve portfolio stability",
            confidence_score=0.9,
            affected_symbols=[largest_symbol],
            target_allocation=15.0,
            timeframe="1-2 months"
        )
    
    def _create_sector_rebalancing_recommendations(
        self,
        overexposed_sectors: Dict[str, float]
    ) -> List[PortfolioRecommendation]:
        """Create sector rebalancing recommendations"""
        recommendations = []
        
        for sector, allocation in overexposed_sectors.items():
            recommendations.append(PortfolioRecommendation(
                recommendation_id=f"sector_rebal_{uuid.uuid4().hex[:8]}",
                type=RecommendationType.REBALANCE,
                priority=Priority.MEDIUM,
                title=f"Rebalance {sector} Sector Exposure",
                description=f"{sector} sector allocation is {allocation:.1f}% (recommended max: 25%)",
                rationale="Sector over-concentration increases correlation risk and volatility",
                implementation_steps=[
                    f"Reduce {sector} sector allocation to 20-25% of portfolio",
                    "Identify specific holdings to trim within the sector",
                    "Diversify proceeds into underrepresented sectors",
                    "Monitor sector allocation regularly"
                ],
                expected_impact="Improve sector diversification and reduce correlation risk",
                confidence_score=0.85,
                target_allocation=22.5,
                timeframe="2-3 months"
            ))
        
        return recommendations
    
    def _create_performance_improvement_recommendations(
        self,
        performance_metrics: PerformanceMetrics,
        holdings: List[Dict[str, Any]]
    ) -> List[PortfolioRecommendation]:
        """Create performance improvement recommendations"""
        recommendations = []
        
        # Overall performance improvement
        recommendations.append(PortfolioRecommendation(
            recommendation_id=f"performance_{uuid.uuid4().hex[:8]}",
            type=RecommendationType.PERFORMANCE,
            priority=Priority.HIGH,
            title="Improve Portfolio Performance",
            description=f"Portfolio return is {performance_metrics.total_return_percentage:.1f}%",
            rationale="Negative returns indicate need for portfolio optimization",
            implementation_steps=[
                "Review and exit underperforming positions",
                "Focus on quality stocks with strong fundamentals",
                "Consider growth sectors and themes",
                "Implement systematic review process"
            ],
            expected_impact="Improve portfolio returns and performance consistency",
            confidence_score=0.75,
            timeframe="3-6 months"
        ))
        
        # Worst performer specific recommendation
        if performance_metrics.worst_performer:
            worst_symbol = performance_metrics.worst_performer['symbol']
            worst_return = performance_metrics.worst_performer['return_percentage']
            
            recommendations.append(PortfolioRecommendation(
                recommendation_id=f"worst_performer_{uuid.uuid4().hex[:8]}",
                type=RecommendationType.OPTIMIZE,
                priority=Priority.MEDIUM,
                title=f"Review {worst_symbol} Position",
                description=f"{worst_symbol} is down {abs(worst_return):.1f}%",
                rationale="Worst performing position may need review or exit strategy",
                implementation_steps=[
                    f"Analyze {worst_symbol} fundamentals and outlook",
                    "Consider stop-loss or position reduction",
                    "Evaluate replacement opportunities",
                    "Set clear exit criteria"
                ],
                expected_impact="Reduce drag on portfolio performance",
                confidence_score=0.7,
                affected_symbols=[worst_symbol],
                timeframe="1 month"
            ))
        
        return recommendations
    
    def _create_liquidity_improvement_recommendation(self) -> PortfolioRecommendation:
        """Create liquidity improvement recommendation"""
        return PortfolioRecommendation(
            recommendation_id=f"liquidity_{uuid.uuid4().hex[:8]}",
            type=RecommendationType.OPTIMIZE,
            priority=Priority.LOW,
            title="Improve Portfolio Liquidity",
            description="Portfolio liquidity score is below optimal levels",
            rationale="Better liquidity provides flexibility for rebalancing and opportunities",
            implementation_steps=[
                "Focus on large-cap, actively traded stocks",
                "Consider liquid ETFs for sector exposure",
                "Avoid illiquid small-cap or penny stocks",
                "Maintain some cash allocation for opportunities"
            ],
            expected_impact="Improve portfolio flexibility and trading efficiency",
            confidence_score=0.8,
            timeframe="Ongoing"
        )
    
    def _process_ai_recommendations(self, ai_recommendations: List[Dict[str, Any]]) -> List[PortfolioRecommendation]:
        """Process and structure AI-generated recommendations"""
        processed_recs = []
        
        try:
            for ai_rec in ai_recommendations:
                # Extract information from AI recommendation
                title = ai_rec.get('title', 'AI Recommendation')[:200]
                description = ai_rec.get('description', '')[:1000]
                rationale = ai_rec.get('rationale', 'AI-generated recommendation')[:1500]
                
                # Determine recommendation type
                rec_type = self._determine_recommendation_type(title, description)
                
                # Determine priority
                priority = self._determine_priority(ai_rec.get('priority', 'medium'))
                
                # Extract implementation steps
                steps = ai_rec.get('implementation_steps', [])
                if isinstance(steps, str):
                    steps = [steps]
                
                processed_rec = PortfolioRecommendation(
                    recommendation_id=f"ai_{uuid.uuid4().hex[:8]}",
                    type=rec_type,
                    priority=priority,
                    title=title,
                    description=description,
                    rationale=rationale,
                    implementation_steps=steps[:5],  # Limit to 5 steps
                    expected_impact=ai_rec.get('expected_impact', 'Improve portfolio performance'),
                    confidence_score=float(ai_rec.get('confidence_score', 0.7)),
                    risk_impact=ai_rec.get('risk_impact'),
                    timeframe=ai_rec.get('timeframe', '1-3 months')
                )
                
                processed_recs.append(processed_rec)
                
        except Exception as e:
            logger.warning(f"Failed to process AI recommendation: {e}")
        
        return processed_recs
    
    def _determine_recommendation_type(self, title: str, description: str) -> RecommendationType:
        """Determine recommendation type from title and description"""
        text = (title + " " + description).lower()
        
        if any(word in text for word in ['rebalance', 'reduce', 'trim', 'allocation']):
            return RecommendationType.REBALANCE
        elif any(word in text for word in ['diversify', 'sector', 'spread']):
            return RecommendationType.DIVERSIFY
        elif any(word in text for word in ['risk', 'volatility', 'stop-loss']):
            return RecommendationType.RISK_MANAGEMENT
        elif any(word in text for word in ['performance', 'return', 'growth']):
            return RecommendationType.PERFORMANCE
        else:
            return RecommendationType.OPTIMIZE
    
    def _determine_priority(self, priority_str: str) -> Priority:
        """Determine priority from string"""
        priority_str = priority_str.lower()
        if priority_str in ['high', 'urgent', 'critical']:
            return Priority.HIGH
        elif priority_str in ['low', 'minor', 'optional']:
            return Priority.LOW
        else:
            return Priority.MEDIUM
    
    def _prioritize_recommendations(self, recommendations: List[PortfolioRecommendation]) -> List[PortfolioRecommendation]:
        """Prioritize recommendations by importance and confidence"""
        
        priority_weights = {
            Priority.HIGH: 3,
            Priority.MEDIUM: 2,
            Priority.LOW: 1
        }
        
        def recommendation_score(rec):
            priority_score = priority_weights.get(rec.priority, 1)
            confidence_score = rec.confidence_score
            return priority_score * confidence_score
        
        return sorted(recommendations, key=recommendation_score, reverse=True)