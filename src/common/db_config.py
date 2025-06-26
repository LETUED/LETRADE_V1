"""
데이터베이스 설정 및 초기화 관리

이 모듈은 Letrade_v1 시스템의 데이터베이스 설정, 마이그레이션, 
그리고 초기 데이터 설정을 관리합니다.
"""

import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import (
    Portfolio,
    PortfolioRule,
    Strategy,
    SystemLog,
    db_manager,
    init_database,
)

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """데이터베이스 초기화 및 설정 관리"""

    def __init__(self):
        self.db_manager = db_manager

    def initialize_system(self) -> None:
        """전체 데이터베이스 시스템 초기화"""
        logger.info("데이터베이스 시스템 초기화 시작...")

        # 1. 데이터베이스 연결
        self.db_manager.connect()

        # 2. 테이블 생성
        self.db_manager.create_tables()

        # 3. 초기 데이터 생성
        self._create_initial_data()

        # 4. 시스템 로그 기록
        self._log_initialization()

        logger.info("데이터베이스 시스템 초기화 완료!")

    def _create_initial_data(self) -> None:
        """초기 필수 데이터 생성"""
        with self._get_session() as session:
            try:
                # 기본 포트폴리오가 존재하는지 확인
                existing_portfolio = (
                    session.query(Portfolio).filter_by(name="Default Portfolio").first()
                )

                if not existing_portfolio:
                    # 기본 포트폴리오 생성
                    default_portfolio = Portfolio(
                        name="Default Portfolio",
                        total_capital=10000.00,
                        available_capital=10000.00,
                        currency="USDT",
                        is_active=True,
                    )
                    session.add(default_portfolio)
                    session.commit()

                    logger.info("기본 포트폴리오가 생성되었습니다.")

                    # 기본 포트폴리오 리스크 규칙 생성
                    self._create_default_portfolio_rules(session, default_portfolio.id)

                    # 샘플 전략 생성
                    self._create_sample_strategy(session, default_portfolio.id)

                else:
                    logger.info("기본 포트폴리오가 이미 존재합니다.")

            except Exception as e:
                session.rollback()
                logger.error(f"초기 데이터 생성 실패: {e}")
                raise

    def _create_default_portfolio_rules(
        self, session: Session, portfolio_id: int
    ) -> None:
        """기본 포트폴리오 리스크 규칙 생성"""
        default_rules = [
            {"rule_type": "max_position_size_percent", "rule_value": {"value": 10.0}},
            {"rule_type": "max_daily_loss_percent", "rule_value": {"value": 5.0}},
            {
                "rule_type": "max_portfolio_exposure_percent",
                "rule_value": {"value": 80.0},
            },
            {"rule_type": "min_position_size_usd", "rule_value": {"value": 10.0}},
        ]

        for rule_data in default_rules:
            rule = PortfolioRule(
                portfolio_id=portfolio_id,
                rule_type=rule_data["rule_type"],
                rule_value=rule_data["rule_value"],
                is_active=True,
            )
            session.add(rule)

        session.commit()
        logger.info("기본 포트폴리오 리스크 규칙이 생성되었습니다.")

    def _create_sample_strategy(self, session: Session, portfolio_id: int) -> None:
        """샘플 MA Crossover 전략 생성"""
        sample_strategy = Strategy(
            name="BTC MA Crossover",
            strategy_type="MA_CROSSOVER",
            exchange="binance",
            symbol="BTC/USDT",
            parameters={"fast": 50, "slow": 200, "min_volume_24h": 1000000},
            position_sizing_config={"model": "fixed_fractional", "risk_percent": 0.02},
            portfolio_id=portfolio_id,
            is_active=False,  # 기본적으로 비활성화
        )

        session.add(sample_strategy)
        session.commit()
        logger.info("샘플 MA Crossover 전략이 생성되었습니다.")

    def _log_initialization(self) -> None:
        """시스템 초기화 로그 기록"""
        with self._get_session() as session:
            try:
                log_entry = SystemLog(
                    level="INFO",
                    logger_name="database.initializer",
                    message="데이터베이스 시스템 초기화 완료",
                    context={
                        "version": "001_initial_schema",
                        "tables_created": 7,
                        "initialization_type": "ORM_based",
                    },
                )
                session.add(log_entry)
                session.commit()

            except Exception as e:
                logger.warning(f"초기화 로그 기록 실패: {e}")

    @contextmanager
    def _get_session(self):
        """컨텍스트 매니저를 통한 세션 관리"""
        session = self.db_manager.get_session()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


class DatabaseHealthChecker:
    """데이터베이스 연결 상태 및 건강성 체크"""

    def __init__(self):
        self.db_manager = db_manager

    def check_connection(self) -> Dict[str, Any]:
        """데이터베이스 연결 상태 체크"""
        try:
            with self._get_session() as session:
                # 간단한 쿼리로 연결 테스트
                result = session.execute(text("SELECT 1"))
                result.fetchone()

                return {
                    "status": "healthy",
                    "connected": True,
                    "message": "데이터베이스 연결 정상",
                }

        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
                "message": "데이터베이스 연결 실패",
            }

    def check_tables(self) -> Dict[str, Any]:
        """필수 테이블 존재 여부 확인"""
        required_tables = [
            "portfolios",
            "strategies",
            "trades",
            "positions",
            "portfolio_rules",
            "performance_metrics",
            "system_logs",
        ]

        try:
            with self._get_session() as session:
                existing_tables = []
                missing_tables = []

                for table_name in required_tables:
                    try:
                        result = session.execute(
                            text(f"SELECT 1 FROM {table_name} LIMIT 1")
                        )
                        existing_tables.append(table_name)
                    except Exception:
                        missing_tables.append(table_name)

                return {
                    "status": "healthy" if not missing_tables else "unhealthy",
                    "existing_tables": existing_tables,
                    "missing_tables": missing_tables,
                    "total_required": len(required_tables),
                    "total_existing": len(existing_tables),
                }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "테이블 확인 중 오류 발생",
            }

    def get_table_counts(self) -> Dict[str, Any]:
        """각 테이블의 레코드 수 조회"""
        try:
            with self._get_session() as session:
                counts = {}

                # 포트폴리오 수
                counts["portfolios"] = session.query(Portfolio).count()

                # 전략 수
                counts["strategies"] = session.query(Strategy).count()

                # 기타 카운트들은 필요시 추가

                return {"status": "success", "counts": counts}

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "테이블 카운트 조회 실패",
            }

    @contextmanager
    def _get_session(self):
        """컨텍스트 매니저를 통한 세션 관리"""
        session = self.db_manager.get_session()
        try:
            yield session
        finally:
            session.close()


# 편의 함수들
def initialize_database() -> None:
    """데이터베이스 전체 시스템 초기화"""
    initializer = DatabaseInitializer()
    initializer.initialize_system()


def check_database_health() -> Dict[str, Any]:
    """데이터베이스 건강성 체크"""
    checker = DatabaseHealthChecker()

    connection_status = checker.check_connection()
    tables_status = checker.check_tables()
    counts = checker.get_table_counts()

    return {
        "connection": connection_status,
        "tables": tables_status,
        "counts": counts,
        "overall_status": (
            "healthy"
            if (
                connection_status["status"] == "healthy"
                and tables_status["status"] == "healthy"
            )
            else "unhealthy"
        ),
    }


# 환경변수 검증
def validate_database_config() -> Dict[str, Any]:
    """데이터베이스 설정 환경변수 검증"""
    required_vars = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]

    missing_vars = []
    existing_vars = {}

    for var in required_vars:
        value = os.getenv(var)
        if value:
            existing_vars[var] = value if var != "DB_PASSWORD" else "***"
        else:
            missing_vars.append(var)

    return {
        "status": "valid" if not missing_vars else "invalid",
        "existing_vars": existing_vars,
        "missing_vars": missing_vars,
        "total_required": len(required_vars),
        "total_existing": len(existing_vars),
    }

