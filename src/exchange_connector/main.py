"""Exchange Connector main module for Letrade_v1 trading system.

The Exchange Connector provides a unified interface to interact with
cryptocurrency exchanges, handling authentication, rate limiting,
and data normalization.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order types supported by the system."""

    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class OrderSide(Enum):
    """Order sides."""

    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Order status."""

    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class OrderRequest:
    """Order request data structure."""

    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "GTC"  # Good Till Cancelled
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "quantity": self.quantity,
            "price": self.price,
            "stop_price": self.stop_price,
            "time_in_force": self.time_in_force,
            "metadata": self.metadata,
        }


@dataclass
class Order:
    """Order data structure."""

    id: str
    client_order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    filled_quantity: float
    remaining_quantity: float
    price: Optional[float]
    average_price: Optional[float]
    status: OrderStatus
    timestamp: datetime
    update_time: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "client_order_id": self.client_order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "quantity": self.quantity,
            "filled_quantity": self.filled_quantity,
            "remaining_quantity": self.remaining_quantity,
            "price": self.price,
            "average_price": self.average_price,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "update_time": self.update_time.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class Balance:
    """Account balance data structure."""

    asset: str
    free: float
    locked: float
    total: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "asset": self.asset,
            "free": self.free,
            "locked": self.locked,
            "total": self.total,
        }


@dataclass
class Position:
    """Position data structure."""

    symbol: str
    side: str  # "long" or "short"
    size: float
    entry_price: float
    mark_price: float
    unrealized_pnl: float
    percentage: float
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "symbol": self.symbol,
            "side": self.side,
            "size": self.size,
            "entry_price": self.entry_price,
            "mark_price": self.mark_price,
            "unrealized_pnl": self.unrealized_pnl,
            "percentage": self.percentage,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class MarketData:
    """Market data structure."""

    symbol: str
    price: float
    bid: float
    ask: float
    volume_24h: float
    change_24h: float
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "symbol": self.symbol,
            "price": self.price,
            "bid": self.bid,
            "ask": self.ask,
            "volume_24h": self.volume_24h,
            "change_24h": self.change_24h,
            "timestamp": self.timestamp.isoformat(),
        }


class BaseExchangeConnector(ABC):
    """Abstract base class for exchange connectors."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the exchange connector.

        Args:
            config: Exchange configuration
        """
        self.config = config
        self.exchange_name = config.get("name", "unknown")
        self.is_connected = False
        self.dry_run = config.get("dry_run", True)  # Default to dry-run for safety

        # Rate limiting
        self._rate_limiter = None
        self._last_request_time = {}

        logger.info(
            "Exchange connector initialized",
            extra={"exchange": self.exchange_name, "dry_run": self.dry_run},
        )

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the exchange.

        Returns:
            True if connected successfully, False otherwise
        """
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the exchange.

        Returns:
            True if disconnected successfully, False otherwise
        """
        pass

    @abstractmethod
    async def get_account_balance(self) -> Dict[str, Balance]:
        """Get account balance for all assets.

        Returns:
            Dictionary mapping asset names to Balance objects
        """
        pass

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get open positions.

        Returns:
            List of Position objects
        """
        pass

    @abstractmethod
    async def place_order(self, order_request: OrderRequest) -> Order:
        """Place a new order.

        Args:
            order_request: Order details

        Returns:
            Order object with exchange-assigned ID
        """
        pass

    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an existing order.

        Args:
            symbol: Trading symbol
            order_id: Order ID to cancel

        Returns:
            True if cancelled successfully, False otherwise
        """
        pass

    @abstractmethod
    async def get_order_status(self, symbol: str, order_id: str) -> Order:
        """Get status of an existing order.

        Args:
            symbol: Trading symbol
            order_id: Order ID

        Returns:
            Order object with current status
        """
        pass

    @abstractmethod
    async def get_market_data(self, symbol: str) -> MarketData:
        """Get current market data for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            MarketData object
        """
        pass

    @abstractmethod
    async def get_order_book(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """Get order book for a symbol.

        Args:
            symbol: Trading symbol
            limit: Number of price levels to return

        Returns:
            Order book data
        """
        pass

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check.

        Returns:
            Health status dictionary
        """
        try:
            # Test connection
            test_symbol = self.config.get("test_symbol", "BTCUSDT")
            market_data = await self.get_market_data(test_symbol)

            return {
                "exchange": self.exchange_name,
                "connected": self.is_connected,
                "healthy": True,
                "timestamp": datetime.utcnow().isoformat(),
                "test_market_data": market_data.to_dict() if market_data else None,
            }

        except Exception as e:
            logger.error(
                f"Health check failed for {self.exchange_name}",
                extra={"exchange": self.exchange_name, "error": str(e)},
            )
            return {
                "exchange": self.exchange_name,
                "connected": self.is_connected,
                "healthy": False,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
            }


class MockExchangeConnector(BaseExchangeConnector):
    """Mock exchange connector for testing and dry-run mode."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._mock_balances = {
            "USDT": Balance("USDT", 10000.0, 0.0, 10000.0),
            "BTC": Balance("BTC", 0.0, 0.0, 0.0),
            "ETH": Balance("ETH", 0.0, 0.0, 0.0),
        }
        self._mock_orders = {}
        self._order_counter = 1000

    async def connect(self) -> bool:
        """Connect to mock exchange."""
        logger.info(
            "Connecting to mock exchange", extra={"exchange": self.exchange_name}
        )
        await asyncio.sleep(0.1)  # Simulate connection delay
        self.is_connected = True
        return True

    async def disconnect(self) -> bool:
        """Disconnect from mock exchange."""
        logger.info(
            "Disconnecting from mock exchange", extra={"exchange": self.exchange_name}
        )
        self.is_connected = False
        return True

    async def get_account_balance(self) -> Dict[str, Balance]:
        """Get mock account balance."""
        if not self.is_connected:
            raise Exception("Not connected to exchange")

        return dict(self._mock_balances)

    async def get_positions(self) -> List[Position]:
        """Get mock positions."""
        if not self.is_connected:
            raise Exception("Not connected to exchange")

        # Return empty positions for now
        return []

    async def place_order(self, order_request: OrderRequest) -> Order:
        """Place a mock order."""
        if not self.is_connected:
            raise Exception("Not connected to exchange")

        if self.dry_run:
            logger.info(
                "DRY RUN: Would place order",
                extra={
                    "exchange": self.exchange_name,
                    "order": order_request.to_dict(),
                },
            )

        # Create mock order
        order_id = f"mock_{self._order_counter}"
        self._order_counter += 1

        order = Order(
            id=order_id,
            client_order_id=f"client_{order_id}",
            symbol=order_request.symbol,
            side=order_request.side,
            order_type=order_request.order_type,
            quantity=order_request.quantity,
            filled_quantity=0.0,
            remaining_quantity=order_request.quantity,
            price=order_request.price,
            average_price=None,
            status=OrderStatus.OPEN,
            timestamp=datetime.utcnow(),
            update_time=datetime.utcnow(),
            metadata=order_request.metadata,
        )

        self._mock_orders[order_id] = order

        logger.info(
            "Mock order placed",
            extra={
                "exchange": self.exchange_name,
                "order_id": order_id,
                "dry_run": self.dry_run,
            },
        )

        return order

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel a mock order."""
        if not self.is_connected:
            raise Exception("Not connected to exchange")

        if order_id in self._mock_orders:
            self._mock_orders[order_id].status = OrderStatus.CANCELLED
            self._mock_orders[order_id].update_time = datetime.utcnow()

            if self.dry_run:
                logger.info(
                    "DRY RUN: Would cancel order",
                    extra={"exchange": self.exchange_name, "order_id": order_id},
                )

            return True

        return False

    async def get_order_status(self, symbol: str, order_id: str) -> Order:
        """Get mock order status."""
        if not self.is_connected:
            raise Exception("Not connected to exchange")

        if order_id not in self._mock_orders:
            raise Exception(f"Order {order_id} not found")

        return self._mock_orders[order_id]

    async def get_market_data(self, symbol: str) -> MarketData:
        """Get mock market data."""
        if not self.is_connected:
            raise Exception("Not connected to exchange")

        # Return mock market data
        mock_prices = {"BTCUSDT": 50000.0, "ETHUSDT": 3000.0, "ADAUSDT": 1.5}

        base_price = mock_prices.get(symbol, 100.0)

        return MarketData(
            symbol=symbol,
            price=base_price,
            bid=base_price * 0.999,
            ask=base_price * 1.001,
            volume_24h=1000000.0,
            change_24h=2.5,
            timestamp=datetime.utcnow(),
        )

    async def get_order_book(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """Get mock order book."""
        if not self.is_connected:
            raise Exception("Not connected to exchange")

        market_data = await self.get_market_data(symbol)

        # Generate mock order book
        bids = []
        asks = []

        for i in range(min(limit, 10)):
            bid_price = market_data.bid - (i * 0.01)
            ask_price = market_data.ask + (i * 0.01)

            bids.append([bid_price, 10.0])  # [price, quantity]
            asks.append([ask_price, 10.0])

        return {
            "symbol": symbol,
            "bids": bids,
            "asks": asks,
            "timestamp": datetime.utcnow().isoformat(),
        }


class ExchangeConnector:
    """Main exchange connector that manages multiple exchange connections."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the exchange connector manager.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.connectors: Dict[str, BaseExchangeConnector] = {}
        self.default_exchange = config.get("default_exchange", "mock")

        logger.info(
            "Exchange connector manager initialized",
            extra={"default_exchange": self.default_exchange},
        )

    async def start(self) -> bool:
        """Start all exchange connectors.

        Returns:
            True if all connectors started successfully
        """
        try:
            # Initialize configured exchanges
            exchanges_config = self.config.get("exchanges", {})

            for exchange_name, exchange_config in exchanges_config.items():
                if exchange_name == "mock" or exchange_config.get("type") == "mock":
                    connector = MockExchangeConnector(exchange_config)
                else:
                    # TODO: Add real exchange connectors (Binance, Coinbase, etc.)
                    logger.warning(
                        f"Real exchange {exchange_name} not implemented, using mock",
                        extra={"exchange": exchange_name},
                    )
                    connector = MockExchangeConnector(exchange_config)

                if await connector.connect():
                    self.connectors[exchange_name] = connector
                    logger.info(
                        f"Exchange {exchange_name} connected",
                        extra={"exchange": exchange_name},
                    )
                else:
                    logger.error(
                        f"Failed to connect to {exchange_name}",
                        extra={"exchange": exchange_name},
                    )
                    return False

            # If no exchanges configured, create default mock
            if not self.connectors:
                mock_config = {"name": "mock", "dry_run": True}
                mock_connector = MockExchangeConnector(mock_config)
                if await mock_connector.connect():
                    self.connectors["mock"] = mock_connector
                    logger.info("Default mock exchange connected")
                else:
                    logger.error("Failed to connect to default mock exchange")
                    return False

            logger.info(
                "Exchange connector manager started",
                extra={"exchanges": list(self.connectors.keys())},
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to start exchange connector manager", extra={"error": str(e)}
            )
            return False

    async def stop(self) -> bool:
        """Stop all exchange connectors.

        Returns:
            True if all connectors stopped successfully
        """
        try:
            for exchange_name, connector in self.connectors.items():
                await connector.disconnect()
                logger.info(
                    f"Exchange {exchange_name} disconnected",
                    extra={"exchange": exchange_name},
                )

            self.connectors.clear()
            logger.info("Exchange connector manager stopped")

            return True

        except Exception as e:
            logger.error(
                "Failed to stop exchange connector manager", extra={"error": str(e)}
            )
            return False

    def get_connector(
        self, exchange_name: Optional[str] = None
    ) -> BaseExchangeConnector:
        """Get exchange connector by name.

        Args:
            exchange_name: Name of exchange, uses default if None

        Returns:
            Exchange connector instance
        """
        exchange_name = exchange_name or self.default_exchange

        if exchange_name not in self.connectors:
            raise ValueError(f"Exchange {exchange_name} not available")

        return self.connectors[exchange_name]

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all connectors.

        Returns:
            Health status for all exchanges
        """
        health_results = {"timestamp": datetime.utcnow().isoformat(), "exchanges": {}}

        for exchange_name, connector in self.connectors.items():
            health_results["exchanges"][exchange_name] = await connector.health_check()

        return health_results


async def main():
    """Main entry point for testing Exchange Connector."""
    logging.basicConfig(level=logging.INFO)

    # Test configuration
    config = {
        "default_exchange": "mock",
        "exchanges": {"mock": {"name": "mock", "type": "mock", "dry_run": True}},
    }

    # Create and test Exchange Connector
    connector_manager = ExchangeConnector(config)

    try:
        if await connector_manager.start():
            logger.info("Exchange Connector Manager started successfully")

            # Test basic functionality
            connector = connector_manager.get_connector()

            # Test market data
            market_data = await connector.get_market_data("BTCUSDT")
            logger.info(f"Market data: {market_data.to_dict()}")

            # Test health check
            health = await connector_manager.health_check()
            logger.info(f"Health check: {json.dumps(health, indent=2)}")

        else:
            logger.error("Failed to start Exchange Connector Manager")

    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await connector_manager.stop()


if __name__ == "__main__":
    asyncio.run(main())
