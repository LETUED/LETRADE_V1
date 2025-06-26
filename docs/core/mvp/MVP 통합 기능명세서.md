# 자동 암호화폐 거래 시스템 MVP 통합 기능명세서

## 목차
1. [개요](#1-개요)
2. [시스템 아키텍처 및 디자인 패턴](#2-시스템-아키텍처-및-디자인-패턴)
3. [기능 요구사항](#3-기능-요구사항)
4. [비기능 요구사항](#4-비기능-요구사항)
5. [데이터 모델](#5-데이터-모델)
6. [인터페이스 명세](#6-인터페이스-명세)
7. [보안 요구사항](#7-보안-요구사항)
8. [성능 요구사항](#8-성능-요구사항)
9. [테스트 요구사항](#9-테스트-요구사항)

---

## 1. 개요

### 1.1 문서 목적
본 문서는 개인 투자자를 위한 자동 암호화폐 거래 시스템의 MVP(Minimum Viable Product) 기능 명세를 정의합니다. V-model 방법론을 따라 각 개발 단계별 요구사항과 검증 방법을 명시합니다.

### 1.2 시스템 개요
- **목표**: Binance 거래소에서 이동평균 교차 전략을 활용한 24/7 자동 거래
- **대상 사용자**: 개인 암호화폐 투자자
- **핵심 가치**: 안정성과 리스크 관리를 최우선으로 하는 자동화된 거래 시스템

### 1.3 MVP 범위
- **거래소**: Binance (현물 거래)
- **전략**: 이동평균 교차 (MA Crossover)
- **거래쌍**: 주요 암호화폐 페어 (BTC/USDT, ETH/USDT 등)
- **리스크 관리**: 손절매, 포지션 크기 제한, 최대 손실률 제한

### 1.4 V-Model 접근 방식
```
요구사항 분석 ←→ 인수 테스트
  시스템 설계 ←→ 시스템 테스트
    상세 설계 ←→ 통합 테스트
      구현 ←→ 단위 테스트
```

---

## 2. 시스템 아키텍처 및 디자인 패턴

### 2.1 전체 아키텍처 (마이크로서비스 패턴)
```
┌─────────────────────────────────────────────────────────────┐
│                      User Interface Layer                    │
│  ┌─────────────┐                      ┌──────────────────┐ │
│  │     CLI     │                      │  Telegram Bot    │ │
│  └─────────────┘                      └──────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────┐
│                    Application Service Layer                 │
│  ┌──────────────┐  ┌─────────────────┐  ┌───────────────┐ │
│  │ Core Engine  │  │Strategy Worker  │  │Capital Manager│ │
│  │  (Observer)  │  │   (Strategy)    │  │  (Singleton)  │ │
│  └──────────────┘  └─────────────────┘  └───────────────┘ │
│  ┌──────────────────────┐         ┌────────────────────┐   │
│  │  Exchange Connector  │         │ Telegram Interface │   │
│  │  (Adapter/Facade)    │         │    (Adapter)       │   │
│  └──────────────────────┘         └────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                      │
│  ┌──────────────┐  ┌─────────────────┐  ┌───────────────┐ │
│  │  RabbitMQ    │  │   Cloud SQL     │  │Secret Manager │ │
│  │(Message Bus) │  │   (Database)    │  │   (Vault)     │ │
│  └──────────────┘  └─────────────────┘  └───────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 적용된 디자인 패턴

#### 2.2.1 Strategy Pattern (전략 패턴)
- **적용 위치**: BaseStrategy 추상 클래스와 구체적 전략 구현체
- **목적**: 거래 전략의 알고리즘을 캡슐화하고 런타임에 교체 가능

#### 2.2.2 Observer Pattern (관찰자 패턴)
- **적용 위치**: Core Engine과 이벤트 구독 시스템
- **목적**: 시스템 이벤트에 대한 느슨한 결합 달성

#### 2.2.3 Singleton Pattern (싱글톤 패턴)
- **적용 위치**: Capital Manager
- **목적**: 자본 관리의 단일 진실 소스 보장

#### 2.2.4 Adapter Pattern (어댑터 패턴)
- **적용 위치**: Exchange Connector, Telegram Interface
- **목적**: 외부 API와의 인터페이스 표준화

#### 2.2.5 Factory Pattern (팩토리 패턴)
- **적용 위치**: Strategy Worker 생성
- **목적**: 전략 인스턴스의 동적 생성 관리

### 2.3 SOLID 원칙 적용

#### Single Responsibility Principle (SRP)
- 각 서비스는 단일 책임만 보유
- 예: Exchange Connector는 오직 거래소 통신만 담당

#### Open/Closed Principle (OCP)
- BaseStrategy 인터페이스를 통한 확장 가능한 설계
- 새 전략 추가 시 기존 코드 수정 불필요

#### Liskov Substitution Principle (LSP)
- 모든 전략 구현체는 BaseStrategy를 완벽히 대체 가능

#### Interface Segregation Principle (ISP)
- 각 서비스는 필요한 인터페이스만 구현
- 예: 읽기 전용 서비스는 쓰기 인터페이스 불필요

#### Dependency Inversion Principle (DIP)
- 고수준 모듈은 추상화에 의존
- 메시지 버스를 통한 느슨한 결합

---

## 3. 기능 요구사항

### 3.1 Core Engine (FR-CE)

#### FR-CE-001: 시스템 초기화
- **설명**: 시스템 시작 시 모든 서비스 초기화 및 상태 검증
- **입력**: 시스템 시작 명령
- **처리**: 
  1. 데이터베이스 연결 확인
  2. RabbitMQ 연결 확인
  3. Secret Manager 접근 확인
  4. 활성 전략 로드
- **출력**: 시스템 준비 상태
- **검증**: 시스템 테스트에서 확인

#### FR-CE-002: 전략 생명주기 관리
- **설명**: 전략의 시작, 중지, 재시작 관리
- **입력**: 전략 제어 명령
- **처리**:
  1. 전략 상태 확인
  2. Strategy Worker 프로세스 생성/종료
  3. 상태 업데이트
- **출력**: 전략 실행 상태
- **검증**: 통합 테스트에서 확인

#### FR-CE-003: 시스템 모니터링
- **설명**: 전체 시스템 상태 실시간 모니터링
- **입력**: 시스템 이벤트 스트림
- **처리**:
  1. 이벤트 수집
  2. 메트릭 계산
  3. 이상 상태 감지
- **출력**: 시스템 상태 리포트
- **검증**: 시스템 테스트에서 확인

### 3.2 Strategy Worker (FR-SW)

#### FR-SW-001: 이동평균 계산
- **설명**: 단기 및 장기 이동평균 계산
- **입력**: OHLCV 시장 데이터
- **처리**:
  1. 가격 데이터 수집
  2. SMA 계산 (기본: 50일, 200일)
  3. 지표 업데이트
- **출력**: 계산된 이동평균 값
- **검증**: 단위 테스트에서 확인

#### FR-SW-002: 거래 신호 생성
- **설명**: 골든/데스 크로스 감지 및 거래 신호 생성
- **입력**: 계산된 이동평균 값
- **처리**:
  1. 크로스오버 감지
  2. 신호 유효성 검증
  3. 거래 제안 생성
- **출력**: 거래 제안 (매수/매도)
- **검증**: 단위 테스트 및 통합 테스트에서 확인

#### FR-SW-003: 상태 영속성
- **설명**: 전략 상태의 저장 및 복구
- **입력**: 전략 상태 데이터
- **처리**:
  1. 주기적 상태 저장
  2. 재시작 시 상태 복구
- **출력**: 영속화된 전략 상태
- **검증**: 통합 테스트에서 확인

### 3.3 Capital Manager (FR-CM)

#### FR-CM-001: 자본 할당
- **설명**: 거래 요청에 대한 자본 할당 결정
- **입력**: 거래 제안
- **처리**:
  1. 가용 자본 확인
  2. 리스크 규칙 검증
  3. 포지션 크기 계산
- **출력**: 승인된 거래 명령 또는 거부
- **검증**: 통합 테스트에서 확인

#### FR-CM-002: 리스크 관리 규칙 적용
- **설명**: 포트폴리오 수준 리스크 관리
- **입력**: 리스크 규칙 설정
- **처리**:
  1. 최대 손실률 확인
  2. 포지션 집중도 확인
  3. 거래 빈도 제한 확인
- **출력**: 리스크 검증 결과
- **검증**: 시스템 테스트에서 확인

#### FR-CM-003: 포지션 사이징
- **설명**: 적절한 거래 규모 결정
- **입력**: 거래 신호, 리스크 파라미터
- **처리**:
  1. 고정 비율 방식 적용 (기본 2%)
  2. 손절매 거리 계산
  3. 최종 포지션 크기 결정
- **출력**: 계산된 거래 수량
- **검증**: 단위 테스트에서 확인

### 3.4 Exchange Connector (FR-EC)

#### FR-EC-001: 시장 데이터 수집
- **설명**: Binance로부터 실시간 시장 데이터 수집
- **입력**: 구독 심볼 목록
- **처리**:
  1. WebSocket 연결 관리
  2. 데이터 스트림 수신
  3. 데이터 정규화
- **출력**: 표준화된 시장 데이터
- **검증**: 통합 테스트에서 확인

#### FR-EC-002: 주문 실행
- **설명**: 거래 명령의 실제 실행
- **입력**: 거래 명령
- **처리**:
  1. API 인증
  2. 주문 전송
  3. 실행 확인
- **출력**: 거래 실행 결과
- **검증**: 시스템 테스트에서 확인

#### FR-EC-003: 계정 정보 조회
- **설명**: 잔고 및 포지션 정보 조회
- **입력**: 조회 요청
- **처리**:
  1. API 호출
  2. 데이터 파싱
  3. 상태 업데이트
- **출력**: 계정 상태 정보
- **검증**: 통합 테스트에서 확인

### 3.5 Telegram Interface (FR-TI)

#### FR-TI-001: 명령어 처리
- **설명**: 사용자 명령어 해석 및 실행
- **입력**: 텔레그램 메시지
- **처리**:
  1. 사용자 인증
  2. 명령어 파싱
  3. 시스템 메시지 변환
- **출력**: 명령 실행 결과
- **검증**: 시스템 테스트에서 확인

#### FR-TI-002: 알림 발송
- **설명**: 시스템 이벤트에 대한 사용자 알림
- **입력**: 시스템 이벤트
- **처리**:
  1. 이벤트 필터링
  2. 메시지 포맷팅
  3. 알림 전송
- **출력**: 텔레그램 알림
- **검증**: 시스템 테스트에서 확인

### 3.6 상태 조정 프로토콜 (FR-SR)

#### FR-SR-001: 상태 불일치 감지
- **설명**: 시스템 상태와 거래소 상태 간 불일치 감지
- **입력**: 시스템 상태, 거래소 상태
- **처리**:
  1. 상태 비교
  2. 불일치 항목 식별
  3. 심각도 평가
- **출력**: 불일치 리포트
- **검증**: 통합 테스트에서 확인

#### FR-SR-002: 상태 조정 실행
- **설명**: 감지된 불일치 해결
- **입력**: 불일치 리포트
- **처리**:
  1. 조정 전략 선택
  2. 상태 업데이트 실행
  3. 조정 결과 검증
- **출력**: 조정된 시스템 상태
- **검증**: 시스템 테스트에서 확인

---

## 4. 비기능 요구사항

### 4.1 가용성 (NFR-AV)
- **NFR-AV-001**: 시스템 가동률 99.5% 이상 (월간 다운타임 3.6시간 이내)
- **NFR-AV-002**: 단일 서비스 장애 시 30초 이내 자동 복구

### 4.2 성능 (NFR-PF)
- **NFR-PF-001**: 거래 신호 생성부터 주문 실행까지 1초 이내
- **NFR-PF-002**: 시장 데이터 처리 지연 100ms 이내
- **NFR-PF-003**: 동시 처리 가능 거래쌍 최소 10개

### 4.3 확장성 (NFR-SC)
- **NFR-SC-001**: 새로운 전략 추가 시 기존 시스템 수정 불필요
- **NFR-SC-002**: 전략 워커 수평 확장 가능

### 4.4 보안 (NFR-SE)
- **NFR-SE-001**: 모든 API 키는 암호화되어 저장
- **NFR-SE-002**: 텔레그램 사용자 화이트리스트 기반 접근 제어
- **NFR-SE-003**: 모든 통신은 TLS 암호화

### 4.5 유지보수성 (NFR-MT)
- **NFR-MT-001**: 모든 서비스는 독립적으로 배포 가능
- **NFR-MT-002**: 코드 커버리지 80% 이상
- **NFR-MT-003**: 모든 API는 버전 관리

---

## 5. 데이터 모델

### 5.1 핵심 엔티티

#### 5.1.1 strategies 테이블
```sql
CREATE TABLE strategies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    strategy_type VARCHAR(50) NOT NULL DEFAULT 'MA_CROSSOVER',
    exchange VARCHAR(50) NOT NULL DEFAULT 'binance',
    symbol VARCHAR(50) NOT NULL,
    parameters JSONB DEFAULT '{"fast": 50, "slow": 200}',
    position_sizing_config JSONB DEFAULT '{"model": "fixed_fractional", "risk_percent": 0.02}',
    is_active BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### 5.1.2 portfolios 테이블
```sql
CREATE TABLE portfolios (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    total_capital NUMERIC(20, 8) NOT NULL,
    available_capital NUMERIC(20, 8) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'USDT',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### 5.1.3 trades 테이블
```sql
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER NOT NULL REFERENCES strategies(id),
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('buy', 'sell')),
    type VARCHAR(20) NOT NULL CHECK (type IN ('market', 'limit')),
    amount DOUBLE PRECISION NOT NULL,
    price DOUBLE PRECISION,
    cost DOUBLE PRECISION,
    fee DOUBLE PRECISION,
    status VARCHAR(20) NOT NULL,
    exchange_order_id VARCHAR(255) UNIQUE NOT NULL,
    timestamp_created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    timestamp_updated TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### 5.1.4 positions 테이블
```sql
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER NOT NULL REFERENCES strategies(id),
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    entry_price DOUBLE PRECISION NOT NULL,
    current_size DOUBLE PRECISION NOT NULL,
    stop_loss_price DOUBLE PRECISION,
    take_profit_price DOUBLE PRECISION,
    unrealized_pnl DOUBLE PRECISION DEFAULT 0,
    realized_pnl DOUBLE PRECISION DEFAULT 0,
    is_open BOOLEAN NOT NULL DEFAULT true,
    opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ
);
```

#### 5.1.5 portfolio_rules 테이블
```sql
CREATE TABLE portfolio_rules (
    id SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(id),
    rule_type VARCHAR(50) NOT NULL,
    rule_value JSONB NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 5.2 데이터 무결성 제약

- 모든 외래 키에 CASCADE 옵션 적용
- 거래 금액은 양수값만 허용
- 타임스탬프는 UTC 기준으로 저장
- JSONB 필드는 스키마 검증 트리거 적용

---

## 6. 인터페이스 명세

### 6.1 RabbitMQ 메시지 인터페이스

#### 6.1.1 시장 데이터 메시지
```json
{
  "routing_key": "market_data.binance.btcusdt",
  "payload": {
    "symbol": "BTC/USDT",
    "timestamp": 1234567890,
    "open": 50000.0,
    "high": 51000.0,
    "low": 49500.0,
    "close": 50500.0,
    "volume": 1000.0
  }
}
```

#### 6.1.2 자본 할당 요청
```json
{
  "routing_key": "request.capital.allocation.123",
  "payload": {
    "strategy_id": 123,
    "symbol": "BTC/USDT",
    "side": "buy",
    "signal_price": 50000.0,
    "stop_loss_price": 49000.0,
    "confidence": 0.8
  }
}
```

#### 6.1.3 거래 실행 명령
```json
{
  "routing_key": "commands.execute_trade",
  "payload": {
    "strategy_id": 123,
    "exchange": "binance",
    "symbol": "BTC/USDT",
    "side": "buy",
    "type": "market",
    "amount": 0.01,
    "stop_loss": 49000.0
  }
}
```

### 6.2 REST API 인터페이스 (CLI용)

#### 6.2.1 전략 관리
```
GET    /api/v1/strategies              # 전략 목록 조회
POST   /api/v1/strategies              # 새 전략 추가
GET    /api/v1/strategies/{id}         # 특정 전략 조회
PUT    /api/v1/strategies/{id}         # 전략 설정 업데이트
DELETE /api/v1/strategies/{id}         # 전략 삭제
POST   /api/v1/strategies/{id}/start   # 전략 시작
POST   /api/v1/strategies/{id}/stop    # 전략 중지
```

#### 6.2.2 포트폴리오 관리
```
GET    /api/v1/portfolios              # 포트폴리오 목록
POST   /api/v1/portfolios              # 포트폴리오 생성
GET    /api/v1/portfolios/{id}/status  # 포트폴리오 상태
PUT    /api/v1/portfolios/{id}/rules   # 리스크 규칙 설정
```

### 6.3 텔레그램 명령어 인터페이스

```
/start              - 봇 시작 및 인증
/status             - 시스템 상태 조회
/portfolio          - 포트폴리오 현황
/positions          - 현재 포지션 목록
/profit [period]    - 수익률 조회
/stop_strategy [id] - 특정 전략 중지
/help               - 도움말
```

---

## 7. 보안 요구사항

### 7.1 인증 및 권한 (SEC-AUTH)
- **SEC-AUTH-001**: 텔레그램 사용자 화이트리스트 기반 인증
- **SEC-AUTH-002**: CLI는 로컬 접근만 허용
- **SEC-AUTH-003**: 서비스 간 통신은 mTLS 사용

### 7.2 데이터 보호 (SEC-DATA)
- **SEC-DATA-001**: API 키는 GCP Secret Manager에 암호화 저장
- **SEC-DATA-002**: 데이터베이스 연결은 SSL/TLS 필수
- **SEC-DATA-003**: 로그에 민감 정보 마스킹

### 7.3 네트워크 보안 (SEC-NET)
- **SEC-NET-001**: VPC 내부 통신만 허용
- **SEC-NET-002**: 거래소 API는 IP 화이트리스트 적용
- **SEC-NET-003**: 모든 외부 통신은 HTTPS

---

## 8. 성능 요구사항

### 8.1 응답 시간 (PERF-RT)
- **PERF-RT-001**: 거래 신호 처리: < 100ms
- **PERF-RT-002**: API 응답 시간: < 200ms
- **PERF-RT-003**: 데이터베이스 쿼리: < 50ms

### 8.2 처리량 (PERF-TP)
- **PERF-TP-001**: 초당 100개 이상의 시장 데이터 메시지 처리
- **PERF-TP-002**: 동시 10개 이상의 전략 실행 지원
- **PERF-TP-003**: 분당 60개 이상의 거래 실행 가능

### 8.3 리소스 사용 (PERF-RU)
- **PERF-RU-001**: 전략 워커당 메모리 사용량 < 256MB
- **PERF-RU-002**: CPU 사용률 평균 < 50%
- **PERF-RU-003**: 데이터베이스 연결 풀 크기 < 50

---

## 9. 테스트 요구사항

### 9.1 단위 테스트 (V-Model Level 1)
- **대상**: 개별 함수 및 메서드
- **커버리지**: 80% 이상
- **도구**: pytest, unittest.mock
- **주요 테스트**:
  - 이동평균 계산 정확성
  - 거래 신호 생성 로직
  - 포지션 사이징 계산

### 9.2 통합 테스트 (V-Model Level 2)
- **대상**: 서비스 간 상호작용
- **환경**: Docker Compose 기반 로컬 환경
- **주요 테스트**:
  - RabbitMQ 메시지 흐름
  - 데이터베이스 트랜잭션
  - API 통합

### 9.3 시스템 테스트 (V-Model Level 3)
- **대상**: 전체 시스템 동작
- **환경**: 스테이징 환경 (프로덕션 유사)
- **주요 테스트**:
  - End-to-End 거래 흐름
  - 장애 복구 시나리오
  - 성능 및 부하 테스트

### 9.4 인수 테스트 (V-Model Level 4)
- **대상**: 비즈니스 요구사항 충족
- **방법**: 실제 소액 거래 실행
- **주요 검증**:
  - 수익성 검증
  - 리스크 관리 효과성
  - 사용자 경험

---

## 부록 A: 용어집

- **MA (Moving Average)**: 이동평균
- **Golden Cross**: 단기 이동평균이 장기 이동평균을 상향 돌파
- **Death Cross**: 단기 이동평균이 장기 이동평균을 하향 돌파
- **Position Sizing**: 거래 규모 결정
- **Stop Loss**: 손절매
- **MVP**: Minimum Viable Product (최소 기능 제품)

## 부록 B: 참조 문서

- 원본 시스템 설계 문서
- Binance API 문서
- RabbitMQ 문서
- GCP 모범 사례 가이드