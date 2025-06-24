"""Standalone REST API runner for Letrade V1 trading system.

This script provides a simplified version of the REST API that can run independently
for development and testing purposes.
"""

import sys
import os
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone
from decimal import Decimal

# Add src to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from fastapi import FastAPI, HTTPException, status, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
import uvicorn
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Basic response models
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class LoginRequest(BaseModel):
    username: str
    password: str

class StrategyResponse(BaseModel):
    id: int
    name: str
    type: str
    status: str
    description: str = None
    created_at: str
    updated_at: str

class PortfolioResponse(BaseModel):
    id: int
    name: str
    status: str
    current_value: float
    available_capital: float
    total_pnl: float
    created_at: str
    updated_at: str

# Create FastAPI app
app = FastAPI(
    title="Letrade V1 Trading System API",
    description="REST API for cryptocurrency trading system management and monitoring",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Mock users
MOCK_USERS = {
    "admin": {
        "password": "admin123!",
        "permissions": ["system:read", "system:write", "strategies:read", "strategies:write", "portfolios:read", "portfolios:write"]
    },
    "trader": {
        "password": "trader123!",
        "permissions": ["strategies:read", "strategies:control", "portfolios:read"]
    }
}

# Mock data
MOCK_STRATEGIES = [
    {
        "id": 1,
        "name": "BTC MA Crossover",
        "type": "ma_crossover",
        "status": "active",
        "description": "Bitcoin moving average crossover strategy",
        "created_at": "2024-06-24T05:00:00Z",
        "updated_at": "2024-06-24T05:41:00Z"
    },
    {
        "id": 2,
        "name": "ETH RSI Strategy",
        "type": "rsi_mean_reversion",
        "status": "inactive",
        "description": "Ethereum RSI mean reversion strategy",
        "created_at": "2024-06-23T10:00:00Z",
        "updated_at": "2024-06-24T03:30:00Z"
    }
]

MOCK_PORTFOLIOS = [
    {
        "id": 1,
        "name": "Main Portfolio",
        "status": "active",
        "current_value": 10000.0,
        "available_capital": 8500.0,
        "total_pnl": 0.0,
        "created_at": "2024-06-24T00:00:00Z",
        "updated_at": "2024-06-24T05:41:00Z"
    }
]

# Root endpoints
@app.get("/")
async def root():
    """Root endpoint providing API information."""
    return {
        "name": "Letrade V1 Trading System API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "redoc": "/redoc",
        "available_endpoints": {
            "authentication": "/api/v1/auth/*",
            "strategies": "/api/v1/strategies/*", 
            "portfolios": "/api/v1/portfolios/*",
            "monitoring": "/api/v1/monitoring/*"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "api_version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "rest_api": "running",
            "mock_data": "available"
        }
    }

# Authentication endpoints
@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(login_data: LoginRequest):
    """Authenticate user and return mock JWT token."""
    user = MOCK_USERS.get(login_data.username)
    if not user or user["password"] != login_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Return mock token
    return TokenResponse(
        access_token=f"mock_token_for_{login_data.username}",
        token_type="bearer",
        expires_in=1800
    )

@app.get("/api/v1/auth/me")
async def get_current_user_info():
    """Get current user information (mock)."""
    return {
        "user_id": "admin-001",
        "username": "admin",
        "permissions": MOCK_USERS["admin"]["permissions"]
    }

# Strategy endpoints
@app.get("/api/v1/strategies/", response_model=List[StrategyResponse])
async def list_strategies(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """List all strategies."""
    strategies = MOCK_STRATEGIES[offset:offset + limit]
    return [StrategyResponse(**strategy) for strategy in strategies]

@app.get("/api/v1/strategies/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(strategy_id: int):
    """Get strategy by ID."""
    strategy = next((s for s in MOCK_STRATEGIES if s["id"] == strategy_id), None)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return StrategyResponse(**strategy)

@app.post("/api/v1/strategies/{strategy_id}/control")
async def control_strategy(strategy_id: int, action: str = "start"):
    """Control strategy (start/stop/pause/resume)."""
    strategy = next((s for s in MOCK_STRATEGIES if s["id"] == strategy_id), None)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    # Update strategy status based on action
    if action == "start":
        strategy["status"] = "active"
    elif action == "stop":
        strategy["status"] = "inactive"
    elif action == "pause":
        strategy["status"] = "paused"
    
    return {
        "message": f"Strategy {strategy_id} {action} command executed successfully",
        "strategy_id": strategy_id,
        "new_status": strategy["status"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# Portfolio endpoints
@app.get("/api/v1/portfolios/", response_model=List[PortfolioResponse])
async def list_portfolios(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """List all portfolios."""
    portfolios = MOCK_PORTFOLIOS[offset:offset + limit]
    return [PortfolioResponse(**portfolio) for portfolio in portfolios]

@app.get("/api/v1/portfolios/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio(portfolio_id: int):
    """Get portfolio by ID."""
    portfolio = next((p for p in MOCK_PORTFOLIOS if p["id"] == portfolio_id), None)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return PortfolioResponse(**portfolio)

@app.get("/api/v1/portfolios/{portfolio_id}/balances")
async def get_portfolio_balances(portfolio_id: int):
    """Get portfolio asset balances."""
    return [
        {
            "asset": "USDT",
            "free": 8500.0,
            "locked": 1500.0,
            "total": 10000.0,
            "usd_value": 10000.0
        },
        {
            "asset": "BTC",
            "free": 0.0,
            "locked": 0.0,
            "total": 0.0,
            "usd_value": 0.0
        }
    ]

# Monitoring endpoints
@app.get("/api/v1/monitoring/status")
async def get_system_status():
    """Get system status."""
    return {
        "overall_status": "healthy",
        "uptime": 86400,
        "version": "1.0.0",
        "components": [
            {"name": "REST API", "status": "online"},
            {"name": "Mock Data", "status": "online"}
        ],
        "active_strategies": len([s for s in MOCK_STRATEGIES if s["status"] == "active"]),
        "total_portfolios": len(MOCK_PORTFOLIOS),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/v1/monitoring/metrics")
async def get_system_metrics():
    """Get system metrics."""
    return {
        "period": "hour",
        "avg_response_time": 45.2,
        "throughput": 150.5,
        "error_rate": 0.1,
        "total_trades": 0,
        "successful_trades": 0,
        "collected_at": datetime.now(timezone.utc).isoformat()
    }

# Demo/testing endpoints
@app.get("/api/v1/demo/mock-data")
async def get_mock_data():
    """Get all mock data for testing."""
    return {
        "strategies": MOCK_STRATEGIES,
        "portfolios": MOCK_PORTFOLIOS,
        "users": list(MOCK_USERS.keys())
    }

@app.post("/api/v1/demo/reset-data")
async def reset_mock_data():
    """Reset mock data to initial state."""
    global MOCK_STRATEGIES
    MOCK_STRATEGIES[0]["status"] = "inactive"
    MOCK_STRATEGIES[1]["status"] = "inactive"
    
    return {
        "message": "Mock data reset to initial state",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

if __name__ == "__main__":
    print("🚀 Starting Letrade V1 REST API (Standalone Mode)")
    print("=" * 60)
    print("📖 API Documentation: http://localhost:8000/docs")
    print("📋 ReDoc Documentation: http://localhost:8000/redoc")
    print("🔗 API Root: http://localhost:8000/")
    print("❤️  Health Check: http://localhost:8000/health")
    print("")
    print("🧪 Demo Endpoints:")
    print("   Mock Data: http://localhost:8000/api/v1/demo/mock-data")
    print("   Reset Data: POST http://localhost:8000/api/v1/demo/reset-data")
    print("")
    print("🔐 Test Credentials:")
    print("   Admin: username=admin, password=admin123!")
    print("   Trader: username=trader, password=trader123!")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False
    )