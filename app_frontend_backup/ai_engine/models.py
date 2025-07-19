"""
AI Engine Data Models
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class AIPreferences(BaseModel):
    """User AI preferences model"""
    user_id: str
    preferred_ai_provider: str = Field(default="auto", description="Preferred AI provider (openai, claude, gemini, auto)")
    openai_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class AIPreferencesRequest(BaseModel):
    """Request model for updating AI preferences"""
    preferred_ai_provider: str = Field(default="auto")
    openai_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

class AIPreferencesResponse(BaseModel):
    """Response model for AI preferences"""
    status: str
    preferences: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

class APIKeyValidationRequest(BaseModel):
    """Request model for API key validation"""
    provider: str
    api_key: str

class APIKeyValidationResponse(BaseModel):
    """Response model for API key validation"""
    valid: bool
    provider: str
    message: Optional[str] = None

class AISignalsRequest(BaseModel):
    """Request model for AI trading signals"""
    symbols: Optional[List[str]] = None
    timeframe: str = Field(default="1D")
    signal_type: str = Field(default="all")

class AISignalsResponse(BaseModel):
    """Response model for AI trading signals"""
    status: str
    signals: List[Dict[str, Any]] = []
    message: Optional[str] = None

class AIStrategyRequest(BaseModel):
    """Request model for AI strategy generation"""
    portfolio_data: Optional[Dict[str, Any]] = None
    risk_level: str = Field(default="medium")
    investment_horizon: str = Field(default="medium_term")

class AIStrategyResponse(BaseModel):
    """Response model for AI strategy generation"""
    status: str
    strategy: Optional[Dict[str, Any]] = None
    message: Optional[str] = None 