"""
AI Engine Response Schemas

Enhanced Pydantic models for AI Engine responses including feedback,
learning insights, strategy clustering, and analytics.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


class AnalysisResponse(BaseModel):
    """Response model for AI analysis requests"""
    success: bool
    analysis: str
    confidence: float = Field(ge=0.0, le=1.0)
    provider_used: str
    analysis_type: str
    recommendations: Optional[List[str]] = None
    risk_assessment: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class StrategyResponse(BaseModel):
    """Enhanced response model for AI strategy generation"""
    success: bool
    strategy_id: str
    strategy_content: str
    strategy_type: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    confidence_reason: str
    tags: List[str]
    symbols: List[str]
    timeframe: str
    risk_level: str
    expected_return: Optional[float] = None
    max_drawdown: Optional[float] = None
    provider_used: str
    entry_criteria: Optional[List[str]] = None
    exit_criteria: Optional[List[str]] = None
    risk_management: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class SignalResponse(BaseModel):
    """Response model for AI trading signals"""
    success: bool
    signals: List[Dict[str, Any]]
    confidence: float = Field(ge=0.0, le=1.0)
    provider_used: str
    market_context: Optional[str] = None
    recommendations: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class LearningInsight(BaseModel):
    """Model for AI learning insights"""
    insight_type: str
    category: str
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    applicable_strategies: List[str]
    created_at: Optional[datetime] = None


class FeedbackResponse(BaseModel):
    """Response model for trade outcome feedback"""
    success: bool
    message: str
    outcome_id: Optional[str] = None
    ai_reflection: Optional[str] = None
    learning_insights: List[LearningInsight] = []
    confidence_update: Optional[float] = None
    performance_impact: Optional[Dict[str, Any]] = None


class StrategyCluster(BaseModel):
    """Model for strategy clustering results"""
    cluster_id: str
    cluster_name: str
    strategy_type: str
    total_strategies: int
    avg_confidence: float
    avg_performance: float
    common_tags: List[str]
    representative_strategy: Optional[Dict[str, Any]] = None


class StrategyClusteringResponse(BaseModel):
    """Response model for strategy clustering analysis"""
    success: bool
    clusters: List[StrategyCluster]
    total_strategies: int
    clustering_method: str
    performance_summary: Dict[str, Any]
    recommendations: List[str] = []


class PerformanceMetrics(BaseModel):
    """Model for strategy performance metrics"""
    strategy_id: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_return: float
    average_return: float
    sharpe_ratio: Optional[float] = None
    max_consecutive_wins: int
    max_consecutive_losses: int
    performance_score: float
    last_updated: datetime


class AnalyticsResponse(BaseModel):
    """Response model for analytics data"""
    success: bool
    analytics_type: str
    data: Dict[str, Any]
    insights: List[str] = []
    recommendations: List[str] = []
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    generated_at: datetime


class CrowdInsight(BaseModel):
    """Model for crowd intelligence insights"""
    insight_id: str
    insight_type: str
    strategy_type: Optional[str] = None
    symbols: List[str] = []
    tags: List[str] = []
    user_count: int
    total_trades: int
    average_performance: float
    confidence_level: float
    risk_score: float
    trending_score: Optional[float] = None


class CrowdIntelligenceResponse(BaseModel):
    """Response model for crowd intelligence data"""
    success: bool
    insights: List[CrowdInsight]
    trending_strategies: List[Dict[str, Any]] = []
    risk_alerts: List[Dict[str, Any]] = []
    popular_symbols: List[Dict[str, Any]] = []
    performance_leaders: List[Dict[str, Any]] = []
    generated_at: datetime


class PortfolioCopilotRecommendation(BaseModel):
    """Model for portfolio co-pilot recommendations"""
    recommendation_id: str
    recommendation_type: str  # rebalance, allocation, diversification
    priority: str  # high, medium, low
    title: str
    description: str
    rationale: str
    impact_estimate: Optional[str] = None
    implementation_steps: List[str] = []
    risk_impact: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)


class PortfolioCopilotResponse(BaseModel):
    """Response model for portfolio co-pilot analysis"""
    success: bool
    portfolio_health_score: float = Field(ge=0.0, le=1.0)
    recommendations: List[PortfolioCopilotRecommendation]
    risk_analysis: Dict[str, Any]
    diversification_score: float = Field(ge=0.0, le=1.0)
    suggested_allocations: Optional[Dict[str, float]] = None
    market_context: str
    generated_at: datetime


class AIStatusResponse(BaseModel):
    """Response model for AI engine status"""
    success: bool
    providers_status: Dict[str, bool]
    active_providers: List[str]
    total_strategies: int
    total_trades: int
    system_performance: Dict[str, Any]
    last_learning_update: Optional[datetime] = None


class ErrorResponse(BaseModel):
    """Response model for errors"""
    success: bool = False
    error_type: str
    error_message: str
    error_code: Optional[str] = None
    provider_errors: Optional[Dict[str, str]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class HealthCheckResponse(BaseModel):
    """Response model for health checks"""
    status: str
    providers: Dict[str, str]
    database: str
    memory_usage: Optional[str] = None
    uptime: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


# Enhanced union types for comprehensive responses
AIResponse = Union[
    AnalysisResponse,
    StrategyResponse,
    SignalResponse,
    FeedbackResponse,
    StrategyClusteringResponse,
    AnalyticsResponse,
    CrowdIntelligenceResponse,
    PortfolioCopilotResponse,
    AIStatusResponse,
    ErrorResponse,
    HealthCheckResponse
] 