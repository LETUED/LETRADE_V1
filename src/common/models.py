"""
데이터베이스 ORM 모델 정의

설계 문서(05_Data_and_State_Management.md)에 따른 완전한 데이터베이스 스키마 구현
PostgreSQL 기반의 금융 거래 시스템을 위한 프로덕션 레벨 모델
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any

from sqlalchemy import (
    Column, Integer, String, Boolean, DECIMAL, TIMESTAMP,
    ForeignKey, Text, CheckConstraint, Index, UniqueConstraint,
    func, text
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import expression

# Base 클래스 생성
Base = declarative_base()


class Portfolio(Base):
    """
    포트폴리오 테이블
    
    자산 할당과 리스크 관리의 최상위 개념
    여러 전략이 동일한 포트폴리오에서 자본을 공유할 수 있음
    """
    __tablename__ = 'portfolios'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    parent_id = Column(Integer, ForeignKey('portfolios.id', ondelete='CASCADE'), nullable=True)
    total_capital = Column(DECIMAL(20, 8), nullable=False)
    available_capital = Column(DECIMAL(20, 8), nullable=False)
    currency = Column(String(10), nullable=False, default='USDT')
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 관계 정의
    parent = relationship("Portfolio", remote_side=[id], backref="children")
    rules = relationship("PortfolioRule", back_populates="portfolio", cascade="all, delete-orphan")
    strategies = relationship("Strategy", secondary="strategy_portfolio_map", back_populates="portfolios")
    
    # 인덱스
    __table_args__ = (
        Index('idx_portfolios_is_active', 'is_active'),
        Index('idx_portfolios_currency', 'currency'),
        CheckConstraint('total_capital >= 0', name='ck_portfolios_positive_total_capital'),
        CheckConstraint('available_capital >= 0', name='ck_portfolios_positive_available_capital'),
        CheckConstraint('available_capital <= total_capital', name='ck_portfolios_available_le_total'),
    )


class PortfolioRule(Base):
    """
    포트폴리오 리스크 관리 규칙 테이블
    
    각 포트폴리오에 적용될 리스크 관리 규칙을 정의
    """
    __tablename__ = 'portfolio_rules'
    
    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id', ondelete='CASCADE'), nullable=False)
    rule_type = Column(String(50), nullable=False)
    rule_value = Column(JSONB, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    
    # 관계 정의
    portfolio = relationship("Portfolio", back_populates="rules")
    
    # 제약 조건
    __table_args__ = (
        Index('idx_portfolio_rules_portfolio_id', 'portfolio_id'),
        Index('idx_portfolio_rules_rule_type', 'rule_type'),
        Index('idx_portfolio_rules_is_active', 'is_active'),
        CheckConstraint(
            "rule_type IN ('max_position_size_percent', 'max_daily_loss_percent', "
            "'max_portfolio_exposure_percent', 'min_position_size_usd', "
            "'max_positions_per_symbol', 'blacklisted_symbols')",
            name='ck_portfolio_rules_valid_type'
        ),
    )


class Strategy(Base):
    """
    거래 전략 테이블
    
    개별 전략 인스턴스에 대한 설정 및 상태 정보
    """
    __tablename__ = 'strategies'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    strategy_type = Column(String(50), nullable=False)
    exchange = Column(String(50), nullable=False)
    symbol = Column(String(50), nullable=False)
    parameters = Column(JSONB, nullable=True)
    position_sizing_config = Column(JSONB, nullable=True)
    is_active = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 관계 정의
    portfolios = relationship("Portfolio", secondary="strategy_portfolio_map", back_populates="strategies")
    trades = relationship("Trade", back_populates="strategy")
    positions = relationship("Position", back_populates="strategy")
    grid_orders = relationship("GridOrder", back_populates="strategy")
    
    # 제약 조건
    __table_args__ = (
        UniqueConstraint('name', 'exchange', 'symbol', name='uq_strategies_name_exchange_symbol'),
        Index('idx_strategies_strategy_type', 'strategy_type'),
        Index('idx_strategies_exchange_symbol', 'exchange', 'symbol'),
        Index('idx_strategies_is_active', 'is_active'),
        CheckConstraint(
            "strategy_type IN ('MA_CROSSOVER', 'MEAN_REVERSION', 'MOMENTUM', 'DCA', 'ML_BASED', 'GRID')",
            name='ck_strategies_valid_type'
        ),
        CheckConstraint(
            "exchange IN ('binance', 'coinbase', 'kraken', 'okx')",
            name='ck_strategies_valid_exchange'
        ),
    )


class StrategyPortfolioMap(Base):
    """
    전략-포트폴리오 매핑 테이블
    
    Many-to-Many 관계를 위한 연결 테이블
    """
    __tablename__ = 'strategy_portfolio_map'
    
    strategy_id = Column(Integer, ForeignKey('strategies.id', ondelete='CASCADE'), primary_key=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id', ondelete='CASCADE'), primary_key=True)
    allocation_percent = Column(DECIMAL(5, 2), nullable=True)  # 선택적: 전략별 자본 할당 비율
    
    # 제약 조건
    __table_args__ = (
        CheckConstraint('allocation_percent >= 0 AND allocation_percent <= 100', 
                       name='ck_strategy_portfolio_valid_allocation'),
    )


class Trade(Base):
    """
    거래 내역 테이블 (파티셔닝 적용)
    
    거래소로 전송된 모든 주문의 완전하고 불변하는 원장
    대용량 데이터를 위해 월별 파티셔닝 적용
    """
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey('strategies.id', ondelete='CASCADE'), nullable=False)
    exchange = Column(String(50), nullable=False)
    exchange_order_id = Column(String(255), unique=True, nullable=False)  # ccxt_order_id를 더 명확한 이름으로
    symbol = Column(String(50), nullable=False)
    type = Column(String(20), nullable=False)  # limit, market
    side = Column(String(10), nullable=False)  # buy, sell
    amount = Column(DECIMAL(20, 8), nullable=False)
    price = Column(DECIMAL(20, 8), nullable=True)
    cost = Column(DECIMAL(20, 8), nullable=True)
    fee = Column(DECIMAL(20, 8), nullable=True)
    fee_currency = Column(String(10), nullable=True)
    status = Column(String(20), nullable=False)  # open, closed, canceled
    timestamp_created = Column(TIMESTAMP(timezone=True), nullable=False)
    timestamp_updated = Column(TIMESTAMP(timezone=True), nullable=False)
    
    # 관계 정의
    strategy = relationship("Strategy", back_populates="trades")
    
    # 제약 조건
    __table_args__ = (
        Index('idx_trades_strategy_id', 'strategy_id'),
        Index('idx_trades_exchange_symbol', 'exchange', 'symbol'),
        Index('idx_trades_status', 'status'),
        Index('idx_trades_timestamp_created', 'timestamp_created'),
        Index('idx_trades_exchange_order_id', 'exchange_order_id'),
        CheckConstraint("type IN ('limit', 'market', 'stop_loss', 'take_profit')", 
                       name='ck_trades_valid_type'),
        CheckConstraint("side IN ('buy', 'sell')", name='ck_trades_valid_side'),
        CheckConstraint("status IN ('open', 'closed', 'canceled', 'expired')", 
                       name='ck_trades_valid_status'),
        CheckConstraint("amount > 0", name='ck_trades_positive_amount'),
    )


class Position(Base):
    """
    포지션 테이블
    
    봇이 현재 보유 자산에 대해 가지고 있는 이해를 나타내는 가변적인 테이블
    """
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey('strategies.id', ondelete='CASCADE'), nullable=False)
    exchange = Column(String(50), nullable=False)
    symbol = Column(String(50), nullable=False)
    position_type = Column(String(20), nullable=False, default='spot')  # spot, futures
    entry_price = Column(DECIMAL(20, 8), nullable=False)
    current_size = Column(DECIMAL(20, 8), nullable=False)  # 양수=롱, 음수=숏
    avg_entry_price = Column(DECIMAL(20, 8), nullable=False)
    leverage = Column(Integer, nullable=True, default=1)  # 선물용
    mark_price = Column(DECIMAL(20, 8), nullable=True)  # 선물용
    liquidation_price = Column(DECIMAL(20, 8), nullable=True)  # 선물용
    stop_loss_price = Column(DECIMAL(20, 8), nullable=True)
    take_profit_price = Column(DECIMAL(20, 8), nullable=True)
    unrealized_pnl = Column(DECIMAL(20, 8), nullable=True, default=0)
    realized_pnl = Column(DECIMAL(20, 8), nullable=True, default=0)
    total_fees = Column(DECIMAL(20, 8), nullable=True, default=0)
    is_open = Column(Boolean, nullable=False, default=True)
    opened_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    closed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    
    # 관계 정의
    strategy = relationship("Strategy", back_populates="positions")
    
    # 제약 조건
    __table_args__ = (
        Index('idx_positions_strategy_id', 'strategy_id'),
        Index('idx_positions_exchange_symbol', 'exchange', 'symbol'),
        Index('idx_positions_is_open', 'is_open'),
        Index('idx_positions_opened_at', 'opened_at'),
        CheckConstraint("position_type IN ('spot', 'futures', 'margin')", 
                       name='ck_positions_valid_type'),
        CheckConstraint("leverage >= 1 AND leverage <= 125", 
                       name='ck_positions_valid_leverage'),
    )


class StakingLog(Base):
    """
    스테이킹 로그 테이블
    
    모든 스테이킹 및 언스테이킹 작업 추적
    """
    __tablename__ = 'staking_logs'
    
    id = Column(Integer, primary_key=True)
    exchange = Column(String(50), nullable=False)
    asset = Column(String(20), nullable=False)
    amount = Column(DECIMAL(20, 8), nullable=False)
    transaction_type = Column(String(20), nullable=False)  # stake, unstake
    status = Column(String(20), nullable=False)  # success, failed, pending
    transaction_hash = Column(String(255), nullable=True)
    estimated_apr = Column(DECIMAL(10, 4), nullable=True)  # 연이율
    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    
    # 제약 조건
    __table_args__ = (
        Index('idx_staking_logs_asset', 'asset'),
        Index('idx_staking_logs_timestamp', 'timestamp'),
        CheckConstraint("transaction_type IN ('stake', 'unstake', 'claim_rewards')", 
                       name='ck_staking_logs_valid_type'),
        CheckConstraint("status IN ('success', 'failed', 'pending')", 
                       name='ck_staking_logs_valid_status'),
        CheckConstraint("amount > 0", name='ck_staking_logs_positive_amount'),
    )


class GridOrder(Base):
    """
    그리드 주문 테이블
    
    그리드 거래 전략의 모든 개별 주문 상태를 영속적으로 저장
    시스템 재시작 후에도 그리드 상태를 완벽하게 복구 가능
    """
    __tablename__ = 'grid_orders'
    
    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey('strategies.id', ondelete='CASCADE'), nullable=False)
    grid_level = Column(Integer, nullable=False)  # 0 to N
    price = Column(DECIMAL(20, 8), nullable=False)
    side = Column(String(4), nullable=False)  # buy, sell
    amount = Column(DECIMAL(20, 8), nullable=False)
    exchange_order_id = Column(String(255), ForeignKey('trades.exchange_order_id'), nullable=True)
    status = Column(String(20), nullable=False)  # active, filled, cancelled
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    filled_at = Column(TIMESTAMP(timezone=True), nullable=True)
    
    # 관계 정의
    strategy = relationship("Strategy", back_populates="grid_orders")
    
    # 제약 조건
    __table_args__ = (
        Index('idx_grid_orders_strategy_id', 'strategy_id'),
        Index('idx_grid_orders_status', 'status'),
        Index('idx_grid_orders_grid_level', 'grid_level'),
        UniqueConstraint('strategy_id', 'grid_level', 'side', 
                        name='uq_grid_orders_strategy_level_side'),
        CheckConstraint("side IN ('buy', 'sell')", name='ck_grid_orders_valid_side'),
        CheckConstraint("status IN ('active', 'filled', 'cancelled')", 
                       name='ck_grid_orders_valid_status'),
        CheckConstraint("price > 0", name='ck_grid_orders_positive_price'),
        CheckConstraint("amount > 0", name='ck_grid_orders_positive_amount'),
    )


# 성능 메트릭 및 시스템 로그는 필요에 따라 추가
class PerformanceMetric(Base):
    """
    성능 메트릭 테이블
    
    전략별 성능 지표를 시계열로 저장
    """
    __tablename__ = 'performance_metrics'
    
    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey('strategies.id', ondelete='CASCADE'), nullable=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id', ondelete='CASCADE'), nullable=True)
    metric_name = Column(String(50), nullable=False)
    metric_value = Column(DECIMAL(20, 8), nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    
    # 인덱스
    __table_args__ = (
        Index('idx_performance_metrics_strategy_id', 'strategy_id'),
        Index('idx_performance_metrics_portfolio_id', 'portfolio_id'),
        Index('idx_performance_metrics_metric_name', 'metric_name'),
        Index('idx_performance_metrics_timestamp', 'timestamp'),
    )


class SystemLog(Base):
    """
    시스템 로그 테이블
    
    중요한 시스템 이벤트 및 오류를 영구 저장
    """
    __tablename__ = 'system_logs'
    
    id = Column(Integer, primary_key=True)
    level = Column(String(20), nullable=False)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    logger_name = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    context = Column(JSONB, nullable=True)
    strategy_id = Column(Integer, ForeignKey('strategies.id', ondelete='SET NULL'), nullable=True)
    trade_id = Column(Integer, ForeignKey('trades.id', ondelete='SET NULL'), nullable=True)
    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    
    # 인덱스
    __table_args__ = (
        Index('idx_system_logs_level', 'level'),
        Index('idx_system_logs_logger_name', 'logger_name'),
        Index('idx_system_logs_timestamp', 'timestamp'),
        Index('idx_system_logs_strategy_id', 'strategy_id'),
        CheckConstraint(
            "level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')",
            name='ck_system_logs_valid_level'
        ),
    )