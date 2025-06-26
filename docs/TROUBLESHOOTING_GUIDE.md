# 문제 해결 가이드

## 개요

Letrade_v1 시스템 운영 중 발생할 수 있는 일반적인 문제와 해결 방법을 설명합니다.

## 1. 시작/종료 문제

### 1.1 서비스가 시작되지 않음

#### 증상
```bash
$ python -m src.core_engine.main
Error: Failed to start Core Engine
```

#### 진단
```bash
# 포트 충돌 확인
netstat -tulpn | grep -E '5432|5672|6379|8000'

# Docker 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs postgres rabbitmq redis
```

#### 해결책
```bash
# 1. Docker 서비스 재시작
docker-compose down
docker-compose up -d

# 2. 포트 충돌 해결
sudo kill -9 $(lsof -t -i:5432)  # PostgreSQL
sudo kill -9 $(lsof -t -i:5672)  # RabbitMQ

# 3. 권한 문제 해결
sudo chown -R $USER:$USER ./data
chmod -R 755 ./data
```

### 1.2 데이터베이스 연결 실패

#### 증상
```
sqlalchemy.exc.OperationalError: could not connect to server
```

#### 진단
```bash
# PostgreSQL 상태 확인
docker-compose exec postgres pg_isready

# 연결 테스트
psql -h localhost -U letrade_user -d letrade_db
```

#### 해결책
```bash
# 1. 데이터베이스 재시작
docker-compose restart postgres

# 2. 연결 설정 확인
echo $DATABASE_URL

# 3. 마이그레이션 재실행
alembic downgrade -1
alembic upgrade head
```

## 2. 거래 관련 문제

### 2.1 거래 실행 실패

#### 증상
```
Trade execution failed: Insufficient balance
```

#### 진단
```python
# 잔고 확인 스크립트
from src.exchange_connector.main import ExchangeConnector

connector = ExchangeConnector()
balance = await connector.get_balance()
print(f"Available balance: {balance}")
```

#### 해결책
1. **잔고 부족**: 입금 또는 거래 크기 조정
2. **API 권한**: 거래 권한 활성화 확인
3. **최소 주문량**: 거래소 최소 주문량 확인

### 2.2 WebSocket 연결 끊김

#### 증상
```
WebSocket connection closed unexpectedly
```

#### 진단
```bash
# 네트워크 연결 확인
ping api.binance.com

# WebSocket 테스트
python scripts/test_websocket_connection.py
```

#### 해결책
```python
# 자동 재연결 설정
websocket_config = {
    'ping_interval': 20,
    'ping_timeout': 10,
    'reconnect_interval': 5,
    'max_reconnect_attempts': 10
}
```

## 3. 성능 문제

### 3.1 높은 CPU 사용률

#### 증상
- CPU 사용률 80% 이상
- 시스템 응답 지연

#### 진단
```bash
# 프로세스별 CPU 사용량
htop

# Python 프로파일링
python -m cProfile -o profile.stats src/core_engine/main.py
python -m pstats profile.stats
```

#### 해결책
1. **무한 루프 확인**
   ```python
   # 잘못된 코드
   while True:
       check_market()  # sleep 없음
   
   # 올바른 코드
   while True:
       check_market()
       await asyncio.sleep(1)
   ```

2. **워커 수 조정**
   ```yaml
   # config/settings.yaml
   workers:
     strategy_workers: 2  # CPU 코어 수에 맞게 조정
   ```

### 3.2 메모리 누수

#### 증상
- 메모리 사용량 지속적 증가
- Out of Memory 에러

#### 진단
```python
# 메모리 프로파일링
import tracemalloc

tracemalloc.start()
# ... 코드 실행 ...
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

for stat in top_stats[:10]:
    print(stat)
```

#### 해결책
1. **캐시 크기 제한**
   ```python
   cache = LocalCache(max_size=1000)  # 무제한 → 제한
   ```

2. **이벤트 리스너 정리**
   ```python
   # 리스너 등록 해제
   def cleanup():
       bus.unsubscribe_all()
   ```

## 4. 메시지 버스 문제

### 4.1 메시지 큐 과부하

#### 증상
```
RabbitMQ queue depth > 10000
```

#### 진단
```bash
# RabbitMQ 관리 UI
http://localhost:15672

# CLI로 큐 상태 확인
docker-compose exec rabbitmq rabbitmqctl list_queues
```

#### 해결책
1. **소비자 증가**
   ```python
   # 멀티 컨슈머 설정
   for i in range(4):
       asyncio.create_task(consume_messages())
   ```

2. **메시지 TTL 설정**
   ```python
   channel.queue_declare(
       queue='market_data',
       arguments={'x-message-ttl': 60000}  # 60초
   )
   ```

### 4.2 Dead Letter Queue 처리

#### 증상
```
Messages accumulating in DLQ
```

#### 진단
```python
# DLQ 메시지 확인
async def check_dlq():
    dlq_messages = await bus.get_dlq_messages()
    for msg in dlq_messages:
        logger.error(f"DLQ message: {msg}")
```

#### 해결책
```python
# DLQ 메시지 재처리
async def reprocess_dlq():
    while True:
        msg = await dlq.get_message()
        if msg:
            try:
                await process_message(msg)
                await dlq.ack(msg)
            except Exception as e:
                logger.error(f"Failed to reprocess: {e}")
```

## 5. 캐시 문제

### 5.1 캐시 히트율 낮음

#### 증상
```
Cache hit rate < 50%
```

#### 진단
```python
# 캐시 통계 확인
stats = cache_manager.get_stats()
print(f"Hit rate: {stats['hit_rate']}%")
print(f"Miss count: {stats['misses']}")
```

#### 해결책
1. **TTL 조정**
   ```python
   # 자주 사용되는 데이터는 TTL 증가
   @cached(ttl=3600)  # 1시간
   def get_portfolio_metrics():
       pass
   ```

2. **캐시 워밍**
   ```python
   async def warm_cache():
       # 시작 시 자주 사용되는 데이터 미리 로드
       await cache_manager.set("markets", await get_all_markets())
   ```

## 6. 보안 문제

### 6.1 API 키 인증 실패

#### 증상
```
401 Unauthorized: Invalid API credentials
```

#### 진단
```bash
# 환경 변수 확인
echo $BINANCE_API_KEY | wc -c  # 길이 확인
echo $BINANCE_API_KEY | head -c 5  # 앞 5자리만 확인
```

#### 해결책
1. **환경 변수 재설정**
   ```bash
   export BINANCE_API_KEY="your-key"
   export BINANCE_API_SECRET="your-secret"
   ```

2. **Secret Manager 확인**
   ```python
   secret = await secret_manager.get_secret("binance-api-key")
   print(f"Key exists: {bool(secret)}")
   ```

## 7. 로깅 및 디버깅

### 7.1 로그 레벨 조정

```python
# 디버깅을 위한 상세 로그
import logging
logging.getLogger().setLevel(logging.DEBUG)

# 특정 모듈만 디버그
logging.getLogger('src.capital_manager').setLevel(logging.DEBUG)
```

### 7.2 상관 ID 추적

```python
# 요청 추적을 위한 상관 ID
import uuid

correlation_id = str(uuid.uuid4())
logger.info("Processing trade", extra={'correlation_id': correlation_id})
```

## 8. 일반적인 에러 메시지

### 8.1 "Circuit breaker is open"
**원인**: 외부 API 반복 실패
**해결**: 5분 후 자동 복구, 또는 수동 리셋
```python
circuit_breaker.reset()
```

### 8.2 "Rate limit exceeded"
**원인**: API 호출 한도 초과
**해결**: 호출 빈도 조정
```python
exchange.enableRateLimit = True
exchange.rateLimit = 100  # ms between requests
```

### 8.3 "Database connection pool exhausted"
**원인**: 연결 풀 고갈
**해결**: 풀 크기 증가
```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10
)
```

## 9. 복구 절차

### 9.1 전체 시스템 재시작

```bash
#!/bin/bash
# safe_restart.sh

# 1. 거래 중지
bot-cli halt-trading

# 2. 서비스 중지
docker-compose down

# 3. 데이터 백업
pg_dump -h localhost -U letrade_user letrade_db > backup_$(date +%Y%m%d).sql

# 4. 서비스 시작
docker-compose up -d

# 5. 상태 확인
sleep 30
bot-cli status

# 6. 거래 재개
bot-cli resume-trading
```

### 9.2 데이터 복구

```bash
# PostgreSQL 복원
psql -h localhost -U letrade_user letrade_db < backup.sql

# Redis 데이터 복원
redis-cli --rdb dump.rdb
```

## 10. 지원 및 에스컬레이션

### 로그 수집
```bash
# 지원팀에 제공할 로그 수집
./scripts/collect_logs.sh

# 생성된 파일: logs_20240101_123456.tar.gz
```

### 문제 보고 템플릿
```markdown
**환경**:
- OS: Ubuntu 20.04
- Python: 3.11.5
- 배포 방식: Docker

**증상**:
[상세 설명]

**재현 단계**:
1. ...
2. ...

**에러 메시지**:
[전체 스택 트레이스]

**시도한 해결 방법**:
- ...
- ...
```