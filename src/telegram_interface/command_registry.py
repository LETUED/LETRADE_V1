"""Command Registry for BotFather-style automatic command registration.

Implements automatic command registration with descriptions that appear
when users type '/' in Telegram, similar to BotFather's UX.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime

from telegram import BotCommand
from telegram.ext import Application

logger = logging.getLogger(__name__)


class CommandRegistry:
    """BotFather-style automatic command registration system.
    
    Provides automatic command registration with descriptions that appear
    when users type '/' in Telegram, enhancing user experience with
    discoverable and descriptive command interface.
    """
    
    # Core trading commands with descriptions
    CORE_COMMANDS = [
        BotCommand("/start", "🚀 시스템 시작 + 자동 보고 활성화"),
        BotCommand("/stop", "🛑 시스템 완전 중지"),
        BotCommand("/restart", "🔄 시스템 재시작"),
        BotCommand("/status", "📊 실시간 시스템 상태 확인"),
        BotCommand("/portfolio", "💼 포트폴리오 현황 조회"),
        BotCommand("/report", "📈 즉시 상세 보고서 생성"),
        BotCommand("/help", "❓ 도움말 및 명령어 가이드")
    ]
    
    # Advanced commands (shown to experienced users)
    ADVANCED_COMMANDS = [
        BotCommand("/settings", "⚙️ 거래 설정 및 환경 구성"),
        BotCommand("/alerts", "🔔 알림 설정 관리"),
        BotCommand("/security", "🛡️ 보안 설정 관리"),
        BotCommand("/backup", "💾 데이터 백업 및 복원"),
        BotCommand("/debug", "🔧 디버그 모드 및 로그")
    ]
    
    # Emergency commands (always available)
    EMERGENCY_COMMANDS = [
        BotCommand("/emergency", "🚨 긴급 중지 및 안전 모드"),
        BotCommand("/panic", "⛔ 모든 거래 즉시 중단")
    ]
    
    def __init__(self):
        """Initialize command registry."""
        self.registered_commands: List[BotCommand] = []
        self.user_levels: Dict[int, str] = {}  # user_id -> level mapping
        logger.info("Command registry initialized")
    
    async def register_commands(self, application: Application, user_level: str = "basic") -> bool:
        """Register commands with Telegram based on user level.
        
        Args:
            application: Telegram application instance
            user_level: User experience level (basic, advanced, expert)
            
        Returns:
            bool: True if registration successful
        """
        try:
            commands = self._get_commands_for_level(user_level)
            
            # Register commands with Telegram
            await application.bot.set_my_commands(commands)
            
            self.registered_commands = commands
            logger.info(f"Successfully registered {len(commands)} commands for level: {user_level}")
            
            # Log registered commands for debugging
            for cmd in commands:
                logger.debug(f"Registered: {cmd.command} - {cmd.description}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to register commands: {e}")
            return False
    
    def _get_commands_for_level(self, user_level: str) -> List[BotCommand]:
        """Get appropriate commands based on user level.
        
        Args:
            user_level: User experience level
            
        Returns:
            List[BotCommand]: Commands appropriate for user level
        """
        commands = self.CORE_COMMANDS.copy()
        
        if user_level in ["advanced", "expert"]:
            commands.extend(self.ADVANCED_COMMANDS)
        
        if user_level == "expert":
            commands.extend(self.EMERGENCY_COMMANDS)
        
        return commands
    
    async def update_user_level(self, application: Application, user_id: int, new_level: str) -> bool:
        """Update user level and re-register commands.
        
        Args:
            application: Telegram application instance
            user_id: User ID to update
            new_level: New user level
            
        Returns:
            bool: True if update successful
        """
        try:
            old_level = self.user_levels.get(user_id, "basic")
            self.user_levels[user_id] = new_level
            
            # Re-register commands for new level
            success = await self.register_commands(application, new_level)
            
            if success:
                logger.info(f"Updated user {user_id} level: {old_level} -> {new_level}")
                return True
            else:
                # Rollback on failure
                self.user_levels[user_id] = old_level
                return False
                
        except Exception as e:
            logger.error(f"Failed to update user level: {e}")
            return False
    
    def get_command_help(self, command: str) -> str:
        """Get detailed help for specific command.
        
        Args:
            command: Command name (with or without /)
            
        Returns:
            str: Detailed command help or error message
        """
        # Normalize command format
        if not command.startswith('/'):
            command = f'/{command}'
        
        # Search in all command lists
        all_commands = self.CORE_COMMANDS + self.ADVANCED_COMMANDS + self.EMERGENCY_COMMANDS
        
        for cmd in all_commands:
            if cmd.command == command:
                return self._get_detailed_help(cmd)
        
        return f"❌ 알 수 없는 명령어: {command}\n\n/help 명령어로 전체 목록을 확인하세요."
    
    def _get_detailed_help(self, command: BotCommand) -> str:
        """Get detailed help for a specific command.
        
        Args:
            command: BotCommand instance
            
        Returns:
            str: Detailed help text
        """
        detailed_help = {
            "/start": """
🚀 **시스템 시작 명령어**

**기능**: 거래 시스템을 시작하고 1시간마다 자동 보고를 활성화합니다.

**실행 결과**:
• 모든 거래 전략 활성화
• 자동 포트폴리오 모니터링 시작
• 정기 보고서 자동 전송 (1시간 간격)
• 리스크 관리 시스템 활성화

**주의사항**: 실제 자금을 사용한 거래가 시작됩니다.
""",
            "/stop": """
🛑 **시스템 중지 명령어**

**기능**: 거래 시스템을 완전히 중지합니다.

**실행 결과**:
• 모든 신규 거래 중단
• 자동 보고 시스템 비활성화
• 기존 포지션은 유지 (수동 관리 필요)
• 시스템 안전 모드 활성화

**사용 시점**: 시장 불안정 시 또는 시스템 점검 시
""",
            "/restart": """
🔄 **시스템 재시작 명령어**

**기능**: 거래 시스템을 안전하게 재시작합니다.

**실행 과정**:
1. 현재 거래 안전하게 중지
2. 시스템 상태 초기화
3. 모든 연결 재설정
4. 거래 시스템 재시작

**소요 시간**: 약 2-5초
""",
            "/status": """
📊 **실시간 상태 확인**

**표시 정보**:
• 시스템 전체 상태 (정상/오류)
• 활성 전략 수 및 성과
• 포트폴리오 요약 정보
• 성능 지표 (응답시간, 처리량)
• 다음 예정 작업

**업데이트**: 실시간 최신 정보 제공
""",
            "/portfolio": """
💼 **포트폴리오 현황 조회**

**상세 정보**:
• 총 자산 및 가용 잔고
• 자산별 구성 비율
• 일일/주간/월간 수익률
• 리스크 평가 및 권장 조치
• 포지션별 상세 내역

**업데이트 주기**: 실시간 시세 반영
""",
            "/report": """
📈 **즉시 상세 보고서**

**포함 내용**:
• 종합 포트폴리오 분석
• 전략별 성과 평가
• 거래 활동 요약
• 리스크 분석 리포트
• 개선 권장사항

**생성 시간**: 약 3-5초
""",
            "/help": """
❓ **도움말 시스템**

**제공 정보**:
• 전체 명령어 목록 및 설명
• 사용법 가이드
• 자주 묻는 질문
• 문제 해결 방법
• 연락처 정보

**특징**: 사용자 수준별 맞춤 도움말
"""
        }
        
        return detailed_help.get(command.command, f"{command.description}\n\n자세한 정보는 개발팀에 문의하세요.")
    
    def get_command_stats(self) -> Dict[str, Any]:
        """Get command registration statistics.
        
        Returns:
            dict: Command registration statistics
        """
        return {
            'total_commands': len(self.registered_commands),
            'core_commands': len(self.CORE_COMMANDS),
            'advanced_commands': len(self.ADVANCED_COMMANDS),
            'emergency_commands': len(self.EMERGENCY_COMMANDS),
            'registered_users': len(self.user_levels),
            'user_levels': dict(self.user_levels),
            'last_update': datetime.now().isoformat()
        }
    
    def validate_command_format(self, command: str) -> bool:
        """Validate command format and naming conventions.
        
        Args:
            command: Command to validate
            
        Returns:
            bool: True if command format is valid
        """
        if not command.startswith('/'):
            return False
        
        # Remove the '/' and check the rest
        cmd_name = command[1:]
        
        # Check length (3-20 characters)
        if not (3 <= len(cmd_name) <= 20):
            return False
        
        # Check for valid characters (lowercase letters, numbers, underscores)
        if not cmd_name.replace('_', '').isalnum():
            return False
        
        # Check if starts with letter
        if not cmd_name[0].isalpha():
            return False
        
        return True
    
    async def cleanup_old_commands(self, application: Application) -> bool:
        """Clean up old or unused commands.
        
        Args:
            application: Telegram application instance
            
        Returns:
            bool: True if cleanup successful
        """
        try:
            # Get current commands from Telegram
            current_commands = await application.bot.get_my_commands()
            
            # Re-register only current valid commands
            valid_commands = [cmd for cmd in current_commands if self.validate_command_format(cmd.command)]
            
            if len(valid_commands) != len(current_commands):
                await application.bot.set_my_commands(valid_commands)
                logger.info(f"Cleaned up {len(current_commands) - len(valid_commands)} invalid commands")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup commands: {e}")
            return False