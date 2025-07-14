from fastapi import APIRouter, Depends, HTTPException
from .service import portfolio_service
from .models import FetchResponse
from ..auth.dependencies import get_user_from_headers
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

@router.get("/holdings")
async def get_holdings(user_id: str = Depends(get_user_from_headers)):
    """
    Retrieves holdings from the latest portfolio snapshot for the user.
    """
    try:
        snapshot = portfolio_service.get_latest_portfolio(user_id)
        if snapshot and snapshot.holdings:
            return {"status": "success", "data": snapshot.holdings}
        else:
            return {"status": "not_found", "data": [], "message": "No holdings data available for this user."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/positions")
async def get_positions(user_id: str = Depends(get_user_from_headers)):
    """
    Retrieves positions from the latest portfolio snapshot for the user.
    """
    try:
        snapshot = portfolio_service.get_latest_portfolio(user_id)
        if snapshot and snapshot.positions:
            return {"status": "success", "data": {"net": snapshot.positions}}
        else:
            return {"status": "not_found", "data": {"net": []}, "message": "No positions data available for this user."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/holdings")
async def post_holdings(user_id: str = Depends(get_user_from_headers)):
    return await get_holdings(user_id)

@router.post("/positions")
async def post_positions(user_id: str = Depends(get_user_from_headers)):
    return await get_positions(user_id)
