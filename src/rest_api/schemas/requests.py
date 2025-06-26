"""Request schemas for REST API."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, validator


class LoginRequest(BaseModel):
    """Login request schema."""

    username: str = Field(min_length=3, max_length=50, description="Username")
    password: str = Field(min_length=8, max_length=100, description="Password")

    @validator("username")
    def validate_username(cls, v):
        if not v.isalnum() and "_" not in v:
            raise ValueError(
                "Username must contain only alphanumeric characters and underscores"
            )
        return v.lower()


class TokenRequest(BaseModel):
    """Token refresh request schema."""

    token: str = Field(description="JWT token to refresh")


class PaginationRequest(BaseModel):
    """Pagination request parameters."""

    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")


class FilterRequest(BaseModel):
    """Base filter request parameters."""

    search: Optional[str] = Field(
        default=None, max_length=100, description="Search query"
    )
    sort_by: Optional[str] = Field(default=None, description="Sort field")
    sort_order: Optional[str] = Field(
        default="asc", pattern="^(asc|desc)$", description="Sort order"
    )

    @validator("search")
    def validate_search(cls, v):
        if v and len(v.strip()) < 2:
            raise ValueError("Search query must be at least 2 characters")
        return v.strip() if v else None


class SystemCommandRequest(BaseModel):
    """System command request schema."""

    command: str = Field(description="Command to execute")
    parameters: Optional[Dict[str, Any]] = Field(
        default=None, description="Command parameters"
    )
    confirm: bool = Field(
        default=False, description="Confirmation flag for destructive operations"
    )

    @validator("command")
    def validate_command(cls, v):
        allowed_commands = [
            "start_system",
            "stop_system",
            "restart_system",
            "start_strategy",
            "stop_strategy",
            "pause_strategy",
            "resume_strategy",
            "reconcile_state",
            "flush_cache",
            "backup_data",
        ]
        if v not in allowed_commands:
            raise ValueError(f'Command must be one of: {", ".join(allowed_commands)}')
        return v
