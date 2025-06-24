"""Main FastAPI application for Letrade_v1 REST API.

Implements FR 6.2.1 (Strategy Management API) and FR 6.2.2 (Portfolio Management API)
from MVP specification. Provides secure REST endpoints for system management.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse

from common.message_bus import MessageBus
from .auth.jwt_auth import JWTAuthHandler
from .services.api_service import APIService
from .routers import auth, strategies, portfolios, monitoring, system
from .schemas.responses import ErrorResponse, HealthResponse

logger = logging.getLogger(__name__)


# Global instances
message_bus: MessageBus = None
api_service: APIService = None
jwt_handler: JWTAuthHandler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management - startup and shutdown."""
    # Startup
    global message_bus, api_service, jwt_handler
    
    try:
        logger.info("Starting REST API application...")
        
        # Initialize JWT handler
        jwt_handler = JWTAuthHandler(
            secret_key=os.getenv("JWT_SECRET_KEY", "letrade-default-secret-change-in-production"),
            algorithm="HS256",
            access_token_expire_minutes=30
        )
        
        # Initialize message bus
        message_bus = MessageBus()
        await message_bus.connect()
        
        # Initialize API service
        api_service = APIService(message_bus, jwt_handler)
        await api_service.start()
        
        logger.info("REST API application started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start REST API application: {e}")
        raise
    
    # Shutdown
    try:
        logger.info("Shutting down REST API application...")
        
        if api_service:
            await api_service.stop()
        
        if message_bus:
            await message_bus.disconnect()
            
        logger.info("REST API application shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during REST API shutdown: {e}")


def create_app() -> FastAPI:
    """Create and configure FastAPI application.
    
    Returns:
        FastAPI: Configured application instance
    """
    app = FastAPI(
        title="Letrade V1 Trading System API",
        description="REST API for cryptocurrency trading system management and monitoring",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )
    
    # Security middleware
    security = HTTPBearer()
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080").split(","),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )
    
    # Trusted host middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    )
    
    # Include routers
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
    app.include_router(strategies.router, prefix="/api/v1/strategies", tags=["strategies"])
    app.include_router(portfolios.router, prefix="/api/v1/portfolios", tags=["portfolios"])
    app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["monitoring"])
    app.include_router(system.router, prefix="/api/v1/system", tags=["system"])
    
    return app


# Create app instance
app = create_app()


@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint providing API information."""
    return {
        "name": "Letrade V1 Trading System API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for monitoring and load balancers.
    
    Returns:
        HealthResponse: Current system health status
    """
    try:
        health_status = {
            "status": "healthy",
            "api_service_running": api_service.is_running if api_service else False,
            "message_bus_connected": message_bus.is_connected if message_bus else False,
            "jwt_handler_available": jwt_handler is not None,
            "timestamp": "2024-06-24T05:41:00Z"  # Will be dynamic
        }
        
        # Determine overall health
        if not all([
            health_status["api_service_running"],
            health_status["message_bus_connected"],
            health_status["jwt_handler_available"]
        ]):
            health_status["status"] = "degraded"
            
        return HealthResponse(**health_status)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            api_service_running=False,
            message_bus_connected=False,
            jwt_handler_available=False,
            timestamp="2024-06-24T05:41:00Z",
            error=str(e)
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Global HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            status_code=exc.status_code,
            timestamp="2024-06-24T05:41:00Z"
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Global exception handler for unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            status_code=500,
            timestamp="2024-06-24T05:41:00Z"
        ).model_dump()
    )


# Dependency providers
def get_api_service() -> APIService:
    """Dependency provider for API service."""
    if not api_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API service not available"
        )
    return api_service


def get_jwt_handler() -> JWTAuthHandler:
    """Dependency provider for JWT handler."""
    global jwt_handler
    if not jwt_handler:
        # Initialize with default values if not available
        jwt_handler = JWTAuthHandler(
            secret_key=os.getenv("JWT_SECRET_KEY", "letrade-default-secret-change-in-production"),
            algorithm="HS256",
            access_token_expire_minutes=30
        )
    return jwt_handler


def get_message_bus() -> MessageBus:
    """Dependency provider for message bus."""
    if not message_bus:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Message bus not available"
        )
    return message_bus


if __name__ == "__main__":
    import uvicorn
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run application
    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("API_RELOAD", "false").lower() == "true",
        log_level=os.getenv("API_LOG_LEVEL", "info")
    )