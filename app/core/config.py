"""
Core configuration management for QuantumLeap Trading Backend
"""
import os
from typing import Optional
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
    encryption_key: bytes = None
    
    # External URLs
    frontend_url: str = "http://localhost:8501"
    
    # Logging
    log_level: str = "INFO"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Generate or get encryption key
        if not self.encryption_key:
            env_key = os.environ.get("ENCRYPTION_KEY")
            if env_key:
                self.encryption_key = env_key.encode()
            else:
                self.encryption_key = Fernet.generate_key()
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings() 