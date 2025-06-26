"""
데이터베이스 세션 관리 모듈

Thread-safe하고 프로덕션 레벨의 데이터베이스 연결 관리
"""

import logging
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from src.common.config import Config

logger = logging.getLogger(__name__)


class DatabaseSession:
    """Thread-safe 데이터베이스 세션 관리 클래스"""

    def __init__(self) -> None:
        """데이터베이스 세션 관리자 초기화"""
        self.engine: Optional[Engine] = None
        self.SessionLocal: Optional[sessionmaker] = None
        self._initialized = False

    def initialize(self, database_url: Optional[str] = None) -> None:
        """
        데이터베이스 연결 초기화

        Args:
            database_url: PostgreSQL 연결 URL (없으면 환경변수에서 읽음)
        """
        if self._initialized:
            logger.warning("Database session already initialized")
            return

        # 데이터베이스 URL 설정
        db_url = database_url or Config.DATABASE_URL
        if not db_url:
            raise ValueError("DATABASE_URL not configured")

        # SQLAlchemy 엔진 생성
        self.engine = create_engine(
            db_url,
            # 커넥션 풀 설정
            poolclass=QueuePool,
            pool_size=20,  # 기본 풀 크기
            max_overflow=40,  # 최대 오버플로우
            pool_pre_ping=True,  # 연결 상태 체크
            pool_recycle=3600,  # 1시간마다 연결 재생성
            # 성능 옵션
            echo=False,  # SQL 로깅 비활성화 (프로덕션)
            echo_pool=False,
            # PostgreSQL 특화 옵션
            connect_args={
                "connect_timeout": 10,
                "options": "-c timezone=utc",
            },
        )

        # 세션 팩토리 생성
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            expire_on_commit=False,  # 커밋 후 객체 만료 방지
        )

        self._initialized = True
        logger.info(f"Database connection initialized: {self._mask_password(db_url)}")

    def close(self) -> None:
        """데이터베이스 연결 종료"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")

    @contextmanager
    def get_db(self) -> Generator[Session, None, None]:
        """
        데이터베이스 세션 컨텍스트 매니저

        사용 예시:
            with db_session.get_db() as db:
                result = db.query(Model).all()

        Yields:
            SQLAlchemy 세션 객체
        """
        if not self._initialized:
            raise RuntimeError("Database session not initialized")

        db = self.SessionLocal()
        try:
            yield db
        except Exception as e:
            db.rollback()
            logger.error(f"Database error occurred: {e}")
            raise
        finally:
            db.close()

    @contextmanager
    def atomic_transaction(self) -> Generator[Session, None, None]:
        """
        원자적 트랜잭션 컨텍스트 매니저

        성공시 자동 커밋, 실패시 자동 롤백

        사용 예시:
            with db_session.atomic_transaction() as db:
                db.add(new_object)
                # 자동 커밋됨
        """
        with self.get_db() as db:
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise

    def execute_query(self, query: str, params: Optional[dict] = None) -> list:
        """
        원시 SQL 쿼리 실행

        Args:
            query: SQL 쿼리 문자열
            params: 쿼리 파라미터

        Returns:
            쿼리 결과 리스트
        """
        with self.get_db() as db:
            result = db.execute(query, params or {})
            return result.fetchall()

    def _mask_password(self, url: str) -> str:
        """데이터베이스 URL에서 비밀번호 마스킹"""
        import re

        return re.sub(r"://[^:]+:([^@]+)@", r"://****:****@", url)

    def check_connection(self) -> bool:
        """데이터베이스 연결 상태 확인"""
        try:
            with self.get_db() as db:
                from sqlalchemy import text
                db.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False


# 전역 데이터베이스 세션 인스턴스
db_session = DatabaseSession()


def init_db() -> None:
    """데이터베이스 초기화 헬퍼 함수"""
    db_session.initialize()


def get_db() -> Generator[Session, None, None]:
    """FastAPI 의존성 주입용 함수"""
    with db_session.get_db() as db:
        yield db