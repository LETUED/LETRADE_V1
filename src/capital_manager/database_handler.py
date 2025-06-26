"""
Capital Manager 데이터베이스 핸들러

데이터베이스 관련 로직을 비즈니스 로직과 분리
"""

import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.common.db_session import db_session
from src.common.models import (
    PerformanceMetric,
    Portfolio,
    PortfolioRule,
    Position,
    Strategy,
    SystemLog,
    Trade,
)

from .interfaces import (
    PortfolioMetrics,
    PositionInfo,
    RiskParameters,
    TradeExecution,
    TradeRequest,
    ValidationResponse,
)

logger = logging.getLogger(__name__)


class CapitalManagerDatabaseHandler:
    """Capital Manager 데이터베이스 핸들러"""

    def __init__(self, portfolio_id: int = 1):
        """
        데이터베이스 핸들러 초기화

        Args:
            portfolio_id: 포트폴리오 ID (기본값: 1)
        """
        self.portfolio_id = portfolio_id
        self._portfolio_cache = None
        self._rules_cache = {}

    @contextmanager
    def get_db_session(self):
        """데이터베이스 세션 컨텍스트 매니저"""
        with db_session.get_db() as session:
            yield session

    async def load_portfolio_state(self) -> Optional[Portfolio]:
        """포트폴리오 상태 로드"""
        try:
            with self.get_db_session() as session:
                portfolio = (
                    session.query(Portfolio).filter_by(id=self.portfolio_id).first()
                )

                if portfolio:
                    self._portfolio_cache = portfolio
                    logger.info(
                        "Loaded portfolio state",
                        extra={
                            "portfolio_id": self.portfolio_id,
                            "name": portfolio.name,
                            "total_capital": float(portfolio.total_capital),
                        },
                    )
                    return portfolio
                else:
                    logger.warning(f"Portfolio {self.portfolio_id} not found")
                    return None

        except Exception as e:
            logger.error(f"Failed to load portfolio state: {e}")
            return None

    async def load_portfolio_rules(self) -> Dict[str, Any]:
        """포트폴리오 규칙 로드"""
        try:
            with self.get_db_session() as session:
                rules = (
                    session.query(PortfolioRule)
                    .filter_by(portfolio_id=self.portfolio_id, is_active=True)
                    .all()
                )

                self._rules_cache = {rule.rule_name: rule.rule_value for rule in rules}

                logger.info(
                    f"Loaded {len(rules)} portfolio rules",
                    extra={"portfolio_id": self.portfolio_id},
                )

                return self._rules_cache

        except Exception as e:
            logger.error(f"Failed to load portfolio rules: {e}")
            return {}

    async def save_trade_validation(
        self, trade_request: TradeRequest, validation_response: ValidationResponse
    ) -> Optional[int]:
        """거래 검증 결과 저장"""
        try:
            with self.get_db_session() as session:
                trade = Trade(
                    portfolio_id=self.portfolio_id,
                    strategy_id=trade_request.strategy_id,
                    symbol=trade_request.symbol,
                    side=trade_request.side,
                    quantity=trade_request.quantity,
                    price=trade_request.price or 0,
                    status=(
                        "validated" if validation_response.is_approved() else "rejected"
                    ),
                    validation_result={
                        "result": validation_response.result.value,
                        "risk_level": validation_response.risk_level.value,
                        "reasons": validation_response.reasons,
                    },
                )

                session.add(trade)
                session.commit()

                logger.info(
                    "Saved trade validation result",
                    extra={
                        "trade_id": trade.id,
                        "result": validation_response.result.value,
                    },
                )

                return trade.id

        except Exception as e:
            logger.error(f"Failed to save trade validation: {e}")
            return None

    async def update_position(self, symbol: str, position_data: Dict[str, Any]) -> bool:
        """포지션 업데이트"""
        try:
            with self.get_db_session() as session:
                position = (
                    session.query(Position)
                    .filter_by(
                        portfolio_id=self.portfolio_id, symbol=symbol, is_open=True
                    )
                    .first()
                )

                if position:
                    # 기존 포지션 업데이트
                    for key, value in position_data.items():
                        if hasattr(position, key):
                            setattr(position, key, value)
                else:
                    # 새 포지션 생성
                    position = Position(
                        portfolio_id=self.portfolio_id, symbol=symbol, **position_data
                    )
                    session.add(position)

                session.commit()

                logger.info(
                    "Updated position",
                    extra={"symbol": symbol, "portfolio_id": self.portfolio_id},
                )

                return True

        except Exception as e:
            logger.error(f"Failed to update position: {e}")
            return False

    async def get_portfolio_metrics(self) -> Optional[PortfolioMetrics]:
        """포트폴리오 메트릭스 조회"""
        try:
            with self.get_db_session() as session:
                # 포트폴리오 정보
                portfolio = (
                    session.query(Portfolio).filter_by(id=self.portfolio_id).first()
                )

                if not portfolio:
                    return None

                # 오픈 포지션 정보
                positions = (
                    session.query(Position)
                    .filter_by(portfolio_id=self.portfolio_id, is_open=True)
                    .all()
                )

                # 오늘 실현 손익 계산
                today_start = datetime.now(timezone.utc).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )

                today_trades = (
                    session.query(Trade)
                    .filter(
                        Trade.portfolio_id == self.portfolio_id,
                        Trade.created_at >= today_start,
                        Trade.status == "completed",
                    )
                    .all()
                )

                realized_pnl_today = sum(
                    float(trade.realized_pnl or 0) for trade in today_trades
                )

                # 미실현 손익 계산
                unrealized_pnl = sum(
                    float(pos.unrealized_pnl or 0) for pos in positions
                )

                # 리스크 노출 계산
                total_risk_exposure = sum(
                    float(pos.size * pos.entry_price * 0.02)  # 2% 기본 리스크
                    for pos in positions
                )

                # 가장 큰 포지션 비율
                largest_position_percent = 0.0
                if positions and float(portfolio.total_capital) > 0:
                    largest_position_value = max(
                        float(pos.size * pos.entry_price) for pos in positions
                    )
                    largest_position_percent = (
                        largest_position_value / float(portfolio.total_capital)
                    ) * 100

                return PortfolioMetrics(
                    total_value=float(portfolio.total_capital),
                    available_cash=float(portfolio.available_capital),
                    unrealized_pnl=unrealized_pnl,
                    realized_pnl_today=realized_pnl_today,
                    total_risk_exposure=total_risk_exposure,
                    number_of_positions=len(positions),
                    largest_position_percent=largest_position_percent,
                    daily_var=float(portfolio.total_capital) * 0.02,  # 2% VaR
                )

        except Exception as e:
            logger.error(f"Failed to get portfolio metrics: {e}")
            return None

    async def get_open_positions(self) -> List[PositionInfo]:
        """오픈 포지션 목록 조회"""
        try:
            with self.get_db_session() as session:
                positions = (
                    session.query(Position)
                    .filter_by(portfolio_id=self.portfolio_id, is_open=True)
                    .all()
                )

                position_list = []
                for pos in positions:
                    position_info = PositionInfo(
                        symbol=pos.symbol,
                        side=pos.side,
                        size=float(pos.size),
                        entry_price=float(pos.entry_price),
                        current_price=float(pos.current_price or pos.entry_price),
                        unrealized_pnl=float(pos.unrealized_pnl or 0),
                        realized_pnl=float(pos.realized_pnl or 0),
                        stop_loss=float(pos.stop_loss) if pos.stop_loss else None,
                        take_profit=float(pos.take_profit) if pos.take_profit else None,
                        opened_at=pos.created_at,
                        strategy_id=pos.strategy_id,
                    )
                    position_list.append(position_info)

                return position_list

        except Exception as e:
            logger.error(f"Failed to get open positions: {e}")
            return []

    async def log_risk_event(self, event_type: str, details: Dict[str, Any]) -> bool:
        """리스크 이벤트 로깅"""
        try:
            with self.get_db_session() as session:
                log_entry = SystemLog(
                    log_level="WARNING",
                    component="capital_manager",
                    message=f"Risk event: {event_type}",
                    details={
                        "event_type": event_type,
                        "portfolio_id": self.portfolio_id,
                        **details,
                    },
                )

                session.add(log_entry)
                session.commit()

                logger.warning(
                    f"Risk event logged: {event_type}", extra={"details": details}
                )

                return True

        except Exception as e:
            logger.error(f"Failed to log risk event: {e}")
            return False

    async def save_performance_metrics(self, metrics: Dict[str, float]) -> bool:
        """성능 메트릭스 저장"""
        try:
            with self.get_db_session() as session:
                # 포트폴리오와 연결된 기본 전략 찾기
                strategy = (
                    session.query(Strategy)
                    .filter_by(portfolio_id=self.portfolio_id, is_active=True)
                    .first()
                )

                if not strategy:
                    logger.warning("No active strategy found for portfolio")
                    return False

                for metric_name, metric_value in metrics.items():
                    metric = PerformanceMetric(
                        strategy_id=strategy.id,
                        metric_name=metric_name,
                        metric_value=metric_value,
                    )
                    session.add(metric)

                session.commit()

                logger.info(
                    f"Saved {len(metrics)} performance metrics",
                    extra={"portfolio_id": self.portfolio_id},
                )

                return True

        except Exception as e:
            logger.error(f"Failed to save performance metrics: {e}")
            return False

    async def record_trade_execution(self, trade_execution: TradeExecution) -> bool:
        """거래 실행 기록"""
        try:
            with self.get_db_session() as session:
                # Trade 레코드 업데이트
                trade = (
                    session.query(Trade)
                    .filter_by(id=int(trade_execution.trade_id))
                    .first()
                )

                if trade:
                    trade.status = trade_execution.status
                    trade.executed_quantity = trade_execution.executed_quantity
                    trade.executed_price = trade_execution.price
                    trade.fees = trade_execution.fees
                    trade.executed_at = trade_execution.executed_at

                    # 실현 손익 계산 (간단한 버전)
                    if trade_execution.status == "filled":
                        if trade.side == "sell":
                            # 매도 시 실현 손익 계산
                            position = (
                                session.query(Position)
                                .filter_by(
                                    portfolio_id=self.portfolio_id,
                                    symbol=trade.symbol,
                                    is_open=True,
                                )
                                .first()
                            )

                            if position:
                                realized_pnl = (
                                    trade_execution.price - position.entry_price
                                ) * trade_execution.executed_quantity

                                trade.realized_pnl = realized_pnl

                    session.commit()

                    logger.info(
                        "Recorded trade execution",
                        extra={
                            "trade_id": trade_execution.trade_id,
                            "status": trade_execution.status,
                        },
                    )

                    return True

                else:
                    logger.warning(f"Trade {trade_execution.trade_id} not found")
                    return False

        except Exception as e:
            logger.error(f"Failed to record trade execution: {e}")
            return False
