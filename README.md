# Letrade_v1 - 자동 암호화폐 거래 시스템

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Letrade_v1은 생산급 자동 암호화폐 거래 시스템으로, 마이크로서비스 아키텍처 기반의 안정적이고 확장 가능한 솔루션입니다.

## 🎯 주요 특징

- **🏗️ 마이크로서비스 아키텍처**: RabbitMQ 메시지 버스 기반
- **☁️ 클라우드 네이티브**: Google Cloud Platform 완벽 지원
- **🔒 보안 우선**: GCP Secret Manager 통합
- **📊 실시간 모니터링**: Prometheus + Grafana
- **🔄 자동 복구**: 장애 감지 및 자동 재시작
- **📱 원격 제어**: 텔레그램 봇 인터페이스
- **🧪 테스트 기반**: 85%+ 코드 커버리지

## 🚀 빠른 시작

### 사전 요구사항

- Python 3.11+
- Docker & Docker Compose
- Git

### 1️⃣ 프로젝트 클론

```bash
git clone https://github.com/your-org/letrade_v1.git
cd letrade_v1
```

### 2️⃣ 개발 환경 설정

```bash
# 자동 설정 스크립트 실행
./scripts/setup_dev_env.sh
```

이 스크립트는 다음을 자동으로 수행합니다:
- Python 가상환경 생성 및 활성화
- 의존성 패키지 설치
- Docker 서비스 시작 (PostgreSQL, RabbitMQ, Redis)
- 데이터베이스 마이그레이션
- Pre-commit 훅 설정

### 3️⃣ 환경 변수 설정

```bash
# .env 파일 수정
cp .env.example .env
# 실제 API 키와 설정 값들로 수정
vi .env
```

### 4️⃣ 시스템 시작

```bash
# 가상환경 활성화
source venv/bin/activate

# Core Engine 시작
python -m src.core_engine.main

# 별도 터미널에서 CLI 사용
bot-cli status
```

## 📁 프로젝트 구조

```
letrade_v1/
├── src/                        # 소스 코드
│   ├── core_engine/           # 메인 오케스트레이터
│   ├── strategies/            # 거래 전략들
│   ├── capital_manager/       # 리스크 및 자본 관리
│   ├── exchange_connector/    # 거래소 API 연동
│   └── common/               # 공통 유틸리티
├── tests/                     # 테스트 코드
│   ├── unit/                 # 단위 테스트
│   ├── integration/          # 통합 테스트
│   └── e2e/                  # End-to-End 테스트
├── docs/                      # 문서
├── config/                    # 설정 파일
├── migrations/               # 데이터베이스 마이그레이션
├── scripts/                  # 유틸리티 스크립트
└── docker-compose.yml        # 로컬 개발 환경
```

## 🏗️ 아키텍처

### 시스템 구성 요소

```mermaid
graph TD
    A[CLI/Telegram] --> B[Core Engine]
    B --> C[Strategy Workers]
    B --> D[Capital Manager]
    B --> E[Exchange Connector]
    
    C --> F[RabbitMQ]
    D --> F
    E --> F
    
    F --> G[PostgreSQL]
    F --> H[Redis]
    
    E --> I[Binance API]
    E --> J[Other Exchanges]
```

### 핵심 서비스

- **Core Engine**: 시스템 오케스트레이터 및 모니터링
- **Strategy Workers**: 개별 거래 전략 실행 (프로세스 격리)
- **Capital Manager**: 리스크 관리 및 자본 할당
- **Exchange Connector**: 거래소 API 통신 및 추상화

## 📊 거래 전략

### 현재 지원하는 전략

1. **이동평균 교차 (MA Crossover)**
   - 단기/장기 이동평균 교차 신호
   - 골든 크로스 / 데스 크로스

2. **평균회귀 (Mean Reversion)**
   - 볼린저 밴드 기반
   - RSI 오버바이/오버셀

### 새 전략 추가

```python
from src.strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    def populate_indicators(self, dataframe):
        # 기술 지표 계산
        return dataframe
    
    def on_data(self, data, dataframe):
        # 거래 신호 생성
        return trade_signal
    
    def get_required_subscriptions(self):
        return ["market_data.binance.btcusdt"]
```

## 🔧 개발 가이드

### 코드 스타일

```bash
# 코드 포맷팅
black src/ tests/

# Import 정렬
isort src/ tests/

# 타입 체크
mypy src/

# 린팅
flake8 src/ tests/
```

### 테스트 실행

```bash
# 실제 인프라 테스트 (MVP 요구사항: mock 없는 테스트)
docker-compose up -d         # 인프라 시작
pytest tests/integration/test_real_message_bus_integration.py -v

# 전체 테스트
pytest

# 특정 테스트 유형
pytest tests/unit/           # 단위 테스트
pytest tests/integration/    # 통합 테스트 (실제 인프라 연동)
pytest tests/e2e/           # E2E 테스트

# 커버리지 리포트
pytest --cov=src --cov-report=html
```

#### 실제 인프라 통합 테스트

MVP 완료 기준: **"mock이 없는 상태로 모든 테스트를 통과해야한다"**

- ✅ 실제 RabbitMQ 서버와 연동 테스트
- ✅ 실제 메시지 발행/소비 검증  
- ✅ 200ms 미만 거래 지연시간 검증
- ✅ Core Engine 통합 테스트

### Git 워크플로우

```bash
# 피처 브랜치 생성
git checkout -b feature/new-strategy

# 커밋 (pre-commit 훅 자동 실행)
git add .
git commit -m "feat: add new strategy"

# 푸시 및 PR
git push origin feature/new-strategy
```

## 🚀 배포

### 로컬 배포 (Docker)

```bash
# 프로덕션 빌드
docker-compose -f docker-compose.prod.yml up -d
```

### GCP 배포

```bash
# Cloud Build 배포
gcloud builds submit --config=cloudbuild.yaml

# 서비스 상태 확인
bot-cli status --env=production
```

## 📊 모니터링

### 서비스 상태 확인

```bash
# Docker 서비스 상태
docker-compose ps

# 시스템 상태
bot-cli status

# 로그 확인
docker-compose logs core-engine
```

### 메트릭 대시보드

- **RabbitMQ 관리 UI**: http://localhost:15672
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000

## 🔒 보안

### API 키 관리

```bash
# GCP Secret Manager에 API 키 저장
gcloud secrets create binance-api-key --data-file=api_key.txt

# 환경 변수에서 Secret 경로 참조
BINANCE_API_SECRET_PATH=projects/your-project/secrets/binance-api-key
```

### 네트워크 보안

- VPC 내부 통신만 허용
- IP 화이트리스트 적용
- TLS/SSL 통신 강제

## 📖 문서

### 주요 문서 링크

- [시스템 아키텍처](docs/design-docs/00_System_Overview_and_Architecture.md)
- [MVP 기능 명세](docs/mvp/MVP%20통합%20기능명세서.md)
- [개발 로드맵](docs/roadmap/상세%20개발%20로드맵.md)
- [API 문서](docs/api/)

### 개발 가이드라인

- [CLAUDE.md](CLAUDE.md) - Claude Code 가이드라인
- [.cursorrules](.cursorrules) - Cursor IDE 규칙

## 🤝 기여하기

1. Fork 프로젝트
2. 피처 브랜치 생성 (`git checkout -b feature/amazing-feature`)
3. 변경 사항 커밋 (`git commit -m 'Add amazing feature'`)
4. 브랜치 푸시 (`git push origin feature/amazing-feature`)
5. Pull Request 생성

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🆘 지원

- **이슈 리포트**: [GitHub Issues](https://github.com/your-org/letrade_v1/issues)
- **토론**: [GitHub Discussions](https://github.com/your-org/letrade_v1/discussions)
- **문서**: [Wiki](https://github.com/your-org/letrade_v1/wiki)

## 📈 로드맵

### Week 1: MVP 핵심 인프라 구축 ✅
- [x] 시스템 아키텍처 설계
- [x] 개발 환경 구축
- [ ] 핵심 서비스 스켈레톤 구현

### Week 2: MVP 거래 기능 완성
- [ ] 이동평균 교차 전략 구현
- [ ] Capital Manager 구현
- [ ] 실시간 거래 실행

### Week 3: AI/ML 전략 개발
- [ ] 강화학습 환경 구축
- [ ] RL 에이전트 구현
- [ ] ML 모델 통합

### Week 4: 고급 기능 개발
- [ ] 스테이킹 모듈
- [ ] 선물 거래 기능
- [ ] 성능 최적화

---

**⚠️ 면책 조항**: 이 소프트웨어는 교육 및 연구 목적으로 제공됩니다. 실제 거래에서 발생하는 손실에 대해 개발자는 책임지지 않습니다.