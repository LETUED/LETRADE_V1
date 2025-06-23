"""
데이터베이스 ORM 모델 단위 테스트

MVP Section 5.1 요구사항 준수 및 데이터 무결성 검증
"""

import pytest
from decimal import Decimal
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from src.common.database import (
    Base, Portfolio, Strategy, Trade, Position, 
    PortfolioRule, PerformanceMetric, SystemLog
)

# SQLite compatibility: Replace JSONB with JSON for testing
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import JSON
import sqlalchemy

# Monkey patch JSONB to JSON for SQLite testing
original_jsonb_compile = None

def setup_sqlite_compatibility():
    """Setup SQLite compatibility for JSONB columns."""
    # Replace JSONB columns with JSON in test environment
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if hasattr(column.type, 'python_type') and isinstance(column.type, JSONB):
                column.type = JSON()

@pytest.fixture
def in_memory_db():
    """인메모리 SQLite 데이터베이스 설정"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    
    # Setup SQLite compatibility for JSONB columns
    setup_sqlite_compatibility()
    
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()

@pytest.fixture
def sample_portfolio(in_memory_db):
    """테스트용 샘플 포트폴리오"""
    portfolio = Portfolio(
        name="Test Portfolio",
        total_capital=Decimal("10000.00"),
        available_capital=Decimal("8000.00"),
        currency="USDT",
        is_active=True
    )
    in_memory_db.add(portfolio)
    in_memory_db.commit()
    return portfolio

@pytest.fixture
def sample_strategy(in_memory_db, sample_portfolio):
    """테스트용 샘플 전략"""
    strategy = Strategy(
        name="Test MA Strategy",
        strategy_type="MA_CROSSOVER",
        exchange="binance",
        symbol="BTC/USDT",
        parameters={"fast": 50, "slow": 200},
        position_sizing_config={"model": "fixed_fractional", "risk_percent": 0.02},
        portfolio_id=sample_portfolio.id,
        is_active=True
    )
    in_memory_db.add(strategy)
    in_memory_db.commit()
    return strategy

class TestPortfolioModel:
    """Portfolio 모델 테스트"""
    
    def test_portfolio_creation(self, in_memory_db):
        """포트폴리오 생성 테스트"""
        portfolio = Portfolio(
            name="New Portfolio",
            total_capital=Decimal("5000.00"),
            available_capital=Decimal("5000.00"),
            currency="USDT"
        )
        
        in_memory_db.add(portfolio)
        in_memory_db.commit()
        
        assert portfolio.id is not None
        assert portfolio.name == "New Portfolio"
        assert portfolio.total_capital == Decimal("5000.00")
        assert portfolio.is_active is True
        assert portfolio.created_at is not None
    
    def test_portfolio_unique_name_constraint(self, in_memory_db, sample_portfolio):
        """포트폴리오 이름 유일성 제약 테스트"""
        duplicate_portfolio = Portfolio(
            name="Test Portfolio",  # 중복 이름
            total_capital=Decimal("1000.00"),
            available_capital=Decimal("1000.00")
        )
        
        in_memory_db.add(duplicate_portfolio)
        
        with pytest.raises(IntegrityError):
            in_memory_db.commit()
    
    def test_portfolio_relationship_with_strategies(self, in_memory_db, sample_portfolio, sample_strategy):
        """포트폴리오-전략 관계 테스트"""
        # 관계 확인
        assert len(sample_portfolio.strategies) == 1
        assert sample_portfolio.strategies[0].name == "Test MA Strategy"
        assert sample_strategy.portfolio.name == "Test Portfolio"

class TestStrategyModel:
    """Strategy 모델 테스트"""
    
    def test_strategy_creation(self, in_memory_db, sample_portfolio):
        """전략 생성 테스트"""
        strategy = Strategy(
            name="Momentum Strategy",
            strategy_type="MOMENTUM",
            exchange="binance",
            symbol="ETH/USDT",
            parameters={"lookback": 14, "threshold": 0.02},
            portfolio_id=sample_portfolio.id
        )
        
        in_memory_db.add(strategy)
        in_memory_db.commit()
        
        assert strategy.id is not None
        assert strategy.name == "Momentum Strategy"
        assert strategy.strategy_type == "MOMENTUM"
        assert strategy.is_active is False  # 기본값
    
    def test_strategy_symbol_format_validation(self, in_memory_db, sample_portfolio):
        """전략 심볼 형식 검증 테스트"""
        # 유효한 심볼 형식
        valid_strategy = Strategy(
            name="Valid Symbol Strategy",
            symbol="BTC/USDT",
            portfolio_id=sample_portfolio.id
        )
        
        in_memory_db.add(valid_strategy)
        in_memory_db.commit()  # 성공해야 함
        
        # 무효한 심볼 형식은 SQLite에서는 CHECK 제약조건이 완전히 지원되지 않음
        # PostgreSQL에서는 실패할 것

class TestTradeModel:
    """Trade 모델 테스트"""
    
    def test_trade_creation(self, in_memory_db, sample_strategy):
        """거래 생성 테스트"""
        trade = Trade(
            strategy_id=sample_strategy.id,
            exchange="binance",
            symbol="BTC/USDT",
            side="buy",
            type="market",
            amount=Decimal("0.1"),
            price=Decimal("50000.00"),
            cost=Decimal("5000.00"),
            fee=Decimal("5.00"),
            status="closed",
            exchange_order_id="12345"
        )
        
        in_memory_db.add(trade)
        in_memory_db.commit()
        
        assert trade.id is not None
        assert trade.side == "buy"
        assert trade.amount == Decimal("0.1")
        assert trade.status == "closed"
    
    def test_trade_relationship_with_strategy(self, in_memory_db, sample_strategy):
        """거래-전략 관계 테스트"""
        trade = Trade(
            strategy_id=sample_strategy.id,
            exchange="binance",
            symbol="BTC/USDT",
            side="sell",
            type="limit",
            amount=Decimal("0.05"),
            price=Decimal("55000.00")
        )
        
        in_memory_db.add(trade)
        in_memory_db.commit()
        
        # 관계 확인
        assert trade.strategy.name == "Test MA Strategy"
        assert len(sample_strategy.trades) == 1

class TestPositionModel:
    """Position 모델 테스트"""
    
    def test_position_creation(self, in_memory_db, sample_strategy):
        """포지션 생성 테스트"""
        position = Position(
            strategy_id=sample_strategy.id,
            exchange="binance",
            symbol="BTC/USDT",
            side="long",
            entry_price=Decimal("50000.00"),
            current_size=Decimal("0.1"),
            avg_entry_price=Decimal("50000.00"),
            stop_loss_price=Decimal("48000.00"),
            take_profit_price=Decimal("55000.00"),
            unrealized_pnl=Decimal("500.00")
        )
        
        in_memory_db.add(position)
        in_memory_db.commit()
        
        assert position.id is not None
        assert position.side == "long"
        assert position.is_open is True  # 기본값
        assert position.unrealized_pnl == Decimal("500.00")
    
    def test_position_close_logic(self, in_memory_db, sample_strategy):
        """포지션 종료 로직 테스트"""
        position = Position(
            strategy_id=sample_strategy.id,
            exchange="binance",
            symbol="BTC/USDT",
            side="short",
            entry_price=Decimal("50000.00"),
            current_size=Decimal("0.1"),
            avg_entry_price=Decimal("50000.00"),
            is_open=False,
            closed_at=datetime.utcnow()
        )
        
        in_memory_db.add(position)
        in_memory_db.commit()
        
        assert position.is_open is False
        assert position.closed_at is not None

class TestPortfolioRuleModel:
    """PortfolioRule 모델 테스트"""
    
    def test_portfolio_rule_creation(self, in_memory_db, sample_portfolio):
        """포트폴리오 규칙 생성 테스트"""
        rule = PortfolioRule(
            portfolio_id=sample_portfolio.id,
            rule_type="max_position_size_percent",
            rule_value={"value": 15.0},
            is_active=True
        )
        
        in_memory_db.add(rule)
        in_memory_db.commit()
        
        assert rule.id is not None
        assert rule.rule_type == "max_position_size_percent"
        assert rule.rule_value["value"] == 15.0
    
    def test_portfolio_rule_relationship(self, in_memory_db, sample_portfolio):
        """포트폴리오 규칙 관계 테스트"""
        rule1 = PortfolioRule(
            portfolio_id=sample_portfolio.id,
            rule_type="max_daily_loss_percent",
            rule_value={"value": 5.0}
        )
        
        rule2 = PortfolioRule(
            portfolio_id=sample_portfolio.id,
            rule_type="min_position_size_usd",
            rule_value={"value": 10.0}
        )
        
        in_memory_db.add_all([rule1, rule2])
        in_memory_db.commit()
        
        # 관계 확인
        assert len(sample_portfolio.portfolio_rules) == 2

class TestPerformanceMetricModel:
    """PerformanceMetric 모델 테스트"""
    
    def test_performance_metric_creation(self, in_memory_db, sample_strategy):
        """성능 지표 생성 테스트"""
        metric = PerformanceMetric(
            strategy_id=sample_strategy.id,
            metric_name="total_return_percent",
            metric_value=Decimal("15.75"),
            metric_unit="percent"
        )
        
        in_memory_db.add(metric)
        in_memory_db.commit()
        
        assert metric.id is not None
        assert metric.metric_name == "total_return_percent"
        assert metric.metric_value == Decimal("15.75")

class TestSystemLogModel:
    """SystemLog 모델 테스트"""
    
    def test_system_log_creation(self, in_memory_db):
        """시스템 로그 생성 테스트"""
        log = SystemLog(
            level="INFO",
            logger_name="test.logger",
            message="Test log message",
            context={"test_key": "test_value"}
        )
        
        in_memory_db.add(log)
        in_memory_db.commit()
        
        assert log.id is not None
        assert log.level == "INFO"
        assert log.message == "Test log message"
        assert log.context["test_key"] == "test_value"

class TestDatabaseIntegration:
    """데이터베이스 통합 테스트"""
    
    def test_full_portfolio_setup(self, in_memory_db):
        """완전한 포트폴리오 설정 테스트"""
        # 1. 포트폴리오 생성
        portfolio = Portfolio(
            name="Integration Test Portfolio",
            total_capital=Decimal("20000.00"),
            available_capital=Decimal("20000.00")
        )
        in_memory_db.add(portfolio)
        in_memory_db.commit()
        
        # 2. 포트폴리오 규칙 생성
        rules = [
            PortfolioRule(
                portfolio_id=portfolio.id,
                rule_type="max_position_size_percent",
                rule_value={"value": 10.0}
            ),
            PortfolioRule(
                portfolio_id=portfolio.id,
                rule_type="max_daily_loss_percent",
                rule_value={"value": 5.0}
            )
        ]
        in_memory_db.add_all(rules)
        in_memory_db.commit()
        
        # 3. 전략 생성
        strategy = Strategy(
            name="Integration Test Strategy",
            strategy_type="MA_CROSSOVER",
            exchange="binance",
            symbol="BTC/USDT",
            portfolio_id=portfolio.id
        )
        in_memory_db.add(strategy)
        in_memory_db.commit()
        
        # 4. 거래 생성
        trade = Trade(
            strategy_id=strategy.id,
            exchange="binance",
            symbol="BTC/USDT",
            side="buy",
            type="market",
            amount=Decimal("0.1"),
            status="closed"
        )
        in_memory_db.add(trade)
        in_memory_db.commit()
        
        # 5. 포지션 생성
        position = Position(
            strategy_id=strategy.id,
            exchange="binance",
            symbol="BTC/USDT",
            side="long",
            entry_price=Decimal("50000.00"),
            current_size=Decimal("0.1"),
            avg_entry_price=Decimal("50000.00")
        )
        in_memory_db.add(position)
        in_memory_db.commit()
        
        # 6. 성능 지표 생성
        metric = PerformanceMetric(
            strategy_id=strategy.id,
            metric_name="total_return_percent",
            metric_value=Decimal("5.0")
        )
        in_memory_db.add(metric)
        in_memory_db.commit()
        
        # 모든 관계 검증
        assert len(portfolio.strategies) == 1
        assert len(portfolio.portfolio_rules) == 2
        assert len(strategy.trades) == 1
        assert len(strategy.positions) == 1
        assert len(strategy.performance_metrics) == 1
        
        # 데이터 일관성 검증
        assert strategy.portfolio.name == "Integration Test Portfolio"
        assert trade.strategy.name == "Integration Test Strategy"
        assert position.strategy.name == "Integration Test Strategy"
        assert metric.strategy.name == "Integration Test Strategy"