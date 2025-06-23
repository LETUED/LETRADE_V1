#!/usr/bin/env python3
"""
거래 제안 메시지 흐름 테스트

Strategy Worker → Capital Manager → Exchange Connector 
메시지 흐름을 테스트합니다.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any

# 프로젝트 루트를 sys.path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.capital_manager.main import CapitalManager, TradeRequest
from src.common.message_bus import create_message_bus
from src.strategies.ma_crossover import MAcrossoverStrategy
from src.strategies.base_strategy import StrategyConfig

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockExchangeConnector:
    """Mock Exchange Connector for testing"""
    
    def __init__(self, message_bus):
        self.message_bus = message_bus
        self.executed_trades = []
    
    async def start(self):
        """Exchange Connector 시작"""
        await self.message_bus.subscribe("trade_commands", self._handle_trade_command)
        logger.info("Mock Exchange Connector started")
    
    async def _handle_trade_command(self, message: Dict[str, Any]):
        """거래 명령 처리"""
        try:
            payload = message.get("payload", {})
            trade_command = payload.get("trade_command", {})
            
            logger.info(f"Executing trade: {trade_command}")
            
            # Mock 거래 실행
            execution_result = {
                "order_id": f"order_{len(self.executed_trades) + 1}",
                "symbol": trade_command.get("symbol", "BTC/USDT"),
                "side": trade_command.get("side", "buy"),
                "filled_quantity": trade_command.get("quantity", 0),
                "average_price": 50000.0,  # Mock price
                "status": "filled",
                "fees": 5.0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            self.executed_trades.append(execution_result)
            
            # 거래 실행 이벤트 발송
            event_message = {
                "routing_key": "events.trade_executed",
                "payload": {
                    "strategy_id": payload.get("strategy_id"),
                    **execution_result
                }
            }
            
            await self.message_bus.publish(event_message)
            
            logger.info(f"Trade executed successfully: {execution_result['order_id']}")
            
        except Exception as e:
            logger.error(f"Failed to execute trade: {e}")


async def test_trade_proposal_flow():
    """거래 제안 흐름 테스트"""
    logger.info("=" * 60)
    logger.info("🔄 거래 제안 메시지 흐름 테스트")
    logger.info("=" * 60)
    
    # Message Bus 설정
    config = {
        "host": "localhost",
        "port": 5672,
        "username": "letrade_user",
        "password": "letrade_password",
        "virtual_host": "/"
    }
    
    try:
        # 1. Message Bus 초기화
        logger.info("1. Message Bus 초기화")
        message_bus = await create_message_bus(config)
        
        # 2. Capital Manager 초기화
        logger.info("2. Capital Manager 초기화")
        capital_manager = CapitalManager(
            config={
                "risk_parameters": {
                    "max_position_size_percent": 5.0,
                    "max_daily_loss_percent": 2.0,
                    "min_trade_amount": 10.0,
                    "max_trade_amount": 1000.0
                }
            },
            message_bus=message_bus
        )
        
        # 3. Mock Exchange Connector 초기화
        logger.info("3. Mock Exchange Connector 초기화")
        exchange_connector = MockExchangeConnector(message_bus)
        await exchange_connector.start()
        
        # 4. Capital Manager 시작
        logger.info("4. Capital Manager 시작")
        await capital_manager.start()
        
        # 5. 거래 제안 메시지 생성 및 발송
        logger.info("5. 거래 제안 메시지 발송")
        
        # Golden Cross 신호 시뮬레이션
        trade_proposal = {
            "routing_key": "request.capital.allocation",
            "payload": {
                "strategy_id": "test_ma_strategy",
                "signal_data": {
                    "signal_type": "golden_cross",
                    "symbol": "BTC/USDT",
                    "current_price": 50000.0,
                    "signal_strength": 0.75,
                    "fast_ma": 49800.0,
                    "slow_ma": 49500.0,
                    "quantity": 0.02,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "correlation_id": "test_001"
            }
        }
        
        # 메시지 구조 분해
        routing_key = trade_proposal["routing_key"]
        payload = trade_proposal["payload"]
        
        # 적절한 exchange 선택
        exchange_name = "letrade.requests"  # Capital Manager 요청용 exchange
        
        await message_bus.publish(exchange_name, routing_key, payload)
        logger.info("✅ 거래 제안 메시지 발송 완료")
        
        # 6. 메시지 처리 대기
        logger.info("6. 메시지 처리 대기 (10초)")
        await asyncio.sleep(10)
        
        # 7. 결과 확인
        logger.info("7. 거래 실행 결과 확인")
        logger.info(f"실행된 거래 수: {len(exchange_connector.executed_trades)}")
        
        for i, trade in enumerate(exchange_connector.executed_trades, 1):
            logger.info(f"거래 {i}: {trade}")
        
        # 8. Death Cross 신호 테스트
        logger.info("8. Death Cross 신호 테스트")
        
        death_cross_proposal = {
            "routing_key": "request.capital.allocation",
            "payload": {
                "strategy_id": "test_ma_strategy",
                "signal_data": {
                    "signal_type": "death_cross",
                    "symbol": "BTC/USDT",
                    "current_price": 49000.0,
                    "signal_strength": 0.65,
                    "fast_ma": 49200.0,
                    "slow_ma": 49500.0,
                    "quantity": 0.015,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "correlation_id": "test_002"
            }
        }
        
        # Death Cross 메시지 발송
        routing_key2 = death_cross_proposal["routing_key"]
        payload2 = death_cross_proposal["payload"]
        
        await message_bus.publish(exchange_name, routing_key2, payload2)
        logger.info("✅ Death Cross 신호 발송 완료")
        
        # 9. 두 번째 처리 대기
        logger.info("9. 두 번째 메시지 처리 대기 (10초)")
        await asyncio.sleep(10)
        
        # 10. 최종 결과
        logger.info("10. 최종 거래 실행 결과")
        logger.info(f"총 실행된 거래 수: {len(exchange_connector.executed_trades)}")
        
        # 11. Capital Manager 상태 확인
        logger.info("11. Capital Manager 상태 확인")
        health_status = await capital_manager.health_check()
        logger.info(f"Capital Manager 상태: {json.dumps(health_status, indent=2)}")
        
        # 12. 포트폴리오 메트릭 확인
        logger.info("12. 포트폴리오 메트릭 확인")
        portfolio_metrics = await capital_manager.get_portfolio_metrics()
        logger.info(f"포트폴리오 메트릭: {json.dumps(portfolio_metrics.to_dict(), indent=2)}")
        
        # 정리
        await capital_manager.stop()
        await message_bus.disconnect()
        
        return len(exchange_connector.executed_trades) > 0
        
    except Exception as e:
        logger.error(f"거래 제안 흐름 테스트 중 오류: {e}")
        return False


async def test_risk_rejection_scenario():
    """위험 거부 시나리오 테스트"""
    logger.info("\n" + "=" * 60)
    logger.info("⚠️  위험 거부 시나리오 테스트")
    logger.info("=" * 60)
    
    config = {
        "host": "localhost",
        "port": 5672,
        "username": "letrade_user",
        "password": "letrade_password",
        "virtual_host": "/"
    }
    
    try:
        # Message Bus 초기화
        message_bus = await create_message_bus(config)
        
        # 매우 엄격한 위험 파라미터로 Capital Manager 설정
        capital_manager = CapitalManager(
            config={
                "risk_parameters": {
                    "max_position_size_percent": 0.1,  # 매우 낮음
                    "max_daily_loss_percent": 0.1,     # 매우 낮음
                    "min_trade_amount": 1000.0,        # 매우 높음
                    "max_trade_amount": 2000.0
                }
            },
            message_bus=message_bus
        )
        
        # Mock Exchange Connector
        exchange_connector = MockExchangeConnector(message_bus)
        await exchange_connector.start()
        
        await capital_manager.start()
        
        # 거대한 거래 제안 (거부될 것)
        large_trade_proposal = {
            "routing_key": "request.capital.allocation",
            "payload": {
                "strategy_id": "test_risky_strategy",
                "signal_data": {
                    "signal_type": "golden_cross",
                    "symbol": "BTC/USDT",
                    "current_price": 50000.0,
                    "signal_strength": 0.95,
                    "quantity": 1.0,  # 매우 큰 수량
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "correlation_id": "risk_test_001"
            }
        }
        
        # 위험 거래 메시지 발송
        routing_key3 = large_trade_proposal["routing_key"]
        payload3 = large_trade_proposal["payload"]
        exchange_name = "letrade.requests"
        
        await message_bus.publish(exchange_name, routing_key3, payload3)
        logger.info("✅ 위험한 거래 제안 발송 완료")
        
        # 처리 대기
        await asyncio.sleep(8)
        
        # 결과 확인 (거래가 실행되지 않아야 함)
        logger.info(f"실행된 거래 수: {len(exchange_connector.executed_trades)}")
        
        if len(exchange_connector.executed_trades) == 0:
            logger.info("✅ 위험 거부 테스트 성공: 위험한 거래가 차단됨")
            result = True
        else:
            logger.error("❌ 위험 거부 테스트 실패: 위험한 거래가 실행됨")
            result = False
        
        # 정리
        await capital_manager.stop()
        await message_bus.disconnect()
        
        return result
        
    except Exception as e:
        logger.error(f"위험 거부 시나리오 테스트 중 오류: {e}")
        return False


async def main():
    """메인 테스트 실행"""
    logger.info("🧪 거래 제안 메시지 흐름 통합 테스트 시작")
    
    results = []
    
    try:
        # 1. 정상 거래 흐름 테스트
        logger.info("테스트 1: 정상 거래 제안 흐름")
        result1 = await test_trade_proposal_flow()
        results.append(("정상 거래 흐름", result1))
        
        # 잠시 대기
        await asyncio.sleep(3)
        
        # 2. 위험 거부 시나리오 테스트
        logger.info("테스트 2: 위험 거부 시나리오")
        result2 = await test_risk_rejection_scenario()
        results.append(("위험 거부 시나리오", result2))
        
        # 결과 요약
        logger.info("\n" + "=" * 60)
        logger.info("📊 테스트 결과 요약")
        logger.info("=" * 60)
        
        for test_name, success in results:
            status = "✅ 성공" if success else "❌ 실패"
            logger.info(f"{test_name}: {status}")
        
        all_passed = all(result for _, result in results)
        logger.info(f"\n🎯 전체 테스트 결과: {'✅ 모든 테스트 성공!' if all_passed else '❌ 일부 테스트 실패'}")
        
    except Exception as e:
        logger.error(f"테스트 실행 중 예상치 못한 오류: {e}")


if __name__ == "__main__":
    asyncio.run(main())