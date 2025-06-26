"""
성능 모니터링 도구
시스템 성능 측정 및 병목 현상 감지
"""

import time
import asyncio
import logging
import psutil
import functools
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime
from contextlib import asynccontextmanager
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """성능 메트릭 수집기"""
    
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self.counters: Dict[str, int] = defaultdict(int)
        
    def record_latency(self, operation: str, latency_ms: float):
        """레이턴시 기록"""
        self.metrics[f"{operation}_latency"].append(latency_ms)
        self.counters[f"{operation}_count"] += 1
        
    def record_throughput(self, operation: str, count: int):
        """처리량 기록"""
        self.counters[f"{operation}_throughput"] += count
        
    def get_stats(self, operation: str) -> Dict[str, float]:
        """통계 조회"""
        latency_key = f"{operation}_latency"
        latencies = list(self.metrics.get(latency_key, []))
        
        if not latencies:
            return {
                'count': 0,
                'avg_latency_ms': 0,
                'min_latency_ms': 0,
                'max_latency_ms': 0,
                'p50_latency_ms': 0,
                'p95_latency_ms': 0,
                'p99_latency_ms': 0
            }
        
        latencies.sort()
        count = len(latencies)
        
        return {
            'count': self.counters.get(f"{operation}_count", 0),
            'avg_latency_ms': sum(latencies) / count,
            'min_latency_ms': latencies[0],
            'max_latency_ms': latencies[-1],
            'p50_latency_ms': latencies[int(count * 0.5)],
            'p95_latency_ms': latencies[int(count * 0.95)],
            'p99_latency_ms': latencies[int(count * 0.99)]
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """모든 통계 조회"""
        operations = set()
        for key in self.metrics.keys():
            if key.endswith('_latency'):
                operations.add(key[:-8])  # Remove '_latency'
        
        return {op: self.get_stats(op) for op in operations}


class PerformanceMonitor:
    """성능 모니터"""
    
    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.start_time = time.time()
        self._monitoring = False
        self._monitor_task = None
        
    @asynccontextmanager
    async def measure(self, operation: str):
        """비동기 작업 측정"""
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self.metrics.record_latency(operation, elapsed_ms)
            
            if elapsed_ms > 1000:  # 1초 이상
                logger.warning(
                    f"Slow operation detected: {operation} took {elapsed_ms:.2f}ms"
                )
    
    def measure_sync(self, operation: str):
        """동기 함수 데코레이터"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    self.metrics.record_latency(operation, elapsed_ms)
            return wrapper
        return decorator
    
    def measure_async(self, operation: str):
        """비동기 함수 데코레이터"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                async with self.measure(operation):
                    return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    async def start_monitoring(self, interval: int = 60):
        """시스템 모니터링 시작"""
        if self._monitoring:
            return
            
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval))
        logger.info("Performance monitoring started")
    
    async def stop_monitoring(self):
        """시스템 모니터링 중지"""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Performance monitoring stopped")
    
    async def _monitor_loop(self, interval: int):
        """모니터링 루프"""
        while self._monitoring:
            try:
                # 시스템 리소스 측정
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # 네트워크 I/O
                net_io = psutil.net_io_counters()
                
                # 프로세스 정보
                process = psutil.Process()
                process_memory = process.memory_info()
                process_cpu = process.cpu_percent()
                
                system_stats = {
                    'timestamp': datetime.now(),
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_available_gb': memory.available / (1024**3),
                    'disk_percent': disk.percent,
                    'network_sent_mb': net_io.bytes_sent / (1024**2),
                    'network_recv_mb': net_io.bytes_recv / (1024**2),
                    'process_memory_mb': process_memory.rss / (1024**2),
                    'process_cpu_percent': process_cpu
                }
                
                # 리소스 경고
                if cpu_percent > 80:
                    logger.warning(f"High CPU usage: {cpu_percent}%")
                
                if memory.percent > 80:
                    logger.warning(f"High memory usage: {memory.percent}%")
                
                # 성능 메트릭 로깅
                operation_stats = self.metrics.get_all_stats()
                
                logger.info(
                    "System performance stats",
                    extra={
                        'system': system_stats,
                        'operations': operation_stats
                    }
                )
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
            
            await asyncio.sleep(interval)
    
    def get_performance_report(self) -> Dict[str, Any]:
        """성능 리포트 생성"""
        uptime_seconds = time.time() - self.start_time
        
        # 시스템 정보
        cpu_count = psutil.cpu_count()
        memory = psutil.virtual_memory()
        
        # 작업 통계
        operation_stats = self.metrics.get_all_stats()
        
        # 병목 현상 감지
        bottlenecks = []
        for op, stats in operation_stats.items():
            if stats['p95_latency_ms'] > 500:  # 95분위 500ms 이상
                bottlenecks.append({
                    'operation': op,
                    'p95_latency_ms': stats['p95_latency_ms'],
                    'avg_latency_ms': stats['avg_latency_ms']
                })
        
        return {
            'uptime_seconds': uptime_seconds,
            'system': {
                'cpu_count': cpu_count,
                'total_memory_gb': memory.total / (1024**3),
                'available_memory_gb': memory.available / (1024**3)
            },
            'operations': operation_stats,
            'bottlenecks': sorted(bottlenecks, key=lambda x: x['p95_latency_ms'], reverse=True),
            'timestamp': datetime.now()
        }
    
    def reset_metrics(self):
        """메트릭 초기화"""
        self.metrics = PerformanceMetrics()
        logger.info("Performance metrics reset")


# 글로벌 모니터 인스턴스
_monitor: Optional[PerformanceMonitor] = None


def get_monitor() -> PerformanceMonitor:
    """모니터 싱글톤 반환"""
    global _monitor
    if _monitor is None:
        _monitor = PerformanceMonitor()
    return _monitor


# 편의 함수
async def measure(operation: str):
    """성능 측정 컨텍스트 매니저"""
    monitor = get_monitor()
    async with monitor.measure(operation):
        yield


def profile_async(operation: str):
    """비동기 함수 프로파일링 데코레이터"""
    return get_monitor().measure_async(operation)


def profile_sync(operation: str):
    """동기 함수 프로파일링 데코레이터"""
    return get_monitor().measure_sync(operation)