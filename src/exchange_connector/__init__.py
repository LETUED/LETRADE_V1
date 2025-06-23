"""Exchange Connector module for Letrade_v1 trading system.

This module provides a unified interface to interact with cryptocurrency exchanges,
handling authentication, rate limiting, order management, and data normalization.

Supports both Mock (testing) and CCXT (real exchange) implementations.
"""

# Legacy imports for backward compatibility
from .main import (
    Balance,
    BaseExchangeConnector,
    ExchangeConnector,
    MarketData,
    MockExchangeConnector,
    Order,
    OrderRequest,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    CCXTExchangeConnector,
    create_exchange_connector,
    HAS_CCXT
)

# New interface-based imports
from .interfaces import (
    IExchangeConnector,
    ExchangeConfig, 
    MarketData as NewMarketData,
    OrderRequest as NewOrderRequest,
    OrderResponse,
    AccountBalance,
    OrderSide as NewOrderSide,
    OrderType as NewOrderType, 
    OrderStatus as NewOrderStatus
)

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
]
