"""
OpenAI Client

Isolated client wrapper for OpenAI API integration.
Handles OpenAI-specific implementation details while providing a consistent interface.
"""
import os
import logging
from typing import Dict, Any, Optional
import json
import asyncio

from .base_provider import BaseAIProvider

logger = logging.getLogger(__name__)


class OpenAIClient(BaseAIProvider):
    """
    OpenAI API client for trading analysis and strategy generation.
    
    Features:
    - GPT-4 for complex analysis
    - GPT-3.5-turbo for faster responses
    - Structured output support
    - Cost optimization
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4", **kwargs):
        """
        Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key (defaults to environment variable)
            model: Model to use (gpt-4, gpt-3.5-turbo, etc.)
            **kwargs: Additional configuration
        """
        # Get API key from environment if not provided
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
        
        super().__init__(api_key, **kwargs)
        self.model = model
        self.max_tokens = kwargs.get("max_tokens", 4000)
        self.temperature = kwargs.get("temperature", 0.7)
        
        # Initialize OpenAI client only if API key is available
        self.client = None
        if self.api_key:
            try:
                # Import openai only when needed to avoid dependency issues
                import openai
                self.client = openai.AsyncOpenAI(api_key=self.api_key)
                logger.info(f"OpenAI client initialized with model: {self.model}")
            except ImportError:
                logger.error("OpenAI library not installed. Install with: pip install openai")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {str(e)}")
    
    @property
    def is_available(self) -> bool:
        """Check if OpenAI client is available and configured"""
        return self.client is not None and self.api_key is not None
    
    async def generate_analysis(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate market analysis using OpenAI.
        
        Args:
            prompt: Analysis prompt
            context: Additional context data
            
        Returns:
            Analysis response from OpenAI
        """
        if not self.is_available:
            return self._handle_error(Exception("OpenAI client not available"), "analysis")
        
        try:
            system_prompt = """You are an expert financial analyst with deep knowledge of Indian stock markets, 
            technical analysis, and portfolio management. Provide detailed, actionable insights based on the data provided.
            Focus on practical recommendations that can be implemented immediately."""
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"} if "json" in prompt.lower() else {"type": "text"}
            )
            
            content = response.choices[0].message.content
            
            # Try to parse as JSON if requested, fallback to text
            try:
                if "json" in prompt.lower():
                    parsed_content = json.loads(content)
                else:
                    parsed_content = {"analysis": content}
            except json.JSONDecodeError:
                parsed_content = {"analysis": content}
            
            return {
                "content": parsed_content,
                "provider": "openai",
                "model": self.model,
                "tokens_used": response.usage.total_tokens if response.usage else 0
            }
            
        except Exception as e:
            return self._handle_error(e, "analysis")
    
    async def generate_strategy(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate trading strategy using OpenAI.
        
        Args:
            prompt: Strategy generation prompt
            context: Additional context data
            
        Returns:
            Strategy response from OpenAI
        """
        if not self.is_available:
            return self._handle_error(Exception("OpenAI client not available"), "strategy")
        
        try:
            system_prompt = """You are an expert trading strategy developer with expertise in algorithmic trading,
            risk management, and Indian stock markets. Create detailed, executable trading strategies with clear
            entry/exit rules, position sizing, and risk management. Always format responses as valid JSON."""
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=0.5,  # Lower temperature for more consistent strategy generation
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            
            try:
                strategy_data = json.loads(content)
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                strategy_data = {
                    "strategy_name": "AI Generated Strategy",
                    "description": content,
                    "error": "JSON parsing failed - content returned as description"
                }
            
            return {
                "strategy": strategy_data,
                "provider": "openai",
                "model": self.model,
                "tokens_used": response.usage.total_tokens if response.usage else 0
            }
            
        except Exception as e:
            return self._handle_error(e, "strategy")
    
    async def generate_signals(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate trading signals using OpenAI.
        
        Args:
            prompt: Signals generation prompt
            context: Additional context data
            
        Returns:
            Signals response from OpenAI
        """
        if not self.is_available:
            return self._handle_error(Exception("OpenAI client not available"), "signals")
        
        try:
            system_prompt = """You are a professional trading signal generator with real-time market analysis expertise.
            Generate clear buy/sell/hold signals with confidence levels, target prices, and stop-loss recommendations.
            Focus on actionable signals for Indian stock markets. Always respond in JSON format."""
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=0.3,  # Low temperature for consistent signal generation
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            
            try:
                signals_data = json.loads(content)
            except json.JSONDecodeError:
                signals_data = {
                    "signals": [],
                    "raw_content": content,
                    "error": "JSON parsing failed"
                }
            
            return {
                "signals": signals_data,
                "provider": "openai",
                "model": self.model,
                "tokens_used": response.usage.total_tokens if response.usage else 0
            }
            
        except Exception as e:
            return self._handle_error(e, "signals")
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test OpenAI API connection.
        
        Returns:
            Connection test results
        """
        if not self.is_available:
            return {"status": "unavailable", "reason": "Client not initialized"}
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Use cheaper model for testing
                messages=[{"role": "user", "content": "Hello, this is a connection test."}],
                max_tokens=10
            )
            
            return {
                "status": "connected", 
                "model": self.model,
                "test_response": response.choices[0].message.content
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)} 