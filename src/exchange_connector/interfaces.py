"""Exchange Connector interfaces and data structures.

Defines the contract for exchange interactions following MVP requirements.
Implements standardized data formats for cross-exchange compatibility.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class OrderSide(Enum):
    """Order side enumeration."""

    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Order type enumeration."""

    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(Enum):
    """Order status enumeration."""

    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    CANCELED = "canceled"
    REJECTED = "rejected"


@dataclass
class ExchangeConfig:
    """Exchange configuration for connection setup."""

    exchange_name: str
    api_key: str
    api_secret: str
    api_passphrase: Optional[str] = None  # For exchanges like OKX
    sandbox: bool = True  # Always start in sandbox mode for safety
    rate_limit: int = 1200  # Default rate limit per minute
    timeout: int = 30  # Request timeout in seconds

    def to_ccxt_config(self) -> Dict[str, Any]:
        """Convert to ccxt exchange configuration."""
        config = {
            "apiKey": self.api_key,
            "secret": self.api_secret,
            "sandbox": self.sandbox,
            "rateLimit": self.rate_limit,
            "timeout": self.timeout * 1000,  # ccxt expects milliseconds
            "enableRateLimit": True,
            "options": {
                "defaultType": "spot",  # MVP focuses on spot trading
            },
        }

        if self.api_passphrase:
            config["password"] = self.api_passphrase

        return config


@dataclass
class MarketData:
    """Standardized market data structure."""

    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    @classmethod
    def from_ccxt_ohlcv(cls, symbol: str, ohlcv: List) -> "MarketData":
        """Create MarketData from ccxt OHLCV array."""
        return cls(
            symbol=symbol,
            timestamp=datetime.fromtimestamp(ohlcv[0] / 1000, tz=timezone.utc),
            open=Decimal(str(ohlcv[1])),
            high=Decimal(str(ohlcv[2])),
            low=Decimal(str(ohlcv[3])),
            close=Decimal(str(ohlcv[4])),
            volume=Decimal(str(ohlcv[5])),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for message passing."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "open": float(self.open),
            "high": float(self.high),
            "low": float(self.low),
            "close": float(self.close),
            "volume": float(self.volume),
        }


@dataclass
class OrderRequest:
    """Standardized order request structure."""

    symbol: str
    side: OrderSide
    type: OrderType
    amount: Decimal
    price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    client_order_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        """Validate order request."""
        if not self.symbol or not self.side or not self.type:
            return False

        if self.amount <= 0:
            return False

        if self.type == OrderType.LIMIT and not self.price:
            return False

        return True

    def to_ccxt_params(self) -> Dict[str, Any]:
        """Convert to ccxt order parameters."""
        params = {
            "symbol": self.symbol,
            "side": self.side.value,
            "type": self.type.value,
            "amount": float(self.amount),
        }

        if self.price:
            params["price"] = float(self.price)

        if self.client_order_id:
            params["clientOrderId"] = self.client_order_id

        return params


@dataclass
class OrderResponse:
    """Standardized order response structure."""

    order_id: str
    client_order_id: Optional[str]
    symbol: str
    side: OrderSide
    type: OrderType
    amount: Decimal
    filled: Decimal
    remaining: Decimal
    status: OrderStatus
    average_price: Optional[Decimal] = None
    cost: Optional[Decimal] = None
    fee: Optional[Decimal] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_ccxt_order(cls, ccxt_order: Dict[str, Any]) -> "OrderResponse":
        """Create OrderResponse from ccxt order data."""
        return cls(
            order_id=str(ccxt_order["id"]),
            client_order_id=ccxt_order.get("clientOrderId"),
            symbol=ccxt_order["symbol"],
            side=OrderSide(ccxt_order["side"]),
            type=OrderType(ccxt_order["type"]),
            amount=Decimal(str(ccxt_order["amount"])),
            filled=Decimal(str(ccxt_order.get("filled", 0))),
            remaining=Decimal(str(ccxt_order.get("remaining", 0))),
            status=OrderStatus(ccxt_order["status"]),
            average_price=(
                Decimal(str(ccxt_order["average"]))
                if ccxt_order.get("average")
                else None
            ),
            cost=Decimal(str(ccxt_order["cost"])) if ccxt_order.get("cost") else None,
            fee=(
                Decimal(str(ccxt_order["fee"]["cost"]))
                if ccxt_order.get("fee")
                else None
            ),
            timestamp=datetime.fromtimestamp(
                ccxt_order["timestamp"] / 1000, tz=timezone.utc
            ),
        )


@dataclass
class AccountBalance:
    """Account balance information."""

    currency: str
    free: Decimal
    used: Decimal
    total: Decimal

    @classmethod
    def from_ccxt_balance(
        cls, currency: str, balance_data: Dict[str, Any]
    ) -> "AccountBalance":
        """Create AccountBalance from ccxt balance data."""
        return cls(
            currency=currency,
            free=Decimal(str(balance_data.get("free", 0))),
            used=Decimal(str(balance_data.get("used", 0))),
            total=Decimal(str(balance_data.get("total", 0))),
        )


class IExchangeConnector(ABC):
    """Interface for exchange connector implementations.

    Defines the contract that all exchange connectors must implement.
    Follows MVP requirements for market data collection and order execution.
    """

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to exchange.

        Returns:
            bool: True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from exchange.

        Returns:
            bool: True if disconnection successful, False otherwise
        """
        pass

    @abstractmethod
    async def get_market_data(
        self, symbol: str, timeframe: str = "1m", limit: int = 100
    ) -> List[MarketData]:
        """Fetch historical market data.

        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Candle timeframe (e.g., '1m', '5m', '1h')
            limit: Number of candles to fetch

        Returns:
            List of MarketData objects
        """
        pass

    @abstractmethod
    async def subscribe_market_data(
        self, symbols: List[str], callback: Callable[[MarketData], None]
    ) -> bool:
        """Subscribe to real-time market data stream.

        Args:
            symbols: List of symbols to subscribe to
            callback: Function to call when new data arrives

        Returns:
            bool: True if subscription successful, False otherwise
        """
        pass

    @abstractmethod
    async def place_order(self, order_request: OrderRequest) -> OrderResponse:
        """Place a trading order.

        Args:
            order_request: Order details

        Returns:
            OrderResponse with execution details
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an existing order.

        Args:
            order_id: Exchange order ID
            symbol: Trading pair symbol

        Returns:
            bool: True if cancellation successful, False otherwise
        """
        pass

    @abstractmethod
    async def get_order_status(self, order_id: str, symbol: str) -> OrderResponse:
        """Get current order status.

        Args:
            order_id: Exchange order ID
            symbol: Trading pair symbol

        Returns:
            OrderResponse with current status
        """
        pass

    @abstractmethod
    async def get_account_balance(self) -> Dict[str, AccountBalance]:
        """Get account balance information.

        Returns:
            Dictionary mapping currency to AccountBalance
        """
        pass

    @abstractmethod
    async def get_open_orders(
        self, symbol: Optional[str] = None
    ) -> List[OrderResponse]:
        """Get list of open orders.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of open OrderResponse objects
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on exchange connection.

        Returns:
            Health status information
        """
        pass
