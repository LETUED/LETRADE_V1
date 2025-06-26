"""Portfolio-related schemas for REST API."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class PortfolioStatus(str, Enum):
    """Portfolio status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    LIQUIDATING = "liquidating"


class PositionSide(str, Enum):
    """Position side enumeration."""

    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class AssetType(str, Enum):
    """Asset type enumeration."""

    CRYPTOCURRENCY = "cryptocurrency"
    FIAT = "fiat"
    STABLECOIN = "stablecoin"


class BalanceResponse(BaseModel):
    """Balance response schema."""

    asset: str = Field(description="Asset symbol")
    asset_type: AssetType = Field(description="Asset type")
    free: Decimal = Field(description="Available balance")
    locked: Decimal = Field(description="Locked balance")
    total: Decimal = Field(description="Total balance")
    usd_value: Optional[Decimal] = Field(default=None, description="USD value")
    last_updated: str = Field(description="Last update timestamp")


class PositionResponse(BaseModel):
    """Position response schema."""

    id: int = Field(description="Position ID")
    symbol: str = Field(description="Trading symbol")
    side: PositionSide = Field(description="Position side")
    size: Decimal = Field(description="Position size")
    entry_price: Decimal = Field(description="Average entry price")
    current_price: Optional[Decimal] = Field(
        default=None, description="Current market price"
    )
    unrealized_pnl: Optional[Decimal] = Field(
        default=None, description="Unrealized P&L"
    )
    realized_pnl: Decimal = Field(default=Decimal("0"), description="Realized P&L")

    # Risk metrics
    margin_used: Optional[Decimal] = Field(default=None, description="Margin used")
    leverage: Optional[float] = Field(default=None, description="Leverage ratio")
    liquidation_price: Optional[Decimal] = Field(
        default=None, description="Liquidation price"
    )

    # Timestamps
    opened_at: str = Field(description="Position open timestamp")
    updated_at: str = Field(description="Last update timestamp")

    class Config:
        from_attributes = True


class PortfolioResponse(BaseModel):
    """Portfolio response schema."""

    id: int = Field(description="Portfolio ID")
    name: str = Field(description="Portfolio name")
    status: PortfolioStatus = Field(description="Portfolio status")
    description: Optional[str] = Field(
        default=None, description="Portfolio description"
    )

    # Capital information
    initial_capital: Decimal = Field(description="Initial capital")
    current_value: Decimal = Field(description="Current portfolio value")
    available_capital: Decimal = Field(
        description="Available capital for new positions"
    )
    allocated_capital: Decimal = Field(description="Capital allocated to strategies")

    # Performance metrics
    total_pnl: Decimal = Field(description="Total profit/loss")
    total_pnl_pct: float = Field(description="Total P&L percentage")
    daily_pnl: Decimal = Field(description="Daily profit/loss")
    daily_pnl_pct: float = Field(description="Daily P&L percentage")

    # Risk metrics
    max_drawdown: Optional[float] = Field(default=None, description="Maximum drawdown")
    var_95: Optional[Decimal] = Field(default=None, description="Value at Risk (95%)")
    sharpe_ratio: Optional[float] = Field(default=None, description="Sharpe ratio")

    # Holdings
    balances: List[BalanceResponse] = Field(description="Asset balances")
    positions: List[PositionResponse] = Field(description="Open positions")

    # Configuration
    config: Dict[str, Any] = Field(description="Portfolio configuration")
    risk_limits: Dict[str, Any] = Field(description="Risk limits configuration")

    # Timestamps
    created_at: str = Field(description="Creation timestamp")
    updated_at: str = Field(description="Last update timestamp")

    class Config:
        from_attributes = True


class PortfolioUpdateRequest(BaseModel):
    """Portfolio update request schema."""

    name: Optional[str] = Field(
        default=None, min_length=3, max_length=100, description="Portfolio name"
    )
    description: Optional[str] = Field(
        default=None, max_length=500, description="Portfolio description"
    )

    # Risk limits updates
    risk_limits: Optional[Dict[str, Any]] = Field(
        default=None, description="Risk limits configuration"
    )
    config: Optional[Dict[str, Any]] = Field(
        default=None, description="Portfolio configuration"
    )

    @validator("risk_limits")
    def validate_risk_limits(cls, v):
        if v:
            allowed_keys = [
                "max_position_size_pct",
                "max_daily_loss_pct",
                "max_total_loss_pct",
                "max_leverage",
                "max_correlation",
                "max_sector_exposure_pct",
            ]
            for key in v.keys():
                if key not in allowed_keys:
                    raise ValueError(f"Invalid risk limit key: {key}")
        return v


class PortfolioCreateRequest(BaseModel):
    """Portfolio creation request schema."""

    name: str = Field(min_length=3, max_length=100, description="Portfolio name")
    description: Optional[str] = Field(
        default=None, max_length=500, description="Portfolio description"
    )
    initial_capital: Decimal = Field(gt=0, description="Initial capital amount")

    # Configuration
    config: Optional[Dict[str, Any]] = Field(
        default=None, description="Portfolio configuration"
    )
    risk_limits: Optional[Dict[str, Any]] = Field(
        default=None, description="Risk limits configuration"
    )

    @validator("name")
    def validate_name(cls, v):
        if not v.replace("_", "").replace("-", "").replace(" ", "").isalnum():
            raise ValueError(
                "Portfolio name must contain only alphanumeric characters, spaces, hyphens, and underscores"
            )
        return v


class PortfolioListResponse(BaseModel):
    """Portfolio list response schema."""

    portfolios: List[PortfolioResponse] = Field(description="List of portfolios")
    total: int = Field(description="Total number of portfolios")
    active: int = Field(description="Number of active portfolios")
    total_value: Decimal = Field(description="Total value across all portfolios")


class PortfolioMetricsResponse(BaseModel):
    """Portfolio metrics response schema."""

    portfolio_id: int = Field(description="Portfolio ID")
    period: str = Field(description="Metrics period")

    # Return metrics
    total_return: Decimal = Field(description="Total return")
    total_return_pct: float = Field(description="Total return percentage")
    annualized_return: Optional[float] = Field(
        default=None, description="Annualized return"
    )

    # Risk metrics
    volatility: Optional[float] = Field(default=None, description="Volatility")
    downside_volatility: Optional[float] = Field(
        default=None, description="Downside volatility"
    )
    max_drawdown: Optional[float] = Field(default=None, description="Maximum drawdown")
    var_95: Optional[Decimal] = Field(default=None, description="Value at Risk (95%)")
    cvar_95: Optional[Decimal] = Field(
        default=None, description="Conditional VaR (95%)"
    )

    # Performance ratios
    sharpe_ratio: Optional[float] = Field(default=None, description="Sharpe ratio")
    sortino_ratio: Optional[float] = Field(default=None, description="Sortino ratio")
    calmar_ratio: Optional[float] = Field(default=None, description="Calmar ratio")

    # Portfolio statistics
    total_trades: int = Field(description="Total number of trades")
    winning_days: int = Field(description="Number of winning days")
    losing_days: int = Field(description="Number of losing days")

    # Period information
    start_date: str = Field(description="Period start date")
    end_date: str = Field(description="Period end date")
    calculated_at: str = Field(description="Calculation timestamp")


class AssetAllocationResponse(BaseModel):
    """Asset allocation response schema."""

    portfolio_id: int = Field(description="Portfolio ID")
    allocations: List[Dict[str, Any]] = Field(description="Asset allocations")
    total_allocated_pct: float = Field(description="Total allocated percentage")
    cash_pct: float = Field(description="Cash percentage")
    updated_at: str = Field(description="Last update timestamp")
