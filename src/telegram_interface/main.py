"""Main Telegram Bot implementation for Letrade_v1 trading system.

Implements FR-TI-001 (명령어 처리) and FR-TI-002 (알림 발송) from MVP specification.
Provides secure, whitelist-based remote access to trading system functionality.
"""

import asyncio
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from telegram import Update, Bot
from telegram.ext import (
    Application, 
    CommandHandler as TgCommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

from common.message_bus import MessageBus
from .auth import AuthManager
from .commands import CommandHandler
from .notifications import NotificationManager
from .message_integration import TelegramMessageIntegration
from .command_registry import CommandRegistry
from .menu_system import MenuSystem

logger = logging.getLogger(__name__)


class TelegramBot:
    """Main Telegram Bot class for Letrade trading system.
    
    Provides secure remote access to system monitoring and control.
    Implements MVP requirements FR-TI-001 and FR-TI-002.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Telegram Bot.
        
        Args:
            config: Bot configuration including token and security settings
        """
        self.config = config
        self.bot_token = config.get('bot_token')
        self.is_running = False
        
        # Initialize components
        self.auth_manager = AuthManager(config.get('auth', {}))
        self.command_handler = CommandHandler()
        self.notification_manager = NotificationManager()
        self.message_integration = TelegramMessageIntegration(
            self.command_handler, 
            self.notification_manager
        )
        self.message_bus = None
        
        # Initialize BotFather-style UI/UX components
        self.command_registry = CommandRegistry()
        self.menu_system = MenuSystem()
        
        # Telegram application
        self.application = None
        
        # Security settings
        self.allowed_users = config.get('allowed_users', [])
        self.rate_limit_window = config.get('rate_limit_window', 60)  # seconds
        self.max_commands_per_window = config.get('max_commands_per_window', 10)
        
        # Command rate limiting
        self.user_command_history: Dict[int, List[datetime]] = {}
        
        logger.info("Telegram Bot initialized")
    
    async def start(self) -> bool:
        """Start the Telegram Bot.
        
        Returns:
            bool: True if started successfully
        """
        try:
            if self.is_running:
                logger.info("Telegram Bot already running")
                return True
            
            if not self.bot_token:
                logger.error("Bot token not provided")
                return False
            
            # Initialize message bus connection
            if not self.message_bus:
                # MessageBus config from bot config or defaults
                message_bus_config = self.config.get('message_bus', {
                    'host': 'localhost',
                    'port': 5672,
                    'username': 'guest',
                    'password': 'guest',
                    'virtual_host': '/',
                    'heartbeat': 60,
                    'connection_timeout': 30
                })
                self.message_bus = MessageBus(message_bus_config)
                await self.message_bus.connect()
            
            # Create application
            self.application = Application.builder().token(self.bot_token).build()
            
            # Register command handlers
            await self._register_handlers()
            
            # Register BotFather-style commands with Telegram
            await self.command_registry.register_commands(self.application)
            
            # Start notification system
            await self.notification_manager.start(self.application.bot, self.message_bus)
            
            # Start message integration
            await self.message_integration.connect(self.message_bus, self.application.bot)
            
            # Start the bot
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            self.is_running = True
            logger.info("Telegram Bot started successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Telegram Bot: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the Telegram Bot.
        
        Returns:
            bool: True if stopped successfully
        """
        try:
            if not self.is_running:
                logger.info("Telegram Bot not running")
                return True
            
            # Stop message integration
            await self.message_integration.disconnect()
            
            # Stop notification system
            await self.notification_manager.stop()
            
            # Stop application
            if self.application:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            
            # Disconnect message bus
            if self.message_bus:
                await self.message_bus.disconnect()
            
            self.is_running = False
            logger.info("Telegram Bot stopped")
            
            return True
            
        except Exception as e:
            logger.error(f"Error stopping Telegram Bot: {e}")
            return False
    
    async def _register_handlers(self) -> None:
        """Register all redesigned command handlers."""
        # Core system control commands
        self.application.add_handler(
            TgCommandHandler("start", self._handle_start)
        )
        self.application.add_handler(
            TgCommandHandler("stop", self._handle_stop)
        )
        self.application.add_handler(
            TgCommandHandler("restart", self._handle_restart)
        )
        
        # Information commands
        self.application.add_handler(
            TgCommandHandler("help", self._handle_help)
        )
        self.application.add_handler(
            TgCommandHandler("status", self._handle_status)
        )
        self.application.add_handler(
            TgCommandHandler("portfolio", self._handle_portfolio)
        )
        self.application.add_handler(
            TgCommandHandler("report", self._handle_report)
        )
        
        # Legacy commands for backward compatibility
        self.application.add_handler(
            TgCommandHandler("positions", self._handle_legacy_positions)
        )
        self.application.add_handler(
            TgCommandHandler("strategies", self._handle_legacy_strategies)
        )
        
        # Settings and menu commands
        self.application.add_handler(
            TgCommandHandler("settings", self._handle_settings)
        )
        self.application.add_handler(
            TgCommandHandler("menu", self._handle_main_menu)
        )
        
        # Callback query handler for inline keyboards
        self.application.add_handler(
            CallbackQueryHandler(self.menu_system.handle_callback_query)
        )
        
        # Unknown command handler
        self.application.add_handler(
            MessageHandler(filters.COMMAND, self._handle_unknown_command)
        )
        
        logger.info("Redesigned command handlers registered")
    
    async def _check_auth(self, update: Update) -> bool:
        """Check if user is authenticated and authorized.
        
        Args:
            update: Telegram update object
            
        Returns:
            bool: True if user is authorized
        """
        user_id = update.effective_user.id
        username = update.effective_user.username
        
        # Check authentication
        if not await self.auth_manager.is_authenticated(user_id, username):
            await update.message.reply_text(
                "❌ Unauthorized access. Contact system administrator."
            )
            logger.warning(f"Unauthorized access attempt from user {user_id} (@{username})")
            return False
        
        # Check rate limiting
        if not self._check_rate_limit(user_id):
            await update.message.reply_text(
                "⚠️ Rate limit exceeded. Please wait before sending more commands."
            )
            logger.warning(f"Rate limit exceeded for user {user_id}")
            return False
        
        return True
    
    def _check_rate_limit(self, user_id: int) -> bool:
        """Check if user is within rate limits.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bool: True if within limits
        """
        now = datetime.now(timezone.utc)
        
        # Initialize user history if not exists
        if user_id not in self.user_command_history:
            self.user_command_history[user_id] = []
        
        # Clean old entries
        cutoff_time = now.timestamp() - self.rate_limit_window
        self.user_command_history[user_id] = [
            cmd_time for cmd_time in self.user_command_history[user_id]
            if cmd_time.timestamp() > cutoff_time
        ]
        
        # Check if within limits
        if len(self.user_command_history[user_id]) >= self.max_commands_per_window:
            return False
        
        # Add current command
        self.user_command_history[user_id].append(now)
        return True
    
    # Redesigned command handlers with intuitive /start /stop /restart structure
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command - Start system with hourly reporting."""
        if not await self._check_auth(update):
            return
        await self.command_handler.handle_start(update, context, self.message_bus)
    
    async def _handle_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stop command - Stop entire system."""
        if not await self._check_auth(update):
            return
        await self.command_handler.handle_stop(update, context, self.message_bus)
    
    async def _handle_restart(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /restart command - Restart system."""
        if not await self._check_auth(update):
            return
        await self.command_handler.handle_restart(update, context, self.message_bus)
    
    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command - Show new intuitive commands."""
        if not await self._check_auth(update):
            return
        await self.command_handler.handle_help(update, context)
    
    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command - Real-time system status."""
        if not await self._check_auth(update):
            return
        await self.command_handler.handle_status(update, context, self.message_bus)
    
    async def _handle_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /portfolio command - Portfolio overview."""
        if not await self._check_auth(update):
            return
        await self.command_handler.handle_portfolio(update, context, self.message_bus)
    
    async def _handle_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /report command - Immediate detailed report."""
        if not await self._check_auth(update):
            return
        await self.command_handler.handle_report(update, context, self.message_bus)
    
    # Legacy command handlers for backward compatibility
    async def _handle_legacy_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle legacy /positions command."""
        if not await self._check_auth(update):
            return
        await update.message.reply_text(
            "📊 /positions 명령어가 업데이트되었습니다!\n\n"
            "새로운 명령어를 사용해주세요:\n"
            "• /portfolio - 포트폴리오 전체 현황\n"
            "• /status - 실시간 시스템 상태\n"
            "• /report - 상세 보고서\n\n"
            "더 간단하고 직관적인 명령어로 바뀌었습니다!"
        )
    
    async def _handle_legacy_strategies(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle legacy /strategies command."""
        if not await self._check_auth(update):
            return
        await update.message.reply_text(
            "🎯 /strategies 명령어가 업데이트되었습니다!\n\n"
            "새로운 명령어를 사용해주세요:\n"
            "• /status - 전략 상태 포함 시스템 현황\n"
            "• /report - 전략 성과 상세 분석\n"
            "• /start - 모든 전략 시작\n"
            "• /stop - 모든 전략 중지\n\n"
            "더 간단하고 직관적인 제어가 가능합니다!"
        )
    
    async def _handle_unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle unknown commands with helpful guidance."""
        if not await self._check_auth(update):
            return
        
        command = update.message.text
        
        # Provide helpful suggestions for common typos or old commands
        suggestions = {
            "/strat": "/start",
            "/stop_strategy": "/stop (전체 시스템 중지)",
            "/start_strategy": "/start (전체 시스템 시작)",
            "/positions": "/portfolio",
            "/strategies": "/status",
            "/profit": "/report"
        }
        
        suggestion_text = ""
        for old_cmd, new_cmd in suggestions.items():
            if old_cmd in command.lower():
                suggestion_text = f"\n\n💡 혹시 '{new_cmd}' 명령어를 찾으시나요?"
                break
        
        await update.message.reply_text(
            f"❓ **알 수 없는 명령어입니다**\n\n"
            f"🎛️ **사용 가능한 핵심 명령어:**\n"
            f"• /start - 시스템 시작\n"
            f"• /stop - 시스템 중지\n"
            f"• /status - 현재 상태\n"
            f"• /portfolio - 포트폴리오\n"
            f"• /settings - 설정 메뉴\n"
            f"• /menu - 메인 메뉴\n"
            f"• /help - 전체 도움말"
            f"{suggestion_text}\n\n"
            f"💡 **팁**: '/' 만 입력하면 전체 명령어 목록이 나타납니다!"
        )
    
    # New BotFather-style menu handlers
    async def _handle_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /settings command - Show BotFather-style settings menu."""
        if not await self._check_auth(update):
            return
        
        # Initialize service client for menu system if needed
        if not self.menu_system.service_client:
            if not self.command_handler.service_client:
                await self.command_handler.initialize_service_client(self.message_bus)
            self.menu_system.service_client = self.command_handler.service_client
        
        await self.menu_system.show_settings_menu(update, context)
    
    async def _handle_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /menu command - Show BotFather-style main menu."""
        if not await self._check_auth(update):
            return
        
        # Initialize service client for menu system if needed
        if not self.menu_system.service_client:
            if not self.command_handler.service_client:
                await self.command_handler.initialize_service_client(self.message_bus)
            self.menu_system.service_client = self.command_handler.service_client
        
        await self.menu_system.show_main_menu(update, context)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on redesigned Telegram Bot.
        
        Returns:
            dict: Health status information
        """
        hourly_reporter_status = False
        if hasattr(self.command_handler, 'hourly_reporter') and self.command_handler.hourly_reporter:
            hourly_reporter_status = self.command_handler.hourly_reporter.is_running
        
        return {
            'telegram_bot_running': self.is_running,
            'message_bus_connected': self.message_bus.is_connected if self.message_bus else False,
            'message_integration_connected': self.message_integration.is_connected,
            'authenticated_users': len(self.auth_manager.authenticated_users),
            'bot_token_configured': bool(self.bot_token),
            'system_running': getattr(self.command_handler, 'system_running', False),
            'hourly_reporting_enabled': getattr(self.command_handler, 'reporting_enabled', False),
            'hourly_reporter_active': hourly_reporter_status,
            'command_structure': 'redesigned_v2',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }


async def main():
    """Main entry point for testing Telegram Bot."""
    logging.basicConfig(level=logging.INFO)
    
    # Test configuration (use environment variables in production)
    config = {
        'bot_token': os.getenv('TELEGRAM_BOT_TOKEN'),
        'auth': {
            'allowed_users': [int(uid) for uid in os.getenv('TELEGRAM_ALLOWED_USERS', '').split(',') if uid],
            'allowed_usernames': os.getenv('TELEGRAM_ALLOWED_USERNAMES', '').split(',')
        },
        'rate_limit_window': 60,
        'max_commands_per_window': 10
    }
    
    if not config['bot_token']:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
        return
    
    # Create and start bot
    bot = TelegramBot(config)
    
    try:
        if await bot.start():
            logger.info("Telegram Bot started successfully")
            
            # Keep running
            while bot.is_running:
                await asyncio.sleep(1)
                
        else:
            logger.error("Failed to start Telegram Bot")
            
    except KeyboardInterrupt:
        logger.info("Shutting down Telegram Bot...")
    except Exception as e:
        logger.error(f"Telegram Bot error: {e}")
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())