"""Response schemas for REST API."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """Base response schema with common fields."""

    success: bool = Field(
        default=True, description="Whether the request was successful"
    )
    timestamp: str = Field(description="Response timestamp in ISO format")

    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    """Error response schema."""

    error: str = Field(description="Error message")
    status_code: int = Field(description="HTTP status code")
    timestamp: str = Field(description="Error timestamp in ISO format")
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional error details"
    )


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(
        description="Overall health status: healthy, degraded, unhealthy"
    )
    api_service_running: bool = Field(description="Whether API service is running")
    message_bus_connected: bool = Field(description="Whether message bus is connected")
    jwt_handler_available: bool = Field(description="Whether JWT handler is available")
    timestamp: str = Field(description="Health check timestamp")
    error: Optional[str] = Field(default=None, description="Error message if unhealthy")


class TokenResponse(BaseModel):
    """JWT token response schema."""

    access_token: str = Field(description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Token expiration time in seconds")


class UserResponse(BaseModel):
    """User information response schema."""

    user_id: str = Field(description="User identifier")
    username: str = Field(description="Username")
    permissions: List[str] = Field(description="User permissions")
    last_login: Optional[str] = Field(default=None, description="Last login timestamp")


class PaginationMeta(BaseModel):
    """Pagination metadata schema."""

    page: int = Field(ge=1, description="Current page number")
    per_page: int = Field(ge=1, le=100, description="Items per page")
    total: int = Field(ge=0, description="Total number of items")
    pages: int = Field(ge=0, description="Total number of pages")
    has_next: bool = Field(description="Whether there is a next page")
    has_prev: bool = Field(description="Whether there is a previous page")


class PaginatedResponse(BaseResponse):
    """Paginated response schema."""

    data: List[Any] = Field(description="Response data items")
    meta: PaginationMeta = Field(description="Pagination metadata")


class MessageResponse(BaseResponse):
    """Simple message response schema."""

    message: str = Field(description="Response message")
    data: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional response data"
    )
