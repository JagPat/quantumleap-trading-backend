"""
AI Preferences Service

Handles user AI provider preferences, API key validation, and settings management.
"""
import logging
import asyncio
from typing import Dict, Any, Optional, Tuple
from ..database.service import update_user_ai_preferences, get_user_credentials
from ..ai_engine.providers import OpenAIClient, ClaudeClient, GeminiClient

logger = logging.getLogger(__name__)


class AIPreferencesService:
    """Service for managing user AI preferences and API keys"""
    
    def __init__(self):
        self.providers = {
            "openai": OpenAIClient,
            "claude": ClaudeClient,
            "gemini": GeminiClient
        }
    
    async def validate_api_key(self, provider: str, api_key: str) -> Tuple[bool, str]:
        """
        Validate an API key for a specific provider
        
        Args:
            provider: Provider name ('openai', 'claude', 'gemini')
            api_key: API key to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not provider or provider not in self.providers:
            return False, f"Unsupported provider: {provider}"
        
        if not api_key or not api_key.strip():
            return False, "API key cannot be empty"
        
        try:
            # Create provider instance with the key
            provider_class = self.providers[provider]
            provider_instance = provider_class(api_key=api_key.strip())
            
            # Check basic availability
            if not provider_instance.is_available:
                return False, f"{provider.capitalize()} client not properly initialized"
            
            # Try a simple test call to validate the key
            test_prompt = "Hello, this is a test."
            test_context = {"test": True}
            
            try:
                # Set a timeout for the validation call
                result = await asyncio.wait_for(
                    provider_instance.generate_analysis(test_prompt, test_context),
                    timeout=30.0
                )
                
                # Check if we got a valid response (not an error)
                if result and not result.get("error"):
                    logger.info(f"API key validation successful for {provider}")
                    return True, "API key is valid"
                else:
                    error_msg = result.get("error", "Unknown validation error") if result else "No response"
                    logger.warning(f"API key validation failed for {provider}: {error_msg}")
                    return False, f"API key validation failed: {error_msg}"
                    
            except asyncio.TimeoutError:
                logger.warning(f"API key validation timed out for {provider}")
                return False, "API key validation timed out"
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"API key validation error for {provider}: {error_msg}")
                
                # Check for common API key errors
                if "api key" in error_msg.lower() or "unauthorized" in error_msg.lower():
                    return False, "Invalid API key"
                elif "quota" in error_msg.lower() or "limit" in error_msg.lower():
                    return False, "API quota exceeded"
                else:
                    return False, f"Validation error: {error_msg}"
                    
        except Exception as e:
            logger.error(f"Error validating API key for {provider}: {str(e)}")
            return False, f"Validation failed: {str(e)}"
    
    async def update_user_preferences(
        self,
        user_id: str,
        preferred_provider: Optional[str] = None,
        openai_key: Optional[str] = None,
        claude_key: Optional[str] = None,
        gemini_key: Optional[str] = None,
        validate_keys: bool = True
    ) -> Dict[str, Any]:
        """
        Update user's AI preferences and API keys
        
        Args:
            user_id: User identifier
            preferred_provider: Preferred AI provider
            openai_key: OpenAI API key
            claude_key: Claude API key  
            gemini_key: Gemini API key
            validate_keys: Whether to validate API keys before saving
            
        Returns:
            Result dictionary with status and any validation errors
        """
        try:
            validation_errors = {}
            
            # Validate API keys if requested
            if validate_keys:
                if openai_key:
                    is_valid, error = await self.validate_api_key("openai", openai_key)
                    if not is_valid:
                        validation_errors["openai_api_key"] = error
                
                if claude_key:
                    is_valid, error = await self.validate_api_key("claude", claude_key)
                    if not is_valid:
                        validation_errors["claude_api_key"] = error
                
                if gemini_key:
                    is_valid, error = await self.validate_api_key("gemini", gemini_key)
                    if not is_valid:
                        validation_errors["gemini_api_key"] = error
                
                # If there are validation errors, don't save
                if validation_errors:
                    return {
                        "status": "error",
                        "message": "API key validation failed",
                        "validation_errors": validation_errors
                    }
            
            # Validate preferred provider
            if preferred_provider and preferred_provider not in ["auto", "openai", "claude", "gemini"]:
                validation_errors["preferred_provider"] = "Invalid provider. Must be 'auto', 'openai', 'claude', or 'gemini'"
                return {
                    "status": "error",
                    "message": "Invalid preferred provider",
                    "validation_errors": validation_errors
                }
            
            # Update database
            success = update_user_ai_preferences(
                user_id=user_id,
                preferred_ai_provider=preferred_provider,
                ai_api_key_openai=openai_key,
                ai_api_key_claude=claude_key,
                ai_api_key_gemini=gemini_key
            )
            
            if success:
                logger.info(f"Successfully updated AI preferences for user: {user_id}")
                return {
                    "status": "success",
                    "message": "AI preferences updated successfully"
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to update AI preferences in database"
                }
                
        except Exception as e:
            logger.error(f"Error updating AI preferences for user {user_id}: {str(e)}")
            return {
                "status": "error",
                "message": f"Update failed: {str(e)}"
            }
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's current AI preferences
        
        Args:
            user_id: User identifier
            
        Returns:
            User's AI preferences (without sensitive API keys)
        """
        try:
            user_data = get_user_credentials(user_id)
            if not user_data:
                return {
                    "status": "error",
                    "message": "User not found"
                }
            
            # Return preferences without exposing full API keys
            preferences = {
                "preferred_ai_provider": user_data.get("preferred_ai_provider", "auto"),
                "has_openai_key": bool(user_data.get("ai_api_key_openai")),
                "has_claude_key": bool(user_data.get("ai_api_key_claude")),
                "has_gemini_key": bool(user_data.get("ai_api_key_gemini")),
                "ai_settings_updated_at": user_data.get("ai_settings_updated_at")
            }
            
            # Show partial keys for confirmation (first 8 characters + masked)
            if user_data.get("ai_api_key_openai"):
                key = user_data["ai_api_key_openai"]
                preferences["openai_key_preview"] = f"{key[:8]}..." if len(key) > 8 else "***"
            
            if user_data.get("ai_api_key_claude"):
                key = user_data["ai_api_key_claude"]
                preferences["claude_key_preview"] = f"{key[:8]}..." if len(key) > 8 else "***"
            
            if user_data.get("ai_api_key_gemini"):
                key = user_data["ai_api_key_gemini"]
                preferences["gemini_key_preview"] = f"{key[:8]}..." if len(key) > 8 else "***"
            
            return {
                "status": "success",
                "preferences": preferences
            }
            
        except Exception as e:
            logger.error(f"Error getting AI preferences for user {user_id}: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to get preferences: {str(e)}"
            }


# Global service instance
ai_preferences_service = AIPreferencesService() 