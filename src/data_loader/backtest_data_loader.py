"""
백테스트 데이터 로더

히스토리컬 OHLCV 데이터를 로드하고 관리하는 모듈입니다.
다양한 데이터 소스 (CSV, API, 데이터베이스 등)를 지원합니다.
"""

import asyncio
import io
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiohttp
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class DataSourceConfig:
    """데이터 소스 설정"""

    source_type: str  # 'csv', 'api', 'mock', 'database'
    symbol: str
    timeframe: str = "1h"  # 1m, 5m, 15m, 1h, 4h, 1d
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # CSV 관련 설정
    file_path: Optional[str] = None

    # API 관련 설정
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None

    # Mock 데이터 설정
    mock_config: Dict[str, Any] = field(default_factory=dict)

    # 추가 매개변수
    extra_params: Dict[str, Any] = field(default_factory=dict)


class BaseDataLoader(ABC):
    """데이터 로더 기본 클래스"""

    def __init__(self, config: DataSourceConfig):
        self.config = config
        self.data_cache: Optional[pd.DataFrame] = None

    @abstractmethod
    async def load_data(self) -> pd.DataFrame:
        """데이터 로드 추상 메서드"""
        pass

    def validate_data(self, data: pd.DataFrame) -> bool:
        """데이터 유효성 검증"""
        try:
            required_columns = ["timestamp", "open", "high", "low", "close", "volume"]
            missing_columns = [
                col for col in required_columns if col not in data.columns
            ]

            if missing_columns:
                logger.error(f"Missing required columns: {missing_columns}")
                return False

            # 데이터 타입 확인
            numeric_columns = ["open", "high", "low", "close", "volume"]
            for col in numeric_columns:
                if not pd.api.types.is_numeric_dtype(data[col]):
                    logger.error(f"Column {col} is not numeric")
                    return False

            # 가격 데이터 논리적 검증
            invalid_rows = data[
                (data["high"] < data["low"])
                | (data["high"] < data["open"])
                | (data["high"] < data["close"])
                | (data["low"] > data["open"])
                | (data["low"] > data["close"])
                | (data["volume"] < 0)
            ]

            if not invalid_rows.empty:
                logger.warning(f"Found {len(invalid_rows)} rows with invalid OHLC data")

            return True

        except Exception as e:
            logger.error(f"Data validation error: {e}")
            return False

    def normalize_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """데이터 정규화"""
        try:
            df = data.copy()

            # 타임스탬프 정규화
            if "timestamp" in df.columns:
                if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
                    df["timestamp"] = pd.to_datetime(df["timestamp"])

                # UTC 타임존 설정
                if df["timestamp"].dt.tz is None:
                    df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
                else:
                    df["timestamp"] = df["timestamp"].dt.tz_convert("UTC")

            # 인덱스 설정
            if "timestamp" in df.columns:
                df = df.set_index("timestamp").sort_index()

            # 중복 제거
            df = df[~df.index.duplicated(keep="last")]

            # 숫자 컬럼 타입 보장
            numeric_columns = ["open", "high", "low", "close", "volume"]
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            # NaN 값 처리
            df = df.dropna()

            logger.debug(
                f"Data normalized: {len(df)} rows, {df.index.min()} to {df.index.max()}"
            )

            return df

        except Exception as e:
            logger.error(f"Data normalization error: {e}")
            return data


class CSVDataLoader(BaseDataLoader):
    """CSV 파일 데이터 로더"""

    async def load_data(self) -> pd.DataFrame:
        """CSV 파일에서 데이터 로드"""
        try:
            if not self.config.file_path:
                raise ValueError("CSV file path not specified")

            file_path = Path(self.config.file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"CSV file not found: {file_path}")

            logger.info(f"Loading data from CSV: {file_path}")

            # CSV 파일 읽기
            data = pd.read_csv(file_path)

            # 컬럼 매핑 (다양한 CSV 포맷 지원)
            column_mapping = {
                "time": "timestamp",
                "datetime": "timestamp",
                "date": "timestamp",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }

            data = data.rename(columns=column_mapping)

            # 데이터 검증 및 정규화
            if not self.validate_data(data):
                raise ValueError("Invalid CSV data format")

            data = self.normalize_data(data)

            # 날짜 범위 필터링
            if self.config.start_date:
                data = data[data.index >= self.config.start_date]
            if self.config.end_date:
                data = data[data.index <= self.config.end_date]

            logger.info(f"Loaded {len(data)} rows from CSV")

            self.data_cache = data
            return data

        except Exception as e:
            logger.error(f"Failed to load CSV data: {e}")
            raise


class MockDataLoader(BaseDataLoader):
    """Mock 데이터 생성기"""

    async def load_data(self) -> pd.DataFrame:
        """가상의 시장 데이터 생성"""
        try:
            config = self.config.mock_config

            # 기본 설정
            num_periods = config.get("num_periods", 1000)
            base_price = config.get("base_price", 50000.0)
            volatility = config.get("volatility", 0.02)  # 2% 일일 변동성
            trend = config.get("trend", 0.0001)  # 0.01% 일일 상승 추세

            # 시작/종료 시간 설정
            if self.config.end_date:
                end_time = self.config.end_date
            else:
                end_time = datetime.now(timezone.utc)

            # 타임프레임별 시간 간격
            timeframe_deltas = {
                "1m": timedelta(minutes=1),
                "5m": timedelta(minutes=5),
                "15m": timedelta(minutes=15),
                "1h": timedelta(hours=1),
                "4h": timedelta(hours=4),
                "1d": timedelta(days=1),
            }

            delta = timeframe_deltas.get(self.config.timeframe, timedelta(hours=1))
            start_time = end_time - (delta * num_periods)

            # 시간 인덱스 생성
            timestamps = pd.date_range(start=start_time, end=end_time, freq=delta)[:-1]

            logger.info(
                f"Generating {len(timestamps)} mock data points for {self.config.symbol}"
            )

            # 가격 데이터 생성 (기하 브라운 운동)
            returns = np.random.normal(trend, volatility, len(timestamps))
            price_multipliers = np.exp(returns.cumsum())
            close_prices = base_price * price_multipliers

            # OHLCV 데이터 생성
            data_rows = []

            for i, (timestamp, close) in enumerate(zip(timestamps, close_prices)):
                # 이전 종가를 시가로 사용
                if i == 0:
                    open_price = base_price
                else:
                    open_price = close_prices[i - 1]

                # 고가/저가 생성 (현실적인 범위)
                price_range = close * np.random.uniform(0.005, 0.03)  # 0.5-3% 범위
                high = max(open_price, close) + np.random.uniform(0, price_range)
                low = min(open_price, close) - np.random.uniform(0, price_range)

                # 거래량 생성 (로그 정규 분포)
                volume = np.random.lognormal(mean=8, sigma=1) * 100

                data_rows.append(
                    {
                        "timestamp": timestamp,
                        "open": round(open_price, 2),
                        "high": round(high, 2),
                        "low": round(low, 2),
                        "close": round(close, 2),
                        "volume": round(volume, 2),
                    }
                )

            # 데이터프레임 생성
            data = pd.DataFrame(data_rows)
            data = self.normalize_data(data)

            # 특별한 패턴 추가 (옵션)
            if config.get("add_trends", False):
                data = self._add_trend_patterns(data)

            logger.info(f"Generated mock data: {len(data)} periods")

            self.data_cache = data
            return data

        except Exception as e:
            logger.error(f"Failed to generate mock data: {e}")
            raise

    def _add_trend_patterns(self, data: pd.DataFrame) -> pd.DataFrame:
        """트렌드 패턴 추가"""
        try:
            df = data.copy()

            # 강한 상승 구간 추가
            uptrend_start = len(df) // 4
            uptrend_end = len(df) // 2

            for i in range(uptrend_start, uptrend_end):
                multiplier = 1 + (i - uptrend_start) * 0.002  # 점진적 상승
                df.iloc[i, df.columns.get_loc("close")] *= multiplier
                df.iloc[i, df.columns.get_loc("high")] *= multiplier
                df.iloc[i, df.columns.get_loc("low")] *= multiplier
                df.iloc[i, df.columns.get_loc("open")] *= multiplier

            # 하락 구간 추가
            downtrend_start = len(df) * 3 // 4
            downtrend_end = len(df) * 9 // 10

            for i in range(downtrend_start, downtrend_end):
                multiplier = 1 - (i - downtrend_start) * 0.001  # 점진적 하락
                df.iloc[i, df.columns.get_loc("close")] *= multiplier
                df.iloc[i, df.columns.get_loc("high")] *= multiplier
                df.iloc[i, df.columns.get_loc("low")] *= multiplier
                df.iloc[i, df.columns.get_loc("open")] *= multiplier

            return df

        except Exception as e:
            logger.error(f"Error adding trend patterns: {e}")
            return data


class APIDataLoader(BaseDataLoader):
    """외부 API 데이터 로더"""

    async def load_data(self) -> pd.DataFrame:
        """API에서 데이터 로드"""
        try:
            if not self.config.api_base_url:
                raise ValueError("API base URL not specified")

            logger.info(f"Loading data from API for {self.config.symbol}")

            # API 엔드포인트 구성
            params = {
                "symbol": self.config.symbol,
                "interval": self.config.timeframe,
                "limit": 1000,
            }

            if self.config.start_date:
                params["startTime"] = int(self.config.start_date.timestamp() * 1000)
            if self.config.end_date:
                params["endTime"] = int(self.config.end_date.timestamp() * 1000)

            # API 호출 (MVP 명세서 Section 7.2 보안 요구사항 준수)
            async with aiohttp.ClientSession() as session:
                headers = {}
                if self.config.api_key:
                    # TODO: GCP Secret Manager에서 API 키 로드 필요
                    # 현재는 환경변수에서 로드하도록 수정
                    import os

                    api_key = os.getenv("BINANCE_API_KEY", self.config.api_key)
                    if api_key and not api_key.startswith("test_"):
                        headers["X-MBX-APIKEY"] = api_key
                        logger.debug("API key loaded from environment")
                    else:
                        logger.warning("API key not configured or using test key")

                async with session.get(
                    f"{self.config.api_base_url}/api/v3/klines",
                    params=params,
                    headers=headers,
                ) as response:
                    response.raise_for_status()
                    api_data = await response.json()

            # Binance API 응답 포맷 파싱
            data_rows = []
            for row in api_data:
                data_rows.append(
                    {
                        "timestamp": pd.to_datetime(row[0], unit="ms"),
                        "open": float(row[1]),
                        "high": float(row[2]),
                        "low": float(row[3]),
                        "close": float(row[4]),
                        "volume": float(row[5]),
                    }
                )

            data = pd.DataFrame(data_rows)

            if data.empty:
                raise ValueError("No data received from API")

            # 데이터 검증 및 정규화
            if not self.validate_data(data):
                raise ValueError("Invalid API data format")

            data = self.normalize_data(data)

            logger.info(f"Loaded {len(data)} rows from API")

            self.data_cache = data
            return data

        except Exception as e:
            logger.error(f"Failed to load API data: {e}")
            raise


class BacktestDataLoader:
    """백테스트 데이터 로더 메인 클래스"""

    def __init__(self, config: DataSourceConfig):
        """
        백테스트 데이터 로더 초기화

        Args:
            config: 데이터 소스 설정
        """
        self.config = config
        self.loader = self._create_loader()

        logger.info(
            f"BacktestDataLoader initialized for {config.symbol} "
            f"({config.source_type}, {config.timeframe})"
        )

    def _create_loader(self) -> BaseDataLoader:
        """소스 타입에 따른 데이터 로더 생성"""
        loaders = {"csv": CSVDataLoader, "mock": MockDataLoader, "api": APIDataLoader}

        loader_class = loaders.get(self.config.source_type)
        if not loader_class:
            raise ValueError(f"Unsupported data source type: {self.config.source_type}")

        return loader_class(self.config)

    async def load_data(self, use_cache: bool = True) -> pd.DataFrame:
        """
        데이터 로드

        Args:
            use_cache: 캐시된 데이터 사용 여부

        Returns:
            pd.DataFrame: OHLCV 데이터
        """
        if use_cache and self.loader.data_cache is not None:
            logger.debug("Using cached data")
            return self.loader.data_cache

        return await self.loader.load_data()

    async def get_data_slice(
        self, start_date: datetime, end_date: datetime, use_cache: bool = True
    ) -> pd.DataFrame:
        """
        특정 기간의 데이터 조회

        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            use_cache: 캐시 사용 여부

        Returns:
            pd.DataFrame: 기간별 데이터
        """
        data = await self.load_data(use_cache=use_cache)

        return data[(data.index >= start_date) & (data.index <= end_date)]

    def get_data_info(self) -> Dict[str, Any]:
        """데이터 정보 조회"""
        if self.loader.data_cache is None:
            return {"status": "No data loaded"}

        data = self.loader.data_cache

        return {
            "symbol": self.config.symbol,
            "timeframe": self.config.timeframe,
            "source_type": self.config.source_type,
            "total_periods": len(data),
            "date_range": {
                "start": data.index.min().isoformat() if not data.empty else None,
                "end": data.index.max().isoformat() if not data.empty else None,
            },
            "price_range": {
                "min": float(data["low"].min()) if "low" in data.columns else None,
                "max": float(data["high"].max()) if "high" in data.columns else None,
            },
            "volume_stats": {
                "avg": (
                    float(data["volume"].mean()) if "volume" in data.columns else None
                ),
                "total": (
                    float(data["volume"].sum()) if "volume" in data.columns else None
                ),
            },
        }

    @staticmethod
    def create_mock_config(
        symbol: str = "BTC/USDT",
        timeframe: str = "1h",
        num_periods: int = 1000,
        base_price: float = 50000.0,
        volatility: float = 0.02,
        trend: float = 0.0001,
        add_trends: bool = True,
    ) -> DataSourceConfig:
        """Mock 데이터 설정 생성 유틸리티"""
        return DataSourceConfig(
            source_type="mock",
            symbol=symbol,
            timeframe=timeframe,
            mock_config={
                "num_periods": num_periods,
                "base_price": base_price,
                "volatility": volatility,
                "trend": trend,
                "add_trends": add_trends,
            },
        )

    @staticmethod
    def create_csv_config(
        symbol: str,
        file_path: str,
        timeframe: str = "1h",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> DataSourceConfig:
        """CSV 데이터 설정 생성 유틸리티"""
        return DataSourceConfig(
            source_type="csv",
            symbol=symbol,
            timeframe=timeframe,
            file_path=file_path,
            start_date=start_date,
            end_date=end_date,
        )

    @staticmethod
    def create_api_config(
        symbol: str,
        api_base_url: str,
        timeframe: str = "1h",
        api_key: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> DataSourceConfig:
        """API 데이터 설정 생성 유틸리티"""
        return DataSourceConfig(
            source_type="api",
            symbol=symbol,
            timeframe=timeframe,
            api_base_url=api_base_url,
            api_key=api_key,
            start_date=start_date,
            end_date=end_date,
        )
