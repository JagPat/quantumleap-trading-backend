"""
Application Configuration
"""

import os
from typing import Optional

try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for deployment environments
    import os
    class BaseSettings:
        def __init__(self, **kwargs):
            # Set default values
            self.database_url = os.getenv("DATABASE_URL", "sqlite:///./trading_app.db")
            self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
            self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
            self.google_api_key = os.getenv("GOOGLE_API_KEY", "")
            self.kite_api_key = os.getenv("KITE_API_KEY", "")
            self.kite_api_secret = os.getenv("KITE_API_SECRET", "")
            self.kite_redirect_url = os.getenv("KITE_REDIRECT_URL", "http://localhost:8000/api/auth/callback")
            self.encryption_key = os.getenv("ENCRYPTION_KEY", "HKQ5bWD9sbwXxKsWVuF57mVf6Ty_WtGtoX8GwPCmtD0=")
            self.session_secret = os.getenv("SESSION_SECRET", "quantum-leap-secure-session-secret-2025")
            self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
            self.database_path = os.getenv("DATABASE_PATH", "trading_app.db")
            self.log_level = os.getenv("LOG_LEVEL", "INFO")
            self.host = os.getenv("HOST", "0.0.0.0")
            self.port = os.getenv("PORT", "8000")
            
            # Override with any provided kwargs
            for key, value in kwargs.items():
                setattr(self, key, value)

class Settings(BaseSettings):
    """Application settings"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Set additional attributes that might not be in BaseSettings
        if not hasattr(self, 'database_url'):
            self.database_url = os.getenv("DATABASE_URL", "sqlite:///./quantum_leap.db")
        if not hasattr(self, 'openai_api_key'):
            self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not hasattr(self, 'anthropic_api_key'):
            self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if not hasattr(self, 'google_api_key'):
            self.google_api_key = os.getenv("GOOGLE_API_KEY")
        if not hasattr(self, 'kite_api_key'):
            self.kite_api_key = os.getenv("KITE_API_KEY")
        if not hasattr(self, 'kite_api_secret'):
            self.kite_api_secret = os.getenv("KITE_API_SECRET")
        if not hasattr(self, 'environment'):
            self.environment = os.getenv("ENVIRONMENT", "production")
        if not hasattr(self, 'debug'):
            self.debug = os.getenv("DEBUG", "false").lower() == "true"
        if not hasattr(self, 'cors_origins'):
            self.cors_origins = [
                "https://quantum-leap-frontend.vercel.app",
                "http://localhost:3000",
                "http://localhost:5173"
            ]

# Global settings instance
settings = Settings()
