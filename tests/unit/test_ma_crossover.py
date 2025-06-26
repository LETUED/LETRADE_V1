"""
MA Crossover Strategy 단위 테스트

이동평균 교차 전략의 핵심 로직을 테스트합니다.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

from src.strategies.base_strategy import StrategyConfig
from src.strategies.ma_crossover import MAcrossoverStrategy


@pytest.fixture
def strategy_config():
    """테스트용 MA Crossover 전략 설정"""
    return StrategyConfig(
        strategy_id="ma_test_001",
        name="MA Crossover Test Strategy",
        enabled=True,
        dry_run=True,
        custom_params={
            "fast_period": 5,  # 테스트용으로 짧은 기간 사용
            "slow_period": 10,
            "symbol": "BTC/USDT",
            "exchange": "binance",
            "min_signal_interval": 60,  # 1분
            "min_crossover_strength": 0.01,  # 1%
        },
    )


@pytest.fixture
def ma_strategy(strategy_config):
    """테스트용 MA Crossover 전략 인스턴스"""
    return MAcrossoverStrategy(strategy_config)


@pytest.fixture
def sample_ohlcv_data():
    """테스트용 OHLCV 데이터"""
    dates = pd.date_range(start="2023-01-01", periods=20, freq="1H")

    # 상승 추세에서 하락 추세로 변하는 데이터 생성
    base_price = 50000
    price_changes = np.concatenate(
        [
            np.random.normal(50, 100, 10),  # 상승 구간
            np.random.normal(-50, 100, 10),  # 하락 구간
        ]
    )

    prices = [base_price]
    for change in price_changes:
        prices.append(prices[-1] + change)

    data = []
    for i, (date, price) in enumerate(zip(dates, prices[1:])):
        high = price + np.random.uniform(10, 100)
        low = price - np.random.uniform(10, 100)
        open_price = prices[i] if i < len(prices) - 1 else price
        volume = np.random.uniform(1000, 10000)

        data.append(
            {
                "timestamp": date,
                "open": open_price,
                "high": high,
                "low": low,
                "close": price,
                "volume": volume,
            }
        )

    return pd.DataFrame(data)


@pytest.fixture
def golden_cross_data():
    """골든 크로스가 발생하는 테스트 데이터"""
    dates = pd.date_range(start="2023-01-01", periods=15, freq="1H")

    # 단기 MA가 장기 MA를 상향 돌파하는 패턴
    prices = [
        49000,
        49100,
        49200,
        49300,
        49400,  # 초기 상승
        49500,
        49700,
        50000,
        50300,
        50600,  # 가속 상승 (크로스오버 발생)
        50800,
        51000,
        51200,
        51400,
        51600,  # 지속 상승
    ]

    data = []
    for i, (date, price) in enumerate(zip(dates, prices)):
        data.append(
            {
                "timestamp": date,
                "open": price - 50,
                "high": price + 100,
                "low": price - 100,
                "close": price,
                "volume": 5000,
            }
        )

    return pd.DataFrame(data)


@pytest.fixture
def death_cross_data():
    """데스 크로스가 발생하는 테스트 데이터"""
    dates = pd.date_range(start="2023-01-01", periods=15, freq="1H")

    # 단기 MA가 장기 MA를 하향 돌파하는 패턴
    prices = [
        51000,
        50900,
        50800,
        50700,
        50600,  # 초기 하락
        50400,
        50100,
        49800,
        49500,
        49200,  # 가속 하락 (크로스오버 발생)
        49000,
        48800,
        48600,
        48400,
        48200,  # 지속 하락
    ]

    data = []
    for i, (date, price) in enumerate(zip(dates, prices)):
        data.append(
            {
                "timestamp": date,
                "open": price + 50,
                "high": price + 100,
                "low": price - 100,
                "close": price,
                "volume": 5000,
            }
        )

    return pd.DataFrame(data)


class TestMAcrossoverStrategy:
    """MA Crossover 전략 기본 테스트"""

    def test_strategy_initialization(self, ma_strategy, strategy_config):
        """전략 초기화 테스트"""
        assert ma_strategy.strategy_id == "ma_test_001"
        assert ma_strategy.name == "MA Crossover Test Strategy"
        assert ma_strategy.fast_period == 5
        assert ma_strategy.slow_period == 10
        assert ma_strategy.symbol == "BTC/USDT"
        assert ma_strategy.exchange == "binance"
        assert ma_strategy.min_signal_interval == 60
        assert ma_strategy.min_crossover_strength == 0.01

        # 초기 상태 확인
        assert ma_strategy._last_crossover_direction is None
        assert ma_strategy._last_signal_timestamp is None
        assert ma_strategy._position_side is None
        assert ma_strategy._indicators_calculated is False

    def test_get_required_subscriptions(self, ma_strategy):
        """구독 채널 테스트"""
        subscriptions = ma_strategy.get_required_subscriptions()

        assert len(subscriptions) == 1
        assert subscriptions[0] == "market_data.binance.btcusdt"

    def test_populate_indicators_empty_dataframe(self, ma_strategy):
        """빈 데이터프레임에 대한 지표 계산 테스트"""
        empty_df = pd.DataFrame()
        result = ma_strategy.populate_indicators(empty_df)

        assert result.empty
        assert ma_strategy._indicators_calculated is False

    def test_populate_indicators_missing_columns(self, ma_strategy):
        """필수 컬럼이 없는 데이터에 대한 테스트"""
        invalid_df = pd.DataFrame({"price": [100, 200, 300]})
        result = ma_strategy.populate_indicators(invalid_df)

        # 원본 데이터프레임이 그대로 반환되어야 함
        assert "price" in result.columns
        assert "ma_fast" not in result.columns

    def test_populate_indicators_valid_data(self, ma_strategy, sample_ohlcv_data):
        """유효한 데이터에 대한 지표 계산 테스트"""
        result = ma_strategy.populate_indicators(sample_ohlcv_data)

        # 필수 컬럼 확인
        assert "sma_5" in result.columns
        assert "sma_10" in result.columns
        assert "ma_fast" in result.columns
        assert "ma_slow" in result.columns
        assert "ma_difference" in result.columns
        assert "ma_difference_pct" in result.columns
        assert "ma_signal" in result.columns
        assert "ma_crossover" in result.columns

        # 지표 계산 완료 플래그 확인
        assert ma_strategy._indicators_calculated is True

        # 이동평균 값이 계산되었는지 확인
        assert not result["ma_fast"].isna().all()
        assert not result["ma_slow"].isna().all()

    def test_on_data_invalid_input(self, ma_strategy):
        """잘못된 입력에 대한 on_data 테스트"""
        # None 데이터
        result = ma_strategy.on_data(None, pd.DataFrame())
        assert result is None

        # 빈 딕셔너리
        result = ma_strategy.on_data({}, pd.DataFrame())
        assert result is None

        # 가격 정보가 없는 데이터
        result = ma_strategy.on_data({"volume": 1000}, pd.DataFrame())
        assert result is None

    def test_on_data_insufficient_data(self, ma_strategy):
        """데이터가 부족한 경우 테스트"""
        # 지표가 계산되지 않은 상태
        market_data = {"close": 50000}
        dataframe = pd.DataFrame({"close": [49000, 49500, 50000]})

        result = ma_strategy.on_data(market_data, dataframe)
        assert result is None

    def test_detect_crossover_insufficient_data(self, ma_strategy):
        """크로스오버 감지 - 데이터 부족"""
        df = pd.DataFrame({"ma_signal": [1]})  # 데이터 1개만
        result = ma_strategy._detect_crossover(df)
        assert result is None

    def test_detect_crossover_no_crossover(self, ma_strategy):
        """크로스오버 감지 - 크로스오버 없음"""
        df = pd.DataFrame({"ma_signal": [1, 1, 1]})  # 계속 같은 신호
        result = ma_strategy._detect_crossover(df)
        assert result is None

    def test_detect_crossover_golden_cross(self, ma_strategy):
        """골든 크로스 감지 테스트"""
        df = pd.DataFrame({"ma_signal": [-1, -1, 1]})  # 하락에서 상승으로 변화
        result = ma_strategy._detect_crossover(df)
        assert result == "golden"

    def test_detect_crossover_death_cross(self, ma_strategy):
        """데스 크로스 감지 테스트"""
        df = pd.DataFrame({"ma_signal": [1, 1, -1]})  # 상승에서 하락으로 변화
        result = ma_strategy._detect_crossover(df)
        assert result == "death"

    def test_detect_crossover_duplicate_prevention(self, ma_strategy):
        """중복 크로스오버 신호 방지 테스트"""
        # 첫 번째 골든 크로스
        df = pd.DataFrame({"ma_signal": [-1, -1, 1]})
        result = ma_strategy._detect_crossover(df)
        assert result == "golden"

        # 상태 업데이트 후 같은 방향 크로스오버는 감지되지 않아야 함
        ma_strategy._last_crossover_direction = "golden"
        result = ma_strategy._detect_crossover(df)
        assert result is None

    def test_generate_trading_signal_golden_cross(self, ma_strategy):
        """골든 크로스 거래 신호 생성 테스트"""
        signal = ma_strategy._generate_trading_signal(
            crossover_type="golden",
            current_price=50000.0,
            fast_ma=50100.0,
            slow_ma=49900.0,
            strength_pct=0.4,  # 0.4%
        )

        assert signal is not None
        assert "routing_key" in signal
        assert "payload" in signal

        payload = signal["payload"]
        assert payload["side"] == "buy"
        assert payload["signal_price"] == 50000.0
        assert payload["symbol"] == "BTC/USDT"
        assert payload["stop_loss_price"] == 50000.0 * 0.98  # 2% 손절매
        assert 0.0 <= payload["confidence"] <= 1.0

        # 전략 파라미터 확인
        params = payload["strategy_params"]
        assert params["crossover_type"] == "golden"
        assert params["fast_ma"] == 50100.0
        assert params["slow_ma"] == 49900.0
        assert params["strength_pct"] == 0.4

    def test_generate_trading_signal_death_cross(self, ma_strategy):
        """데스 크로스 거래 신호 생성 테스트"""
        signal = ma_strategy._generate_trading_signal(
            crossover_type="death",
            current_price=50000.0,
            fast_ma=49900.0,
            slow_ma=50100.0,
            strength_pct=-0.4,  # -0.4%
        )

        assert signal is not None
        assert "routing_key" in signal
        assert "payload" in signal

        payload = signal["payload"]
        assert payload["side"] == "sell"
        assert payload["signal_price"] == 50000.0
        assert payload["stop_loss_price"] == 50000.0 * 1.02  # 2% 손절매

    def test_generate_trading_signal_invalid_type(self, ma_strategy):
        """잘못된 크로스오버 타입 테스트"""
        signal = ma_strategy._generate_trading_signal(
            crossover_type="invalid",
            current_price=50000.0,
            fast_ma=50000.0,
            slow_ma=50000.0,
            strength_pct=0.0,
        )

        assert signal is None

    def test_is_signal_allowed_no_previous(self, ma_strategy):
        """이전 신호가 없을 때 허용 테스트"""
        assert ma_strategy._is_signal_allowed() is True

    def test_is_signal_allowed_recent_signal(self, ma_strategy):
        """최근 신호가 있을 때 차단 테스트"""
        ma_strategy._last_signal_timestamp = datetime.now(timezone.utc)
        assert ma_strategy._is_signal_allowed() is False

    def test_is_signal_allowed_old_signal(self, ma_strategy):
        """오래된 신호 후 허용 테스트"""
        ma_strategy._last_signal_timestamp = datetime.now(timezone.utc) - timedelta(
            seconds=120
        )
        assert ma_strategy._is_signal_allowed() is True

    def test_update_signal_state_golden(self, ma_strategy):
        """골든 크로스 상태 업데이트 테스트"""
        ma_strategy._update_signal_state("golden")

        assert ma_strategy._last_crossover_direction == "golden"
        assert ma_strategy._position_side == "long"
        assert ma_strategy._last_signal_timestamp is not None

    def test_update_signal_state_death(self, ma_strategy):
        """데스 크로스 상태 업데이트 테스트"""
        ma_strategy._update_signal_state("death")

        assert ma_strategy._last_crossover_direction == "death"
        assert ma_strategy._position_side == "short"
        assert ma_strategy._last_signal_timestamp is not None

    def test_get_strategy_params(self, ma_strategy):
        """전략 파라미터 조회 테스트"""
        params = ma_strategy.get_strategy_params()

        assert params["strategy_type"] == "MA_CROSSOVER"
        assert params["fast_period"] == 5
        assert params["slow_period"] == 10
        assert params["symbol"] == "BTC/USDT"
        assert params["exchange"] == "binance"
        assert "current_state" in params

        state = params["current_state"]
        assert "last_crossover_direction" in state
        assert "position_side" in state
        assert "indicators_calculated" in state

    @pytest.mark.asyncio
    async def test_strategy_lifecycle(self, ma_strategy):
        """전략 생명주기 테스트"""
        # 시작 전 상태
        assert ma_strategy.is_running is False

        # 전략 시작
        with patch.object(ma_strategy, "_validate_startup", return_value=True):
            result = await ma_strategy.start()
            assert result is True
            assert ma_strategy.is_running is True

        # 전략 중지
        result = await ma_strategy.stop()
        assert result is True
        assert ma_strategy.is_running is False

    @pytest.mark.asyncio
    async def test_health_check(self, ma_strategy):
        """헬스체크 테스트"""
        health = await ma_strategy.health_check()

        assert health["strategy_id"] == "ma_test_001"
        assert health["healthy"] is False  # 시작되지 않은 상태
        assert "strategy_specific" in health
        assert "parameters" in health

        strategy_health = health["strategy_specific"]
        assert "indicators_ready" in strategy_health
        assert "ma_periods_valid" in strategy_health
        assert "symbol_configured" in strategy_health
        assert "exchange_configured" in strategy_health


class TestMAcrossoverIntegration:
    """MA Crossover 전략 통합 테스트"""

    def test_full_golden_cross_flow(self, ma_strategy, golden_cross_data):
        """골든 크로스 전체 플로우 테스트"""
        # 지표 계산
        df_with_indicators = ma_strategy.populate_indicators(golden_cross_data)
        assert ma_strategy._indicators_calculated is True

        # 마지막 데이터로 신호 생성 시도
        latest_data = {
            "close": golden_cross_data["close"].iloc[-1],
            "timestamp": golden_cross_data["timestamp"].iloc[-1],
        }

        # 신호 간격 조건을 만족하도록 설정
        ma_strategy.min_signal_interval = 0
        ma_strategy.min_crossover_strength = 0.001

        signal = ma_strategy.on_data(latest_data, df_with_indicators)

        # 골든 크로스가 감지되면 매수 신호가 생성되어야 함
        if signal:
            payload = signal.get("payload", signal)
            assert payload["side"] == "buy"
            assert payload["signal_price"] == latest_data["close"]

    def test_full_death_cross_flow(self, ma_strategy, death_cross_data):
        """데스 크로스 전체 플로우 테스트"""
        # 지표 계산
        df_with_indicators = ma_strategy.populate_indicators(death_cross_data)
        assert ma_strategy._indicators_calculated is True

        # 마지막 데이터로 신호 생성 시도
        latest_data = {
            "close": death_cross_data["close"].iloc[-1],
            "timestamp": death_cross_data["timestamp"].iloc[-1],
        }

        # 신호 간격 조건을 만족하도록 설정
        ma_strategy.min_signal_interval = 0
        ma_strategy.min_crossover_strength = 0.001

        signal = ma_strategy.on_data(latest_data, df_with_indicators)

        # 데스 크로스가 감지되면 매도 신호가 생성되어야 함
        if signal:
            payload = signal.get("payload", signal)
            assert payload["side"] == "sell"
            assert payload["signal_price"] == latest_data["close"]

    def test_signal_strength_filtering(self, ma_strategy, sample_ohlcv_data):
        """신호 강도 필터링 테스트"""
        # 강한 신호 강도 요구 설정
        ma_strategy.min_crossover_strength = 5.0  # 5% - 매우 높은 임계값

        df_with_indicators = ma_strategy.populate_indicators(sample_ohlcv_data)

        latest_data = {"close": sample_ohlcv_data["close"].iloc[-1]}

        # 높은 임계값으로 인해 신호가 생성되지 않아야 함
        signal = ma_strategy.on_data(latest_data, df_with_indicators)
        assert signal is None

    def test_signal_interval_filtering(self, ma_strategy, golden_cross_data):
        """신호 간격 필터링 테스트"""
        # 매우 긴 신호 간격 설정
        ma_strategy.min_signal_interval = 3600  # 1시간

        # 첫 번째 신호 생성
        ma_strategy._last_signal_timestamp = datetime.now(timezone.utc)

        df_with_indicators = ma_strategy.populate_indicators(golden_cross_data)
        latest_data = {"close": golden_cross_data["close"].iloc[-1]}

        # 신호 간격이 짧아 신호가 생성되지 않아야 함
        signal = ma_strategy.on_data(latest_data, df_with_indicators)
        assert signal is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
