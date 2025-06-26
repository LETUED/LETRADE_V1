"""Authentication and authorization module for REST API."""

from .dependencies import require_auth, require_permissions
from .jwt_auth import JWTAuthHandler, get_current_user

__all__ = ["JWTAuthHandler", "get_current_user", "require_auth", "require_permissions"]
