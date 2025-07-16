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
            cursor.execute(
                "SELECT preferences FROM ai_preferences WHERE user_id = ?",
                (user_id,)
            )
            result = cursor.fetchone()
            
            if result:
                preferences = json.loads(result[0])
                # Decrypt API keys for display (partial)
                if preferences.get('openai_api_key'):
                    preferences['openai_api_key_preview'] = self.get_key_preview(preferences['openai_api_key'])
                if preferences.get('claude_api_key'):
                    preferences['claude_api_key_preview'] = self.get_key_preview(preferences['claude_api_key'])
                if preferences.get('gemini_api_key'):
                    preferences['gemini_api_key_preview'] = self.get_key_preview(preferences['gemini_api_key'])
                return preferences
            return None
        except Exception as e:
            print(f"Error getting user preferences: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def get_key_preview(self, encrypted_key: str) -> str:
        """Get a preview of the API key (first 8 chars + *****)"""
        try:
            if not encrypted_key:
                return ""
            decrypted = self.decrypt_api_key(encrypted_key)
            if len(decrypted) > 8:
                return f"{decrypted[:8]}*****"
            return "*****"
        except:
            return "*****"

    async def save_user_preferences(self, user_id: str, preferences: AIPreferencesRequest) -> bool:
        """Save user AI preferences to database"""
        try:
            # Encrypt API keys
            prefs_dict = preferences.dict()
            if prefs_dict.get('openai_api_key'):
                prefs_dict['openai_api_key'] = self.encrypt_api_key(prefs_dict['openai_api_key'])
            if prefs_dict.get('claude_api_key'):
                prefs_dict['claude_api_key'] = self.encrypt_api_key(prefs_dict['claude_api_key'])
            if prefs_dict.get('gemini_api_key'):
                prefs_dict['gemini_api_key'] = self.encrypt_api_key(prefs_dict['gemini_api_key'])

            conn = sqlite3.connect(settings.database_path)
            cursor = conn.cursor()
            # Create table if not exists
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ai_preferences (
                    user_id TEXT PRIMARY KEY,
                    preferences TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insert or update preferences
            cursor.execute('''
                INSERT OR REPLACE INTO ai_preferences (user_id, preferences, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, json.dumps(prefs_dict)))
            
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