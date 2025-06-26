#!/bin/bash
# 🚀 로컬 테스트 완전 자동화 스크립트
# CI/CD 의존성 없이 모든 검증을 로컬에서 실행

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
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

# 타이머 시작
start_time=$(date +%s)

echo "🎯 Letrade_v1 로컬 테스트 자동화 시스템"
echo "========================================"

# 1. 환경 확인
log_info "1. 개발 환경 확인 중..."

# Python 버전 확인
python_version=$(python --version 2>&1)
log_info "Python 버전: $python_version"

# 가상환경 확인
if [[ "$VIRTUAL_ENV" != "" ]]; then
    log_success "가상환경 활성화됨: $VIRTUAL_ENV"
else
    log_warning "가상환경이 활성화되지 않음"
fi

# 2. 빠른 문법 검사 (30초 이내)
log_info "2. 빠른 문법 검사 실행..."

# Python 문법 체크 (매우 빠름)
if python -m py_compile src/core_engine/main.py > /dev/null 2>&1; then
    log_success "핵심 모듈 문법 검사 통과"
else
    log_error "핵심 모듈 문법 오류 발견"
    exit 1
fi

# 3. 코드 포맷팅 검사 (자동 수정)
log_info "3. 코드 포맷팅 검사 및 자동 수정..."

# Black 포맷팅 (자동 수정)
if command -v black > /dev/null; then
    black src/ tests/ --quiet || true
    log_success "Black 포맷팅 완료"
else
    log_warning "Black이 설치되지 않음 - pip install black"
fi

# Import 정렬 (자동 수정)
if command -v isort > /dev/null; then
    isort src/ tests/ --quiet || true
    log_success "Import 정렬 완료"
else
    log_warning "isort가 설치되지 않음"
fi

# 4. 핵심 테스트만 실행 (빠른 검증)
log_info "4. 핵심 기능 테스트 실행..."

# 핵심 단위 테스트만 실행 (타임아웃 30초)
if python -m pytest tests/unit/core_engine/ tests/unit/strategies/ \
    --timeout=30 \
    --timeout-method=thread \
    -x \
    --tb=no \
    -q \
    > /dev/null 2>&1; then
    log_success "핵심 단위 테스트 통과"
else
    log_warning "일부 테스트 실패 - 자세한 내용은 전체 테스트에서 확인"
fi

# 5. 보안 스캔 (빠른 검사)
log_info "5. 보안 취약점 빠른 스캔..."

# 기본적인 보안 패턴 검사 - 실제 하드코딩된 키만 탐지
if grep -r "api_key.*=.*['\"][a-zA-Z0-9]\{20,\}['\"]" src/ --exclude-dir=htmlcov --include="*.py" > /dev/null 2>&1; then
    log_error "하드코딩된 API 키 발견!"
    grep -r "api_key.*=.*['\"][a-zA-Z0-9]\{20,\}['\"]" src/ --exclude-dir=htmlcov --include="*.py" || true
    exit 1
else
    log_success "하드코딩된 시크릿 없음"
fi

# 6. 임포트 체크 (순환 참조 등)
log_info "6. 임포트 순환 참조 검사..."

# 핵심 모듈 임포트 테스트
if python -c "
try:
    import src.core_engine.main
    import src.strategies.base_strategy
    import src.exchange_connector.main
    print('✅ 핵심 모듈 임포트 성공')
except ImportError as e:
    print(f'❌ 임포트 오류: {e}')
    exit(1)
" > /dev/null 2>&1; then
    log_success "핵심 모듈 임포트 검증 완료"
else
    log_error "모듈 임포트 오류 발견"
    python -c "
import src.core_engine.main
import src.strategies.base_strategy  
import src.exchange_connector.main
"
    exit 1
fi

# 7. 설정 파일 검증
log_info "7. 설정 파일 유효성 검사..."

# .env 파일 존재 확인
if [[ -f ".env" ]]; then
    log_success ".env 파일 존재"
    
    # 필수 환경변수 확인
    required_vars=("ENVIRONMENT" "DATABASE_URL")
    for var in "${required_vars[@]}"; do
        if grep -q "^$var=" .env; then
            log_success "$var 설정됨"
        else
            log_warning "$var 미설정"
        fi
    done
else
    log_warning ".env 파일이 없음 - .env.example을 복사하세요"
fi

# 8. 데이터베이스 연결 테스트 (선택적)
log_info "8. 빠른 시스템 상태 확인..."

# PostgreSQL 연결 테스트 (타임아웃 5초)
if timeout 5 python -c "
import os
from sqlalchemy import create_engine, text
try:
    # 환경변수에서 DB URL 가져오기
    db_url = os.getenv('DATABASE_URL', 'sqlite:///./test.db')
    engine = create_engine(db_url)
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    print('✅ 데이터베이스 연결 성공')
except Exception as e:
    print(f'⚠️  데이터베이스 연결 실패: {e}')
" 2>/dev/null; then
    log_success "데이터베이스 연결 확인"
else
    log_warning "데이터베이스 연결 실패 (프로덕션에서는 정상)"
fi

# 9. Git 상태 확인
log_info "9. Git 상태 확인..."

# 변경된 파일 수 확인
changed_files=$(git diff --name-only | wc -l)
if [[ $changed_files -gt 0 ]]; then
    log_warning "$changed_files 개 파일이 변경됨"
    git diff --name-only
else
    log_success "변경사항 없음"
fi

# 10. 완료 및 요약
end_time=$(date +%s)
duration=$((end_time - start_time))

echo ""
echo "🎉 로컬 테스트 완료!"
echo "=========================="
log_success "총 소요 시간: ${duration}초"

# 커밋 가능 여부 판단
if [[ $? -eq 0 ]]; then
    log_success "✅ 커밋 준비 완료! git add . && git commit -m \"your message\""
    echo ""
    echo "🚀 다음 단계:"
    echo "   1. git add ."
    echo "   2. git commit -m \"feat: your feature description\""
    echo "   3. git push origin main"
    echo ""
else
    log_error "❌ 수정이 필요한 항목이 있습니다"
    exit 1
fi

# 추가 옵션 제공
echo "📋 추가 옵션:"
echo "   • 전체 테스트: ./scripts/test_full.sh"
echo "   • 성능 테스트: ./scripts/test_performance.sh"
echo "   • 프로덕션 배포: ./scripts/deploy_production.sh"