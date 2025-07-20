"""
Gemini (Google) Provider Implementation
Cost-effective implementation with good performance for various tasks
"""
import json
import google.generativeai as genai
from typing import Dict, List, Optional, Any
from .base_provider import BaseAIProvider, ValidationResult, Message, ChatResponse, AnalysisResponse
import logging

logger = logging.getLogger(__name__)

class GeminiProvider(BaseAIProvider):
    """Gemini provider optimized for cost-effectiveness"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, "gemini")
        genai.configure(api_key=api_key)
        self.default_model = "gemini-pro"
        self.analysis_model = "gemini-pro"
        
        # Cost per 1K tokens (in cents) - Gemini is very cost-effective
        self.cost_per_1k_tokens = {
            "gemini-pro": {"input": 0.05, "output": 0.15},
            "gemini-pro-vision": {"input": 0.05, "output": 0.15}
        }
    
    async def validate_api_key(self, api_key: str) -> ValidationResult:
        """Validate Gemini API key"""
        try:
            # Configure with test key
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-pro')
            
            # Test with a simple prompt
            response = model.generate_content("Hello", 
                generation_config=genai.types.GenerationConfig(max_output_tokens=5))
            
            return ValidationResult(
                valid=True, 
                message="Gemini API key is valid"
            )
        except Exception as e:
            error_str = str(e).lower()
            if "api key" in error_str or "authentication" in error_str:
                return ValidationResult(
                    valid=False, 
                    error="Invalid Gemini API key"
                )
            elif "quota" in error_str or "rate limit" in error_str:
                return ValidationResult(
                    valid=True, 
                    message="API key valid but rate limited"
                )
            else:
                return ValidationResult(
                    valid=False, 
                    error=f"Gemini validation error: {str(e)}"
                )
    
    async def generate_chat_response(
        self, 
        messages: List[Message], 
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> ChatResponse:
        """Generate chat response using Gemini"""
        
        async def _generate():
            # Initialize model
            gemini_model = genai.GenerativeModel(model or self.default_model)
            
            # Convert messages to Gemini format
            # Gemini uses a different conversation format
            conversation_parts = []
            for msg in messages:
                if msg.role == "system":
                    # Add system message as context
                    conversation_parts.append(f"System: {msg.content}")
                elif msg.role == "user":
                    conversation_parts.append(f"User: {msg.content}")
                elif msg.role == "assistant":
                    conversation_parts.append(f"Assistant: {msg.content}")
            
            # Combine into single prompt for Gemini
            prompt = "\n".join(conversation_parts)
            if not prompt.endswith("User:"):
                prompt += "\nAssistant:"
            
            # Generate response
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                **kwargs
            )
            
            response = gemini_model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Extract content
            content = response.text if response.text else ""
            
            # Estimate tokens (Gemini doesn't provide exact token counts)
            tokens_used = self.estimate_tokens(prompt + content)
            cost_cents = self.estimate_cost(tokens_used, model or self.default_model)
            
            # Update usage stats
            self.usage_stats.total_tokens += tokens_used
            self.usage_stats.total_cost_cents += cost_cents
            
            return ChatResponse(
                content=content,
                tokens_used=tokens_used,
                cost_cents=cost_cents,
                model_used=model or self.default_model
            )
        
        return await self.with_retry(_generate)
    
    async def generate_analysis(
        self, 
        prompt: str, 
        data: Dict[str, Any], 
        model: str = None,
        **kwargs
    ) -> AnalysisResponse:
        """Generate analysis using Gemini"""
        
        async def _generate():
            # Build analysis prompt
            analysis_prompt = self.build_analysis_prompt(prompt, data)
            
            # Initialize model
            gemini_model = genai.GenerativeModel(model or self.analysis_model)
            
            # Generate analysis
            generation_config = genai.types.GenerationConfig(
                temperature=0.3,  # Lower temperature for analysis
                max_output_tokens=2000,
                **kwargs
            )
            
            response = gemini_model.generate_content(
                analysis_prompt,
                generation_config=generation_config
            )
            
            content = response.text if response.text else ""
            
            # Estimate tokens and cost
            tokens_used = self.estimate_tokens(analysis_prompt + content)
            cost_cents = self.estimate_cost(tokens_used, model or self.analysis_model)
            
            # Update usage stats
            self.usage_stats.total_tokens += tokens_used
            self.usage_stats.total_cost_cents += cost_cents
            
            return AnalysisResponse(
                analysis=content,
                confidence_score=0.75,  # Good confidence for Gemini
                tokens_used=tokens_used,
                cost_cents=cost_cents,
                model_used=model or self.analysis_model
            )
        
        return await self.with_retry(_generate)
    
    async def generate_structured_output(
        self, 
        prompt: str, 
        schema: Dict[str, Any], 
        model: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate structured output using Gemini"""
        
        async def _generate():
            # Build structured prompt
            structured_prompt = f"""
{prompt}

Please respond with a JSON object that matches this exact schema:
{json.dumps(schema, indent=2)}

Important: Respond ONLY with valid JSON. Do not include any explanatory text before or after the JSON.
"""
            
            # Initialize model
            gemini_model = genai.GenerativeModel(model or self.default_model)
            
            # Generate structured response
            generation_config = genai.types.GenerationConfig(
                temperature=0.1,  # Very low temperature for structured output
                max_output_tokens=1500,
                **kwargs
            )
            
            response = gemini_model.generate_content(
                structured_prompt,
                generation_config=generation_config
            )
            
            content = response.text if response.text else ""
            
            # Extract JSON from response
            try:
                # Clean up the response (remove markdown formatting if present)
                cleaned_content = content.strip()
                if cleaned_content.startswith("```json"):
                    cleaned_content = cleaned_content[7:]
                if cleaned_content.endswith("```"):
                    cleaned_content = cleaned_content[:-3]
                cleaned_content = cleaned_content.strip()
                
                # Parse JSON
                structured_data = json.loads(cleaned_content)
                
                # Update usage stats
                tokens_used = self.estimate_tokens(structured_prompt + content)
                cost_cents = self.estimate_cost(tokens_used, model or self.default_model)
                self.usage_stats.total_tokens += tokens_used
                self.usage_stats.total_cost_cents += cost_cents
                
                return structured_data
                
            except json.JSONDecodeError:
                # Try to extract JSON from the response
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    try:
                        structured_data = json.loads(json_match.group(0))
                        return structured_data
                    except json.JSONDecodeError:
                        pass
                
                logger.error(f"Failed to parse Gemini structured response: {content}")
                raise ValueError("Invalid structured response from Gemini")
        
        return await self.with_retry(_generate)
    
    async def check_availability(self) -> bool:
        """Check Gemini service availability"""
        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content("ping", 
                generation_config=genai.types.GenerationConfig(max_output_tokens=1))
            return True
        except Exception as e:
            logger.warning(f"Gemini availability check failed: {e}")
            return False
    
    def get_supported_models(self) -> List[str]:
        """Get supported Gemini models"""
        return [
            "gemini-pro",
            "gemini-pro-vision"
        ]
    
    def estimate_cost(self, tokens: int, model: str = None) -> int:
        """Estimate cost in cents for given token count"""
        model = model or self.default_model
        
        if model not in self.cost_per_1k_tokens:
            model = "gemini-pro"  # Default fallback
        
        # Assume 75% input tokens, 25% output tokens
        input_tokens = int(tokens * 0.75)
        output_tokens = int(tokens * 0.25)
        
        input_cost = (input_tokens / 1000) * self.cost_per_1k_tokens[model]["input"]
        output_cost = (output_tokens / 1000) * self.cost_per_1k_tokens[model]["output"]
        
        return int((input_cost + output_cost) * 100)  # Convert to cents
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (rough approximation)"""
        # Rough estimation: ~4 characters per token
        return len(text) // 4
    
    def build_analysis_prompt(self, prompt: str, data: Dict[str, Any]) -> str:
        """Build comprehensive analysis prompt"""
        context_parts = []
        
        if "portfolio" in data:
            context_parts.append(f"Portfolio Data: {json.dumps(data['portfolio'], indent=2)}")
        
        if "market_data" in data:
            context_parts.append(f"Market Data: {json.dumps(data['market_data'], indent=2)}")
        
        if "user_preferences" in data:
            context_parts.append(f"User Preferences: {json.dumps(data['user_preferences'], indent=2)}")
        
        context = "\n\n".join(context_parts)
        
        return f"""
You are an expert financial analyst. Provide comprehensive analysis based on the following request and context.

Request: {prompt}

Context Information:
{context}

Please provide detailed analysis covering:
1. Current situation assessment
2. Key insights and patterns
3. Risk factors and opportunities
4. Actionable recommendations

Be specific and provide reasoning for your conclusions.
"""