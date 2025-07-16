"""
Gemini Client

Isolated client wrapper for Google Gemini API integration.
Handles Gemini-specific implementation details while providing a consistent interface.
"""
import os
import logging
from typing import Dict, Any, Optional
import json

from .base_provider import BaseAIProvider

logger = logging.getLogger(__name__)


class GeminiClient(BaseAIProvider):
    """
    Google Gemini API client for trading analysis and strategy generation.
    
    Features:
    - Gemini Pro for general tasks
    - Strong multimodal capabilities
    - Good performance-to-cost ratio
    - Real-time data integration friendly
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-pro", **kwargs):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Google API key (defaults to environment variable)
            model: Model to use (gemini-pro, gemini-pro-vision, etc.)
            **kwargs: Additional configuration
        """
        # Get API key from environment if not provided
        if not api_key:
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        super().__init__(api_key, **kwargs)
        self.model = model
        self.temperature = kwargs.get("temperature", 0.7)
        
        # Initialize Gemini client only if API key is available
        self.client = None
        if self.api_key:
            try:
                # Import google.generativeai only when needed
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.client = genai.GenerativeModel(self.model)
                logger.info(f"Gemini client initialized with model: {self.model}")
            except ImportError:
                logger.error("Google GenerativeAI library not installed. Install with: pip install google-generativeai")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {str(e)}")
    
    @property
    def is_available(self) -> bool:
        """Check if Gemini client is available and configured"""
        return self.client is not None and self.api_key is not None
    
    async def generate_analysis(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate market analysis using Gemini.
        
        Args:
            prompt: Analysis prompt
            context: Additional context data
            
        Returns:
            Analysis response from Gemini
        """
        if not self.is_available:
            return self._handle_error(Exception("Gemini client not available"), "analysis")
        
        try:
            # Create enhanced prompt with system instructions
            system_instruction = """You are an expert financial analyst specializing in Indian stock markets, 
            technical analysis, and portfolio optimization. Provide detailed, data-driven insights with clear 
            reasoning and actionable recommendations. Focus on practical applications for retail investors."""
            
            enhanced_prompt = f"{system_instruction}\n\n{prompt}"
            
            # Gemini doesn't have async API yet, so we'll simulate it
            import asyncio
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.client.generate_content, enhanced_prompt
            )
            
            content = response.text if response and hasattr(response, 'text') else ""
            
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
                "provider": "gemini",
                "model": self.model,
                "tokens_used": len(content.split()) if content else 0  # Approximate token count
            }
            
        except Exception as e:
            return self._handle_error(e, "analysis")
    
    async def generate_strategy(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate trading strategy using Gemini.
        
        Args:
            prompt: Strategy generation prompt
            context: Additional context data
            
        Returns:
            Strategy response from Gemini
        """
        if not self.is_available:
            return self._handle_error(Exception("Gemini client not available"), "strategy")
        
        try:
            # Enhanced prompt with explicit JSON structure request
            system_instruction = """You are an expert algorithmic trading strategist with deep knowledge of 
            systematic trading approaches, risk management, and quantitative analysis. Create detailed, 
            executable trading strategies with precise rules and robust risk controls."""
            
            enhanced_prompt = f"""{system_instruction}

{prompt}

IMPORTANT: Respond with a valid JSON object using this exact structure:
{{
    "strategy_name": "descriptive name",
    "description": "detailed description",
    "entry_conditions": ["condition1", "condition2"],
    "exit_conditions": ["condition1", "condition2"],
    "position_sizing": "sizing methodology",
    "risk_management": ["rule1", "rule2"],
    "timeframe": "holding period",
    "expected_returns": "return expectations",
    "implementation_steps": ["step1", "step2", "step3"]
}}"""
            
            import asyncio
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.client.generate_content, enhanced_prompt
            )
            
            content = response.text if response and hasattr(response, 'text') else ""
            
            try:
                strategy_data = json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from response if wrapped in other text
                try:
                    start = content.find('{')
                    end = content.rfind('}') + 1
                    if start >= 0 and end > start:
                        strategy_data = json.loads(content[start:end])
                    else:
                        raise json.JSONDecodeError("No JSON found", content, 0)
                except json.JSONDecodeError:
                    # Final fallback
                    strategy_data = {
                        "strategy_name": "AI Generated Strategy",
                        "description": content,
                        "error": "JSON parsing failed - content returned as description"
                    }
            
            return {
                "strategy": strategy_data,
                "provider": "gemini",
                "model": self.model,
                "tokens_used": len(content.split()) if content else 0
            }
            
        except Exception as e:
            return self._handle_error(e, "strategy")
    
    async def generate_signals(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate trading signals using Gemini.
        
        Args:
            prompt: Signals generation prompt
            context: Additional context data
            
        Returns:
            Signals response from Gemini
        """
        if not self.is_available:
            return self._handle_error(Exception("Gemini client not available"), "signals")
        
        try:
            system_instruction = """You are a professional trading signal generator with expertise in 
            technical analysis, market patterns, and risk assessment. Generate precise buy/sell/hold 
            signals with confidence levels and risk parameters for Indian stock markets."""
            
            enhanced_prompt = f"""{system_instruction}

{prompt}

Please respond with a valid JSON object in this format:
{{
    "signals": [
        {{
            "symbol": "stock symbol",
            "action": "buy/sell/hold",
            "confidence": 0.85,
            "target_price": 1250.50,
            "stop_loss": 1150.00,
            "reasoning": "explanation for the signal"
        }}
    ],
    "market_outlook": "overall market assessment",
    "risk_level": "low/medium/high",
    "timestamp": "analysis timestamp"
}}"""
            
            import asyncio
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.client.generate_content, enhanced_prompt
            )
            
            content = response.text if response and hasattr(response, 'text') else ""
            
            try:
                signals_data = json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                try:
                    start = content.find('{')
                    end = content.rfind('}') + 1
                    if start >= 0 and end > start:
                        signals_data = json.loads(content[start:end])
                    else:
                        raise json.JSONDecodeError("No JSON found", content, 0)
                except json.JSONDecodeError:
                    signals_data = {
                        "signals": [],
                        "raw_content": content,
                        "error": "JSON parsing failed"
                    }
            
            return {
                "signals": signals_data,
                "provider": "gemini",
                "model": self.model,
                "tokens_used": len(content.split()) if content else 0
            }
            
        except Exception as e:
            return self._handle_error(e, "signals")
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test Gemini API connection.
        
        Returns:
            Connection test results
        """
        if not self.is_available:
            return {"status": "unavailable", "reason": "Client not initialized"}
        
        try:
            import asyncio
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.client.generate_content, "Hello, this is a connection test. Respond with 'Connected'."
            )
            
            test_response = response.text if response and hasattr(response, 'text') else "No response"
            
            return {
                "status": "connected", 
                "model": self.model,
                "test_response": test_response
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)} 