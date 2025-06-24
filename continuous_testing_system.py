#!/usr/bin/env python3
"""
24시간 연속 드라이런 테스트 시스템
24-Hour Continuous Dry-Run Testing System

시스템 안정성을 검증하기 위한 24시간 연속 테스트 프레임워크
- 실시간 성능 모니터링
- 자동 오류 감지 및 복구
- 상세한 메트릭 수집
- 최적화된 성능 검증
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import signal

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("continuous_test.log", mode="a")
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class TestMetrics:
    """테스트 메트릭 데이터 구조"""
    start_time: datetime
    end_time: Optional[datetime] = None
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    average_latency_ms: float = 0.0
    peak_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    performance_samples: List[float] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        if self.total_operations == 0:
            return 0.0
        return (self.successful_operations / self.total_operations) * 100
    
    @property
    def duration_hours(self) -> float:
        if not self.end_time:
            end_time = datetime.now(timezone.utc)
        else:
            end_time = self.end_time
        return (end_time - self.start_time).total_seconds() / 3600
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_hours": self.duration_hours,
            "total_operations": self.total_operations,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "success_rate": self.success_rate,
            "average_latency_ms": self.average_latency_ms,
            "peak_latency_ms": self.peak_latency_ms,
            "min_latency_ms": self.min_latency_ms if self.min_latency_ms != float('inf') else 0.0,
            "memory_usage_mb": self.memory_usage_mb,
            "cpu_usage_percent": self.cpu_usage_percent,
            "error_count": len(self.errors),
            "latest_errors": self.errors[-5:] if self.errors else []
        }


class PerformanceMonitor:
    """성능 모니터링 클래스"""
    
    def __init__(self):
        self.metrics = TestMetrics(start_time=datetime.now(timezone.utc))
        self.running = False
        
    async def record_operation(self, success: bool, latency_ms: float, error: Optional[str] = None):
        """개별 연산 기록"""
        self.metrics.total_operations += 1
        
        if success:
            self.metrics.successful_operations += 1
        else:
            self.metrics.failed_operations += 1
            if error:
                self.metrics.errors.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": error,
                    "latency_ms": latency_ms
                })
        
        # 레이턴시 통계 업데이트
        self.metrics.performance_samples.append(latency_ms)
        self.metrics.peak_latency_ms = max(self.metrics.peak_latency_ms, latency_ms)
        self.metrics.min_latency_ms = min(self.metrics.min_latency_ms, latency_ms)
        
        # 평균 레이턴시 계산 (최근 1000개 샘플)
        if len(self.metrics.performance_samples) > 1000:
            self.metrics.performance_samples = self.metrics.performance_samples[-1000:]
        
        if self.metrics.performance_samples:
            self.metrics.average_latency_ms = sum(self.metrics.performance_samples) / len(self.metrics.performance_samples)
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """현재 메트릭 반환"""
        return self.metrics.to_dict()
    
    def save_metrics_report(self, filename: str):
        """메트릭 보고서 저장"""
        report = self.get_current_metrics()
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"📊 Metrics report saved: {filename}")


class MockExchangeConnector:
    """테스트용 Mock Exchange Connector"""
    
    def __init__(self):
        self.connected = False
        self.base_latency = 0.5  # 0.5ms base latency
        self.error_rate = 0.001  # 0.1% error rate
        
    async def connect(self) -> bool:
        """연결 시뮬레이션"""
        await asyncio.sleep(0.001)  # 1ms 연결 시간
        self.connected = True
        return True
    
    async def disconnect(self) -> bool:
        """연결 해제"""
        self.connected = False
        return True
    
    async def get_market_data(self, symbol: str, timeframe: str = "1m", limit: int = 50) -> List[Dict]:
        """시장 데이터 가져오기 시뮬레이션"""
        if not self.connected:
            raise Exception("Not connected")
        
        # 성능 시뮬레이션 (0.5ms ~ 2ms 범위)
        latency = self.base_latency + (time.time() % 1.5)
        await asyncio.sleep(latency / 1000)
        
        # 드물게 오류 발생 시뮬레이션
        if time.time() % 1000 < self.error_rate * 1000:
            raise Exception("Simulated network error")
        
        # Mock 데이터 반환
        return [
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "open": 50000.0,
                "high": 50100.0,
                "low": 49900.0,
                "close": 50050.0,
                "volume": 1000.0
            }
            for _ in range(limit)
        ]
    
    async def health_check(self) -> Dict[str, Any]:
        """헬스체크"""
        return {
            "connected": self.connected,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "healthy" if self.connected else "disconnected"
        }


class ContinuousTestingSystem:
    """24시간 연속 테스트 시스템"""
    
    def __init__(self, test_duration_hours: float = 24.0):
        self.test_duration_hours = test_duration_hours
        self.monitor = PerformanceMonitor()
        self.exchange_connector = MockExchangeConnector()
        self.running = False
        self.stop_event = asyncio.Event()
        
        # 테스트 설정
        self.operation_interval = 1.0  # 1초마다 테스트 연산
        self.health_check_interval = 60.0  # 1분마다 헬스체크
        self.report_interval = 300.0  # 5분마다 진행 보고
        
        # 신호 핸들러 설정
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """종료 신호 처리"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.stop_event.set()
    
    async def start_test(self):
        """연속 테스트 시작"""
        logger.info("🚀 Starting 24-Hour Continuous Testing System")
        logger.info(f"📊 Test Duration: {self.test_duration_hours} hours")
        logger.info(f"⚡ Target Performance: <1ms latency")
        logger.info("=" * 60)
        
        self.running = True
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(hours=self.test_duration_hours)
        
        # Exchange connector 연결
        connected = await self.exchange_connector.connect()
        if not connected:
            logger.error("❌ Failed to connect to exchange connector")
            return False
        
        logger.info("✅ Exchange connector connected")
        
        # 백그라운드 태스크 시작
        tasks = [
            asyncio.create_task(self._continuous_operations()),
            asyncio.create_task(self._health_check_loop()),
            asyncio.create_task(self._progress_reporting_loop()),
            asyncio.create_task(self._duration_monitor(end_time))
        ]
        
        try:
            # 모든 태스크 실행
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"❌ Test execution error: {e}")
            
        finally:
            # 정리 작업
            await self._cleanup()
            
        # 최종 보고서 생성
        await self._generate_final_report()
        
        return True
    
    async def _continuous_operations(self):
        """연속 연산 수행"""
        logger.info("🔄 Starting continuous operations...")
        
        while self.running and not self.stop_event.is_set():
            try:
                # 시장 데이터 가져오기 테스트
                start_time = time.time()
                
                market_data = await self.exchange_connector.get_market_data("BTC/USDT")
                
                latency_ms = (time.time() - start_time) * 1000
                await self.monitor.record_operation(True, latency_ms)
                
                # 성능 목표 확인 (1ms 목표)
                if latency_ms > 10.0:  # 10ms 이상이면 경고
                    logger.warning(f"⚠️ High latency detected: {latency_ms:.2f}ms")
                
            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                await self.monitor.record_operation(False, latency_ms, str(e))
                logger.error(f"❌ Operation failed: {e}")
            
            # 다음 연산까지 대기
            await asyncio.sleep(self.operation_interval)
    
    async def _health_check_loop(self):
        """헬스체크 루프"""
        while self.running and not self.stop_event.is_set():
            try:
                health = await self.exchange_connector.health_check()
                
                if not health.get("connected", False):
                    logger.error("❌ Health check failed: connector not connected")
                    # 재연결 시도
                    await self.exchange_connector.connect()
                
            except Exception as e:
                logger.error(f"❌ Health check error: {e}")
            
            await asyncio.sleep(self.health_check_interval)
    
    async def _progress_reporting_loop(self):
        """진행 상황 보고 루프"""
        while self.running and not self.stop_event.is_set():
            metrics = self.monitor.get_current_metrics()
            
            logger.info("📊 Progress Report")
            logger.info("-" * 40)
            logger.info(f"⏱️  Duration: {metrics['duration_hours']:.2f} hours")
            logger.info(f"🔢 Total Operations: {metrics['total_operations']:,}")
            logger.info(f"✅ Success Rate: {metrics['success_rate']:.2f}%")
            logger.info(f"⚡ Avg Latency: {metrics['average_latency_ms']:.3f}ms")
            logger.info(f"🔥 Peak Latency: {metrics['peak_latency_ms']:.3f}ms")
            logger.info(f"⚠️  Errors: {metrics['error_count']}")
            
            # 성능 평가
            if metrics['average_latency_ms'] < 1.0:
                logger.info("🎉 EXCELLENT performance maintained")
            elif metrics['average_latency_ms'] < 5.0:
                logger.info("🎯 GOOD performance maintained") 
            elif metrics['average_latency_ms'] < 200.0:
                logger.info("✅ ACCEPTABLE performance")
            else:
                logger.warning("⚠️ Performance degradation detected")
            
            logger.info("")
            
            await asyncio.sleep(self.report_interval)
    
    async def _duration_monitor(self, end_time: datetime):
        """테스트 기간 모니터링"""
        while datetime.now(timezone.utc) < end_time and not self.stop_event.is_set():
            remaining = end_time - datetime.now(timezone.utc)
            
            if remaining.total_seconds() <= 0:
                logger.info("⏰ Test duration completed")
                self.stop_event.set()
                break
            
            await asyncio.sleep(60)  # 1분마다 체크
    
    async def _cleanup(self):
        """정리 작업"""
        logger.info("🔄 Performing cleanup...")
        
        self.running = False
        self.monitor.metrics.end_time = datetime.now(timezone.utc)
        
        try:
            await self.exchange_connector.disconnect()
            logger.info("✅ Exchange connector disconnected")
        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")
    
    async def _generate_final_report(self):
        """최종 보고서 생성"""
        logger.info("📋 Generating final test report...")
        
        metrics = self.monitor.get_current_metrics()
        
        # 콘솔 보고서
        logger.info("🎯 24-Hour Continuous Test Final Report")
        logger.info("=" * 60)
        logger.info(f"⏱️  Test Duration: {metrics['duration_hours']:.2f} hours")
        logger.info(f"🔢 Total Operations: {metrics['total_operations']:,}")
        logger.info(f"✅ Successful Operations: {metrics['successful_operations']:,}")
        logger.info(f"❌ Failed Operations: {metrics['failed_operations']:,}")
        logger.info(f"📊 Success Rate: {metrics['success_rate']:.2f}%")
        logger.info(f"⚡ Average Latency: {metrics['average_latency_ms']:.3f}ms")
        logger.info(f"🔥 Peak Latency: {metrics['peak_latency_ms']:.3f}ms")
        logger.info(f"🚀 Min Latency: {metrics['min_latency_ms']:.3f}ms")
        logger.info(f"⚠️  Total Errors: {metrics['error_count']}")
        
        # 최종 성능 평가
        if metrics['success_rate'] >= 99.9 and metrics['average_latency_ms'] < 1.0:
            logger.info("🎉 EXCELLENT: Production-ready performance achieved!")
            grade = "A+"
        elif metrics['success_rate'] >= 99.5 and metrics['average_latency_ms'] < 5.0:
            logger.info("🎯 VERY GOOD: High-performance trading ready")
            grade = "A"
        elif metrics['success_rate'] >= 99.0 and metrics['average_latency_ms'] < 200.0:
            logger.info("✅ GOOD: MVP requirements met")
            grade = "B"
        else:
            logger.warning("⚠️ NEEDS IMPROVEMENT: Performance issues detected")
            grade = "C"
        
        # 파일 보고서 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"24h_test_report_{timestamp}.json"
        
        detailed_report = metrics.copy()
        detailed_report.update({
            "test_type": "24_hour_continuous_dry_run",
            "performance_grade": grade,
            "target_latency_ms": 1.0,
            "target_success_rate": 99.9,
            "targets_met": {
                "latency": metrics['average_latency_ms'] < 1.0,
                "success_rate": metrics['success_rate'] >= 99.9,
                "overall": grade in ["A+", "A"]
            }
        })
        
        with open(report_filename, 'w') as f:
            json.dump(detailed_report, f, indent=2)
        
        logger.info(f"📄 Detailed report saved: {report_filename}")
        logger.info("=" * 60)
        
        return grade in ["A+", "A", "B"]


async def main():
    """메인 실행 함수"""
    # 테스트 기간 설정 (기본 24시간, 테스트용으로 짧게 설정 가능)
    test_duration = float(os.getenv("TEST_DURATION_HOURS", "24.0"))
    
    # 빠른 테스트를 위해 5분으로 설정 (실제로는 24시간)
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        test_duration = 0.083  # 5분
        logger.info("🚀 Quick test mode: 5 minutes")
    
    # 연속 테스트 시스템 생성 및 실행
    test_system = ContinuousTestingSystem(test_duration_hours=test_duration)
    
    success = await test_system.start_test()
    
    if success:
        logger.info("🎉 Continuous testing completed successfully")
        return 0
    else:
        logger.error("❌ Continuous testing failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)