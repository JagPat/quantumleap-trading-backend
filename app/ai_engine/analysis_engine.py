"""
Analysis Engine
Advanced trading analysis capabilities including portfolio, market sentiment, and technical analysis
"""
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import sqlite3
import asyncio
from .orchestrator import AIOrchestrator
from .portfolio_analyzer import PortfolioAnalyzer
from .recommendation_engine import RecommendationEngine
from .models import (
    AnalysisRequest, AnalysisResponse, AnalysisType,
    TradingSignal, SignalType, AIPreferences
)
from .portfolio_models import (
    PortfolioAnalysisResult, PortfolioAnalysisResponse,
    MarketContext
)
from ..core.config import settings
from ..database.service import get_db_connection

logger = logging.getLogger(__name__)

class AnalysisEngine:
    """
    Core analysis engine for portfolio analysis, market sentiment, and technical analysis
    """
    
    def __init__(self):
        self.orchestrator = AIOrchestrator()
        self.portfolio_analyzer = PortfolioAnalyzer()
        self.recommendation_engine = RecommendationEngine()
        
    async def generate_portfolio_analysis(
        self, 
        user_id: str, 
        portfolio_data: Dict[str, Any]
    ) -> AnalysisResponse:
        """Generate comprehensive portfolio analysis with AI-powered insights"""
        
        start_time = datetime.now()
        analysis_id = f"analysis_{user_id}_{int(start_time.timestamp())}"
        
        try:
            logger.info(f"Starting comprehensive portfolio analysis for user {user_id}")
            
            # Step 1: Validate portfolio data
            validation_result = self.portfolio_analyzer.validate_portfolio_data(portfolio_data)
            if not validation_result.is_valid:
                return AnalysisResponse(
                    status="error",
                    analysis_type=AnalysisType.PORTFOLIO,
                    symbols=[],
                    results={
                        "error": "Portfolio data validation failed",
                        "validation_errors": validation_result.errors,
                        "warnings": validation_result.warnings
                    },
                    confidence_score=0.0,
                    provider_used="none",
                    created_at=datetime.now()
                )
            
            # Step 2: Calculate portfolio health score
            health_result = self.portfolio_analyzer.calculate_portfolio_health(portfolio_data)
            if not health_result.success:
                logger.error(f"Health calculation failed: {health_result.error_message}")
                health_score = None
            else:
                health_score = health_result.result
            
            # Step 3: Calculate diversification metrics
            diversification_result = self.portfolio_analyzer.calculate_diversification_metrics(portfolio_data)
            if not diversification_result.success:
                logger.error(f"Diversification calculation failed: {diversification_result.error_message}")
                diversification_metrics = None
            else:
                diversification_metrics = diversification_result.result
            
            # Step 4: Calculate risk analysis
            market_context = await self.get_market_context()
            risk_result = self.portfolio_analyzer.calculate_risk_analysis(portfolio_data, market_context)
            if not risk_result.success:
                logger.error(f"Risk analysis failed: {risk_result.error_message}")
                risk_analysis = None
            else:
                risk_analysis = risk_result.result
            
            # Step 5: Calculate performance metrics
            performance_result = self.portfolio_analyzer.calculate_performance_metrics(portfolio_data)
            if not performance_result.success:
                logger.error(f"Performance calculation failed: {performance_result.error_message}")
                performance_metrics = None
            else:
                performance_metrics = performance_result.result
            
            # Step 6: Generate AI-powered recommendations
            ai_recommendations = []
            provider_used = "rule_based"
            
            try:
                user_preferences = await self.get_user_preferences(user_id)
                if user_preferences:
                    await self.orchestrator.initialize_providers(
                        self._convert_to_ai_preferences(user_id, user_preferences)
                    )
                    
                    provider = await self.orchestrator.select_optimal_provider("portfolio_optimization", user_preferences)
                    if provider:
                        ai_recommendations = await self._generate_ai_recommendations(
                            provider, portfolio_data, health_score, risk_analysis, diversification_metrics
                        )
                        provider_used = provider.provider_name
                        logger.info(f"Generated AI recommendations using {provider_used}")
            except Exception as e:
                logger.warning(f"AI recommendation generation failed, using rule-based only: {e}")
            
            # Step 7: Generate comprehensive recommendations
            if health_score and risk_analysis and diversification_metrics and performance_metrics:
                rec_result = self.recommendation_engine.generate_recommendations(
                    portfolio_data, health_score, risk_analysis, 
                    diversification_metrics, performance_metrics, ai_recommendations
                )
                
                if rec_result.success:
                    recommendations = rec_result.result
                else:
                    logger.error(f"Recommendation generation failed: {rec_result.error_message}")
                    recommendations = []
            else:
                recommendations = []
            
            # Step 8: Generate key insights
            key_insights = self._generate_key_insights(
                health_score, risk_analysis, diversification_metrics, performance_metrics
            )
            
            # Step 9: Calculate processing time and confidence
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            confidence_score = self._calculate_overall_confidence(
                health_score, risk_analysis, diversification_metrics, performance_metrics
            )
            
            # Step 10: Create comprehensive analysis result
            analysis_result = {
                "analysis_id": analysis_id,
                "portfolio_health": health_score.dict() if health_score else None,
                "risk_analysis": risk_analysis.dict() if risk_analysis else None,
                "diversification_analysis": diversification_metrics.dict() if diversification_metrics else None,
                "performance_metrics": performance_metrics.dict() if performance_metrics else None,
                "recommendations": [rec.dict() for rec in recommendations],
                "key_insights": key_insights,
                "market_context": market_context,
                "analysis_metadata": {
                    "validation_warnings": validation_result.warnings,
                    "processing_time_ms": processing_time,
                    "components_calculated": {
                        "health_score": health_score is not None,
                        "risk_analysis": risk_analysis is not None,
                        "diversification": diversification_metrics is not None,
                        "performance": performance_metrics is not None,
                        "recommendations": len(recommendations) > 0
                    }
                },
                "confidence_score": confidence_score,
                "generated_at": datetime.now().isoformat()
            }
            
            # Step 11: Store analysis results
            await self.store_analysis_result(
                user_id, 
                AnalysisType.PORTFOLIO, 
                [], 
                portfolio_data, 
                analysis_result, 
                provider_used,
                confidence_score
            )
            
            logger.info(f"Portfolio analysis completed for user {user_id} in {processing_time}ms")
            
            return AnalysisResponse(
                status="success",
                analysis_type=AnalysisType.PORTFOLIO,
                symbols=[],
                results=analysis_result,
                confidence_score=confidence_score,
                provider_used=provider_used,
                created_at=datetime.now()
            )
            
        except Exception as e:
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"Portfolio analysis failed for user {user_id} after {processing_time}ms: {e}")
            
            return AnalysisResponse(
                status="error",
                analysis_type=AnalysisType.PORTFOLIO,
                symbols=[],
                results={
                    "error": str(e), 
                    "message": "Portfolio analysis failed",
                    "analysis_id": analysis_id,
                    "processing_time_ms": processing_time
                },
                confidence_score=0.0,
                provider_used="none",
                created_at=datetime.now()
            )   
 
    async def build_portfolio_analysis_context(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build context for portfolio analysis"""
        context = {}
        
        try:
            # Calculate basic portfolio metrics
            total_value = portfolio_data.get("total_value", 0)
            holdings = portfolio_data.get("holdings", [])
            
            if holdings:
                # Calculate diversification metrics
                context["diversification"] = await self.calculate_diversification_metrics(holdings)
                
                # Calculate sector allocation
                context["sector_allocation"] = await self.calculate_sector_allocation(holdings)
                
                # Calculate risk metrics
                context["risk_metrics"] = await self.calculate_risk_metrics(holdings, total_value)
                
                # Get market benchmarks
                context["benchmarks"] = await self.get_market_benchmarks()
            
        except Exception as e:
            logger.warning(f"Failed to build complete portfolio analysis context: {e}")
        
        return context
    
    def build_portfolio_analysis_prompt(self, portfolio_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Build AI prompt for portfolio analysis"""
        
        holdings = portfolio_data.get("holdings", [])
        total_value = portfolio_data.get("total_value", 0)
        
        prompt = f"""
        Analyze the following investment portfolio and provide comprehensive insights:

        PORTFOLIO OVERVIEW:
        - Total Portfolio Value: ₹{total_value:,.2f}
        - Number of Holdings: {len(holdings)}
        - Last Updated: {portfolio_data.get('last_updated', 'Unknown')}

        HOLDINGS BREAKDOWN:
        """
        
        for holding in holdings[:10]:  # Limit to top 10 for prompt length
            prompt += f"""
        - {holding.get('symbol', 'Unknown')}: {holding.get('quantity', 0)} shares
          Current Value: ₹{holding.get('current_value', 0):,.2f}
          Allocation: {holding.get('allocation_percentage', 0):.1f}%
        """
        
        if context.get("diversification"):
            prompt += f"""
        
        DIVERSIFICATION METRICS:
        - Number of Sectors: {context['diversification'].get('sector_count', 0)}
        - Largest Position: {context['diversification'].get('largest_position_pct', 0):.1f}%
        - Top 5 Concentration: {context['diversification'].get('top5_concentration', 0):.1f}%
        """
        
        if context.get("sector_allocation"):
            prompt += f"""
        
        SECTOR ALLOCATION:
        """
            for sector, allocation in context['sector_allocation'].items():
                prompt += f"- {sector}: {allocation:.1f}%\n"
        
        prompt += """
        
        ANALYSIS REQUIREMENTS:
        Please provide a comprehensive analysis covering:

        1. DIVERSIFICATION ANALYSIS:
           - Assess portfolio diversification across sectors and stocks
           - Identify concentration risks and over-exposures
           - Recommend optimal allocation adjustments

        2. RISK ASSESSMENT:
           - Evaluate overall portfolio risk level
           - Identify high-risk positions
           - Assess correlation risks between holdings

        3. PERFORMANCE EVALUATION:
           - Compare performance against market benchmarks
           - Identify top and bottom performers
           - Analyze risk-adjusted returns

        4. OPTIMIZATION RECOMMENDATIONS:
           - Suggest specific buy/sell actions
           - Recommend portfolio rebalancing strategies
           - Identify underrepresented sectors or opportunities

        5. RISK MANAGEMENT:
           - Suggest stop-loss levels for high-risk positions
           - Recommend position sizing adjustments
           - Identify hedging opportunities

        Please provide specific, actionable recommendations with reasoning.
        Format the response as structured JSON with clear sections for each analysis area.
        """
        
        return prompt 
    
    async def process_portfolio_analysis_results(self, ai_response: str, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and structure AI analysis results"""
        
        try:
            # Try to parse JSON response
            if ai_response.strip().startswith('{'):
                analysis_data = json.loads(ai_response)
            else:
                # If not JSON, structure the text response
                analysis_data = {
                    "summary": ai_response,
                    "recommendations": [],
                    "risk_assessment": {},
                    "diversification_score": 0.7,
                    "confidence_score": 0.8
                }
            
            # Add calculated metrics
            analysis_data["portfolio_metrics"] = {
                "total_value": portfolio_data.get("total_value", 0),
                "holdings_count": len(portfolio_data.get("holdings", [])),
                "analysis_timestamp": datetime.now().isoformat()
            }
            
            # Ensure required fields
            if "confidence_score" not in analysis_data:
                analysis_data["confidence_score"] = 0.8
            
            return analysis_data
            
        except json.JSONDecodeError:
            # Fallback for non-JSON responses
            return {
                "summary": ai_response,
                "recommendations": ["Review portfolio diversification", "Consider rebalancing"],
                "risk_assessment": {"level": "medium"},
                "confidence_score": 0.7,
                "portfolio_metrics": {
                    "total_value": portfolio_data.get("total_value", 0),
                    "holdings_count": len(portfolio_data.get("holdings", [])),
                    "analysis_timestamp": datetime.now().isoformat()
                }
            }
    
    async def calculate_diversification_metrics(self, holdings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate portfolio diversification metrics"""
        
        try:
            if not holdings:
                return {}
            
            # Calculate position sizes
            total_value = sum(holding.get("current_value", 0) for holding in holdings)
            
            if total_value == 0:
                return {}
            
            # Calculate largest position percentage
            largest_position = max(holding.get("current_value", 0) for holding in holdings)
            largest_position_pct = (largest_position / total_value) * 100
            
            # Calculate top 5 concentration
            sorted_holdings = sorted(holdings, key=lambda x: x.get("current_value", 0), reverse=True)
            top5_value = sum(holding.get("current_value", 0) for holding in sorted_holdings[:5])
            top5_concentration = (top5_value / total_value) * 100
            
            # Count unique sectors (simplified - would need real sector data)
            sectors = set()
            for holding in holdings:
                # This would need real sector mapping
                symbol = holding.get("symbol", "")
                if symbol:
                    sectors.add(self.get_sector_for_symbol(symbol))
            
            return {
                "sector_count": len(sectors),
                "largest_position_pct": largest_position_pct,
                "top5_concentration": top5_concentration,
                "holdings_count": len(holdings),
                "diversification_score": min(100 - largest_position_pct, 100)
            }
            
        except Exception as e:
            logger.warning(f"Failed to calculate diversification metrics: {e}")
            return {}
    
    def get_sector_for_symbol(self, symbol: str) -> str:
        """Get sector for a stock symbol (simplified mapping)"""
        
        # This is a simplified sector mapping - in production, you'd use a real data source
        sector_mapping = {
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
            "WIPRO": "Technology"
        }
        
        return sector_mapping.get(symbol.upper(), "Other")    

    async def calculate_sector_allocation(self, holdings: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate sector allocation percentages"""
        
        try:
            sector_values = {}
            total_value = sum(holding.get("current_value", 0) for holding in holdings)
            
            if total_value == 0:
                return {}
            
            for holding in holdings:
                sector = self.get_sector_for_symbol(holding.get("symbol", ""))
                value = holding.get("current_value", 0)
                
                if sector in sector_values:
                    sector_values[sector] += value
                else:
                    sector_values[sector] = value
            
            # Convert to percentages
            sector_allocation = {}
            for sector, value in sector_values.items():
                sector_allocation[sector] = (value / total_value) * 100
            
            return sector_allocation
            
        except Exception as e:
            logger.warning(f"Failed to calculate sector allocation: {e}")
            return {}
    
    async def calculate_risk_metrics(self, holdings: List[Dict[str, Any]], total_value: float) -> Dict[str, Any]:
        """Calculate portfolio risk metrics"""
        
        try:
            if not holdings or total_value == 0:
                return {}
            
            # Calculate concentration risk
            max_position_pct = 0
            high_risk_positions = 0
            
            for holding in holdings:
                position_pct = (holding.get("current_value", 0) / total_value) * 100
                max_position_pct = max(max_position_pct, position_pct)
                
                if position_pct > 10:  # Positions > 10% considered high concentration
                    high_risk_positions += 1
            
            # Simple risk scoring
            risk_score = min(max_position_pct / 5, 10)  # Scale 0-10
            
            return {
                "max_position_percentage": max_position_pct,
                "high_concentration_positions": high_risk_positions,
                "risk_score": risk_score,
                "risk_level": "High" if risk_score > 7 else "Medium" if risk_score > 4 else "Low"
            }
            
        except Exception as e:
            logger.warning(f"Failed to calculate risk metrics: {e}")
            return {}
    
    async def get_market_benchmarks(self) -> Dict[str, Any]:
        """Get market benchmark data for comparison"""
        
        try:
            # This would integrate with real market data APIs
            # For now, return placeholder data
            return {
                "nifty50": {
                    "current_value": 19500,
                    "change_percent": 0.5,
                    "ytd_return": 12.5
                },
                "sensex": {
                    "current_value": 65000,
                    "change_percent": 0.3,
                    "ytd_return": 11.8
                }
            }
            
        except Exception as e:
            logger.warning(f"Failed to get market benchmarks: {e}")
            return {}
    
    async def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's AI preferences"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT preferred_provider, provider_priorities, cost_limits, 
                       risk_tolerance, trading_style, openai_api_key, 
                       claude_api_key, gemini_api_key, grok_api_key
                FROM ai_user_preferences
                WHERE user_id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    "preferred_ai_provider": row[0] or "auto",
                    "provider_priorities": json.loads(row[1]) if row[1] else None,
                    "cost_limits": json.loads(row[2]) if row[2] else None,
                    "risk_tolerance": row[3] or "medium",
                    "trading_style": row[4] or "balanced",
                    "openai_api_key": row[5],
                    "claude_api_key": row[6],
                    "gemini_api_key": row[7],
                    "grok_api_key": row[8]
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get preferences for user {user_id}: {e}")
            return None
    
    async def store_analysis_result(
        self,
        user_id: str,
        analysis_type: AnalysisType,
        symbols: List[str],
        input_data: Dict[str, Any],
        analysis_result: Dict[str, Any],
        provider_used: str,
        confidence_score: float
    ):
        """Store analysis results in database"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO ai_analysis_results 
                (user_id, analysis_type, symbols, input_data, analysis_result, 
                 provider_used, confidence_score, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                analysis_type.value,
                json.dumps(symbols),
                json.dumps(input_data),
                json.dumps(analysis_result),
                provider_used,
                confidence_score,
                datetime.now()
            ))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Stored analysis result for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to store analysis result: {e}")    

    async def get_latest_analysis(self, user_id: str, analysis_type: AnalysisType) -> Optional[Dict[str, Any]]:
        """Get the latest analysis result for a user"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT analysis_result, provider_used, confidence_score, created_at
                FROM ai_analysis_results
                WHERE user_id = ? AND analysis_type = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (user_id, analysis_type.value))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    "analysis_result": json.loads(row[0]),
                    "provider_used": row[1],
                    "confidence_score": row[2],
                    "created_at": row[3]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get latest analysis: {e}")
            return None
    
    async def initialize_orchestrator(self, user_id: str) -> bool:
        """Initialize the AI orchestrator with user preferences"""
        try:
            # Get user preferences
            preferences_dict = await self.get_user_preferences(user_id)
            if not preferences_dict:
                return False
            
            # Convert to AIPreferences model
            preferences = AIPreferences(
                user_id=user_id,
                preferred_ai_provider=preferences_dict.get("preferred_ai_provider", "auto"),
                openai_api_key=preferences_dict.get("openai_api_key"),
                claude_api_key=preferences_dict.get("claude_api_key"),
                gemini_api_key=preferences_dict.get("gemini_api_key"),
                grok_api_key=preferences_dict.get("grok_api_key"),
                provider_priorities=preferences_dict.get("provider_priorities"),
                cost_limits=preferences_dict.get("cost_limits"),
                risk_tolerance=preferences_dict.get("risk_tolerance", "medium"),
                trading_style=preferences_dict.get("trading_style", "balanced")
            )
            
            # Initialize providers in orchestrator
            await self.orchestrator.initialize_providers(preferences)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator for user {user_id}: {e}")
            return False
    
    async def get_market_context(self) -> Dict[str, Any]:
        """Get current market context for analysis"""
        try:
            # This would integrate with real market data APIs
            # For now, return reasonable default context
            return {
                "market_sentiment": "neutral",
                "volatility_index": 0.45,
                "market_trend": "sideways",
                "nifty50_change": 0.2,
                "sector_performance": {
                    "Technology": 1.2,
                    "Banking": -0.5,
                    "Energy": 0.8,
                    "Consumer Goods": 0.3,
                    "Pharma": -0.2
                },
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            logger.warning(f"Failed to get market context: {e}")
            return {"market_sentiment": "neutral", "volatility_index": 0.5}
    
    async def _generate_ai_recommendations(
        self, 
        provider, 
        portfolio_data: Dict[str, Any],
        health_score,
        risk_analysis,
        diversification_metrics
    ) -> List[Dict[str, Any]]:
        """Generate AI-powered portfolio recommendations"""
        try:
            # Create comprehensive prompt for AI analysis
            prompt = self._create_ai_recommendation_prompt(
                portfolio_data, health_score, risk_analysis, diversification_metrics
            )
            
            # Generate AI response
            response = await provider.generate_analysis(prompt, portfolio_data)
            
            if response and hasattr(response, 'analysis'):
                # Parse AI recommendations
                return self._parse_ai_recommendations(response.analysis)
            
            return []
            
        except Exception as e:
            logger.error(f"AI recommendation generation failed: {e}")
            return []
    
    def _create_ai_recommendation_prompt(
        self, 
        portfolio_data: Dict[str, Any],
        health_score,
        risk_analysis,
        diversification_metrics
    ) -> str:
        """Create comprehensive prompt for AI portfolio recommendations"""
        
        holdings = portfolio_data.get('holdings', [])
        total_value = sum(abs(float(h.get('current_value', 0))) for h in holdings)
        
        prompt = f"""
PORTFOLIO OPTIMIZATION ANALYSIS

You are an expert portfolio manager analyzing a client's investment portfolio.
Provide specific, actionable recommendations for optimization.

PORTFOLIO OVERVIEW:
- Total Holdings: {len(holdings)}
- Total Value: ₹{total_value:,.2f}
- Health Score: {health_score.overall_score:.1f}/100 (Grade: {health_score.grade.value}) if health_score else "N/A"

CURRENT ANALYSIS:
"""
        
        if health_score:
            prompt += f"""
HEALTH BREAKDOWN:
- Performance: {health_score.performance_score:.1f}/100
- Diversification: {health_score.diversification_score:.1f}/100
- Risk Management: {health_score.risk_score:.1f}/100
- Liquidity: {health_score.liquidity_score:.1f}/100

IMPROVEMENT AREAS: {', '.join(health_score.improvement_areas)}
STRENGTHS: {', '.join(health_score.strengths)}
"""
        
        if risk_analysis:
            prompt += f"""
RISK ANALYSIS:
- Overall Risk Level: {risk_analysis.overall_risk_level.value}
- Concentration Risk: {risk_analysis.concentration_risk:.2f}
- Overexposed Sectors: {', '.join(risk_analysis.overexposed_sectors.keys())}
"""
        
        if diversification_metrics:
            prompt += f"""
DIVERSIFICATION:
- Sector Count: {diversification_metrics.sector_count}
- Largest Position: {diversification_metrics.largest_position_pct:.1f}%
- Top 5 Concentration: {diversification_metrics.top5_concentration:.1f}%
"""
        
        # Add top holdings
        prompt += "\nTOP HOLDINGS:\n"
        sorted_holdings = sorted(holdings, key=lambda x: abs(float(x.get('current_value', 0))), reverse=True)
        for i, holding in enumerate(sorted_holdings[:8]):
            symbol = holding.get('symbol', 'Unknown')
            value = abs(float(holding.get('current_value', 0)))
            allocation = (value / total_value) * 100 if total_value > 0 else 0
            pnl = float(holding.get('pnl', 0))
            pnl_pct = (pnl / abs(float(holding.get('investment_value', 1)))) * 100
            
            prompt += f"{i+1}. {symbol}: {allocation:.1f}% (P&L: {pnl_pct:+.1f}%)\n"
        
        prompt += """

ANALYSIS REQUIRED:
Provide 3-5 specific, actionable recommendations in JSON format:

{
  "recommendations": [
    {
      "title": "Clear, actionable title",
      "description": "Detailed description of the recommendation",
      "rationale": "Why this recommendation is important",
      "implementation_steps": ["Step 1", "Step 2", "Step 3"],
      "expected_impact": "Expected outcome",
      "confidence_score": 0.8,
      "priority": "high/medium/low",
      "timeframe": "1-3 months"
    }
  ]
}

Focus on:
1. Risk reduction opportunities
2. Diversification improvements  
3. Performance optimization
4. Rebalancing suggestions
5. Specific actionable steps

Provide practical advice that can be executed immediately.
"""
        
        return prompt
    
    def _parse_ai_recommendations(self, ai_response: str) -> List[Dict[str, Any]]:
        """Parse AI recommendations from response"""
        try:
            # Try to parse JSON response
            if '{' in ai_response and '}' in ai_response:
                # Extract JSON part
                start = ai_response.find('{')
                end = ai_response.rfind('}') + 1
                json_str = ai_response[start:end]
                
                parsed = json.loads(json_str)
                return parsed.get('recommendations', [])
            
            # Fallback: parse text recommendations
            return self._parse_text_recommendations(ai_response)
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI recommendations as JSON: {e}")
            return self._parse_text_recommendations(ai_response)
        except Exception as e:
            logger.error(f"Failed to parse AI recommendations: {e}")
            return []
    
    def _parse_text_recommendations(self, text: str) -> List[Dict[str, Any]]:
        """Parse text-based AI recommendations"""
        recommendations = []
        
        try:
            lines = text.split('\n')
            current_rec = None
            
            for line in lines:
                line = line.strip()
                
                # Look for recommendation headers
                if any(line.startswith(prefix) for prefix in ['1.', '2.', '3.', '4.', '5.', '-', '•']):
                    if current_rec:
                        recommendations.append(current_rec)
                    
                    # Extract title
                    title = line
                    for prefix in ['1.', '2.', '3.', '4.', '5.', '-', '•']:
                        title = title.replace(prefix, '').strip()
                    
                    current_rec = {
                        "title": title[:100],
                        "description": title,
                        "rationale": "AI-generated recommendation",
                        "implementation_steps": [],
                        "expected_impact": "Improve portfolio performance",
                        "confidence_score": 0.7,
                        "priority": "medium",
                        "timeframe": "1-3 months"
                    }
                
                elif current_rec and line:
                    # Add content to current recommendation
                    if len(current_rec["description"]) < 500:
                        current_rec["description"] += f" {line}"
                    
                    if 'step' in line.lower() or 'action' in line.lower():
                        current_rec["implementation_steps"].append(line)
            
            # Add final recommendation
            if current_rec:
                recommendations.append(current_rec)
                
        except Exception as e:
            logger.error(f"Failed to parse text recommendations: {e}")
        
        return recommendations
    
    def _generate_key_insights(self, health_score, risk_analysis, diversification_metrics, performance_metrics) -> List[str]:
        """Generate key insights from analysis results"""
        insights = []
        
        try:
            if health_score:
                if health_score.overall_score >= 80:
                    insights.append(f"Portfolio demonstrates strong fundamentals with {health_score.grade.value} grade health score")
                elif health_score.overall_score >= 60:
                    insights.append(f"Portfolio shows moderate health ({health_score.grade.value} grade) with room for optimization")
                else:
                    insights.append(f"Portfolio health needs attention ({health_score.grade.value} grade) - focus on improvement areas")
            
            if risk_analysis:
                if risk_analysis.overall_risk_level.value == "low":
                    insights.append("Risk profile is well-managed with low overall risk exposure")
                elif risk_analysis.overall_risk_level.value == "high":
                    insights.append("High risk exposure detected - consider risk reduction strategies")
                
                if risk_analysis.concentration_risk > 0.7:
                    insights.append("Portfolio shows high concentration risk - diversification recommended")
            
            if diversification_metrics:
                if diversification_metrics.diversification_score > 0.8:
                    insights.append("Excellent portfolio diversification across sectors and holdings")
                elif diversification_metrics.diversification_score < 0.5:
                    insights.append("Limited diversification - consider expanding across sectors")
                
                if diversification_metrics.largest_position_pct > 25:
                    insights.append(f"Largest position represents {diversification_metrics.largest_position_pct:.1f}% - consider rebalancing")
            
            if performance_metrics:
                if performance_metrics.total_return_percentage > 10:
                    insights.append(f"Strong portfolio performance with {performance_metrics.total_return_percentage:.1f}% returns")
                elif performance_metrics.total_return_percentage < -5:
                    insights.append("Portfolio performance needs attention - review underperforming positions")
            
            # Add general insights
            insights.append("Regular portfolio review and rebalancing helps maintain optimal allocation")
            insights.append("Consider market conditions and personal risk tolerance when making changes")
            
        except Exception as e:
            logger.error(f"Failed to generate insights: {e}")
            insights.append("Portfolio analysis completed - review recommendations for optimization opportunities")
        
        return insights[:5]  # Limit to 5 key insights
    
    def _calculate_overall_confidence(self, health_score, risk_analysis, diversification_metrics, performance_metrics) -> float:
        """Calculate overall confidence score for the analysis"""
        try:
            confidence_factors = []
            
            # Data completeness factor
            components_available = sum([
                health_score is not None,
                risk_analysis is not None,
                diversification_metrics is not None,
                performance_metrics is not None
            ])
            data_completeness = components_available / 4.0
            confidence_factors.append(data_completeness * 0.3)
            
            # Analysis quality factor
            if health_score and health_score.overall_score > 0:
                confidence_factors.append(0.25)
            
            if risk_analysis and risk_analysis.overall_risk_score >= 0:
                confidence_factors.append(0.25)
            
            if diversification_metrics and diversification_metrics.diversification_score >= 0:
                confidence_factors.append(0.2)
            
            return min(1.0, sum(confidence_factors))
            
        except Exception:
            return 0.75  # Default confidence
    
    def _convert_to_ai_preferences(self, user_id: str, preferences_dict: Dict[str, Any]):
        """Convert preferences dict to AIPreferences model"""
        try:
            from .models import AIPreferences, RiskTolerance, TradingStyle
            
            return AIPreferences(
                user_id=user_id,
                preferred_ai_provider=preferences_dict.get("preferred_ai_provider", "auto"),
                openai_api_key=preferences_dict.get("openai_api_key"),
                claude_api_key=preferences_dict.get("claude_api_key"),
                gemini_api_key=preferences_dict.get("gemini_api_key"),
                grok_api_key=preferences_dict.get("grok_api_key"),
                provider_priorities=preferences_dict.get("provider_priorities"),
                cost_limits=preferences_dict.get("cost_limits"),
                risk_tolerance=preferences_dict.get("risk_tolerance", "medium"),
                trading_style=preferences_dict.get("trading_style", "balanced")
            )
        except Exception as e:
            logger.error(f"Failed to convert preferences: {e}")
            return None