"""
Base AI Provider Interface

Defines the common interface that all AI providers must implement.
Ensures consistency across different provider implementations.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BaseAIProvider(ABC):
    """
    Abstract base class for AI providers.
    
    All AI provider clients must implement this interface to ensure
    consistency and interchangeability.
    """
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """
        Initialize the AI provider.
        
        Args:
            api_key: API key for the provider (should come from environment)
            **kwargs: Additional provider-specific configuration
        """
        self.api_key = api_key
        self.provider_name = self.__class__.__name__.replace("Client", "").lower()
        self.config = kwargs
        
        if not api_key:
            logger.warning(f"{self.provider_name} API key not provided - provider will not be available")
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and properly configured"""
        pass
    
    @abstractmethod
    async def generate_analysis(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate market analysis using the provider.
        
        Args:
            prompt: Formatted analysis prompt
            context: Additional context data
            
        Returns:
            Analysis response from the provider
        """
        pass
    
    @abstractmethod
    async def generate_strategy(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate trading strategy using the provider.
        
        Args:
            prompt: Formatted strategy prompt
            context: Additional context data
            
        Returns:
            Strategy response from the provider
        """
        pass
    
    @abstractmethod
    async def generate_signals(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate trading signals using the provider.
        
        Args:
            prompt: Formatted signals prompt
            context: Additional context data
            
        Returns:
            Signals response from the provider
        """
        pass
    
    def _validate_response(self, response: Any) -> Dict[str, Any]:
        """
        Validate and normalize provider response.
        
        Args:
            response: Raw response from provider
            
        Returns:
            Normalized response dictionary
        """
        if not response:
            return {"error": "Empty response from provider"}
        
        try:
            # Basic validation - subclasses can override for provider-specific validation
            if isinstance(response, dict):
                return response
            elif isinstance(response, str):
                return {"content": response}
            else:
                return {"content": str(response)}
        except Exception as e:
            logger.error(f"Error validating {self.provider_name} response: {str(e)}")
            return {"error": f"Invalid response format: {str(e)}"}
    
    def _handle_error(self, error: Exception, operation: str) -> Dict[str, Any]:
        """
        Handle provider errors consistently.
        
        Args:
            error: Exception that occurred
            operation: Operation that failed
            
        Returns:
            Standardized error response
        """
        error_msg = f"{self.provider_name} {operation} failed: {str(error)}"
        logger.error(error_msg)
        
        return {
            "error": error_msg,
            "provider": self.provider_name,
            "operation": operation,
            "error_type": type(error).__name__
        } 