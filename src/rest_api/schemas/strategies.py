"""Strategy-related schemas for REST API."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from decimal import Decimal
from pydantic import BaseModel, Field, validator
from enum import Enum


class StrategyStatus(str, Enum):
    """Strategy status enumeration."""
    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    STARTING = "starting"
    STOPPING = "stopping"


class StrategyType(str, Enum):
    """Strategy type enumeration."""
    MA_CROSSOVER = "ma_crossover"
    RSI_MEAN_REVERSION = "rsi_mean_reversion"
    BOLLINGER_BANDS = "bollinger_bands"
    CUSTOM = "custom"


class StrategyResponse(BaseModel):
    """Strategy response schema."""
    id: int = Field(description="Strategy ID")
    name: str = Field(description="Strategy name")
    type: StrategyType = Field(description="Strategy type")
    status: StrategyStatus = Field(description="Current strategy status")
    description: Optional[str] = Field(default=None, description="Strategy description")
    
    # Configuration
    config: Dict[str, Any] = Field(description="Strategy configuration parameters")
    risk_config: Dict[str, Any] = Field(description="Risk management configuration")
    
    # Portfolio allocation
    portfolio_id: int = Field(description="Associated portfolio ID")
    allocated_capital: Decimal = Field(description="Allocated capital amount")
    max_position_size: Decimal = Field(description="Maximum position size")
    
    # Performance metrics
    total_trades: int = Field(default=0, description="Total number of trades")
    winning_trades: int = Field(default=0, description="Number of winning trades")
    total_pnl: Decimal = Field(default=Decimal("0"), description="Total profit/loss")
    win_rate: float = Field(default=0.0, description="Win rate percentage")
    sharpe_ratio: Optional[float] = Field(default=None, description="Sharpe ratio")
    max_drawdown: Optional[float] = Field(default=None, description="Maximum drawdown")
    
    # Timestamps
    created_at: str = Field(description="Creation timestamp")
    updated_at: str = Field(description="Last update timestamp")
    started_at: Optional[str] = Field(default=None, description="Last start timestamp")
    
    class Config:
        from_attributes = True


class StrategyCreateRequest(BaseModel):
    """Strategy creation request schema."""
    name: str = Field(min_length=3, max_length=100, description="Strategy name")
    type: StrategyType = Field(description="Strategy type")
    description: Optional[str] = Field(default=None, max_length=500, description="Strategy description")
    
    # Configuration
    config: Dict[str, Any] = Field(description="Strategy configuration parameters")
    risk_config: Optional[Dict[str, Any]] = Field(default=None, description="Risk management configuration")
    
    # Portfolio allocation
    portfolio_id: int = Field(description="Portfolio ID to associate with")
    allocated_capital: Decimal = Field(gt=0, description="Capital to allocate")
    max_position_size: Optional[Decimal] = Field(default=None, gt=0, description="Maximum position size")
    
    @validator('name')
    def validate_name(cls, v):
        if not v.replace('_', '').replace('-', '').replace(' ', '').isalnum():
            raise ValueError('Strategy name must contain only alphanumeric characters, spaces, hyphens, and underscores')
        return v
    
    @validator('config')
    def validate_config(cls, v, values):
        strategy_type = values.get('type')
        if strategy_type == StrategyType.MA_CROSSOVER:
            required_fields = ['fast_period', 'slow_period', 'symbol']
            for field in required_fields:
                if field not in v:
                    raise ValueError(f'MA Crossover strategy requires {field} in config')
        return v


class StrategyUpdateRequest(BaseModel):
    """Strategy update request schema."""
    name: Optional[str] = Field(default=None, min_length=3, max_length=100, description="Strategy name")
    description: Optional[str] = Field(default=None, max_length=500, description="Strategy description")
    
    # Configuration updates
    config: Optional[Dict[str, Any]] = Field(default=None, description="Strategy configuration parameters")
    risk_config: Optional[Dict[str, Any]] = Field(default=None, description="Risk management configuration")
    
    # Capital allocation updates
    allocated_capital: Optional[Decimal] = Field(default=None, gt=0, description="Capital allocation")
    max_position_size: Optional[Decimal] = Field(default=None, gt=0, description="Maximum position size")


class StrategyControlRequest(BaseModel):
    """Strategy control request schema."""
    action: str = Field(description="Control action")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Action parameters")
    force: bool = Field(default=False, description="Force action even if risky")
    
    @validator('action')
    def validate_action(cls, v):
        allowed_actions = ['start', 'stop', 'pause', 'resume', 'restart']
        if v not in allowed_actions:
            raise ValueError(f'Action must be one of: {", ".join(allowed_actions)}')
        return v


class StrategyListResponse(BaseModel):
    """Strategy list response schema."""
    strategies: List[StrategyResponse] = Field(description="List of strategies")
    total: int = Field(description="Total number of strategies")
    active: int = Field(description="Number of active strategies")
    inactive: int = Field(description="Number of inactive strategies")
    error: int = Field(description="Number of strategies in error state")


class StrategyPerformanceResponse(BaseModel):
    """Strategy performance response schema."""
    strategy_id: int = Field(description="Strategy ID")
    period: str = Field(description="Performance period (daily, weekly, monthly)")
    
    # Performance metrics
    total_return: Decimal = Field(description="Total return")
    total_return_pct: float = Field(description="Total return percentage")
    annualized_return: Optional[float] = Field(default=None, description="Annualized return")
    volatility: Optional[float] = Field(default=None, description="Volatility")
    sharpe_ratio: Optional[float] = Field(default=None, description="Sharpe ratio")
    sortino_ratio: Optional[float] = Field(default=None, description="Sortino ratio")
    max_drawdown: Optional[float] = Field(default=None, description="Maximum drawdown")
    
    # Trade statistics
    total_trades: int = Field(description="Total number of trades")
    winning_trades: int = Field(description="Number of winning trades")
    losing_trades: int = Field(description="Number of losing trades")
    win_rate: float = Field(description="Win rate percentage")
    avg_win: Optional[Decimal] = Field(default=None, description="Average winning trade")
    avg_loss: Optional[Decimal] = Field(default=None, description="Average losing trade")
    profit_factor: Optional[float] = Field(default=None, description="Profit factor")
    
    # Period information
    start_date: str = Field(description="Period start date")
    end_date: str = Field(description="Period end date")
    calculated_at: str = Field(description="Calculation timestamp")