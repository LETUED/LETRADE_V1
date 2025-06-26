#!/usr/bin/env python3
"""
Letrade_v1 텔레그램 메시지 테스트 스크립트

실제 텔레그램 봇 토큰 없이도 텔레그램 메시지 발송 기능을 테스트합니다.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
import sys

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class TelegramTestBot:
    """텔레그램 봇 테스트 시뮬레이터"""
    
    def __init__(self, bot_token: str = "demo_token", chat_id: str = "demo_chat"):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.is_running = False
        
    async def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """메시지 전송 시뮬레이션"""
        try:
            # 실제 API 호출 대신 시뮬레이션
            await asyncio.sleep(0.1)  # 네트워크 지연 시뮬레이션
            
            logger.info("📱 텔레그램 메시지 전송:")
            logger.info(f"   봇 토큰: {self.bot_token[:10]}...")
            logger.info(f"   채팅 ID: {self.chat_id}")
            logger.info(f"   메시지: {message[:100]}...")
            logger.info("   ✅ 전송 성공 (시뮬레이션)")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 메시지 전송 실패: {e}")
            return False
    
    async def send_system_status(self):
        """시스템 상태 메시지 전송"""
        message = """
🚀 <b>Letrade V1 시스템 상태</b>

📊 <b>실시간 성능:</b>
• 평균 레이턴시: <code>1.921ms</code>
• 시스템 가용성: <code>99.90%</code>
• 메모리 사용량: <code>8.6MB</code>
• CPU 사용률: <code>2.4%</code>

💰 <b>포트폴리오:</b>
• 총 자본: <code>$100.00</code>
• 가용 잔고: <code>$98.19</code>
• 오늘 P&L: <code>-$1.81 (-1.81%)</code>

📈 <b>활성 전략:</b>
• MA Crossover (이동평균 교차)
• 상태: <code>실행 중</code>
• 오늘 거래: <code>2회</code>

🕐 <b>업데이트 시간:</b> {timestamp}
        """.format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        return await self.send_message(message)
    
    async def send_trade_notification(self, trade_type: str = "BUY"):
        """거래 알림 메시지 전송"""
        if trade_type == "BUY":
            message = """
📈 <b>매수 주문 체결</b>

🔸 <b>거래 정보:</b>
• 심볼: <code>BTCUSDT</code>
• 수량: <code>0.00002 BTC</code>
• 가격: <code>$49,950.00</code>
• 총액: <code>$1.00</code>

💡 <b>전략:</b> MA Crossover
⚡ <b>신호:</b> 골든 크로스 감지

🕐 <b>체결 시간:</b> {timestamp}
            """.format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        else:
            message = """
📉 <b>매도 주문 체결</b>

🔸 <b>거래 정보:</b>
• 심볼: <code>BTCUSDT</code>
• 수량: <code>0.00002 BTC</code>
• 가격: <code>$50,050.00</code>
• 총액: <code>$1.00</code>

💡 <b>전략:</b> MA Crossover
⚡ <b>신호:</b> 데드 크로스 감지
💰 <b>수익:</b> <code>+$2.00 (+0.2%)</code>

🕐 <b>체결 시간:</b> {timestamp}
            """.format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        return await self.send_message(message)
    
    async def send_risk_alert(self):
        """리스크 경고 메시지 전송"""
        message = """
🚨 <b>리스크 경고</b>

⚠️ <b>일일 손실 한도 접근</b>

📊 <b>현재 상태:</b>
• 일일 손실: <code>$2.81</code>
• 한도: <code>$5.00</code>
• 사용률: <code>56.2%</code>

🛡️ <b>자동 조치:</b>
• 포지션 크기 축소
• 추가 거래 제한
• 실시간 모니터링 강화

⏰ <b>알림 시간:</b> {timestamp}

👥 관리자 승인 없이는 추가 거래가 제한됩니다.
        """.format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        return await self.send_message(message)
    
    async def send_portfolio_update(self):
        """포트폴리오 업데이트 메시지 전송"""
        message = """
💼 <b>포트폴리오 업데이트</b>

📊 <b>계정 요약:</b>
• 총 자산: <code>$100.00</code>
• 가용 잔고: <code>$98.19</code>
• 포지션 가치: <code>$1.81</code>

📈 <b>오늘 성과:</b>
• 거래 횟수: <code>2회</code>
• 승률: <code>50.0%</code>
• P&L: <code>-$1.81 (-1.81%)</code>

🔍 <b>포지션 상세:</b>
• BTCUSDT Long: <code>0.00002 BTC</code>
• 진입 가격: <code>$50,000.00</code>
• 현재 가격: <code>$49,950.00</code>
• 미실현 손익: <code>-$1.00</code>

🕐 <b>업데이트:</b> {timestamp}
        """.format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        return await self.send_message(message)
    
    async def send_system_startup(self):
        """시스템 시작 메시지 전송"""
        message = """
🟢 <b>Letrade V1 시스템 시작</b>

✅ <b>초기화 완료:</b>
• Core Engine: <code>정상</code>
• Exchange Connector: <code>연결됨</code>
• Strategy Worker: <code>활성화</code>
• Capital Manager: <code>준비됨</code>

🎯 <b>전략 상태:</b>
• MA Crossover: <code>실행 중</code>
• 리스크 관리: <code>활성화</code>
• 모니터링: <code>24/7 감시</code>

🔧 <b>시스템 설정:</b>
• 모드: <code>드라이런</code>
• 자본: <code>$100.00</code>
• 최대 손실 한도: <code>$5.00</code>

🕐 <b>시작 시간:</b> {timestamp}

🚀 시스템이 정상적으로 시작되었습니다!
        """.format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        return await self.send_message(message)


class TelegramTestSuite:
    """텔레그램 메시지 테스트 스위트"""
    
    def __init__(self):
        self.bot = TelegramTestBot()
    
    async def run_all_tests(self):
        """모든 메시지 테스트 실행"""
        logger.info("🤖 텔레그램 메시지 테스트 시작...")
        
        test_scenarios = [
            ("시스템 시작 메시지", self.bot.send_system_startup),
            ("시스템 상태 업데이트", self.bot.send_system_status),
            ("매수 거래 알림", lambda: self.bot.send_trade_notification("BUY")),
            ("매도 거래 알림", lambda: self.bot.send_trade_notification("SELL")),
            ("포트폴리오 업데이트", self.bot.send_portfolio_update),
            ("리스크 경고", self.bot.send_risk_alert),
        ]
        
        results = []
        
        for i, (test_name, test_func) in enumerate(test_scenarios, 1):
            logger.info(f"📝 테스트 {i}/6: {test_name}")
            
            try:
                success = await test_func()
                results.append((test_name, success))
                
                if success:
                    logger.info(f"   ✅ 성공")
                else:
                    logger.error(f"   ❌ 실패")
                
                # 메시지 간 간격
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"   💥 오류: {e}")
                results.append((test_name, False))
        
        # 결과 요약
        self.print_test_summary(results)
    
    def print_test_summary(self, results):
        """테스트 결과 요약 출력"""
        logger.info("📊 텔레그램 메시지 테스트 결과:")
        logger.info("=" * 50)
        
        success_count = 0
        for test_name, success in results:
            status = "✅ 성공" if success else "❌ 실패"
            logger.info(f"   {test_name}: {status}")
            if success:
                success_count += 1
        
        logger.info("=" * 50)
        logger.info(f"📈 총 {len(results)}개 테스트 중 {success_count}개 성공")
        logger.info(f"📊 성공률: {(success_count/len(results)*100):.1f}%")
        
        if success_count == len(results):
            logger.info("🎉 모든 텔레그램 메시지 테스트 통과!")
        else:
            logger.warning("⚠️ 일부 테스트 실패")


async def main():
    """메인 실행 함수"""
    print("🤖 Letrade V1 텔레그램 메시지 테스트")
    print("=" * 60)
    print("이 테스트는 실제 텔레그램 봇 없이 메시지 발송을 시뮬레이션합니다.")
    print("=" * 60)
    
    # 테스트 스위트 실행
    test_suite = TelegramTestSuite()
    await test_suite.run_all_tests()
    
    print("\n🔔 실제 텔레그램 봇 설정 방법:")
    print("1. @BotFather에서 새 봇 생성")
    print("2. 봇 토큰을 환경 변수에 설정")
    print("3. 채팅 ID 확인 후 설정")
    print("4. src/telegram_interface/main.py 실행")


if __name__ == "__main__":
    asyncio.run(main())