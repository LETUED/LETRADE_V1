# 📚 Letrade_v1 문서 가이드

이 폴더는 Letrade_v1 프로젝트의 모든 문서를 기능별로 체계적으로 정리한 곳입니다.

## 🗂️ 문서 구조 (기능별 분류)

### 🔒 **core/** - 근본 문서들 (터치 금지)
프로젝트의 핵심 설계 문서들로, 사용자가 직접 관리합니다.
```
core/
├── mvp/           # MVP 기능 명세서 + UML 다이어그램
├── full-system/   # 전체 시스템 고급 기능 설계
└── design-docs/   # 상세 아키텍처 설계 문서들 (8개 문서)
```

### 🏗️ **architecture/** - 시스템 아키텍처
현재 구현된 시스템의 아키텍처 및 설계 패턴들
- `design-system-architecture-v2.md` - 핵심 시스템 아키텍처
- `design-interface-specification.md` - 인터페이스 명세
- `design-implementation-plan.md` - 구현 계획
- `design-test-strategy.md` - 테스트 전략

### 📡 **api/** - API 명세서들
모든 API 인터페이스 문서들
- `api-message-bus.md` - RabbitMQ 메시지 버스 API
- `api-rest.md` - REST API 명세
- `api-telegram-botfather.md` - 텔레그램 봇 API

### 🧠 **strategies/** - 전략 개발
거래 전략 개발 관련 문서들
- `guide-base-strategy-development.md` - BaseStrategy 개발 가이드
- `03_Strategy_Library_and_Implementation.md` - 전략 라이브러리 설계

### 💰 **capital-management/** - 자금 관리
리스크 관리 및 자본 배분 관련 문서들
- `02_Capital_and_Risk_Management.md` - 자금 관리 시스템 설계

### 🔄 **exchange-integration/** - 거래소 연동
거래소 API 통합 및 설정 문서들
- `research-binance-api-integration.md` - Binance API 통합 전략
- `setup-binance-api.md` - Binance API 설정 가이드
- `setup-binance-testnet.md` - Binance 테스트넷 설정

### 🧪 **testing/** - 테스트 가이드
테스트 전략 및 실행 가이드들
- `guide-testing-philosophy.md` - 테스팅 철학 (내부 테스트는 절대 심플하면 안됨!)
- `guide-24h-continuous-testing.md` - 24시간 연속 테스팅 시스템
- `guide-real-infrastructure-testing.md` - 실제 인프라 통합 테스트
- `test-binance-integration-plan.md` - Binance 통합 테스트 계획

### 🚀 **deployment/** - 배포 & 자동화
배포 및 CI/CD 관련 문서들
- `guide-auto-release.md` - 자동 릴리즈 시스템
- `guide-ci-optimization.md` - CI/CD 최적화 가이드
- `guide-deployment-workflow.md` - 배포 워크플로우

### 📊 **monitoring/** - 성능 & 모니터링
시스템 성능 및 모니터링 관련 문서들
- `guide-performance-optimization.md` - 성능 최적화 가이드
- `report-performance-achievement.md` - 성능 달성 보고서 (0.86ms 거래 실행)
- `report-performance-optimization.md` - 성능 최적화 상세 보고서

### 🔒 **security/** - 보안
보안 가이드 및 안전 체크리스트들
- `guide-security.md` - 전체 보안 가이드
- `guide-live-trading-safety.md` - 실거래 안전 체크리스트

### 📱 **interfaces/** - 사용자 인터페이스
웹 및 텔레그램 인터페이스 관련 문서들
- `feature-binance-style-web-interface.md` - 바이낸스 스타일 웹 인터페이스
- `feature-botfather-style-ui-ux.md` - BotFather 스타일 UI/UX
- `guide-telegram-botfather-features.md` - 텔레그램 봇 기능 가이드

### 📈 **reports/** - 분석 보고서
프로젝트 성과 및 분석 보고서들
- `report-mvp-certification.md` - MVP 인증서
- `report-mvp-completion.md` - MVP 완성 보고서
- `report-cross-validation.md` - 교차검증 보고서
- `report-final-metrics.md` - 최종 메트릭 분석
- `report-botfather-analysis.md` - BotFather 분석 보고서

### 🛠️ **development/** - 개발 도구
개발 과정에서 사용하는 도구 및 임시 문서들
- `development-handoff-prompt.md` - AI 인수인계 프롬프트
- `development-simple-test.md` - 간단한 시스템 테스트
- `development-temp-futures-diagram.md` - 선물 거래 임시 다이어그램

### 📚 **guides/** - 일반 가이드
프로젝트 전반적인 사용 가이드들
- `guide-deployment.md` - 배포 가이드
- `guide-project-setup.md` - 프로젝트 설정 워크플로우
- `guide-troubleshooting.md` - 문제 해결 가이드

### 🗺️ **roadmap/** - 개발 로드맵
프로젝트 계획 및 진행 상황
- `roadmap-detailed-development.md` - 상세 개발 로드맵
- `roadmap-system-development-dashboard.md` - 개발 진행 대시보드
- `roadmap-system-development-gantt.md` - 간트 차트

### 📦 **releases/** - 릴리즈
릴리즈 노트 및 변경 사항
- `release-notes.md` - 릴리즈 노트

## 🎯 **문서 탐색 가이드**

### **🔍 목적별 문서 찾기**

#### **새로운 개발자 온보딩**
1. `core/mvp/MVP 통합 기능명세서.md` - 프로젝트 전체 이해
2. `architecture/design-system-architecture-v2.md` - 시스템 아키텍처
3. `guides/guide-project-setup.md` - 프로젝트 설정
4. `security/guide-security.md` - 보안 가이드

#### **전략 개발자**
1. `strategies/guide-base-strategy-development.md` - 기본 전략 개발
2. `strategies/03_Strategy_Library_and_Implementation.md` - 전략 라이브러리
3. `testing/guide-testing-philosophy.md` - 테스팅 철학
4. `api/api-message-bus.md` - 메시지 버스 API

#### **운영/배포 담당자**
1. `deployment/guide-deployment-workflow.md` - 배포 워크플로우
2. `security/guide-live-trading-safety.md` - 실거래 안전 가이드
3. `monitoring/guide-performance-optimization.md` - 성능 모니터링
4. `guides/guide-troubleshooting.md` - 문제 해결

#### **성능 분석가**
1. `monitoring/report-performance-achievement.md` - 성능 달성 보고서
2. `reports/report-final-metrics.md` - 최종 메트릭 분석
3. `testing/guide-24h-continuous-testing.md` - 연속 테스팅 시스템

## 📏 **문서 작성 규칙**

### **파일명 규칙 (kebab-case)**
- **가이드**: `guide-[기능명].md`
- **보고서**: `report-[주제명].md`
- **API**: `api-[서비스명].md`
- **설계**: `design-[영역명].md`
- **설정**: `setup-[도구명].md`
- **테스트**: `test-[테스트명].md`
- **기능**: `feature-[기능명].md`

### **문서 구조 권장사항**
```markdown
# 제목

## 🎯 목적 및 개요
## 📋 주요 내용
## 🔧 사용법/구현 방법
## 📊 결과/성과 (해당시)
## 🔗 관련 문서 링크
```

## 🔄 **문서 유지보수**

### **새 문서 추가 시**
1. 해당 기능의 디렉토리 확인
2. 적절한 접두사로 파일명 생성
3. 이 README에 항목 추가
4. 관련 문서들과 상호 링크 연결

### **문서 수정 시**
1. 변경 날짜 기록
2. 관련 문서들의 링크 확인
3. CLAUDE.md 경로 업데이트 (필요시)

## 🎉 **문서 품질 기준**

### ✅ **우수한 문서**
- 명확한 목적과 범위
- 실제 코드와 일치하는 내용
- 단계별 설명과 예제
- 관련 문서들과의 연결

### ❌ **개선이 필요한 문서**
- 목적이 불분명
- 오래된 정보
- 코드와 불일치
- 고립된 문서 (링크 없음)

---

## 🚀 **MVP 현황 반영**

현재 문서들은 **Letrade_v1 MVP 96% 완료** 상태를 정확히 반영하고 있습니다:
- ✅ **0.86ms 거래 실행 성능** (목표 대비 233배 빠름)
- ✅ **24시간 연속 테스팅 완료** (99.9% 가용성)
- ✅ **Circuit Breaker 패턴 구현** (안정성 확보)
- ✅ **CCXT 통합** (200+ 거래소 지원)

**이 문서 구조를 통해 프로젝트의 모든 정보를 체계적으로 관리하고 있습니다!** 📚✨