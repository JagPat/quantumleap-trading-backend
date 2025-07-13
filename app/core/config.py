"""
Core configuration management for QuantumLeap Trading Backend
"""
import os
from typing import Optional
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from cryptography.fernet import Fernet
from pydantic import Field


class Settings(BaseSettings):
    """Application settings"""
    
    # App Configuration
    app_name: str = "QuantumLeap Trading Backend API"
    app_version: str = "2.0.0"
    debug: bool = False
    
    # Database
    database_path: str = "trading_app.db"
    
    # Security
    encryption_key: Optional[str] = None
    
    # External URLs
    frontend_url: str = Field(
        default="http://localhost:5173",
        env="FRONTEND_URL",
        description="Frontend application URL for OAuth redirects"
    )
    
    # Logging
    log_level: str = "INFO"
    
    def get_encryption_key(self) -> bytes:
        """Get encryption key from environment variable"""
        env_key = os.environ.get("ENCRYPTION_KEY")
        if not env_key:
            raise ValueError("ENCRYPTION_KEY environment variable not set.")
        return env_key.encode()
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings() 