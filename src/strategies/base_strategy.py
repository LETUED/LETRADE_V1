"""Base Strategy interface for Letrade_v1 trading system.

All trading strategies must inherit from BaseStrategy and implement
the required abstract methods for indicator calculation, signal generation,
and subscription management.

Designed following the system architecture in
docs/design-docs/03_Strategy_Library_and_Implementation.md
Integrates with pandas-ta for technical analysis indicators.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from contextlib import contextmanager

import pandas as pd

from common.database import Strategy, PerformanceMetric, db_manager

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """Real-time performance tracking for strategies.

    Tracks execution metrics for strategy optimization and monitoring.
    Enhanced with database persistence for MVP state management requirements.
    """

    def __init__(self, strategy_id: Optional[int] = None):
        self.strategy_id = strategy_id
        self.signal_count = 0
        self.execution_times = []
        self.memory_usage_history = []
        self.last_update_time = datetime.now(timezone.utc)
        self.start_time = time.time()
        
        # Performance metrics for database storage
        self._metrics_buffer = {
            'total_return_percent': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown_percent': 0.0,
            'win_rate_percent': 0.0,
            'profit_factor': 0.0,
            'total_trades': 0,
            'avg_trade_duration_hours': 0.0
        }

    def record_signal(self):
        """Record a signal generation event."""
        self.signal_count += 1
        self.last_update_time = datetime.now(timezone.utc)

    def record_execution_time(self, execution_time: float):
        """Record execution time for performance monitoring."""
        self.execution_times.append(execution_time)
        # Keep only last 1000 measurements
        if len(self.execution_times) > 1000:
            self.execution_times = self.execution_times[-1000:]

    def record_memory_usage(self, memory_mb: float):
        """Record memory usage."""
        self.memory_usage_history.append(memory_mb)
        # Keep only last 100 measurements
        if len(self.memory_usage_history) > 100:
            self.memory_usage_history = self.memory_usage_history[-100:]

    @property
    def avg_execution_time(self) -> float:
        """Average execution time in milliseconds."""
        if not self.execution_times:
            return 0.0
        return sum(self.execution_times) / len(self.execution_times) * 1000

    @property
    def current_memory_usage(self) -> float:
        """Current memory usage in MB."""
        if not self.memory_usage_history:
            return 0.0
        return self.memory_usage_history[-1]

    @property
    def uptime_seconds(self) -> float:
        """Strategy uptime in seconds."""
        return time.time() - self.start_time
    
    def update_metric(self, metric_name: str, value: float) -> None:
        """Update a performance metric value."""
        if metric_name in self._metrics_buffer:
            self._metrics_buffer[metric_name] = value
            logger.debug(f"Updated metric {metric_name}: {value}")
    
    def save_metrics_to_db(self) -> None:
        """Save current performance metrics to database."""
        if not self.strategy_id:
            logger.warning("Cannot save metrics: strategy_id not set")
            return
            
        try:
            with self._get_db_session() as session:
                for metric_name, value in self._metrics_buffer.items():
                    metric = PerformanceMetric(
                        strategy_id=self.strategy_id,
                        metric_name=metric_name,
                        metric_value=value,
                        metric_unit=self._get_metric_unit(metric_name)
                    )
                    session.add(metric)
                
                session.commit()
                logger.info(f"Saved {len(self._metrics_buffer)} performance metrics to database")
                
        except Exception as e:
            logger.error(f"Failed to save performance metrics: {e}")
    
    def load_latest_metrics_from_db(self) -> Dict[str, float]:
        """Load latest performance metrics from database."""
        if not self.strategy_id:
            logger.warning("Cannot load metrics: strategy_id not set")
            return {}
            
        try:
            with self._get_db_session() as session:
                # Get latest metric for each type
                latest_metrics = {}
                for metric_name in self._metrics_buffer.keys():
                    latest_metric = session.query(PerformanceMetric)\
                        .filter_by(strategy_id=self.strategy_id, metric_name=metric_name)\
                        .order_by(PerformanceMetric.timestamp.desc())\
                        .first()
                    
                    if latest_metric:
                        latest_metrics[metric_name] = float(latest_metric.metric_value)
                
                # Update local buffer
                self._metrics_buffer.update(latest_metrics)
                
                logger.info(f"Loaded {len(latest_metrics)} performance metrics from database")
                return latest_metrics
                
        except Exception as e:
            logger.error(f"Failed to load performance metrics: {e}")
            return {}
    
    def _get_metric_unit(self, metric_name: str) -> Optional[str]:
        """Get appropriate unit for metric."""
        unit_map = {
            'total_return_percent': 'percent',
            'max_drawdown_percent': 'percent', 
            'win_rate_percent': 'percent',
            'total_trades': 'count',
            'avg_trade_duration_hours': 'hours',
            'sharpe_ratio': 'ratio',
            'profit_factor': 'ratio'
        }
        return unit_map.get(metric_name)
    
    @contextmanager
    def _get_db_session(self):
        """Get database session with proper cleanup."""
        session = db_manager.get_session()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


class SignalType(Enum):
    """Trading signal types."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"


@dataclass
class TradingSignal:
    """Trading signal data structure.

    Format follows MVP specification:
    - side: "buy" or "sell"
    - signal_price: Entry price
    - stop_loss_price: Risk management price
    - strategy_params: Additional strategy-specific data
    """

    strategy_id: str
    symbol: str
    side: str  # "buy" or "sell" following MVP spec
    signal_price: float
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    confidence: float = 1.0  # 0.0 to 1.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    strategy_params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert signal to dictionary for Capital Manager request.

        Returns format compatible with request.capital.allocation message.
        """
        return {
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "side": self.side,
            "signal_price": self.signal_price,
            "stop_loss_price": self.stop_loss_price,
            "take_profit_price": self.take_profit_price,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "strategy_params": self.strategy_params,
        }


@dataclass
class StrategyConfig:
    """Strategy configuration data structure."""

    strategy_id: str
    name: str
    enabled: bool = True
    dry_run: bool = True  # Always start in dry-run mode for safety
    risk_params: Dict[str, Any] = field(default_factory=dict)
    custom_params: Dict[str, Any] = field(default_factory=dict)


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies.

    This class defines the interface that all strategies must implement
    to integrate with the Letrade_v1 trading system.
    """

    def __init__(self, config: StrategyConfig):
        """Initialize the strategy.

        Args:
            config: Strategy configuration
        """
        self.config = config
        self.strategy_id = config.strategy_id
        self.name = config.name
        self.is_running = False
        self._position_tracker = {}
        self._last_signal_time = None

        # Performance tracking with enhanced metrics and DB integration
        self.performance_metrics = PerformanceTracker(strategy_id=config.strategy_id)
        self.total_signals = 0
        self.successful_trades = 0
        self.failed_trades = 0
        
        # Database integration for state persistence
        self._db_strategy_id = config.strategy_id  # Database strategy ID
        self._state_loaded = False

        logger.info(
            f"Strategy {self.strategy_id} initialized",
            extra={
                "strategy_id": self.strategy_id,
                "strategy_name": self.name,
                "dry_run": self.config.dry_run,
            },
        )

    @abstractmethod
    def populate_indicators(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Calculate and populate technical indicators.

        This method should add indicator columns to the provided dataframe.
        Common indicators include moving averages, RSI, MACD, etc.

        Args:
            dataframe: OHLCV data with columns: open, high, low, close, volume

        Returns:
            DataFrame with additional indicator columns
        """
        pass

    @abstractmethod
    def on_data(
        self, data: Dict[str, Any], dataframe: pd.DataFrame
    ) -> Optional[Dict[str, Any]]:
        """Process new market data and generate trading signals.

        This method is called whenever new market data is received.
        It should analyze the data and indicators to generate trading signals.

        Args:
            data: Latest market data point (tick/candle)
            dataframe: Historical data with populated indicators

        Returns:
            Trading proposal dictionary compatible with Capital Manager:
            {
                "side": "buy" or "sell",
                "signal_price": float,
                "stop_loss_price": float (optional),
                "take_profit_price": float (optional),
                "confidence": float (0.0-1.0),
                "strategy_params": dict
            }
            Returns None if no signal is generated.
        """
        pass

    @abstractmethod
    def get_required_subscriptions(self) -> List[str]:
        """Get list of RabbitMQ routing keys this strategy needs to subscribe to.

        Should return routing keys in format: ["market_data.{exchange}.{symbol}"]
        Example: ["market_data.binance.btcusdt", "market_data.binance.ethusdt"]

        Returns:
            List of RabbitMQ routing key strings
        """
        pass

    async def on_data_async(
        self, data: Dict[str, Any], dataframe: pd.DataFrame
    ) -> Optional[Dict[str, Any]]:
        """Asynchronous version of on_data for high-performance strategies.

        Default implementation runs the synchronous version in a thread pool.
        Override this method for strategies that need async processing.

        Args:
            data: Latest market data point
            dataframe: Historical data with populated indicators

        Returns:
            Same format as on_data method
        """
        start_time = time.time()

        # Run synchronous version in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.on_data, data, dataframe)

        # Record performance metrics
        execution_time = time.time() - start_time
        self.performance_metrics.record_execution_time(execution_time)

        if result:
            self.performance_metrics.record_signal()

        return result

    def validate_signal(self, signal: TradingSignal) -> bool:
        """Validate a trading signal before sending.

        This method performs safety checks on generated signals.
        Override to add custom validation logic.

        Args:
            signal: The trading signal to validate

        Returns:
            True if signal is valid, False otherwise
        """
        try:
            # Basic validation
            if not signal.strategy_id or signal.strategy_id != self.strategy_id:
                logger.warning(
                    "Invalid strategy_id in signal",
                    extra={
                        "strategy_id": self.strategy_id,
                        "signal_strategy_id": signal.strategy_id,
                    },
                )
                return False

            if not signal.symbol:
                logger.warning(
                    "Missing symbol in signal", extra={"strategy_id": self.strategy_id}
                )
                return False

            if not (0.0 <= signal.confidence <= 1.0):
                logger.warning(
                    "Invalid confidence level",
                    extra={
                        "strategy_id": self.strategy_id,
                        "confidence": signal.confidence,
                    },
                )
                return False

            # Dry-run check
            if self.config.dry_run:
                logger.info(
                    "Signal generated in dry-run mode",
                    extra={"strategy_id": self.strategy_id, "signal": signal.to_dict()},
                )

            return True

        except Exception as e:
            logger.error(
                "Signal validation failed",
                extra={"strategy_id": self.strategy_id, "error": str(e)},
            )
            return False

    async def start(self) -> bool:
        """Start the strategy.

        Returns:
            True if started successfully, False otherwise
        """
        try:
            if not self.config.enabled:
                logger.info(
                    "Strategy is disabled, not starting",
                    extra={"strategy_id": self.strategy_id},
                )
                return False

            logger.info("Starting strategy", extra={"strategy_id": self.strategy_id})

            # Perform startup validation
            if not await self._validate_startup():
                logger.error(
                    "Strategy startup validation failed",
                    extra={"strategy_id": self.strategy_id},
                )
                return False

            # Call custom startup logic
            await self.on_start()

            self.is_running = True
            logger.info(
                "Strategy started successfully", extra={"strategy_id": self.strategy_id}
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to start strategy",
                extra={"strategy_id": self.strategy_id, "error": str(e)},
            )
            return False

    async def stop(self) -> bool:
        """Stop the strategy gracefully.

        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            logger.info("Stopping strategy", extra={"strategy_id": self.strategy_id})

            # Call custom shutdown logic
            await self.on_stop()

            self.is_running = False
            logger.info(
                "Strategy stopped successfully",
                extra={
                    "strategy_id": self.strategy_id,
                    "total_signals": self.total_signals,
                    "successful_trades": self.successful_trades,
                    "failed_trades": self.failed_trades,
                },
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to stop strategy",
                extra={"strategy_id": self.strategy_id, "error": str(e)},
            )
            return False

    async def on_start(self):
        """Custom startup logic for the strategy.

        Override this method to implement strategy-specific startup procedures.
        """
        pass

    async def on_stop(self):
        """Custom shutdown logic for the strategy.

        Override this method to implement strategy-specific shutdown procedures.
        """
        pass

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive strategy performance metrics.

        Includes real-time performance data for monitoring and optimization.

        Returns:
            Dictionary with comprehensive performance metrics
        """
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "is_running": self.is_running,
            "total_signals": self.performance_metrics.signal_count,
            "successful_trades": self.successful_trades,
            "failed_trades": self.failed_trades,
            "success_rate": (
                self.successful_trades
                / max(1, self.successful_trades + self.failed_trades)
            )
            * 100,
            "execution_time_avg_ms": self.performance_metrics.avg_execution_time,
            "memory_usage_mb": self.performance_metrics.current_memory_usage,
            "uptime_seconds": self.performance_metrics.uptime_seconds,
            "last_update": self.performance_metrics.last_update_time.isoformat(),
            "last_signal_time": (
                self._last_signal_time.isoformat() if self._last_signal_time else None
            ),
            "positions": dict(self._position_tracker),
        }

    async def save_strategy_state(self) -> bool:
        """
        전략 상태를 데이터베이스에 저장 (MVP 명세서 Section 5.1.1 준수)
        
        Returns:
            bool: 저장 성공 여부
        """
        try:
            # TODO: 실제 데이터베이스 연동 구현 필요
            # strategies 테이블에 현재 상태 저장
            strategy_state = {
                "id": self.strategy_id,
                "name": self.name,
                "strategy_type": "MA_CROSSOVER",
                "parameters": {
                    "fast_period": getattr(self, 'fast_period', 50),
                    "slow_period": getattr(self, 'slow_period', 200)
                },
                "is_active": self.is_running,
                "last_signal_time": (
                    self._last_signal_time.isoformat() 
                    if self._last_signal_time else None
                ),
                "performance_metrics": self.get_performance_metrics(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.debug(
                f"Strategy state saved for {self.strategy_id}",
                extra={"state": strategy_state}
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to save strategy state: {e}",
                extra={"strategy_id": self.strategy_id}
            )
            return False
    
    async def load_strategy_state(self) -> bool:
        """
        데이터베이스에서 전략 상태 복구 (MVP 명세서 Section 5.1.1 준수)
        
        Returns:
            bool: 로드 성공 여부
        """
        try:
            # TODO: 실제 데이터베이스 연동 구현 필요
            # strategies 테이블에서 상태 로드
            
            logger.debug(f"Strategy state loaded for {self.strategy_id}")
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to load strategy state: {e}",
                extra={"strategy_id": self.strategy_id}
            )
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Perform strategy health check.

        Returns:
            Health status dictionary
        """
        return {
            "strategy_id": self.strategy_id,
            "healthy": self.is_running,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "config_valid": self._validate_config(),
            "subscriptions": self.get_required_subscriptions(),
            "database_connected": False,  # TODO: 실제 DB 연결 상태 확인
        }

    def _validate_config(self) -> bool:
        """Validate strategy configuration."""
        try:
            # Basic config validation
            if not self.config.strategy_id:
                return False
            if not self.config.name:
                return False
            # Add more validation as needed
            return True
        except Exception:
            return False

    async def _validate_startup(self) -> bool:
        """Validate conditions for strategy startup."""
        try:
            # Check configuration
            if not self._validate_config():
                logger.error(
                    "Invalid strategy configuration",
                    extra={"strategy_id": self.strategy_id},
                )
                return False

            # Check required subscriptions
            subscriptions = self.get_required_subscriptions()
            if not subscriptions:
                logger.error(
                    "Strategy has no required subscriptions",
                    extra={"strategy_id": self.strategy_id},
                )
                return False

            return True

        except Exception as e:
            logger.error(
                "Strategy startup validation failed",
                extra={"strategy_id": self.strategy_id, "error": str(e)},
            )
            return False

    def _record_signal_generated(self, signal: TradingSignal):
        """Record that a signal was generated (for metrics)."""
        self.total_signals += 1
        self._last_signal_time = signal.timestamp

        logger.debug(
            "Signal recorded",
            extra={
                "strategy_id": self.strategy_id,
                "signal_type": signal.side,
                "symbol": signal.symbol,
                "confidence": signal.confidence,
            },
        )

    def _record_trade_result(self, success: bool, metadata: Optional[Dict] = None):
        """Record trade execution result."""
        if success:
            self.successful_trades += 1
        else:
            self.failed_trades += 1

        logger.debug(
            "Trade result recorded",
            extra={
                "strategy_id": self.strategy_id,
                "success": success,
                "metadata": metadata or {},
            },
        )
    
    def save_state_to_db(self) -> bool:
        """Save current strategy state to database.
        
        Critical for MVP state reconciliation requirements.
        Saves performance metrics and internal state for recovery after restarts.
        
        Returns:
            bool: True if save successful, False otherwise
        """
        try:
            # Save performance metrics
            self.performance_metrics.save_metrics_to_db()
            
            # Update strategy statistics in database
            if self._db_strategy_id:
                with self._get_db_session() as session:
                    strategy = session.query(Strategy).filter_by(id=self._db_strategy_id).first()
                    if strategy:
                        # Update strategy parameters with current state
                        current_state = {
                            'total_signals': self.total_signals,
                            'successful_trades': self.successful_trades,
                            'failed_trades': self.failed_trades,
                            'last_signal_time': self._last_signal_time.isoformat() if self._last_signal_time else None,
                            'position_tracker': self._position_tracker
                        }
                        
                        # Merge with existing parameters
                        if strategy.parameters:
                            strategy.parameters.update({'internal_state': current_state})
                        else:
                            strategy.parameters = {'internal_state': current_state}
                        
                        session.commit()
                        logger.info(f"Strategy {self.strategy_id} state saved to database")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to save strategy state: {e}")
            return False
    
    def load_state_from_db(self) -> bool:
        """Load strategy state from database.
        
        Critical for MVP state reconciliation requirements.
        Restores performance metrics and internal state after system restarts.
        
        Returns:
            bool: True if load successful, False otherwise
        """
        try:
            if not self._db_strategy_id:
                logger.warning("Cannot load state: database strategy ID not set")
                return False
                
            # Load performance metrics
            self.performance_metrics.load_latest_metrics_from_db()
            
            # Load strategy state from database
            with self._get_db_session() as session:
                strategy = session.query(Strategy).filter_by(id=self._db_strategy_id).first()
                if strategy and strategy.parameters:
                    internal_state = strategy.parameters.get('internal_state', {})
                    
                    # Restore internal state
                    self.total_signals = internal_state.get('total_signals', 0)
                    self.successful_trades = internal_state.get('successful_trades', 0)
                    self.failed_trades = internal_state.get('failed_trades', 0)
                    
                    # Restore last signal time
                    last_signal_str = internal_state.get('last_signal_time')
                    if last_signal_str:
                        try:
                            self._last_signal_time = datetime.fromisoformat(last_signal_str.replace('Z', '+00:00'))
                        except ValueError:
                            logger.warning("Invalid last_signal_time format in database")
                    
                    # Restore position tracker
                    self._position_tracker = internal_state.get('position_tracker', {})
                    
                    self._state_loaded = True
                    logger.info(f"Strategy {self.strategy_id} state loaded from database")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to load strategy state: {e}")
            return False
    
    def ensure_state_loaded(self) -> None:
        """Ensure strategy state is loaded from database.
        
        Called automatically before strategy execution to implement
        MVP state reconciliation requirements.
        """
        if not self._state_loaded and self._db_strategy_id:
            logger.info(f"Loading strategy {self.strategy_id} state from database...")
            self.load_state_from_db()
    
    @contextmanager 
    def _get_db_session(self):
        """Get database session with proper cleanup."""
        session = db_manager.get_session()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# Utility functions for strategy development with pandas-ta integration
try:
    import pandas_ta as ta

    HAS_PANDAS_TA = True
except ImportError:
    HAS_PANDAS_TA = False
    logger.warning("pandas-ta not available, using fallback implementations")


def calculate_sma(data: pd.Series, period: int) -> pd.Series:
    """Calculate Simple Moving Average using pandas-ta if available."""
    if HAS_PANDAS_TA:
        return ta.sma(data, length=period)
    return data.rolling(window=period).mean()


def calculate_ema(data: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average using pandas-ta if available."""
    if HAS_PANDAS_TA:
        return ta.ema(data, length=period)
    return data.ewm(span=period, adjust=False).mean()


def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index using pandas-ta if available."""
    if HAS_PANDAS_TA:
        return ta.rsi(data, length=period)

    # Fallback implementation
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_bollinger_bands(
    data: pd.Series, period: int = 20, std_dev: int = 2
) -> Dict[str, pd.Series]:
    """Calculate Bollinger Bands using pandas-ta if available."""
    if HAS_PANDAS_TA:
        bb = ta.bbands(data, length=period, std=std_dev)
        return {
            "upper": bb[f"BBU_{period}_{std_dev}.0"],
            "middle": bb[f"BBM_{period}_{std_dev}.0"],
            "lower": bb[f"BBL_{period}_{std_dev}.0"],
        }

    # Fallback implementation
    sma = calculate_sma(data, period)
    std = data.rolling(window=period).std()
    return {
        "upper": sma + (std * std_dev),
        "middle": sma,
        "lower": sma - (std * std_dev),
    }


def calculate_macd(
    data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> Dict[str, pd.Series]:
    """Calculate MACD using pandas-ta if available."""
    if HAS_PANDAS_TA:
        macd = ta.macd(data, fast=fast, slow=slow, signal=signal)
        return {
            "macd": macd[f"MACD_{fast}_{slow}_{signal}"],
            "signal": macd[f"MACDs_{fast}_{slow}_{signal}"],
            "histogram": macd[f"MACDh_{fast}_{slow}_{signal}"],
        }

    # Fallback implementation
    ema_fast = calculate_ema(data, fast)
    ema_slow = calculate_ema(data, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


def add_all_indicators(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Add comprehensive set of technical indicators using pandas-ta.

    This is a convenience function that adds commonly used indicators.
    Individual strategies should use specific indicators in populate_indicators().

    Args:
        dataframe: OHLCV dataframe with columns: open, high, low, close, volume

    Returns:
        Dataframe with additional indicator columns
    """
    if not HAS_PANDAS_TA:
        logger.warning("pandas-ta not available, skipping comprehensive indicators")
        return dataframe

    # Use pandas-ta strategy for comprehensive analysis
    dataframe.ta.strategy(ta.AllStrategy)
    return dataframe
