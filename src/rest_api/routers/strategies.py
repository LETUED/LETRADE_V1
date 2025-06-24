"""Strategy management endpoints for REST API.

Implements FR 6.2.1 (Strategy Management API) from MVP specification.
Provides CRUD operations and control functionality for trading strategies.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from ..auth.dependencies import require_strategies_read, require_strategies_write, require_strategies_control
from ..auth.jwt_auth import UserPayload
from ..services.api_service import APIService
from ..schemas.strategies import (
    StrategyResponse,
    StrategyCreateRequest,
    StrategyUpdateRequest,
    StrategyControlRequest,
    StrategyListResponse,
    StrategyPerformanceResponse,
    StrategyStatus
)
from ..schemas.responses import MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=StrategyListResponse)
async def list_strategies(
    status_filter: Optional[StrategyStatus] = Query(None, description="Filter by strategy status"),
    limit: int = Query(20, ge=1, le=100, description="Number of strategies to return"),
    offset: int = Query(0, ge=0, description="Number of strategies to skip"),
    current_user: UserPayload = Depends(require_strategies_read),
    api_service: APIService = Depends()
) -> StrategyListResponse:
    """List all strategies with optional filtering.
    
    Args:
        status_filter: Optional status filter
        limit: Maximum number of strategies to return
        offset: Number of strategies to skip
        current_user: Current authenticated user
        api_service: API service instance
        
    Returns:
        StrategyListResponse: List of strategies with metadata
        
    Raises:
        HTTPException: If request fails
    """
    try:
        filters = {
            'status': status_filter.value if status_filter else None,
            'limit': limit,
            'offset': offset
        }
        
        response = await api_service.list_strategies(current_user.user_id, filters)
        
        if not response.get('success', True):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=response.get('error', 'Failed to list strategies')
            )
        
        # Transform response data to match schema
        strategies_data = response.get('data', {})
        strategies = strategies_data.get('strategies', [])
        
        return StrategyListResponse(
            strategies=[StrategyResponse(**strategy) for strategy in strategies],
            total=strategies_data.get('total', 0),
            active=strategies_data.get('active', 0),
            inactive=strategies_data.get('inactive', 0),
            error=strategies_data.get('error', 0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing strategies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: int,
    current_user: UserPayload = Depends(require_strategies_read),
    api_service: APIService = Depends()
) -> StrategyResponse:
    """Get strategy by ID.
    
    Args:
        strategy_id: Strategy ID
        current_user: Current authenticated user
        api_service: API service instance
        
    Returns:
        StrategyResponse: Strategy details
        
    Raises:
        HTTPException: If strategy not found or request fails
    """
    try:
        response = await api_service.get_strategy(current_user.user_id, strategy_id)
        
        if not response.get('success', True):
            error = response.get('error', 'Strategy not found')
            if 'not found' in error.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Strategy {strategy_id} not found"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )
        
        strategy_data = response.get('data', {})
        return StrategyResponse(**strategy_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting strategy {strategy_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    strategy_data: StrategyCreateRequest,
    current_user: UserPayload = Depends(require_strategies_write),
    api_service: APIService = Depends()
) -> StrategyResponse:
    """Create new strategy.
    
    Args:
        strategy_data: Strategy configuration
        current_user: Current authenticated user
        api_service: API service instance
        
    Returns:
        StrategyResponse: Created strategy details
        
    Raises:
        HTTPException: If creation fails
    """
    try:
        response = await api_service.create_strategy(
            current_user.user_id, 
            strategy_data.model_dump()
        )
        
        if not response.get('success', True):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=response.get('error', 'Failed to create strategy')
            )
        
        strategy_result = response.get('data', {})
        logger.info(f"Created strategy {strategy_result.get('id')} for user {current_user.username}")
        
        return StrategyResponse(**strategy_result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating strategy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: int,
    update_data: StrategyUpdateRequest,
    current_user: UserPayload = Depends(require_strategies_write),
    api_service: APIService = Depends()
) -> StrategyResponse:
    """Update strategy.
    
    Args:
        strategy_id: Strategy ID
        update_data: Update data
        current_user: Current authenticated user
        api_service: API service instance
        
    Returns:
        StrategyResponse: Updated strategy details
        
    Raises:
        HTTPException: If strategy not found or update fails
    """
    try:
        response = await api_service.update_strategy(
            current_user.user_id,
            strategy_id,
            update_data.model_dump(exclude_unset=True)
        )
        
        if not response.get('success', True):
            error = response.get('error', 'Failed to update strategy')
            if 'not found' in error.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Strategy {strategy_id} not found"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )
        
        strategy_result = response.get('data', {})
        logger.info(f"Updated strategy {strategy_id} for user {current_user.username}")
        
        return StrategyResponse(**strategy_result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating strategy {strategy_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete("/{strategy_id}", response_model=MessageResponse)
async def delete_strategy(
    strategy_id: int,
    current_user: UserPayload = Depends(require_strategies_write),
    api_service: APIService = Depends()
) -> MessageResponse:
    """Delete strategy.
    
    Args:
        strategy_id: Strategy ID
        current_user: Current authenticated user
        api_service: API service instance
        
    Returns:
        MessageResponse: Deletion confirmation
        
    Raises:
        HTTPException: If strategy not found or deletion fails
    """
    try:
        response = await api_service.delete_strategy(current_user.user_id, strategy_id)
        
        if not response.get('success', True):
            error = response.get('error', 'Failed to delete strategy')
            if 'not found' in error.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Strategy {strategy_id} not found"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )
        
        logger.info(f"Deleted strategy {strategy_id} for user {current_user.username}")
        
        return MessageResponse(
            message=f"Strategy {strategy_id} deleted successfully",
            timestamp="2024-06-24T05:41:00Z"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting strategy {strategy_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/{strategy_id}/control", response_model=MessageResponse)
async def control_strategy(
    strategy_id: int,
    control_data: StrategyControlRequest,
    current_user: UserPayload = Depends(require_strategies_control),
    api_service: APIService = Depends()
) -> MessageResponse:
    """Control strategy (start/stop/pause/resume).
    
    Args:
        strategy_id: Strategy ID
        control_data: Control action and parameters
        current_user: Current authenticated user
        api_service: API service instance
        
    Returns:
        MessageResponse: Control result
        
    Raises:
        HTTPException: If strategy not found or control fails
    """
    try:
        response = await api_service.control_strategy(
            current_user.user_id,
            strategy_id,
            control_data.action,
            control_data.parameters
        )
        
        if not response.get('success', True):
            error = response.get('error', 'Failed to control strategy')
            if 'not found' in error.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Strategy {strategy_id} not found"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )
        
        logger.info(f"Strategy {strategy_id} {control_data.action} by user {current_user.username}")
        
        return MessageResponse(
            message=f"Strategy {strategy_id} {control_data.action} command executed successfully",
            timestamp="2024-06-24T05:41:00Z",
            data=response.get('data')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error controlling strategy {strategy_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/{strategy_id}/performance", response_model=StrategyPerformanceResponse)
async def get_strategy_performance(
    strategy_id: int,
    period: str = Query("daily", pattern="^(daily|weekly|monthly)$", description="Performance period"),
    current_user: UserPayload = Depends(require_strategies_read),
    api_service: APIService = Depends()
) -> StrategyPerformanceResponse:
    """Get strategy performance metrics.
    
    Args:
        strategy_id: Strategy ID
        period: Performance period
        current_user: Current authenticated user
        api_service: API service instance
        
    Returns:
        StrategyPerformanceResponse: Performance metrics
        
    Raises:
        HTTPException: If strategy not found or request fails
    """
    try:
        # This would be implemented when performance calculation is available
        # For now, return mock data structure
        
        return StrategyPerformanceResponse(
            strategy_id=strategy_id,
            period=period,
            total_return=0,
            total_return_pct=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            start_date="2024-06-24",
            end_date="2024-06-24",
            calculated_at="2024-06-24T05:41:00Z"
        )
        
    except Exception as e:
        logger.error(f"Error getting strategy {strategy_id} performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )