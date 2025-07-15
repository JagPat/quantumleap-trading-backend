from fastapi import APIRouter, Depends, HTTPException
from .service import portfolio_service
from .models import FetchResponse
from ..auth.router import get_user_from_headers
from ..database.service import get_latest_portfolio_snapshot as get_snapshot_from_db

router = APIRouter(
    prefix="/api/portfolio",
    tags=["Portfolio"],
)

@router.post("/fetch-live", response_model=FetchResponse)
async def fetch_live_portfolio(user_id: str = Depends(get_user_from_headers)):
    """
    Fetches the latest portfolio from the broker, stores it, and returns it.
    """
    try:
        snapshot = portfolio_service.fetch_and_store_portfolio(user_id)
        return FetchResponse(status="success", message="Portfolio fetched and stored successfully.", snapshot=snapshot)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/latest", response_model=FetchResponse)
async def get_latest_snapshot(user_id: str = Depends(get_user_from_headers)):
    """
    Retrieves the latest stored portfolio snapshot for the user.
    """
    try:
        snapshot = portfolio_service.get_latest_portfolio(user_id)
        if snapshot:
            return FetchResponse(status="success", message="Latest snapshot retrieved.", snapshot=snapshot)
        else:
            return FetchResponse(status="not_found", message="No snapshot available for this user.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 