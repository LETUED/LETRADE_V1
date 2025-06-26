# 배포 가이드

## 목차
1. [사전 요구사항](#사전-요구사항)
2. [로컬 배포](#로컬-배포)
3. [Docker 배포](#docker-배포)
4. [Google Cloud Platform 배포](#google-cloud-platform-배포)
5. [보안 설정](#보안-설정)
6. [모니터링 설정](#모니터링-설정)
7. [문제 해결](#문제-해결)

## 사전 요구사항

### 시스템 요구사항
- **OS**: Ubuntu 20.04+ / macOS 12+
- **CPU**: 4 cores 이상
- **RAM**: 8GB 이상
- **Storage**: 50GB 이상

### 소프트웨어 요구사항
- Python 3.11+
- Docker 20.10+
- Docker Compose 2.0+
- PostgreSQL 15+
- RabbitMQ 3.11+
- Redis 7+

## 로컬 배포

### 1. 환경 설정
```bash
# 프로젝트 클론
git clone https://github.com/your-org/letrade_v1.git
cd letrade_v1

# 환경 변수 설정
cp .env.example .env
# .env 파일 수정하여 실제 값 입력
```

### 2. 개발 환경 시작
```bash
# 자동 설정 스크립트
./scripts/setup_dev_env.sh

# 또는 수동 설정
python -m venv venv
source venv/bin/activate
pip install -e .
docker-compose up -d
alembic upgrade head
```

### 3. 서비스 시작
```bash
# 개별 서비스 시작
python -m src.core_engine.main &
python -m src.capital_manager.main &
python -m src.exchange_connector.main &

# 또는 전체 시작
./scripts/start_all.sh
```

## Docker 배포

### 1. Docker 이미지 빌드
```bash
# 프로덕션 이미지 빌드
docker build -t letrade:latest .

# 특정 서비스 빌드
docker build --build-arg LETRADE_SERVICE=core-engine -t letrade-core:latest .
```

### 2. Docker Compose 실행
```bash
# 개발 환경
docker-compose up -d

# 프로덕션 환경
docker-compose -f docker-compose.prod.yml up -d
```

### 3. 상태 확인
```bash
# 서비스 상태
docker-compose ps

# 로그 확인
docker-compose logs -f core-engine

# 컨테이너 진입
docker-compose exec core-engine bash
```

## Google Cloud Platform 배포

### 1. GCP 프로젝트 설정
```bash
# 프로젝트 생성
gcloud projects create letrade-prod

# 프로젝트 설정
gcloud config set project letrade-prod

# 필요한 API 활성화
gcloud services enable compute.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

### 2. 인프라 구축
```bash
# Cloud SQL 인스턴스 생성
gcloud sql instances create letrade-db \
  --database-version=POSTGRES_15 \
  --tier=db-g1-small \
  --region=us-central1

# Secret Manager에 API 키 저장
echo -n "your-binance-api-key" | \
  gcloud secrets create binance-api-key --data-file=-

# VPC 네트워크 설정
gcloud compute networks create letrade-network \
  --subnet-mode=custom

gcloud compute networks subnets create letrade-subnet \
  --network=letrade-network \
  --region=us-central1 \
  --range=10.0.0.0/24
```

### 3. Cloud Run 배포
```bash
# Cloud Build로 이미지 빌드 및 푸시
gcloud builds submit --config=cloudbuild.yaml

# Cloud Run 서비스 배포
gcloud run deploy letrade-core-engine \
  --image gcr.io/letrade-prod/letrade:latest \
  --platform managed \
  --region us-central1 \
  --set-env-vars="LETRADE_SERVICE=core-engine" \
  --vpc-connector=letrade-vpc-connector \
  --service-account=letrade-sa@letrade-prod.iam.gserviceaccount.com
```

### 4. 자동 스케일링 설정
```yaml
# cloud-run-service.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: letrade-core-engine
  annotations:
    run.googleapis.com/cpu-throttling: "false"
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/minScale: "1"
        autoscaling.knative.dev/maxScale: "10"
    spec:
      containerConcurrency: 100
      timeoutSeconds: 300
      containers:
      - image: gcr.io/letrade-prod/letrade:latest
        resources:
          limits:
            cpu: "2"
            memory: "4Gi"
```

## 보안 설정

### 1. API 키 관리
```bash
# GCP Secret Manager 사용
gcloud secrets create binance-api-key \
  --data-file=secrets/binance-api-key.txt

# 서비스 계정에 권한 부여
gcloud secrets add-iam-policy-binding binance-api-key \
  --member="serviceAccount:letrade-sa@project.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 2. 네트워크 보안
```bash
# 방화벽 규칙 설정
gcloud compute firewall-rules create allow-letrade-internal \
  --network=letrade-network \
  --allow=tcp:5432,tcp:5672,tcp:6379 \
  --source-tags=letrade-service \
  --target-tags=letrade-service

# IP 화이트리스트
gcloud sql instances patch letrade-db \
  --authorized-networks=35.235.240.0/20
```

### 3. SSL/TLS 설정
```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    server_name api.letrade.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 모니터링 설정

### 1. Prometheus 설정
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'letrade'
    static_configs:
      - targets: 
        - 'core-engine:9090'
        - 'capital-manager:9091'
        - 'exchange-connector:9092'
```

### 2. Grafana 대시보드
```bash
# Grafana 설치
docker run -d -p 3000:3000 \
  -v grafana-storage:/var/lib/grafana \
  grafana/grafana

# 대시보드 임포트
curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @dashboards/letrade-dashboard.json
```

### 3. 알림 설정
```yaml
# alerting-rules.yml
groups:
  - name: letrade_alerts
    rules:
    - alert: HighErrorRate
      expr: rate(letrade_errors_total[5m]) > 0.1
      for: 5m
      annotations:
        summary: "High error rate detected"
        
    - alert: LowCacheHitRate
      expr: letrade_cache_hit_rate < 0.5
      for: 10m
      annotations:
        summary: "Cache hit rate below 50%"
```

## 문제 해결

### 1. 일반적인 문제

#### 서비스가 시작되지 않음
```bash
# 로그 확인
docker-compose logs core-engine

# 포트 충돌 확인
netstat -tulpn | grep -E '5432|5672|6379|8000'

# 권한 문제
sudo chown -R $USER:$USER ./data
```

#### 데이터베이스 연결 실패
```bash
# PostgreSQL 상태 확인
docker-compose exec postgres pg_isready

# 연결 테스트
psql -h localhost -U letrade_user -d letrade_db

# 마이그레이션 재실행
alembic downgrade -1
alembic upgrade head
```

### 2. 성능 문제

#### 높은 CPU 사용률
```bash
# 프로세스 확인
htop

# 프로파일링
python -m cProfile -o profile.stats src/core_engine/main.py

# 분석
python -m pstats profile.stats
```

#### 메모리 누수
```bash
# 메모리 사용량 모니터링
docker stats

# 힙 덤프
import tracemalloc
tracemalloc.start()
# ... 코드 실행 ...
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
```

### 3. 복구 절차

#### 백업에서 복원
```bash
# 데이터베이스 백업
pg_dump -h localhost -U letrade_user letrade_db > backup.sql

# 복원
psql -h localhost -U letrade_user letrade_db < backup.sql
```

#### 긴급 정지
```bash
# 모든 거래 중지
bot-cli emergency-stop --reason="System maintenance"

# 서비스 중지
docker-compose stop

# 안전 모드로 재시작
LETRADE_SAFE_MODE=true docker-compose up
```

## 체크리스트

### 배포 전
- [ ] 모든 테스트 통과
- [ ] 환경 변수 확인
- [ ] 데이터베이스 백업
- [ ] 보안 설정 검토
- [ ] 리소스 할당 확인

### 배포 중
- [ ] 서비스 순차적 배포
- [ ] 헬스체크 확인
- [ ] 로그 모니터링
- [ ] 메트릭 확인

### 배포 후
- [ ] 시스템 상태 확인
- [ ] 성능 메트릭 검증
- [ ] 알림 시스템 테스트
- [ ] 백업 정책 확인