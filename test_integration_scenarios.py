#!/usr/bin/env python3
"""
통합 테스트 시나리오 모음

전체 시스템의 다양한 시나리오를 테스트합니다:
- 정상 거래 흐름
- 위험 관리 시나리오
- 에러 복구 시나리오
- 부하 테스트 시나리오
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Dict, Any, List

# 프로젝트 루트를 sys.path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core_engine.main import CoreEngine
from src.capital_manager.main import CapitalManager
from src.common.message_bus import create_message_bus
from src.strategies.base_strategy import StrategyConfig

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestMetrics:
    """테스트 메트릭 수집"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.total_messages = 0
        self.successful_trades = 0
        self.rejected_trades = 0
        self.errors = []
        self.response_times = []
    
    def start(self):
        self.start_time = time.time()
    
    def end(self):
        self.end_time = time.time()
    
    def add_message(self):
        self.total_messages += 1
    
    def add_successful_trade(self):
        self.successful_trades += 1
    
    def add_rejected_trade(self):
        self.rejected_trades += 1
    
    def add_error(self, error: str):
        self.errors.append(error)
    
    def add_response_time(self, response_time: float):
        self.response_times.append(response_time)
    
    def get_summary(self) -> Dict[str, Any]:
        duration = self.end_time - self.start_time if self.end_time else 0
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        
        return {
            "duration_seconds": duration,
            "total_messages": self.total_messages,
            "successful_trades": self.successful_trades,
            "rejected_trades": self.rejected_trades,
            "total_errors": len(self.errors),
            "messages_per_second": self.total_messages / duration if duration > 0 else 0,
            "success_rate": self.successful_trades / (self.successful_trades + self.rejected_trades) if (self.successful_trades + self.rejected_trades) > 0 else 0,
            "average_response_time_ms": avg_response_time * 1000,
            "errors": self.errors[:5]  # 처음 5개 에러만
        }


class MockExchangeConnector:
    """Mock Exchange Connector with metrics"""
    
    def __init__(self, message_bus, metrics: TestMetrics):
        self.message_bus = message_bus
        self.metrics = metrics
        self.executed_trades = []
        self.failure_rate = 0.0  # 실패율 시뮬레이션
    
    async def start(self):
        await self.message_bus.subscribe("trade_commands", self._handle_trade_command)
        logger.info("Mock Exchange Connector started")
    
    def set_failure_rate(self, rate: float):
        """실패율 설정 (0.0 = 실패 없음, 1.0 = 100% 실패)"""
        self.failure_rate = rate
    
    async def _handle_trade_command(self, message: Dict[str, Any]):
        """거래 명령 처리"""
        request_time = time.time()
        
        try:
            payload = message.get("payload", {})
            trade_command = payload.get("trade_command", {})
            
            logger.info(f"Executing trade: {trade_command}")
            
            # 실패 시뮬레이션
            import random
            if random.random() < self.failure_rate:
                raise Exception("Simulated exchange failure")
            
            # Mock 거래 실행
            execution_result = {
                "order_id": f"order_{len(self.executed_trades) + 1}",
                "symbol": trade_command.get("symbol", "BTC/USDT"),
                "side": trade_command.get("side", "buy"),
                "filled_quantity": trade_command.get("quantity", 0),
                "average_price": 50000.0 + random.uniform(-1000, 1000),  # 가격 변동
                "status": "filled",
                "fees": 5.0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            self.executed_trades.append(execution_result)
            self.metrics.add_successful_trade()
            
            # 거래 실행 이벤트 발송
            event_message = {
                "routing_key": "events.trade_executed",
                "payload": {
                    "strategy_id": payload.get("strategy_id"),
                    **execution_result
                }
            }
            
            # 응답 시간 측정
            response_time = time.time() - request_time
            self.metrics.add_response_time(response_time)
            
            logger.info(f"Trade executed successfully: {execution_result['order_id']} (response time: {response_time*1000:.1f}ms)")
            
        except Exception as e:
            self.metrics.add_error(str(e))
            logger.error(f"Failed to execute trade: {e}")


async def test_normal_trading_flow(metrics: TestMetrics) -> bool:
    """정상 거래 흐름 테스트"""
    logger.info("🔄 정상 거래 흐름 테스트")
    
    config = {
        "host": "localhost", "port": 5672,
        "username": "letrade_user", "password": "letrade_password", "virtual_host": "/"
    }
    
    try:
        message_bus = await create_message_bus(config)
        
        # Capital Manager 및 Exchange Connector 설정
        capital_manager = CapitalManager(
            config={"risk_parameters": {"max_position_size_percent": 5.0}},
            message_bus=message_bus
        )
        exchange_connector = MockExchangeConnector(message_bus, metrics)
        
        await exchange_connector.start()
        await capital_manager.start()
        
        # 여러 거래 신호 발송
        for i in range(5):
            trade_proposal = {
                "strategy_id": f"test_strategy_{i}",
                "signal_data": {
                    "signal_type": "golden_cross" if i % 2 == 0 else "death_cross",
                    "symbol": "BTC/USDT",
                    "current_price": 50000.0 + (i * 100),
                    "quantity": 0.01 + (i * 0.005),
                    "signal_strength": 0.7 + (i * 0.05)
                },
                "correlation_id": f"test_{i}"
            }
            
            await message_bus.publish("letrade.requests", "request.capital.allocation", trade_proposal)
            metrics.add_message()
            
            # 메시지 간 간격
            await asyncio.sleep(0.5)
        
        # 처리 대기
        await asyncio.sleep(5)
        
        # 정리
        await capital_manager.stop()
        await message_bus.disconnect()
        
        # 성공 조건: 거래가 실행되었고 에러가 적음
        return len(exchange_connector.executed_trades) > 0 and len(metrics.errors) < 3
        
    except Exception as e:
        metrics.add_error(str(e))
        logger.error(f"정상 거래 흐름 테스트 실패: {e}")
        return False


async def test_risk_management_scenarios(metrics: TestMetrics) -> bool:
    """위험 관리 시나리오 테스트"""
    logger.info("⚠️  위험 관리 시나리오 테스트")
    
    config = {
        "host": "localhost", "port": 5672,
        "username": "letrade_user", "password": "letrade_password", "virtual_host": "/"
    }
    
    try:
        message_bus = await create_message_bus(config)
        
        # 엄격한 위험 관리 설정
        capital_manager = CapitalManager(
            config={
                "risk_parameters": {
                    "max_position_size_percent": 1.0,  # 매우 낮음
                    "max_daily_loss_percent": 0.5,
                    "min_trade_amount": 100.0,
                    "max_trade_amount": 500.0
                }
            },
            message_bus=message_bus
        )
        
        exchange_connector = MockExchangeConnector(message_bus, metrics)
        await exchange_connector.start()
        await capital_manager.start()
        
        # 위험한 거래들 시도
        risky_trades = [
            {"quantity": 1.0, "reason": "거대한 포지션"},
            {"quantity": 0.5, "reason": "큰 포지션"},
            {"quantity": 0.001, "price": 10.0, "reason": "소액 거래"}  # min_trade_amount 미달
        ]
        
        initial_trades = len(exchange_connector.executed_trades)
        
        for i, trade in enumerate(risky_trades):
            trade_proposal = {
                "strategy_id": f"risky_strategy_{i}",
                "signal_data": {
                    "signal_type": "golden_cross",
                    "symbol": "BTC/USDT",
                    "current_price": trade.get("price", 50000.0),
                    "quantity": trade["quantity"],
                    "signal_strength": 0.9
                },
                "correlation_id": f"risk_test_{i}"
            }
            
            await message_bus.publish("letrade.requests", "request.capital.allocation", trade_proposal)
            metrics.add_message()
            logger.info(f"위험 거래 {i+1} 시도: {trade['reason']}")
        
        await asyncio.sleep(5)
        
        # 정리
        await capital_manager.stop()
        await message_bus.disconnect()
        
        # 성공 조건: 위험한 거래들이 대부분 차단됨
        executed_trades = len(exchange_connector.executed_trades) - initial_trades
        success = executed_trades <= 1  # 최대 1건만 허용
        
        logger.info(f"위험 관리 결과: {executed_trades}/3 거래 실행됨")
        return success
        
    except Exception as e:
        metrics.add_error(str(e))
        logger.error(f"위험 관리 테스트 실패: {e}")
        return False


async def test_error_recovery_scenarios(metrics: TestMetrics) -> bool:
    """에러 복구 시나리오 테스트"""
    logger.info("🔄 에러 복구 시나리오 테스트")
    
    config = {
        "host": "localhost", "port": 5672,
        "username": "letrade_user", "password": "letrade_password", "virtual_host": "/"
    }
    
    try:
        message_bus = await create_message_bus(config)
        
        capital_manager = CapitalManager(message_bus=message_bus)
        exchange_connector = MockExchangeConnector(message_bus, metrics)
        
        # 50% 실패율 설정
        exchange_connector.set_failure_rate(0.5)
        
        await exchange_connector.start()
        await capital_manager.start()
        
        # 여러 거래 시도 (일부는 실패할 것)
        for i in range(10):
            trade_proposal = {
                "strategy_id": f"recovery_test_{i}",
                "signal_data": {
                    "signal_type": "golden_cross",
                    "symbol": "BTC/USDT",
                    "current_price": 50000.0,
                    "quantity": 0.01,
                    "signal_strength": 0.8
                },
                "correlation_id": f"recovery_{i}"
            }
            
            await message_bus.publish("letrade.requests", "request.capital.allocation", trade_proposal)
            metrics.add_message()
            
            await asyncio.sleep(0.2)
        
        await asyncio.sleep(5)
        
        # 정리
        await capital_manager.stop()
        await message_bus.disconnect()
        
        # 성공 조건: 일부 거래는 성공하고, 시스템이 계속 작동함
        success = len(exchange_connector.executed_trades) > 2 and len(metrics.errors) > 0
        
        logger.info(f"에러 복구 결과: {len(exchange_connector.executed_trades)}건 성공, {len(metrics.errors)}개 에러")
        return success
        
    except Exception as e:
        metrics.add_error(str(e))
        logger.error(f"에러 복구 테스트 실패: {e}")
        return False


async def test_load_scenarios(metrics: TestMetrics) -> bool:
    """부하 테스트 시나리오"""
    logger.info("🚀 부하 테스트 시나리오")
    
    config = {
        "host": "localhost", "port": 5672,
        "username": "letrade_user", "password": "letrade_password", "virtual_host": "/"
    }
    
    try:
        message_bus = await create_message_bus(config)
        
        capital_manager = CapitalManager(message_bus=message_bus)
        exchange_connector = MockExchangeConnector(message_bus, metrics)
        
        await exchange_connector.start()
        await capital_manager.start()
        
        # 동시에 많은 메시지 발송
        start_time = time.time()
        
        # 50개 메시지를 빠르게 발송
        tasks = []
        for i in range(50):
            trade_proposal = {
                "strategy_id": f"load_test_{i}",
                "signal_data": {
                    "signal_type": "golden_cross",
                    "symbol": "BTC/USDT",
                    "current_price": 50000.0 + (i % 10) * 10,
                    "quantity": 0.005 + (i % 5) * 0.001,
                    "signal_strength": 0.6 + (i % 10) * 0.04
                },
                "correlation_id": f"load_{i}"
            }
            
            task = message_bus.publish("letrade.requests", "request.capital.allocation", trade_proposal)
            tasks.append(task)
            metrics.add_message()
        
        # 모든 메시지 발송 대기
        await asyncio.gather(*tasks)
        
        # 처리 완료 대기
        await asyncio.sleep(10)
        
        processing_time = time.time() - start_time
        
        # 정리
        await capital_manager.stop()
        await message_bus.disconnect()
        
        # 성공 조건: 대부분의 메시지가 처리되고, 처리 시간이 합리적
        throughput = len(exchange_connector.executed_trades) / processing_time
        success = len(exchange_connector.executed_trades) > 30 and throughput > 2.0  # 초당 2건 이상
        
        logger.info(f"부하 테스트 결과: {len(exchange_connector.executed_trades)}건 처리, 처리율: {throughput:.1f} TPS")
        return success
        
    except Exception as e:
        metrics.add_error(str(e))
        logger.error(f"부하 테스트 실패: {e}")
        return False


async def run_integration_scenarios():
    """통합 테스트 시나리오 실행"""
    logger.info("🧪 통합 테스트 시나리오 시작")
    
    metrics = TestMetrics()
    metrics.start()
    
    # 테스트 시나리오들
    scenarios = [
        ("정상 거래 흐름", test_normal_trading_flow),
        ("위험 관리", test_risk_management_scenarios),
        ("에러 복구", test_error_recovery_scenarios),
        ("부하 테스트", test_load_scenarios)
    ]
    
    results = {}
    
    try:
        for scenario_name, test_func in scenarios:
            logger.info(f"\n{'='*60}")
            logger.info(f"시나리오: {scenario_name}")
            logger.info(f"{'='*60}")
            
            scenario_start = time.time()
            
            try:
                result = await test_func(metrics)
                results[scenario_name] = result
                
                scenario_time = time.time() - scenario_start
                status = "✅ 성공" if result else "❌ 실패"
                logger.info(f"{scenario_name}: {status} (소요시간: {scenario_time:.1f}초)")
                
            except Exception as e:
                results[scenario_name] = False
                metrics.add_error(f"{scenario_name}: {str(e)}")
                logger.error(f"{scenario_name} 실행 중 오류: {e}")
            
            # 시나리오 간 대기
            await asyncio.sleep(2)
    
    finally:
        metrics.end()
    
    # 결과 요약
    logger.info(f"\n{'='*60}")
    logger.info("📊 통합 테스트 결과 요약")
    logger.info(f"{'='*60}")
    
    total_scenarios = len(scenarios)
    passed_scenarios = sum(1 for result in results.values() if result)
    
    for scenario_name, result in results.items():
        status = "✅ 성공" if result else "❌ 실패"
        logger.info(f"{scenario_name}: {status}")
    
    logger.info(f"\n📈 성능 메트릭:")
    summary = metrics.get_summary()
    for key, value in summary.items():
        if key != "errors":
            logger.info(f"  {key}: {value}")
    
    if summary["errors"]:
        logger.info(f"\n⚠️  주요 에러:")
        for error in summary["errors"]:
            logger.info(f"  - {error}")
    
    success_rate = passed_scenarios / total_scenarios
    logger.info(f"\n🎯 전체 결과: {passed_scenarios}/{total_scenarios} 시나리오 성공 ({success_rate:.1%})")
    
    if success_rate >= 0.75:
        logger.info("✅ 통합 테스트 전체 성공!")
        return True
    else:
        logger.info("❌ 통합 테스트 일부 실패")
        return False


if __name__ == "__main__":
    asyncio.run(run_integration_scenarios())