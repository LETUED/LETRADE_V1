"""Unit tests for Message Bus module."""

from unittest.mock import AsyncMock, patch

import pytest

from common.message_bus import (  # noqa: E402
    MessageBus,
    MessageRoutes,
    create_message_bus,
)


class TestMessageBus:
    """Test cases for Message Bus."""

    def test_initialization(self):
        """Test Message Bus initialization."""
        config = {
            "host": "localhost",
            "port": 5672,
            "username": "test_user",
            "password": "test_pass",
            "virtual_host": "/test",
        }

        message_bus = MessageBus(config)

        assert message_bus.config == config
        assert message_bus.host == "localhost"
        assert message_bus.port == 5672
        assert message_bus.username == "test_user"
        assert message_bus.password == "test_pass"
        assert message_bus.virtual_host == "/test"
        assert message_bus.is_connected is False

    def test_initialization_with_defaults(self):
        """Test Message Bus initialization with default values."""
        message_bus = MessageBus({})

        assert message_bus.host == "localhost"
        assert message_bus.port == 5672
        assert message_bus.username == "guest"
        assert message_bus.password == "guest"
        assert message_bus.virtual_host == "/"

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection to RabbitMQ."""
        message_bus = MessageBus({"host": "localhost"})

        # Mock aio_pika
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_connection.channel.return_value = mock_channel

        with patch(
            "common.message_bus.aio_pika.connect_robust", return_value=mock_connection
        ):
            with patch.object(message_bus, "_setup_infrastructure", return_value=None):
                result = await message_bus.connect()

        assert result is True
        assert message_bus.is_connected is True
        assert message_bus.connection == mock_connection
        assert message_bus.channel == mock_channel

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test connection failure."""
        message_bus = MessageBus({"host": "localhost"})

        with patch(
            "common.message_bus.aio_pika.connect_robust",
            side_effect=Exception("Connection failed"),
        ):
            result = await message_bus.connect()

        assert result is False
        assert message_bus.is_connected is False

    @pytest.mark.asyncio
    async def test_disconnect_success(self):
        """Test successful disconnection."""
        message_bus = MessageBus({"host": "localhost"})

        # Setup mock connection
        mock_connection = AsyncMock()
        mock_connection.is_closed = False
        message_bus.connection = mock_connection
        message_bus.is_connected = True

        result = await message_bus.disconnect()

        assert result is True
        assert message_bus.is_connected is False
        assert message_bus.connection is None
        mock_connection.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_message_success(self):
        """Test successful message publishing."""
        message_bus = MessageBus({"host": "localhost"})

        # Setup mocks
        mock_exchange = AsyncMock()
        mock_channel = AsyncMock()

        message_bus.is_connected = True
        message_bus.channel = mock_channel
        message_bus.exchanges["letrade.events"] = mock_exchange

        test_message = {"symbol": "BTCUSDT", "price": 50000}

        result = await message_bus.publish(
            "letrade.events", "market_data.binance.btcusdt", test_message
        )

        assert result is True
        mock_exchange.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_message_not_connected(self):
        """Test publishing when not connected."""
        message_bus = MessageBus({"host": "localhost"})
        message_bus.is_connected = False

        result = await message_bus.publish(
            "letrade.events", "market_data.binance.btcusdt", {"test": "data"}
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_publish_message_exchange_not_found(self):
        """Test publishing to non-existent exchange."""
        message_bus = MessageBus({"host": "localhost"})
        message_bus.is_connected = True
        message_bus.channel = AsyncMock()

        result = await message_bus.publish(
            "non_existent_exchange", "test.routing.key", {"test": "data"}
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_subscribe_success(self):
        """Test successful queue subscription."""
        message_bus = MessageBus({"host": "localhost"})

        # Setup mocks
        mock_queue = AsyncMock()
        mock_channel = AsyncMock()

        message_bus.is_connected = True
        message_bus.channel = mock_channel
        message_bus.queues["market_data"] = mock_queue

        async def test_callback(message):
            pass

        result = await message_bus.subscribe("market_data", test_callback)

        assert result is True
        assert "market_data" in message_bus.subscribers
        mock_queue.consume.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscribe_not_connected(self):
        """Test subscribing when not connected."""
        message_bus = MessageBus({"host": "localhost"})
        message_bus.is_connected = False

        async def test_callback(message):
            pass

        result = await message_bus.subscribe("market_data", test_callback)

        assert result is False

    @pytest.mark.asyncio
    async def test_subscribe_queue_not_found(self):
        """Test subscribing to non-existent queue."""
        message_bus = MessageBus({"host": "localhost"})
        message_bus.is_connected = True
        message_bus.channel = AsyncMock()

        async def test_callback(message):
            pass

        result = await message_bus.subscribe("non_existent_queue", test_callback)

        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_connected(self):
        """Test health check when connected."""
        message_bus = MessageBus({"host": "localhost"})

        # Setup mock connection
        mock_connection = AsyncMock()
        mock_connection.is_closed = False

        message_bus.is_connected = True
        message_bus.connection = mock_connection
        message_bus.exchanges = {"test": "exchange"}
        message_bus.queues = {"test": "queue"}
        message_bus.subscribers = {"test": "callback"}

        health = await message_bus.health_check()

        assert health["component"] == "message_bus"
        assert health["healthy"] is True
        assert health["connected"] is True
        assert health["exchanges_count"] == 1
        assert health["queues_count"] == 1
        assert health["subscribers_count"] == 1

    @pytest.mark.asyncio
    async def test_health_check_disconnected(self):
        """Test health check when disconnected."""
        message_bus = MessageBus({"host": "localhost"})
        message_bus.is_connected = False

        health = await message_bus.health_check()

        assert health["component"] == "message_bus"
        assert health["healthy"] is False
        assert health["connected"] is False

    @pytest.mark.asyncio
    async def test_declare_exchange(self):
        """Test exchange declaration."""
        message_bus = MessageBus({"host": "localhost"})

        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_channel.declare_exchange.return_value = mock_exchange

        message_bus.channel = mock_channel

        exchange = await message_bus._declare_exchange("test_exchange", "topic", True)

        assert exchange == mock_exchange
        assert "test_exchange" in message_bus.exchanges
        mock_channel.declare_exchange.assert_called_once_with(
            "test_exchange", type="topic", durable=True
        )

    @pytest.mark.asyncio
    async def test_declare_queue(self):
        """Test queue declaration and binding."""
        message_bus = MessageBus({"host": "localhost"})

        mock_channel = AsyncMock()
        mock_queue = AsyncMock()
        mock_exchange = AsyncMock()

        mock_channel.declare_queue.return_value = mock_queue
        message_bus.channel = mock_channel
        message_bus.exchanges["test_exchange"] = mock_exchange

        queue = await message_bus._declare_queue(
            "test_queue", "test_exchange", "test.routing.key"
        )

        assert queue == mock_queue
        assert "test_queue" in message_bus.queues
        mock_queue.bind.assert_called_once_with(mock_exchange, "test.routing.key")

    @pytest.mark.asyncio
    async def test_setup_infrastructure(self):
        """Test infrastructure setup."""
        message_bus = MessageBus({"host": "localhost"})

        mock_channel = AsyncMock()
        message_bus.channel = mock_channel

        # Mock the declare methods
        mock_exchange = AsyncMock()
        mock_queue = AsyncMock()

        # Mock the declare methods to actually populate exchanges and queues
        async def mock_declare_exchange(name, exchange_type="topic", durable=True):
            message_bus.exchanges[name] = mock_exchange
            return mock_exchange

        async def mock_declare_queue(name, exchange_name, routing_key, **kwargs):
            message_bus.queues[name] = mock_queue
            return mock_queue

        message_bus._declare_exchange = mock_declare_exchange
        message_bus._declare_queue = mock_declare_queue

        await message_bus._setup_infrastructure()

        # Verify exchanges and queues were created
        assert (
            len(message_bus.exchanges) >= 4
        )  # At least 4 exchanges should be declared
        assert len(message_bus.queues) >= 5  # At least 5 queues should be declared


class TestMessageRoutes:
    """Test cases for Message Routes constants."""

    def test_market_data_routes(self):
        """Test market data routing keys."""
        btc_route = MessageRoutes.MARKET_DATA_BINANCE.format(symbol="btcusdt")
        assert btc_route == "market_data.binance.btcusdt"

        eth_route = MessageRoutes.MARKET_DATA_BINANCE.format(symbol="ethusdt")
        assert eth_route == "market_data.binance.ethusdt"

    def test_command_routes(self):
        """Test command routing keys."""
        assert MessageRoutes.EXECUTE_TRADE == "commands.execute_trade"
        assert MessageRoutes.STOP_STRATEGY == "commands.stop_strategy"
        assert MessageRoutes.START_STRATEGY == "commands.start_strategy"

    def test_request_routes(self):
        """Test request routing keys."""
        capital_route = MessageRoutes.CAPITAL_ALLOCATION.format(strategy_id="123")
        assert capital_route == "request.capital.allocation.123"

    def test_event_routes(self):
        """Test event routing keys."""
        assert MessageRoutes.TRADE_EXECUTED == "events.trade.executed"
        assert MessageRoutes.STRATEGY_STARTED == "events.strategy.started"
        assert MessageRoutes.STRATEGY_STOPPED == "events.strategy.stopped"
        assert MessageRoutes.SYSTEM_ERROR == "events.system.error"


class TestMessageBusIntegration:
    """Integration test cases for Message Bus."""

    @pytest.mark.asyncio
    async def test_create_message_bus_success(self):
        """Test message bus factory function success."""
        config = {"host": "localhost"}

        with patch(
            "common.message_bus.aio_pika.connect_robust", return_value=AsyncMock()
        ):
            with patch.object(MessageBus, "_setup_infrastructure", return_value=None):
                message_bus = await create_message_bus(config)

        assert isinstance(message_bus, MessageBus)
        assert message_bus.is_connected is True

    @pytest.mark.asyncio
    async def test_create_message_bus_failure(self):
        """Test message bus factory function failure."""
        config = {"host": "localhost"}

        with patch(
            "common.message_bus.aio_pika.connect_robust",
            side_effect=Exception("Connection failed"),
        ):
            with pytest.raises(RuntimeError, match="Failed to connect to message bus"):
                await create_message_bus(config)


class TestMessageBusTradingSafety:
    """Trading system safety tests for Message Bus."""

    def test_no_hardcoded_secrets(self):
        """Ensure no hardcoded secrets in message bus code."""
        import inspect

        import src.common.message_bus as module

        source = inspect.getsource(module)

        # Check for common secret patterns
        forbidden_patterns = [
            "password=",
            "secret=",
            "api_key=",
            "private_key=",
        ]

        for pattern in forbidden_patterns:
            assert (
                pattern not in source.lower()
            ), f"Hardcoded secret pattern detected: {pattern}"

    @pytest.mark.asyncio
    async def test_graceful_failure_handling(self):
        """Test that message bus failures don't crash system ungracefully."""
        message_bus = MessageBus({"host": "localhost"})

        # Test that connection failures are handled gracefully
        with patch(
            "common.message_bus.aio_pika.connect_robust",
            side_effect=Exception("Network error"),
        ):
            result = await message_bus.connect()
            assert result is False
            assert message_bus.is_connected is False

    @pytest.mark.asyncio
    async def test_message_isolation(self):
        """Test that message processing errors don't affect other messages."""
        message_bus = MessageBus({"host": "localhost"})
        message_bus.is_connected = True
        message_bus.channel = AsyncMock()

        # Test that publish failures don't crash the system
        with patch.object(
            message_bus.channel, "publish", side_effect=Exception("Publish error")
        ):
            result = await message_bus.publish(
                "test_exchange", "test.key", {"data": "test"}
            )
            assert result is False  # Should return False, not crash


@pytest.mark.performance
class TestMessageBusPerformance:
    """Performance tests for Message Bus."""

    @pytest.mark.asyncio
    async def test_connection_performance(self):
        """Test message bus connection performance."""
        import time

        config = {"host": "localhost"}

        with patch(
            "common.message_bus.aio_pika.connect_robust", return_value=AsyncMock()
        ):
            with patch.object(MessageBus, "_setup_infrastructure", return_value=None):
                start_time = time.time()
                message_bus = MessageBus(config)
                await message_bus.connect()
                duration = time.time() - start_time

        assert duration < 1.0, f"Connection took {duration:.3f}s, should be < 1.0s"

    @pytest.mark.asyncio
    async def test_publish_performance(self):
        """Test message publishing performance."""
        import time

        message_bus = MessageBus({"host": "localhost"})
        message_bus.is_connected = True
        message_bus.channel = AsyncMock()
        message_bus.exchanges["test"] = AsyncMock()

        start_time = time.time()

        # Test multiple publishes
        for i in range(100):
            await message_bus.publish("test", f"test.{i}", {"data": i})

        duration = time.time() - start_time

        # Should be able to publish 100 messages in reasonable time
        assert duration < 1.0, f"100 publishes took {duration:.3f}s, should be < 1.0s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
