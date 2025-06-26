#!/usr/bin/env python3
"""
긴급 상황 텔레그램 알림 메시지 테스트

시스템에 정의된 긴급 상황별 메시지들을 테스트합니다.
NotificationLevel: LOW, MEDIUM, HIGH, CRITICAL
NotificationCategory: TRADE_EXECUTION, SYSTEM_ALERT, PERFORMANCE, ERROR, STRATEGY, PORTFOLIO
"""

import asyncio
import aiohttp
import logging
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv('.env.telegram')

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class EmergencyNotificationTester:
    """긴급 상황 알림 테스터"""
    
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.session = None
        
        if not self.bot_token or not self.chat_id:
            raise ValueError("TELEGRAM_BOT_TOKEN과 TELEGRAM_CHAT_ID가 필요합니다")
    
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.session:
            await self.session.close()
    
    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """메시지 전송"""
        url = f"{self.api_url}/sendMessage"
        
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': parse_mode
        }
        
        try:
            async with self.session.post(url, json=payload) as response:
                data = await response.json()
                
                if data.get('ok'):
                    logger.info(f"✅ 긴급 알림 전송 성공")
                    return True
                else:
                    logger.error(f"❌ 메시지 전송 실패: {data}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ 메시지 전송 중 오류: {e}")
            return False
    
    async def send_critical_system_error(self) -> bool:
        """🚨 CRITICAL - 시스템 오류"""
        message = f"""
🚨 🔧 <b>시스템 오류</b>

<b>구성요소:</b> Core Engine
<b>오류:</b> API 연결 실패 - 연속 5회 오류 발생

조치가 필요할 수 있습니다.

🕐 {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC
        """
        return await self.send_message(message.strip())
    
    async def send_critical_portfolio_risk(self) -> bool:
        """🚨 CRITICAL - 포트폴리오 위험"""
        message = f"""
🚨 💼 <b>포트폴리오 변동: -15.25%</b>

<b>현재 가치:</b> $8,475.00

포트폴리오에 상당한 변동이 있었습니다.

🕐 {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC
        """
        return await self.send_message(message.strip())
    
    async def send_critical_trade_error(self) -> bool:
        """🚨 CRITICAL - 거래 실행 오류"""
        message = f"""
🔴 💰 <b>거래 실행 오류</b>

<b>구성요소:</b> Exchange Connector
<b>오류:</b> Order placement failed - Insufficient balance

조치가 필요할 수 있습니다.

🕐 {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC
        """
        return await self.send_message(message.strip())
    
    async def send_high_stop_loss_triggered(self) -> bool:
        """🔴 HIGH - 손절매 발동"""
        message = f"""
🔴 💰 <b>매도 완료</b>

📉 <b>손절매 발동</b>

<b>거래 정보:</b>
• 심볼: BTC/USDT
• 수량: 0.001500
• 가격: $48,500.00
• 손실: -$75.00 (-1.5%)
• 전략: #1 MA Crossover

거래가 성공적으로 체결되었습니다.

🕐 {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC
        """
        return await self.send_message(message.strip())
    
    async def send_high_strategy_stopped(self) -> bool:
        """⚠️ HIGH - 전략 중지"""
        message = f"""
⚠️ 🎯 <b>전략 stopped</b>

<b>전략 ID:</b> 1
<b>전략명:</b> MA Crossover
<b>이벤트:</b> 연속 손실 3회로 인한 자동 중지

전략 상태가 변경되었습니다.

🕐 {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC
        """
        return await self.send_message(message.strip())
    
    async def send_high_liquidation_warning(self) -> bool:
        """🚨 HIGH - 청산 위험 경고"""
        message = f"""
🚨 ⚠️ <b>청산 위험 경고</b>

<b>포지션:</b> BTCUSDT Long
<b>현재 손실:</b> -$4.75 (-4.75%)
<b>청산가:</b> $47,500.00 (현재가: $48,250.00)
<b>거리:</b> $750.00 (1.55%)

<b>⚡ 자동 조치:</b>
• 포지션 크기 50% 축소
• 추가 거래 일시 중단
• 실시간 모니터링 강화

즉각적인 조치가 필요할 수 있습니다.

🕐 {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC
        """
        return await self.send_message(message.strip())
    
    async def send_high_risk_limit_breach(self) -> bool:
        """🚨 HIGH - 리스크 한도 위반"""
        message = f"""
🚨 🛡️ <b>리스크 한도 위반</b>

<b>위반 유형:</b> 일일 손실 한도 초과
<b>현재 손실:</b> $5.25
<b>설정 한도:</b> $5.00
<b>초과 금액:</b> $0.25 (5% 초과)

<b>🛑 자동 조치 실행:</b>
• 모든 신규 거래 중단
• 기존 포지션 유지 (수동 관리)
• 관리자 승인 필요

즉시 확인이 필요합니다.

🕐 {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC
        """
        return await self.send_message(message.strip())
    
    async def send_medium_trade_execution(self) -> bool:
        """⚠️ MEDIUM - 거래 실행 성공"""
        message = f"""
💰 <b>매수 완료</b>

📈 <b>매수 완료</b>

<b>거래 정보:</b>
• 심볼: BTC/USDT
• 수량: 0.000200
• 가격: $50,125.00
• 총액: $10.03
• 전략: #1 MA Crossover

거래가 성공적으로 체결되었습니다.

🕐 {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC
        """
        return await self.send_message(message.strip())
    
    async def send_medium_performance_alert(self) -> bool:
        """⚠️ MEDIUM - 성능 경고"""
        message = f"""
⚠️ 📈 <b>성능 경고</b>

<b>지표:</b> 평균 응답 시간
<b>현재값:</b> 250ms
<b>임계값:</b> 200ms
<b>상태:</b> 25% 초과

성능 모니터링이 필요합니다.

🕐 {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC
        """
        return await self.send_message(message.strip())
    
    async def send_emergency_halt_notification(self) -> bool:
        """🚨 CRITICAL - 긴급 정지"""
        message = f"""
🚨 🛑 <b>긴급 정지 실행</b>

<b>명령자:</b> @{os.getenv('TELEGRAM_ADMIN_USER_ID', 'admin')}
<b>실행 시간:</b> {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC

<b>🛑 시스템 상태:</b>
• 모든 거래 중단: ✅ 완료
• 신규 주문 차단: ✅ 완료
• 포지션 보호: ✅ 활성화
• 시스템 잠금: ✅ 완료

<b>⚠️ 현재 포지션:</b>
• BTCUSDT Long: 유지됨 (수동 관리)
• 자동 스톱로스: 계속 활성화

<b>🔄 재시작 방법:</b>
관리자 승인 후 /emergency_resume 명령어 사용

<b>📞 긴급 연락:</b>
시스템이 안전 모드로 전환되었습니다.

🕐 {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC
        """
        return await self.send_message(message.strip())
    
    async def send_state_reconciliation_error(self) -> bool:
        """🚨 CRITICAL - 상태 조정 오류"""
        message = f"""
🚨 🔄 <b>상태 조정 오류</b>

<b>심각도:</b> CRITICAL
<b>구성요소:</b> State Reconciliation
<b>문제:</b> 시스템-거래소 포지션 불일치

<b>📊 감지된 차이:</b>
• 시스템: 0.00200 BTC
• 거래소: 0.00150 BTC  
• 차이: 0.00050 BTC ($25.00)

<b>🛑 자동 조치:</b>
• 거래 일시 중단
• 수동 검토 필요
• 데이터 무결성 검사 실행

즉시 관리자 개입이 필요합니다.

🕐 {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC
        """
        return await self.send_message(message.strip())


async def main():
    """메인 실행 함수"""
    print("🚨 긴급 상황 텔레그램 알림 메시지 테스트")
    print("=" * 60)
    
    try:
        async with EmergencyNotificationTester() as tester:
            logger.info("🚀 긴급 알림 테스트 시작...")
            
            emergency_scenarios = [
                ("🚨 CRITICAL - 시스템 오류", tester.send_critical_system_error),
                ("🚨 CRITICAL - 포트폴리오 위험", tester.send_critical_portfolio_risk),
                ("🚨 CRITICAL - 거래 실행 오류", tester.send_critical_trade_error),
                ("🚨 CRITICAL - 긴급 정지", tester.send_emergency_halt_notification),
                ("🚨 CRITICAL - 상태 조정 오류", tester.send_state_reconciliation_error),
                ("🔴 HIGH - 손절매 발동", tester.send_high_stop_loss_triggered),
                ("⚠️ HIGH - 전략 중지", tester.send_high_strategy_stopped),
                ("🚨 HIGH - 청산 위험 경고", tester.send_high_liquidation_warning),
                ("🚨 HIGH - 리스크 한도 위반", tester.send_high_risk_limit_breach),
                ("⚠️ MEDIUM - 거래 실행", tester.send_medium_trade_execution),
                ("⚠️ MEDIUM - 성능 경고", tester.send_medium_performance_alert),
            ]
            
            results = []
            
            for i, (scenario_name, test_func) in enumerate(emergency_scenarios, 1):
                logger.info(f"📝 테스트 {i}/{len(emergency_scenarios)}: {scenario_name}")
                
                try:
                    success = await test_func()
                    results.append((scenario_name, success))
                    
                    if success:
                        logger.info(f"   ✅ 성공")
                    else:
                        logger.error(f"   ❌ 실패")
                    
                    # 메시지 간 간격 (텔레그램 속도 제한 고려)
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"   💥 오류: {e}")
                    results.append((scenario_name, False))
            
            # 결과 요약
            print_test_summary(results)
            
    except Exception as e:
        logger.error(f"❌ 긴급 알림 테스트 실패: {e}")


def print_test_summary(results):
    """테스트 결과 요약 출력"""
    logger.info("📊 긴급 알림 테스트 결과:")
    logger.info("=" * 60)
    
    success_count = 0
    for scenario_name, success in results:
        status = "✅ 성공" if success else "❌ 실패"
        logger.info(f"   {scenario_name}: {status}")
        if success:
            success_count += 1
    
    logger.info("=" * 60)
    logger.info(f"📈 총 {len(results)}개 테스트 중 {success_count}개 성공")
    logger.info(f"📊 성공률: {(success_count/len(results)*100):.1f}%")
    
    if success_count == len(results):
        logger.info("🎉 모든 긴급 알림 테스트 통과!")
        logger.info("📱 텔레그램 앱에서 긴급 메시지들을 확인해보세요!")
    else:
        logger.warning("⚠️ 일부 테스트 실패")
    
    print("\n🔔 긴급 상황 알림 시스템 정보:")
    print("• 우선순위: CRITICAL > HIGH > MEDIUM > LOW")
    print("• 자동 필터링: 중복 방지, 속도 제한")
    print("• 긴급 명령어: /emergency_halt, /emergency_resume")
    print("• 상태 조정: 실시간 모니터링 및 자동 복구")


if __name__ == "__main__":
    asyncio.run(main())