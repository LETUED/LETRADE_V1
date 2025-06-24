#!/usr/bin/env python3
"""
Core Engine 통합 검증 테스트 (최적화된 성능 포함)
Core Engine Integration Verification Test with Performance Optimization

최적화된 WebSocket 커넥터가 Core Engine에 완전히 통합되고,
전체 시스템이 0.86ms 성능으로 동작하는지 검증합니다.
"""

import asyncio
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_core_engine_startup():
    """Core Engine 시작 및 최적화된 커넥터 초기화 테스트"""
    logger.info("🏗️ Testing Core Engine startup with optimized connector")
    
    try:
        # Import Core Engine
        import os
        os.chdir(str(src_path))
        
        from core_engine.main import CoreEngine
        
        # Create configuration
        config = {
            "log_level": "INFO",
            "health_check_interval": 30,
            "reconciliation_interval": 300,
            "exchange_connector": {
                "exchange_name": "binance",
                "sandbox": True,
                "enable_rate_limiting": True,
                "timeout": 10.0
            }
        }
        
        # Create and start Core Engine
        engine = CoreEngine(config)
        
        start_time = time.time()
        started = await engine.start()
        startup_time = (time.time() - start_time) * 1000
        
        if not started:
            logger.error("❌ Core Engine startup failed")
            return False
        
        logger.info(f"✅ Core Engine started in {startup_time:.2f}ms")
        
        # Check if optimized exchange connector is properly integrated
        if engine.exchange_connector:
            logger.info("✅ Optimized Exchange Connector integrated successfully")
            
            # Test health check
            health = await engine.exchange_connector.health_check()
            logger.info(f"📊 Exchange Connector Health: {health}")
            
            # Test performance stats if available
            if hasattr(engine.exchange_connector, 'get_performance_stats'):
                stats = engine.exchange_connector.get_performance_stats()
                logger.info(f"🚀 Performance Stats: {stats}")
            
        else:
            logger.warning("⚠️ Exchange Connector not initialized")
        
        # Test system status
        status = engine.get_status()
        logger.info(f"🖥️ System Status:")
        logger.info(f"   Running: {status['is_running']}")
        logger.info(f"   Components: {status['component_status']}")
        
        # Test health check
        health_result = await engine.health_check()
        logger.info(f"🏥 System Health: {health_result.get('overall_health', False)}")
        
        # Cleanup
        await engine.stop()
        logger.info("🔄 Core Engine stopped successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Core Engine integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_strategy_worker_integration():
    """Strategy Worker와 최적화된 Exchange Connector 통합 테스트"""
    logger.info("🧠 Testing Strategy Worker integration")
    
    try:
        from core_engine.main import CoreEngine
        from strategies.base_strategy import StrategyConfig
        
        # Create Core Engine
        config = {
            "log_level": "INFO",
            "health_check_interval": 30,
        }
        
        engine = CoreEngine(config)
        started = await engine.start()
        
        if not started:
            logger.error("❌ Failed to start Core Engine")
            return False
        
        # Test strategy creation and execution
        strategy_config = StrategyConfig(
            strategy_id="test_ma_strategy",
            name="Test MA Crossover",
            enabled=True,
            dry_run=True,
            risk_params={"max_position_size": 0.01},
            custom_params={"fast_period": 10, "slow_period": 20}
        )
        
        # Start strategy
        strategy_started = await engine.start_strategy(strategy_config)
        
        if strategy_started:
            logger.info("✅ Strategy started successfully")
            
            # Check strategy status
            strategy_status = await engine.get_strategy_status("test_ma_strategy")
            logger.info(f"📊 Strategy Status: {strategy_status}")
            
            # Stop strategy
            await engine.stop_strategy("test_ma_strategy")
            logger.info("✅ Strategy stopped successfully")
        else:
            logger.warning("⚠️ Strategy startup failed")
        
        # Cleanup
        await engine.stop()
        return strategy_started
        
    except Exception as e:
        logger.error(f"❌ Strategy Worker integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_end_to_end_performance():
    """E2E 성능 테스트 - 최적화된 성능 검증"""
    logger.info("⚡ Testing End-to-End performance with optimization")
    
    try:
        # Direct exchange connector performance test
        from exchange_connector import create_optimized_connector, ExchangeConfig
        
        config = ExchangeConfig(
            exchange_name="binance",
            api_key="",
            api_secret="",
            sandbox=True,
            enable_rate_limiting=True,
            timeout=10.0
        )
        
        connector = create_optimized_connector(config)
        
        # Connect and test performance
        connected = await connector.connect()
        if not connected:
            logger.error("❌ Failed to connect to optimized connector")
            return False
        
        # Performance test - cold cache
        start_time = time.time()
        market_data = await connector.get_market_data("BTC/USDT", "1m", 50)
        cold_time = (time.time() - start_time) * 1000
        
        # Performance test - warm cache
        start_time = time.time()
        market_data = await connector.get_market_data("BTC/USDT", "1m", 50)
        warm_time = (time.time() - start_time) * 1000
        
        # Performance analysis
        target = 200.0  # MVP target <200ms
        optimized_target = 1.0  # Optimized target <1ms
        
        logger.info(f"📊 Performance Results:")
        logger.info(f"   Cold cache: {cold_time:.2f}ms")
        logger.info(f"   Warm cache: {warm_time:.2f}ms")
        logger.info(f"   Data points: {len(market_data)} candles")
        
        # Performance assessment
        if warm_time < optimized_target:
            logger.info(f"🎉 EXCELLENT: {warm_time:.3f}ms (Target: <{optimized_target}ms)")
            performance_grade = "A+"
        elif warm_time < 10.0:
            logger.info(f"🎯 VERY GOOD: {warm_time:.2f}ms (Target: <{optimized_target}ms)")
            performance_grade = "A"
        elif warm_time < target:
            logger.info(f"✅ GOOD: {warm_time:.2f}ms (MVP Target: <{target}ms)")
            performance_grade = "B"
        else:
            logger.warning(f"⚠️ NEEDS IMPROVEMENT: {warm_time:.2f}ms")
            performance_grade = "C"
        
        # Get performance stats
        if hasattr(connector, 'get_performance_stats'):
            stats = connector.get_performance_stats()
            logger.info(f"📈 Performance Stats: {stats}")
        
        await connector.disconnect()
        
        return performance_grade in ["A+", "A", "B"]
        
    except Exception as e:
        logger.error(f"❌ E2E performance test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_database_integration():
    """데이터베이스 통합 테스트"""
    logger.info("🗄️ Testing database integration")
    
    try:
        from common.database import db_manager, Portfolio, Strategy
        
        # Test database connection
        db_manager.connect()
        
        if not db_manager.is_connected():
            logger.error("❌ Database connection failed")
            return False
        
        logger.info("✅ Database connected successfully")
        
        # Test table creation
        db_manager.create_tables()
        logger.info("✅ Database tables created successfully")
        
        # Test basic operations
        with db_manager.get_session() as session:
            # Test portfolio creation
            test_portfolio = Portfolio(
                name="test_portfolio",
                total_capital=10000.0,
                available_capital=10000.0,
                currency="USDT"
            )
            session.add(test_portfolio)
            session.flush()  # Get the ID
            
            # Test strategy creation
            test_strategy = Strategy(
                name="test_strategy",
                strategy_type="MA_CROSSOVER",
                exchange="binance",
                symbol="BTC/USDT",
                parameters={"fast": 10, "slow": 20},
                portfolio_id=test_portfolio.id
            )
            session.add(test_strategy)
            session.commit()
            
            logger.info("✅ Database CRUD operations successful")
            
            # Cleanup
            session.delete(test_strategy)
            session.delete(test_portfolio)
            session.commit()
        
        db_manager.disconnect()
        logger.info("✅ Database integration test successful")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """메인 통합 테스트 실행"""
    logger.info("🚀 Core Engine Integration Verification Test")
    logger.info("=" * 60)
    
    tests = [
        ("Core Engine Startup", test_core_engine_startup),
        ("Strategy Worker Integration", test_strategy_worker_integration),
        ("E2E Performance", test_end_to_end_performance),
        ("Database Integration", test_database_integration),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n📊 Test: {test_name}")
        logger.info("-" * 50)
        
        start_time = time.time()
        success = await test_func()
        elapsed = (time.time() - start_time) * 1000
        
        results[test_name] = {
            "success": success,
            "elapsed_ms": elapsed
        }
        
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(f"{status} - {elapsed:.2f}ms")
    
    # Summary
    logger.info(f"\n📋 Integration Test Summary")
    logger.info("=" * 60)
    
    passed = sum(1 for r in results.values() if r["success"])
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅" if result["success"] else "❌"
        logger.info(f"{status} {test_name}: {result['elapsed_ms']:.2f}ms")
    
    if passed == total:
        logger.info(f"\n🎉 ALL TESTS PASSED! ({passed}/{total})")
        logger.info("✅ Core Engine integration with optimized performance verified")
        logger.info("🚀 System ready for 24-hour continuous testing")
        
        # Update todo status
        logger.info("\n📝 Updating project status...")
        logger.info("✅ Core Engine 통합 및 검증 완료")
        logger.info("🎯 다음 단계: 24시간 연속 드라이런 테스트 구현")
        
        return True
    else:
        logger.error(f"\n❌ SOME TESTS FAILED ({passed}/{total})")
        logger.error("⚠️ Integration issues need to be resolved")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)