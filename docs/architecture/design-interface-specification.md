# 인터페이스 명세서 (Interface Specification)

## 🎯 목표
- **계약 기반 개발**: 인터페이스 먼저 정의, 구현은 나중에
- **테스트 용이성**: Mock 객체 쉽게 생성 가능
- **확장성**: 새로운 구현체 추가 시 기존 코드 변경 없음

## 🔌 **Core Ports (핵심 인터페이스)**

### **1. ExchangePort - 거래소 추상화**

```python
# src/domain/ports/exchange_port.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime

from ..entities.trade import Trade
from ..entities.position import Position
from ..value_objects.symbol import Symbol
from ..value_objects.money import Money

class ExchangePort(ABC):
    """거래소 연동을 위한 포트 인터페이스"""
    
    @abstractmethod
    async def connect(self) -> bool:
        """거래소 연결
        
        Returns:
            bool: 연결 성공 여부
            
        Raises:
            ConnectionError: 연결 실패 시
        """
        pass
    
    @abstractmethod
    async def place_order(self, trade: Trade) -> str:
        """주문 실행
        
        Args:
            trade: 거래 정보
            
        Returns:
            str: 거래소 주문 ID
            
        Raises:
            InsufficientFundsError: 잔고 부족
            InvalidOrderError: 잘못된 주문 정보
            ExchangeError: 거래소 오류
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """주문 취소
        
        Args:
            order_id: 거래소 주문 ID
            
        Returns:
            bool: 취소 성공 여부
        """
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """주문 상태 조회
        
        Args:
            order_id: 거래소 주문 ID
            
        Returns:
            Dict: 주문 상태 정보
            {
                "id": "12345",
                "status": "filled|partial|open|canceled",
                "filled_amount": Decimal("1.5"),
                "remaining_amount": Decimal("0.5"),
                "avg_price": Decimal("50000.0")
            }
        """
        pass
    
    @abstractmethod
    async def get_balance(self) -> Dict[str, Money]:
        """잔고 조회
        
        Returns:
            Dict[str, Money]: 통화별 잔고
            {"USDT": Money("1000.50", "USDT"), "BTC": Money("0.1", "BTC")}
        """
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """현재 포지션 목록 조회
        
        Returns:
            List[Position]: 활성 포지션 목록
        """
        pass
    
    @abstractmethod
    async def get_market_price(self, symbol: Symbol) -> Decimal:
        """현재 시장 가격 조회
        
        Args:
            symbol: 거래 심볼
            
        Returns:
            Decimal: 현재 가격
        """
        pass
    
    @abstractmethod
    async def subscribe_market_data(self, symbols: List[Symbol]) -> None:
        """실시간 시장 데이터 구독
        
        Args:
            symbols: 구독할 심볼 목록
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """거래소 연결 상태 확인
        
        Returns:
            Dict: 상태 정보
            {
                "connected": True,
                "latency_ms": 50,
                "rate_limit_remaining": 1000,
                "last_response_time": "2025-01-01T00:00:00Z"
            }
        """
        pass
```

### **2. RiskManagerPort - 리스크 관리**

```python
# src/domain/ports/risk_manager_port.py
from abc import ABC, abstractmethod
from typing import Dict, Any
from decimal import Decimal

from ..entities.trade import Trade
from ..entities.portfolio import Portfolio
from ..value_objects.symbol import Symbol

class ValidationResult:
    def __init__(self, is_valid: bool, reason: str = "", risk_score: float = 0.0):
        self.is_valid = is_valid
        self.reason = reason
        self.risk_score = risk_score  # 0.0 (안전) ~ 1.0 (위험)

class RiskManagerPort(ABC):
    """리스크 관리를 위한 포트 인터페이스"""
    
    @abstractmethod
    async def validate_trade(self, trade: Trade, portfolio: Portfolio) -> ValidationResult:
        """거래 검증
        
        Args:
            trade: 검증할 거래
            portfolio: 현재 포트폴리오
            
        Returns:
            ValidationResult: 검증 결과
            
        검증 항목:
        - 포지션 크기 한도
        - 일일 손실 한도
        - 포트폴리오 노출도
        - 금지 심볼 체크
        """
        pass
    
    @abstractmethod
    async def calculate_position_size(self, 
                                     signal_strength: float,
                                     symbol: Symbol,
                                     portfolio: Portfolio) -> Decimal:
        """적정 포지션 크기 계산
        
        Args:
            signal_strength: 신호 강도 (0.0 ~ 1.0)
            symbol: 거래 심볼
            portfolio: 현재 포트폴리오
            
        Returns:
            Decimal: 계산된 포지션 크기
        """
        pass
    
    @abstractmethod
    async def check_emergency_stop(self, portfolio: Portfolio) -> bool:
        """긴급 정지 조건 확인
        
        Args:
            portfolio: 현재 포트폴리오
            
        Returns:
            bool: 긴급 정지 필요 여부
            
        조건:
        - 일일 손실 한도 초과
        - 최대 드로우다운 초과
        - 연속 손실 횟수 초과
        """
        pass
    
    @abstractmethod
    async def get_risk_metrics(self, portfolio: Portfolio) -> Dict[str, Any]:
        """리스크 지표 계산
        
        Returns:
            Dict: 리스크 지표
            {
                "var_95": Decimal("500.0"),      # 95% VaR
                "max_drawdown": Decimal("0.15"),  # 최대 드로우다운
                "sharpe_ratio": Decimal("1.5"),   # 샤프 비율
                "exposure_pct": Decimal("0.8"),   # 포트폴리오 노출도
                "daily_pnl": Decimal("-100.0")    # 일일 손익
            }
        """
        pass
```

### **3. RepositoryPort - 데이터 저장소**

```python
# src/domain/ports/repository_port.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..entities.portfolio import Portfolio
from ..entities.trade import Trade
from ..entities.position import Position
from ..entities.strategy import Strategy

class RepositoryPort(ABC):
    """데이터 저장소를 위한 포트 인터페이스"""
    
    # Portfolio 관련
    @abstractmethod
    async def save_portfolio(self, portfolio: Portfolio) -> None:
        """포트폴리오 저장"""
        pass
    
    @abstractmethod
    async def get_portfolio(self, portfolio_id: str) -> Optional[Portfolio]:
        """포트폴리오 조회"""
        pass
    
    @abstractmethod
    async def update_portfolio_balance(self, portfolio_id: str, new_balance: Dict[str, Any]) -> None:
        """포트폴리오 잔고 업데이트"""
        pass
    
    # Trade 관련
    @abstractmethod
    async def save_trade(self, trade: Trade) -> None:
        """거래 저장"""
        pass
    
    @abstractmethod
    async def get_trades(self, 
                        portfolio_id: str, 
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None) -> List[Trade]:
        """거래 내역 조회"""
        pass
    
    @abstractmethod
    async def update_trade_status(self, trade_id: str, status: str, 
                                 exchange_order_id: Optional[str] = None) -> None:
        """거래 상태 업데이트"""
        pass
    
    # Position 관련
    @abstractmethod
    async def save_position(self, position: Position) -> None:
        """포지션 저장"""
        pass
    
    @abstractmethod
    async def get_active_positions(self, portfolio_id: str) -> List[Position]:
        """활성 포지션 조회"""
        pass
    
    @abstractmethod
    async def close_position(self, position_id: str, close_price: Decimal, close_time: datetime) -> None:
        """포지션 종료"""
        pass
    
    # Strategy 관련
    @abstractmethod
    async def save_strategy(self, strategy: Strategy) -> None:
        """전략 저장"""
        pass
    
    @abstractmethod
    async def get_active_strategies(self, portfolio_id: str) -> List[Strategy]:
        """활성 전략 조회"""
        pass
```

### **4. NotificationPort - 알림 시스템**

```python
# src/domain/ports/notification_port.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from enum import Enum

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class NotificationPort(ABC):
    """알림을 위한 포트 인터페이스"""
    
    @abstractmethod
    async def send_alert(self, 
                        level: AlertLevel,
                        title: str,
                        message: str,
                        metadata: Dict[str, Any] = None) -> bool:
        """알림 전송
        
        Args:
            level: 알림 레벨
            title: 알림 제목
            message: 알림 내용
            metadata: 추가 정보
            
        Returns:
            bool: 전송 성공 여부
        """
        pass
    
    @abstractmethod
    async def send_trade_notification(self, trade: Trade) -> bool:
        """거래 알림 전송"""
        pass
    
    @abstractmethod
    async def send_performance_report(self, portfolio_id: str, metrics: Dict[str, Any]) -> bool:
        """성과 리포트 전송"""
        pass
    
    @abstractmethod
    async def send_risk_alert(self, risk_type: str, current_value: float, limit_value: float) -> bool:
        """리스크 알림 전송"""
        pass
```

## 🏭 **Factory Patterns (생성 패턴)**

### **ExchangeFactory**
```python
# src/infrastructure/factories/exchange_factory.py
from typing import Dict, Type
from ..exchanges.binance_adapter import BinanceAdapter
from ..exchanges.coinbase_adapter import CoinbaseAdapter
from ..exchanges.mock_exchange import MockExchange

class ExchangeFactory:
    _exchanges: Dict[str, Type[ExchangePort]] = {
        "binance": BinanceAdapter,
        "coinbase": CoinbaseAdapter,
        "mock": MockExchange
    }
    
    @classmethod
    def create(cls, exchange_name: str, config: Dict[str, Any]) -> ExchangePort:
        """거래소 어댑터 생성
        
        Args:
            exchange_name: 거래소 이름 ("binance", "coinbase", "mock")
            config: 설정 정보
            
        Returns:
            ExchangePort: 거래소 어댑터 인스턴스
            
        Raises:
            ValueError: 지원하지 않는 거래소
        """
        if exchange_name not in cls._exchanges:
            raise ValueError(f"Unsupported exchange: {exchange_name}")
        
        return cls._exchanges[exchange_name](config)
    
    @classmethod
    def register_exchange(cls, name: str, exchange_class: Type[ExchangePort]) -> None:
        """새로운 거래소 등록"""
        cls._exchanges[name] = exchange_class
```

## 🧪 **테스트 지원 인터페이스**

### **TestFixturePort**
```python
# src/domain/ports/test_fixture_port.py
class TestFixturePort(ABC):
    """테스트를 위한 픽스처 인터페이스"""
    
    @abstractmethod
    async def setup_test_portfolio(self) -> Portfolio:
        """테스트용 포트폴리오 생성"""
        pass
    
    @abstractmethod
    async def create_mock_market_data(self, symbol: Symbol, count: int) -> List[Dict[str, Any]]:
        """모의 시장 데이터 생성"""
        pass
    
    @abstractmethod
    async def cleanup_test_data(self) -> None:
        """테스트 데이터 정리"""
        pass
```

## 📋 **구현 가이드라인**

### **1. 에러 처리 표준**
```python
# src/domain/exceptions.py
class LetradeException(Exception):
    """기본 예외 클래스"""
    pass

class ExchangeError(LetradeException):
    """거래소 관련 오류"""
    pass

class RiskLimitExceededError(LetradeException):
    """리스크 한도 초과"""
    pass

class InsufficientFundsError(ExchangeError):
    """잔고 부족"""
    pass
```

### **2. 로깅 표준**
```python
# 모든 포트 구현체는 구조화된 로깅 사용
logger.info("Order placed", extra={
    "order_id": order_id,
    "symbol": symbol,
    "amount": amount,
    "price": price,
    "exchange": "binance"
})
```

### **3. 메트릭 수집 표준**
```python
# 모든 포트 구현체는 메트릭 수집
from prometheus_client import Counter, Histogram

TRADE_COUNTER = Counter('trades_total', 'Total trades', ['exchange', 'symbol', 'side'])
TRADE_LATENCY = Histogram('trade_latency_seconds', 'Trade execution latency')
```

---

## 📋 **다음 단계**
1. 각 포트별 구현체 작성 가이드
2. 테스트 케이스 템플릿 정의
3. 마이그레이션 스크립트 작성
4. 성능 벤치마크 기준 설정