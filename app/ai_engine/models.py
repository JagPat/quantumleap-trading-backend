"""
Enhanced Pydantic models for BYOAI system
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

# ========================================
# Enums and Constants
# ========================================

class AIProvider(str, Enum):
    """Supported AI providers"""
    OPENAI = "openai"
    CLAUDE = "claude"
    GEMINI = "gemini"
    GROK = "grok"
    AUTO = "auto"

class MessageType(str, Enum):
    """Chat message types"""
    USER = "user"
    ASSISTANT = "assistant"

class SignalType(str, Enum):
    """Trading signal types"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

class AnalysisType(str, Enum):
    """Analysis types"""
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"
    PORTFOLIO = "portfolio"
    MARKET = "market"

class StrategyType(str, Enum):
    """Strategy types"""
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    SCALPING = "scalping"
    SWING = "swing"
    LONG_TERM = "long_term"

class RiskTolerance(str, Enum):
    """Risk tolerance levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class TradingStyle(str, Enum):
    """Trading style preferences"""
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"

# ========================================
# AI Preferences Models
# ========================================

class AIPreferences(BaseModel):
    """AI preferences model for database storage"""
    user_id: str
    preferred_ai_provider: AIProvider = AIProvider.AUTO
    openai_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    grok_api_key: Optional[str] = None
    provider_priorities: Optional[Dict[str, List[str]]] = None
    cost_limits: Optional[Dict[str, float]] = None
    risk_tolerance: RiskTolerance = RiskTolerance.MEDIUM
    trading_style: TradingStyle = TradingStyle.BALANCED
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class AIPreferencesRequest(BaseModel):
    """Enhanced AI preferences request"""
    preferred_ai_provider: AIProvider = AIProvider.AUTO
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    claude_api_key: Optional[str] = Field(None, description="Claude API key")
    gemini_api_key: Optional[str] = Field(None, description="Gemini API key")
    grok_api_key: Optional[str] = Field(None, description="Grok API key")
    provider_priorities: Optional[Dict[str, List[str]]] = Field(None, description="Provider priorities by task type")
    cost_limits: Optional[Dict[str, float]] = Field(None, description="Cost limits per provider")
    risk_tolerance: RiskTolerance = RiskTolerance.MEDIUM
    trading_style: TradingStyle = TradingStyle.BALANCED

    @validator('provider_priorities')
    def validate_provider_priorities(cls, v):
        if v is not None:
            valid_tasks = ['chat', 'analysis', 'strategy', 'signals', 'sentiment']
            valid_providers = ['openai', 'claude', 'gemini', 'grok']
            for task, providers in v.items():
                if task not in valid_tasks:
                    raise ValueError(f"Invalid task type: {task}")
                for provider in providers:
                    if provider not in valid_providers:
                        raise ValueError(f"Invalid provider: {provider}")
        return v

class AIPreferencesResponse(BaseModel):
    """AI preferences response"""
    status: str
    preferences: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

class APIKeyValidationRequest(BaseModel):
    """API key validation request"""
    provider: AIProvider
    api_key: str = Field(..., min_length=1, description="API key to validate")

class APIKeyValidationResponse(BaseModel):
    """API key validation response"""
    valid: bool
    provider: str
    message: Optional[str] = None

# ========================================
# Chat Models
# ========================================

class ChatMessage(BaseModel):
    """Chat message model"""
    role: MessageType
    content: str = Field(..., min_length=1, description="Message content")
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None

class ChatRequest(BaseModel):
    """Chat request model"""
    message: str = Field(..., min_length=1, description="User message")
    thread_id: Optional[str] = Field(None, description="Thread ID for conversation continuity")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")

class ChatResponse(BaseModel):
    """Chat response model"""
    status: str
    reply: str
    thread_id: str
    message_id: str
    provider_used: str
    tokens_used: int = 0
    cost_cents: int = 0
    metadata: Optional[Dict[str, Any]] = None

class ChatSession(BaseModel):
    """Chat session model"""
    id: int
    thread_id: str
    session_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

# ========================================
# Strategy Models
# ========================================

class StrategyParameters(BaseModel):
    """Strategy generation parameters"""
    strategy_type: StrategyType
    risk_tolerance: RiskTolerance
    time_horizon: str = Field(..., description="Time horizon (short, medium, long)")
    target_symbols: Optional[List[str]] = Field(None, description="Target symbols for strategy")
    capital_allocation: Optional[float] = Field(None, ge=0, le=1, description="Capital allocation percentage")
    max_drawdown: Optional[float] = Field(None, ge=0, le=1, description="Maximum acceptable drawdown")

class TradingStrategy(BaseModel):
    """Trading strategy model"""
    id: str
    name: str
    type: StrategyType
    description: str
    entry_rules: List[str]
    exit_rules: List[str]
    risk_management: Dict[str, Any]
    parameters: Dict[str, Any]
    backtesting_results: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    is_active: bool = False
    created_at: datetime
    updated_at: datetime

class StrategyRequest(BaseModel):
    """Strategy generation request"""
    parameters: StrategyParameters
    portfolio_data: Optional[Dict[str, Any]] = None

# Alias for backward compatibility
AIStrategyRequest = StrategyRequest

class StrategyResponse(BaseModel):
    """Strategy generation response"""
    status: str
    strategy: Optional[TradingStrategy] = None
    message: Optional[str] = None

# Alias for backward compatibility
AIStrategyResponse = StrategyResponse

# ========================================
# Signal Models
# ========================================

class TradingSignal(BaseModel):
    """Trading signal model"""
    id: str
    symbol: str = Field(..., description="Trading symbol")
    signal_type: SignalType
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)")
    reasoning: str = Field(..., description="Explanation for the signal")
    target_price: Optional[float] = Field(None, gt=0, description="Target price")
    stop_loss: Optional[float] = Field(None, gt=0, description="Stop loss price")
    take_profit: Optional[float] = Field(None, gt=0, description="Take profit price")
    position_size: Optional[float] = Field(None, gt=0, description="Recommended position size")
    expires_at: Optional[datetime] = Field(None, description="Signal expiration time")
    created_at: datetime = Field(default_factory=datetime.now)

class SignalsRequest(BaseModel):
    """Trading signals request"""
    symbols: Optional[List[str]] = Field(None, description="Symbols to analyze")
    signal_type: Optional[SignalType] = Field(None, description="Type of signals to generate")
    portfolio_data: Optional[Dict[str, Any]] = None

# Alias for backward compatibility
AISignalsRequest = SignalsRequest

class SignalsResponse(BaseModel):
    """Trading signals response"""
    status: str
    signals: List[TradingSignal] = []
    message: Optional[str] = None

# Alias for backward compatibility
AISignalsResponse = SignalsResponse

# ========================================
# Analysis Models
# ========================================

class AnalysisRequest(BaseModel):
    """Analysis request model"""
    analysis_type: AnalysisType
    symbols: List[str] = Field(..., min_items=1, description="Symbols to analyze")
    timeframe: Optional[str] = Field("1d", description="Analysis timeframe")
    parameters: Optional[Dict[str, Any]] = None

class AnalysisResponse(BaseModel):
    """Analysis response model"""
    status: str
    analysis_type: AnalysisType
    symbols: List[str]
    results: Dict[str, Any]
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    provider_used: str
    created_at: datetime = Field(default_factory=datetime.now)

# ========================================
# Usage Tracking Models
# ========================================

class UsageStats(BaseModel):
    """Usage statistics model"""
    provider: str
    requests: int = 0
    total_tokens: int = 0
    total_cost_cents: int = 0
    avg_response_time_ms: float = 0.0

class UsageReport(BaseModel):
    """Usage report model"""
    user_id: str
    period_days: int
    provider_statistics: List[UsageStats]
    operation_statistics: List[Dict[str, Any]]
    total_cost_cents: int = 0
    total_requests: int = 0

# ========================================
# Error Models
# ========================================

class ErrorResponse(BaseModel):
    """Error response model"""
    status: str = "error"
    message: str
    error_code: Optional[str] = None
    retry_after: Optional[int] = None

class ValidationError(BaseModel):
    """Validation error model"""
    field: str
    message: str
    value: Any

# ========================================
# Health and Status Models
# ========================================

class ProviderStatus(BaseModel):
    """AI provider status model"""
    provider: str
    available: bool
    last_checked: datetime
    error_message: Optional[str] = None

class AIEngineStatus(BaseModel):
    """AI engine status model"""
    status: str
    providers: List[ProviderStatus]
    active_sessions: int = 0
    total_requests_today: int = 0
    uptime_seconds: int = 0

# ========================================
# Batch Operation Models
# ========================================

class BatchAnalysisRequest(BaseModel):
    """Batch analysis request"""
    requests: List[AnalysisRequest] = Field(..., min_items=1, max_items=10)
    priority: Optional[str] = Field("normal", description="Processing priority")

class BatchAnalysisResponse(BaseModel):
    """Batch analysis response"""
    status: str
    results: List[AnalysisResponse]
    failed_requests: List[Dict[str, Any]] = []
    processing_time_ms: int = 0

# ========================================
# Configuration Models
# ========================================

class AIEngineConfig(BaseModel):
    """AI engine configuration"""
    max_concurrent_requests: int = Field(10, ge=1, le=100)
    default_timeout_seconds: int = Field(30, ge=5, le=300)
    cost_limit_cents_per_day: int = Field(1000, ge=0)
    enable_caching: bool = True
    cache_ttl_seconds: int = Field(3600, ge=60)

# ========================================
# Assistant Models
# ========================================

class AssistantMessageRequest(BaseModel):
    """OpenAI Assistant message request"""
    message: str = Field(..., min_length=1, description="Message to send to assistant")
    thread_id: Optional[str] = Field(None, description="Thread ID for conversation continuity")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")

class AssistantMessageResponse(BaseModel):
    """OpenAI Assistant message response"""
    status: str
    reply: str
    thread_id: str
    message_id: Optional[str] = None
    run_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class AssistantStatusResponse(BaseModel):
    """OpenAI Assistant status response"""
    status: str
    assistant_id: Optional[str] = None
    assistant_name: Optional[str] = None
    is_available: bool = False
    message: Optional[str] = None

# ========================================
# Response Wrapper Models
# ========================================

class SuccessResponse(BaseModel):
    """Generic success response"""
    status: str = "success"
    data: Any
    message: Optional[str] = None

class PaginatedResponse(BaseModel):
    """Paginated response model"""
    status: str = "success"
    data: List[Any]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool