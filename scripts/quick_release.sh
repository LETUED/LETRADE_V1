#!/bin/bash
# ⚡ 빠른 릴리즈 스크립트 
# 개발자용 원클릭 "테스트 → 커밋 → 릴리즈" 자동화

set -e

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# 파라미터 설정
COMMIT_MESSAGE="${1:-"feat: development update"}"
FORCE_RELEASE="${2:-false}"

echo "⚡ Letrade_v1 빠른 릴리즈"
echo "========================"
echo "커밋 메시지: $COMMIT_MESSAGE"

# 1. 빠른 테스트
log_info "1. 빠른 테스트 실행 중..."
if ./scripts/test_local.sh > /dev/null 2>&1; then
    log_success "로컬 테스트 통과"
else
    echo "❌ 로컬 테스트 실패"
    echo "💡 수동 실행: ./scripts/test_local.sh"
    exit 1
fi

# 2. 변경사항 확인
log_info "2. 변경사항 확인..."
if [[ -z $(git status --porcelain) ]] && [[ "$FORCE_RELEASE" != "true" ]]; then
    log_warning "커밋할 변경사항이 없습니다"
    echo "💡 강제 릴리즈: $0 \"$COMMIT_MESSAGE\" true"
    exit 0
fi

# 3. 자동 커밋
log_info "3. 변경사항 커밋 중..."
git add .
git commit -m "$COMMIT_MESSAGE" || log_warning "커밋할 변경사항 없음"

# 4. 푸시 및 자동 릴리즈 트리거
log_info "4. GitHub 자동 릴리즈 트리거..."
git push origin main

# 5. 완료 메시지
echo ""
log_success "🚀 빠른 릴리즈 완료!"
echo ""
echo "📋 진행 상황:"
echo "   1. ✅ 로컬 테스트 통과"
echo "   2. ✅ 변경사항 커밋"
echo "   3. ✅ GitHub 푸시 완료"
echo "   4. 🔄 GitHub Actions 자동 릴리즈 진행 중..."
echo ""
echo "🌐 확인하기:"
echo "   • GitHub Actions: https://github.com/$(git config --get remote.origin.url | sed 's/.*github.com[:/]\([^.]*\).*/\1/')/actions"
echo "   • 릴리즈: https://github.com/$(git config --get remote.origin.url | sed 's/.*github.com[:/]\([^.]*\).*/\1/')/releases"
echo ""
echo "⏱️  약 3-5분 후 stable 브랜치에 자동 릴리즈됩니다!"