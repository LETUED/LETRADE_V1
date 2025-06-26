#!/bin/bash

# Rollback Script for Letrade_v1
# 배포 실패 시 이전 버전으로 롤백하는 스크립트

set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 백업 목록 표시
list_backups() {
    log_info "사용 가능한 백업 목록:"
    if [ -d "backups" ]; then
        ls -1d backups/*/ 2>/dev/null | sort -r | head -10 || echo "백업이 없습니다."
    else
        log_error "백업 디렉토리가 없습니다."
        exit 1
    fi
}

# 롤백 실행
perform_rollback() {
    local backup_dir=$1
    
    log_info "롤백 시작: $backup_dir"
    
    # 1. 현재 서비스 중지
    log_info "현재 서비스 중지 중..."
    docker-compose -f docker-compose.prod.yml down
    
    # 2. 환경 파일 복원
    if [ -f "$backup_dir/.env.prod.backup" ]; then
        cp "$backup_dir/.env.prod.backup" .env.prod
        log_success "환경 파일 복원 완료"
    fi
    
    # 3. 데이터베이스 복원 (선택적)
    if [ -f "$backup_dir/database.sql" ]; then
        read -p "데이터베이스를 복원하시겠습니까? (yes/no): " restore_db
        if [ "$restore_db" = "yes" ]; then
            # PostgreSQL 시작
            docker-compose -f docker-compose.prod.yml up -d postgres
            sleep 10
            
            # 데이터베이스 복원
            docker-compose -f docker-compose.prod.yml exec -T postgres psql -U letrade_user -d letrade_db < "$backup_dir/database.sql"
            log_success "데이터베이스 복원 완료"
        fi
    fi
    
    # 4. 이전 버전 태그 확인
    PREVIOUS_VERSION=$(cat "$backup_dir/VERSION" 2>/dev/null || echo "latest")
    
    # 5. 서비스 재시작
    log_info "서비스 재시작 중 (버전: $PREVIOUS_VERSION)..."
    VERSION=$PREVIOUS_VERSION docker-compose -f docker-compose.prod.yml up -d
    
    # 6. 헬스체크
    log_info "헬스체크 대기 중..."
    sleep 30
    
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log_success "롤백 완료! 시스템이 정상 작동 중입니다."
    else
        log_error "롤백 후 시스템이 응답하지 않습니다."
        exit 1
    fi
}

# 메인 함수
main() {
    log_warning "Letrade_v1 롤백 프로세스"
    echo "======================================"
    
    # 백업 목록 표시
    list_backups
    echo ""
    
    # 백업 선택
    read -p "롤백할 백업 디렉토리를 입력하세요 (예: backups/20240101_120000): " backup_dir
    
    if [ ! -d "$backup_dir" ]; then
        log_error "유효하지 않은 백업 디렉토리입니다: $backup_dir"
        exit 1
    fi
    
    # 롤백 확인
    echo ""
    log_warning "주의: 이 작업은 현재 시스템을 중지하고 이전 버전으로 되돌립니다."
    read -p "계속하시겠습니까? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        log_warning "롤백이 취소되었습니다."
        exit 0
    fi
    
    # 롤백 실행
    perform_rollback "$backup_dir"
    
    echo ""
    echo "======================================"
    log_success "롤백이 완료되었습니다!"
    echo ""
    echo "다음 단계:"
    echo "1. 시스템 상태 확인: docker-compose -f docker-compose.prod.yml ps"
    echo "2. 로그 모니터링: docker-compose -f docker-compose.prod.yml logs -f"
    echo "3. API 테스트: curl http://localhost:8000/api/v1/system/status"
}

# 스크립트 실행
main "$@"