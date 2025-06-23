#!/usr/bin/env python3
"""
Core Engine과 Strategy Worker 통합 테스트

이 스크립트는 Core Engine이 Strategy Worker를 정상적으로 관리하는지 테스트합니다.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core_engine.main import CoreEngine
from src.strategies.base_strategy import StrategyConfig

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_core_engine_startup():
    """Core Engine 시작 테스트"""
    logger.info("=" * 60)
    logger.info("🚀 Core Engine 시작 테스트")
    logger.info("=" * 60)
    
    # Core Engine 설정
    config = {
        "message_bus": {
            "host": "localhost",
            "port": 5672,
            "username": "letrade_user",
            "password": "letrade_password",
            "virtual_host": "/"
        },
        "log_level": "INFO",
        "health_check_interval": 10,
        "reconciliation_interval": 60
    }
    
    # Core Engine 생성
    engine = CoreEngine(config)
    
    try:
        # 시작
        logger.info("Core Engine 시작 중...")
        success = await engine.start()
        
        if success:
            logger.info("✅ Core Engine 시작 성공!")
            
            # 상태 확인
            status = engine.get_status()
            logger.info(f"시스템 상태: {status}")
            
            # 헬스체크
            health = await engine.health_check()
            logger.info(f"헬스체크 결과: {health}")
            
            return engine, True
        else:
            logger.error("❌ Core Engine 시작 실패")
            return None, False
            
    except Exception as e:
        logger.error(f"Core Engine 시작 중 오류: {e}")
        return None, False


async def test_strategy_lifecycle(engine: CoreEngine):
    """전략 생명주기 테스트"""
    logger.info("\n" + "=" * 60)
    logger.info("🎯 전략 생명주기 테스트")
    logger.info("=" * 60)
    
    # 테스트용 전략 설정
    strategy_config = StrategyConfig(
        strategy_id="test_integration_ma_001",
        name="Integration Test MA Strategy",
        enabled=True,
        dry_run=True,
        custom_params={
            "fast_period": 5,
            "slow_period": 20,
            "symbol": "BTC/USDT",
            "exchange": "binance",
            "min_signal_interval": 30,
            "min_crossover_strength": 0.1
        }
    )
    
    try:
        # 1. 전략 시작
        logger.info(f"1. 전략 시작: {strategy_config.strategy_id}")
        success = await engine.start_strategy(strategy_config)
        
        if success:
            logger.info("✅ 전략 시작 성공!")
        else:
            logger.error("❌ 전략 시작 실패")
            return False
        
        # 2. 전략 상태 확인
        await asyncio.sleep(2)  # 잠시 대기
        
        logger.info("2. 전략 상태 확인")
        strategy_status = await engine.get_strategy_status(strategy_config.strategy_id)
        logger.info(f"전략 상태: {strategy_status}")
        
        # 3. 전체 상태 확인
        logger.info("3. 전체 시스템 상태 확인")
        system_status = engine.get_status()
        logger.info(f"활성 전략 수: {len(system_status['active_strategies'])}")
        logger.info(f"활성 전략 목록: {system_status['active_strategies']}")
        
        # 4. 잠시 실행 대기 (Strategy Worker가 동작하는지 확인)
        logger.info("4. 전략 실행 대기 (10초)")
        await asyncio.sleep(10)
        
        # 5. 전략 중지
        logger.info(f"5. 전략 중지: {strategy_config.strategy_id}")
        success = await engine.stop_strategy(strategy_config.strategy_id)
        
        if success:
            logger.info("✅ 전략 중지 성공!")
        else:
            logger.error("❌ 전략 중지 실패")
            return False
        
        # 6. 중지 후 상태 확인
        await asyncio.sleep(2)  # 잠시 대기
        
        logger.info("6. 중지 후 상태 확인")
        system_status = engine.get_status()
        logger.info(f"활성 전략 수: {len(system_status['active_strategies'])}")
        
        return True
        
    except Exception as e:
        logger.error(f"전략 생명주기 테스트 중 오류: {e}")
        return False


async def test_multiple_strategies(engine: CoreEngine):
    """다중 전략 관리 테스트"""
    logger.info("\n" + "=" * 60)
    logger.info("🔄 다중 전략 관리 테스트")
    logger.info("=" * 60)
    
    # 여러 전략 설정
    strategies = [
        StrategyConfig(
            strategy_id="test_multi_ma_001",
            name="Multi Test MA Strategy 1",
            enabled=True,
            dry_run=True,
            custom_params={
                "fast_period": 5,
                "slow_period": 20,
                "symbol": "BTC/USDT",
                "exchange": "binance",
                "min_signal_interval": 0,
                "min_crossover_strength": 0.1
            }
        ),
        StrategyConfig(
            strategy_id="test_multi_ma_002",
            name="Multi Test MA Strategy 2",
            enabled=True,
            dry_run=True,
            custom_params={
                "fast_period": 10,
                "slow_period": 50,
                "symbol": "ETH/USDT",
                "exchange": "binance",
                "min_signal_interval": 0,
                "min_crossover_strength": 0.2
            }
        )
    ]
    
    try:
        # 1. 모든 전략 시작
        logger.info("1. 다중 전략 시작")
        started_strategies = []
        
        for strategy_config in strategies:
            logger.info(f"   전략 시작: {strategy_config.strategy_id}")
            success = await engine.start_strategy(strategy_config)
            
            if success:
                started_strategies.append(strategy_config.strategy_id)
                logger.info(f"   ✅ {strategy_config.strategy_id} 시작 성공")
            else:
                logger.error(f"   ❌ {strategy_config.strategy_id} 시작 실패")
        
        logger.info(f"시작된 전략 수: {len(started_strategies)}")
        
        # 2. 전체 상태 확인
        await asyncio.sleep(3)
        
        logger.info("2. 전체 전략 상태 확인")
        all_status = await engine.get_strategy_status()
        logger.info(f"Strategy Worker Manager 상태: {all_status}")
        
        # 3. 각 전략 개별 상태 확인
        logger.info("3. 개별 전략 상태 확인")
        for strategy_id in started_strategies:
            status = await engine.get_strategy_status(strategy_id)
            logger.info(f"   {strategy_id}: 상태 = {status.get('healthy', 'unknown')}")
        
        # 4. 실행 대기
        logger.info("4. 다중 전략 실행 대기 (15초)")
        await asyncio.sleep(15)
        
        # 5. 모든 전략 중지
        logger.info("5. 모든 전략 중지")
        for strategy_id in started_strategies:
            logger.info(f"   전략 중지: {strategy_id}")
            success = await engine.stop_strategy(strategy_id)
            
            if success:
                logger.info(f"   ✅ {strategy_id} 중지 성공")
            else:
                logger.error(f"   ❌ {strategy_id} 중지 실패")
        
        # 6. 최종 상태 확인
        await asyncio.sleep(2)
        
        logger.info("6. 최종 상태 확인")
        system_status = engine.get_status()
        logger.info(f"활성 전략 수: {len(system_status['active_strategies'])}")
        
        return True
        
    except Exception as e:
        logger.error(f"다중 전략 테스트 중 오류: {e}")
        return False


async def main():
    """메인 테스트 실행 함수"""
    logger.info("🧪 Core Engine & Strategy Worker 통합 테스트 시작")
    
    engine = None
    
    try:
        # 1. Core Engine 시작 테스트
        engine, startup_success = await test_core_engine_startup()
        
        if not startup_success:
            logger.error("Core Engine 시작 실패로 테스트 중단")
            return
        
        # 2. 단일 전략 생명주기 테스트
        lifecycle_success = await test_strategy_lifecycle(engine)
        
        if lifecycle_success:
            logger.info("✅ 전략 생명주기 테스트 성공")
        else:
            logger.error("❌ 전략 생명주기 테스트 실패")
        
        # 3. 다중 전략 관리 테스트
        multi_success = await test_multiple_strategies(engine)
        
        if multi_success:
            logger.info("✅ 다중 전략 관리 테스트 성공")
        else:
            logger.error("❌ 다중 전략 관리 테스트 실패")
        
        # 결과 요약
        logger.info("\n" + "=" * 60)
        logger.info("📊 테스트 결과 요약")
        logger.info("=" * 60)
        logger.info(f"Core Engine 시작: {'✅ 성공' if startup_success else '❌ 실패'}")
        logger.info(f"전략 생명주기: {'✅ 성공' if lifecycle_success else '❌ 실패'}")
        logger.info(f"다중 전략 관리: {'✅ 성공' if multi_success else '❌ 실패'}")
        
        all_success = startup_success and lifecycle_success and multi_success
        logger.info(f"\n🎯 전체 테스트 결과: {'✅ 모든 테스트 성공!' if all_success else '❌ 일부 테스트 실패'}")
        
    except Exception as e:
        logger.error(f"테스트 실행 중 예상치 못한 오류: {e}")
        
    finally:
        # Core Engine 정리
        if engine:
            logger.info("\n🛑 Core Engine 종료 중...")
            await engine.stop()
            logger.info("Core Engine 종료 완료")


if __name__ == "__main__":
    asyncio.run(main())