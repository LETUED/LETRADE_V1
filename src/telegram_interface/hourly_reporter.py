"""Hourly Reporter for Telegram Bot.

Provides automatic hourly system status reports for active trading sessions.
Implements scheduled reporting with comprehensive system status updates.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


class HourlyReporter:
    """Provides automatic hourly reporting for trading system status.

    Sends comprehensive system status reports every hour including:
    - Portfolio status and changes
    - Strategy performance summary
    - Trading activity report
    - System health metrics
    """

    def __init__(self, service_client):
        """Initialize hourly reporter.

        Args:
            service_client: ServiceClient instance for data retrieval
        """
        self.service_client = service_client
        self.reporting_task: Optional[asyncio.Task] = None
        self.is_running = False
        self.chat_id: Optional[int] = None
        self.bot = None
        self.start_time = datetime.now(timezone.utc)
        logger.info("Hourly reporter initialized")

    async def start_reporting(self, chat_id: int, bot: Any) -> None:
        """Start hourly reporting to specified chat.

        Args:
            chat_id: Telegram chat ID to send reports to
            bot: Telegram bot instance
        """
        if self.is_running:
            logger.info("Hourly reporting already running")
            return

        self.chat_id = chat_id
        self.bot = bot
        self.is_running = True

        # Start reporting task
        self.reporting_task = asyncio.create_task(self._reporting_loop())
        logger.info(f"Started hourly reporting for chat {chat_id}")

    async def stop_reporting(self) -> None:
        """Stop hourly reporting."""
        if not self.is_running:
            return

        self.is_running = False

        if self.reporting_task and not self.reporting_task.done():
            self.reporting_task.cancel()
            try:
                await self.reporting_task
            except asyncio.CancelledError:
                pass

        logger.info("Stopped hourly reporting")

    def next_report_time(self) -> str:
        """Get next scheduled report time.

        Returns:
            str: Formatted next report time
        """
        if not self.is_running:
            return "보고 비활성화"

        now = datetime.now(timezone.utc)
        next_hour = (now + timedelta(hours=1)).replace(
            minute=0, second=0, microsecond=0
        )
        return next_hour.strftime("%H:%M UTC")

    async def _reporting_loop(self) -> None:
        """Main reporting loop that runs every hour."""
        try:
            # Wait until the next hour boundary
            now = datetime.now(timezone.utc)
            next_hour = (now + timedelta(hours=1)).replace(
                minute=0, second=0, microsecond=0
            )
            sleep_seconds = (next_hour - now).total_seconds()

            logger.info(
                f"First report scheduled in {sleep_seconds:.0f} seconds at {next_hour.strftime('%H:%M UTC')}"
            )
            await asyncio.sleep(sleep_seconds)

            # Send initial report
            await self._send_hourly_report()

            # Continue hourly reporting
            while self.is_running:
                await asyncio.sleep(3600)  # 1 hour
                if self.is_running:  # Check again after sleep
                    await self._send_hourly_report()

        except asyncio.CancelledError:
            logger.info("Hourly reporting task cancelled")
        except Exception as e:
            logger.error(f"Error in reporting loop: {e}")

    async def _send_hourly_report(self) -> None:
        """Send comprehensive hourly report."""
        try:
            # Get current system data
            status_data = await self.service_client.get_system_status()
            portfolio_data = await self.service_client.get_portfolio_status()
            strategies_data = await self.service_client.get_strategies_status()

            # Calculate running time
            running_time = datetime.now(timezone.utc) - self.start_time
            hours = int(running_time.total_seconds() // 3600)
            minutes = int((running_time.total_seconds() % 3600) // 60)

            # Format comprehensive report
            report = f"""
🕐 **정기 시스템 보고서** ({datetime.now(timezone.utc).strftime('%H:%M UTC')})

⏱️ **운영 시간**: {hours}시간 {minutes}분

📊 **시스템 상태**:
• 전체 상태: {'🟢 정상' if status_data.get('healthy') else '🔴 문제'}
• 활성 전략: {status_data.get('active_strategies', 0)}개
• 처리 성능: {status_data.get('avg_response_time', 0):.1f}ms

💼 **포트폴리오 현황**:
• 총 자산: ${portfolio_data.get('total_value', 0):.2f}
• 가용 자금: ${portfolio_data.get('available_balance', 0):.2f}
• 오늘 손익: ${portfolio_data.get('daily_pnl', 0):+.2f} ({portfolio_data.get('daily_pnl_percent', 0):+.1f}%)

🎯 **전략 성과**:
"""

            # Add strategy performance details
            strategies = strategies_data.get("strategies", [])
            if strategies:
                for strategy in strategies[:3]:  # Top 3 strategies
                    report += f"• {strategy.get('name', 'Unknown')}: "
                    report += f"{strategy.get('daily_pnl_percent', 0):+.1f}% "
                    report += f"({strategy.get('status', 'unknown')})\n"
            else:
                report += "• 활성 전략 없음\n"

            # Add risk status
            daily_loss = abs(portfolio_data.get("daily_pnl", 0))
            risk_level = (
                "🟢 낮음"
                if daily_loss < 2
                else "🟡 중간" if daily_loss < 4 else "🔴 높음"
            )

            report += f"""
⚠️ **리스크 상태**: {risk_level}
• 일일 손실: ${daily_loss:.2f}/5.00 ({daily_loss/5*100:.1f}%)

📈 **거래 활동**:
• 총 거래 수: {status_data.get('total_trades', 0)}회
• 성공률: {status_data.get('success_rate', 0):.1f}%

🔄 **다음 보고**: {self.next_report_time()}

시스템이 안전하게 운영되고 있습니다! 🛡️
            """

            # Send report
            if self.bot and self.chat_id:
                await self.bot.send_message(chat_id=self.chat_id, text=report.strip())
                logger.info("Hourly report sent successfully")

        except Exception as e:
            logger.error(f"Error sending hourly report: {e}")
            # Send error notification
            if self.bot and self.chat_id:
                try:
                    await self.bot.send_message(
                        chat_id=self.chat_id,
                        text="⚠️ 정기 보고서 생성 중 오류가 발생했습니다. 시스템은 계속 작동 중입니다.",
                    )
                except Exception as e2:
                    logger.error(f"Failed to send error notification: {e2}")

    async def send_immediate_report(self, chat_id: int, bot: Any) -> None:
        """Send immediate comprehensive report.

        Args:
            chat_id: Telegram chat ID
            bot: Telegram bot instance
        """
        temp_chat_id = self.chat_id
        temp_bot = self.bot

        # Temporarily set for immediate report
        self.chat_id = chat_id
        self.bot = bot

        try:
            await self._send_hourly_report()
        finally:
            # Restore original values
            self.chat_id = temp_chat_id
            self.bot = temp_bot
