"""
AI Engine Data Preprocessor

Cleans and formats portfolio/market data into AI-friendly prompt formats.
Isolates data preparation logic from AI provider specifics.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class DataPreprocessor:
    """
    Preprocesses raw market and portfolio data for AI consumption.
    
    Responsibilities:
    - Clean and normalize portfolio data
    - Format market data for analysis
    - Generate context-rich prompts
    - Handle data validation and sanitization
    """
    
    def __init__(self):
        self.supported_timeframes = ["1d", "1w", "1m", "3m", "6m", "1y"]
    
    def prepare_portfolio_context(self, portfolio_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """
        Prepare portfolio data for AI analysis.
        
        Args:
            portfolio_data: Raw portfolio data from backend
            user_id: User identifier
            
        Returns:
            Cleaned and structured portfolio context
        """
        try:
            holdings = portfolio_data.get("holdings", [])
            positions = portfolio_data.get("positions", [])
            summary = portfolio_data.get("summary", {})
            
            # Extract key portfolio metrics
            total_value = summary.get("current_value", 0)
            total_pnl = summary.get("total_pnl", 0)
            day_pnl = summary.get("day_pnl", 0)
            
            # Analyze holdings composition
            holdings_analysis = self._analyze_holdings(holdings)
            positions_analysis = self._analyze_positions(positions)
            
            context = {
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "portfolio_summary": {
                    "total_value": total_value,
                    "total_pnl": total_pnl,
                    "total_pnl_percentage": (total_pnl / total_value * 100) if total_value > 0 else 0,
                    "day_pnl": day_pnl,
                    "holdings_count": len(holdings),
                    "positions_count": len(positions)
                },
                "holdings_analysis": holdings_analysis,
                "positions_analysis": positions_analysis,
                "risk_metrics": self._calculate_risk_metrics(holdings, positions)
            }
            
            logger.info(f"Prepared portfolio context for user {user_id}: {total_value:.2f} total value")
            return context
            
        except Exception as e:
            logger.error(f"Error preparing portfolio context: {str(e)}")
            raise
    
    def prepare_market_context(self, symbols: List[str], timeframe: str = "1d") -> Dict[str, Any]:
        """
        Prepare market data context for AI analysis.
        
        Args:
            symbols: List of stock symbols
            timeframe: Analysis timeframe
            
        Returns:
            Market context data
        """
        try:
            if timeframe not in self.supported_timeframes:
                logger.warning(f"Unsupported timeframe {timeframe}, defaulting to 1d")
                timeframe = "1d"
            
            context = {
                "symbols": symbols,
                "timeframe": timeframe,
                "timestamp": datetime.now().isoformat(),
                "symbol_count": len(symbols),
                "analysis_period": self._get_analysis_period(timeframe)
            }
            
            # Note: In a full implementation, this would fetch real market data
            # For now, we prepare the structure that AI providers expect
            logger.info(f"Prepared market context for {len(symbols)} symbols with {timeframe} timeframe")
            return context
            
        except Exception as e:
            logger.error(f"Error preparing market context: {str(e)}")
            raise
    
    def generate_analysis_prompt(self, context: Dict[str, Any], analysis_type: str, 
                                additional_context: Optional[str] = None) -> str:
        """
        Generate AI prompt for market analysis.
        
        Args:
            context: Prepared data context
            analysis_type: Type of analysis requested
            additional_context: Additional user-provided context
            
        Returns:
            Formatted prompt string
        """
        try:
            base_prompt = f"""
You are an expert financial analyst. Analyze the following portfolio and market data to provide {analysis_type} insights.

PORTFOLIO CONTEXT:
{json.dumps(context, indent=2)}

ANALYSIS REQUESTED: {analysis_type}

Please provide:
1. Key insights and observations
2. Specific recommendations
3. Risk assessment
4. Confidence level in your analysis

"""
            
            if additional_context:
                base_prompt += f"\nADDITIONAL CONTEXT:\n{additional_context}\n"
            
            base_prompt += "\nProvide your analysis in a structured format with clear reasoning."
            
            logger.debug(f"Generated {analysis_type} prompt with context size: {len(str(context))}")
            return base_prompt
            
        except Exception as e:
            logger.error(f"Error generating analysis prompt: {str(e)}")
            raise
    
    def generate_strategy_prompt(self, strategy_description: str, portfolio_context: Dict[str, Any],
                               risk_tolerance: str = "medium") -> str:
        """
        Generate AI prompt for strategy creation.
        
        Args:
            strategy_description: User's natural language strategy description
            portfolio_context: Current portfolio context
            risk_tolerance: Risk tolerance level
            
        Returns:
            Formatted strategy generation prompt
        """
        try:
            prompt = f"""
You are an expert trading strategy developer. Create a detailed, executable trading strategy based on the user's description.

USER STRATEGY REQUEST:
"{strategy_description}"

CURRENT PORTFOLIO CONTEXT:
{json.dumps(portfolio_context, indent=2)}

RISK TOLERANCE: {risk_tolerance}

Please provide a comprehensive strategy that includes:
1. Strategy name and description
2. Entry and exit conditions
3. Position sizing rules
4. Risk management measures
5. Expected timeframe
6. Key performance indicators
7. Implementation steps

Ensure the strategy is:
- Clearly defined and executable
- Appropriate for the user's risk tolerance
- Compatible with their current portfolio
- Based on sound financial principles

Format your response as a structured JSON object that can be used programmatically.
"""
            
            logger.debug(f"Generated strategy prompt for risk tolerance: {risk_tolerance}")
            return prompt
            
        except Exception as e:
            logger.error(f"Error generating strategy prompt: {str(e)}")
            raise
    
    def _analyze_holdings(self, holdings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze portfolio holdings composition"""
        if not holdings:
            return {"total_holdings": 0, "sectors": {}, "top_holdings": []}
        
        total_value = sum(h.get("current_value", 0) for h in holdings)
        
        # Sort by current value
        sorted_holdings = sorted(holdings, key=lambda x: x.get("current_value", 0), reverse=True)
        top_holdings = sorted_holdings[:5]  # Top 5 holdings
        
        return {
            "total_holdings": len(holdings),
            "total_value": total_value,
            "top_holdings": [
                {
                    "symbol": h.get("tradingsymbol", ""),
                    "value": h.get("current_value", 0),
                    "percentage": (h.get("current_value", 0) / total_value * 100) if total_value > 0 else 0
                }
                for h in top_holdings
            ],
            "concentration_risk": (top_holdings[0].get("current_value", 0) / total_value * 100) if total_value > 0 and top_holdings else 0
        }
    
    def _analyze_positions(self, positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze current day positions"""
        if not positions:
            return {"total_positions": 0, "net_pnl": 0}
        
        total_pnl = sum(p.get("pnl", 0) for p in positions)
        
        return {
            "total_positions": len(positions),
            "net_pnl": total_pnl,
            "winning_positions": len([p for p in positions if p.get("pnl", 0) > 0]),
            "losing_positions": len([p for p in positions if p.get("pnl", 0) < 0])
        }
    
    def _calculate_risk_metrics(self, holdings: List[Dict[str, Any]], 
                              positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate basic risk metrics"""
        total_value = sum(h.get("current_value", 0) for h in holdings)
        
        if total_value == 0:
            return {"diversification_score": 0, "risk_level": "unknown"}
        
        # Simple diversification score based on number of holdings
        diversification_score = min(len(holdings) / 10, 1.0)  # Normalize to 0-1
        
        return {
            "diversification_score": diversification_score,
            "risk_level": "low" if diversification_score > 0.8 else "medium" if diversification_score > 0.5 else "high"
        }
    
    def _get_analysis_period(self, timeframe: str) -> str:
        """Convert timeframe to human-readable analysis period"""
        period_map = {
            "1d": "1 day",
            "1w": "1 week", 
            "1m": "1 month",
            "3m": "3 months",
            "6m": "6 months",
            "1y": "1 year"
        }
        return period_map.get(timeframe, "1 day") 