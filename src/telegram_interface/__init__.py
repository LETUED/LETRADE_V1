"""Telegram Interface module for Letrade_v1 trading system.

This module provides Telegram bot functionality for remote control and monitoring
of the cryptocurrency trading system. Implements user authentication, command
processing, and real-time notifications.

Key Features:
- User authentication with whitelist-based security
- System status and portfolio monitoring commands
- Real-time trading notifications and alerts
- Integration with Core Engine via message bus
"""

from .auth import AuthManager
from .commands import CommandHandler
from .main import TelegramBot
from .message_integration import TelegramMessageIntegration
from .notifications import NotificationManager

__version__ = "0.1.0"
__author__ = "Letrade Team"

__all__ = [
    "TelegramBot",
    "AuthManager",
    "CommandHandler",
    "NotificationManager",
    "TelegramMessageIntegration",
]
