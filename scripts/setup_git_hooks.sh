#!/bin/bash
# 🔄 Git 훅 설정 스크립트
# Pre-commit 훅 자동 설치 및 설정

set -e

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

echo "🔄 Git 훅 자동 설정"
echo "=================="

# 1. pre-commit 설치
log_info "1. pre-commit 설치 확인..."

if ! command -v pre-commit &> /dev/null; then
    log_warning "pre-commit이 설치되지 않음. 설치 중..."
    pip install pre-commit
fi

log_success "pre-commit 설치 완료"

# 2. pre-commit 훅 설치
log_info "2. pre-commit 훅 설치..."

pre-commit install

log_success "Pre-commit 훅 설치 완료"

# 3. 첫 실행 (모든 파일 검사)
log_info "3. 전체 파일 첫 검사 실행..."

pre-commit run --all-files || {
    log_warning "일부 파일이 자동 수정되었습니다"
}

log_success "첫 검사 완료"

# 4. 커스텀 pre-push 훅 생성
log_info "4. 커스텀 pre-push 훅 설정..."

cat > .git/hooks/pre-push << 'EOF'
#!/bin/bash
# 🚀 Pre-push 훅: 로컬 테스트 자동 실행

echo "🔍 푸시 전 빠른 검증 실행..."

# 빠른 로컬 테스트 실행
if [[ -f "scripts/test_local.sh" ]]; then
    ./scripts/test_local.sh
    if [[ $? -ne 0 ]]; then
        echo "❌ 로컬 테스트 실패. 푸시를 중단합니다."
        echo "💡 수정 후 다시 시도하세요: ./scripts/test_local.sh"
        exit 1
    fi
else
    echo "⚠️  로컬 테스트 스크립트가 없습니다"
fi

echo "✅ 푸시 전 검증 완료!"
EOF

chmod +x .git/hooks/pre-push

log_success "Pre-push 훅 설정 완료"

# 5. 커밋 메시지 템플릿 설정
log_info "5. 커밋 메시지 템플릿 설정..."

cat > .gitmessage << 'EOF'
# 📝 커밋 메시지 가이드라인
# 
# 형식: <타입>: <제목>
#
# 타입:
#   feat:     새로운 기능 추가
#   fix:      버그 수정
#   docs:     문서 변경
#   style:    코드 포맷팅, 세미콜론 누락 등
#   refactor: 코드 리팩토링
#   test:     테스트 추가/수정
#   perf:     성능 개선
#   security: 보안 개선
#
# 예시:
#   feat: add MA crossover strategy
#   fix: resolve database connection timeout
#   docs: update API documentation
#
# 제목은 50자 이내, 명령형으로 작성
# 본문은 72자로 줄바꿈, 변경 이유와 방법 설명
EOF

git config commit.template .gitmessage

log_success "커밋 메시지 템플릿 설정 완료"

# 6. Git 설정 최적화
log_info "6. Git 설정 최적화..."

# 자동 CRLF 변환 설정
git config core.autocrlf input

# 대소문자 구분 설정
git config core.ignorecase false

# Push 기본 동작 설정
git config push.default simple

# 풀 리베이스 설정
git config pull.rebase true

log_success "Git 설정 최적화 완료"

# 완료
echo ""
echo "🎉 Git 훅 설정 완료!"
echo "==================="
echo ""
echo "📋 설정된 내용:"
echo "   ✅ Pre-commit 훅: 코드 포맷팅, 문법 검사"
echo "   ✅ Pre-push 훅: 로컬 테스트 자동 실행"
echo "   ✅ 커밋 메시지 템플릿"
echo "   ✅ Git 설정 최적화"
echo ""
echo "🚀 사용법:"
echo "   1. git add . (자동 포맷팅 실행)"
echo "   2. git commit (템플릿 가이드 표시)"
echo "   3. git push (자동 테스트 실행)"
echo ""
echo "🔧 수동 실행:"
echo "   • 전체 검사: pre-commit run --all-files"
echo "   • 빠른 테스트: ./scripts/test_local.sh"
echo "   • 전체 테스트: ./scripts/test_full.sh"

log_success "모든 설정이 완료되었습니다!"