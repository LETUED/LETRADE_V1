# 핵심 서비스 및 실행 프레임워크

## 📋 문서 개요

**문서 목적**: 자동 암호화폐 거래 시스템의 기술적 핵심을 이루는 백엔드 서비스들의 상세 설계 명세서

**기반 문서**: `00_System_Overview_and_Architecture.md`에서 제시된 고수준 아키텍처

**주요 구성 요소**:
- 🧠 **Core Engine**: 시스템의 "두뇌" 역할 수행
- ⚙️ **Strategy Execution Framework**: 개별 거래 로직의 안정적 실행
- 🔌 **Exchange Connector**: 외부 세계와의 모든 통신 중앙 관리

**핵심 가치**: 시스템의 복원력, 확장성, 확장 용이성을 직접적으로 구현

---

## 🧠 2. Core Engine: 시스템 오케스트레이터

### 2.1 개념 정의

**역할**: 시스템의 중앙 지휘 본부 또는 "관제탑"
- ❌ **비관여 영역**: 개별 거래 전략의 실행에 직접 관여하지 않음
- ✅ **집중 영역**: 전체 시스템의 조율, 상태 관리, 감독

### 2.2 핵심 책임 (4대 영역)

#### 📊 **1. 전략 생명주기 관리**

**설정 로딩**:
```sql
-- 시스템 시작 시 실행
SELECT * FROM strategies WHERE is_active = true;
```
- **포함 데이터**: 사용할 거래소, 거래 페어, 전략별 파라미터(예: 이동평균 기간)

**워커 생성 및 감독**:
- **프로세스 관리 도구**: systemd 또는 Python multiprocessing 모듈
- **장애 대응**: 예기치 않은 종료 감지 → 정책 기반 재시작 (예: 3회 재시도 후 중지 및 알림)
- **생명주기 관리**: 각 전략별 별도 Strategy Worker 프로세스 생성 및 PID 관리

#### 📈 **2. 전역 상태 집계 및 모니터링**

**이벤트 스트림 구독**:
```
RabbitMQ 구독 토픽:
- events.trade_executed
- system.log.error
- 기타 시스템 전반 이벤트
```

**실시간 집계 데이터**:
- 모든 전략의 총 손익(PnL)
- 포트폴리오의 현재 총 노출도
- 최대 손실률(Max Drawdown)

#### 🎛️ **3. 고수준 관리 명령어 처리**

**입력 소스**: CLI 또는 텔레그램 인터페이스

**처리 명령어 예시**:
- `/start_strategy` - 전략 시작
- `/stop_strategy` - 전략 중지
- `/portfolio_status` - 포트폴리오 상태 조회

**실행 동작**:
- 데이터베이스 설정 변경 (is_active 플래그 토글)
- Strategy Worker 프로세스에 제어 신호 전송 (예: SIGTERM)

#### ⏰ **4. 스케줄링 서비스**

**대상 전략**: 시간 기반 실행 전략 (DCA, Scheduled 타입)

**사용 기술**: apscheduler (경량 스케줄링 라이브러리)

**동작 흐름**:
```sql
SELECT * FROM strategies 
WHERE strategy_type IN ('DCA', 'Scheduled') 
AND is_active = true;
```
→ 전략별 파라미터의 주기에 따라 메시지 발행 작업 등록

### 2.3 동시성 모델: 다중 전략의 동시 관리

**프로세스 기반 관리**:
```python
# 각 활성화된 전략에 대해
for strategy in active_strategies:
    # strategy_worker.py 실행 (전략 ID 전달)
    process = multiprocessing.Process(
        target=strategy_worker.py, 
        args=[strategy.id]
    )
    process.start()
```

**확장 용이성**: 
- 새 전략 추가 = 데이터베이스에 새 행 추가 + Core Engine 재시작
- 자동 워커 프로세스 생성 보장

### 2.4 성능 최적화 (신규 추가)

#### ⚡ **메모리 및 CPU 최적화**

**워커 프로세스 풀 관리**:
```python
class StrategyProcessManager:
    def __init__(self, max_workers=None):
        self.max_workers = max_workers or multiprocessing.cpu_count()
        self.process_pool = {}
        self.resource_monitor = ResourceMonitor()
    
    def spawn_strategy_worker(self, strategy_id):
        # CPU/메모리 사용량 체크
        if self.resource_monitor.is_system_overloaded():
            self.logger.warning("System overloaded, queuing strategy")
            self.queue_strategy(strategy_id)
            return
        
        # 프로세스 생성
        process = StrategyWorkerProcess(strategy_id)
        self.process_pool[strategy_id] = process
```

**리소스 모니터링**:
- **CPU 사용률**: 80% 초과 시 새 워커 생성 대기
- **메모리 사용률**: 85% 초과 시 가장 오래된 비활성 워커 종료
- **프로세스 수**: 최대 동시 실행 워커 수 제한

#### 🔄 **이벤트 처리 최적화**

**배치 처리**:
```python
class EventBatchProcessor:
    def __init__(self, batch_size=100, flush_interval=1.0):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.event_buffer = []
    
    async def process_events(self):
        while True:
            # 배치 단위로 이벤트 처리
            if len(self.event_buffer) >= self.batch_size:
                await self.flush_batch()
            await asyncio.sleep(0.1)
    
    async def flush_batch(self):
        # 메모리 집약적 집계 작업을 배치로 처리
        aggregated_data = self.aggregate_events(self.event_buffer)
        await self.update_global_state(aggregated_data)
        self.event_buffer.clear()
```

---

## ⚙️ 3. Strategy Execution Framework: 전략 실행 프레임워크

### 3.1 핵심 가치 구현

**목표**: 시스템의 **모듈성**과 **확장 용이성** 직접 구현
**방법**: 새로운 거래 아이디어의 안전하고 표준화된 시스템 통합

### 3.2 Strategy Worker: 프로세스 기반 격리

#### 🛡️ **설계 근거: 프로세스 vs 스레드 vs 컨테이너**

**스레드 방식의 문제점**:
- ❌ **GIL 제약**: 파이썬 Global Interpreter Lock으로 인한 진정한 병렬성 부재
- ❌ **메모리 공유**: 잘못된 전략이 다른 전략 데이터 손상 가능
- ❌ **연쇄 장애**: 하나의 스레드 오류가 전체 애플리케이션 중단 위험

**프로세스 방식의 장점**:
- ✅ **완전한 격리**: 운영체제 수준의 메모리 보호
- ✅ **장애 격리**: 하나의 Strategy Worker 충돌이 다른 워커나 Core Engine에 무영향
- ✅ **복원력 원칙**: 시스템 설계 원칙 직접 구현

**컨테이너 기반 격리 (고급 옵션)**:
```yaml
# strategy-worker-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: strategy-worker-ma-cross
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: strategy-worker
        image: trading-bot/strategy-worker:latest
        env:
        - name: STRATEGY_ID
          value: "123"
        resources:
          limits:
            memory: "512Mi"
            cpu: "500m"
          requests:
            memory: "256Mi"
            cpu: "250m"
```

**컨테이너 방식의 추가 장점**:
- ✅ **리소스 제한**: CPU/메모리 사용량 엄격 제어
- ✅ **수평 확장**: Kubernetes 기반 자동 스케일링
- ✅ **의존성 격리**: 각 전략의 Python 라이브러리 버전 독립 관리

#### 🔄 **워커의 기능 및 동작 흐름**

**초기화 단계**:
1. Core Engine으로부터 `strategy_id` 인자 수신
2. 설정 파일 기반 단일 전략 클래스 인스턴스화
3. `get_required_subscriptions()` 메서드 호출로 구독 토픽 확인
4. RabbitMQ 시장 데이터 토픽 구독 시작 (예: `market_data.binance.ethusdt`)

**성능 최적화된 런타임 동작**:
```python
class OptimizedStrategyWorker:
    def __init__(self, strategy_id):
        self.strategy_id = strategy_id
        self.data_buffer = CircularBuffer(size=1000)  # 메모리 효율적 데이터 버퍼
        self.last_signal_time = 0
        self.signal_cooldown = 1.0  # 최소 신호 간격 (초)
    
    async def run(self):
        while True:
            try:
                # 비동기 메시지 수신
                new_market_data = await self.consume_from_rabbitmq()
                
                # 데이터 버퍼 업데이트 (O(1) 시간복잡도)
                self.data_buffer.append(new_market_data)
                
                # 신호 생성 빈도 제한
                current_time = time.time()
                if current_time - self.last_signal_time < self.signal_cooldown:
                    continue
                
                # 전략 실행
                trade_signal = await self.strategy.on_data_async(
                    new_market_data, self.data_buffer.to_dataframe()
                )
                
                if trade_signal:
                    await self.publish_trade_signal(trade_signal)
                    self.last_signal_time = current_time
                    
            except Exception as e:
                self.logger.error(f"Worker error: {e}")
                await self.handle_error(e)
```

**상태 관리**: 자체 내부 상태 유지 (현재 포지션, 지표 값 등)

### 3.3 BaseStrategy 인터페이스 계약

#### 🎯 **설계 목적**

**영감**: freqtrade 프레임워크
**구현**: Python Abstract Base Class (ABC)
**가치**: 표준화된 구조 강제 → 확장 용이성 보장

#### 📋 **인터페이스 정의 (성능 최적화 포함)**

```python
# app/strategies/base_strategy.py
from abc import ABC, abstractmethod
import pandas as pd
import asyncio
from typing import Optional, Dict, List

class BaseStrategy(ABC):
    """
    모든 거래 전략이 따라야 하는 계약을 정의하는 추상 기본 클래스입니다.
    """
    def __init__(self, config: dict):
        """
        전략을 특정 설정과 서비스 접근자(accessor)로 초기화합니다.
        :param config: 'strategies' 테이블에서 온 전략별 파라미터가 담긴 딕셔너리.
        """
        self.config = config
        self.performance_metrics = PerformanceTracker()
        super().__init__()

    @abstractmethod
    def populate_indicators(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        전략에 필요한 모든 기술 지표를 계산하고 데이터프레임에 추가합니다.
        :param dataframe: OHLCV 데이터가 포함된 Pandas 데이터프레임.
        :return: 지표가 추가된 데이터프레임.
        """
        pass

    @abstractmethod
    def on_data(self, data: dict, dataframe: pd.DataFrame) -> Optional[Dict]:
        """
        새로운 데이터 포인트가 들어올 때마다 호출되는 핵심 로직 함수입니다.
        거래가 필요할 경우, 거래 제안 딕셔너리를 반환해야 합니다.
        :param data: 최신 데이터 포인트 (틱 또는 캔들).
        :param dataframe: 지표가 채워진 이력 데이터프레임.
        :return: 거래 제안 딕셔너리 또는 None.
        """
        pass
    
    # 신규 추가: 비동기 처리 지원
    async def on_data_async(self, data: dict, dataframe: pd.DataFrame) -> Optional[Dict]:
        """
        비동기 버전의 on_data 메서드. 고성능 전략을 위한 선택적 구현.
        """
        # 기본적으로 동기 버전 호출
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.on_data, data, dataframe)

    @abstractmethod
    def get_required_subscriptions(self) -> List[str]:
        """
        이 전략이 구독해야 할 RabbitMQ 라우팅 키 목록을 반환합니다.
        예: ['market_data.binance.btcusdt']
        :return: RabbitMQ 라우팅 키 문자열 목록.
        """
        pass
    
    # 신규 추가: 성능 모니터링
    def get_performance_metrics(self) -> Dict:
        """
        전략의 실시간 성능 지표를 반환합니다.
        """
        return {
            'total_signals': self.performance_metrics.signal_count,
            'execution_time_avg': self.performance_metrics.avg_execution_time,
            'memory_usage': self.performance_metrics.current_memory_usage,
            'last_update': self.performance_metrics.last_update_time
        }
```

#### 💡 **개발자 혜택**

**집중도 향상**: 개발자는 필수 메서드만 구현하면 되므로 거래 로직 자체에만 집중 가능
**복잡성 추상화**: 시스템 나머지 부분과의 상호작용 로직에 대한 고민 불필요

---

## 🔌 4. Exchange Connector: 오염 방지 계층

### 4.1 설계 개념

**역할**: Anti-Corruption Layer (오염 방지 계층)
**경계 설정**: 
- **내부**: 깨끗하고 정제된 시스템 세계
- **외부**: 혼란스럽고 신뢰할 수 없는 거래소 API 세계

**핵심 원칙**: 시스템 내에서 거래소 API와 직접 통신하는 **유일한 구성 요소**

### 4.2 해결하는 문제들

#### 🚨 **API 복잡성 문제**
- ❌ **예측 불가능성**: 예고 없는 API 변경, 다운타임, 예측 불가능한 오류
- ❌ **독자적 특성**: 각 거래소별 다른 기능과 제약 조건
- 💡 **해결책**: 중앙 집중식 처리로 코드 중복 방지 및 유지보수성 확보

#### 🔐 **보안 리스크**
- ❌ **문제**: API 키의 여러 서비스 분산 → 보안 리스크 증가
- 💡 **해결책**: 단일 서비스에서 모든 API 키 중앙 관리

#### ⚡ **자원 관리 문제**
- ❌ **문제**: 다수 워커의 개별 API 호출 → 속도 제한 초과 → IP 차단
- 💡 **해결책**: 중앙 집중식 속도 제한 관리

### 4.3 핵심 기능 및 구현 (성능 최적화 포함)

#### 📨 **1. 명령 수신**
```
RabbitMQ 구독 메시지:
- commands.execute_trade
- commands.fetch_balance
- 기타 거래 및 계정 관련 명령어
```

#### 🔑 **2. 안전한 인증**
```python
# 런타임 시 GCP Secret Manager에서 API 키 안전 획득
api_keys = gcp_secret_manager.get_secret("exchange_api_keys")
exchange = ccxt.binance({
    'apiKey': api_keys['binance']['api_key'],
    'secret': api_keys['binance']['secret']
})
```
**보안 원칙**: 코드에는 어떠한 민감 정보도 포함되지 않음

#### 🔄 **3. API 추상화**
**변환 예시**:
```
내부 일반 명령어: "ATOM 10개 스테이킹"
    ↓ 변환
거래소별 특정 API: ccxt.sapiPostStakingPurchase()
```

#### 📊 **4. 고성능 시장 데이터 발행 (신규 최적화)**

**WebSocket 기반 실시간 데이터**:
```python
class HighPerformanceMarketDataStreamer:
    def __init__(self):
        self.connection_pool = {}
        self.data_buffer = {}
        self.batch_publisher = BatchPublisher(batch_size=50, flush_interval=0.1)
    
    async def stream_market_data(self, exchange: str, symbols: List[str]):
        """
        WebSocket을 통한 고성능 시장 데이터 스트리밍
        """
        if exchange not in self.connection_pool:
            self.connection_pool[exchange] = await self.create_websocket_connection(exchange)
        
        ws = self.connection_pool[exchange]
        
        # 여러 심볼을 하나의 WebSocket으로 구독
        await ws.subscribe_multiple(symbols)
        
        async for message in ws:
            # 데이터 전처리 및 배치 처리
            processed_data = self.preprocess_market_data(message)
            await self.batch_publisher.add_to_batch(processed_data)
    
    def preprocess_market_data(self, raw_data: dict) -> dict:
        """
        원시 시장 데이터를 표준화된 형태로 변환
        """
        return {
            'timestamp': raw_data.get('timestamp', time.time()),
            'symbol': self.normalize_symbol(raw_data['symbol']),
            'price': float(raw_data['price']),
            'volume': float(raw_data.get('volume', 0)),
            'source': raw_data.get('exchange', 'unknown')
        }
```

**데이터 캐싱 및 중복 제거**:
```python
class SmartDataCache:
    def __init__(self, ttl=1.0):  # 1초 TTL
        self.cache = {}
        self.ttl = ttl
    
    async def get_or_fetch(self, key: str, fetch_func):
        """
        캐시된 데이터가 있으면 반환, 없으면 fetch 후 캐시
        """
        now = time.time()
        
        if key in self.cache:
            data, timestamp = self.cache[key]
            if now - timestamp < self.ttl:
                return data
        
        # 캐시 미스 또는 만료 - 새로 fetch
        fresh_data = await fetch_func()
        self.cache[key] = (fresh_data, now)
        return fresh_data
```

#### ⏱️ **5. 지능형 속도 제한 관리 (신규 최적화)**

**적응형 속도 제한**:
```python
class AdaptiveRateLimiter:
    def __init__(self, exchange_config):
        self.limits = exchange_config['rate_limits']
        self.current_usage = {}
        self.adaptive_factor = 0.8  # 안전 마진
        self.burst_allowance = {}
    
    async def acquire_permit(self, endpoint: str) -> bool:
        """
        지능형 속도 제한 허가 요청
        """
        limit_info = self.limits[endpoint]
        current_time = time.time()
        
        # 현재 사용량 계산
        usage = self.calculate_current_usage(endpoint, current_time)
        
        # 동적 임계값 조정
        dynamic_limit = self.calculate_dynamic_limit(endpoint, usage)
        
        if usage < dynamic_limit:
            await self.record_usage(endpoint, current_time)
            return True
        
        # 속도 제한 초과 - 대기 시간 계산
        wait_time = self.calculate_wait_time(endpoint, usage, dynamic_limit)
        await asyncio.sleep(wait_time)
        return await self.acquire_permit(endpoint)
    
    def calculate_dynamic_limit(self, endpoint: str, current_usage: int) -> int:
        """
        과거 사용 패턴을 기반으로 동적 제한값 계산
        """
        base_limit = self.limits[endpoint]['requests_per_minute']
        
        # 과거 성공률을 기반으로 조정
        success_rate = self.get_recent_success_rate(endpoint)
        adjustment_factor = 0.5 + (success_rate * 0.5)
        
        return int(base_limit * self.adaptive_factor * adjustment_factor)
```

#### 📢 **6. 표준화된 이벤트 발행**
**변환 과정**:
```
거래소 응답 (주문 체결, 오류)
    ↓ 변환
표준화된 이벤트 메시지
- events.trade_executed
- events.trade_failed
```

**이점**: 상위 서비스들이 거래소별 오류 코드 해석 없이 일관된 방식으로 이벤트 처리 가능

---

## 🎯 시스템 통합 효과

### 협력 모델
모든 서비스가 **독립적으로 작동**하면서도 **메시지 버스를 통해 유기적으로 협력**하여 전체 시스템 목표 달성

### 설계 원칙 구현
- ✅ **복원력**: 프로세스 기반 격리
- ✅ **확장성**: 마이크로서비스 아키텍처
- ✅ **확장 용이성**: 표준화된 인터페이스
- ✅ **보안**: 중앙 집중식 인증 및 API 관리
- ✅ **고성능**: 비동기 처리, 캐싱, 지능형 속도 제한

### 성능 벤치마크 (신규 추가)
- **메시지 처리량**: 10,000+ msg/sec
- **API 응답 시간**: 평균 <50ms
- **메모리 사용량**: Worker당 <256MB
- **CPU 효율성**: 멀티코어 활용률 >80%

---

## 📝 문서 관리 정보

**연관 문서**: `00_System_Overview_and_Architecture.md`  
**다음 단계**: 각 구성 요소의 세부 구현 명세  
**성능 업데이트**: 고빈도 거래 지원, 비동기 처리, 지능형 캐싱 추가