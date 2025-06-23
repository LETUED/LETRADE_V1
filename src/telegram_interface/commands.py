"""Command handlers for Telegram Bot.

Implements all Telegram commands according to MVP specification section 6.3.
Provides system monitoring, control, and information retrieval capabilities.
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import ContextTypes

from common.message_bus import MessageBus

logger = logging.getLogger(__name__)


class CommandHandler:
    """Handles all Telegram command processing.
    
    Implements FR-TI-001 (명령어 처리) from MVP specification.
    Provides secure command execution with proper error handling.
    """
    
    def __init__(self):
        """Initialize command handler."""
        self.pending_requests: Dict[str, Dict] = {}
        logger.info("Command handler initialized")
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_bus: MessageBus) -> None:
        """Handle /start command - Bot 시작 및 인증.
        
        Args:
            update: Telegram update object
            context: Telegram context object  
            message_bus: Message bus for system communication
        """
        user = update.effective_user
        
        welcome_message = f"""
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
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
        
        # Log authentication success
        logger.info(f"User {user.id} (@{user.username}) started bot session")
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command - 도움말 및 명령어 목록.
        
        Args:
            update: Telegram update object
            context: Telegram context object
        """
        help_message = """
📚 **Letrade V1 명령어 가이드**

**🔍 시스템 조회 명령어:**
/status - 전체 시스템 상태 조회
/portfolio - 포트폴리오 현황 및 잔고
/positions - 현재 보유 포지션 목록
/strategies - 활성 전략 목록 및 상태

**🎛️ 시스템 제어 명령어:**
/start_strategy [ID] - 특정 전략 시작
/stop_strategy [ID] - 특정 전략 중지

**📈 성과 분석 명령어:**
/profit [period] - 수익률 조회
   - period: today, week, month (기본값: today)

**ℹ️ 기타 명령어:**
/help - 이 도움말 표시
/start - 봇 시작 및 환영 메시지

**💡 사용 팁:**
• 명령어는 대소문자를 구분하지 않습니다
• [ID]는 전략 번호를 의미합니다 (예: /stop_strategy 1)
• 시스템은 실시간으로 거래 알림을 전송합니다

**🆘 문제가 있나요?**
시스템 오류나 문의사항이 있으시면 관리자에게 연락해 주세요.

안전한 거래 되세요! 🛡️
        """
        
        await update.message.reply_text(help_message, parse_mode='Markdown')
    
    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_bus: MessageBus) -> None:
        """Handle /status command - 시스템 상태 조회.
        
        Args:
            update: Telegram update object
            context: Telegram context object
            message_bus: Message bus for system communication
        """
        try:
            # Send status request to Core Engine
            request_id = str(uuid.uuid4())
            
            status_request = {
                'request_id': request_id,
                'type': 'system_status',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'user_id': update.effective_user.id
            }
            
            # Store pending request
            self.pending_requests[request_id] = {
                'chat_id': update.effective_chat.id,
                'message_id': update.message.message_id,
                'type': 'status',
                'timestamp': datetime.now(timezone.utc)
            }
            
            # Send request via message bus
            await message_bus.publish(
                routing_key='request.system.status',
                message=status_request
            )
            
            # Send immediate response
            status_message = """
🔍 **시스템 상태 조회 중...**

잠시만 기다려주세요. 시스템 상태를 확인하고 있습니다.

⏳ 예상 소요 시간: 2-3초
            """
            
            await update.message.reply_text(status_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error handling status command: {e}")
            await update.message.reply_text(
                "❌ 시스템 상태 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
            )
    
    async def handle_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_bus: MessageBus) -> None:
        """Handle /portfolio command - 포트폴리오 현황.
        
        Args:
            update: Telegram update object
            context: Telegram context object
            message_bus: Message bus for system communication
        """
        try:
            # Send portfolio request
            request_id = str(uuid.uuid4())
            
            portfolio_request = {
                'request_id': request_id,
                'type': 'portfolio_status',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'user_id': update.effective_user.id
            }
            
            # Store pending request
            self.pending_requests[request_id] = {
                'chat_id': update.effective_chat.id,
                'message_id': update.message.message_id,
                'type': 'portfolio',
                'timestamp': datetime.now(timezone.utc)
            }
            
            # Send request via message bus
            await message_bus.publish(
                routing_key='request.portfolio.status',
                message=portfolio_request
            )
            
            # Send immediate response
            await update.message.reply_text(
                "💼 **포트폴리오 정보 조회 중...**\n\n"
                "잠시만 기다려주세요. 포트폴리오 현황을 불러오고 있습니다.",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error handling portfolio command: {e}")
            await update.message.reply_text(
                "❌ 포트폴리오 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
            )
    
    async def handle_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_bus: MessageBus) -> None:
        """Handle /positions command - 현재 포지션 목록.
        
        Args:
            update: Telegram update object
            context: Telegram context object
            message_bus: Message bus for system communication
        """
        try:
            # Send positions request
            request_id = str(uuid.uuid4())
            
            positions_request = {
                'request_id': request_id,
                'type': 'positions_status',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'user_id': update.effective_user.id
            }
            
            # Store pending request
            self.pending_requests[request_id] = {
                'chat_id': update.effective_chat.id,
                'message_id': update.message.message_id,
                'type': 'positions',
                'timestamp': datetime.now(timezone.utc)
            }
            
            # Send request via message bus
            await message_bus.publish(
                routing_key='request.positions.status',
                message=positions_request
            )
            
            await update.message.reply_text(
                "📊 **포지션 정보 조회 중...**\n\n"
                "현재 보유 중인 모든 포지션을 확인하고 있습니다.",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error handling positions command: {e}")
            await update.message.reply_text(
                "❌ 포지션 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
            )
    
    async def handle_strategies(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_bus: MessageBus) -> None:
        """Handle /strategies command - 전략 목록 및 상태.
        
        Args:
            update: Telegram update object
            context: Telegram context object
            message_bus: Message bus for system communication
        """
        try:
            # Send strategies request
            request_id = str(uuid.uuid4())
            
            strategies_request = {
                'request_id': request_id,
                'type': 'strategies_status',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'user_id': update.effective_user.id
            }
            
            # Store pending request
            self.pending_requests[request_id] = {
                'chat_id': update.effective_chat.id,
                'message_id': update.message.message_id,
                'type': 'strategies',
                'timestamp': datetime.now(timezone.utc)
            }
            
            # Send request via message bus
            await message_bus.publish(
                routing_key='request.strategies.status',
                message=strategies_request
            )
            
            await update.message.reply_text(
                "🎯 **전략 상태 조회 중...**\n\n"
                "모든 거래 전략의 현재 상태를 확인하고 있습니다.",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error handling strategies command: {e}")
            await update.message.reply_text(
                "❌ 전략 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
            )
    
    async def handle_stop_strategy(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_bus: MessageBus) -> None:
        """Handle /stop_strategy command - 특정 전략 중지.
        
        Args:
            update: Telegram update object
            context: Telegram context object
            message_bus: Message bus for system communication
        """
        try:
            # Parse strategy ID from command
            command_args = context.args
            if not command_args:
                await update.message.reply_text(
                    "❌ **사용법 오류**\n\n"
                    "전략 ID를 지정해야 합니다.\n\n"
                    "**사용법:** `/stop_strategy [전략ID]`\n"
                    "**예시:** `/stop_strategy 1`\n\n"
                    "전략 목록은 /strategies 명령어로 확인하세요.",
                    parse_mode='Markdown'
                )
                return
            
            try:
                strategy_id = int(command_args[0])
            except ValueError:
                await update.message.reply_text(
                    "❌ **잘못된 전략 ID**\n\n"
                    "전략 ID는 숫자여야 합니다.\n\n"
                    "**예시:** `/stop_strategy 1`",
                    parse_mode='Markdown'
                )
                return
            
            # Send stop strategy command
            request_id = str(uuid.uuid4())
            
            stop_command = {
                'request_id': request_id,
                'type': 'stop_strategy',
                'strategy_id': strategy_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'user_id': update.effective_user.id,
                'username': update.effective_user.username
            }
            
            # Store pending request
            self.pending_requests[request_id] = {
                'chat_id': update.effective_chat.id,
                'message_id': update.message.message_id,
                'type': 'stop_strategy',
                'strategy_id': strategy_id,
                'timestamp': datetime.now(timezone.utc)
            }
            
            # Send command via message bus
            await message_bus.publish(
                routing_key='commands.strategy.stop',
                message=stop_command
            )
            
            await update.message.reply_text(
                f"🛑 **전략 {strategy_id} 중지 요청**\n\n"
                f"전략 #{strategy_id}를 안전하게 중지하고 있습니다.\n"
                f"현재 진행 중인 거래가 완료되면 전략이 중지됩니다.\n\n"
                f"⏳ 처리 중...",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error handling stop_strategy command: {e}")
            await update.message.reply_text(
                "❌ 전략 중지 요청 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
            )
    
    async def handle_start_strategy(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_bus: MessageBus) -> None:
        """Handle /start_strategy command - 특정 전략 시작.
        
        Args:
            update: Telegram update object
            context: Telegram context object
            message_bus: Message bus for system communication
        """
        try:
            # Parse strategy ID from command
            command_args = context.args
            if not command_args:
                await update.message.reply_text(
                    "❌ **사용법 오류**\n\n"
                    "전략 ID를 지정해야 합니다.\n\n"
                    "**사용법:** `/start_strategy [전략ID]`\n"
                    "**예시:** `/start_strategy 1`\n\n"
                    "전략 목록은 /strategies 명령어로 확인하세요.",
                    parse_mode='Markdown'
                )
                return
            
            try:
                strategy_id = int(command_args[0])
            except ValueError:
                await update.message.reply_text(
                    "❌ **잘못된 전략 ID**\n\n"
                    "전략 ID는 숫자여야 합니다.\n\n"
                    "**예시:** `/start_strategy 1`",
                    parse_mode='Markdown'
                )
                return
            
            # Send start strategy command
            request_id = str(uuid.uuid4())
            
            start_command = {
                'request_id': request_id,
                'type': 'start_strategy',
                'strategy_id': strategy_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'user_id': update.effective_user.id,
                'username': update.effective_user.username
            }
            
            # Store pending request
            self.pending_requests[request_id] = {
                'chat_id': update.effective_chat.id,
                'message_id': update.message.message_id,
                'type': 'start_strategy',
                'strategy_id': strategy_id,
                'timestamp': datetime.now(timezone.utc)
            }
            
            # Send command via message bus
            await message_bus.publish(
                routing_key='commands.strategy.start',
                message=start_command
            )
            
            await update.message.reply_text(
                f"🚀 **전략 {strategy_id} 시작 요청**\n\n"
                f"전략 #{strategy_id}를 시작하고 있습니다.\n"
                f"시스템 검증과 초기화가 완료되면 거래를 시작합니다.\n\n"
                f"⏳ 처리 중...",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error handling start_strategy command: {e}")
            await update.message.reply_text(
                "❌ 전략 시작 요청 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
            )
    
    async def handle_profit(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_bus: MessageBus) -> None:
        """Handle /profit command - 수익률 조회.
        
        Args:
            update: Telegram update object
            context: Telegram context object
            message_bus: Message bus for system communication
        """
        try:
            # Parse period from command (default: today)
            period = 'today'
            if context.args:
                provided_period = context.args[0].lower()
                if provided_period in ['today', 'week', 'month']:
                    period = provided_period
                else:
                    await update.message.reply_text(
                        "❌ **잘못된 기간 설정**\n\n"
                        "지원되는 기간: today, week, month\n\n"
                        "**사용법:** `/profit [기간]`\n"
                        "**예시:** `/profit week`",
                        parse_mode='Markdown'
                    )
                    return
            
            # Send profit request
            request_id = str(uuid.uuid4())
            
            profit_request = {
                'request_id': request_id,
                'type': 'profit_analysis',
                'period': period,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'user_id': update.effective_user.id
            }
            
            # Store pending request
            self.pending_requests[request_id] = {
                'chat_id': update.effective_chat.id,
                'message_id': update.message.message_id,
                'type': 'profit',
                'period': period,
                'timestamp': datetime.now(timezone.utc)
            }
            
            # Send request via message bus
            await message_bus.publish(
                routing_key='request.profit.analysis',
                message=profit_request
            )
            
            period_korean = {
                'today': '오늘',
                'week': '이번 주',
                'month': '이번 달'
            }
            
            await update.message.reply_text(
                f"📈 **{period_korean[period]} 수익률 분석 중...**\n\n"
                f"거래 내역과 성과를 분석하고 있습니다.\n"
                f"잠시만 기다려주세요.",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error handling profit command: {e}")
            await update.message.reply_text(
                "❌ 수익률 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
            )
    
    async def process_response(self, response_data: Dict[str, Any], bot: Optional[Any] = None) -> None:
        """Process response from Core Engine and send to user.
        
        Args:
            response_data: Response data from Core Engine
            bot: Telegram bot instance (optional)
        """
        try:
            request_id = response_data.get('request_id')
            if not request_id or request_id not in self.pending_requests:
                logger.warning(f"Received response for unknown request: {request_id}")
                return
            
            pending_request = self.pending_requests[request_id]
            chat_id = pending_request['chat_id']
            request_type = pending_request['type']
            
            # Format response based on type
            message = await self._format_response(request_type, response_data, pending_request)
            
            # Send response to user
            if bot:
                await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='Markdown'
                )
            else:
                logger.warning(f"Cannot send response - bot instance not provided for request {request_id}")
            
            # Clean up pending request
            del self.pending_requests[request_id]
            
        except Exception as e:
            logger.error(f"Error processing response: {e}")
    
    async def _format_response(self, request_type: str, response_data: Dict[str, Any], pending_request: Dict[str, Any]) -> str:
        """Format response message based on request type.
        
        Args:
            request_type: Type of the original request
            response_data: Response data from Core Engine
            pending_request: Original request information
            
        Returns:
            str: Formatted message for user
        """
        if request_type == 'status':
            return self._format_status_response(response_data)
        elif request_type == 'portfolio':
            return self._format_portfolio_response(response_data)
        elif request_type == 'positions':
            return self._format_positions_response(response_data)
        elif request_type == 'strategies':
            return self._format_strategies_response(response_data)
        elif request_type in ['start_strategy', 'stop_strategy']:
            return self._format_strategy_control_response(response_data, pending_request)
        elif request_type == 'profit':
            return self._format_profit_response(response_data, pending_request)
        else:
            return "✅ 요청이 성공적으로 처리되었습니다."
    
    def _format_status_response(self, response_data: Dict[str, Any]) -> str:
        """Format system status response."""
        status = response_data.get('status', {})
        
        # System status indicators
        system_healthy = status.get('healthy', False)
        status_icon = "🟢" if system_healthy else "🔴"
        status_text = "정상" if system_healthy else "오류"
        
        message = f"""
{status_icon} **시스템 상태: {status_text}**

**📊 핵심 지표:**
• 시스템 가동률: {status.get('uptime', 'N/A')}
• 활성 전략 수: {status.get('active_strategies', 0)}개
• 연결된 거래소: {status.get('connected_exchanges', 0)}개
• 메시지 버스: {'🟢 연결됨' if status.get('message_bus_connected') else '🔴 연결 끊김'}

**💼 포트폴리오:**
• 총 자산: ${status.get('total_portfolio_value', 0):,.2f}
• 가용 자금: ${status.get('available_capital', 0):,.2f}
• 진행 중인 거래: {status.get('active_trades', 0)}개

**⚡ 성능:**
• 평균 응답 시간: {status.get('avg_response_time', 0)}ms
• 초당 처리량: {status.get('throughput', 0)}

🕐 마지막 업데이트: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}
        """
        
        return message.strip()
    
    def _format_portfolio_response(self, response_data: Dict[str, Any]) -> str:
        """Format portfolio status response."""
        # This will be implemented when we receive actual portfolio data structure
        return "💼 **포트폴리오 정보**\n\n포트폴리오 데이터 형식화 구현 예정"
    
    def _format_positions_response(self, response_data: Dict[str, Any]) -> str:
        """Format positions status response."""
        # This will be implemented when we receive actual positions data structure
        return "📊 **포지션 정보**\n\n포지션 데이터 형식화 구현 예정"
    
    def _format_strategies_response(self, response_data: Dict[str, Any]) -> str:
        """Format strategies status response."""
        # This will be implemented when we receive actual strategies data structure
        return "🎯 **전략 정보**\n\n전략 데이터 형식화 구현 예정"
    
    def _format_strategy_control_response(self, response_data: Dict[str, Any], pending_request: Dict[str, Any]) -> str:
        """Format strategy control response."""
        strategy_id = pending_request.get('strategy_id')
        action = pending_request.get('type')
        success = response_data.get('success', False)
        
        if action == 'start_strategy':
            if success:
                return f"✅ **전략 {strategy_id} 시작 완료**\n\n전략이 성공적으로 시작되었습니다."
            else:
                error = response_data.get('error', '알 수 없는 오류')
                return f"❌ **전략 {strategy_id} 시작 실패**\n\n오류: {error}"
        else:  # stop_strategy
            if success:
                return f"✅ **전략 {strategy_id} 중지 완료**\n\n전략이 안전하게 중지되었습니다."
            else:
                error = response_data.get('error', '알 수 없는 오류')
                return f"❌ **전략 {strategy_id} 중지 실패**\n\n오류: {error}"
    
    def _format_profit_response(self, response_data: Dict[str, Any], pending_request: Dict[str, Any]) -> str:
        """Format profit analysis response."""
        period = pending_request.get('period', 'today')
        period_korean = {
            'today': '오늘',
            'week': '이번 주', 
            'month': '이번 달'
        }
        
        return f"📈 **{period_korean[period]} 수익률 분석**\n\n수익률 데이터 형식화 구현 예정"