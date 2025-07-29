"""
AI Engine Service
Handles AI provider management, preferences storage, and AI operations
"""
import json
import asyncio
from typing import Optional, Dict, Any, List
from cryptography.fernet import Fernet
from app.core.config import settings
import sqlite3
from app.core.config import settings
from app.ai_engine.models import AIPreferences, AIPreferencesRequest
import openai
import anthropic
import google.generativeai as genai

class AIEngineService:
    def __init__(self):
        self.encryption_key = settings.encryption_key
        if self.encryption_key:
            self.cipher = Fernet(self.encryption_key.encode())
        else:
            self.cipher = None

    def encrypt_api_key(self, api_key: str) -> str:
        """Encrypt API key for secure storage"""
        if not self.cipher or not api_key:
            return api_key
        return self.cipher.encrypt(api_key.encode()).decode()

    def decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt API key for use"""
        if not self.cipher or not encrypted_key:
            return encrypted_key
        try:
            return self.cipher.decrypt(encrypted_key.encode()).decode()
        except:
            return encrypted_key

    async def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user AI preferences from database"""
        try:
            conn = sqlite3.connect(settings.database_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT openai_api_key, claude_api_key, gemini_api_key, grok_api_key
                FROM ai_user_preferences 
                WHERE user_id = ?
            """, (user_id,))
            result = cursor.fetchone()
            
            if result:
                # Decrypt API keys
                openai_key = self.decrypt_api_key(result[0]) if result[0] else None
                claude_key = self.decrypt_api_key(result[1]) if result[1] else None
                gemini_key = self.decrypt_api_key(result[2]) if result[2] else None
                grok_key = self.decrypt_api_key(result[3]) if result[3] else None
                
                return {
                    "preferred_ai_provider": "auto",
                    "provider_priorities": None,
                    "cost_limits": None,
                    "risk_tolerance": "medium",
                    "trading_style": "balanced",
                    "openai_api_key": openai_key,
                    "claude_api_key": claude_key,
                    "gemini_api_key": gemini_key,
                    "grok_api_key": grok_key,
                    "has_openai_key": bool(openai_key and len(openai_key.strip()) > 0),
                    "has_claude_key": bool(claude_key and len(claude_key.strip()) > 0),
                    "has_gemini_key": bool(gemini_key and len(gemini_key.strip()) > 0),
                    "has_grok_key": bool(grok_key and len(grok_key.strip()) > 0),
                    "openai_key_preview": self.get_key_preview(openai_key),
                    "claude_key_preview": self.get_key_preview(claude_key),
                    "gemini_key_preview": self.get_key_preview(gemini_key),
                    "grok_key_preview": self.get_key_preview(grok_key)
                }
            return None
        except Exception as e:
            print(f"Error getting user preferences: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def get_key_preview(self, api_key: str) -> str:
        """Get a preview of the API key (first 8 chars + ...)"""
        try:
            if not api_key or len(api_key.strip()) == 0:
                return "***"
            if len(api_key) > 8:
                return f"{api_key[:8]}..."
            return "***"
        except:
            return "***"

    async def save_user_preferences(self, user_id: str, preferences: AIPreferencesRequest) -> bool:
        """Save user AI preferences to database"""
        try:
            conn = sqlite3.connect(settings.database_path)
            cursor = conn.cursor()
            
            # Encrypt API keys before storing
            openai_key = self.encrypt_api_key(preferences.openai_api_key) if preferences.openai_api_key else None
            claude_key = self.encrypt_api_key(preferences.claude_api_key) if preferences.claude_api_key else None
            gemini_key = self.encrypt_api_key(preferences.gemini_api_key) if preferences.gemini_api_key else None
            grok_key = self.encrypt_api_key(preferences.grok_api_key) if preferences.grok_api_key else None
            
            # Insert or update preferences (using only the columns that exist)
            cursor.execute("""
                INSERT OR REPLACE INTO ai_user_preferences 
                (user_id, openai_api_key, claude_api_key, gemini_api_key, grok_api_key, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                user_id,
                openai_key,
                claude_key,
                gemini_key,
                grok_key
            ))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving user preferences: {e}")
            return False
        finally:
            if conn:
                conn.close()

    async def validate_api_key(self, provider: str, api_key: str) -> Dict[str, Any]:
        """Validate API key against provider"""
        try:
            if provider == "openai":
                client = openai.AsyncOpenAI(api_key=api_key)
                await client.models.list()
                return {"valid": True, "message": "OpenAI API key is valid"}
            
            elif provider == "claude":
                client = anthropic.AsyncAnthropic(api_key=api_key)
                # Test with a simple message
                await client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Hello"}]
                )
                return {"valid": True, "message": "Claude API key is valid"}
            
            elif provider == "gemini":
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-pro')
                await asyncio.to_thread(model.generate_content, "Hello")
                return {"valid": True, "message": "Gemini API key is valid"}
            
            else:
                return {"valid": False, "message": f"Unknown provider: {provider}"}
                
        except Exception as e:
            return {"valid": False, "message": f"API key validation failed: {str(e)}"}

    async def get_ai_signals(self, user_id: str, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get AI trading signals for user"""
        # Placeholder implementation
        return {
            "status": "success",
            "signals": [
                {
                    "symbol": "RELIANCE",
                    "signal": "BUY",
                    "confidence": 0.85,
                    "price_target": 2650,
                    "stop_loss": 2450,
                    "reasoning": "Strong fundamentals and technical breakout"
                },
                {
                    "symbol": "TCS",
                    "signal": "HOLD",
                    "confidence": 0.75,
                    "reasoning": "Stable growth but limited upside in short term"
                }
            ],
            "message": "AI signals generated successfully"
        }

    async def generate_strategy(self, user_id: str, portfolio_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Generate AI trading strategy"""
        # Placeholder implementation
        return {
            "status": "success",
            "strategy": {
                "name": "Balanced Growth Strategy",
                "risk_level": "medium",
                "allocation": {
                    "equity": 70,
                    "debt": 20,
                    "cash": 10
                },
                "recommendations": [
                    "Increase tech sector exposure",
                    "Consider defensive stocks for stability",
                    "Monitor market volatility"
                ]
            },
            "message": "Strategy generated successfully"
        }

# Global service instance
ai_service = AIEngineService()

# Alias for backward compatibility
AIService = AIEngineService 