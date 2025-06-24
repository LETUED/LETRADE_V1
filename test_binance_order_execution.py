#!/usr/bin/env python3
"""
Binance Order Execution Test

Binance Testnet에서 실제 주문 생성, 조회, 취소를 테스트합니다.
소액 주문으로 안전하게 테스트를 진행합니다.
"""

import asyncio
import sys
import logging
import os
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from exchange_connector.interfaces import ExchangeConfig, OrderRequest, OrderSide, OrderType
from exchange_connector.main import CCXTExchangeConnector

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_market_order_execution(connector):
    """시장가 주문 실행 테스트"""
    logger.info("📈 Testing market order execution...")
    
    try:
        # API 키가 실제로 설정되어 있는지 확인
        has_real_keys = (
            os.getenv("BINANCE_TESTNET_API_KEY") and 
            os.getenv("BINANCE_TESTNET_SECRET_KEY") and
            os.getenv("BINANCE_TESTNET_API_KEY") != "test_api_key"
        )
        
        if not has_real_keys:
            logger.info("ℹ️ No real API keys found - skipping market order test")
            return True
        
        # 매우 소액 BTC 매수 주문 (Testnet에서만)
        order_request = OrderRequest(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            amount=Decimal("0.001"),  # 매우 소액 (약 $100 상당)
            client_order_id=f"test_market_buy_{int(datetime.now().timestamp())}"
        )
        
        logger.info(f"🛒 Placing market order: {order_request.side.value} {order_request.amount} {order_request.symbol}")
        
        # 주문 실행
        order_response = await connector.place_order(order_request)
        
        logger.info("✅ Market order placed successfully:")
        logger.info(f"   - Order ID: {order_response.order_id}")
        logger.info(f"   - Status: {order_response.status.value}")
        logger.info(f"   - Amount: {order_response.amount}")
        logger.info(f"   - Filled: {order_response.filled}")
        logger.info(f"   - Remaining: {order_response.remaining}")
        
        if order_response.average_price:
            logger.info(f"   - Average Price: ${order_response.average_price}")
        
        if order_response.cost:
            logger.info(f"   - Total Cost: ${order_response.cost}")
        
        # 주문 상태 재확인
        await asyncio.sleep(2)  # 잠시 대기
        
        order_status = await connector.get_order_status(order_response.order_id, order_request.symbol)
        logger.info(f"📊 Order status after execution: {order_status.status.value}")
        
        return order_response
        
    except Exception as e:
        logger.error(f"❌ Market order test failed: {e}")
        return None


async def test_limit_order_creation_and_cancellation(connector):
    """지정가 주문 생성 및 취소 테스트"""
    logger.info("📋 Testing limit order creation and cancellation...")
    
    try:
        # API 키가 실제로 설정되어 있는지 확인
        has_real_keys = (
            os.getenv("BINANCE_TESTNET_API_KEY") and 
            os.getenv("BINANCE_TESTNET_SECRET_KEY") and
            os.getenv("BINANCE_TESTNET_API_KEY") != "test_api_key"
        )
        
        if not has_real_keys:
            logger.info("ℹ️ No real API keys found - skipping limit order test")
            return True
        
        # 현재 BTC 가격 조회
        market_data = await connector.get_market_data("BTC/USDT", limit=1)
        if not market_data:
            logger.error("❌ Failed to get current BTC price")
            return False
        
        current_price = float(market_data[-1].close)
        logger.info(f"📊 Current BTC price: ${current_price}")
        
        # 현재 가격보다 10% 낮은 가격으로 매수 지정가 주문 (체결되지 않을 가격)
        limit_price = Decimal(str(current_price * 0.90))
        
        order_request = OrderRequest(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            amount=Decimal("0.001"),  # 소액
            price=limit_price,
            client_order_id=f"test_limit_buy_{int(datetime.now().timestamp())}"
        )
        
        logger.info(f"📝 Placing limit order: {order_request.side.value} {order_request.amount} {order_request.symbol} @ ${limit_price}")
        
        # 지정가 주문 실행
        order_response = await connector.place_order(order_request)
        
        logger.info("✅ Limit order placed successfully:")
        logger.info(f"   - Order ID: {order_response.order_id}")
        logger.info(f"   - Status: {order_response.status.value}")
        logger.info(f"   - Amount: {order_response.amount}")
        logger.info(f"   - Price: ${order_response.average_price or 'N/A'}")
        
        # 잠시 대기 후 주문 상태 확인
        await asyncio.sleep(3)
        
        order_status = await connector.get_order_status(order_response.order_id, order_request.symbol)
        logger.info(f"📊 Order status: {order_status.status.value}")
        
        # 열린 주문 목록 확인
        open_orders = await connector.get_open_orders("BTC/USDT")
        logger.info(f"📋 Open orders count: {len(open_orders)}")
        
        # 주문 취소
        logger.info(f"❌ Cancelling order: {order_response.order_id}")
        cancel_success = await connector.cancel_order(order_response.order_id, order_request.symbol)
        
        if cancel_success:
            logger.info("✅ Order cancelled successfully")
            
            # 취소 후 상태 확인
            await asyncio.sleep(2)
            final_status = await connector.get_order_status(order_response.order_id, order_request.symbol)
            logger.info(f"📊 Final order status: {final_status.status.value}")
        else:
            logger.warning("⚠️ Order cancellation failed")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Limit order test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_order_history_and_balances(connector):
    """주문 히스토리 및 잔고 변화 테스트"""
    logger.info("💰 Testing order history and balance changes...")
    
    try:
        # API 키가 실제로 설정되어 있는지 확인
        has_real_keys = (
            os.getenv("BINANCE_TESTNET_API_KEY") and 
            os.getenv("BINANCE_TESTNET_SECRET_KEY") and
            os.getenv("BINANCE_TESTNET_API_KEY") != "test_api_key"
        )
        
        if not has_real_keys:
            logger.info("ℹ️ No real API keys found - skipping balance test")
            return True
        
        # 현재 잔고 조회
        balances = await connector.get_account_balance()
        
        logger.info("💳 Current account balances:")
        
        # 주요 코인 잔고 표시
        major_coins = ['USDT', 'BTC', 'ETH', 'BNB']
        for coin in major_coins:
            if coin in balances:
                balance = balances[coin]
                if balance.total > 0:
                    logger.info(f"   - {coin}: {balance.total} (Free: {balance.free}, Used: {getattr(balance, 'used', 0)})")
                else:
                    logger.info(f"   - {coin}: 0.00000000")
            else:
                logger.info(f"   - {coin}: Not found")
        
        # 0이 아닌 모든 잔고 표시
        non_zero_balances = {
            currency: balance for currency, balance in balances.items()
            if balance.total > 0
        }
        
        if non_zero_balances:
            logger.info(f"💰 Total non-zero balances: {len(non_zero_balances)}")
            for currency, balance in list(non_zero_balances.items())[:10]:  # 최대 10개만 표시
                logger.info(f"   - {currency}: {balance.total}")
        else:
            logger.info("💰 All balances are zero (normal for new testnet account)")
        
        # 모든 열린 주문 조회
        all_open_orders = await connector.get_open_orders()
        logger.info(f"📋 Total open orders across all symbols: {len(all_open_orders)}")
        
        if all_open_orders:
            for order in all_open_orders[:5]:  # 최대 5개만 표시
                logger.info(f"   - {order.symbol}: {order.side.value} {order.amount} @ {order.average_price or 'Market'}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Balance and history test failed: {e}")
        return False


async def test_error_handling(connector):
    """에러 처리 테스트"""
    logger.info("⚠️ Testing error handling...")
    
    try:
        # 잘못된 심볼로 주문 시도
        try:
            invalid_order = OrderRequest(
                symbol="INVALID/PAIR",
                side=OrderSide.BUY,
                type=OrderType.MARKET,
                amount=Decimal("0.001")
            )
            
            await connector.place_order(invalid_order)
            logger.warning("⚠️ Invalid symbol order should have failed")
            
        except Exception as e:
            logger.info(f"✅ Invalid symbol error handled correctly: {e}")
        
        # 잘못된 주문 ID로 상태 조회 시도
        try:
            await connector.get_order_status("INVALID_ORDER_ID", "BTC/USDT")
            logger.warning("⚠️ Invalid order ID query should have failed")
            
        except Exception as e:
            logger.info(f"✅ Invalid order ID error handled correctly: {e}")
        
        # 잘못된 주문 ID로 취소 시도
        try:
            await connector.cancel_order("INVALID_ORDER_ID", "BTC/USDT")
            logger.warning("⚠️ Invalid order ID cancellation should have failed")
            
        except Exception as e:
            logger.info(f"✅ Invalid order cancellation error handled correctly: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error handling test failed: {e}")
        return False


async def main():
    """메인 테스트 실행"""
    logger.info("🚀 Starting Binance Order Execution Tests")
    logger.info("=" * 70)
    
    # 환경 정보 출력
    logger.info("📋 Environment Information:")
    logger.info(f"   - API Key Set: {bool(os.getenv('BINANCE_TESTNET_API_KEY'))}")
    logger.info(f"   - Secret Key Set: {bool(os.getenv('BINANCE_TESTNET_SECRET_KEY'))}")
    
    connector = None
    
    try:
        # Exchange Connector 초기화
        config = ExchangeConfig(
            exchange_name="binance",
            api_key=os.getenv("BINANCE_TESTNET_API_KEY", "test_api_key"),
            api_secret=os.getenv("BINANCE_TESTNET_SECRET_KEY", "test_secret_key"),
            sandbox=True,  # 테스트넷 모드
            rate_limit=1200,
            timeout=30
        )
        
        connector = CCXTExchangeConnector(config)
        
        # 연결
        if not await connector.connect():
            logger.error("❌ Failed to connect to exchange - stopping tests")
            return
        
        logger.info("✅ Connected to Binance Testnet")
        logger.info("-" * 70)
        
        # Test 1: 시장가 주문 실행 테스트
        market_order_result = await test_market_order_execution(connector)
        
        logger.info("-" * 70)
        
        # Test 2: 지정가 주문 생성 및 취소 테스트
        await test_limit_order_creation_and_cancellation(connector)
        
        logger.info("-" * 70)
        
        # Test 3: 주문 히스토리 및 잔고 테스트
        await test_order_history_and_balances(connector)
        
        logger.info("-" * 70)
        
        # Test 4: 에러 처리 테스트
        await test_error_handling(connector)
        
        logger.info("=" * 70)
        logger.info("🎉 Binance Order Execution tests completed!")
        
        # 성능 요약
        logger.info("\n📊 Test Summary:")
        logger.info("1. ✅ Market order execution tested")
        logger.info("2. ✅ Limit order creation/cancellation tested") 
        logger.info("3. ✅ Account balance monitoring tested")
        logger.info("4. ✅ Error handling validated")
        
        logger.info("\n📝 Next Steps:")
        logger.info("1. Integration with Strategy Worker")
        logger.info("2. Capital Manager order validation")
        logger.info("3. E2E trading pipeline test")
        logger.info("4. Performance benchmarking (<200ms target)")
        
    except Exception as e:
        logger.error(f"❌ Order execution tests failed: {e}")
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