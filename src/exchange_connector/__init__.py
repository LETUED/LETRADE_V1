"""Exchange Connector module for Letrade_v1 trading system.

This module provides a unified interface to interact with cryptocurrency exchanges,
handling authentication, rate limiting, order management, and data normalization.
"""

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
)

__version__ = "0.1.0"
__author__ = "Letrade Team"

__all__ = [
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
]
