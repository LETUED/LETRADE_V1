"""Redesigned Command handlers for Telegram Bot.

Implements intuitive /start /stop /restart command structure with hourly reporting.
Provides simple, clear system control and monitoring capabilities.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from telegram import Update
from telegram.ext import ContextTypes

from common.message_bus import MessageBus

from .hourly_reporter import HourlyReporter
from .service_client import ServiceClient

logger = logging.getLogger(__name__)


class CommandHandler:
    """Redesigned command handler with intuitive /start /stop /restart structure.

    Implements simple, clear command system with automatic hourly reporting.
    Provides easy-to-use system control for non-technical users.
    """

    def __init__(self):
        """Initialize redesigned command handler."""
        self.pending_requests: Dict[str, Dict] = {}
        self.service_client: Optional[ServiceClient] = None
        self.hourly_reporter: Optional[HourlyReporter] = None
        self.system_running = False
        self.reporting_enabled = False
        logger.info("Redesigned command handler initialized")

    async def initialize_service_client(self, message_bus: MessageBus) -> None:
        """Initialize service client for real system communication.

        Args:
            message_bus: MessageBus instance for async communication
        """
        self.service_client = ServiceClient(message_bus=message_bus)
        await self.service_client.__aenter__()
        logger.info("Service client initialized for redesigned commands")

    async def handle_start(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        message_bus: MessageBus,
    ) -> None:
        """Handle /start command - 시스템 시작 및 정기 보고 활성화.

        새로운 직관적 명령어: 시스템을 시작하고 1시간마다 자동 보고를 받습니다.

        Args:
            update: Telegram update object
            context: Telegram context object
            message_bus: Message bus for system communication
        """
        user = update.effective_user

        try:
            # Initialize service client if not already done
            if not self.service_client:
                await self.initialize_service_client(message_bus)

            # Initialize hourly reporter if not already done
            if not self.hourly_reporter:
                self.hourly_reporter = HourlyReporter(self.service_client)

            # Start the trading system
            start_result = await self.service_client.start_trading_system(user.id)

            if start_result.get("success", False):
                self.system_running = True

                # Start hourly reporting
                await self.hourly_reporter.start_reporting(
                    chat_id=update.effective_chat.id, bot=update.get_bot()
                )
                self.reporting_enabled = True

                success_message = f"""
🚀 **시스템 시작 완료!**

안녕하세요, {user.first_name}님!

✅ **시작된 서비스:**
• 거래 시스템: 활성화
• 전략 모니터링: 시작됨
• 리스크 관리: 활성화
• 자동 보고: 1시간마다 전송

📊 **자동 보고 내용:**
• 포트폴리오 현황
• 전략 성과 요약
• 거래 활동 리포트
• 시스템 상태 체크

🎛️ **간단한 제어 명령어:**
• `/status` - 실시간 상태 확인
• `/portfolio` - 포트폴리오 조회
• `/stop` - 시스템 중지
• `/restart` - 시스템 재시작

⏰ **다음 보고**: {self.hourly_reporter.next_report_time()}

🛡️ **안전한 거래가 시작되었습니다!**
                """

                await update.message.reply_text(success_message.strip())
                logger.info(
                    f"System started by user {user.id} with hourly reporting enabled"
                )

            else:
                error_msg = start_result.get("error", "알 수 없는 오류")
                await update.message.reply_text(
                    f"❌ **시스템 시작 실패**\n\n"
                    f"오류: {error_msg}\n\n"
                    f"잠시 후 다시 시도해 주세요."
                )

        except Exception as e:
            logger.error(f"Error in handle_start: {e}")
            await update.message.reply_text(
                "❌ 시스템 시작 중 오류가 발생했습니다. 관리자에게 문의해 주세요."
            )

    async def handle_stop(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        message_bus: MessageBus,
    ) -> None:
        """Handle /stop command - 시스템 완전 중지.

        Args:
            update: Telegram update object
            context: Telegram context object
            message_bus: Message bus for system communication
        """
        user = update.effective_user

        try:
            # Initialize service client if not already done
            if not self.service_client:
                await self.initialize_service_client(message_bus)

            # Stop hourly reporting first
            if self.hourly_reporter:
                await self.hourly_reporter.stop_reporting()
                self.reporting_enabled = False

            # Stop the trading system
            stop_result = await self.service_client.stop_trading_system(user.id)

            if stop_result.get("success", False):
                self.system_running = False

                stop_message = f"""
🛑 **시스템 중지 완료**

{user.first_name}님, 시스템이 안전하게 중지되었습니다.

✅ **중지된 서비스:**
• 거래 시스템: 중지됨
• 모든 전략: 안전하게 중지
• 자동 보고: 비활성화
• 신규 거래: 차단됨

💼 **기존 포지션:**
• 현재 보유 포지션은 유지됩니다
• 수동으로 정리하거나 재시작 후 관리 가능

🔄 **재시작 방법:**
• `/start` - 시스템 다시 시작
• `/restart` - 즉시 재시작

📊 **최종 상태 확인:**
• `/portfolio` - 포트폴리오 확인
• `/status` - 시스템 상태 확인

시스템이 안전하게 중지되었습니다. 🛡️
                """

                await update.message.reply_text(stop_message.strip())
                logger.info(f"System stopped by user {user.id}")

            else:
                error_msg = stop_result.get("error", "알 수 없는 오류")
                await update.message.reply_text(
                    f"❌ **시스템 중지 실패**\n\n"
                    f"오류: {error_msg}\n\n"
                    f"긴급한 경우 관리자에게 연락해 주세요."
                )

        except Exception as e:
            logger.error(f"Error in handle_stop: {e}")
            await update.message.reply_text(
                "❌ 시스템 중지 중 오류가 발생했습니다. 관리자에게 문의해 주세요."
            )

    async def handle_restart(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        message_bus: MessageBus,
    ) -> None:
        """Handle /restart command - 시스템 재시작.

        Args:
            update: Telegram update object
            context: Telegram context object
            message_bus: Message bus for system communication
        """
        user = update.effective_user

        try:
            # Initialize service client if not already done
            if not self.service_client:
                await self.initialize_service_client(message_bus)

            # Send restart notification
            await update.message.reply_text(
                "🔄 **시스템 재시작 중...**\n\n"
                "잠시만 기다려주세요. 시스템을 안전하게 재시작하고 있습니다."
            )

            # Stop hourly reporting first
            if self.hourly_reporter:
                await self.hourly_reporter.stop_reporting()
                self.reporting_enabled = False

            # Restart the trading system
            restart_result = await self.service_client.restart_trading_system(user.id)

            if restart_result.get("success", False):
                self.system_running = True

                # Restart hourly reporting
                if not self.hourly_reporter:
                    self.hourly_reporter = HourlyReporter(self.service_client)

                await self.hourly_reporter.start_reporting(
                    chat_id=update.effective_chat.id, bot=update.get_bot()
                )
                self.reporting_enabled = True

                restart_message = f"""
✅ **시스템 재시작 완료!**

{user.first_name}님, 시스템이 성공적으로 재시작되었습니다.

🔄 **재시작된 서비스:**
• 거래 시스템: 재활성화
• 전략 모니터링: 재시작
• 리스크 관리: 업데이트됨
• 자동 보고: 재개됨

📊 **시스템 상태:**
• 다운타임: {restart_result.get('downtime_seconds', 0)}초
• 모든 연결: 재설정 완료
• 데이터 동기화: 완료

⏰ **다음 보고**: {self.hourly_reporter.next_report_time()}

🎯 **이용 가능한 명령어:**
• `/status` - 시스템 상태
• `/portfolio` - 포트폴리오
• `/stop` - 시스템 중지

시스템이 새롭게 시작되었습니다! 🚀
                """

                await update.message.reply_text(restart_message.strip())
                logger.info(f"System restarted by user {user.id}")

            else:
                error_msg = restart_result.get("error", "알 수 없는 오류")
                await update.message.reply_text(
                    f"❌ **시스템 재시작 실패**\n\n"
                    f"오류: {error_msg}\n\n"
                    f"수동으로 중지 후 시작해 보세요:\n"
                    f"1. `/stop`\n"
                    f"2. `/start`"
                )

        except Exception as e:
            logger.error(f"Error in handle_restart: {e}")
            await update.message.reply_text(
                "❌ 시스템 재시작 중 오류가 발생했습니다. 관리자에게 문의해 주세요."
            )

    async def handle_help(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /help command - 새로운 직관적 명령어 가이드.

        완전히 재설계된 간단하고 직관적인 명령어 구조를 안내합니다.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        # 간단하고 직관적인 도움말 (Markdown 문제 방지를 위해 일반 텍스트 사용)
        help_message = """
🚀 Letrade V1 자동거래 시스템

🎛️ 핵심 제어 명령어:

/start - 시스템 시작 + 1시간마다 자동 보고
/stop - 시스템 완전 중지
/restart - 시스템 재시작

📊 정보 조회 명령어:

/status - 실시간 시스템 상태
/portfolio - 포트폴리오 현황
/report - 즉시 상세 보고서

💡 사용법:

1️⃣ 시작: /start 입력
   → 시스템이 시작되고 1시간마다 보고서가 자동 전송됩니다

2️⃣ 확인: /status 또는 /portfolio로 언제든 현황 확인

3️⃣ 중지: /stop으로 시스템 완전 중지

🔄 자동 보고 내용:
• 포트폴리오 잔고 및 변화
• 활성 전략 성과
• 거래 활동 요약
• 수익률 분석

⚠️ 주의사항:
• /start 실행 시 실제 거래가 시작됩니다
• 자동 보고는 /stop까지 계속됩니다
• 문제 발생 시 즉시 /stop 사용하세요

💰 안전한 자동거래를 시작하세요!
        """

        try:
            # 일반 텍스트로 전송 (파싱 오류 방지)
            await update.message.reply_text(help_message.strip())
            logger.info("Help command executed successfully")
        except Exception as e:
            logger.error(f"Error in handle_help: {e}")
            # 최소한의 폴백 메시지
            await update.message.reply_text(
                "Letrade V1 명령어:\n\n"
                "/start - 시스템 시작\n"
                "/stop - 시스템 중지\n"
                "/status - 상태 확인\n"
                "/portfolio - 포트폴리오\n\n"
                "자세한 도움말은 /help를 다시 시도해주세요."
            )

    async def handle_status(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        message_bus: MessageBus,
    ) -> None:
        """Handle /status command - 실시간 시스템 상태.

        Args:
            update: Telegram update object
            context: Telegram context object
            message_bus: Message bus for system communication
        """
        try:
            # Initialize service client if not already done
            if not self.service_client:
                await self.initialize_service_client(message_bus)

            # Get real system status
            status_data = await self.service_client.get_system_status()

            # Format status message with real data
            status_icon = "🟢" if status_data.get("healthy", False) else "🔴"
            status_text = (
                "정상 운영" if status_data.get("healthy", False) else "문제 발생"
            )

            # System running status
            system_status = "🟢 실행 중" if self.system_running else "🔴 중지됨"
            reporting_status = "🟢 활성화" if self.reporting_enabled else "🔴 비활성화"

            message = f"""
{status_icon} **시스템 상태: {status_text}**

🎛️ **제어 상태:**
• 거래 시스템: {system_status}
• 자동 보고: {reporting_status}
• 활성 전략: {status_data.get('active_strategies', 0)}개

📊 **성능 지표:**
• 응답 시간: {status_data.get('avg_response_time', 0):.1f}ms
• 처리량: {status_data.get('throughput', 0):,}회/분
• 성공률: {status_data.get('success_rate', 0):.1f}%

💼 **포트폴리오 요약:**
• 총 자산: ${status_data.get('total_portfolio_value', 0):,.2f}
• 가용 자금: ${status_data.get('available_capital', 0):,.2f}
• 활성 거래: {status_data.get('active_trades', 0)}개

🔄 **다음 작업:**
{f'• 다음 보고: {self.hourly_reporter.next_report_time()}' if self.reporting_enabled else '• 시스템 시작: /start'}

🕐 업데이트: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}
            """

            await update.message.reply_text(message.strip())

        except Exception as e:
            logger.error(f"Error handling status command: {e}")
            await update.message.reply_text(
                "❌ 시스템 상태 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
            )

    async def handle_portfolio(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        message_bus: MessageBus,
    ) -> None:
        """Handle /portfolio command - 포트폴리오 현황.

        Args:
            update: Telegram update object
            context: Telegram context object
            message_bus: Message bus for system communication
        """
        try:
            # Initialize service client if not already done
            if not self.service_client:
                await self.initialize_service_client(message_bus)

            # Get real portfolio data
            portfolio_data = await self.service_client.get_portfolio_status()

            # Format portfolio message with real data
            total_value = portfolio_data.get("total_value", 0)
            available = portfolio_data.get("available_balance", 0)
            positions_value = portfolio_data.get("positions_value", 0)
            unrealized_pnl = portfolio_data.get("unrealized_pnl", 0)
            daily_pnl = portfolio_data.get("daily_pnl", 0)
            daily_pnl_percent = portfolio_data.get("daily_pnl_percent", 0)

            # Asset breakdown
            assets = portfolio_data.get("assets", [])
            asset_lines = []
            for asset in assets:
                symbol = asset.get("symbol", "Unknown")
                amount = asset.get("amount", 0)
                value = asset.get("value", 0)
                percentage = asset.get("percentage", 0)

                if symbol == "USDT":
                    asset_lines.append(f"USDT: ${value:.2f} ({percentage:.1f}%) 🔵")
                elif symbol == "BTC":
                    asset_lines.append(
                        f"BTC: {amount:.8f} BTC ≈ ${value:.2f} ({percentage:.1f}%) 🟡"
                    )
                else:
                    asset_lines.append(f"{symbol}: ${value:.2f} ({percentage:.1f}%)")

            # Risk assessment
            daily_loss = abs(daily_pnl) if daily_pnl < 0 else 0
            risk_level = (
                "🟢 낮음"
                if daily_loss < 2
                else "🟡 중간" if daily_loss < 4 else "🔴 높음"
            )

            message = f"""💼 **포트폴리오 현황**

📊 **계정 요약 (Binance Spot)**
• 총 자산: ${total_value:.2f}
• 가용 잔고: ${available:.2f} ({(available/total_value*100 if total_value > 0 else 0):.1f}%)
• 활성 포지션: ${positions_value:.2f} ({(positions_value/total_value*100 if total_value > 0 else 0):.1f}%)

💰 **자산 구성:**
{chr(10).join(asset_lines) if asset_lines else '데이터 없음'}

📈 **오늘 거래 성과:**
• 실현 손익: ${portfolio_data.get('realized_pnl', 0):.2f}
• 미실현 손익: ${unrealized_pnl:.2f}
• 순 손익: ${daily_pnl:+.2f} ({daily_pnl_percent:+.2f}%)

⚠️ **리스크 관리:**
• 일일 손실 한도: $5.00
• 현재 손실: ${daily_loss:.2f} ({(daily_loss/5*100):.1f}% 사용)
• 위험도 레벨: {risk_level}

🔄 **권장 조치:**
{('정상 운영 중' if daily_loss < 3 else '주의 깊은 모니터링 필요')}

🕐 **업데이트**: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}"""

            await update.message.reply_text(message)

        except Exception as e:
            logger.error(f"Error handling portfolio command: {e}")
            await update.message.reply_text(
                "❌ 포트폴리오 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
            )

    async def handle_report(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        message_bus: MessageBus,
    ) -> None:
        """Handle /report command - 즉시 상세 보고서.

        Args:
            update: Telegram update object
            context: Telegram context object
            message_bus: Message bus for system communication
        """
        try:
            # Initialize service client if not already done
            if not self.service_client:
                await self.initialize_service_client(message_bus)

            # Initialize hourly reporter if not already done for immediate report
            if not self.hourly_reporter:
                self.hourly_reporter = HourlyReporter(self.service_client)

            await update.message.reply_text(
                "📊 **상세 보고서 생성 중...**\n\n"
                "포트폴리오, 전략, 거래 활동을 종합 분석하고 있습니다."
            )

            # Send immediate comprehensive report
            await self.hourly_reporter.send_immediate_report(
                chat_id=update.effective_chat.id, bot=update.get_bot()
            )

        except Exception as e:
            logger.error(f"Error handling report command: {e}")
            await update.message.reply_text(
                "❌ 보고서 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
            )
