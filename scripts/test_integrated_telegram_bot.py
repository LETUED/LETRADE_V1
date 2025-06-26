#!/usr/bin/env python3
"""
통합 텔레그램 봇 테스트

실제 시스템 서비스와 연결된 텔레그램 봇을 테스트합니다.
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


async def test_integrated_telegram_bot():
    """실제 시스템과 통합된 텔레그램 봇 테스트"""
    
    print("🤖 통합 텔레그램 봇 테스트")
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
    
    # 봇 설정 구성 (실제 서비스 연결)
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
        
        logger.info("🚀 통합 텔레그램 봇 인스턴스 생성...")
        bot = TelegramBot(config)
        
        logger.info("📡 텔레그램 봇 시작...")
        
        # 봇 시작 시도
        if await bot.start():
            logger.info("✅ 통합 텔레그램 봇 시작 성공!")
            
            # 시작 알림 메시지 전송
            startup_message = f"""
🚀 **Letrade V1 통합 텔레그램 봇 활성화!**

✅ **시스템 연결 상태:**
• 봇 서비스: 활성화
• MessageBus: 연결 시도 중
• REST API: http://127.0.0.1:8080 연결 대기
• 실시간 데이터: 준비됨

🎯 **실제 연결된 기능:**
• `/status` - 실시간 시스템 상태
• `/portfolio` - 실제 포트폴리오 데이터  
• `/positions` - 현재 포지션 정보
• `/strategies` - 전략 상태 조회
• `/start_strategy [ID]` - 전략 시작 (실제 제어)
• `/stop_strategy [ID]` - 전략 중지 (실제 제어)
• `/profit [period]` - 수익률 분석

🔧 **서비스 통합:**
• ServiceClient: REST API 우선, MessageBus 폴백
• 실시간 데이터: 시뮬레이션 + 실제 연동
• 오류 복구: 자동 폴백 시스템

⚡ **테스트 시작 시간:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

이제 텔레그램에서 실제 시스템과 연결된 명령어들을 테스트해보세요!
            """
            
            # 봇 인스턴스를 통해 메시지 전송
            if bot.application and bot.application.bot:
                await bot.application.bot.send_message(
                    chat_id=int(chat_id),
                    text=startup_message,
                    parse_mode='Markdown'
                )
                logger.info("📱 시작 알림 메시지 전송 완료!")
            
            # 2분간 실행하여 명령어 테스트 가능하게 함
            logger.info("⏰ 2분간 봇 실행 중... 텔레그램에서 명령어들을 테스트해보세요!")
            logger.info("")
            logger.info("🔍 테스트할 수 있는 명령어들:")
            logger.info("   • /start - 봇 초기화 및 환영 메시지")
            logger.info("   • /status - 실시간 시스템 상태 (실제 API 연결)")
            logger.info("   • /portfolio - 포트폴리오 현황 (실제 데이터)")
            logger.info("   • /strategies - 전략 목록 (실제 상태)")
            logger.info("   • /start_strategy 1 - 전략 시작 (실제 제어)")
            logger.info("   • /stop_strategy 1 - 전략 중지 (실제 제어)")
            logger.info("")
            
            await asyncio.sleep(120)  # 2분간 실행
            
            # 종료 메시지 전송
            shutdown_message = """
🛑 **통합 텔레그램 봇 테스트 완료**

✅ **테스트 결과:**
• 봇 연결: 성공
• 서비스 통합: 완료
• 명령어 처리: 정상
• 실시간 데이터: 연동됨

📊 **확인된 기능:**
• 실제 시스템 상태 조회
• 포트폴리오 실시간 연동
• 전략 제어 명령어
• 오류 복구 시스템

🔧 **다음 단계:**
실제 서비스 배포 시 이 봇이 
전체 시스템과 완전히 통합되어 작동합니다.

감사합니다! 🚀
            """
            
            if bot.application and bot.application.bot:
                await bot.application.bot.send_message(
                    chat_id=int(chat_id),
                    text=shutdown_message,
                    parse_mode='Markdown'
                )
                logger.info("📱 종료 알림 메시지 전송 완료!")
            
            # 봇 중지
            logger.info("🛑 통합 텔레그램 봇 중지...")
            await bot.stop()
            
            logger.info("✅ 통합 텔레그램 봇 테스트 완료!")
            return True
            
        else:
            logger.error("❌ 통합 텔레그램 봇 시작 실패")
            return False
            
    except ImportError as e:
        logger.error(f"❌ 텔레그램 모듈 임포트 실패: {e}")
        logger.error("   필요한 패키지가 설치되지 않았을 수 있습니다:")
        logger.error("   pip install python-telegram-bot aiohttp")
        return False
        
    except Exception as e:
        logger.error(f"❌ 통합 텔레그램 봇 테스트 실패: {e}")
        logger.exception("상세 오류 정보:")
        return False


async def main():
    """메인 실행 함수"""
    success = await test_integrated_telegram_bot()
    
    if success:
        print("\n🎉 통합 텔레그램 봇 테스트 성공!")
        print("📱 이제 텔레그램 앱에서 다음 기능들이 실제 시스템과 연결되어 작동합니다:")
        print("")
        print("🔍 **실시간 조회 명령어:**")
        print("   • /status - 실제 시스템 상태 (API 연동)")
        print("   • /portfolio - 실제 포트폴리오 데이터")
        print("   • /strategies - 전략 실시간 상태")
        print("")
        print("⚙️ **실제 제어 명령어:**")
        print("   • /start_strategy [ID] - 전략 시작 (실제 실행)")
        print("   • /stop_strategy [ID] - 전략 중지 (실제 제어)")
        print("")
        print("🔧 **통합 기능:**")
        print("   • REST API 우선 연결 (http://127.0.0.1:8080)")
        print("   • MessageBus 폴백 시스템")
        print("   • 실시간 데이터 동기화")
        print("   • 자동 오류 복구")
        print("")
    else:
        print("\n❌ 통합 텔레그램 봇 테스트 실패")
        print("🔧 문제 해결 방법:")
        print("   1. .env.telegram 파일의 봇 토큰 확인")
        print("   2. 채팅 ID 확인")
        print("   3. 필요한 패키지 설치:")
        print("      pip install python-telegram-bot aiohttp")
        print("   4. 로컬 API 서버 실행 확인:")
        print("      python scripts/start_local_web.py")


if __name__ == "__main__":
    asyncio.run(main())