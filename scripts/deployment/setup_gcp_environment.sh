#!/bin/bash

# =============================================================================
# GCP 환경 설정 자동화 스크립트
# Letrade_v1 프로젝트를 위한 완전한 GCP 환경 구성
# =============================================================================

set -e

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 로깅 함수
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} ✅ $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} ⚠️ $1"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} ❌ $1"
}

# 설정 변수들
PROJECT_ID=${GCP_PROJECT_ID:-"letrade-crypto-bot"}
REGION=${GCP_REGION:-"asia-northeast3"}
ZONE=${GCP_ZONE:-"asia-northeast3-a"}
SERVICE_ACCOUNT_NAME="letrade-bot"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# 함수: 전제조건 확인
check_prerequisites() {
    log "전제조건 확인 중..."
    
    # gcloud CLI 확인
    if ! command -v gcloud &> /dev/null; then
        log_error "Google Cloud SDK가 설치되지 않았습니다."
        log "설치 방법: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
    
    # 인증 확인
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        log_error "Google Cloud에 인증되지 않았습니다."
        log "실행하세요: gcloud auth login"
        exit 1
    fi
    
    log_success "전제조건 확인 완료"
}

# 함수: GCP 프로젝트 설정
setup_project() {
    log "GCP 프로젝트 설정 중..."
    
    # 프로젝트 존재 확인
    if ! gcloud projects describe "$PROJECT_ID" &> /dev/null; then
        log "프로젝트 '$PROJECT_ID' 생성 중..."
        gcloud projects create "$PROJECT_ID" --name="Letrade Trading Bot"
    else
        log_success "프로젝트 '$PROJECT_ID' 이미 존재함"
    fi
    
    # 프로젝트 설정
    gcloud config set project "$PROJECT_ID"
    gcloud config set compute/region "$REGION"
    gcloud config set compute/zone "$ZONE"
    
    log_success "프로젝트 설정 완료"
}

# 함수: API 활성화
enable_apis() {
    log "필요한 API들 활성화 중..."
    
    apis=(
        "secretmanager.googleapis.com"
        "cloudsql.googleapis.com"
        "cloudbuild.googleapis.com"
        "containerregistry.googleapis.com"
        "compute.googleapis.com"
        "run.googleapis.com"
        "monitoring.googleapis.com"
        "logging.googleapis.com"
    )
    
    for api in "${apis[@]}"; do
        log "API 활성화: $api"
        gcloud services enable "$api"
    done
    
    log_success "API 활성화 완료"
}

# 함수: 서비스 계정 생성
create_service_account() {
    log "서비스 계정 설정 중..."
    
    # 서비스 계정 생성
    if ! gcloud iam service-accounts describe "$SERVICE_ACCOUNT_EMAIL" &> /dev/null; then
        gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" \
            --display-name="Letrade Trading Bot Service Account" \
            --description="Service account for Letrade automated trading system"
    else
        log_success "서비스 계정 이미 존재함"
    fi
    
    # 권한 부여
    log "IAM 권한 설정 중..."
    roles=(
        "roles/secretmanager.admin"
        "roles/cloudsql.client"
        "roles/monitoring.editor"
        "roles/logging.logWriter"
        "roles/cloudtrace.agent"
    )
    
    for role in "${roles[@]}"; do
        gcloud projects add-iam-policy-binding "$PROJECT_ID" \
            --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
            --role="$role"
    done
    
    # 키 파일 생성
    if [[ ! -f "./service-account.json" ]]; then
        log "서비스 계정 키 파일 생성 중..."
        gcloud iam service-accounts keys create ./service-account.json \
            --iam-account="$SERVICE_ACCOUNT_EMAIL"
        chmod 600 ./service-account.json
    else
        log_success "서비스 계정 키 파일 이미 존재함"
    fi
    
    log_success "서비스 계정 설정 완료"
}

# 함수: Secret Manager 설정
setup_secret_manager() {
    log "Secret Manager 설정 중..."
    
    # 예제 비밀 생성 (사용자가 실제 값으로 업데이트해야 함)
    secrets=(
        "binance-api-credentials:{\"api_key\":\"REPLACE_WITH_ACTUAL_KEY\",\"secret_key\":\"REPLACE_WITH_ACTUAL_SECRET\",\"sandbox\":true}"
        "database-credentials:{\"host\":\"localhost\",\"user\":\"letrade_user\",\"password\":\"REPLACE_WITH_ACTUAL_PASSWORD\",\"database\":\"letrade_db\",\"port\":5432}"
        "telegram-bot-credentials:{\"bot_token\":\"REPLACE_WITH_ACTUAL_TOKEN\",\"admin_chat_id\":\"REPLACE_WITH_ACTUAL_CHAT_ID\"}"
    )
    
    for secret_entry in "${secrets[@]}"; do
        secret_name=$(echo "$secret_entry" | cut -d: -f1)
        secret_value=$(echo "$secret_entry" | cut -d: -f2-)
        
        if ! gcloud secrets describe "$secret_name" &> /dev/null; then
            log "비밀 생성: $secret_name"
            echo "$secret_value" | gcloud secrets create "$secret_name" --data-file=-
        else
            log_success "비밀 '$secret_name' 이미 존재함"
        fi
    done
    
    log_warning "⚠️ 중요: Secret Manager의 비밀들을 실제 값으로 업데이트해야 합니다!"
    log "업데이트 방법:"
    log "  gcloud secrets versions add binance-api-credentials --data-file=binance_creds.json"
    log "  gcloud secrets versions add telegram-bot-credentials --data-file=telegram_creds.json"
    
    log_success "Secret Manager 설정 완료"
}

# 함수: Cloud SQL 설정
setup_cloud_sql() {
    log "Cloud SQL 설정 중..."
    
    instance_name="letrade-postgres"
    
    # Cloud SQL 인스턴스 확인
    if ! gcloud sql instances describe "$instance_name" &> /dev/null; then
        log "Cloud SQL PostgreSQL 인스턴스 생성 중... (시간이 걸릴 수 있습니다)"
        gcloud sql instances create "$instance_name" \
            --database-version=POSTGRES_14 \
            --tier=db-f1-micro \
            --region="$REGION" \
            --storage-type=SSD \
            --storage-size=10GB \
            --backup \
            --maintenance-window-day=SAT \
            --maintenance-window-hour=02
    else
        log_success "Cloud SQL 인스턴스 '$instance_name' 이미 존재함"
    fi
    
    # 데이터베이스 생성
    if ! gcloud sql databases describe letrade_db --instance="$instance_name" &> /dev/null; then
        log "데이터베이스 생성 중..."
        gcloud sql databases create letrade_db --instance="$instance_name"
    else
        log_success "데이터베이스 'letrade_db' 이미 존재함"
    fi
    
    # 사용자 생성
    if ! gcloud sql users describe letrade_user --instance="$instance_name" &> /dev/null; then
        log "데이터베이스 사용자 생성 중..."
        # 임시 비밀번호 생성
        temp_password=$(openssl rand -base64 32)
        gcloud sql users create letrade_user --instance="$instance_name" --password="$temp_password"
        
        log_warning "⚠️ 임시 데이터베이스 비밀번호: $temp_password"
        log "이 비밀번호를 Secret Manager의 database-credentials에 업데이트하세요"
    else
        log_success "데이터베이스 사용자 'letrade_user' 이미 존재함"
    fi
    
    log_success "Cloud SQL 설정 완료"
}

# 함수: 모니터링 설정
setup_monitoring() {
    log "모니터링 및 로깅 설정 중..."
    
    # 로그 싱크 생성
    if ! gcloud logging sinks describe letrade-error-sink &> /dev/null; then
        gcloud logging sinks create letrade-error-sink \
            bigquery.googleapis.com/projects/"$PROJECT_ID"/datasets/letrade_logs \
            --log-filter='severity>=ERROR AND resource.type="gce_instance"'
    fi
    
    # 알림 정책 설정을 위한 예제 (실제 구현 필요)
    log "모니터링 알림 정책은 Google Cloud Console에서 수동으로 설정하세요"
    log "추천 알림:"
    log "  - CPU 사용률 > 80%"
    log "  - 메모리 사용률 > 90%"
    log "  - 오류율 > 5%"
    
    log_success "모니터링 설정 완료"
}

# 함수: 환경변수 파일 생성
create_env_file() {
    log "환경변수 파일 생성 중..."
    
    cat > .env.gcp << EOF
# GCP Production Environment Configuration
GCP_PROJECT_ID=$PROJECT_ID
GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
ENVIRONMENT=production

# Database (Cloud SQL)
DATABASE_URL=postgresql://letrade_user:PASSWORD_FROM_SECRET@CLOUD_SQL_IP:5432/letrade_db

# RabbitMQ (Cloud Memorystore 또는 GCE)
RABBITMQ_URL=amqp://letrade_user:PASSWORD@RABBITMQ_IP:5672/

# Application Configuration
LOG_LEVEL=INFO
DRY_RUN=false

# Security
SECRET_FALLBACK_TO_ENV=false
SECRET_CACHE_ENABLED=true

# Region Settings
GCP_REGION=$REGION
GCP_ZONE=$ZONE
EOF

    log_success "환경변수 파일 '.env.gcp' 생성 완료"
    log_warning "⚠️ 실제 IP 주소와 비밀번호로 업데이트하세요"
}

# 함수: 배포 스크립트 생성
create_deployment_scripts() {
    log "배포 스크립트 생성 중..."
    
    # Docker 빌드 및 푸시 스크립트
    cat > scripts/build_and_push.sh << 'EOF'
#!/bin/bash
set -e

PROJECT_ID=${GCP_PROJECT_ID}
IMAGE_NAME="letrade-bot"
TAG=${1:-latest}

echo "🏗️ Building Docker image..."
docker build -t "gcr.io/$PROJECT_ID/$IMAGE_NAME:$TAG" .

echo "📤 Pushing to Container Registry..."
docker push "gcr.io/$PROJECT_ID/$IMAGE_NAME:$TAG"

echo "✅ Build and push completed!"
echo "Image: gcr.io/$PROJECT_ID/$IMAGE_NAME:$TAG"
EOF

    # Cloud Run 배포 스크립트
    cat > scripts/deploy_to_cloud_run.sh << 'EOF'
#!/bin/bash
set -e

PROJECT_ID=${GCP_PROJECT_ID}
REGION=${GCP_REGION:-asia-northeast3}
IMAGE_NAME="letrade-bot"
TAG=${1:-latest}

services=(
    "letrade-core-engine:core-engine"
    "letrade-capital-manager:capital-manager"
    "letrade-exchange-connector:exchange-connector"
    "letrade-telegram-bot:telegram-bot"
)

for service_config in "${services[@]}"; do
    service_name=$(echo "$service_config" | cut -d: -f1)
    letrade_service=$(echo "$service_config" | cut -d: -f2)
    
    echo "🚀 Deploying $service_name..."
    
    gcloud run deploy "$service_name" \
        --image="gcr.io/$PROJECT_ID/$IMAGE_NAME:$TAG" \
        --region="$REGION" \
        --platform=managed \
        --set-env-vars="ENVIRONMENT=production,LETRADE_SERVICE=$letrade_service,GCP_PROJECT_ID=$PROJECT_ID" \
        --service-account="letrade-bot@$PROJECT_ID.iam.gserviceaccount.com" \
        --memory=512Mi \
        --cpu=1 \
        --min-instances=1 \
        --max-instances=10 \
        --port=8000 \
        --timeout=900 \
        --no-allow-unauthenticated
done

echo "✅ All services deployed!"
EOF

    chmod +x scripts/build_and_push.sh
    chmod +x scripts/deploy_to_cloud_run.sh
    
    log_success "배포 스크립트 생성 완료"
}

# 함수: 최종 검증
final_verification() {
    log "설정 검증 중..."
    
    # 프로젝트 확인
    current_project=$(gcloud config get-value project)
    if [[ "$current_project" == "$PROJECT_ID" ]]; then
        log_success "프로젝트 설정: $current_project"
    else
        log_error "프로젝트 설정 오류"
    fi
    
    # 서비스 계정 확인
    if [[ -f "./service-account.json" ]]; then
        log_success "서비스 계정 키 파일 존재"
    else
        log_error "서비스 계정 키 파일 없음"
    fi
    
    # Secret Manager 확인
    secret_count=$(gcloud secrets list --format="value(name)" | wc -l)
    log_success "Secret Manager: $secret_count 개 비밀 설정됨"
    
    log_success "GCP 환경 설정 완료!"
}

# 메인 실행 함수
main() {
    log "🚀 Letrade_v1 GCP 환경 설정 시작"
    log "프로젝트 ID: $PROJECT_ID"
    log "리전: $REGION"
    log "================================================================"
    
    check_prerequisites
    setup_project
    enable_apis
    create_service_account
    setup_secret_manager
    setup_cloud_sql
    setup_monitoring
    create_env_file
    create_deployment_scripts
    final_verification
    
    log "================================================================"
    log_success "🎉 GCP 환경 설정 완료!"
    
    echo ""
    log_warning "📋 다음 단계:"
    log "1. Secret Manager의 실제 API 키들 업데이트"
    log "2. Cloud SQL 인스턴스 IP 주소 확인 및 환경변수 업데이트"
    log "3. 첫 배포 실행: ./scripts/build_and_push.sh"
    log "4. Cloud Run 서비스 배포: ./scripts/deploy_to_cloud_run.sh"
    
    echo ""
    log "📚 유용한 명령어들:"
    log "  gcloud secrets list                    # 비밀 목록 확인"
    log "  gcloud sql instances list              # Cloud SQL 인스턴스 목록"
    log "  gcloud run services list               # Cloud Run 서비스 목록"
    log "  gcloud builds submit                   # 빌드 실행"
}

# 스크립트 실행
main "$@"