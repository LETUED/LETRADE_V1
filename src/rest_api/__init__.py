"""REST API module for Letrade_v1 trading system.

This module provides FastAPI-based REST endpoints for system management,
strategy control, and portfolio monitoring. Implements MVP requirements
FR 6.2.1 (Strategy Management API) and FR 6.2.2 (Portfolio Management API).

Key Features:
- JWT-based authentication and authorization
- Strategy CRUD operations and control
- Portfolio monitoring and configuration
- Real-time system status and metrics
- Integration with Core Engine via message bus
"""

from .auth.jwt_auth import JWTAuthHandler
from .main import app, create_app
from .services.api_service import APIService

__version__ = "0.1.0"
__author__ = "Letrade Team"

__all__ = ["app", "create_app", "JWTAuthHandler", "APIService"]
