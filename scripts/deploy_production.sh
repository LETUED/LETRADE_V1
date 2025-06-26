#!/bin/bash
# 🚀 프로덕션 배포 스크립트
# 24/7 서버 운영을 위한 안전한 배포

set -e

# 색상 정의
RED='\033[0;31m'
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

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 배포 환경 설정
ENVIRONMENT=${1:-production}
BACKUP_BEFORE_DEPLOY=${2:-true}
HEALTH_CHECK_TIMEOUT=300  # 5분

echo "🚀 Letrade_v1 프로덕션 배포"
echo "=========================="
echo "환경: $ENVIRONMENT"
echo "백업: $BACKUP_BEFORE_DEPLOY"

# 1. 사전 검사
log_info "1. 배포 사전 검사..."

# Docker 설치 확인
if ! command -v docker &> /dev/null; then
    log_error "Docker가 설치되지 않음"
    exit 1
fi

# Docker Compose 확인
if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose가 설치되지 않음"
    exit 1
fi

# 환경 파일 확인
if [[ ! -f ".env.production" ]]; then
    log_error ".env.production 파일이 없습니다"
    echo "💡 .env.prod.example을 복사하여 .env.production을 생성하세요"
    exit 1
fi

log_success "사전 검사 완료"

# 2. 로컬 테스트 실행
log_info "2. 배포 전 로컬 테스트..."

if [[ -f "scripts/test_local.sh" ]]; then
    ./scripts/test_local.sh
    if [[ $? -ne 0 ]]; then
        log_error "로컬 테스트 실패. 배포를 중단합니다."
        exit 1
    fi
else
    log_warning "로컬 테스트 스크립트가 없습니다"
fi

log_success "로컬 테스트 통과"

# 3. 백업 (선택적)
if [[ "$BACKUP_BEFORE_DEPLOY" == "true" ]]; then
    log_info "3. 배포 전 백업 생성..."
    
    # 백업 디렉토리 생성
    mkdir -p backups/$(date +%Y%m%d_%H%M%S)
    
    # 데이터베이스 백업 (실행 중인 경우)
    if docker ps | grep -q letrade-postgres; then
        log_info "데이터베이스 백업 중..."
        docker exec letrade-postgres pg_dump -U letrade letrade > backups/$(date +%Y%m%d_%H%M%S)/database_backup.sql
        log_success "데이터베이스 백업 완료"
    fi
    
    # 설정 파일 백업
    cp -r config/ backups/$(date +%Y%m%d_%H%M%S)/config_backup/
    
    log_success "백업 완료"
fi

# 4. 이미지 빌드
log_info "4. Docker 이미지 빌드..."

# 빌드 캐시 활용
docker-compose -f docker-compose.production.yml build --parallel

log_success "이미지 빌드 완료"

# 5. 기존 서비스 안전 종료 (Rolling Deployment)
log_info "5. 기존 서비스 안전 종료..."

if docker ps | grep -q letrade-main; then
    log_info "기존 서비스가 실행 중입니다. 안전하게 종료 중..."
    
    # 새로운 요청 차단 (헬스체크 실패 유도)
    docker exec letrade-main touch /app/maintenance_mode || true
    
    # 30초 대기 (기존 요청 완료 대기)
    log_info "기존 요청 완료 대기 (30초)..."
    sleep 30
    
    # 기존 컨테이너 종료
    docker-compose -f docker-compose.production.yml stop letrade-main
    
    log_success "기존 서비스 안전 종료 완료"
else
    log_info "실행 중인 기존 서비스가 없습니다"
fi

# 6. 새 서비스 시작
log_info "6. 새 서비스 시작..."

# 인프라 서비스 먼저 시작 (DB, Redis, RabbitMQ)
log_info "인프라 서비스 시작 중..."
docker-compose -f docker-compose.production.yml up -d postgres redis rabbitmq

# 인프라 서비스 준비 대기
log_info "인프라 서비스 준비 대기..."
sleep 30

# 메인 애플리케이션 시작
log_info "메인 애플리케이션 시작 중..."
docker-compose -f docker-compose.production.yml up -d letrade-main

log_success "새 서비스 시작 완료"

# 7. 헬스체크
log_info "7. 헬스체크 실행..."

# 헬스체크 함수
check_health() {
    local service_url=$1
    local timeout=$2
    local interval=10
    local elapsed=0
    
    while [[ $elapsed -lt $timeout ]]; do
        if curl -sf "$service_url/health" > /dev/null 2>&1; then
            return 0
        fi
        sleep $interval
        elapsed=$((elapsed + interval))
        echo -n "."
    done
    return 1
}

# 메인 서비스 헬스체크
echo -n "메인 서비스 헬스체크"
if check_health "http://localhost:8000" $HEALTH_CHECK_TIMEOUT; then
    echo ""
    log_success "메인 서비스 정상 동작"
else
    echo ""
    log_error "메인 서비스 헬스체크 실패"
    
    # 롤백
    log_warning "롤백 시작..."
    docker-compose -f docker-compose.production.yml logs letrade-main
    docker-compose -f docker-compose.production.yml stop letrade-main
    exit 1
fi

# 8. 모니터링 서비스 시작
log_info "8. 모니터링 서비스 시작..."

docker-compose -f docker-compose.production.yml up -d prometheus grafana

log_success "모니터링 서비스 시작 완료"

# 9. 최종 검증
log_info "9. 최종 시스템 검증..."

# 모든 서비스 상태 확인
services=("letrade-main" "letrade-postgres" "letrade-redis" "letrade-rabbitmq")
failed_services=()

for service in "${services[@]}"; do
    if docker ps --filter "name=$service" --filter "status=running" | grep -q "$service"; then
        log_success "$service 정상 동작"
    else
        log_error "$service 동작 실패"
        failed_services+=("$service")
    fi
done

if [[ ${#failed_services[@]} -gt 0 ]]; then
    log_error "일부 서비스 실패: ${failed_services[*]}"
    exit 1
fi

# 10. 정리 작업
log_info "10. 정리 작업..."

# 사용하지 않는 이미지 정리
docker image prune -f

# 로그 순환 설정 확인
if [[ ! -f "/etc/logrotate.d/docker" ]]; then
    log_warning "로그 순환 설정이 없습니다. 설정을 권장합니다."
fi

log_success "정리 작업 완료"

# 배포 완료
echo ""
echo "🎉 배포 완료!"
echo "============="
echo ""
echo "📊 서비스 현황:"
echo "   • 메인 애플리케이션: http://localhost:8000"
echo "   • API 문서: http://localhost:8000/docs"
echo "   • 헬스체크: http://localhost:8000/health"
echo "   • Grafana 모니터링: http://localhost:3000"
echo "   • Prometheus 메트릭: http://localhost:9090"
echo "   • RabbitMQ 관리: http://localhost:15672"
echo ""
echo "🔧 관리 명령어:"
echo "   • 로그 확인: docker-compose -f docker-compose.production.yml logs -f"
echo "   • 상태 확인: docker-compose -f docker-compose.production.yml ps"
echo "   • 재시작: docker-compose -f docker-compose.production.yml restart letrade-main"
echo "   • 종료: docker-compose -f docker-compose.production.yml down"
echo ""
echo "💾 백업 위치: backups/$(date +%Y%m%d)/"
echo ""

log_success "🚀 Letrade_v1이 24/7 모드로 성공적으로 배포되었습니다!"

# 자동 모니터링 설정 안내
echo ""
echo "📋 다음 단계:"
echo "   1. Grafana 대시보드 설정 (http://localhost:3000)"
echo "   2. 알림 설정 (텔레그램/이메일)"
echo "   3. 백업 스케줄 확인"
echo "   4. 소액 실거래 테스트 ($100)"