# Letrade V1 시스템 아키텍처 V2.0

## 🎯 설계 목표
- **확장성**: 새로운 전략/거래소 추가 시 기존 코드 수정 최소화
- **안정성**: 24/7 운영을 위한 robust한 에러 처리
- **테스트 용이성**: 각 컴포넌트 독립적 테스트 가능
- **유지보수성**: 명확한 책임 분리와 인터페이스

## 🏗️ 핵심 아키텍처 원칙

### 1. **Hexagonal Architecture (Port & Adapter)**
```
Core Business Logic (Domain)
    ↕️ (Ports - 인터페이스)
Adapters (Infrastructure)
```

### 2. **Event-Driven Architecture**
```
Event Source → Event Bus → Event Handlers
```

### 3. **CQRS Pattern**
```
Command Side: 거래 실행
Query Side: 상태 조회, 리포팅
```

## 🧩 컴포넌트 설계

### **Core Domain (불변 비즈니스 로직)**
```
src/domain/
├── entities/           # 도메인 엔티티
│   ├── portfolio.py
│   ├── strategy.py
│   ├── trade.py
│   └── position.py
├── value_objects/      # 값 객체
│   ├── money.py
│   ├── symbol.py
│   └── price.py
├── services/          # 도메인 서비스
│   ├── risk_calculator.py
│   ├── position_sizer.py
│   └── pnl_calculator.py
└── events/            # 도메인 이벤트
    ├── trade_executed.py
    ├── position_opened.py
    └── risk_limit_exceeded.py
```

### **Application Layer (유스케이스)**
```
src/application/
├── commands/          # 명령 처리
│   ├── place_trade.py
│   ├── close_position.py
│   └── update_strategy.py
├── queries/           # 조회 처리
│   ├── get_portfolio.py
│   ├── get_positions.py
│   └── get_performance.py
├── handlers/          # 이벤트 핸들러
│   ├── trade_handler.py
│   ├── risk_handler.py
│   └── notification_handler.py
└── services/          # 애플리케이션 서비스
    ├── trading_service.py
    ├── portfolio_service.py
    └── strategy_service.py
```

### **Infrastructure Layer (외부 연동)**
```
src/infrastructure/
├── exchanges/         # 거래소 어댑터
│   ├── binance_adapter.py
│   ├── coinbase_adapter.py
│   └── exchange_factory.py
├── persistence/       # 데이터 저장
│   ├── postgres_repository.py
│   ├── redis_cache.py
│   └── repository_factory.py
├── messaging/         # 메시지 버스
│   ├── rabbitmq_bus.py
│   ├── memory_bus.py
│   └── message_bus_factory.py
└── notifications/     # 알림
    ├── telegram_notifier.py
    ├── email_notifier.py
    └── notification_factory.py
```

## 🔌 **Port 인터페이스 정의**

### **거래소 포트**
```python
from abc import ABC, abstractmethod
from typing import List, Optional
from domain.entities import Trade, Position

class ExchangePort(ABC):
    @abstractmethod
    async def place_order(self, trade: Trade) -> str:
        """주문 실행 - 주문 ID 반환"""
        
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """현재 포지션 조회"""
        
    @abstractmethod
    async def get_balance(self) -> dict:
        """잔고 조회"""
        
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """주문 취소"""
```

### **리스크 관리 포트**
```python
class RiskManagerPort(ABC):
    @abstractmethod
    async def validate_trade(self, trade: Trade) -> ValidationResult:
        """거래 검증"""
        
    @abstractmethod
    async def calculate_position_size(self, signal: TradingSignal) -> float:
        """포지션 크기 계산"""
        
    @abstractmethod
    async def check_risk_limits(self) -> RiskStatus:
        """리스크 한도 확인"""
```

### **데이터 저장 포트**
```python
class RepositoryPort(ABC):
    @abstractmethod
    async def save_trade(self, trade: Trade) -> None:
        """거래 저장"""
        
    @abstractmethod
    async def get_portfolio(self, portfolio_id: str) -> Portfolio:
        """포트폴리오 조회"""
        
    @abstractmethod
    async def save_performance_metric(self, metric: PerformanceMetric) -> None:
        """성과 지표 저장"""
```

## 📊 **데이터 플로우**

### **거래 실행 플로우**
```
1. Strategy → TradingSignal 생성
2. TradingService → RiskManager 검증
3. RiskManager → PositionSizer 크기 계산  
4. TradingService → Exchange 주문 실행
5. Exchange → TradeExecuted 이벤트 발생
6. EventHandler → Portfolio/Position 업데이트
7. NotificationHandler → 사용자 알림
```

### **에러 처리 플로우**
```
1. Exception 발생
2. ErrorHandler → 에러 분류
3. Critical Error → 즉시 알림 + 거래 중단
4. Normal Error → 로그 기록 + 재시도
5. BusinessError → 사용자 알림
```

## 🧪 **테스트 전략**

### **1. 단위 테스트 (Unit Tests)**
- Domain Layer: 순수 비즈니스 로직
- 외부 의존성 없이 빠른 실행
- 100% 커버리지 목표

### **2. 통합 테스트 (Integration Tests)**
- Port & Adapter 인터페이스
- 실제 인프라 없이 Mock 사용
- 컴포넌트 간 상호작용 검증

### **3. E2E 테스트 (End-to-End Tests)**
- 전체 플로우 검증
- Test Container 사용
- 프로덕션 환경과 동일한 설정

## 🚀 **확장성 고려사항**

### **새로운 거래소 추가**
```python
# 기존 코드 수정 없이 새 어댑터만 추가
class KrakenAdapter(ExchangePort):
    async def place_order(self, trade: Trade) -> str:
        # Kraken API 구현
        pass
```

### **새로운 전략 추가**
```python
# BaseStrategy 인터페이스 구현만으로 자동 통합
class MLStrategy(BaseStrategy):
    def generate_signal(self, data: MarketData) -> TradingSignal:
        # ML 로직 구현
        pass
```

### **새로운 알림 채널 추가**
```python
# 기존 시스템에 자동 통합
class SlackNotifier(NotificationPort):
    async def send_alert(self, message: str) -> None:
        # Slack API 구현
        pass
```

## 📈 **성능 고려사항**

### **비동기 처리**
- 모든 I/O 작업 async/await
- 동시성 처리로 지연시간 최소화

### **캐싱 전략**
- 자주 조회되는 데이터 Redis 캐싱
- 시장 데이터 로컬 캐시

### **배치 처리**
- 대량 데이터 처리 시 배치 단위
- 메모리 사용량 최적화

## 🔒 **보안 고려사항**

### **API 키 관리**
- GCP Secret Manager 통합
- 환경별 분리 관리

### **데이터 암호화**
- 민감 정보 DB 저장 시 암호화
- 통신 구간 TLS 적용

### **감사 로깅**
- 모든 거래 활동 추적
- 변경 이력 보관

---

## 📋 **다음 단계**
1. 각 컴포넌트별 상세 설계 문서 작성
2. 인터페이스 정의 및 구현 가이드
3. 테스트 케이스 정의
4. 마이그레이션 계획 수립