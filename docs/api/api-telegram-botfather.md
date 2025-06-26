# BotFather 스타일 UI/UX API 참조 문서

## 📋 개요

Letrade V1 텔레그램 봇의 BotFather 스타일 고급 UI/UX 시스템에 대한 API 참조 문서입니다. 개발자들이 시스템을 확장하거나 수정할 때 필요한 모든 API 정보를 제공합니다.

## 🏗️ 아키텍처 구조

```python
TelegramBot
├── CommandRegistry    # 자동 명령어 등록 API
├── MenuSystem        # 계층적 메뉴 시스템 API  
├── CallbackHandler   # 인라인 키보드 처리 API
└── ServiceClient     # 실제 시스템 연동 API
```

## 📚 핵심 API 클래스

### CommandRegistry

자동 명령어 등록 및 관리를 담당하는 클래스입니다.

#### 클래스 정의
```python
class CommandRegistry:
    """BotFather 스타일 자동 명령어 등록 시스템."""
    
    def __init__(self):
        self.registered_commands: List[BotCommand] = []
        self.user_levels: Dict[int, str] = {}
```

#### 주요 메서드

##### `register_commands()`
```python
async def register_commands(
    self, 
    application: Application, 
    user_level: str = "basic"
) -> bool:
    """텔레그램에 명령어를 등록합니다.
    
    Args:
        application: 텔레그램 Application 인스턴스
        user_level: 사용자 레벨 ("basic", "advanced", "expert")
        
    Returns:
        bool: 등록 성공 여부
        
    Example:
        registry = CommandRegistry()
        success = await registry.register_commands(app, "advanced")
    """
```

##### `get_command_help()`
```python
def get_command_help(self, command: str) -> str:
    """특정 명령어의 상세 도움말을 반환합니다.
    
    Args:
        command: 명령어 이름 (/ 포함 또는 미포함)
        
    Returns:
        str: 상세 도움말 텍스트
        
    Example:
        help_text = registry.get_command_help("/start")
    """
```

##### `update_user_level()`
```python
async def update_user_level(
    self, 
    application: Application, 
    user_id: int, 
    new_level: str
) -> bool:
    """사용자 레벨을 업데이트하고 명령어를 재등록합니다.
    
    Args:
        application: 텔레그램 Application 인스턴스
        user_id: 사용자 ID
        new_level: 새로운 사용자 레벨
        
    Returns:
        bool: 업데이트 성공 여부
    """
```

#### 명령어 정의

##### 핵심 명령어
```python
CORE_COMMANDS = [
    BotCommand("/start", "🚀 시스템 시작 + 자동 보고 활성화"),
    BotCommand("/stop", "🛑 시스템 완전 중지"),
    BotCommand("/restart", "🔄 시스템 재시작"),
    BotCommand("/status", "📊 실시간 시스템 상태 확인"),
    BotCommand("/portfolio", "💼 포트폴리오 현황 조회"),
    BotCommand("/report", "📈 즉시 상세 보고서 생성"),
    BotCommand("/help", "❓ 도움말 및 명령어 가이드")
]
```

##### 고급 명령어
```python
ADVANCED_COMMANDS = [
    BotCommand("/settings", "⚙️ 거래 설정 및 환경 구성"),
    BotCommand("/alerts", "🔔 알림 설정 관리"),
    BotCommand("/security", "🛡️ 보안 설정 관리"),
    BotCommand("/backup", "💾 데이터 백업 및 복원"),
    BotCommand("/debug", "🔧 디버그 모드 및 로그")
]
```

##### 긴급 명령어
```python
EMERGENCY_COMMANDS = [
    BotCommand("/emergency", "🚨 긴급 중지 및 안전 모드"),
    BotCommand("/panic", "⛔ 모든 거래 즉시 중단")
]
```

### MenuSystem

계층적 메뉴 시스템을 관리하는 클래스입니다.

#### 클래스 정의
```python
class MenuSystem:
    """BotFather 스타일 계층적 메뉴 시스템."""
    
    def __init__(self, service_client=None):
        self.service_client = service_client
        self.user_sessions: Dict[int, Dict] = {}
        self.menu_cache: Dict[str, Any] = {}
```

#### 주요 메서드

##### `show_main_menu()`
```python
async def show_main_menu(
    self, 
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """동적 메인 메뉴를 표시합니다.
    
    시스템 상태에 따라 메뉴 구성이 자동으로 변경됩니다.
    
    Args:
        update: 텔레그램 Update 객체
        context: 텔레그램 Context 객체
        
    Example:
        await menu_system.show_main_menu(update, context)
    """
```

##### `show_settings_menu()`
```python
async def show_settings_menu(
    self, 
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """종합 설정 메뉴를 표시합니다.
    
    5개 주요 카테고리로 구성된 계층적 설정 인터페이스를 제공합니다.
    
    Args:
        update: 텔레그램 Update 객체
        context: 텔레그램 Context 객체
    """
```

##### `show_trading_settings()`
```python
async def show_trading_settings(
    self, 
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """거래 전략 설정 메뉴를 표시합니다.
    
    현재 거래 설정을 확인하고 수정할 수 있는 인터페이스를 제공합니다.
    
    Args:
        update: 텔레그램 Update 객체
        context: 텔레그램 Context 객체
    """
```

##### `show_portfolio_settings()`
```python
async def show_portfolio_settings(
    self, 
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """포트폴리오 관리 설정 메뉴를 표시합니다.
    
    자산 배분, 리밸런싱, 수익실현 등의 설정을 관리합니다.
    
    Args:
        update: 텔레그램 Update 객체
        context: 텔레그램 Context 객체
    """
```

##### `show_confirmation_dialog()`
```python
async def show_confirmation_dialog(
    self, 
    update: Update, 
    action: str, 
    details: Dict
) -> None:
    """중요한 액션에 대한 확인 다이얼로그를 표시합니다.
    
    Args:
        update: 텔레그램 Update 객체
        action: 실행할 액션 이름
        details: 액션 상세 정보
        
    Example:
        await menu_system.show_confirmation_dialog(
            update, 
            "start_system", 
            {"strategy_count": 3}
        )
    """
```

##### `handle_callback_query()`
```python
async def handle_callback_query(
    self, 
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """인라인 키보드 콜백 쿼리를 처리합니다.
    
    Args:
        update: 텔레그램 Update 객체
        context: 텔레그램 Context 객체
        
    처리되는 콜백 패턴:
        - menu_*: 메뉴 네비게이션
        - action_*: 액션 실행 요청
        - settings_*: 설정 네비게이션
        - confirm_*: 확인 다이얼로그
        - quick_*: 빠른 액션
    """
```

#### 메뉴 레벨 정의
```python
class MenuLevel(Enum):
    """메뉴 계층 레벨."""
    MAIN = "main"
    SETTINGS = "settings"
    TRADING = "trading"
    PORTFOLIO = "portfolio"
    NOTIFICATIONS = "notifications"
    SECURITY = "security"
    ADVANCED = "advanced"
```

#### 내부 헬퍼 메서드

##### `_build_main_menu_keyboard()`
```python
def _build_main_menu_keyboard(self, system_status: Dict) -> InlineKeyboardMarkup:
    """시스템 상태 기반 동적 메인 메뉴 키보드를 생성합니다.
    
    Args:
        system_status: 현재 시스템 상태
        
    Returns:
        InlineKeyboardMarkup: 생성된 키보드
    """
```

##### `_format_main_menu_text()`
```python
def _format_main_menu_text(self, system_status: Dict) -> str:
    """메인 메뉴 텍스트를 포맷팅합니다.
    
    Args:
        system_status: 현재 시스템 상태
        
    Returns:
        str: 포맷팅된 메뉴 텍스트
    """
```

##### `_update_user_session()`
```python
def _update_user_session(self, user_id: int, level: MenuLevel, data: Dict) -> None:
    """사용자 세션 데이터를 업데이트합니다.
    
    Args:
        user_id: 사용자 ID
        level: 현재 메뉴 레벨
        data: 세션 데이터
    """
```

### TelegramBot (메인 클래스)

BotFather 스타일 기능이 통합된 메인 텔레그램 봇 클래스입니다.

#### 클래스 정의
```python
class TelegramBot:
    """BotFather 스타일 고급 UI/UX가 통합된 메인 텔레그램 봇."""
    
    def __init__(self, config: Dict[str, Any]):
        # 기존 컴포넌트
        self.auth_manager = AuthManager(config.get('auth', {}))
        self.command_handler = CommandHandler()
        self.notification_manager = NotificationManager()
        
        # BotFather 스타일 컴포넌트
        self.command_registry = CommandRegistry()
        self.menu_system = MenuSystem()
```

#### 통합 메서드

##### `_register_handlers()`
```python
async def _register_handlers(self) -> None:
    """모든 핸들러를 등록합니다.
    
    기존 명령어 핸들러와 BotFather 스타일 핸들러를 모두 등록합니다.
    """
```

##### `_handle_settings()`
```python
async def _handle_settings(
    self, 
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """BotFather 스타일 설정 메뉴 핸들러."""
```

##### `_handle_main_menu()`
```python
async def _handle_main_menu(
    self, 
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """BotFather 스타일 메인 메뉴 핸들러."""
```

## 🔧 콜백 데이터 패턴

### 메뉴 네비게이션
```python
# 패턴: menu_{destination}
"menu_main"         # 메인 메뉴로 이동
"menu_settings"     # 설정 메뉴로 이동
"menu_notifications" # 알림 메뉴로 이동
```

### 액션 실행
```python
# 패턴: action_{action_name}
"action_start"      # 시스템 시작
"action_stop"       # 시스템 중지
"action_pause"      # 시스템 일시정지
"action_restart"    # 시스템 재시작
```

### 설정 네비게이션
```python
# 패턴: settings_{category}
"settings_trading"     # 거래 설정
"settings_portfolio"   # 포트폴리오 설정
"settings_notifications" # 알림 설정
"settings_security"    # 보안 설정
"settings_advanced"    # 고급 설정
```

### 확인 다이얼로그
```python
# 패턴: confirm_{action}
"confirm_start_system"   # 시스템 시작 확인
"confirm_stop_system"    # 시스템 중지 확인
"confirm_emergency_stop" # 긴급 중지 확인
```

### 빠른 액션
```python
# 패턴: quick_{action}
"quick_status"      # 빠른 상태 확인
"quick_portfolio"   # 빠른 포트폴리오 확인
"quick_report"      # 빠른 보고서 생성
```

## 📊 데이터 구조

### 시스템 상태 구조
```python
SystemStatus = {
    "healthy": bool,              # 시스템 정상 여부
    "trading_active": bool,       # 거래 활성 상태
    "active_strategies": int,     # 활성 전략 수
    "total_value": float,         # 총 포트폴리오 가치
    "status_text": str,           # 상태 텍스트
    "risk_level": str,            # 위험 수준 (LOW/MEDIUM/HIGH)
    "avg_response_time": float,   # 평균 응답 시간 (ms)
    "unrealized_profit": float    # 미실현 수익 (%)
}
```

### 거래 설정 구조
```python
TradingConfig = {
    "active_strategies": int,     # 활성 전략 수
    "risk_level": str,           # 리스크 레벨
    "daily_limit": float,        # 일일 거래 한도
    "auto_trading": bool,        # 자동거래 활성화
    "trading_hours": Dict[str, str] # 거래 시간 설정
}
```

### 포트폴리오 설정 구조
```python
PortfolioConfig = {
    "total_value": float,           # 총 자산 가치
    "rebalancing_frequency": str,   # 리밸런싱 주기
    "profit_threshold": float,      # 수익실현 임계값 (%)
    "stop_loss_threshold": float,   # 손절매 임계값 (%)
    "diversification_rules": Dict   # 분산투자 규칙
}
```

### 사용자 세션 구조
```python
UserSession = {
    "current_level": MenuLevel,     # 현재 메뉴 레벨
    "last_update": datetime,        # 마지막 업데이트 시간
    "data": Dict[str, Any],        # 세션 데이터
    "preferences": Dict[str, Any]   # 사용자 선호도
}
```

## 🎨 UI 컴포넌트

### 인라인 키보드 생성
```python
def create_inline_keyboard(buttons: List[List[Dict]]) -> InlineKeyboardMarkup:
    """인라인 키보드를 생성합니다.
    
    Args:
        buttons: 버튼 정의 리스트
        
    Example:
        buttons = [
            [{"text": "🚀 시작", "callback_data": "action_start"}],
            [{"text": "🛑 중지", "callback_data": "action_stop"}]
        ]
        keyboard = create_inline_keyboard(buttons)
    """
```

### 상태 기반 버튼 생성
```python
def create_status_based_buttons(system_status: Dict) -> List[List[InlineKeyboardButton]]:
    """시스템 상태에 따른 동적 버튼을 생성합니다.
    
    Args:
        system_status: 현재 시스템 상태
        
    Returns:
        List[List[InlineKeyboardButton]]: 생성된 버튼 리스트
    """
```

## 🔐 보안 및 권한

### 사용자 레벨 시스템
```python
USER_LEVELS = {
    "basic": {
        "commands": "CORE_COMMANDS",
        "menus": ["main", "settings"],
        "actions": ["view", "basic_control"]
    },
    "advanced": {
        "commands": "CORE_COMMANDS + ADVANCED_COMMANDS", 
        "menus": ["all"],
        "actions": ["view", "control", "configure"]
    },
    "expert": {
        "commands": "ALL_COMMANDS",
        "menus": ["all"],
        "actions": ["all"]
    }
}
```

### 권한 검사
```python
async def check_permissions(
    user_id: int, 
    action: str, 
    level_required: str = "basic"
) -> bool:
    """사용자 권한을 검사합니다.
    
    Args:
        user_id: 사용자 ID
        action: 실행하려는 액션
        level_required: 필요한 권한 레벨
        
    Returns:
        bool: 권한 있음 여부
    """
```

## 🔄 이벤트 플로우

### 메뉴 네비게이션 플로우
```
사용자 버튼 클릭
    ↓
CallbackQueryHandler.handle_callback_query()
    ↓
패턴 매칭 (menu_*, action_*, settings_*)
    ↓
해당 핸들러 메서드 호출
    ↓
새로운 메뉴/다이얼로그 표시
```

### 액션 실행 플로우
```
사용자 액션 버튼 클릭
    ↓
_handle_action_request()
    ↓
중요 액션인가? → 예: show_confirmation_dialog()
    ↓              ↓
아니오: 즉시 실행   사용자 확인
    ↓              ↓
결과 표시          confirm_ 콜백 → 실행
```

## 🧪 테스트 API

### 단위 테스트 예시
```python
import pytest
from telegram_interface.command_registry import CommandRegistry
from telegram_interface.menu_system import MenuSystem

class TestCommandRegistry:
    """CommandRegistry 테스트."""
    
    @pytest.fixture
    def registry(self):
        return CommandRegistry()
    
    def test_command_validation(self, registry):
        """명령어 형식 검증 테스트."""
        assert registry.validate_command_format("/start")
        assert not registry.validate_command_format("start")
        assert not registry.validate_command_format("/a")
    
    def test_command_help(self, registry):
        """명령어 도움말 테스트."""
        help_text = registry.get_command_help("/start")
        assert "시스템 시작" in help_text
```

### 통합 테스트 예시
```python
class TestMenuSystem:
    """MenuSystem 통합 테스트."""
    
    @pytest.fixture
    async def menu_system(self):
        return MenuSystem()
    
    async def test_main_menu_display(self, menu_system, mock_update):
        """메인 메뉴 표시 테스트."""
        await menu_system.show_main_menu(mock_update, mock_context)
        # 검증 로직
    
    async def test_callback_handling(self, menu_system, mock_callback_update):
        """콜백 처리 테스트."""
        mock_callback_update.callback_query.data = "menu_settings"
        await menu_system.handle_callback_query(mock_callback_update, mock_context)
        # 검증 로직
```

## 📈 성능 고려사항

### 캐싱 전략
```python
class MenuCache:
    """메뉴 시스템 캐싱."""
    
    def __init__(self, ttl: int = 60):
        self.cache: Dict[str, Any] = {}
        self.ttl = ttl
    
    async def get_system_status(self) -> Dict:
        """캐시된 시스템 상태 반환."""
        if "system_status" not in self.cache:
            self.cache["system_status"] = await self._fetch_system_status()
        return self.cache["system_status"]
```

### 비동기 처리
```python
async def handle_multiple_callbacks(callbacks: List[str]) -> List[Any]:
    """여러 콜백을 병렬 처리합니다."""
    tasks = [process_callback(cb) for cb in callbacks]
    return await asyncio.gather(*tasks)
```

## 🔧 확장 가이드

### 새 메뉴 추가
```python
# 1. MenuLevel에 새 레벨 추가
class MenuLevel(Enum):
    CUSTOM = "custom"

# 2. MenuSystem에 메서드 추가
async def show_custom_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """커스텀 메뉴 표시."""
    # 구현

# 3. 콜백 핸들러에 라우팅 추가
if callback_data.startswith('custom_'):
    await self._handle_custom_navigation(update, context, callback_data)
```

### 새 명령어 추가
```python
# 1. CommandRegistry에 명령어 추가
CUSTOM_COMMANDS = [
    BotCommand("/mycmd", "📱 커스텀 명령어")
]

# 2. TelegramBot에 핸들러 추가
self.application.add_handler(
    TgCommandHandler("mycmd", self._handle_mycmd)
)
```

## 📝 API 변경 로그

### v1.0.0 (2025-06-25)
- ✅ 초기 BotFather 스타일 API 구현
- ✅ CommandRegistry 클래스 추가
- ✅ MenuSystem 클래스 추가
- ✅ 인라인 키보드 지원
- ✅ 동적 메뉴 시스템
- ✅ 확인 다이얼로그 시스템

### 향후 계획
- [ ] v1.1.0: 사용자별 맞춤 메뉴
- [ ] v1.2.0: 음성 명령 지원  
- [ ] v2.0.0: AI 통합 자연어 처리

---

## 📞 지원 및 문의

### API 지원
- **개발자 문서**: [docs/api/](../api/)
- **예제 코드**: [examples/](../examples/)
- **테스트 케이스**: [tests/](../tests/)

### 기여 가이드
- **코딩 표준**: [CODING_STANDARDS.md](../CODING_STANDARDS.md)
- **PR 가이드라인**: [CONTRIBUTING.md](../CONTRIBUTING.md)
- **이슈 리포팅**: [GitHub Issues](https://github.com/your-repo/issues)

---

*이 API 문서는 Letrade V1의 BotFather 스타일 UI/UX 시스템에 대한 완전한 개발자 참조 가이드입니다.*