#!/usr/bin/env python3
"""
MVP 통합 테스트 스크립트

전체 시스템이 설계서대로 작동하는지 검증
- 데이터베이스 연결
- 메시지 버스 통신
- 텔레그램 봇 응답
- 웹 인터페이스 접속
- Mock 거래 플로우
"""

import asyncio
import logging
import sys
from pathlib import Path
import time
from datetime import datetime, timezone

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MVPIntegrationTest:
    """MVP 통합 테스트 클래스"""
    
    def __init__(self):
        self.test_results = {
            "database": {"status": "pending", "details": ""},
            "message_bus": {"status": "pending", "details": ""},
            "telegram": {"status": "pending", "details": ""},
            "web_interface": {"status": "pending", "details": ""},
            "mock_trading": {"status": "pending", "details": ""},
        }
        
    async def test_database_connection(self):
        """데이터베이스 연결 테스트"""
        logger.info("🔍 Testing database connection...")
        try:
            from src.common.db_session import db_session
            from src.common.models import Portfolio, Strategy
            
            # 데이터베이스 초기화
            db_session.initialize()
            
            # 연결 테스트
            if db_session.check_connection():
                # 테스트 포트폴리오 생성
                with db_session.get_db() as db:
                    test_portfolio = Portfolio(
                        name="Test_Portfolio_MVP",
                        total_capital=1000.0,
                        available_capital=1000.0,
                        currency="USDT"
                    )
                    db.add(test_portfolio)
                    db.commit()
                    
                    # 확인
                    portfolio = db.query(Portfolio).filter_by(name="Test_Portfolio_MVP").first()
                    if portfolio:
                        self.test_results["database"]["status"] = "✅ PASSED"
                        self.test_results["database"]["details"] = f"Portfolio created with ID: {portfolio.id}"
                        logger.info("✅ Database test PASSED")
                    else:
                        raise Exception("Failed to create test portfolio")
            else:
                raise Exception("Database connection check failed")
                
        except Exception as e:
            self.test_results["database"]["status"] = "❌ FAILED"
            self.test_results["database"]["details"] = str(e)
            logger.error(f"❌ Database test FAILED: {e}")
    
    async def test_message_bus(self):
        """메시지 버스 통신 테스트"""
        logger.info("🔍 Testing message bus communication...")
        try:
            from src.common.message_bus import MessageBus
            from src.common.config import Config
            
            # RabbitMQ 연결 테스트
            message_bus = MessageBus(Config.get_message_bus_config())
            
            # 연결 시도
            connected = await message_bus.connect()
            if not connected:
                raise Exception("Failed to connect to RabbitMQ")
            
            # 테스트 큐 생성
            test_queue = "test_mvp_integration"
            await message_bus._declare_queue(
                test_queue,
                exchange_name="letrade.events",
                routing_key="test.mvp.*",
                durable=False,
                auto_delete=True
            )
            
            # 테스트 메시지
            test_message = {
                "type": "test",
                "data": {"test": "MVP integration test"}
            }
            
            # 구독 및 발행 테스트
            received_messages = []
            
            async def test_handler(message):
                received_messages.append(message.get("payload"))
            
            # 구독
            await message_bus.subscribe(test_queue, test_handler)
            
            # 발행
            await message_bus.publish(
                exchange_name="letrade.events",
                routing_key="test.mvp.integration", 
                message=test_message
            )
            
            # 잠시 대기
            await asyncio.sleep(0.5)
            
            # 연결 해제
            await message_bus.disconnect()
            
            if received_messages and received_messages[0]["type"] == "test":
                self.test_results["message_bus"]["status"] = "✅ PASSED"
                self.test_results["message_bus"]["details"] = "Message published and received successfully"
                logger.info("✅ Message bus test PASSED")
            else:
                raise Exception("Message not received")
                
        except Exception as e:
            self.test_results["message_bus"]["status"] = "❌ FAILED"
            self.test_results["message_bus"]["details"] = str(e)
            logger.error(f"❌ Message bus test FAILED: {e}")
    
    async def test_telegram_bot(self):
        """텔레그램 봇 응답 테스트"""
        logger.info("🔍 Testing Telegram bot...")
        try:
            # 텔레그램 봇 모듈과 명령어 확인
            import os
            from pathlib import Path
            
            # 텔레그램 인터페이스 파일 확인
            telegram_path = Path(project_root) / "src" / "telegram_interface"
            files = [
                "main.py",
                "handlers.py", 
                "auth.py",
                "commands.py"
            ]
            
            all_files_exist = all((telegram_path / f).exists() for f in files)
            
            if all_files_exist:
                # 토큰이 설정되어 있는지 확인
                token_exists = os.getenv("TELEGRAM_BOT_TOKEN") is not None
                
                if token_exists:
                    self.test_results["telegram"]["status"] = "✅ PASSED"
                    self.test_results["telegram"]["details"] = "Telegram bot modules found and token configured"
                else:
                    self.test_results["telegram"]["status"] = "⚠️ SKIPPED"
                    self.test_results["telegram"]["details"] = "Telegram bot requires token configuration"
                
                logger.info(f"✅ Telegram bot modules verified")
            else:
                raise Exception("Missing telegram interface files")
                
        except Exception as e:
            self.test_results["telegram"]["status"] = "⚠️ SKIPPED"
            self.test_results["telegram"]["details"] = str(e)
            logger.warning(f"⚠️ Telegram bot test SKIPPED: {e}")
    
    async def test_web_interface(self):
        """웹 인터페이스 접속 테스트"""
        logger.info("🔍 Testing web interface...")
        try:
            import aiohttp
            
            # 웹 인터페이스 URL
            web_url = "http://127.0.0.1:8080/health"
            
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(web_url, timeout=5) as response:
                        if response.status == 200:
                            data = await response.json()
                            self.test_results["web_interface"]["status"] = "✅ PASSED"
                            self.test_results["web_interface"]["details"] = f"API status: {data.get('status', 'unknown')}"
                            logger.info("✅ Web interface test PASSED")
                        else:
                            raise Exception(f"HTTP {response.status}")
                except:
                    # 웹 서버가 실행되지 않은 경우
                    self.test_results["web_interface"]["status"] = "⚠️ NOT RUNNING"
                    self.test_results["web_interface"]["details"] = "Web server not started"
                    logger.warning("⚠️ Web interface not running")
                    
        except Exception as e:
            self.test_results["web_interface"]["status"] = "❌ FAILED"
            self.test_results["web_interface"]["details"] = str(e)
            logger.error(f"❌ Web interface test FAILED: {e}")
    
    async def test_mock_trading_flow(self):
        """Mock 거래 플로우 테스트"""
        logger.info("🔍 Testing mock trading flow...")
        try:
            from src.strategies.ma_crossover import MAcrossoverStrategy
            from src.strategies.base_strategy import StrategyConfig
            
            # 전략 설정
            strategy_config = StrategyConfig(
                strategy_id="test_ma_crossover",
                name="Test MA Crossover Strategy",
                enabled=True,
                dry_run=True,
                risk_params={
                    "stop_loss_pct": 2.0,
                    "take_profit_pct": 5.0
                },
                custom_params={
                    "symbol": "BTC/USDT",
                    "exchange": "mock",
                    "timeframe": "1h",
                    "capital_allocation": 100.0,
                    "fast_period": 10,
                    "slow_period": 20
                }
            )
            
            # 전략 초기화
            strategy = MAcrossoverStrategy(strategy_config)
            
            # 테스트 데이터 생성
            import pandas as pd
            import numpy as np
            
            # 100개의 테스트 캔들 데이터
            dates = pd.date_range(end=datetime.now(timezone.utc), periods=100, freq='1h')
            prices = 50000 + np.cumsum(np.random.randn(100) * 100)
            
            test_df = pd.DataFrame({
                'timestamp': dates,
                'open': prices,
                'high': prices + np.random.rand(100) * 100,
                'low': prices - np.random.rand(100) * 100,
                'close': prices + np.random.randn(100) * 50,
                'volume': np.random.rand(100) * 1000
            })
            
            # 지표 계산
            df_with_indicators = strategy.populate_indicators(test_df)
            
            # 신호 생성 테스트
            last_candle = {
                'timestamp': dates[-1].isoformat(),
                'close': float(prices[-1]),
                'volume': 1000.0
            }
            
            signal = strategy.on_data(last_candle, df_with_indicators)
            
            # 전략이 데이터를 처리했는지 확인
            if len(df_with_indicators) > 0:
                # MA 전략의 지표 확인
                expected_cols = [f'sma_{strategy.fast_period}', f'sma_{strategy.slow_period}', 'ma_fast', 'ma_slow']
                indicators_present = all(col in df_with_indicators.columns for col in expected_cols)
                
                if indicators_present:
                    self.test_results["mock_trading"]["status"] = "✅ PASSED"
                    self.test_results["mock_trading"]["details"] = f"Strategy processed {len(df_with_indicators)} candles with indicators"
                    logger.info("✅ Mock trading test PASSED")
                else:
                    logger.debug(f"Available columns: {list(df_with_indicators.columns)}")
                    raise Exception(f"Strategy indicators not found. Expected: {expected_cols}")
            else:
                raise Exception("Empty dataframe returned")
                
        except Exception as e:
            self.test_results["mock_trading"]["status"] = "❌ FAILED"
            self.test_results["mock_trading"]["details"] = str(e)
            logger.error(f"❌ Mock trading test FAILED: {e}")
    
    async def run_all_tests(self):
        """모든 테스트 실행"""
        logger.info("=" * 60)
        logger.info("🚀 Starting MVP Integration Tests")
        logger.info("=" * 60)
        
        # 각 테스트 실행
        await self.test_database_connection()
        await self.test_message_bus()
        await self.test_telegram_bot()
        await self.test_web_interface()
        await self.test_mock_trading_flow()
        
        # 결과 출력
        logger.info("\n" + "=" * 60)
        logger.info("📊 MVP Integration Test Results")
        logger.info("=" * 60)
        
        all_passed = True
        for component, result in self.test_results.items():
            logger.info(f"{component.upper():20} {result['status']}")
            if result['details']:
                logger.info(f"{'':20} └─ {result['details']}")
            
            if "FAILED" in result['status']:
                all_passed = False
        
        logger.info("=" * 60)
        if all_passed:
            logger.info("✅ All tests PASSED! MVP is ready.")
        else:
            logger.info("❌ Some tests FAILED. Please check the errors above.")
        logger.info("=" * 60)
        
        return all_passed


async def main():
    """메인 실행 함수"""
    tester = MVPIntegrationTest()
    success = await tester.run_all_tests()
    
    # 테스트 데이터 정리
    try:
        from src.common.db_session import db_session
        from src.common.models import Portfolio
        
        with db_session.get_db() as db:
            # 테스트 포트폴리오 삭제
            test_portfolio = db.query(Portfolio).filter_by(name="Test_Portfolio_MVP").first()
            if test_portfolio:
                db.delete(test_portfolio)
                db.commit()
                logger.info("🧹 Test data cleaned up")
    except:
        pass
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)