"""
AI Provider Failover System
Handles automatic failover between AI providers, health monitoring, and graceful degradation
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from app.database.service import get_db_connection
from app.ai_engine.service import AIEngineService

logger = logging.getLogger(__name__)

class ProviderStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"

class FailoverReason(Enum):
    TIMEOUT = "timeout"
    API_ERROR = "api_error"
    RATE_LIMIT = "rate_limit"
    QUOTA_EXCEEDED = "quota_exceeded"
    NETWORK_ERROR = "network_error"
    INVALID_RESPONSE = "invalid_response"
    HEALTH_CHECK_FAILED = "health_check_failed"

@dataclass
class ProviderHealth:
    provider_name: str
    status: ProviderStatus = ProviderStatus.UNKNOWN
    last_check: datetime = field(default_factory=datetime.utcnow)
    response_time_ms: float = 0.0
    success_rate: float = 0.0
    error_count: int = 0
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    last_success: Optional[datetime] = None
    is_available: bool = True

@dataclass
class FailoverEvent:
    timestamp: datetime
    from_provider: str
    to_provider: str
    reason: FailoverReason
    user_id: str
    operation_type: str
    error_details: Optional[str] = None

class AIProviderFailoverManager:
    """
    Manages AI provider failover, health monitoring, and graceful degradation
    """
    
    def __init__(self):
        self.ai_service = AIEngineService()
        self.provider_health: Dict[str, ProviderHealth] = {}
        self.failover_history: List[FailoverEvent] = []
        self.provider_priorities = ["openai", "claude", "gemini", "grok"]
        self.health_check_interval = 300  # 5 minutes
        self.max_consecutive_failures = 3
        self.timeout_seconds = 30
        self.circuit_breaker_timeout = 900  # 15 minutes
        self.degraded_mode_enabled = True
        self._health_check_task = None
        self._initialize_provider_health()

    def _initialize_provider_health(self):
        """Initialize health tracking for all providers"""
        for provider in self.provider_priorities:
            self.provider_health[provider] = ProviderHealth(provider_name=provider)

    async def start_health_monitoring(self):
        """Start continuous health monitoring of AI providers"""
        if self._health_check_task is None:
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            logger.info("AI provider health monitoring started")

    async def stop_health_monitoring(self):
        """Stop health monitoring"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
            logger.info("AI provider health monitoring stopped")

    async def _health_check_loop(self):
        """Continuous health check loop"""
        while True:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def _perform_health_checks(self):
        """Perform health checks on all providers"""
        logger.info("Performing AI provider health checks")
        
        # Get a test user's preferences to check providers
        test_user_id = "health_check_user"
        
        for provider_name in self.provider_priorities:
            try:
                health = self.provider_health[provider_name]
                start_time = time.time()
                
                # Perform health check
                is_healthy, error_msg = await self._check_provider_health(provider_name, test_user_id)
                
                response_time = (time.time() - start_time) * 1000
                health.response_time_ms = response_time
                health.last_check = datetime.utcnow()
                
                if is_healthy:
                    health.status = ProviderStatus.HEALTHY
                    health.consecutive_failures = 0
                    health.last_success = datetime.utcnow()
                    health.is_available = True
                    health.last_error = None
                else:
                    health.consecutive_failures += 1
                    health.error_count += 1
                    health.last_error = error_msg
                    
                    if health.consecutive_failures >= self.max_consecutive_failures:
                        health.status = ProviderStatus.FAILED
                        health.is_available = False
                    else:
                        health.status = ProviderStatus.DEGRADED
                        health.is_available = True
                
                # Update success rate (last 100 operations)
                await self._update_success_rate(provider_name)
                
                logger.info(f"Health check for {provider_name}: {health.status.value} "
                          f"(response: {response_time:.0f}ms, failures: {health.consecutive_failures})")
                
            except Exception as e:
                logger.error(f"Health check failed for {provider_name}: {e}")
                health = self.provider_health[provider_name]
                health.status = ProviderStatus.FAILED
                health.consecutive_failures += 1
                health.error_count += 1
                health.last_error = str(e)
                health.is_available = False

    async def _check_provider_health(self, provider_name: str, user_id: str) -> Tuple[bool, Optional[str]]:
        """Check health of a specific provider"""
        try:
            # Get user preferences to access API keys
            preferences = await self.ai_service.get_user_preferences(user_id)
            if not preferences:
                return False, "No user preferences found"
            
            # Get API key for provider
            api_key = preferences.get(f"{provider_name}_api_key")
            if not api_key:
                return False, f"No API key configured for {provider_name}"
            
            # Validate API key (this also tests connectivity)
            result = await asyncio.wait_for(
                self.ai_service.validate_api_key(provider_name, api_key),
                timeout=self.timeout_seconds
            )
            
            return result.get("valid", False), result.get("message")
            
        except asyncio.TimeoutError:
            return False, "Health check timeout"
        except Exception as e:
            return False, str(e)

    async def _update_success_rate(self, provider_name: str):
        """Update success rate based on recent operations"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get recent operations (last 100)
            cursor.execute("""
                SELECT success FROM ai_provider_operations 
                WHERE provider_name = ? 
                ORDER BY created_at DESC 
                LIMIT 100
            """, (provider_name,))
            
            results = cursor.fetchall()
            if results:
                success_count = sum(1 for r in results if r[0])
                success_rate = success_count / len(results)
                self.provider_health[provider_name].success_rate = success_rate
            
            conn.close()
        except Exception as e:
            logger.error(f"Error updating success rate for {provider_name}: {e}")

    async def get_best_available_provider(self, user_id: str, operation_type: str = "general") -> Optional[str]:
        """Get the best available AI provider based on health and user preferences"""
        try:
            # Get user preferences for provider priorities
            preferences = await self.ai_service.get_user_preferences(user_id)
            if not preferences:
                logger.warning(f"No preferences found for user {user_id}")
                return None
            
            # Check which providers have API keys configured
            available_providers = []
            for provider in self.provider_priorities:
                api_key = preferences.get(f"{provider}_api_key")
                if api_key and len(api_key.strip()) > 0:
                    health = self.provider_health.get(provider)
                    if health and health.is_available:
                        available_providers.append((provider, health))
            
            if not available_providers:
                logger.warning(f"No available AI providers for user {user_id}")
                return None
            
            # Sort by health status and success rate
            available_providers.sort(key=lambda x: (
                x[1].status == ProviderStatus.HEALTHY,  # Healthy providers first
                x[1].success_rate,  # Higher success rate first
                -x[1].response_time_ms  # Lower response time first
            ), reverse=True)
            
            best_provider = available_providers[0][0]
            logger.info(f"Selected provider {best_provider} for user {user_id} operation {operation_type}")
            return best_provider
            
        except Exception as e:
            logger.error(f"Error selecting best provider: {e}")
            return None

    async def execute_with_failover(self, user_id: str, operation_type: str, operation_func, *args, **kwargs) -> Dict[str, Any]:
        """
        Execute an AI operation with automatic failover support
        
        Args:
            user_id: User ID
            operation_type: Type of operation (e.g., 'portfolio_analysis', 'signal_generation')
            operation_func: Function to execute (should accept provider_name as first argument)
            *args, **kwargs: Arguments to pass to operation_func
        """
        start_time = datetime.utcnow()
        attempted_providers = []
        last_error = None
        
        try:
            # Get user preferences
            preferences = await self.ai_service.get_user_preferences(user_id)
            if not preferences:
                return {
                    "status": "error",
                    "error": "No user preferences found",
                    "fallback_used": True
                }
            
            # Try providers in order of preference/health
            for provider in self.provider_priorities:
                # Check if provider has API key configured
                api_key = preferences.get(f"{provider}_api_key")
                if not api_key or len(api_key.strip()) == 0:
                    continue
                
                # Check provider health
                health = self.provider_health.get(provider)
                if not health or not health.is_available:
                    continue
                
                # Skip if provider is in circuit breaker state
                if await self._is_circuit_breaker_open(provider):
                    continue
                
                attempted_providers.append(provider)
                
                try:
                    logger.info(f"Attempting {operation_type} with provider {provider} for user {user_id}")
                    
                    # Execute operation with timeout
                    result = await asyncio.wait_for(
                        operation_func(provider, user_id, *args, **kwargs),
                        timeout=self.timeout_seconds
                    )
                    
                    # Record successful operation
                    await self._record_operation(user_id, provider, operation_type, True, None)
                    
                    # Update provider health
                    if health:
                        health.consecutive_failures = 0
                        health.last_success = datetime.utcnow()
                        health.status = ProviderStatus.HEALTHY
                    
                    # Add metadata to result
                    if isinstance(result, dict):
                        result.update({
                            "provider_used": provider,
                            "failover_attempted": len(attempted_providers) > 1,
                            "attempted_providers": attempted_providers,
                            "execution_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000
                        })
                    
                    logger.info(f"Successfully executed {operation_type} with provider {provider}")
                    return result
                    
                except asyncio.TimeoutError:
                    error_msg = f"Timeout after {self.timeout_seconds}s"
                    last_error = error_msg
                    await self._handle_provider_failure(user_id, provider, operation_type, FailoverReason.TIMEOUT, error_msg)
                    
                except Exception as e:
                    error_msg = str(e)
                    last_error = error_msg
                    
                    # Determine failure reason
                    reason = self._classify_error(e)
                    await self._handle_provider_failure(user_id, provider, operation_type, reason, error_msg)
                    
                    logger.warning(f"Provider {provider} failed for {operation_type}: {error_msg}")
            
            # All providers failed - return error or fallback
            if self.degraded_mode_enabled:
                logger.warning(f"All AI providers failed for {operation_type}, using fallback")
                return await self._execute_fallback(user_id, operation_type, attempted_providers, last_error)
            else:
                return {
                    "status": "error",
                    "error": f"All AI providers failed. Last error: {last_error}",
                    "attempted_providers": attempted_providers,
                    "fallback_available": False
                }
                
        except Exception as e:
            logger.error(f"Critical error in failover execution: {e}")
            return {
                "status": "error",
                "error": f"Critical failover error: {str(e)}",
                "attempted_providers": attempted_providers
            }

    def _classify_error(self, error: Exception) -> FailoverReason:
        """Classify error to determine appropriate failover reason"""
        error_str = str(error).lower()
        
        if "timeout" in error_str:
            return FailoverReason.TIMEOUT
        elif "rate limit" in error_str or "429" in error_str:
            return FailoverReason.RATE_LIMIT
        elif "quota" in error_str or "billing" in error_str:
            return FailoverReason.QUOTA_EXCEEDED
        elif "network" in error_str or "connection" in error_str:
            return FailoverReason.NETWORK_ERROR
        elif "invalid" in error_str or "malformed" in error_str:
            return FailoverReason.INVALID_RESPONSE
        else:
            return FailoverReason.API_ERROR

    async def _handle_provider_failure(self, user_id: str, provider: str, operation_type: str, 
                                     reason: FailoverReason, error_msg: str):
        """Handle provider failure and update health status"""
        try:
            # Record failed operation
            await self._record_operation(user_id, provider, operation_type, False, error_msg)
            
            # Update provider health
            health = self.provider_health.get(provider)
            if health:
                health.consecutive_failures += 1
                health.error_count += 1
                health.last_error = error_msg
                
                # Update status based on failure count
                if health.consecutive_failures >= self.max_consecutive_failures:
                    health.status = ProviderStatus.FAILED
                    health.is_available = False
                    logger.warning(f"Provider {provider} marked as FAILED after {health.consecutive_failures} consecutive failures")
                else:
                    health.status = ProviderStatus.DEGRADED
            
            # Record failover event if we're switching providers
            if len(self.failover_history) == 0 or self.failover_history[-1].from_provider != provider:
                failover_event = FailoverEvent(
                    timestamp=datetime.utcnow(),
                    from_provider=provider,
                    to_provider="next_available",
                    reason=reason,
                    user_id=user_id,
                    operation_type=operation_type,
                    error_details=error_msg
                )
                self.failover_history.append(failover_event)
                
                # Keep only last 100 failover events
                if len(self.failover_history) > 100:
                    self.failover_history = self.failover_history[-100:]
            
        except Exception as e:
            logger.error(f"Error handling provider failure: {e}")

    async def _is_circuit_breaker_open(self, provider: str) -> bool:
        """Check if circuit breaker is open for provider"""
        health = self.provider_health.get(provider)
        if not health or health.status != ProviderStatus.FAILED:
            return False
        
        # Check if enough time has passed to try again
        if health.last_check:
            time_since_failure = datetime.utcnow() - health.last_check
            return time_since_failure < timedelta(seconds=self.circuit_breaker_timeout)
        
        return False

    async def _execute_fallback(self, user_id: str, operation_type: str, 
                              attempted_providers: List[str], last_error: str) -> Dict[str, Any]:
        """Execute fallback logic when all AI providers fail"""
        try:
            logger.info(f"Executing fallback for {operation_type}")
            
            # Generate basic fallback response based on operation type
            if operation_type == "portfolio_analysis":
                return {
                    "status": "success",
                    "analysis": {
                        "portfolio_health": {
                            "overall_score": 60,
                            "risk_level": "MODERATE",
                            "diversification_score": 0.5,
                            "concentration_risk": 0.3
                        },
                        "recommendations": {
                            "immediate_actions": [],
                            "portfolio_optimization": [
                                {
                                    "type": "diversification",
                                    "recommendation": "Consider diversifying portfolio across sectors",
                                    "priority": "MEDIUM"
                                }
                            ],
                            "risk_management": [
                                {
                                    "type": "monitoring",
                                    "recommendation": "Monitor portfolio regularly for changes",
                                    "priority": "LOW"
                                }
                            ]
                        },
                        "market_context": {
                            "market_sentiment": "neutral",
                            "volatility_assessment": "moderate"
                        }
                    },
                    "provider_used": "fallback",
                    "fallback_used": True,
                    "attempted_providers": attempted_providers,
                    "fallback_reason": f"All AI providers failed: {last_error}",
                    "confidence_score": 0.3
                }
            
            elif operation_type == "signal_generation":
                return {
                    "status": "success",
                    "signals": [],
                    "provider_used": "fallback",
                    "fallback_used": True,
                    "attempted_providers": attempted_providers,
                    "fallback_reason": f"All AI providers failed: {last_error}",
                    "message": "No signals generated - AI providers unavailable"
                }
            
            else:
                return {
                    "status": "partial_success",
                    "result": "Basic fallback response",
                    "provider_used": "fallback",
                    "fallback_used": True,
                    "attempted_providers": attempted_providers,
                    "fallback_reason": f"All AI providers failed: {last_error}",
                    "message": "Operation completed with limited functionality"
                }
                
        except Exception as e:
            logger.error(f"Error in fallback execution: {e}")
            return {
                "status": "error",
                "error": f"Fallback execution failed: {str(e)}",
                "attempted_providers": attempted_providers
            }

    async def _record_operation(self, user_id: str, provider: str, operation_type: str, 
                              success: bool, error_msg: Optional[str]):
        """Record AI operation for tracking and analytics"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Create table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_provider_operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    provider_name TEXT NOT NULL,
                    operation_type TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    response_time_ms REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                INSERT INTO ai_provider_operations 
                (user_id, provider_name, operation_type, success, error_message)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, provider, operation_type, success, error_msg))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error recording operation: {e}")

    async def get_provider_status(self) -> Dict[str, Any]:
        """Get current status of all AI providers"""
        return {
            "providers": {
                name: {
                    "status": health.status.value,
                    "is_available": health.is_available,
                    "last_check": health.last_check.isoformat() if health.last_check else None,
                    "response_time_ms": health.response_time_ms,
                    "success_rate": health.success_rate,
                    "consecutive_failures": health.consecutive_failures,
                    "error_count": health.error_count,
                    "last_error": health.last_error,
                    "last_success": health.last_success.isoformat() if health.last_success else None
                }
                for name, health in self.provider_health.items()
            },
            "failover_history": [
                {
                    "timestamp": event.timestamp.isoformat(),
                    "from_provider": event.from_provider,
                    "to_provider": event.to_provider,
                    "reason": event.reason.value,
                    "operation_type": event.operation_type,
                    "error_details": event.error_details
                }
                for event in self.failover_history[-10:]  # Last 10 events
            ],
            "health_monitoring_active": self._health_check_task is not None,
            "degraded_mode_enabled": self.degraded_mode_enabled
        }

    async def force_provider_status(self, provider: str, status: ProviderStatus):
        """Manually set provider status (for testing/admin purposes)"""
        if provider in self.provider_health:
            health = self.provider_health[provider]
            health.status = status
            health.is_available = status != ProviderStatus.FAILED
            health.last_check = datetime.utcnow()
            logger.info(f"Manually set {provider} status to {status.value}")

# Global failover manager instance
failover_manager = AIProviderFailoverManager()