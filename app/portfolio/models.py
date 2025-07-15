from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class PortfolioSnapshot(BaseModel):
    user_id: str
    holdings: List[Dict[str, Any]]
    positions: Dict[str, Any]
    summary: Dict[str, float]
    imported_at: str

class FetchResponse(BaseModel):
    status: str
    message: str
    snapshot: Optional[PortfolioSnapshot] = None 