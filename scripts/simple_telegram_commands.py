#!/usr/bin/env python3
"""
간단한 텔레그램 명령어 봇 테스트

MessageBus 없이 기본적인 텔레그램 명령어들을 테스트합니다.
"""

import asyncio
import logging
import os
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 환경 변수 로드
load_dotenv('.env.telegram')

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class SimpleBot:
    """간단한 텔레그램 명령어 봇"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.application = Application.builder().token(bot_token).build()
        self.is_running = False
        
        # 명령어 핸들러 등록
        self._register_handlers()
    
    def _register_handlers(self):
        """명령어 핸들러 등록"""
        self.application.add_handler(CommandHandler("start", self.handle_start))
        self.application.add_handler(CommandHandler("help", self.handle_help))
        self.application.add_handler(CommandHandler("status", self.handle_status))
        self.application.add_handler(CommandHandler("portfolio", self.handle_portfolio))
        self.application.add_handler(CommandHandler("strategies", self.handle_strategies))
        self.application.add_handler(CommandHandler("profit", self.handle_profit))
        self.application.add_handler(MessageHandler(filters.COMMAND, self.handle_unknown))
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """시작 명령어"""
        user = update.effective_user
        message = f"""
🚀 **Letrade V1 자동 거래 시스템**

안녕하세요, {user.first_name}님!

Letrade V1 시스템에 성공적으로 연결되었습니다.
이 봇을 통해 거래 시스템을 모니터링하고 제어할 수 있습니다.

**주요 기능:**
• 📊 시스템 상태 실시간 모니터링
• 💼 포트폴리오 및 포지션 조회
• 🔧 전략 시작/중지 제어
• 📈 수익률 및 성과 분석
• 🔔 실시간 거래 알림

**시작하기:**
/help - 모든 명령어 보기
/status - 시스템 상태 확인
/portfolio - 포트폴리오 현황

⚠️ **보안 알림**: 이 시스템은 실제 자금을 다룹니다. 
명령어 사용 시 신중하게 확인해 주세요.

행복한 거래 되세요! 💰
        """
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """도움말 명령어"""
        message = """
📚 **Letrade V1 명령어 가이드**

**🔍 시스템 조회 명령어:**
/status - 전체 시스템 상태 조회
/portfolio - 포트폴리오 현황 및 잔고
/strategies - 활성 전략 목록 및 상태

**📈 성과 분석 명령어:**
/profit [period] - 수익률 조회
   - period: today, week, month (기본값: today)

**ℹ️ 기타 명령어:**
/help - 이 도움말 표시
/start - 봇 시작 및 환영 메시지

**💡 사용 팁:**
• 명령어는 대소문자를 구분하지 않습니다
• 시스템은 실시간으로 거래 알림을 전송합니다

**🆘 문제가 있나요?**
시스템 오류나 문의사항이 있으시면 관리자에게 연락해 주세요.

안전한 거래 되세요! 🛡️
        """
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """상태 조회 명령어"""
        message = f"""
🟢 **시스템 상태: 정상**

**📊 핵심 지표:**
• 시스템 가동률: 8.92시간 (99.90%)
• 활성 전략 수: 1개
• 연결된 거래소: 1개 (Binance)
• 메시지 버스: 🟢 연결됨

**💼 포트폴리오:**
• 총 자산: $100.00
• 가용 자금: $98.19
• 진행 중인 거래: 0개

**⚡ 성능:**
• 평균 응답 시간: 1.921ms
• 초당 처리량: 31,989회

**🎯 활성 전략:**
• MA Crossover (이동평균 교차)
• 상태: 실행 중 (드라이런 모드)
• 오늘 거래: 0회

🕐 마지막 업데이트: {datetime.now().strftime('%H:%M:%S')}
        """
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def handle_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """포트폴리오 조회 명령어"""
        message = f"""
💼 **포트폴리오 현황**

**📊 계정 요약:**
• 총 자산: $100.00
• 가용 잔고: $98.19
• 포지션 가치: $1.81
• 미실현 손익: -$1.81 (-1.81%)

**💰 자산 구성:**
• USDT: $98.19 (98.19%)
• BTC: 0.00002 BTC ($1.81)

**📈 오늘 성과:**
• 거래 횟수: 2회
• 승률: 50.0%
• 실현 손익: $0.00
• 수수료: $0.02

**🔍 포지션 상세:**
• BTCUSDT Long: 0.00002 BTC
• 진입 가격: $50,000.00
• 현재 가격: $49,950.00
• 미실현 손익: -$1.00 (-2.0%)

**⚠️ 리스크 관리:**
• 일일 손실 한도: $5.00
• 현재 손실: $1.81 (36.2%)
• 위험도: 낮음

🕐 업데이트: {datetime.now().strftime('%H:%M:%S')}
        """
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def handle_strategies(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """전략 조회 명령어"""
        message = f"""
🎯 **전략 상태 현황**

**📈 활성 전략:**

**1. MA Crossover (이동평균 교차)**
• 상태: 🟢 실행 중
• 모드: 드라이런
• 심볼: BTCUSDT
• 시간프레임: 1분

**전략 성과:**
• 오늘 신호: 3회
• 체결된 거래: 2회
• 승률: 50.0%
• 수익률: -1.81%

**리스크 설정:**
• 포지션 크기: 1% (최대 $1.00)
• 스톱로스: 2%
• 테이크프로핏: 3%

**📊 기술적 지표:**
• MA 7: $49,980.00
• MA 25: $50,020.00
• 상태: 베어리시 크로스

**⚙️ 전략 설정:**
• 자동 매매: 활성화
• 리스크 관리: 엄격
• 알림: 모든 신호

**🔄 마지막 신호:**
• 시간: 14:32:15
• 유형: 매도 신호
• 강도: 중간

🕐 업데이트: {datetime.now().strftime('%H:%M:%S')}
        """
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def handle_profit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """수익률 조회 명령어"""
        period = 'today'
        if context.args and context.args[0].lower() in ['today', 'week', 'month']:
            period = context.args[0].lower()
        
        period_korean = {
            'today': '오늘',
            'week': '이번 주',
            'month': '이번 달'
        }
        
        message = f"""
📈 **{period_korean[period]} 수익률 분석**

**💰 손익 요약:**
• 시작 자본: $100.00
• 현재 자산: $98.19
• 실현 손익: $0.00
• 미실현 손익: -$1.81
• 총 손익: -$1.81 (-1.81%)

**📊 거래 통계:**
• 총 거래 횟수: 2회
• 매수: 1회
• 매도: 1회
• 승률: 50.0%

**📈 성과 지표:**
• 최대 수익: +$2.00 (+2.0%)
• 최대 손실: -$1.81 (-1.81%)
• 평균 거래: -$0.91
• 수익 팩터: 0.52

**⚡ 효율성:**
• 샤프 비율: -0.12
• 최대 낙폭: -1.81%
• 복구 시간: 진행 중

**🎯 목표 대비:**
• 일일 목표: +1.0%
• 현재 상태: -1.81%
• 목표 달성률: -181%

**🔍 세부 거래:**
1. BTCUSDT 매수: $1.00 → 미실현
2. 수수료: -$0.02

🕐 분석 시간: {datetime.now().strftime('%H:%M:%S')}
        """
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def handle_unknown(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """알 수 없는 명령어"""
        await update.message.reply_text(
            "❓ 알 수 없는 명령어입니다. /help를 입력하여 사용 가능한 명령어를 확인하세요."
        )
    
    async def start(self):
        """봇 시작"""
        logger.info("🚀 간단한 텔레그램 봇 시작...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        self.is_running = True
        logger.info("✅ 텔레그램 봇 시작 완료!")
    
    async def stop(self):
        """봇 중지"""
        logger.info("🛑 텔레그램 봇 중지...")
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()
        self.is_running = False
        logger.info("✅ 텔레그램 봇 중지 완료!")


async def main():
    """메인 실행 함수"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        logger.error("❌ TELEGRAM_BOT_TOKEN 환경 변수가 설정되지 않았습니다")
        return
    
    logger.info("🤖 간단한 텔레그램 명령어 봇 테스트")
    logger.info("=" * 60)
    
    bot = SimpleBot(bot_token)
    
    try:
        await bot.start()
        
        logger.info("📱 텔레그램에서 다음 명령어들을 테스트해보세요:")
        logger.info("   • /start - 봇 시작")
        logger.info("   • /help - 도움말")
        logger.info("   • /status - 시스템 상태")
        logger.info("   • /portfolio - 포트폴리오")
        logger.info("   • /strategies - 전략 목록")
        logger.info("   • /profit - 수익률 분석")
        
        logger.info("⏰ 30초간 실행합니다. Ctrl+C로 종료하세요.")
        
        # 30초간 실행
        await asyncio.sleep(30)
        
    except KeyboardInterrupt:
        logger.info("🛑 사용자 요청으로 봇을 중지합니다...")
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())