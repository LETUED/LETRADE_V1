# 자동 암호화폐 거래 시스템: 개요 및 아키텍처

## 📋 문서 개요

**문서 목적**: 전문가 수준의 모듈형 자동 암호화폐 거래 및 투자 플랫폼 구축을 위한 포괄적인 기술 청사진 제시

**대상 독자**: 소프트웨어 아키텍트, 퀀트 개발자, 기술 프로젝트 관리자 (분산 시스템, 클라우드 컴퓨팅, 데이터베이스 관리, 자동매매 시스템에 대한 깊은 기술적 이해 보유)

---

## 🎯 1. 프로젝트 비전 및 목표

### 1.1 핵심 목적
- **멀티 전략 동시 실행**: 여러 거래 전략의 안정적인 병렬 실행
- **다양한 투자 지원**: 현물/선물 거래, 스테이킹 등 포괄적 투자 활동
- **24/7 무중단 운영**: Google Cloud Platform(GCP) 환경에서 견고한 연속 운영
- **이중 제어 인터페이스**: CLI 심층 관리 + 텔레그램 원격 제어/실시간 알림

### 1.2 설계 철학
**프로덕션 등급 솔루션** - 단순한 거래 스크립트를 넘어 실제 운영 환경에서의 안정성, 보안성, 확장성을 보장

---

## 🏗️ 2. 핵심 설계 원칙 (아키텍처의 네 기둥)

### 2.1 복원력 (Resilience)
**목표**: 장애 허용 구조 구현
- **문제**: 전통적 모델에서 하나의 전략 실패 → 전체 시스템 중단
- **해결책**: 각 전략을 별도 프로세스로 격리 + 비동기 서비스 간 통신
- **결과**: 연쇄 장애 위험 근본적 차단

### 2.2 확장성 (Scalability)
**목표**: 대규모 리팩토링 없는 성장 지원
- **다차원 확장**: 새 거래 전략, 신규 거래소, 새 금융 상품, 증가하는 처리량
- **구현**: 마이크로서비스 아키텍처를 통한 개별 구성 요소 독립적 확장

### 2.3 확장 용이성 (Extensibility)
**목표**: 새로운 로직의 쉬운 추가 및 통합
- **방법**: 표준화된 BaseStrategy 인터페이스 + 메시지 기반 통신 버스
- **결과**: "플러그인" 방식의 새 거래 전략 모듈 통합 (기존 시스템 수정 없음)

### 2.4 보안 (Security)
**목표**: "보안 우선(Security-First)" 접근 방식
- **다층적 보안 모델**: API 키/DB 자격증명 안전 관리, 최소 권한 원칙, 통신 암호화
- **GCP 보안 기능 활용**: Secret Manager, VPC 방화벽, IP 화이트리스트, 세분화된 IAM

---

## 🔧 3. 고수준 아키텍처: 비동기 메시지 기반 마이크로서비스

### 3.1 아키텍처 패러다임

**선택된 패턴**: 비동기 메시지 기반 마이크로서비스 (Asynchronous Message-Driven Microservices)

**차별점**:
- ❌ 모놀리식 설계 (모든 기능을 단일 애플리케이션으로 구현)
- ❌ 동기식 시스템 (서비스 간 직접 REST API 호출)
- ✅ 독립적 서비스들의 비동기 통신

### 3.2 디커플링의 당위성

**문제 시나리오**: 
```
Strategy Worker → (직접 REST 호출) → Exchange Connector
만약 Exchange Connector 장애 발생 시
→ Strategy Worker 동기적 실패 → 전략 로직 상태 손상 → 전체 워커 중단
```

**해결 방안**:
```
Strategy Worker → (메시지 발행) → RabbitMQ → (메시지 소비) → Exchange Connector
장애 시: 메시지는 큐에 안전하게 저장 → Exchange Connector 복구 시 처리 재개
```

### 3.3 RabbitMQ 선택 이유

**vs ZeroMQ**:
- ✅ 메시지 영속성 (브로커 재시작 시에도 메시지 보존)
- ✅ 전송 확인 (acknowledgment, 메시지 처리 성공 보장)
- ✅ 관리 UI 제공
- ✅ 유연한 라우팅 규칙
- ✅ 엔터프라이즈급 기능 기본 제공

---

## 🏛️ 4. 시스템 아키텍처 다이어그램 및 구성 요소

### 4.1 아키텍처 다이어그램

```mermaid
graph TD
    subgraph "User Interfaces"
        CLI[Command-Line Interface]
        TelegramUI[Telegram UI]
    end

    subgraph "System Services (GCP Compute Engine)"
        CoreEngine[Core Engine]
        StrategyWorkers[Strategy Worker(s)]
        CapitalManager[Capital Manager]
        ExchangeConnector[Exchange Connector]
        TelegramInterface[Telegram Interface]
    end

    subgraph "GCP Managed Services"
        MessageBus[RabbitMQ Message Bus]
        Database[Cloud SQL Database]
        SecretManager[Secret Manager]
    end

    subgraph "External Services"
        Exchanges[Binance, etc.]
    end

    CLI -- "Configuration & Control" --> CoreEngine
    TelegramUI <--> TelegramInterface

    CoreEngine -- "Spawns & Monitors" --> StrategyWorkers
    CoreEngine -- "System Events & Logs" --> MessageBus
    
    StrategyWorkers -- "1. request.capital.allocation" --> MessageBus
    MessageBus -- "2. request.capital.allocation" --> CapitalManager
    CapitalManager -- "3. commands.execute_trade" --> MessageBus
    MessageBus -- "4. commands.execute_trade" --> ExchangeConnector
    
    ExchangeConnector -- "Market Data & Trade Events" --> MessageBus
    MessageBus -- "Market Data" --> StrategyWorkers
    MessageBus -- "Trade Events & Notifications" --> CoreEngine & TelegramInterface & StrategyWorkers
    
    TelegramInterface -- "User Commands" --> MessageBus
    MessageBus -- "Commands" --> CoreEngine

    ExchangeConnector <--> Exchanges

    CoreEngine <--> Database
    StrategyWorkers <--> Database
    ExchangeConnector <--> Database
    CapitalManager <--> Database

    CoreEngine & ExchangeConnector & TelegramInterface -- "Secrets" --> SecretManager
```

### 4.2 핵심 서비스 상세 설명

#### 🎛️ Core Engine
- **역할**: 중앙 오케스트레이터
- **책임**: 
  - 전략 설정 관리
  - 워커 프로세스 생성 및 감독
  - 시스템 전반 상태/성능 데이터 집계

#### ⚙️ Strategy Worker(s)
- **역할**: 격리된 단일 목적 프로세스
- **책임**:
  - 단일 거래 전략 로직 실행
  - 필요한 시장 데이터 구독
  - 거래 '제안' 발행

#### 💰 Capital Manager
- **역할**: 자본 할당 및 포트폴리오 리스크 관리 중앙 허브
- **책임**:
  - 거래 '제안' 검토 및 승인
  - 최종 주문 크기 결정
  - 실행 지시
- **참조**: 상세 내용은 `02_Capital_and_Risk_Management.md` 참조

#### 🔌 Exchange Connector
- **역할**: 외부 거래소 API 통신 전담 게이트웨이
- **책임**:
  - API 키 관리
  - 속도 제한 처리
  - 오류 처리 중앙 추상화

#### 📱 Telegram Interface
- **역할**: 텔레그램 봇 API 상호작용 처리
- **책임**:
  - 사용자 명령 → 시스템 메시지 변환
  - 시스템 이벤트 → 사용자 알림 변환

#### 🗄️ Database (GCP Cloud SQL)
- **역할**: 영구 데이터 저장소
- **기술**: 관리형 PostgreSQL 데이터베이스
- **저장 데이터**: 거래 내역, 포지션, 설정 등

#### 🚌 Message Bus (RabbitMQ)
- **역할**: 중앙 신경 시스템
- **책임**: 모든 서비스 간 비동기 통신 중개

#### 🔐 Secret Manager (GCP)
- **역할**: 민감 정보 안전 저장소
- **관리 대상**: API 키, 텔레그램 토큰, 데이터베이스 자격 증명 등

---

## 🛠️ 5. 기술 스택

> **선택 기준**: 각 기술은 시스템의 핵심 설계 원칙(복원력, 확장성, 확장 용이성, 보안)을 충족시키기 위해 신중하게 선택

### 5.1 기술 스택 상세표

| **분류** | **기술/서비스** | **목적 및 정당성** |
|----------|----------------|-------------------|
| **클라우드 플랫폼** | Google Cloud Platform (GCP) | 전체 인프라의 호스팅, 관리, 운영을 위한 통합 플랫폼 |
| **실행 환경** | Google Compute Engine (GCE) | 24/7 지속적인 실행이 요구되는 롱러닝(long-running) 애플리케이션을 위한 가상 머신 |
| **컨테이너화** | Docker | 애플리케이션과 모든 종속성을 격리된, 이식 가능한 환경으로 패키징하여 개발과 운영의 일관성 보장 |
| **CI/CD** | Google Cloud Build | Git 푸시 시 코드의 빌드, 테스트, 배포 과정을 자동화하여 신속하고 일관된 배포 실현 |
| **아티팩트 저장소** | Google Artifact Registry | 빌드된 Docker 컨테이너 이미지를 안전하게 버전 관리하며 저장 |
| **비밀 관리** | Google Secret Manager | API 키, 데이터베이스 암호 등 민감한 자격 증명을 코드와 분리하여 안전하게 저장하고 런타임에 접근 |
| **데이터베이스** | Google Cloud SQL (PostgreSQL) | 거래 상태, 포지션, 로그 등 모든 영구 데이터를 위한 완전 관리형 관계형 데이터베이스 |
| **메시지 버스** | RabbitMQ | 서비스 간의 비동기 통신을 중개하여 시스템의 복원력과 결합도 완화 |
| **핵심 프로그래밍 언어** | Python 3.11+ | 거래 봇의 핵심 로직 개발을 위한 주력 언어 |
| **거래소 라이브러리** | ccxt | 100개 이상의 암호화폐 거래소와의 상호작용을 표준화된 인터페이스로 추상화 |
| **데이터베이스 ORM** | SQLAlchemy | 파이썬 객체와 관계형 데이터베이스 테이블 간의 매핑을 자동화하고 커넥션 풀링 관리 |
| **프로세스 관리** | systemd | GCE 인스턴스 내에서 봇 컨테이너의 자동 시작, 재시작, 로깅을 관리하는 견고한 서비스 관리자 |
| **사용자 인터페이스** | Telegram Bot API, Python click | 실시간 원격 제어 및 알림(텔레그램)과 심층적인 관리(CLI)를 위한 인터페이스 |

---

## 📝 문서 관리 정보

**작성일**: 해당 정보 미제공  
**버전**: 1.0  
**관련 문서**: `02_Capital_and_Risk_Management.md`  
**문서 타입**: 기술 아키텍처 명세서