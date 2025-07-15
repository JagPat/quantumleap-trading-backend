from pydantic import BaseModel
<<<<<<< HEAD
from typing import List, Dict, Any, Optional

class PortfolioSnapshot(BaseModel):
    user_id: str
    holdings: List[Dict[str, Any]]
    positions: Dict[str, Any]
    summary: Dict[str, float]
    imported_at: str
=======
from typing import List, Optional, Any
from datetime import datetime

class PortfolioSnapshot(BaseModel):
    user_id: str
    timestamp: datetime
    holdings: List[Any] 
    positions: List[Any]
>>>>>>> 1dc30303b85cf886c4618fb5b1e5e73642d1324b

class FetchResponse(BaseModel):
    status: str
    message: str
<<<<<<< HEAD
    snapshot: Optional[PortfolioSnapshot] = None 
=======
    snapshot: Optional[PortfolioSnapshot] = None
>>>>>>> 1dc30303b85cf886c4618fb5b1e5e73642d1324b
