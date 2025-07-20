"""
OpenAI Provider Implementation
Enhanced implementation with structured output and comprehensive error handling
"""
import json
import openai
from typing import Dict, List, Optional, Any
from .base_provider import BaseAIProvider, ValidationResult, Message, ChatResponse, AnalysisResponse
import logging

logger = logging.getLogger(__name__)

class OpenAIProvider(BaseAIProvider):
    """Enhanced OpenAI provider with GPT-4 and structured output support"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, "openai")
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.default_model = "gpt-4"
        self.chat_model = "gpt-4"
        self.analysis_model = "gpt-4"
        
        # Cost per 1K tokens (in cents)
        self.cost_per_1k_tokens = {
            "gpt-4": {"input": 3.0, "output": 6.0},
            "gpt-4-turbo": {"input": 1.0, "output": 3.0},
            "gpt-3.5-turbo": {"input": 0.15, "output": 0.2}
        }
    
    async def validate_api_key(self, api_key: str) -> ValidationResult:
        """Validate OpenAI API key"""
        try:
            test_client = openai.AsyncOpenAI(api_key=api_key)
            response = await test_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            return ValidationResult(
                valid=True, 
                message="OpenAI API key is valid"
            )
        except openai.AuthenticationError:
            return ValidationResult(
                valid=False, 
                error="Invalid OpenAI API key"
            )
        except openai.RateLimitError:
            return ValidationResult(
                valid=True, 
                message="API key valid but rate limited"
            )
        except Exception as e:
            return ValidationResult(
                valid=False, 
                error=f"OpenAI validation error: {str(e)}"
            )
    
    async def generate_chat_response(
        self, 
        messages: List[Message], 
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> ChatResponse:
        """Generate chat response using OpenAI"""
        
        async def _generate():
            # Convert messages to OpenAI format
            openai_messages = [
                {"role": msg.role, "content": msg.content} 
                for msg in messages
            ]
            
            response = await self.client.chat.completions.create(
                model=model or self.chat_model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            # Calculate cost
            tokens_used = response.usage.total_tokens
            cost_cents = self.estimate_cost(tokens_used, model or self.chat_model)
            
            # Update usage stats
            self.usage_stats.total_tokens += tokens_used
            self.usage_stats.total_cost_cents += cost_cents
            
            return ChatResponse(
                content=response.choices[0].message.content,
                tokens_used=tokens_used,
                cost_cents=cost_cents,
                model_used=response.model
            )
        
        return await self.with_retry(_generate)
    
    async def generate_analysis(
        self, 
        prompt: str, 
        data: Dict[str, Any], 
        model: str = None,
        **kwargs
    ) -> AnalysisResponse:
        """Generate analysis using OpenAI"""
        
        async def _generate():
            # Build analysis prompt with data context
            analysis_prompt = self.build_analysis_prompt(prompt, data)
            
            response = await self.client.chat.completions.create(
                model=model or self.analysis_model,
                messages=[
                    {"role": "system", "content": "You are an expert financial analyst. Provide detailed, actionable analysis."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.3,  # Lower temperature for analysis
                max_tokens=2000,
                **kwargs
            )
            
            # Calculate cost
            tokens_used = response.usage.total_tokens
            cost_cents = self.estimate_cost(tokens_used, model or self.analysis_model)
            
            # Update usage stats
            self.usage_stats.total_tokens += tokens_used
            self.usage_stats.total_cost_cents += cost_cents
            
            return AnalysisResponse(
                analysis=response.choices[0].message.content,
                confidence_score=0.8,  # Default confidence for OpenAI
                tokens_used=tokens_used,
                cost_cents=cost_cents,
                model_used=response.model
            )
        
        return await self.with_retry(_generate)
    
    async def generate_structured_output(
        self, 
        prompt: str, 
        schema: Dict[str, Any], 
        model: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate structured output using OpenAI function calling"""
        
        async def _generate():
            # Create function definition from schema
            function_def = {
                "name": "structured_response",
                "description": "Generate structured response according to schema",
                "parameters": schema
            }
            
            response = await self.client.chat.completions.create(
                model=model or self.default_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that provides structured responses."},
                    {"role": "user", "content": prompt}
                ],
                functions=[function_def],
                function_call={"name": "structured_response"},
                temperature=0.3,
                **kwargs
            )
            
            # Extract structured data from function call
            function_call = response.choices[0].message.function_call
            if function_call and function_call.arguments:
                try:
                    structured_data = json.loads(function_call.arguments)
                    
                    # Update usage stats
                    tokens_used = response.usage.total_tokens
                    cost_cents = self.estimate_cost(tokens_used, model or self.default_model)
                    self.usage_stats.total_tokens += tokens_used
                    self.usage_stats.total_cost_cents += cost_cents
                    
                    return structured_data
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse OpenAI function call response: {e}")
                    raise ValueError("Invalid structured response from OpenAI")
            
            raise ValueError("No structured response received from OpenAI")
        
        return await self.with_retry(_generate)
    
    async def check_availability(self) -> bool:
        """Check OpenAI service availability"""
        try:
            await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1
            )
            return True
        except Exception as e:
            logger.warning(f"OpenAI availability check failed: {e}")
            return False
    
    def get_supported_models(self) -> List[str]:
        """Get supported OpenAI models"""
        return [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k"
        ]
    
    def estimate_cost(self, tokens: int, model: str = None) -> int:
        """Estimate cost in cents for given token count"""
        model = model or self.default_model
        
        if model not in self.cost_per_1k_tokens:
            model = "gpt-4"  # Default fallback
        
        # Assume 75% input tokens, 25% output tokens
        input_tokens = int(tokens * 0.75)
        output_tokens = int(tokens * 0.25)
        
        input_cost = (input_tokens / 1000) * self.cost_per_1k_tokens[model]["input"]
        output_cost = (output_tokens / 1000) * self.cost_per_1k_tokens[model]["output"]
        
        return int((input_cost + output_cost) * 100)  # Convert to cents
    
    def build_analysis_prompt(self, prompt: str, data: Dict[str, Any]) -> str:
        """Build comprehensive analysis prompt with data context"""
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

Please provide a comprehensive analysis considering all the provided context data.
"""