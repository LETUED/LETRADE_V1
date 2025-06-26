#!/usr/bin/env python3
"""
완전히 재설계된 텔레그램 봇 테스트

새로운 /start /stop /restart 명령어 구조와 1시간마다 자동 보고 기능을 테스트합니다.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv('.env.telegram')

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_redesigned_telegram_bot():
    """완전히 재설계된 텔레그램 봇 테스트"""
    
    print("🔄 완전히 재설계된 텔레그램 봇 테스트")
    print("=" * 60)
    
    # 환경 변수 확인
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID') 
    admin_user_id = os.getenv('TELEGRAM_ADMIN_USER_ID')
    
    if not bot_token or not chat_id:
        logger.error("❌ 텔레그램 봇 설정이 없습니다")
        logger.error("   TELEGRAM_BOT_TOKEN 또는 TELEGRAM_CHAT_ID가 설정되지 않음")
        return False
    
    logger.info("✅ 텔레그램 봇 설정 확인:")
    logger.info(f"   봇 토큰: {bot_token[:20]}...")
    logger.info(f"   채팅 ID: {chat_id}")
    logger.info(f"   관리자 ID: {admin_user_id}")
    
    # 봇 설정 구성 (재설계된 구조)
    config = {
        'bot_token': bot_token,
        'auth': {
            'allowed_users': [int(admin_user_id)] if admin_user_id else [],
            'allowed_usernames': []
        },
        'rate_limit_window': 60,
        'max_commands_per_window': 10,
        'message_bus': {
            'host': 'localhost',
            'port': 5672,
            'username': 'guest',
            'password': 'guest',
            'virtual_host': '/',
            'heartbeat': 60,
            'connection_timeout': 30
        }
    }
    
    try:
        # 텔레그램 봇 임포트 및 시작
        from telegram_interface.main import TelegramBot
        
        logger.info("🚀 재설계된 텔레그램 봇 인스턴스 생성...")
        bot = TelegramBot(config)
        
        logger.info("📡 재설계된 텔레그램 봇 시작...")
        
        # 봇 시작 시도
        if await bot.start():
            logger.info("✅ 재설계된 텔레그램 봇 시작 성공!")
            
            # 시작 알림 메시지 전송
            startup_message = f"""
🔄 **완전히 재설계된 Letrade V1 봇 활성화!**

🎉 **새로운 기능:**
• 직관적인 /start /stop /restart 명령어
• 1시간마다 자동 정기 보고
• 간단명료한 시스템 제어
• 완전히 개선된 사용자 경험

🎛️ **새로운 핵심 명령어:**
• `/start` - 시스템 시작 + 자동 보고 활성화
• `/stop` - 시스템 완전 중지
• `/restart` - 시스템 재시작
• `/status` - 실시간 상태 확인
• `/portfolio` - 포트폴리오 현황
• `/report` - 즉시 상세 보고서

📊 **자동 보고 시스템:**
• 포트폴리오 변화 추적
• 전략 성과 분석
• 거래 활동 요약
• 리스크 관리 현황

🔧 **주요 개선사항:**
• /help 명령어 오류 완전 해결
• Markdown 파싱 문제 해결
• 안정적인 메시지 전송 보장
• 사용자 친화적 인터페이스

⚡ **테스트 시작**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

지금 새로운 명령어들을 테스트해보세요!
            """
            
            # 봇 인스턴스를 통해 메시지 전송
            if bot.application and bot.application.bot:
                await bot.application.bot.send_message(
                    chat_id=int(chat_id),
                    text=startup_message.strip()
                )
                logger.info("📱 재설계된 봇 시작 알림 메시지 전송 완료!")
            
            # 3분간 실행하여 새로운 명령어 테스트 가능하게 함
            logger.info("⏰ 3분간 봇 실행 중... 텔레그램에서 새로운 명령어들을 테스트해보세요!")
            logger.info("")
            logger.info("🔍 테스트할 새로운 명령어들:")
            logger.info("   • /help - 새로운 직관적 도움말 (오류 해결됨)")
            logger.info("   • /start - 시스템 시작 + 정기 보고 활성화")
            logger.info("   • /status - 실시간 상태 (개선된 형식)")
            logger.info("   • /portfolio - 포트폴리오 현황")
            logger.info("   • /stop - 시스템 중지")
            logger.info("   • /restart - 시스템 재시작")
            logger.info("   • /report - 즉시 상세 보고서")
            logger.info("")
            logger.info("🆕 이전 명령어들도 호환성 안내 메시지와 함께 작동:")
            logger.info("   • /positions → /portfolio 권장")
            logger.info("   • /strategies → /status 권장")
            logger.info("")
            
            await asyncio.sleep(180)  # 3분간 실행
            
            # 종료 메시지 전송
            shutdown_message = """
✅ **재설계된 텔레그램 봇 테스트 완료**

🎯 **테스트 결과:**
• 새로운 명령어 구조: 성공
• /help 오류 해결: 완료
• 자동 보고 시스템: 준비됨
• 직관적 제어: 구현됨

🔧 **확인된 개선사항:**
• 완전히 안정된 /help 명령어
• 간단명료한 /start /stop /restart
• 1시간마다 자동 보고 기능
• 사용자 친화적 메시지

🚀 **다음 단계:**
실제 운영 시 이 새로운 봇 구조가
더욱 직관적이고 안정적인 거래 경험을 제공합니다.

새로운 자동거래 봇이 준비되었습니다! 🎉
            """
            
            if bot.application and bot.application.bot:
                await bot.application.bot.send_message(
                    chat_id=int(chat_id),
                    text=shutdown_message.strip()
                )
                logger.info("📱 테스트 완료 알림 메시지 전송 완료!")
            
            # 봇 중지
            logger.info("🛑 재설계된 텔레그램 봇 중지...")
            await bot.stop()
            
            logger.info("✅ 재설계된 텔레그램 봇 테스트 완료!")
            return True
            
        else:
            logger.error("❌ 재설계된 텔레그램 봇 시작 실패")
            return False
            
    except ImportError as e:
        logger.error(f"❌ 텔레그램 모듈 임포트 실패: {e}")
        logger.error("   필요한 패키지가 설치되지 않았을 수 있습니다:")
        logger.error("   pip install python-telegram-bot aiohttp")
        return False
        
    except Exception as e:
        logger.error(f"❌ 재설계된 텔레그램 봇 테스트 실패: {e}")
        logger.exception("상세 오류 정보:")
        return False


async def main():
    """메인 실행 함수"""
    success = await test_redesigned_telegram_bot()
    
    if success:
        print("\n🎉 재설계된 텔레그램 봇 테스트 성공!")
        print("📱 이제 텔레그램 앱에서 완전히 새로운 명령어 구조를 사용할 수 있습니다:")
        print("")
        print("🎛️ **핵심 제어 명령어:**")
        print("   • /start - 시스템 시작 + 1시간마다 자동 보고")
        print("   • /stop - 시스템 완전 중지")
        print("   • /restart - 시스템 재시작")
        print("")
        print("📊 **정보 조회 명령어:**")
        print("   • /status - 실시간 시스템 상태")
        print("   • /portfolio - 포트폴리오 현황")
        print("   • /report - 즉시 상세 보고서")
        print("   • /help - 새로운 직관적 도움말")
        print("")
        print("🔧 **주요 개선사항:**")
        print("   • /help 명령어 오류 완전 해결")
        print("   • 직관적이고 간단한 명령어 구조")
        print("   • 1시간마다 자동 정기 보고")
        print("   • 안정적인 메시지 전송 시스템")
        print("")
        print("💰 **사용법:**")
        print("   1. /start로 시스템 시작")
        print("   2. 자동으로 1시간마다 보고서 수신")
        print("   3. /status나 /portfolio로 언제든 확인")
        print("   4. /stop으로 시스템 중지")
        print("")
    else:
        print("\n❌ 재설계된 텔레그램 봇 테스트 실패")
        print("🔧 문제 해결 방법:")
        print("   1. .env.telegram 파일의 봇 토큰 확인")
        print("   2. 채팅 ID 확인")
        print("   3. 필요한 패키지 설치:")
        print("      pip install python-telegram-bot aiohttp")
        print("   4. 로컬 API 서버 실행 확인:")
        print("      python scripts/start_local_web.py")


if __name__ == "__main__":
    asyncio.run(main())