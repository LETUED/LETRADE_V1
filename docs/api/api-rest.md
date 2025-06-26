# REST API 문서

## 개요

Letrade_v1 REST API는 시스템과의 프로그래매틱 상호작용을 제공합니다.

## 기본 정보

- **Base URL**: `http://localhost:8000/api/v1`
- **인증**: JWT Bearer Token
- **Content-Type**: `application/json`

## 인증

### 로그인
```http
POST /auth/login
```

**Request Body:**
```json
{
  "username": "admin",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### 토큰 갱신
```http
POST /auth/refresh
Authorization: Bearer {refresh_token}
```

## 포트폴리오 관리

### 포트폴리오 목록 조회
```http
GET /portfolios
Authorization: Bearer {token}
```

**Response:**
```json
{
  "portfolios": [
    {
      "id": 1,
      "name": "Main Portfolio",
      "total_capital": 10000.0,
      "available_capital": 5000.0,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### 포트폴리오 상세 조회
```http
GET /portfolios/{portfolio_id}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "id": 1,
  "name": "Main Portfolio",
  "total_capital": 10000.0,
  "available_capital": 5000.0,
  "metrics": {
    "unrealized_pnl": 150.50,
    "realized_pnl_today": 50.25,
    "total_risk_exposure": 2000.0,
    "number_of_positions": 3
  }
}
```

## 전략 관리

### 활성 전략 목록
```http
GET /strategies
Authorization: Bearer {token}
```

**Query Parameters:**
- `portfolio_id` (optional): 특정 포트폴리오의 전략만 조회
- `is_active` (optional): 활성/비활성 필터

**Response:**
```json
{
  "strategies": [
    {
      "id": 1,
      "name": "MA Crossover BTC",
      "class_name": "MACrossoverStrategy",
      "portfolio_id": 1,
      "is_active": true,
      "parameters": {
        "fast_period": 20,
        "slow_period": 50
      }
    }
  ]
}
```

### 전략 생성
```http
POST /strategies
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "name": "New Strategy",
  "class_name": "MACrossoverStrategy",
  "portfolio_id": 1,
  "parameters": {
    "fast_period": 15,
    "slow_period": 45,
    "symbol": "ETH/USDT"
  }
}
```

### 전략 수정
```http
PUT /strategies/{strategy_id}
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "is_active": false,
  "parameters": {
    "fast_period": 25
  }
}
```

### 전략 삭제
```http
DELETE /strategies/{strategy_id}
Authorization: Bearer {token}
```

## 거래 관련

### 거래 내역 조회
```http
GET /trades
Authorization: Bearer {token}
```

**Query Parameters:**
- `portfolio_id`: 포트폴리오 ID
- `strategy_id`: 전략 ID
- `symbol`: 거래 심볼
- `status`: 거래 상태 (pending, filled, cancelled)
- `start_date`: 시작 날짜 (ISO 8601)
- `end_date`: 종료 날짜 (ISO 8601)
- `limit`: 결과 수 제한 (기본: 100)
- `offset`: 페이지네이션 오프셋

**Response:**
```json
{
  "trades": [
    {
      "id": 1,
      "portfolio_id": 1,
      "strategy_id": 1,
      "symbol": "BTC/USDT",
      "side": "buy",
      "quantity": 0.001,
      "price": 50000.0,
      "status": "filled",
      "executed_at": "2024-01-01T10:00:00Z",
      "realized_pnl": 0.0
    }
  ],
  "total": 150,
  "limit": 100,
  "offset": 0
}
```

### 포지션 조회
```http
GET /positions
Authorization: Bearer {token}
```

**Query Parameters:**
- `portfolio_id`: 포트폴리오 ID
- `is_open`: 오픈 포지션만 조회 (true/false)
- `symbol`: 특정 심볼

**Response:**
```json
{
  "positions": [
    {
      "id": 1,
      "portfolio_id": 1,
      "symbol": "BTC/USDT",
      "side": "long",
      "size": 0.01,
      "entry_price": 50000.0,
      "current_price": 51000.0,
      "unrealized_pnl": 10.0,
      "is_open": true
    }
  ]
}
```

## 모니터링

### 시스템 상태
```http
GET /system/status
Authorization: Bearer {token}
```

**Response:**
```json
{
  "status": "healthy",
  "services": {
    "core_engine": "running",
    "capital_manager": "running",
    "exchange_connector": "running",
    "database": "connected",
    "message_bus": "connected"
  },
  "uptime_seconds": 86400,
  "version": "1.0.0"
}
```

### 성능 메트릭
```http
GET /system/metrics
Authorization: Bearer {token}
```

**Response:**
```json
{
  "metrics": {
    "trade_validation_latency_ms": {
      "avg": 0.15,
      "p95": 0.25,
      "p99": 0.5
    },
    "websocket_messages_per_second": 150,
    "cache_hit_rate": 0.85,
    "active_strategies": 5,
    "open_positions": 3
  }
}
```

### 시스템 로그
```http
GET /system/logs
Authorization: Bearer {token}
```

**Query Parameters:**
- `level`: 로그 레벨 (DEBUG, INFO, WARNING, ERROR)
- `component`: 컴포넌트 이름
- `start_time`: 시작 시간
- `end_time`: 종료 시간
- `limit`: 결과 수 제한

## 제어 명령

### 긴급 정지
```http
POST /control/emergency-stop
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "reason": "Market anomaly detected"
}
```

### 전략 재시작
```http
POST /control/restart-strategy
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "strategy_id": 1
}
```

## 에러 응답

모든 에러는 다음 형식으로 반환됩니다:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {
      "field": "quantity",
      "reason": "Must be positive number"
    }
  }
}
```

### 에러 코드
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error

## Rate Limiting

- **인증된 사용자**: 1000 요청/분
- **인증되지 않은 사용자**: 100 요청/분

Rate limit 정보는 응답 헤더에 포함됩니다:
- `X-RateLimit-Limit`: 제한
- `X-RateLimit-Remaining`: 남은 요청 수
- `X-RateLimit-Reset`: 리셋 시간 (Unix timestamp)

## WebSocket API

실시간 데이터는 WebSocket을 통해 제공됩니다:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

// 인증
ws.send(JSON.stringify({
  type: 'auth',
  token: 'your_jwt_token'
}));

// 구독
ws.send(JSON.stringify({
  type: 'subscribe',
  channels: ['trades', 'positions', 'market_data.BTC/USDT']
}));

// 메시지 수신
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};
```