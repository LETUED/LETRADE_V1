"""Capital Manager main module for Letrade_v1 trading system.

The Capital Manager is responsible for risk management, position sizing,
capital allocation, and ensuring all trades comply with risk parameters
before execution.
"""

import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from decimal import Decimal
from contextlib import contextmanager

# Add path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.message_bus import MessageBus, create_message_bus  # noqa: E402
from common.database import (  # noqa: E402
    Portfolio, PortfolioRule, Strategy, Trade, Position, 
    db_manager, SystemLog
)

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


# Strategy Pattern for validation rules
class ValidationRule:
    """Base class for validation rules."""
    
    async def validate(self, trade_request: 'TradeRequest', context: Dict[str, Any]) -> bool:
        """Validate trade request.
        
        Args:
            trade_request: Trade request to validate
            context: Validation context including portfolio metrics
            
        Returns:
            True if validation passes, False otherwise
        """
        raise NotImplementedError


class AmountBoundsValidationRule(ValidationRule):
    """Validates trade amount bounds."""
    
    def __init__(self, risk_params: 'RiskParameters'):
        self.risk_params = risk_params
    
    async def validate(self, trade_request: 'TradeRequest', context: Dict[str, Any]) -> bool:
        """Validate trade amount is within bounds."""
        amount_usd = trade_request.quantity * (trade_request.price or context.get('current_price', 0))
        
        if amount_usd < self.risk_params.min_trade_amount:
            context['rejection_reason'] = f"Trade amount ${amount_usd:.2f} below minimum ${self.risk_params.min_trade_amount}"
            return False
        
        if amount_usd > self.risk_params.max_trade_amount:
            context['rejection_reason'] = f"Trade amount ${amount_usd:.2f} exceeds maximum ${self.risk_params.max_trade_amount}"
            return False
        
        return True


class PositionSizingValidationRule(ValidationRule):
    """Validates position sizing rules."""
    
    def __init__(self, risk_params: 'RiskParameters'):
        self.risk_params = risk_params
    
    async def validate(self, trade_request: 'TradeRequest', context: Dict[str, Any]) -> bool:
        """Validate position sizing."""
        portfolio_metrics = context.get('portfolio_metrics', {})
        total_capital = portfolio_metrics.get('total_capital', 0)
        
        if total_capital == 0:
            context['rejection_reason'] = "No capital available"
            return False
        
        trade_value = trade_request.quantity * (trade_request.price or context.get('current_price', 0))
        position_percent = (trade_value / total_capital) * 100
        
        if position_percent > self.risk_params.max_position_size_percent:
            context['rejection_reason'] = f"Position size {position_percent:.2f}% exceeds limit {self.risk_params.max_position_size_percent}%"
            return False
        
        return True


class RiskLimitValidationRule(ValidationRule):
    """Validates risk limits."""
    
    def __init__(self, risk_params: 'RiskParameters'):
        self.risk_params = risk_params
    
    async def validate(self, trade_request: 'TradeRequest', context: Dict[str, Any]) -> bool:
        """Validate risk limits."""
        portfolio_metrics = context.get('portfolio_metrics', {})
        current_risk = portfolio_metrics.get('total_risk_percent', 0)
        
        if current_risk > self.risk_params.max_portfolio_risk_percent:
            context['rejection_reason'] = f"Portfolio risk {current_risk:.2f}% exceeds limit {self.risk_params.max_portfolio_risk_percent}%"
            return False
        
        return True


class ValidationRuleEngine:
    """Engine that applies validation rules using Strategy Pattern."""
    
    def __init__(self, risk_params: 'RiskParameters'):
        self.risk_params = risk_params
        self.rules = [
            AmountBoundsValidationRule(risk_params),
            PositionSizingValidationRule(risk_params),
            RiskLimitValidationRule(risk_params)
        ]
    
    def add_rule(self, rule: ValidationRule) -> None:
        """Add a validation rule."""
        self.rules.append(rule)
    
    async def validate_all(self, trade_request: 'TradeRequest', context: Dict[str, Any]) -> bool:
        """Apply all validation rules."""
        for rule in self.rules:
            if not await rule.validate(trade_request, context):
                return False
        return True


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

    def __init__(self, config: Optional[Dict[str, Any]] = None, message_bus: Optional[MessageBus] = None):
        """Initialize Capital Manager.

        Args:
            config: Configuration dictionary
            message_bus: Message bus instance for communication
        """
        self.config = config or {}
        self.risk_params = RiskParameters()
        self.is_running = False
        self.message_bus = message_bus
        
        # Strategy Pattern: Initialize validation rule engine
        self.validation_engine = ValidationRuleEngine(self.risk_params)
        
        # Message routing
        self._message_handlers = {
            "request.capital.allocation": self._handle_trade_proposal,
            "request.capital.validation": self._handle_trade_validation,
            "events.trade_executed": self._handle_trade_executed_event,
        }

        # Load risk parameters from config
        if "risk_parameters" in self.config:
            self._load_risk_parameters(self.config["risk_parameters"])
            # Update validation engine with new risk parameters
            self.validation_engine = ValidationRuleEngine(self.risk_params)

        # Portfolio tracking
        self._positions = {}  # symbol -> position data
        self._daily_pnl = 0.0
        self._trade_history = []
        self._blocked_symbols = set()

        # Circuit breakers
        self._max_daily_loss_triggered = False
        self._emergency_stop = False
        
        # Database integration for MVP state reconciliation
        self._portfolio_id = self.config.get('portfolio_id', 1)  # Default portfolio
        self._portfolio_rules_cache = {}  # Cache for portfolio rules
        self._db_connected = False

        logger.info(
            "Capital Manager initialized",
            extra={
                "component": "capital_manager",
                "risk_params": self.risk_params.to_dict(),
                "portfolio_id": self._portfolio_id,
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

            # Initialize database connection and load state
            await self._initialize_database_connection()
            
            # Load portfolio rules and state from database
            await self._load_portfolio_state_from_db()

            # Initialize portfolio metrics
            await self._initialize_portfolio_state()

            # Reset daily counters if needed
            await self._reset_daily_counters()
            
            # Setup message subscriptions
            if self.message_bus:
                await self._setup_message_subscriptions()

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

            # Unsubscribe from messages
            if self.message_bus:
                await self._cleanup_message_subscriptions()
                
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

            # Portfolio metrics for validation context
            portfolio_metrics = await self.get_portfolio_metrics()
            
            # Create validation context
            validation_context = {
                'current_price': trade_request.price or 100.0,  # Default price for estimation
                'portfolio_metrics': {
                    'total_capital': portfolio_metrics.total_value,
                    'total_risk_percent': portfolio_metrics.risk_level * 10  # Convert to percentage
                }
            }

            # Apply Strategy Pattern validation
            validation_passed = await self.validation_engine.validate_all(trade_request, validation_context)
            
            if not validation_passed:
                response.reasons.append(validation_context.get('rejection_reason', 'Validation failed'))
                return response

            # Calculate trade amount for further processing
            trade_amount = trade_request.quantity * validation_context['current_price']
            
            # Set approved quantity (validation passed, so approve full amount)
            response.approved_quantity = trade_request.quantity
            
            # Calculate position size percentage for risk level assessment
            position_size_percent = (trade_amount / portfolio_metrics.total_value) * 100
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

            # Save trade validation result to database
            self.save_trade_to_db(trade_request, response)
            
            # Log risk event if rejected
            if response.result != ValidationResult.APPROVED:
                self.log_risk_event_to_db(
                    "trade_rejected",
                    {
                        "strategy_id": trade_request.strategy_id,
                        "symbol": trade_request.symbol,
                        "reasons": response.reasons,
                        "risk_level": response.risk_level.value
                    }
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

            # Update position in database
            position_data = {
                'strategy_id': trade_request.strategy_id,
                'side': trade_request.side,
                'size': execution_result.get("filled_quantity", 0),
                'entry_price': execution_result.get("average_price", trade_request.price),
                'unrealized_pnl': 0,  # Will be updated by market data
                'realized_pnl': 0
            }
            self.update_position_in_db(trade_request.symbol, position_data)

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
    
    # Message handling methods
    async def _setup_message_subscriptions(self):
        """메시지 버스 구독 설정"""
        try:
            # Capital Manager는 capital_requests 큐에 구독
            await self.message_bus.subscribe("capital_requests", self._route_message)
            logger.info(
                "Subscribed to capital_requests queue",
                extra={"component": "capital_manager"}
            )
        except Exception as e:
            logger.error(
                "Failed to setup message subscriptions",
                extra={"component": "capital_manager", "error": str(e)}
            )
            raise
    
    async def _cleanup_message_subscriptions(self):
        """메시지 버스 구독 정리"""
        try:
            # TODO: Implement message subscription cleanup
            logger.info(
                "Message subscriptions cleaned up",
                extra={"component": "capital_manager"}
            )
        except Exception as e:
            logger.error(
                "Failed to cleanup message subscriptions",
                extra={"component": "capital_manager", "error": str(e)}
            )
    
    async def _route_message(self, message: Dict[str, Any]):
        """메시지 라우팅 처리"""
        try:
            routing_key = message.get("routing_key", "")
            
            if routing_key in self._message_handlers:
                handler = self._message_handlers[routing_key]
                await handler(message)
            else:
                logger.warning(
                    f"No handler found for routing key: {routing_key}",
                    extra={"component": "capital_manager"}
                )
                
        except Exception as e:
            logger.error(
                "Error routing message",
                extra={
                    "component": "capital_manager",
                    "error": str(e),
                    "message": message
                }
            )
    
    async def _handle_trade_proposal(self, message: Dict[str, Any]):
        """거래 제안 처리"""
        try:
            payload = message.get("payload", {})
            strategy_id = payload.get("strategy_id")
            signal_data = payload.get("signal_data", {})
            
            logger.info(
                f"Processing trade proposal from strategy {strategy_id}",
                extra={
                    "component": "capital_manager",
                    "strategy_id": strategy_id,
                    "signal_type": signal_data.get("signal_type")
                }
            )
            
            # TradeRequest 객체 생성
            trade_request = self._create_trade_request_from_signal(payload)
            
            # 거래 검증
            validation_response = await self.validate_trade(trade_request)
            
            # 응답 메시지 발송
            await self._send_validation_response(
                strategy_id, 
                validation_response,
                message.get("correlation_id")
            )
            
        except Exception as e:
            logger.error(
                "Failed to handle trade proposal",
                extra={
                    "component": "capital_manager",
                    "error": str(e),
                    "message": message
                }
            )
    
    async def _handle_trade_validation(self, message: Dict[str, Any]):
        """거래 검증 요청 처리"""
        try:
            payload = message.get("payload", {})
            
            # TradeRequest 재구성
            trade_request = TradeRequest(
                strategy_id=payload.get("strategy_id"),
                symbol=payload.get("symbol"),
                side=payload.get("side"),
                quantity=payload.get("quantity"),
                price=payload.get("price"),
                order_type=payload.get("order_type", "market")
            )
            
            # 검증 수행
            validation_response = await self.validate_trade(trade_request)
            
            # 응답 발송
            await self._send_validation_response(
                trade_request.strategy_id,
                validation_response,
                message.get("correlation_id")
            )
            
        except Exception as e:
            logger.error(
                "Failed to handle trade validation",
                extra={
                    "component": "capital_manager",
                    "error": str(e),
                    "message": message
                }
            )
    
    async def _handle_trade_executed_event(self, message: Dict[str, Any]):
        """거래 실행 이벤트 처리"""
        try:
            payload = message.get("payload", {})
            
            # 거래 기록 업데이트
            trade_record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "strategy_id": payload.get("strategy_id"),
                "symbol": payload.get("symbol"),
                "side": payload.get("side"),
                "executed_quantity": payload.get("filled_quantity", 0),
                "price": payload.get("average_price", 0),
                "status": payload.get("status", "filled"),
                "order_id": payload.get("order_id"),
                "fees": payload.get("fees", 0)
            }
            
            await self._update_position_tracking(trade_record)
            await self._update_daily_pnl(trade_record)
            
            logger.info(
                "Trade execution event processed",
                extra={
                    "component": "capital_manager",
                    "order_id": trade_record["order_id"],
                    "symbol": trade_record["symbol"]
                }
            )
            
        except Exception as e:
            logger.error(
                "Failed to handle trade executed event",
                extra={
                    "component": "capital_manager",
                    "error": str(e),
                    "message": message
                }
            )
    
    def _create_trade_request_from_signal(self, payload: Dict[str, Any]) -> TradeRequest:
        """신호 데이터로부터 TradeRequest 생성"""
        signal_data = payload.get("signal_data", {})
        
        # 기본 거래 크기 설정 (포트폴리오의 1%)
        default_quantity = 0.01  # BTC 기준
        
        return TradeRequest(
            strategy_id=payload.get("strategy_id"),
            symbol=signal_data.get("symbol", "BTC/USDT"),
            side="buy" if signal_data.get("signal_type") == "golden_cross" else "sell",
            quantity=signal_data.get("quantity", default_quantity),
            price=signal_data.get("current_price"),
            order_type="market",
            metadata={
                "signal_type": signal_data.get("signal_type"),
                "signal_strength": signal_data.get("signal_strength", 0),
                "fast_ma": signal_data.get("fast_ma"),
                "slow_ma": signal_data.get("slow_ma")
            }
        )
    
    async def _send_validation_response(
        self, 
        strategy_id: str, 
        validation_response: ValidationResponse,
        correlation_id: Optional[str] = None
    ):
        """검증 응답 메시지 발송"""
        if not self.message_bus:
            logger.warning("Message bus not available for sending response")
            return
        
        try:
            # 응답에 따라 다른 라우팅 키 사용
            if validation_response.result == ValidationResult.APPROVED:
                routing_key = "commands.execute_trade"
                exchange_name = "letrade.commands"
                
                payload = {
                    "strategy_id": strategy_id,
                    "correlation_id": correlation_id,
                    "trade_command": {
                        "symbol": "BTC/USDT",  # TODO: 실제 심볼 사용
                        "side": "buy",  # TODO: 실제 거래 정보에서 가져오기
                        "quantity": validation_response.approved_quantity,
                        "order_type": "market"
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                routing_key = "response.capital.validation"
                exchange_name = "letrade.events"
                
                payload = {
                    "strategy_id": strategy_id,
                    "correlation_id": correlation_id,
                    "validation_result": validation_response.to_dict(),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            await self.message_bus.publish(exchange_name, routing_key, payload)
            
            logger.info(
                f"Validation response sent to strategy {strategy_id}",
                extra={
                    "component": "capital_manager",
                    "result": validation_response.result.value,
                    "routing_key": routing_key
                }
            )
            
        except Exception as e:
            logger.error(
                "Failed to send validation response",
                extra={
                    "component": "capital_manager",
                    "strategy_id": strategy_id,
                    "error": str(e)
                }
            )
    
    async def _initialize_database_connection(self) -> None:
        """Initialize database connection for MVP state reconciliation."""
        try:
            # Ensure database manager is connected
            if not db_manager.engine:
                db_manager.connect()
            
            self._db_connected = True
            logger.info("Database connection initialized for Capital Manager")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            self._db_connected = False
    
    async def _load_portfolio_state_from_db(self) -> None:
        """Load portfolio rules and state from database.
        
        Critical for MVP state reconciliation requirements.
        """
        try:
            if not self._db_connected:
                logger.warning("Database not connected, skipping state load")
                return
                
            with self._get_db_session() as session:
                # Load portfolio
                portfolio = session.query(Portfolio).filter_by(id=self._portfolio_id).first()
                if not portfolio:
                    logger.warning(f"Portfolio {self._portfolio_id} not found in database")
                    return
                
                # Load portfolio rules
                rules = session.query(PortfolioRule)\
                    .filter_by(portfolio_id=self._portfolio_id, is_active=True)\
                    .all()
                
                # Update risk parameters from database rules
                for rule in rules:
                    rule_value = rule.rule_value.get('value', 0) if rule.rule_value else 0
                    
                    if rule.rule_type == 'max_position_size_percent':
                        self.risk_params.max_position_size_percent = rule_value
                    elif rule.rule_type == 'max_daily_loss_percent':
                        self.risk_params.max_daily_loss_percent = rule_value
                    elif rule.rule_type == 'max_portfolio_exposure_percent':
                        self.risk_params.max_portfolio_risk_percent = rule_value
                    elif rule.rule_type == 'min_position_size_usd':
                        # Store for validation later
                        self._portfolio_rules_cache[rule.rule_type] = rule_value
                    elif rule.rule_type == 'blacklisted_symbols':
                        # Update blocked symbols
                        blocked_symbols = rule.rule_value.get('symbols', [])
                        self._blocked_symbols.update(blocked_symbols)
                
                # Load current positions from database
                positions = session.query(Position)\
                    .join(Strategy)\
                    .filter(Strategy.portfolio_id == self._portfolio_id, Position.is_open == True)\
                    .all()
                
                for position in positions:
                    position_data = {
                        'strategy_id': position.strategy_id,
                        'side': position.side,
                        'size': float(position.current_size),
                        'entry_price': float(position.entry_price),
                        'unrealized_pnl': float(position.unrealized_pnl),
                        'realized_pnl': float(position.realized_pnl)
                    }
                    self._positions[position.symbol] = position_data
                
                logger.info(
                    f"Loaded portfolio state from database",
                    extra={
                        "portfolio_id": self._portfolio_id,
                        "rules_loaded": len(rules),
                        "positions_loaded": len(positions),
                        "blocked_symbols": len(self._blocked_symbols)
                    }
                )
                
        except Exception as e:
            logger.error(f"Failed to load portfolio state from database: {e}")
    
    def save_trade_to_db(self, trade_request: TradeRequest, validation_result: ValidationResponse) -> None:
        """Save trade record to database.
        
        Args:
            trade_request: Original trade request
            validation_result: Validation result
        """
        try:
            if not self._db_connected:
                logger.warning("Database not connected, skipping trade save")
                return
                
            with self._get_db_session() as session:
                # Get strategy
                strategy = session.query(Strategy).filter_by(id=trade_request.strategy_id).first()
                if not strategy:
                    logger.warning(f"Strategy {trade_request.strategy_id} not found")
                    return
                
                # Create trade record
                trade = Trade(
                    strategy_id=trade_request.strategy_id,
                    exchange=strategy.exchange,
                    symbol=trade_request.symbol,
                    side=trade_request.side,
                    type='market',  # Default to market for now
                    amount=Decimal(str(trade_request.quantity)),
                    price=Decimal(str(trade_request.price)) if trade_request.price else None,
                    status='pending' if validation_result.result == ValidationResult.APPROVED else 'rejected',
                    error_message=validation_result.reasons[0] if validation_result.result != ValidationResult.APPROVED and validation_result.reasons else None
                )
                
                session.add(trade)
                session.commit()
                
                logger.info(
                    f"Trade saved to database",
                    extra={
                        "trade_id": trade.id,
                        "strategy_id": trade_request.strategy_id,
                        "symbol": trade_request.symbol,
                        "status": trade.status
                    }
                )
                
        except Exception as e:
            logger.error(f"Failed to save trade to database: {e}")
    
    def update_position_in_db(self, symbol: str, position_data: Dict[str, Any]) -> None:
        """Update position in database.
        
        Args:
            symbol: Trading symbol
            position_data: Position information
        """
        try:
            if not self._db_connected:
                return
                
            with self._get_db_session() as session:
                # Find existing position
                position = session.query(Position)\
                    .filter_by(
                        strategy_id=position_data['strategy_id'],
                        symbol=symbol,
                        is_open=True
                    ).first()
                
                if position:
                    # Update existing position
                    position.current_size = Decimal(str(position_data['size']))
                    position.unrealized_pnl = Decimal(str(position_data.get('unrealized_pnl', 0)))
                    position.realized_pnl = Decimal(str(position_data.get('realized_pnl', 0)))
                else:
                    # Create new position
                    position = Position(
                        strategy_id=position_data['strategy_id'],
                        exchange='binance',  # Default for now
                        symbol=symbol,
                        side=position_data['side'],
                        entry_price=Decimal(str(position_data['entry_price'])),
                        current_size=Decimal(str(position_data['size'])),
                        avg_entry_price=Decimal(str(position_data['entry_price'])),
                        unrealized_pnl=Decimal(str(position_data.get('unrealized_pnl', 0))),
                        realized_pnl=Decimal(str(position_data.get('realized_pnl', 0)))
                    )
                    session.add(position)
                
                session.commit()
                
        except Exception as e:
            logger.error(f"Failed to update position in database: {e}")
    
    def log_risk_event_to_db(self, event_type: str, details: Dict[str, Any]) -> None:
        """Log risk management event to database.
        
        Args:
            event_type: Type of risk event
            details: Event details
        """
        try:
            if not self._db_connected:
                return
                
            with self._get_db_session() as session:
                log_entry = SystemLog(
                    level="WARNING" if "rejected" in event_type.lower() else "INFO",
                    logger_name="capital_manager.risk",
                    message=f"Risk event: {event_type}",
                    context=details,
                    strategy_id=details.get('strategy_id')
                )
                
                session.add(log_entry)
                session.commit()
                
        except Exception as e:
            logger.error(f"Failed to log risk event: {e}")
    
    @contextmanager
    def _get_db_session(self):
        """Get database session with proper cleanup."""
        session = db_manager.get_session()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


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
