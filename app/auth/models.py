"""
Authentication models - Request/Response schemas for broker authentication
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel


class GenerateSessionRequest(BaseModel):
    """Request model for generating broker session"""
    request_token: str
    api_key: str
    api_secret: str


class GenerateSessionResponse(BaseModel):
    """Response model for broker session generation"""
    status: str
    access_token: Optional[str] = None
    user_data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


class BrokerStatusResponse(BaseModel):
    """Response model for broker connection status"""
    status: str
    is_connected: bool
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    last_sync: Optional[str] = None
    message: Optional[str] = None


class UserCredentials(BaseModel):
    """User credentials model"""
    user_id: str
    api_key: str
    api_secret: str
    access_token: Optional[str] = None
    user_name: Optional[str] = None
    email: Optional[str] = None


class Base44User(BaseModel):
    """Base44 user information extracted from JWT token"""
    email: str
    user_id: str
    app_id: Optional[str] = None
    permissions: Optional[list] = None


class BrokerProfileResponse(BaseModel):
    """Response model for broker profile information"""
    status: str
    user_data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None 