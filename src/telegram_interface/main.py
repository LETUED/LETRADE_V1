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
    filters,
    ContextTypes
)

from common.message_bus import MessageBus
from .auth import AuthManager
from .commands import CommandHandler
from .notifications import NotificationManager
from .message_integration import TelegramMessageIntegration

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
                self.message_bus = MessageBus()
                await self.message_bus.connect()
            
            # Create application
            self.application = Application.builder().token(self.bot_token).build()
            
            # Register command handlers
            await self._register_handlers()
            
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
        """Register all command and message handlers."""
        # Basic commands
        self.application.add_handler(
            TgCommandHandler("start", self._handle_start)
        )
        self.application.add_handler(
            TgCommandHandler("help", self._handle_help)
        )
        self.application.add_handler(
            TgCommandHandler("status", self._handle_status)
        )
        
        # Portfolio and position commands
        self.application.add_handler(
            TgCommandHandler("portfolio", self._handle_portfolio)
        )
        self.application.add_handler(
            TgCommandHandler("positions", self._handle_positions)
        )
        self.application.add_handler(
            TgCommandHandler("strategies", self._handle_strategies)
        )
        
        # Control commands
        self.application.add_handler(
            TgCommandHandler("stop_strategy", self._handle_stop_strategy)
        )
        self.application.add_handler(
            TgCommandHandler("start_strategy", self._handle_start_strategy)
        )
        
        # Profit/performance commands
        self.application.add_handler(
            TgCommandHandler("profit", self._handle_profit)
        )
        
        # Unknown command handler
        self.application.add_handler(
            MessageHandler(filters.COMMAND, self._handle_unknown_command)
        )
        
        logger.info("Command handlers registered")
    
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
    
    # Command handlers (will be implemented in next tasks)
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        if not await self._check_auth(update):
            return
            
        await self.command_handler.handle_start(update, context, self.message_bus)
    
    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        if not await self._check_auth(update):
            return
            
        await self.command_handler.handle_help(update, context)
    
    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        if not await self._check_auth(update):
            return
            
        await self.command_handler.handle_status(update, context, self.message_bus)
    
    async def _handle_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /portfolio command."""
        if not await self._check_auth(update):
            return
            
        await self.command_handler.handle_portfolio(update, context, self.message_bus)
    
    async def _handle_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /positions command."""
        if not await self._check_auth(update):
            return
            
        await self.command_handler.handle_positions(update, context, self.message_bus)
    
    async def _handle_strategies(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /strategies command."""
        if not await self._check_auth(update):
            return
            
        await self.command_handler.handle_strategies(update, context, self.message_bus)
    
    async def _handle_stop_strategy(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stop_strategy command."""
        if not await self._check_auth(update):
            return
            
        await self.command_handler.handle_stop_strategy(update, context, self.message_bus)
    
    async def _handle_start_strategy(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start_strategy command."""
        if not await self._check_auth(update):
            return
            
        await self.command_handler.handle_start_strategy(update, context, self.message_bus)
    
    async def _handle_profit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /profit command."""
        if not await self._check_auth(update):
            return
            
        await self.command_handler.handle_profit(update, context, self.message_bus)
    
    async def _handle_unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle unknown commands."""
        if not await self._check_auth(update):
            return
            
        await update.message.reply_text(
            "❓ Unknown command. Type /help for available commands."
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on Telegram Bot.
        
        Returns:
            dict: Health status information
        """
        return {
            'telegram_bot_running': self.is_running,
            'message_bus_connected': self.message_bus.is_connected if self.message_bus else False,
            'message_integration_connected': self.message_integration.is_connected,
            'authenticated_users': len(self.auth_manager.authenticated_users),
            'bot_token_configured': bool(self.bot_token),
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