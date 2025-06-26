# 보안 가이드

## 개요

Letrade_v1 자동 암호화폐 거래 시스템의 보안 모범 사례와 구현 가이드입니다.

## 1. API 키 관리

### 1.1 절대 하지 말아야 할 것
```python
# ❌ 하드코딩 금지
api_key = "your-api-key-here"  # 절대 금지!

# ❌ 코드에 직접 포함 금지
config = {
    "api_key": "actual-key",  # 절대 금지!
    "secret": "actual-secret"  # 절대 금지!
}
```

### 1.2 올바른 방법

#### 환경 변수 사용
```python
# ✅ 환경 변수에서 읽기
import os
api_key = os.environ.get("BINANCE_API_KEY")
api_secret = os.environ.get("BINANCE_API_SECRET")
```

#### GCP Secret Manager 사용
```python
# ✅ Secret Manager 통합
from src.common.secret_manager import SecretManager

secret_manager = SecretManager()
api_key = await secret_manager.get_secret("binance-api-key")
```

### 1.3 API 키 권한 설정
- **읽기 전용**: 시장 데이터 조회
- **거래 권한**: 주문 생성/취소
- **출금 권한**: 절대 활성화 금지!

## 2. 네트워크 보안

### 2.1 TLS/SSL 통신
```python
# ✅ HTTPS 사용 강제
exchange = ccxt.binance({
    'apiKey': api_key,
    'secret': api_secret,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',
        'adjustForTimeDifference': True
    },
    'urls': {
        'api': 'https://api.binance.com'  # HTTPS 필수
    }
})
```

### 2.2 IP 화이트리스트
```yaml
# GCP 방화벽 규칙
gcloud compute firewall-rules create allow-trading-api \
  --allow tcp:443 \
  --source-ranges=35.235.240.0/20 \
  --target-tags=trading-server
```

### 2.3 VPC 격리
```yaml
# 프라이빗 서브넷 사용
apiVersion: v1
kind: Service
metadata:
  name: letrade-internal
spec:
  type: ClusterIP  # 내부 통신만 허용
```

## 3. 인증 및 권한 관리

### 3.1 JWT 구현
```python
# JWT 토큰 생성
from datetime import datetime, timedelta
import jwt

def create_access_token(user_id: str) -> str:
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=1),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')
```

### 3.2 역할 기반 접근 제어 (RBAC)
```python
# 권한 검증 데코레이터
def require_permission(permission: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not current_user.has_permission(permission):
                raise PermissionError("Insufficient permissions")
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# 사용 예
@require_permission("trade:execute")
async def execute_trade(trade_request):
    pass
```

## 4. 데이터 보안

### 4.1 민감한 데이터 암호화
```python
from cryptography.fernet import Fernet

class DataEncryption:
    def __init__(self, key: bytes):
        self.cipher = Fernet(key)
    
    def encrypt(self, data: str) -> bytes:
        return self.cipher.encrypt(data.encode())
    
    def decrypt(self, encrypted_data: bytes) -> str:
        return self.cipher.decrypt(encrypted_data).decode()
```

### 4.2 데이터베이스 보안
```sql
-- 컬럼 레벨 암호화
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- API 키 저장 시 암호화
INSERT INTO api_credentials (user_id, encrypted_key) 
VALUES (1, pgp_sym_encrypt('api-key', 'encryption-password'));
```

### 4.3 로그 보안
```python
# 민감한 정보 마스킹
def mask_sensitive_data(log_entry: dict) -> dict:
    sensitive_fields = ['api_key', 'password', 'secret']
    for field in sensitive_fields:
        if field in log_entry:
            log_entry[field] = '***REDACTED***'
    return log_entry
```

## 5. 거래 보안

### 5.1 거래 검증
```python
class TradeValidator:
    def validate_trade_signature(self, trade_request):
        # 서명 검증
        signature = trade_request.get('signature')
        data = self._get_signed_data(trade_request)
        
        if not self._verify_signature(data, signature):
            raise SecurityError("Invalid trade signature")
    
    def validate_trade_limits(self, trade_request):
        # 일일 거래 한도 확인
        daily_volume = self._get_daily_volume(trade_request.user_id)
        if daily_volume + trade_request.amount > MAX_DAILY_LIMIT:
            raise SecurityError("Daily trading limit exceeded")
```

### 5.2 이중 실행 방지
```python
# Idempotency 키 사용
async def execute_trade_once(trade_id: str):
    # Redis를 사용한 분산 락
    lock_key = f"trade_lock:{trade_id}"
    
    if await redis.set(lock_key, "1", nx=True, ex=300):
        try:
            # 거래 실행
            return await execute_trade(trade_id)
        finally:
            await redis.delete(lock_key)
    else:
        raise DuplicateTradeError("Trade already in progress")
```

## 6. 시스템 보안

### 6.1 컨테이너 보안
```dockerfile
# 비루트 사용자 실행
FROM python:3.11-slim

# 보안 업데이트
RUN apt-get update && apt-get upgrade -y

# 비루트 사용자 생성
RUN useradd -m -u 1000 trader
USER trader

# 읽기 전용 파일시스템
VOLUME ["/app/data"]
```

### 6.2 시크릿 스캐닝
```yaml
# pre-commit 설정
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

### 6.3 의존성 관리
```bash
# 보안 취약점 검사
pip-audit

# 의존성 업데이트
pip list --outdated
pip install --upgrade package_name
```

## 7. 모니터링 및 감사

### 7.1 보안 이벤트 로깅
```python
class SecurityAudit:
    def log_security_event(self, event_type: str, details: dict):
        audit_log = {
            'timestamp': datetime.utcnow(),
            'event_type': event_type,
            'user_id': current_user.id,
            'ip_address': request.remote_addr,
            'details': details
        }
        
        # 감사 로그 저장
        await audit_repository.save(audit_log)
        
        # 중요 이벤트 알림
        if event_type in CRITICAL_EVENTS:
            await alert_service.send_alert(audit_log)
```

### 7.2 이상 탐지
```python
class AnomalyDetector:
    def detect_unusual_activity(self, user_id: str):
        # 비정상적인 거래 패턴
        recent_trades = await get_recent_trades(user_id)
        
        if self._is_unusual_volume(recent_trades):
            await security_alert("Unusual trading volume detected")
        
        if self._is_unusual_frequency(recent_trades):
            await security_alert("Unusual trading frequency detected")
```

## 8. 인시던트 대응

### 8.1 긴급 정지 절차
```python
async def emergency_shutdown():
    """보안 인시던트 발생 시 긴급 정지"""
    # 1. 모든 거래 중지
    await trading_engine.halt_all_trades()
    
    # 2. API 키 무효화
    await secret_manager.revoke_all_keys()
    
    # 3. 시스템 격리
    await network_manager.isolate_system()
    
    # 4. 알림 발송
    await alert_service.send_critical_alert("Emergency shutdown activated")
```

### 8.2 복구 절차
1. 인시던트 원인 파악
2. 보안 패치 적용
3. 새 API 키 생성
4. 시스템 재검증
5. 단계적 서비스 재개

## 9. 보안 체크리스트

### 개발 단계
- [ ] 코드에 하드코딩된 시크릿 없음
- [ ] 민감한 데이터 암호화
- [ ] 입력 검증 구현
- [ ] SQL 인젝션 방지
- [ ] XSS 방지

### 배포 단계
- [ ] HTTPS 적용
- [ ] 방화벽 규칙 설정
- [ ] 최소 권한 원칙 적용
- [ ] 보안 헤더 설정
- [ ] 취약점 스캔 실행

### 운영 단계
- [ ] 정기적 보안 감사
- [ ] 로그 모니터링
- [ ] 백업 암호화
- [ ] 접근 권한 검토
- [ ] 인시던트 대응 훈련

## 10. 규정 준수

### 10.1 데이터 보호
- GDPR 준수 (EU 사용자)
- 개인정보 최소 수집
- 데이터 보관 기한 설정
- 사용자 동의 관리

### 10.2 금융 규정
- KYC/AML 정책 구현
- 거래 기록 보관
- 의심스러운 활동 보고
- 감사 추적 유지

## 중요 연락처

- **보안 인시던트**: security@letrade.com
- **버그 바운티**: bugbounty@letrade.com
- **24/7 긴급 대응**: +1-xxx-xxx-xxxx