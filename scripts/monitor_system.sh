#!/bin/bash
# 📊 24/7 시스템 모니터링 스크립트
# 시스템 상태 실시간 모니터링 및 알림

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}ℹ️  [$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ [$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  [$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

log_error() {
    echo -e "${RED}❌ [$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

# 설정
MONITOR_INTERVAL=${1:-60}  # 모니터링 주기 (초)
ALERT_THRESHOLD_CPU=80     # CPU 사용률 알림 임계값 (%)
ALERT_THRESHOLD_MEMORY=80  # 메모리 사용률 알림 임계값 (%)
ALERT_THRESHOLD_DISK=85    # 디스크 사용률 알림 임계값 (%)
LOG_FILE="logs/monitor_$(date +%Y%m%d).log"

# 로그 디렉토리 생성
mkdir -p logs

echo "📊 Letrade_v1 24/7 시스템 모니터링"
echo "================================="
echo "모니터링 주기: ${MONITOR_INTERVAL}초"
echo "로그 파일: $LOG_FILE"
echo ""

# 알림 함수 (텔레그램)
send_telegram_alert() {
    local message="$1"
    local bot_token="${TELEGRAM_BOT_TOKEN}"
    local chat_id="${TELEGRAM_CHAT_ID}"
    
    if [[ -n "$bot_token" && -n "$chat_id" ]]; then
        curl -s -X POST "https://api.telegram.org/bot$bot_token/sendMessage" \
            -d chat_id="$chat_id" \
            -d text="🚨 Letrade_v1 Alert: $message" \
            > /dev/null 2>&1
    fi
}

# 시스템 상태 체크 함수
check_system_health() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local issues=()
    
    # 1. Docker 서비스 상태 확인
    log_info "Docker 서비스 상태 확인 중..."
    
    services=("letrade-main" "letrade-postgres" "letrade-redis" "letrade-rabbitmq")
    for service in "${services[@]}"; do
        if docker ps --filter "name=$service" --filter "status=running" | grep -q "$service"; then
            echo "   ✅ $service: 정상 동작"
        else
            echo "   ❌ $service: 중단됨"
            issues+=("$service 서비스 중단")
        fi
    done
    
    # 2. 헬스체크 확인
    log_info "애플리케이션 헬스체크..."
    
    if curl -sf "http://localhost:8000/health" > /dev/null 2>&1; then
        echo "   ✅ 메인 애플리케이션: 정상"
    else
        echo "   ❌ 메인 애플리케이션: 응답 없음"
        issues+=("메인 애플리케이션 응답 없음")
    fi
    
    # 3. 시스템 리소스 확인
    log_info "시스템 리소스 확인 중..."
    
    # CPU 사용률
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F% '{print $1}')
    if (( $(echo "$cpu_usage > $ALERT_THRESHOLD_CPU" | bc -l) )); then
        echo "   ⚠️  CPU 사용률: ${cpu_usage}% (임계값: ${ALERT_THRESHOLD_CPU}%)"
        issues+=("CPU 사용률 높음: ${cpu_usage}%")
    else
        echo "   ✅ CPU 사용률: ${cpu_usage}%"
    fi
    
    # 메모리 사용률
    memory_usage=$(free | grep Mem | awk '{printf("%.1f", $3/$2 * 100.0)}')
    if (( $(echo "$memory_usage > $ALERT_THRESHOLD_MEMORY" | bc -l) )); then
        echo "   ⚠️  메모리 사용률: ${memory_usage}% (임계값: ${ALERT_THRESHOLD_MEMORY}%)"
        issues+=("메모리 사용률 높음: ${memory_usage}%")
    else
        echo "   ✅ 메모리 사용률: ${memory_usage}%"
    fi
    
    # 디스크 사용률
    disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [[ $disk_usage -gt $ALERT_THRESHOLD_DISK ]]; then
        echo "   ⚠️  디스크 사용률: ${disk_usage}% (임계값: ${ALERT_THRESHOLD_DISK}%)"
        issues+=("디스크 사용률 높음: ${disk_usage}%")
    else
        echo "   ✅ 디스크 사용률: ${disk_usage}%"
    fi
    
    # 4. 거래 시스템 특화 체크
    log_info "거래 시스템 상태 확인 중..."
    
    # 데이터베이스 연결 확인
    if docker exec letrade-postgres pg_isready -U letrade > /dev/null 2>&1; then
        echo "   ✅ 데이터베이스: 연결 정상"
    else
        echo "   ❌ 데이터베이스: 연결 실패"
        issues+=("데이터베이스 연결 실패")
    fi
    
    # Redis 연결 확인
    if docker exec letrade-redis redis-cli ping | grep -q PONG; then
        echo "   ✅ Redis: 연결 정상"
    else
        echo "   ❌ Redis: 연결 실패"
        issues+=("Redis 연결 실패")
    fi
    
    # RabbitMQ 연결 확인
    if docker exec letrade-rabbitmq rabbitmq-diagnostics ping > /dev/null 2>&1; then
        echo "   ✅ RabbitMQ: 연결 정상"
    else
        echo "   ❌ RabbitMQ: 연결 실패"
        issues+=("RabbitMQ 연결 실패")
    fi
    
    # 5. 로그 크기 확인 (디스크 공간 관리)
    log_size=$(du -sh logs/ 2>/dev/null | cut -f1 || echo "0K")
    echo "   📊 로그 크기: $log_size"
    
    # 6. 결과 로깅
    {
        echo "[$timestamp] System Check:"
        echo "  Services: ${#issues[@]} issues"
        echo "  CPU: ${cpu_usage}%"
        echo "  Memory: ${memory_usage}%"
        echo "  Disk: ${disk_usage}%"
        echo "  Log Size: $log_size"
        if [[ ${#issues[@]} -gt 0 ]]; then
            echo "  Issues: ${issues[*]}"
        fi
        echo ""
    } >> "$LOG_FILE"
    
    # 7. 알림 발송
    if [[ ${#issues[@]} -gt 0 ]]; then
        log_error "${#issues[@]}개 이슈 발견"
        for issue in "${issues[@]}"; do
            echo "   • $issue"
        done
        
        # 텔레그램 알림 발송
        alert_message="시스템 이슈 ${#issues[@]}개 발견: ${issues[*]}"
        send_telegram_alert "$alert_message"
        
        return 1
    else
        log_success "모든 시스템 정상 동작"
        return 0
    fi
}

# 자동 복구 함수
auto_recovery() {
    local service="$1"
    
    log_warning "$service 자동 복구 시도..."
    
    case "$service" in
        "letrade-main")
            docker-compose -f docker-compose.production.yml restart letrade-main
            sleep 30
            if curl -sf "http://localhost:8000/health" > /dev/null 2>&1; then
                log_success "$service 복구 성공"
                send_telegram_alert "$service 자동 복구 성공"
                return 0
            else
                log_error "$service 복구 실패"
                send_telegram_alert "$service 자동 복구 실패 - 수동 개입 필요"
                return 1
            fi
            ;;
        *)
            log_info "$service 수동 복구 필요"
            send_telegram_alert "$service 이슈 발견 - 수동 확인 필요"
            return 1
            ;;
    esac
}

# 메인 모니터링 루프
main_loop() {
    local consecutive_failures=0
    local max_failures=3
    
    while true; do
        echo ""
        echo "🔍 시스템 상태 확인 ($(date '+%H:%M:%S'))"
        echo "=================================="
        
        if check_system_health; then
            consecutive_failures=0
        else
            consecutive_failures=$((consecutive_failures + 1))
            
            # 연속 실패 시 자동 복구 시도
            if [[ $consecutive_failures -ge $max_failures ]]; then
                log_warning "연속 ${consecutive_failures}회 실패. 자동 복구 시도..."
                
                # 메인 서비스 재시작 시도
                if ! docker ps --filter "name=letrade-main" --filter "status=running" | grep -q "letrade-main"; then
                    auto_recovery "letrade-main"
                fi
                
                consecutive_failures=0
            fi
        fi
        
        echo ""
        echo "⏰ 다음 확인까지 ${MONITOR_INTERVAL}초 대기..."
        sleep "$MONITOR_INTERVAL"
    done
}

# 시그널 핸들러 (안전한 종료)
cleanup() {
    echo ""
    log_info "모니터링 중단 중..."
    send_telegram_alert "시스템 모니터링이 중단되었습니다"
    exit 0
}

trap cleanup SIGINT SIGTERM

# 모니터링 시작
log_info "24/7 모니터링 시작..."
send_telegram_alert "Letrade_v1 24/7 모니터링이 시작되었습니다"

main_loop