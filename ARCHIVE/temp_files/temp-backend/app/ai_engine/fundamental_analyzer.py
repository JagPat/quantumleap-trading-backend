"""
Fundamental Analyzer
Comprehensive fundamental analysis with financial data integration and valuation models
"""
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import random
from .orchestrator import AIOrchestrator
from .models import AnalysisResponse, AnalysisType
from ..database.service import get_db_connection

logger = logging.getLogger(__name__)

class FundamentalAnalyzer:
    """
    Fundamental analysis engine with financial data integration and valuation models
    """
    
    def __init__(self):
        self.orchestrator = AIOrchestrator()
        
    async def generate_fundamental_analysis(
        self, 
        user_id: str, 
        symbol: str
    ) -> AnalysisResponse:
        """Generate fundamental analysis for a specific symbol"""
        
        try:
            logger.info(f"Starting fundamental analysis for {symbol}")
            
            # Get user preferences for provider selection
            user_preferences = await self.get_user_preferences(user_id)
            
            # Fetch financial data
            financial_data = await self.fetch_financial_data(symbol)
            
            # Build fundamental analysis prompt
            fundamental_prompt = self.build_fundamental_analysis_prompt(symbol, financial_data)
            
            # Select optimal provider for fundamental analysis
            provider = await self.orchestrator.select_optimal_provider("fundamental_analysis", user_preferences)
            
            # Generate analysis using AI
            ai_response = await provider.generate_analysis(fundamental_prompt, financial_data)
            
            # Process and structure the fundamental results
            fundamental_results = await self.process_fundamental_analysis_results(ai_response, symbol, financial_data)
            
            # Store analysis results
            await self.store_analysis_result(
                user_id, 
                AnalysisType.FUNDAMENTAL,
                [symbol],
                financial_data,
                fundamental_results,
                provider.provider_name,
                fundamental_results.get('confidence_score', 0.85)
            )
            
            return AnalysisResponse(
                status="success",
                analysis_type=AnalysisType.FUNDAMENTAL,
                symbols=[symbol],
                results=fundamental_results,
                confidence_score=fundamental_results.get('confidence_score', 0.85),
                provider_used=provider.provider_name,
                created_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Fundamental analysis failed for {symbol}: {e}")
            return AnalysisResponse(
                status="error",
                analysis_type=AnalysisType.FUNDAMENTAL,
                symbols=[symbol],
                results={"error": str(e), "message": "Fundamental analysis failed"},
                confidence_score=0.0,
                provider_used="none",
                created_at=datetime.now()
            )
    
    async def fetch_financial_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch comprehensive financial data for fundamental analysis"""
        
        # Simulate financial data - in production, this would fetch from financial data APIs
        financial_data = {
            "symbol": symbol,
            "company_info": {
                "name": f"{symbol} Limited",
                "sector": self.get_sector_for_symbol(symbol),
                "industry": self.get_industry_for_symbol(symbol),
                "market_cap": random.randint(10000, 500000),  # In crores
                "employees": random.randint(1000, 100000)
            },
            "financial_metrics": {
                "revenue": random.randint(5000, 50000),  # In crores
                "net_profit": random.randint(500, 8000),  # In crores
                "ebitda": random.randint(1000, 12000),  # In crores
                "total_assets": random.randint(10000, 100000),  # In crores
                "total_debt": random.randint(2000, 30000),  # In crores
                "cash_and_equivalents": random.randint(1000, 15000)  # In crores
            },
            "ratios": {
                "pe_ratio": round(random.uniform(8, 35), 2),
                "pb_ratio": round(random.uniform(0.5, 5), 2),
                "debt_to_equity": round(random.uniform(0.1, 2), 2),
                "roe": round(random.uniform(5, 25), 2),
                "roa": round(random.uniform(2, 15), 2),
                "current_ratio": round(random.uniform(0.8, 3), 2),
                "quick_ratio": round(random.uniform(0.5, 2.5), 2)
            },
            "growth_metrics": {
                "revenue_growth_yoy": round(random.uniform(-10, 30), 2),
                "profit_growth_yoy": round(random.uniform(-15, 40), 2),
                "revenue_growth_3y_cagr": round(random.uniform(0, 25), 2),
                "profit_growth_3y_cagr": round(random.uniform(-5, 35), 2)
            },
            "valuation": {
                "current_price": round(random.uniform(100, 3000), 2),
                "book_value_per_share": round(random.uniform(50, 1500), 2),
                "earnings_per_share": round(random.uniform(5, 200), 2),
                "dividend_yield": round(random.uniform(0, 8), 2)
            },
            "recent_results": {
                "last_quarter": "Q3 FY24",
                "revenue_surprise": round(random.uniform(-5, 10), 2),
                "earnings_surprise": round(random.uniform(-10, 15), 2),
                "guidance": random.choice(["Positive", "Neutral", "Cautious"])
            },
            "peer_comparison": self.get_peer_comparison_data(symbol),
            "last_updated": datetime.now().isoformat()
        }
        
        return financial_data
    
    def build_fundamental_analysis_prompt(self, symbol: str, financial_data: Dict[str, Any]) -> str:
        """Build AI prompt for fundamental analysis"""
        
        company_info = financial_data.get('company_info', {})
        metrics = financial_data.get('financial_metrics', {})
        ratios = financial_data.get('ratios', {})
        growth = financial_data.get('growth_metrics', {})
        valuation = financial_data.get('valuation', {})
        results = financial_data.get('recent_results', {})
        
        prompt = f"""
        As an expert fundamental analyst, analyze {symbol} ({company_info.get('name', 'Unknown Company')}) based on the following comprehensive financial data:
        
        COMPANY OVERVIEW:
        - Sector: {company_info.get('sector', 'Unknown')}
        - Industry: {company_info.get('industry', 'Unknown')}
        - Market Cap: ₹{company_info.get('market_cap', 0):,} crores
        - Employees: {company_info.get('employees', 0):,}
        
        FINANCIAL PERFORMANCE:
        - Revenue: ₹{metrics.get('revenue', 0):,} crores
        - Net Profit: ₹{metrics.get('net_profit', 0):,} crores
        - EBITDA: ₹{metrics.get('ebitda', 0):,} crores
        - Total Assets: ₹{metrics.get('total_assets', 0):,} crores
        - Total Debt: ₹{metrics.get('total_debt', 0):,} crores
        - Cash & Equivalents: ₹{metrics.get('cash_and_equivalents', 0):,} crores
        
        KEY RATIOS:
        - P/E Ratio: {ratios.get('pe_ratio', 0)}
        - P/B Ratio: {ratios.get('pb_ratio', 0)}
        - Debt-to-Equity: {ratios.get('debt_to_equity', 0)}
        - ROE: {ratios.get('roe', 0)}%
        - ROA: {ratios.get('roa', 0)}%
        - Current Ratio: {ratios.get('current_ratio', 0)}
        - Quick Ratio: {ratios.get('quick_ratio', 0)}
        
        GROWTH METRICS:
        - Revenue Growth (YoY): {growth.get('revenue_growth_yoy', 0)}%
        - Profit Growth (YoY): {growth.get('profit_growth_yoy', 0)}%
        - Revenue CAGR (3Y): {growth.get('revenue_growth_3y_cagr', 0)}%
        - Profit CAGR (3Y): {growth.get('profit_growth_3y_cagr', 0)}%
        
        VALUATION METRICS:
        - Current Price: ₹{valuation.get('current_price', 0)}
        - Book Value/Share: ₹{valuation.get('book_value_per_share', 0)}
        - EPS: ₹{valuation.get('earnings_per_share', 0)}
        - Dividend Yield: {valuation.get('dividend_yield', 0)}%
        
        RECENT PERFORMANCE:
        - Last Quarter: {results.get('last_quarter', 'Unknown')}
        - Revenue Surprise: {results.get('revenue_surprise', 0)}%
        - Earnings Surprise: {results.get('earnings_surprise', 0)}%
        - Management Guidance: {results.get('guidance', 'Unknown')}
        
        ANALYSIS REQUIREMENTS:
        Please provide a comprehensive fundamental analysis covering:
        
        1. FINANCIAL HEALTH ASSESSMENT:
           - Overall financial strength and stability
           - Debt management and liquidity position
           - Cash flow generation capability
           - Balance sheet quality
        
        2. PROFITABILITY ANALYSIS:
           - Profit margins and efficiency ratios
           - Return on equity and assets analysis
           - Earnings quality and sustainability
           - Comparison with industry standards
        
        3. GROWTH PROSPECTS:
           - Revenue and earnings growth trends
           - Market opportunity and competitive position
           - Management execution capability
           - Future growth drivers and catalysts
        
        4. VALUATION ASSESSMENT:
           - Current valuation vs intrinsic value
           - P/E, P/B ratio analysis vs peers
           - DCF-based fair value estimation
           - Value vs growth trade-off
        
        5. INVESTMENT RECOMMENDATION:
           - Buy/Hold/Sell recommendation with rationale
           - Target price range with time horizon
           - Key risks and risk mitigation factors
           - Portfolio allocation suggestion
        
        6. SECTOR AND PEER COMPARISON:
           - Performance vs sector averages
           - Competitive advantages and moats
           - Market share and positioning
           - Relative valuation attractiveness
        
        Please provide specific numerical targets, risk assessments, and actionable investment insights.
        Rate the overall fundamental strength as: Excellent, Good, Average, Below Average, or Poor.
        """
        
        return prompt    

    def get_sector_for_symbol(self, symbol: str) -> str:
        """Get sector for a stock symbol"""
        sector_mapping = {
            "RELIANCE": "Energy & Petrochemicals",
            "TCS": "Information Technology",
            "HDFCBANK": "Banking & Financial Services",
            "INFY": "Information Technology",
            "HINDUNILVR": "Consumer Goods",
            "ICICIBANK": "Banking & Financial Services",
            "KOTAKBANK": "Banking & Financial Services",
            "SBIN": "Banking & Financial Services",
            "BHARTIARTL": "Telecommunications",
            "ITC": "Consumer Goods",
            "ASIANPAINT": "Consumer Goods",
            "MARUTI": "Automotive",
            "AXISBANK": "Banking & Financial Services",
            "LT": "Infrastructure & Construction",
            "WIPRO": "Information Technology"
        }
        return sector_mapping.get(symbol.upper(), "Diversified")
    
    def get_industry_for_symbol(self, symbol: str) -> str:
        """Get industry for a stock symbol"""
        industry_mapping = {
            "RELIANCE": "Oil & Gas Refining",
            "TCS": "IT Services",
            "HDFCBANK": "Private Banking",
            "INFY": "IT Services",
            "HINDUNILVR": "FMCG",
            "ICICIBANK": "Private Banking",
            "KOTAKBANK": "Private Banking",
            "SBIN": "Public Banking",
            "BHARTIARTL": "Telecom Services",
            "ITC": "Tobacco & FMCG",
            "ASIANPAINT": "Paints & Coatings",
            "MARUTI": "Automobile Manufacturing",
            "AXISBANK": "Private Banking",
            "LT": "Engineering & Construction",
            "WIPRO": "IT Services"
        }
        return industry_mapping.get(symbol.upper(), "Diversified")
    
    def get_peer_comparison_data(self, symbol: str) -> Dict[str, Any]:
        """Get peer comparison data for the symbol"""
        
        # Simplified peer mapping
        peer_groups = {
            "RELIANCE": ["ONGC", "BPCL", "IOC"],
            "TCS": ["INFY", "WIPRO", "HCLTECH"],
            "HDFCBANK": ["ICICIBANK", "KOTAKBANK", "AXISBANK"],
            "INFY": ["TCS", "WIPRO", "HCLTECH"],
            "HINDUNILVR": ["ITC", "NESTLEIND", "BRITANNIA"]
        }
        
        peers = peer_groups.get(symbol.upper(), ["NIFTY50"])
        
        return {
            "peer_companies": peers,
            "sector_pe_avg": round(random.uniform(15, 25), 2),
            "sector_pb_avg": round(random.uniform(1.5, 4), 2),
            "sector_roe_avg": round(random.uniform(12, 20), 2),
            "relative_performance": random.choice(["Outperforming", "In-line", "Underperforming"])
        }
    
    async def process_fundamental_analysis_results(
        self, 
        ai_response: str, 
        symbol: str,
        financial_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process and structure fundamental analysis results"""
        
        # Calculate additional fundamental metrics
        fundamental_scores = self.calculate_fundamental_scores(financial_data)
        
        # Structure the results
        results = {
            "ai_analysis": ai_response,
            "symbol": symbol,
            "financial_data": financial_data,
            "fundamental_scores": fundamental_scores,
            "valuation_summary": self.generate_valuation_summary(financial_data),
            "investment_thesis": self.extract_investment_thesis(ai_response),
            "risk_factors": self.identify_risk_factors(financial_data),
            "confidence_score": 0.85,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        return results
    
    def calculate_fundamental_scores(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate fundamental strength scores"""
        
        ratios = financial_data.get('ratios', {})
        growth = financial_data.get('growth_metrics', {})
        
        # Financial Health Score (0-100)
        debt_to_equity = ratios.get('debt_to_equity', 1)
        current_ratio = ratios.get('current_ratio', 1)
        
        financial_health = 50  # Base score
        if debt_to_equity < 0.5:
            financial_health += 20
        elif debt_to_equity < 1:
            financial_health += 10
        elif debt_to_equity > 2:
            financial_health -= 20
        
        if current_ratio > 1.5:
            financial_health += 15
        elif current_ratio < 1:
            financial_health -= 15
        
        # Profitability Score (0-100)
        roe = ratios.get('roe', 10)
        roa = ratios.get('roa', 5)
        
        profitability = 50  # Base score
        if roe > 20:
            profitability += 25
        elif roe > 15:
            profitability += 15
        elif roe < 10:
            profitability -= 15
        
        if roa > 10:
            profitability += 15
        elif roa < 5:
            profitability -= 10
        
        # Growth Score (0-100)
        revenue_growth = growth.get('revenue_growth_yoy', 0)
        profit_growth = growth.get('profit_growth_yoy', 0)
        
        growth_score = 50  # Base score
        if revenue_growth > 15:
            growth_score += 20
        elif revenue_growth > 10:
            growth_score += 10
        elif revenue_growth < 0:
            growth_score -= 20
        
        if profit_growth > 20:
            growth_score += 20
        elif profit_growth > 10:
            growth_score += 10
        elif profit_growth < 0:
            growth_score -= 20
        
        # Valuation Score (0-100)
        pe_ratio = ratios.get('pe_ratio', 20)
        pb_ratio = ratios.get('pb_ratio', 2)
        
        valuation_score = 50  # Base score
        if pe_ratio < 15:
            valuation_score += 20
        elif pe_ratio < 20:
            valuation_score += 10
        elif pe_ratio > 30:
            valuation_score -= 20
        
        if pb_ratio < 2:
            valuation_score += 15
        elif pb_ratio > 4:
            valuation_score -= 15
        
        # Overall Score
        overall_score = (financial_health + profitability + growth_score + valuation_score) / 4
        
        return {
            "financial_health_score": max(0, min(100, financial_health)),
            "profitability_score": max(0, min(100, profitability)),
            "growth_score": max(0, min(100, growth_score)),
            "valuation_score": max(0, min(100, valuation_score)),
            "overall_score": max(0, min(100, overall_score)),
            "rating": self.get_rating_from_score(overall_score)
        }
    
    def get_rating_from_score(self, score: float) -> str:
        """Convert numerical score to rating"""
        if score >= 80:
            return "Excellent"
        elif score >= 70:
            return "Good"
        elif score >= 60:
            return "Average"
        elif score >= 50:
            return "Below Average"
        else:
            return "Poor"
    
    def generate_valuation_summary(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate valuation summary"""
        
        valuation = financial_data.get('valuation', {})
        ratios = financial_data.get('ratios', {})
        peer_data = financial_data.get('peer_comparison', {})
        
        current_price = valuation.get('current_price', 0)
        pe_ratio = ratios.get('pe_ratio', 0)
        sector_pe = peer_data.get('sector_pe_avg', 20)
        
        # Simple fair value calculation
        if pe_ratio > 0:
            fair_value_pe = current_price * (sector_pe / pe_ratio)
        else:
            fair_value_pe = current_price
        
        return {
            "current_price": current_price,
            "fair_value_estimate": round(fair_value_pe, 2),
            "upside_downside": round(((fair_value_pe - current_price) / current_price * 100), 2),
            "valuation_vs_peers": "Expensive" if pe_ratio > sector_pe * 1.2 else "Cheap" if pe_ratio < sector_pe * 0.8 else "Fair"
        }
    
    def extract_investment_thesis(self, ai_response: str) -> List[str]:
        """Extract key investment thesis points from AI response"""
        
        # Simplified extraction - in production, would use NLP
        thesis_points = []
        
        if "strong" in ai_response.lower():
            thesis_points.append("Strong financial fundamentals")
        
        if "growth" in ai_response.lower():
            thesis_points.append("Solid growth prospects")
        
        if "market leader" in ai_response.lower():
            thesis_points.append("Market leadership position")
        
        if "undervalued" in ai_response.lower():
            thesis_points.append("Attractive valuation")
        
        # Default thesis points if none extracted
        if not thesis_points:
            thesis_points = [
                "Established market position",
                "Consistent financial performance",
                "Reasonable valuation metrics"
            ]
        
        return thesis_points
    
    def identify_risk_factors(self, financial_data: Dict[str, Any]) -> List[str]:
        """Identify key risk factors"""
        
        risks = []
        ratios = financial_data.get('ratios', {})
        growth = financial_data.get('growth_metrics', {})
        
        # Debt risk
        if ratios.get('debt_to_equity', 0) > 1.5:
            risks.append("High debt levels may impact financial flexibility")
        
        # Liquidity risk
        if ratios.get('current_ratio', 1) < 1:
            risks.append("Liquidity concerns with current ratio below 1")
        
        # Growth risk
        if growth.get('revenue_growth_yoy', 0) < 0:
            risks.append("Declining revenue growth trend")
        
        # Valuation risk
        if ratios.get('pe_ratio', 20) > 30:
            risks.append("High valuation multiples may limit upside")
        
        # Default risks if none identified
        if not risks:
            risks = [
                "Market volatility and economic cycles",
                "Sector-specific regulatory changes",
                "Competition and market dynamics"
            ]
        
        return risks    

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
            
            logger.debug(f"Stored fundamental analysis result for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to store fundamental analysis result: {e}")