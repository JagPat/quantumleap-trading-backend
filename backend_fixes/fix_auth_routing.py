# Authentication Routing Fixes
# These fixes address HTTP method routing issues found in testing

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

class LogoutRequest(BaseModel):
    user_id: str = None

# Fix 1: Ensure login endpoint accepts POST with email field
@router.post("/api/auth/login")
async def login(request: LoginRequest):
    """
    User login endpoint
    
    Accepts email and password, returns JWT token if valid
    """
    # Your existing login logic here
    # Make sure it uses request.email (not username)
    pass

# Fix 2: Ensure logout endpoint accepts POST method
@router.post("/api/auth/logout") 
async def logout(request: LogoutRequest = None):
    """
    User logout endpoint
    
    Invalidates the current session/token
    """
    # Your existing logout logic here
    return {"message": "Successfully logged out"}

# Fix 3: Ensure AI endpoints accept correct HTTP methods
@router.post("/api/ai/chat")
async def ai_chat(request: dict):
    """AI Chat endpoint - should accept POST"""
    # Your existing AI chat logic
    pass

@router.post("/api/ai/analysis/comprehensive") 
async def ai_analysis(request: dict):
    """AI Analysis endpoint - should accept POST"""
    # Your existing AI analysis logic
    pass

@router.post("/api/ai/strategy-templates/deploy")
async def deploy_strategy(request: dict):
    """Strategy deployment endpoint - should accept POST"""
    # Your existing strategy deployment logic
    pass

@router.post("/api/ai/performance-analytics")
async def performance_analytics(request: dict):
    """Performance analytics endpoint - should accept POST"""
    # Your existing performance analytics logic
    pass

@router.post("/api/ai/market-intelligence")
async def market_intelligence(request: dict):
    """Market intelligence endpoint - should accept POST"""
    # Your existing market intelligence logic
    pass

@router.post("/api/ai/risk-settings")
async def risk_settings(request: dict):
    """Risk settings endpoint - should accept POST"""
    # Your existing risk settings logic
    pass

# Note: GET endpoints should remain GET
# @router.get("/api/ai/strategy-templates")  # This should stay GET
# @router.get("/api/ai/risk-metrics")        # This should stay GET  
# @router.get("/api/ai/learning-insights")   # This should stay GET
# @router.get("/api/ai/optimization-recommendations")  # This should stay GET
# @router.get("/api/ai/cost-tracking")       # This should stay GET