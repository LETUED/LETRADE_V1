# Binance API 연동 테스트 계획

## 📋 개요

Letrade_v1 시스템의 Binance API 연동을 위한 체계적인 테스트 계획서입니다.
Testnet 환경에서의 철저한 검증 후 Production 환경으로 단계적 전환을 목표로 합니다.

## 🎯 테스트 목적

1. **기능 검증**: 모든 API 기능이 정상 작동하는지 확인
2. **성능 검증**: 응답 시간 및 처리량 요구사항 만족 확인  
3. **안정성 검증**: 에러 상황에서의 복구 능력 확인
4. **보안 검증**: API 키 보안 및 접근 제어 확인
5. **통합 검증**: 전체 거래 파이프라인 동작 확인

---

## 📊 테스트 단계별 계획

### Phase 1: Testnet 기본 연결 테스트 (1일)

#### 1.1 환경 설정 테스트
- [ ] **Testnet API 키 발급 및 검증**
  - API 키 형식 확인
  - 권한 설정 확인 (spot trading)
  - IP 제한 설정 (선택사항)
  
- [ ] **환경별 설정 검증**
  - testnet/production 설정 분리 확인
  - 설정 파일 로드 테스트
  - 환경 변수 검증

#### 1.2 기본 API 연결 테스트
```python
# 테스트 시나리오
async def test_basic_connection():
    """기본 연결 테스트"""
    # 1. 인증 테스트
    assert await exchange.connect() == True
    
    # 2. 계정 정보 조회
    account = await exchange.get_account_balance()
    assert account is not None
    
    # 3. 시장 정보 조회
    markets = await exchange.get_market_data("BTC/USDT")
    assert len(markets) > 0
```

#### 1.3 Rate Limiting 테스트
- [ ] **요청 제한 확인**
  - 분당 요청 수 측정
  - Rate limit 도달 시 동작 확인
  - Circuit breaker 동작 확인

### Phase 2: Testnet 전체 기능 테스트 (2일)

#### 2.1 시장 데이터 테스트
- [ ] **Historical Data 조회**
  - 다양한 timeframe (1m, 5m, 1h) 테스트
  - 대량 데이터 조회 성능 테스트
  - 데이터 정합성 검증

- [ ] **Real-time Data Stream**
  - WebSocket 연결 안정성
  - 데이터 지연시간 측정
  - 연결 끊김 시 재연결 테스트

#### 2.2 주문 관리 테스트
- [ ] **주문 생성/취소**
  - Market 주문 테스트
  - Limit 주문 테스트  
  - 주문 취소 기능 테스트
  - 잘못된 주문 처리 테스트

- [ ] **주문 상태 추적**
  - 주문 상태 변화 모니터링
  - 부분 체결 처리
  - 체결 완료 알림

#### 2.3 포트폴리오 관리 테스트
- [ ] **잔고 조회 및 추적**
  - 실시간 잔고 업데이트
  - 다중 자산 관리
  - 잔고 변화 알림

### Phase 3: Testnet 통합 테스트 (2일)

#### 3.1 전체 거래 파이프라인 테스트
```python
# 통합 테스트 시나리오
async def test_full_trading_pipeline():
    """전체 거래 파이프라인 테스트"""
    # 1. 전략 신호 생성
    signal = strategy.generate_signal()
    
    # 2. Capital Manager 검증
    validation = await capital_manager.validate_trade(signal)
    assert validation.result == "approved"
    
    # 3. Exchange 주문 실행
    order = await exchange.place_order(validation.order_request)
    assert order.status == "filled"
    
    # 4. 상태 동기화 확인
    reconciliation = await reconciler.perform_reconciliation()
    assert reconciliation.discrepancies == 0
```

#### 3.2 에러 처리 테스트
- [ ] **네트워크 오류 시나리오**
  - 연결 끊김 처리
  - 타임아웃 처리
  - 재연결 로직 검증

- [ ] **API 오류 시나리오**
  - 잘못된 주문 처리
  - 잔고 부족 시나리오
  - Rate limit 초과 처리

#### 3.3 성능 및 스트레스 테스트
- [ ] **응답 시간 측정**
  - API 호출 평균/최대 응답 시간
  - WebSocket 메시지 지연 시간
  - 전체 거래 실행 시간 (<200ms 목표)

- [ ] **동시성 테스트**
  - 다중 전략 동시 실행
  - 동시 주문 처리
  - 리소스 경합 상황 테스트

### Phase 4: Production 준비 테스트 (1일)

#### 4.1 보안 검증
- [ ] **API 키 보안**
  - GCP Secret Manager 연동
  - API 키 암호화 저장
  - 권한 최소화 확인

- [ ] **접근 제어**
  - IP 제한 설정
  - 2FA 활성화 확인
  - 감사 로그 설정

#### 4.2 모니터링 설정
- [ ] **로깅 시스템**
  - 구조화된 로그 포맷
  - 로그 레벨 설정
  - 민감 정보 마스킹

- [ ] **알림 시스템**
  - 거래 실행 알림
  - 오류 발생 알림
  - 성능 임계값 알림

### Phase 5: Production 점진적 배포 (3일)

#### 5.1 소액 테스트 ($10-20)
```python
# 실제 거래 테스트 시나리오
TEST_SCENARIOS = [
    {
        "name": "small_buy_order",
        "symbol": "BTC/USDT", 
        "side": "buy",
        "amount": 0.0005,  # ~$20
        "type": "market"
    },
    {
        "name": "small_sell_order", 
        "symbol": "BTC/USDT",
        "side": "sell", 
        "amount": 0.0005,
        "type": "market"
    }
]
```

#### 5.2 중간 금액 테스트 ($50-100)
- [ ] **복수 전략 테스트**
  - 2-3개 전략 동시 운영
  - 포트폴리오 균형 유지
  - 리스크 분산 확인

#### 5.3 전체 시스템 운영
- [ ] **24시간 연속 운영**
  - 시스템 안정성 모니터링
  - 성능 지표 추적
  - 수익/손실 분석

---

## 🧪 자동화된 테스트 스위트

### 1. 단위 테스트 (Unit Tests)

```python
# tests/unit/test_exchange_environments.py
class TestExchangeEnvironments:
    def test_testnet_config(self):
        """Testnet 설정 테스트"""
        config = get_environment_config("testnet")
        assert config.sandbox == True
        assert config.base_url == "https://testnet.binance.vision"
    
    def test_production_config(self):
        """Production 설정 테스트"""
        config = get_environment_config("production")
        assert config.sandbox == False
        assert config.base_url == "https://api.binance.com"
    
    def test_config_validation(self):
        """설정 검증 테스트"""
        result = validate_environment_config("production", "test_key", "test_secret")
        assert result["valid"] == True
```

### 2. 통합 테스트 (Integration Tests)

```python
# tests/integration/test_binance_integration.py
@pytest.mark.asyncio
class TestBinanceIntegration:
    async def test_testnet_connection(self):
        """Testnet 연결 테스트"""
        config = ExchangeConfig(
            exchange_name="binance",
            api_key=os.getenv("BINANCE_TESTNET_API_KEY"),
            api_secret=os.getenv("BINANCE_TESTNET_SECRET"),
            environment="testnet"
        )
        
        connector = ExchangeConnector(config)
        assert await connector.connect() == True
        
    async def test_market_data_retrieval(self):
        """시장 데이터 조회 테스트"""
        data = await connector.get_market_data("BTC/USDT", "1m", 10)
        assert len(data) == 10
        assert all(isinstance(d, MarketData) for d in data)
```

### 3. E2E 테스트 (End-to-End Tests)

```python
# tests/e2e/test_full_trading_flow.py
@pytest.mark.asyncio
class TestFullTradingFlow:
    async def test_complete_trading_cycle(self):
        """완전한 거래 사이클 테스트"""
        # 1. 시스템 초기화
        engine = CoreEngine(test_config)
        await engine.start()
        
        # 2. 전략 실행
        strategy_config = StrategyConfig(
            strategy_id="test_ma_crossover",
            symbol="BTC/USDT",
            parameters={"fast": 5, "slow": 10}
        )
        
        success = await engine.start_strategy(strategy_config)
        assert success == True
        
        # 3. 거래 실행 대기 및 검증
        await asyncio.sleep(60)  # 1분 대기
        
        # 4. 시스템 종료
        await engine.stop()
```

---

## 📈 성공 지표 및 기준

### 1. 기능 기준
- [ ] **API 연결 성공률**: > 99.9%
- [ ] **주문 실행 성공률**: > 99.5%
- [ ] **WebSocket 연결 안정성**: > 99.9%
- [ ] **상태 동기화 정확도**: 100%

### 2. 성능 기준
- [ ] **API 응답 시간**: < 200ms (평균)
- [ ] **WebSocket 지연**: < 50ms
- [ ] **전체 거래 실행 시간**: < 500ms
- [ ] **시스템 가동률**: > 99.9%

### 3. 보안 기준
- [ ] **API 키 암호화**: 100%
- [ ] **IP 제한 설정**: 활성화
- [ ] **2FA 인증**: 활성화
- [ ] **감사 로그**: 완전성

### 4. 비즈니스 기준
- [ ] **슬리피지**: < 0.1%
- [ ] **거래 수수료**: 예상 범위 내
- [ ] **자금 안전성**: 100%
- [ ] **수익률 추적**: 정확성

---

## 🛠️ 테스트 도구 및 환경

### 1. 테스트 프레임워크
```python
# 필요한 도구들
pytest==7.4.0              # 테스트 프레임워크
pytest-asyncio==0.21.0     # 비동기 테스트 지원
pytest-mock==3.11.1        # 모킹 지원
pytest-cov==4.1.0          # 커버리지 측정
```

### 2. 모니터링 도구
- **성능 모니터링**: Prometheus + Grafana
- **로그 관리**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **알림 시스템**: Slack/Telegram 봇
- **에러 추적**: Sentry

### 3. 테스트 환경 설정
```yaml
# docker-compose.test.yml
version: '3.8'
services:
  letrade-test:
    build: .
    environment:
      - ENVIRONMENT=testnet
      - BINANCE_TESTNET_API_KEY=${BINANCE_TESTNET_API_KEY}
      - BINANCE_TESTNET_SECRET=${BINANCE_TESTNET_SECRET}
      - LOG_LEVEL=DEBUG
    depends_on:
      - postgres
      - rabbitmq
```

---

## 🚨 위험 관리 및 롤백 계획

### 1. 테스트 중 위험 요소
- **API 키 유출**: 즉시 키 폐기 및 재발급
- **예상치 못한 거래**: 긴급 정지 및 포지션 청산
- **시스템 오류**: 자동 롤백 및 안전 모드 전환

### 2. 롤백 절차
1. **즉시 조치** (5분 이내)
   - 모든 전략 중지
   - 신규 주문 차단
   - 현재 포지션 모니터링

2. **긴급 대응** (30분 이내)
   - 기술팀 소집
   - 문제 원인 분석
   - 임시 해결책 적용

3. **완전 복구** (24시간 이내)
   - 근본 원인 해결
   - 시스템 재시작
   - 전체 테스트 재실행

---

## ✅ 테스트 완료 체크리스트

### Phase 1: Testnet 기본 연결
- [ ] API 키 발급 및 검증 완료
- [ ] 환경별 설정 분리 완료
- [ ] 기본 API 연결 테스트 통과
- [ ] Rate limiting 테스트 통과

### Phase 2: Testnet 전체 기능
- [ ] 시장 데이터 테스트 통과
- [ ] 주문 관리 테스트 통과
- [ ] 포트폴리오 관리 테스트 통과
- [ ] WebSocket 안정성 확인

### Phase 3: Testnet 통합
- [ ] 전체 거래 파이프라인 테스트 통과
- [ ] 에러 처리 시나리오 테스트 통과
- [ ] 성능 기준 달성 (200ms 응답 시간)
- [ ] 스트레스 테스트 통과

### Phase 4: Production 준비
- [ ] 보안 검증 완료
- [ ] 모니터링 시스템 설정 완료
- [ ] 자동화된 테스트 스위트 구축
- [ ] 롤백 계획 수립 완료

### Phase 5: Production 배포
- [ ] 소액 테스트 성공 ($10-20)
- [ ] 중간 금액 테스트 성공 ($50-100)
- [ ] 24시간 연속 운영 성공
- [ ] 모든 성능 지표 달성

---

## 📚 참고 자료 및 문서

1. **Binance API 문서**: https://binance-docs.github.io/apidocs/spot/en/
2. **Testnet 가이드**: https://testnet.binance.vision/
3. **ccxt 문서**: https://docs.ccxt.com/
4. **프로젝트 아키텍처**: `/docs/design-docs/00_System_Overview_and_Architecture.md`

---

## 🎯 결론

이 테스트 계획을 통해 Binance API 연동의 모든 측면을 체계적으로 검증할 수 있습니다.
특히 Testnet에서의 철저한 테스트를 통해 Production 환경에서의 위험을 최소화하고,
안전하고 안정적인 거래 시스템 운영을 보장할 수 있습니다.

**다음 단계**: Testnet API 키 발급 및 Phase 1 테스트 시작