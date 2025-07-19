"""
OpenAI Assistants API Service
Handles OpenAI Assistants API integration with persistent threads
"""
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import openai
from app.core.config import settings

logger = logging.getLogger(__name__)

class OpenAIAssistantsService:
    """Service for OpenAI Assistants API integration"""
    
    def __init__(self, api_key: str):
        """Initialize OpenAI Assistants service"""
        self.api_key = api_key
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.assistant_id = "asst_ac2dctErJa91jwvfNMa54GCK"  # Your predefined assistant ID
        
        # In-memory thread storage (replace with Redis/DB in production)
        self.user_threads: Dict[str, str] = {}
        
        # Assistant configuration
        self.max_retries = 3
        self.polling_interval = 1.0  # seconds
        self.max_polling_time = 60.0  # seconds
    
    async def get_or_create_thread(self, user_id: str) -> str:
        """Get existing thread for user or create new one"""
        if user_id in self.user_threads:
            return self.user_threads[user_id]
        
        try:
            # Create new thread
            thread = await self.client.beta.threads.create(
                metadata={
                    "user_id": user_id,
                    "created_at": datetime.utcnow().isoformat(),
                    "platform": "quantum_leap_trading"
                }
            )
            
            # Store thread ID
            self.user_threads[user_id] = thread.id
            logger.info(f"Created new thread {thread.id} for user {user_id}")
            
            return thread.id
            
        except Exception as e:
            logger.error(f"Failed to create thread for user {user_id}: {str(e)}")
            raise Exception(f"Thread creation failed: {str(e)}")
    
    async def send_message(
        self, 
        user_id: str, 
        message: str, 
        thread_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send message to OpenAI Assistant and get response
        
        Args:
            user_id: User identifier
            message: User message content
            thread_id: Optional existing thread ID
            context: Optional additional context
            
        Returns:
            Dictionary with assistant response and metadata
        """
        try:
            # Get or create thread
            if thread_id:
                # Validate thread exists
                try:
                    await self.client.beta.threads.retrieve(thread_id)
                    current_thread_id = thread_id
                except Exception:
                    logger.warning(f"Thread {thread_id} not found, creating new thread")
                    current_thread_id = await self.get_or_create_thread(user_id)
            else:
                current_thread_id = await self.get_or_create_thread(user_id)
            
            # Prepare message content
            message_content = message
            if context:
                # Add context to message if provided
                context_str = f"\n\nContext: {str(context)}"
                message_content += context_str
            
            # Add message to thread
            thread_message = await self.client.beta.threads.messages.create(
                thread_id=current_thread_id,
                role="user",
                content=message_content
            )
            
            # Run assistant
            run = await self.client.beta.threads.runs.create(
                thread_id=current_thread_id,
                assistant_id=self.assistant_id
            )
            
            # Poll for completion
            assistant_response = await self._poll_run_completion(current_thread_id, run.id)
            
            return {
                "status": "success",
                "reply": assistant_response,
                "thread_id": current_thread_id,
                "message_id": thread_message.id,
                "run_id": run.id,
                "metadata": {
                    "user_id": user_id,
                    "assistant_id": self.assistant_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error in send_message for user {user_id}: {str(e)}")
            return {
                "status": "error",
                "reply": f"Sorry, I encountered an error: {str(e)}",
                "thread_id": thread_id or "unknown",
                "error": str(e)
            }
    
    async def _poll_run_completion(self, thread_id: str, run_id: str) -> str:
        """Poll for run completion and return assistant response"""
        start_time = asyncio.get_event_loop().time()
        
        while True:
            try:
                # Check if we've exceeded max polling time
                if asyncio.get_event_loop().time() - start_time > self.max_polling_time:
                    raise Exception("Assistant response timeout")
                
                # Get run status
                run = await self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run_id
                )
                
                if run.status == "completed":
                    # Get the latest assistant message
                    messages = await self.client.beta.threads.messages.list(
                        thread_id=thread_id,
                        limit=1
                    )
                    
                    if messages.data:
                        latest_message = messages.data[0]
                        if latest_message.role == "assistant":
                            # Extract text content
                            content = latest_message.content[0]
                            if hasattr(content, 'text'):
                                return content.text.value
                            else:
                                return str(content)
                    
                    return "Assistant completed but no response found"
                
                elif run.status == "failed":
                    raise Exception(f"Assistant run failed: {run.last_error}")
                
                elif run.status == "cancelled":
                    raise Exception("Assistant run was cancelled")
                
                elif run.status == "expired":
                    raise Exception("Assistant run expired")
                
                # Wait before polling again
                await asyncio.sleep(self.polling_interval)
                
            except Exception as e:
                logger.error(f"Error polling run completion: {str(e)}")
                raise e
    
    async def get_thread_messages(self, thread_id: str, limit: int = 10) -> list:
        """Get recent messages from a thread"""
        try:
            messages = await self.client.beta.threads.messages.list(
                thread_id=thread_id,
                limit=limit
            )
            
            return [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content[0].text.value if msg.content else "",
                    "created_at": msg.created_at
                }
                for msg in messages.data
            ]
            
        except Exception as e:
            logger.error(f"Error getting thread messages: {str(e)}")
            return []
    
    async def delete_thread(self, thread_id: str) -> bool:
        """Delete a thread"""
        try:
            await self.client.beta.threads.delete(thread_id)
            
            # Remove from in-memory storage
            for user_id, stored_thread_id in self.user_threads.items():
                if stored_thread_id == thread_id:
                    del self.user_threads[user_id]
                    break
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting thread {thread_id}: {str(e)}")
            return False
    
    async def get_assistant_status(self) -> Dict[str, Any]:
        """Get assistant status and information"""
        try:
            assistant = await self.client.beta.assistants.retrieve(self.assistant_id)
            
            return {
                "status": "success",
                "assistant_id": assistant.id,
                "assistant_name": assistant.name,
                "is_available": True,
                "model": assistant.model,
                "instructions": assistant.instructions[:100] + "..." if len(assistant.instructions) > 100 else assistant.instructions,
                "tools_count": len(assistant.tools) if assistant.tools else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting assistant status: {str(e)}")
            return {
                "status": "error",
                "assistant_id": self.assistant_id,
                "assistant_name": "Unknown",
                "is_available": False,
                "message": str(e)
            }
    
    def get_user_thread_id(self, user_id: str) -> Optional[str]:
        """Get thread ID for user from in-memory storage"""
        return self.user_threads.get(user_id)
    
    def clear_user_thread(self, user_id: str) -> bool:
        """Clear thread ID for user"""
        if user_id in self.user_threads:
            del self.user_threads[user_id]
            return True
        return False
