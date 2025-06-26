# 테스트 전략 및 구현 가이드

## 🎯 테스트 목표
- **신뢰성**: 24/7 운영에서 오류 없는 동작 보장
- **안전성**: 실제 자금 손실 방지
- **성능**: 200ms 이하 거래 실행 보장
- **유지보수성**: 코드 변경 시 회귀 테스트 자동화

## 🏗️ **테스트 피라미드**

```
         E2E Tests (5%)
        ▒▒▒▒▒▒▒▒▒▒▒▒
      Integration Tests (25%)
    ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
  Unit Tests (70%)
▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
```

## 🧪 **1. Unit Tests (70%)**

### **Domain Layer 테스트**

#### **포트폴리오 엔티티 테스트**
```python
# tests/unit/domain/entities/test_portfolio.py
import pytest
from decimal import Decimal
from src.domain.entities.portfolio import Portfolio
from src.domain.value_objects.money import Money
from src.domain.exceptions import InsufficientFundsError

class TestPortfolio:
    def test_create_portfolio_with_valid_data(self):
        """유효한 데이터로 포트폴리오 생성"""
        portfolio = Portfolio(
            id="port_001",
            name="Test Portfolio",
            base_currency="USDT",
            initial_balance=Money("10000.0", "USDT")
        )
        
        assert portfolio.id == "port_001"
        assert portfolio.name == "Test Portfolio"
        assert portfolio.base_currency == "USDT"
        assert portfolio.total_balance == Money("10000.0", "USDT")
        assert portfolio.available_balance == Money("10000.0", "USDT")
    
    def test_portfolio_cannot_have_negative_balance(self):
        """음수 잔고로 포트폴리오 생성 불가"""
        with pytest.raises(ValueError, match="Balance cannot be negative"):
            Portfolio(
                id="port_001",
                name="Test Portfolio",
                base_currency="USDT",
                initial_balance=Money("-100.0", "USDT")
            )
    
    def test_reserve_funds_success(self):
        """자금 예약 성공"""
        portfolio = Portfolio(
            id="port_001",
            name="Test Portfolio", 
            base_currency="USDT",
            initial_balance=Money("10000.0", "USDT")
        )
        
        reservation_id = portfolio.reserve_funds(Money("1000.0", "USDT"))
        
        assert portfolio.available_balance == Money("9000.0", "USDT")
        assert portfolio.reserved_balance == Money("1000.0", "USDT")
        assert reservation_id is not None
    
    def test_reserve_funds_insufficient_balance(self):
        """잔고 부족 시 자금 예약 실패"""
        portfolio = Portfolio(
            id="port_001",
            name="Test Portfolio",
            base_currency="USDT", 
            initial_balance=Money("1000.0", "USDT")
        )
        
        with pytest.raises(InsufficientFundsError):
            portfolio.reserve_funds(Money("2000.0", "USDT"))
```

#### **거래 엔티티 테스트**
```python
# tests/unit/domain/entities/test_trade.py
import pytest
from datetime import datetime
from decimal import Decimal
from src.domain.entities.trade import Trade
from src.domain.value_objects.symbol import Symbol
from src.domain.value_objects.money import Money

class TestTrade:
    def test_create_market_buy_order(self):
        """시장가 매수 주문 생성"""
        trade = Trade.create_market_order(
            portfolio_id="port_001",
            symbol=Symbol("BTC/USDT"),
            side="buy",
            amount=Decimal("0.1"),
            strategy_id="strategy_001"
        )
        
        assert trade.symbol == Symbol("BTC/USDT")
        assert trade.side == "buy"
        assert trade.amount == Decimal("0.1")
        assert trade.order_type == "market"
        assert trade.status == "pending"
    
    def test_create_limit_sell_order(self):
        """지정가 매도 주문 생성"""
        trade = Trade.create_limit_order(
            portfolio_id="port_001",
            symbol=Symbol("BTC/USDT"),
            side="sell",
            amount=Decimal("0.1"),
            price=Decimal("50000.0"),
            strategy_id="strategy_001"
        )
        
        assert trade.price == Decimal("50000.0")
        assert trade.order_type == "limit"
    
    def test_trade_cannot_have_zero_amount(self):
        """거래 수량은 0이 될 수 없음"""
        with pytest.raises(ValueError, match="Amount must be positive"):
            Trade.create_market_order(
                portfolio_id="port_001",
                symbol=Symbol("BTC/USDT"),
                side="buy",
                amount=Decimal("0"),
                strategy_id="strategy_001"
            )
    
    def test_trade_execution_updates_status(self):
        """거래 실행 시 상태 업데이트"""
        trade = Trade.create_market_order(
            portfolio_id="port_001",
            symbol=Symbol("BTC/USDT"),
            side="buy",
            amount=Decimal("0.1"),
            strategy_id="strategy_001"
        )
        
        # 거래 실행
        trade.execute(
            exchange_order_id="binance_12345",
            executed_price=Decimal("50000.0"),
            executed_amount=Decimal("0.1"),
            fees=Decimal("2.5")
        )
        
        assert trade.status == "executed"
        assert trade.exchange_order_id == "binance_12345"
        assert trade.executed_price == Decimal("50000.0")
        assert trade.executed_amount == Decimal("0.1")
        assert trade.fees == Decimal("2.5")
```

### **Application Layer 테스트**

#### **거래 서비스 테스트**
```python
# tests/unit/application/services/test_trading_service.py
import pytest
from unittest.mock import Mock, AsyncMock
from src.application.services.trading_service import TradingService
from src.domain.entities.trade import Trade
from src.domain.entities.portfolio import Portfolio
from src.domain.value_objects.symbol import Symbol

class TestTradingService:
    @pytest.fixture
    def setup_mocks(self):
        """테스트용 Mock 객체 설정"""
        exchange_port = Mock()
        risk_manager_port = Mock()
        repository_port = Mock()
        notification_port = Mock()
        
        exchange_port.place_order = AsyncMock(return_value="exchange_order_123")
        risk_manager_port.validate_trade = AsyncMock(return_value=ValidationResult(True))
        repository_port.save_trade = AsyncMock()
        notification_port.send_trade_notification = AsyncMock(return_value=True)
        
        return {
            "exchange": exchange_port,
            "risk_manager": risk_manager_port,
            "repository": repository_port,
            "notification": notification_port
        }
    
    @pytest.mark.asyncio
    async def test_execute_trade_success(self, setup_mocks):
        """거래 실행 성공"""
        mocks = setup_mocks
        service = TradingService(
            exchange_port=mocks["exchange"],
            risk_manager_port=mocks["risk_manager"],
            repository_port=mocks["repository"],
            notification_port=mocks["notification"]
        )
        
        # 포트폴리오 설정
        portfolio = Portfolio(
            id="port_001",
            name="Test Portfolio",
            base_currency="USDT",
            initial_balance=Money("10000.0", "USDT")
        )
        
        # 거래 생성
        trade = Trade.create_market_order(
            portfolio_id="port_001",
            symbol=Symbol("BTC/USDT"),
            side="buy",
            amount=Decimal("0.1"),
            strategy_id="strategy_001"
        )
        
        # 거래 실행
        result = await service.execute_trade(trade, portfolio)
        
        # 검증
        assert result.success is True
        assert result.exchange_order_id == "exchange_order_123"
        
        # Mock 호출 검증
        mocks["risk_manager"].validate_trade.assert_called_once_with(trade, portfolio)
        mocks["exchange"].place_order.assert_called_once_with(trade)
        mocks["repository"].save_trade.assert_called_once()
        mocks["notification"].send_trade_notification.assert_called_once_with(trade)
    
    @pytest.mark.asyncio
    async def test_execute_trade_risk_validation_failed(self, setup_mocks):
        """리스크 검증 실패 시 거래 거부"""
        mocks = setup_mocks
        mocks["risk_manager"].validate_trade = AsyncMock(
            return_value=ValidationResult(False, "Position size too large")
        )
        
        service = TradingService(
            exchange_port=mocks["exchange"],
            risk_manager_port=mocks["risk_manager"],
            repository_port=mocks["repository"],
            notification_port=mocks["notification"]
        )
        
        portfolio = Portfolio(
            id="port_001",
            name="Test Portfolio",
            base_currency="USDT",
            initial_balance=Money("10000.0", "USDT")
        )
        
        trade = Trade.create_market_order(
            portfolio_id="port_001",
            symbol=Symbol("BTC/USDT"),
            side="buy",
            amount=Decimal("10.0"),  # 큰 수량
            strategy_id="strategy_001"
        )
        
        # 거래 실행 시도
        result = await service.execute_trade(trade, portfolio)
        
        # 검증
        assert result.success is False
        assert result.error_message == "Position size too large"
        
        # 거래소 호출되지 않음을 확인
        mocks["exchange"].place_order.assert_not_called()
```

## 🔗 **2. Integration Tests (25%)**

### **포트 통합 테스트**

#### **거래소 어댑터 통합 테스트**
```python
# tests/integration/test_exchange_integration.py
import pytest
from src.infrastructure.exchanges.binance_adapter import BinanceAdapter
from src.infrastructure.exchanges.mock_exchange import MockExchange
from src.domain.entities.trade import Trade
from src.domain.value_objects.symbol import Symbol

class TestExchangeIntegration:
    @pytest.fixture
    def mock_exchange(self):
        """Mock 거래소 설정"""
        config = {
            "api_key": "test_key",
            "secret": "test_secret",
            "sandbox": True,
            "initial_balance": {"USDT": "10000.0", "BTC": "1.0"}
        }
        return MockExchange(config)
    
    @pytest.mark.asyncio
    async def test_place_order_and_check_status(self, mock_exchange):
        """주문 실행 및 상태 확인 통합 테스트"""
        # 연결
        connected = await mock_exchange.connect()
        assert connected is True
        
        # 주문 생성
        trade = Trade.create_market_order(
            portfolio_id="port_001",
            symbol=Symbol("BTC/USDT"),
            side="buy",
            amount=Decimal("0.1"),
            strategy_id="strategy_001"
        )
        
        # 주문 실행
        order_id = await mock_exchange.place_order(trade)
        assert order_id is not None
        
        # 주문 상태 확인
        status = await mock_exchange.get_order_status(order_id)
        assert status["id"] == order_id
        assert status["status"] in ["filled", "partial", "open"]
        
        # 포지션 확인
        positions = await mock_exchange.get_positions()
        if status["status"] == "filled":
            assert len(positions) > 0
            position = positions[0]
            assert position.symbol == Symbol("BTC/USDT")
    
    @pytest.mark.asyncio
    async def test_balance_update_after_trade(self, mock_exchange):
        """거래 후 잔고 업데이트 확인"""
        await mock_exchange.connect()
        
        # 초기 잔고 확인
        initial_balance = await mock_exchange.get_balance()
        initial_usdt = initial_balance["USDT"].amount
        
        # 매수 주문
        trade = Trade.create_market_order(
            portfolio_id="port_001",
            symbol=Symbol("BTC/USDT"),
            side="buy",
            amount=Decimal("0.01"),
            strategy_id="strategy_001"
        )
        
        order_id = await mock_exchange.place_order(trade)
        
        # 주문 완료 대기 (Mock에서는 즉시 완료)
        await asyncio.sleep(0.1)
        
        # 잔고 재확인
        final_balance = await mock_exchange.get_balance()
        final_usdt = final_balance["USDT"].amount
        
        # USDT 잔고 감소 확인
        assert final_usdt < initial_usdt
```

### **리스크 관리 통합 테스트**
```python
# tests/integration/test_risk_management_integration.py
import pytest
from src.infrastructure.risk.portfolio_risk_manager import PortfolioRiskManager
from src.domain.entities.portfolio import Portfolio
from src.domain.entities.trade import Trade

class TestRiskManagementIntegration:
    @pytest.fixture
    def risk_manager(self):
        """리스크 매니저 설정"""
        config = {
            "max_position_size_pct": 10.0,  # 10%
            "max_daily_loss_pct": 5.0,      # 5%
            "max_portfolio_exposure_pct": 80.0,  # 80%
            "blocked_symbols": ["DOGE/USDT"]
        }
        return PortfolioRiskManager(config)
    
    @pytest.mark.asyncio
    async def test_position_size_limit_enforcement(self, risk_manager):
        """포지션 크기 한도 검증"""
        portfolio = Portfolio(
            id="port_001",
            name="Test Portfolio",
            base_currency="USDT",
            initial_balance=Money("10000.0", "USDT")
        )
        
        # 허용 범위 내 거래
        small_trade = Trade.create_market_order(
            portfolio_id="port_001",
            symbol=Symbol("BTC/USDT"),
            side="buy",
            amount=Decimal("0.02"),  # ~1000 USDT (10% 이하)
            strategy_id="strategy_001"
        )
        
        result = await risk_manager.validate_trade(small_trade, portfolio)
        assert result.is_valid is True
        
        # 허용 범위 초과 거래
        large_trade = Trade.create_market_order(
            portfolio_id="port_001",
            symbol=Symbol("BTC/USDT"),
            side="buy",
            amount=Decimal("0.25"),  # ~12500 USDT (10% 초과)
            strategy_id="strategy_001"
        )
        
        result = await risk_manager.validate_trade(large_trade, portfolio)
        assert result.is_valid is False
        assert "position size" in result.reason.lower()
    
    @pytest.mark.asyncio
    async def test_blocked_symbol_rejection(self, risk_manager):
        """금지 심볼 거래 거부"""
        portfolio = Portfolio(
            id="port_001", 
            name="Test Portfolio",
            base_currency="USDT",
            initial_balance=Money("10000.0", "USDT")
        )
        
        blocked_trade = Trade.create_market_order(
            portfolio_id="port_001",
            symbol=Symbol("DOGE/USDT"),  # 금지된 심볼
            side="buy",
            amount=Decimal("100.0"),
            strategy_id="strategy_001"
        )
        
        result = await risk_manager.validate_trade(blocked_trade, portfolio)
        assert result.is_valid is False
        assert "blocked" in result.reason.lower()
```

## 🌐 **3. E2E Tests (5%)**

### **전체 거래 플로우 테스트**
```python
# tests/e2e/test_complete_trading_flow.py
import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.rabbitmq import RabbitMqContainer
from src.main import create_app
from src.domain.value_objects.symbol import Symbol

class TestCompleteTradingFlow:
    @pytest.fixture(scope="session")
    def infrastructure(self):
        """테스트 인프라 설정"""
        with PostgresContainer("postgres:15") as postgres, \
             RabbitMqContainer("rabbitmq:3-management") as rabbitmq:
            
            # 데이터베이스 초기화
            db_url = postgres.get_connection_url()
            
            # RabbitMQ 설정
            rabbitmq_url = f"amqp://guest:guest@{rabbitmq.get_container_host_ip()}:{rabbitmq.get_exposed_port(5672)}"
            
            yield {
                "database_url": db_url,
                "rabbitmq_url": rabbitmq_url
            }
    
    @pytest.mark.asyncio
    async def test_end_to_end_trading_scenario(self, infrastructure):
        """전체 거래 시나리오 E2E 테스트"""
        # 1. 애플리케이션 시작
        app = create_app({
            "database_url": infrastructure["database_url"],
            "rabbitmq_url": infrastructure["rabbitmq_url"],
            "exchange": "mock",
            "dry_run": False
        })
        
        await app.start()
        
        try:
            # 2. 포트폴리오 생성
            portfolio_service = app.get_service("portfolio")
            portfolio = await portfolio_service.create_portfolio(
                name="E2E Test Portfolio",
                base_currency="USDT",
                initial_balance=10000.0
            )
            
            # 3. 전략 활성화
            strategy_service = app.get_service("strategy")
            strategy = await strategy_service.create_strategy(
                portfolio_id=portfolio.id,
                strategy_type="MA_CROSSOVER",
                symbol="BTC/USDT",
                parameters={"fast_period": 10, "slow_period": 20}
            )
            
            await strategy_service.activate_strategy(strategy.id)
            
            # 4. 시장 데이터 주입 (가격 상승 패턴)
            market_data_service = app.get_service("market_data")
            await market_data_service.inject_test_data([
                {"symbol": "BTC/USDT", "price": 50000, "volume": 100},
                {"symbol": "BTC/USDT", "price": 50100, "volume": 120},
                {"symbol": "BTC/USDT", "price": 50200, "volume": 110},
                # ... 더 많은 데이터로 MA 크로스오버 유발
            ])
            
            # 5. 신호 생성 대기
            await asyncio.sleep(2.0)
            
            # 6. 거래 실행 확인
            trading_service = app.get_service("trading")
            trades = await trading_service.get_recent_trades(portfolio.id)
            
            assert len(trades) > 0
            first_trade = trades[0]
            assert first_trade.symbol == Symbol("BTC/USDT")
            assert first_trade.status == "executed"
            
            # 7. 포지션 확인
            positions = await trading_service.get_active_positions(portfolio.id)
            assert len(positions) > 0
            
            # 8. 포트폴리오 업데이트 확인
            updated_portfolio = await portfolio_service.get_portfolio(portfolio.id)
            assert updated_portfolio.total_value != 10000.0  # 거래로 인한 변동
            
        finally:
            await app.stop()
```

## ⚡ **4. Performance Tests**

### **지연시간 테스트**
```python
# tests/performance/test_latency.py
import pytest
import time
from src.application.services.trading_service import TradingService

class TestPerformance:
    @pytest.mark.asyncio
    async def test_trade_execution_latency(self, trading_service):
        """거래 실행 지연시간 테스트 (목표: 200ms 이하)"""
        trade = Trade.create_market_order(
            portfolio_id="port_001",
            symbol=Symbol("BTC/USDT"),
            side="buy",
            amount=Decimal("0.1"),
            strategy_id="strategy_001"
        )
        
        start_time = time.time()
        result = await trading_service.execute_trade(trade, portfolio)
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        assert latency_ms < 200, f"Trade execution took {latency_ms:.2f}ms, expected < 200ms"
    
    @pytest.mark.asyncio
    async def test_concurrent_trade_processing(self, trading_service):
        """동시 거래 처리 성능 테스트"""
        trades = [
            Trade.create_market_order(
                portfolio_id="port_001",
                symbol=Symbol("BTC/USDT"),
                side="buy",
                amount=Decimal("0.01"),
                strategy_id=f"strategy_{i}"
            )
            for i in range(10)
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*[
            trading_service.execute_trade(trade, portfolio)
            for trade in trades
        ])
        end_time = time.time()
        
        total_time_ms = (end_time - start_time) * 1000
        avg_time_per_trade = total_time_ms / len(trades)
        
        assert avg_time_per_trade < 100, f"Average trade time: {avg_time_per_trade:.2f}ms"
        assert all(r.success for r in results), "Some trades failed"
```

## 📊 **테스트 메트릭 및 리포팅**

### **커버리지 목표**
```
Unit Tests: 90%+ 라인 커버리지
Integration Tests: 80%+ 브랜치 커버리지
E2E Tests: 주요 비즈니스 플로우 100% 커버
```

### **성능 기준**
```
거래 실행: < 200ms
리스크 검증: < 50ms
포트폴리오 조회: < 100ms
메모리 사용량: < 512MB (steady state)
```

### **테스트 자동화 스크립트**
```bash
# scripts/run-tests.sh
#!/bin/bash
set -e

echo "🧪 Running comprehensive test suite..."

# Unit Tests
echo "Running unit tests..."
pytest tests/unit/ -v --cov=src --cov-report=html --cov-fail-under=90

# Integration Tests  
echo "Running integration tests..."
pytest tests/integration/ -v --tb=short

# Performance Tests
echo "Running performance tests..."
pytest tests/performance/ -v --benchmark-only

# E2E Tests (with infrastructure)
echo "Running E2E tests..."
pytest tests/e2e/ -v --tb=short

echo "✅ All tests completed successfully!"
echo "📊 Coverage report: htmlcov/index.html"
```

---

## 📋 **다음 단계**
1. 각 테스트 케이스별 구현 템플릿 작성
2. CI/CD 파이프라인에서 테스트 자동화 설정
3. 성능 벤치마크 베이스라인 설정
4. 테스트 데이터 픽스처 라이브러리 구축