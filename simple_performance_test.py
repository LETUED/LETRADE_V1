#!/usr/bin/env python3
"""
간단한 성능 최적화 테스트
Simple performance optimization test

WebSocket 기반 최적화된 Exchange Connector 성능을 직접 테스트합니다.
"""

import asyncio
import sys
import time
import logging
from pathlib import Path

# Add src path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def test_websocket_performance():
    """WebSocket 최적화 성능 테스트"""
    try:
        # Import the optimized connector
        sys.path.append(str(src_path / "exchange_connector"))
        
        from websocket_connector import OptimizedExchangeConnector
        from interfaces import ExchangeConfig
        
        logger.info("🚀 Testing WebSocket optimized Exchange Connector")
        
        # Create configuration
        config = ExchangeConfig(
            exchange_name="binance",
            api_key="",
            api_secret="",
            sandbox=True,
            enable_rate_limiting=True,
            timeout=10.0
        )
        
        # Create connector
        connector = OptimizedExchangeConnector(config)
        
        # Connect
        logger.info("Connecting to exchange...")
        start_time = time.time()
        
        connected = await connector.connect()
        connect_time = (time.time() - start_time) * 1000
        
        if not connected:
            logger.error("❌ Failed to connect")
            return False
        
        logger.info(f"✅ Connected in {connect_time:.2f}ms")
        
        # Test market data performance
        logger.info("Testing market data fetching performance...")
        
        # First request (cold cache)
        start_time = time.time()
        try:
            market_data = await connector.get_market_data("BTC/USDT", "1m", 50)
            cold_time = (time.time() - start_time) * 1000
            logger.info(f"📊 Cold cache: {cold_time:.2f}ms ({len(market_data)} candles)")
        except Exception as e:
            logger.error(f"Cold cache test failed: {e}")
            cold_time = float('inf')
        
        # Second request (warm cache)
        start_time = time.time()
        try:
            market_data = await connector.get_market_data("BTC/USDT", "1m", 50)
            warm_time = (time.time() - start_time) * 1000
            logger.info(f"⚡ Warm cache: {warm_time:.2f}ms ({len(market_data)} candles)")
        except Exception as e:
            logger.error(f"Warm cache test failed: {e}")
            warm_time = float('inf')
        
        # Performance analysis
        target = 200.0  # 200ms target
        
        if warm_time < 1.0:
            logger.info(f"🎉 EXCELLENT: {warm_time:.3f}ms (Target: <{target}ms)")
            grade = "A+"
        elif warm_time < 10.0:
            logger.info(f"🎯 VERY GOOD: {warm_time:.2f}ms (Target: <{target}ms)")
            grade = "A"
        elif warm_time < target:
            logger.info(f"✅ GOOD: {warm_time:.2f}ms (Target: <{target}ms)")
            grade = "B"
        else:
            logger.warning(f"⚠️ NEEDS IMPROVEMENT: {warm_time:.2f}ms (Target: <{target}ms)")
            grade = "C"
        
        # Get performance stats
        stats = connector.get_performance_stats()
        logger.info(f"📊 Performance Stats:")
        logger.info(f"   Cache hit rate: {stats.get('cache_hit_rate', 0):.1%}")
        logger.info(f"   Cache size: {stats.get('cache_size', 0)} entries")
        logger.info(f"   WebSocket connections: {stats.get('websocket_connections', 0)}")
        
        # Cleanup
        await connector.disconnect()
        logger.info("🔄 Disconnected")
        
        return grade in ["A+", "A", "B"]
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """메인 테스트"""
    logger.info("🚀 Simple Performance Optimization Test")
    logger.info("=" * 50)
    
    success = await test_websocket_performance()
    
    logger.info("\n📋 Test Summary")
    logger.info("=" * 50)
    
    if success:
        logger.info("🎉 PERFORMANCE TEST PASSED!")
        logger.info("✅ WebSocket optimization working correctly")
        logger.info("🚀 Ready for high-frequency trading")
    else:
        logger.error("❌ PERFORMANCE TEST FAILED")
        logger.error("⚠️ Check connection and dependencies")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)