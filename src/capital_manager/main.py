"""Capital Manager main module for Letrade_v1 trading system.

The Capital Manager is responsible for risk management, position sizing,
capital allocation, and ensuring all trades comply with risk parameters
before execution.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level categories."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class ValidationResult(Enum):
    """Trade validation results."""

    APPROVED = "approved"
    REJECTED = "rejected"
    REQUIRES_APPROVAL = "requires_approval"


@dataclass
class RiskParameters:
    """Risk management parameters."""

    max_position_size_percent: float = 5.0  # Max % of portfolio per position
    max_daily_loss_percent: float = 2.0  # Max daily loss %
    max_portfolio_risk_percent: float = 10.0  # Max total portfolio risk %
    max_correlation_exposure: float = 0.3  # Max correlation between positions
    stop_loss_percent: float = 2.0  # Default stop loss %
    take_profit_percent: float = 6.0  # Default take profit %
    max_leverage: float = 1.0  # Max leverage allowed
    min_trade_amount: float = 10.0  # Minimum trade amount in USD
    max_trade_amount: float = 10000.0  # Maximum trade amount in USD

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "max_position_size_percent": self.max_position_size_percent,
            "max_daily_loss_percent": self.max_daily_loss_percent,
            "max_portfolio_risk_percent": self.max_portfolio_risk_percent,
            "max_correlation_exposure": self.max_correlation_exposure,
            "stop_loss_percent": self.stop_loss_percent,
            "take_profit_percent": self.take_profit_percent,
            "max_leverage": self.max_leverage,
            "min_trade_amount": self.min_trade_amount,
            "max_trade_amount": self.max_trade_amount,
        }


@dataclass
class TradeRequest:
    """Trade request for validation."""

    strategy_id: str
    symbol: str
    side: str  # "buy" or "sell"
    quantity: float
    price: Optional[float] = None
    order_type: str = "market"
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "price": self.price,
            "order_type": self.order_type,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ValidationResponse:
    """Trade validation response."""

    result: ValidationResult
    approved_quantity: float
    risk_level: RiskLevel
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggested_stop_loss: Optional[float] = None
    suggested_take_profit: Optional[float] = None
    estimated_risk_amount: float = 0.0
    portfolio_impact: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "result": self.result.value,
            "approved_quantity": self.approved_quantity,
            "risk_level": self.risk_level.value,
            "reasons": self.reasons,
            "warnings": self.warnings,
            "suggested_stop_loss": self.suggested_stop_loss,
            "suggested_take_profit": self.suggested_take_profit,
            "estimated_risk_amount": self.estimated_risk_amount,
            "portfolio_impact": self.portfolio_impact,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class PortfolioMetrics:
    """Portfolio performance metrics."""

    total_value: float
    available_cash: float
    unrealized_pnl: float
    realized_pnl_today: float
    total_risk_exposure: float
    number_of_positions: int
    largest_position_percent: float
    daily_var: float  # Value at Risk
    sharpe_ratio: Optional[float] = None
    max_drawdown_percent: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_value": self.total_value,
            "available_cash": self.available_cash,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl_today": self.realized_pnl_today,
            "total_risk_exposure": self.total_risk_exposure,
            "number_of_positions": self.number_of_positions,
            "largest_position_percent": self.largest_position_percent,
            "daily_var": self.daily_var,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown_percent": self.max_drawdown_percent,
            "timestamp": self.timestamp.isoformat(),
        }


class CapitalManager:
    """Capital Manager for risk management and trade validation.

    The Capital Manager ensures all trades comply with risk parameters,
    manages position sizing, and tracks portfolio metrics.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Capital Manager.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.risk_params = RiskParameters()
        self.is_running = False

        # Load risk parameters from config
        if "risk_parameters" in self.config:
            self._load_risk_parameters(self.config["risk_parameters"])

        # Portfolio tracking
        self._positions = {}  # symbol -> position data
        self._daily_pnl = 0.0
        self._trade_history = []
        self._blocked_symbols = set()

        # Circuit breakers
        self._max_daily_loss_triggered = False
        self._emergency_stop = False

        logger.info(
            "Capital Manager initialized",
            extra={
                "component": "capital_manager",
                "risk_params": self.risk_params.to_dict(),
            },
        )

    async def start(self) -> bool:
        """Start the Capital Manager.

        Returns:
            True if started successfully, False otherwise
        """
        try:
            logger.info(
                "Starting Capital Manager", extra={"component": "capital_manager"}
            )

            # Initialize portfolio metrics
            await self._initialize_portfolio_state()

            # Reset daily counters if needed
            await self._reset_daily_counters()

            self.is_running = True

            logger.info(
                "Capital Manager started successfully",
                extra={"component": "capital_manager"},
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to start Capital Manager",
                extra={"component": "capital_manager", "error": str(e)},
            )
            return False

    async def stop(self) -> bool:
        """Stop the Capital Manager.

        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            logger.info(
                "Stopping Capital Manager", extra={"component": "capital_manager"}
            )

            # Persist final state
            await self._persist_portfolio_state()

            self.is_running = False

            logger.info(
                "Capital Manager stopped successfully",
                extra={
                    "component": "capital_manager",
                    "final_daily_pnl": self._daily_pnl,
                    "total_positions": len(self._positions),
                },
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to stop Capital Manager",
                extra={"component": "capital_manager", "error": str(e)},
            )
            return False

    async def validate_trade(self, trade_request: TradeRequest) -> ValidationResponse:
        """Validate a trade request against risk parameters.

        Args:
            trade_request: Trade request to validate

        Returns:
            Validation response with approval/rejection and reasons
        """
        try:
            logger.info(
                "Validating trade request",
                extra={
                    "component": "capital_manager",
                    "strategy_id": trade_request.strategy_id,
                    "symbol": trade_request.symbol,
                    "side": trade_request.side,
                    "quantity": trade_request.quantity,
                },
            )

            # Initialize response
            response = ValidationResponse(
                result=ValidationResult.REJECTED,
                approved_quantity=0.0,
                risk_level=RiskLevel.HIGH,
            )

            # Pre-validation checks
            if not self.is_running:
                response.reasons.append("Capital Manager is not running")
                return response

            if self._emergency_stop:
                response.reasons.append("Emergency stop is active")
                return response

            if trade_request.symbol in self._blocked_symbols:
                response.reasons.append(f"Symbol {trade_request.symbol} is blocked")
                return response

            # Circuit breaker checks
            if self._max_daily_loss_triggered:
                response.reasons.append("Daily loss limit exceeded")
                return response

            # Validate trade amount
            trade_amount = trade_request.quantity * (
                trade_request.price or 100.0
            )  # Default price for estimation

            if trade_amount < self.risk_params.min_trade_amount:
                response.reasons.append(
                    f"Trade amount {trade_amount:.2f} below minimum "
                    f"{self.risk_params.min_trade_amount}"
                )
                return response

            if trade_amount > self.risk_params.max_trade_amount:
                response.reasons.append(
                    f"Trade amount {trade_amount:.2f} exceeds maximum "
                    f"{self.risk_params.max_trade_amount}"
                )
                return response

            # Portfolio metrics
            portfolio_metrics = await self.get_portfolio_metrics()

            # Position size validation
            position_size_percent = (trade_amount / portfolio_metrics.total_value) * 100
            if position_size_percent > self.risk_params.max_position_size_percent:
                # Calculate approved quantity
                max_trade_amount = (
                    portfolio_metrics.total_value
                    * self.risk_params.max_position_size_percent
                ) / 100
                approved_quantity = max_trade_amount / (trade_request.price or 100.0)

                response.approved_quantity = approved_quantity
                response.warnings.append(
                    f"Position size reduced from {position_size_percent:.2f}% "
                    f"to {self.risk_params.max_position_size_percent}%"
                )
                response.risk_level = RiskLevel.MEDIUM
            else:
                response.approved_quantity = trade_request.quantity
                response.risk_level = self._calculate_risk_level(position_size_percent)

            # Daily loss check
            estimated_risk = trade_amount * (self.risk_params.stop_loss_percent / 100)
            if (portfolio_metrics.realized_pnl_today - estimated_risk) < -(
                portfolio_metrics.total_value
                * self.risk_params.max_daily_loss_percent
                / 100
            ):
                response.reasons.append("Trade would exceed daily loss limit")
                return response

            # Portfolio risk check
            current_risk_percent = (
                portfolio_metrics.total_risk_exposure / portfolio_metrics.total_value
            ) * 100
            new_risk_percent = (
                current_risk_percent
                + (estimated_risk / portfolio_metrics.total_value) * 100
            )

            if new_risk_percent > self.risk_params.max_portfolio_risk_percent:
                response.reasons.append(
                    f"Trade would exceed portfolio risk limit "
                    f"({new_risk_percent:.2f}% > "
                    f"{self.risk_params.max_portfolio_risk_percent}%)"
                )
                return response

            # Generate risk management suggestions
            if not trade_request.stop_loss:
                if trade_request.side == "buy":
                    response.suggested_stop_loss = (trade_request.price or 100.0) * (
                        1 - self.risk_params.stop_loss_percent / 100
                    )
                else:
                    response.suggested_stop_loss = (trade_request.price or 100.0) * (
                        1 + self.risk_params.stop_loss_percent / 100
                    )

            if not trade_request.take_profit:
                if trade_request.side == "buy":
                    response.suggested_take_profit = (trade_request.price or 100.0) * (
                        1 + self.risk_params.take_profit_percent / 100
                    )
                else:
                    response.suggested_take_profit = (trade_request.price or 100.0) * (
                        1 - self.risk_params.take_profit_percent / 100
                    )

            # Final approval
            response.result = ValidationResult.APPROVED
            response.estimated_risk_amount = estimated_risk
            response.portfolio_impact = {
                "position_size_percent": position_size_percent,
                "new_portfolio_risk_percent": new_risk_percent,
                "estimated_daily_pnl_impact": estimated_risk,
            }

            logger.info(
                "Trade validation completed",
                extra={
                    "component": "capital_manager",
                    "result": response.result.value,
                    "approved_quantity": response.approved_quantity,
                    "risk_level": response.risk_level.value,
                },
            )

            return response

        except Exception as e:
            logger.error(
                "Trade validation failed",
                extra={"component": "capital_manager", "error": str(e)},
            )

            return ValidationResponse(
                result=ValidationResult.REJECTED,
                approved_quantity=0.0,
                risk_level=RiskLevel.EXTREME,
                reasons=[f"Validation error: {str(e)}"],
            )

    async def record_trade_execution(
        self, trade_request: TradeRequest, execution_result: Dict[str, Any]
    ) -> bool:
        """Record the execution of a trade.

        Args:
            trade_request: Original trade request
            execution_result: Result from exchange execution

        Returns:
            True if recorded successfully, False otherwise
        """
        try:
            # Record trade in history
            trade_record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "strategy_id": trade_request.strategy_id,
                "symbol": trade_request.symbol,
                "side": trade_request.side,
                "requested_quantity": trade_request.quantity,
                "executed_quantity": execution_result.get("filled_quantity", 0),
                "price": execution_result.get("average_price", trade_request.price),
                "status": execution_result.get("status", "unknown"),
                "order_id": execution_result.get("order_id"),
                "fees": execution_result.get("fees", 0),
            }

            self._trade_history.append(trade_record)

            # Update position tracking
            await self._update_position_tracking(trade_record)

            # Update daily P&L if trade is filled
            if execution_result.get("status") == "filled":
                await self._update_daily_pnl(trade_record)

            logger.info(
                "Trade execution recorded",
                extra={"component": "capital_manager", "trade_record": trade_record},
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to record trade execution",
                extra={"component": "capital_manager", "error": str(e)},
            )
            return False

    async def get_portfolio_metrics(self) -> PortfolioMetrics:
        """Get current portfolio metrics.

        Returns:
            Portfolio metrics object
        """
        try:
            # TODO: Integrate with exchange connector to get real-time data
            # For now, return mock metrics

            total_value = 10000.0  # Mock total portfolio value
            available_cash = 5000.0  # Mock available cash
            unrealized_pnl = 100.0  # Mock unrealized P&L
            total_risk_exposure = 500.0  # Mock risk exposure

            return PortfolioMetrics(
                total_value=total_value,
                available_cash=available_cash,
                unrealized_pnl=unrealized_pnl,
                realized_pnl_today=self._daily_pnl,
                total_risk_exposure=total_risk_exposure,
                number_of_positions=len(self._positions),
                largest_position_percent=max(
                    [pos.get("size_percent", 0) for pos in self._positions.values()],
                    default=0,
                ),
                daily_var=total_value * 0.02,  # 2% Value at Risk
            )

        except Exception as e:
            logger.error(
                "Failed to calculate portfolio metrics",
                extra={"component": "capital_manager", "error": str(e)},
            )

            # Return default safe metrics
            return PortfolioMetrics(
                total_value=0.0,
                available_cash=0.0,
                unrealized_pnl=0.0,
                realized_pnl_today=0.0,
                total_risk_exposure=0.0,
                number_of_positions=0,
                largest_position_percent=0.0,
                daily_var=0.0,
            )

    async def emergency_stop(self, reason: str) -> bool:
        """Activate emergency stop.

        Args:
            reason: Reason for emergency stop

        Returns:
            True if activated successfully
        """
        try:
            self._emergency_stop = True

            logger.critical(
                "Emergency stop activated",
                extra={
                    "component": "capital_manager",
                    "reason": reason,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            # TODO: Send alerts to administrators
            # TODO: Close all open positions if configured

            return True

        except Exception as e:
            logger.error(
                "Failed to activate emergency stop",
                extra={"component": "capital_manager", "error": str(e)},
            )
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check.

        Returns:
            Health status dictionary
        """
        try:
            portfolio_metrics = await self.get_portfolio_metrics()

            return {
                "component": "capital_manager",
                "healthy": self.is_running and not self._emergency_stop,
                "running": self.is_running,
                "emergency_stop": self._emergency_stop,
                "daily_loss_limit_triggered": self._max_daily_loss_triggered,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "portfolio_metrics": portfolio_metrics.to_dict(),
                "risk_parameters": self.risk_params.to_dict(),
                "total_trades_today": len(
                    [
                        t
                        for t in self._trade_history
                        if datetime.fromisoformat(t["timestamp"]).date()
                        == datetime.now(timezone.utc).date()
                    ]
                ),
                "blocked_symbols": list(self._blocked_symbols),
            }

        except Exception as e:
            logger.error(
                "Health check failed",
                extra={"component": "capital_manager", "error": str(e)},
            )

            return {
                "component": "capital_manager",
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    # Private methods
    def _load_risk_parameters(self, risk_config: Dict[str, Any]):
        """Load risk parameters from configuration."""
        for key, value in risk_config.items():
            if hasattr(self.risk_params, key):
                setattr(self.risk_params, key, value)

        logger.info(
            "Risk parameters loaded",
            extra={
                "component": "capital_manager",
                "parameters": self.risk_params.to_dict(),
            },
        )

    def _calculate_risk_level(self, position_size_percent: float) -> RiskLevel:
        """Calculate risk level based on position size."""
        if position_size_percent <= 1.0:
            return RiskLevel.LOW
        elif position_size_percent <= 3.0:
            return RiskLevel.MEDIUM
        elif position_size_percent <= 5.0:
            return RiskLevel.HIGH
        else:
            return RiskLevel.EXTREME

    async def _initialize_portfolio_state(self):
        """Initialize portfolio state on startup."""
        # TODO: Load existing positions and state from database
        logger.info(
            "Portfolio state initialized", extra={"component": "capital_manager"}
        )

    async def _reset_daily_counters(self):
        """Reset daily counters if new day."""
        # TODO: Check if new trading day and reset counters
        current_date = datetime.now(timezone.utc).date()
        # Reset logic here
        logger.info(
            "Daily counters checked",
            extra={"component": "capital_manager", "date": current_date.isoformat()},
        )

    async def _persist_portfolio_state(self):
        """Persist portfolio state."""
        # TODO: Save portfolio state to database
        logger.info("Portfolio state persisted", extra={"component": "capital_manager"})

    async def _update_position_tracking(self, trade_record: Dict[str, Any]):
        """Update position tracking after trade execution."""
        symbol = trade_record["symbol"]

        if symbol not in self._positions:
            self._positions[symbol] = {
                "quantity": 0.0,
                "average_price": 0.0,
                "unrealized_pnl": 0.0,
                "size_percent": 0.0,
            }

        # TODO: Update position calculations
        logger.debug(
            "Position tracking updated",
            extra={"component": "capital_manager", "symbol": symbol},
        )

    async def _update_daily_pnl(self, trade_record: Dict[str, Any]):
        """Update daily P&L after trade execution."""
        # TODO: Calculate and update daily P&L
        logger.debug(
            "Daily P&L updated",
            extra={"component": "capital_manager", "daily_pnl": self._daily_pnl},
        )


async def main():
    """Main entry point for testing Capital Manager."""
    logging.basicConfig(level=logging.INFO)

    # Test configuration
    config = {
        "risk_parameters": {
            "max_position_size_percent": 3.0,
            "max_daily_loss_percent": 1.5,
            "stop_loss_percent": 1.5,
            "take_profit_percent": 4.5,
        }
    }

    # Create and test Capital Manager
    capital_manager = CapitalManager(config)

    try:
        if await capital_manager.start():
            logger.info("Capital Manager started successfully")

            # Test trade validation
            trade_request = TradeRequest(
                strategy_id="test_strategy",
                symbol="BTCUSDT",
                side="buy",
                quantity=0.01,
                price=50000.0,
            )

            validation_response = await capital_manager.validate_trade(trade_request)
            logger.info(
                "Trade validation: %s",
                json.dumps(validation_response.to_dict(), indent=2),
            )

            # Test health check
            health = await capital_manager.health_check()
            logger.info(f"Health check: {json.dumps(health, indent=2)}")

        else:
            logger.error("Failed to start Capital Manager")

    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await capital_manager.stop()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
