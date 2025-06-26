#!/usr/bin/env python3
"""
기존 텔레그램 봇 시스템 테스트

src/telegram_interface/main.py에 구현된 완전한 텔레그램 봇 시스템을 
실제 자격증명으로 테스트합니다.
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


async def test_existing_telegram_bot():
    """기존 텔레그램 봇 시스템 테스트"""
    
    print("🤖 기존 텔레그램 봇 시스템 테스트")
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
    
    # 봇 설정 구성 (MessageBus 설정 포함)
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
        
        logger.info("🚀 텔레그램 봇 인스턴스 생성...")
        bot = TelegramBot(config)
        
        logger.info("📡 텔레그램 봇 시작...")
        
        # 봇 시작 시도
        if await bot.start():
            logger.info("✅ 텔레그램 봇 시작 성공!")
            
            # 웰컴 메시지 전송 (실제 API 사용)
            welcome_message = f"""
🚀 **Letrade V1 텔레그램 봇 테스트 성공!**

✅ **연결 상태:**
• 봇 토큰: 유효
• 채팅 연결: 성공
• 명령어 핸들러: 활성화

🤖 **사용 가능한 명령어:**
• /start - 봇 시작 및 환영 메시지
• /help - 명령어 도움말
• /status - 시스템 상태 조회
• /portfolio - 포트폴리오 현황
• /strategies - 전략 목록
• /profit - 수익률 분석

🔧 **시스템 정보:**
• 인증 사용자: {len(config['auth']['allowed_users'])}명
• 레이트 제한: {config['max_commands_per_window']}명령/{config['rate_limit_window']}초
• 메시지 버스: 연결 준비

⚡ **테스트 완료 시간:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

이제 텔레그램에서 /start 명령어를 입력해보세요!
            """
            
            # 봇 인스턴스를 통해 메시지 전송
            if bot.application and bot.application.bot:
                await bot.application.bot.send_message(
                    chat_id=int(chat_id),
                    text=welcome_message,
                    parse_mode='Markdown'
                )
                logger.info("📱 웰컴 메시지 전송 완료!")
            
            # 3초간 실행하여 명령어 테스트 가능하게 함
            logger.info("⏰ 3초간 봇 실행 중... 텔레그램에서 /start 명령어를 테스트해보세요!")
            await asyncio.sleep(3)
            
            # 봇 중지
            logger.info("🛑 텔레그램 봇 중지...")
            await bot.stop()
            
            logger.info("✅ 텔레그램 봇 테스트 완료!")
            return True
            
        else:
            logger.error("❌ 텔레그램 봇 시작 실패")
            return False
            
    except ImportError as e:
        logger.error(f"❌ 텔레그램 모듈 임포트 실패: {e}")
        logger.error("   필요한 패키지가 설치되지 않았을 수 있습니다:")
        logger.error("   pip install python-telegram-bot")
        return False
        
    except Exception as e:
        logger.error(f"❌ 텔레그램 봇 테스트 실패: {e}")
        return False


async def main():
    """메인 실행 함수"""
    success = await test_existing_telegram_bot()
    
    if success:
        print("\n🎉 텔레그램 봇 테스트 성공!")
        print("📱 이제 텔레그램 앱에서 다음 명령어들을 테스트해보세요:")
        print("   • /start - 봇 시작")
        print("   • /help - 도움말")
        print("   • /status - 시스템 상태")
        print("   • /portfolio - 포트폴리오")
        print("   • /strategies - 전략 목록")
    else:
        print("\n❌ 텔레그램 봇 테스트 실패")
        print("🔧 문제 해결 방법:")
        print("   1. .env.telegram 파일의 봇 토큰 확인")
        print("   2. 채팅 ID 확인")
        print("   3. 필요한 패키지 설치: pip install python-telegram-bot")


if __name__ == "__main__":
    asyncio.run(main())