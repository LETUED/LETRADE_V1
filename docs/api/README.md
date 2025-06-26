# API 문서

## 개요

Letrade_v1 시스템의 API 문서입니다. REST API와 Message Bus API를 통해 시스템과 상호작용할 수 있습니다.

## API 문서 목록

### 1. [REST API](./REST_API.md)
- HTTP/HTTPS 기반 동기식 API
- 인증, 포트폴리오 관리, 전략 제어, 모니터링
- JWT 기반 인증
- WebSocket 실시간 데이터 스트리밍

### 2. [Message Bus API](./MESSAGE_BUS_API.md)
- RabbitMQ 기반 비동기 메시징
- 마이크로서비스 간 통신
- 이벤트 드리븐 아키텍처
- 거래 명령, 시장 데이터, 시스템 이벤트

## 빠른 시작

### REST API 예제

```bash
# 로그인
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password123"}'

# 포트폴리오 조회
curl -X GET http://localhost:8000/api/v1/portfolios \
  -H "Authorization: Bearer {token}"
```

### Message Bus 예제

```python
from src.common.message_bus import MessageBus

# 메시지 발행
bus = MessageBus()
await bus.connect()
await bus.publish("letrade.commands", "execute_trade", {
    "strategy_id": 123,
    "symbol": "BTC/USDT",
    "side": "buy",
    "amount": 0.01
})
```

## API 설계 원칙

### 1. RESTful 원칙
- 리소스 기반 URL 설계
- HTTP 메서드 의미 준수
- 상태 코드 표준 활용

### 2. 일관된 응답 형식
```json
{
  "status": "success",
  "data": {...},
  "meta": {
    "timestamp": "2024-01-01T10:00:00Z",
    "version": "1.0.0"
  }
}
```

### 3. 에러 처리
```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {...}
  }
}
```

## 인증 및 보안

### JWT 토큰
- Access Token: 1시간 유효
- Refresh Token: 7일 유효
- Bearer 토큰 헤더 사용

### API 키 관리
- GCP Secret Manager 통합
- 환경별 키 분리
- 정기적 키 로테이션

## Rate Limiting

### REST API
- 인증된 사용자: 1000 요청/분
- 미인증 사용자: 100 요청/분

### Message Bus
- 메시지 발행: 10,000 msg/s
- 메시지 소비: 무제한

## 버전 관리

- 현재 버전: v1
- URL 패스에 버전 포함: `/api/v1/`
- 하위 호환성 유지

## 모니터링

### 헬스체크
```bash
curl http://localhost:8000/health
```

### 메트릭
- Prometheus 형식: `/metrics`
- 커스텀 메트릭: `/api/v1/system/metrics`

## 문제 해결

### 일반적인 문제

1. **401 Unauthorized**
   - 토큰 만료 확인
   - 토큰 갱신 필요

2. **429 Too Many Requests**
   - Rate limit 초과
   - 요청 간격 조정

3. **503 Service Unavailable**
   - 서비스 상태 확인
   - Circuit breaker 활성화 여부

### 디버깅 팁

1. 요청/응답 로깅 활성화
2. 상관 ID 추적
3. 타임스탬프 동기화 확인

## 지원

- GitHub Issues: 버그 리포트
- Discord: 실시간 지원
- 문서: 상세 가이드