"""Authentication endpoints for REST API."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from ..auth.jwt_auth import JWTAuthHandler, UserPayload, get_current_user
from ..schemas.requests import LoginRequest, TokenRequest
from ..schemas.responses import TokenResponse, UserResponse, MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    jwt_handler: JWTAuthHandler = Depends()
) -> TokenResponse:
    """Authenticate user and return JWT token.
    
    Args:
        login_data: Login credentials
        jwt_handler: JWT authentication handler
        
    Returns:
        TokenResponse: JWT token and metadata
        
    Raises:
        HTTPException: If authentication fails
    """
    # Authenticate user
    user_data = jwt_handler.authenticate_user(login_data.username, login_data.password)
    if not user_data:
        logger.warning(f"Failed login attempt for username: {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = jwt_handler.create_access_token(user_data)
    
    logger.info(f"Successful login for user: {login_data.username}")
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=jwt_handler.access_token_expire_minutes * 60
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: TokenRequest,
    jwt_handler: JWTAuthHandler = Depends()
) -> TokenResponse:
    """Refresh JWT token.
    
    Args:
        token_data: Current token to refresh
        jwt_handler: JWT authentication handler
        
    Returns:
        TokenResponse: New JWT token
        
    Raises:
        HTTPException: If token refresh fails
    """
    # Refresh token
    new_token = jwt_handler.refresh_token(token_data.token)
    if not new_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return TokenResponse(
        access_token=new_token,
        token_type="bearer",
        expires_in=jwt_handler.access_token_expire_minutes * 60
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: UserPayload = Depends(get_current_user)
) -> UserResponse:
    """Get current user information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        UserResponse: User information
    """
    return UserResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        permissions=current_user.permissions
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: UserPayload = Depends(get_current_user)
) -> MessageResponse:
    """Logout user (client-side token invalidation).
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        MessageResponse: Logout confirmation
    """
    # In a stateless JWT system, logout is handled client-side
    # by discarding the token. In production, you might want to
    # implement a token blacklist or use shorter-lived tokens.
    
    logger.info(f"User logout: {current_user.username}")
    
    return MessageResponse(
        message="Successfully logged out",
        timestamp="2024-06-24T05:41:00Z"
    )