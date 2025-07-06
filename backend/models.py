from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# Request Models
class GenerateSessionRequest(BaseModel):
    request_token: str = Field(..., description="The one-time request token from the broker's successful login redirect.")
    user_id: str = Field(..., description="The unique ID of the user from the frontend.")
    api_key: str = Field(..., description="The user's broker API key.")
    api_secret: str = Field(..., description="The user's broker API secret.")

# Response Models
class UserData(BaseModel):
    user_id: str
    user_name: str
    email: str

class GenerateSessionResponse(BaseModel):
    status: str = Field(example="success")
    message: str = Field(example="Broker connected successfully.")
    data: UserData

class PortfolioSummaryData(BaseModel):
    total_value: float
    total_pnl: float
    todays_pnl: float

class PortfolioSummaryResponse(BaseModel):
    status: str = Field(example="success")
    data: PortfolioSummaryData

class HoldingItem(BaseModel):
    symbol: str
    quantity: float
    avg_price: float
    current_price: float
    pnl: float

class HoldingsResponse(BaseModel):
    status: str = Field(example="success")
    data: List[HoldingItem]

class PositionsResponse(BaseModel):
    status: str = Field(example="success")
    data: Dict[str, Any]  # Keeping flexible structure as per spec

# Error Response Models
class ErrorResponse(BaseModel):
    status: str = Field(example="error")
    message: str
    error_code: Optional[str] = None 