"""
Strategy Worker 프로세스 관리자

이 모듈은 거래 전략의 실행을 담당하는 프로세스를 관리합니다.
각 전략은 독립적인 프로세스에서 실행되어 격리성과 안정성을 보장합니다.
"""

import asyncio
import logging
import multiprocessing as mp
import os
import signal
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, TimeoutError
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Type

import pandas as pd
import psutil

from src.common.message_bus import MessageBus
from src.strategies.base_strategy import BaseStrategy, StrategyConfig, TradingSignal

logger = logging.getLogger(__name__)


class WorkerStatus(Enum):
    """Strategy Worker 상태 열거형"""
    
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    CRASHED = "crashed"


@dataclass
class WorkerMetrics:
    """Worker 성능 메트릭"""
    
    process_id: Optional[int] = None
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_percent: float = 0.0
    start_time: Optional[datetime] = None
    uptime_seconds: float = 0.0
    messages_processed: int = 0
    signals_generated: int = 0
    last_heartbeat: Optional[datetime] = None
    error_count: int = 0
    restart_count: int = 0


@dataclass
class WorkerConfig:
    """Worker 설정"""
    
    max_memory_mb: float = 512.0  # 최대 메모리 사용량 (MB)
    max_cpu_percent: float = 80.0  # 최대 CPU 사용률 (%)
    heartbeat_interval: float = 30.0  # 헬스체크 간격 (초)
    max_restart_attempts: int = 3  # 최대 재시작 시도 횟수
    restart_delay: float = 5.0  # 재시작 지연 시간 (초)
    process_timeout: float = 120.0  # 프로세스 타임아웃 (초)
    enable_auto_restart: bool = True  # 자동 재시작 활성화
    resource_monitoring: bool = True  # 리소스 모니터링 활성화


class StrategyWorker:
    """
    Strategy Worker 프로세스 관리자
    
    각 거래 전략을 독립적인 프로세스에서 실행하고 관리합니다.
    프로세스 격리를 통해 안정성과 성능을 보장합니다.
    """
    
    def __init__(
        self,
        strategy_class: Type[BaseStrategy],
        strategy_config: StrategyConfig,
        worker_config: Optional[WorkerConfig] = None,
        message_bus: Optional[MessageBus] = None
    ):
        """
        Strategy Worker 초기화
        
        Args:
            strategy_class: 실행할 전략 클래스
            strategy_config: 전략 설정
            worker_config: Worker 설정
            message_bus: 메시지 버스 인스턴스
        """
        self.strategy_class = strategy_class
        self.strategy_config = strategy_config
        self.worker_config = worker_config or WorkerConfig()
        self.message_bus = message_bus
        
        # Worker 상태 관리
        self.status = WorkerStatus.IDLE
        self.metrics = WorkerMetrics()
        self.process: Optional[mp.Process] = None
        self.process_executor: Optional[ProcessPoolExecutor] = None
        
        # 내부 상태
        self._shutdown_event = asyncio.Event()
        self._monitoring_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        
        logger.info(
            f"Strategy Worker initialized for {strategy_config.strategy_id}",
            extra={
                "strategy_id": strategy_config.strategy_id,
                "strategy_class": strategy_class.__name__,
                "dry_run": strategy_config.dry_run
            }
        )
    
    async def start(self) -> bool:
        """
        Strategy Worker 시작
        
        Returns:
            bool: 시작 성공 여부
        """
        try:
            if self.status == WorkerStatus.RUNNING:
                logger.warning(
                    f"Strategy Worker {self.strategy_config.strategy_id} is already running"
                )
                return True
            
            logger.info(
                f"Starting Strategy Worker for {self.strategy_config.strategy_id}"
            )
            
            self.status = WorkerStatus.STARTING
            
            # 프로세스 실행기 생성
            self.process_executor = ProcessPoolExecutor(
                max_workers=1,
                mp_context=mp.get_context('spawn')
            )
            
            # 전략 프로세스 시작
            future = self.process_executor.submit(
                self._run_strategy_process,
                self.strategy_class,
                self.strategy_config,
                self.worker_config
            )
            
            # 프로세스 시작 대기 (타임아웃 적용)
            try:
                await asyncio.wait_for(
                    asyncio.wrap_future(future),
                    timeout=self.worker_config.process_timeout
                )
            except TimeoutError:
                logger.error(
                    f"Strategy process start timeout for {self.strategy_config.strategy_id}"
                )
                await self.stop()
                return False
            
            # 모니터링 시작
            await self._start_monitoring()
            
            self.status = WorkerStatus.RUNNING
            self.metrics.start_time = datetime.now(timezone.utc)
            
            logger.info(
                f"Strategy Worker {self.strategy_config.strategy_id} started successfully"
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to start Strategy Worker {self.strategy_config.strategy_id}: {e}",
                extra={"error": str(e), "traceback": traceback.format_exc()}
            )
            self.status = WorkerStatus.ERROR
            await self.stop()
            return False
    
    async def stop(self) -> bool:
        """
        Strategy Worker 중지
        
        Returns:
            bool: 중지 성공 여부
        """
        try:
            if self.status in (WorkerStatus.STOPPED, WorkerStatus.STOPPING):
                return True
            
            logger.info(
                f"Stopping Strategy Worker for {self.strategy_config.strategy_id}"
            )
            
            self.status = WorkerStatus.STOPPING
            
            # 모니터링 중지
            await self._stop_monitoring()
            
            # 프로세스 종료
            if self.process_executor:
                try:
                    # 우아한 종료 시도
                    self.process_executor.shutdown(wait=True, timeout=10.0)
                except Exception as e:
                    logger.warning(
                        f"Graceful shutdown failed, forcing termination: {e}"
                    )
                    # 강제 종료
                    self.process_executor.shutdown(wait=False)
                
                self.process_executor = None
            
            # 프로세스 정보 정리
            if self.process and self.process.is_alive():
                try:
                    self.process.terminate()
                    self.process.join(timeout=5.0)
                    if self.process.is_alive():
                        self.process.kill()
                        self.process.join()
                except Exception as e:
                    logger.warning(f"Error cleaning up process: {e}")
            
            self.process = None
            self.status = WorkerStatus.STOPPED
            
            logger.info(
                f"Strategy Worker {self.strategy_config.strategy_id} stopped successfully"
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to stop Strategy Worker {self.strategy_config.strategy_id}: {e}",
                extra={"error": str(e)}
            )
            self.status = WorkerStatus.ERROR
            return False
    
    async def restart(self) -> bool:
        """
        Strategy Worker 재시작
        
        Returns:
            bool: 재시작 성공 여부
        """
        logger.info(
            f"Restarting Strategy Worker for {self.strategy_config.strategy_id}"
        )
        
        self.metrics.restart_count += 1
        
        # 중지 후 재시작
        await self.stop()
        await asyncio.sleep(self.worker_config.restart_delay)
        return await self.start()
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Worker 헬스체크
        
        Returns:
            Dict[str, Any]: 헬스체크 결과
        """
        health_status = {
            "strategy_id": self.strategy_config.strategy_id,
            "status": self.status.value,
            "healthy": self.status == WorkerStatus.RUNNING,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": self._get_current_metrics(),
            "config": {
                "dry_run": self.strategy_config.dry_run,
                "enabled": self.strategy_config.enabled,
                "max_memory_mb": self.worker_config.max_memory_mb,
                "max_cpu_percent": self.worker_config.max_cpu_percent
            }
        }
        
        # 프로세스 상태 확인
        if self.process:
            try:
                process_info = psutil.Process(self.process.pid)
                health_status["process_info"] = {
                    "pid": self.process.pid,
                    "status": process_info.status(),
                    "cpu_percent": process_info.cpu_percent(),
                    "memory_mb": process_info.memory_info().rss / 1024 / 1024,
                    "threads": process_info.num_threads()
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                health_status["process_info"] = {"error": "Process not accessible"}
        
        return health_status
    
    def get_metrics(self) -> WorkerMetrics:
        """현재 Worker 메트릭 반환"""
        return self.metrics
    
    def get_status(self) -> WorkerStatus:
        """현재 Worker 상태 반환"""
        return self.status
    
    async def _start_monitoring(self):
        """모니터링 태스크 시작"""
        if not self.worker_config.resource_monitoring:
            return
        
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
    
    async def _stop_monitoring(self):
        """모니터링 태스크 중지"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
    
    async def _monitoring_loop(self):
        """리소스 모니터링 루프"""
        while not self._shutdown_event.is_set():
            try:
                await self._update_metrics()
                await self._check_resource_limits()
                await asyncio.sleep(10.0)  # 10초마다 모니터링
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    f"Monitoring error for {self.strategy_config.strategy_id}: {e}"
                )
                await asyncio.sleep(5.0)
    
    async def _heartbeat_loop(self):
        """헬스체크 루프"""
        while not self._shutdown_event.is_set():
            try:
                self.metrics.last_heartbeat = datetime.now(timezone.utc)
                
                # 프로세스 생존 확인
                if self.process and not self.process.is_alive():
                    logger.warning(
                        f"Strategy process died for {self.strategy_config.strategy_id}"
                    )
                    self.status = WorkerStatus.CRASHED
                    
                    # 자동 재시작
                    if (self.worker_config.enable_auto_restart and 
                        self.metrics.restart_count < self.worker_config.max_restart_attempts):
                        await self.restart()
                
                await asyncio.sleep(self.worker_config.heartbeat_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    f"Heartbeat error for {self.strategy_config.strategy_id}: {e}"
                )
                await asyncio.sleep(5.0)
    
    async def _update_metrics(self):
        """메트릭 업데이트"""
        if not self.process:
            return
        
        try:
            process_info = psutil.Process(self.process.pid)
            
            self.metrics.process_id = self.process.pid
            self.metrics.cpu_percent = process_info.cpu_percent()
            
            memory_info = process_info.memory_info()
            self.metrics.memory_mb = memory_info.rss / 1024 / 1024
            self.metrics.memory_percent = process_info.memory_percent()
            
            if self.metrics.start_time:
                self.metrics.uptime_seconds = (
                    datetime.now(timezone.utc) - self.metrics.start_time
                ).total_seconds()
            
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.warning(
                f"Cannot access process metrics for {self.strategy_config.strategy_id}: {e}"
            )
            self.metrics.error_count += 1
    
    async def _check_resource_limits(self):
        """리소스 한계 확인"""
        # 메모리 사용량 확인
        if self.metrics.memory_mb > self.worker_config.max_memory_mb:
            logger.warning(
                f"Memory limit exceeded for {self.strategy_config.strategy_id}: "
                f"{self.metrics.memory_mb:.2f}MB > {self.worker_config.max_memory_mb}MB"
            )
            self.metrics.error_count += 1
            
            # 자동 재시작
            if self.worker_config.enable_auto_restart:
                await self.restart()
        
        # CPU 사용률 확인
        if self.metrics.cpu_percent > self.worker_config.max_cpu_percent:
            logger.warning(
                f"CPU limit exceeded for {self.strategy_config.strategy_id}: "
                f"{self.metrics.cpu_percent:.2f}% > {self.worker_config.max_cpu_percent}%"
            )
            self.metrics.error_count += 1
    
    def _get_current_metrics(self) -> Dict[str, Any]:
        """현재 메트릭을 딕셔너리로 반환"""
        return {
            "process_id": self.metrics.process_id,
            "cpu_percent": self.metrics.cpu_percent,
            "memory_mb": self.metrics.memory_mb,
            "memory_percent": self.metrics.memory_percent,
            "uptime_seconds": self.metrics.uptime_seconds,
            "messages_processed": self.metrics.messages_processed,
            "signals_generated": self.metrics.signals_generated,
            "error_count": self.metrics.error_count,
            "restart_count": self.metrics.restart_count,
            "last_heartbeat": (
                self.metrics.last_heartbeat.isoformat() 
                if self.metrics.last_heartbeat else None
            )
        }
    
    @staticmethod
    def _run_strategy_process(
        strategy_class: Type[BaseStrategy],
        strategy_config: StrategyConfig,
        worker_config: WorkerConfig
    ):
        """
        별도 프로세스에서 전략 실행
        
        Args:
            strategy_class: 전략 클래스
            strategy_config: 전략 설정
            worker_config: Worker 설정
        """
        runner = StrategyProcessRunner(
            strategy_class=strategy_class,
            strategy_config=strategy_config,
            worker_config=worker_config
        )
        runner.run()


class StrategyProcessRunner:
    """전략 프로세스 실행을 담당하는 분리된 클래스"""
    
    def __init__(
        self,
        strategy_class: Type[BaseStrategy],
        strategy_config: StrategyConfig,
        worker_config: WorkerConfig
    ):
        self.strategy_class = strategy_class
        self.strategy_config = strategy_config
        self.worker_config = worker_config
        self.loop = None
        self.strategy = None
        self.message_bus = None
    
    def run(self):
        """프로세스 실행 진입점"""
        # 프로세스 내부에서 새로운 이벤트 루프 생성
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            self._setup_signal_handlers()
            self.loop.run_until_complete(self._run_strategy())
        except Exception as e:
            logger.error(
                f"Strategy process error: {e}",
                extra={"traceback": traceback.format_exc()}
            )
        finally:
            self.loop.close()
    
    def _setup_signal_handlers(self):
        """시그널 핸들러 설정"""
        def signal_handler(signum, frame):
            logger.info(f"Strategy process {os.getpid()} received signal {signum}")
            self.loop.stop()
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    
    async def _run_strategy(self):
        """비동기 전략 실행"""
        try:
            await self._initialize_strategy()
            await self._start_strategy()
            await self._subscribe_market_data()
            await self._monitor_strategy()
        except Exception as e:
            logger.error(
                f"Strategy execution error: {e}",
                extra={
                    "strategy_id": self.strategy_config.strategy_id,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
            )
        finally:
            await self._cleanup()
    
    async def _initialize_strategy(self):
        """전략 초기화"""
        # 전략 인스턴스 생성
        self.strategy = self.strategy_class(self.strategy_config)
        
        # 메시지 버스 설정 및 연결
        message_bus_config = {
            "host": os.getenv("RABBITMQ_HOST", "localhost"),
            "port": int(os.getenv("RABBITMQ_PORT", 5672)),
            "username": os.getenv("RABBITMQ_USERNAME", "guest"),
            "password": os.getenv("RABBITMQ_PASSWORD", "guest"),
            "virtual_host": os.getenv("RABBITMQ_VHOST", "/")
        }
        
        from src.common.message_bus import MessageBus
        self.message_bus = MessageBus(message_bus_config)
        
        if not await self.message_bus.connect():
            raise Exception("Failed to connect to message bus")
    
    async def _start_strategy(self):
        """전략 시작"""
        if not await self.strategy.start():
            raise Exception(f"Failed to start strategy {self.strategy_config.strategy_id}")
        
        logger.info(
            f"Strategy {self.strategy_config.strategy_id} running in process {os.getpid()}",
            extra={
                "strategy_id": self.strategy_config.strategy_id,
                "process_id": os.getpid(),
                "dry_run": self.strategy_config.dry_run
            }
        )
    
    async def _subscribe_market_data(self):
        """시장 데이터 구독"""
        subscriptions = self.strategy.get_required_subscriptions()
        
        for routing_key in subscriptions:
            success = await self.message_bus.subscribe(
                queue_name="market_data",
                callback=self._handle_market_data,
                auto_ack=False
            )
            
            if success:
                logger.info(
                    f"Subscribed to market data",
                    extra={
                        "strategy_id": self.strategy_config.strategy_id,
                        "routing_key": routing_key
                    }
                )
            else:
                logger.error(
                    f"Failed to subscribe to market data",
                    extra={
                        "strategy_id": self.strategy_config.strategy_id,
                        "routing_key": routing_key
                    }
                )
    
    async def _handle_market_data(self, message_data):
        """시장 데이터 수신 및 전략 처리"""
        try:
            payload = message_data.get("payload", {})
            routing_key = message_data.get("routing_key", "")
            
            logger.debug(
                f"Received market data for {self.strategy_config.strategy_id}",
                extra={
                    "routing_key": routing_key,
                    "payload_keys": list(payload.keys())
                }
            )
            
            # 빈 데이터프레임으로 시작 (실제로는 히스토리컬 데이터 제공 필요)
            dataframe = pd.DataFrame()
            
            # 전략에서 신호 생성
            signal = await self.strategy.on_data_async(payload, dataframe)
            
            if signal:
                await self._send_trading_signal(signal)
            
        except Exception as e:
            logger.error(
                f"Error handling market data: {e}",
                extra={
                    "strategy_id": self.strategy_config.strategy_id,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
            )
    
    async def _send_trading_signal(self, signal):
        """거래 신호 전송"""
        exchange_name = "letrade.requests"
        signal_routing_key = signal.get("routing_key", f"request.capital.allocation.{self.strategy_config.strategy_id}")
        signal_payload = signal.get("payload", signal)
        
        success = await self.message_bus.publish(
            exchange_name=exchange_name,
            routing_key=signal_routing_key,
            message=signal_payload
        )
        
        if success:
            logger.info(
                f"Trading signal sent to Capital Manager",
                extra={
                    "strategy_id": self.strategy_config.strategy_id,
                    "routing_key": signal_routing_key,
                    "side": signal_payload.get("side"),
                    "signal_price": signal_payload.get("signal_price")
                }
            )
        else:
            logger.error(
                f"Failed to send signal to Capital Manager",
                extra={"strategy_id": self.strategy_config.strategy_id}
            )
    
    async def _monitor_strategy(self):
        """전략 모니터링"""
        while True:
            await asyncio.sleep(30.0)
            
            health_status = await self.strategy.health_check()
            logger.debug(
                f"Strategy health check",
                extra={
                    "strategy_id": self.strategy_config.strategy_id,
                    "healthy": health_status.get("healthy", False)
                }
            )
    
    async def _cleanup(self):
        """정리 작업"""
        if self.strategy:
            try:
                await self.strategy.stop()
            except Exception as e:
                logger.error(f"Error stopping strategy: {e}")
        
        if self.message_bus:
            try:
                await self.message_bus.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting message bus: {e}")


class StrategyWorkerManager:
    """
    여러 Strategy Worker를 관리하는 매니저 클래스
    """
    
    def __init__(self, message_bus: Optional[MessageBus] = None):
        """
        Manager 초기화
        
        Args:
            message_bus: 메시지 버스 인스턴스
        """
        self.message_bus = message_bus
        self.workers: Dict[str, StrategyWorker] = {}
        self._shutdown_event = asyncio.Event()
        
        logger.info("Strategy Worker Manager initialized")
    
    async def add_worker(
        self,
        strategy_id: str,
        strategy_class: Type[BaseStrategy],
        strategy_config: StrategyConfig,
        worker_config: Optional[WorkerConfig] = None
    ) -> bool:
        """
        새로운 Worker 추가
        
        Args:
            strategy_id: 전략 ID
            strategy_class: 전략 클래스
            strategy_config: 전략 설정
            worker_config: Worker 설정
            
        Returns:
            bool: 추가 성공 여부
        """
        if strategy_id in self.workers:
            logger.warning(f"Worker {strategy_id} already exists")
            return False
        
        worker = StrategyWorker(
            strategy_class=strategy_class,
            strategy_config=strategy_config,
            worker_config=worker_config,
            message_bus=self.message_bus
        )
        
        self.workers[strategy_id] = worker
        
        logger.info(f"Worker {strategy_id} added to manager")
        return True
    
    async def start_worker(self, strategy_id: str) -> bool:
        """Worker 시작"""
        if strategy_id not in self.workers:
            logger.error(f"Worker {strategy_id} not found")
            return False
        
        return await self.workers[strategy_id].start()
    
    async def stop_worker(self, strategy_id: str) -> bool:
        """Worker 중지"""
        if strategy_id not in self.workers:
            logger.error(f"Worker {strategy_id} not found")
            return False
        
        return await self.workers[strategy_id].stop()
    
    async def restart_worker(self, strategy_id: str) -> bool:
        """Worker 재시작"""
        if strategy_id not in self.workers:
            logger.error(f"Worker {strategy_id} not found")
            return False
        
        return await self.workers[strategy_id].restart()
    
    async def remove_worker(self, strategy_id: str) -> bool:
        """Worker 제거"""
        if strategy_id not in self.workers:
            logger.error(f"Worker {strategy_id} not found")
            return False
        
        worker = self.workers[strategy_id]
        await worker.stop()
        del self.workers[strategy_id]
        
        logger.info(f"Worker {strategy_id} removed from manager")
        return True
    
    async def start_all(self) -> bool:
        """모든 Worker 시작"""
        results = []
        for strategy_id, worker in self.workers.items():
            result = await worker.start()
            results.append(result)
            logger.info(f"Worker {strategy_id} start result: {result}")
        
        return all(results)
    
    async def stop_all(self) -> bool:
        """모든 Worker 중지"""
        results = []
        for strategy_id, worker in self.workers.items():
            result = await worker.stop()
            results.append(result)
            logger.info(f"Worker {strategy_id} stop result: {result}")
        
        return all(results)
    
    async def get_all_health_status(self) -> Dict[str, Dict[str, Any]]:
        """모든 Worker의 헬스 상태 조회"""
        health_status = {}
        
        for strategy_id, worker in self.workers.items():
            health_status[strategy_id] = await worker.health_check()
        
        return health_status
    
    def get_worker_count(self) -> int:
        """활성 Worker 개수 반환"""
        return len(self.workers)
    
    def get_running_worker_count(self) -> int:
        """실행 중인 Worker 개수 반환"""
        return len([
            w for w in self.workers.values() 
            if w.get_status() == WorkerStatus.RUNNING
        ])
    
    async def health_check(self) -> Dict[str, Any]:
        """Manager 전체 헬스체크"""
        return {
            "manager_healthy": True,
            "total_workers": self.get_worker_count(),
            "running_workers": self.get_running_worker_count(),
            "workers": await self.get_all_health_status(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }