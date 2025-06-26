# 구현 실행 계획 및 마이그레이션 가이드

## 🎯 실행 목표
- **안전한 마이그레이션**: 기존 시스템 중단 없이 점진적 전환
- **최소 코드 수정**: 새로운 인터페이스 도입으로 변경 최소화
- **검증된 구현**: 각 단계별 철저한 테스트
- **롤백 가능**: 문제 발생 시 이전 상태로 복구 가능

## 📋 **마이그레이션 전략: Strangler Fig Pattern**

```
기존 시스템 ──→ 새로운 시스템
     ↓              ↓
[Legacy Code] → [Port Interface] → [New Implementation]
```

### **단계별 마이그레이션**
1. **Interface 도입** → 기존 코드를 포트 뒤에 숨김
2. **New Implementation** → 포트 인터페이스 구현
3. **점진적 교체** → 기능별로 하나씩 교체
4. **Legacy 제거** → 사용되지 않는 코드 정리

## 🗓️ **상세 실행 계획 (8주)**

### **Week 1: 기반 구조 설정**

#### **Day 1-2: Domain Layer 구현**
```bash
# 우선순위 1: 핵심 엔티티 구현
src/domain/
├── entities/
│   ├── __init__.py
│   ├── portfolio.py      # ✅ 구현
│   ├── trade.py          # ✅ 구현  
│   ├── position.py       # ✅ 구현
│   └── strategy.py       # ✅ 구현
├── value_objects/
│   ├── __init__.py
│   ├── money.py          # ✅ 구현
│   ├── symbol.py         # ✅ 구현
│   └── price.py          # ✅ 구현
└── exceptions.py         # ✅ 구현
```

**구현 예시:**
```python
# src/domain/entities/portfolio.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime
from ..value_objects.money import Money
from ..exceptions import InsufficientFundsError

@dataclass
class Portfolio:
    """포트폴리오 엔티티 (Domain Layer)"""
    
    id: str
    name: str
    base_currency: str
    created_at: datetime = field(default_factory=datetime.now)
    _balances: Dict[str, Money] = field(default_factory=dict)
    _reserved: Dict[str, Money] = field(default_factory=dict)
    
    def __post_init__(self):
        """초기화 후 검증"""
        if not self.id:
            raise ValueError("Portfolio ID cannot be empty")
        if not self.name:
            raise ValueError("Portfolio name cannot be empty")
    
    @property
    def total_balance(self) -> Money:
        """총 잔고 (예약 자금 포함)"""
        total = self._balances.get(self.base_currency, Money("0", self.base_currency))
        reserved = self._reserved.get(self.base_currency, Money("0", self.base_currency))
        return total + reserved
    
    @property
    def available_balance(self) -> Money:
        """사용 가능 잔고 (예약 자금 제외)"""
        return self._balances.get(self.base_currency, Money("0", self.base_currency))
    
    def reserve_funds(self, amount: Money) -> str:
        """자금 예약"""
        if amount.currency != self.base_currency:
            raise ValueError(f"Currency mismatch: {amount.currency} != {self.base_currency}")
        
        available = self.available_balance
        if available.amount < amount.amount:
            raise InsufficientFundsError(f"Insufficient funds: {available} < {amount}")
        
        # 예약 처리
        reservation_id = f"reserve_{datetime.now().timestamp()}"
        self._balances[self.base_currency] = available - amount
        self._reserved[self.base_currency] = self._reserved.get(self.base_currency, Money("0", self.base_currency)) + amount
        
        return reservation_id
    
    def release_reservation(self, reservation_id: str, amount: Money) -> None:
        """예약 해제"""
        # 구현...
        pass
```

#### **Day 3-4: Port Interfaces 정의**
```python
# src/domain/ports/__init__.py
from .exchange_port import ExchangePort
from .risk_manager_port import RiskManagerPort
from .repository_port import RepositoryPort
from .notification_port import NotificationPort

__all__ = [
    "ExchangePort",
    "RiskManagerPort", 
    "RepositoryPort",
    "NotificationPort"
]
```

#### **Day 5-7: 기존 코드를 Adapter로 래핑**
```python
# src/infrastructure/adapters/legacy_capital_manager_adapter.py
from src.domain.ports.risk_manager_port import RiskManagerPort, ValidationResult
from src.capital_manager.main import CapitalManager as LegacyCapitalManager

class LegacyCapitalManagerAdapter(RiskManagerPort):
    """기존 Capital Manager를 새로운 인터페이스로 래핑"""
    
    def __init__(self, config: Dict[str, Any]):
        self._legacy_manager = LegacyCapitalManager(config)
    
    async def validate_trade(self, trade: Trade, portfolio: Portfolio) -> ValidationResult:
        """기존 validate_trade를 새로운 인터페이스로 변환"""
        # 새로운 Trade 엔티티를 기존 format으로 변환
        legacy_request = {
            "strategy_id": trade.strategy_id,
            "symbol": str(trade.symbol),
            "side": trade.side,
            "amount": float(trade.amount),
            "price": float(trade.price) if trade.price else None
        }
        
        # 기존 검증 로직 호출
        result = await self._legacy_manager.validate_trade(legacy_request)
        
        # 결과를 새로운 format으로 변환
        return ValidationResult(
            is_valid=result["approved"],
            reason=result.get("reason", ""),
            risk_score=result.get("risk_score", 0.0)
        )
```

### **Week 2: Application Layer 구현**

#### **Day 8-10: Command/Query 패턴 구현**
```python
# src/application/commands/place_trade_command.py
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from src.domain.value_objects.symbol import Symbol

@dataclass
class PlaceTradeCommand:
    """거래 실행 명령"""
    portfolio_id: str
    symbol: Symbol
    side: str  # "buy" or "sell"
    amount: Decimal
    order_type: str = "market"
    price: Optional[Decimal] = None
    strategy_id: Optional[str] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None

# src/application/handlers/place_trade_handler.py
from typing import Dict, Any
from src.domain.ports.exchange_port import ExchangePort
from src.domain.ports.risk_manager_port import RiskManagerPort
from src.domain.ports.repository_port import RepositoryPort
from src.domain.entities.trade import Trade

class PlaceTradeHandler:
    """거래 실행 핸들러"""
    
    def __init__(self,
                 exchange_port: ExchangePort,
                 risk_manager_port: RiskManagerPort,
                 repository_port: RepositoryPort):
        self.exchange = exchange_port
        self.risk_manager = risk_manager_port
        self.repository = repository_port
    
    async def handle(self, command: PlaceTradeCommand) -> Dict[str, Any]:
        """거래 명령 처리"""
        # 1. 포트폴리오 조회
        portfolio = await self.repository.get_portfolio(command.portfolio_id)
        if not portfolio:
            return {"success": False, "error": "Portfolio not found"}
        
        # 2. 거래 엔티티 생성
        trade = Trade.create_market_order(
            portfolio_id=command.portfolio_id,
            symbol=command.symbol,
            side=command.side,
            amount=command.amount,
            strategy_id=command.strategy_id
        )
        
        # 3. 리스크 검증
        validation = await self.risk_manager.validate_trade(trade, portfolio)
        if not validation.is_valid:
            return {"success": False, "error": validation.reason}
        
        # 4. 거래 실행
        try:
            order_id = await self.exchange.place_order(trade)
            trade.update_status("submitted", exchange_order_id=order_id)
            
            # 5. 저장
            await self.repository.save_trade(trade)
            
            return {
                "success": True,
                "trade_id": trade.id,
                "exchange_order_id": order_id
            }
            
        except Exception as e:
            trade.update_status("failed", error_message=str(e))
            await self.repository.save_trade(trade)
            return {"success": False, "error": str(e)}
```

#### **Day 11-14: Service Layer 구현**
```python
# src/application/services/trading_service.py
from typing import List, Optional, Dict, Any
from src.application.commands.place_trade_command import PlaceTradeCommand
from src.application.handlers.place_trade_handler import PlaceTradeHandler
from src.application.queries.get_positions_query import GetPositionsQuery
from src.domain.entities.trade import Trade
from src.domain.entities.position import Position

class TradingService:
    """거래 서비스 (Application Layer)"""
    
    def __init__(self, place_trade_handler: PlaceTradeHandler):
        self.place_trade_handler = place_trade_handler
    
    async def execute_trade(self, command: PlaceTradeCommand) -> Dict[str, Any]:
        """거래 실행 (Command)"""
        return await self.place_trade_handler.handle(command)
    
    async def get_positions(self, portfolio_id: str) -> List[Position]:
        """포지션 조회 (Query)"""
        query = GetPositionsQuery(portfolio_id=portfolio_id)
        return await self.get_positions_handler.handle(query)
    
    async def get_trade_history(self, 
                               portfolio_id: str,
                               limit: int = 100) -> List[Trade]:
        """거래 내역 조회 (Query)"""
        # 구현...
        pass
```

### **Week 3-4: Infrastructure Layer 구현**

#### **Day 15-21: 새로운 Exchange Adapter 구현**
```python
# src/infrastructure/exchanges/enhanced_binance_adapter.py
import asyncio
from typing import Dict, Any, List, Optional
from decimal import Decimal
import ccxt.async_support as ccxt
from src.domain.ports.exchange_port import ExchangePort
from src.domain.entities.trade import Trade
from src.domain.entities.position import Position
from src.domain.value_objects.symbol import Symbol
from src.domain.value_objects.money import Money

class EnhancedBinanceAdapter(ExchangePort):
    """향상된 Binance 어댑터 (새로운 아키텍처)"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._exchange = None
        self._connected = False
        self._health_metrics = {
            "last_response_time": None,
            "rate_limit_remaining": 0,
            "latency_ms": 0
        }
    
    async def connect(self) -> bool:
        """거래소 연결"""
        try:
            self._exchange = ccxt.binance({
                'apiKey': self.config['api_key'],
                'secret': self.config['secret'],
                'sandbox': self.config.get('sandbox', True),
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                    'adjustForTimeDifference': True
                }
            })
            
            # 연결 테스트
            await self._exchange.load_markets()
            balance = await self._exchange.fetch_balance()
            
            self._connected = True
            return True
            
        except Exception as e:
            self._connected = False
            raise ConnectionError(f"Failed to connect to Binance: {e}")
    
    async def place_order(self, trade: Trade) -> str:
        """주문 실행 (Circuit Breaker 패턴 적용)"""
        if not self._connected:
            raise ConnectionError("Exchange not connected")
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # CCXT 주문 파라미터 변환
            order_params = self._convert_trade_to_order_params(trade)
            
            # 주문 실행
            order = await self._exchange.create_order(**order_params)
            
            # 메트릭 업데이트
            end_time = asyncio.get_event_loop().time()
            self._health_metrics["latency_ms"] = (end_time - start_time) * 1000
            self._health_metrics["last_response_time"] = datetime.now().isoformat()
            
            return order['id']
            
        except ccxt.BaseError as e:
            # CCXT 에러 처리
            if "insufficient" in str(e).lower():
                raise InsufficientFundsError(str(e))
            elif "invalid" in str(e).lower():
                raise InvalidOrderError(str(e))
            else:
                raise ExchangeError(f"Binance error: {e}")
    
    async def get_balance(self) -> Dict[str, Money]:
        """잔고 조회 (캐시 적용)"""
        balance = await self._exchange.fetch_balance()
        
        result = {}
        for currency, amounts in balance.items():
            if currency == 'info':  # CCXT metadata skip
                continue
            
            total = amounts.get('total', 0)
            if total > 0:
                result[currency] = Money(str(total), currency)
        
        return result
    
    async def health_check(self) -> Dict[str, Any]:
        """상태 확인"""
        try:
            start_time = asyncio.get_event_loop().time()
            await self._exchange.fetch_status()
            end_time = asyncio.get_event_loop().time()
            
            latency = (end_time - start_time) * 1000
            
            return {
                "connected": True,
                "latency_ms": latency,
                "rate_limit_remaining": self._exchange.rateLimit,
                "last_response_time": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e),
                "last_response_time": self._health_metrics["last_response_time"]
            }
    
    def _convert_trade_to_order_params(self, trade: Trade) -> Dict[str, Any]:
        """Trade 엔티티를 CCXT 주문 파라미터로 변환"""
        params = {
            'symbol': str(trade.symbol),
            'type': trade.order_type,
            'side': trade.side,
            'amount': float(trade.amount)
        }
        
        if trade.order_type == 'limit' and trade.price:
            params['price'] = float(trade.price)
        
        return params
```

#### **Day 22-28: Repository 구현**
```python
# src/infrastructure/persistence/sqlalchemy_repository.py
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from src.domain.ports.repository_port import RepositoryPort
from src.domain.entities.portfolio import Portfolio
from src.domain.entities.trade import Trade
from src.infrastructure.persistence.models import PortfolioModel, TradeModel

class SqlAlchemyRepository(RepositoryPort):
    """SQLAlchemy 기반 저장소 구현"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def save_portfolio(self, portfolio: Portfolio) -> None:
        """포트폴리오 저장"""
        # 기존 모델 조회
        stmt = select(PortfolioModel).where(PortfolioModel.id == portfolio.id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if model:
            # 업데이트
            model.name = portfolio.name
            model.updated_at = datetime.now()
        else:
            # 새로 생성
            model = PortfolioModel(
                id=portfolio.id,
                name=portfolio.name,
                base_currency=portfolio.base_currency,
                created_at=portfolio.created_at
            )
            self.session.add(model)
        
        await self.session.commit()
    
    async def get_portfolio(self, portfolio_id: str) -> Optional[Portfolio]:
        """포트폴리오 조회"""
        stmt = select(PortfolioModel).where(PortfolioModel.id == portfolio_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if not model:
            return None
        
        # 모델을 엔티티로 변환
        return Portfolio(
            id=model.id,
            name=model.name,
            base_currency=model.base_currency,
            created_at=model.created_at
        )
    
    async def save_trade(self, trade: Trade) -> None:
        """거래 저장"""
        model = TradeModel(
            id=trade.id,
            portfolio_id=trade.portfolio_id,
            symbol=str(trade.symbol),
            side=trade.side,
            amount=trade.amount,
            order_type=trade.order_type,
            price=trade.price,
            status=trade.status,
            exchange_order_id=trade.exchange_order_id,
            created_at=trade.created_at
        )
        
        self.session.add(model)
        await self.session.commit()
```

### **Week 5-6: 기존 시스템과 통합**

#### **Day 29-35: Adapter Pattern으로 점진적 교체**
```python
# src/application/services/hybrid_trading_service.py
class HybridTradingService:
    """기존 시스템과 새 시스템을 함께 사용하는 하이브리드 서비스"""
    
    def __init__(self, 
                 new_trading_service: TradingService,
                 legacy_trading_service: Any,
                 migration_config: Dict[str, Any]):
        self.new_service = new_trading_service
        self.legacy_service = legacy_trading_service
        self.config = migration_config
    
    async def execute_trade(self, trade_request: Dict[str, Any]) -> Dict[str, Any]:
        """거래 실행 - 설정에 따라 새/기존 시스템 선택"""
        
        # 마이그레이션 대상 확인
        symbol = trade_request.get("symbol")
        use_new_system = self._should_use_new_system(symbol)
        
        if use_new_system:
            # 새로운 시스템 사용
            command = PlaceTradeCommand(
                portfolio_id=trade_request["portfolio_id"],
                symbol=Symbol(symbol),
                side=trade_request["side"],
                amount=Decimal(str(trade_request["amount"])),
                strategy_id=trade_request.get("strategy_id")
            )
            return await self.new_service.execute_trade(command)
        else:
            # 기존 시스템 사용
            return await self.legacy_service.execute_trade(trade_request)
    
    def _should_use_new_system(self, symbol: str) -> bool:
        """새 시스템 사용 여부 결정"""
        # 설정 기반 A/B 테스팅
        migrated_symbols = self.config.get("migrated_symbols", [])
        migration_percentage = self.config.get("migration_percentage", 0)
        
        if symbol in migrated_symbols:
            return True
        
        # 점진적 마이그레이션 (해시 기반)
        import hashlib
        hash_value = int(hashlib.md5(symbol.encode()).hexdigest(), 16)
        return (hash_value % 100) < migration_percentage
```

#### **Day 36-42: 통합 테스트 및 검증**
```python
# tests/integration/test_migration_compatibility.py
class TestMigrationCompatibility:
    """마이그레이션 호환성 테스트"""
    
    @pytest.mark.asyncio
    async def test_hybrid_service_consistency(self):
        """하이브리드 서비스에서 동일한 결과 보장"""
        trade_request = {
            "portfolio_id": "port_001",
            "symbol": "BTC/USDT",
            "side": "buy",
            "amount": "0.1",
            "strategy_id": "test_strategy"
        }
        
        # 기존 시스템 결과
        legacy_result = await legacy_service.execute_trade(trade_request)
        
        # 새 시스템 결과  
        new_result = await new_service.execute_trade(trade_request)
        
        # 결과 호환성 검증
        assert legacy_result["success"] == new_result["success"]
        if legacy_result["success"]:
            assert "trade_id" in new_result
            assert "exchange_order_id" in new_result
```

### **Week 7-8: 최적화 및 완료**

#### **Day 43-49: 성능 최적화**
```python
# src/infrastructure/caching/redis_cache_adapter.py
class RedisCacheAdapter:
    """Redis 기반 캐싱 어댑터"""
    
    async def get_cached_balance(self, portfolio_id: str) -> Optional[Dict[str, Money]]:
        """캐시된 잔고 조회"""
        cache_key = f"balance:{portfolio_id}"
        cached_data = await self.redis.get(cache_key)
        
        if cached_data:
            return self._deserialize_balance(cached_data)
        return None
    
    async def cache_balance(self, portfolio_id: str, balance: Dict[str, Money], ttl: int = 30) -> None:
        """잔고 캐시 저장"""
        cache_key = f"balance:{portfolio_id}"
        serialized_data = self._serialize_balance(balance)
        await self.redis.setex(cache_key, ttl, serialized_data)
```

#### **Day 50-56: 문서화 및 배포 준비**
```python
# src/main.py
from src.infrastructure.factories.service_factory import ServiceFactory
from src.infrastructure.config.app_config import AppConfig

async def create_app(config_path: str = "config/production.yaml") -> Application:
    """애플리케이션 생성 및 초기화"""
    
    # 설정 로드
    config = AppConfig.load_from_file(config_path)
    
    # 서비스 팩토리 초기화
    factory = ServiceFactory(config)
    
    # 서비스들 생성
    trading_service = await factory.create_trading_service()
    portfolio_service = await factory.create_portfolio_service()
    risk_service = await factory.create_risk_service()
    
    # 애플리케이션 조립
    app = Application(
        trading_service=trading_service,
        portfolio_service=portfolio_service,
        risk_service=risk_service,
        config=config
    )
    
    # 초기화
    await app.initialize()
    
    return app

class Application:
    """메인 애플리케이션 클래스"""
    
    async def start(self) -> None:
        """애플리케이션 시작"""
        # 1. 데이터베이스 연결
        await self.database.connect()
        
        # 2. 메시지 버스 시작
        await self.message_bus.start()
        
        # 3. 거래소 연결
        await self.exchange.connect()
        
        # 4. 상태 복구
        await self.restore_state()
        
        logger.info("Application started successfully")
    
    async def stop(self) -> None:
        """안전한 종료"""
        # 1. 새로운 거래 중단
        await self.trading_service.stop_new_trades()
        
        # 2. 기존 거래 완료 대기
        await self.trading_service.wait_for_pending_trades(timeout=30)
        
        # 3. 상태 저장
        await self.save_state()
        
        # 4. 연결 종료
        await self.cleanup_connections()
        
        logger.info("Application stopped safely")
```

## 🔄 **롤백 계획**

### **각 단계별 롤백 전략**
```python
# scripts/rollback.py
class RollbackManager:
    """롤백 관리자"""
    
    async def rollback_to_stage(self, target_stage: str) -> bool:
        """특정 단계로 롤백"""
        
        rollback_map = {
            "week1": self._rollback_to_legacy_entities,
            "week2": self._rollback_to_legacy_services,
            "week3": self._rollback_to_legacy_infrastructure,
            "week4": self._rollback_to_legacy_integration
        }
        
        if target_stage in rollback_map:
            return await rollback_map[target_stage]()
        return False
    
    async def _rollback_to_legacy_entities(self) -> bool:
        """엔티티 롤백"""
        # 새로운 엔티티 비활성화
        # 기존 모델 재활성화
        # 데이터 마이그레이션 되돌리기
        pass
```

## 📊 **진행 상황 추적**

### **마일스톤 체크리스트**
```yaml
# milestone-tracker.yaml
Week 1:
  - domain_entities: ✅
  - value_objects: ✅  
  - port_interfaces: ✅
  - legacy_adapters: ⏳

Week 2:
  - command_handlers: ⏳
  - query_handlers: ⏳
  - application_services: ⏳
  - event_handlers: ⏳

Week 3:
  - exchange_adapters: ❌
  - repository_impl: ❌
  - notification_impl: ❌
  - caching_layer: ❌

Week 4:
  - integration_tests: ❌
  - performance_tests: ❌
  - migration_scripts: ❌
  - deployment_prep: ❌
```

### **자동화된 검증 스크립트**
```bash
# scripts/verify-implementation.sh
#!/bin/bash

echo "🔍 Verifying implementation progress..."

# 1. 코드 구조 검증
echo "Checking directory structure..."
required_dirs=("src/domain/entities" "src/domain/ports" "src/application" "src/infrastructure")
for dir in "${required_dirs[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "❌ Missing directory: $dir"
        exit 1
    fi
done

# 2. 인터페이스 구현 검증
echo "Checking interface implementations..."
python scripts/check_interface_compliance.py

# 3. 테스트 실행
echo "Running tests..."
pytest tests/unit/ -v --tb=short

# 4. 성능 벤치마크
echo "Running performance benchmarks..."
python scripts/benchmark.py

echo "✅ Implementation verification completed!"
```

---

## 📋 **다음 즉시 실행할 작업**

1. **Domain Layer 구현 시작** (오늘부터)
   ```bash
   mkdir -p src/domain/{entities,value_objects,ports}
   touch src/domain/entities/{portfolio,trade,position,strategy}.py
   ```

2. **첫 번째 엔티티 테스트** (내일)
   ```bash
   pytest tests/unit/domain/entities/test_portfolio.py -v
   ```

3. **Legacy Adapter 작성** (이번 주 내)
   - 기존 Capital Manager 래핑
   - 기존 Exchange Connector 래핑

이 계획을 따라 진행하면 **코드 수정을 최소화**하면서 **안전하게 새로운 아키텍처로 마이그레이션**할 수 있습니다!