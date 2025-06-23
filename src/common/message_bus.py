"""Message Bus implementation for Letrade_v1 trading system.

Provides RabbitMQ-based message bus for inter-service communication
following the event-driven architecture pattern.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import aio_pika
from aio_pika import Connection, Exchange, Message, Queue
from aio_pika.abc import AbstractChannel, AbstractConnection

logger = logging.getLogger(__name__)


class MessageBus:
    """RabbitMQ message bus for inter-service communication.

    Provides publish/subscribe functionality with automatic reconnection,
    dead letter queues, and message persistence.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize message bus.

        Args:
            config: Message bus configuration
        """
        self.config = config
        self.connection: Optional[AbstractConnection] = None
        self.channel: Optional[AbstractChannel] = None
        self.exchanges: Dict[str, Exchange] = {}
        self.queues: Dict[str, Queue] = {}
        self.subscribers: Dict[str, Callable] = {}
        self.is_connected = False

        # Configuration with defaults
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 5672)
        self.username = config.get("username", "guest")
        self.password = config.get("password", "guest")
        self.virtual_host = config.get("virtual_host", "/")
        self.heartbeat = config.get("heartbeat", 60)
        self.connection_timeout = config.get("connection_timeout", 30)

        logger.info(
            "Message Bus initialized",
            extra={
                "component": "message_bus",
                "host": self.host,
                "port": self.port,
                "virtual_host": self.virtual_host,
            },
        )

    async def connect(self) -> bool:
        """Connect to RabbitMQ server.

        Returns:
            True if connected successfully, False otherwise
        """
        try:
            logger.info("Connecting to RabbitMQ", extra={"component": "message_bus"})

            # Build connection URL
            connection_url = (
                f"amqp://{self.username}:{self.password}@"
                f"{self.host}:{self.port}{self.virtual_host}"
            )

            # Establish connection
            self.connection = await aio_pika.connect_robust(
                connection_url,
                heartbeat=self.heartbeat,
                connection_timeout=self.connection_timeout,
            )

            # Create channel
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=100)

            # Setup exchanges and queues
            await self._setup_infrastructure()

            self.is_connected = True

            logger.info(
                "Successfully connected to RabbitMQ", extra={"component": "message_bus"}
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to connect to RabbitMQ",
                extra={"component": "message_bus", "error": str(e)},
            )
            self.is_connected = False
            return False

    async def disconnect(self) -> bool:
        """Disconnect from RabbitMQ server.

        Returns:
            True if disconnected successfully, False otherwise
        """
        try:
            logger.info(
                "Disconnecting from RabbitMQ", extra={"component": "message_bus"}
            )

            if self.connection and not self.connection.is_closed:
                await self.connection.close()

            self.is_connected = False
            self.connection = None
            self.channel = None
            self.exchanges.clear()
            self.queues.clear()

            logger.info(
                "Successfully disconnected from RabbitMQ",
                extra={"component": "message_bus"},
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to disconnect from RabbitMQ",
                extra={"component": "message_bus", "error": str(e)},
            )
            return False

    async def _setup_infrastructure(self):
        """Setup RabbitMQ exchanges and queues."""
        if not self.channel:
            raise RuntimeError("Channel not available")

        # Declare main exchanges
        await self._declare_exchange("letrade.events", "topic", durable=True)
        await self._declare_exchange("letrade.commands", "topic", durable=True)
        await self._declare_exchange("letrade.requests", "topic", durable=True)
        await self._declare_exchange(
            "letrade.dlx", "topic", durable=True
        )  # Dead letter exchange

        # Declare core queues
        await self._declare_queue(
            "market_data",
            exchange_name="letrade.events",
            routing_key="market_data.*",
            durable=True,
        )

        await self._declare_queue(
            "trade_commands",
            exchange_name="letrade.commands",
            routing_key="commands.*",
            durable=True,
        )

        await self._declare_queue(
            "capital_requests",
            exchange_name="letrade.requests",
            routing_key="request.capital.#",  # # 와일드카드로 변경하여 하위 레벨 매칭
            durable=True,
        )

        await self._declare_queue(
            "system_events",
            exchange_name="letrade.events",
            routing_key="events.system.*",
            durable=True,
        )

        # Dead letter queue
        await self._declare_queue(
            "dead_letters", exchange_name="letrade.dlx", routing_key="#", durable=True
        )

        logger.info(
            "Message bus infrastructure setup completed",
            extra={"component": "message_bus"},
        )

    async def _declare_exchange(
        self, name: str, exchange_type: str = "topic", durable: bool = True
    ) -> Exchange:
        """Declare an exchange.

        Args:
            name: Exchange name
            exchange_type: Exchange type (topic, direct, fanout)
            durable: Whether exchange should survive server restart

        Returns:
            Declared exchange
        """
        if not self.channel:
            raise RuntimeError("Channel not available")

        exchange = await self.channel.declare_exchange(
            name, type=exchange_type, durable=durable
        )

        self.exchanges[name] = exchange

        logger.debug(
            f"Declared exchange: {name}",
            extra={"component": "message_bus", "exchange": name, "type": exchange_type},
        )

        return exchange

    async def _declare_queue(
        self,
        name: str,
        exchange_name: str,
        routing_key: str,
        durable: bool = True,
        exclusive: bool = False,
        auto_delete: bool = False,
    ) -> Queue:
        """Declare a queue and bind it to an exchange.

        Args:
            name: Queue name
            exchange_name: Exchange to bind to
            routing_key: Routing key pattern
            durable: Whether queue should survive server restart
            exclusive: Whether queue is exclusive to this connection
            auto_delete: Whether queue should be deleted when not used

        Returns:
            Declared queue
        """
        if not self.channel:
            raise RuntimeError("Channel not available")

        # Queue arguments with dead letter exchange
        queue_args = {
            "x-dead-letter-exchange": "letrade.dlx",
            "x-message-ttl": 3600000,  # 1 hour TTL
        }

        queue = await self.channel.declare_queue(
            name,
            durable=durable,
            exclusive=exclusive,
            auto_delete=auto_delete,
            arguments=queue_args,
        )

        # Bind queue to exchange
        if exchange_name in self.exchanges:
            await queue.bind(self.exchanges[exchange_name], routing_key)

        self.queues[name] = queue

        logger.debug(
            f"Declared and bound queue: {name}",
            extra={
                "component": "message_bus",
                "queue": name,
                "exchange": exchange_name,
                "routing_key": routing_key,
            },
        )

        return queue

    async def publish(
        self,
        exchange_name: str,
        routing_key: str,
        message: Dict[str, Any],
        persistent: bool = True,
    ) -> bool:
        """Publish a message to an exchange.

        Args:
            exchange_name: Target exchange name
            routing_key: Message routing key
            message: Message payload
            persistent: Whether message should be persistent

        Returns:
            True if published successfully, False otherwise
        """
        if not self.is_connected or not self.channel:
            logger.error(
                "Cannot publish: not connected to message bus",
                extra={"component": "message_bus"},
            )
            return False

        try:
            # Add metadata to message
            enriched_message = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "routing_key": routing_key,
                "payload": message,
            }

            # Create message
            aio_message = Message(
                json.dumps(enriched_message).encode(),
                content_type="application/json",
                delivery_mode=2 if persistent else 1,  # Persistent or not
                timestamp=datetime.now(timezone.utc),
            )

            # Get exchange
            if exchange_name not in self.exchanges:
                logger.error(
                    f"Exchange {exchange_name} not found",
                    extra={"component": "message_bus", "exchange": exchange_name},
                )
                return False

            exchange = self.exchanges[exchange_name]

            # Publish message
            await exchange.publish(aio_message, routing_key)

            logger.debug(
                "Message published successfully",
                extra={
                    "component": "message_bus",
                    "exchange": exchange_name,
                    "routing_key": routing_key,
                    "message_size": len(aio_message.body),
                },
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to publish message",
                extra={
                    "component": "message_bus",
                    "exchange": exchange_name,
                    "routing_key": routing_key,
                    "error": str(e),
                },
            )
            return False

    async def subscribe(
        self,
        queue_name: str,
        callback: Callable[[Dict[str, Any]], None],
        auto_ack: bool = False,
    ) -> bool:
        """Subscribe to messages from a queue.

        Args:
            queue_name: Queue to subscribe to
            callback: Message handler function
            auto_ack: Whether to automatically acknowledge messages

        Returns:
            True if subscribed successfully, False otherwise
        """
        if not self.is_connected or not self.channel:
            logger.error(
                "Cannot subscribe: not connected to message bus",
                extra={"component": "message_bus"},
            )
            return False

        try:
            if queue_name not in self.queues:
                logger.error(
                    f"Queue {queue_name} not found",
                    extra={"component": "message_bus", "queue": queue_name},
                )
                return False

            queue = self.queues[queue_name]

            async def message_handler(message: aio_pika.abc.AbstractIncomingMessage):
                async with message.process(ignore_processed=True):
                    try:
                        # Parse message
                        message_data = json.loads(message.body.decode())

                        logger.debug(
                            "Processing message",
                            extra={
                                "component": "message_bus",
                                "queue": queue_name,
                                "routing_key": message_data.get("routing_key"),
                            },
                        )

                        # Call handler
                        if asyncio.iscoroutinefunction(callback):
                            await callback(message_data)
                        else:
                            callback(message_data)

                        # Message will be automatically acked by context manager

                    except Exception as e:
                        logger.error(
                            "Error processing message",
                            extra={
                                "component": "message_bus",
                                "queue": queue_name,
                                "error": str(e),
                            },
                        )
                        # Message will be automatically rejected by context manager
                        raise  # Re-raise to trigger reject behavior

            # Start consuming
            await queue.consume(message_handler, no_ack=auto_ack)

            self.subscribers[queue_name] = callback

            logger.info(
                f"Successfully subscribed to queue: {queue_name}",
                extra={"component": "message_bus", "queue": queue_name},
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to subscribe to queue",
                extra={
                    "component": "message_bus",
                    "queue": queue_name,
                    "error": str(e),
                    "connected": self.is_connected,
                    "channel_available": self.channel is not None,
                    "queue_exists": queue_name in self.queues,
                },
                exc_info=True,
            )
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on message bus.

        Returns:
            Health status information
        """
        try:
            health_status = {
                "component": "message_bus",
                "healthy": self.is_connected,
                "connected": self.is_connected,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            if self.is_connected and self.connection:
                health_status.update(
                    {
                        "connection_closed": self.connection.is_closed,
                        "exchanges_count": len(self.exchanges),
                        "queues_count": len(self.queues),
                        "subscribers_count": len(self.subscribers),
                    }
                )

            return health_status

        except Exception as e:
            logger.error(
                "Health check failed",
                extra={"component": "message_bus", "error": str(e)},
            )

            return {
                "component": "message_bus",
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }


# Message type constants for routing keys
class MessageRoutes:
    """Message routing key constants."""

    # Market data
    MARKET_DATA_BINANCE = "market_data.binance.{symbol}"
    MARKET_DATA_ALL = "market_data.*"

    # Commands
    EXECUTE_TRADE = "commands.execute_trade"
    STOP_STRATEGY = "commands.stop_strategy"
    START_STRATEGY = "commands.start_strategy"

    # Requests
    CAPITAL_ALLOCATION = "request.capital.allocation.{strategy_id}"
    POSITION_STATUS = "request.position.status"

    # Events
    TRADE_EXECUTED = "events.trade.executed"
    STRATEGY_STARTED = "events.strategy.started"
    STRATEGY_STOPPED = "events.strategy.stopped"
    SYSTEM_ERROR = "events.system.error"
    SYSTEM_HEALTH = "events.system.health"


async def create_message_bus(config: Dict[str, Any]) -> MessageBus:
    """Factory function to create and connect message bus.

    Args:
        config: Message bus configuration

    Returns:
        Connected message bus instance

    Raises:
        RuntimeError: If connection fails
    """
    message_bus = MessageBus(config)

    if not await message_bus.connect():
        raise RuntimeError("Failed to connect to message bus")

    return message_bus
