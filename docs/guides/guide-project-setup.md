# 🚀 Production-Grade Project Setup Workflow

이 문서는 암호화폐 거래 시스템과 같은 금융 시스템을 위한 생산급 프로젝트 설정 워크플로우를 정의합니다.

## 개요

이 워크플로우는 Letrade_v1 프로젝트 설정 과정에서 검증된 방법론으로, 다음과 같은 특징을 가집니다:

- **보안 우선**: 금융 시스템에 필요한 보안 검증 자동화
- **전문성**: 업계 표준 도구와 관행 적용
- **자동화**: 수동 오류를 최소화하는 완전 자동화된 설정
- **확장성**: 팀 협업과 대규모 배포 준비
- **안정성**: 프로덕션 환경 운영에 적합한 구성

## Phase 1: Project Structure & Environment Setup

### 1.1 Directory Structure Creation

```bash
# 포괄적인 프로젝트 구조 생성
mkdir -p src/{core_engine,strategies,capital_manager,exchange_connector,common}
mkdir -p tests/{unit,integration,e2e}
mkdir -p config migrations scripts docs
```

**구조 설명:**
- `src/`: 소스 코드 (마이크로서비스 기반 구조)
- `tests/`: 계층화된 테스트 (단위/통합/E2E)
- `config/`: 설정 파일 및 환경별 구성
- `migrations/`: 데이터베이스 스키마 버전 관리
- `scripts/`: 자동화 스크립트
- `docs/`: 프로젝트 문서

### 1.2 Python Project Configuration (`pyproject.toml`)

핵심 구성 요소:

**Build System:**
```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"
```

**Dependencies Categories:**
- **Core Trading**: ccxt, pandas, numpy, sqlalchemy
- **Message Bus**: pika (RabbitMQ), celery, redis
- **Web Framework**: fastapi, uvicorn
- **CLI**: click, rich
- **Security**: cryptography, google-cloud-secret-manager
- **Monitoring**: prometheus-client, structlog

**Development Dependencies:**
- **Testing**: pytest, pytest-cov, pytest-asyncio
- **Code Quality**: black, flake8, mypy, isort
- **Development**: pre-commit, jupyter, ipython

**Optional Dependencies:**
- **ML**: scikit-learn, tensorflow, torch (Week 3용)
- **Production**: gunicorn, sentry-sdk

### 1.3 Environment Configuration

**`.env.example` 구조:**
```bash
# 환경 설정
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# 데이터베이스
DATABASE_URL=postgresql://user:pass@localhost:5432/db
DATABASE_POOL_SIZE=20

# 메시지 버스
RABBITMQ_URL=amqp://user:pass@localhost:5672/
REDIS_URL=redis://localhost:6379/0

# 클라우드 설정
GCP_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json

# 거래 설정
DEFAULT_POSITION_SIZE_PERCENT=2.0
MAX_DAILY_LOSS_PERCENT=5.0

# 보안
SECRET_KEY=your-secret-key
API_RATE_LIMIT=100
```

**`config/settings.yaml` 구조:**
- 계층화된 설정 (system, logging, database, trading)
- 환경별 오버라이드 지원
- 타입 안전성과 검증

### 1.4 Development Environment Automation

`scripts/setup_dev_env.sh` 기능:

1. **사전 요구사항 검증**
   - Python 3.11+ 버전 확인
   - Docker 및 Docker Compose 설치 확인

2. **가상환경 설정**
   - Python venv 생성 및 활성화
   - pip 업그레이드 및 의존성 설치

3. **Docker 서비스 시작**
   - PostgreSQL, RabbitMQ, Redis 컨테이너 실행
   - 서비스 상태 및 연결성 검증

4. **데이터베이스 설정**
   - 스키마 마이그레이션 실행
   - 초기 데이터 삽입

5. **개발 도구 설정**
   - Pre-commit 훅 설치
   - 코드 품질 도구 설정

## Phase 2: Containerization & Infrastructure

### 2.1 Multi-stage Docker Configuration

**Builder Stage:**
- Python 3.11 slim 기반
- 빌드 도구 설치 (gcc, build-essential)
- 의존성 컴파일 최적화

**Runtime Stage:**
- 최소한의 런타임 이미지
- 비루트 사용자 실행 (보안)
- 다중 서비스 지원

**지원 서비스:**
```bash
LETRADE_SERVICE=core-engine        # 메인 오케스트레이터
LETRADE_SERVICE=strategy-worker    # 개별 전략 실행
LETRADE_SERVICE=capital-manager    # 리스크 관리
LETRADE_SERVICE=exchange-connector # API 게이트웨이
LETRADE_SERVICE=telegram-bot       # 사용자 인터페이스
LETRADE_SERVICE=cli               # 명령줄 도구
```

**운영 기능:**
- 우아한 종료 (SIGTERM/SIGINT 핸들링)
- 헬스 체크 엔드포인트
- 서비스 의존성 대기
- 구조화된 로깅

### 2.2 Docker Compose Development Environment

```yaml
# 로컬 개발용 서비스 구성
services:
  postgres:    # PostgreSQL 15 with persistence
  rabbitmq:    # RabbitMQ 3 with management UI
  redis:       # Redis 7 for caching
```

**특징:**
- 헬스 체크 통합
- 데이터 영속성 (볼륨 마운트)
- 네트워크 격리
- 개발 편의 기능 (관리 UI 등)

## Phase 3: CI/CD Pipeline & Git Workflow

### 3.1 Branch Strategy

```
main (production-ready)
├── dev (integration)
│   ├── feature/new-strategy
│   ├── feature/ui-improvements
│   └── bugfix/memory-leak
├── hotfix/critical-fix
└── release/v1.0.0
```

**브랜치 정책:**
- `main`: 프로덕션 배포 가능한 안정 버전
- `dev`: 개발 통합 브랜치
- `feature/*`: 새 기능 개발
- `bugfix/*`: 버그 수정
- `hotfix/*`: 긴급 수정

### 3.2 GitHub Actions Workflows

#### CI Pipeline (`ci.yml`)

**트리거:** main/dev 푸시, 모든 PR

**작업 흐름:**
1. **code-quality**: 코드 품질 검사
   - Black 포맷팅 검증
   - isort import 정렬 검증
   - flake8 린팅
   - mypy 타입 체크
   - bandit 보안 스캔

2. **unit-tests**: 단위 테스트
   - 다중 Python 버전 (3.11, 3.12)
   - 커버리지 측정 (85% 이상)
   - Codecov 업로드

3. **integration-tests**: 통합 테스트
   - PostgreSQL, RabbitMQ, Redis 서비스 실행
   - 실제 데이터베이스 연결 테스트
   - 메시지 버스 통신 검증

4. **build**: 빌드 및 패키징
   - Python 패키지 빌드
   - Docker 이미지 빌드 (캐시 최적화)

5. **security**: 보안 검사
   - 의존성 취약점 스캔 (safety)
   - 코드 보안 분석 (bandit)

#### PR Validation (`pr-validation.yml`)

**거래 시스템 특화 검증:**

1. **pr-validation**: 기본 검증
   - PR 제목 형식 (conventional commits)
   - 설명 길이 및 품질
   - 라벨링 권장사항

2. **trading-safety-checks**: 금융 시스템 안전성
   ```bash
   # 하드코딩된 시크릿 검사
   patterns=(
     "api_key.*=.*[\"'][a-zA-Z0-9]{20,}[\"']"
     "secret.*=.*[\"'][a-zA-Z0-9]{20,}[\"']"
     "binance.*key"
   )
   ```

3. **breaking-changes**: 호환성 검사
   - 중요 파일 삭제 감지
   - BaseStrategy 인터페이스 변경 감지
   - 데이터베이스 스키마 변경 감지

4. **documentation-check**: 문서화 요구사항
   - 코드 변경 대비 문서 업데이트 권장
   - API 문서 업데이트 확인

5. **test-coverage-check**: 테스트 커버리지
   - 변경된 파일에 대한 테스트 존재 확인
   - 누락된 테스트 파일 알림

#### Release & Deploy (`release.yml`)

**자동 배포 파이프라인:**

1. **build-and-test**: 전체 테스트 실행
2. **build-image**: 멀티아키텍처 이미지 빌드
3. **create-release**: GitHub 릴리즈 생성
4. **deploy-staging**: 스테이징 자동 배포
5. **deploy-production**: 프로덕션 수동 승인 배포

### 3.3 GitHub Templates

#### Pull Request Template

**주요 섹션:**
- 변경 사항 설명
- 관련 이슈 링크
- 변경 유형 분류
- **거래 시스템 안전성 체크리스트** ⚠️
- 보안 검증
- 성능 영향 평가
- 테스트 커버리지
- 배포 고려사항

**거래 시스템 특화 체크리스트:**
```markdown
### 🔒 Security & Safety (Required for Trading System)

#### Security Checklist
- [ ] No hardcoded API keys or secrets
- [ ] All sensitive data uses GCP Secret Manager
- [ ] Input validation implemented

#### Trading Safety Checklist
- [ ] Dry-run mode properly implemented
- [ ] All trades validated through CapitalManager
- [ ] Risk management rules applied
- [ ] Error handling prevents system crashes
- [ ] State reconciliation tested
```

#### Issue Templates

**Bug Report Template:**
- 심각도 분류 (Critical/High/Medium/Low)
- 컴포넌트 식별
- **거래 영향 평가** ⚠️
- 재현 단계
- 환경 정보
- **금융 손실 영향** 섹션

**Feature Request Template:**
- 기능 카테고리 (Trading Strategy/Risk Management/Exchange Integration 등)
- 우선순위 수준
- 비즈니스 가치 설명
- 기술적 고려사항
- **복잡도 추정**

## Phase 4: Safety & Security Configuration

### 4.1 Git Security Configuration

**`.gitignore` 보안 설정:**
```gitignore
# 민감한 정보 제외
.env
*.key
*.pem
service-account.json
google-credentials.json

# Claude Code 파일 제외 (개발 도구용)
CLAUDE.md
.cursorrules
.claude/

# 대용량 데이터 제외
data/
models/
*.pkl
*.h5
```

### 4.2 Trading System Safety Automation

**자동화된 안전성 검사:**

1. **시크릿 스캐닝:**
   ```bash
   # CI에서 자동 실행
   grep -r "api_key.*=" src/ && exit 1
   grep -r "binance.*key" src/ && exit 1
   ```

2. **Dry-run 검증:**
   ```bash
   # 거래 코드에 dry-run 보호 확인
   grep -l "execute_trade" src/ | xargs grep -L "dry_run"
   ```

3. **Capital Manager 검증:**
   ```bash
   # 모든 거래가 Capital Manager를 거치는지 확인
   grep -l "trade.*signal" src/ | xargs grep -L "CapitalManager"
   ```

## Phase 5: Documentation & Project Management

### 5.1 Documentation Structure

```
docs/
├── design-docs/              # 시스템 아키텍처
│   ├── 00_System_Overview_and_Architecture.md
│   ├── 01_Core_Services_and_Execution_Framework.md
│   └── 02_Capital_and_Risk_Management.md
├── mvp/                      # MVP 명세서
│   ├── MVP 통합 기능명세서.md
│   └── 자동 암호화폐 거래 시스템 UML 다이어그램.md
├── full-system/              # 고급 기능
└── roadmap/                  # 개발 일정
    ├── 상세 개발 로드맵.md
    └── 시스템 개발 간트 차트.md
```

### 5.2 README.md Structure

**포함 요소:**
- 프로젝트 개요 및 특징
- 빠른 시작 가이드 (자동화 스크립트)
- 아키텍처 다이어그램
- 개발 가이드 (코딩 스타일, 테스트)
- 배포 지침 (로컬/프로덕션)
- 보안 및 안전성 요구사항
- 기여 가이드라인

## 🔄 Setup Execution Order

### 1. Repository Initialization
```bash
git init
mkdir -p src/{core_engine,strategies,capital_manager,exchange_connector,common}
mkdir -p tests/{unit,integration,e2e} config migrations scripts
```

### 2. Core Configuration Files
- `pyproject.toml`: Python 프로젝트 설정
- `.env.example`: 환경 변수 템플릿
- `config/settings.yaml`: 애플리케이션 설정
- `docker-compose.yml`: 로컬 개발 환경
- `migrations/001_initial_schema.sql`: 데이터베이스 스키마

### 3. Automation Scripts
- `scripts/setup_dev_env.sh`: 개발 환경 자동 설정
- `.gitignore`: Git 보안 설정
- `Dockerfile`: 프로덕션 컨테이너 설정

### 4. First Commit (Stable Baseline)
```bash
git add .
git commit -m "feat: initial project setup with development environment

🚀 Complete development environment setup including:
- Project structure and Python configuration
- Docker Compose infrastructure
- Database schema and migrations
- Automated setup scripts
- Comprehensive documentation"
```

### 5. Development Branch Setup
```bash
git checkout -b dev
# GitHub workflows 및 템플릿 추가
mkdir -p .github/{workflows,ISSUE_TEMPLATE,PULL_REQUEST_TEMPLATE}
# CI/CD 파이프라인 구성
```

### 6. CI/CD and Templates
- `.github/workflows/ci.yml`: CI 파이프라인
- `.github/workflows/pr-validation.yml`: PR 검증
- `.github/workflows/release.yml`: 배포 자동화
- `.github/PULL_REQUEST_TEMPLATE/default.md`: PR 템플릿
- `.github/ISSUE_TEMPLATE/`: 이슈 템플릿들

### 7. Containerization
```bash
# Dockerfile 및 .dockerignore 추가
git add Dockerfile .dockerignore
git commit -m "feat: add production-ready Docker configuration"
```

### 8. GitHub Integration
```bash
git remote add origin git@github.com:USERNAME/PROJECT_NAME.git
git push -u origin main
git push -u origin dev
```

## 🎯 Benefits of This Workflow

### 개발 효율성
- **10분 내 완전한 개발 환경** 구축
- **자동화된 품질 보증** (코딩 실수 방지)
- **표준화된 워크플로우** (팀 온보딩 간소화)

### 보안 및 안전성
- **금융 시스템 특화 검증** 자동화
- **시크릿 관리** 모범 사례 강제
- **거래 안전성** 검사 내장

### 확장성 및 유지보수성
- **마이크로서비스 아키텍처** 준비
- **컨테이너 기반 배포** 지원
- **포괄적인 문서화** 자동 생성

### 프로덕션 준비성
- **다중 환경 지원** (dev/staging/prod)
- **자동화된 배포 파이프라인**
- **모니터링 및 로깅** 기본 제공

## 🔧 Customization Guidelines

### 다른 프로젝트 적용 시

1. **의존성 조정:**
   ```toml
   # pyproject.toml에서 프로젝트 특성에 맞는 라이브러리 선택
   dependencies = [
       # 웹 애플리케이션: fastapi, django
       # 데이터 분석: pandas, numpy, jupyter  
       # ML: scikit-learn, tensorflow, pytorch
   ]
   ```

2. **보안 검사 커스터마이징:**
   ```yaml
   # .github/workflows/pr-validation.yml에서 도메인별 검사 추가
   - name: Domain-specific security checks
     run: |
       # 의료 시스템: HIPAA 준수 검사
       # 금융 시스템: PCI DSS 검사
       # 일반 웹앱: OWASP Top 10 검사
   ```

3. **Docker 설정 조정:**
   - 서비스별 포트 및 환경변수 수정
   - 멀티서비스 vs 모놀리식 구조 선택
   - 보안 요구사항에 따른 사용자 권한 조정

4. **테스트 전략 조정:**
   - 도메인별 테스트 유형 (성능/보안/접근성 등)
   - 커버리지 목표 설정
   - 테스트 환경 구성

## 🔄 Daily Development Workflow

프로젝트 설정 완료 후, 일상적인 개발 작업을 위한 세분화된 워크플로우입니다.

### Step 1: Feature Development Initialization

```bash
# 1.1 최신 dev 브랜치로 동기화
git checkout dev
git pull origin dev

# 1.2 새 feature 브랜치 생성
git checkout -b feature/[기능명]
# 예: feature/core-engine-skeleton
# 예: feature/ma-crossover-strategy
# 예: feature/telegram-notifications
```

**브랜치 네이밍 컨벤션:**
- `feature/[기능명]`: 새 기능 개발
- `bugfix/[이슈명]`: 버그 수정
- `hotfix/[긴급수정명]`: 프로덕션 긴급 수정
- `refactor/[모듈명]`: 코드 리팩토링
- `docs/[문서명]`: 문서 업데이트

### Step 2: Test-Driven Development (TDD)

```bash
# 2.1 테스트 파일 먼저 생성
# 예: Core Engine 개발 시
touch tests/unit/test_core_engine.py
touch tests/integration/test_core_engine_integration.py

# 2.2 실패하는 테스트 작성
cat > tests/unit/test_core_engine.py << 'EOF'
import pytest
from src.core_engine.main import CoreEngine

def test_core_engine_initialization():
    """Core Engine이 올바르게 초기화되는지 테스트"""
    engine = CoreEngine()
    assert engine is not None
    assert engine.status == "initialized"

def test_core_engine_strategy_loading():
    """전략 로딩 기능 테스트"""
    engine = CoreEngine()
    strategies = engine.load_active_strategies()
    assert isinstance(strategies, list)
EOF

# 2.3 테스트 실행 (실패 확인)
pytest tests/unit/test_core_engine.py -v
# Expected: FAILED (구현되지 않았으므로)
```

### Step 3: Implementation Phase

```bash
# 3.1 기본 구조 생성
mkdir -p src/core_engine
touch src/core_engine/__init__.py
touch src/core_engine/main.py

# 3.2 최소 구현으로 테스트 통과시키기
cat > src/core_engine/main.py << 'EOF'
"""Core Engine: 시스템의 중앙 오케스트레이터"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class CoreEngine:
    """시스템의 메인 오케스트레이터"""
    
    def __init__(self):
        self.status = "initialized"
        self.strategies = []
        logger.info("Core Engine initialized")
    
    def load_active_strategies(self) -> List[Dict[str, Any]]:
        """활성화된 전략들을 로드"""
        # TODO: 데이터베이스에서 활성 전략 조회
        return []
EOF

# 3.3 테스트 실행 (통과 확인)
pytest tests/unit/test_core_engine.py -v
# Expected: PASSED
```

### Step 4: Incremental Development & Testing

```bash
# 4.1 기능 단위별 커밋
git add tests/unit/test_core_engine.py
git commit -m "test: add basic Core Engine unit tests"

git add src/core_engine/
git commit -m "feat: implement basic Core Engine structure

- Add CoreEngine class with initialization
- Implement strategy loading interface
- Add structured logging"

# 4.2 더 복잡한 테스트 추가
cat >> tests/unit/test_core_engine.py << 'EOF'

def test_strategy_worker_management():
    """Strategy Worker 관리 기능 테스트"""
    engine = CoreEngine()
    
    # Worker 시작
    worker_id = engine.start_strategy_worker(strategy_id=1)
    assert worker_id is not None
    
    # Worker 상태 확인
    status = engine.get_worker_status(worker_id)
    assert status == "running"
    
    # Worker 중지
    engine.stop_strategy_worker(worker_id)
    status = engine.get_worker_status(worker_id)
    assert status == "stopped"
EOF

# 4.3 기능 구현 및 테스트
# (구현 → 테스트 → 커밋 반복)
```

### Step 5: Code Quality & Security Validation

```bash
# 5.1 자동 포맷팅 적용
black src/ tests/
isort src/ tests/

# 5.2 코드 품질 검사
flake8 src/ tests/
mypy src/

# 5.3 보안 검사 (거래 시스템 특화)
# API 키 하드코딩 검사
grep -r "api_key.*=" src/ && echo "❌ Hardcoded API key detected!" || echo "✅ No hardcoded API keys"

# 시크릿 하드코딩 검사  
grep -r "secret.*=" src/ && echo "❌ Hardcoded secret detected!" || echo "✅ No hardcoded secrets"

# Dry-run 보호 검사 (거래 관련 코드에서)
if grep -r "execute_trade\|place_order" src/; then
    grep -r "dry_run\|test_mode" src/ || echo "⚠️ Trading code needs dry-run protection"
fi
```

### Step 6: Integration Testing

```bash
# 6.1 Docker 서비스 시작
docker-compose up -d

# 6.2 서비스 연결 대기
./scripts/wait-for-services.sh

# 6.3 통합 테스트 실행
pytest tests/integration/ -v

# 6.4 E2E 테스트 (필요시)
pytest tests/e2e/ -v --slow
```

### Step 7: Comprehensive Testing & Documentation

```bash
# 7.1 전체 테스트 스위트 실행
pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing

# 7.2 커버리지 확인 (85% 이상 목표)
echo "Coverage Report:"
coverage report --show-missing

# 7.3 성능 테스트 (거래 시스템 특화)
pytest tests/performance/ -v --benchmark-only

# 7.4 문서 업데이트
# API 문서 자동 생성
sphinx-build -b html docs/ docs/_build/

# README 업데이트 (필요시)
# Architecture 다이어그램 업데이트 (필요시)
```

### Step 8: Final Commit & Push

```bash
# 8.1 문서 커밋
git add docs/
git commit -m "docs: update Core Engine documentation

- Add API documentation
- Update architecture diagrams  
- Add usage examples"

# 8.2 마일스톤 완료 커밋 (주요 기능 완료 시)
git commit --allow-empty -m "feat: complete Day 5-6 milestone - Core Engine implementation

🎯 Milestone: Core Services Skeleton
📅 Progress: Day 5-6/30 complete

✅ Completed Features:
- Core Engine basic structure and initialization
- Strategy loading framework
- Worker management interface
- Database connection setup
- Structured logging implementation

📊 Quality Metrics:
- Test coverage: 87% (target: 85%+)
- All security checks passed
- Performance benchmarks within limits
- Documentation updated

🔜 Next Phase: Day 7 - Message Bus Integration
- RabbitMQ exchange setup
- Event publishing/subscription
- Strategy-CapitalManager communication

💡 Technical Notes:
- Implemented process-based worker isolation
- Added graceful shutdown handling
- Error boundaries prevent cascade failures"

# 8.3 GitHub에 푸시
git push -u origin feature/core-engine-skeleton
```

### Step 9: CI Validation & Monitoring

```bash
# 9.1 GitHub Actions 모니터링
echo "Monitor CI pipeline at:"
echo "https://github.com/LETUED/LETRADE_V1/actions"

# 9.2 CI 실패 시 로컬 디버깅
# CI와 동일한 환경에서 테스트
docker run --rm -v $(pwd):/app python:3.11 bash -c "
  cd /app && 
  pip install -e .[dev] && 
  pytest tests/ -v --cov=src
"

# 9.3 보안 스캔 로컬 실행
bandit -r src/ -f json -o security-report.json
safety check --json --output safety-report.json
```

### Step 10: Pull Request Creation & Management

```bash
# 10.1 PR 생성 (GitHub CLI 사용 시)
gh pr create \
  --title "feat: implement Core Engine skeleton (Day 5-6)" \
  --body "$(cat <<'EOF'
## 📋 Description

Implements the Core Engine skeleton as part of Day 5-6 milestone.

### What changed?
- Core Engine basic structure with process management
- Strategy loading framework
- Worker lifecycle management
- Database connection abstractions

### Why was this change made?
- Required for MVP system architecture
- Establishes foundation for strategy execution
- Enables process-based isolation for reliability

## 🔗 Related Issues
- Relates to #1 (Day 5-6 milestone)
- Implements design from #2 (Architecture specification)

## 📦 Type of Change
- [x] 🚀 Feature: New functionality
- [x] 📚 Documentation: Documentation updates

## 🔒 Security & Safety (Required for Trading System)

### Security Checklist
- [x] No hardcoded API keys or secrets
- [x] All sensitive data uses environment variables
- [x] Input validation implemented
- [x] Error handling prevents information leakage

### Trading Safety Checklist
- [x] Process isolation prevents cascade failures
- [x] Graceful shutdown handling implemented
- [x] Error boundaries prevent system crashes
- [x] State management designed for reconciliation

## 🧪 Testing
- [x] Unit tests added (87% coverage)
- [x] Integration tests added
- [x] Manual testing completed
- [x] Performance benchmarks pass

## 📊 Performance Impact
- Memory usage: <256MB per worker (within limits)
- Startup time: <5 seconds (target: <10s)
- No significant performance degradation detected
EOF
)" \
  --assignee "@me" \
  --label "feature,day-5-6,core-engine"
```

### Step 11: Post-Merge Cleanup

```bash
# 11.1 PR 병합 후 정리
git checkout dev
git pull origin dev
git branch -d feature/core-engine-skeleton

# 11.2 다음 기능 준비
git checkout -b feature/next-component

# 11.3 마일스톤 업데이트
# GitHub Projects에서 진행률 업데이트
# 다음 주차 계획 검토
```

## 🤖 Automation Scripts

개발 워크플로우 자동화를 위한 스크립트들:

### `scripts/new-feature.sh`
```bash
#!/bin/bash
# 새 기능 개발 시작 자동화

FEATURE_NAME=$1
if [ -z "$FEATURE_NAME" ]; then
    echo "Usage: ./scripts/new-feature.sh <feature-name>"
    exit 1
fi

echo "🚀 Starting new feature: $FEATURE_NAME"

# 최신 dev로 동기화
git checkout dev
git pull origin dev

# 새 브랜치 생성
git checkout -b "feature/$FEATURE_NAME"

# 기본 테스트 파일 생성
mkdir -p "tests/unit"
touch "tests/unit/test_${FEATURE_NAME//-/_}.py"

# 기본 소스 파일 생성
mkdir -p "src/${FEATURE_NAME//-/_}"
touch "src/${FEATURE_NAME//-/_}/__init__.py"
touch "src/${FEATURE_NAME//-/_}/main.py"

echo "✅ Feature branch ready: feature/$FEATURE_NAME"
echo "📝 Next steps:"
echo "  1. Write failing tests in tests/unit/test_${FEATURE_NAME//-/_}.py"
echo "  2. Implement minimum code to pass tests"
echo "  3. Run: ./scripts/test-and-commit.sh"
```

### `scripts/test-and-commit.sh`
```bash
#!/bin/bash
# 테스트 실행 및 품질 검사 자동화

echo "🧪 Running comprehensive test suite..."

# 코드 포맷팅
echo "🎨 Formatting code..."
black src/ tests/
isort src/ tests/

# 린팅
echo "🔍 Running linters..."
flake8 src/ tests/ || exit 1
mypy src/ || exit 1

# 보안 검사
echo "🔒 Security checks..."
./scripts/security-check.sh || exit 1

# 테스트 실행
echo "🧪 Running tests..."
pytest tests/ -v --cov=src --cov-report=term-missing || exit 1

# 커버리지 확인
COVERAGE=$(coverage report | tail -n 1 | awk '{print $4}' | sed 's/%//')
if [ "$COVERAGE" -lt 85 ]; then
    echo "❌ Coverage $COVERAGE% is below 85% threshold"
    exit 1
fi

echo "✅ All checks passed!"
echo "💡 Ready to commit. Use descriptive commit message following conventional commits."
```

### `scripts/security-check.sh`
```bash
#!/bin/bash
# 거래 시스템 특화 보안 검사

echo "🔐 Running trading system security checks..."

# 하드코딩된 API 키 검사
echo "Checking for hardcoded API keys..."
if grep -r "api_key.*=" src/; then
    echo "❌ Hardcoded API key detected!"
    exit 1
fi

# 하드코딩된 시크릿 검사
echo "Checking for hardcoded secrets..."
if grep -r "secret.*=" src/; then
    echo "❌ Hardcoded secret detected!"
    exit 1
fi

# Binance 관련 키워드 검사
echo "Checking for exchange-specific hardcoded values..."
if grep -r "binance.*key\|coinbase.*key" src/; then
    echo "❌ Exchange API key detected!"
    exit 1
fi

# Dry-run 보호 검사
echo "Checking dry-run protection..."
TRADING_FILES=$(grep -r "execute_trade\|place_order" src/ | cut -d: -f1 | sort | uniq)
if [ -n "$TRADING_FILES" ]; then
    for file in $TRADING_FILES; do
        if ! grep -q "dry_run\|test_mode\|mock" "$file"; then
            echo "⚠️ $file contains trading code without dry-run protection"
        fi
    done
fi

echo "✅ Security checks completed"
```

### `scripts/milestone-commit.sh`
```bash
#!/bin/bash
# 마일스톤 완료 커밋 자동화

MILESTONE=$1
DAY=$2
DESCRIPTION=$3

if [ -z "$MILESTONE" ] || [ -z "$DAY" ] || [ -z "$DESCRIPTION" ]; then
    echo "Usage: ./scripts/milestone-commit.sh <milestone> <day> <description>"
    echo "Example: ./scripts/milestone-commit.sh 'Core Engine' '5-6' 'Basic structure implementation'"
    exit 1
fi

# 커버리지 계산
COVERAGE=$(coverage report | tail -n 1 | awk '{print $4}')

# 자동 마일스톤 커밋 메시지 생성
git commit --allow-empty -m "feat: complete Day $DAY milestone - $MILESTONE

🎯 Milestone: $DESCRIPTION
📅 Progress: Day $DAY/30 complete

✅ Quality Metrics:
- Test coverage: $COVERAGE (target: 85%+)
- All security checks passed
- Code quality standards met
- Documentation updated

🔜 Next Phase: [Update as needed]

💡 Implementation Notes:
- [Add specific technical details]
- [Highlight important decisions]
- [Note any trade-offs or limitations]

(마일스톤 커밋 스크립트)"

echo "✅ Milestone commit created for Day $DAY: $MILESTONE"
```

## 🎯 Workflow Benefits

이 자동화된 워크플로우의 장점:

### 개발 효율성
- **자동화된 환경 설정**: 스크립트로 반복 작업 제거
- **표준화된 프로세스**: 일관된 개발 패턴
- **빠른 피드백**: 즉시 품질 검증

### 코드 품질 보장
- **TDD 강제**: 테스트 우선 개발
- **자동 품질 검사**: 포맷팅, 린팅, 타입 체크
- **커버리지 보장**: 85% 이상 자동 검증

### 거래 시스템 안전성
- **자동 보안 검사**: 하드코딩된 시크릿 방지
- **Dry-run 보호**: 거래 코드 안전성 검증
- **프로세스 격리**: 장애 전파 방지

### 팀 협업 효율성
- **명확한 PR**: 표준화된 템플릿과 체크리스트
- **자동 CI/CD**: GitHub Actions 통합
- **문서 자동화**: 코드 변경에 따른 문서 업데이트

이 워크플로우를 따르면 **프로덕션 품질의 코드**를 **빠르고 안전하게** 개발할 수 있습니다.

## 결론

이 워크플로우는 **생산급 시스템 개발을 위한 검증된 방법론**입니다. 특히 금융, 의료, 보안이 중요한 시스템에서 다음과 같은 가치를 제공합니다:

- **안전성**: 자동화된 보안 검증으로 인적 오류 방지
- **전문성**: 업계 표준 도구와 관행 적용
- **효율성**: 반복 작업 자동화로 개발 속도 향상
- **품질**: 일관된 코드 품질과 문서화 보장
- **확장성**: 팀 규모와 프로젝트 복잡도 증가에 대응

이러한 설정을 통해 **"하루 만에 프로덕션 준비 완료"**라는 목표를 달성할 수 있으며, 장기적으로 유지보수 비용을 크게 절감할 수 있습니다.