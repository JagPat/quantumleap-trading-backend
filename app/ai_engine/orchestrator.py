"""
AI Engine Orchestrator

Chooses the optimal AI provider for each task based on requirements, availability, and cost.
Acts as the central coordinator for all AI operations.
"""
import logging
from typing import Dict, Any, Optional, List
import time
from datetime import datetime

from .schemas.requests import AIProvider, AnalysisType
from .schemas.responses import ErrorResponse
from .providers import OpenAIClient, ClaudeClient, GeminiClient
from .preprocessor import DataPreprocessor
from ..database.service import get_user_credentials

logger = logging.getLogger(__name__)


class AIOrchestrator:
    """
    AI Engine Orchestrator
    
    Responsibilities:
    - Choose optimal AI provider for each task
    - Load balance across providers
    - Handle provider fallbacks
    - Manage cost optimization
    - Track usage and performance
    """
    
    def __init__(self):
        """Initialize the AI orchestrator with all available providers"""
        self.preprocessor = DataPreprocessor()
        
        # Initialize all providers
        self.providers = {
            AIProvider.OPENAI: OpenAIClient(),
            AIProvider.CLAUDE: ClaudeClient(),
            AIProvider.GEMINI: GeminiClient()
        }
        
        # Provider selection strategies
        self.provider_preferences = {
            AnalysisType.TECHNICAL: [AIProvider.CLAUDE, AIProvider.OPENAI, AIProvider.GEMINI],
            AnalysisType.FUNDAMENTAL: [AIProvider.OPENAI, AIProvider.CLAUDE, AIProvider.GEMINI],
            AnalysisType.SENTIMENT: [AIProvider.CLAUDE, AIProvider.GEMINI, AIProvider.OPENAI],
            AnalysisType.STRATEGY_GENERATION: [AIProvider.OPENAI, AIProvider.CLAUDE, AIProvider.GEMINI],
            AnalysisType.PORTFOLIO_OPTIMIZATION: [AIProvider.CLAUDE, AIProvider.OPENAI, AIProvider.GEMINI]
        }
    
    def get_user_providers(self, user_id: str) -> Dict[AIProvider, Any]:
        """
        Get provider instances with user-specific API keys
        
        Args:
            user_id: User identifier to get personalized providers
            
        Returns:
            Dictionary of available providers with user's API keys
        """
        try:
            # Get user credentials including AI preferences
            user_data = get_user_credentials(user_id)
            if not user_data:
                logger.warning(f"No user data found for {user_id}, using global providers")
                return self.providers
            
            # Create user-specific provider instances
            user_providers = {}
            
            # OpenAI
            openai_key = user_data.get("ai_api_key_openai")
            if openai_key:
                user_providers[AIProvider.OPENAI] = OpenAIClient(api_key=openai_key)
                logger.debug(f"Using user-specific OpenAI key for {user_id}")
            else:
                user_providers[AIProvider.OPENAI] = self.providers[AIProvider.OPENAI]
            
            # Claude
            claude_key = user_data.get("ai_api_key_claude")
            if claude_key:
                user_providers[AIProvider.CLAUDE] = ClaudeClient(api_key=claude_key)
                logger.debug(f"Using user-specific Claude key for {user_id}")
            else:
                user_providers[AIProvider.CLAUDE] = self.providers[AIProvider.CLAUDE]
            
            # Gemini
            gemini_key = user_data.get("ai_api_key_gemini")
            if gemini_key:
                user_providers[AIProvider.GEMINI] = GeminiClient(api_key=gemini_key)
                logger.debug(f"Using user-specific Gemini key for {user_id}")
            else:
                user_providers[AIProvider.GEMINI] = self.providers[AIProvider.GEMINI]
            
            return user_providers
            
        except Exception as e:
            logger.error(f"Error getting user providers for {user_id}: {str(e)}")
            return self.providers
    
    def get_user_preferred_provider(self, user_id: str, analysis_type: AnalysisType) -> AIProvider:
        """
        Get user's preferred provider for a specific analysis type
        
        Args:
            user_id: User identifier
            analysis_type: Type of analysis being performed
            
        Returns:
            Preferred AI provider for the user
        """
        try:
            user_data = get_user_credentials(user_id)
            if user_data:
                preferred = user_data.get("preferred_ai_provider", "auto")
                
                # If user has a specific preference and it's not 'auto'
                if preferred and preferred != "auto":
                    preferred_enum = AIProvider(preferred.lower())
                    
                    # Check if user has a valid API key for their preferred provider
                    user_providers = self.get_user_providers(user_id)
                    if preferred_enum in user_providers and user_providers[preferred_enum].is_available:
                        logger.debug(f"Using user preferred provider {preferred} for {user_id}")
                        return preferred_enum
                    else:
                        logger.warning(f"User preferred provider {preferred} not available for {user_id}, falling back to automatic selection")
            
            # Fall back to automatic selection based on analysis type
            return self._choose_provider_auto(user_id, analysis_type)
            
        except Exception as e:
            logger.error(f"Error getting user preferred provider for {user_id}: {str(e)}")
            return self._choose_provider_auto(user_id, analysis_type)
    
    def _choose_provider_auto(self, user_id: str, analysis_type: AnalysisType) -> AIProvider:
        """
        Automatically choose the best available provider for the user
        
        Args:
            user_id: User identifier
            analysis_type: Type of analysis being performed
            
        Returns:
            Best available AI provider
        """
        user_providers = self.get_user_providers(user_id)
        preferred_order = self.provider_preferences.get(analysis_type, [AIProvider.OPENAI, AIProvider.CLAUDE, AIProvider.GEMINI])
        
        # Try providers in order of preference, checking availability
        for provider in preferred_order:
            if provider in user_providers and user_providers[provider].is_available:
                logger.debug(f"Auto-selected {provider.value} for {user_id} ({analysis_type.value})")
                return provider
        
        # If no provider is available, return the first one and let error handling deal with it
        logger.warning(f"No available providers found for {user_id}, defaulting to OpenAI")
        return AIProvider.OPENAI
        
        # Usage tracking
        self.usage_stats = {}
        self.last_used = {}
        
        logger.info("AI Orchestrator initialized")
        self._log_provider_availability()
    
    def _log_provider_availability(self):
        """Log which providers are available"""
        available = []
        unavailable = []
        
        for provider_name, provider in self.providers.items():
            if provider.is_available:
                available.append(provider_name.value)
            else:
                unavailable.append(provider_name.value)
        
        logger.info(f"Available AI providers: {available}")
        if unavailable:
            logger.warning(f"Unavailable AI providers: {unavailable}")
    
    def choose_provider(self, analysis_type: Optional[AnalysisType] = None, 
                       preferred_provider: AIProvider = AIProvider.AUTO,
                       fallback_enabled: bool = True) -> Optional[AIProvider]:
        """
        Choose the optimal AI provider for a task.
        
        Args:
            analysis_type: Type of analysis being performed
            preferred_provider: User's preferred provider
            fallback_enabled: Whether to fallback to other providers
            
        Returns:
            Selected provider or None if none available
        """
        # If specific provider requested and available, use it
        if preferred_provider != AIProvider.AUTO:
            provider = self.providers.get(preferred_provider)
            if provider and provider.is_available:
                logger.debug(f"Using requested provider: {preferred_provider.value}")
                return preferred_provider
            elif not fallback_enabled:
                logger.warning(f"Requested provider {preferred_provider.value} not available and fallback disabled")
                return None
        
        # Choose based on analysis type preferences
        if analysis_type:
            candidates = self.provider_preferences.get(analysis_type, list(self.providers.keys()))
        else:
            candidates = list(self.providers.keys())
        
        # Filter to available providers
        available_candidates = [
            provider_name for provider_name in candidates 
            if self.providers[provider_name].is_available
        ]
        
        if not available_candidates:
            logger.error("No AI providers available")
            return None
        
        # Simple round-robin for load balancing
        selected = self._select_with_load_balancing(available_candidates)
        logger.debug(f"Selected provider: {selected.value} for analysis type: {analysis_type}")
        return selected
    
    def _select_with_load_balancing(self, candidates: List[AIProvider]) -> AIProvider:
        """Select provider using simple load balancing"""
        # For now, use simple round-robin based on last used time
        least_recently_used = None
        oldest_time = float('inf')
        
        for provider in candidates:
            last_used = self.last_used.get(provider, 0)
            if last_used < oldest_time:
                oldest_time = last_used
                least_recently_used = provider
        
        return least_recently_used or candidates[0]
    
    async def generate_market_analysis(self, user_id: str, analysis_type: AnalysisType,
                                     symbols: List[str], timeframe: str = "1d",
                                     provider: AIProvider = AIProvider.AUTO,
                                     context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate market analysis using the optimal provider.
        
        Args:
            user_id: User identifier
            analysis_type: Type of analysis to perform
            symbols: Stock symbols to analyze
            timeframe: Analysis timeframe
            provider: Preferred provider
            context: Additional context data
            
        Returns:
            Analysis response
        """
        start_time = time.time()
        
        try:
            # Choose provider based on user preferences
            if provider == AIProvider.AUTO:
                selected_provider = self.get_user_preferred_provider(user_id, analysis_type)
            else:
                selected_provider = provider
            
            # Get user-specific providers
            user_providers = self.get_user_providers(user_id)
            if selected_provider not in user_providers or not user_providers[selected_provider].is_available:
                return self._create_error_response("Selected AI provider unavailable", "PROVIDER_UNAVAILABLE")
            
            # Prepare context data
            market_context = self.preprocessor.prepare_market_context(symbols, timeframe)
            if context:
                market_context.update(context)
            
            # Generate prompt
            prompt = self.preprocessor.generate_analysis_prompt(
                market_context, analysis_type.value, context.get("additional_prompt") if context else None
            )
            
            # Get user-specific provider and generate analysis
            provider_client = user_providers[selected_provider]
            result = await provider_client.generate_analysis(prompt, market_context)
            
            # Track usage
            self._track_usage(selected_provider, "analysis", time.time() - start_time)
            
            # Add orchestrator metadata
            result.update({
                "orchestrator_metadata": {
                    "user_id": user_id,
                    "analysis_type": analysis_type.value,
                    "symbols": symbols,
                    "timeframe": timeframe,
                    "provider_selected": selected_provider.value,
                    "processing_time_ms": int((time.time() - start_time) * 1000)
                }
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating market analysis: {str(e)}")
            return self._create_error_response(str(e), "ANALYSIS_FAILED")
    
    async def generate_trading_strategy(self, user_id: str, strategy_prompt: str,
                                      risk_tolerance: str = "medium",
                                      portfolio_data: Optional[Dict[str, Any]] = None,
                                      provider: AIProvider = AIProvider.AUTO) -> Dict[str, Any]:
        """
        Generate trading strategy using the optimal provider.
        
        Args:
            user_id: User identifier
            strategy_prompt: Natural language strategy description
            risk_tolerance: Risk tolerance level
            portfolio_data: Current portfolio data
            provider: Preferred provider
            
        Returns:
            Strategy response
        """
        start_time = time.time()
        
        try:
            # Choose provider based on user preferences
            if provider == AIProvider.AUTO:
                selected_provider = self.get_user_preferred_provider(user_id, AnalysisType.STRATEGY_GENERATION)
            else:
                selected_provider = provider
            
            # Get user-specific providers
            user_providers = self.get_user_providers(user_id)
            if selected_provider not in user_providers or not user_providers[selected_provider].is_available:
                return self._create_error_response("Selected AI provider unavailable", "PROVIDER_UNAVAILABLE")
            
            # Prepare portfolio context
            portfolio_context = {}
            if portfolio_data:
                portfolio_context = self.preprocessor.prepare_portfolio_context(portfolio_data, user_id)
            
            # Generate strategy prompt
            prompt = self.preprocessor.generate_strategy_prompt(
                strategy_prompt, portfolio_context, risk_tolerance
            )
            
            # Get user-specific provider and generate strategy
            provider_client = user_providers[selected_provider]
            result = await provider_client.generate_strategy(prompt, portfolio_context)
            
            # Track usage
            self._track_usage(selected_provider, "strategy", time.time() - start_time)
            
            # Add orchestrator metadata
            result.update({
                "orchestrator_metadata": {
                    "user_id": user_id,
                    "risk_tolerance": risk_tolerance,
                    "provider_selected": selected_provider.value,
                    "processing_time_ms": int((time.time() - start_time) * 1000)
                }
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating trading strategy: {str(e)}")
            return self._create_error_response(str(e), "STRATEGY_FAILED")
    
    async def generate_trading_signals(self, user_id: str, symbols: List[str],
                                     signal_type: str = "buy_sell",
                                     live_data: bool = True,
                                     provider: AIProvider = AIProvider.AUTO) -> Dict[str, Any]:
        """
        Generate trading signals using the optimal provider.
        
        Args:
            user_id: User identifier
            symbols: Symbols to generate signals for
            signal_type: Type of signals to generate
            live_data: Use live market data
            provider: Preferred provider
            
        Returns:
            Signals response
        """
        start_time = time.time()
        
        try:
            # Choose provider
            selected_provider = self.choose_provider(None, provider)  # No specific preference for signals
            if not selected_provider:
                return self._create_error_response("No AI providers available", "PROVIDER_UNAVAILABLE")
            
            # Prepare market context
            market_context = self.preprocessor.prepare_market_context(symbols)
            market_context.update({
                "signal_type": signal_type,
                "live_data": live_data,
                "user_id": user_id
            })
            
            # Create signals prompt
            prompt = f"""
Generate {signal_type} trading signals for the following stocks: {', '.join(symbols)}

Market Context: {market_context}

Provide specific buy/sell/hold recommendations with:
- Confidence levels (0-1)
- Target prices
- Stop-loss levels  
- Clear reasoning for each signal

Focus on actionable signals for Indian stock markets with current market conditions.
"""
            
            # Get provider and generate signals
            provider_client = self.providers[selected_provider]
            result = await provider_client.generate_signals(prompt, market_context)
            
            # Track usage
            self._track_usage(selected_provider, "signals", time.time() - start_time)
            
            # Add orchestrator metadata
            result.update({
                "orchestrator_metadata": {
                    "user_id": user_id,
                    "symbols": symbols,
                    "signal_type": signal_type,
                    "provider_selected": selected_provider.value,
                    "processing_time_ms": int((time.time() - start_time) * 1000)
                }
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating trading signals: {str(e)}")
            return self._create_error_response(str(e), "SIGNALS_FAILED")
    
    async def test_providers(self) -> Dict[str, Any]:
        """
        Test all available providers.
        
        Returns:
            Test results for all providers
        """
        results = {}
        
        for provider_name, provider in self.providers.items():
            try:
                if hasattr(provider, 'test_connection'):
                    result = await provider.test_connection()
                else:
                    result = {"status": "no_test_method"}
                results[provider_name.value] = result
            except Exception as e:
                results[provider_name.value] = {"status": "error", "error": str(e)}
        
        return {
            "provider_tests": results,
            "orchestrator_status": "operational",
            "timestamp": datetime.now().isoformat()
        }
    
    def _track_usage(self, provider: AIProvider, operation: str, duration: float):
        """Track provider usage for analytics and load balancing"""
        provider_key = provider.value
        
        if provider_key not in self.usage_stats:
            self.usage_stats[provider_key] = {
                "requests": 0,
                "total_duration": 0,
                "operations": {}
            }
        
        stats = self.usage_stats[provider_key]
        stats["requests"] += 1
        stats["total_duration"] += duration
        
        if operation not in stats["operations"]:
            stats["operations"][operation] = {"count": 0, "duration": 0}
        
        stats["operations"][operation]["count"] += 1
        stats["operations"][operation]["duration"] += duration
        
        self.last_used[provider] = time.time()
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for all providers"""
        return {
            "usage_stats": self.usage_stats,
            "available_providers": [p.value for p, client in self.providers.items() if client.is_available],
            "last_updated": datetime.now().isoformat()
        }
    
    def _create_error_response(self, message: str, error_code: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            "error": message,
            "error_code": error_code,
            "timestamp": datetime.now().isoformat(),
            "status": "error"
        } 