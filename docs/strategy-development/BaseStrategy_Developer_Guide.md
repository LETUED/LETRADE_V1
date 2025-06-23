# BaseStrategy 개발자 가이드

## 📋 개요

이 문서는 Letrade_v1 시스템에서 새로운 거래 전략을 개발하는 개발자를 위한 완전한 가이드입니다. BaseStrategy 추상 클래스를 사용하여 안전하고 효율적인 거래 전략을 구현하는 방법을 단계별로 설명합니다.

## 🎯 BaseStrategy 인터페이스 개요

BaseStrategy는 모든 거래 전략이 따라야 하는 표준 인터페이스입니다:

- **모듈성**: 각 전략은 독립적인 프로세스로 실행
- **확장성**: 새 전략 추가 시 기존 시스템 수정 불필요
- **안전성**: 개별 전략 오류가 전체 시스템에 영향 없음
- **성능**: 비동기 처리 및 실시간 성능 모니터링 지원

## 🔧 필수 구현 메서드

### 1. populate_indicators(dataframe)

**목적**: 거래 전략에 필요한 기술적 지표를 계산하고 데이터프레임에 추가

```python
def populate_indicators(self, dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    기술적 지표 계산 및 추가
    
    Args:
        dataframe: OHLCV 데이터 (open, high, low, close, volume 컬럼 포함)
        
    Returns:
        지표가 추가된 데이터프레임
    """
    # pandas-ta 라이브러리 사용 예시
    dataframe['sma_fast'] = calculate_sma(dataframe['close'], 50)
    dataframe['sma_slow'] = calculate_sma(dataframe['close'], 200)
    dataframe['rsi'] = calculate_rsi(dataframe['close'], 14)
    
    return dataframe
```

**주요 특징**:
- pandas-ta 라이브러리 활용 권장
- 원본 데이터프레임을 수정하여 반환
- 계산 집약적 작업은 여기서 수행

### 2. on_data(data, dataframe)

**목적**: 새로운 시장 데이터 수신 시 거래 신호 생성

```python
def on_data(self, data: Dict[str, Any], dataframe: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    거래 신호 생성 핵심 로직
    
    Args:
        data: 최신 시장 데이터 포인트
        dataframe: 지표가 포함된 과거 데이터
        
    Returns:
        거래 제안 딕셔너리 또는 None
    """
    if len(dataframe) < 200:  # 충분한 데이터 확보 대기
        return None
    
    current = dataframe.iloc[-1]
    previous = dataframe.iloc[-2]
    
    # 골든 크로스 감지
    if (previous['sma_fast'] < previous['sma_slow'] and 
        current['sma_fast'] > current['sma_slow']):
        
        return {
            "side": "buy",
            "signal_price": current['close'],
            "stop_loss_price": current['close'] * 0.98,
            "take_profit_price": current['close'] * 1.05,
            "confidence": 0.8,
            "strategy_params": {
                "signal_type": "golden_cross",
                "sma_fast": current['sma_fast'],
                "sma_slow": current['sma_slow']
            }
        }
    
    return None
```

**신호 포맷 규격**:
- `side`: "buy" 또는 "sell"
- `signal_price`: 진입 가격
- `stop_loss_price`: 손절매 가격 (선택사항)
- `take_profit_price`: 익절 가격 (선택사항)
- `confidence`: 신호 신뢰도 (0.0-1.0)
- `strategy_params`: 전략별 추가 정보

### 3. get_required_subscriptions()

**목적**: 전략이 구독해야 할 RabbitMQ 라우팅 키 목록 반환

```python
def get_required_subscriptions(self) -> List[str]:
    """
    RabbitMQ 구독 목록 정의
    
    Returns:
        라우팅 키 문자열 목록
    """
    exchange = self.config.custom_params.get('exchange', 'binance')
    symbol = self.config.custom_params.get('symbol', 'btcusdt')
    
    return [f"market_data.{exchange}.{symbol}"]
```

**라우팅 키 형식**:
- `market_data.{exchange}.{symbol}`: 시장 데이터
- 예시: `"market_data.binance.btcusdt"`

## 🚀 고급 기능 활용

### 비동기 처리 (고성능 전략용)

```python
async def on_data_async(self, data: Dict[str, Any], dataframe: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    고성능 비동기 신호 생성
    """
    # 비동기 처리가 필요한 복잡한 계산
    await asyncio.sleep(0)  # 다른 작업에게 제어권 양보
    
    # ML 모델 예측 등 시간이 오래 걸리는 작업
    prediction = await self.ml_model.predict_async(dataframe)
    
    if prediction > 0.7:
        return {
            "side": "buy",
            "signal_price": data['close'],
            "confidence": prediction,
            "strategy_params": {"model_confidence": prediction}
        }
    
    return None
```

### 성능 모니터링

```python
def get_performance_metrics(self) -> Dict[str, Any]:
    """전략 성능 지표 확인"""
    metrics = super().get_performance_metrics()
    
    # 커스텀 메트릭 추가
    metrics.update({
        "custom_metric": self.calculate_custom_metric(),
        "signal_quality_score": self.calculate_signal_quality()
    })
    
    return metrics
```

## 📚 완전한 구현 예시: MA 크로스오버 전략

```python
# /src/strategies/ma_crossover_strategy.py

import pandas as pd
from typing import Dict, Any, List, Optional
from src.strategies.base_strategy import BaseStrategy, StrategyConfig, calculate_sma


class MovingAverageCrossoverStrategy(BaseStrategy):
    """이동평균 교차 전략 구현."""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # 설정에서 파라미터 로드
        self.fast_period = config.custom_params.get('fast', 50)
        self.slow_period = config.custom_params.get('slow', 200)
        self.exchange = config.custom_params.get('exchange', 'binance')
        self.symbol = config.custom_params.get('symbol', 'btcusdt')
        
        # 상태 추적
        self.last_cross_type = None
        self.position_entry_price = None
    
    def populate_indicators(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """이동평균 지표 계산."""
        if dataframe.empty:
            return dataframe
        
        # 단기 및 장기 이동평균 계산
        dataframe[f'sma_{self.fast_period}'] = calculate_sma(
            dataframe['close'], self.fast_period
        )
        dataframe[f'sma_{self.slow_period}'] = calculate_sma(
            dataframe['close'], self.slow_period
        )
        
        # 추가 필터 지표
        dataframe['volume_sma'] = calculate_sma(dataframe['volume'], 20)
        
        return dataframe
    
    def on_data(self, data: Dict[str, Any], dataframe: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """골든/데스 크로스 신호 생성."""
        if len(dataframe) < self.slow_period:
            return None
        
        current = dataframe.iloc[-1]
        previous = dataframe.iloc[-2]
        
        fast_col = f'sma_{self.fast_period}'
        slow_col = f'sma_{self.slow_period}'
        
        # 볼륨 필터 (최근 평균 볼륨의 120% 이상)
        if current['volume'] < current['volume_sma'] * 1.2:
            return None
        
        # 골든 크로스 (매수 신호)
        if (previous[fast_col] <= previous[slow_col] and 
            current[fast_col] > current[slow_col] and
            self.last_cross_type != 'golden'):
            
            self.last_cross_type = 'golden'
            
            return {
                "side": "buy",
                "signal_price": current['close'],
                "stop_loss_price": current['close'] * 0.98,  # 2% 손절
                "take_profit_price": current['close'] * 1.06,  # 6% 익절
                "confidence": self._calculate_signal_strength(dataframe),
                "strategy_params": {
                    "signal_type": "golden_cross",
                    "fast_ma": current[fast_col],
                    "slow_ma": current[slow_col],
                    "volume_ratio": current['volume'] / current['volume_sma']
                }
            }
        
        # 데스 크로스 (매도 신호)
        elif (previous[fast_col] >= previous[slow_col] and 
              current[fast_col] < current[slow_col] and
              self.last_cross_type != 'death'):
            
            self.last_cross_type = 'death'
            
            return {
                "side": "sell",
                "signal_price": current['close'],
                "stop_loss_price": current['close'] * 1.02,  # 2% 손절
                "take_profit_price": current['close'] * 0.94,  # 6% 익절
                "confidence": self._calculate_signal_strength(dataframe),
                "strategy_params": {
                    "signal_type": "death_cross",
                    "fast_ma": current[fast_col],
                    "slow_ma": current[slow_col],
                    "volume_ratio": current['volume'] / current['volume_sma']
                }
            }
        
        return None
    
    def get_required_subscriptions(self) -> List[str]:
        """구독할 데이터 스트림 정의."""
        return [f"market_data.{self.exchange}.{self.symbol}"]
    
    def _calculate_signal_strength(self, dataframe: pd.DataFrame) -> float:
        """신호 강도 계산 (0.0-1.0)."""
        if len(dataframe) < 10:
            return 0.5
        
        # 최근 10일간 가격 변동성 기반 신호 강도 계산
        recent_volatility = dataframe['close'].iloc[-10:].std()
        normalized_volatility = min(recent_volatility / dataframe['close'].iloc[-1], 0.1)
        
        # 볼륨 기반 강도
        current = dataframe.iloc[-1]
        volume_strength = min(current['volume'] / current['volume_sma'], 2.0) / 2.0
        
        # 종합 신호 강도
        signal_strength = (0.6 * (1 - normalized_volatility * 10) + 0.4 * volume_strength)
        return max(0.1, min(1.0, signal_strength))
    
    async def on_start(self):
        """전략 시작 시 초기화."""
        self.logger.info(
            f"MA Crossover strategy started",
            extra={
                "strategy_id": self.strategy_id,
                "fast_period": self.fast_period,
                "slow_period": self.slow_period,
                "symbol": self.symbol
            }
        )
    
    async def on_stop(self):
        """전략 종료 시 정리."""
        self.logger.info(
            f"MA Crossover strategy stopped",
            extra={
                "strategy_id": self.strategy_id,
                "total_signals": self.performance_metrics.signal_count
            }
        )
```

## 📊 데이터베이스 설정 예시

```sql
INSERT INTO strategies (
    name, 
    strategy_type, 
    exchange, 
    symbol, 
    parameters,
    position_sizing_config,
    is_active
) VALUES (
    'MA Cross BTC/USDT',
    'MA_CROSSOVER',
    'binance',
    'BTC/USDT',
    '{"fast": 50, "slow": 200, "exchange": "binance", "symbol": "btcusdt"}',
    '{"model": "fixed_fractional", "risk_percent": 0.02}',
    true
);
```

## 🧪 테스트 가이드

### 단위 테스트 예시

```python
import pytest
from src.strategies.ma_crossover_strategy import MovingAverageCrossoverStrategy
from src.strategies.base_strategy import StrategyConfig

def test_ma_crossover_signal_generation():
    """MA 크로스오버 신호 생성 테스트."""
    config = StrategyConfig(
        strategy_id="test_ma",
        name="Test MA Strategy",
        custom_params={"fast": 5, "slow": 10, "symbol": "btcusdt"}
    )
    
    strategy = MovingAverageCrossoverStrategy(config)
    
    # 테스트 데이터 생성
    test_data = create_golden_cross_scenario()
    df_with_indicators = strategy.populate_indicators(test_data)
    
    # 신호 생성 테스트
    market_data = {"close": 50100.0, "volume": 1000}
    signal = strategy.on_data(market_data, df_with_indicators)
    
    assert signal is not None
    assert signal["side"] == "buy"
    assert signal["signal_price"] == 50100.0
    assert "strategy_params" in signal
```

### 백테스팅 연동

```python
async def backtest_strategy():
    """전략 백테스트 실행."""
    from src.backtest.backtest_engine import BacktestEngine
    
    config = StrategyConfig(
        strategy_id="backtest_ma",
        name="Backtest MA Strategy",
        custom_params={"fast": 50, "slow": 200}
    )
    
    strategy = MovingAverageCrossoverStrategy(config)
    backtest_engine = BacktestEngine()
    
    results = await backtest_engine.run(
        strategy=strategy,
        start_date="2024-01-01",
        end_date="2024-03-01",
        initial_capital=10000
    )
    
    print(f"Total Return: {results['total_return']:.2%}")
    print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {results['max_drawdown']:.2%}")
```

## ⚠️ 주의사항 및 모범 사례

### 1. 안전성
- 항상 충분한 데이터 검증 후 신호 생성
- 예외 처리로 개별 전략 오류가 시스템 전체에 영향 없도록
- dry_run 모드에서 충분히 테스트

### 2. 성능
- 계산 집약적 작업은 `populate_indicators`에서 수행
- `on_data`는 가능한 빠르게 실행 (목표: <100ms)
- 불필요한 지표 계산 피하기

### 3. 리스크 관리
- 항상 stop_loss_price 설정 권장
- confidence 값으로 신호 품질 표현
- 포지션 크기는 Capital Manager가 결정

### 4. 로깅 및 모니터링
- 중요한 이벤트는 구조화된 로깅
- 성능 메트릭 정기적 모니터링
- 신호 생성 이유를 strategy_params에 기록

## 🔄 시스템 통합 플로우

```
1. Strategy Worker 프로세스 시작
   ↓
2. get_required_subscriptions() 호출
   ↓  
3. RabbitMQ market_data 토픽 구독
   ↓
4. 새 데이터 수신시:
   - populate_indicators() 실행
   - on_data() 또는 on_data_async() 실행
   ↓
5. 신호 생성시:
   - Capital Manager에게 request.capital.allocation 전송
   ↓
6. Capital Manager 승인시:
   - Exchange Connector가 실제 거래 실행
```

## 📈 성능 최적화 팁

1. **지표 캐싱**: 자주 사용하는 지표는 인스턴스 변수로 캐싱
2. **데이터 슬라이싱**: 필요한 기간만 계산 (예: 최근 1000개 캔들)
3. **비동기 처리**: ML 모델 등 무거운 계산은 `on_data_async` 활용
4. **메모리 관리**: 큰 데이터프레임은 적절히 정리

이 가이드를 따라 구현하면 Letrade_v1 시스템에 완벽히 통합되는 안전하고 효율적인 거래 전략을 개발할 수 있습니다.