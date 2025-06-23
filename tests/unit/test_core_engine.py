"""Unit tests for Core Engine module."""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from core_engine.main import CoreEngine, SystemStatus  # noqa: E402


class TestCoreEngine:
    """Test cases for Core Engine."""

    def test_initialization(self):
        """Test Core Engine initialization."""
        engine = CoreEngine()
        assert engine is not None
        assert isinstance(engine.status, SystemStatus)
        assert engine.status.is_running is False
        assert engine.config == {}

    def test_initialization_with_config(self):
        """Test Core Engine initialization with config."""
        config = {"test": "value", "log_level": "DEBUG"}
        engine = CoreEngine(config=config)
        assert engine.config == config

    @pytest.mark.asyncio
    async def test_start_success(self):
        """Test successful Core Engine startup."""
        engine = CoreEngine()

        # Mock the private methods
        engine._validate_startup_conditions = AsyncMock(return_value=True)
        engine._initialize_subsystems = AsyncMock()
        engine._start_background_tasks = AsyncMock()
        engine._perform_startup_reconciliation = AsyncMock()

        result = await engine.start()

        assert result is True
        assert engine.status.is_running is True
        assert engine.status.start_time is not None

    @pytest.mark.asyncio
    async def test_start_validation_failure(self):
        """Test Core Engine startup with validation failure."""
        engine = CoreEngine()

        # Mock validation to fail
        engine._validate_startup_conditions = AsyncMock(return_value=False)
        engine._emergency_shutdown = AsyncMock()

        result = await engine.start()

        assert result is False
        assert engine.status.is_running is False
        # Note: _emergency_shutdown is called in exception handler,
        # not in validation failure path

    @pytest.mark.asyncio
    async def test_stop_success(self):
        """Test successful Core Engine shutdown."""
        engine = CoreEngine()

        # Setup running state
        engine.status.is_running = True

        # Mock the private methods
        engine._stop_new_operations = AsyncMock()
        engine._wait_for_active_operations = AsyncMock()
        engine._stop_background_tasks = AsyncMock()
        engine._shutdown_subsystems = AsyncMock()
        engine._persist_final_state = AsyncMock()

        result = await engine.stop()

        assert result is True
        assert engine.status.is_running is False

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test Core Engine health check."""
        engine = CoreEngine()
        engine.status.is_running = True

        # Mock component health checks
        engine._check_component_health = AsyncMock(return_value=True)

        health_result = await engine.health_check()

        assert "core_engine" in health_result
        assert "timestamp" in health_result
        assert "components" in health_result
        assert "overall_health" in health_result

    def test_get_status(self):
        """Test status retrieval."""
        engine = CoreEngine()
        engine.status.is_running = True
        engine.status.total_trades = 5

        status = engine.get_status()

        assert "is_running" in status
        assert status["is_running"] is True
        assert "total_trades" in status
        assert status["total_trades"] == 5

    @pytest.mark.asyncio
    async def test_emergency_shutdown(self):
        """Test emergency shutdown procedures."""
        engine = CoreEngine()
        engine.status.is_running = True
        engine._tasks = [Mock(), Mock()]

        await engine._emergency_shutdown()

        assert engine.status.is_running is False
        assert engine._shutdown_event.is_set()

        # Verify tasks were cancelled
        for task in engine._tasks:
            task.cancel.assert_called_once()


class TestCoreEngineIntegration:
    """Integration test cases for Core Engine."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test complete Core Engine lifecycle."""
        engine = CoreEngine({"test_mode": True})

        # Mock all external dependencies
        engine._validate_startup_conditions = AsyncMock(return_value=True)
        engine._initialize_subsystems = AsyncMock()
        engine._start_background_tasks = AsyncMock()
        engine._perform_startup_reconciliation = AsyncMock()
        engine._stop_new_operations = AsyncMock()
        engine._wait_for_active_operations = AsyncMock()
        engine._stop_background_tasks = AsyncMock()
        engine._shutdown_subsystems = AsyncMock()
        engine._persist_final_state = AsyncMock()

        # Test startup
        assert await engine.start() is True
        assert engine.status.is_running is True

        # Test health check while running
        health = await engine.health_check()
        assert health["core_engine"] is True

        # Test shutdown
        assert await engine.stop() is True
        assert engine.status.is_running is False


class TestCoreEngineTradingSafety:
    """Trading system safety tests for Core Engine."""

    def test_no_hardcoded_secrets(self):
        """Ensure no hardcoded API keys or secrets."""
        import inspect

        import src.core_engine.main as module

        source = inspect.getsource(module)

        # Check for common secret patterns
        forbidden_patterns = [
            "api_key=",
            "secret=",
            "password=",
            "binance_key",
            "coinbase_key",
        ]

        for pattern in forbidden_patterns:
            assert (
                pattern not in source.lower()
            ), f"Hardcoded secret pattern detected: {pattern}"

    @pytest.mark.asyncio
    async def test_graceful_shutdown_on_error(self):
        """Test that errors don't crash the system ungracefully."""
        engine = CoreEngine()

        # Mock startup to succeed but background task to fail
        engine._validate_startup_conditions = AsyncMock(return_value=True)
        engine._initialize_subsystems = AsyncMock()
        engine._perform_startup_reconciliation = AsyncMock()

        # Mock background tasks to raise exception
        async def failing_task():
            raise Exception("Simulated background task failure")

        engine._start_background_tasks = AsyncMock()
        engine._tasks = [asyncio.create_task(failing_task())]

        # Start engine
        await engine.start()

        # Wait a bit for background task to fail
        await asyncio.sleep(0.1)

        # Engine should still be able to shutdown gracefully
        engine._stop_new_operations = AsyncMock()
        engine._wait_for_active_operations = AsyncMock()
        engine._stop_background_tasks = AsyncMock()
        engine._shutdown_subsystems = AsyncMock()
        engine._persist_final_state = AsyncMock()

        result = await engine.stop()
        assert result is True

    @pytest.mark.asyncio
    async def test_component_isolation(self):
        """Test that component failures don't affect Core Engine."""
        engine = CoreEngine()

        # Mock a failing component
        failing_component = Mock()
        failing_component.health_check = AsyncMock(
            side_effect=Exception("Component failed")
        )
        engine.strategy_manager = failing_component

        # Health check should not raise exception
        health_result = await engine.health_check()

        # Core engine should still report as healthy
        assert "core_engine" in health_result
        assert health_result["components"]["strategy_manager"] is False


@pytest.mark.performance
class TestCoreEnginePerformance:
    """Performance tests for Core Engine."""

    @pytest.mark.asyncio
    async def test_startup_performance(self):
        """Test Core Engine startup performance."""

        async def startup_test():
            engine = CoreEngine()

            # Mock dependencies for fast startup
            engine._validate_startup_conditions = AsyncMock(return_value=True)
            engine._initialize_subsystems = AsyncMock()
            engine._start_background_tasks = AsyncMock()
            engine._perform_startup_reconciliation = AsyncMock()
            engine._stop_new_operations = AsyncMock()
            engine._wait_for_active_operations = AsyncMock()
            engine._stop_background_tasks = AsyncMock()
            engine._shutdown_subsystems = AsyncMock()
            engine._persist_final_state = AsyncMock()

            result = await engine.start()
            await engine.stop()
            return result

        # Test should complete within reasonable time
        import time

        start_time = time.time()
        result = await startup_test()
        duration = time.time() - start_time

        assert result is True
        assert duration < 1.0, f"Startup took {duration:.3f}s, should be < 1.0s"

    @pytest.mark.asyncio
    async def test_health_check_performance(self):
        """Test health check performance."""
        engine = CoreEngine()
        engine.status.is_running = True

        # Mock component health checks
        engine._check_component_health = AsyncMock(return_value=True)

        import time

        start_time = time.time()

        # Health check should be fast (< 100ms)
        await engine.health_check()

        duration = time.time() - start_time
        assert duration < 0.1, f"Health check took {duration:.3f}s, should be < 0.1s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
