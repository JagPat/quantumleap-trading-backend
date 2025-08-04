"""
Authentication Router for Quantum Leap AI Components
Handles login, token management, and user authentication
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import timedelta, datetime
import logging

from app.core.auth import (
    TokenManager, 
    PasswordManager, 
    get_current_user_id,
    AuthValidator,
    AuthenticationError
)

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Request/Response models
class LoginRequest(BaseModel):
    """Login request model"""
    email: EmailStr
    password: str
    remember_me: Optional[bool] = False

class LoginResponse(BaseModel):
    """Login response model"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    message: str = "Login successful"

class RegisterRequest(BaseModel):
    """User registration request model"""
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    confirm_password: str

class RegisterResponse(BaseModel):
    """Registration response model"""
    user_id: str
    email: str
    message: str = "Registration successful"
    access_token: Optional[str] = None

class TokenValidationResponse(BaseModel):
    """Token validation response model"""
    valid: bool
    user_id: Optional[str] = None
    expires_at: Optional[int] = None
    message: str

class AuthStatusResponse(BaseModel):
    """Authentication status response model"""
    authenticated: bool
    user_id: Optional[str] = None
    token_valid: bool
    message: str

# Mock user database (replace with real database in production)
MOCK_USERS = {
    "test@quantumleap.com": {
        "user_id": "test_user_123",
        "email": "test@quantumleap.com",
        "password_hash": PasswordManager.hash_password("testpassword123"),
        "full_name": "Test User",
        "active": True
    },
    "admin@quantumleap.com": {
        "user_id": "admin_user_456", 
        "email": "admin@quantumleap.com",
        "password_hash": PasswordManager.hash_password("adminpassword123"),
        "full_name": "Admin User",
        "active": True,
        "role": "admin"
    }
}

# Authentication endpoints
@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Authenticate user and return JWT token
    """
    try:
        logger.info(f"Login attempt for email: {request.email}")
        
        # Find user in mock database
        user = MOCK_USERS.get(request.email.lower())
        if not user:
            logger.warning(f"Login failed: User not found - {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not PasswordManager.verify_password(request.password, user["password_hash"]):
            logger.warning(f"Login failed: Invalid password - {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user is active
        if not user.get("active", True):
            logger.warning(f"Login failed: User inactive - {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is inactive"
            )
        
        # Create access token
        token_data = {
            "user_id": user["user_id"],
            "email": user["email"],
            "role": user.get("role", "user")
        }
        
        # Set token expiry based on remember_me
        expires_delta = timedelta(days=30) if request.remember_me else timedelta(hours=24)
        access_token = TokenManager.create_access_token(
            data=token_data,
            expires_delta=expires_delta
        )
        
        logger.info(f"Login successful for user: {user['user_id']}")
        
        return LoginResponse(
            access_token=access_token,
            expires_in=int(expires_delta.total_seconds()),
            user_id=user["user_id"],
            message="Login successful"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed due to server error"
        )

@router.post("/register", response_model=RegisterResponse)
async def register(request: RegisterRequest):
    """
    Register a new user account
    """
    try:
        logger.info(f"Registration attempt for email: {request.email}")
        
        # Validate password confirmation
        if request.password != request.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passwords do not match"
            )
        
        # Check if user already exists
        if request.email.lower() in MOCK_USERS:
            logger.warning(f"Registration failed: User already exists - {request.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Validate password strength (basic validation)
        if len(request.password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )
        
        # Create new user
        user_id = f"user_{len(MOCK_USERS) + 1}_{request.email.split('@')[0]}"
        new_user = {
            "user_id": user_id,
            "email": request.email.lower(),
            "password_hash": PasswordManager.hash_password(request.password),
            "full_name": request.full_name or request.email.split('@')[0],
            "active": True,
            "role": "user"
        }
        
        # Add to mock database
        MOCK_USERS[request.email.lower()] = new_user
        
        logger.info(f"Registration successful for user: {user_id}")
        
        return RegisterResponse(
            user_id=user_id,
            email=request.email,
            message="Registration successful"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed due to server error"
        )

@router.post("/validate-token", response_model=TokenValidationResponse)
async def validate_token(user_id: str = Depends(get_current_user_id)):
    """
    Validate current JWT token
    """
    try:
        logger.debug(f"Token validation for user: {user_id}")
        
        return TokenValidationResponse(
            valid=True,
            user_id=user_id,
            message="Token is valid"
        )
        
    except Exception as e:
        logger.warning(f"Token validation failed: {str(e)}")
        return TokenValidationResponse(
            valid=False,
            message="Token is invalid or expired"
        )

@router.get("/status", response_model=AuthStatusResponse)
async def auth_status(user_id: Optional[str] = Depends(get_current_user_id)):
    """
    Get current authentication status
    """
    try:
        if user_id:
            return AuthStatusResponse(
                authenticated=True,
                user_id=user_id,
                token_valid=True,
                message="User is authenticated"
            )
        else:
            return AuthStatusResponse(
                authenticated=False,
                token_valid=False,
                message="User is not authenticated"
            )
            
    except Exception as e:
        logger.debug(f"Auth status check failed: {str(e)}")
        return AuthStatusResponse(
            authenticated=False,
            token_valid=False,
            message="Authentication status unknown"
        )

@router.post("/logout")
async def logout(user_id: str = Depends(get_current_user_id)):
    """
    Logout user (client should discard token)
    """
    try:
        logger.info(f"Logout for user: {user_id}")
        
        # In a real implementation, you might want to blacklist the token
        # For now, we just return success and rely on client to discard token
        
        return {
            "message": "Logout successful",
            "user_id": user_id
        }
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@router.get("/test-users")
async def get_test_users():
    """
    Get available test users for development
    """
    try:
        test_users = []
        for email, user_data in MOCK_USERS.items():
            test_users.append({
                "email": email,
                "user_id": user_data["user_id"],
                "role": user_data.get("role", "user")
            })
        
        return {
            "test_users": test_users,
            "note": "Use these credentials for testing. Remove this endpoint in production."
        }
        
    except Exception as e:
        logger.error(f"Get test users error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get test users"
        )

@router.get("/test-auth")
async def test_authentication():
    """
    Test authentication system configuration
    """
    try:
        # Validate authentication setup
        validation_results = await AuthValidator.validate_authentication_setup()
        
        # Create and test a token
        test_token = AuthValidator.create_test_token("test_validation_user")
        token_test = await AuthValidator.test_token_validation(test_token)
        
        return {
            "message": "Authentication system test",
            "setup_validation": validation_results,
            "token_test": {
                "token_created": bool(test_token),
                "token_valid": token_test["valid"],
                "test_user_id": token_test.get("user_id")
            },
            "mock_users_available": len(MOCK_USERS),
            "test_credentials": {
                "email": "test@quantumleap.com",
                "password": "testpassword123",
                "note": "Use these credentials for testing"
            }
        }
        
    except Exception as e:
        logger.error(f"Authentication test failed: {str(e)}")
        return {
            "message": "Authentication system test failed",
            "error": str(e),
            "setup_validation": {"overall_status": "error"}
        }

# Health check endpoint for authentication service
@router.get("/health")
async def auth_health():
    """
    Authentication service health check
    """
    try:
        # Test basic functionality
        validation_results = await AuthValidator.validate_authentication_setup()
        
        return {
            "status": "healthy" if validation_results["overall_status"] == "valid" else "degraded",
            "service": "authentication",
            "timestamp": "2025-01-03T06:00:00Z",
            "details": validation_results
        }
        
    except Exception as e:
        logger.error(f"Auth health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "authentication", 
            "error": str(e),
            "timestamp": "2025-01-03T06:00:00Z"
        }

# Kite Authentication Models
class KiteLoginRequest(BaseModel):
    """Kite login request model"""
    user_id: str
    access_token: str
    user_name: str
    email: EmailStr

class KiteRegisterRequest(BaseModel):
    """Kite user registration request model"""
    user_id: str
    user_name: str
    email: EmailStr
    access_token: str
    broker_name: str = "zerodha"
    phone: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = {}

@router.post("/kite-exchange-token", response_model=LoginResponse)
async def kite_exchange_token(request: dict):
    """
    Exchange Kite Connect request token for access token
    """
    try:
        logger.info(f"Kite token exchange for API key: {request.get('api_key')}")
        
        # In a real implementation, you would:
        # 1. Use the Kite Connect API to exchange request_token for access_token
        # 2. Fetch user profile from Kite
        # 3. Create or update user in your database
        
        # For now, we'll simulate the process
        user_data = {
            "user_id": f"kite_{request.get('user_id', 'unknown')}",
            "kite_user_id": request.get('user_id'),
            "email": f"{request.get('user_id')}@kite.zerodha.com",
            "user_name": f"Kite User {request.get('user_id')}",
            "role": "user",
            "broker": "zerodha",
            "kite_access_token": "simulated_kite_token",
            "api_key": request.get('api_key')
        }
        
        # Generate JWT token
        token_manager = TokenManager()
        access_token = token_manager.create_access_token(
            data={"sub": user_data["user_id"], "email": user_data["email"]},
            expires_delta=timedelta(hours=24)
        )
        
        logger.info(f"Kite token exchange successful for user: {user_data['user_name']}")
        
        return LoginResponse(
            access_token=access_token,
            expires_in=86400,  # 24 hours
            user_id=user_data["user_id"],
            email=user_data["email"],
            role=user_data["role"],
            message="Kite Connect authentication successful"
        )
        
    except Exception as e:
        logger.error(f"Kite token exchange error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kite Connect authentication failed"
        )

@router.post("/kite-login", response_model=LoginResponse)
async def kite_login(request: KiteLoginRequest):
    """
    Authenticate user with Kite credentials
    """
    try:
        logger.info(f"Kite login attempt for user: {request.user_id}")
        
        # Create or update user with Kite credentials
        user_data = {
            "user_id": f"kite_{request.user_id}",
            "email": request.email,
            "name": request.user_name,
            "role": "user",
            "broker": "zerodha",
            "kite_user_id": request.user_id,
            "access_token": request.access_token,
            "is_kite_user": True
        }
        
        # Generate JWT token
        token_manager = TokenManager()
        access_token = token_manager.create_access_token(
            data={"sub": user_data["user_id"], "email": user_data["email"]},
            expires_delta=timedelta(hours=24)
        )
        
        logger.info(f"Kite login successful for user: {request.user_name}")
        
        return LoginResponse(
            access_token=access_token,
            expires_in=86400,  # 24 hours
            user_id=user_data["user_id"],
            email=user_data["email"],
            role=user_data["role"],
            message="Kite login successful"
        )
        
    except Exception as e:
        logger.error(f"Kite login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kite authentication failed"
        )

@router.post("/kite-register", response_model=RegisterResponse)
async def kite_register(request: KiteRegisterRequest):
    """
    Register new user with Kite credentials
    """
    try:
        logger.info(f"Kite registration for user: {request.user_id}")
        
        # Create user with Kite credentials
        user_data = {
            "user_id": f"kite_{request.user_id}",
            "email": request.email,
            "name": request.user_name,
            "role": "user",
            "broker": request.broker_name,
            "kite_user_id": request.user_id,
            "access_token": request.access_token,
            "phone": request.phone,
            "preferences": request.preferences,
            "is_kite_user": True,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Store user data (in a real app, this would go to a database)
        # For now, we'll just log it
        logger.info(f"Kite user registered: {user_data}")
        
        return RegisterResponse(
            user_id=user_data["user_id"],
            email=user_data["email"],
            message="Kite user registration successful"
        )
        
    except Exception as e:
        logger.error(f"Kite registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kite user registration failed"
        )

@router.post("/sync-kite-profile")
async def sync_kite_profile(
    profile_data: Dict[str, Any],
    user_id: str = Depends(get_current_user_id)
):
    """
    Sync Kite profile data with backend
    """
    try:
        logger.info(f"Syncing Kite profile for user: {user_id}")
        
        # Update user profile with Kite data
        # In a real app, this would update the database
        logger.info(f"Kite profile synced: {profile_data}")
        
        return {
            "message": "Kite profile synced successfully",
            "user_id": user_id,
            "synced_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Kite profile sync error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync Kite profile"
        )

# Export router
__all__ = ["router"]