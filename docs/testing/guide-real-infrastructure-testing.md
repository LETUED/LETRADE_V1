# 실제 인프라 통합 테스팅

이 문서는 Letrade_v1에서 실제 인프라(RabbitMQ, PostgreSQL, Redis)와 연동하는 테스팅 전략을 설명합니다.

## MVP 요구사항

CLAUDE.md 명시: **"mvp를 완료하려면 mock이 없는 상태로 모든 테스트를 통과해야한다"**

이 요구사항에 따라 모든 핵심 통합 테스트는 실제 인프라와 연동하여 목(mock) 없이 동작합니다.

## 테스트 환경 설정

### 1. Docker Compose 인프라 시작

```bash
# 실제 인프라 서비스 시작
docker-compose up -d

# 서비스 상태 확인
docker-compose ps
```

### 2. 서비스 확인

- **PostgreSQL**: localhost:5432 (letrade_user/letrade_password)
- **RabbitMQ**: localhost:5672 (AMQP), localhost:15672 (관리 UI)
- **Redis**: localhost:6379

## 실제 통합 테스트

### 메시지 버스 테스트

**위치**: `tests/integration/test_real_message_bus_integration.py`

#### 주요 테스트 케이스

1. **실제 RabbitMQ 연결 및 인프라 설정**
   ```bash
   pytest tests/integration/test_real_message_bus_integration.py::TestRealMessageBusIntegration::test_real_connection_and_infrastructure_setup -v
   ```

2. **실제 메시지 발행 및 소비**
   ```bash
   pytest tests/integration/test_real_message_bus_integration.py::TestRealMessageBusIntegration::test_real_message_publish_and_consume -v
   ```

3. **Core Engine 통합**
   ```bash
   pytest tests/integration/test_real_message_bus_integration.py::TestRealMessageBusIntegration::test_real_core_engine_message_bus_integration -v
   ```

4. **다중 메시지 버스 통신**
   ```bash
   pytest tests/integration/test_real_message_bus_integration.py::TestRealMessageBusIntegration::test_real_multiple_message_buses_communication -v
   ```

### 성능 테스트

#### 트레이딩 지연시간 요구사항 테스트

```bash
pytest tests/integration/test_real_message_bus_integration.py::TestRealMessageBusPerformance::test_real_trading_latency_requirements -v
```

**요구사항**: CLAUDE.md 명시된 200ms 미만 거래 실행 지연시간

### 전체 실제 통합 테스트 실행

```bash
# 모든 실제 통합 테스트 실행
pytest tests/integration/test_real_message_bus_integration.py -v

# 성능 테스트 포함
pytest tests/integration/test_real_message_bus_integration.py -v -m performance
```

## 테스트 아키텍처

### 실제 인프라 연동 특징

1. **목(Mock) 없는 테스트**: 모든 테스트가 실제 RabbitMQ 서버와 연결
2. **실제 메시지 흐름**: 진짜 메시지 발행/소비 검증
3. **성능 검증**: 실제 인프라에서의 지연시간 측정
4. **오류 처리**: 실제 환경에서의 데드레터 큐 동작 확인

### 테스트 패턴

```python
@pytest_asyncio.fixture
async def real_message_bus(self, rabbitmq_config):
    """실제 RabbitMQ와 연결된 메시지 버스."""
    message_bus = MessageBus(rabbitmq_config)
    
    # 실제 연결 시도 (최대 30초 대기)
    max_retries = 30
    for attempt in range(max_retries):
        if await message_bus.connect():
            break
        await asyncio.sleep(1)
    else:
        pytest.skip("RabbitMQ 서버에 연결할 수 없습니다.")
    
    yield message_bus
    await message_bus.disconnect()
```

## 메시지 라우팅 패턴

### 교환소 및 큐 설정

- **letrade.events** (topic): 시스템 이벤트
- **letrade.commands** (topic): 거래 명령
- **letrade.requests** (topic): 자본 할당 요청
- **letrade.dlx** (topic): 데드레터 교환소

### 라우팅 키 패턴

- `market_data.*`: 시장 데이터
- `commands.*`: 거래 명령
- `request.capital.#`: 자본 할당 요청 (하위 레벨 매칭)
- `events.system.*`: 시스템 이벤트

## 성능 기준

### 지연시간 요구사항

- **평균 지연시간**: < 200ms
- **최대 지연시간**: < 500ms
- **처리량**: > 50 msg/s

### 연결 성능

- **연결 시간**: < 2.0s
- **메시지 발행**: 100개 메시지 < 1.0s

## 트러블슈팅

### 일반적인 문제

1. **연결 실패**
   ```bash
   # Docker 서비스 상태 확인
   docker-compose ps
   
   # 포트 점유 확인
   lsof -i :5672
   ```

2. **메시지 수신 실패**
   - 라우팅 키 패턴 확인
   - 큐 바인딩 상태 확인
   - RabbitMQ 관리 UI에서 메시지 흐름 모니터링

3. **성능 이슈**
   - Docker 리소스 할당 확인
   - 네트워크 지연시간 측정
   - RabbitMQ 설정 최적화

## 금융 시스템 안전성

### 핵심 검증 항목

1. **메시지 지속성**: 중요한 거래 메시지는 persistent=True
2. **데드레터 큐**: 실패한 메시지의 적절한 처리
3. **오류 격리**: 개별 메시지 실패가 시스템 전체에 영향 없음
4. **상태 일관성**: 실제 인프라에서의 상태 동기화

### 테스트 커버리지

- **연결 안정성**: 재연결 및 복구 테스트
- **메시지 무결성**: 실제 전송에서의 데이터 보존
- **성능 검증**: 실제 환경에서의 지연시간 측정
- **오류 시나리오**: 실제 실패 상황 처리

## 결론

이 실제 인프라 통합 테스팅 전략을 통해:

- ✅ MVP 요구사항 충족 (목 없는 테스트)
- ✅ 금융 시스템 신뢰성 확보
- ✅ 실제 환경에서의 성능 검증
- ✅ 프로덕션 준비 완료

모든 테스트가 실제 인프라에서 성공적으로 동작하여, 시스템의 안정성과 신뢰성이 검증되었습니다.