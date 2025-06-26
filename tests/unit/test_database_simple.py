"""
간단한 데이터베이스 ORM 통합 테스트

SQLite 호환성 문제를 피하기 위해 핵심 기능만 테스트
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from src.common.database import DatabaseManager, db_manager
from src.common.db_config import DatabaseHealthChecker, DatabaseInitializer


class TestDatabaseManager:
    """DatabaseManager 클래스 테스트"""

    def test_database_url_construction(self):
        """데이터베이스 URL 구성 테스트"""
        with patch.dict(
            "os.environ",
            {
                "DB_HOST": "test-host",
                "DB_PORT": "5433",
                "DB_NAME": "test_db",
                "DB_USER": "test_user",
                "DB_PASSWORD": "test_pass",
            },
        ):
            manager = DatabaseManager()
            expected_url = "postgresql://test_user:test_pass@test-host:5433/test_db"
            assert manager._get_database_url() == expected_url

    def test_database_url_defaults(self):
        """데이터베이스 URL 기본값 테스트"""
        with patch.dict("os.environ", {}, clear=True):
            manager = DatabaseManager()
            expected_url = (
                "postgresql://letrade_user:letrade_password@localhost:5432/letrade_db"
            )
            assert manager._get_database_url() == expected_url


class TestDatabaseInitializer:
    """DatabaseInitializer 클래스 테스트"""

    @patch("src.common.db_config.db_manager")
    def test_initialize_system_calls(self, mock_db_manager):
        """시스템 초기화 호출 확인"""
        # Mock 설정
        mock_session = MagicMock()
        mock_db_manager.get_session.return_value = mock_session
        mock_session.__enter__.return_value = mock_session
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        initializer = DatabaseInitializer()
        initializer.initialize_system()

        # 호출 확인
        mock_db_manager.connect.assert_called_once()
        mock_db_manager.create_tables.assert_called_once()


class TestDatabaseHealthChecker:
    """DatabaseHealthChecker 클래스 테스트"""

    @patch("src.common.db_config.db_manager")
    def test_check_connection_healthy(self, mock_db_manager):
        """정상 연결 상태 테스트"""
        # Mock 설정
        mock_session = MagicMock()
        mock_db_manager.get_session.return_value = mock_session
        mock_session.__enter__.return_value = mock_session
        mock_session.execute.return_value.fetchone.return_value = True

        checker = DatabaseHealthChecker()
        result = checker.check_connection()

        assert result["status"] == "healthy"
        assert result["connected"] is True
        assert "정상" in result["message"]

    @patch("src.common.db_config.db_manager")
    def test_check_connection_unhealthy(self, mock_db_manager):
        """연결 실패 상태 테스트"""
        # Mock 설정
        mock_db_manager.get_session.side_effect = Exception("Connection failed")

        checker = DatabaseHealthChecker()
        result = checker.check_connection()

        assert result["status"] == "unhealthy"
        assert result["connected"] is False
        assert "Connection failed" in result["error"]


class TestDatabaseIntegration:
    """데이터베이스 통합 기능 테스트"""

    @patch("src.common.database.create_engine")
    @patch("src.common.database.sessionmaker")
    def test_database_manager_connect(self, mock_sessionmaker, mock_create_engine):
        """데이터베이스 매니저 연결 테스트"""
        # Mock 설정
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_session_class = MagicMock()
        mock_sessionmaker.return_value = mock_session_class

        manager = DatabaseManager()
        manager.connect()

        # 호출 확인
        mock_create_engine.assert_called_once()
        mock_sessionmaker.assert_called_once_with(
            autocommit=False, autoflush=False, bind=mock_engine
        )

        assert manager.engine == mock_engine
        assert manager.SessionLocal == mock_session_class

    @patch("src.common.database.Base")
    def test_create_tables(self, mock_base):
        """테이블 생성 테스트"""
        # Mock 설정
        mock_engine = MagicMock()
        mock_metadata = MagicMock()
        mock_base.metadata = mock_metadata

        manager = DatabaseManager()
        manager.engine = mock_engine
        manager.create_tables()

        # 호출 확인
        mock_metadata.create_all.assert_called_once_with(bind=mock_engine)


class TestPerformanceTrackerIntegration:
    """PerformanceTracker 데이터베이스 통합 테스트"""

    @patch("src.strategies.base_strategy.db_manager")
    def test_save_metrics_to_db(self, mock_db_manager):
        """성능 지표 데이터베이스 저장 테스트"""
        from src.strategies.base_strategy import PerformanceTracker

        # Mock 설정
        mock_session = MagicMock()
        mock_db_manager.get_session.return_value = mock_session
        mock_session.__enter__.return_value = mock_session

        tracker = PerformanceTracker(strategy_id=1)
        tracker.update_metric("total_return_percent", 15.5)
        tracker.save_metrics_to_db()

        # 세션 사용 확인
        mock_db_manager.get_session.assert_called()
        mock_session.add.assert_called()
        mock_session.commit.assert_called()

    @patch("src.strategies.base_strategy.db_manager")
    def test_load_metrics_from_db(self, mock_db_manager):
        """성능 지표 데이터베이스 로드 테스트"""
        from src.strategies.base_strategy import PerformanceTracker

        # Mock 설정
        mock_session = MagicMock()
        mock_db_manager.get_session.return_value = mock_session
        mock_session.__enter__.return_value = mock_session
        mock_session.query.return_value.filter_by.return_value.order_by.return_value.first.return_value = (
            None
        )

        tracker = PerformanceTracker(strategy_id=1)
        result = tracker.load_latest_metrics_from_db()

        # 세션 사용 확인
        mock_db_manager.get_session.assert_called()
        mock_session.query.assert_called()


class TestConfigValidation:
    """환경변수 검증 테스트"""

    def test_validate_database_config_valid(self):
        """유효한 데이터베이스 설정 테스트"""
        from src.common.db_config import validate_database_config

        with patch.dict(
            "os.environ",
            {
                "DB_HOST": "localhost",
                "DB_PORT": "5432",
                "DB_NAME": "letrade_db",
                "DB_USER": "letrade_user",
                "DB_PASSWORD": "letrade_password",
            },
        ):
            result = validate_database_config()

            assert result["status"] == "valid"
            assert len(result["missing_vars"]) == 0
            assert result["total_existing"] == 5

    def test_validate_database_config_missing(self):
        """누락된 데이터베이스 설정 테스트"""
        from src.common.db_config import validate_database_config

        with patch.dict("os.environ", {"DB_HOST": "localhost"}, clear=True):
            result = validate_database_config()

            assert result["status"] == "invalid"
            assert len(result["missing_vars"]) == 4
            assert "DB_PORT" in result["missing_vars"]
            assert "DB_NAME" in result["missing_vars"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
