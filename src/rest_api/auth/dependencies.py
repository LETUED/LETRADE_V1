"""Authentication dependencies for FastAPI endpoints."""

from typing import Callable, List

from fastapi import Depends, HTTPException, status

from .jwt_auth import JWTAuthHandler, UserPayload, get_current_user


def require_auth(current_user: UserPayload = Depends(get_current_user)) -> UserPayload:
    """Require authentication for endpoint.

    Args:
        current_user: Current authenticated user

    Returns:
        UserPayload: Authenticated user payload
    """
    return current_user


def require_permissions(required_permissions: List[str]) -> Callable:
    """Create dependency that requires specific permissions.

    Args:
        required_permissions: List of required permissions

    Returns:
        Callable: Dependency function
    """

    def permission_checker(
        current_user: UserPayload = Depends(get_current_user),
    ) -> UserPayload:
        """Check if user has required permissions.

        Args:
            current_user: Current authenticated user

        Returns:
            UserPayload: User payload if authorized

        Raises:
            HTTPException: If user lacks required permissions
        """
        for permission in required_permissions:
            if permission not in current_user.permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permission: {permission}",
                )

        return current_user

    return permission_checker


# Common permission requirements
require_system_read = require_permissions(["system:read"])
require_system_write = require_permissions(["system:write"])
require_strategies_read = require_permissions(["strategies:read"])
require_strategies_write = require_permissions(["strategies:write"])
require_strategies_control = require_permissions(["strategies:control"])
require_portfolios_read = require_permissions(["portfolios:read"])
require_portfolios_write = require_permissions(["portfolios:write"])
require_monitoring_read = require_permissions(["monitoring:read"])

# Admin-only permissions
require_admin = require_permissions(
    [
        "system:read",
        "system:write",
        "strategies:read",
        "strategies:write",
        "strategies:control",
        "portfolios:read",
        "portfolios:write",
        "monitoring:read",
    ]
)
