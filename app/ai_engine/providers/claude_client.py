"""
Claude Client

Isolated client wrapper for Anthropic Claude API integration.
Handles Claude-specific implementation details while providing a consistent interface.
"""
import os
import logging
from typing import Dict, Any, Optional
import json

from .base_provider import BaseAIProvider

logger = logging.getLogger(__name__)


class ClaudeClient(BaseAIProvider):
    """
    Anthropic Claude API client for trading analysis and strategy generation.
    
    Features:
    - Claude-3.5 Sonnet for complex reasoning
    - Strong analytical capabilities
    - Large context window
    - Structured thinking
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022", **kwargs):
        """
        Initialize Claude client.
        
        Args:
            api_key: Anthropic API key (defaults to environment variable)
            model: Model to use (claude-3-5-sonnet, claude-3-haiku, etc.)
            **kwargs: Additional configuration
        """
        # Get API key from environment if not provided
        if not api_key:
            api_key = os.getenv("ANTHROPIC_API_KEY")
        
        super().__init__(api_key, **kwargs)
        self.model = model
        self.max_tokens = kwargs.get("max_tokens", 4000)
        self.temperature = kwargs.get("temperature", 0.7)
        
        # Initialize Claude client only if API key is available
        self.client = None
        if self.api_key:
            try:
                # Import anthropic only when needed to avoid dependency issues
                import anthropic
                self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
                logger.info(f"Claude client initialized with model: {self.model}")
            except ImportError:
                logger.error("Anthropic library not installed. Install with: pip install anthropic")
            except Exception as e:
                logger.error(f"Failed to initialize Claude client: {str(e)}")
    
    @property
    def is_available(self) -> bool:
        """Check if Claude client is available and configured"""
        return self.client is not None and self.api_key is not None
    
    async def generate_analysis(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate market analysis using Claude.
        
        Args:
            prompt: Analysis prompt
            context: Additional context data
            
        Returns:
            Analysis response from Claude
        """
        if not self.is_available:
            return self._handle_error(Exception("Claude client not available"), "analysis")
        
        try:
            system_prompt = """You are an expert financial analyst with deep expertise in Indian stock markets, 
            portfolio management, and quantitative analysis. You excel at breaking down complex market data 
            and providing clear, actionable insights. Focus on practical recommendations with clear reasoning."""
            
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = message.content[0].text if message.content else ""
            
            # Try to parse as JSON if requested, fallback to structured text
            try:
                if "json" in prompt.lower():
                    parsed_content = json.loads(content)
                else:
                    parsed_content = {"analysis": content}
            except json.JSONDecodeError:
                parsed_content = {"analysis": content}
            
            return {
                "content": parsed_content,
                "provider": "claude",
                "model": self.model,
                "tokens_used": getattr(message.usage, 'input_tokens', 0) + getattr(message.usage, 'output_tokens', 0)
            }
            
        except Exception as e:
            return self._handle_error(e, "analysis")
    
    async def generate_strategy(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate trading strategy using Claude.
        
        Args:
            prompt: Strategy generation prompt
            context: Additional context data
            
        Returns:
            Strategy response from Claude
        """
        if not self.is_available:
            return self._handle_error(Exception("Claude client not available"), "strategy")
        
        try:
            system_prompt = """You are an expert trading strategy developer with deep knowledge of algorithmic trading, 
            risk management, and systematic investment approaches. You excel at creating detailed, executable strategies 
            with clear rules and robust risk management. Focus on strategies suitable for Indian stock markets."""
            
            # Claude works better with explicit JSON formatting instructions
            enhanced_prompt = f"""{prompt}

Please structure your response as a valid JSON object with the following format:
{{
    "strategy_name": "string",
    "description": "string", 
    "entry_conditions": ["list", "of", "conditions"],
    "exit_conditions": ["list", "of", "conditions"],
    "position_sizing": "string",
    "risk_management": ["list", "of", "rules"],
    "timeframe": "string",
    "expected_returns": "string",
    "implementation_steps": ["step1", "step2", "step3"]
}}"""
            
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=0.5,  # Lower temperature for more consistent strategy generation
                system=system_prompt,
                messages=[{"role": "user", "content": enhanced_prompt}]
            )
            
            content = message.content[0].text if message.content else ""
            
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
                "provider": "claude",
                "model": self.model,
                "tokens_used": getattr(message.usage, 'input_tokens', 0) + getattr(message.usage, 'output_tokens', 0)
            }
            
        except Exception as e:
            return self._handle_error(e, "strategy")
    
    async def generate_signals(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate trading signals using Claude.
        
        Args:
            prompt: Signals generation prompt
            context: Additional context data
            
        Returns:
            Signals response from Claude
        """
        if not self.is_available:
            return self._handle_error(Exception("Claude client not available"), "signals")
        
        try:
            system_prompt = """You are a professional trading signal generator with expertise in technical analysis, 
            market timing, and risk assessment. You excel at generating clear, actionable trading signals with 
            appropriate confidence levels and risk parameters. Focus on Indian stock markets."""
            
            # Structure the prompt for better JSON output
            enhanced_prompt = f"""{prompt}

Please provide trading signals in the following JSON format:
{{
    "signals": [
        {{
            "symbol": "string",
            "action": "buy/sell/hold",
            "confidence": 0.0-1.0,
            "target_price": "number",
            "stop_loss": "number",
            "reasoning": "string"
        }}
    ],
    "market_outlook": "string",
    "risk_level": "low/medium/high"
}}"""
            
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=0.3,  # Low temperature for consistent signal generation
                system=system_prompt,
                messages=[{"role": "user", "content": enhanced_prompt}]
            )
            
            content = message.content[0].text if message.content else ""
            
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
                "provider": "claude",
                "model": self.model,
                "tokens_used": getattr(message.usage, 'input_tokens', 0) + getattr(message.usage, 'output_tokens', 0)
            }
            
        except Exception as e:
            return self._handle_error(e, "signals")
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test Claude API connection.
        
        Returns:
            Connection test results
        """
        if not self.is_available:
            return {"status": "unavailable", "reason": "Client not initialized"}
        
        try:
            message = await self.client.messages.create(
                model="claude-3-haiku-20240307",  # Use faster model for testing
                max_tokens=10,
                messages=[{"role": "user", "content": "Hello, this is a connection test."}]
            )
            
            return {
                "status": "connected", 
                "model": self.model,
                "test_response": message.content[0].text if message.content else "No response"
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)} 