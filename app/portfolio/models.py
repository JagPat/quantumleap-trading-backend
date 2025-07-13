from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

class PortfolioSnapshot(BaseModel):
    user_id: str
    timestamp: datetime
    holdings: List[Any] 
    positions: List[Any]

class FetchResponse(BaseModel):
    status: str
    message: str
    snapshot: Optional[PortfolioSnapshot] = None
