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
    frontend_url: str = "http://localhost:8501"
    
    # Logging
    log_level: str = "INFO"
    
    def get_encryption_key(self) -> bytes:
        """Get encryption key as bytes"""
        if self.encryption_key:
            return self.encryption_key.encode()
        
        env_key = os.environ.get("ENCRYPTION_KEY")
        if env_key:
            return env_key.encode()
        
        return Fernet.generate_key()
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings() 