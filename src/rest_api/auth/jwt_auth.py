"""JWT authentication handler for REST API."""

import jwt
import bcrypt
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class UserPayload(BaseModel):
    """User payload for JWT token."""
    user_id: str
    username: str
    permissions: List[str]
    exp: int


class JWTAuthHandler:
    """JWT authentication handler.
    
    Provides secure authentication using JWT tokens with user permissions.
    Implements secure password hashing and token validation.
    """
    
    def __init__(self, secret_key: str, algorithm: str = "HS256", access_token_expire_minutes: int = 30):
        """Initialize JWT auth handler.
        
        Args:
            secret_key: Secret key for JWT signing
            algorithm: JWT algorithm to use
            access_token_expire_minutes: Token expiration time in minutes
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        
        # Hardcoded users for MVP (replace with database in production)
        self.users = {
            "admin": {
                "user_id": "admin-001",
                "username": "admin",
                "hashed_password": self._hash_password("admin123!"),  # Change in production
                "permissions": [
                    "system:read",
                    "system:write", 
                    "strategies:read",
                    "strategies:write",
                    "strategies:control",
                    "portfolios:read",
                    "portfolios:write",
                    "monitoring:read"
                ]
            },
            "trader": {
                "user_id": "trader-001", 
                "username": "trader",
                "hashed_password": self._hash_password("trader123!"),  # Change in production
                "permissions": [
                    "strategies:read",
                    "strategies:control",
                    "portfolios:read",
                    "monitoring:read"
                ]
            },
            "viewer": {
                "user_id": "viewer-001",
                "username": "viewer", 
                "hashed_password": self._hash_password("viewer123!"),  # Change in production
                "permissions": [
                    "strategies:read",
                    "portfolios:read",
                    "monitoring:read"
                ]
            }
        }
        
        logger.info(f"JWT auth handler initialized with {len(self.users)} users")
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            str: Hashed password
        """
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash.
        
        Args:
            password: Plain text password
            hashed_password: Hashed password
            
        Returns:
            bool: True if password matches
        """
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with username and password.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            dict: User data if authenticated, None otherwise
        """
        user = self.users.get(username)
        if not user:
            return None
            
        if not self._verify_password(password, user["hashed_password"]):
            return None
            
        return user
    
    def create_access_token(self, user_data: Dict[str, Any]) -> str:
        """Create JWT access token.
        
        Args:
            user_data: User data dictionary
            
        Returns:
            str: JWT token
        """
        expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "user_id": user_data["user_id"],
            "username": user_data["username"],
            "permissions": user_data["permissions"],
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access"
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        logger.info(f"Created access token for user {user_data['username']}")
        
        return token
    
    def verify_token(self, token: str) -> Optional[UserPayload]:
        """Verify and decode JWT token.
        
        Args:
            token: JWT token
            
        Returns:
            UserPayload: User payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Validate token type
            if payload.get("type") != "access":
                return None
            
            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, timezone.utc) < datetime.now(timezone.utc):
                return None
            
            return UserPayload(
                user_id=payload["user_id"],
                username=payload["username"],
                permissions=payload["permissions"],
                exp=exp
            )
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None
    
    def has_permission(self, user: UserPayload, required_permission: str) -> bool:
        """Check if user has required permission.
        
        Args:
            user: User payload
            required_permission: Required permission string
            
        Returns:
            bool: True if user has permission
        """
        return required_permission in user.permissions
    
    def refresh_token(self, token: str) -> Optional[str]:
        """Refresh access token.
        
        Args:
            token: Current JWT token
            
        Returns:
            str: New JWT token if valid, None otherwise
        """
        user_payload = self.verify_token(token)
        if not user_payload:
            return None
        
        # Get fresh user data
        user_data = self.users.get(user_payload.username)
        if not user_data:
            return None
            
        return self.create_access_token(user_data)


# Security scheme
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserPayload:
    """Get current authenticated user.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        UserPayload: Current user payload
        
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create temporary JWT handler instance
    from ..main import get_jwt_handler
    jwt_handler = get_jwt_handler()
    
    user = jwt_handler.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user