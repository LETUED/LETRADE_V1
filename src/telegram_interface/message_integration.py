"""Message Bus Integration for Telegram Interface.

Implements RabbitMQ message bus integration for Telegram bot.
Handles incoming responses from Core Engine and manages subscription lifecycle.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from common.message_bus import MessageBus

from .commands import CommandHandler
from .notifications import NotificationManager

logger = logging.getLogger(__name__)


class TelegramMessageIntegration:
    """Manages message bus integration for Telegram Interface.

    Handles bidirectional communication with Core Engine:
    - Outgoing: Command requests from Telegram users
    - Incoming: Responses and notifications for users
    """

    def __init__(
        self, command_handler: CommandHandler, notification_manager: NotificationManager
    ):
        """Initialize message integration.

        Args:
            command_handler: Command handler instance
            notification_manager: Notification manager instance
        """
        self.command_handler = command_handler
        self.notification_manager = notification_manager
        self.message_bus: Optional[MessageBus] = None
        self.bot_instance = None
        self.is_connected = False

        # Response routing configuration
        self.response_handlers = {
            "response.system.status": self._handle_status_response,
            "response.portfolio.status": self._handle_portfolio_response,
            "response.positions.status": self._handle_positions_response,
            "response.strategies.status": self._handle_strategies_response,
            "response.strategy.control": self._handle_strategy_control_response,
            "response.profit.analysis": self._handle_profit_response,
        }

        # Notification event handlers (already configured in notification_manager)
        self.notification_subscriptions = [
            "events.trade_executed",
            "events.trade_failed",
            "events.strategy_started",
            "events.strategy_stopped",
            "events.system_alert",
            "events.performance_update",
            "events.error",
            "events.portfolio_update",
        ]

        logger.info("Telegram message integration initialized")

    async def connect(self, message_bus: MessageBus, bot_instance=None) -> bool:
        """Connect to message bus and set up subscriptions.

        Args:
            message_bus: MessageBus instance
            bot_instance: Telegram bot instance

        Returns:
            bool: True if connection successful
        """
        try:
            if self.is_connected:
                logger.info("Message integration already connected")
                return True

            self.message_bus = message_bus
            self.bot_instance = bot_instance

            # Subscribe to response channels
            await self._setup_response_subscriptions()

            # Subscribe to notification events (handled by notification_manager)
            await self._setup_notification_subscriptions()

            self.is_connected = True
            logger.info("Telegram message integration connected successfully")

            return True

        except Exception as e:
            logger.error(f"Failed to connect message integration: {e}")
            return False

    async def disconnect(self) -> bool:
        """Disconnect from message bus.

        Returns:
            bool: True if disconnection successful
        """
        try:
            self.is_connected = False
            self.message_bus = None

            logger.info("Telegram message integration disconnected")
            return True

        except Exception as e:
            logger.error(f"Error disconnecting message integration: {e}")
            return False

    async def _setup_response_subscriptions(self) -> None:
        """Set up subscriptions for Core Engine responses."""
        for routing_key, handler in self.response_handlers.items():
            try:
                await self.message_bus.subscribe(routing_key, handler)
                logger.debug(f"Subscribed to response channel: {routing_key}")
            except Exception as e:
                logger.error(f"Failed to subscribe to {routing_key}: {e}")

        logger.info(f"Set up {len(self.response_handlers)} response subscriptions")

    async def _setup_notification_subscriptions(self) -> None:
        """Set up subscriptions for notification events."""
        # Notification subscriptions are handled by NotificationManager
        # We just need to ensure the notification manager is connected
        if hasattr(self.notification_manager, "message_bus"):
            logger.info(
                "Notification subscriptions already configured in NotificationManager"
            )
        else:
            logger.warning(
                "NotificationManager not properly configured with message bus"
            )

    async def _handle_status_response(self, message: Dict[str, Any]) -> None:
        """Handle system status response from Core Engine."""
        try:
            logger.debug(f"Received status response: {message.get('request_id')}")

            # Forward to command handler for processing and user response
            await self.command_handler.process_response(message, self.bot_instance)

        except Exception as e:
            logger.error(f"Error handling status response: {e}")

    async def _handle_portfolio_response(self, message: Dict[str, Any]) -> None:
        """Handle portfolio status response from Core Engine."""
        try:
            logger.debug(f"Received portfolio response: {message.get('request_id')}")

            # Forward to command handler
            await self.command_handler.process_response(message, self.bot_instance)

        except Exception as e:
            logger.error(f"Error handling portfolio response: {e}")

    async def _handle_positions_response(self, message: Dict[str, Any]) -> None:
        """Handle positions status response from Core Engine."""
        try:
            logger.debug(f"Received positions response: {message.get('request_id')}")

            # Forward to command handler
            await self.command_handler.process_response(message, self.bot_instance)

        except Exception as e:
            logger.error(f"Error handling positions response: {e}")

    async def _handle_strategies_response(self, message: Dict[str, Any]) -> None:
        """Handle strategies status response from Core Engine."""
        try:
            logger.debug(f"Received strategies response: {message.get('request_id')}")

            # Forward to command handler
            await self.command_handler.process_response(message, self.bot_instance)

        except Exception as e:
            logger.error(f"Error handling strategies response: {e}")

    async def _handle_strategy_control_response(self, message: Dict[str, Any]) -> None:
        """Handle strategy start/stop response from Core Engine."""
        try:
            logger.debug(
                f"Received strategy control response: {message.get('request_id')}"
            )

            # Forward to command handler
            await self.command_handler.process_response(message, self.bot_instance)

        except Exception as e:
            logger.error(f"Error handling strategy control response: {e}")

    async def _handle_profit_response(self, message: Dict[str, Any]) -> None:
        """Handle profit analysis response from Core Engine."""
        try:
            logger.debug(f"Received profit response: {message.get('request_id')}")

            # Forward to command handler
            await self.command_handler.process_response(message, self.bot_instance)

        except Exception as e:
            logger.error(f"Error handling profit response: {e}")

    async def send_command(
        self, routing_key: str, command_data: Dict[str, Any]
    ) -> bool:
        """Send command to Core Engine via message bus.

        Args:
            routing_key: Message routing key
            command_data: Command data to send

        Returns:
            bool: True if sent successfully
        """
        try:
            if not self.is_connected or not self.message_bus:
                logger.error("Message integration not connected")
                return False

            await self.message_bus.publish(routing_key, command_data)

            logger.debug(
                f"Sent command via {routing_key}: {command_data.get('request_id')}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send command via {routing_key}: {e}")
            return False

    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status.

        Returns:
            dict: Connection status information
        """
        return {
            "is_connected": self.is_connected,
            "message_bus_available": self.message_bus is not None,
            "response_handlers_count": len(self.response_handlers),
            "notification_subscriptions_count": len(self.notification_subscriptions),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
