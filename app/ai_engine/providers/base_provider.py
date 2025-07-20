"""
Base AI Provider Abstract Class
Defines the standard interface for all AI providers
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel
import time
import asyncio
import logging

logger = logging.getLogger(__name__)

class ValidationResult(BaseModel):
    """Result of API key validation"""
    valid: bool
    message: Optional[str] = None
    error: Optional[str] = None

class UsageStats(BaseModel):
    """Usage statistics for a provider"""
    provider: str
    requests: int = 0
    total_tokens: int = 0
    total_cost_cents: int = 0
    avg_response_time_ms: float = 0.0
    success_rate: float = 1.0
    last_used: Optional[datetime] = None

class Message(BaseModel):
    """Standard message format"""
    role: str  # 'user', 'assistant', 'system'
    content: str

class ChatResponse(BaseModel):
    """Standard chat response format"""
    content: str
    tokens_used: int = 0
    cost_cents: int = 0
    model_used: Optional[str] = None
    response_time_ms: int = 0

class AnalysisResponse(BaseModel):
    """Standard analysis response format"""
    analysis: str
    confidence_score: float = 0.0
    tokens_used: int = 0
    cost_cents: int = 0
    model_used: Optional[str] = None
    response_time_ms: int = 0

class BaseAIProvider(ABC):
    """
    Abstract base class for all AI providers
    Defines the standard interface and common functionality
    """
    
    def __init__(self, api_key: str, provider_name: str):
        self.api_key = api_key
        self.provider_name = provider_name
        self.is_available = True
        self.last_error = None
        self.usage_stats = UsageStats(provider=provider_name)
        self._rate_limit_reset = None
        
    @abstractmethod
    async def validate_api_key(self, api_key: str) -> ValidationResult:
        """Validate the API key with the provider"""
        pass
    
    @abstractmethod
    async def generate_chat_response(
        self, 
        messages: List[Message], 
        **kwargs
    ) -> ChatResponse:
        """Generate a chat response"""
        pass
    
    @abstractmethod
    async def generate_analysis(
        self, 
        prompt: str, 
        data: Dict[str, Any], 
        **kwargs
    ) -> AnalysisResponse:
        """Generate analysis based on prompt and data"""
        pass
    
    @abstractmethod
    async def generate_structured_output(
        self, 
        prompt: str, 
        schema: Dict[str, Any], 
        **kwargs
    ) -> Dict[str, Any]:
        """Generate structured output matching the provided schema"""
        pass
    
    @abstractmethod
    async def check_availability(self) -> bool:
        """Check if the provider is currently available"""
        pass
    
    @abstractmethod
    def get_supported_models(self) -> List[str]:
        """Get list of supported models for this provider"""
        pass
    
    @abstractmethod
    def estimate_cost(self, tokens: int, model: str = None) -> int:
        """Estimate cost in cents for given token count"""
        pass
    
    # Common functionality implemented in base class
    
    async def with_retry(
        self, 
        operation, 
        max_retries: int = 3, 
        base_delay: float = 1.0
    ):
        """Execute operation with exponential backoff retry"""
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                result = await operation()
                response_time = int((time.time() - start_time) * 1000)
                
                # Update usage stats on success
                self.usage_stats.requests += 1
                self.usage_stats.avg_response_time_ms = (
                    (self.usage_stats.avg_response_time_ms * (self.usage_stats.requests - 1) + response_time) 
                    / self.usage_stats.requests
                )
                self.usage_stats.last_used = datetime.now()
                self.is_available = True
                self.last_error = None
                
                return result
                
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1} failed for {self.provider_name}: {str(e)}")
                
                # Handle rate limiting
                if "rate limit" in str(e).lower() or "429" in str(e):
                    await self.handle_rate_limit(e)
                    continue
                
                # Handle other errors
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                else:
                    self.is_available = False
                    self.last_error = str(e)
                    self.update_failure_stats()
        
        raise last_exception
    
    async def handle_rate_limit(self, error: Exception):
        """Handle rate limiting with appropriate delays"""
        # Extract retry-after from error if available
        retry_after = self.extract_retry_after(error)
        if retry_after:
            logger.info(f"Rate limited, waiting {retry_after} seconds")
            await asyncio.sleep(retry_after)
        else:
            # Default exponential backoff
            await asyncio.sleep(60)  # 1 minute default
    
    def extract_retry_after(self, error: Exception) -> Optional[int]:
        """Extract retry-after value from error message"""
        error_str = str(error).lower()
        if "retry after" in error_str:
            try:
                # Try to extract number from error message
                import re
                match = re.search(r'retry after (\d+)', error_str)
                if match:
                    return int(match.group(1))
            except:
                pass
        return None
    
    def update_failure_stats(self):
        """Update statistics after a failure"""
        total_requests = self.usage_stats.requests + 1
        success_requests = int(self.usage_stats.requests * self.usage_stats.success_rate)
        self.usage_stats.success_rate = success_requests / total_requests if total_requests > 0 else 0.0
    
    def get_usage_stats(self) -> UsageStats:
        """Get current usage statistics"""
        return self.usage_stats
    
    def reset_usage_stats(self):
        """Reset usage statistics"""
        self.usage_stats = UsageStats(provider=self.provider_name)
    
    def is_rate_limited(self) -> bool:
        """Check if provider is currently rate limited"""
        if self._rate_limit_reset:
            return datetime.now() < self._rate_limit_reset
        return False
    
    def set_rate_limit_reset(self, reset_time: datetime):
        """Set when rate limit will reset"""
        self._rate_limit_reset = reset_time
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get provider health status"""
        return {
            "provider": self.provider_name,
            "available": self.is_available,
            "rate_limited": self.is_rate_limited(),
            "last_error": self.last_error,
            "success_rate": self.usage_stats.success_rate,
            "total_requests": self.usage_stats.requests,
            "avg_response_time_ms": self.usage_stats.avg_response_time_ms,
            "last_used": self.usage_stats.last_used.isoformat() if self.usage_stats.last_used else None
        }
    
    def __str__(self) -> str:
        return f"{self.provider_name}Provider(available={self.is_available})"
    
    def __repr__(self) -> str:
        return self.__str__()