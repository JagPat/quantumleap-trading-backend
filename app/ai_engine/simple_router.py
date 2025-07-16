"""
Simple AI Engine Router - BYOAI (Bring Your Own AI)
FastAPI router for basic AI-related endpoints without complex dependencies
"""
from fastapi import APIRouter, Depends, Header
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

# Simple models for BYOAI
class AIPreferencesRequest(BaseModel):
    preferred_ai_provider: str = "auto"
    openai_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

class AIPreferencesResponse(BaseModel):
    status: str
    preferences: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

class APIKeyValidationRequest(BaseModel):
    provider: str
    api_key: str

class APIKeyValidationResponse(BaseModel):
    valid: bool
    provider: str
    message: Optional[str] = None

class AISignalsResponse(BaseModel):
    status: str
    signals: List[Dict[str, Any]] = []
    message: Optional[str] = None

class AIStrategyResponse(BaseModel):
    status: str
    strategy: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

router = APIRouter(prefix="/api/ai", tags=["AI Engine - BYOAI"])

def get_user_id_from_headers(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> str:
    if x_user_id:
        return x_user_id
    return "default_user"

@router.get("/status")
async def ai_engine_status():
    return {
        "status": "no_key",
        "engine": "BYOAI (Bring Your Own AI)",
        "providers": ["openai", "claude", "gemini"],
        "message": "No API key configured. Add your AI key to enable features.",
        "endpoints": [
            "/api/ai/preferences",
            "/api/ai/validate-key", 
            "/api/ai/signals",
            "/api/ai/strategy"
        ]
    }

@router.get("/preferences", response_model=AIPreferencesResponse)
async def get_ai_preferences(user_id: str = Depends(get_user_id_from_headers)):
    return AIPreferencesResponse(
        status="no_key",
        preferences={
            "preferred_ai_provider": "auto",
            "openai_api_key": None,
            "claude_api_key": None,
            "gemini_api_key": None
        },
        message="No preferences found. Add your AI key."
    )

@router.post("/preferences", response_model=AIPreferencesResponse)
async def save_ai_preferences(
    preferences: AIPreferencesRequest,
    user_id: str = Depends(get_user_id_from_headers)
):
    return AIPreferencesResponse(
        status="no_key",
        message="Preferences not saved. No AI key configured."
    )

@router.post("/validate-key", response_model=APIKeyValidationResponse)
async def validate_api_key(request: APIKeyValidationRequest):
    return APIKeyValidationResponse(
        valid=False,
        provider=request.provider,
        message="No API key configured. Validation not possible."
    )

@router.get("/signals", response_model=AISignalsResponse)
async def get_ai_signals(
    symbols: Optional[str] = None,
    user_id: str = Depends(get_user_id_from_headers)
):
    return AISignalsResponse(
        status="no_key",
        signals=[],
        message="No AI key configured. Cannot generate signals."
    )

@router.get("/strategy", response_model=AIStrategyResponse)
async def get_ai_strategy(user_id: str = Depends(get_user_id_from_headers)):
    return AIStrategyResponse(
        status="no_key",
        strategy=None,
        message="No AI key configured. Cannot generate strategy."
    )
