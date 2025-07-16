"""
AI Engine Request Schemas

Pydantic models for validating AI engine API requests.
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class AIProvider(str, Enum):
    """Supported AI providers"""
    OPENAI = "openai"
    CLAUDE = "claude" 
    GEMINI = "gemini"
    AUTO = "auto"  # Let orchestrator choose


class AnalysisType(str, Enum):
    """Types of market analysis"""
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"
    STRATEGY_GENERATION = "strategy_generation"
    PORTFOLIO_OPTIMIZATION = "portfolio_optimization"


class MarketAnalysisRequest(BaseModel):
    """Request for AI market analysis"""
    user_id: str = Field(..., description="User identifier")
    analysis_type: AnalysisType = Field(..., description="Type of analysis to perform")
    symbols: List[str] = Field(..., description="Stock symbols to analyze")
    timeframe: str = Field(default="1d", description="Analysis timeframe (1d, 1w, 1m)")
    provider: AIProvider = Field(default=AIProvider.AUTO, description="Preferred AI provider")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context data")


class StrategyGenerationRequest(BaseModel):
    """Request for AI strategy generation"""
    user_id: str = Field(..., description="User identifier")
    strategy_prompt: str = Field(..., description="Natural language strategy description")
    risk_tolerance: str = Field(default="medium", description="Risk tolerance level")
    investment_amount: Optional[float] = Field(default=None, description="Investment amount")
    provider: AIProvider = Field(default=AIProvider.AUTO, description="Preferred AI provider")
    include_backtesting: bool = Field(default=False, description="Include backtesting analysis")


class PortfolioOptimizationRequest(BaseModel):
    """Request for AI portfolio optimization"""
    user_id: str = Field(..., description="User identifier")
    optimization_goal: str = Field(..., description="Optimization objective")
    constraints: Optional[Dict[str, Any]] = Field(default=None, description="Optimization constraints")
    provider: AIProvider = Field(default=AIProvider.AUTO, description="Preferred AI provider")


class SignalGenerationRequest(BaseModel):
    """Request for AI trading signals"""
    user_id: str = Field(..., description="User identifier")
    symbols: List[str] = Field(..., description="Symbols to generate signals for")
    signal_type: str = Field(default="buy_sell", description="Type of signals to generate")
    provider: AIProvider = Field(default=AIProvider.AUTO, description="Preferred AI provider")
    live_data: bool = Field(default=True, description="Use live market data") 