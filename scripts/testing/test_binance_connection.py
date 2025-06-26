#!/usr/bin/env python3
"""
Binance API 연결 테스트 스크립트

실제 Binance API와의 연결을 테스트하고 기본 기능을 확인합니다.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.exchange_connector.main import create_exchange_connector, HAS_CCXT
from src.exchange_connector.interfaces import ExchangeConfig, OrderRequest, OrderSide, OrderType
from src.common.config import Config

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_binance_connection():
    """Binance API 연결 테스트"""
    
    # CCXT 라이브러리 확인
    if not HAS_CCXT:
        logger.error("❌ CCXT library not installed. Please run: pip install ccxt")
        return False
    
    logger.info("=" * 60)
    logger.info("🚀 Starting Binance API Connection Test")
    logger.info("=" * 60)
    
    # 환경 변수에서 API 키 로드
    api_key = os.getenv("BINANCE_API_KEY", Config.BINANCE_API_KEY)
    api_secret = os.getenv("BINANCE_API_SECRET", Config.BINANCE_API_SECRET)
    use_testnet = os.getenv("BINANCE_TESTNET", "true").lower() == "true"
    
    if not api_key or not api_secret or api_key == "":
        logger.error("❌ Binance API credentials not found in environment variables")
        logger.info("Please set BINANCE_API_KEY and BINANCE_API_SECRET")
        return False
    
    # Exchange 설정
    exchange_config = {
        'api_key': api_key,
        'api_secret': api_secret,
        'sandbox': use_testnet,  # Testnet 사용
        'rate_limit': 1200,
        'timeout': 30
    }
    
    try:
        # Exchange Connector 생성
        logger.info(f"Creating Binance connector (testnet: {use_testnet})...")
        connector = create_exchange_connector('binance', exchange_config, use_ccxt=True)
        
        # 1. 연결 테스트
        logger.info("\n📡 Testing connection...")
        connected = await connector.connect()
        if connected:
            logger.info("✅ Successfully connected to Binance")
        else:
            logger.error("❌ Failed to connect to Binance")
            return False
        
        # 2. 계정 잔액 조회
        logger.info("\n💰 Fetching account balance...")
        try:
            balances = await connector.get_account_balance()
            logger.info(f"✅ Account balances fetched: {len(balances)} assets")
            
            # 주요 자산 표시
            for asset in ['USDT', 'BTC', 'ETH', 'BNB']:
                if asset in balances:
                    balance = balances[asset]
                    if balance.total > 0:
                        logger.info(f"  {asset}: {balance.total:.8f} (free: {balance.free:.8f}, locked: {balance.locked:.8f})")
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch balance (might need real API keys): {e}")
        
        # 3. 시장 데이터 조회
        logger.info("\n📊 Fetching market data...")
        symbol = 'BTC/USDT'
        market_data = await connector.get_market_data(symbol, timeframe='1h', limit=5)
        if market_data:
            logger.info(f"✅ Market data fetched for {symbol}: {len(market_data)} candles")
            latest = market_data[-1]
            logger.info(f"  Latest price: ${latest.close:.2f}")
            logger.info(f"  24h volume: {latest.volume:.2f}")
            logger.info(f"  Timestamp: {latest.timestamp}")
        
        # 4. 오픈 주문 조회
        logger.info("\n📋 Fetching open orders...")
        try:
            open_orders = await connector.get_open_orders()
            logger.info(f"✅ Open orders: {len(open_orders)}")
            for order in open_orders[:5]:  # 최대 5개만 표시
                logger.info(f"  Order {order.order_id}: {order.symbol} {order.side} {order.amount} @ {order.price}")
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch open orders: {e}")
        
        # 5. 헬스 체크
        logger.info("\n🏥 Performing health check...")
        health = await connector.health_check()
        logger.info(f"✅ Health check completed:")
        logger.info(f"  Status: {health.get('status', 'unknown')}")
        logger.info(f"  Response time: {health.get('response_time_ms', 'N/A')}ms")
        logger.info(f"  Circuit breaker: {'Open' if health.get('circuit_breaker_open') else 'Closed'}")
        
        # 6. WebSocket 스트리밍 테스트 (선택적)
        if hasattr(connector.exchange, 'watch_ohlcv'):
            logger.info("\n📡 Testing WebSocket streaming...")
            
            # 콜백 함수 정의
            def on_market_data(data):
                logger.info(f"  Streaming: {data.symbol} - Price: ${data.close:.2f} at {data.timestamp}")
            
            # 스트리밍 구독
            subscribed = await connector.subscribe_market_data(['BTC/USDT'], on_market_data)
            if subscribed:
                logger.info("✅ WebSocket streaming subscribed")
                logger.info("  Waiting for 5 seconds to receive data...")
                await asyncio.sleep(5)
            else:
                logger.info("⚠️ WebSocket streaming not available")
        
        # 7. 연결 종료
        logger.info("\n🔌 Disconnecting...")
        await connector.disconnect()
        logger.info("✅ Disconnected successfully")
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ Binance API test completed successfully!")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_mock_trading():
    """Mock 거래 테스트 (실제 거래 없이)"""
    logger.info("\n" + "=" * 60)
    logger.info("🎭 Testing Mock Trading Flow")
    logger.info("=" * 60)
    
    # Mock Exchange 사용
    mock_config = {
        'name': 'mock',
        'type': 'mock',
        'dry_run': True
    }
    
    connector = create_exchange_connector('mock', mock_config, use_ccxt=False)
    
    try:
        # 연결
        await connector.connect()
        logger.info("✅ Connected to Mock Exchange")
        
        # 잔액 확인
        balances = await connector.get_account_balance()
        logger.info(f"Initial USDT balance: {balances['USDT'].free}")
        
        # Mock 주문 생성
        from src.exchange_connector.main import OrderRequest as OldOrderRequest, OrderSide as OldOrderSide, OrderType as OldOrderType
        
        order_request = OldOrderRequest(
            symbol='BTC/USDT',
            side=OldOrderSide.BUY,
            order_type=OldOrderType.LIMIT,
            quantity=0.001,
            price=45000.0
        )
        
        # 주문 실행
        order = await connector.place_order(order_request)
        logger.info(f"✅ Mock order placed: {order.id}")
        logger.info(f"  Symbol: {order.symbol}")
        logger.info(f"  Side: {order.side.value}")
        logger.info(f"  Quantity: {order.quantity}")
        logger.info(f"  Price: {order.price}")
        
        # 주문 상태 확인
        order_status = await connector.get_order_status(order.symbol, order.id)
        logger.info(f"Order status: {order_status.status.value}")
        
        # 연결 종료
        await connector.disconnect()
        logger.info("✅ Mock trading test completed")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Mock trading test failed: {e}")
        return False


async def main():
    """메인 실행 함수"""
    # Mock 거래 테스트
    mock_success = await test_mock_trading()
    
    # Binance API 테스트
    binance_success = await test_binance_connection()
    
    # 결과 요약
    logger.info("\n" + "=" * 60)
    logger.info("📊 Test Summary")
    logger.info("=" * 60)
    logger.info(f"Mock Trading: {'✅ PASSED' if mock_success else '❌ FAILED'}")
    logger.info(f"Binance API: {'✅ PASSED' if binance_success else '❌ FAILED'}")
    logger.info("=" * 60)
    
    return 0 if (mock_success and binance_success) else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)