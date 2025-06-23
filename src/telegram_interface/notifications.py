"""Notification system for Telegram Bot.

Implements FR-TI-002 (알림 발송) from MVP specification.
Provides real-time notifications for trading events, system alerts, and performance updates.
"""

import asyncio
import logging
from typing import Dict, Any, List, Set, Optional, Callable
from datetime import datetime, timezone
from enum import Enum

from telegram import Bot
from common.message_bus import MessageBus

logger = logging.getLogger(__name__)


class NotificationLevel(Enum):
    """Notification priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationCategory(Enum):
    """Notification categories."""
    TRADE_EXECUTION = "trade_execution"
    SYSTEM_ALERT = "system_alert"
    PERFORMANCE = "performance"
    ERROR = "error"
    STRATEGY = "strategy"
    PORTFOLIO = "portfolio"


class NotificationManager:
    """Manages real-time notifications for Telegram users.
    
    Implements FR-TI-002 from MVP specification.
    Provides filtering, formatting, and delivery of system notifications.
    """
    
    def __init__(self):
        """Initialize notification manager."""
        self.is_running = False
        self.bot: Optional[Bot] = None
        self.message_bus: Optional[MessageBus] = None
        
        # Notification settings
        self.subscribers: Set[int] = set()  # Chat IDs to send notifications
        self.notification_filters: Dict[int, Dict[str, Any]] = {}  # Per-user filters
        
        # Rate limiting
        self.notification_counts: Dict[int, Dict[str, int]] = {}  # Per-user, per-category counts
        self.rate_limit_window = 300  # 5 minutes
        self.max_notifications_per_window = 20
        
        # Message formatting
        self.emoji_map = {
            NotificationLevel.LOW: "ℹ️",
            NotificationLevel.MEDIUM: "⚠️", 
            NotificationLevel.HIGH: "🔴",
            NotificationLevel.CRITICAL: "🚨"
        }
        
        self.category_emoji = {
            NotificationCategory.TRADE_EXECUTION: "💰",
            NotificationCategory.SYSTEM_ALERT: "🔧",
            NotificationCategory.PERFORMANCE: "📈",
            NotificationCategory.ERROR: "❌",
            NotificationCategory.STRATEGY: "🎯",
            NotificationCategory.PORTFOLIO: "💼"
        }
        
        logger.info("Notification manager initialized")
    
    async def start(self, bot: Bot, message_bus: MessageBus) -> bool:
        """Start notification system.
        
        Args:
            bot: Telegram bot instance
            message_bus: Message bus for receiving events
            
        Returns:
            bool: True if started successfully
        """
        try:
            if self.is_running:
                logger.info("Notification manager already running")
                return True
            
            self.bot = bot
            self.message_bus = message_bus
            
            # Subscribe to notification events
            await self._setup_event_subscriptions()
            
            self.is_running = True
            logger.info("Notification manager started successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start notification manager: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop notification system.
        
        Returns:
            bool: True if stopped successfully
        """
        try:
            self.is_running = False
            self.bot = None
            self.message_bus = None
            
            logger.info("Notification manager stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping notification manager: {e}")
            return False
    
    async def _setup_event_subscriptions(self) -> None:
        """Set up message bus subscriptions for notification events."""
        # Subscribe to various event types
        event_subscriptions = [
            ('events.trade_executed', self._handle_trade_execution),
            ('events.trade_failed', self._handle_trade_error),
            ('events.strategy_started', self._handle_strategy_event),
            ('events.strategy_stopped', self._handle_strategy_event),
            ('events.system_alert', self._handle_system_alert),
            ('events.performance_update', self._handle_performance_update),
            ('events.error', self._handle_error_event),
            ('events.portfolio_update', self._handle_portfolio_update)
        ]
        
        for routing_key, handler in event_subscriptions:
            await self.message_bus.subscribe(routing_key, handler)
        
        logger.info(f"Subscribed to {len(event_subscriptions)} notification events")
    
    def add_subscriber(self, chat_id: int, filters: Optional[Dict[str, Any]] = None) -> None:
        """Add notification subscriber.
        
        Args:
            chat_id: Telegram chat ID
            filters: Notification filters (optional)
        """
        self.subscribers.add(chat_id)
        
        if filters:
            self.notification_filters[chat_id] = filters
        
        # Initialize rate limiting
        if chat_id not in self.notification_counts:
            self.notification_counts[chat_id] = {}
        
        logger.info(f"Added notification subscriber: {chat_id}")
    
    def remove_subscriber(self, chat_id: int) -> None:
        """Remove notification subscriber.
        
        Args:
            chat_id: Telegram chat ID
        """
        self.subscribers.discard(chat_id)
        self.notification_filters.pop(chat_id, None)
        self.notification_counts.pop(chat_id, None)
        
        logger.info(f"Removed notification subscriber: {chat_id}")
    
    async def _handle_trade_execution(self, message: Dict[str, Any]) -> None:
        """Handle trade execution notifications."""
        try:
            notification = {
                'category': NotificationCategory.TRADE_EXECUTION,
                'level': NotificationLevel.MEDIUM,
                'title': '거래 실행 완료',
                'data': message
            }
            
            await self._send_notification(notification)
            
        except Exception as e:
            logger.error(f"Error handling trade execution notification: {e}")
    
    async def _handle_trade_error(self, message: Dict[str, Any]) -> None:
        """Handle trade error notifications."""
        try:
            notification = {
                'category': NotificationCategory.ERROR,
                'level': NotificationLevel.HIGH,
                'title': '거래 실행 오류',
                'data': message
            }
            
            await self._send_notification(notification)
            
        except Exception as e:
            logger.error(f"Error handling trade error notification: {e}")
    
    async def _handle_strategy_event(self, message: Dict[str, Any]) -> None:
        """Handle strategy event notifications."""
        try:
            event_type = message.get('event_type', 'unknown')
            level = NotificationLevel.MEDIUM if 'started' in event_type else NotificationLevel.LOW
            
            notification = {
                'category': NotificationCategory.STRATEGY,
                'level': level,
                'title': f'전략 {event_type}',
                'data': message
            }
            
            await self._send_notification(notification)
            
        except Exception as e:
            logger.error(f"Error handling strategy event notification: {e}")
    
    async def _handle_system_alert(self, message: Dict[str, Any]) -> None:
        """Handle system alert notifications."""
        try:
            severity = message.get('severity', 'medium')
            level_map = {
                'low': NotificationLevel.LOW,
                'medium': NotificationLevel.MEDIUM,
                'high': NotificationLevel.HIGH,
                'critical': NotificationLevel.CRITICAL
            }
            
            notification = {
                'category': NotificationCategory.SYSTEM_ALERT,
                'level': level_map.get(severity, NotificationLevel.MEDIUM),
                'title': '시스템 알림',
                'data': message
            }
            
            await self._send_notification(notification)
            
        except Exception as e:
            logger.error(f"Error handling system alert notification: {e}")
    
    async def _handle_performance_update(self, message: Dict[str, Any]) -> None:
        """Handle performance update notifications."""
        try:
            notification = {
                'category': NotificationCategory.PERFORMANCE,
                'level': NotificationLevel.LOW,
                'title': '성과 업데이트',
                'data': message
            }
            
            await self._send_notification(notification)
            
        except Exception as e:
            logger.error(f"Error handling performance update notification: {e}")
    
    async def _handle_error_event(self, message: Dict[str, Any]) -> None:
        """Handle error event notifications."""
        try:
            error_level = message.get('level', 'medium')
            level_map = {
                'warning': NotificationLevel.MEDIUM,
                'error': NotificationLevel.HIGH,
                'critical': NotificationLevel.CRITICAL
            }
            
            notification = {
                'category': NotificationCategory.ERROR,
                'level': level_map.get(error_level, NotificationLevel.HIGH),
                'title': '시스템 오류',
                'data': message
            }
            
            await self._send_notification(notification)
            
        except Exception as e:
            logger.error(f"Error handling error event notification: {e}")
    
    async def _handle_portfolio_update(self, message: Dict[str, Any]) -> None:
        """Handle portfolio update notifications."""
        try:
            # Only send significant portfolio changes
            change_percent = abs(message.get('change_percent', 0))
            
            if change_percent >= 5:  # 5% or more change
                level = NotificationLevel.HIGH if change_percent >= 10 else NotificationLevel.MEDIUM
                
                notification = {
                    'category': NotificationCategory.PORTFOLIO,
                    'level': level,
                    'title': '포트폴리오 변동',
                    'data': message
                }
                
                await self._send_notification(notification)
            
        except Exception as e:
            logger.error(f"Error handling portfolio update notification: {e}")
    
    async def _send_notification(self, notification: Dict[str, Any]) -> None:
        """Send notification to all subscribers.
        
        Args:
            notification: Notification data
        """
        try:
            if not self.bot or not self.is_running:
                return
            
            category = notification['category']
            level = notification['level']
            title = notification['title']
            data = notification['data']
            
            # Format notification message
            message_text = self._format_notification_message(category, level, title, data)
            
            # Send to all subscribers
            for chat_id in self.subscribers.copy():
                try:
                    # Check rate limiting
                    if not self._check_rate_limit(chat_id, category):
                        continue
                    
                    # Check user filters
                    if not self._should_send_notification(chat_id, category, level):
                        continue
                    
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=message_text,
                        parse_mode='Markdown'
                    )
                    
                    # Update rate limiting
                    self._update_rate_limit_count(chat_id, category)
                    
                except Exception as e:
                    logger.error(f"Failed to send notification to {chat_id}: {e}")
                    # Remove invalid chat IDs
                    if "chat not found" in str(e).lower():
                        self.remove_subscriber(chat_id)
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    
    def _format_notification_message(self, category: NotificationCategory, level: NotificationLevel, 
                                   title: str, data: Dict[str, Any]) -> str:
        """Format notification message for Telegram.
        
        Args:
            category: Notification category
            level: Notification level
            title: Notification title
            data: Notification data
            
        Returns:
            str: Formatted message
        """
        # Get emojis
        level_emoji = self.emoji_map.get(level, "ℹ️")
        category_emoji = self.category_emoji.get(category, "📢")
        
        # Format timestamp
        timestamp = datetime.now(timezone.utc).strftime('%H:%M:%S')
        
        # Base message
        message = f"{level_emoji} {category_emoji} **{title}**\n\n"
        
        # Format based on category
        if category == NotificationCategory.TRADE_EXECUTION:
            message += self._format_trade_execution_data(data)
        elif category == NotificationCategory.SYSTEM_ALERT:
            message += self._format_system_alert_data(data)
        elif category == NotificationCategory.PERFORMANCE:
            message += self._format_performance_data(data)
        elif category == NotificationCategory.ERROR:
            message += self._format_error_data(data)
        elif category == NotificationCategory.STRATEGY:
            message += self._format_strategy_data(data)
        elif category == NotificationCategory.PORTFOLIO:
            message += self._format_portfolio_data(data)
        else:
            message += f"데이터: {data.get('message', '정보 없음')}"
        
        message += f"\n\n🕐 {timestamp} UTC"
        
        return message
    
    def _format_trade_execution_data(self, data: Dict[str, Any]) -> str:
        """Format trade execution notification data."""
        symbol = data.get('symbol', 'N/A')
        side = data.get('side', 'N/A')
        amount = data.get('amount', 0)
        price = data.get('average_price', data.get('price', 0))
        strategy_id = data.get('strategy_id', 'N/A')
        
        side_emoji = "📈" if side.lower() == "buy" else "📉"
        side_korean = "매수" if side.lower() == "buy" else "매도"
        
        return f"""
{side_emoji} **{side_korean} 완료**

**거래 정보:**
• 심볼: {symbol}
• 수량: {amount:,.6f}
• 가격: ${price:,.2f}
• 전략: #{strategy_id}

거래가 성공적으로 체결되었습니다.
        """.strip()
    
    def _format_system_alert_data(self, data: Dict[str, Any]) -> str:
        """Format system alert notification data."""
        message = data.get('message', '시스템 알림')
        component = data.get('component', 'System')
        
        return f"""
**구성요소:** {component}
**메시지:** {message}

시스템 상태를 확인해 주세요.
        """.strip()
    
    def _format_performance_data(self, data: Dict[str, Any]) -> str:
        """Format performance notification data."""
        return f"""
**성과 요약:**
성과 데이터 형식화 구현 예정
        """.strip()
    
    def _format_error_data(self, data: Dict[str, Any]) -> str:
        """Format error notification data."""
        error_message = data.get('error_message', '알 수 없는 오류')
        component = data.get('component', 'System')
        
        return f"""
**구성요소:** {component}
**오류:** {error_message}

조치가 필요할 수 있습니다.
        """.strip()
    
    def _format_strategy_data(self, data: Dict[str, Any]) -> str:
        """Format strategy notification data."""
        strategy_id = data.get('strategy_id', 'N/A')
        event_type = data.get('event_type', 'unknown')
        
        return f"""
**전략 ID:** {strategy_id}
**이벤트:** {event_type}

전략 상태가 변경되었습니다.
        """.strip()
    
    def _format_portfolio_data(self, data: Dict[str, Any]) -> str:
        """Format portfolio notification data."""
        change_percent = data.get('change_percent', 0)
        current_value = data.get('current_value', 0)
        
        change_emoji = "📈" if change_percent > 0 else "📉"
        
        return f"""
{change_emoji} **포트폴리오 변동: {change_percent:+.2f}%**

**현재 가치:** ${current_value:,.2f}

포트폴리오에 상당한 변동이 있었습니다.
        """.strip()
    
    def _check_rate_limit(self, chat_id: int, category: NotificationCategory) -> bool:
        """Check if user is within rate limits for category.
        
        Args:
            chat_id: Telegram chat ID
            category: Notification category
            
        Returns:
            bool: True if within limits
        """
        if chat_id not in self.notification_counts:
            self.notification_counts[chat_id] = {}
        
        category_key = category.value
        current_count = self.notification_counts[chat_id].get(category_key, 0)
        
        return current_count < self.max_notifications_per_window
    
    def _update_rate_limit_count(self, chat_id: int, category: NotificationCategory) -> None:
        """Update rate limit count for user and category.
        
        Args:
            chat_id: Telegram chat ID
            category: Notification category
        """
        category_key = category.value
        if chat_id not in self.notification_counts:
            self.notification_counts[chat_id] = {}
        
        self.notification_counts[chat_id][category_key] = (
            self.notification_counts[chat_id].get(category_key, 0) + 1
        )
    
    def _should_send_notification(self, chat_id: int, category: NotificationCategory, 
                                level: NotificationLevel) -> bool:
        """Check if notification should be sent to user based on filters.
        
        Args:
            chat_id: Telegram chat ID
            category: Notification category
            level: Notification level
            
        Returns:
            bool: True if notification should be sent
        """
        if chat_id not in self.notification_filters:
            return True  # No filters = send all
        
        filters = self.notification_filters[chat_id]
        
        # Check category filter
        allowed_categories = filters.get('categories', [])
        if allowed_categories and category.value not in allowed_categories:
            return False
        
        # Check level filter
        min_level = filters.get('min_level', 'low')
        level_order = ['low', 'medium', 'high', 'critical']
        
        if level_order.index(level.value) < level_order.index(min_level):
            return False
        
        return True
    
    async def send_custom_notification(self, chat_id: int, message: str, 
                                     level: NotificationLevel = NotificationLevel.MEDIUM) -> bool:
        """Send custom notification to specific user.
        
        Args:
            chat_id: Telegram chat ID
            message: Custom message
            level: Notification level
            
        Returns:
            bool: True if sent successfully
        """
        try:
            if not self.bot or not self.is_running:
                return False
            
            level_emoji = self.emoji_map.get(level, "ℹ️")
            formatted_message = f"{level_emoji} **사용자 지정 알림**\n\n{message}"
            
            await self.bot.send_message(
                chat_id=chat_id,
                text=formatted_message,
                parse_mode='Markdown'
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send custom notification: {e}")
            return False