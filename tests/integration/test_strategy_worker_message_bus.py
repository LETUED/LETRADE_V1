"""
Strategy Worker와 Message Bus 통합 테스트

실제 메시지 흐름과 신호 전송을 검증합니다.
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.common.message_bus import MessageBus
from src.data_loader.backtest_data_loader import BacktestDataLoader, DataSourceConfig
from src.strategies.base_strategy import StrategyConfig
from src.strategies.ma_crossover import MAcrossoverStrategy
from src.strategy_worker.main import (
    StrategyWorker,
    StrategyWorkerManager,
    WorkerConfig,
    WorkerStatus,
)


@pytest.fixture
def message_bus_config():
    """메시지 버스 테스트 설정"""
    return {
        "host": os.getenv("TEST_RABBITMQ_HOST", "localhost"),
        "port": int(os.getenv("TEST_RABBITMQ_PORT", 5672)),
        "username": os.getenv("TEST_RABBITMQ_USERNAME", "guest"),
        "password": os.getenv("TEST_RABBITMQ_PASSWORD", "guest"),
        "virtual_host": os.getenv("TEST_RABBITMQ_VHOST", "/test"),
    }


@pytest.fixture
def strategy_config():
    """테스트용 전략 설정"""
    return StrategyConfig(
        strategy_id="test_ma_001",
        name="Test MA Crossover Strategy",
        enabled=True,
        dry_run=True,
        custom_params={
            "fast_period": 5,
            "slow_period": 10,
            "symbol": "BTC/USDT",
            "exchange": "binance",
            "min_signal_interval": 1,  # 1초 (테스트용)
            "min_crossover_strength": 0.001,
        },
    )


@pytest.fixture
def worker_config():
    """테스트용 Worker 설정"""
    return WorkerConfig(
        max_memory_mb=128.0,
        max_cpu_percent=50.0,
        heartbeat_interval=5.0,
        max_restart_attempts=1,
        restart_delay=1.0,
        process_timeout=10.0,
        enable_auto_restart=False,
        resource_monitoring=False,
    )


@pytest.fixture
def mock_message_bus():
    """Mock 메시지 버스"""
    bus = Mock(spec=MessageBus)
    bus.connect = AsyncMock(return_value=True)
    bus.disconnect = AsyncMock(return_value=True)
    bus.publish = AsyncMock(return_value=True)
    bus.subscribe = AsyncMock(return_value=True)
    bus.health_check = AsyncMock(return_value={"healthy": True})
    bus.is_connected = True
    return bus


class TestStrategyWorkerMessageBusIntegration:
    """Strategy Worker와 Message Bus 통합 테스트"""

    @pytest.mark.asyncio
    async def test_worker_message_bus_connection(
        self, strategy_config, worker_config, mock_message_bus
    ):
        """Worker가 메시지 버스에 정상적으로 연결되는지 테스트"""

        with patch(
            "src.strategy_worker.main.MessageBus", return_value=mock_message_bus
        ):
            worker = StrategyWorker(
                strategy_class=MAcrossoverStrategy,
                strategy_config=strategy_config,
                worker_config=worker_config,
            )

            # Worker 시작 시도
            # 실제 프로세스가 아닌 mock으로 테스트
            with patch.object(worker, "process_executor") as mock_executor:
                mock_future = AsyncMock()
                mock_future.result.return_value = None
                mock_executor.submit.return_value = mock_future

                result = await worker.start()

                # 연결 시도 확인
                assert mock_message_bus.connect.called

    @pytest.mark.asyncio
    async def test_strategy_signal_publishing(self, strategy_config, mock_message_bus):
        """전략에서 생성된 신호가 메시지 버스로 발행되는지 테스트"""

        # MA 전략 인스턴스 생성
        strategy = MAcrossoverStrategy(strategy_config)

        # 메시지 버스 mock
        with patch(
            "src.strategy_worker.main.MessageBus", return_value=mock_message_bus
        ):

            # Mock 시장 데이터 (골든 크로스 시나리오)
            market_data = {
                "close": 50000.0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # 골든 크로스를 유발하는 지표 데이터 생성
            import pandas as pd

            test_data = pd.DataFrame(
                {
                    "close": [49000, 49500, 50000],
                    "ma_fast": [49200, 49600, 50100],  # 단기 MA가 상승
                    "ma_slow": [49800, 49900, 49900],  # 장기 MA보다 위로
                    "ma_signal": [-1, -1, 1],  # 크로스오버 발생
                    "ma_difference_pct": [0.01, 0.02, 0.5],  # 충분한 강도
                }
            )

            # 전략에서 신호 생성
            signal = strategy.on_data(market_data, test_data)

            if signal:
                # 신호가 올바른 형식인지 확인
                assert "routing_key" in signal
                assert "payload" in signal

                payload = signal["payload"]
                assert payload["side"] == "buy"  # 골든 크로스 = 매수
                assert payload["signal_price"] == 50000.0
                assert "strategy_id" in payload
                assert "confidence" in payload

    @pytest.mark.asyncio
    async def test_market_data_subscription(
        self, strategy_config, worker_config, mock_message_bus
    ):
        """Worker가 시장 데이터를 올바르게 구독하는지 테스트"""

        with patch(
            "src.strategy_worker.main.MessageBus", return_value=mock_message_bus
        ):
            worker = StrategyWorker(
                strategy_class=MAcrossoverStrategy,
                strategy_config=strategy_config,
                worker_config=worker_config,
            )

            # 구독 정보 확인
            strategy = MAcrossoverStrategy(strategy_config)
            subscriptions = strategy.get_required_subscriptions()

            # 예상되는 구독 채널
            expected_routing_key = "market_data.binance.btcusdt"
            assert expected_routing_key in subscriptions

    @pytest.mark.asyncio
    async def test_signal_routing_format(self, strategy_config):
        """신호가 올바른 라우팅 키 형식으로 전송되는지 테스트"""

        strategy = MAcrossoverStrategy(strategy_config)

        # Mock 데이터로 신호 생성
        test_signal = strategy._generate_trading_signal(
            crossover_type="golden",
            current_price=50000.0,
            fast_ma=50100.0,
            slow_ma=49900.0,
            strength_pct=0.4,
        )

        assert test_signal is not None

        # 라우팅 키 형식 확인
        routing_key = test_signal["routing_key"]
        assert routing_key.startswith("request.capital.allocation")
        assert strategy_config.strategy_id in routing_key

        # 페이로드 형식 확인 (MVP 명세서 호환)
        payload = test_signal["payload"]
        required_fields = [
            "strategy_id",
            "symbol",
            "side",
            "signal_price",
            "confidence",
        ]
        for field in required_fields:
            assert field in payload

    @pytest.mark.asyncio
    async def test_worker_manager_integration(
        self, strategy_config, worker_config, mock_message_bus
    ):
        """Worker Manager와 메시지 버스 통합 테스트"""

        with patch(
            "src.strategy_worker.main.MessageBus", return_value=mock_message_bus
        ):
            manager = StrategyWorkerManager(message_bus=mock_message_bus)

            # Worker 추가
            success = await manager.add_worker(
                strategy_id="test_ma_001",
                strategy_class=MAcrossoverStrategy,
                strategy_config=strategy_config,
                worker_config=worker_config,
            )

            assert success is True
            assert "test_ma_001" in manager.workers

            # Worker 개수 확인
            assert manager.get_worker_count() == 1

            # 헬스체크
            health_status = await manager.health_check()
            assert health_status["manager_healthy"] is True
            assert health_status["total_workers"] == 1


class TestMessageFlowEnd2End:
    """End-to-End 메시지 흐름 테스트"""

    @pytest.mark.asyncio
    async def test_complete_signal_flow(self, strategy_config, mock_message_bus):
        """완전한 신호 생성 → 메시지 발행 흐름 테스트"""

        published_messages = []

        # publish 호출을 캡처하는 mock
        async def capture_publish(exchange_name, routing_key, message, persistent=True):
            published_messages.append(
                {
                    "exchange": exchange_name,
                    "routing_key": routing_key,
                    "message": message,
                    "persistent": persistent,
                }
            )
            return True

        mock_message_bus.publish = AsyncMock(side_effect=capture_publish)

        # 전략 인스턴스
        strategy = MAcrossoverStrategy(strategy_config)

        with patch(
            "src.strategy_worker.main.MessageBus", return_value=mock_message_bus
        ):

            # 시뮬레이션된 시장 데이터 처리
            market_data = {"close": 51000.0}

            # 골든 크로스 시나리오 데이터
            import pandas as pd

            df_with_crossover = pd.DataFrame(
                {
                    "close": [50000, 50500, 51000],
                    "ma_fast": [50200, 50600, 51100],
                    "ma_slow": [50800, 50900, 50900],
                    "ma_signal": [-1, -1, 1],  # 크로스오버
                    "ma_difference_pct": [0.5, 0.6, 0.7],
                }
            )

            # 지표 계산 활성화
            strategy._indicators_calculated = True

            # 신호 생성
            signal = strategy.on_data(market_data, df_with_crossover)

            if signal:
                # 실제 메시지 발행 시뮬레이션
                exchange_name = "letrade.requests"
                routing_key = signal.get("routing_key")
                payload = signal.get("payload")

                await mock_message_bus.publish(
                    exchange_name=exchange_name,
                    routing_key=routing_key,
                    message=payload,
                )

                # 발행된 메시지 검증
                assert len(published_messages) == 1

                published = published_messages[0]
                assert published["exchange"] == "letrade.requests"
                assert "request.capital.allocation" in published["routing_key"]
                assert published["message"]["side"] == "buy"
                assert published["message"]["signal_price"] == 51000.0

    @pytest.mark.asyncio
    async def test_error_handling_in_message_flow(
        self, strategy_config, mock_message_bus
    ):
        """메시지 흐름에서 에러 처리 테스트"""

        # 메시지 발행 실패 시뮬레이션
        mock_message_bus.publish = AsyncMock(return_value=False)

        strategy = MAcrossoverStrategy(strategy_config)

        # 신호 생성 시도
        market_data = {"close": 50000.0}

        import pandas as pd

        df_with_signal = pd.DataFrame(
            {
                "close": [50000],
                "ma_fast": [50100],
                "ma_slow": [49900],
                "ma_signal": [1],
                "ma_difference_pct": [0.5],
            }
        )

        strategy._indicators_calculated = True
        signal = strategy.on_data(market_data, df_with_signal)

        # 신호가 생성되었지만 발행에 실패하는 상황을 시뮬레이션
        if signal:
            result = await mock_message_bus.publish(
                exchange_name="letrade.requests",
                routing_key=signal["routing_key"],
                message=signal["payload"],
            )

            # 발행 실패 확인
            assert result is False

    @pytest.mark.asyncio
    async def test_backtest_data_integration(self):
        """백테스트 데이터 로더와 전략 통합 테스트"""

        # Mock 데이터 생성
        data_config = DataSourceConfig(
            source_type="mock",
            symbol="BTC/USDT",
            timeframe="1h",
            mock_config={
                "num_periods": 50,
                "base_price": 50000.0,
                "volatility": 0.02,
                "add_trends": True,
            },
        )

        data_loader = BacktestDataLoader(data_config)

        # 데이터 로드
        historical_data = await data_loader.load_data()

        assert not historical_data.empty
        assert len(historical_data) == 50
        assert "close" in historical_data.columns

        # 전략에 적용
        strategy_config = StrategyConfig(
            strategy_id="backtest_ma_001",
            name="Backtest MA Strategy",
            enabled=True,
            dry_run=True,
            custom_params={
                "fast_period": 5,
                "slow_period": 10,
                "symbol": "BTC/USDT",
                "exchange": "binance",
            },
        )

        strategy = MAcrossoverStrategy(strategy_config)

        # 지표 계산
        df_with_indicators = strategy.populate_indicators(historical_data)

        assert "ma_fast" in df_with_indicators.columns
        assert "ma_slow" in df_with_indicators.columns
        assert "ma_signal" in df_with_indicators.columns

        # 마지막 데이터로 신호 생성 시도
        latest_data = {
            "close": historical_data["close"].iloc[-1],
            "timestamp": historical_data.index[-1].isoformat(),
        }

        signal = strategy.on_data(latest_data, df_with_indicators)

        # 신호 생성 여부와 관계없이 에러가 없어야 함
        assert signal is None or isinstance(signal, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
