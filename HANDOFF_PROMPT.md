# 🚨 다음 세션 AI 인수인계 프롬프트

## 📋 프로젝트 개요
안녕하세요! **Letrade_v1 자동 암호화폐 거래 시스템** 개발을 이어받습니다.

### 🎯 현재 상황 (Day 8 완료, MVP Week 2 중반)
- **전체 진행률**: 45% (8/30일)
- **마일스톤**: M3 MVP 완성 진행중 (Day 14 목표)
- **테스트 현황**: 87 passed, 3 skipped (CI 파이프라인 정상)
- **코드 커버리지**: 74% (목표 85%)

## 🏗️ 현재 완성된 핵심 구성 요소

### ✅ 완료된 서비스 (80% 구현)
1. **Core Engine** - `src/core_engine/main.py` (80% 완료)
   - 시스템 라이프사이클 관리
   - 백그라운드 태스크 관리
   - 헬스체크 및 모니터링

2. **BaseStrategy** - `src/strategies/base_strategy.py` (95% 완료)
   - 추상 기반 클래스 정의 (ABC 패턴)
   - 성능 추적 (PerformanceTracker)
   - pandas-ta 통합 지원

3. **Capital Manager** - `src/capital_manager/main.py` (85% 완료)
   - 거래 검증 (TradeRequest → ValidationResponse)
   - 리스크 파라미터 관리
   - 포지션 크기 제한

4. **Exchange Connector** - `src/exchange_connector/main.py` (75% 완료)
   - 추상 기반 클래스 정의
   - Mock Exchange 구현 완료
   - 주문 관리 (place, cancel, status)

5. **Message Bus** - `src/common/message_bus.py` (90% 완료)
   - RabbitMQ 연동
   - 토픽 기반 라우팅
   - 발행/구독 패턴

### ✅ 개발 환경 및 CI/CD
- GitHub Actions 파이프라인 완전 작동
- Docker Compose 로컬 환경 구성
- 코드 품질 검사 통과 (Black, isort, flake8)
- 보안 스캔 통과

## 🚀 즉시 시작할 작업 (Day 9 목표)

### 🔴 최우선 (오전 09:00-12:00)
**1. Strategy Worker 프로세스 관리자 구현**
```bash
# 새 파일 생성 필요
src/strategy_worker/main.py
src/strategy_worker/__init__.py
```

구현 내용:
- 프로세스 격리 및 라이프사이클 관리 (start/stop/restart)
- 메모리/CPU 사용량 모니터링
- 헬스체크 및 자동 복구 메커니즘
- BaseStrategy 인스턴스 관리

### 🔴 고우선 (오후 13:00-18:00)
**2. MAcrossoverStrategy 클래스 구현**
```bash
# 새 파일 생성 필요
src/strategies/ma_crossover.py
```

구현 내용:
- BaseStrategy 상속 클래스
- populate_indicators 메서드 (SMA 50/200 계산)
- on_data 메서드 (골든/데스 크로스 신호 생성)
- MVP 명세서 TradingSignal 포맷 준수

### 🟡 중간 우선 (저녁 19:00-21:00)
**3. 테스트 및 검증**
- Strategy Worker 단위 테스트 작성
- MA 전략 백테스트 준비
- 코드 리뷰 및 문서 업데이트

## 📁 중요 파일 및 디렉토리

### 📖 참조해야 할 문서
```bash
docs/mvp/MVP 통합 기능명세서.md  # 요구사항 상세 명세
docs/roadmap/시스템 개발 진행 대시보드.md  # 현재 진행 상황
docs/roadmap/상세 개발 로드맵.md  # 전체 개발 계획
```

### 🔧 설정 파일
```bash
pyproject.toml  # Python 프로젝트 설정, 의존성, 테스트 설정
docker-compose.yml  # 로컬 개발 환경 (PostgreSQL, RabbitMQ, Redis)
.github/workflows/  # CI/CD 파이프라인 (작동 중)
```

### 📝 Todo 리스트
현재 설정된 TODO를 확인하려면:
```python
# TodoRead 도구 사용
```

## ⚠️ 중요 주의사항

### 🔒 보안 및 안전성
- 모든 거래는 dry_run=True로 기본 설정
- API 키나 민감 정보 하드코딩 금지
- GCP Secret Manager 사용 예정

### 🧪 테스트 우선 개발
- 새 코드 작성 시 반드시 단위 테스트 포함
- 현재 74% 커버리지를 85% 이상으로 유지
- CI 파이프라인이 깨지지 않도록 주의

### 📏 코드 스타일
- Black 포맷터 적용 (line-length: 88)
- Type hints 필수
- Docstrings 작성 (Google style)
- BaseStrategy 인터페이스 준수

## 🎯 Day 9 완료 기준

### ✅ 성공 지표
- [ ] Strategy Worker 프로세스 관리 완성
- [ ] MA Crossover 전략 완전 구현
- [ ] 모든 테스트 통과 (87+ passed)
- [ ] 코드 커버리지 74% 이상 유지
- [ ] BaseStrategy 인터페이스 100% 준수

### 📊 검증 방법
```bash
# 테스트 실행
python -m pytest tests/ -v --cov=src --cov-report=html

# 코드 품질 검사
black --check src/ tests/
isort --check-only src/ tests/
flake8 src/ tests/ --max-line-length=88 --extend-ignore=E203,W503
```

## 🔄 다음 단계 예고 (Day 10-14)

### Week 2 완성 로드맵
- **Day 10**: Core Engine ↔ Strategy Worker 통합
- **Day 11**: Capital Manager ↔ Exchange Connector 통합  
- **Day 12**: 데이터베이스 ORM 모델 및 상태 영속성
- **Day 13**: Telegram Bot 인터페이스
- **Day 14**: 24시간 드라이런 및 MVP 완성

## 🚀 시작 명령어

```bash
# 환경 확인
cd /Users/jeondonghwan/Letrade_v1
git status
python -m pytest tests/ -v  # 현재 테스트 상태 확인

# Todo 리스트 확인
# TodoRead 도구 사용

# Day 9 작업 시작
# 1. src/strategy_worker/main.py 구현부터 시작
# 2. Strategy Worker 프로세스 관리자 개발
```

---

## 💬 추가 정보

프로젝트는 **금융 시스템의 안전성을 최우선**으로 하며, **V-Model 방법론**을 따라 개발 중입니다. 

현재까지의 성과:
- ✅ 전문적인 마이크로서비스 아키텍처 구축
- ✅ 완전 자동화된 CI/CD 파이프라인
- ✅ 높은 코드 품질 (기술 부채 2.1일, 복잡도 3.2)
- ✅ 우수한 성능 (레이턴시 175ms < 200ms 목표)

**Strategy Worker가 전체 시스템의 핵심 누락 부분**이므로, 이를 우선 완성하면 MVP의 90%가 완료됩니다!

화이팅! 🚀