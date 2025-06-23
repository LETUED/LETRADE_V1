# MVP 다이어그램 모음

이 폴더에는 Letrade_v1 MVP 시스템의 주요 다이어그램들이 포함되어 있습니다.

## 📊 다이어그램 목록

### 1. 시스템 아키텍처
- **파일**: `system_architecture.md`
- **타입**: Component/Architecture Diagram
- **설명**: 전체 시스템의 레이어별 구조와 컴포넌트 간의 연결 관계
- **주요 요소**: 
  - User Interface Layer (CLI, Telegram Bot)
  - Application Layer (Core Services, Trading Services, Integration Services)
  - Infrastructure Layer (RabbitMQ, Cloud SQL, Secret Manager)

### 2. 클래스 다이어그램
- **파일**: `class_diagram.md`
- **타입**: UML Class Diagram
- **설명**: MVP 핵심 클래스들의 구조와 관계
- **주요 클래스**:
  - `BaseStrategy` (Abstract) / `MAcrossoverStrategy`
  - `CoreEngine` (Singleton)
  - `CapitalManager` (Singleton)
  - `ExchangeConnector` (Adapter)
  - `StrategyWorker`

### 3. 시퀀스 다이어그램
- **파일**: `sequence_diagram.md`
- **타입**: UML Sequence Diagram
- **설명**: 시스템 시작 및 거래 실행의 시간순 흐름
- **주요 시나리오**:
  - 시스템 초기화 과정
  - 골든 크로스 감지부터 거래 실행까지의 전체 플로우

### 4. 상태 다이어그램
- **파일**: `state_diagram.md`
- **타입**: State Diagram
- **설명**: 시스템, 전략, 주문, 포지션의 상태 전환
- **상태 다이어그램**:
  - 시스템 상태 (SystemOff → Initializing → Running)
  - 전략 상태 (Inactive → Active → Processing)
  - 주문 상태 (Created → Pending → Filled)
  - 포지션 상태 (Opening → Open → Closed)

## 🎯 VS Code에서 다이어그램 보기

### Mermaid Chart Extension 사용법
1. **설치**: VS Code에서 "Mermaid Chart" 확장 설치
2. **미리보기**: 파일을 열면 자동으로 사이드 패널에 다이어그램 표시
3. **편집**: 실시간으로 다이어그램 업데이트 확인
4. **내보내기**: PNG, SVG 형태로 내보내기 가능

### 명령어
- `Cmd+Shift+P` → "MermaidChart: Preview Diagram"
- `Cmd+Shift+P` → "MermaidChart: Create Diagram"

## 🔧 CLI 도구로 이미지 생성

```bash
# PNG 생성
mmdc -i system_architecture.md -o system_architecture.png -t dark

# SVG 생성 (벡터 이미지)
mmdc -i class_diagram.md -o class_diagram.svg -f svg -t dark

# 배치 변환
../../../scripts/convert-diagrams.sh
```

## 📝 다이어그램 활용 방법

1. **개발 가이드**: 구현할 클래스와 메서드 구조 참조
2. **코드 리뷰**: 설계 의도와 구현 방향성 검토
3. **팀 커뮤니케이션**: 시스템 아키텍처 설명
4. **문서화**: README.md나 기술 문서에 이미지 삽입

## 🔄 다이어그램 업데이트

다이어그램은 시스템 구현 진행에 따라 지속적으로 업데이트됩니다:

- **Day 8-9**: 이동평균 교차 전략 구현 시 클래스 다이어그램 업데이트
- **Day 10-11**: Capital Manager 구현 시 시퀀스 다이어그램 상세화
- **Day 12-14**: 전체 거래 플로우 완성 시 상태 다이어그램 검증

## 📚 관련 문서

- [MVP 통합 기능명세서](../MVP%20통합%20기능명세서.md)
- [상세 개발 로드맵](../../roadmap/상세%20개발%20로드맵.md)
- [시스템 아키텍처 설계 문서](../../design-docs/00_System_Overview_and_Architecture.md)