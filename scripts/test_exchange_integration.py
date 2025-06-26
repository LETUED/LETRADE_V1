#!/usr/bin/env python3
"""
Exchange Connector 통합 테스트 스크립트

Mock과 실제 Exchange Connector의 통합을 테스트합니다.
실제 API 키 없이도 기본 기능을 확인할 수 있습니다.
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.exchange_connector.main import ExchangeConnector, HAS_CCXT
from src.core_engine.main import CoreEngine
from src.common.message_bus import MessageBus
from src.common.config import Config

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_exchange_connector_integration():
    """Exchange Connector 통합 테스트"""
    
    logger.info("=" * 60)
    logger.info("🚀 Exchange Connector Integration Test")
    logger.info("=" * 60)
    
    # Exchange Connector 설정
    exchange_config = {
        "default_exchange": "mock",
        "exchanges": {
            "mock": {
                "name": "mock",
                "type": "mock",
                "dry_run": True
            }
        }
    }
    
    # CCXT가 설치되어 있으면 Binance Testnet도 추가
    if HAS_CCXT:
        logger.info("✅ CCXT library detected - adding Binance testnet configuration")
        exchange_config["exchanges"]["binance_testnet"] = {
            "name": "binance",
            "type": "ccxt",
            "api_key": "test_api_key",  # Testnet에서는 가짜 키로도 일부 기능 테스트 가능
            "api_secret": "test_api_secret",
            "sandbox": True,
            "dry_run": True
        }
    
    # Exchange Connector Manager 생성
    connector_manager = ExchangeConnector(exchange_config)
    
    try:
        # 1. Exchange Connector 시작
        logger.info("\n📡 Starting Exchange Connector Manager...")
        success = await connector_manager.start()
        if success:
            logger.info("✅ Exchange Connector Manager started successfully")
            logger.info(f"  Available exchanges: {list(connector_manager.connectors.keys())}")
        else:
            logger.error("❌ Failed to start Exchange Connector Manager")
            return False
        
        # 2. 각 거래소 테스트
        for exchange_name in connector_manager.connectors.keys():
            logger.info(f"\n🔍 Testing {exchange_name} exchange...")
            
            connector = connector_manager.get_connector(exchange_name)
            
            # 시장 데이터 조회
            try:
                market_data = await connector.get_market_data("BTCUSDT")
                logger.info(f"  ✅ Market data: BTC price = ${market_data.price:.2f}")
            except Exception as e:
                logger.warning(f"  ⚠️ Market data failed: {e}")
            
            # 계정 잔액 조회 (Mock은 성공, 실제는 API 키 필요)
            try:
                balances = await connector.get_account_balance()
                logger.info(f"  ✅ Account balance fetched: {len(balances)} assets")
            except Exception as e:
                logger.warning(f"  ⚠️ Balance fetch failed: {e}")
        
        # 3. 헬스 체크
        logger.info("\n🏥 Performing health check on all exchanges...")
        health_status = await connector_manager.health_check()
        
        for exchange, status in health_status["exchanges"].items():
            logger.info(f"\n  {exchange}:")
            logger.info(f"    Connected: {status.get('connected', False)}")
            logger.info(f"    Healthy: {status.get('healthy', False)}")
            if 'error' in status:
                logger.info(f"    Error: {status['error']}")
        
        # 4. Message Bus 통합 테스트
        logger.info("\n📬 Testing Message Bus integration...")
        
        # 메시지 버스 설정
        message_bus = MessageBus(Config.get_message_bus_config())
        if await message_bus.connect():
            logger.info("✅ Message Bus connected")
            
            # Exchange Connector가 메시지를 받을 수 있도록 핸들러 등록
            async def handle_trade_command(topic: str, message: dict):
                logger.info(f"  Received trade command: {message}")
                
                # Mock 거래 실행
                connector = connector_manager.get_connector()
                from src.exchange_connector.main import OrderRequest, OrderSide, OrderType
                
                order_request = OrderRequest(
                    symbol=message.get('symbol', 'BTCUSDT'),
                    side=OrderSide.BUY if message.get('side') == 'buy' else OrderSide.SELL,
                    order_type=OrderType.LIMIT,
                    quantity=message.get('quantity', 0.001),
                    price=message.get('price', 50000.0)
                )
                
                order = await connector.place_order(order_request)
                logger.info(f"  ✅ Order placed: {order.id}")
            
            # 구독
            await message_bus.subscribe("commands.execute_trade", handle_trade_command)
            
            # 테스트 명령 발행
            test_command = {
                "symbol": "BTCUSDT",
                "side": "buy",
                "quantity": 0.001,
                "price": 48000.0,
                "strategy_id": "test_integration"
            }
            
            await message_bus.publish("letrade.commands", "execute_trade", test_command)
            
            # 메시지 처리 대기
            await asyncio.sleep(1)
            
            await message_bus.disconnect()
            logger.info("✅ Message Bus integration test completed")
        
        # 5. 정리
        logger.info("\n🧹 Cleaning up...")
        await connector_manager.stop()
        logger.info("✅ Exchange Connector Manager stopped")
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ Exchange Connector Integration Test PASSED")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        
        # 정리
        try:
            await connector_manager.stop()
        except:
            pass
            
        return False


async def test_strategy_to_exchange_flow():
    """전략에서 거래소까지의 전체 플로우 테스트"""
    
    logger.info("\n" + "=" * 60)
    logger.info("🔄 Testing Strategy to Exchange Flow")
    logger.info("=" * 60)
    
    # 설정
    config = {
        "exchange_connector": {
            "default_exchange": "mock",
            "exchanges": {
                "mock": {
                    "name": "mock",
                    "type": "mock",
                    "dry_run": True
                }
            }
        },
        "message_bus": Config.get_message_bus_config()
    }
    
    try:
        # 컴포넌트 초기화
        message_bus = MessageBus(config["message_bus"])
        exchange_connector = ExchangeConnector(config["exchange_connector"])
        
        # 시작
        await message_bus.connect()
        await exchange_connector.start()
        
        logger.info("✅ Components initialized")
        
        # 플로우 시뮬레이션
        # 1. Strategy Worker가 신호 생성
        strategy_signal = {
            "strategy_id": 1,
            "symbol": "BTCUSDT",
            "side": "buy",
            "signal_price": 49000.0,
            "stop_loss_price": 47000.0,
            "confidence": 0.85
        }
        
        logger.info("\n1️⃣ Strategy signal generated:")
        logger.info(f"  {strategy_signal}")
        
        # 2. Capital Manager 시뮬레이션 (실제로는 별도 서비스)
        capital_allocation = {
            "order_id": "cap_mgr_12345",
            "symbol": "BTCUSDT",
            "side": "buy",
            "quantity": 0.002,  # Capital Manager가 계산한 수량
            "price": 49000.0,
            "order_type": "limit"
        }
        
        logger.info("\n2️⃣ Capital Manager approved:")
        logger.info(f"  Allocated quantity: {capital_allocation['quantity']} BTC")
        
        # 3. Exchange Connector가 주문 실행
        from src.exchange_connector.main import OrderRequest, OrderSide, OrderType
        
        connector = exchange_connector.get_connector()
        order_request = OrderRequest(
            symbol=capital_allocation["symbol"],
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=capital_allocation["quantity"],
            price=capital_allocation["price"]
        )
        
        order = await connector.place_order(order_request)
        
        logger.info("\n3️⃣ Order executed:")
        logger.info(f"  Order ID: {order.id}")
        logger.info(f"  Status: {order.status.value}")
        
        # 4. 이벤트 발행 (실제로는 Exchange Connector가 발행)
        trade_event = {
            "event_type": "trade_executed",
            "order_id": order.id,
            "symbol": order.symbol,
            "side": order.side.value,
            "quantity": order.quantity,
            "price": order.price,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await message_bus.publish("letrade.events", "trade_executed", trade_event)
        
        logger.info("\n4️⃣ Trade event published")
        
        # 정리
        await exchange_connector.stop()
        await message_bus.disconnect()
        
        logger.info("\n✅ Strategy to Exchange flow test completed successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Flow test failed: {e}")
        return False


async def main():
    """메인 실행 함수"""
    
    # 1. Exchange Connector 통합 테스트
    integration_success = await test_exchange_connector_integration()
    
    # 2. 전략-거래소 플로우 테스트
    flow_success = await test_strategy_to_exchange_flow()
    
    # 결과 요약
    logger.info("\n" + "=" * 60)
    logger.info("📊 Test Summary")
    logger.info("=" * 60)
    logger.info(f"Exchange Integration: {'✅ PASSED' if integration_success else '❌ FAILED'}")
    logger.info(f"Strategy Flow: {'✅ PASSED' if flow_success else '❌ FAILED'}")
    logger.info("=" * 60)
    
    # API 키 설정 안내
    if not Config.BINANCE_API_KEY:
        logger.info("\n💡 To test with real Binance API:")
        logger.info("  1. Get API keys from https://testnet.binance.vision/")
        logger.info("  2. Set in .env file:")
        logger.info("     BINANCE_API_KEY=your_testnet_api_key")
        logger.info("     BINANCE_API_SECRET=your_testnet_api_secret")
        logger.info("  3. Run: python scripts/test_binance_connection.py")
    
    return 0 if (integration_success and flow_success) else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)