"""
Grok (xAI) Provider Implementation
Implementation for xAI's Grok model with real-time data capabilities
"""
import json
import httpx
from typing import Dict, List, Optional, Any
from .base_provider import BaseAIProvider, ValidationResult, Message, ChatResponse, AnalysisResponse
import logging

logger = logging.getLogger(__name__)

class GrokProvider(BaseAIProvider):
    """Grok provider with real-time data and Twitter integration"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, "grok")
        self.base_url = "https://api.x.ai/v1"
        self.client = httpx.AsyncClient(timeout=30.0)
        self.default_model = "grok-beta"
        
        # Cost per 1K tokens (estimated, adjust based on actual pricing)
        self.cost_per_1k_tokens = {
            "grok-beta": {"input": 2.0, "output": 4.0}
        }
    
    async def validate_api_key(self, api_key: str) -> ValidationResult:
        """Validate Grok API key"""
        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "grok-beta",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 5
                }
            )
            
            if response.status_code == 200:
                return ValidationResult(
                    valid=True, 
                    message="Grok API key is valid"
                )
            elif response.status_code == 401:
                return ValidationResult(
                    valid=False, 
                    error="Invalid Grok API key"
                )
            elif response.status_code == 429:
                return ValidationResult(
                    valid=True, 
                    message="API key valid but rate limited"
                )
            else:
                return ValidationResult(
                    valid=False, 
                    error=f"Grok API error: {response.status_code}"
                )
                
        except Exception as e:
            return ValidationResult(
                valid=False, 
                error=f"Grok validation error: {str(e)}"
            )
    
    async def generate_chat_response(
        self, 
        messages: List[Message], 
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> ChatResponse:
        """Generate chat response using Grok"""
        
        async def _generate():
            # Convert messages to Grok format
            grok_messages = [
                {"role": msg.role, "content": msg.content} 
                for msg in messages
            ]
            
            # Add system message for Grok's personality
            if not any(msg["role"] == "system" for msg in grok_messages):
                grok_messages.insert(0, {
                    "role": "system", 
                    "content": "You are Grok, a witty and helpful AI assistant with access to real-time information. Provide accurate, up-to-date responses with a touch of humor when appropriate."
                })
            
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model or self.default_model,
                    "messages": grok_messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    **kwargs
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Grok API error: {response.status_code} - {response.text}")
            
            data = response.json()
            
            # Extract response content
            content = data["choices"][0]["message"]["content"]
            tokens_used = data.get("usage", {}).get("total_tokens", 0)
            
            # Calculate cost
            cost_cents = self.estimate_cost(tokens_used, model or self.default_model)
            
            # Update usage stats
            self.usage_stats.total_tokens += tokens_used
            self.usage_stats.total_cost_cents += cost_cents
            
            return ChatResponse(
                content=content,
                tokens_used=tokens_used,
                cost_cents=cost_cents,
                model_used=data.get("model", model or self.default_model)
            )
        
        return await self.with_retry(_generate)
    
    async def generate_analysis(
        self, 
        prompt: str, 
        data: Dict[str, Any], 
        model: str = None,
        **kwargs
    ) -> AnalysisResponse:
        """Generate analysis using Grok with real-time data"""
        
        async def _generate():
            # Build analysis prompt with real-time context
            analysis_prompt = self.build_analysis_prompt(prompt, data)
            
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model or self.default_model,
                    "messages": [
                        {
                            "role": "system", 
                            "content": "You are Grok, an expert financial analyst with access to real-time market data and social sentiment. Provide detailed, actionable analysis with current market context."
                        },
                        {"role": "user", "content": analysis_prompt}
                    ],
                    "temperature": 0.3,  # Lower temperature for analysis
                    "max_tokens": 2000,
                    **kwargs
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Grok API error: {response.status_code} - {response.text}")
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            tokens_used = data.get("usage", {}).get("total_tokens", 0)
            
            # Calculate cost
            cost_cents = self.estimate_cost(tokens_used, model or self.default_model)
            
            # Update usage stats
            self.usage_stats.total_tokens += tokens_used
            self.usage_stats.total_cost_cents += cost_cents
            
            return AnalysisResponse(
                analysis=content,
                confidence_score=0.85,  # Grok has high confidence with real-time data
                tokens_used=tokens_used,
                cost_cents=cost_cents,
                model_used=data.get("model", model or self.default_model)
            )
        
        return await self.with_retry(_generate)
    
    async def generate_structured_output(
        self, 
        prompt: str, 
        schema: Dict[str, Any], 
        model: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate structured output using Grok"""
        
        async def _generate():
            # Build structured prompt with schema
            structured_prompt = f"""
{prompt}

Please respond with a JSON object that matches this exact schema:
{json.dumps(schema, indent=2)}

Ensure your response is valid JSON and follows the schema exactly.
"""
            
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model or self.default_model,
                    "messages": [
                        {
                            "role": "system", 
                            "content": "You are Grok, a helpful assistant that provides structured JSON responses. Always respond with valid JSON that matches the requested schema."
                        },
                        {"role": "user", "content": structured_prompt}
                    ],
                    "temperature": 0.1,  # Very low temperature for structured output
                    **kwargs
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Grok API error: {response.status_code} - {response.text}")
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            # Extract JSON from response
            try:
                # Try to parse the entire response as JSON
                structured_data = json.loads(content)
                
                # Update usage stats
                tokens_used = data.get("usage", {}).get("total_tokens", 0)
                cost_cents = self.estimate_cost(tokens_used, model or self.default_model)
                self.usage_stats.total_tokens += tokens_used
                self.usage_stats.total_cost_cents += cost_cents
                
                return structured_data
                
            except json.JSONDecodeError:
                # Try to extract JSON from markdown code blocks
                import re
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
                if json_match:
                    try:
                        structured_data = json.loads(json_match.group(1))
                        return structured_data
                    except json.JSONDecodeError:
                        pass
                
                logger.error(f"Failed to parse Grok structured response: {content}")
                raise ValueError("Invalid structured response from Grok")
        
        return await self.with_retry(_generate)
    
    async def check_availability(self) -> bool:
        """Check Grok service availability"""
        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "grok-beta",
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1
                }
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Grok availability check failed: {e}")
            return False
    
    def get_supported_models(self) -> List[str]:
        """Get supported Grok models"""
        return ["grok-beta"]
    
    def estimate_cost(self, tokens: int, model: str = None) -> int:
        """Estimate cost in cents for given token count"""
        model = model or self.default_model
        
        if model not in self.cost_per_1k_tokens:
            model = "grok-beta"  # Default fallback
        
        # Assume 75% input tokens, 25% output tokens
        input_tokens = int(tokens * 0.75)
        output_tokens = int(tokens * 0.25)
        
        input_cost = (input_tokens / 1000) * self.cost_per_1k_tokens[model]["input"]
        output_cost = (output_tokens / 1000) * self.cost_per_1k_tokens[model]["output"]
        
        return int((input_cost + output_cost) * 100)  # Convert to cents
    
    def build_analysis_prompt(self, prompt: str, data: Dict[str, Any]) -> str:
        """Build comprehensive analysis prompt with real-time context"""
        context_parts = []
        
        if "portfolio" in data:
            context_parts.append(f"Portfolio Data: {json.dumps(data['portfolio'], indent=2)}")
        
        if "market_data" in data:
            context_parts.append(f"Market Data: {json.dumps(data['market_data'], indent=2)}")
        
        if "user_preferences" in data:
            context_parts.append(f"User Preferences: {json.dumps(data['user_preferences'], indent=2)}")
        
        context = "\n\n".join(context_parts)
        
        return f"""
{prompt}

Context Information:
{context}

Please provide a comprehensive analysis considering:
1. Current market conditions and real-time data
2. Social sentiment and news trends
3. Technical and fundamental factors
4. Risk assessment and opportunities

Use your access to real-time information to provide the most current insights.
"""
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()