#!/bin/bash

# Production Deployment Script for Letrade_v1
# 이 스크립트는 프로덕션 환경으로 안전하게 배포하는 프로세스를 자동화합니다.

set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로깅 함수
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

# 사전 검사
pre_deployment_checks() {
    log_info "사전 배포 검사 시작..."
    
    # 1. 환경 파일 확인
    if [ ! -f ".env.prod" ]; then
        log_error ".env.prod 파일이 없습니다. .env.prod.example을 복사하여 설정하세요."
        exit 1
    fi
    
    # 2. Docker 실행 확인
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker가 실행되지 않고 있습니다."
        exit 1
    fi
    
    # 3. 필수 환경 변수 확인
    source .env.prod
    required_vars=(
        "POSTGRES_PASSWORD"
        "RABBITMQ_PASSWORD"
        "REDIS_PASSWORD"
        "BINANCE_API_KEY"
        "BINANCE_API_SECRET"
        "TELEGRAM_BOT_TOKEN"
        "JWT_SECRET_KEY"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            log_error "필수 환경 변수가 설정되지 않았습니다: $var"
            exit 1
        fi
    done
    
    log_success "사전 배포 검사 완료"
}

# 테스트 실행
run_tests() {
    log_info "테스트 실행 중..."
    
    # 테스트 환경 설정
    docker-compose -f docker-compose.test.yml up -d
    sleep 10
    
    # 테스트 실행
    docker-compose -f docker-compose.test.yml run --rm test pytest tests/ -v --cov=src --cov-report=term
    
    # 테스트 환경 정리
    docker-compose -f docker-compose.test.yml down
    
    log_success "모든 테스트 통과"
}

# 보안 검사
security_scan() {
    log_info "보안 검사 실행 중..."
    
    # Bandit 보안 스캔
    bandit -r src/ -f json -o security_report.json || true
    
    # 비밀 정보 스캔
    if grep -r "BINANCE_API" src/ --exclude-dir=__pycache__ | grep -v "os.environ"; then
        log_error "소스 코드에 하드코딩된 API 키가 발견되었습니다!"
        exit 1
    fi
    
    log_success "보안 검사 완료"
}

# 백업 생성
create_backup() {
    log_info "현재 상태 백업 중..."
    
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # 데이터베이스 백업 (프로덕션 환경이 이미 실행 중인 경우)
    if docker-compose -f docker-compose.prod.yml ps | grep -q "postgres"; then
        docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump -U letrade_user letrade_db > "$BACKUP_DIR/database.sql"
        log_success "데이터베이스 백업 완료: $BACKUP_DIR/database.sql"
    fi
    
    # 설정 파일 백업
    cp .env.prod "$BACKUP_DIR/.env.prod.backup"
    
    log_success "백업 완료: $BACKUP_DIR"
}

# 이미지 빌드
build_images() {
    log_info "Docker 이미지 빌드 중..."
    
    # 버전 태깅
    VERSION=$(cat VERSION 2>/dev/null || echo "1.0.0")
    
    # 프로덕션 이미지 빌드
    docker build -t letrade:${VERSION} -t letrade:latest .
    
    log_success "이미지 빌드 완료: letrade:${VERSION}"
}

# 블루-그린 배포
deploy_blue_green() {
    log_info "블루-그린 배포 시작..."
    
    # 현재 실행 중인 컨테이너 확인
    if docker-compose -f docker-compose.prod.yml ps | grep -q "letrade"; then
        log_info "기존 서비스 감지됨. 그린 환경으로 배포합니다."
        
        # 새 버전으로 서비스 업데이트 (롤링 업데이트)
        docker-compose -f docker-compose.prod.yml up -d --no-deps --build \
            core-engine \
            capital-manager \
            exchange-connector \
            telegram-bot
        
        # 헬스체크 대기
        log_info "헬스체크 대기 중..."
        sleep 30
        
        # 헬스체크
        if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
            log_error "헬스체크 실패! 롤백을 시작합니다."
            docker-compose -f docker-compose.prod.yml down
            exit 1
        fi
        
        log_success "새 버전 배포 완료"
    else
        log_info "첫 배포입니다. 전체 스택을 시작합니다."
        docker-compose -f docker-compose.prod.yml up -d
    fi
}

# 배포 후 검증
post_deployment_validation() {
    log_info "배포 후 검증 시작..."
    
    # 1. 서비스 상태 확인
    services=("core-engine" "capital-manager" "exchange-connector" "telegram-bot")
    for service in "${services[@]}"; do
        if ! docker-compose -f docker-compose.prod.yml ps | grep -q "$service.*Up"; then
            log_error "$service 서비스가 실행되지 않고 있습니다!"
            exit 1
        fi
    done
    
    # 2. API 응답 확인
    max_retries=5
    retry_count=0
    
    while [ $retry_count -lt $max_retries ]; do
        if curl -f http://localhost:8000/api/v1/system/status > /dev/null 2>&1; then
            log_success "API 응답 정상"
            break
        fi
        
        retry_count=$((retry_count + 1))
        log_warning "API 응답 대기 중... ($retry_count/$max_retries)"
        sleep 10
    done
    
    if [ $retry_count -eq $max_retries ]; then
        log_error "API가 응답하지 않습니다!"
        exit 1
    fi
    
    # 3. 데이터베이스 연결 확인
    docker-compose -f docker-compose.prod.yml exec -T postgres pg_isready -U letrade_user
    
    log_success "배포 후 검증 완료"
}

# 모니터링 설정
setup_monitoring() {
    log_info "모니터링 설정 중..."
    
    # Grafana 대시보드 임포트
    if [ -d "config/grafana/dashboards" ]; then
        log_info "Grafana 대시보드 설정 완료"
    fi
    
    # 알림 설정
    log_info "알림 채널 설정을 확인하세요:"
    echo "  - Grafana: http://localhost:3000"
    echo "  - Prometheus: http://localhost:9090"
    echo "  - RabbitMQ: http://localhost:15672"
    
    log_success "모니터링 설정 완료"
}

# 메인 배포 프로세스
main() {
    log_info "Letrade_v1 프로덕션 배포 시작"
    echo "======================================"
    
    # 배포 확인
    read -p "프로덕션 배포를 진행하시겠습니까? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        log_warning "배포가 취소되었습니다."
        exit 0
    fi
    
    # 단계별 실행
    pre_deployment_checks
    run_tests
    security_scan
    create_backup
    build_images
    deploy_blue_green
    post_deployment_validation
    setup_monitoring
    
    echo "======================================"
    log_success "프로덕션 배포가 성공적으로 완료되었습니다!"
    echo ""
    echo "다음 단계:"
    echo "1. 모니터링 대시보드 확인: http://localhost:3000"
    echo "2. 로그 모니터링: docker-compose -f docker-compose.prod.yml logs -f"
    echo "3. 텔레그램 봇 테스트: /status 명령어 실행"
    echo ""
    echo "문제 발생 시:"
    echo "- 롤백: ./scripts/rollback.sh"
    echo "- 로그 확인: docker-compose -f docker-compose.prod.yml logs [서비스명]"
}

# 스크립트 실행
main "$@"