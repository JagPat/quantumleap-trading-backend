"""
Core configuration management for QuantumLeap Trading Backend
"""
import os
from typing import Optional
from cryptography.fernet import Fernet
from pydantic import Field
import logging

logger = logging.getLogger(__name__)

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # App Configuration
    app_name: str = "QuantumLeap Trading Backend API"
    app_version: str = "2.0.0"
    debug: bool = False
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = Field(
        default=8000,
        env="PORT",
        description="Server port (Railway provides this via PORT env var)"
    )
    
    # Database
    database_path: str = "trading_app.db"
    
    # Security
    encryption_key: Optional[str] = None
    session_secret: str = "a-secure-secret-key-for-oauth-state-management"
    
    # External URLs
    frontend_url: str = Field(
        default="http://localhost:5173",
        env="FRONTEND_URL",
        description="Frontend application URL for OAuth redirects"
    )
    
    # Logging
    log_level: str = "INFO"
    
    # Kite Connect Configuration
    kite_api_timeout: int = 30
    kite_api_retries: int = 3
    
    # Railway Configuration
    railway_environment: str = "development"
    
    # AI Engine API Keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    
    def get_encryption_key(self) -> bytes:
        """Get encryption key from environment variable or generate one"""
        env_key = self.encryption_key or os.environ.get("ENCRYPTION_KEY")
        if not env_key:
            logger.warning("ENCRYPTION_KEY not found. Generating temporary key for this session.")
            from cryptography.fernet import Fernet
            return Fernet.generate_key()
        return env_key.encode()
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"


# Global settings instance
settings = Settings()
