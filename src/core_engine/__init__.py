"""Core Engine module for Letrade_v1 trading system.

The Core Engine serves as the central orchestrator for the entire trading system,
managing component lifecycle, coordinating strategy execution, and ensuring
system-wide consistency and safety.
"""

from .main import CoreEngine, SystemStatus

__version__ = "0.1.0"
__author__ = "Letrade Team"

__all__ = ["CoreEngine", "SystemStatus"]
