# 🚀 Letrade_v1 배포 및 운영 가이드

## 📋 빠른 시작 가이드

### 1. 로컬 개발 환경 설정

```bash
# 1. Git 훅 설정 (한 번만 실행)
./scripts/setup_git_hooks.sh

# 2. 개발 의존성 설치
pip install -e ".[dev]"

# 3. 빠른 테스트 (푸시 전)
./scripts/test_local.sh

# 4. 전체 테스트 (필요시)
./scripts/test_full.sh
```

### 2. 프로덕션 배포

```bash
# 1. 환경 설정 파일 준비
cp .env.prod.example .env.production
# .env.production 파일 편집 필요

# 2. 프로덕션 배포
./scripts/deploy_production.sh

# 3. 시스템 모니터링 시작
./scripts/monitor_system.sh
```

## 🔧 개발 워크플로우

### 일상적인 개발 작업

```bash
# 코드 수정 후
git add .                    # 자동 포맷팅 실행 (pre-commit)
git commit -m "feat: ..."    # 커밋 메시지 템플릿 가이드
git push origin main         # 자동 로컬 테스트 실행 (pre-push)
```

### CI/CD 파이프라인

**간소화된 GitHub Actions:**
- ✅ **기본 검증** (3분): 문법 체크, 포맷팅 확인
- ✅ **전체 테스트** (10분): `[test-all]` 커밋 메시지 시 실행
- ✅ **수동 배포**: GitHub Actions에서 수동 트리거

### 로컬 테스트 우선 전략

- **빠른 검증**: `./scripts/test_local.sh` (1분 이내)
- **상세 검증**: `./scripts/test_full.sh` (5분 이내)
- **CI 의존도 최소화**: 로컬에서 모든 검증 완료

## 🏗️ 24/7 운영 환경

### 프로덕션 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                  24/7 Production Stack                  │
├─────────────────────────────────────────────────────────┤
│  🚀 Letrade Main App    │  📊 Monitoring Stack         │
│  • Auto-restart         │  • Prometheus (metrics)       │
│  • Health checks        │  • Grafana (dashboards)       │
│  • Rolling deployment   │  • Real-time alerts          │
├─────────────────────────────────────────────────────────┤
│  💾 Data Layer         │  🔄 Message Bus               │
│  • PostgreSQL          │  • RabbitMQ                   │
│  • Redis (cache)       │  • Auto-recovery              │
│  • Auto-backup         │  • Queue monitoring           │
└─────────────────────────────────────────────────────────┘
```

### 자동 기능

- **🔄 자동 재시작**: 서비스 장애 시 자동 복구
- **💾 자동 백업**: 매일 새벽 2시 데이터베이스 백업
- **📊 실시간 모니터링**: 60초마다 시스템 상태 확인
- **🚨 자동 알림**: 텔레그램으로 즉시 알림 발송

### 운영 명령어

```bash
# 상태 확인
docker-compose -f docker-compose.production.yml ps

# 로그 확인
docker-compose -f docker-compose.production.yml logs -f letrade-main

# 서비스 재시작
docker-compose -f docker-compose.production.yml restart letrade-main

# 전체 시스템 종료
docker-compose -f docker-compose.production.yml down

# 백업 확인
ls -la backups/
```

## 📊 모니터링 및 알림

### 대시보드 접근

- **메인 애플리케이션**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **헬스체크**: http://localhost:8000/health
- **Grafana 모니터링**: http://localhost:3000 (admin/admin123)
- **Prometheus 메트릭**: http://localhost:9090
- **RabbitMQ 관리**: http://localhost:15672 (guest/guest)

### 알림 설정

```bash
# .env.production에 추가
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 모니터링 지표

- **시스템 리소스**: CPU, 메모리, 디스크 사용률
- **서비스 상태**: 모든 마이크로서비스 헬스체크
- **거래 성능**: 거래 실행 시간, 성공률
- **데이터베이스**: 연결 상태, 쿼리 성능

## 🛡️ 보안 및 백업

### 보안 체크리스트

- ✅ **환경변수 분리**: 시크릿은 .env.production에만 저장
- ✅ **API 키 암호화**: GCP Secret Manager 사용 권장
- ✅ **네트워크 격리**: Docker 네트워크 분리
- ✅ **로그 마스킹**: 민감정보 자동 마스킹

### 백업 전략

```bash
# 수동 백업
./scripts/backup_system.sh

# 백업 확인
ls -la backups/

# 복구 (필요시)
./scripts/restore_system.sh [backup_date]
```

## 🚨 문제 해결

### 일반적인 문제

**1. 로컬 테스트 실패**
```bash
# 의존성 재설치
pip install -e ".[dev]" --force-reinstall

# 포맷팅 수정
black src/ tests/
isort src/ tests/

# 다시 테스트
./scripts/test_local.sh
```

**2. Docker 빌드 실패**
```bash
# 캐시 클리어
docker system prune -f

# 다시 빌드
docker-compose -f docker-compose.production.yml build --no-cache
```

**3. 서비스 응답 없음**
```bash
# 로그 확인
docker-compose -f docker-compose.production.yml logs letrade-main

# 컨테이너 재시작
docker-compose -f docker-compose.production.yml restart letrade-main
```

### 긴급 상황 대응

**거래 시스템 중단 시:**
1. **즉시 수동 개입**: 활성 포지션 확인
2. **로그 분석**: `docker logs letrade-main`
3. **서비스 재시작**: `docker-compose restart letrade-main`
4. **백업에서 복구**: 최악의 경우

## 📈 성능 최적화

### 권장 설정

```yaml
# docker-compose.production.yml
services:
  letrade-main:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 1G
        reservations:
          cpus: '1.0'
          memory: 512M
```

### 성능 모니터링

```bash
# 실시간 성능 확인
./scripts/monitor_system.sh 30  # 30초마다 체크

# 성능 벤치마크
./scripts/test_performance.sh
```

## 🎯 다음 단계

### 즉시 실행 가능

1. **소액 실거래 테스트**: $100 환경에서 실제 거래 테스트
2. **알림 시스템 설정**: 텔레그램 봇 토큰 설정
3. **대시보드 커스터마이징**: Grafana 대시보드 개인화

### 중장기 개선

1. **클라우드 배포**: GCP Cloud Run으로 확장
2. **고가용성 구성**: 다중 인스턴스 배포
3. **자동 스케일링**: 부하에 따른 자동 확장/축소

---

**🎉 축하합니다! Letrade_v1이 24/7 프로덕션 환경에서 실행 준비가 완료되었습니다.**