"""
AI Engine Router
FastAPI router for AI-related endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional, List
from app.ai_engine.models import (
    AIPreferencesRequest, AIPreferencesResponse,
    APIKeyValidationRequest, APIKeyValidationResponse,
    AISignalsRequest, AISignalsResponse,
    AIStrategyRequest, AIStrategyResponse,
    AssistantMessageRequest, AssistantMessageResponse,
    AssistantStatusResponse
)
from app.ai_engine.service import ai_service
from app.ai_engine.assistants_service import OpenAIAssistantsService

router = APIRouter(prefix="/api/ai", tags=["AI Engine"])

def get_user_id_from_headers(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> str:
    """Extract user ID from headers"""
    if x_user_id:
        return x_user_id
    # Fallback to a default for testing
    return "default_user"

@router.get("/preferences", response_model=AIPreferencesResponse)
async def get_ai_preferences(user_id: str = Depends(get_user_id_from_headers)):
    """Get user AI preferences"""
    try:
        preferences = await ai_service.get_user_preferences(user_id)
        if preferences:
            return AIPreferencesResponse(
                status="success",
                preferences=preferences,
                message="Preferences retrieved successfully"
            )
        else:
            return AIPreferencesResponse(
                status="success",
                preferences={
                    "preferred_ai_provider": "auto",
                    "openai_api_key": None,
                    "claude_api_key": None,
                    "gemini_api_key": None
                },
                message="No preferences found, returning defaults"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving preferences: {str(e)}")

@router.post("/preferences", response_model=AIPreferencesResponse)
async def save_ai_preferences(
    preferences: AIPreferencesRequest,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Save user AI preferences"""
    try:
        success = await ai_service.save_user_preferences(user_id, preferences)
        if success:
            return AIPreferencesResponse(
                status="success",
                message="Preferences saved successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to save preferences")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving preferences: {str(e)}")

@router.post("/validate-key", response_model=APIKeyValidationResponse)
async def validate_api_key(request: APIKeyValidationRequest):
    """Validate API key for a specific provider"""
    try:
        result = await ai_service.validate_api_key(request.provider, request.api_key)
        return APIKeyValidationResponse(
            valid=result["valid"],
            provider=request.provider,
            message=result["message"]
        )
    except Exception as e:
        return APIKeyValidationResponse(
            valid=False,
            provider=request.provider,
            message=f"Validation error: {str(e)}"
        )

@router.post("/signals", response_model=AISignalsResponse)
async def get_ai_signals(
    request: AISignalsRequest,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get AI trading signals"""
    try:
        signals = await ai_service.get_ai_signals(user_id, request.symbols)
        return AISignalsResponse(**signals)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating signals: {str(e)}")

@router.get("/signals", response_model=AISignalsResponse)
async def get_ai_signals_get(
    symbols: Optional[str] = None,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get AI trading signals (GET endpoint for compatibility)"""
    try:
        symbol_list = symbols.split(',') if symbols else None
        signals = await ai_service.get_ai_signals(user_id, symbol_list)
        return AISignalsResponse(**signals)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating signals: {str(e)}")

@router.post("/strategy", response_model=AIStrategyResponse)
async def generate_ai_strategy(
    request: AIStrategyRequest,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Generate AI trading strategy"""
    try:
        strategy = await ai_service.generate_strategy(user_id, request.portfolio_data)
        return AIStrategyResponse(**strategy)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating strategy: {str(e)}")

@router.get("/strategy", response_model=AIStrategyResponse)
async def get_ai_strategy(user_id: str = Depends(get_user_id_from_headers)):
    """Get AI trading strategy (GET endpoint for compatibility)"""
    try:
        strategy = await ai_service.generate_strategy(user_id)
        return AIStrategyResponse(**strategy)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating strategy: {str(e)}")

# Alternative routes for /ai/* endpoints (without /api prefix)
alt_router = APIRouter(prefix="/ai", tags=["AI Engine - Alternative"])

@alt_router.get("/preferences", response_model=AIPreferencesResponse)
async def get_ai_preferences_alt(user_id: str = Depends(get_user_id_from_headers)):
    """Get user AI preferences (alternative endpoint)"""
    return await get_ai_preferences(user_id)

@alt_router.post("/preferences", response_model=AIPreferencesResponse)
async def save_ai_preferences_alt(
    preferences: AIPreferencesRequest,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Save user AI preferences (alternative endpoint)"""
    return await save_ai_preferences(preferences, user_id)

@alt_router.post("/validate-key", response_model=APIKeyValidationResponse)
async def validate_api_key_alt(request: APIKeyValidationRequest):
    """Validate API key (alternative endpoint)"""
    return await validate_api_key(request) 

# OpenAI Assistants API Routes
@router.post("/message", response_model=AssistantMessageResponse)
async def send_assistant_message(
    request: AssistantMessageRequest,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Send message to OpenAI Assistant and get response"""
    try:
        # Get OpenAI Assistant service
        assistant_service = OpenAIAssistantsService(api_key="your-api-key-here")  # TODO: Get from user preferences
        
        # Send message to assistant
        result = await assistant_service.send_message(
            user_id=user_id,
            message=request.message,
            thread_id=request.thread_id,
            context=request.context
        )
        
        if result["status"] == "success":
            return AssistantMessageResponse(
                status="success",
                reply=result["reply"],
                thread_id=result["thread_id"],
                message_id=result.get("message_id"),
                run_id=result.get("run_id"),
                metadata=result.get("metadata")
            )
        else:
            raise HTTPException(
                status_code=500, 
                detail=f"Assistant error: {result.get('error', 'Unknown error')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error sending message to assistant: {str(e)}"
        )

@router.get("/assistant/status", response_model=AssistantStatusResponse)
async def get_assistant_status(user_id: str = Depends(get_user_id_from_headers)):
    """Get OpenAI Assistant status and information"""
    try:
        assistant_service = OpenAIAssistantsService(api_key="your-api-key-here")  # TODO: Get from user preferences
        status = await assistant_service.get_assistant_status()
        
        return AssistantStatusResponse(
            status=status["status"],
            assistant_id=status["assistant_id"],
            assistant_name=status["assistant_name"],
            is_available=status["is_available"],
            message=status.get("message")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error getting assistant status: {str(e)}"
        )
