"""
AI Orchestrator
Central coordinator for AI operations with intelligent provider selection
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from .providers import (
    BaseAIProvider, OpenAIProvider, ClaudeProvider, 
    GeminiProvider, GrokProvider, ValidationResult, Message
)
from .models import (
    AIPreferences, ChatRequest, ChatResponse, 
    AnalysisRequest, AnalysisResponse, StrategyRequest, StrategyResponse,
    SignalsRequest, SignalsResponse
)

logger = logging.getLogger(__name__)

class AIOrchestrator:
    """
    Central AI orchestrator that manages provider selection, load balancing,
    and intelligent routing of AI requests
    """
    
    # Provider preferences by task type (ordered by preference)
    PROVIDER_PREFERENCES = {
        "chat": ["openai", "claude", "grok", "gemini"],
        "technical_analysis": ["claude", "openai", "grok", "gemini"],
        "fundamental_analysis": ["openai", "claude", "grok", "gemini"],
        "strategy_generation": ["openai", "claude", "grok", "gemini"],
        "sentiment_analysis": ["grok", "claude", "gemini", "openai"],
        "portfolio_optimization": ["claude", "openai", "grok", "gemini"],
        "structured_output": ["openai", "claude", "grok", "gemini"],
        "cost_effective": ["gemini", "grok", "claude", "openai"]
    }
    
    def __init__(self):
        self.providers: Dict[str, BaseAIProvider] = {}
        self.provider_health: Dict[str, Dict[str, Any]] = {}
        self.last_health_check = None
        self.health_check_interval = timedelta(minutes=5)
        
    async def initialize_providers(self, user_preferences: AIPreferences) -> Dict[str, bool]:
        """Initialize AI providers based on user preferences"""
        initialization_results = {}
        
        # Initialize OpenAI
        if user_preferences.openai_api_key:
            try:
                self.providers["openai"] = OpenAIProvider(user_preferences.openai_api_key)
                validation = await self.providers["openai"].validate_api_key(user_preferences.openai_api_key)
                initialization_results["openai"] = validation.valid
                if not validation.valid:
                    logger.warning(f"OpenAI validation failed: {validation.error}")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI provider: {e}")
                initialization_results["openai"] = False
        
        # Initialize Claude
        if user_preferences.claude_api_key:
            try:
                self.providers["claude"] = ClaudeProvider(user_preferences.claude_api_key)
                validation = await self.providers["claude"].validate_api_key(user_preferences.claude_api_key)
                initialization_results["claude"] = validation.valid
                if not validation.valid:
                    logger.warning(f"Claude validation failed: {validation.error}")
            except Exception as e:
                logger.error(f"Failed to initialize Claude provider: {e}")
                initialization_results["claude"] = False
        
        # Initialize Gemini
        if user_preferences.gemini_api_key:
            try:
                self.providers["gemini"] = GeminiProvider(user_preferences.gemini_api_key)
                validation = await self.providers["gemini"].validate_api_key(user_preferences.gemini_api_key)
                initialization_results["gemini"] = validation.valid
                if not validation.valid:
                    logger.warning(f"Gemini validation failed: {validation.error}")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini provider: {e}")
                initialization_results["gemini"] = False
        
        # Initialize Grok
        if user_preferences.grok_api_key:
            try:
                self.providers["grok"] = GrokProvider(user_preferences.grok_api_key)
                validation = await self.providers["grok"].validate_api_key(user_preferences.grok_api_key)
                initialization_results["grok"] = validation.valid
                if not validation.valid:
                    logger.warning(f"Grok validation failed: {validation.error}")
            except Exception as e:
                logger.error(f"Failed to initialize Grok provider: {e}")
                initialization_results["grok"] = False
        
        # Perform initial health check
        await self.check_provider_health()
        
        logger.info(f"Initialized providers: {list(initialization_results.keys())}")
        return initialization_results
    
    async def select_optimal_provider(
        self, 
        task_type: str, 
        user_preferences: Optional[Dict[str, Any]] = None,
        cost_priority: bool = False
    ) -> Optional[BaseAIProvider]:
        """Select the optimal provider for a given task"""
        
        # Check if health check is needed
        await self.ensure_health_check()
        
        # Get provider preferences for task type
        if cost_priority:
            preferred_providers = self.PROVIDER_PREFERENCES.get("cost_effective", [])
        else:
            preferred_providers = self.PROVIDER_PREFERENCES.get(task_type, [])
        
        # Apply user preferences if provided
        if user_preferences and "provider_priorities" in user_preferences:
            user_priorities = user_preferences["provider_priorities"].get(task_type, [])
            if user_priorities:
                preferred_providers = user_priorities
        
        # Find the best available provider
        for provider_name in preferred_providers:
            if provider_name in self.providers:
                provider = self.providers[provider_name]
                
                # Check if provider is available and healthy
                if (provider.is_available and 
                    not provider.is_rate_limited() and
                    self.is_provider_healthy(provider_name)):
                    
                    logger.debug(f"Selected {provider_name} for {task_type}")
                    return provider
        
        # Fallback: return any available provider
        for provider_name, provider in self.providers.items():
            if provider.is_available and not provider.is_rate_limited():
                logger.warning(f"Using fallback provider {provider_name} for {task_type}")
                return provider
        
        logger.error(f"No available providers for task type: {task_type}")
        return None
    
    async def process_chat_message(
        self, 
        user_id: str, 
        request: ChatRequest,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> ChatResponse:
        """Process a chat message with optimal provider selection"""
        
        provider = await self.select_optimal_provider("chat", user_preferences)
        if not provider:
            return ChatResponse(
                status="error",
                reply="No AI providers are currently available. Please check your API keys.",
                thread_id=request.thread_id or "error",
                message_id="error",
                provider_used="none",
                tokens_used=0,
                cost_cents=0
            )
        
        try:
            # Convert to provider message format
            messages = [Message(role="user", content=request.message)]
            
            # Add context if provided
            if request.context:
                context_message = self.build_context_message(request.context)
                messages.insert(0, context_message)
            
            # Generate response
            response = await provider.generate_chat_response(messages)
            
            return ChatResponse(
                status="success",
                reply=response.content,
                thread_id=request.thread_id or f"chat_{user_id}_{datetime.now().timestamp()}",
                message_id=f"msg_{datetime.now().timestamp()}",
                provider_used=provider.provider_name,
                tokens_used=response.tokens_used,
                cost_cents=response.cost_cents,
                metadata={"model_used": response.model_used}
            )
            
        except Exception as e:
            logger.error(f"Chat processing failed with {provider.provider_name}: {e}")
            
            # Try fallback provider
            fallback_provider = await self.get_fallback_provider(provider.provider_name, "chat")
            if fallback_provider:
                try:
                    messages = [Message(role="user", content=request.message)]
                    response = await fallback_provider.generate_chat_response(messages)
                    
                    return ChatResponse(
                        status="success",
                        reply=response.content,
                        thread_id=request.thread_id or f"chat_{user_id}_{datetime.now().timestamp()}",
                        message_id=f"msg_{datetime.now().timestamp()}",
                        provider_used=fallback_provider.provider_name,
                        tokens_used=response.tokens_used,
                        cost_cents=response.cost_cents,
                        metadata={"model_used": response.model_used, "fallback": True}
                    )
                except Exception as fallback_error:
                    logger.error(f"Fallback provider also failed: {fallback_error}")
            
            return ChatResponse(
                status="error",
                reply="I'm experiencing technical difficulties. Please try again in a moment.",
                thread_id=request.thread_id or "error",
                message_id="error",
                provider_used=provider.provider_name,
                tokens_used=0,
                cost_cents=0
            )
    
    async def generate_market_analysis(
        self, 
        user_id: str, 
        request: AnalysisRequest,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> AnalysisResponse:
        """Generate market analysis using optimal provider"""
        
        task_type = f"{request.analysis_type}_analysis"
        provider = await self.select_optimal_provider(task_type, user_preferences)
        
        if not provider:
            return AnalysisResponse(
                status="error",
                analysis_type=request.analysis_type,
                symbols=request.symbols,
                results={"error": "No AI providers available"},
                confidence_score=0.0,
                provider_used="none"
            )
        
        try:
            # Build analysis prompt
            prompt = self.build_analysis_prompt(request)
            data = {"symbols": request.symbols, "parameters": request.parameters}
            
            # Generate analysis
            response = await provider.generate_analysis(prompt, data)
            
            return AnalysisResponse(
                status="success",
                analysis_type=request.analysis_type,
                symbols=request.symbols,
                results={
                    "analysis": response.analysis,
                    "confidence_score": response.confidence_score,
                    "tokens_used": response.tokens_used,
                    "cost_cents": response.cost_cents
                },
                confidence_score=response.confidence_score,
                provider_used=provider.provider_name
            )
            
        except Exception as e:
            logger.error(f"Analysis generation failed: {e}")
            return AnalysisResponse(
                status="error",
                analysis_type=request.analysis_type,
                symbols=request.symbols,
                results={"error": str(e)},
                confidence_score=0.0,
                provider_used=provider.provider_name
            )
    
    async def check_provider_health(self):
        """Check health of all providers"""
        health_tasks = []
        
        for provider_name, provider in self.providers.items():
            health_tasks.append(self.check_single_provider_health(provider_name, provider))
        
        if health_tasks:
            await asyncio.gather(*health_tasks, return_exceptions=True)
        
        self.last_health_check = datetime.now()
        logger.debug("Provider health check completed")
    
    async def check_single_provider_health(self, provider_name: str, provider: BaseAIProvider):
        """Check health of a single provider"""
        try:
            is_available = await provider.check_availability()
            health_status = provider.get_health_status()
            
            self.provider_health[provider_name] = {
                "available": is_available,
                "last_check": datetime.now(),
                "health_status": health_status
            }
            
        except Exception as e:
            logger.warning(f"Health check failed for {provider_name}: {e}")
            self.provider_health[provider_name] = {
                "available": False,
                "last_check": datetime.now(),
                "error": str(e)
            }
    
    async def ensure_health_check(self):
        """Ensure health check is up to date"""
        if (not self.last_health_check or 
            datetime.now() - self.last_health_check > self.health_check_interval):
            await self.check_provider_health()
    
    def is_provider_healthy(self, provider_name: str) -> bool:
        """Check if a provider is healthy"""
        if provider_name not in self.provider_health:
            return True  # Assume healthy if no data
        
        health_data = self.provider_health[provider_name]
        return health_data.get("available", False)
    
    async def get_fallback_provider(
        self, 
        failed_provider: str, 
        task_type: str
    ) -> Optional[BaseAIProvider]:
        """Get a fallback provider when the primary fails"""
        preferred_providers = self.PROVIDER_PREFERENCES.get(task_type, [])
        
        for provider_name in preferred_providers:
            if (provider_name != failed_provider and 
                provider_name in self.providers and
                self.providers[provider_name].is_available):
                return self.providers[provider_name]
        
        return None
    
    def build_context_message(self, context: Dict[str, Any]) -> Message:
        """Build context message from provided context data"""
        context_parts = []
        
        if "portfolio" in context:
            context_parts.append("Current Portfolio Information:")
            context_parts.append(str(context["portfolio"]))
        
        if "market_data" in context:
            context_parts.append("Market Data:")
            context_parts.append(str(context["market_data"]))
        
        if "user_preferences" in context:
            context_parts.append("User Preferences:")
            context_parts.append(str(context["user_preferences"]))
        
        context_content = "\n".join(context_parts)
        return Message(role="system", content=f"Context: {context_content}")
    
    def build_analysis_prompt(self, request: AnalysisRequest) -> str:
        """Build analysis prompt from request"""
        symbols_str = ", ".join(request.symbols)
        
        prompt_templates = {
            "technical": f"Perform technical analysis on {symbols_str}. Analyze price patterns, trends, and technical indicators.",
            "fundamental": f"Perform fundamental analysis on {symbols_str}. Analyze financial metrics, earnings, and company fundamentals.",
            "sentiment": f"Analyze market sentiment for {symbols_str}. Consider news, social media, and market mood.",
            "portfolio": f"Analyze portfolio composition including {symbols_str}. Evaluate diversification, risk, and optimization opportunities."
        }
        
        return prompt_templates.get(request.analysis_type, 
                                  f"Analyze {symbols_str} for {request.analysis_type}")
    
    def get_provider_statistics(self) -> Dict[str, Any]:
        """Get comprehensive provider statistics"""
        stats = {}
        
        for provider_name, provider in self.providers.items():
            usage_stats = provider.get_usage_stats()
            health_data = self.provider_health.get(provider_name, {})
            
            stats[provider_name] = {
                "usage": usage_stats.dict(),
                "health": health_data,
                "available": provider.is_available,
                "rate_limited": provider.is_rate_limited()
            }
        
        return stats
    
    def reset_provider_statistics(self):
        """Reset usage statistics for all providers"""
        for provider in self.providers.values():
            provider.reset_usage_stats()
        
        logger.info("Provider statistics reset")