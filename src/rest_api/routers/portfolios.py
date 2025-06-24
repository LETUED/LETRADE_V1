"""Portfolio management endpoints for REST API.

Implements FR 6.2.2 (Portfolio Management API) from MVP specification.
Provides portfolio monitoring, configuration, and risk management functionality.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from ..auth.dependencies import require_portfolios_read, require_portfolios_write
from ..auth.jwt_auth import UserPayload
from ..services.api_service import APIService
from ..schemas.portfolios import (
    PortfolioResponse,
    PortfolioCreateRequest,
    PortfolioUpdateRequest,
    PortfolioListResponse,
    PortfolioMetricsResponse,
    AssetAllocationResponse,
    BalanceResponse,
    PositionResponse
)
from ..schemas.responses import MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=PortfolioListResponse)
async def list_portfolios(
    active_only: bool = Query(False, description="Return only active portfolios"),
    limit: int = Query(20, ge=1, le=100, description="Number of portfolios to return"),
    offset: int = Query(0, ge=0, description="Number of portfolios to skip"),
    current_user: UserPayload = Depends(require_portfolios_read),
    api_service: APIService = Depends()
) -> PortfolioListResponse:
    """List all portfolios with optional filtering.
    
    Args:
        active_only: Filter for active portfolios only
        limit: Maximum number of portfolios to return
        offset: Number of portfolios to skip
        current_user: Current authenticated user
        api_service: API service instance
        
    Returns:
        PortfolioListResponse: List of portfolios with metadata
        
    Raises:
        HTTPException: If request fails
    """
    try:
        filters = {
            'active_only': active_only,
            'limit': limit,
            'offset': offset
        }
        
        response = await api_service.list_portfolios(current_user.user_id, filters)
        
        if not response.get('success', True):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=response.get('error', 'Failed to list portfolios')
            )
        
        # Transform response data to match schema
        portfolios_data = response.get('data', {})
        portfolios = portfolios_data.get('portfolios', [])
        
        return PortfolioListResponse(
            portfolios=[PortfolioResponse(**portfolio) for portfolio in portfolios],
            total=portfolios_data.get('total', 0),
            active=portfolios_data.get('active', 0),
            total_value=portfolios_data.get('total_value', 0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing portfolios: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio(
    portfolio_id: int,
    current_user: UserPayload = Depends(require_portfolios_read),
    api_service: APIService = Depends()
) -> PortfolioResponse:
    """Get portfolio by ID.
    
    Args:
        portfolio_id: Portfolio ID
        current_user: Current authenticated user
        api_service: API service instance
        
    Returns:
        PortfolioResponse: Portfolio details
        
    Raises:
        HTTPException: If portfolio not found or request fails
    """
    try:
        response = await api_service.get_portfolio(current_user.user_id, portfolio_id)
        
        if not response.get('success', True):
            error = response.get('error', 'Portfolio not found')
            if 'not found' in error.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Portfolio {portfolio_id} not found"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )
        
        portfolio_data = response.get('data', {})
        return PortfolioResponse(**portfolio_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting portfolio {portfolio_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    portfolio_data: PortfolioCreateRequest,
    current_user: UserPayload = Depends(require_portfolios_write),
    api_service: APIService = Depends()
) -> PortfolioResponse:
    """Create new portfolio.
    
    Args:
        portfolio_data: Portfolio configuration
        current_user: Current authenticated user
        api_service: API service instance
        
    Returns:
        PortfolioResponse: Created portfolio details
        
    Raises:
        HTTPException: If creation fails
    """
    try:
        # For MVP, we'll simulate portfolio creation
        # In full implementation, this would call Core Engine
        
        # Mock response for demonstration
        mock_portfolio = {
            "id": 1,
            "name": portfolio_data.name,
            "status": "active",
            "description": portfolio_data.description,
            "initial_capital": portfolio_data.initial_capital,
            "current_value": portfolio_data.initial_capital,
            "available_capital": portfolio_data.initial_capital,
            "allocated_capital": 0,
            "total_pnl": 0,
            "total_pnl_pct": 0.0,
            "daily_pnl": 0,
            "daily_pnl_pct": 0.0,
            "balances": [],
            "positions": [],
            "config": portfolio_data.config or {},
            "risk_limits": portfolio_data.risk_limits or {},
            "created_at": "2024-06-24T05:41:00Z",
            "updated_at": "2024-06-24T05:41:00Z"
        }
        
        logger.info(f"Created portfolio {mock_portfolio['id']} for user {current_user.username}")
        
        return PortfolioResponse(**mock_portfolio)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating portfolio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put("/{portfolio_id}", response_model=PortfolioResponse)
async def update_portfolio(
    portfolio_id: int,
    update_data: PortfolioUpdateRequest,
    current_user: UserPayload = Depends(require_portfolios_write),
    api_service: APIService = Depends()
) -> PortfolioResponse:
    """Update portfolio.
    
    Args:
        portfolio_id: Portfolio ID
        update_data: Update data
        current_user: Current authenticated user
        api_service: API service instance
        
    Returns:
        PortfolioResponse: Updated portfolio details
        
    Raises:
        HTTPException: If portfolio not found or update fails
    """
    try:
        response = await api_service.update_portfolio(
            current_user.user_id,
            portfolio_id,
            update_data.model_dump(exclude_unset=True)
        )
        
        if not response.get('success', True):
            error = response.get('error', 'Failed to update portfolio')
            if 'not found' in error.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Portfolio {portfolio_id} not found"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )
        
        portfolio_result = response.get('data', {})
        logger.info(f"Updated portfolio {portfolio_id} for user {current_user.username}")
        
        return PortfolioResponse(**portfolio_result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating portfolio {portfolio_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/{portfolio_id}/balances", response_model=List[BalanceResponse])
async def get_portfolio_balances(
    portfolio_id: int,
    current_user: UserPayload = Depends(require_portfolios_read),
    api_service: APIService = Depends()
) -> List[BalanceResponse]:
    """Get portfolio asset balances.
    
    Args:
        portfolio_id: Portfolio ID
        current_user: Current authenticated user
        api_service: API service instance
        
    Returns:
        List[BalanceResponse]: List of asset balances
        
    Raises:
        HTTPException: If portfolio not found or request fails
    """
    try:
        # For MVP, return mock balances
        mock_balances = [
            {
                "asset": "USDT",
                "asset_type": "stablecoin",
                "free": 10000.0,
                "locked": 0.0,
                "total": 10000.0,
                "usd_value": 10000.0,
                "last_updated": "2024-06-24T05:41:00Z"
            },
            {
                "asset": "BTC",
                "asset_type": "cryptocurrency",
                "free": 0.0,
                "locked": 0.0,
                "total": 0.0,
                "usd_value": 0.0,
                "last_updated": "2024-06-24T05:41:00Z"
            }
        ]
        
        return [BalanceResponse(**balance) for balance in mock_balances]
        
    except Exception as e:
        logger.error(f"Error getting portfolio {portfolio_id} balances: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/{portfolio_id}/positions", response_model=List[PositionResponse])
async def get_portfolio_positions(
    portfolio_id: int,
    active_only: bool = Query(True, description="Return only active positions"),
    current_user: UserPayload = Depends(require_portfolios_read),
    api_service: APIService = Depends()
) -> List[PositionResponse]:
    """Get portfolio positions.
    
    Args:
        portfolio_id: Portfolio ID
        active_only: Filter for active positions only
        current_user: Current authenticated user
        api_service: API service instance
        
    Returns:
        List[PositionResponse]: List of positions
        
    Raises:
        HTTPException: If portfolio not found or request fails
    """
    try:
        # For MVP, return empty positions list
        return []
        
    except Exception as e:
        logger.error(f"Error getting portfolio {portfolio_id} positions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/{portfolio_id}/metrics", response_model=PortfolioMetricsResponse)
async def get_portfolio_metrics(
    portfolio_id: int,
    period: str = Query("daily", pattern="^(daily|weekly|monthly)$", description="Metrics period"),
    current_user: UserPayload = Depends(require_portfolios_read),
    api_service: APIService = Depends()
) -> PortfolioMetricsResponse:
    """Get portfolio performance metrics.
    
    Args:
        portfolio_id: Portfolio ID
        period: Metrics period
        current_user: Current authenticated user
        api_service: API service instance
        
    Returns:
        PortfolioMetricsResponse: Portfolio metrics
        
    Raises:
        HTTPException: If portfolio not found or request fails
    """
    try:
        # For MVP, return mock metrics
        mock_metrics = {
            "portfolio_id": portfolio_id,
            "period": period,
            "total_return": 0.0,
            "total_return_pct": 0.0,
            "total_trades": 0,
            "winning_days": 0,
            "losing_days": 0,
            "start_date": "2024-06-24",
            "end_date": "2024-06-24",
            "calculated_at": "2024-06-24T05:41:00Z"
        }
        
        return PortfolioMetricsResponse(**mock_metrics)
        
    except Exception as e:
        logger.error(f"Error getting portfolio {portfolio_id} metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/{portfolio_id}/allocation", response_model=AssetAllocationResponse)
async def get_portfolio_allocation(
    portfolio_id: int,
    current_user: UserPayload = Depends(require_portfolios_read),
    api_service: APIService = Depends()
) -> AssetAllocationResponse:
    """Get portfolio asset allocation.
    
    Args:
        portfolio_id: Portfolio ID
        current_user: Current authenticated user
        api_service: API service instance
        
    Returns:
        AssetAllocationResponse: Asset allocation breakdown
        
    Raises:
        HTTPException: If portfolio not found or request fails
    """
    try:
        # For MVP, return mock allocation
        mock_allocation = {
            "portfolio_id": portfolio_id,
            "allocations": [
                {
                    "asset": "USDT",
                    "percentage": 100.0,
                    "value": 10000.0,
                    "target_percentage": 100.0
                }
            ],
            "total_allocated_pct": 100.0,
            "cash_pct": 100.0,
            "updated_at": "2024-06-24T05:41:00Z"
        }
        
        return AssetAllocationResponse(**mock_allocation)
        
    except Exception as e:
        logger.error(f"Error getting portfolio {portfolio_id} allocation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )