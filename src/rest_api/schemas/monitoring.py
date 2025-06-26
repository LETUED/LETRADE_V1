"""Monitoring and system status schemas for REST API."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SystemStatus(str, Enum):
    """System status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    MAINTENANCE = "maintenance"


class ComponentStatus(str, Enum):
    """Component status enumeration."""

    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    STARTING = "starting"
    STOPPING = "stopping"


class AlertLevel(str, Enum):
    """Alert level enumeration."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ComponentStatusResponse(BaseModel):
    """Component status response schema."""

    name: str = Field(description="Component name")
    status: ComponentStatus = Field(description="Component status")
    uptime: Optional[int] = Field(default=None, description="Uptime in seconds")
    last_heartbeat: Optional[str] = Field(
        default=None, description="Last heartbeat timestamp"
    )
    error_count: int = Field(default=0, description="Number of errors")
    performance_metrics: Optional[Dict[str, Any]] = Field(
        default=None, description="Performance metrics"
    )


class SystemStatusResponse(BaseModel):
    """System status response schema."""

    overall_status: SystemStatus = Field(description="Overall system status")
    uptime: int = Field(description="System uptime in seconds")
    version: str = Field(description="System version")

    # Component statuses
    components: List[ComponentStatusResponse] = Field(description="Component statuses")

    # System metrics
    cpu_usage: Optional[float] = Field(default=None, description="CPU usage percentage")
    memory_usage: Optional[float] = Field(
        default=None, description="Memory usage percentage"
    )
    disk_usage: Optional[float] = Field(
        default=None, description="Disk usage percentage"
    )

    # Trading metrics
    active_strategies: int = Field(description="Number of active strategies")
    total_portfolios: int = Field(description="Total number of portfolios")
    open_positions: int = Field(description="Number of open positions")
    daily_trades: int = Field(description="Number of trades today")

    # Market data
    market_data_lag: Optional[int] = Field(
        default=None, description="Market data lag in milliseconds"
    )
    last_price_update: Optional[str] = Field(
        default=None, description="Last price update timestamp"
    )

    # Timestamps
    timestamp: str = Field(description="Status timestamp")
    last_restart: Optional[str] = Field(
        default=None, description="Last system restart timestamp"
    )


class MetricsResponse(BaseModel):
    """System metrics response schema."""

    period: str = Field(description="Metrics period")

    # Performance metrics
    avg_response_time: float = Field(
        description="Average response time in milliseconds"
    )
    p95_response_time: float = Field(description="95th percentile response time")
    p99_response_time: float = Field(description="99th percentile response time")
    throughput: float = Field(description="Requests per second")
    error_rate: float = Field(description="Error rate percentage")

    # Trading metrics
    total_trades: int = Field(description="Total number of trades")
    successful_trades: int = Field(description="Number of successful trades")
    failed_trades: int = Field(description="Number of failed trades")
    trade_success_rate: float = Field(description="Trade success rate percentage")
    avg_trade_execution_time: float = Field(
        description="Average trade execution time in milliseconds"
    )

    # System resource metrics
    avg_cpu_usage: float = Field(description="Average CPU usage percentage")
    max_cpu_usage: float = Field(description="Maximum CPU usage percentage")
    avg_memory_usage: float = Field(description="Average memory usage percentage")
    max_memory_usage: float = Field(description="Maximum memory usage percentage")

    # Message bus metrics
    messages_published: int = Field(description="Number of messages published")
    messages_consumed: int = Field(description="Number of messages consumed")
    message_queue_depth: int = Field(description="Current message queue depth")

    # Period information
    start_time: str = Field(description="Period start time")
    end_time: str = Field(description="Period end time")
    collected_at: str = Field(description="Collection timestamp")


class PerformanceResponse(BaseModel):
    """Performance summary response schema."""

    period: str = Field(description="Performance period")

    # Overall performance
    total_pnl: Decimal = Field(description="Total profit/loss")
    total_pnl_pct: float = Field(description="Total P&L percentage")
    total_return: Decimal = Field(description="Total return")

    # Strategy performance
    active_strategies: int = Field(description="Number of active strategies")
    profitable_strategies: int = Field(description="Number of profitable strategies")
    avg_strategy_return: float = Field(description="Average strategy return percentage")
    best_strategy_return: float = Field(description="Best strategy return percentage")
    worst_strategy_return: float = Field(description="Worst strategy return percentage")

    # Portfolio performance
    total_portfolio_value: Decimal = Field(description="Total portfolio value")
    available_capital: Decimal = Field(description="Available capital")
    allocated_capital: Decimal = Field(description="Allocated capital")
    utilization_rate: float = Field(description="Capital utilization rate percentage")

    # Risk metrics
    max_drawdown: Optional[float] = Field(default=None, description="Maximum drawdown")
    current_drawdown: Optional[float] = Field(
        default=None, description="Current drawdown"
    )
    var_95: Optional[Decimal] = Field(default=None, description="Value at Risk (95%)")
    sharpe_ratio: Optional[float] = Field(default=None, description="Sharpe ratio")

    # Trade statistics
    total_trades: int = Field(description="Total number of trades")
    winning_trades: int = Field(description="Number of winning trades")
    losing_trades: int = Field(description="Number of losing trades")
    win_rate: float = Field(description="Win rate percentage")

    # Period information
    start_date: str = Field(description="Period start date")
    end_date: str = Field(description="Period end date")
    calculated_at: str = Field(description="Calculation timestamp")


class AlertResponse(BaseModel):
    """Alert response schema."""

    id: int = Field(description="Alert ID")
    level: AlertLevel = Field(description="Alert level")
    title: str = Field(description="Alert title")
    message: str = Field(description="Alert message")
    component: Optional[str] = Field(
        default=None, description="Component that triggered the alert"
    )
    strategy_id: Optional[int] = Field(
        default=None, description="Strategy ID if related"
    )
    portfolio_id: Optional[int] = Field(
        default=None, description="Portfolio ID if related"
    )

    # Alert details
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional alert details"
    )
    acknowledged: bool = Field(
        default=False, description="Whether alert has been acknowledged"
    )
    resolved: bool = Field(default=False, description="Whether alert has been resolved")

    # Timestamps
    created_at: str = Field(description="Alert creation timestamp")
    acknowledged_at: Optional[str] = Field(
        default=None, description="Acknowledgment timestamp"
    )
    resolved_at: Optional[str] = Field(default=None, description="Resolution timestamp")


class LogResponse(BaseModel):
    """Log entry response schema."""

    id: int = Field(description="Log entry ID")
    level: str = Field(description="Log level")
    message: str = Field(description="Log message")
    component: str = Field(description="Component that generated the log")

    # Context information
    strategy_id: Optional[int] = Field(
        default=None, description="Strategy ID if related"
    )
    portfolio_id: Optional[int] = Field(
        default=None, description="Portfolio ID if related"
    )
    trade_id: Optional[str] = Field(default=None, description="Trade ID if related")

    # Additional data
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional log metadata"
    )
    stack_trace: Optional[str] = Field(default=None, description="Stack trace if error")

    # Timestamp
    timestamp: str = Field(description="Log timestamp")


class SystemConfigResponse(BaseModel):
    """System configuration response schema."""

    environment: str = Field(description="Current environment")
    debug_mode: bool = Field(description="Whether debug mode is enabled")

    # Component configurations
    exchange_config: Dict[str, Any] = Field(
        description="Exchange connector configuration"
    )
    message_bus_config: Dict[str, Any] = Field(description="Message bus configuration")
    database_config: Dict[str, Any] = Field(description="Database configuration")

    # Trading configurations
    default_risk_limits: Dict[str, Any] = Field(description="Default risk limits")
    trading_hours: Dict[str, Any] = Field(description="Trading hours configuration")
    supported_exchanges: List[str] = Field(description="Supported exchanges")
    supported_symbols: List[str] = Field(description="Supported trading symbols")

    # Feature flags
    features: Dict[str, bool] = Field(description="Feature flags")

    # Last updated
    updated_at: str = Field(description="Configuration last update timestamp")
