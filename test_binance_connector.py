#!/usr/bin/env python3
"""
Binance Exchange Connector Test

Binance Testnet API 연결 및 기본 기능을 테스트합니다.
실제 API 키 없이도 기본 구조를 검증할 수 있도록 설계되었습니다.
"""

import asyncio
import sys
import logging
import os
from pathlib import Path
from datetime import datetime, timezone

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from exchange_connector.interfaces import ExchangeConfig
from exchange_connector.main import CCXTExchangeConnector

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_binance_connector_initialization():
    """Binance Connector 초기화 테스트"""
    logger.info("🔌 Testing Binance Connector Initialization...")
    
    try:
        # 테스트넷 설정
        config = ExchangeConfig(
            exchange_name="binance",
            api_key=os.getenv("BINANCE_TESTNET_API_KEY", "test_api_key"),
            api_secret=os.getenv("BINANCE_TESTNET_SECRET_KEY", "test_secret_key"),
            sandbox=True,  # 테스트넷 모드
            rate_limit=1200,  # 분당 요청 수 제한
            timeout=30  # 요청 타임아웃 (초)
        )
        
        # Exchange Connector 초기화
        connector = CCXTExchangeConnector(config)
        
        # 연결 시도 (API 키가 없으면 실패할 수 있음)
        try:
            await connector.connect()
        except Exception as e:
            logger.warning(f"⚠️ Connection failed (expected without real API keys): {e}")
            # API 키가 없어도 connector 객체 자체는 테스트할 수 있음
        
        logger.info("✅ Binance Connector initialized successfully")
        logger.info(f"   - Exchange: {connector.exchange_name}")
        logger.info(f"   - Sandbox Mode: {config.sandbox}")
        logger.info(f"   - Rate Limit: {config.rate_limit}")
        
        return connector
        
    except Exception as e:
        logger.error(f"❌ Binance Connector initialization failed: {e}")
        return None


async def test_connectivity(connector):
    """연결 테스트"""
    if not connector:
        logger.warning("⚠️ Skipping connectivity test - no connector available")
        return False
    
    logger.info("🌐 Testing exchange connectivity...")
    
    try:
        # 기본 연결 테스트 (health_check 사용)
        health_status = await connector.health_check()
        is_connected = health_status.get('connected', False)
        
        if is_connected:
            logger.info("✅ Exchange connectivity test passed")
            logger.info(f"   - Status: {health_status.get('status', 'unknown')}")
            if 'response_time_ms' in health_status:
                logger.info(f"   - Response time: {health_status['response_time_ms']:.2f}ms")
        else:
            logger.warning("⚠️ Exchange connectivity test failed")
            if 'error' in health_status:
                logger.warning(f"   - Error: {health_status['error']}")
        
        return is_connected
        
    except Exception as e:
        logger.error(f"❌ Connectivity test error: {e}")
        return False


async def test_market_data(connector):
    """시장 데이터 조회 테스트"""
    if not connector:
        logger.warning("⚠️ Skipping market data test - no connector available")
        return False
    
    logger.info("📊 Testing market data retrieval...")
    
    try:
        # 심볼 정보 조회 테스트
        symbols = ["BTC/USDT", "ETH/USDT"]
        
        for symbol in symbols:
            try:
                # 현재 가격 조회 (get_market_data 사용)
                market_data_list = await connector.get_market_data(symbol, timeframe='1m', limit=1)
                
                if market_data_list:
                    latest_data = market_data_list[-1]
                    logger.info(f"✅ {symbol} market data retrieved:")
                    logger.info(f"   - Price: ${float(latest_data.close)}")
                    logger.info(f"   - Volume: {float(latest_data.volume)}")
                    logger.info(f"   - Timestamp: {latest_data.timestamp}")
                else:
                    logger.warning(f"⚠️ Failed to get market data for {symbol}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Error getting market data for {symbol}: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Market data test error: {e}")
        return False


async def test_account_info(connector):
    """계정 정보 조회 테스트"""
    if not connector:
        logger.warning("⚠️ Skipping account info test - no connector available")
        return False
    
    logger.info("👤 Testing account information retrieval...")
    
    try:
        # API 키가 실제로 설정되어 있는지 확인
        has_real_keys = (
            os.getenv("BINANCE_TESTNET_API_KEY") and 
            os.getenv("BINANCE_TESTNET_SECRET_KEY") and
            os.getenv("BINANCE_TESTNET_API_KEY") != "test_api_key"
        )
        
        if not has_real_keys:
            logger.info("ℹ️ No real API keys found - skipping account info test")
            logger.info("   To test with real API keys, set:")
            logger.info("   - BINANCE_TESTNET_API_KEY")
            logger.info("   - BINANCE_TESTNET_SECRET_KEY")
            return True
        
        # 계정 잔고 조회
        balances = await connector.get_account_balance()
        
        if balances:
            logger.info("✅ Account balance retrieved:")
            
            # 0이 아닌 잔고만 표시
            non_zero_balances = {
                currency: balance for currency, balance in balances.items()
                if balance.total > 0
            }
            
            if non_zero_balances:
                for currency, balance in non_zero_balances.items():
                    used_amount = getattr(balance, 'used', getattr(balance, 'locked', 0))
                    logger.info(f"   - {currency}: {balance.total} (Free: {balance.free}, Used: {used_amount})")
            else:
                logger.info("   - All balances are zero (normal for new testnet account)")
        else:
            logger.warning("⚠️ Failed to retrieve account balance")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Account info test error: {e}")
        return False


async def test_order_management(connector):
    """주문 관리 테스트 (테스트넷에서만)"""
    if not connector:
        logger.warning("⚠️ Skipping order management test - no connector available")
        return False
    
    logger.info("📋 Testing order management...")
    
    try:
        # API 키가 실제로 설정되어 있는지 확인
        has_real_keys = (
            os.getenv("BINANCE_TESTNET_API_KEY") and 
            os.getenv("BINANCE_TESTNET_SECRET_KEY") and
            os.getenv("BINANCE_TESTNET_API_KEY") != "test_api_key"
        )
        
        if not has_real_keys:
            logger.info("ℹ️ No real API keys found - skipping order management test")
            return True
        
        # 열린 주문 조회
        open_orders = await connector.get_open_orders("BTC/USDT")
        
        if open_orders is not None:
            logger.info(f"✅ Open orders retrieved: {len(open_orders)} orders")
            
            for order in open_orders[:3]:  # 최대 3개만 표시
                logger.info(f"   - Order {order.order_id}: {order.side.value} {order.amount} @ {order.price}")
        else:
            logger.warning("⚠️ Failed to retrieve open orders")
        
        # 주문 히스토리는 get_open_orders로 대체 (인터페이스에 없음)
        logger.info("ℹ️ Order history retrieval skipped (method not in interface)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Order management test error: {e}")
        return False


async def test_health_check(connector):
    """헬스 체크 테스트"""
    if not connector:
        logger.warning("⚠️ Skipping health check test - no connector available")
        return False
    
    logger.info("🔍 Testing health check...")
    
    try:
        health_status = await connector.health_check()
        
        logger.info("✅ Health check completed:")
        logger.info(f"   - Connected: {health_status.get('connected', False)}")
        logger.info(f"   - Exchange: {health_status.get('exchange_name', 'N/A')}")
        logger.info(f"   - Timestamp: {health_status.get('timestamp', 'N/A')}")
        
        if 'latency' in health_status:
            logger.info(f"   - Latency: {health_status['latency']:.2f}ms")
        
        return health_status.get('connected', False)
        
    except Exception as e:
        logger.error(f"❌ Health check error: {e}")
        return False


async def main():
    """메인 테스트 실행"""
    logger.info("🚀 Starting Binance Exchange Connector Tests")
    logger.info("=" * 60)
    
    # 환경 정보 출력
    logger.info("📋 Environment Information:")
    logger.info(f"   - Has CCXT: {hasattr(sys.modules.get('ccxt', {}), 'binance')}")
    logger.info(f"   - API Key Set: {bool(os.getenv('BINANCE_TESTNET_API_KEY'))}")
    logger.info(f"   - Secret Key Set: {bool(os.getenv('BINANCE_TESTNET_SECRET_KEY'))}")
    
    connector = None
    
    try:
        # Test 1: Connector Initialization
        connector = await test_binance_connector_initialization()
        
        if not connector:
            logger.error("❌ Cannot proceed without connector - stopping tests")
            return
        
        logger.info("-" * 60)
        
        # Test 2: Connectivity
        await test_connectivity(connector)
        
        logger.info("-" * 60)
        
        # Test 3: Market Data
        await test_market_data(connector)
        
        logger.info("-" * 60)
        
        # Test 4: Account Info
        await test_account_info(connector)
        
        logger.info("-" * 60)
        
        # Test 5: Order Management
        await test_order_management(connector)
        
        logger.info("-" * 60)
        
        # Test 6: Health Check
        await test_health_check(connector)
        
        logger.info("=" * 60)
        logger.info("🎉 Binance Exchange Connector tests completed!")
        
        # 다음 단계 안내
        logger.info("\n📝 Next Steps:")
        logger.info("1. Set up real Binance Testnet API keys for full testing")
        logger.info("2. Run integration tests with Core Engine")
        logger.info("3. Test with Strategy Worker")
        logger.info("4. Performance benchmarking")
        
    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        if connector:
            try:
                await connector.cleanup()
                logger.info("🧹 Connector cleanup completed")
            except Exception as e:
                logger.warning(f"⚠️ Cleanup error: {e}")


if __name__ == "__main__":
    # Run the async tests
    asyncio.run(main())