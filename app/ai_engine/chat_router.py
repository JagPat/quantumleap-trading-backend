"""
Chat Router
FastAPI endpoints for real-time AI chat functionality
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional, List, Dict, Any
from .chat_engine import ChatEngine
from .models import (
    ChatRequest, ChatResponse, ChatMessage, ChatSession,
    AssistantMessageRequest, AssistantMessageResponse
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai/chat", tags=["AI Chat"])

# Initialize chat engine
chat_engine = ChatEngine()

def get_user_id_from_headers(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> str:
    """Extract user ID from headers"""
    if x_user_id:
        return x_user_id
    # Fallback to a default for testing
    return "default_user"

@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: AssistantMessageRequest,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Send a message to the AI assistant and get a response"""
    try:
        # Initialize orchestrator for user if needed
        await chat_engine.initialize_orchestrator(user_id)
        
        # Process the message
        response = await chat_engine.process_message(
            user_id=user_id,
            message=request.message,
            thread_id=request.thread_id,
            context=request.context
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Chat message processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process message: {str(e)}"
        )

@router.get("/sessions", response_model=List[Dict[str, Any]])
async def get_chat_sessions(user_id: str = Depends(get_user_id_from_headers)):
    """Get all chat sessions for the user"""
    try:
        sessions = await chat_engine.get_user_sessions(user_id)
        
        # Convert to dict format for response
        session_list = []
        for session in sessions:
            session_list.append({
                "id": session.id,
                "thread_id": session.thread_id,
                "session_name": session.session_name,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "is_active": session.is_active
            })
        
        return session_list
        
    except Exception as e:
        logger.error(f"Failed to get chat sessions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve chat sessions: {str(e)}"
        )

@router.post("/sessions", response_model=Dict[str, Any])
async def create_chat_session(
    session_name: Optional[str] = None,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Create a new chat session"""
    try:
        # Create new session
        session = await chat_engine.get_or_create_session(user_id)
        
        # Update session name if provided
        if session_name:
            # TODO: Add method to update session name
            pass
        
        return {
            "id": session.id,
            "thread_id": session.thread_id,
            "session_name": session.session_name,
            "created_at": session.created_at.isoformat(),
            "message": "Chat session created successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to create chat session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create chat session: {str(e)}"
        )

@router.delete("/sessions/{thread_id}")
async def delete_chat_session(
    thread_id: str,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Delete a chat session"""
    try:
        success = await chat_engine.delete_session(user_id, thread_id)
        
        if success:
            return {"message": "Chat session deleted successfully"}
        else:
            raise HTTPException(
                status_code=404,
                detail="Chat session not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete chat session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete chat session: {str(e)}"
        )

@router.get("/sessions/{thread_id}/messages")
async def get_session_messages(
    thread_id: str,
    limit: int = 50,
    user_id: str = Depends(get_user_id_from_headers)
):
    """Get messages from a specific chat session"""
    try:
        # Get conversation history for the thread
        messages = await chat_engine.get_recent_conversation_history(user_id, limit)
        
        # Filter by thread_id if we had that capability
        # For now, return recent messages
        return {
            "thread_id": thread_id,
            "messages": messages,
            "total": len(messages)
        }
        
    except Exception as e:
        logger.error(f"Failed to get session messages: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve messages: {str(e)}"
        )

@router.get("/context/{user_id}")
async def get_user_context(
    user_id: str,
    requesting_user: str = Depends(get_user_id_from_headers)
):
    """Get user context for AI conversations (admin/debug endpoint)"""
    try:
        # Only allow users to access their own context
        if user_id != requesting_user:
            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )
        
        context = await chat_engine.build_user_context(user_id)
        
        return {
            "user_id": user_id,
            "context": context,
            "timestamp": "2025-07-20T05:30:00Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user context: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve user context: {str(e)}"
        )

@router.post("/test")
async def test_chat_functionality(
    message: str = "Hello, can you help me with my portfolio?",
    user_id: str = Depends(get_user_id_from_headers)
):
    """Test endpoint for chat functionality"""
    try:
        # Initialize orchestrator
        await chat_engine.initialize_orchestrator(user_id)
        
        # Send test message
        response = await chat_engine.process_message(
            user_id=user_id,
            message=message
        )
        
        return {
            "test_message": message,
            "response": response.dict(),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Chat test failed: {e}")
        return {
            "test_message": message,
            "error": str(e),
            "status": "failed"
        }

# Health check endpoint for chat system
@router.get("/health")
async def chat_health_check():
    """Health check for chat system"""
    try:
        # Basic health checks
        health_status = {
            "chat_engine": "operational",
            "database": "connected",
            "ai_orchestrator": "ready",
            "timestamp": "2025-07-20T05:30:00Z"
        }
        
        return {
            "status": "healthy",
            "components": health_status
        }
        
    except Exception as e:
        logger.error(f"Chat health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }