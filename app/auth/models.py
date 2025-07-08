"""
Authentication module models
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any


class GenerateSessionRequest(BaseModel):
    """Request model for generating broker session"""
    request_token: str
    api_key: str
    api_secret: str


class GenerateSessionResponse(BaseModel):
    """Response model for session generation"""
    status: str
    access_token: Optional[str] = None
    user_data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


class BrokerConnectionStatus(BaseModel):
    """Broker connection status model"""
    user_id: str
    is_connected: bool
    connection_status: str
    last_connected: Optional[str] = None


class UserCredentials(BaseModel):
    """User credentials model"""
    user_id: str
    api_key: str
    api_secret: str
    access_token: Optional[str] = None
    user_name: Optional[str] = None
    email: Optional[str] = None 