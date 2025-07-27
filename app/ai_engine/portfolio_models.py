"""
Enhanced Portfolio Analysis Models
Comprehensive data models for portfolio analysis, risk assessment, and recommendations
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

# ========================================
# Enums and Constants
# ========================================

class RecommendationType(str, Enum):
    """Portfolio recommendation types"""
    REBALANCE = "rebalance"
    DIVERSIFY = "diversify"
    OPTIMIZE = "optimize"
    RISK_MANAGEMENT = "risk_management"
    PERFORMANCE = "performance"

class Priority(str, Enum):
    """Recommendation priority levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class RiskLevel(str, Enum):
    """Risk level categories"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class HealthGrade(str, Enum):
    """Portfolio health grades"""
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"

# ========================================
# Portfolio Analysis Models
# ========================================

class PortfolioHolding(BaseModel):
    """Individual portfolio holding model"""
    symbol: str
    quantity: float
    current_value: float
    investment_value: float
    pnl: float
    pnl_percentage: float
    allocation_percentage: float
    sector: Optional[str] = None
    instrument_type: Optional[str] = None
    last_updated: Optional[datetime] = None

class PortfolioData(BaseModel):
    """Portfolio data input model"""
    total_value: float
    total_investment: float
    total_pnl: float
    holdings: List[PortfolioHolding]
    last_updated: datetime
    currency: str = "INR"
    
    @validator('holdings')
    def validate_holdings(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Portfolio must contain at least one holding")
        return v

class AnalysisOptions(BaseModel):
    """Portfolio analysis options"""
    include_recommendations: bool = True
    include_risk_analysis: bool = True
    include_optimization: bool = True
    include_benchmarking: bool = True
    analysis_depth: str = "comprehensive"  # basic, standard, comprehensive
    provider_preference: Optional[str] = None

# ========================================
# Analysis Result Models
# ========================================

class PortfolioHealthScore(BaseModel):
    """Portfolio health scoring model"""
    overall_score: float = Field(..., ge=0.0, le=100.0, description="Overall health score (0-100)")
    performance_score: float = Field(..., ge=0.0, le=100.0)
    diversification_score: float = Field(..., ge=0.0, le=100.0)
    risk_score: float = Field(..., ge=0.0, le=100.0)
    liquidity_score: float = Field(..., ge=0.0, le=100.0)
    
    factors: Dict[str, float] = Field(default_factory=dict)
    grade: HealthGrade
    improvement_areas: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    
    @validator('grade', pre=True, always=True)
    def calculate_grade(cls, v, values):
        if 'overall_score' in values:
            score = values['overall_score']
            if score >= 90:
                return HealthGrade.A
            elif score >= 80:
                return HealthGrade.B
            elif score >= 70:
                return HealthGrade.C
            elif score >= 60:
                return HealthGrade.D
            else:
                return HealthGrade.F
        return v

class DiversificationMetrics(BaseModel):
    """Portfolio diversification metrics"""
    sector_count: int
    holding_count: int
    largest_position_pct: float
    top5_concentration: float
    top10_concentration: float
    herfindahl_index: float
    diversification_score: float = Field(..., ge=0.0, le=1.0)
    sector_allocations: Dict[str, float] = Field(default_factory=dict)
    concentration_risk_level: RiskLevel

class VolatilityMetrics(BaseModel):
    """Portfolio volatility metrics"""
    portfolio_volatility: float
    risk_score: float = Field(..., ge=0.0, le=1.0)
    coefficient_of_variation: float
    mean_return: float
    standard_deviation: float
    assessment: str

class RiskFactor(BaseModel):
    """Individual risk factor"""
    factor_name: str
    risk_level: RiskLevel
    impact_score: float = Field(..., ge=0.0, le=1.0)
    description: str
    mitigation_suggestions: List[str] = Field(default_factory=list)

class RiskAnalysisResult(BaseModel):
    """Comprehensive risk analysis result"""
    overall_risk_level: RiskLevel
    overall_risk_score: float = Field(..., ge=0.0, le=1.0)
    concentration_risk: float = Field(..., ge=0.0, le=1.0)
    
    sector_exposure: Dict[str, float] = Field(default_factory=dict)
    overexposed_sectors: Dict[str, float] = Field(default_factory=dict)
    
    volatility_metrics: VolatilityMetrics
    risk_factors: List[RiskFactor] = Field(default_factory=list)
    
    market_risk: Optional[Dict[str, Any]] = None
    liquidity_risk: Optional[Dict[str, Any]] = None

class PerformanceMetrics(BaseModel):
    """Portfolio performance metrics"""
    total_return: float
    total_return_percentage: float
    annualized_return: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    
    best_performer: Optional[Dict[str, Any]] = None
    worst_performer: Optional[Dict[str, Any]] = None
    
    benchmark_comparison: Optional[Dict[str, Any]] = None
    performance_attribution: Optional[Dict[str, Any]] = None

class PortfolioRecommendation(BaseModel):
    """Portfolio optimization recommendation"""
    recommendation_id: str
    type: RecommendationType
    priority: Priority
    
    title: str = Field(..., max_length=200)
    description: str = Field(..., max_length=1000)
    rationale: str = Field(..., max_length=1500)
    
    implementation_steps: List[str] = Field(default_factory=list)
    expected_impact: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    
    risk_impact: Optional[str] = None
    cost_estimate: Optional[float] = None
    timeframe: Optional[str] = None
    
    affected_symbols: List[str] = Field(default_factory=list)
    target_allocation: Optional[float] = None

# ========================================
# Main Analysis Response Models
# ========================================

class PortfolioAnalysisResult(BaseModel):
    """Complete portfolio analysis result"""
    analysis_id: str
    user_id: str
    
    portfolio_health: PortfolioHealthScore
    risk_analysis: RiskAnalysisResult
    diversification_analysis: DiversificationMetrics
    performance_metrics: PerformanceMetrics
    
    recommendations: List[PortfolioRecommendation] = Field(default_factory=list)
    key_insights: List[str] = Field(default_factory=list)
    
    market_context: Optional[Dict[str, Any]] = None
    analysis_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    provider_used: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    processing_time_ms: int
    generated_at: datetime = Field(default_factory=datetime.now)

class PortfolioAnalysisResponse(BaseModel):
    """API response for portfolio analysis"""
    status: str
    analysis: Optional[PortfolioAnalysisResult] = None
    message: Optional[str] = None
    error_code: Optional[str] = None

class AnalysisHistoryItem(BaseModel):
    """Portfolio analysis history item"""
    analysis_id: str
    generated_at: datetime
    portfolio_health_score: float
    risk_level: RiskLevel
    recommendations_count: int
    provider_used: str
    confidence_score: float

class AnalysisHistoryResponse(BaseModel):
    """Analysis history response"""
    status: str
    analyses: List[AnalysisHistoryItem] = Field(default_factory=list)
    total_count: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool

class AnalysisStatusResponse(BaseModel):
    """Analysis status response"""
    status: str
    analysis_id: str
    processing_status: str  # pending, processing, completed, failed
    progress_percentage: Optional[int] = None
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None

# ========================================
# Market Context Models
# ========================================

class MarketContext(BaseModel):
    """Market context for analysis"""
    market_sentiment: str = "neutral"
    volatility_index: float = 0.5
    market_trend: str = "sideways"
    sector_performance: Dict[str, float] = Field(default_factory=dict)
    benchmark_data: Dict[str, Any] = Field(default_factory=dict)
    economic_indicators: Dict[str, Any] = Field(default_factory=dict)

# ========================================
# Configuration Models
# ========================================

class PortfolioAnalysisConfig(BaseModel):
    """Portfolio analysis configuration"""
    max_recommendations: int = 10
    min_confidence_threshold: float = 0.6
    enable_ai_recommendations: bool = True
    enable_rule_based_recommendations: bool = True
    cache_ttl_minutes: int = 30
    analysis_timeout_seconds: int = 120

# ========================================
# Utility Models
# ========================================

class ValidationResult(BaseModel):
    """Portfolio data validation result"""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)

class CalculationResult(BaseModel):
    """Generic calculation result"""
    success: bool
    result: Optional[Any] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)