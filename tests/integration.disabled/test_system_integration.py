"""Integration tests for the complete trading system."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from src.capital_manager.main import CapitalManager, TradeRequest
from src.core_engine.main import CoreEngine
from src.exchange_connector.main import (
    ExchangeConnector,
    OrderRequest,
    OrderSide,
    OrderType,
)
from src.strategies.base_strategy import BaseStrategy, StrategyConfig, TradingSignal


class MockStrategy(BaseStrategy):
    """Mock strategy for testing."""

    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self._should_signal = False
        self._signal_count = 0

    def populate_indicators(self, dataframe):
        """Mock indicator population."""
        # Add simple mock indicators
        dataframe["sma_20"] = 100.0  # Mock SMA
        dataframe["rsi"] = 50.0  # Mock RSI
        return dataframe

    def on_data(self, data, dataframe):
        """Mock signal generation."""
        if self._should_signal:
            self._signal_count += 1
            signal = TradingSignal(
                strategy_id=self.strategy_id,
                symbol="BTCUSDT",
                side="buy",
                confidence=0.8,
                timestamp=datetime.now(timezone.utc),
                signal_price=50000.0,
            )
            self._record_signal_generated(signal)
            return signal
        return None

    def get_required_subscriptions(self):
        """Mock subscription requirements."""
        return ["BTCUSDT"]

    def trigger_signal(self):
        """Trigger a signal for testing."""
        self._should_signal = True


@pytest.mark.integration
class TestSystemIntegration:
    """Integration tests for the complete trading system."""

    @pytest_asyncio.fixture
    async def trading_system(self):
        """Setup a complete trading system for testing."""
        # Core Engine
        core_config = {"log_level": "INFO", "health_check_interval": 30}
        core_engine = CoreEngine(core_config)

        # Capital Manager
        capital_config = {
            "risk_parameters": {
                "max_position_size_percent": 5.0,
                "max_daily_loss_percent": 2.0,
                "stop_loss_percent": 2.0,
            }
        }
        capital_manager = CapitalManager(capital_config)

        # Exchange Connector
        exchange_config = {
            "default_exchange": "mock",
            "exchanges": {"mock": {"name": "mock", "type": "mock", "dry_run": True}},
        }
        exchange_connector = ExchangeConnector(exchange_config)

        # Mock Strategy
        strategy_config = StrategyConfig(
            strategy_id="test_strategy",
            name="Test Strategy",
            enabled=True,
            dry_run=True,
        )
        strategy = MockStrategy(strategy_config)

        # Wire components together (simplified)
        core_engine.capital_manager = capital_manager
        core_engine.exchange_connector = exchange_connector

        return {
            "core_engine": core_engine,
            "capital_manager": capital_manager,
            "exchange_connector": exchange_connector,
            "strategy": strategy,
        }

    @pytest.mark.asyncio
    async def test_system_startup_shutdown(self, trading_system):
        """Test complete system startup and shutdown."""
        core_engine = trading_system["core_engine"]
        capital_manager = trading_system["capital_manager"]
        exchange_connector = trading_system["exchange_connector"]
        strategy = trading_system["strategy"]

        # Test individual component startup
        assert await capital_manager.start() is True
        assert await exchange_connector.start() is True
        assert await strategy.start() is True

        # Mock core engine startup dependencies
        core_engine._validate_startup_conditions = AsyncMock(return_value=True)
        core_engine._initialize_subsystems = AsyncMock()
        core_engine._start_background_tasks = AsyncMock()
        core_engine._perform_startup_reconciliation = AsyncMock()

        # Test core engine startup
        assert await core_engine.start() is True

        # Verify all components are running
        assert capital_manager.is_running is True
        assert exchange_connector.connectors["mock"].is_connected is True
        assert strategy.is_running is True
        assert core_engine.status.is_running is True

        # Test shutdown
        core_engine._stop_new_operations = AsyncMock()
        core_engine._wait_for_active_operations = AsyncMock()
        core_engine._stop_background_tasks = AsyncMock()
        core_engine._shutdown_subsystems = AsyncMock()
        core_engine._persist_final_state = AsyncMock()

        assert await core_engine.stop() is True
        assert await strategy.stop() is True
        assert await exchange_connector.stop() is True
        assert await capital_manager.stop() is True

    @pytest.mark.asyncio
    async def test_trade_flow_integration(self, trading_system):
        """Test complete trade flow from signal to execution."""
        capital_manager = trading_system["capital_manager"]
        exchange_connector = trading_system["exchange_connector"]
        strategy = trading_system["strategy"]

        # Start required components
        await capital_manager.start()
        await exchange_connector.start()
        await strategy.start()

        try:
            # 1. Generate trading signal
            strategy.trigger_signal()

            # Mock market data for signal generation
            import pandas as pd

            mock_dataframe = pd.DataFrame(
                {
                    "open": [49000],
                    "high": [51000],
                    "low": [48000],
                    "close": [50000],
                    "volume": [1000],
                }
            )

            mock_data = {
                "symbol": "BTCUSDT",
                "price": 50000.0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            signal = strategy.on_data(mock_data, mock_dataframe)
            assert signal is not None
            assert signal.side == "buy"

            # 2. Validate trade through Capital Manager
            trade_request = TradeRequest(
                strategy_id=signal.strategy_id,
                symbol=signal.symbol,
                side="buy",
                quantity=0.01,
                price=signal.signal_price,
            )

            validation_response = await capital_manager.validate_trade(trade_request)
            assert validation_response.result.value == "approved"
            assert validation_response.approved_quantity > 0

            # 3. Execute trade through Exchange Connector
            connector = exchange_connector.get_connector("mock")

            order_request = OrderRequest(
                symbol=trade_request.symbol,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=validation_response.approved_quantity,
                price=trade_request.price,
            )

            order = await connector.place_order(order_request)
            assert order.id is not None
            assert order.symbol == "BTCUSDT"
            assert order.quantity == validation_response.approved_quantity

            # 4. Record trade execution
            execution_result = {
                "order_id": order.id,
                "status": "filled",
                "filled_quantity": order.quantity,
                "average_price": order.price or 50000.0,
                "fees": 1.0,
            }

            recorded = await capital_manager.record_trade_execution(
                trade_request, execution_result
            )
            assert recorded is True

        finally:
            # Cleanup
            await strategy.stop()
            await exchange_connector.stop()
            await capital_manager.stop()

    @pytest.mark.asyncio
    async def test_risk_management_integration(self, trading_system):
        """Test risk management across components."""
        capital_manager = trading_system["capital_manager"]

        await capital_manager.start()

        try:
            # Test large trade rejection
            large_trade = TradeRequest(
                strategy_id="test_strategy",
                symbol="BTCUSDT",
                side="buy",
                quantity=10.0,  # Very large quantity
                price=50000.0,
            )

            validation = await capital_manager.validate_trade(large_trade)

            # Should either be rejected or quantity reduced
            if validation.result.value == "approved":
                assert validation.approved_quantity < large_trade.quantity
                assert validation.warnings  # Should have warnings
            else:
                assert validation.result.value == "rejected"
                assert validation.reasons  # Should have rejection reasons

            # Test portfolio metrics
            metrics = await capital_manager.get_portfolio_metrics()
            assert metrics.total_value > 0
            assert metrics.available_cash >= 0

        finally:
            await capital_manager.stop()

    @pytest.mark.asyncio
    async def test_component_health_checks(self, trading_system):
        """Test health checks across all components."""
        core_engine = trading_system["core_engine"]
        capital_manager = trading_system["capital_manager"]
        exchange_connector = trading_system["exchange_connector"]
        strategy = trading_system["strategy"]

        # Start components
        await capital_manager.start()
        await exchange_connector.start()
        await strategy.start()

        try:
            # Test individual health checks
            capital_health = await capital_manager.health_check()
            assert capital_health["healthy"] is True
            assert capital_health["component"] == "capital_manager"

            exchange_health = await exchange_connector.health_check()
            assert "exchanges" in exchange_health
            assert "mock" in exchange_health["exchanges"]

            strategy_health = await strategy.health_check()
            assert strategy_health["healthy"] is True
            assert strategy_health["strategy_id"] == "test_strategy"

            # Test core engine health check (mocked)
            core_engine.strategy_manager = strategy
            core_engine.capital_manager = capital_manager
            core_engine.exchange_connector = exchange_connector
            core_engine._check_component_health = AsyncMock(return_value=True)

            core_health = await core_engine.health_check()
            assert "core_engine" in core_health
            assert "components" in core_health

        finally:
            await strategy.stop()
            await exchange_connector.stop()
            await capital_manager.stop()

    @pytest.mark.asyncio
    async def test_error_isolation(self, trading_system):
        """Test that component errors don't cascade."""
        capital_manager = trading_system["capital_manager"]
        exchange_connector = trading_system["exchange_connector"]

        await capital_manager.start()
        await exchange_connector.start()

        try:
            # Simulate exchange connector failure
            connector = exchange_connector.get_connector("mock")
            connector.is_connected = False

            # Capital manager should still function
            metrics = await capital_manager.get_portfolio_metrics()
            assert metrics is not None

            # Health checks should reflect component status
            capital_health = await capital_manager.health_check()
            assert capital_health["healthy"] is True

            exchange_health = await exchange_connector.health_check()
            # Should show degraded status but not crash
            assert "exchanges" in exchange_health

        finally:
            await exchange_connector.stop()
            await capital_manager.stop()

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_trade_validation(self, trading_system):
        """Test concurrent trade validation performance."""
        capital_manager = trading_system["capital_manager"]
        await capital_manager.start()

        try:
            # Create multiple concurrent trade requests
            trade_requests = [
                TradeRequest(
                    strategy_id=f"strategy_{i}",
                    symbol="BTCUSDT",
                    side="buy",
                    quantity=0.001,
                    price=50000.0,
                )
                for i in range(10)
            ]

            # Submit all trades concurrently
            import time

            start_time = time.time()

            validation_tasks = [
                capital_manager.validate_trade(request) for request in trade_requests
            ]

            results = await asyncio.gather(*validation_tasks)

            duration = time.time() - start_time

            # All should complete successfully
            assert len(results) == 10
            for result in results:
                assert result.result.value in ["approved", "rejected"]

            # Should complete in reasonable time (< 1 second)
            assert duration < 1.0, f"Concurrent validation took {duration:.3f}s"

        finally:
            await capital_manager.stop()


@pytest.mark.database
class TestDatabaseIntegration:
    """Database integration tests."""

    @pytest.mark.skipif(
        condition=True,  # Skip until database is implemented
        reason="Database integration not yet implemented",
    )
    @pytest.mark.asyncio
    async def test_trade_persistence(self):
        """Test trade data persistence."""
        # TODO: Implement when database integration is added
        pass


@pytest.mark.messagebus
class TestMessageBusIntegration:
    """Message bus integration tests."""

    @pytest.mark.skipif(
        condition=True,  # Skip until message bus is implemented
        reason="Message bus integration not yet implemented",
    )
    @pytest.mark.asyncio
    async def test_message_flow(self):
        """Test message flow between components."""
        # TODO: Implement when RabbitMQ integration is added
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
