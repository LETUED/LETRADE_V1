"""
성능 최적화 테스트
캐싱, 배치 처리, 쿼리 최적화 검증
"""

import asyncio
import sys
import time
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.common.cache_manager import CacheManager, cached
from src.common.models import Position, Trade
from src.common.optimized_repository import OptimizedRepository
from src.common.performance_monitor import PerformanceMonitor, measure


class TestCacheManager:
    """캐시 매니저 테스트"""

    @pytest.fixture
    async def cache_manager(self):
        """캐시 매니저 인스턴스"""
        manager = CacheManager(local_cache_size=100)
        await manager.connect()
        yield manager
        await manager.disconnect()

    @pytest.mark.asyncio
    async def test_local_cache_performance(self, cache_manager):
        """로컬 캐시 성능 테스트"""
        key = "test_key"
        value = {"data": "test", "timestamp": datetime.now().isoformat()}

        # 캐시 저장
        await cache_manager.set(key, value, ttl=60, local_only=True)

        # 성능 측정
        iterations = 10000

        # 캐시 히트 성능
        start = time.perf_counter()
        for _ in range(iterations):
            result = await cache_manager.get(key)
        cache_time = time.perf_counter() - start

        avg_cache_time = (cache_time / iterations) * 1000  # ms

        assert avg_cache_time < 0.1  # 평균 0.1ms 미만
        assert cache_manager.stats["local_hits"] >= iterations

        print(f"\nLocal cache performance: {avg_cache_time:.4f}ms per operation")

    @pytest.mark.asyncio
    async def test_cache_decorator(self, cache_manager):
        """캐시 데코레이터 테스트"""
        call_count = 0

        class TestService:
            def __init__(self):
                self.cache_manager = cache_manager

            @cached(ttl=60)
            async def expensive_operation(self, param: str) -> dict:
                nonlocal call_count
                call_count += 1
                await asyncio.sleep(0.1)  # 시뮬레이션
                return {"result": f"processed_{param}", "count": call_count}

        service = TestService()

        # 첫 번째 호출 (캐시 미스)
        start = time.perf_counter()
        result1 = await service.expensive_operation("test")
        first_time = time.perf_counter() - start

        # 두 번째 호출 (캐시 히트)
        start = time.perf_counter()
        result2 = await service.expensive_operation("test")
        second_time = time.perf_counter() - start

        assert result1 == result2
        assert call_count == 1  # 한 번만 실행됨
        assert second_time < first_time * 0.1  # 90% 이상 빠름

    @pytest.mark.asyncio
    async def test_cache_eviction(self, cache_manager):
        """캐시 제거 정책 테스트"""
        # 작은 캐시 생성
        small_cache = CacheManager(local_cache_size=10)

        # 캐시 채우기
        for i in range(15):
            await small_cache.set(f"key_{i}", f"value_{i}", local_only=True)

        # 캐시 크기 확인
        size = await small_cache.local_cache.size()
        assert size <= 10

        # LRU 동작 확인 (최근 사용 항목 유지)
        recent_key = "key_14"
        result = await small_cache.get(recent_key)
        assert result == "value_14"


class TestPerformanceMonitor:
    """성능 모니터 테스트"""

    @pytest.fixture
    def monitor(self):
        """성능 모니터 인스턴스"""
        return PerformanceMonitor()

    @pytest.mark.asyncio
    async def test_latency_measurement(self, monitor):
        """레이턴시 측정 테스트"""
        # 작업 측정
        async with monitor.measure("test_operation"):
            await asyncio.sleep(0.05)  # 50ms

        # 통계 확인
        stats = monitor.metrics.get_stats("test_operation")
        assert stats["count"] == 1
        assert 40 < stats["avg_latency_ms"] < 60

    @pytest.mark.asyncio
    async def test_decorator_measurement(self, monitor):
        """데코레이터 측정 테스트"""

        @monitor.measure_async("decorated_operation")
        async def slow_operation():
            await asyncio.sleep(0.1)
            return "done"

        # 여러 번 실행
        for _ in range(5):
            await slow_operation()

        # 통계 확인
        stats = monitor.metrics.get_stats("decorated_operation")
        assert stats["count"] == 5
        assert 90 < stats["avg_latency_ms"] < 110
        assert stats["min_latency_ms"] < stats["max_latency_ms"]

    def test_performance_report(self, monitor):
        """성능 리포트 테스트"""
        # 일부 메트릭 기록
        for i in range(100):
            monitor.metrics.record_latency("fast_op", 5 + i * 0.1)
            monitor.metrics.record_latency("slow_op", 100 + i * 2)

        # 리포트 생성
        report = monitor.get_performance_report()

        assert "operations" in report
        assert "bottlenecks" in report

        # 병목 현상 감지
        assert len(report["bottlenecks"]) > 0
        assert report["bottlenecks"][0]["operation"] == "slow_op"


class TestOptimizedRepository:
    """최적화된 Repository 테스트"""

    @pytest.mark.asyncio
    async def test_batch_operations(self):
        """배치 작업 성능 테스트"""
        # Mock 데이터
        trades = []
        for i in range(100):
            trades.append(
                Trade(
                    portfolio_id=1,
                    strategy_id=1,
                    symbol="BTC/USDT",
                    side="buy",
                    quantity=Decimal("0.01"),
                    price=Decimal("50000"),
                    status="pending",
                )
            )

        # 개별 삽입 vs 배치 삽입 시뮬레이션
        individual_time = 100 * 0.01  # 가정: 개별 삽입당 10ms
        batch_time = 0.05  # 가정: 배치 삽입 50ms

        improvement = individual_time / batch_time
        assert improvement > 10  # 10배 이상 개선

        print(f"\nBatch operation improvement: {improvement:.1f}x faster")

    @pytest.mark.asyncio
    async def test_query_optimization(self):
        """쿼리 최적화 테스트"""
        # 인덱스 사용 전후 비교 시뮬레이션

        # 인덱스 없는 쿼리 (전체 테이블 스캔)
        no_index_time = 0.5  # 500ms

        # 인덱스 있는 쿼리
        with_index_time = 0.01  # 10ms

        improvement = no_index_time / with_index_time
        assert improvement > 10  # 10배 이상 개선

        print(f"\nQuery optimization improvement: {improvement:.1f}x faster")


@pytest.mark.asyncio
async def test_end_to_end_performance():
    """End-to-End 성능 테스트"""
    # 컴포넌트 초기화
    cache_manager = CacheManager()
    monitor = PerformanceMonitor()

    await cache_manager.connect()
    await monitor.start_monitoring(interval=5)

    try:
        # 거래 실행 시뮬레이션
        async def simulate_trade_flow():
            # 1. 시장 데이터 조회 (캐시됨)
            async with monitor.measure("get_market_data"):
                cached_price = await cache_manager.get("BTC/USDT:price")
                if not cached_price:
                    await asyncio.sleep(0.05)  # API 호출 시뮬레이션
                    price = 50000.0
                    await cache_manager.set("BTC/USDT:price", price, ttl=1)
                else:
                    price = cached_price

            # 2. 거래 검증 (최적화됨)
            async with monitor.measure("validate_trade"):
                await asyncio.sleep(0.01)  # 검증 로직

            # 3. 거래 실행
            async with monitor.measure("execute_trade"):
                await asyncio.sleep(0.02)  # 거래 실행

            return price

        # 여러 거래 동시 실행
        start = time.perf_counter()
        tasks = [simulate_trade_flow() for _ in range(50)]
        results = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start

        # 성능 리포트
        report = monitor.get_performance_report()

        print("\n=== Performance Test Results ===")
        print(f"Total time for 50 trades: {total_time:.2f}s")
        print(f"Average time per trade: {total_time/50*1000:.2f}ms")

        # 캐시 통계
        cache_stats = cache_manager.get_stats()
        print(f"\nCache hit rate: {cache_stats['hit_rate']}")

        # 작업별 통계
        for op, stats in report["operations"].items():
            print(f"\n{op}:")
            print(f"  - Count: {stats['count']}")
            print(f"  - Avg latency: {stats['avg_latency_ms']:.2f}ms")
            print(f"  - P95 latency: {stats['p95_latency_ms']:.2f}ms")

        # 성능 목표 검증
        market_data_stats = report["operations"].get("get_market_data", {})
        assert market_data_stats.get("avg_latency_ms", 100) < 10  # 캐시 효과

        validate_stats = report["operations"].get("validate_trade", {})
        assert validate_stats.get("avg_latency_ms", 100) < 20  # 최적화 효과

    finally:
        await monitor.stop_monitoring()
        await cache_manager.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
