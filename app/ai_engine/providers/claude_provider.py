"""
Claude (Anthropic) Provider Implementation
Enhanced implementation with improved reasoning capabilities
"""
import json
import anthropic
from typing import Dict, List, Optional, Any
from .base_provider import BaseAIProvider, ValidationResult, Message, ChatResponse, AnalysisResponse
import logging

logger = logging.getLogger(__name__)

class ClaudeProvider(BaseAIProvider):
    """Claude provider with enhanced reasoning for analysis tasks"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, "claude")
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.default_model = "claude-3-sonnet-20240229"
        self.analysis_model = "claude-3-opus-20240229"  # Best for complex analysis
        
        # Cost per 1K tokens (in cents)
        self.cost_per_1k_tokens = {
            "claude-3-opus-20240229": {"input": 1.5, "output": 7.5},
            "claude-3-sonnet-20240229": {"input": 0.3, "output": 1.5},
            "claude-3-haiku-20240307": {"input": 0.025, "output": 0.125}
        }
    
    async def validate_api_key(self, api_key: str) -> ValidationResult:
        """Validate Claude API key"""
        try:
            test_client = anthropic.AsyncAnthropic(api_key=api_key)
            response = await test_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=5,
                messages=[{"role": "user", "content": "Hello"}]
            )
            return ValidationResult(
                valid=True, 
                message="Claude API key is valid"
            )
        except anthropic.AuthenticationError:
            return ValidationResult(
                valid=False, 
                error="Invalid Claude API key"
            )
        except anthropic.RateLimitError:
            return ValidationResult(
                valid=True, 
                message="API key valid but rate limited"
            )
        except Exception as e:
            return ValidationResult(
                valid=False, 
                error=f"Claude validation error: {str(e)}"
            )
    
    async def generate_chat_response(
        self, 
        messages: List[Message], 
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> ChatResponse:
        """Generate chat response using Claude"""
        
        async def _generate():
            # Convert messages to Claude format (separate system message)
            system_message = None
            claude_messages = []
            
            for msg in messages:
                if msg.role == "system":
                    system_message = msg.content
                else:
                    claude_messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })
            
            # Create Claude request
            request_params = {
                "model": model or self.default_model,
                "messages": claude_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                **kwargs
            }
            
            if system_message:
                request_params["system"] = system_message
            
            response = await self.client.messages.create(**request_params)
            
            # Calculate cost
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            cost_cents = self.estimate_cost_detailed(
                response.usage.input_tokens,
                response.usage.output_tokens,
                model or self.default_model
            )
            
            # Update usage stats
            self.usage_stats.total_tokens += tokens_used
            self.usage_stats.total_cost_cents += cost_cents
            
            return ChatResponse(
                content=response.content[0].text,
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
        """Generate analysis using Claude's superior reasoning"""
        
        async def _generate():
            # Build analysis prompt with structured thinking
            analysis_prompt = self.build_analysis_prompt(prompt, data)
            
            response = await self.client.messages.create(
                model=model or self.analysis_model,
                system="You are Claude, an expert financial analyst with exceptional reasoning abilities. Think step-by-step and provide comprehensive, well-reasoned analysis.",
                messages=[{"role": "user", "content": analysis_prompt}],
                max_tokens=3000,
                temperature=0.2,  # Lower temperature for analysis
                **kwargs
            )
            
            # Calculate cost
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            cost_cents = self.estimate_cost_detailed(
                response.usage.input_tokens,
                response.usage.output_tokens,
                model or self.analysis_model
            )
            
            # Update usage stats
            self.usage_stats.total_tokens += tokens_used
            self.usage_stats.total_cost_cents += cost_cents
            
            return AnalysisResponse(
                analysis=response.content[0].text,
                confidence_score=0.9,  # Claude has high confidence in analysis
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
        """Generate structured output using Claude"""
        
        async def _generate():
            # Build structured prompt
            structured_prompt = f"""
{prompt}

Please respond with a JSON object that matches this exact schema:
{json.dumps(schema, indent=2)}

Think through your response step by step, then provide the final JSON object.
"""
            
            response = await self.client.messages.create(
                model=model or self.default_model,
                system="You are Claude, a helpful assistant that provides structured JSON responses. Always respond with valid JSON that matches the requested schema.",
                messages=[{"role": "user", "content": structured_prompt}],
                max_tokens=2000,
                temperature=0.1,
                **kwargs
            )
            
            content = response.content[0].text
            
            # Extract JSON from response
            try:
                # Try to parse the entire response as JSON
                structured_data = json.loads(content)
                
                # Update usage stats
                tokens_used = response.usage.input_tokens + response.usage.output_tokens
                cost_cents = self.estimate_cost_detailed(
                    response.usage.input_tokens,
                    response.usage.output_tokens,
                    model or self.default_model
                )
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
                
                logger.error(f"Failed to parse Claude structured response: {content}")
                raise ValueError("Invalid structured response from Claude")
        
        return await self.with_retry(_generate)
    
    async def check_availability(self) -> bool:
        """Check Claude service availability"""
        try:
            await self.client.messages.create(
                model="claude-3-haiku-20240307",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1
            )
            return True
        except Exception as e:
            logger.warning(f"Claude availability check failed: {e}")
            return False
    
    def get_supported_models(self) -> List[str]:
        """Get supported Claude models"""
        return [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229", 
            "claude-3-haiku-20240307"
        ]
    
    def estimate_cost(self, tokens: int, model: str = None) -> int:
        """Estimate cost in cents for given token count"""
        # Assume 75% input tokens, 25% output tokens
        input_tokens = int(tokens * 0.75)
        output_tokens = int(tokens * 0.25)
        return self.estimate_cost_detailed(input_tokens, output_tokens, model)
    
    def estimate_cost_detailed(self, input_tokens: int, output_tokens: int, model: str = None) -> int:
        """Estimate cost with detailed input/output token breakdown"""
        model = model or self.default_model
        
        if model not in self.cost_per_1k_tokens:
            model = "claude-3-sonnet-20240229"  # Default fallback
        
        input_cost = (input_tokens / 1000) * self.cost_per_1k_tokens[model]["input"]
        output_cost = (output_tokens / 1000) * self.cost_per_1k_tokens[model]["output"]
        
        return int((input_cost + output_cost) * 100)  # Convert to cents
    
    def build_analysis_prompt(self, prompt: str, data: Dict[str, Any]) -> str:
        """Build comprehensive analysis prompt with structured thinking"""
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

Please provide a comprehensive analysis following this structure:
1. **Situation Assessment**: Current state analysis
2. **Key Insights**: Important findings and patterns
3. **Risk Analysis**: Potential risks and mitigation strategies
4. **Opportunities**: Actionable opportunities identified
5. **Recommendations**: Specific, actionable recommendations
6. **Reasoning**: Step-by-step reasoning for your conclusions

Consider all provided context data and think through each aspect systematically.
"""