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
    
<<<<<<< HEAD
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    
=======
>>>>>>> 1dc30303b85cf886c4618fb5b1e5e73642d1324b
    # Database
    database_path: str = "trading_app.db"
    
    # Security
    encryption_key: Optional[str] = None
<<<<<<< HEAD
    session_secret: str = "a-secure-secret-key-for-oauth-state-management"
    
    # Frontend Configuration
    frontend_url: str = "http://localhost:5173"
    
    # AI Provider Configuration
    openai_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
=======
    
    # External URLs
    frontend_url: str = Field(
        default="http://localhost:5173",
        env="FRONTEND_URL",
        description="Frontend application URL for OAuth redirects"
    )
>>>>>>> 1dc30303b85cf886c4618fb5b1e5e73642d1324b
    
    # Logging
    log_level: str = "INFO"
    
<<<<<<< HEAD
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Generate encryption key if not provided
        if not self.encryption_key:
            self.encryption_key = Fernet.generate_key().decode()
            
        # Load from environment variables
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.database_path = os.getenv("DATABASE_PATH", self.database_path)
        self.frontend_url = os.getenv("FRONTEND_URL", self.frontend_url)
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.claude_api_key = os.getenv("CLAUDE_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.log_level = os.getenv("LOG_LEVEL", self.log_level)
=======
    def get_encryption_key(self) -> bytes:
        """Get encryption key from environment variable"""
        env_key = os.environ.get("ENCRYPTION_KEY")
        if not env_key:
            raise ValueError("ENCRYPTION_KEY environment variable not set.")
        return env_key.encode()
    
    class Config:
        env_file = ".env"
        case_sensitive = False

>>>>>>> 1dc30303b85cf886c4618fb5b1e5e73642d1324b

# Global settings instance
settings = Settings() 