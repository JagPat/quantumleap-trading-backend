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
from .models import (
    AnalysisRequest, AnalysisResponse, AnalysisType,
    TradingSignal, SignalType, AIPreferences
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
        
    async def generate_portfolio_analysis(
        self, 
        user_id: str, 
        portfolio_data: Dict[str, Any]
    ) -> AnalysisResponse:
        """Generate comprehensive portfolio analysis with diversification metrics"""
        
        try:
            logger.info(f"Starting portfolio analysis for user {user_id}")
            
            # Get user preferences for provider selection
            user_preferences = await self.get_user_preferences(user_id)
            
            # Build analysis context
            analysis_context = await self.build_portfolio_analysis_context(portfolio_data)
            
            # Create analysis prompt
            analysis_prompt = self.build_portfolio_analysis_prompt(portfolio_data, analysis_context)
            
            # Select optimal provider for portfolio analysis
            provider = await self.orchestrator.select_optimal_provider("portfolio_analysis", user_preferences)
            
            # Generate analysis using AI
            ai_response = await provider.generate_analysis(analysis_prompt, portfolio_data)
            
            # Process and structure the analysis results
            analysis_results = await self.process_portfolio_analysis_results(ai_response, portfolio_data)
            
            # Store analysis results
            await self.store_analysis_result(
                user_id, 
                AnalysisType.PORTFOLIO, 
                [], 
                portfolio_data, 
                analysis_results, 
                provider.provider_name,
                analysis_results.get("confidence_score", 0.8)
            )
            
            return AnalysisResponse(
                status="success",
                analysis_type=AnalysisType.PORTFOLIO,
                symbols=[],
                results=analysis_results,
                confidence_score=analysis_results.get("confidence_score", 0.8),
                provider_used=provider.provider_name,
                created_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Portfolio analysis failed for user {user_id}: {e}")
            return AnalysisResponse(
                status="error",
                analysis_type=AnalysisType.PORTFOLIO,
                symbols=[],
                results={"error": str(e), "message": "Portfolio analysis failed"},
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