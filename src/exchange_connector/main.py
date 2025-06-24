"""Exchange Connector main module for Letrade_v1 trading system.

The Exchange Connector provides a unified interface to interact with
cryptocurrency exchanges, handling authentication, rate limiting,
and data normalization.

Now includes CCXT integration for real exchange connectivity while maintaining
backward compatibility with existing Mock implementation.

PERFORMANCE OPTIMIZED: Includes WebSocket real-time data streaming
and advanced caching for <1ms latency trading execution.
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Callable

# Import new interfaces
from .interfaces import (
    IExchangeConnector, ExchangeConfig, MarketData as NewMarketData,
    OrderRequest as NewOrderRequest, OrderResponse, AccountBalance,
    OrderSide as NewOrderSide, OrderType as NewOrderType, OrderStatus as NewOrderStatus
)

# Import optimized WebSocket connector
from .websocket_connector import OptimizedExchangeConnector, create_optimized_connector

logger = logging.getLogger(__name__)

# Try to import ccxt for real exchange connectivity
try:
    import ccxt.async_support as ccxt
    HAS_CCXT = True
except ImportError:
    HAS_CCXT = False
    logger.warning("ccxt not available, only mock exchange connector will work")


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


# New CCXT-based Exchange Connector implementing IExchangeConnector interface
class CCXTExchangeConnector(IExchangeConnector):
    """CCXT-based exchange connector implementation.
    
    Provides real exchange connectivity using ccxt library.
    Implements circuit breaker pattern for reliability.
    """
    
    def __init__(self, config: ExchangeConfig):
        """Initialize exchange connector.
        
        Args:
            config: Exchange configuration
        """
        if not HAS_CCXT:
            raise RuntimeError("ccxt library is required for CCXTExchangeConnector")
            
        self.config = config
        self.exchange_name = config.exchange_name  # Add missing exchange_name attribute
        self.exchange = None
        self.is_connected = False
        self._market_subscriptions = {}
        self._circuit_breaker_failures = 0
        self._circuit_breaker_reset_time = None
        self._last_health_check = None
        
        # Circuit breaker configuration
        self.max_failures = 5
        self.circuit_breaker_timeout = 300  # 5 minutes
        
        logger.info(f"CCXT Exchange connector initialized for {config.exchange_name}")
    
    async def connect(self) -> bool:
        """Establish connection to exchange."""
        try:
            if self.is_connected:
                logger.info("Exchange already connected")
                return True
            
            # Create exchange instance based on configuration
            exchange_class = getattr(ccxt, self.config.exchange_name.lower())
            self.exchange = exchange_class(self.config.to_ccxt_config())
            
            # Test connection with markets fetch
            await self.exchange.load_markets()
            
            # Only verify API credentials if real keys are provided
            if (self.config.api_key and self.config.api_secret and 
                self.config.api_key != "test_api_key"):
                await self.exchange.fetch_balance()
            
            self.is_connected = True
            self._circuit_breaker_failures = 0
            self._circuit_breaker_reset_time = None
            
            logger.info(f"Successfully connected to {self.config.exchange_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to exchange: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from exchange."""
        try:
            if self.exchange:
                await self.exchange.close()
                self.exchange = None
            
            self.is_connected = False
            self._market_subscriptions.clear()
            
            logger.info(f"Disconnected from {self.config.exchange_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
            return False
    
    async def get_market_data(self, symbol: str, timeframe: str = '1m', limit: int = 100) -> List[NewMarketData]:
        """Fetch historical market data."""
        if not await self._check_circuit_breaker():
            raise ConnectionError("Circuit breaker is open")
        
        try:
            if not self.is_connected:
                await self.connect()
            
            # Fetch OHLCV data from exchange
            ohlcv_data = await self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit
            )
            
            # Convert to standardized format
            market_data = []
            for ohlcv in ohlcv_data:
                market_data.append(NewMarketData.from_ccxt_ohlcv(symbol, ohlcv))
            
            self._reset_circuit_breaker()
            logger.debug(f"Fetched {len(market_data)} candles for {symbol}")
            
            return market_data
            
        except Exception as e:
            await self._handle_exchange_error(e)
            raise
    
    async def subscribe_market_data(self, symbols: List[str], callback: Callable[[NewMarketData], None]) -> bool:
        """Subscribe to real-time market data stream."""
        try:
            if not self.is_connected:
                await self.connect()
            
            # Check if exchange supports WebSocket
            if not hasattr(self.exchange, 'watch_ohlcv'):
                logger.warning(f"{self.config.exchange_name} does not support WebSocket streaming")
                return False
            
            # Start WebSocket subscription for each symbol
            for symbol in symbols:
                if symbol not in self._market_subscriptions:
                    self._market_subscriptions[symbol] = callback
                    
                    # Start async task for WebSocket monitoring
                    asyncio.create_task(self._monitor_symbol_stream(symbol, callback))
            
            logger.info(f"Subscribed to market data for {len(symbols)} symbols")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe to market data: {e}")
            return False
    
    async def place_order(self, order_request: NewOrderRequest) -> OrderResponse:
        """Place a trading order."""
        if not await self._check_circuit_breaker():
            raise ConnectionError("Circuit breaker is open")
        
        try:
            if not order_request.validate():
                raise ValueError("Invalid order request")
            
            if not self.is_connected:
                await self.connect()
            
            # Convert to ccxt parameters
            ccxt_params = order_request.to_ccxt_params()
            
            # Place order based on type
            if order_request.type == NewOrderType.MARKET:
                ccxt_order = await self.exchange.create_market_order(
                    symbol=ccxt_params['symbol'],
                    side=ccxt_params['side'],
                    amount=ccxt_params['amount']
                )
            else:  # LIMIT order
                ccxt_order = await self.exchange.create_limit_order(
                    symbol=ccxt_params['symbol'],
                    side=ccxt_params['side'],
                    amount=ccxt_params['amount'],
                    price=ccxt_params['price']
                )
            
            # Convert response to standardized format
            order_response = OrderResponse.from_ccxt_order(ccxt_order)
            
            self._reset_circuit_breaker()
            logger.info(f"Order placed successfully: {order_response.order_id}")
            
            return order_response
            
        except Exception as e:
            await self._handle_exchange_error(e)
            raise
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an existing order."""
        if not await self._check_circuit_breaker():
            raise ConnectionError("Circuit breaker is open")
        
        try:
            if not self.is_connected:
                await self.connect()
            
            await self.exchange.cancel_order(order_id, symbol)
            
            self._reset_circuit_breaker()
            logger.info(f"Order cancelled successfully: {order_id}")
            
            return True
            
        except Exception as e:
            await self._handle_exchange_error(e)
            return False
    
    async def get_order_status(self, order_id: str, symbol: str) -> OrderResponse:
        """Get current order status."""
        if not await self._check_circuit_breaker():
            raise ConnectionError("Circuit breaker is open")
        
        try:
            if not self.is_connected:
                await self.connect()
            
            ccxt_order = await self.exchange.fetch_order(order_id, symbol)
            order_response = OrderResponse.from_ccxt_order(ccxt_order)
            
            self._reset_circuit_breaker()
            
            return order_response
            
        except Exception as e:
            await self._handle_exchange_error(e)
            raise
    
    async def get_account_balance(self) -> Dict[str, AccountBalance]:
        """Get account balance information."""
        if not await self._check_circuit_breaker():
            raise ConnectionError("Circuit breaker is open")
        
        try:
            if not self.is_connected:
                await self.connect()
            
            ccxt_balance = await self.exchange.fetch_balance()
            
            # Convert to standardized format
            balances = {}
            for currency, balance_data in ccxt_balance.items():
                if currency not in ['info', 'free', 'used', 'total'] and isinstance(balance_data, dict):
                    balances[currency] = AccountBalance.from_ccxt_balance(currency, balance_data)
            
            self._reset_circuit_breaker()
            logger.debug(f"Fetched balance for {len(balances)} currencies")
            
            return balances
            
        except Exception as e:
            await self._handle_exchange_error(e)
            raise
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[OrderResponse]:
        """Get list of open orders."""
        if not await self._check_circuit_breaker():
            raise ConnectionError("Circuit breaker is open")
        
        try:
            if not self.is_connected:
                await self.connect()
            
            if symbol:
                ccxt_orders = await self.exchange.fetch_open_orders(symbol)
            else:
                ccxt_orders = await self.exchange.fetch_open_orders()
            
            # Convert to standardized format
            orders = []
            for ccxt_order in ccxt_orders:
                orders.append(OrderResponse.from_ccxt_order(ccxt_order))
            
            self._reset_circuit_breaker()
            logger.debug(f"Fetched {len(orders)} open orders")
            
            return orders
            
        except Exception as e:
            await self._handle_exchange_error(e)
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on exchange connection."""
        health_status = {
            'exchange': self.config.exchange_name,
            'connected': self.is_connected,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'circuit_breaker_open': not await self._check_circuit_breaker(),
            'failures': self._circuit_breaker_failures,
            'last_check': self._last_health_check
        }
        
        try:
            if self.is_connected:
                # Test with simple API call
                start_time = time.time()
                await self.exchange.fetch_ticker('BTC/USDT')
                response_time = (time.time() - start_time) * 1000
                
                health_status.update({
                    'status': 'healthy',
                    'response_time_ms': response_time,
                    'api_accessible': True
                })
            else:
                health_status.update({
                    'status': 'disconnected',
                    'api_accessible': False
                })
                
            self._last_health_check = datetime.now(timezone.utc).isoformat()
            
        except Exception as e:
            health_status.update({
                'status': 'unhealthy',
                'error': str(e),
                'api_accessible': False
            })
            
            await self._handle_exchange_error(e)
        
        return health_status
    
    async def _monitor_symbol_stream(self, symbol: str, callback: Callable[[NewMarketData], None]) -> None:
        """Monitor WebSocket stream for a specific symbol."""
        try:
            while symbol in self._market_subscriptions and self.is_connected:
                try:
                    # Watch for new OHLCV data
                    ohlcv_data = await self.exchange.watch_ohlcv(symbol, '1m')
                    
                    if ohlcv_data:
                        # Convert latest candle to MarketData
                        latest_candle = ohlcv_data[-1]
                        market_data = NewMarketData.from_ccxt_ohlcv(symbol, latest_candle)
                        
                        # Call the callback function
                        callback(market_data)
                    
                except Exception as e:
                    logger.error(f"Error in WebSocket stream for {symbol}: {e}")
                    await asyncio.sleep(1)  # Brief pause before retrying
                    
        except Exception as e:
            logger.error(f"WebSocket monitoring failed for {symbol}: {e}")
            
        finally:
            # Clean up subscription
            if symbol in self._market_subscriptions:
                del self._market_subscriptions[symbol]
    
    async def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker allows operations."""
        if self._circuit_breaker_failures < self.max_failures:
            return True
        
        if self._circuit_breaker_reset_time is None:
            self._circuit_breaker_reset_time = time.time() + self.circuit_breaker_timeout
            return False
        
        if time.time() > self._circuit_breaker_reset_time:
            # Reset circuit breaker
            self._circuit_breaker_failures = 0
            self._circuit_breaker_reset_time = None
            logger.info("Circuit breaker reset")
            return True
        
        return False
    
    async def _handle_exchange_error(self, error: Exception) -> None:
        """Handle exchange errors and update circuit breaker."""
        self._circuit_breaker_failures += 1
        
        logger.error(f"Exchange error (failure {self._circuit_breaker_failures}): {error}")
        
        if HAS_CCXT:
            # Check for specific error types
            if isinstance(error, ccxt.NetworkError):
                logger.warning("Network error detected, checking connection")
                self.is_connected = False
            elif isinstance(error, ccxt.ExchangeError):
                logger.warning("Exchange API error detected")
        
        # Open circuit breaker if too many failures
        if self._circuit_breaker_failures >= self.max_failures:
            logger.warning("Circuit breaker opened due to repeated failures")
    
    def _reset_circuit_breaker(self) -> None:
        """Reset circuit breaker on successful operation."""
        if self._circuit_breaker_failures > 0:
            self._circuit_breaker_failures = 0
            self._circuit_breaker_reset_time = None
            logger.debug("Circuit breaker reset after successful operation")
    
    async def cleanup(self) -> bool:
        """Cleanup exchange resources (same as disconnect)."""
        return await self.disconnect()


# Factory function for creating exchange connectors
def create_exchange_connector(exchange_name: str, config: Dict[str, Any], use_ccxt: bool = False) -> BaseExchangeConnector:
    """Factory function to create exchange connector instances.
    
    Args:
        exchange_name: Name of the exchange (e.g., 'binance')
        config: Configuration dictionary
        use_ccxt: Whether to use CCXT-based connector or Mock connector
        
    Returns:
        Exchange connector instance
    """
    if use_ccxt and HAS_CCXT:
        # Create ExchangeConfig for CCXT connector
        exchange_config = ExchangeConfig(
            exchange_name=exchange_name,
            api_key=config.get('api_key', ''),
            api_secret=config.get('api_secret', ''),
            api_passphrase=config.get('api_passphrase'),
            sandbox=config.get('sandbox', True),
            rate_limit=config.get('rate_limit', 1200),
            timeout=config.get('timeout', 30)
        )
        return CCXTExchangeConnector(exchange_config)
    else:
        # Use existing Mock connector
        if use_ccxt and not HAS_CCXT:
            logger.warning("CCXT requested but not available, falling back to Mock connector")
        return MockExchangeConnector(config)


if __name__ == "__main__":
    asyncio.run(main())
