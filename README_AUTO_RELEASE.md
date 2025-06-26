# 🚀 완전 자동화된 GitHub Stable 브랜치 릴리즈 시스템

## 📋 시스템 개요

**완전 자동화된 워크플로우**: 코드 변경 → 테스트 → 릴리즈 → Stable 브랜치 배포

```
개발자 작업 → 자동 테스트 → 자동 릴리즈 → Stable 브랜치
     ↓             ↓             ↓            ↓
   git push    GitHub Actions  Version Bump   Production Ready
```

## ⚡ 빠른 사용법

### 1. 원클릭 릴리즈 (가장 간단)

```bash
# 개발 완료 후 한 번에 테스트 + 커밋 + 릴리즈
./scripts/quick_release.sh "feat: add new trading strategy"

# 또는 자동 커밋 메시지로
./scripts/quick_release.sh
```

### 2. 전통적인 Git 워크플로우

```bash
# 일반적인 개발 과정
git add .
git commit -m "feat: implement advanced risk management"
git push origin main

# → 자동으로 GitHub Actions 트리거됨
# → 3-5분 후 stable 브랜치에 자동 릴리즈
```

### 3. 수동 릴리즈 (고급 사용자)

```bash
# 로컬에서 직접 릴리즈 실행
./scripts/release_to_stable.sh
```

## 🔄 자동화 플로우 상세

### GitHub Actions 자동 릴리즈 워크플로우

**트리거 조건:**
- `main` 브랜치에 푸시
- 문서 파일(*.md) 변경은 제외
- `[skip release]` 커밋 메시지 시 건너뛰기

**자동 실행 단계:**

1. **🧪 전체 테스트 검증 (3-5분)**
   ```
   ✅ 보안 스캔 (하드코딩 시크릿 체크)
   ✅ 코드 품질 (Black, isort, flake8)
   ✅ 단위 테스트 (70%+ 커버리지)
   ✅ 통합 테스트 (핵심 시나리오)
   ✅ Docker 빌드 검증
   ```

2. **🚀 자동 릴리즈 생성 (1-2분)**
   ```
   📝 Semantic Versioning 자동 계산
   🌟 Stable 브랜치 생성/업데이트
   🏷️ Git 태그 자동 생성
   📋 릴리즈 노트 자동 생성
   📤 GitHub Release 발행
   ```

3. **📢 완료 알림**
   ```
   🎉 성공 시 상세 정보 표시
   🌐 GitHub Release 링크 제공
   📊 배포 준비 완료 상태 확인
   ```

### 버전 관리 (Semantic Versioning)

**자동 버전 증가 규칙:**
- `feat!:` 또는 `BREAKING CHANGE` → **Major** (1.0.0 → 2.0.0)
- `feat:` → **Minor** (1.0.0 → 1.1.0)  
- `fix:`, `docs:`, 기타 → **Patch** (1.0.0 → 1.0.1)

**커밋 메시지 예시:**
```bash
# Major 버전 업
git commit -m "feat!: redesign trading engine API"

# Minor 버전 업
git commit -m "feat: add RSI strategy implementation"

# Patch 버전 업  
git commit -m "fix: resolve connection timeout issue"
git commit -m "docs: update API documentation"
```

## 📊 릴리즈 상태 확인

### 실시간 진행 상황

```bash
# GitHub Actions 상태 확인
gh run list --workflow="Auto Release to Stable"

# 최신 릴리즈 확인
gh release list --limit 5
```

### 브랜치 및 태그 상태

```bash
# 최신 stable 브랜치 확인
git ls-remote origin stable

# 모든 릴리즈 태그 확인
git tag -l "v*" --sort=-version:refname | head -10
```

## 🛠️ 고급 설정

### 수동 릴리즈 타입 지정

GitHub Actions에서 수동 트리거 시 릴리즈 타입 선택 가능:

```bash
# GitHub 웹 인터페이스에서:
# Actions → Auto Release to Stable → Run workflow
# → Release Type: patch/minor/major 선택
```

### 릴리즈 건너뛰기

```bash
# 특정 커밋에서 릴리즈 건너뛰기
git commit -m "docs: update README [skip release]"
```

### 환경변수 설정

`.env` 파일에서 알림 설정:
```bash
# 텔레그램 알림 (선택적)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## 🔧 문제 해결

### 일반적인 문제

**1. 자동 릴리즈가 실행되지 않음**
```bash
# 원인 체크
- GitHub Actions 활성화 확인
- 커밋 메시지에 [skip release] 포함 여부
- 문서 파일만 변경했는지 확인

# 해결책
git push origin main --force-with-lease
```

**2. 테스트 실패로 릴리즈 중단**
```bash
# 로컬에서 테스트 재실행
./scripts/test_local.sh

# 문제 수정 후 다시 푸시
git add . && git commit -m "fix: resolve test failures"
git push origin main
```

**3. 버전 충돌**
```bash
# VERSION 파일 수동 수정
echo "1.2.3" > VERSION
git add VERSION
git commit -m "chore: fix version conflict"
```

### 수동 복구

```bash
# 실패한 릴리즈 수동 완료
./scripts/release_to_stable.sh

# Stable 브랜치 강제 업데이트
git checkout stable
git reset --hard main
git push origin stable --force-with-lease
```

## 📋 워크플로우 커스터마이징

### GitHub Actions 수정

`.github/workflows/auto-release.yml` 파일에서:

- **테스트 타임아웃 조정**: `timeout-minutes: 15`
- **커버리지 요구사항**: `--cov-fail-under=70`
- **실행 조건 변경**: `paths-ignore` 섹션

### 로컬 스크립트 수정

`scripts/release_to_stable.sh`에서:

- **알림 설정 추가**
- **추가 테스트 단계**  
- **배포 후 작업**

## 🎯 모범 사례

### 개발 워크플로우 권장사항

1. **기능 개발**
   ```bash
   # 새 기능 브랜치 (선택적)
   git checkout -b feature/new-strategy
   
   # 개발 및 로컬 테스트
   ./scripts/test_local.sh
   
   # 커밋 및 푸시
   git add .
   git commit -m "feat: implement momentum strategy"
   ```

2. **통합 및 릴리즈**
   ```bash
   # Main 브랜치로 통합
   git checkout main
   git merge feature/new-strategy
   
   # 빠른 릴리즈 (권장)
   ./scripts/quick_release.sh "feat: add momentum trading strategy"
   ```

3. **프로덕션 배포**
   ```bash
   # Stable 브랜치에서 배포
   git checkout stable
   git pull origin stable
   ./scripts/deploy_production.sh
   ```

### 커밋 메시지 가이드라인

```bash
# 좋은 예시
feat: add RSI indicator with custom periods
fix: resolve WebSocket connection timeout
docs: update trading strategy documentation
perf: optimize order execution latency

# 나쁜 예시  
update stuff
fix bug
wip
temp commit
```

## 🌐 GitHub 인터페이스 활용

### 릴리즈 페이지 확인

1. **GitHub Repository** → **Releases**
2. **최신 릴리즈 확인**
3. **Assets 다운로드** (Docker 이미지 등)
4. **릴리즈 노트 검토**

### Actions 모니터링

1. **GitHub Repository** → **Actions**
2. **Auto Release to Stable** 워크플로우 선택
3. **실시간 로그 확인**
4. **실패 시 디버그 정보 확인**

---

## 🎉 완전 자동화된 릴리즈 시스템의 이점

✅ **개발 효율성**: 수동 작업 90% 감소  
✅ **오류 방지**: 자동 테스트로 품질 보장  
✅ **일관성**: 표준화된 릴리즈 프로세스  
✅ **추적성**: 모든 릴리즈 히스토리 자동 기록  
✅ **안정성**: Stable 브랜치는 항상 배포 가능한 상태  

**이제 `git push origin main` 한 번으로 전체 릴리즈 파이프라인이 자동 실행됩니다!** 🚀