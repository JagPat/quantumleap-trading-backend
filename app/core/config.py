"""
Application Configuration - Pydantic v2 Compatible
"""

import os
from typing import List, Optional

try:
    from pydantic_settings import BaseSettings
    from pydantic import Field
    PYDANTIC_V2_AVAILABLE = True
except ImportError:
    # Fallback for environments without pydantic-settings
    from pydantic import BaseModel, Field
    PYDANTIC_V2_AVAILABLE = False
    
    class BaseSettings(BaseModel):
        class Config:
            env_file = ".env"
            case_sensitive = False

class Settings(BaseSettings):
    """Application settings - Pydantic v2 compatible"""
    
    # Database settings
    database_url: str = Field(
        default="sqlite:///./quantum_leap.db",
        description="Database connection URL"
    )
    database_path: str = Field(
        default="quantum_leap.db",
        description="SQLite database file path"
    )
    
    # Redis settings
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL"
    )
    
    # AI API Keys
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key"
    )
    anthropic_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API key"
    )
    google_api_key: Optional[str] = Field(
        default=None,
        description="Google API key"
    )
    
    # Kite Connect API settings
    kite_api_key: Optional[str] = Field(
        default=None,
        description="Kite Connect API key"
    )
    kite_api_secret: Optional[str] = Field(
        default=None,
        description="Kite Connect API secret"
    )
    kite_redirect_url: str = Field(
        default="http://localhost:8000/api/auth/callback",
        description="Kite Connect redirect URL"
    )
    
    # Security settings
    encryption_key: str = Field(
        default="HKQ5bWD9sbwXxKsWVuF57mVf6Ty_WtGtoX8GwPCmtD0=",
        description="Encryption key for sensitive data"
    )
    session_secret: str = Field(
        default="quantum-leap-secure-session-secret-2025",
        description="Session secret key"
    )
    
    # Application settings
    environment: str = Field(
        default="production",
        description="Application environment"
    )
    debug: bool = Field(
        default=False,
        description="Debug mode"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    
    # Server settings
    host: str = Field(
        default="0.0.0.0",
        description="Server host"
    )
    port: str = Field(
        default="8000",
        description="Server port"
    )
    
    # Frontend settings
    frontend_url: str = Field(
        default="http://localhost:5173",
        description="Frontend URL for CORS"
    )
    cors_origins: str = Field(
        default="https://quantum-leap-frontend.vercel.app,http://localhost:3000,http://localhost:5173",
        description="CORS allowed origins (comma-separated)"
    )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Convert comma-separated CORS origins to list"""
        if not self.cors_origins:
            return ["http://localhost:5173"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        # Allow environment variables to override defaults
        env_prefix = ""

# Global settings instance
settings = Settings()