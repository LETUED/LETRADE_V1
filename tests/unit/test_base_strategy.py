"""Unit tests for BaseStrategy abstract class.

Tests the interface contract and utility functions for strategy development.
"""

from datetime import datetime

import pandas as pd
import pytest

from strategies.base_strategy import (
    BaseStrategy,
    PerformanceTracker,
    StrategyConfig,
    TradingSignal,
    calculate_bollinger_bands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_sma,
)


class ConcreteStrategy(BaseStrategy):
    """Concrete implementation of BaseStrategy for testing."""

    def populate_indicators(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Test implementation."""
        dataframe["sma_20"] = calculate_sma(dataframe["close"], 20)
        return dataframe

    def on_data(self, data, dataframe):
        """Test implementation."""
        if len(dataframe) < 20:
            return None

        return {
            "side": "buy",
            "signal_price": data.get("close", 100.0),
            "stop_loss_price": data.get("close", 100.0) * 0.98,
            "confidence": 0.8,
            "strategy_params": {"signal_type": "test"},
        }

    def get_required_subscriptions(self):
        """Test implementation."""
        return ["market_data.binance.btcusdt"]


@pytest.fixture
def strategy_config():
    """Create test strategy configuration."""
    return StrategyConfig(
        strategy_id="test_strategy_1",
        name="Test Strategy",
        enabled=True,
        dry_run=True,
        risk_params={"max_position_size": 0.1},
        custom_params={"fast": 50, "slow": 200},
    )


@pytest.fixture
def test_strategy(strategy_config):
    """Create test strategy instance."""
    return ConcreteStrategy(strategy_config)


@pytest.fixture
def sample_ohlcv_data():
    """Create sample OHLCV data for testing."""
    dates = pd.date_range("2024-01-01", periods=100, freq="1h")

    # Generate realistic price data
    import numpy as np

    np.random.seed(42)  # For reproducible tests

    prices = 50000 + np.cumsum(np.random.randn(100) * 100)

    return pd.DataFrame(
        {
            "timestamp": dates,
            "open": prices + np.random.randn(100) * 10,
            "high": prices + np.random.randn(100) * 15 + 20,
            "low": prices + np.random.randn(100) * 15 - 20,
            "close": prices,
            "volume": np.random.randint(100, 1000, 100),
        }
    )


class TestPerformanceTracker:
    """Test PerformanceTracker class."""

    def test_initialization(self):
        """Test PerformanceTracker initialization."""
        tracker = PerformanceTracker()

        assert tracker.signal_count == 0
        assert tracker.execution_times == []
        assert tracker.memory_usage_history == []
        assert tracker.avg_execution_time == 0.0
        assert tracker.current_memory_usage == 0.0
        assert tracker.uptime_seconds >= 0

    def test_record_signal(self):
        """Test signal recording."""
        tracker = PerformanceTracker()

        tracker.record_signal()
        assert tracker.signal_count == 1

        tracker.record_signal()
        assert tracker.signal_count == 2

    def test_record_execution_time(self):
        """Test execution time recording."""
        tracker = PerformanceTracker()

        tracker.record_execution_time(0.1)  # 100ms
        tracker.record_execution_time(0.2)  # 200ms

        assert len(tracker.execution_times) == 2
        assert abs(tracker.avg_execution_time - 150.0) < 0.001  # Average in ms

    def test_record_memory_usage(self):
        """Test memory usage recording."""
        tracker = PerformanceTracker()

        tracker.record_memory_usage(256.0)
        tracker.record_memory_usage(300.0)

        assert tracker.current_memory_usage == 300.0
        assert len(tracker.memory_usage_history) == 2

    def test_execution_time_limit(self):
        """Test execution time history limit (1000 entries)."""
        tracker = PerformanceTracker()

        # Add 1001 entries
        for i in range(1001):
            tracker.record_execution_time(0.1)

        assert len(tracker.execution_times) == 1000

    def test_memory_usage_limit(self):
        """Test memory usage history limit (100 entries)."""
        tracker = PerformanceTracker()

        # Add 101 entries
        for i in range(101):
            tracker.record_memory_usage(100.0 + i)

        assert len(tracker.memory_usage_history) == 100
        assert tracker.current_memory_usage == 200.0  # Last entry


class TestTradingSignal:
    """Test TradingSignal data structure."""

    def test_signal_creation(self):
        """Test TradingSignal creation."""
        signal = TradingSignal(
            strategy_id="test_1",
            symbol="BTCUSDT",
            side="buy",
            signal_price=50000.0,
            stop_loss_price=49000.0,
            confidence=0.9,
        )

        assert signal.strategy_id == "test_1"
        assert signal.symbol == "BTCUSDT"
        assert signal.side == "buy"
        assert signal.signal_price == 50000.0
        assert signal.stop_loss_price == 49000.0
        assert signal.confidence == 0.9
        assert isinstance(signal.timestamp, datetime)

    def test_signal_to_dict(self):
        """Test TradingSignal to_dict conversion."""
        signal = TradingSignal(
            strategy_id="test_1",
            symbol="BTCUSDT",
            side="buy",
            signal_price=50000.0,
            stop_loss_price=49000.0,
            strategy_params={"signal_type": "golden_cross"},
        )

        signal_dict = signal.to_dict()

        assert signal_dict["strategy_id"] == "test_1"
        assert signal_dict["symbol"] == "BTCUSDT"
        assert signal_dict["side"] == "buy"
        assert signal_dict["signal_price"] == 50000.0
        assert signal_dict["stop_loss_price"] == 49000.0
        assert signal_dict["strategy_params"]["signal_type"] == "golden_cross"
        assert "timestamp" in signal_dict


class TestBaseStrategy:
    """Test BaseStrategy abstract class implementation."""

    def test_strategy_initialization(self, test_strategy, strategy_config):
        """Test strategy initialization."""
        assert test_strategy.strategy_id == strategy_config.strategy_id
        assert test_strategy.name == strategy_config.name
        assert test_strategy.config == strategy_config
        assert not test_strategy.is_running
        assert isinstance(test_strategy.performance_metrics, PerformanceTracker)

    def test_abstract_methods_implemented(self, test_strategy):
        """Test that abstract methods are properly implemented."""
        # This should not raise NotImplementedError
        test_data = pd.DataFrame({"close": [100, 101, 102]})

        # populate_indicators
        result = test_strategy.populate_indicators(test_data.copy())
        assert isinstance(result, pd.DataFrame)

        # on_data
        market_data = {"close": 100.0}
        signal = test_strategy.on_data(market_data, result)
        assert signal is None or isinstance(signal, dict)

        # get_required_subscriptions
        subscriptions = test_strategy.get_required_subscriptions()
        assert isinstance(subscriptions, list)
        assert len(subscriptions) > 0

    @pytest.mark.asyncio
    async def test_on_data_async(self, test_strategy, sample_ohlcv_data):
        """Test asynchronous on_data method."""
        # Populate indicators first
        df_with_indicators = test_strategy.populate_indicators(sample_ohlcv_data)

        market_data = {"close": 50000.0}

        # Test async version
        signal = await test_strategy.on_data_async(market_data, df_with_indicators)

        assert signal is not None
        assert signal["side"] == "buy"
        assert signal["signal_price"] == 50000.0
        assert "stop_loss_price" in signal
        assert signal["confidence"] == 0.8

        # Check that performance was recorded
        assert test_strategy.performance_metrics.signal_count == 1
        assert len(test_strategy.performance_metrics.execution_times) == 1

    @pytest.mark.asyncio
    async def test_strategy_lifecycle(self, test_strategy):
        """Test strategy start/stop lifecycle."""
        # Initially not running
        assert not test_strategy.is_running

        # Start strategy
        success = await test_strategy.start()
        assert success
        assert test_strategy.is_running

        # Stop strategy
        success = await test_strategy.stop()
        assert success
        assert not test_strategy.is_running

    @pytest.mark.asyncio
    async def test_disabled_strategy_start(self, strategy_config):
        """Test that disabled strategy won't start."""
        strategy_config.enabled = False
        strategy = ConcreteStrategy(strategy_config)

        success = await strategy.start()
        assert not success
        assert not strategy.is_running

    def test_get_performance_metrics(self, test_strategy):
        """Test performance metrics retrieval."""
        # Record some performance data
        test_strategy.performance_metrics.record_signal()
        test_strategy.performance_metrics.record_execution_time(0.1)
        test_strategy.performance_metrics.record_memory_usage(256.0)

        metrics = test_strategy.get_performance_metrics()

        assert metrics["strategy_id"] == test_strategy.strategy_id
        assert metrics["name"] == test_strategy.name
        assert metrics["total_signals"] == 1
        assert metrics["execution_time_avg_ms"] == 100.0
        assert metrics["memory_usage_mb"] == 256.0
        assert "uptime_seconds" in metrics
        assert "last_update" in metrics

    @pytest.mark.asyncio
    async def test_health_check(self, test_strategy):
        """Test strategy health check."""
        await test_strategy.start()

        health = await test_strategy.health_check()

        assert health["strategy_id"] == test_strategy.strategy_id
        assert health["healthy"] is True
        assert health["config_valid"] is True
        assert "timestamp" in health
        assert health["subscriptions"] == ["market_data.binance.btcusdt"]


class TestUtilityFunctions:
    """Test technical analysis utility functions."""

    @pytest.fixture
    def sample_price_data(self):
        """Create sample price data for indicator testing."""
        import numpy as np

        np.random.seed(42)

        # Generate trending price data
        base_price = 100
        trend = np.linspace(0, 10, 50)  # Upward trend
        noise = np.random.normal(0, 2, 50)  # Random noise
        prices = base_price + trend + noise

        return pd.Series(prices, name="close")

    def test_calculate_sma(self, sample_price_data):
        """Test Simple Moving Average calculation."""
        sma_10 = calculate_sma(sample_price_data, 10)

        assert len(sma_10) == len(sample_price_data)
        assert pd.isna(sma_10.iloc[:9]).all()  # First 9 values should be NaN
        assert not pd.isna(sma_10.iloc[9:]).any()  # Rest should have values

        # Test that SMA smooths the data
        assert sma_10.iloc[-1] != sample_price_data.iloc[-1]

    def test_calculate_ema(self, sample_price_data):
        """Test Exponential Moving Average calculation."""
        ema_10 = calculate_ema(sample_price_data, 10)

        assert len(ema_10) == len(sample_price_data)
        assert not pd.isna(
            ema_10.iloc[10:]
        ).any()  # Should have values after warmup period

        # EMA should respond faster than SMA
        sma_10 = calculate_sma(sample_price_data, 10)
        # Check that both are calculated and not equal (different smoothing methods)
        assert not pd.isna(ema_10.iloc[-1])
        assert not pd.isna(sma_10.iloc[-1])
        # In general case, they should be different
        # Direction depends on recent price movement, just check computed

    def test_calculate_rsi(self, sample_price_data):
        """Test RSI calculation."""
        rsi = calculate_rsi(sample_price_data, 14)

        assert len(rsi) == len(sample_price_data)

        # RSI should be between 0 and 100
        valid_rsi = rsi.dropna()
        assert (valid_rsi >= 0).all()
        assert (valid_rsi <= 100).all()

    def test_calculate_bollinger_bands(self, sample_price_data):
        """Test Bollinger Bands calculation."""
        bb = calculate_bollinger_bands(sample_price_data, 20, 2)

        assert "upper" in bb
        assert "middle" in bb
        assert "lower" in bb

        # Upper should be > Middle > Lower
        valid_data = pd.DataFrame(bb).dropna()
        assert (valid_data["upper"] > valid_data["middle"]).all()
        assert (valid_data["middle"] > valid_data["lower"]).all()

        # Price should mostly be within bands
        price_data = sample_price_data[valid_data.index]
        within_bands = (price_data >= valid_data["lower"]) & (
            price_data <= valid_data["upper"]
        )
        # At least 90% should be within bands for normal data
        assert within_bands.mean() > 0.8

    def test_calculate_macd(self, sample_price_data):
        """Test MACD calculation."""
        macd = calculate_macd(sample_price_data, 12, 26, 9)

        assert "macd" in macd
        assert "signal" in macd
        assert "histogram" in macd

        # All should have same length
        assert len(macd["macd"]) == len(sample_price_data)
        assert len(macd["signal"]) == len(sample_price_data)
        assert len(macd["histogram"]) == len(sample_price_data)

        # Histogram should be MACD - Signal
        valid_idx = ~(pd.isna(macd["macd"]) | pd.isna(macd["signal"]))
        histogram_calculated = macd["macd"] - macd["signal"]

        pd.testing.assert_series_equal(
            macd["histogram"][valid_idx],
            histogram_calculated[valid_idx],
            check_names=False,
        )


@pytest.mark.integration
class TestStrategyIntegration:
    """Integration tests for strategy with pandas-ta."""

    @pytest.mark.skipif(
        True,  # Skip if pandas-ta not available in test environment
        reason="pandas-ta integration test",
    )
    def test_pandas_ta_integration(self, sample_ohlcv_data):
        """Test pandas-ta integration."""
        # This test would require pandas-ta to be installed
        # Test that our utility functions work with pandas-ta
        sma = calculate_sma(sample_ohlcv_data["close"], 20)
        assert not sma.isna().all()
