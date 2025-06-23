"""Integration tests for Message Bus with Core Engine."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from common.message_bus import MessageBus, MessageRoutes
from core_engine.main import CoreEngine


class TestMessageBusIntegration:
    """Integration tests for Message Bus with other components."""

    @pytest.mark.asyncio
    async def test_core_engine_message_bus_integration(self):
        """Test Core Engine integration with Message Bus."""
        # Mock message bus connection
        with patch(
            "common.message_bus.aio_pika.connect_robust", return_value=AsyncMock()
        ):
            with patch.object(MessageBus, "_setup_infrastructure", return_value=None):
                # Create Core Engine with message bus config
                config = {
                    "message_bus": {
                        "host": "localhost",
                        "port": 5672,
                        "username": "guest",
                        "password": "guest",
                    }
                }

                engine = CoreEngine(config)

                # Start Core Engine (should initialize message bus)
                with patch.object(
                    engine, "_validate_startup_conditions", return_value=True
                ):
                    with patch.object(
                        engine, "_start_background_tasks", return_value=None
                    ):
                        with patch.object(
                            engine, "_perform_startup_reconciliation", return_value=None
                        ):
                            result = await engine.start()

                assert result is True
                assert engine.message_bus is not None
                assert engine.message_bus.is_connected is True

                # Test health check includes message bus
                health = await engine.health_check()
                assert "message_bus" in health["components"]

                # Stop engine (should disconnect message bus)
                with patch.object(engine, "_stop_new_operations", return_value=None):
                    with patch.object(
                        engine, "_wait_for_active_operations", return_value=None
                    ):
                        with patch.object(
                            engine, "_stop_background_tasks", return_value=None
                        ):
                            with patch.object(
                                engine, "_persist_final_state", return_value=None
                            ):
                                await engine.stop()

    @pytest.mark.asyncio
    async def test_message_flow_system_events(self):
        """Test system event message flow."""
        # Mock message bus
        with patch(
            "common.message_bus.aio_pika.connect_robust", return_value=AsyncMock()
        ):
            with patch.object(MessageBus, "_setup_infrastructure", return_value=None):
                config = {"message_bus": {"host": "localhost"}}
                engine = CoreEngine(config)

                # Mock the subsystem initialization
                with patch.object(
                    engine, "_validate_startup_conditions", return_value=True
                ):
                    with patch.object(
                        engine, "_start_background_tasks", return_value=None
                    ):
                        with patch.object(
                            engine, "_perform_startup_reconciliation", return_value=None
                        ):
                            await engine.start()

                # Test handling different system events
                test_events = [
                    {
                        "routing_key": MessageRoutes.TRADE_EXECUTED,
                        "payload": {"strategy_id": "test_strategy", "trade_id": "123"},
                    },
                    {
                        "routing_key": MessageRoutes.STRATEGY_STARTED,
                        "payload": {"strategy_id": "test_strategy"},
                    },
                    {
                        "routing_key": MessageRoutes.STRATEGY_STOPPED,
                        "payload": {"strategy_id": "test_strategy"},
                    },
                    {
                        "routing_key": MessageRoutes.SYSTEM_ERROR,
                        "payload": {"error": "Test error", "component": "test"},
                    },
                ]

                for event in test_events:
                    await engine._handle_system_event(event)

                # Verify strategy tracking
                assert (
                    "test_strategy" not in engine.status.active_strategies
                )  # Stopped at the end
                assert engine.status.total_trades == 1

                # Clean shutdown
                with patch.object(engine, "_stop_new_operations", return_value=None):
                    with patch.object(
                        engine, "_wait_for_active_operations", return_value=None
                    ):
                        with patch.object(
                            engine, "_stop_background_tasks", return_value=None
                        ):
                            with patch.object(
                                engine, "_persist_final_state", return_value=None
                            ):
                                await engine.stop()

    @pytest.mark.asyncio
    async def test_message_bus_publish_subscribe_flow(self):
        """Test complete publish/subscribe message flow."""
        # Create two message bus instances to simulate different components
        with patch(
            "common.message_bus.aio_pika.connect_robust", return_value=AsyncMock()
        ):
            with patch.object(MessageBus, "_setup_infrastructure", return_value=None):
                # Publisher (e.g., Strategy Worker)
                publisher_config = {"host": "localhost"}
                publisher = MessageBus(publisher_config)
                await publisher.connect()

                # Subscriber (e.g., Capital Manager)
                subscriber_config = {"host": "localhost"}
                subscriber = MessageBus(subscriber_config)
                await subscriber.connect()

                # Setup mock exchanges and queues
                mock_exchange = AsyncMock()
                mock_queue = AsyncMock()

                publisher.exchanges["letrade.requests"] = mock_exchange
                subscriber.queues["capital_requests"] = mock_queue

                # Test message publishing
                test_message = {
                    "strategy_id": "ma_crossover_1",
                    "symbol": "BTC/USDT",
                    "side": "buy",
                    "signal_price": 50000.0,
                    "confidence": 0.8,
                }

                result = await publisher.publish(
                    "letrade.requests",
                    MessageRoutes.CAPITAL_ALLOCATION.format(
                        strategy_id="ma_crossover_1"
                    ),
                    test_message,
                )

                assert result is True
                mock_exchange.publish.assert_called_once()

                # Test subscription setup
                received_messages = []

                async def message_handler(message):
                    received_messages.append(message)

                result = await subscriber.subscribe("capital_requests", message_handler)
                assert result is True

                # Cleanup
                await publisher.disconnect()
                await subscriber.disconnect()

    @pytest.mark.asyncio
    async def test_message_routing_patterns(self):
        """Test different message routing patterns."""
        with patch(
            "common.message_bus.aio_pika.connect_robust", return_value=AsyncMock()
        ):
            with patch.object(MessageBus, "_setup_infrastructure", return_value=None):
                message_bus = MessageBus({"host": "localhost"})
                await message_bus.connect()

                # Setup mock infrastructure
                mock_exchange = AsyncMock()
                message_bus.exchanges["letrade.events"] = mock_exchange

                # Test different routing key patterns
                routing_tests = [
                    {
                        "routing_key": "market_data.binance.btcusdt",
                        "message": {"symbol": "BTC/USDT", "price": 50000},
                    },
                    {
                        "routing_key": "market_data.binance.ethusdt",
                        "message": {"symbol": "ETH/USDT", "price": 3000},
                    },
                    {
                        "routing_key": "events.trade.executed",
                        "message": {"trade_id": "123", "status": "filled"},
                    },
                    {
                        "routing_key": "events.system.health",
                        "message": {"component": "core_engine", "healthy": True},
                    },
                ]

                for test in routing_tests:
                    result = await message_bus.publish(
                        "letrade.events", test["routing_key"], test["message"]
                    )
                    assert result is True

                # Verify all messages were published
                assert mock_exchange.publish.call_count == len(routing_tests)

                await message_bus.disconnect()

    @pytest.mark.asyncio
    async def test_message_bus_error_handling(self):
        """Test message bus error handling in integration scenarios."""
        with patch(
            "common.message_bus.aio_pika.connect_robust", return_value=AsyncMock()
        ):
            config = {"message_bus": {"host": "localhost"}}
            engine = CoreEngine(config)

            # Test startup with message bus connection failure
            with patch.object(MessageBus, "connect", return_value=False):
                with patch.object(
                    engine, "_validate_startup_conditions", return_value=True
                ):
                    result = await engine.start()
                    # Should return False when message bus connection fails
                    assert result is False

    @pytest.mark.asyncio
    async def test_message_persistence_and_durability(self):
        """Test message persistence and durability settings."""
        with patch(
            "common.message_bus.aio_pika.connect_robust", return_value=AsyncMock()
        ):
            with patch.object(MessageBus, "_setup_infrastructure", return_value=None):
                message_bus = MessageBus({"host": "localhost"})
                await message_bus.connect()

                # Test persistent message publishing
                mock_exchange = AsyncMock()
                message_bus.exchanges["letrade.commands"] = mock_exchange

                critical_message = {
                    "strategy_id": "critical_strategy",
                    "action": "emergency_stop",
                    "reason": "risk_limit_exceeded",
                }

                # Publish with persistence enabled (default)
                result = await message_bus.publish(
                    "letrade.commands",
                    MessageRoutes.STOP_STRATEGY,
                    critical_message,
                    persistent=True,
                )

                assert result is True

                # Verify message was published with persistence
                mock_exchange.publish.assert_called()
                call_args = mock_exchange.publish.call_args
                message_arg = call_args[0][
                    0
                ]  # First positional argument (Message object)

                # Should have delivery_mode=2 for persistence
                assert hasattr(message_arg, "delivery_mode")

                await message_bus.disconnect()

    @pytest.mark.asyncio
    async def test_dead_letter_queue_setup(self):
        """Test dead letter queue configuration."""
        with patch(
            "common.message_bus.aio_pika.connect_robust", return_value=AsyncMock()
        ):
            message_bus = MessageBus({"host": "localhost"})

            mock_channel = AsyncMock()
            mock_exchange = AsyncMock()
            mock_queue = AsyncMock()

            message_bus.channel = mock_channel

            # Mock the declare methods to capture arguments
            async def mock_declare_exchange(name, exchange_type="topic", durable=True):
                message_bus.exchanges[name] = mock_exchange
                return mock_exchange

            async def mock_declare_queue(
                name, exchange_name, routing_key, durable=True, **kwargs
            ):
                # Verify DLX configuration in queue arguments
                if "arguments" in kwargs:
                    assert "x-dead-letter-exchange" in kwargs["arguments"]
                    assert (
                        kwargs["arguments"]["x-dead-letter-exchange"] == "letrade.dlx"
                    )
                message_bus.queues[name] = mock_queue
                return mock_queue

            message_bus._declare_exchange = mock_declare_exchange
            message_bus._declare_queue = mock_declare_queue

            # Setup infrastructure should create DLX
            await message_bus._setup_infrastructure()

            # Verify DLX exchange was created
            assert "letrade.dlx" in message_bus.exchanges

            # Verify dead letter queue was created
            assert "dead_letters" in message_bus.queues

    @pytest.mark.asyncio
    async def test_concurrent_message_handling(self):
        """Test concurrent message publishing and subscribing."""
        with patch(
            "common.message_bus.aio_pika.connect_robust", return_value=AsyncMock()
        ):
            with patch.object(MessageBus, "_setup_infrastructure", return_value=None):
                message_bus = MessageBus({"host": "localhost"})
                await message_bus.connect()

                # Setup mock infrastructure
                mock_exchange = AsyncMock()
                mock_queue = AsyncMock()

                message_bus.exchanges["letrade.events"] = mock_exchange
                message_bus.queues["market_data"] = mock_queue

                # Test concurrent publishing
                async def publish_messages():
                    tasks = []
                    for i in range(10):
                        task = message_bus.publish(
                            "letrade.events",
                            f"market_data.binance.symbol{i}",
                            {"price": 1000 + i},
                        )
                        tasks.append(task)

                    results = await asyncio.gather(*tasks)
                    return all(results)

                # Execute concurrent publishes
                result = await publish_messages()
                assert result is True

                # Verify all messages were published
                assert mock_exchange.publish.call_count == 10

                await message_bus.disconnect()


@pytest.mark.performance
class TestMessageBusPerformanceIntegration:
    """Performance integration tests for Message Bus."""

    @pytest.mark.asyncio
    async def test_high_throughput_messaging(self):
        """Test high throughput message processing."""
        with patch(
            "common.message_bus.aio_pika.connect_robust", return_value=AsyncMock()
        ):
            with patch.object(MessageBus, "_setup_infrastructure", return_value=None):
                message_bus = MessageBus({"host": "localhost"})
                await message_bus.connect()

                # Setup mock infrastructure
                mock_exchange = AsyncMock()
                message_bus.exchanges["letrade.events"] = mock_exchange

                import time

                start_time = time.time()

                # Publish 1000 messages
                tasks = []
                for i in range(1000):
                    task = message_bus.publish(
                        "letrade.events",
                        f"market_data.test.{i}",
                        {"sequence": i, "timestamp": time.time()},
                    )
                    tasks.append(task)

                results = await asyncio.gather(*tasks)
                duration = time.time() - start_time

                # All should succeed
                assert all(results)

                # Should be able to publish 1000 messages in reasonable time
                throughput = len(results) / duration
                assert throughput > 100, f"Throughput {throughput:.1f} msg/s is too low"

                await message_bus.disconnect()

    @pytest.mark.asyncio
    async def test_core_engine_startup_performance_with_message_bus(self):
        """Test Core Engine startup performance with message bus."""
        with patch(
            "common.message_bus.aio_pika.connect_robust", return_value=AsyncMock()
        ):
            with patch.object(MessageBus, "_setup_infrastructure", return_value=None):
                config = {"message_bus": {"host": "localhost"}}

                import time

                start_time = time.time()

                engine = CoreEngine(config)

                with patch.object(
                    engine, "_validate_startup_conditions", return_value=True
                ):
                    with patch.object(
                        engine, "_start_background_tasks", return_value=None
                    ):
                        with patch.object(
                            engine, "_perform_startup_reconciliation", return_value=None
                        ):
                            await engine.start()

                startup_duration = time.time() - start_time

                # Startup with message bus should be fast
                assert (
                    startup_duration < 2.0
                ), f"Startup took {startup_duration:.3f}s, should be < 2.0s"

                # Clean shutdown
                with patch.object(engine, "_stop_new_operations", return_value=None):
                    with patch.object(
                        engine, "_wait_for_active_operations", return_value=None
                    ):
                        with patch.object(
                            engine, "_stop_background_tasks", return_value=None
                        ):
                            with patch.object(
                                engine, "_persist_final_state", return_value=None
                            ):
                                await engine.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
