"""BotFather-style Menu System with Inline Keyboards.

Implements hierarchical menu system with inline keyboards similar to BotFather,
providing intuitive navigation and settings management for trading system.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

logger = logging.getLogger(__name__)


class MenuLevel(Enum):
    """Menu hierarchy levels."""

    MAIN = "main"
    SETTINGS = "settings"
    TRADING = "trading"
    PORTFOLIO = "portfolio"
    NOTIFICATIONS = "notifications"
    SECURITY = "security"
    ADVANCED = "advanced"


class MenuSystem:
    """BotFather-style hierarchical menu system.

    Provides intuitive navigation through settings and controls using
    inline keyboards with breadcrumb navigation and context-aware options.
    """

    def __init__(self, service_client=None):
        """Initialize menu system.

        Args:
            service_client: Service client for system interactions
        """
        self.service_client = service_client
        self.user_sessions: Dict[int, Dict] = {}  # user_id -> session data
        self.menu_cache: Dict[str, Any] = {}
        logger.info("Menu system initialized")

    async def show_main_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Show main menu with primary system controls.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        user_id = update.effective_user.id

        # Get current system status for dynamic menu
        system_status = await self._get_system_status()

        keyboard = self._build_main_menu_keyboard(system_status)

        main_text = self._format_main_menu_text(system_status)

        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=main_text, reply_markup=keyboard, parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                text=main_text, reply_markup=keyboard, parse_mode="Markdown"
            )

        # Update user session
        self._update_user_session(user_id, MenuLevel.MAIN, {})

    def _build_main_menu_keyboard(self, system_status: Dict) -> InlineKeyboardMarkup:
        """Build main menu keyboard based on system status.

        Args:
            system_status: Current system status

        Returns:
            InlineKeyboardMarkup: Main menu keyboard
        """
        keyboard = []

        # System control row
        if system_status.get("trading_active", False):
            keyboard.append(
                [
                    InlineKeyboardButton("⏸️ 일시정지", callback_data="action_pause"),
                    InlineKeyboardButton("🛑 중지", callback_data="action_stop"),
                ]
            )
        else:
            keyboard.append(
                [
                    InlineKeyboardButton("🚀 시작", callback_data="action_start"),
                    InlineKeyboardButton("🔄 재시작", callback_data="action_restart"),
                ]
            )

        # Quick info row
        keyboard.append(
            [
                InlineKeyboardButton("📊 상태", callback_data="quick_status"),
                InlineKeyboardButton("💼 포트폴리오", callback_data="quick_portfolio"),
                InlineKeyboardButton("📈 보고서", callback_data="quick_report"),
            ]
        )

        # Settings and configuration
        keyboard.append(
            [
                InlineKeyboardButton("⚙️ 설정", callback_data="menu_settings"),
                InlineKeyboardButton("🔔 알림", callback_data="menu_notifications"),
            ]
        )

        # Emergency controls (if needed)
        if system_status.get("risk_level") == "HIGH":
            keyboard.append(
                [InlineKeyboardButton("🚨 긴급 중지", callback_data="emergency_stop")]
            )

        # Refresh button
        keyboard.append(
            [InlineKeyboardButton("🔄 새로고침", callback_data="refresh_main")]
        )

        return InlineKeyboardMarkup(keyboard)

    def _format_main_menu_text(self, system_status: Dict) -> str:
        """Format main menu text with current status.

        Args:
            system_status: Current system status

        Returns:
            str: Formatted main menu text
        """
        status_icon = "🟢" if system_status.get("healthy", False) else "🔴"
        trading_status = (
            "🟢 활성" if system_status.get("trading_active", False) else "🔴 중지"
        )

        return f"""
🎛️ **Letrade V1 제어 센터**

**시스템 상태**: {status_icon} {system_status.get('status_text', '확인 중')}
**거래 상태**: {trading_status}
**활성 전략**: {system_status.get('active_strategies', 0)}개
**포트폴리오**: ${system_status.get('total_value', 0):.2f}

원하는 작업을 선택해주세요:
        """

    async def show_settings_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Show comprehensive settings menu.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        user_id = update.effective_user.id

        keyboard = [
            # Trading strategy settings
            [
                InlineKeyboardButton(
                    "🎯 거래 전략 설정", callback_data="settings_trading"
                )
            ],
            # Portfolio management
            [
                InlineKeyboardButton(
                    "📊 포트폴리오 관리", callback_data="settings_portfolio"
                )
            ],
            # Risk management
            [InlineKeyboardButton("⚠️ 리스크 관리", callback_data="settings_risk")],
            # Notifications and alerts
            [
                InlineKeyboardButton(
                    "🔔 알림 및 보고", callback_data="settings_notifications"
                )
            ],
            # Security settings
            [InlineKeyboardButton("🛡️ 보안 설정", callback_data="settings_security")],
            # Advanced configuration
            [InlineKeyboardButton("🔧 고급 설정", callback_data="settings_advanced")],
            # Back to main menu
            [InlineKeyboardButton("↩️ 메인 메뉴", callback_data="menu_main")],
        ]

        settings_text = """
⚙️ **Letrade V1 설정 메뉴**

시스템의 각종 설정을 관리할 수 있습니다.
설정할 항목을 선택해주세요:

💡 **팁**: 각 설정은 즉시 적용되며, 안전을 위해 중요한 변경사항은 확인 절차를 거칩니다.
        """

        await update.callback_query.edit_message_text(
            text=settings_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

        self._update_user_session(user_id, MenuLevel.SETTINGS, {})

    async def show_trading_settings(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Show trading strategy settings.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        user_id = update.effective_user.id

        # Get current trading settings
        trading_config = await self._get_trading_config()

        keyboard = [
            # Strategy activation/deactivation
            [
                InlineKeyboardButton(
                    "🎯 전략 활성화/비활성화", callback_data="trading_strategies"
                )
            ],
            # Risk level adjustment
            [
                InlineKeyboardButton(
                    "⚖️ 리스크 레벨 조정", callback_data="trading_risk_level"
                )
            ],
            # Trading limits
            [InlineKeyboardButton("💰 거래 한도 설정", callback_data="trading_limits")],
            # Auto-trading settings
            [InlineKeyboardButton("🤖 자동거래 설정", callback_data="trading_auto")],
            # Trading hours
            [InlineKeyboardButton("🕐 거래 시간 설정", callback_data="trading_hours")],
            # Back buttons
            [
                InlineKeyboardButton("↩️ 설정 메뉴", callback_data="menu_settings"),
                InlineKeyboardButton("🏠 메인 메뉴", callback_data="menu_main"),
            ],
        ]

        trading_text = f"""
🎯 **거래 전략 설정**

**현재 설정**:
• 활성 전략: {trading_config.get('active_strategies', 0)}개
• 리스크 레벨: {trading_config.get('risk_level', '중간')}
• 일일 거래 한도: ${trading_config.get('daily_limit', 100):.2f}
• 자동거래: {'🟢 활성' if trading_config.get('auto_trading', False) else '🔴 비활성'}

설정을 변경할 항목을 선택하세요:
        """

        await update.callback_query.edit_message_text(
            text=trading_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

        self._update_user_session(
            user_id, MenuLevel.TRADING, {"config": trading_config}
        )

    async def show_portfolio_settings(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Show portfolio management settings.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        user_id = update.effective_user.id

        portfolio_config = await self._get_portfolio_config()

        keyboard = [
            # Asset allocation
            [
                InlineKeyboardButton(
                    "📊 자산 배분 설정", callback_data="portfolio_allocation"
                )
            ],
            # Rebalancing
            [
                InlineKeyboardButton(
                    "⚖️ 리밸런싱 설정", callback_data="portfolio_rebalancing"
                )
            ],
            # Profit taking rules
            [
                InlineKeyboardButton(
                    "💰 수익실현 규칙", callback_data="portfolio_profit_taking"
                )
            ],
            # Stop loss settings
            [
                InlineKeyboardButton(
                    "🛑 손절매 설정", callback_data="portfolio_stop_loss"
                )
            ],
            # Diversification rules
            [
                InlineKeyboardButton(
                    "🎯 분산투자 규칙", callback_data="portfolio_diversification"
                )
            ],
            # Back buttons
            [
                InlineKeyboardButton("↩️ 설정 메뉴", callback_data="menu_settings"),
                InlineKeyboardButton("🏠 메인 메뉴", callback_data="menu_main"),
            ],
        ]

        portfolio_text = f"""
📊 **포트폴리오 관리 설정**

**현재 설정**:
• 총 자산: ${portfolio_config.get('total_value', 0):.2f}
• 리밸런싱 주기: {portfolio_config.get('rebalancing_frequency', '주간')}
• 수익실현 임계값: {portfolio_config.get('profit_threshold', 5)}%
• 손절매 임계값: {portfolio_config.get('stop_loss_threshold', -3)}%

관리할 항목을 선택하세요:
        """

        await update.callback_query.edit_message_text(
            text=portfolio_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

        self._update_user_session(
            user_id, MenuLevel.PORTFOLIO, {"config": portfolio_config}
        )

    async def show_confirmation_dialog(
        self, update: Update, action: str, details: Dict
    ) -> None:
        """Show confirmation dialog for important actions.

        Args:
            update: Telegram update object
            action: Action to confirm
            details: Action details
        """
        keyboard = [
            [
                InlineKeyboardButton("✅ 확인", callback_data=f"confirm_{action}"),
                InlineKeyboardButton("❌ 취소", callback_data="cancel_action"),
            ],
            [InlineKeyboardButton("📋 상세 정보", callback_data=f"details_{action}")],
        ]

        confirmation_text = self._format_confirmation_text(action, details)

        await update.callback_query.edit_message_text(
            text=confirmation_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    def _format_confirmation_text(self, action: str, details: Dict) -> str:
        """Format confirmation dialog text.

        Args:
            action: Action to confirm
            details: Action details

        Returns:
            str: Formatted confirmation text
        """
        action_descriptions = {
            "start_system": "시스템 시작",
            "stop_system": "시스템 중지",
            "restart_system": "시스템 재시작",
            "emergency_stop": "긴급 중지",
            "change_risk_level": "리스크 레벨 변경",
            "update_limits": "거래 한도 변경",
        }

        action_name = action_descriptions.get(action, action)

        text = f"""
⚠️ **작업 확인 필요**

**작업**: {action_name}
**요청 시간**: {datetime.now().strftime('%H:%M:%S')}
        """

        if details:
            text += "\n**변경 내용**:\n"
            for key, value in details.items():
                text += f"• {key}: {value}\n"

        text += """
이 작업을 실행하시겠습니까?

⚠️ **주의**: 이 작업은 실제 거래에 영향을 줄 수 있습니다.
        """

        return text

    async def handle_callback_query(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle inline keyboard callback queries.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        query = update.callback_query
        await query.answer()

        callback_data = query.data
        user_id = update.effective_user.id

        try:
            # Route to appropriate handler
            if callback_data.startswith("menu_"):
                await self._handle_menu_navigation(update, context, callback_data)
            elif callback_data.startswith("action_"):
                await self._handle_action_request(update, context, callback_data)
            elif callback_data.startswith("settings_"):
                await self._handle_settings_navigation(update, context, callback_data)
            elif callback_data.startswith("confirm_"):
                await self._handle_confirmation(update, context, callback_data)
            elif callback_data.startswith("quick_"):
                await self._handle_quick_action(update, context, callback_data)
            else:
                await self._handle_unknown_callback(update, context, callback_data)

        except Exception as e:
            logger.error(f"Error handling callback {callback_data}: {e}")
            await query.edit_message_text(
                "❌ 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🏠 메인 메뉴", callback_data="menu_main")]]
                ),
            )

    async def _handle_menu_navigation(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str
    ) -> None:
        """Handle menu navigation callbacks."""
        menu_type = callback_data.split("_")[1]

        if menu_type == "main":
            await self.show_main_menu(update, context)
        elif menu_type == "settings":
            await self.show_settings_menu(update, context)
        elif menu_type == "notifications":
            await self._show_notifications_menu(update, context)

    async def _handle_settings_navigation(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str
    ) -> None:
        """Handle settings navigation callbacks."""
        settings_type = callback_data.split("_")[1]

        if settings_type == "trading":
            await self.show_trading_settings(update, context)
        elif settings_type == "portfolio":
            await self.show_portfolio_settings(update, context)
        elif settings_type == "notifications":
            await self._show_notifications_menu(update, context)
        elif settings_type == "security":
            await self._show_security_menu(update, context)
        elif settings_type == "advanced":
            await self._show_advanced_menu(update, context)

    async def _handle_action_request(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str
    ) -> None:
        """Handle action request callbacks."""
        action = callback_data.split("_")[1]

        # Show confirmation for important actions
        if action in ["start", "stop", "restart"]:
            await self.show_confirmation_dialog(update, f"{action}_system", {})
        else:
            # Execute action directly for safe actions
            await self._execute_action(update, context, action)

    async def _handle_quick_action(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str
    ) -> None:
        """Handle quick action callbacks."""
        action = callback_data.split("_")[1]

        if action == "status":
            # Show quick status update
            status = await self._get_system_status()
            status_text = f"""
📊 **빠른 상태 확인** ({datetime.now().strftime('%H:%M:%S')})

**시스템**: {'🟢 정상' if status.get('healthy') else '🔴 문제'}
**거래**: {'🟢 활성' if status.get('trading_active') else '🔴 중지'}
**전략**: {status.get('active_strategies', 0)}개 활성
**응답시간**: {status.get('avg_response_time', 0):.1f}ms
            """

            keyboard = [
                [
                    InlineKeyboardButton("🔄 새로고침", callback_data="quick_status"),
                    InlineKeyboardButton("↩️ 메인", callback_data="menu_main"),
                ]
            ]

            await update.callback_query.edit_message_text(
                status_text, reply_markup=InlineKeyboardMarkup(keyboard)
            )

    def _update_user_session(self, user_id: int, level: MenuLevel, data: Dict) -> None:
        """Update user session data."""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {}

        self.user_sessions[user_id].update(
            {"current_level": level, "last_update": datetime.now(), "data": data}
        )

    async def _get_system_status(self) -> Dict[str, Any]:
        """Get current system status."""
        if self.service_client:
            try:
                return await self.service_client.get_system_status()
            except Exception as e:
                logger.error(f"Failed to get system status: {e}")

        # Fallback status
        return {
            "healthy": True,
            "trading_active": False,
            "active_strategies": 0,
            "total_value": 100.0,
            "status_text": "시뮬레이션 모드",
            "avg_response_time": 1.0,
        }

    async def _get_trading_config(self) -> Dict[str, Any]:
        """Get current trading configuration."""
        return {
            "active_strategies": 1,
            "risk_level": "중간",
            "daily_limit": 100.0,
            "auto_trading": True,
        }

    async def _get_portfolio_config(self) -> Dict[str, Any]:
        """Get current portfolio configuration."""
        return {
            "total_value": 100.0,
            "rebalancing_frequency": "주간",
            "profit_threshold": 5,
            "stop_loss_threshold": -3,
        }

    async def _show_notifications_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Show notifications settings menu."""
        keyboard = [
            [InlineKeyboardButton("📱 일반 알림 설정", callback_data="notify_general")],
            [
                InlineKeyboardButton(
                    "🚨 긴급 알림 설정", callback_data="notify_emergency"
                )
            ],
            [InlineKeyboardButton("📊 정기 보고 설정", callback_data="notify_reports")],
            [InlineKeyboardButton("↩️ 설정 메뉴", callback_data="menu_settings")],
        ]

        await update.callback_query.edit_message_text(
            "🔔 **알림 설정 메뉴**\n\n설정할 알림을 선택하세요:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    async def _show_security_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Show security settings menu."""
        keyboard = [
            [InlineKeyboardButton("🔐 2FA 설정", callback_data="security_2fa")],
            [InlineKeyboardButton("🌐 IP 화이트리스트", callback_data="security_ip")],
            [InlineKeyboardButton("🔑 API 키 관리", callback_data="security_api")],
            [InlineKeyboardButton("↩️ 설정 메뉴", callback_data="menu_settings")],
        ]

        await update.callback_query.edit_message_text(
            "🛡️ **보안 설정 메뉴**\n\n보안 설정을 관리하세요:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    async def _show_advanced_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Show advanced settings menu."""
        keyboard = [
            [InlineKeyboardButton("🔧 시스템 설정", callback_data="advanced_system")],
            [InlineKeyboardButton("📡 API 연결", callback_data="advanced_api")],
            [InlineKeyboardButton("🐛 디버그 모드", callback_data="advanced_debug")],
            [InlineKeyboardButton("↩️ 설정 메뉴", callback_data="menu_settings")],
        ]

        await update.callback_query.edit_message_text(
            "🔧 **고급 설정 메뉴**\n\n고급 시스템 설정:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    async def _execute_action(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, action: str
    ) -> None:
        """Execute system action."""
        await update.callback_query.edit_message_text(
            f"⚡ {action} 액션이 실행되었습니다.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🏠 메인 메뉴", callback_data="menu_main")]]
            ),
        )

    async def _handle_confirmation(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str
    ) -> None:
        """Handle confirmation callbacks."""
        action = callback_data.replace("confirm_", "")
        await self._execute_action(update, context, action)

    async def _handle_unknown_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str
    ) -> None:
        """Handle unknown callback data."""
        await update.callback_query.edit_message_text(
            f"❓ 알 수 없는 액션: {callback_data}",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🏠 메인 메뉴", callback_data="menu_main")]]
            ),
        )
