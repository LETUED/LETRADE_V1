"""
데이터베이스 ORM 모델 및 연결 관리

이 모듈은 Letrade_v1 시스템의 모든 데이터베이스 관련 작업을 위한 
SQLAlchemy ORM 모델과 세션 관리를 제공합니다.

MVP Section 5.1 요구사항을 완전히 구현하며, 추가적인 보안 및 
성능 최적화 기능을 포함합니다.
"""

import os
from typing import Optional, Any, Dict, List
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    create_engine, 
    Column, 
    Integer, 
    String, 
    Boolean, 
    DECIMAL, 
    TIMESTAMP, 
    ForeignKey,
    Text,
    CheckConstraint,
    Index,
    UniqueConstraint,
    text
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.types import TypeDecorator, Text
import json
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.sql import func
import logging

# 로거 설정
logger = logging.getLogger(__name__)

# Base 클래스 생성
Base = declarative_base()

class Portfolio(Base):
    """포트폴리오 테이블 ORM 모델"""
    __tablename__ = 'portfolios'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    total_capital = Column(DECIMAL(20, 8), nullable=False)
    available_capital = Column(DECIMAL(20, 8), nullable=False)
    currency = Column(String(10), nullable=False, default='USDT')
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    # 관계 설정
    strategies = relationship("Strategy", back_populates="portfolio", cascade="all, delete-orphan")
    portfolio_rules = relationship("PortfolioRule", back_populates="portfolio", cascade="all, delete-orphan")
    
    # 제약조건
    __table_args__ = (
        CheckConstraint('total_capital > 0', name='ck_portfolios_total_capital_positive'),
        CheckConstraint('available_capital >= 0', name='ck_portfolios_available_capital_non_negative'),
        Index('idx_portfolios_is_active', 'is_active'),
        Index('idx_portfolios_currency', 'currency'),
    )
    
    def __repr__(self) -> str:
        return f"<Portfolio(id={self.id}, name='{self.name}', total_capital={self.total_capital})>"

class Strategy(Base):
    """거래 전략 테이블 ORM 모델"""
    __tablename__ = 'strategies'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    strategy_type = Column(String(50), nullable=False, default='MA_CROSSOVER')
    exchange = Column(String(50), nullable=False, default='binance')
    symbol = Column(String(50), nullable=False)
    parameters = Column(JSONB, default={"fast": 50, "slow": 200})
    position_sizing_config = Column(JSONB, default={"model": "fixed_fractional", "risk_percent": 0.02})
    is_active = Column(Boolean, nullable=False, default=False)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id', ondelete='CASCADE'))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    # 관계 설정
    portfolio = relationship("Portfolio", back_populates="strategies")
    trades = relationship("Trade", back_populates="strategy", cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="strategy", cascade="all, delete-orphan")
    performance_metrics = relationship("PerformanceMetric", back_populates="strategy", cascade="all, delete-orphan")
    
    # 제약조건
    __table_args__ = (
        CheckConstraint(
            "strategy_type IN ('MA_CROSSOVER', 'MEAN_REVERSION', 'MOMENTUM', 'DCA', 'ML_BASED')",
            name='ck_strategies_valid_type'
        ),
        CheckConstraint(
            "exchange IN ('binance', 'coinbase', 'kraken', 'okx')",
            name='ck_strategies_valid_exchange'
        ),
        CheckConstraint(
            "symbol ~ '^[A-Z]{3,10}\\/[A-Z]{3,10}$'",
            name='ck_strategies_valid_symbol_format'
        ),
        Index('idx_strategies_is_active', 'is_active'),
        Index('idx_strategies_exchange_symbol', 'exchange', 'symbol'),
        Index('idx_strategies_strategy_type', 'strategy_type'),
        Index('idx_strategies_portfolio_id', 'portfolio_id'),
    )
    
    def __repr__(self) -> str:
        return f"<Strategy(id={self.id}, name='{self.name}', type='{self.strategy_type}', symbol='{self.symbol}')>"

class Trade(Base):
    """거래 내역 테이블 ORM 모델"""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey('strategies.id', ondelete='CASCADE'), nullable=False)
    exchange = Column(String(50), nullable=False)
    symbol = Column(String(50), nullable=False)
    side = Column(String(10), nullable=False)
    type = Column(String(20), nullable=False)
    amount = Column(DECIMAL(20, 8), nullable=False)
    price = Column(DECIMAL(20, 8))
    cost = Column(DECIMAL(20, 8))
    fee = Column(DECIMAL(20, 8), default=0)
    status = Column(String(20), nullable=False, default='pending')
    exchange_order_id = Column(String(255))
    error_message = Column(Text)
    timestamp_created = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    timestamp_updated = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    # 관계 설정
    strategy = relationship("Strategy", back_populates="trades")
    
    # 제약조건
    __table_args__ = (
        CheckConstraint("side IN ('buy', 'sell')", name='ck_trades_valid_side'),
        CheckConstraint("type IN ('market', 'limit', 'stop_loss', 'take_profit')", name='ck_trades_valid_type'),
        CheckConstraint("amount > 0", name='ck_trades_amount_positive'),
        CheckConstraint("price > 0 OR price IS NULL", name='ck_trades_price_positive'),
        CheckConstraint("cost > 0 OR cost IS NULL", name='ck_trades_cost_positive'),
        CheckConstraint("fee >= 0", name='ck_trades_fee_non_negative'),
        CheckConstraint(
            "status IN ('pending', 'open', 'closed', 'canceled', 'failed')",
            name='ck_trades_valid_status'
        ),
        CheckConstraint(
            "(type = 'market') OR (type != 'market' AND price IS NOT NULL)",
            name='ck_trades_price_required_for_limit'
        ),
        Index('idx_trades_strategy_id', 'strategy_id'),
        Index('idx_trades_exchange_symbol', 'exchange', 'symbol'),
        Index('idx_trades_status', 'status'),
        Index('idx_trades_timestamp_created', 'timestamp_created'),
        Index('idx_trades_exchange_order_id', 'exchange_order_id'),
    )
    
    def __repr__(self) -> str:
        return f"<Trade(id={self.id}, strategy_id={self.strategy_id}, side='{self.side}', amount={self.amount}, status='{self.status}')>"

class Position(Base):
    """포지션 테이블 ORM 모델"""
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey('strategies.id', ondelete='CASCADE'), nullable=False)
    exchange = Column(String(50), nullable=False)
    symbol = Column(String(50), nullable=False)
    side = Column(String(10), nullable=False)
    entry_price = Column(DECIMAL(20, 8), nullable=False)
    current_size = Column(DECIMAL(20, 8), nullable=False)
    avg_entry_price = Column(DECIMAL(20, 8), nullable=False)
    stop_loss_price = Column(DECIMAL(20, 8))
    take_profit_price = Column(DECIMAL(20, 8))
    unrealized_pnl = Column(DECIMAL(20, 8), default=0)
    realized_pnl = Column(DECIMAL(20, 8), default=0)
    total_fees = Column(DECIMAL(20, 8), default=0)
    is_open = Column(Boolean, nullable=False, default=True)
    opened_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    closed_at = Column(TIMESTAMP(timezone=True))
    
    # 관계 설정
    strategy = relationship("Strategy", back_populates="positions")
    
    # 제약조건
    __table_args__ = (
        CheckConstraint("side IN ('long', 'short')", name='ck_positions_valid_side'),
        CheckConstraint("entry_price > 0", name='ck_positions_entry_price_positive'),
        CheckConstraint("current_size > 0", name='ck_positions_current_size_positive'),
        CheckConstraint("avg_entry_price > 0", name='ck_positions_avg_entry_price_positive'),
        CheckConstraint("stop_loss_price > 0 OR stop_loss_price IS NULL", name='ck_positions_stop_loss_positive'),
        CheckConstraint("take_profit_price > 0 OR take_profit_price IS NULL", name='ck_positions_take_profit_positive'),
        CheckConstraint("total_fees >= 0", name='ck_positions_total_fees_non_negative'),
        CheckConstraint(
            "(is_open = true AND closed_at IS NULL) OR (is_open = false AND closed_at IS NOT NULL)",
            name='ck_positions_close_logic'
        ),
        Index('idx_positions_strategy_id', 'strategy_id'),
        Index('idx_positions_is_open', 'is_open'),
        Index('idx_positions_exchange_symbol', 'exchange', 'symbol'),
        Index('idx_positions_opened_at', 'opened_at'),
    )
    
    def __repr__(self) -> str:
        return f"<Position(id={self.id}, strategy_id={self.strategy_id}, side='{self.side}', size={self.current_size}, is_open={self.is_open})>"

class PortfolioRule(Base):
    """포트폴리오 리스크 규칙 테이블 ORM 모델"""
    __tablename__ = 'portfolio_rules'
    
    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id', ondelete='CASCADE'), nullable=False)
    rule_type = Column(String(50), nullable=False)
    rule_value = Column(JSONB, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    
    # 관계 설정
    portfolio = relationship("Portfolio", back_populates="portfolio_rules")
    
    # 제약조건
    __table_args__ = (
        CheckConstraint(
            "rule_type IN ('max_position_size_percent', 'max_daily_loss_percent', 'max_portfolio_exposure_percent', 'min_position_size_usd', 'max_positions_per_symbol', 'blacklisted_symbols')",
            name='ck_portfolio_rules_valid_type'
        ),
        Index('idx_portfolio_rules_portfolio_id', 'portfolio_id'),
        Index('idx_portfolio_rules_rule_type', 'rule_type'),
        Index('idx_portfolio_rules_is_active', 'is_active'),
    )
    
    def __repr__(self) -> str:
        return f"<PortfolioRule(id={self.id}, portfolio_id={self.portfolio_id}, type='{self.rule_type}')>"

class PerformanceMetric(Base):
    """성능 지표 테이블 ORM 모델"""
    __tablename__ = 'performance_metrics'
    
    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey('strategies.id', ondelete='CASCADE'), nullable=False)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(DECIMAL(20, 8), nullable=False)
    metric_unit = Column(String(20))
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    
    # 관계 설정
    strategy = relationship("Strategy", back_populates="performance_metrics")
    
    # 제약조건
    __table_args__ = (
        CheckConstraint(
            "metric_name IN ('total_return_percent', 'sharpe_ratio', 'max_drawdown_percent', 'win_rate_percent', 'profit_factor', 'total_trades', 'avg_trade_duration_hours')",
            name='ck_performance_metrics_valid_name'
        ),
        Index('idx_performance_metrics_strategy_id', 'strategy_id'),
        Index('idx_performance_metrics_metric_name', 'metric_name'),
        Index('idx_performance_metrics_timestamp', 'timestamp'),
    )
    
    def __repr__(self) -> str:
        return f"<PerformanceMetric(id={self.id}, strategy_id={self.strategy_id}, metric='{self.metric_name}', value={self.metric_value})>"

class SystemLog(Base):
    """시스템 로그 테이블 ORM 모델"""
    __tablename__ = 'system_logs'
    
    id = Column(Integer, primary_key=True)
    level = Column(String(20), nullable=False)
    logger_name = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    context = Column(JSONB)
    strategy_id = Column(Integer, ForeignKey('strategies.id', ondelete='SET NULL'))
    trade_id = Column(Integer, ForeignKey('trades.id', ondelete='SET NULL'))
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    
    # 제약조건
    __table_args__ = (
        CheckConstraint(
            "level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')",
            name='ck_system_logs_valid_level'
        ),
        Index('idx_system_logs_level', 'level'),
        Index('idx_system_logs_timestamp', 'timestamp'),
        Index('idx_system_logs_logger_name', 'logger_name'),
        Index('idx_system_logs_strategy_id', 'strategy_id'),
    )
    
    def __repr__(self) -> str:
        return f"<SystemLog(id={self.id}, level='{self.level}', logger='{self.logger_name}', timestamp={self.timestamp})>"


class DatabaseManager:
    """데이터베이스 연결 및 세션 관리"""
    
    def __init__(self, database_url: Optional[str] = None):
        """
        데이터베이스 매니저 초기화
        
        Args:
            database_url: PostgreSQL 연결 URL. None인 경우 환경변수에서 읽어옴
        """
        self.database_url = database_url or self._get_database_url()
        self.engine = None
        self.SessionLocal = None
        
    def _get_database_url(self) -> str:
        """환경변수에서 데이터베이스 URL 구성"""
        # 환경변수에서 DATABASE_URL이 설정되어 있으면 사용
        db_url = os.getenv('DATABASE_URL')
        if db_url:
            return db_url
        
        # TEST_MODE가 설정되어 있으면 SQLite 사용
        if os.getenv('TEST_MODE', 'false').lower() == 'true':
            return "sqlite:///./test_letrade.db"
        
        # 환경변수 기본값 설정 (PostgreSQL)
        host = os.getenv('DB_HOST', 'localhost')
        port = os.getenv('DB_PORT', '5432')
        database = os.getenv('DB_NAME', 'letrade_db')
        username = os.getenv('DB_USER', 'letrade_user')
        password = os.getenv('DB_PASSWORD', 'letrade_password')
        
        return f"postgresql://{username}:{password}@{host}:{port}/{database}"
    
    def connect(self) -> None:
        """데이터베이스 연결 초기화"""
        try:
            self.engine = create_engine(
                self.database_url,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,  # 연결 상태 확인
                pool_recycle=3600,   # 1시간마다 연결 재생성
                echo=False  # 프로덕션에서는 False
            )
            
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            logger.info("데이터베이스 연결이 성공적으로 초기화되었습니다.")
            
        except Exception as e:
            logger.error(f"데이터베이스 연결 실패: {e}")
            raise
    
    def create_tables(self) -> None:
        """모든 테이블 생성"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("모든 데이터베이스 테이블이 생성되었습니다.")
        except Exception as e:
            logger.error(f"테이블 생성 실패: {e}")
            raise
    
    def get_session(self) -> Session:
        """새로운 데이터베이스 세션 반환"""
        if self.SessionLocal is None:
            raise RuntimeError("데이터베이스가 연결되지 않았습니다. connect()를 먼저 호출하세요.")
        
        return self.SessionLocal()
    
    async def async_connect(self) -> None:
        """비동기 데이터베이스 연결 설정"""
        # 동기식 connect 메서드를 호출
        self.connect()
    
    def is_connected(self) -> bool:
        """데이터베이스 연결 상태 확인"""
        if self.engine is None:
            return False
        
        try:
            with self.engine.connect() as connection:
                # SQLite와 PostgreSQL 모두 호환되는 쿼리 사용
                result = connection.execute(text("SELECT 1"))
                result.fetchone()
            return True
        except Exception as e:
            logger.debug(f"연결 테스트 실패: {e}")
            return False
    
    def disconnect(self) -> None:
        """데이터베이스 연결 종료"""
        if self.engine:
            self.engine.dispose()
            self.engine = None
            self.SessionLocal = None
            logger.info("데이터베이스 연결이 종료되었습니다.")
    
    async def async_disconnect(self) -> None:
        """비동기 데이터베이스 연결 종료"""
        self.disconnect()
    
    def close(self) -> None:
        """데이터베이스 연결 종료 (backward compatibility)"""
        self.disconnect()


# 전역 데이터베이스 매니저 인스턴스
db_manager = DatabaseManager()

def get_db() -> Session:
    """
    데이터베이스 세션 의존성 주입용 함수
    
    FastAPI 등에서 Depends()와 함께 사용하거나,
    with 문과 함께 사용할 수 있습니다.
    
    Usage:
        with get_db() as db:
            portfolio = db.query(Portfolio).first()
    """
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()

def init_database() -> None:
    """데이터베이스 초기화 (연결 + 테이블 생성)"""
    db_manager.connect()
    db_manager.create_tables()