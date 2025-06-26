"""
Moving Average Crossover Strategy Implementation

이동평균 교차 전략 구현체입니다.
단기 이동평균(fast MA)과 장기 이동평균(slow MA)의 교차를 기반으로 
매수/매도 신호를 생성합니다.

골든 크로스: 단기 MA가 장기 MA를 상향 돌파 시 매수 신호
데스 크로스: 단기 MA가 장기 MA를 하향 돌파 시 매도 신호
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

from .base_strategy import BaseStrategy, StrategyConfig, TradingSignal, calculate_sma

logger = logging.getLogger(__name__)


class MAcrossoverStrategy(BaseStrategy):
    """
    이동평균 교차 전략

    MVP 명세서의 핵심 전략으로, SMA 50/200 교차를 기반으로
    거래 신호를 생성합니다.
    """

    def __init__(self, config: StrategyConfig):
        """
        MA Crossover 전략 초기화

        Args:
            config: 전략 설정
        """
        super().__init__(config)

        # 전략 파라미터 설정 (기본값: SMA 50/200)
        self.fast_period = config.custom_params.get("fast_period", 50)
        self.slow_period = config.custom_params.get("slow_period", 200)
        self.symbol = config.custom_params.get("symbol", "BTC/USDT")
        self.exchange = config.custom_params.get("exchange", "binance")

        # 최소 신호 간격 (초) - 같은 방향 신호 중복 방지
        self.min_signal_interval = config.custom_params.get("min_signal_interval", 3600)

        # 신호 강도 설정
        self.min_crossover_strength = config.custom_params.get(
            "min_crossover_strength", 0.001
        )  # 0.1%

        # 내부 상태
        self._last_crossover_direction = None  # 'golden' or 'death'
        self._last_signal_timestamp = None
        self._position_side = None  # 현재 포지션 방향

        # 데이터 저장소
        self._price_history = pd.DataFrame()
        self._indicators_calculated = False

        logger.info(
            "MAcrossoverStrategy initialized",
            extra={
                "strategy_id": self.strategy_id,
                "fast_period": self.fast_period,
                "slow_period": self.slow_period,
                "symbol": self.symbol,
                "exchange": self.exchange,
                "min_signal_interval": self.min_signal_interval,
            },
        )

    def populate_indicators(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        기술적 지표 계산 - SMA 50/200 계산

        Args:
            dataframe: OHLCV 데이터프레임

        Returns:
            pd.DataFrame: 지표가 추가된 데이터프레임
        """
        if dataframe.empty:
            logger.warning("Empty dataframe provided to populate_indicators")
            return dataframe

        try:
            # 필수 컬럼 확인
            required_columns = ["open", "high", "low", "close", "volume"]
            missing_columns = [
                col for col in required_columns if col not in dataframe.columns
            ]
            if missing_columns:
                logger.error(f"Missing required columns: {missing_columns}")
                return dataframe

            # 데이터프레임 복사 (원본 수정 방지)
            df = dataframe.copy()

            # Simple Moving Averages 계산
            df[f"sma_{self.fast_period}"] = calculate_sma(df["close"], self.fast_period)
            df[f"sma_{self.slow_period}"] = calculate_sma(df["close"], self.slow_period)

            # 크로스오버 감지를 위한 보조 지표
            df["ma_fast"] = df[f"sma_{self.fast_period}"]
            df["ma_slow"] = df[f"sma_{self.slow_period}"]

            # 이동평균 간 차이 (크로스오버 강도 측정)
            df["ma_difference"] = df["ma_fast"] - df["ma_slow"]

            # 안전한 방식으로 ma_difference_pct 계산
            df["ma_difference_pct"] = 0.0
            mask = df["ma_slow"].notna() & (df["ma_slow"] != 0)
            if mask.any():
                df.loc[mask, "ma_difference_pct"] = (
                    df.loc[mask, "ma_difference"] / df.loc[mask, "ma_slow"]
                ) * 100

            # 크로스오버 방향 감지
            df["ma_signal"] = 0
            # NaN 값을 0으로 채우고 비교
            ma_fast_filled = df["ma_fast"].fillna(0)
            ma_slow_filled = df["ma_slow"].fillna(0)
            valid_idx = df["ma_fast"].notna() & df["ma_slow"].notna()

            df.loc[valid_idx & (ma_fast_filled > ma_slow_filled), "ma_signal"] = (
                1  # 골든 크로스 영역
            )
            df.loc[valid_idx & (ma_fast_filled < ma_slow_filled), "ma_signal"] = (
                -1
            )  # 데스 크로스 영역

            # 크로스오버 이벤트 감지 (신호 변화 시점)
            df["ma_crossover"] = df["ma_signal"].diff()

            self._indicators_calculated = True

            logger.debug(
                f"Indicators calculated for {len(df)} data points",
                extra={
                    "strategy_id": self.strategy_id,
                    "fast_ma_last": (
                        df["ma_fast"].iloc[-1]
                        if not df["ma_fast"].isna().all()
                        else None
                    ),
                    "slow_ma_last": (
                        df["ma_slow"].iloc[-1]
                        if not df["ma_slow"].isna().all()
                        else None
                    ),
                    "signal_last": (
                        df["ma_signal"].iloc[-1]
                        if not df["ma_signal"].isna().all()
                        else None
                    ),
                },
            )

            return df

        except Exception as e:
            logger.error(
                f"Error calculating indicators: {e}",
                extra={"strategy_id": self.strategy_id, "error": str(e)},
            )
            return dataframe

    def on_data(
        self, data: Dict[str, Any], dataframe: pd.DataFrame
    ) -> Optional[Dict[str, Any]]:
        """
        새로운 시장 데이터 처리 및 거래 신호 생성

        Args:
            data: 최신 시장 데이터 (OHLCV tick)
            dataframe: 지표가 계산된 히스토리컬 데이터

        Returns:
            Optional[Dict[str, Any]]: 거래 제안 또는 None
        """
        try:
            # 데이터 유효성 검사
            if not data or not isinstance(data, dict):
                logger.warning("Invalid market data received")
                return None

            if dataframe.empty or not self._indicators_calculated:
                logger.warning("No indicators available for signal generation")
                return None

            # 최신 데이터에서 필요한 값 추출
            current_price = data.get("close") or data.get("price")
            if not current_price:
                logger.warning("No price data in market data")
                return None

            # 최신 지표 값 확인
            if len(dataframe) < max(self.fast_period, self.slow_period):
                logger.debug("Insufficient data for MA calculation")
                return None

            latest_row = dataframe.iloc[-1]

            # 이동평균 값 확인
            fast_ma = latest_row.get("ma_fast")
            slow_ma = latest_row.get("ma_slow")
            ma_difference_pct = latest_row.get("ma_difference_pct", 0)

            if pd.isna(fast_ma) or pd.isna(slow_ma):
                logger.debug("MA values not available yet")
                return None

            # 크로스오버 감지
            crossover_type = self._detect_crossover(dataframe)
            if not crossover_type:
                return None

            # 신호 강도 확인
            if abs(ma_difference_pct) < self.min_crossover_strength:
                logger.debug(
                    f"Crossover strength too weak: {ma_difference_pct:.4f}%",
                    extra={"strategy_id": self.strategy_id},
                )
                return None

            # 신호 간격 확인 (중복 신호 방지)
            if not self._is_signal_allowed():
                logger.debug(
                    "Signal interval too short, skipping",
                    extra={"strategy_id": self.strategy_id},
                )
                return None

            # 거래 신호 생성
            signal = self._generate_trading_signal(
                crossover_type, current_price, fast_ma, slow_ma, ma_difference_pct
            )

            if signal:
                self._update_signal_state(crossover_type)

                logger.info(
                    f"Trading signal generated: {crossover_type}",
                    extra={
                        "strategy_id": self.strategy_id,
                        "signal_type": signal.get("payload", {}).get("side", "unknown"),
                        "price": current_price,
                        "fast_ma": fast_ma,
                        "slow_ma": slow_ma,
                        "strength_pct": ma_difference_pct,
                    },
                )

            return signal

        except Exception as e:
            logger.error(
                f"Error in on_data: {e}",
                extra={"strategy_id": self.strategy_id, "error": str(e)},
            )
            return None

    def get_required_subscriptions(self) -> List[str]:
        """
        구독할 시장 데이터 채널 반환

        Returns:
            List[str]: RabbitMQ 라우팅 키 목록
        """
        routing_key = (
            f"market_data.{self.exchange}.{self.symbol.lower().replace('/', '')}"
        )

        logger.debug(
            f"Required subscription: {routing_key}",
            extra={"strategy_id": self.strategy_id},
        )

        return [routing_key]

    def _detect_crossover(self, dataframe: pd.DataFrame) -> Optional[str]:
        """
        크로스오버 이벤트 감지

        Args:
            dataframe: 지표가 계산된 데이터프레임

        Returns:
            Optional[str]: 'golden' (골든 크로스) 또는 'death' (데스 크로스)
        """
        if len(dataframe) < 2:
            return None

        try:
            # 최근 2개 데이터 포인트 확인
            current = dataframe.iloc[-1]
            previous = dataframe.iloc[-2]

            current_signal = current.get("ma_signal", 0)
            previous_signal = previous.get("ma_signal", 0)

            # 크로스오버 이벤트 감지
            if previous_signal <= 0 and current_signal > 0:
                # 골든 크로스: 단기 MA가 장기 MA를 상향 돌파
                if self._last_crossover_direction != "golden":
                    return "golden"
            elif previous_signal >= 0 and current_signal < 0:
                # 데스 크로스: 단기 MA가 장기 MA를 하향 돌파
                if self._last_crossover_direction != "death":
                    return "death"

            return None

        except Exception as e:
            logger.error(
                f"Error detecting crossover: {e}",
                extra={"strategy_id": self.strategy_id},
            )
            return None

    def _generate_trading_signal(
        self,
        crossover_type: str,
        current_price: float,
        fast_ma: float,
        slow_ma: float,
        strength_pct: float,
    ) -> Optional[Dict[str, Any]]:
        """
        거래 신호 생성 (MVP 명세서 Section 6.1.2 호환)

        Args:
            crossover_type: 크로스오버 타입 ('golden' 또는 'death')
            current_price: 현재 가격
            fast_ma: 단기 이동평균
            slow_ma: 장기 이동평균
            strength_pct: 신호 강도 (%)

        Returns:
            Optional[Dict[str, Any]]: MVP 명세서 호환 거래 제안
        """
        try:
            # 크로스오버 타입별 신호 생성
            if crossover_type == "golden":
                side = "buy"
                stop_loss_price = current_price * 0.98  # 2% 손절매
                take_profit_price = current_price * 1.04  # 4% 익절
            elif crossover_type == "death":
                side = "sell"
                stop_loss_price = current_price * 1.02  # 2% 손절매
                take_profit_price = current_price * 0.96  # 4% 익절
            else:
                logger.warning(f"Unknown crossover type: {crossover_type}")
                return None

            # MVP 명세서 Section 6.1.2 호환 포맷
            return {
                "routing_key": f"request.capital.allocation.{self.strategy_id}",
                "payload": {
                    "strategy_id": self._extract_strategy_id_number(),
                    "symbol": self.symbol,
                    "side": side,
                    "signal_price": current_price,
                    "stop_loss_price": stop_loss_price,
                    "confidence": min(abs(strength_pct) / 2.0, 1.0),  # 최대 1.0
                    "strategy_params": {
                        "crossover_type": crossover_type,
                        "fast_ma": fast_ma,
                        "slow_ma": slow_ma,
                        "strength_pct": strength_pct,
                        "fast_period": self.fast_period,
                        "slow_period": self.slow_period,
                    },
                },
            }

        except Exception as e:
            logger.error(
                f"Error generating trading signal: {e}",
                extra={"strategy_id": self.strategy_id},
            )
            return None

    def _is_signal_allowed(self) -> bool:
        """
        신호 생성 허용 여부 확인 (중복 방지)

        Returns:
            bool: 신호 생성 허용 여부
        """
        if not self._last_signal_timestamp:
            return True

        current_time = datetime.now(timezone.utc)
        time_since_last = (current_time - self._last_signal_timestamp).total_seconds()

        return time_since_last >= self.min_signal_interval

    def _update_signal_state(self, crossover_type: str):
        """
        신호 상태 업데이트

        Args:
            crossover_type: 크로스오버 타입
        """
        self._last_crossover_direction = crossover_type
        self._last_signal_timestamp = datetime.now(timezone.utc)

        # 포지션 방향 업데이트
        if crossover_type == "golden":
            self._position_side = "long"
        elif crossover_type == "death":
            self._position_side = "short"

    async def on_start(self):
        """전략 시작 시 실행되는 커스텀 로직"""
        logger.info(
            "MAcrossoverStrategy starting",
            extra={
                "strategy_id": self.strategy_id,
                "symbol": self.symbol,
                "fast_period": self.fast_period,
                "slow_period": self.slow_period,
            },
        )

        # 초기 상태 설정
        self._last_crossover_direction = None
        self._last_signal_timestamp = None
        self._position_side = None
        self._indicators_calculated = False

    async def on_stop(self):
        """전략 중지 시 실행되는 커스텀 로직"""
        logger.info(
            "MAcrossoverStrategy stopping",
            extra={
                "strategy_id": self.strategy_id,
                "last_position": self._position_side,
                "last_crossover": self._last_crossover_direction,
            },
        )

    def _extract_strategy_id_number(self) -> int:
        """Strategy ID에서 숫자 추출"""
        try:
            # strategy_id에서 숫자만 추출
            import re

            numbers = re.findall(r"\d+", str(self.strategy_id))
            if numbers:
                return int(numbers[-1])  # 마지막 숫자 사용
            else:
                # 숫자가 없으면 해시값 사용
                return abs(hash(self.strategy_id)) % 1000
        except Exception:
            return abs(hash(self.strategy_id)) % 1000

    def get_strategy_params(self) -> Dict[str, Any]:
        """전략 파라미터 반환"""
        return {
            "strategy_type": "MA_CROSSOVER",
            "fast_period": self.fast_period,
            "slow_period": self.slow_period,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "min_signal_interval": self.min_signal_interval,
            "min_crossover_strength": self.min_crossover_strength,
            "current_state": {
                "last_crossover_direction": self._last_crossover_direction,
                "position_side": self._position_side,
                "indicators_calculated": self._indicators_calculated,
                "last_signal_time": (
                    self._last_signal_timestamp.isoformat()
                    if self._last_signal_timestamp
                    else None
                ),
            },
        }

    async def health_check(self) -> Dict[str, Any]:
        """전략별 헬스체크"""
        base_health = await super().health_check()

        # MA 전략 특화 헬스체크 추가
        strategy_health = {
            "strategy_specific": {
                "indicators_ready": self._indicators_calculated,
                "ma_periods_valid": (
                    self.fast_period > 0
                    and self.slow_period > 0
                    and self.fast_period < self.slow_period
                ),
                "symbol_configured": bool(self.symbol),
                "exchange_configured": bool(self.exchange),
            },
            "parameters": self.get_strategy_params(),
        }

        # 기본 헬스체크와 병합
        base_health.update(strategy_health)

        return base_health
