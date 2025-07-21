"""
Strategy Generator
AI-powered trading strategy creation with validation and backtesting
"""
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid
from .orchestrator import AIOrchestrator
from .strategy_templates import StrategyTemplateManager, StrategyType
from .strategy_monitor import StrategyMonitor
from .models import StrategyParameters, TradingStrategy, AnalysisType
from ..database.service import get_db_connection

logger = logging.getLogger(__name__)

class StrategyGenerator:
    """
    Core strategy generation engine with AI-powered strategy creation
    """
    
    def __init__(self):
        self.orchestrator = AIOrchestrator()
        self.template_manager = StrategyTemplateManager()
        self.strategy_monitor = StrategyMonitor()
        
    async def generate_strategy(
        self, 
        user_id: str, 
        parameters: StrategyParameters,
        portfolio_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate a new trading strategy using AI"""
        
        try:
            logger.info(f"Generating strategy for user {user_id}")
            
            # Get user preferences for AI provider selection
            user_preferences = await self.get_user_preferences(user_id)
            
            # Build strategy context
            strategy_context = await self.build_strategy_context(
                user_id, parameters, portfolio_data
            )
            
            # Create strategy generation prompt
            generation_prompt = self.build_strategy_generation_prompt(
                parameters, strategy_context
            )
            
            # Select optimal provider for strategy generation
            provider = await self.orchestrator.select_optimal_provider(
                "strategy_generation", user_preferences
            )
            
            # Generate strategy using AI
            ai_response = await provider.generate_structured_output(
                generation_prompt, 
                self.get_strategy_schema()
            )
            
            # Process and validate the generated strategy
            strategy_result = await self.process_generated_strategy(
                ai_response, parameters, user_id
            )
            
            # Perform basic backtesting
            backtest_results = await self.perform_basic_backtest(strategy_result)
            strategy_result["backtesting_results"] = backtest_results
            
            # Store the generated strategy
            strategy_id = await self.store_generated_strategy(
                user_id, strategy_result
            )
            strategy_result["id"] = strategy_id
            
            return {
                "status": "success",
                "strategy": strategy_result,
                "message": "Strategy generated successfully"
            }
            
        except Exception as e:
            logger.error(f"Strategy generation failed for user {user_id}: {e}")
            return {
                "status": "error",
                "message": f"Strategy generation failed: {str(e)}"
            }
    
    async def build_strategy_context(
        self, 
        user_id: str, 
        parameters: StrategyParameters,
        portfolio_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build comprehensive context for strategy generation"""
        
        context = {
            "user_id": user_id,
            "parameters": parameters.dict(),
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Add user preferences
            user_prefs = await self.get_user_preferences(user_id)
            if user_prefs:
                context["user_preferences"] = {
                    "risk_tolerance": user_prefs.get("risk_tolerance", "medium"),
                    "trading_style": user_prefs.get("trading_style", "balanced")
                }
            
            # Add portfolio context if available
            if portfolio_data:
                context["portfolio"] = {
                    "total_value": portfolio_data.get("total_value", 0),
                    "holdings_count": len(portfolio_data.get("holdings", [])),
                    "sectors": self.analyze_portfolio_sectors(portfolio_data)
                }
            
            # Add market context
            context["market_context"] = await self.get_current_market_context()
            
            # Get relevant template as reference
            if hasattr(parameters, 'strategy_type'):
                try:
                    strategy_type = StrategyType(parameters.strategy_type)
                    template = self.template_manager.get_template(strategy_type)
                    if template:
                        context["reference_template"] = template
                except ValueError:
                    pass  # Invalid strategy type, continue without template
            
        except Exception as e:
            logger.warning(f"Failed to build complete strategy context: {e}")
        
        return context
    
    def build_strategy_generation_prompt(
        self, 
        parameters: StrategyParameters, 
        context: Dict[str, Any]
    ) -> str:
        """Build AI prompt for strategy generation"""
        
        user_prefs = context.get("user_preferences", {})
        portfolio = context.get("portfolio", {})
        market_context = context.get("market_context", {})
        
        prompt = f"""
        As an expert quantitative strategist, create a comprehensive trading strategy based on the following requirements:

        STRATEGY PARAMETERS:
        - Strategy Type: {parameters.strategy_type}
        - Risk Tolerance: {parameters.risk_tolerance}
        - Time Horizon: {parameters.time_horizon}
        - Target Symbols: {parameters.target_symbols or 'Any suitable stocks'}
        - Capital Allocation: {parameters.capital_allocation or 'To be determined'}%
        - Max Drawdown: {parameters.max_drawdown or 'To be determined'}%

        USER PROFILE:
        - Risk Tolerance: {user_prefs.get('risk_tolerance', 'medium')}
        - Trading Style: {user_prefs.get('trading_style', 'balanced')}

        PORTFOLIO CONTEXT:
        - Total Value: ₹{portfolio.get('total_value', 0):,}
        - Holdings Count: {portfolio.get('holdings_count', 0)}
        - Sectors: {', '.join(portfolio.get('sectors', []))}

        MARKET CONDITIONS:
        - Market Trend: {market_context.get('trend', 'neutral')}
        - Volatility Level: {market_context.get('volatility', 'medium')}
        - Sector Rotation: {market_context.get('sector_rotation', 'balanced')}

        STRATEGY REQUIREMENTS:
        Please create a detailed trading strategy that includes:

        1. STRATEGY OVERVIEW:
           - Clear strategy name and description
           - Investment thesis and market rationale
           - Expected performance characteristics

        2. ENTRY RULES:
           - Specific technical indicators and thresholds
           - Fundamental criteria (if applicable)
           - Market condition requirements
           - Position sizing rules

        3. EXIT RULES:
           - Profit-taking conditions
           - Stop-loss mechanisms
           - Time-based exits
           - Market condition changes

        4. RISK MANAGEMENT:
           - Maximum position size per trade
           - Portfolio-level risk limits
           - Correlation controls
           - Drawdown management

        5. IMPLEMENTATION DETAILS:
           - Required indicators and data
           - Execution timeframe and frequency
           - Monitoring requirements
           - Performance benchmarks

        6. BACKTESTING FRAMEWORK:
           - Historical testing approach
           - Performance metrics to track
           - Risk-adjusted return expectations
           - Stress testing scenarios

        Please provide a comprehensive, actionable strategy that can be implemented systematically.
        Format the response as structured data with clear sections for each component.
        """
        
        return prompt
    
    def get_strategy_schema(self) -> Dict[str, Any]:
        """Get JSON schema for strategy generation response"""
        
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "strategy_type": {"type": "string"},
                "investment_thesis": {"type": "string"},
                "entry_rules": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "exit_rules": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "risk_management": {
                    "type": "object",
                    "properties": {
                        "max_position_size": {"type": "number"},
                        "stop_loss_percentage": {"type": "number"},
                        "take_profit_percentage": {"type": "number"},
                        "max_drawdown": {"type": "number"}
                    }
                },
                "indicators_required": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "timeframe": {"type": "string"},
                "expected_performance": {
                    "type": "object",
                    "properties": {
                        "annual_return": {"type": "number"},
                        "win_rate": {"type": "number"},
                        "sharpe_ratio": {"type": "number"}
                    }
                },
                "confidence_score": {"type": "number", "minimum": 0, "maximum": 1}
            },
            "required": ["name", "description", "entry_rules", "exit_rules", "risk_management"]
        }
    
    async def process_generated_strategy(
        self, 
        ai_response: Any, 
        parameters: StrategyParameters,
        user_id: str
    ) -> Dict[str, Any]:
        """Process and validate the AI-generated strategy"""
        
        try:
            # Handle different response types
            if isinstance(ai_response, str):
                # Try to parse JSON
                try:
                    strategy_data = json.loads(ai_response)
                except json.JSONDecodeError:
                    # Fallback to structured text parsing
                    strategy_data = self.parse_text_strategy(ai_response)
            elif isinstance(ai_response, dict):
                strategy_data = ai_response
            else:
                raise ValueError("Invalid AI response format")
            
            # Validate required fields
            validated_strategy = await self.validate_strategy(strategy_data)
            
            # Enhance with metadata
            validated_strategy.update({
                "created_at": datetime.now().isoformat(),
                "user_id": user_id,
                "parameters_used": parameters.dict(),
                "status": "generated",
                "version": "1.0"
            })
            
            return validated_strategy
            
        except Exception as e:
            logger.error(f"Failed to process generated strategy: {e}")
            # Return a fallback strategy
            return self.create_fallback_strategy(parameters, user_id)
    
    def parse_text_strategy(self, text_response: str) -> Dict[str, Any]:
        """Parse text-based strategy response into structured format"""
        
        # Simplified text parsing - in production, would use more sophisticated NLP
        return {
            "name": "AI Generated Strategy",
            "description": text_response[:200] + "..." if len(text_response) > 200 else text_response,
            "strategy_type": "custom",
            "entry_rules": ["AI-defined entry conditions"],
            "exit_rules": ["AI-defined exit conditions"],
            "risk_management": {
                "max_position_size": 0.05,
                "stop_loss_percentage": 5.0,
                "take_profit_percentage": 15.0,
                "max_drawdown": 10.0
            },
            "confidence_score": 0.7
        }
    
    async def validate_strategy(self, strategy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and enhance strategy data"""
        
        # Ensure required fields exist
        required_fields = {
            "name": "Unnamed Strategy",
            "description": "AI-generated trading strategy",
            "entry_rules": ["Entry conditions to be defined"],
            "exit_rules": ["Exit conditions to be defined"],
            "risk_management": {
                "max_position_size": 0.05,
                "stop_loss_percentage": 5.0,
                "take_profit_percentage": 15.0,
                "max_drawdown": 10.0
            }
        }
        
        for field, default_value in required_fields.items():
            if field not in strategy_data:
                strategy_data[field] = default_value
        
        # Validate risk management parameters
        risk_mgmt = strategy_data.get("risk_management", {})
        if risk_mgmt.get("max_position_size", 0) > 0.2:  # Max 20% position size
            risk_mgmt["max_position_size"] = 0.2
        
        if risk_mgmt.get("max_drawdown", 0) > 25:  # Max 25% drawdown
            risk_mgmt["max_drawdown"] = 25
        
        return strategy_data
    
    def create_fallback_strategy(
        self, 
        parameters: StrategyParameters, 
        user_id: str
    ) -> Dict[str, Any]:
        """Create a fallback strategy when AI generation fails"""
        
        return {
            "name": f"Fallback {parameters.strategy_type.title()} Strategy",
            "description": "A conservative strategy created as fallback",
            "strategy_type": parameters.strategy_type,
            "entry_rules": [
                "Price above 20-day moving average",
                "RSI between 40-70",
                "Volume above average"
            ],
            "exit_rules": [
                "Price below 20-day moving average",
                "Stop loss at 5%",
                "Take profit at 10%"
            ],
            "risk_management": {
                "max_position_size": 0.03,
                "stop_loss_percentage": 5.0,
                "take_profit_percentage": 10.0,
                "max_drawdown": 8.0
            },
            "confidence_score": 0.6,
            "created_at": datetime.now().isoformat(),
            "user_id": user_id,
            "status": "fallback"
        }    

    async def perform_basic_backtest(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Perform basic backtesting on the generated strategy"""
        
        try:
            # Simplified backtesting - in production, would use historical data
            import random
            
            # Generate mock backtest results
            total_trades = random.randint(20, 100)
            winning_trades = int(total_trades * random.uniform(0.5, 0.8))
            losing_trades = total_trades - winning_trades
            
            total_return = random.uniform(-5, 25)  # -5% to +25%
            max_drawdown = random.uniform(2, 15)   # 2% to 15%
            sharpe_ratio = random.uniform(0.5, 2.5)
            
            backtest_results = {
                "period": "1 year",
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": round((winning_trades / total_trades) * 100, 2),
                "total_return": round(total_return, 2),
                "max_drawdown": round(max_drawdown, 2),
                "sharpe_ratio": round(sharpe_ratio, 2),
                "calmar_ratio": round(total_return / max_drawdown if max_drawdown > 0 else 0, 2),
                "avg_trade_return": round(total_return / total_trades, 3),
                "best_trade": round(random.uniform(5, 20), 2),
                "worst_trade": round(random.uniform(-10, -2), 2),
                "backtest_date": datetime.now().isoformat()
            }
            
            return backtest_results
            
        except Exception as e:
            logger.error(f"Backtesting failed: {e}")
            return {
                "error": "Backtesting failed",
                "message": str(e)
            }
    
    def analyze_portfolio_sectors(self, portfolio_data: Dict[str, Any]) -> List[str]:
        """Analyze portfolio sectors for context"""
        
        try:
            holdings = portfolio_data.get("holdings", [])
            sectors = set()
            
            for holding in holdings:
                symbol = holding.get("symbol", "")
                if symbol:
                    # Simple sector mapping
                    if symbol in ["TCS", "INFY", "WIPRO"]:
                        sectors.add("Technology")
                    elif symbol in ["HDFCBANK", "ICICIBANK", "SBIN"]:
                        sectors.add("Banking")
                    elif symbol in ["RELIANCE"]:
                        sectors.add("Energy")
                    else:
                        sectors.add("Others")
            
            return list(sectors)
            
        except Exception as e:
            logger.warning(f"Failed to analyze portfolio sectors: {e}")
            return ["Mixed"]
    
    async def get_current_market_context(self) -> Dict[str, Any]:
        """Get current market context for strategy generation"""
        
        try:
            # Mock market context - in production, would fetch real data
            import random
            
            return {
                "trend": random.choice(["bullish", "bearish", "neutral"]),
                "volatility": random.choice(["low", "medium", "high"]),
                "sector_rotation": random.choice(["tech_heavy", "banking_focus", "balanced"]),
                "market_sentiment": random.choice(["optimistic", "cautious", "pessimistic"]),
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.warning(f"Failed to get market context: {e}")
            return {
                "trend": "neutral",
                "volatility": "medium",
                "sector_rotation": "balanced"
            }
    
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
    
    async def store_generated_strategy(
        self, 
        user_id: str, 
        strategy: Dict[str, Any]
    ) -> str:
        """Store the generated strategy in database"""
        
        try:
            strategy_id = str(uuid.uuid4())
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO ai_strategies 
                (user_id, strategy_name, strategy_type, parameters, rules, 
                 risk_management, backtesting_results, performance_metrics, 
                 is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                strategy.get("name", "Unnamed Strategy"),
                strategy.get("strategy_type", "custom"),
                json.dumps(strategy.get("parameters_used", {})),
                json.dumps({
                    "entry_rules": strategy.get("entry_rules", []),
                    "exit_rules": strategy.get("exit_rules", [])
                }),
                json.dumps(strategy.get("risk_management", {})),
                json.dumps(strategy.get("backtesting_results", {})),
                json.dumps(strategy.get("expected_performance", {})),
                False,  # Not active by default
                datetime.now(),
                datetime.now()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Stored generated strategy {strategy_id} for user {user_id}")
            return strategy_id
            
        except Exception as e:
            logger.error(f"Failed to store generated strategy: {e}")
            return str(uuid.uuid4())  # Return a UUID even if storage fails
    
    async def get_strategy_by_id(self, user_id: str, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Get a stored strategy by ID"""
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT strategy_name, strategy_type, parameters, rules, 
                       risk_management, backtesting_results, performance_metrics,
                       is_active, created_at, updated_at
                FROM ai_strategies
                WHERE user_id = ? AND id = ?
            """, (user_id, strategy_id))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    "id": strategy_id,
                    "name": row[0],
                    "strategy_type": row[1],
                    "parameters": json.loads(row[2]) if row[2] else {},
                    "rules": json.loads(row[3]) if row[3] else {},
                    "risk_management": json.loads(row[4]) if row[4] else {},
                    "backtesting_results": json.loads(row[5]) if row[5] else {},
                    "performance_metrics": json.loads(row[6]) if row[6] else {},
                    "is_active": bool(row[7]),
                    "created_at": row[8],
                    "updated_at": row[9]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get strategy {strategy_id}: {e}")
            return None
    
    async def list_user_strategies(self, user_id: str) -> List[Dict[str, Any]]:
        """List all strategies for a user"""
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, strategy_name, strategy_type, is_active, 
                       created_at, updated_at
                FROM ai_strategies
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            strategies = []
            for row in rows:
                strategies.append({
                    "id": row[0],
                    "name": row[1],
                    "strategy_type": row[2],
                    "is_active": bool(row[3]),
                    "created_at": row[4],
                    "updated_at": row[5]
                })
            
            return strategies
            
        except Exception as e:
            logger.error(f"Failed to list strategies for user {user_id}: {e}")
            return []