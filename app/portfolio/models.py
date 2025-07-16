"""
Portfolio data models
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any

class FetchResponse(BaseModel):
    """Response model for portfolio fetch operations"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class PortfolioSnapshot(BaseModel):
    """Portfolio snapshot data model"""
    user_id: str
    holdings: list
    positions: list
    timestamp: str
    total_value: Optional[float] = None
    day_pnl: Optional[float] = None
    total_pnl: Optional[float] = None
