# 사용자 인터페이스 및 부록 (User Interfaces and Appendices)

## 📋 문서 개요

**문서 목적**: 자동 암호화폐 거래 시스템과 사용자의 상호작용을 담당하는 인터페이스의 완전한 기능 명세서 및 포괄적인 참조 자료

**핵심 가치**: 강력한 백엔드 시스템은 효과적인 사용자 인터페이스를 통해 그 가치가 극대화

**주요 구성 요소**:
- 💻 **커맨드 라인 인터페이스(CLI)**: 시스템 설정, 구성, 유지보수용 강력한 도구
- 📱 **텔레그램 봇 인터페이스**: 실시간 알림과 필수적인 원격 제어 기능
- 🔐 **고급 보안 기능**: 2FA, 세션 관리, API 사용량 모니터링
- 📚 **부록**: 핵심 용어, 코드 구조, 구성 예시

**대상 독자**: 개발자, 운영자, 시스템 관리자

---

## 💻 1. 커맨드 라인 인터페이스 (CLI)

### 1.1 CLI 개요

**목적**: 시스템의 설정, 구성, 유지보수를 위한 **기본적이고 강력한 도구**

**기술 스택**: Python의 `click` 또는 `argparse` 라이브러리 사용

**사용 환경**: 안전한 개발자 또는 운영자 환경에서 사용

### 1.2 CLI 명령어 전체 참조

#### 🔧 **구성 관리 (bot-cli config)**

| 명령어 | 설명 | 예시 |
|--------|------|------|
| `config set <key> <value>` | 시스템의 구성 값을 설정합니다. 민감 정보(API 키)는 GCP Secret Manager에 직접 저장, 비민감 정보는 구성 파일에 저장 | `bot-cli config set exchange.binance.key <API_KEY>` |
| `config get <key>` | 구성 값을 조회합니다 (민감 정보는 마스킹 처리) | `bot-cli config get exchange.binance.key` |
| `config list` | 모든 구성 항목을 나열합니다 | `bot-cli config list` |
| `config validate` | 모든 구성의 유효성을 검사합니다 | `bot-cli config validate` |

#### ⚙️ **전략 관리 (bot-cli strategy)**

| 명령어 | 설명 | 예시 |
|--------|------|------|
| `strategy add` | 데이터베이스의 strategies 테이블에 새로운 거래 전략을 추가합니다. 이름, 소스 경로, 심볼, 파라미터 등을 인자로 받습니다 | `bot-cli strategy add --name="MA_Crossover" --source="strategies/ma_cross.py" --symbol="BTC/USDT" --params='{"fast": 10, "slow": 50}' --portfolio_id=4 --sizing_config='{"model": "FixedAmount", "amount": 0.01}'` |
| `strategy list` | 데이터베이스에 구성된 모든 전략과 그 상태(is_active)를 표 형식으로 출력합니다 | `bot-cli strategy list` |
| `strategy start <id>` | ID로 특정 전략을 활성화합니다 (is_active를 true로 설정). CoreEngine이 이를 감지하고 워커를 시작합니다 | `bot-cli strategy start 17` |
| `strategy stop <id>` | ID로 특정 전략을 비활성화합니다. 실행 중인 워커에 정상 종료 신호를 보냅니다 | `bot-cli strategy stop 17` |
| `strategy remove <id>` | 데이터베이스에서 특정 전략 구성을 삭제합니다 | `bot-cli strategy remove 17` |
| `strategy backtest <id>` | 특정 전략의 백테스팅을 실행합니다 | `bot-cli strategy backtest 17 --period=30d` |
| `strategy optimize <id>` | 전략 파라미터 최적화를 실행합니다 | `bot-cli strategy optimize 17 --method=bayesian` |

#### 💼 **포트폴리오 관리 (bot-cli portfolio)**

| 명령어 | 설명 | 예시 |
|--------|------|------|
| `portfolio create` | 데이터베이스에 새로운 자금 포트폴리오를 생성합니다 | `bot-cli portfolio create --name="DCA_Fund" --capital=5000 --parent="Global"` |
| `portfolio set-rule` | 특정 포트폴리오에 리스크 관리 규칙을 설정하거나 업데이트합니다 | `bot-cli portfolio set-rule --portfolio_id=3 --rule="MAX_DRAWDOWN_PERCENT" --value='{"value": 10}'` |
| `portfolio assign-strategy` | 특정 전략이 특정 포트폴리오의 자금을 사용하도록 매핑합니다 | `bot-cli portfolio assign-strategy --strategy_id=12 --portfolio_id=3` |
| `portfolio rebalance <id>` | 포트폴리오 리밸런싱을 실행합니다 | `bot-cli portfolio rebalance 3 --method=equal_weight` |

#### 🚀 **운영 및 배포 (bot-cli ops)**

| 명령어 | 설명 | 예시 |
|--------|------|------|
| `deploy` | 최신 코드를 GCP에 배포하기 위해 gcloud builds submit 명령을 트리거하는 래퍼 스크립트입니다 | `bot-cli deploy` |
| `logs <service_name>` | GCP 인스턴스에서 실행 중인 특정 서비스의 로그를 실시간으로 스트리밍합니다 | `bot-cli logs core-engine` |
| `status` | 모든 실행 중인 서비스의 고수준 상태(UP/DOWN)와 핵심 메트릭을 조회하여 표시합니다 | `bot-cli status` |
| `health-check` | 종합적인 시스템 헬스 체크를 실행합니다 | `bot-cli health-check --detailed` |
| `backup create` | 수동 백업을 생성합니다 | `bot-cli backup create --type=full` |
| `backup restore <backup_id>` | 특정 백업에서 시스템을 복구합니다 | `bot-cli backup restore backup_20240115_030000` |

#### 📱 **텔레그램 사용자 관리 (bot-cli telegram)**

| 명령어 | 설명 | 예시 |
|--------|------|------|
| `telegram add-user <chat_id>` | 텔레그램 봇의 사용자 화이트리스트에 새로운 chat_id를 추가합니다 | `bot-cli telegram add-user 123456789` |
| `telegram remove-user <chat_id>` | 화이트리스트에서 사용자를 제거합니다 | `bot-cli telegram remove-user 123456789` |
| `telegram list-users` | 모든 승인된 사용자 목록을 표시합니다 | `bot-cli telegram list-users` |
| `telegram send-test` | 테스트 메시지를 발송합니다 | `bot-cli telegram send-test "System test message"` |

---

## 📱 2. 텔레그램 봇 인터페이스

### 2.1 설계 목적

**핵심 목표**: 실시간 알림과 필수적인 원격 제어 기능 제공

**보안 고려사항**: 본질적으로 덜 안전한 모바일 기기에서 접근될 수 있으므로 **기능이 제한적**이고 **모니터링과 시간 민감적인 조치에 더 초점**

**기술 구현**: `python-telegram-bot` 라이브러리를 사용하는 전용 파이썬 서비스

### 2.2 차별화된 보안 모델

#### 🔐 **역할 분리**

| 인터페이스 | 역할 | 적합한 작업 | 금지된 작업 |
|------------|------|-------------|-------------|
| **CLI** | 관리자/운영 도구 | API 키 설정, 코드 배포, 상세 구성 | - |
| **텔레그램 봇** | 모니터링/경량 제어 도구 | 상태 조회, 알림 수신, 기본 제어 | API 키 설정 등 매우 민감한 작업 |

#### 🛡️ **보안 메커니즘**

**사용자 화이트리스트**:
- **핵심 보안**: 승인된 chat_id 목록 유지
- **동작**: Telegram Interface 서비스가 화이트리스트에 없는 사용자의 모든 메시지 무시

**토큰 보안**:
- ❌ **금지**: 텔레그램 봇 토큰의 코드 하드코딩
- ✅ **필수**: 다른 민감 정보와 마찬가지로 GCP Secret Manager에 안전 저장

### 2.3 고급 보안 강화 (신규 추가)

#### 🔐 **2단계 인증 (2FA) 구현**

```python
class TelegramTwoFactorAuth:
    def __init__(self):
        self.totp_generator = TOTPGenerator()
        self.session_manager = SessionManager()
        self.auth_attempts = {}
        
    async def initiate_2fa_setup(self, chat_id: int, username: str):
        """
        2FA 설정 시작
        """
        # TOTP 시크릿 생성
        secret = self.totp_generator.generate_secret()
        
        # QR 코드 생성
        qr_code_url = self.generate_qr_code(username, secret)
        
        # 임시 저장 (10분 후 만료)
        await self.store_pending_2fa(chat_id, secret, expires_in=600)
        
        return {
            'secret': secret,
            'qr_code_url': qr_code_url,
            'backup_codes': self.generate_backup_codes(chat_id)
        }
    
    async def verify_2fa_setup(self, chat_id: int, totp_code: str) -> bool:
        """
        2FA 설정 완료 검증
        """
        pending_setup = await self.get_pending_2fa(chat_id)
        if not pending_setup:
            return False
        
        # TOTP 코드 검증
        if self.totp_generator.verify(pending_setup['secret'], totp_code):
            # 2FA 활성화
            await self.activate_2fa(chat_id, pending_setup['secret'])
            await self.delete_pending_2fa(chat_id)
            return True
        
        return False
    
    async def require_2fa_for_command(self, chat_id: int, command: str) -> bool:
        """
        민감한 명령어에 대한 2FA 요구
        """
        sensitive_commands = ['/stop_strategy', '/emergency_halt', '/close_position']
        
        if command.split()[0] in sensitive_commands:
            return await self.verify_current_session(chat_id)
        
        return True  # 비민감한 명령어는 2FA 불필요
```

#### 🕐 **세션 관리 강화**

```python
class TelegramSessionManager:
    def __init__(self):
        self.redis_client = redis.Redis()
        self.session_timeout = 3600  # 1시간
        self.max_sessions_per_user = 3
        
    async def create_session(self, chat_id: int, auth_method: str) -> dict:
        """
        새로운 세션 생성
        """
        session_id = secrets.token_urlsafe(32)
        session_data = {
            'chat_id': chat_id,
            'created_at': datetime.utcnow().isoformat(),
            'auth_method': auth_method,
            'last_activity': datetime.utcnow().isoformat(),
            'commands_executed': 0,
            'risk_score': 0
        }
        
        # 기존 세션 제한 확인
        existing_sessions = await self.get_user_sessions(chat_id)
        if len(existing_sessions) >= self.max_sessions_per_user:
            # 가장 오래된 세션 제거
            await self.revoke_oldest_session(chat_id)
        
        # 새 세션 저장
        await self.redis_client.setex(
            f"telegram_session:{session_id}",
            self.session_timeout,
            json.dumps(session_data)
        )
        
        return {'session_id': session_id, 'expires_in': self.session_timeout}
    
    async def validate_session(self, chat_id: int, session_id: str) -> bool:
        """
        세션 유효성 검증 및 활동 시간 업데이트
        """
        session_key = f"telegram_session:{session_id}"
        session_data = await self.redis_client.get(session_key)
        
        if not session_data:
            return False
        
        session = json.loads(session_data)
        
        # 세션 소유자 확인
        if session['chat_id'] != chat_id:
            await self.log_security_incident(
                'session_hijack_attempt',
                {'expected_chat_id': session['chat_id'], 'actual_chat_id': chat_id}
            )
            return False
        
        # 활동 시간 업데이트
        session['last_activity'] = datetime.utcnow().isoformat()
        session['commands_executed'] += 1
        
        await self.redis_client.setex(session_key, self.session_timeout, json.dumps(session))
        
        return True
```

#### 📊 **API 사용량 모니터링**

```python
class TelegramUsageMonitor:
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.usage_tracker = UsageTracker()
        self.anomaly_detector = AnomalyDetector()
        
    async def monitor_command_usage(self, chat_id: int, command: str, timestamp: datetime):
        """
        명령어 사용량 모니터링 및 이상 패턴 감지
        """
        # 사용량 기록
        await self.usage_tracker.record_command(chat_id, command, timestamp)
        
        # 속도 제한 확인
        if not await self.rate_limiter.is_allowed(chat_id, command):
            await self.send_rate_limit_warning(chat_id)
            return False
        
        # 이상 패턴 감지
        usage_pattern = await self.usage_tracker.get_recent_pattern(chat_id, hours=24)
        anomaly_score = await self.anomaly_detector.analyze_pattern(usage_pattern)
        
        if anomaly_score > 0.8:  # 높은 이상 점수
            await self.flag_suspicious_activity(chat_id, usage_pattern, anomaly_score)
        
        return True
    
    async def flag_suspicious_activity(self, chat_id: int, pattern: dict, score: float):
        """
        의심스러운 활동 플래그 및 대응
        """
        incident = {
            'chat_id': chat_id,
            'anomaly_score': score,
            'pattern': pattern,
            'timestamp': datetime.utcnow().isoformat(),
            'severity': 'HIGH' if score > 0.9 else 'MEDIUM'
        }
        
        # 보안 로그 기록
        await self.log_security_incident('suspicious_telegram_activity', incident)
        
        # 높은 위험도인 경우 세션 일시 중단
        if score > 0.9:
            await self.temporary_suspend_user(chat_id, duration=1800)  # 30분
            
        # 운영팀 알림
        await self.send_security_alert(incident)
```

### 2.4 명령어 참조

#### 📊 **기본 명령어**

| 명령어 | 설명 | 권한 레벨 |
|--------|------|----------|
| `/start` | 봇을 시작하고 사용자가 승인된 사용자인지 확인합니다 | 모든 사용자 |
| `/status` | 현재 미결제 포지션, 전체 손익, 각 실행 중인 전략의 상태 요약을 보여줍니다 | 읽기 권한 |
| `/profit` | 일간, 주간, 월간 손익 보고서를 표시합니다 | 읽기 권한 |
| `/help` | 사용 가능한 모든 명령어와 설명을 표시합니다 | 모든 사용자 |

#### 💼 **포트폴리오 및 전략 관리**

| 명령어 | 설명 | 권한 레벨 |
|--------|------|----------|
| `/portfolio_status` | 모든 포트폴리오의 이름, 총 자본, 가용 자본, 현재 손익(PnL)을 요약하여 보여줍니다 | 읽기 권한 |
| `/dca_status` | 모든 활성 DCA 전략의 상태, 총 투자 금액, 다음 매수 예정일 등을 표시합니다 | 읽기 권한 |
| `/grid_status <strategy_id>` | 특정 그리드 전략의 상세 상태(현재 PnL, 체결된 그리드 주문 수 등)를 보여줍니다 | 읽기 권한 |

#### ⚙️ **제어 명령어**

| 명령어 | 설명 | 권한 레벨 |
|--------|------|----------|
| `/start_strategy <strategy_id>` | 구성되었지만 비활성 상태인 전략을 시작합니다 | 제어 권한 + 2FA |
| `/stop_strategy <strategy_id>` | 실행 중인 전략을 정상적으로 중지하는 명령을 발행합니다 | 제어 권한 + 2FA |
| `/close_position <position_id>` | 특정 미결제 포지션을 수동으로 종료하는 명령을 발행합니다 | 제어 권한 + 2FA |
| `/emergency_halt` | 모든 거래를 즉시 중단합니다 | 관리자 권한 + 2FA |

#### 🔍 **모니터링 명령어 (신규 추가)**

| 명령어 | 설명 | 권한 레벨 |
|--------|------|----------|
| `/alerts` | 최근 알림 목록을 표시합니다 | 읽기 권한 |
| `/performance <period>` | 지정 기간의 성과 요약을 보여줍니다 | 읽기 권한 |
| `/risk_metrics` | 현재 리스크 지표 (VaR, 최대 손실률 등)를 표시합니다 | 읽기 권한 |
| `/system_health` | 시스템 구성 요소의 상태를 확인합니다 | 읽기 권한 |

### 2.5 자동 알림 기능

#### 🔔 **알림 메커니즘**
**동작 방식**: Telegram Interface 서비스가 RabbitMQ의 이벤트 큐(예: `alerts.*`, `events.trade_executed`)를 구독

#### 📢 **알림 대상 이벤트**

| 이벤트 유형 | 우선순위 | 설명 |
|-------------|----------|------|
| **새로운 거래 체결** | 정보 | 거래 실행 완료 시 즉시 알림 |
| **손절매 또는 이익 실현 주문 발동** | 중간 | 자동 주문 실행 알림 |
| **청산 위험 경고** | 높음 | 즉각적인 조치 필요 |
| **시스템 오류 발생** | 높음 | API 연결 실패, 데이터베이스 오류 등 |
| **의심스러운 활동 감지** | 중간 | 보안 관련 이상 활동 |
| **성과 목표 달성** | 정보 | 수익률 목표 달성 알림 |

#### 🎛️ **지능형 알림 필터링 (신규 추가)**

```python
class IntelligentNotificationFilter:
    def __init__(self):
        self.user_preferences = {}
        self.notification_history = {}
        self.spam_detector = SpamDetector()
        
    async def should_send_notification(self, chat_id: int, notification: dict) -> bool:
        """
        알림 발송 여부 지능형 결정
        """
        # 1. 사용자 선호도 확인
        preferences = await self.get_user_preferences(chat_id)
        if not self.matches_preferences(notification, preferences):
            return False
        
        # 2. 중복 알림 방지
        if await self.is_duplicate_notification(chat_id, notification):
            return False
        
        # 3. 스팸 감지
        if await self.spam_detector.is_spam(chat_id, notification):
            return False
        
        # 4. 시간대 고려 (Do Not Disturb)
        if await self.is_quiet_hours(chat_id):
            # 긴급 알림만 허용
            return notification.get('priority') == 'CRITICAL'
        
        return True
    
    async def personalize_notification(self, chat_id: int, notification: dict) -> dict:
        """
        사용자별 알림 개인화
        """
        user_profile = await self.get_user_profile(chat_id)
        
        # 언어 설정에 따른 메시지 변환
        if user_profile.get('language') != 'ko':
            notification['message'] = await self.translate_message(
                notification['message'], 
                user_profile['language']
            )
        
        # 알림 형식 개인화
        if user_profile.get('notification_style') == 'detailed':
            notification = await self.add_detailed_context(notification)
        elif user_profile.get('notification_style') == 'minimal':
            notification = await self.simplify_notification(notification)
        
        return notification
```

---

## 📚 3. 부록 (Appendices)

### 📖 **부록 A: 주요 용어집**

#### 🧠 **Core Engine**
**정의**: 중앙 오케스트레이터  
**역할**: 전략 설정을 관리하고, 워커 프로세스를 생성 및 감독하며, 시스템 전반의 상태와 성능 데이터를 집계

#### ⚙️ **Strategy Worker**
**정의**: 격리된 단일 목적 프로세스  
**역할**: 각 워커는 단일 거래 전략의 로직을 실행하며, 필요한 시장 데이터를 구독하고 거래 '제안' 또는 명령을 발행

#### 🔌 **Exchange Connector**
**정의**: 모든 외부 거래소 API와의 통신을 전담하는 게이트웨이  
**역할**: API 키 관리, 속도 제한, 오류 처리, 비표준 기능(스테이킹 등)의 복잡성을 중앙에서 추상화하는 "오염 방지 계층(Anti-Corruption Layer)"

#### 💰 **Capital Manager**
**정의**: 자본 할당 및 포트폴리오 리스크 관리의 중앙 허브  
**역할**: 거래 '제안'을 검토, 승인하고 최종 주문 크기를 결정하여 실행을 지시

#### 🔄 **상태 조정 프로토콜 (State Reconciliation Protocol)**
**정의**: 시스템 시작 시 데이터베이스와 거래소의 실제 상태를 비교하고 동기화하는 엄격한 프로토콜  
**중요성**: 상태 불일치로 인한 치명적인 거래 오류를 방지하여 시스템의 장기적인 신뢰성을 보장

#### 📊 **시장가 (Mark Price)**
**정의**: 여러 현물 거래소 가격과 펀딩 비율을 조합하여 계산된 "공정한" 가치  
**역할**: 미실현 손익과 강제 청산 가격 계산의 기준이 되어 불필요한 청산을 방지

#### 🛡️ **reduceOnly 주문**
**정의**: 새로운 포지션을 열거나 기존 포지션을 확대하는 것을 방지하고, 오직 기존 포지션의 크기를 줄이는 역할만 하도록 보장하는 주문 파라미터  
**중요성**: 손절매 및 이익 실현 주문에 필수적인 안전장치

#### 🔐 **2FA (Two-Factor Authentication)**
**정의**: 사용자 신원 확인을 위해 두 가지 다른 인증 요소를 요구하는 보안 방법  
**구현**: TOTP (Time-based One-Time Password) 방식 사용

#### 📱 **TOTP (Time-based One-Time Password)**
**정의**: 시간을 기반으로 생성되는 일회용 패스워드  
**특징**: 30초마다 새로운 코드가 생성되어 보안성 향상

### 💻 **부록 B: 핵심 코드 및 구성 예시**

#### 🏗️ **BaseStrategy 추상 클래스**

```python
# app/strategies/base_strategy.py
from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):
    """
    모든 거래 전략이 따라야 하는 계약을 정의하는 추상 기본 클래스입니다.
    """
    def __init__(self, config: dict):
        self.config = config
        super().__init__()

    @abstractmethod
    def populate_indicators(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        pass

    @abstractmethod
    def on_data(self, data: dict, dataframe: pd.DataFrame) -> dict | None:
        pass

    @abstractmethod
    def get_required_subscriptions(self) -> list[str]:
        pass
```

#### 🔐 **보안 강화 텔레그램 봇 예시**

```python
# app/telegram_interface/secure_bot.py
from telegram.ext import Application, CommandHandler, filters
from telegram import Update
import asyncio

class SecureTradingBot:
    def __init__(self):
        self.auth_manager = TelegramTwoFactorAuth()
        self.session_manager = TelegramSessionManager()
        self.usage_monitor = TelegramUsageMonitor()
        self.command_processor = CommandProcessor()
        
    async def setup_bot(self):
        """
        보안 강화된 텔레그램 봇 설정
        """
        # 봇 토큰을 Secret Manager에서 안전하게 로드
        bot_token = await self.get_secret('telegram_bot_token')
        
        self.application = Application.builder().token(bot_token).build()
        
        # 인증이 필요한 명령어 핸들러
        self.application.add_handler(
            CommandHandler("start_strategy", self.handle_start_strategy, filters=self.auth_filter)
        )
        self.application.add_handler(
            CommandHandler("stop_strategy", self.handle_stop_strategy, filters=self.auth_filter)
        )
        
        # 읽기 전용 명령어 핸들러
        self.application.add_handler(
            CommandHandler("status", self.handle_status, filters=self.whitelist_filter)
        )
        
        return self.application
    
    async def auth_filter(self, update: Update, context) -> bool:
        """
        인증이 필요한 명령어에 대한 필터
        """
        chat_id = update.effective_chat.id
        
        # 1. 화이트리스트 확인
        if not await self.is_whitelisted(chat_id):
            return False
        
        # 2. 세션 확인
        if not await self.session_manager.has_valid_session(chat_id):
            await update.message.reply_text("세션이 만료되었습니다. /login 명령어로 다시 로그인하세요.")
            return False
        
        # 3. 2FA 확인 (민감한 명령어)
        if not await self.auth_manager.require_2fa_for_command(chat_id, update.message.text):
            await update.message.reply_text("이 명령어는 2단계 인증이 필요합니다. 인증 코드를 입력하세요.")
            return False
        
        # 4. 사용량 모니터링
        if not await self.usage_monitor.monitor_command_usage(
            chat_id, update.message.text.split()[0], datetime.now()
        ):
            return False
        
        return True
    
    async def handle_start_strategy(self, update: Update, context):
        """
        전략 시작 명령어 처리 (2FA 필요)
        """
        try:
            args = context.args
            if not args:
                await update.message.reply_text("사용법: /start_strategy <strategy_id>")
                return
            
            strategy_id = int(args[0])
            
            # 명령 실행
            result = await self.command_processor.start_strategy(strategy_id)
            
            if result['success']:
                await update.message.reply_text(f"전략 {strategy_id} 시작됨")
                
                # 감사 로그 기록
                await self.log_command_execution(
                    chat_id=update.effective_chat.id,
                    command='start_strategy',
                    args={'strategy_id': strategy_id},
                    result=result
                )
            else:
                await update.message.reply_text(f"전략 시작 실패: {result['error']}")
                
        except Exception as e:
            await update.message.reply_text(f"오류 발생: {str(e)}")
            await self.log_error(update.effective_chat.id, 'start_strategy', str(e))
```

#### 🐳 **다단계 Dockerfile 예시**

```dockerfile
# Dockerfile for a Python service
# --- Build Stage ---
FROM python:3.11 as builder
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip wheel --no-cache-dir --wheel-dir /usr/src/app/wheels -r requirements.txt

# --- Production Stage ---
FROM python:3.11-slim
WORKDIR /usr/src/app
COPY --from=builder /usr/src/app/wheels /wheels
RUN pip install --no-cache /wheels/*
COPY . .
CMD ["python", "-u", "main.py"]
```

#### 🚀 **cloudbuild.yaml 구성 예시**

```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', '${_LOCATION}-docker.pkg.dev/${PROJECT_ID}/${_REPO_NAME}/${_SERVICE_NAME}:$COMMIT_SHA', './app/${_SERVICE_NAME}']
    id: 'Build ${_SERVICE_NAME}'
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '${_LOCATION}-docker.pkg.dev/${PROJECT_ID}/${_REPO_NAME}/${_SERVICE_NAME}:$COMMIT_SHA']
    id: 'Push ${_SERVICE_NAME}'
  - name: 'gcr.io/google.com/cloudsdktool/google-cloud-cli'
    entrypoint: 'gcloud'
    args: ['compute', 'ssh', '${_INSTANCE_NAME}', '--zone=${_ZONE}', '--command="sudo /opt/scripts/deploy.sh ${_SERVICE_NAME}"']
    id: 'Deploy ${_SERVICE_NAME}'
images:
  - '${_LOCATION}-docker.pkg.dev/${PROJECT_ID}/${_REPO_NAME}/${_SERVICE_NAME}:$COMMIT_SHA'
substitutions:
  _LOCATION: 'us-central1'
  _REPO_NAME: 'trading-bot-repo'
  _SERVICE_NAME: 'core-engine'
  _INSTANCE_NAME: 'trading-bot-vm'
  _ZONE: 'us-central1-a'
```

#### ⚙️ **systemd 유닛 파일 예시**

```ini
[Unit]
Description=Trading Bot Core Engine
After=docker.service
Requires=docker.service

[Service]
TimeoutStartSec=0
Restart=always
RestartSec=10s
ExecStartPre=-/usr/bin/docker kill core-engine
ExecStartPre=-/usr/bin/docker rm core-engine
ExecStartPre=/usr/bin/docker pull us-central1-docker.pkg.dev/your-project/your-repo/core-engine:latest
ExecStart=/usr/bin/docker run --name core-engine --rm --network=host us-central1-docker.pkg.dev/your-project/your-repo/core-engine:latest
ExecStop=-/usr/bin/docker stop core-engine

[Install]
WantedBy=multi-user.target
```

### 🔐 **부록 C: 보안 설정 가이드**

#### 📱 **2FA 설정 단계별 가이드**

1. **초기 설정**:
   ```
   /setup_2fa
   → QR 코드 수신
   → Google Authenticator/Authy로 스캔
   → 생성된 6자리 코드 입력으로 확인
   ```

2. **백업 코드 저장**:
   ```
   /backup_codes
   → 10개의 일회용 백업 코드 수신
   → 안전한 장소에 저장 (휴대폰 분실 시 사용)
   ```

3. **2FA 상태 확인**:
   ```
   /2fa_status
   → 현재 2FA 설정 상태 확인
   → 마지막 사용 시간 확인
   ```

#### 🛡️ **권한 레벨 설정**

```yaml
# telegram_permissions.yml
user_roles:
  admin:
    permissions:
      - read_all
      - control_strategies
      - emergency_commands
      - user_management
    requires_2fa: true
    
  trader:
    permissions:
      - read_portfolio
      - control_assigned_strategies
    requires_2fa: true
    
  viewer:
    permissions:
      - read_status
      - read_performance
    requires_2fa: false

sensitive_commands:
  - /start_strategy
  - /stop_strategy
  - /emergency_halt
  - /close_position
```

---

## 🎯 시스템 통합 효과

### 사용자 경험 최적화
- ✅ **이중 인터페이스**: CLI로 강력한 관리 기능, 텔레그램으로 편리한 모니터링
- ✅ **역할 기반 접근**: 보안과 편의성의 균형 달성
- ✅ **실시간 알림**: 중요한 이벤트의 즉각적인 전달
- ✅ **지능형 필터링**: 개인화된 알림으로 정보 과부하 방지

### 보안 강화
- ✅ **차별화된 보안 모델**: 인터페이스별 적절한 보안 수준 적용
- ✅ **화이트리스트 기반**: 승인된 사용자만 접근 허용
- ✅ **민감 정보 분리**: Secret Manager 기반 안전한 토큰 관리
- ✅ **2단계 인증**: 민감한 작업에 대한 추가 보안 계층
- ✅ **세션 관리**: 시간 기반 세션 만료 및 활동 추적
- ✅ **이상 감지**: AI 기반 의심스러운 활동 패턴 감지

### 운영 효율성
- ✅ **포괄적인 CLI**: 모든 시스템 관리 작업을 명령어로 수행 가능
- ✅ **자동 알림**: 수동 모니터링 부담 감소
- ✅ **원격 제어**: 모바일 환경에서도 필수 제어 기능 제공
- ✅ **사용량 모니터링**: API 남용 방지 및 최적 사용 패턴 분석

### 개발자 지원
- ✅ **완전한 참조 자료**: 용어집, 코드 예시, 구성 파일 제공
- ✅ **표준화된 구조**: BaseStrategy 등 일관된 개발 패턴
- ✅ **실무 중심**: 실제 사용 가능한 완전한 예시 코드
- ✅ **보안 가이드**: 단계별 보안 설정 및 모범 사례

### 고급 보안 기능 효과
- **다단계 인증**: 중요 작업에 대한 강력한 보안 보장
- **지능형 모니터링**: 실시간 위협 감지 및 대응
- **개인화**: 사용자별 맞춤형 보안 및 알림 설정
- **감사 추적**: 모든 사용자 활동에 대한 완전한 기록

---

## 📝 문서 관리 정보

**연관 문서**: 
- `00_System_Overview_and_Architecture.md`
- `06_Deployment_and_Operations_(DevOps).md`
- 모든 시스템 구성 요소 문서

**핵심 기술**: Python click/argparse, python-telegram-bot, GCP Secret Manager, TOTP, Redis

**보안 요구사항**: 사용자 화이트리스트, 역할 기반 접근 제어, 2FA, 세션 관리, 토큰 안전 저장

**사용 가이드**: CLI 및 텔레그램 봇 명령어 완전 참조, 코드 예시 활용법, 보안 설정 가이드

**보안 수준**: 
- CLI: 최고 보안 (모든 기능 접근)
- 텔레그램: 중간 보안 (제한된 기능, 2FA 적용)
- 모니터링: 실시간 위협 감지 및 대응