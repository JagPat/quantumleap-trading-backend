"""
JWT Authentication Middleware for Quantum Leap AI Components
Fixes critical authentication security vulnerability (0% → 80%+ target)
"""

import os
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Security configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "quantum-leap-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme
security = HTTPBearer()

class AuthenticationError(Exception):
    """Custom authentication error"""
    pass

class TokenManager:
    """JWT Token management utilities"""
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a new JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
        
        to_encode.update({"exp": expire, "iat": datetime.utcnow()})
        
        try:
            encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
            logger.info(f"Created access token for user: {data.get('user_id', 'unknown')}")
            return encoded_jwt
        except Exception as e:
            logger.error(f"Failed to create access token: {str(e)}")
            raise AuthenticationError("Failed to create access token")
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Check if token has expired
            exp = payload.get("exp")
            if exp and datetime.utcnow() > datetime.fromtimestamp(exp):
                raise AuthenticationError("Token has expired")
            
            # Validate required fields
            user_id = payload.get("user_id")
            if not user_id:
                raise AuthenticationError("Invalid token: missing user_id")
            
            logger.debug(f"Token verified successfully for user: {user_id}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token verification failed: Token expired")
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token verification failed: Invalid token - {str(e)}")
            raise AuthenticationError("Invalid token")
        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}")
            raise AuthenticationError("Token verification failed")

class PasswordManager:
    """Password hashing and verification utilities"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)

# Authentication dependency functions
async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Dependency to get current authenticated user ID from JWT token
    This is the main authentication middleware function
    """
    try:
        # Extract token from credentials
        token = credentials.credentials
        
        # Verify and decode token
        payload = TokenManager.verify_token(token)
        
        # Extract user ID
        user_id = payload.get("user_id")
        if not user_id:
            logger.warning("Authentication failed: No user_id in token payload")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.debug(f"User authenticated successfully: {user_id}")
        return user_id
        
    except AuthenticationError as e:
        logger.warning(f"Authentication failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[str]:
    """
    Optional authentication dependency - returns None if no token provided
    Useful for endpoints that work with or without authentication
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user_id(credentials)
    except HTTPException:
        return None

async def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Legacy compatibility function - same as get_current_user_id
    Maintains backward compatibility with existing code
    """
    return await get_current_user_id(credentials)

# Route protection utilities
class RouteProtection:
    """Utilities for protecting API routes"""
    
    @staticmethod
    def is_protected_route(path: str) -> bool:
        """Check if a route should be protected"""
        protected_prefixes = [
            "/api/ai",
            "/api/portfolio", 
            "/api/trading-engine",
            "/api/user",
            "/api/admin"
        ]
        
        # Exclude health and status endpoints
        excluded_paths = [
            "/api/health",
            "/api/status",
            "/api/docs",
            "/api/openapi.json",
            "/api/auth/login",
            "/api/auth/register"
        ]
        
        if path in excluded_paths:
            return False
            
        return any(path.startswith(prefix) for prefix in protected_prefixes)
    
    @staticmethod
    def get_protection_level(path: str) -> str:
        """Get the protection level for a route"""
        if path.startswith("/api/admin"):
            return "admin"
        elif path.startswith("/api/trading-engine"):
            return "trading"
        elif path.startswith("/api/ai") or path.startswith("/api/portfolio"):
            return "user"
        else:
            return "public"

# Authentication validation utilities
class AuthValidator:
    """Authentication validation and testing utilities"""
    
    @staticmethod
    async def validate_authentication_setup() -> Dict[str, Any]:
        """Validate that authentication is properly configured"""
        validation_results = {
            "secret_key_configured": bool(SECRET_KEY and SECRET_KEY != "change-me"),
            "algorithm_valid": ALGORITHM in ["HS256", "HS384", "HS512"],
            "token_expiry_configured": ACCESS_TOKEN_EXPIRE_HOURS > 0,
            "password_hashing_available": True,
            "overall_status": "unknown"
        }
        
        # Calculate overall status
        all_checks = [
            validation_results["secret_key_configured"],
            validation_results["algorithm_valid"], 
            validation_results["token_expiry_configured"],
            validation_results["password_hashing_available"]
        ]
        
        if all(all_checks):
            validation_results["overall_status"] = "valid"
        elif any(all_checks):
            validation_results["overall_status"] = "partial"
        else:
            validation_results["overall_status"] = "invalid"
        
        return validation_results
    
    @staticmethod
    def create_test_token(user_id: str = "test_user") -> str:
        """Create a test token for validation purposes"""
        return TokenManager.create_access_token(
            data={"user_id": user_id, "test": True},
            expires_delta=timedelta(minutes=30)
        )
    
    @staticmethod
    async def test_token_validation(token: str) -> Dict[str, Any]:
        """Test token validation functionality"""
        try:
            payload = TokenManager.verify_token(token)
            return {
                "valid": True,
                "payload": payload,
                "user_id": payload.get("user_id"),
                "expires": payload.get("exp")
            }
        except AuthenticationError as e:
            return {
                "valid": False,
                "error": str(e),
                "payload": None
            }

# Middleware for automatic route protection
class AuthenticationMiddleware:
    """Middleware to automatically protect routes based on path"""
    
    def __init__(self):
        self.route_protection = RouteProtection()
    
    async def __call__(self, request, call_next):
        """Process request and apply authentication if needed"""
        path = request.url.path
        
        # Check if route needs protection
        if self.route_protection.is_protected_route(path):
            # Get authorization header
            auth_header = request.headers.get("Authorization")
            
            if not auth_header or not auth_header.startswith("Bearer "):
                return HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing or invalid authorization header",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Extract and validate token
            token = auth_header.split(" ")[1]
            try:
                payload = TokenManager.verify_token(token)
                # Add user info to request state
                request.state.user_id = payload.get("user_id")
                request.state.user_payload = payload
            except AuthenticationError:
                return HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        
        # Continue with request
        response = await call_next(request)
        return response

# Export main authentication functions
__all__ = [
    "get_current_user_id",
    "get_current_user_optional", 
    "verify_jwt_token",
    "TokenManager",
    "PasswordManager",
    "RouteProtection",
    "AuthValidator",
    "AuthenticationMiddleware",
    "AuthenticationError"
]