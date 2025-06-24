#!/usr/bin/env python3
"""
Database Connection Test

데이터베이스 연결 및 ORM 모델 테스트를 수행합니다.
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from common.database import (
    db_manager, Strategy, Trade, Position, Portfolio, 
    PortfolioRule, PerformanceMetric, SystemLog
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_database_connection():
    """데이터베이스 연결 테스트"""
    logger.info("🔌 Testing database connection...")
    
    try:
        # 데이터베이스 연결 초기화
        await db_manager.async_connect()
        logger.info("✅ Database connected successfully")
        
        # 테이블 생성
        db_manager.create_tables()
        logger.info("✅ Database tables created successfully")
        
        # 연결 상태 확인
        if db_manager.is_connected():
            logger.info("✅ Database connection is active")
        else:
            logger.error("❌ Database connection is not active")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


async def test_database_tables():
    """데이터베이스 테이블 존재 확인"""
    logger.info("🗄️ Testing database tables...")
    
    try:
        with db_manager.get_session() as session:
            # 각 테이블에 대한 간단한 쿼리 테스트
            tables_to_test = [
                (Strategy, "strategies"),
                (Portfolio, "portfolios"), 
                (Trade, "trades"),
                (Position, "positions"),
                (PortfolioRule, "portfolio_rules"),
                (PerformanceMetric, "performance_metrics"),
                (SystemLog, "system_logs")
            ]
            
            for model_class, table_name in tables_to_test:
                try:
                    count = session.query(model_class).count()
                    logger.info(f"✅ Table '{table_name}': {count} records")
                except Exception as e:
                    logger.error(f"❌ Table '{table_name}' error: {e}")
                    return False
        
        logger.info("✅ All database tables are accessible")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database table test failed: {e}")
        return False


async def test_basic_crud_operations():
    """기본 CRUD 연산 테스트"""
    logger.info("📝 Testing basic CRUD operations...")
    
    try:
        with db_manager.get_session() as session:
            # 테스트 데이터 정리 (기존 테스트 데이터 삭제)
            session.query(SystemLog).filter(SystemLog.message.like('%Database connection test log entry%')).delete()
            session.query(Strategy).filter(Strategy.name.like('Test MA Crossover%')).delete()
            session.query(Portfolio).filter(Portfolio.name.like('Test Portfolio%')).delete()
            session.commit()
            logger.info("✅ Cleaned up existing test data")
            # 1. SystemLog 생성 테스트 (가장 간단한 모델)
            test_log = SystemLog(
                level="INFO",
                logger_name="test_database_connection",
                message="Database connection test log entry",
                context={"test": True, "timestamp": datetime.now(timezone.utc).isoformat()}
            )
            
            session.add(test_log)
            session.commit()
            
            logger.info(f"✅ Created SystemLog with ID: {test_log.id}")
            
            # 2. 생성한 로그 조회 테스트
            retrieved_log = session.query(SystemLog).filter_by(id=test_log.id).first()
            
            if retrieved_log:
                logger.info(f"✅ Retrieved SystemLog: {retrieved_log.message}")
            else:
                logger.error("❌ Failed to retrieve created SystemLog")
                return False
            
            # 3. Portfolio 생성 테스트
            test_portfolio = Portfolio(
                name="Test Portfolio",
                currency="USDT",
                total_capital=10000.0,
                available_capital=10000.0,
                is_active=True
            )
            
            session.add(test_portfolio)
            session.commit()
            
            logger.info(f"✅ Created Portfolio with ID: {test_portfolio.id}")
            
            # 4. Strategy 생성 테스트
            test_strategy = Strategy(
                name="Test MA Crossover",
                strategy_type="MA_CROSSOVER",
                exchange="binance",
                symbol="BTC/USDT",
                parameters={"fast_period": 10, "slow_period": 20},
                portfolio_id=test_portfolio.id,
                is_active=False
            )
            
            session.add(test_strategy)
            session.commit()
            
            logger.info(f"✅ Created Strategy with ID: {test_strategy.id}")
            
            # 5. 관계 조회 테스트
            portfolio_with_strategies = session.query(Portfolio).filter_by(id=test_portfolio.id).first()
            strategies_count = len(portfolio_with_strategies.strategies)
            
            logger.info(f"✅ Portfolio has {strategies_count} strategies")
            
            # 6. 정리 (테스트 데이터 삭제)
            session.delete(test_strategy)
            session.delete(test_portfolio)
            session.delete(test_log)
            session.commit()
            
            logger.info("✅ Test data cleaned up")
        
        logger.info("✅ All CRUD operations completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ CRUD operations test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_state_reconciliation_with_db():
    """상태 조정 엔진의 데이터베이스 연동 테스트"""
    logger.info("🔄 Testing state reconciliation with database...")
    
    try:
        from common.state_reconciliation import StateReconciliationEngine
        from unittest.mock import MagicMock
        
        # Mock components
        from unittest.mock import AsyncMock
        exchange_connector = AsyncMock()
        exchange_connector.get_account_balance.return_value = {
            'USDT': MagicMock(total=10000.0, free=9500.0, locked=500.0)
        }
        exchange_connector.get_open_orders.return_value = []
        exchange_connector.config = MagicMock()
        exchange_connector.config.exchange_name = "binance_testnet"
        
        capital_manager = AsyncMock()
        
        # Create reconciliation engine
        reconciliation_engine = StateReconciliationEngine(
            exchange_connector=exchange_connector,
            capital_manager=capital_manager
        )
        
        # Perform reconciliation
        reconciliation_report = await reconciliation_engine.perform_full_reconciliation()
        
        logger.info(f"📊 Reconciliation with database:")
        logger.info(f"   - Session ID: {reconciliation_report.session_id}")
        logger.info(f"   - Status: {reconciliation_report.status.value}")
        logger.info(f"   - Total discrepancies: {len(reconciliation_report.discrepancies)}")
        logger.info(f"   - Duration: {(reconciliation_report.end_time - reconciliation_report.start_time).total_seconds():.2f}s")
        
        # Check if system logs were created
        with db_manager.get_session() as session:
            recent_logs = session.query(SystemLog)\
                .filter(SystemLog.logger_name == "StateReconciliation")\
                .order_by(SystemLog.timestamp.desc())\
                .limit(5)\
                .all()
            
            logger.info(f"✅ Found {len(recent_logs)} reconciliation logs in database")
            for log in recent_logs:
                logger.info(f"   - {log.level}: {log.message}")
        
        logger.info("✅ State reconciliation with database completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ State reconciliation with database failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """메인 테스트 실행"""
    logger.info("🚀 Starting Database Connection Tests")
    logger.info("=" * 60)
    
    try:
        # Test 1: Database connection
        if not await test_database_connection():
            logger.error("❌ Database connection test failed - stopping tests")
            return
        
        logger.info("-" * 60)
        
        # Test 2: Table accessibility
        if not await test_database_tables():
            logger.error("❌ Database tables test failed - stopping tests")
            return
        
        logger.info("-" * 60)
        
        # Test 3: CRUD operations
        if not await test_basic_crud_operations():
            logger.error("❌ CRUD operations test failed")
            return
        
        logger.info("-" * 60)
        
        # Test 4: State reconciliation with database
        if not await test_state_reconciliation_with_db():
            logger.error("❌ State reconciliation test failed")
            return
        
        logger.info("=" * 60)
        logger.info("🎉 All database tests completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Database tests failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        # Cleanup: disconnect from database
        try:
            await db_manager.async_disconnect()
            logger.info("🔌 Database disconnected")
        except Exception as e:
            logger.warning(f"⚠️ Error disconnecting from database: {e}")


if __name__ == "__main__":
    # Run the async tests
    asyncio.run(main())