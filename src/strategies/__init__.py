"""Strategies module for Letrade_v1 trading system.

This module contains the BaseStrategy interface and all trading strategy
implementations. All strategies must inherit from BaseStrategy and implement
the required methods.
"""

from .base_strategy import (
    BaseStrategy,
    SignalType,
    StrategyConfig,
    TradingSignal,
    calculate_bollinger_bands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_sma,
)

__version__ = "0.1.0"
__author__ = "Letrade Team"

__all__ = [
    "BaseStrategy",
    "TradingSignal",
    "SignalType",
    "StrategyConfig",
    "calculate_sma",
    "calculate_ema",
    "calculate_rsi",
    "calculate_bollinger_bands",
    "calculate_macd",
]
