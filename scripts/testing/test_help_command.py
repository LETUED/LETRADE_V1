#!/usr/bin/env python3
"""
/help 명령어 테스트

텔레그램 봇의 /help 명령어가 제대로 작동하는지 테스트합니다.
"""

import asyncio
import logging
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# 환경 변수 로드
load_dotenv('.env.telegram')

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """수정된 /help 명령어 테스트"""
    help_message = """📚 *Letrade V1 명령어 가이드*

🔍 *시스템 조회 명령어:*
/status - 전체 시스템 상태 조회
/portfolio - 포트폴리오 현황 및 잔고
/positions - 현재 보유 포지션 목록
/strategies - 활성 전략 목록 및 상태

🎛️ *시스템 제어 명령어:*
/start\\_strategy [ID] - 특정 전략 시작
/stop\\_strategy [ID] - 특정 전략 중지

📈 *성과 분석 명령어:*
/profit [period] - 수익률 조회
   period: today, week, month (기본값: today)

ℹ️ *기타 명령어:*
/help - 이 도움말 표시
/start - 봇 시작 및 환영 메시지

💡 *사용 팁:*
• 명령어는 대소문자를 구분하지 않습니다
• [ID]는 전략 번호를 의미합니다 (예: /stop\\_strategy 1)
• 시스템은 실시간으로 거래 알림을 전송합니다

🆘 *문제가 있나요?*
시스템 오류나 문의사항이 있으시면 관리자에게 연락해 주세요.

안전한 거래 되세요! 🛡️"""
    
    try:
        await update.message.reply_text(help_message, parse_mode='Markdown')
        logger.info("✅ /help 명령어 성공적으로 전송됨")
    except Exception as e:
        logger.error(f"❌ /help 명령어 전송 실패: {e}")
        # 폴백: HTML 모드로 시도
        help_message_html = """📚 <b>Letrade V1 명령어 가이드</b>

🔍 <b>시스템 조회 명령어:</b>
/status - 전체 시스템 상태 조회
/portfolio - 포트폴리오 현황 및 잔고
/positions - 현재 보유 포지션 목록
/strategies - 활성 전략 목록 및 상태

🎛️ <b>시스템 제어 명령어:</b>
/start_strategy [ID] - 특정 전략 시작
/stop_strategy [ID] - 특정 전략 중지

📈 <b>성과 분석 명령어:</b>
/profit [period] - 수익률 조회
   period: today, week, month (기본값: today)

ℹ️ <b>기타 명령어:</b>
/help - 이 도움말 표시
/start - 봇 시작 및 환영 메시지

💡 <b>사용 팁:</b>
• 명령어는 대소문자를 구분하지 않습니다
• [ID]는 전략 번호를 의미합니다 (예: /stop_strategy 1)
• 시스템은 실시간으로 거래 알림을 전송합니다

🆘 <b>문제가 있나요?</b>
시스템 오류나 문의사항이 있으시면 관리자에게 연락해 주세요.

안전한 거래 되세요! 🛡️"""
        
        try:
            await update.message.reply_text(help_message_html, parse_mode='HTML')
            logger.info("✅ /help 명령어 HTML 모드로 성공적으로 전송됨")
        except Exception as e2:
            logger.error(f"❌ HTML 모드도 실패: {e2}")
            # 마지막 폴백: 일반 텍스트
            await update.message.reply_text(
                "📚 Letrade V1 명령어 가이드\n\n"
                "🔍 시스템 조회 명령어:\n"
                "/status - 전체 시스템 상태 조회\n"
                "/portfolio - 포트폴리오 현황\n"
                "/strategies - 활성 전략 목록\n\n"
                "🎛️ 시스템 제어 명령어:\n"
                "/start_strategy [ID] - 전략 시작\n"
                "/stop_strategy [ID] - 전략 중지\n\n"
                "📈 성과 분석:\n"
                "/profit [period] - 수익률 조회\n\n"
                "안전한 거래 되세요! 🛡️"
            )
            logger.info("✅ /help 명령어 일반 텍스트로 전송됨")


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """간단한 /start 명령어"""
    await update.message.reply_text(
        "🚀 Letrade V1 텔레그램 봇에 오신 것을 환영합니다!\n\n"
        "/help 명령어를 입력하여 사용 가능한 명령어를 확인하세요."
    )


async def main():
    """메인 함수"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        logger.error("❌ TELEGRAM_BOT_TOKEN 환경 변수가 설정되지 않았습니다")
        return
    
    logger.info("🤖 /help 명령어 테스트 봇 시작...")
    
    # 애플리케이션 생성
    application = Application.builder().token(bot_token).build()
    
    # 핸들러 등록
    application.add_handler(CommandHandler("help", handle_help))
    application.add_handler(CommandHandler("start", handle_start))
    
    try:
        # 봇 시작
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        logger.info("✅ 봇이 시작되었습니다!")
        logger.info("📱 텔레그램에서 /help 명령어를 테스트해보세요.")
        logger.info("⏰ 30초간 실행됩니다...")
        
        # 30초간 실행
        await asyncio.sleep(30)
        
    except KeyboardInterrupt:
        logger.info("🛑 사용자 요청으로 봇을 중지합니다...")
    finally:
        # 봇 정지
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        logger.info("✅ 봇이 정지되었습니다.")


if __name__ == "__main__":
    asyncio.run(main())