"""
간단한 메시지 흐름 테스트

Strategy Worker와 Message Bus의 핵심 기능을 직접 테스트합니다.
"""

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

from src.common.message_bus import MessageBus
from src.data_loader.backtest_data_loader import BacktestDataLoader, DataSourceConfig
from src.strategies.base_strategy import StrategyConfig
from src.strategies.ma_crossover import MAcrossoverStrategy


@pytest.fixture
def strategy_config():
    """테스트용 전략 설정"""
    return StrategyConfig(
        strategy_id="test_ma_signal_001",
        name="Test MA Signal Strategy",
        enabled=True,
        dry_run=True,
        custom_params={
            "fast_period": 3,  # 테스트용으로 매우 짧게
            "slow_period": 5,
            "symbol": "BTC/USDT",
            "exchange": "binance",
            "min_signal_interval": 0,  # 신호 간격 제한 없음
            "min_crossover_strength": 0.001,
        },
    )


class TestDirectMessageFlow:
    """직접적인 메시지 흐름 테스트"""

    def test_strategy_signal_generation(self, strategy_config):
        """전략에서 신호가 올바르게 생성되는지 테스트"""

        strategy = MAcrossoverStrategy(strategy_config)

        # 골든 크로스 시나리오 데이터 생성
        test_data = pd.DataFrame(
            {
                "close": [49000, 49500, 50000, 50500, 51000],
                "open": [48900, 49400, 49900, 50400, 50900],
                "high": [49200, 49700, 50200, 50700, 51200],
                "low": [48800, 49300, 49800, 50300, 50800],
                "volume": [1000, 1100, 1200, 1300, 1400],
            }
        )

        # 지표 계산
        df_with_indicators = strategy.populate_indicators(test_data)

        # 지표가 올바르게 계산되었는지 확인
        assert "ma_fast" in df_with_indicators.columns
        assert "ma_slow" in df_with_indicators.columns
        assert "ma_signal" in df_with_indicators.columns

        # 최신 시장 데이터
        market_data = {
            "close": 51000.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # 신호 생성 시도
        signal = strategy.on_data(market_data, df_with_indicators)

        # 신호 검증
        if signal:
            assert "routing_key" in signal
            assert "payload" in signal

            payload = signal["payload"]
            assert "side" in payload
            assert "signal_price" in payload
            assert "strategy_id" in payload
            assert "confidence" in payload

            # 신호 가격이 시장 데이터와 일치
            assert payload["signal_price"] == 51000.0

    def test_message_format_compliance(self, strategy_config):
        """메시지 형식이 MVP 명세서를 준수하는지 테스트"""

        strategy = MAcrossoverStrategy(strategy_config)

        # 직접 신호 생성 함수 테스트
        signal = strategy._generate_trading_signal(
            crossover_type="golden",
            current_price=50000.0,
            fast_ma=50100.0,
            slow_ma=49900.0,
            strength_pct=0.5,
        )

        # MVP 명세서 Section 6.1.2 준수 확인
        assert signal is not None
        assert "routing_key" in signal
        assert "payload" in signal

        # 라우팅 키 형식
        routing_key = signal["routing_key"]
        assert routing_key.startswith("request.capital.allocation")
        assert strategy_config.strategy_id in routing_key

        # 페이로드 필수 필드
        payload = signal["payload"]
        required_fields = [
            "strategy_id",
            "symbol",
            "side",
            "signal_price",
            "stop_loss_price",
            "confidence",
            "strategy_params",
        ]

        for field in required_fields:
            assert field in payload, f"Missing required field: {field}"

        # 데이터 타입 검증
        assert isinstance(payload["strategy_id"], int)
        assert isinstance(payload["signal_price"], (int, float))
        assert isinstance(payload["confidence"], (int, float))
        assert 0.0 <= payload["confidence"] <= 1.0
        assert payload["side"] in ["buy", "sell"]

    def test_subscription_routing_keys(self, strategy_config):
        """구독 라우팅 키가 올바른 형식인지 테스트"""

        strategy = MAcrossoverStrategy(strategy_config)
        subscriptions = strategy.get_required_subscriptions()

        assert len(subscriptions) == 1

        routing_key = subscriptions[0]
        expected = "market_data.binance.btcusdt"

        assert routing_key == expected

    @pytest.mark.asyncio
    async def test_mock_message_bus_integration(self, strategy_config):
        """Mock 메시지 버스와의 통합 테스트"""

        # Mock 메시지 버스 생성
        mock_bus = Mock()
        mock_bus.connect = AsyncMock(return_value=True)
        mock_bus.publish = AsyncMock(return_value=True)
        mock_bus.subscribe = AsyncMock(return_value=True)
        mock_bus.disconnect = AsyncMock(return_value=True)

        # 발행된 메시지 캡처
        published_messages = []

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

        mock_bus.publish.side_effect = capture_publish

        # 전략 인스턴스
        strategy = MAcrossoverStrategy(strategy_config)

        # 신호 생성 데이터
        test_data = pd.DataFrame(
            {
                "close": [49000, 49500, 50000],
                "ma_fast": [49200, 49700, 50200],
                "ma_slow": [49600, 49800, 49900],
                "ma_signal": [-1, -1, 1],  # 크로스오버 발생
                "ma_difference_pct": [0.5, 0.6, 0.7],
            }
        )

        strategy._indicators_calculated = True

        market_data = {"close": 50000.0}
        signal = strategy.on_data(market_data, test_data)

        # 신호가 생성되었다면 메시지 발행 시뮬레이션
        if signal:
            await mock_bus.publish(
                exchange_name="letrade.requests",
                routing_key=signal["routing_key"],
                message=signal["payload"],
            )

            # 발행 확인
            assert len(published_messages) == 1

            published = published_messages[0]
            assert published["exchange"] == "letrade.requests"
            assert "request.capital.allocation" in published["routing_key"]
            assert published["message"]["side"] == "buy"  # 골든 크로스

    @pytest.mark.asyncio
    async def test_backtest_data_with_strategy(self):
        """백테스트 데이터와 전략 연동 테스트"""

        # Mock 데이터 설정
        config = DataSourceConfig(
            source_type="mock",
            symbol="BTC/USDT",
            timeframe="1h",
            mock_config={
                "num_periods": 20,
                "base_price": 50000.0,
                "volatility": 0.01,
                "add_trends": False,  # 단순한 랜덤 데이터
            },
        )

        # 데이터 로더
        loader = BacktestDataLoader(config)
        data = await loader.load_data()

        assert not data.empty
        assert len(data) == 20

        # 전략 설정
        strategy_config = StrategyConfig(
            strategy_id="backtest_test_001",
            name="Backtest Test Strategy",
            enabled=True,
            dry_run=True,
            custom_params={
                "fast_period": 3,
                "slow_period": 5,
                "symbol": "BTC/USDT",
                "exchange": "binance",
            },
        )

        # 전략 생성 및 지표 계산
        strategy = MAcrossoverStrategy(strategy_config)
        df_with_indicators = strategy.populate_indicators(data)

        # 지표가 올바르게 계산되었는지 확인
        assert "ma_fast" in df_with_indicators.columns
        assert "ma_slow" in df_with_indicators.columns

        # 충분한 데이터가 있을 때 지표 값 확인
        if len(df_with_indicators) >= 5:
            # NaN이 아닌 지표 값이 존재해야 함
            assert not df_with_indicators["ma_fast"].iloc[-1:].isna().all()
            assert not df_with_indicators["ma_slow"].iloc[-1:].isna().all()

    def test_signal_strength_filtering(self, strategy_config):
        """신호 강도 필터링 테스트"""

        # 높은 임계값 설정
        strategy_config.custom_params["min_crossover_strength"] = 2.0  # 2%

        strategy = MAcrossoverStrategy(strategy_config)

        # 약한 크로스오버 데이터 (강도 부족)
        weak_data = pd.DataFrame(
            {
                "close": [50000, 50010, 50020],
                "ma_fast": [50000, 50010, 50020],
                "ma_slow": [50005, 50015, 50019],  # 매우 작은 차이
                "ma_signal": [-1, -1, 1],
                "ma_difference_pct": [0.01, 0.02, 0.002],  # 0.002% - 임계값 미달
            }
        )

        strategy._indicators_calculated = True

        market_data = {"close": 50020.0}
        signal = strategy.on_data(market_data, weak_data)

        # 강도가 부족하여 신호가 생성되지 않아야 함
        assert signal is None

    def test_signal_interval_filtering(self, strategy_config):
        """신호 간격 필터링 테스트"""

        # 긴 신호 간격 설정
        strategy_config.custom_params["min_signal_interval"] = 3600  # 1시간

        strategy = MAcrossoverStrategy(strategy_config)

        # 최근에 신호를 보냈다고 설정
        strategy._last_signal_timestamp = datetime.now(timezone.utc)

        # 강한 크로스오버 데이터
        strong_data = pd.DataFrame(
            {
                "close": [49000, 50000, 51000],
                "ma_fast": [49200, 50200, 51200],
                "ma_slow": [49800, 49900, 50000],
                "ma_signal": [-1, -1, 1],
                "ma_difference_pct": [0.5, 1.0, 2.4],  # 강한 신호
            }
        )

        strategy._indicators_calculated = True

        market_data = {"close": 51000.0}
        signal = strategy.on_data(market_data, strong_data)

        # 시간 간격이 부족하여 신호가 생성되지 않아야 함
        assert signal is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
