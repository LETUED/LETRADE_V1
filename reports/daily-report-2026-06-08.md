# LETRADE_V1 Daily Report — 2026-06-08

## 1. 열린 이슈 / PR 상태

### Issues (열린 이슈)
- **총 열린 이슈: 0개** — 현재 등록된 오픈 이슈 없음.

### Pull Requests (열린 PR: 3개)

| # | 제목 | 브랜치 | 베이스 | 상태 | 생성일 |
|---|------|--------|--------|------|--------|
| [#6](https://github.com/LETUED/LETRADE_V1/pull/6) | feat: Complete BaseStrategy implementation and real infrastructure testing | `feature/message-bus-integration` | `dev` | Open | 2025-06-23 |
| [#4](https://github.com/LETUED/LETRADE_V1/pull/4) | Add claude GitHub actions 1750667991168 | `add-claude-github-actions-1750667991168` | `main` | Open | 2025-06-23 |
| [#3](https://github.com/LETUED/LETRADE_V1/pull/3) | Add claude GitHub actions 1750667991184 | `add-claude-github-actions-1750667991184` | `main` | Open | 2025-06-23 |

#### PR #6 상세 메모
- BaseStrategy 추상 클래스, PerformanceTracker, 실제 RabbitMQ 연동 포함
- 테스트 결과: 실제 인프라 테스트 10/10 통과, BaseStrategy 단위 테스트 20/21 통과 (95.2%)
- **주의**: CI 환경의 Python 경로 설정 문제로 CI 단위 테스트 실패 중 (코드 자체 문제 아님)
- 커버리지: BaseStrategy 69%, 전체 35%

#### PR #3 / #4 상세 메모
- 중복 PR (같은 SHA: `30930d0`), 동일 내용의 GitHub Actions 설정 추가 브랜치
- 두 PR 중 하나 정리 필요

---

## 2. TODO / FIXME 코멘트 스캔

총 **24개** TODO 발견 (스크립트 제외 실제 소스 기준 **21개**)

### 우선순위 HIGH — 핵심 기능 미구현

| 파일 | 라인 | 내용 |
|------|------|------|
| `src/web_interface/main.py` | 625 | TODO: 실제 JWT 검증 구현 (보안 위험) |
| `src/exchange_connector/main.py` | 569 | TODO: Add real exchange connectors (Binance, Coinbase 등) |
| `src/data_loader/backtest_data_loader.py` | 347 | TODO: GCP Secret Manager에서 API 키 로드 필요 |

### 우선순위 MEDIUM — 기능 안정성

| 파일 | 라인 | 내용 |
|------|------|------|
| `src/core_engine/main.py` | 921 | TODO: Implement operation stopping logic |
| `src/core_engine/main.py` | 929 | TODO: Implement active operation waiting logic |
| `src/core_engine/main.py` | 955 | TODO: Shutdown other components |
| `src/core_engine/main.py` | 981 | TODO: Implement state persistence |
| `src/core_engine/main.py` | 1125 | TODO: Collect and emit system metrics |
| `src/core_engine/main.py` | 1149 | TODO: Load configuration from environment/files |
| `src/web_interface/main.py` | 544 | TODO: 실제 텔레그램 상태 확인 |
| `src/strategies/base_strategy.py` | 677 | TODO: 실제 DB 연결 상태 확인 |

### 우선순위 LOW — 리팩토링 / 통합 연기

| 파일 | 라인 | 내용 |
|------|------|------|
| `src/capital_manager/main.py` | 367 | TODO: Exchange Connector와 통합 |
| `src/capital_manager/main.py` | 495 | TODO: MessageBus unsubscribe 구현 필요 |
| `src/capital_manager/refactored_main.py` | 367 | TODO: Exchange Connector와 통합 (중복) |
| `src/capital_manager/refactored_main.py` | 495 | TODO: MessageBus unsubscribe 구현 필요 (중복) |
| `src/capital_manager/main_backup.py` | 696~1098 | TODO 9건 (백업 파일, 우선순위 낮음) |

---

## 3. 의존성 버전 체크

### requirements.txt / pyproject.toml 기준 주요 패키지

| 패키지 | 지정 최소 버전 | 비고 |
|--------|--------------|------|
| ccxt | >=4.0.0 | 거래소 API 통합 — 최신 4.x 시리즈 활발히 업데이트 중 |
| pandas | >=2.0.0 | 안정 |
| **pandas-ta** | **>=0.3.14b** | **⚠️ 베타 버전 고정 — 공식 릴리즈 확인 필요** |
| numpy | >=1.24.0 | 안정 |
| sqlalchemy | >=2.0.0 | 안정 |
| alembic | >=1.12.0 | 안정 |
| pika | >=1.3.0 | 안정 |
| aio-pika | >=9.0.0 | 안정 |
| fastapi | >=0.100.0 | 안정 (0.11x 시리즈 최신) |
| uvicorn | >=0.23.0 | 안정 |
| pydantic | >=2.0.0 | v2 마이그레이션 완료 여부 확인 권장 |
| python-telegram-bot | >=20.0 | v21.x 릴리즈됨 — 업그레이드 검토 |
| cryptography | >=41.0.0 | 보안 패키지 — 최신 유지 권장 |
| google-cloud-secret-manager | >=2.16.0 | 안정 |
| tensorflow | >=2.13.0 (ml extra) | ⚠️ TF 2.x → TF 3.x 전환 시기 주시 필요 |
| torch | >=2.0.0 (ml extra) | PyTorch 2.x 안정 |

### 주요 이슈 요약
1. **`pandas-ta>=0.3.14b`** — 베타(`b`) 버전을 명시. PyPI 공식 안정 릴리즈 여부 확인 후 고정 버전 업데이트 권장.
2. **`python-telegram-bot`** — v21.x 릴리즈 이후 v20 API 일부 deprecated. 업그레이드 검토.
3. **`cryptography`** — 보안 취약점 패치가 자주 릴리즈됨. `>=41.0.0` 대신 더 최신 버전으로 하한 올리는 것 권장.
4. **Python 버전** — `pyproject.toml`에 `>=3.11` 지정. 3.12 지원 명시되어 있음. 3.13 지원 여부 미검증.

---

## 4. 액션 아이템 요약

| 우선순위 | 항목 |
|---------|------|
| 🔴 HIGH | `src/web_interface/main.py:625` JWT 검증 실제 구현 |
| 🔴 HIGH | PR #3 / #4 중복 PR 정리 (하나 close) |
| 🔴 HIGH | PR #6 CI Python 경로 문제 해결 후 머지 |
| 🟡 MEDIUM | `src/exchange_connector/main.py:569` 실거래소 커넥터 추가 |
| 🟡 MEDIUM | `src/core_engine/main.py` shutdown / state persistence TODOs 구현 |
| 🟡 MEDIUM | `pandas-ta` 베타 버전 → 안정 버전 확인 및 고정 |
| 🟢 LOW | `src/capital_manager/main_backup.py` — 백업 파일 보관 필요성 검토 (삭제 or 정리) |
| 🟢 LOW | `python-telegram-bot` v21 업그레이드 검토 |
