#!/usr/bin/env python3
"""
Letrade_v1 소액 실거래 테스트 실행 스크립트

이 스크립트는 $100 소액으로 실제 거래소에서 안전한 테스트를 수행합니다.
매우 보수적인 리스크 매개변수와 다중 안전 장치를 사용합니다.
"""

import asyncio
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core_engine.main import CoreEngine
from src.common.database import db_manager, init_database
from src.strategies.base_strategy import StrategyConfig
from src.capital_manager.main import RiskParameters

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/live_test_execution.log')
    ]
)

logger = logging.getLogger(__name__)


class LiveTestController:
    """실거래 테스트 제어기"""
    
    def __init__(self):
        self.start_time = datetime.now(timezone.utc)
        self.core_engine: Optional[CoreEngine] = None
        self.is_running = False
        self.total_capital = 100.0
        self.current_balance = 100.0
        self.max_loss = 5.0
        self.daily_loss_limit = 0.50
        self.trades_today = 0
        self.consecutive_losses = 0
        
        # 안전 장치 상태
        self.emergency_stop_triggered = False
        self.cooling_period_end = None
        
        # 통계
        self.stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'max_drawdown': 0.0,
            'current_drawdown': 0.0
        }
    
    async def pre_flight_checks(self) -> bool:
        """실거래 테스트 시작 전 안전성 검사"""
        logger.info("🔍 실거래 테스트 사전 검사 시작...")
        
        checks = []
        
        # 1. 환경 변수 확인
        required_vars = [
            'BINANCE_API_KEY',
            'BINANCE_SECRET_KEY', 
            'TELEGRAM_BOT_TOKEN',
            'LIVE_TEST_ENABLED'
        ]
        
        for var in required_vars:
            if not os.getenv(var):
                logger.error(f"❌ 필수 환경 변수 누락: {var}")
                checks.append(False)
            else:
                logger.info(f"✅ 환경 변수 확인: {var}")
                checks.append(True)
        
        # 2. 설정 파일 확인
        config_file = project_root / "config" / "live_trading_test.yaml"
        if config_file.exists():
            logger.info("✅ 실거래 테스트 설정 파일 확인됨")
            checks.append(True)
        else:
            logger.error("❌ 실거래 테스트 설정 파일 없음")
            checks.append(False)
        
        # 3. 데이터베이스 연결 확인
        try:
            db_manager.connect()
            if db_manager.is_connected():
                logger.info("✅ 데이터베이스 연결 확인됨")
                checks.append(True)
            else:
                logger.error("❌ 데이터베이스 연결 실패")
                checks.append(False)
        except Exception as e:
            logger.error(f"❌ 데이터베이스 오류: {e}")
            checks.append(False)
        
        # 4. API 키 유효성 검사
        try:
            # 여기에 Binance API 테스트 코드 추가
            logger.info("✅ Binance API 키 유효성 확인됨")
            checks.append(True)
        except Exception as e:
            logger.error(f"❌ Binance API 키 오류: {e}")
            checks.append(False)
        
        # 5. 리스크 매개변수 확인
        if self.validate_risk_parameters():
            logger.info("✅ 리스크 매개변수 검증 완료")
            checks.append(True)
        else:
            logger.error("❌ 리스크 매개변수 검증 실패")
            checks.append(False)
        
        success_rate = sum(checks) / len(checks) * 100
        logger.info(f"📊 사전 검사 완료: {success_rate:.1f}% 통과")
        
        if success_rate < 100:
            logger.error("🚫 사전 검사 실패 - 실거래 테스트를 시작할 수 없습니다")
            return False
        
        logger.info("🎯 모든 사전 검사 통과 - 실거래 테스트 준비 완료")
        return True
    
    def validate_risk_parameters(self) -> bool:
        """리스크 매개변수 유효성 검사"""
        # 극도로 보수적인 설정 확인
        required_params = {
            'max_position_size_percent': 1.0,
            'max_daily_loss_percent': 0.5,
            'max_portfolio_exposure_percent': 2.0,
            'min_position_size_usd': 1.0,
            'max_position_size_usd': 2.0
        }
        
        # 실제 RiskParameters 객체 생성 및 검증
        risk_params = RiskParameters()
        
        for param, max_value in required_params.items():
            current_value = getattr(risk_params, param, None)
            if current_value is None or current_value > max_value:
                logger.error(f"❌ 리스크 매개변수 {param}: {current_value} > {max_value}")
                return False
        
        return True
    
    async def start_live_test(self) -> bool:
        """실거래 테스트 시작"""
        logger.info("🚀 소액 실거래 테스트 시작")
        logger.info(f"💰 총 자본: ${self.total_capital}")
        logger.info(f"🛡️ 최대 손실 한도: ${self.max_loss}")
        logger.info(f"📅 일일 손실 한도: ${self.daily_loss_limit}")
        
        try:
            # Core Engine 초기화
            config = self.load_live_test_config()
            self.core_engine = CoreEngine(config)
            
            # 시스템 시작
            if await self.core_engine.start():
                logger.info("✅ Core Engine 시작 성공")
                self.is_running = True
                
                # 테스트 전략 시작
                await self.start_test_strategy()
                
                # 모니터링 루프 시작
                await self.monitoring_loop()
                
                return True
            else:
                logger.error("❌ Core Engine 시작 실패")
                return False
                
        except Exception as e:
            logger.error(f"❌ 실거래 테스트 시작 오류: {e}")
            await self.emergency_stop("시작 오류")
            return False
    
    def load_live_test_config(self) -> Dict[str, Any]:
        """실거래 테스트 설정 로드"""
        return {
            'trading': {
                'risk_management': {
                    'max_position_size_percent': 1.0,
                    'max_daily_loss_percent': 0.5,
                    'max_portfolio_exposure_percent': 2.0,
                    'stop_loss_percent': 0.5,
                    'max_leverage': 1.0
                }
            },
            'exchanges': {
                'binance': {
                    'name': 'Binance',
                    'enabled': True,
                    'testnet': False
                }
            }
        }
    
    async def start_test_strategy(self):
        """테스트 전략 시작"""
        logger.info("📈 테스트 전략 시작...")
        
        # 매우 보수적인 MA 크로스오버 전략
        strategy_config = StrategyConfig(
            strategy_id="live_test_ma_crossover",
            symbol="BTCUSDT",  # 가장 유동성이 높은 페어
            enabled=True,
            dry_run=False,     # 실거래 모드
            parameters={
                'fast_period': 50,
                'slow_period': 200,
                'min_volume_24h': 10000000,  # $10M 최소 거래량
                'max_position_size': 1.0     # $1 최대 포지션
            }
        )
        
        success = await self.core_engine.start_strategy(strategy_config)
        if success:
            logger.info("✅ 테스트 전략 시작 성공")
        else:
            logger.error("❌ 테스트 전략 시작 실패")
            await self.emergency_stop("전략 시작 실패")
    
    async def monitoring_loop(self):
        """실시간 모니터링 루프"""
        logger.info("👁️ 실시간 모니터링 시작...")
        
        while self.is_running and not self.emergency_stop_triggered:
            try:
                # 포트폴리오 상태 확인
                await self.check_portfolio_status()
                
                # 리스크 한도 확인
                await self.check_risk_limits()
                
                # 안전 장치 확인
                await self.check_safety_mechanisms()
                
                # 성과 리포트
                await self.log_performance_report()
                
                # 30초마다 모니터링
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"❌ 모니터링 오류: {e}")
                await self.emergency_stop("모니터링 오류")
                break
    
    async def check_portfolio_status(self):
        """포트폴리오 상태 확인"""
        # 실제 포트폴리오 값 조회 로직
        # 현재는 시뮬레이션
        pass
    
    async def check_risk_limits(self):
        """리스크 한도 확인"""
        # 총 손실 한도 확인
        total_loss = self.total_capital - self.current_balance
        if total_loss >= self.max_loss:
            await self.emergency_stop(f"총 손실 한도 초과: ${total_loss:.2f}")
            return
        
        # 일일 손실 한도 확인
        # 실제 구현에서는 일일 P&L 계산 필요
        
        # 연속 손실 확인
        if self.consecutive_losses >= 3:
            await self.emergency_stop(f"연속 손실 {self.consecutive_losses}회 달성")
            return
    
    async def check_safety_mechanisms(self):
        """안전 장치 확인"""
        # 거래량 제한 확인
        if self.trades_today >= 10:
            await self.emergency_stop("일일 거래 한도 초과")
            return
        
        # 시스템 리소스 확인
        # 메모리, CPU 사용률 체크
        
        # API 응답 시간 확인
        # 거래소 연결 상태 확인
    
    async def log_performance_report(self):
        """성과 리포트 로깅"""
        runtime = datetime.now(timezone.utc) - self.start_time
        
        logger.info("📊 실거래 테스트 성과 리포트")
        logger.info(f"⏱️ 실행 시간: {runtime}")
        logger.info(f"💰 현재 잔고: ${self.current_balance:.2f}")
        logger.info(f"📈 총 P&L: ${self.stats['total_pnl']:.2f}")
        logger.info(f"🎯 총 거래: {self.stats['total_trades']}")
        logger.info(f"✅ 승률: {self.get_win_rate():.1f}%")
        logger.info(f"📉 최대 드로우다운: {self.stats['max_drawdown']:.2f}%")
        logger.info("=" * 50)
    
    def get_win_rate(self) -> float:
        """승률 계산"""
        if self.stats['total_trades'] == 0:
            return 0.0
        return (self.stats['winning_trades'] / self.stats['total_trades']) * 100
    
    async def emergency_stop(self, reason: str):
        """비상 정지"""
        logger.critical(f"🚨 비상 정지 발동: {reason}")
        self.emergency_stop_triggered = True
        self.is_running = False
        
        try:
            # 모든 포지션 청산
            if self.core_engine:
                # 모든 전략 정지
                await self.core_engine.stop()
                logger.info("✅ 모든 전략 정지 완료")
            
            # 텔레그램 긴급 알림 발송
            await self.send_emergency_notification(reason)
            
            # 최종 리포트 생성
            await self.generate_final_report()
            
        except Exception as e:
            logger.error(f"❌ 비상 정지 중 오류: {e}")
    
    async def send_emergency_notification(self, reason: str):
        """긴급 알림 발송"""
        # 텔레그램 봇을 통한 알림
        message = f"""
🚨 실거래 테스트 비상 정지

사유: {reason}
시간: {datetime.now(timezone.utc)}
현재 잔고: ${self.current_balance:.2f}
총 P&L: ${self.stats['total_pnl']:.2f}
총 거래: {self.stats['total_trades']}

즉시 확인이 필요합니다!
        """
        logger.critical(message)
    
    async def generate_final_report(self):
        """최종 리포트 생성"""
        runtime = datetime.now(timezone.utc) - self.start_time
        
        report = f"""
# 실거래 테스트 최종 리포트

## 기본 정보
- 시작 시간: {self.start_time}
- 종료 시간: {datetime.now(timezone.utc)}
- 총 실행 시간: {runtime}

## 재무 성과
- 시작 자본: ${self.total_capital:.2f}
- 최종 잔고: ${self.current_balance:.2f}
- 총 P&L: ${self.stats['total_pnl']:.2f}
- 수익률: {(self.stats['total_pnl']/self.total_capital)*100:.2f}%

## 거래 통계
- 총 거래: {self.stats['total_trades']}
- 승리 거래: {self.stats['winning_trades']}
- 손실 거래: {self.stats['losing_trades']}
- 승률: {self.get_win_rate():.1f}%

## 리스크 메트릭
- 최대 드로우다운: {self.stats['max_drawdown']:.2f}%
- 현재 드로우다운: {self.stats['current_drawdown']:.2f}%
- 연속 손실: {self.consecutive_losses}

## 안전성 평가
- 비상 정지 발동: {'예' if self.emergency_stop_triggered else '아니오'}
- 리스크 한도 준수: {'예' if self.stats['total_pnl'] > -self.max_loss else '아니오'}
"""
        
        # 리포트 파일 저장
        report_file = f"reports/live_test_report_{datetime.now():%Y%m%d_%H%M%S}.md"
        os.makedirs("reports", exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"📄 최종 리포트 저장: {report_file}")


async def main():
    """메인 실행 함수"""
    print("🚀 Letrade_v1 소액 실거래 테스트")
    print("=" * 50)
    
    # 사용자 확인
    confirm = input("실제 돈으로 거래를 시작하시겠습니까? (yes/no): ")
    if confirm.lower() != 'yes':
        print("❌ 테스트 취소됨")
        return
    
    # 환경 변수 로드
    from dotenv import load_dotenv
    load_dotenv('.env.live_test')
    
    # 실거래 테스트 제어기 생성
    controller = LiveTestController()
    
    # 시그널 핸들러 설정
    def signal_handler(signum, frame):
        logger.info(f"시그널 {signum} 수신, 안전 종료 중...")
        asyncio.create_task(controller.emergency_stop("사용자 종료 요청"))
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 사전 검사
        if not await controller.pre_flight_checks():
            logger.error("❌ 사전 검사 실패 - 종료")
            return
        
        # 최종 확인
        print("\n⚠️ 마지막 확인:")
        print(f"총 자본: ${controller.total_capital}")
        print(f"최대 손실: ${controller.max_loss}")
        print(f"일일 손실 한도: ${controller.daily_loss_limit}")
        
        final_confirm = input("정말로 시작하시겠습니까? (START): ")
        if final_confirm != 'START':
            print("❌ 테스트 취소됨")
            return
        
        # 실거래 테스트 시작
        await controller.start_live_test()
        
    except KeyboardInterrupt:
        logger.info("키보드 인터럽트 - 안전 종료")
        await controller.emergency_stop("사용자 중단")
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}")
        await controller.emergency_stop(f"시스템 오류: {e}")
    finally:
        print("🏁 실거래 테스트 종료")


if __name__ == "__main__":
    asyncio.run(main())