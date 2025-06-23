"""Capital Manager module for Letrade_v1 trading system.

This module handles risk management, position sizing, capital allocation,
and trade validation to ensure all trades comply with risk parameters.
"""

from .main import (
    CapitalManager,
    PortfolioMetrics,
    RiskLevel,
    RiskParameters,
    TradeRequest,
    ValidationResponse,
    ValidationResult,
)

__version__ = "0.1.0"
__author__ = "Letrade Team"

__all__ = [
    "CapitalManager",
    "RiskParameters",
    "TradeRequest",
    "ValidationResponse",
    "PortfolioMetrics",
    "RiskLevel",
    "ValidationResult",
]
