"""
Strategy Worker 단위 테스트

Strategy Worker 프로세스 관리자의 핵심 기능을 테스트합니다.
"""

import asyncio
import multiprocessing as mp
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.strategies.base_strategy import BaseStrategy, StrategyConfig
from src.strategy_worker.main import (
    StrategyWorker,
    StrategyWorkerManager,
    WorkerConfig,
    WorkerMetrics,
    WorkerStatus,
)


class MockStrategy(BaseStrategy):
    """테스트용 Mock 전략"""

    def populate_indicators(self, dataframe):
        return dataframe

    def on_data(self, data, dataframe):
        return {"side": "buy", "signal_price": 50000.0}

    def get_required_subscriptions(self):
        return ["market_data.binance.btcusdt"]


@pytest.fixture
def strategy_config():
    """테스트용 전략 설정"""
    return StrategyConfig(
        strategy_id="test_strategy_001",
        name="Test Strategy",
        enabled=True,
        dry_run=True,
        custom_params={
            "symbol": "BTC/USDT",
            "exchange": "binance",
            "fast_period": 50,
            "slow_period": 200,
        },
    )


@pytest.fixture
def worker_config():
    """테스트용 Worker 설정"""
    return WorkerConfig(
        max_memory_mb=256.0,
        max_cpu_percent=50.0,
        heartbeat_interval=5.0,
        max_restart_attempts=2,
        restart_delay=1.0,
        process_timeout=30.0,
        enable_auto_restart=True,
        resource_monitoring=True,
    )


@pytest.fixture
def strategy_worker(strategy_config, worker_config):
    """테스트용 Strategy Worker 인스턴스"""
    return StrategyWorker(
        strategy_class=MockStrategy,
        strategy_config=strategy_config,
        worker_config=worker_config,
    )


class TestWorkerStatus:
    """Worker 상태 열거형 테스트"""

    def test_worker_status_values(self):
        """Worker 상태 값들이 올바른지 확인"""
        assert WorkerStatus.IDLE.value == "idle"
        assert WorkerStatus.STARTING.value == "starting"
        assert WorkerStatus.RUNNING.value == "running"
        assert WorkerStatus.STOPPING.value == "stopping"
        assert WorkerStatus.STOPPED.value == "stopped"
        assert WorkerStatus.ERROR.value == "error"
        assert WorkerStatus.CRASHED.value == "crashed"


class TestWorkerMetrics:
    """Worker 메트릭 테스트"""

    def test_worker_metrics_initialization(self):
        """Worker 메트릭 초기화 테스트"""
        metrics = WorkerMetrics()

        assert metrics.process_id is None
        assert metrics.cpu_percent == 0.0
        assert metrics.memory_mb == 0.0
        assert metrics.memory_percent == 0.0
        assert metrics.start_time is None
        assert metrics.uptime_seconds == 0.0
        assert metrics.messages_processed == 0
        assert metrics.signals_generated == 0
        assert metrics.last_heartbeat is None
        assert metrics.error_count == 0
        assert metrics.restart_count == 0


class TestWorkerConfig:
    """Worker 설정 테스트"""

    def test_worker_config_defaults(self):
        """Worker 설정 기본값 테스트"""
        config = WorkerConfig()

        assert config.max_memory_mb == 512.0
        assert config.max_cpu_percent == 80.0
        assert config.heartbeat_interval == 30.0
        assert config.max_restart_attempts == 3
        assert config.restart_delay == 5.0
        assert config.process_timeout == 120.0
        assert config.enable_auto_restart is True
        assert config.resource_monitoring is True

    def test_worker_config_custom_values(self, worker_config):
        """사용자 정의 Worker 설정 테스트"""
        assert worker_config.max_memory_mb == 256.0
        assert worker_config.max_cpu_percent == 50.0
        assert worker_config.heartbeat_interval == 5.0
        assert worker_config.max_restart_attempts == 2
        assert worker_config.restart_delay == 1.0
        assert worker_config.process_timeout == 30.0


class TestStrategyWorker:
    """Strategy Worker 클래스 테스트"""

    def test_worker_initialization(self, strategy_worker, strategy_config):
        """Worker 초기화 테스트"""
        assert strategy_worker.strategy_class == MockStrategy
        assert strategy_worker.strategy_config == strategy_config
        assert strategy_worker.status == WorkerStatus.IDLE
        assert strategy_worker.process is None
        assert strategy_worker.process_executor is None
        assert isinstance(strategy_worker.metrics, WorkerMetrics)

    def test_worker_get_status(self, strategy_worker):
        """Worker 상태 조회 테스트"""
        assert strategy_worker.get_status() == WorkerStatus.IDLE

        strategy_worker.status = WorkerStatus.RUNNING
        assert strategy_worker.get_status() == WorkerStatus.RUNNING

    def test_worker_get_metrics(self, strategy_worker):
        """Worker 메트릭 조회 테스트"""
        metrics = strategy_worker.get_metrics()
        assert isinstance(metrics, WorkerMetrics)
        assert metrics.process_id is None
        assert metrics.cpu_percent == 0.0

    @pytest.mark.asyncio
    async def test_worker_health_check(self, strategy_worker):
        """Worker 헬스체크 테스트"""
        health = await strategy_worker.health_check()

        assert health["strategy_id"] == "test_strategy_001"
        assert health["status"] == WorkerStatus.IDLE.value
        assert health["healthy"] is False  # IDLE 상태는 unhealthy
        assert "timestamp" in health
        assert "metrics" in health
        assert "config" in health

        # 설정 정보 확인
        config = health["config"]
        assert config["dry_run"] is True
        assert config["enabled"] is True
        assert config["max_memory_mb"] == 256.0

    @pytest.mark.asyncio
    async def test_worker_start_failure_handling(self, strategy_worker):
        """Worker 시작 실패 처리 테스트"""
        # 이미 실행 중인 상태에서 시작 시도
        strategy_worker.status = WorkerStatus.RUNNING
        result = await strategy_worker.start()
        assert result is True  # 이미 실행 중이면 True 반환

        # IDLE 상태로 되돌리고 실제 시작 실패 시뮬레이션
        strategy_worker.status = WorkerStatus.IDLE

        with patch(
            "src.strategy_worker.main.ProcessPoolExecutor"
        ) as mock_executor_class:
            # ProcessPoolExecutor 생성에서 예외 발생
            mock_executor_class.side_effect = Exception("Test exception")

            # stop 메서드가 호출되는 것을 방지하기 위해 Mock 처리
            with patch.object(strategy_worker, "stop") as mock_stop:
                mock_stop.return_value = True

                result = await strategy_worker.start()

                assert result is False
                # stop이 호출되어 상태가 변경될 수 있으므로 결과만 확인

    @pytest.mark.asyncio
    async def test_worker_stop_idle_state(self, strategy_worker):
        """IDLE 상태에서 중지 테스트"""
        result = await strategy_worker.stop()

        assert result is True
        assert strategy_worker.status == WorkerStatus.STOPPED

    @pytest.mark.asyncio
    async def test_worker_stop_with_executor(self, strategy_worker):
        """실행기가 있는 상태에서 중지 테스트"""
        # Mock 실행기 설정
        mock_executor = Mock()
        strategy_worker.process_executor = mock_executor
        strategy_worker.status = WorkerStatus.RUNNING

        with patch.object(strategy_worker, "_stop_monitoring") as mock_stop_monitoring:
            mock_stop_monitoring.return_value = None

            result = await strategy_worker.stop()

            assert result is True
            assert strategy_worker.status == WorkerStatus.STOPPED
            assert strategy_worker.process_executor is None
            mock_executor.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_worker_restart(self, strategy_worker):
        """Worker 재시작 테스트"""
        original_restart_count = strategy_worker.metrics.restart_count

        with patch.object(strategy_worker, "stop") as mock_stop:
            mock_stop.return_value = True
            with patch.object(strategy_worker, "start") as mock_start:
                mock_start.return_value = True

                result = await strategy_worker.restart()

                assert result is True
                assert (
                    strategy_worker.metrics.restart_count == original_restart_count + 1
                )
                mock_stop.assert_called_once()
                mock_start.assert_called_once()

    def test_worker_metrics_update(self, strategy_worker):
        """Worker 메트릭 업데이트 테스트"""
        # 기본 메트릭 상태 확인
        metrics = strategy_worker.get_metrics()
        assert metrics.restart_count == 0
        assert metrics.error_count == 0

        # 에러 카운트 증가
        strategy_worker.metrics.error_count += 1
        assert strategy_worker.get_metrics().error_count == 1

    def test_worker_status_transitions(self, strategy_worker):
        """Worker 상태 전환 테스트"""
        # 초기 상태
        assert strategy_worker.get_status() == WorkerStatus.IDLE

        # 상태 변경 테스트
        strategy_worker.status = WorkerStatus.STARTING
        assert strategy_worker.get_status() == WorkerStatus.STARTING

        strategy_worker.status = WorkerStatus.RUNNING
        assert strategy_worker.get_status() == WorkerStatus.RUNNING

    def test_worker_config_validation(self, strategy_worker):
        """Worker 설정 유효성 테스트"""
        config = strategy_worker.worker_config

        # 리소스 제한 값이 양수인지 확인
        assert config.max_memory_mb > 0
        assert config.max_cpu_percent > 0
        assert config.heartbeat_interval > 0
        assert config.restart_delay >= 0
        assert config.process_timeout > 0


class TestStrategyWorkerManager:
    """Strategy Worker Manager 테스트"""

    @pytest.fixture
    def worker_manager(self):
        """테스트용 Worker Manager"""
        return StrategyWorkerManager()

    def test_manager_initialization(self, worker_manager):
        """Manager 초기화 테스트"""
        assert worker_manager.message_bus is None
        assert len(worker_manager.workers) == 0
        assert worker_manager.get_worker_count() == 0
        assert worker_manager.get_running_worker_count() == 0

    @pytest.mark.asyncio
    async def test_add_worker(self, worker_manager, strategy_config, worker_config):
        """Worker 추가 테스트"""
        result = await worker_manager.add_worker(
            "test_001", MockStrategy, strategy_config, worker_config
        )

        assert result is True
        assert worker_manager.get_worker_count() == 1
        assert "test_001" in worker_manager.workers

    @pytest.mark.asyncio
    async def test_add_duplicate_worker(
        self, worker_manager, strategy_config, worker_config
    ):
        """중복 Worker 추가 테스트"""
        await worker_manager.add_worker(
            "test_001", MockStrategy, strategy_config, worker_config
        )

        # 같은 ID로 다시 추가 시도
        result = await worker_manager.add_worker(
            "test_001", MockStrategy, strategy_config, worker_config
        )

        assert result is False
        assert worker_manager.get_worker_count() == 1

    @pytest.mark.asyncio
    async def test_start_nonexistent_worker(self, worker_manager):
        """존재하지 않는 Worker 시작 테스트"""
        result = await worker_manager.start_worker("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_stop_nonexistent_worker(self, worker_manager):
        """존재하지 않는 Worker 중지 테스트"""
        result = await worker_manager.stop_worker("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_restart_nonexistent_worker(self, worker_manager):
        """존재하지 않는 Worker 재시작 테스트"""
        result = await worker_manager.restart_worker("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_worker(self, worker_manager, strategy_config, worker_config):
        """Worker 제거 테스트"""
        await worker_manager.add_worker(
            "test_001", MockStrategy, strategy_config, worker_config
        )
        assert worker_manager.get_worker_count() == 1

        with patch.object(worker_manager.workers["test_001"], "stop") as mock_stop:
            mock_stop.return_value = True

            result = await worker_manager.remove_worker("test_001")

            assert result is True
            assert worker_manager.get_worker_count() == 0
            assert "test_001" not in worker_manager.workers

    @pytest.mark.asyncio
    async def test_remove_nonexistent_worker(self, worker_manager):
        """존재하지 않는 Worker 제거 테스트"""
        result = await worker_manager.remove_worker("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_start_all_workers(
        self, worker_manager, strategy_config, worker_config
    ):
        """모든 Worker 시작 테스트"""
        # 여러 Worker 추가
        await worker_manager.add_worker(
            "test_001", MockStrategy, strategy_config, worker_config
        )
        await worker_manager.add_worker(
            "test_002", MockStrategy, strategy_config, worker_config
        )

        with patch.object(worker_manager.workers["test_001"], "start") as mock_start1:
            mock_start1.return_value = True
            with patch.object(
                worker_manager.workers["test_002"], "start"
            ) as mock_start2:
                mock_start2.return_value = True

                result = await worker_manager.start_all()

                assert result is True
                mock_start1.assert_called_once()
                mock_start2.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_all_workers(
        self, worker_manager, strategy_config, worker_config
    ):
        """모든 Worker 중지 테스트"""
        await worker_manager.add_worker(
            "test_001", MockStrategy, strategy_config, worker_config
        )
        await worker_manager.add_worker(
            "test_002", MockStrategy, strategy_config, worker_config
        )

        with patch.object(worker_manager.workers["test_001"], "stop") as mock_stop1:
            mock_stop1.return_value = True
            with patch.object(worker_manager.workers["test_002"], "stop") as mock_stop2:
                mock_stop2.return_value = True

                result = await worker_manager.stop_all()

                assert result is True
                mock_stop1.assert_called_once()
                mock_stop2.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_health_status(
        self, worker_manager, strategy_config, worker_config
    ):
        """전체 Worker 헬스 상태 조회 테스트"""
        await worker_manager.add_worker(
            "test_001", MockStrategy, strategy_config, worker_config
        )

        health_status = await worker_manager.get_all_health_status()

        assert "test_001" in health_status
        assert health_status["test_001"]["strategy_id"] == "test_strategy_001"

    @pytest.mark.asyncio
    async def test_manager_health_check(self, worker_manager):
        """Manager 헬스체크 테스트"""
        health = await worker_manager.health_check()

        assert health["manager_healthy"] is True
        assert health["total_workers"] == 0
        assert health["running_workers"] == 0
        assert "workers" in health
        assert "timestamp" in health


class TestStrategyWorkerIntegration:
    """Strategy Worker 통합 테스트 (프로세스 실행 제외)"""

    @pytest.mark.asyncio
    async def test_worker_lifecycle(self, strategy_config, worker_config):
        """Worker 전체 생명주기 테스트"""
        worker = StrategyWorker(MockStrategy, strategy_config, worker_config)

        # 초기 상태 확인
        assert worker.get_status() == WorkerStatus.IDLE

        # 헬스체크
        health = await worker.health_check()
        assert health["healthy"] is False

        # 메트릭 확인
        metrics = worker.get_metrics()
        assert metrics.process_id is None
        assert metrics.restart_count == 0


@pytest.mark.skipif(
    mp.get_start_method() != "spawn", reason="Process tests require spawn start method"
)
class TestStrategyWorkerProcess:
    """Strategy Worker 프로세스 관련 테스트 (실제 환경에서만 실행)"""

    def test_run_strategy_process_signature(self):
        """_run_strategy_process 메서드 시그니처 테스트"""
        # 메서드가 존재하고 호출 가능한지 확인
        assert hasattr(StrategyWorker, "_run_strategy_process")
        assert callable(StrategyWorker._run_strategy_process)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
