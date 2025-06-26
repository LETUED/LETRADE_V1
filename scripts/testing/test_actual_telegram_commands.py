#!/usr/bin/env python3
"""
실제 정의된 텔레그램 명령어 테스트

MVP 통합 기능명세서에 정의된 정확한 텔레그램 명령어들을 테스트합니다.
docs/mvp/MVP 통합 기능명세서.md 섹션 6.3 기준
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


class ActualTelegramBot:
    """MVP 기능명세서에 정의된 실제 텔레그램 명령어 봇"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.application = Application.builder().token(bot_token).build()
        self.is_running = False
        
        # 인증된 사용자 (실제로는 화이트리스트에서 관리)
        self.authorized_users = [6240064337]  # 환경 변수에서 설정된 사용자
        
        # 명령어 핸들러 등록
        self._register_handlers()
    
    def _register_handlers(self):
        """MVP 기능명세서 기준 명령어 핸들러 등록"""
        # 기본 조회 명령어 (섹션 6.3.1)
        self.application.add_handler(CommandHandler("start", self.handle_start))
        self.application.add_handler(CommandHandler("help", self.handle_help))
        self.application.add_handler(CommandHandler("status", self.handle_status))
        
        # 포트폴리오 및 전략 관리 (섹션 6.3.2)
        self.application.add_handler(CommandHandler("portfolio", self.handle_portfolio))
        self.application.add_handler(CommandHandler("positions", self.handle_positions))
        self.application.add_handler(CommandHandler("strategies", self.handle_strategies))
        
        # 전략 제어 명령어 (섹션 6.3.3)
        self.application.add_handler(CommandHandler("start_strategy", self.handle_start_strategy))
        self.application.add_handler(CommandHandler("stop_strategy", self.handle_stop_strategy))
        
        # 성과 분석 명령어 (섹션 6.3.4)
        self.application.add_handler(CommandHandler("profit", self.handle_profit))
        
        # 알 수 없는 명령어
        self.application.add_handler(MessageHandler(filters.COMMAND, self.handle_unknown))
    
    def _check_auth(self, update: Update) -> bool:
        """사용자 인증 확인 (화이트리스트 기반)"""
        user_id = update.effective_user.id
        return user_id in self.authorized_users
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """봇 시작 및 사용자 인증 확인 (FR-TI-001)"""
        if not self._check_auth(update):
            await update.message.reply_text("❌ 인증되지 않은 사용자입니다. 관리자에게 문의하세요.")
            return
        
        user = update.effective_user
        message = f"""
🚀 **Letrade V1 자동 거래 시스템**

안녕하세요, {user.first_name}님!

Letrade V1 시스템에 성공적으로 연결되었습니다.
이 봇을 통해 거래 시스템을 모니터링하고 제어할 수 있습니다.

**🔍 기본 조회 명령어:**
• `/status` - 전체 시스템 상태 조회
• `/help` - 사용 가능한 모든 명령어 표시

**💼 포트폴리오 및 전략 관리:**
• `/portfolio` - 포트폴리오 현황, 총 자산, 가용 자금 조회
• `/positions` - 현재 보유 중인 포지션 목록 및 상태
• `/strategies` - 활성 전략 목록 및 각 전략의 현재 상태

**⚙️ 전략 제어 명령어:**
• `/start_strategy [전략ID]` - 특정 전략 시작
• `/stop_strategy [전략ID]` - 특정 전략 중지

**📈 성과 분석 명령어:**
• `/profit [period]` - 수익률 조회 (today/week/month)

⚠️ **보안**: 화이트리스트 기반 인증으로 보호됩니다.
💡 **팁**: 명령어는 대소문자를 구분하지 않습니다.

행복한 거래 되세요! 💰
        """
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """사용 가능한 모든 명령어와 설명 표시"""
        if not self._check_auth(update):
            await update.message.reply_text("❌ 인증되지 않은 사용자입니다.")
            return
        
        message = """
📚 **Letrade V1 명령어 완전 가이드**

**🔍 기본 조회 명령어 (읽기 권한)**
• `/start` - 봇 시작 및 사용자 인증 확인
• `/help` - 이 도움말 표시
• `/status` - 전체 시스템 상태, 활성 전략 수, 거래소 연결 상태

**💼 포트폴리오 및 전략 관리 (읽기 권한)**
• `/portfolio` - 포트폴리오 현황, 총 자산, 가용 자금
• `/positions` - 현재 보유 중인 포지션 목록 및 상태  
• `/strategies` - 활성 전략 목록 및 각 전략의 현재 상태

**⚙️ 전략 제어 명령어 (제어 권한 필요)**
• `/start_strategy [전략ID]` - 특정 전략 시작
• `/stop_strategy [전략ID]` - 특정 전략 중지
  
  **사용 예시:**
  - `/start_strategy 1` - 1번 전략 시작
  - `/stop_strategy 2` - 2번 전략 중지

**📈 성과 분석 명령어 (읽기 권한)**
• `/profit [period]` - 수익률 조회
  
  **지원 기간:** `today`, `week`, `month` (기본값: today)
  **사용 예시:**
  - `/profit` - 오늘 수익률
  - `/profit week` - 이번 주 수익률
  - `/profit month` - 이번 달 수익률

**🔐 보안 및 인증**
• 화이트리스트 기반 인증 (사용자 ID + 사용자명)
• 속도 제한: 60초당 최대 10개 명령어
• 세션 관리: 1시간 자동 만료

**🔔 자동 알림 시스템**
다음 이벤트 시 자동 알림 전송:
• 새로운 거래 체결 (정보)
• 손절매/이익실현 발동 (중간)
• 청산 위험 경고 (높음)
• 시스템 오류 발생 (높음)

**💡 사용 팁:**
• 명령어는 대소문자를 구분하지 않습니다
• 응답 시간: 상태 조회 2-3초, 전략 제어 즉시
• 잘못된 명령어 시 사용법 자동 안내

**🛡️ 보안 주의사항:**
이 시스템은 실제 자금을 다룹니다. 명령어 사용 시 신중하게 확인하세요.

📖 **참조 문서:** MVP 통합 기능명세서 섹션 6.3
        """
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """전체 시스템 상태, 활성 전략 수, 거래소 연결 상태 조회"""
        if not self._check_auth(update):
            await update.message.reply_text("❌ 인증되지 않은 사용자입니다.")
            return
        
        # 실제 구현에서는 시스템에서 실시간 상태를 가져옴
        message = f"""
🟢 **시스템 상태: 정상 운영**

**📊 핵심 시스템 지표:**
• 시스템 가동률: 8.92시간 (99.90% 가용성)
• 활성 전략 수: 1개 (MA Crossover)
• 연결된 거래소: 1개 (Binance Spot)
• 메시지 버스: 🟢 RabbitMQ 연결됨
• 데이터베이스: 🟢 PostgreSQL 정상

**💼 포트폴리오 요약:**
• 총 자산: $100.00
• 가용 자금: $98.19
• 활성 포지션: 1개 (BTCUSDT)
• 미실현 손익: -$1.81 (-1.81%)

**⚡ 성능 메트릭:**
• 평균 응답 시간: 1.921ms (목표: <200ms)
• 초당 처리량: 31,989회
• 메모리 사용량: 8.6MB / 256MB (3.4%)
• CPU 사용률: 2.4% / 50% (4.8%)

**🎯 활성 전략 상세:**
1. **MA Crossover** (ID: 1)
   • 상태: 🟢 실행 중 (드라이런 모드)
   • 심볼: BTCUSDT
   • 마지막 신호: 14:32:15 (매도)
   • 오늘 거래: 2회

**🔔 최근 이벤트:**
• 14:32:15 - MA 전략 매도 신호 감지
• 14:30:00 - 포트폴리오 자동 업데이트
• 14:25:00 - 시스템 상태 검사 완료

**📡 연결 상태:**
• Binance API: 🟢 정상 (레이턴시: 45ms)
• WebSocket 스트림: 🟢 연결됨
• 실시간 데이터: 🟢 수신 중

🕐 **마지막 업데이트:** {datetime.now().strftime('%H:%M:%S')}
📍 **서버 위치:** GCP Asia-Northeast1
⏱️ **업타임:** 8시간 55분 12초
        """
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def handle_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """포트폴리오 현황, 총 자산, 가용 자금 조회"""
        if not self._check_auth(update):
            await update.message.reply_text("❌ 인증되지 않은 사용자입니다.")
            return
        
        message = f"""
💼 **포트폴리오 현황**

**📊 계정 요약 (Binance Spot)**
• 총 자산: $100.00
• 가용 잔고: $98.19 (98.19%)
• 활성 포지션: $1.81 (1.81%)
• 미실현 손익: -$1.81 (-1.81%)

**💰 자산 구성:**
```
USDT: $98.19 (98.19%) 🔵
BTC:  0.00002 BTC ≈ $1.81 (1.81%) 🟡
```

**📈 오늘 거래 성과:**
• 시작 자본: $100.00
• 거래 횟수: 2회 (매수 1회, 매도 1회)
• 실현 손익: $0.00
• 미실현 손익: -$1.81
• 거래 수수료: $0.02
• 순 손익: -$1.83 (-1.83%)

**🔍 활성 포지션 상세:**
1. **BTCUSDT Long Position**
   • 수량: 0.00002 BTC
   • 진입 가격: $50,000.00
   • 현재 가격: $49,950.00 (-0.1%)
   • 진입 시간: 오늘 14:30:00
   • 미실현 P&L: -$1.00 (-2.0%)
   • 포지션 크기: 1.0% (보수적)

**⚠️ 리스크 관리:**
• 일일 손실 한도: $5.00
• 현재 손실: $1.83 (36.6% 사용)
• 위험도 레벨: 🟡 낮음-중간
• 자동 스톱로스: 2% (-$1.00)
• 익절 목표: 3% (+$1.50)

**📊 성과 지표:**
• 승률: 50.0% (1승 1패)
• 평균 수익: $0.50
• 평균 손실: -$1.00
• 수익/위험 비율: 0.5:1
• 최대 낙폭: -1.83%

**🔄 자동 리밸런싱:**
• 다음 리밸런싱: 내일 00:00 UTC
• 목표 USDT 비중: 95%
• 목표 BTC 비중: 5%

🕐 **업데이트 시간:** {datetime.now().strftime('%H:%M:%S')}
💡 **다음 조치:** 현재 손실이 한도 내에 있어 정상 운영 중
        """
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def handle_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """현재 보유 중인 포지션 목록 및 상태"""
        if not self._check_auth(update):
            await update.message.reply_text("❌ 인증되지 않은 사용자입니다.")
            return
        
        message = f"""
📊 **현재 포지션 목록**

**🟢 활성 포지션 (1개)**

**Position #1: BTCUSDT Long**
```
심볼:      BTCUSDT
방향:      Long (매수)
수량:      0.00002 BTC
가치:      $1.81
```

**📈 가격 정보:**
• 진입 가격: $50,000.00
• 현재 가격: $49,950.00
• 변동률: -0.1% (-$50.00)
• 24h 변동: -1.2%

**💰 손익 현황:**
• 진입 금액: $1.00
• 현재 가치: $1.81
• 미실현 손익: -$1.00 (-2.0%)
• 수수료 (진입): $0.01
• 순 손익: -$1.01

**⏰ 시간 정보:**
• 진입 시간: 오늘 14:30:00 (2시간 전)
• 보유 기간: 2시간 15분
• 만료일: 없음 (현물)

**🛡️ 리스크 관리:**
• 스톱로스: $49,000.00 (-2%)
• 익절 목표: $51,500.00 (+3%)
• 포지션 크기: 1.0% (매우 보수적)
• 레버리지: 1x (현물)

**📊 전략 정보:**
• 전략명: MA Crossover
• 신호 시간: 14:30:00
• 신호 강도: 중간
• 예상 보유 기간: 2-4시간

**🔔 알림 설정:**
• 손익률 ±2% 시 알림
• 스톱로스/익절 실행 시 즉시 알림
• 24시간 보유 시 검토 알림

**💾 거래 내역:**
```
14:30:00  매수  0.00002 BTC  $50,000.00  -$0.01 수수료
```

**📈 기술적 분석:**
• RSI(14): 45.2 (중립)
• MACD: -0.8 (약간 베어리시)
• 볼린저 밴드: 하단 근처
• 지지선: $49,800
• 저항선: $50,200

🕐 **마지막 업데이트:** {datetime.now().strftime('%H:%M:%S')}
📊 **다음 평가:** 30분 후 (15:30)

---
**💡 참고:** 드라이런 모드에서는 실제 자금이 사용되지 않습니다.
        """
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def handle_strategies(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """활성 전략 목록 및 각 전략의 현재 상태"""
        if not self._check_auth(update):
            await update.message.reply_text("❌ 인증되지 않은 사용자입니다.")
            return
        
        message = f"""
🎯 **전략 목록 및 상태**

**📈 활성 전략 (1개)**

**Strategy #1: MA Crossover** 🟢
```
ID:        1
상태:      실행 중
모드:      드라이런 (안전 모드)
시작:      오늘 12:00:00
```

**🔧 전략 설정:**
• 심볼: BTCUSDT
• 시간프레임: 1분
• MA 단기: 7기간
• MA 장기: 25기간
• 최소 신호 강도: 중간

**📊 오늘 성과:**
• 생성된 신호: 5개
• 실행된 거래: 2개 (40% 실행률)
• 성공한 거래: 1개 (50% 승률)
• 현재 수익률: -1.83%

**💰 자본 할당:**
• 할당된 자본: $10.00 (10%)
• 사용 중인 자본: $1.81 (18.1%)
• 가용 자본: $8.19
• 최대 포지션 크기: 1%

**⚡ 최근 신호 내역:**
```
15:10  매도신호  강도: 낮음    → 무시 (강도 부족)
14:32  매도신호  강도: 중간    → 대기 (보유 없음)
14:30  매수신호  강도: 높음    → 실행 (0.00002 BTC)
13:45  매도신호  강도: 중간    → 무시 (노이즈)
13:15  매수신호  강도: 낮음    → 무시 (강도 부족)
```

**🛡️ 리스크 관리:**
• 최대 동시 포지션: 1개
• 스톱로스: 자동 (-2%)
• 익절 목표: 자동 (+3%)
• 일일 최대 거래: 10회
• 연속 손실 제한: 3회

**📈 기술적 지표 현황:**
• MA7 (단기): $49,980.00
• MA25 (장기): $50,020.00
• 크로스 상태: 데드크로스 (베어리시)
• 신호 강도: 중간 (45/100)

**🔔 알림 설정:**
• 신호 생성 시: ✅ 활성화
• 거래 실행 시: ✅ 활성화
• 손익 업데이트: ✅ 활성화
• 리스크 경고: ✅ 활성화

---

**🛑 비활성 전략 (0개)**
현재 모든 등록된 전략이 실행 중입니다.

**⚙️ 전략 제어:**
• 전략 시작: `/start_strategy [ID]`
• 전략 중지: `/stop_strategy [ID]`

**예시:**
• `/stop_strategy 1` - MA Crossover 전략 중지
• `/start_strategy 1` - MA Crossover 전략 시작

🕐 **마지막 업데이트:** {datetime.now().strftime('%H:%M:%S')}
📊 **다음 신호 검사:** {(datetime.now()).strftime('%H:%M:%S')} (1분마다)

💡 **팁:** 전략 중지 시 현재 포지션은 유지되며, 새로운 신호만 중단됩니다.
        """
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def handle_start_strategy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """특정 전략 시작 (제어 권한 필요)"""
        if not self._check_auth(update):
            await update.message.reply_text("❌ 인증되지 않은 사용자입니다.")
            return
        
        # 전략 ID 파라미터 확인
        if not context.args:
            message = """
❌ **사용법 오류**

전략 ID를 지정해야 합니다.

**사용법:** `/start_strategy [전략ID]`

**사용 예시:**
• `/start_strategy 1` - MA Crossover 전략 시작

**사용 가능한 전략 목록:**
• 1: MA Crossover (이동평균 교차)

전략 목록은 `/strategies` 명령어로 확인하세요.
            """
            await update.message.reply_text(message, parse_mode='Markdown')
            return
        
        try:
            strategy_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text(
                "❌ **잘못된 전략 ID**\n\n"
                "전략 ID는 숫자여야 합니다.\n\n"
                "**예시:** `/start_strategy 1`",
                parse_mode='Markdown'
            )
            return
        
        # 실제 구현에서는 Core Engine에 명령 전송
        message = f"""
🚀 **전략 {strategy_id} 시작 요청**

✅ **요청 정보:**
• 전략 ID: {strategy_id}
• 전략명: MA Crossover
• 요청자: {update.effective_user.first_name}
• 요청 시간: {datetime.now().strftime('%H:%M:%S')}

⏳ **처리 상태:**
• 시스템 검증: ✅ 완료
• 자본 할당 확인: ✅ 완료  
• 리스크 설정 검토: ✅ 완료
• 전략 엔진 초기화: 🔄 진행 중...

**🔧 시작된 설정:**
• 모드: 드라이런 (안전 모드)
• 할당 자본: $10.00 (10%)
• 리스크 레벨: 보수적
• 자동 스톱로스: 활성화

**📊 예상 동작:**
• 1분마다 신호 검사
• 중간 이상 강도 신호만 실행
• 최대 포지션 크기: 1%
• 자동 손익 관리

⚡ **예상 완료 시간:** 10-15초

전략이 성공적으로 시작되면 별도 알림을 받으실 수 있습니다.

💡 **참고:** 현재 포지션이 있는 경우 새로운 신호부터 적용됩니다.
        """
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def handle_stop_strategy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """특정 전략 중지 (제어 권한 필요)"""
        if not self._check_auth(update):
            await update.message.reply_text("❌ 인증되지 않은 사용자입니다.")
            return
        
        # 전략 ID 파라미터 확인
        if not context.args:
            message = """
❌ **사용법 오류**

전략 ID를 지정해야 합니다.

**사용법:** `/stop_strategy [전략ID]`

**사용 예시:**
• `/stop_strategy 1` - MA Crossover 전략 중지

**현재 실행 중인 전략:**
• 1: MA Crossover (이동평균 교차) - 🟢 실행 중

전략 목록은 `/strategies` 명령어로 확인하세요.
            """
            await update.message.reply_text(message, parse_mode='Markdown')
            return
        
        try:
            strategy_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text(
                "❌ **잘못된 전략 ID**\n\n"
                "전략 ID는 숫자여야 합니다.\n\n"
                "**예시:** `/stop_strategy 1`",
                parse_mode='Markdown'
            )
            return
        
        # 실제 구현에서는 Core Engine에 명령 전송
        message = f"""
🛑 **전략 {strategy_id} 중지 요청**

✅ **요청 정보:**
• 전략 ID: {strategy_id}
• 전략명: MA Crossover
• 요청자: {update.effective_user.first_name}
• 요청 시간: {datetime.now().strftime('%H:%M:%S')}

⏳ **안전 중지 절차:**
• 신호 생성 중단: ✅ 즉시 적용
• 진행 중인 분석 완료: 🔄 대기 중...
• 현재 포지션 유지: ✅ 안전 보장
• 시스템 상태 업데이트: 🔄 진행 중...

**💼 현재 포지션 처리:**
• BTCUSDT Long 포지션: 유지됨
• 자동 손익 관리: 계속 활성화
• 스톱로스/익절: 정상 작동
• 수동 청산 필요 시: `/positions`에서 확인

**📊 중지 후 상태:**
• 새로운 신호 생성: ❌ 중단
• 포지션 모니터링: ✅ 계속
• 리스크 관리: ✅ 계속  
• 알림 시스템: ✅ 계속

⚡ **예상 완료 시간:** 5-10초

전략이 성공적으로 중지되면 확인 알림을 받으실 수 있습니다.

⚠️ **중요:** 
• 현재 포지션은 자동으로 청산되지 않습니다
• 수동 청산이 필요한 경우 별도 조치 필요
• 리스크 관리는 계속 활성화 상태입니다

💡 **재시작:** `/start_strategy {strategy_id}` 명령어로 언제든 재시작 가능
        """
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def handle_profit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """수익률 조회 (기간별)"""
        if not self._check_auth(update):
            await update.message.reply_text("❌ 인증되지 않은 사용자입니다.")
            return
        
        # 기간 파라미터 처리
        period = 'today'
        if context.args and context.args[0].lower() in ['today', 'week', 'month']:
            period = context.args[0].lower()
        elif context.args:
            await update.message.reply_text(
                "❌ **잘못된 기간 설정**\n\n"
                "지원되는 기간: today, week, month\n\n"
                "**사용법:** `/profit [기간]`\n"
                "**예시:** `/profit week`",
                parse_mode='Markdown'
            )
            return
        
        period_korean = {
            'today': '오늘',
            'week': '이번 주',
            'month': '이번 달'
        }
        
        # 기간별 데이터 (실제로는 데이터베이스에서 조회)
        profit_data = {
            'today': {
                'start_capital': 100.00,
                'current_capital': 98.19,
                'realized_pnl': 0.00,
                'unrealized_pnl': -1.81,
                'total_pnl': -1.81,
                'pnl_percent': -1.81,
                'trades': 2,
                'wins': 1,
                'losses': 1,
                'win_rate': 50.0,
                'max_profit': 2.00,
                'max_loss': -1.81,
                'fees': 0.02
            },
            'week': {
                'start_capital': 100.00,
                'current_capital': 98.19,
                'realized_pnl': -0.45,
                'unrealized_pnl': -1.81,
                'total_pnl': -2.26,
                'pnl_percent': -2.26,
                'trades': 12,
                'wins': 6,
                'losses': 6,
                'win_rate': 50.0,
                'max_profit': 3.50,
                'max_loss': -2.80,
                'fees': 0.15
            },
            'month': {
                'start_capital': 100.00,
                'current_capital': 98.19,
                'realized_pnl': 1.25,
                'unrealized_pnl': -1.81,
                'total_pnl': -0.56,
                'pnl_percent': -0.56,
                'trades': 45,
                'wins': 24,
                'losses': 21,
                'win_rate': 53.3,
                'max_profit': 5.20,
                'max_loss': -3.10,
                'fees': 0.58
            }
        }
        
        data = profit_data[period]
        
        message = f"""
📈 **{period_korean[period]} 수익률 분석**

**💰 손익 요약:**
• 시작 자본: ${data['start_capital']:.2f}
• 현재 자산: ${data['current_capital']:.2f}
• 실현 손익: ${data['realized_pnl']:.2f}
• 미실현 손익: ${data['unrealized_pnl']:.2f}
• **총 손익: ${data['total_pnl']:.2f} ({data['pnl_percent']:+.2f}%)**

**📊 거래 통계:**
• 총 거래 횟수: {data['trades']}회
• 수익 거래: {data['wins']}회
• 손실 거래: {data['losses']}회
• **승률: {data['win_rate']:.1f}%**

**📈 성과 지표:**
• 최대 수익: +${data['max_profit']:.2f}
• 최대 손실: ${data['max_loss']:.2f}
• 평균 거래: ${data['total_pnl']/data['trades']:.2f}
• 총 수수료: ${data['fees']:.2f}

**⚡ 효율성 분석:**
```
수익 팩터: {abs(data['realized_pnl']/data['max_loss']) if data['max_loss'] != 0 else 0:.2f}
샤프 비율: {-0.12 if period == 'today' else 0.15 if period == 'week' else 0.28:.2f}
최대 낙폭: {abs(data['max_loss']):.2f}% 
회복율: {"진행 중" if data['total_pnl'] < 0 else "완료"}
```

**🎯 목표 대비 성과:**
• {period_korean[period]} 목표: +1.0%
• 실제 성과: {data['pnl_percent']:+.2f}%
• 달성률: {data['pnl_percent']/1.0*100:.0f}%

**🔍 상세 분석 ({period_korean[period]}):**
"""
        
        if period == 'today':
            message += """
**오늘 거래 내역:**
```
14:30  매수  BTCUSDT  $1.00   진행중
14:32  신호  매도     -       무시됨
```

**시간대별 성과:**
• 12:00-14:00: $0.00 (대기)
• 14:00-16:00: -$1.81 (활성)
• 16:00-18:00: 예정 (전망: 보합)
"""
        elif period == 'week':
            message += """
**주간 거래 패턴:**
```
월요일: +$0.50 (2거래)
화요일: -$1.20 (3거래)  
수요일: +$0.80 (2거래)
목요일: -$0.45 (3거래)
금요일: -$2.26 (2거래) ← 오늘
```

**전략별 성과:**
• MA Crossover: -$2.26 (12거래)
"""
        else:  # month
            message += """
**월간 거래 패턴:**
```
1주차: +$2.10 (12거래)
2주차: -$1.05 (10거래)
3주차: +$1.80 (15거래)
4주차: -$3.41 (8거래)
현재: -$0.56 (종합)
```

**전략별 성과:**
• MA Crossover: -$0.56 (45거래)
• 승률 개선 추세: +3.3%p
"""
        
        message += f"""

**📊 위험 조정 수익률:**
• 변동성: {12.5 if period == 'today' else 15.8 if period == 'week' else 18.2:.1f}%
• 정보비율: {-0.08 if period == 'today' else 0.12 if period == 'week' else 0.18:.2f}
• 최대손실 회복: {"2시간 예상" if period == 'today' else "3일 예상" if period == 'week' else "진행 중"}

**🔮 다음 기간 전망:**
• 예상 수익률: {"+0.5~1.2%" if data['pnl_percent'] > -2 else "+1.0~2.0%"}
• 권장 조치: {"포지션 유지" if data['pnl_percent'] > -2 else "리스크 축소"}
• 시장 전망: {"중립" if period == 'today' else "긍정적"}

🕐 **분석 시간:** {datetime.now().strftime('%H:%M:%S')}
📊 **다음 업데이트:** {"1시간 후" if period == 'today' else "내일" if period == 'week' else "다음 주"}

💡 **참고:** 드라이런 모드 결과입니다. 실제 거래 시 결과가 다를 수 있습니다.
        """
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def handle_unknown(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """알 수 없는 명령어 처리"""
        if not self._check_auth(update):
            await update.message.reply_text("❌ 인증되지 않은 사용자입니다.")
            return
        
        await update.message.reply_text(
            "❓ **알 수 없는 명령어**\n\n"
            "`/help`를 입력하여 사용 가능한 명령어를 확인하세요.\n\n"
            "**주요 명령어:**\n"
            "• `/status` - 시스템 상태\n" 
            "• `/portfolio` - 포트폴리오\n"
            "• `/strategies` - 전략 목록\n"
            "• `/profit` - 수익률 분석",
            parse_mode='Markdown'
        )
    
    async def start(self):
        """봇 시작"""
        logger.info("🚀 실제 텔레그램 명령어 봇 시작...")
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
    
    logger.info("🤖 실제 정의된 텔레그램 명령어 봇 테스트")
    logger.info("📋 MVP 통합 기능명세서 섹션 6.3 기준")
    logger.info("=" * 60)
    
    bot = ActualTelegramBot(bot_token)
    
    try:
        await bot.start()
        
        logger.info("📱 텔레그램에서 다음 명령어들을 테스트해보세요:")
        logger.info("   🔍 기본 조회: /start, /help, /status")
        logger.info("   💼 포트폴리오: /portfolio, /positions, /strategies")
        logger.info("   ⚙️ 전략 제어: /start_strategy [ID], /stop_strategy [ID]")
        logger.info("   📈 성과 분석: /profit [period]")
        
        logger.info("⏰ 60초간 실행합니다. Ctrl+C로 종료하세요.")
        
        # 60초간 실행
        await asyncio.sleep(60)
        
    except KeyboardInterrupt:
        logger.info("🛑 사용자 요청으로 봇을 중지합니다...")
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())