"""
Chat Engine
Core functionality for managing AI conversations with context integration
"""
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import sqlite3
from .orchestrator import AIOrchestrator
from .models import (
    ChatRequest, ChatResponse, ChatMessage, ChatSession,
    AIPreferences
)
from .providers.base_provider import Message
from ..core.config import settings
from ..database.service import get_db_connection

logger = logging.getLogger(__name__)

class ChatEngine:
    """
    Core chat engine that manages conversations, context, and AI interactions
    """
    
    def __init__(self):
        self.orchestrator = AIOrchestrator()
        
    async def process_message(
        self, 
        user_id: str, 
        message: str, 
        thread_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ChatResponse:
        """Process a chat message with full context integration"""
        
        try:
            # Get or create chat session
            session = await self.get_or_create_session(user_id, thread_id)
            
            # Build comprehensive user context
            user_context = await self.build_user_context(user_id)
            
            # Enhance message with context
            enhanced_context = {**user_context}
            if context:
                enhanced_context.update(context)
            
            # Create chat request
            chat_request = ChatRequest(
                message=message,
                thread_id=session.thread_id,
                context=enhanced_context
            )
            
            # Get user preferences for provider selection
            user_preferences = await self.get_user_preferences(user_id)
            
            # Process with orchestrator
            response = await self.orchestrator.process_chat_message(
                user_id, 
                chat_request, 
                user_preferences
            )
            
            # Store conversation in database
            await self.store_conversation(
                session.id,
                session.thread_id,
                user_id,
                message,
                response.reply,
                response.provider_used,
                response.tokens_used,
                response.cost_cents,
                response.metadata
            )
            
            # Update session timestamp
            await self.update_session_timestamp(session.id)
            
            return response
            
        except Exception as e:
            logger.error(f"Chat processing failed for user {user_id}: {e}")
            return ChatResponse(
                status="error",
                reply="I'm experiencing technical difficulties. Please try again in a moment.",
                thread_id=thread_id or f"error_{user_id}",
                message_id="error",
                provider_used="none",
                tokens_used=0,
                cost_cents=0
            )
    
    async def get_or_create_session(
        self, 
        user_id: str, 
        thread_id: Optional[str] = None
    ) -> ChatSession:
        """Get existing session or create new one"""
        
        if thread_id:
            # Try to get existing session
            session = await self.get_session_by_thread_id(thread_id)
            if session:
                return session
        
        # Create new session
        new_thread_id = thread_id or f"chat_{user_id}_{int(datetime.now().timestamp())}"
        session_id = await self.create_session(user_id, new_thread_id)
        
        return ChatSession(
            id=session_id,
            thread_id=new_thread_id,
            session_name=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            is_active=True
        )
    
    async def create_session(self, user_id: str, thread_id: str) -> int:
        """Create new chat session in database"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO ai_chat_sessions (user_id, thread_id, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, thread_id, datetime.now(), datetime.now()))
            
            session_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Created chat session {session_id} for user {user_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create chat session: {e}")
            raise
    
    async def get_session_by_thread_id(self, thread_id: str) -> Optional[ChatSession]:
        """Get session by thread ID"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, user_id, thread_id, session_name, created_at, updated_at, is_active
                FROM ai_chat_sessions
                WHERE thread_id = ? AND is_active = 1
            """, (thread_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return ChatSession(
                    id=row[0],
                    thread_id=row[2],
                    session_name=row[3],
                    created_at=datetime.fromisoformat(row[4]) if row[4] else datetime.now(),
                    updated_at=datetime.fromisoformat(row[5]) if row[5] else datetime.now(),
                    is_active=bool(row[6])
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get session by thread_id {thread_id}: {e}")
            return None
    
    async def build_user_context(self, user_id: str) -> Dict[str, Any]:
        """Build comprehensive user context for AI conversations"""
        context = {}
        
        try:
            # Get user portfolio data
            portfolio_data = await self.get_user_portfolio(user_id)
            if portfolio_data:
                context["portfolio"] = portfolio_data
            
            # Get user preferences
            preferences = await self.get_user_preferences(user_id)
            if preferences:
                context["user_preferences"] = {
                    "risk_tolerance": preferences.get("risk_tolerance", "medium"),
                    "trading_style": preferences.get("trading_style", "balanced"),
                    "preferred_provider": preferences.get("preferred_ai_provider", "auto")
                }
            
            # Get recent conversation history for context
            recent_history = await self.get_recent_conversation_history(user_id, limit=5)
            if recent_history:
                context["recent_conversations"] = recent_history
            
            # Get current market data (placeholder for now)
            market_data = await self.get_current_market_data()
            if market_data:
                context["market_data"] = market_data
            
        except Exception as e:
            logger.warning(f"Failed to build complete user context: {e}")
        
        return context
    
    async def get_user_portfolio(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's current portfolio data"""
        try:
            # This would integrate with the portfolio service
            # For now, return a placeholder
            return {
                "total_value": 0,
                "holdings": [],
                "cash_balance": 0,
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            logger.warning(f"Failed to get portfolio for user {user_id}: {e}")
            return None
    
    async def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's AI preferences including API keys"""
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
    
    async def get_recent_conversation_history(
        self, 
        user_id: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent conversation history for context"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT message_type, content, created_at, provider_used
                FROM ai_chat_messages
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            history = []
            for row in rows:
                history.append({
                    "role": row[0],
                    "content": row[1],
                    "timestamp": row[2],
                    "provider": row[3]
                })
            
            # Reverse to get chronological order
            return list(reversed(history))
            
        except Exception as e:
            logger.warning(f"Failed to get conversation history for user {user_id}: {e}")
            return []
    
    async def get_current_market_data(self) -> Optional[Dict[str, Any]]:
        """Get current market data for context"""
        try:
            # Placeholder for market data integration
            return {
                "market_status": "open",
                "major_indices": {
                    "nifty50": {"value": 0, "change": 0},
                    "sensex": {"value": 0, "change": 0}
                },
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            logger.warning(f"Failed to get market data: {e}")
            return None
    
    async def store_conversation(
        self,
        session_id: int,
        thread_id: str,
        user_id: str,
        user_message: str,
        ai_response: str,
        provider_used: str,
        tokens_used: int,
        cost_cents: int,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Store conversation messages in database"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Store user message
            cursor.execute("""
                INSERT INTO ai_chat_messages 
                (session_id, thread_id, user_id, message_type, content, 
                 provider_used, tokens_used, cost_cents, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, thread_id, user_id, "user", user_message,
                provider_used, 0, 0, None, datetime.now()
            ))
            
            # Store AI response
            cursor.execute("""
                INSERT INTO ai_chat_messages 
                (session_id, thread_id, user_id, message_type, content, 
                 provider_used, tokens_used, cost_cents, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, thread_id, user_id, "assistant", ai_response,
                provider_used, tokens_used, cost_cents, 
                json.dumps(metadata) if metadata else None, datetime.now()
            ))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Stored conversation for session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to store conversation: {e}")
    
    async def update_session_timestamp(self, session_id: int):
        """Update session's last activity timestamp"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE ai_chat_sessions 
                SET updated_at = ?
                WHERE id = ?
            """, (datetime.now(), session_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.warning(f"Failed to update session timestamp: {e}")
    
    async def get_user_sessions(self, user_id: str) -> List[ChatSession]:
        """Get all active sessions for a user"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, thread_id, session_name, created_at, updated_at, is_active
                FROM ai_chat_sessions
                WHERE user_id = ? AND is_active = 1
                ORDER BY updated_at DESC
            """, (user_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            sessions = []
            for row in rows:
                sessions.append(ChatSession(
                    id=row[0],
                    thread_id=row[1],
                    session_name=row[2],
                    created_at=datetime.fromisoformat(row[3]) if row[3] else datetime.now(),
                    updated_at=datetime.fromisoformat(row[4]) if row[4] else datetime.now(),
                    is_active=bool(row[5])
                ))
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get sessions for user {user_id}: {e}")
            return []
    
    async def delete_session(self, user_id: str, thread_id: str) -> bool:
        """Delete a chat session"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Mark session as inactive
            cursor.execute("""
                UPDATE ai_chat_sessions 
                SET is_active = 0
                WHERE user_id = ? AND thread_id = ?
            """, (user_id, thread_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Deleted session {thread_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete session {thread_id}: {e}")
            return False
    
    async def initialize_orchestrator(self, user_id: str) -> bool:
        """Initialize the AI orchestrator with user preferences"""
        try:
            # Get user preferences
            preferences_dict = await self.get_user_preferences(user_id)
            if not preferences_dict:
                return False
            
            # Convert to AIPreferences model
            preferences = AIPreferences(
                user_id=user_id,
                preferred_ai_provider=preferences_dict.get("preferred_ai_provider", "auto"),
                openai_api_key=preferences_dict.get("openai_api_key"),
                claude_api_key=preferences_dict.get("claude_api_key"),
                gemini_api_key=preferences_dict.get("gemini_api_key"),
                grok_api_key=preferences_dict.get("grok_api_key"),
                provider_priorities=preferences_dict.get("provider_priorities"),
                cost_limits=preferences_dict.get("cost_limits"),
                risk_tolerance=preferences_dict.get("risk_tolerance", "medium"),
                trading_style=preferences_dict.get("trading_style", "balanced")
            )
            
            # Initialize providers in orchestrator
            await self.orchestrator.initialize_providers(preferences)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator for user {user_id}: {e}")
            return False