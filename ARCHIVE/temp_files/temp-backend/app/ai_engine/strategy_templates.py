"""
Strategy Templates and Frameworks
Pre-built trading strategy templates with risk management and parameter optimization
"""
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class StrategyType(str, Enum):
    """Available strategy types"""
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    SCALPING = "scalping"
    SWING = "swing"

class RiskLevel(str, Enum):
    """Risk levels for strategies"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class StrategyTemplateManager:
    """
    Manages pre-built strategy templates and frameworks
    """
    
    def __init__(self):
        self.templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize all strategy templates"""
        
        templates = {
            StrategyType.MOMENTUM: self._create_momentum_template(),
            StrategyType.MEAN_REVERSION: self._create_mean_reversion_template(),
            StrategyType.BREAKOUT: self._create_breakout_template(),
            StrategyType.SCALPING: self._create_scalping_template(),
            StrategyType.SWING: self._create_swing_template()
        }
        
        return templates
    
    def _create_momentum_template(self) -> Dict[str, Any]:
        """Create momentum strategy template"""
        
        return {
            "name": "Momentum Strategy",
            "description": "Follows strong price trends with momentum indicators",
            "type": StrategyType.MOMENTUM,
            "timeframe": "1d",
            "risk_level": RiskLevel.MEDIUM,
            "entry_rules": [
                "Price above 20-day moving average",
                "RSI between 50-70 (bullish momentum)",
                "MACD line above signal line",
                "Volume above 20-day average"
            ],
            "exit_rules": [
                "Price falls below 20-day moving average",
                "RSI drops below 40",
                "MACD bearish crossover",
                "Stop loss at 5% below entry"
            ],
            "risk_management": {
                "max_position_size": 0.05,  # 5% of portfolio
                "stop_loss_percentage": 5.0,
                "take_profit_percentage": 15.0,
                "max_drawdown": 10.0
            },
            "parameters": {
                "ma_period": 20,
                "rsi_period": 14,
                "rsi_entry_min": 50,
                "rsi_entry_max": 70,
                "volume_multiplier": 1.2
            },
            "indicators_required": ["SMA", "RSI", "MACD", "Volume"],
            "suitable_for": ["trending_markets", "high_volume_stocks"],
            "not_suitable_for": ["sideways_markets", "low_volume_stocks"]
        }
    
    def _create_mean_reversion_template(self) -> Dict[str, Any]:
        """Create mean reversion strategy template"""
        
        return {
            "name": "Mean Reversion Strategy",
            "description": "Buys oversold and sells overbought conditions",
            "type": StrategyType.MEAN_REVERSION,
            "timeframe": "1h",
            "risk_level": RiskLevel.MEDIUM,
            "entry_rules": [
                "RSI below 30 (oversold)",
                "Price touches lower Bollinger Band",
                "Price below 20-day moving average by 3%+",
                "No major negative news"
            ],
            "exit_rules": [
                "RSI above 70 (overbought)",
                "Price reaches upper Bollinger Band",
                "Price returns to 20-day moving average",
                "Stop loss at 7% below entry"
            ],
            "risk_management": {
                "max_position_size": 0.03,  # 3% of portfolio
                "stop_loss_percentage": 7.0,
                "take_profit_percentage": 10.0,
                "max_drawdown": 8.0
            },
            "parameters": {
                "rsi_oversold": 30,
                "rsi_overbought": 70,
                "bb_period": 20,
                "bb_std_dev": 2,
                "ma_deviation_threshold": 3.0
            },
            "indicators_required": ["RSI", "Bollinger_Bands", "SMA"],
            "suitable_for": ["range_bound_markets", "established_stocks"],
            "not_suitable_for": ["strong_trending_markets", "penny_stocks"]
        }
    
    def _create_breakout_template(self) -> Dict[str, Any]:
        """Create breakout strategy template"""
        
        return {
            "name": "Breakout Strategy",
            "description": "Trades breakouts from consolidation patterns",
            "type": StrategyType.BREAKOUT,
            "timeframe": "4h",
            "risk_level": RiskLevel.HIGH,
            "entry_rules": [
                "Price breaks above resistance with volume",
                "Volume 2x above average",
                "RSI above 60 confirming strength",
                "No immediate overhead resistance"
            ],
            "exit_rules": [
                "Price falls back below breakout level",
                "Volume dries up significantly",
                "RSI shows bearish divergence",
                "Stop loss at breakout level"
            ],
            "risk_management": {
                "max_position_size": 0.04,  # 4% of portfolio
                "stop_loss_percentage": 8.0,
                "take_profit_percentage": 20.0,
                "max_drawdown": 12.0
            },
            "parameters": {
                "volume_multiplier": 2.0,
                "rsi_confirmation": 60,
                "consolidation_period": 10,
                "breakout_threshold": 1.02
            },
            "indicators_required": ["Volume", "RSI", "Support_Resistance"],
            "suitable_for": ["consolidating_stocks", "high_volume_periods"],
            "not_suitable_for": ["low_volume_stocks", "highly_volatile_markets"]
        }
    
    def _create_scalping_template(self) -> Dict[str, Any]:
        """Create scalping strategy template"""
        
        return {
            "name": "Scalping Strategy",
            "description": "Quick trades for small profits in liquid markets",
            "type": StrategyType.SCALPING,
            "timeframe": "5m",
            "risk_level": RiskLevel.HIGH,
            "entry_rules": [
                "Price bounces off support/resistance",
                "RSI shows quick reversal pattern",
                "High volume and tight spreads",
                "Clear level to target nearby"
            ],
            "exit_rules": [
                "Target reached (1-2% profit)",
                "Position held for max 30 minutes",
                "Stop loss at 0.5% below entry",
                "Market conditions deteriorate"
            ],
            "risk_management": {
                "max_position_size": 0.02,  # 2% of portfolio
                "stop_loss_percentage": 0.5,
                "take_profit_percentage": 1.5,
                "max_drawdown": 3.0
            },
            "parameters": {
                "profit_target": 1.5,
                "max_hold_time": 30,  # minutes
                "spread_threshold": 0.1,
                "volume_requirement": 1000000
            },
            "indicators_required": ["Support_Resistance", "RSI", "Volume"],
            "suitable_for": ["liquid_stocks", "active_trading_hours"],
            "not_suitable_for": ["illiquid_stocks", "news_driven_moves"]
        }
    
    def _create_swing_template(self) -> Dict[str, Any]:
        """Create swing trading strategy template"""
        
        return {
            "name": "Swing Trading Strategy",
            "description": "Medium-term trades capturing swing moves",
            "type": StrategyType.SWING,
            "timeframe": "1d",
            "risk_level": RiskLevel.LOW,
            "entry_rules": [
                "Price in uptrend (above 50-day MA)",
                "Pullback to 20-day MA support",
                "RSI between 40-60 (not extreme)",
                "Good risk-reward setup available"
            ],
            "exit_rules": [
                "Price reaches swing high target",
                "Trend structure breaks down",
                "Time-based exit after 2 weeks",
                "Stop loss at 6% below entry"
            ],
            "risk_management": {
                "max_position_size": 0.08,  # 8% of portfolio
                "stop_loss_percentage": 6.0,
                "take_profit_percentage": 18.0,
                "max_drawdown": 15.0
            },
            "parameters": {
                "trend_ma_period": 50,
                "pullback_ma_period": 20,
                "rsi_min": 40,
                "rsi_max": 60,
                "max_hold_days": 14
            },
            "indicators_required": ["SMA_20", "SMA_50", "RSI"],
            "suitable_for": ["trending_stocks", "patient_traders"],
            "not_suitable_for": ["choppy_markets", "day_traders"]
        }
    
    def get_template(self, strategy_type: StrategyType) -> Optional[Dict[str, Any]]:
        """Get a specific strategy template"""
        return self.templates.get(strategy_type)
    
    def get_all_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get all available strategy templates"""
        return self.templates
    
    def get_templates_by_risk_level(self, risk_level: RiskLevel) -> Dict[str, Dict[str, Any]]:
        """Get templates filtered by risk level"""
        filtered_templates = {}
        
        for strategy_type, template in self.templates.items():
            if template.get("risk_level") == risk_level:
                filtered_templates[strategy_type] = template
        
        return filtered_templates
    
    def get_suitable_templates(self, market_condition: str, user_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get templates suitable for current market conditions and user profile"""
        
        suitable_templates = []
        user_risk_tolerance = user_profile.get("risk_tolerance", "medium")
        
        for template in self.templates.values():
            # Check market condition suitability
            suitable_for = template.get("suitable_for", [])
            not_suitable_for = template.get("not_suitable_for", [])
            
            if market_condition in suitable_for and market_condition not in not_suitable_for:
                # Check risk tolerance match
                template_risk = template.get("risk_level", RiskLevel.MEDIUM)
                if self._risk_tolerance_matches(user_risk_tolerance, template_risk):
                    suitable_templates.append(template)
        
        return suitable_templates
    
    def _risk_tolerance_matches(self, user_risk: str, template_risk: RiskLevel) -> bool:
        """Check if user risk tolerance matches template risk level"""
        
        risk_mapping = {
            "low": [RiskLevel.LOW],
            "medium": [RiskLevel.LOW, RiskLevel.MEDIUM],
            "high": [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]
        }
        
        allowed_risks = risk_mapping.get(user_risk, [RiskLevel.MEDIUM])
        return template_risk in allowed_risks
    
    def customize_template(
        self, 
        strategy_type: StrategyType, 
        customizations: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Customize a template with user-specific parameters"""
        
        template = self.get_template(strategy_type)
        if not template:
            return None
        
        # Create a copy to avoid modifying the original
        customized_template = json.loads(json.dumps(template))
        
        # Apply customizations
        if "risk_management" in customizations:
            customized_template["risk_management"].update(customizations["risk_management"])
        
        if "parameters" in customizations:
            customized_template["parameters"].update(customizations["parameters"])
        
        if "timeframe" in customizations:
            customized_template["timeframe"] = customizations["timeframe"]
        
        # Add customization metadata
        customized_template["customized"] = True
        customized_template["customization_date"] = datetime.now().isoformat()
        customized_template["original_template"] = strategy_type.value
        
        return customized_template