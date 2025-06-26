"""Exchange Connector module for Letrade_v1 trading system.

This module provides a unified interface to interact with cryptocurrency exchanges,
handling authentication, rate limiting, order management, and data normalization.

Supports both Mock (testing) and CCXT (real exchange) implementations.
"""

# New interface-based imports
from .interfaces import AccountBalance, ExchangeConfig, IExchangeConnector
from .interfaces import MarketData as NewMarketData
from .interfaces import OrderRequest as NewOrderRequest
from .interfaces import OrderResponse
from .interfaces import OrderSide as NewOrderSide
from .interfaces import OrderStatus as NewOrderStatus
from .interfaces import OrderType as NewOrderType

# Legacy imports for backward compatibility
from .main import (
    HAS_CCXT,
    Balance,
    BaseExchangeConnector,
    CCXTExchangeConnector,
    ExchangeConnector,
    MarketData,
    MockExchangeConnector,
    Order,
    OrderRequest,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    create_exchange_connector,
)

# Performance optimized WebSocket connector
from .websocket_connector import OptimizedExchangeConnector, create_optimized_connector

__version__ = "0.1.0"
__author__ = "Letrade Team"

__all__ = [
    # Legacy exports (for backward compatibility)
    "ExchangeConnector",
    "BaseExchangeConnector",
    "MockExchangeConnector",
    "OrderRequest",
    "Order",
    "Balance",
    "Position",
    "MarketData",
    "OrderType",
    "OrderSide",
    "OrderStatus",
    # New exports
    "CCXTExchangeConnector",
    "create_exchange_connector",
    "HAS_CCXT",
    # Interface exports
    "IExchangeConnector",
    "ExchangeConfig",
    "NewMarketData",
    "NewOrderRequest",
    "OrderResponse",
    "AccountBalance",
    "NewOrderSide",
    "NewOrderType",
    "NewOrderStatus",
    # Performance optimized exports
    "OptimizedExchangeConnector",
    "create_optimized_connector",
]
