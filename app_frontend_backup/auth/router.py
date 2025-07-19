"""
Authentication Router
Redirects to existing auth endpoints until full migration
"""
from fastapi import APIRouter, Header, Depends
from fastapi.responses import RedirectResponse
from typing import Optional

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

def get_user_from_headers(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> str:
    """Extract user ID from headers - used by other modules"""
    if x_user_id:
        return x_user_id
    # Fallback to a default for testing
    return "default_user"

@router.get("/broker/status")
async def broker_status_redirect():
    """Redirect to health check for now"""
    return {"status": "ok", "message": "Auth module loaded"}

# ========================================
# PENDING BACKEND FEATURES (Frontend Support)
# ========================================

@router.get("/broker/test-oauth")
async def test_oauth():
    """Test OAuth endpoint - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "OAuth testing endpoint is planned but not yet implemented",
        "feature": "oauth_testing",
        "frontend_expectation": "Test OAuth flow without actual broker connection",
        "planned_features": [
            "Mock OAuth flow",
            "Test credentials validation",
            "Development mode support"
        ]
    }

@router.post("/broker/generate-session")
async def generate_session(session_data: dict):
    """Generate broker session - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "Session generation is planned but not yet implemented",
        "feature": "session_generation",
        "frontend_expectation": "Create broker session from OAuth tokens",
        "planned_features": [
            "Token validation",
            "Session creation",
            "User authentication"
        ],
        "received_data": session_data
    }

@router.post("/broker/invalidate-session")
async def invalidate_session(invalidation_data: dict):
    """Invalidate broker session - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "Session invalidation is planned but not yet implemented",
        "feature": "session_invalidation",
        "frontend_expectation": "Logout and clear broker session",
        "planned_features": [
            "Session cleanup",
            "Token revocation",
            "Security logout"
        ],
        "received_data": invalidation_data
    }

@router.get("/broker/session")
async def get_session(user_id: str = Depends(get_user_from_headers)):
    """Get broker session - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "Session retrieval is planned but not yet implemented",
        "feature": "session_retrieval",
        "user_id": user_id,
        "frontend_expectation": "Get current broker session status",
        "planned_features": [
            "Session status check",
            "Token validation",
            "Connection status"
        ]
    }

@router.get("/broker/callback")
async def oauth_callback():
    """OAuth callback - PENDING BACKEND IMPLEMENTATION"""
    return {
        "status": "not_implemented",
        "message": "OAuth callback is planned but not yet implemented",
        "feature": "oauth_callback",
        "frontend_expectation": "Handle OAuth callback from broker",
        "planned_features": [
            "Callback processing",
            "Token exchange",
            "User session creation"
        ]
    }

# This is a minimal router to satisfy the import
# The actual auth endpoints are handled by the existing codebase 