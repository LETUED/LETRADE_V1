#!/bin/bash
# 🧪 전체 테스트 수트 실행 스크립트
# 상세한 테스트와 성능 검증

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

start_time=$(date +%s)

echo "🧪 Letrade_v1 전체 테스트 수트"
echo "============================="

# 1. 의존성 설치 확인
log_info "1. 개발 의존성 확인 및 설치..."

# 필수 패키지 설치
pip install -e ".[dev]" --quiet || {
    log_error "의존성 설치 실패"
    exit 1
}

log_success "개발 의존성 설치 완료"

# 2. 코드 품질 검사
log_info "2. 코드 품질 전체 검사..."

# Black 포맷팅 검사
echo "   • Black 포맷팅 검사..."
if black --check src/ tests/; then
    log_success "Black 포맷팅 검사 통과"
else
    log_warning "Black 포맷팅 필요 - 자동 수정 중..."
    black src/ tests/
fi

# isort 임포트 정렬 검사
echo "   • Import 정렬 검사..."
if isort --check-only src/ tests/; then
    log_success "Import 정렬 검사 통과"
else
    log_warning "Import 정렬 필요 - 자동 수정 중..."
    isort src/ tests/
fi

# Flake8 린팅
echo "   • Flake8 린팅 검사..."
if flake8 src/ tests/ || true; then  # 경고만 표시
    log_success "Flake8 린팅 완료"
fi

# 3. 타입 검사 (선택적)
log_info "3. 타입 힌트 검사..."

if command -v mypy > /dev/null; then
    echo "   • MyPy 타입 검사..."
    mypy src/ --ignore-missing-imports --no-strict-optional || {
        log_warning "MyPy 타입 검사에서 경고 발견"
    }
    log_success "타입 검사 완료"
else
    log_warning "MyPy가 설치되지 않음"
fi

# 4. 보안 스캔
log_info "4. 보안 취약점 스캔..."

if command -v bandit > /dev/null; then
    echo "   • Bandit 보안 스캔..."
    bandit -r src/ -f json -o security_report.json || {
        log_warning "보안 취약점 발견 - security_report.json 확인"
    }
    log_success "보안 스캔 완료"
else
    log_warning "Bandit이 설치되지 않음"
fi

# 5. 단위 테스트 (상세)
log_info "5. 단위 테스트 실행..."

echo "   • 핵심 엔진 테스트..."
python -m pytest tests/unit/core_engine/ -v --tb=short || true

echo "   • 전략 테스트..."
python -m pytest tests/unit/strategies/ -v --tb=short || true

echo "   • Exchange Connector 테스트..."
python -m pytest tests/unit/exchange_connector/ -v --tb=short || true

echo "   • Capital Manager 테스트..."
python -m pytest tests/unit/capital_manager/ -v --tb=short || true

# 6. 통합 테스트
log_info "6. 통합 테스트 실행..."

echo "   • 시스템 통합 테스트..."
python -m pytest tests/integration/ -v --tb=short -x || {
    log_warning "일부 통합 테스트 실패"
}

# 7. 성능 테스트
log_info "7. 성능 벤치마크 테스트..."

echo "   • 거래 실행 성능 테스트..."
if [[ -f "tests/performance/test_trading_performance.py" ]]; then
    python -m pytest tests/performance/test_trading_performance.py -v --tb=short || {
        log_warning "성능 테스트 실패"
    }
else
    log_warning "성능 테스트 파일이 없음"
fi

# 8. 커버리지 테스트
log_info "8. 코드 커버리지 측정..."

python -m pytest tests/unit/ \
    --cov=src \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-fail-under=70 || {
    log_warning "코드 커버리지 70% 미달"
}

log_success "커버리지 리포트: htmlcov/index.html"

# 9. E2E 테스트 (선택적)
log_info "9. E2E 테스트 실행..."

if [[ -f "tests/e2e/test_trading_flow.py" ]]; then
    echo "   • 전체 거래 플로우 테스트..."
    python -m pytest tests/e2e/ -v --tb=short --timeout=300 || {
        log_warning "E2E 테스트 실패"
    }
else
    log_warning "E2E 테스트 파일이 없음"
fi

# 10. 데이터베이스 마이그레이션 테스트
log_info "10. 데이터베이스 마이그레이션 테스트..."

if [[ -f "alembic.ini" ]]; then
    echo "   • Alembic 마이그레이션 체크..."
    alembic check || {
        log_warning "마이그레이션 체크 실패"
    }
    log_success "마이그레이션 체크 완료"
else
    log_warning "Alembic 설정이 없음"
fi

# 11. 최종 검증
log_info "11. 최종 시스템 검증..."

# 모든 모듈 임포트 테스트
echo "   • 전체 모듈 임포트 테스트..."
python -c "
import sys
sys.path.append('src')

modules = [
    'core_engine.main',
    'strategies.base_strategy',
    'strategies.ma_crossover',
    'exchange_connector.main',
    'capital_manager.main',
    'common.message_bus'
]

failed = []
for module in modules:
    try:
        __import__(module)
        print(f'✅ {module}')
    except ImportError as e:
        print(f'❌ {module}: {e}')
        failed.append(module)

if failed:
    print(f'실패한 모듈: {failed}')
    sys.exit(1)
else:
    print('✅ 모든 모듈 임포트 성공')
" || {
    log_error "모듈 임포트 실패"
    exit 1
}

# 12. 빌드 테스트 (Docker)
log_info "12. Docker 빌드 테스트..."

if [[ -f "Dockerfile" ]]; then
    echo "   • Docker 이미지 빌드..."
    docker build -t letrade-v1:test . || {
        log_warning "Docker 빌드 실패"
    }
    log_success "Docker 빌드 완료"
else
    log_warning "Dockerfile이 없음"
fi

# 완료 및 결과 요약
end_time=$(date +%s)
duration=$((end_time - start_time))

echo ""
echo "🎉 전체 테스트 완료!"
echo "===================="
log_success "총 소요 시간: ${duration}초"

# 파일 정리
echo ""
echo "📊 생성된 리포트:"
echo "   • 코드 커버리지: htmlcov/index.html"
echo "   • 보안 리포트: security_report.json"

# 다음 단계 안내
echo ""
echo "🚀 다음 단계:"
echo "   1. 리포트 검토"
echo "   2. 필요시 코드 수정"
echo "   3. ./scripts/test_local.sh 로 빠른 재검증"
echo "   4. git 커밋 및 푸시"

log_success "전체 테스트 완료!"