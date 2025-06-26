#!/usr/bin/env python3
"""
Circuit Breaker 패턴 테스트
Exchange Connector의 장애 처리 및 자동 복구 테스트
"""

import asyncio
import os
import sys
import logging
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.exchange_connector.main import CCXTExchangeConnector
from src.exchange_connector.interfaces import ExchangeConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CircuitBreakerTester:
    """Circuit Breaker 테스터"""
    
    def __init__(self, connector: CCXTExchangeConnector):
        self.connector = connector
        self.test_results = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'circuit_opens': 0,
            'circuit_recoveries': 0
        }
    
    async def test_normal_operation(self):
        """정상 작동 테스트"""
        logger.info("\n🔵 Testing Normal Operation...")
        
        for i in range(5):
            try:
                self.test_results['total_requests'] += 1
                ticker = await self.connector.get_ticker("BTC/USDT")
                
                if ticker > 0:
                    self.test_results['successful_requests'] += 1
                    logger.info(f"✅ Request {i+1}: Success (BTC price: ${ticker:.2f})")
                else:
                    self.test_results['failed_requests'] += 1
                    logger.warning(f"⚠️ Request {i+1}: Invalid response")
                    
            except Exception as e:
                self.test_results['failed_requests'] += 1
                logger.error(f"❌ Request {i+1}: Failed - {e}")
            
            await asyncio.sleep(0.5)
    
    async def test_failure_scenario(self):
        """장애 시나리오 테스트"""
        logger.info("\n🔴 Testing Failure Scenario...")
        
        # 임시로 잘못된 API 키 설정하여 실패 유도
        original_api_key = self.connector.config.api_key
        self.connector.config.api_key = "invalid_key"
        
        # 여러 번 실패시켜 Circuit Breaker 작동 확인
        for i in range(10):
            try:
                self.test_results['total_requests'] += 1
                
                # Circuit이 열려있는지 확인
                if hasattr(self.connector, '_circuit_breaker_open'):
                    if self.connector._circuit_breaker_open:
                        logger.warning(f"🔌 Request {i+1}: Circuit is OPEN")
                        self.test_results['circuit_opens'] += 1
                        continue
                
                ticker = await self.connector.get_ticker("BTC/USDT")
                self.test_results['successful_requests'] += 1
                logger.info(f"✅ Request {i+1}: Success")
                
            except Exception as e:
                self.test_results['failed_requests'] += 1
                
                # Circuit Breaker 상태 확인
                failures = getattr(self.connector, '_circuit_breaker_failures', 0)
                max_failures = getattr(self.connector, 'max_failures', 5)
                
                logger.error(f"❌ Request {i+1}: Failed (failures: {failures}/{max_failures})")
                
                if failures >= max_failures:
                    logger.warning("⚡ Circuit Breaker OPENED!")
                    self.test_results['circuit_opens'] += 1
            
            await asyncio.sleep(0.5)
        
        # API 키 복원
        self.connector.config.api_key = original_api_key
    
    async def test_recovery(self):
        """복구 시나리오 테스트"""
        logger.info("\n🟢 Testing Recovery Scenario...")
        
        # Circuit Breaker 타임아웃 대기
        timeout = getattr(self.connector, 'circuit_breaker_timeout', 300)
        logger.info(f"⏱️ Waiting for circuit breaker timeout ({timeout}s)...")
        
        # 데모를 위해 짧은 시간만 대기
        await asyncio.sleep(5)
        
        # 수동으로 Circuit 리셋 (테스트용)
        if hasattr(self.connector, '_circuit_breaker_open'):
            self.connector._circuit_breaker_open = False
            self.connector._circuit_breaker_failures = 0
            self.connector._circuit_breaker_opened_at = None
        
        # 복구 시도
        for i in range(5):
            try:
                self.test_results['total_requests'] += 1
                ticker = await self.connector.get_ticker("BTC/USDT")
                
                if ticker > 0:
                    self.test_results['successful_requests'] += 1
                    self.test_results['circuit_recoveries'] += 1
                    logger.info(f"✅ Recovery {i+1}: Success (BTC price: ${ticker:.2f})")
                    
            except Exception as e:
                self.test_results['failed_requests'] += 1
                logger.error(f"❌ Recovery {i+1}: Failed - {e}")
            
            await asyncio.sleep(0.5)
    
    def print_results(self):
        """테스트 결과 출력"""
        logger.info("\n📊 Circuit Breaker Test Results:")
        logger.info(f"- Total Requests: {self.test_results['total_requests']}")
        logger.info(f"- Successful: {self.test_results['successful_requests']}")
        logger.info(f"- Failed: {self.test_results['failed_requests']}")
        logger.info(f"- Circuit Opens: {self.test_results['circuit_opens']}")
        logger.info(f"- Recoveries: {self.test_results['circuit_recoveries']}")
        
        success_rate = (self.test_results['successful_requests'] / 
                       self.test_results['total_requests'] * 100 
                       if self.test_results['total_requests'] > 0 else 0)
        logger.info(f"- Success Rate: {success_rate:.1f}%")


async def test_rate_limiting():
    """Rate Limiting 테스트"""
    logger.info("\n⏱️ Testing Rate Limiting...")
    
    config = ExchangeConfig(
        exchange_name="binance",
        api_key=os.getenv("BINANCE_API_KEY", ""),
        api_secret=os.getenv("BINANCE_SECRET_KEY", ""),
        testnet=True
    )
    
    connector = CCXTExchangeConnector(config)
    
    try:
        await connector.connect()
        
        # 빠른 연속 요청으로 Rate Limit 테스트
        request_times = []
        
        for i in range(20):
            start_time = asyncio.get_event_loop().time()
            
            try:
                await connector.get_ticker("BTC/USDT")
                request_time = asyncio.get_event_loop().time() - start_time
                request_times.append(request_time)
                logger.info(f"Request {i+1}: {request_time*1000:.2f}ms")
                
            except Exception as e:
                logger.warning(f"Request {i+1}: Rate limited - {e}")
                await asyncio.sleep(1)  # Rate limit 대기
        
        # 통계
        if request_times:
            avg_time = sum(request_times) / len(request_times)
            logger.info(f"\n📊 Rate Limiting Statistics:")
            logger.info(f"- Average request time: {avg_time*1000:.2f}ms")
            logger.info(f"- Min time: {min(request_times)*1000:.2f}ms")
            logger.info(f"- Max time: {max(request_times)*1000:.2f}ms")
        
    finally:
        await connector.disconnect()


async def main():
    """메인 테스트 함수"""
    # Exchange Connector 생성
    config = ExchangeConfig(
        exchange_name="binance",
        api_key=os.getenv("BINANCE_API_KEY", ""),
        api_secret=os.getenv("BINANCE_SECRET_KEY", ""),
        testnet=True
    )
    
    connector = CCXTExchangeConnector(config)
    
    try:
        # 연결
        await connector.connect()
        logger.info("✅ Connector connected")
        
        # Circuit Breaker 테스터 생성
        tester = CircuitBreakerTester(connector)
        
        # 테스트 실행
        await tester.test_normal_operation()
        await tester.test_failure_scenario()
        await tester.test_recovery()
        
        # 결과 출력
        tester.print_results()
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        
    finally:
        await connector.disconnect()
        logger.info("🛑 Connector disconnected")
    
    # Rate Limiting 테스트
    await test_rate_limiting()


if __name__ == "__main__":
    asyncio.run(main())