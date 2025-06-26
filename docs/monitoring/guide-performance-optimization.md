# 성능 최적화 가이드

## 개요
Letrade_v1 시스템의 성능 최적화 전략과 구현 방법을 설명합니다.

## 1. 캐싱 전략

### 1.1 계층적 캐싱
```python
# 로컬 메모리 캐시 (L1)
local_cache = LocalCache(max_size=1000, default_ttl=60)

# Redis 분산 캐시 (L2)
redis_cache = CacheManager(redis_url="redis://localhost:6379")
```

### 1.2 캐시 적용 대상
- **시장 데이터**: 1-5초 TTL
- **포트폴리오 메트릭**: 5분 TTL
- **전략 설정**: 1시간 TTL
- **성능 통계**: 1시간 TTL

### 1.3 캐시 데코레이터 사용
```python
@cached(ttl=300)  # 5분 캐시
async def get_portfolio_metrics(self, portfolio_id: int):
    # 비용이 큰 데이터베이스 쿼리
    pass
```

## 2. 데이터베이스 최적화

### 2.1 인덱스 전략
```sql
-- 자주 사용되는 쿼리에 대한 인덱스
CREATE INDEX idx_trades_strategy_created 
ON trades(strategy_id, created_at) 
WHERE status IN ('filled', 'partial');

-- 복합 인덱스
CREATE INDEX idx_positions_portfolio_open 
ON positions(portfolio_id, is_open) 
WHERE is_open = TRUE;
```

### 2.2 쿼리 최적화
- **N+1 쿼리 방지**: `selectinload`, `joinedload` 사용
- **배치 처리**: 개별 삽입 대신 `bulk_insert_mappings`
- **페이지네이션**: 대량 데이터 조회 시 limit/offset

### 2.3 파티셔닝
```sql
-- trades 테이블 월별 파티셔닝
CREATE TABLE trades_2024_01 PARTITION OF trades
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

## 3. 비동기 처리 최적화

### 3.1 동시성 제어
```python
# 동시 실행 제한
semaphore = asyncio.Semaphore(10)

async def process_trade():
    async with semaphore:
        # 처리 로직
        pass
```

### 3.2 배치 처리
```python
# 개별 처리 대신 배치로
async def batch_update_positions(updates: List[Dict]):
    await repository.update_position_batch(updates)
```

## 4. WebSocket 최적화

### 4.1 연결 풀링
```python
# 연결 재사용
ws_manager = WebSocketStreamManager(max_connections=10)
```

### 4.2 메시지 압축
```python
# 대용량 데이터 압축
compressed_data = zlib.compress(json.dumps(data).encode())
```

## 5. 성능 모니터링

### 5.1 메트릭 수집
```python
@profile_async("trade_execution")
async def execute_trade():
    # 자동으로 성능 측정
    pass
```

### 5.2 병목 현상 감지
```python
report = monitor.get_performance_report()
bottlenecks = report['bottlenecks']  # P95 > 500ms
```

## 6. 성능 목표

### 6.1 레이턴시 목표
- **거래 실행**: < 200ms
- **시장 데이터 조회**: < 10ms (캐시 히트)
- **포트폴리오 계산**: < 50ms
- **WebSocket 메시지**: < 5ms

### 6.2 처리량 목표
- **동시 거래**: 100+ TPS
- **WebSocket 연결**: 1000+ 동시 연결
- **메시지 처리**: 10,000+ msg/s

## 7. 최적화 체크리스트

### 7.1 개발 시
- [ ] 캐시 적용 검토
- [ ] 쿼리 실행 계획 확인
- [ ] 비동기 처리 활용
- [ ] 배치 처리 가능성 검토

### 7.2 배포 전
- [ ] 부하 테스트 실행
- [ ] 성능 프로파일링
- [ ] 리소스 사용량 확인
- [ ] 병목 현상 해결

### 7.3 운영 중
- [ ] 성능 메트릭 모니터링
- [ ] 캐시 히트율 확인
- [ ] 느린 쿼리 분석
- [ ] 리소스 스케일링

## 8. 문제 해결

### 8.1 높은 CPU 사용률
- 비효율적인 알고리즘 검토
- 무한 루프 확인
- 워커 수 조정

### 8.2 메모리 누수
- 캐시 크기 제한 확인
- 이벤트 리스너 정리
- 대용량 객체 참조 해제

### 8.3 느린 응답 시간
- 캐시 미스 확인
- 데이터베이스 인덱스 검토
- 네트워크 레이턴시 확인

## 9. 성능 테스트

### 9.1 단위 성능 테스트
```bash
pytest tests/test_performance_optimization.py -v
```

### 9.2 부하 테스트
```bash
locust -f tests/load_test.py --host=http://localhost:8000
```

### 9.3 프로파일링
```bash
python -m cProfile -o profile.stats src/main.py
```

## 10. 모범 사례

1. **측정 후 최적화**: 추측하지 말고 측정하라
2. **점진적 개선**: 큰 변경보다 작은 개선을 반복
3. **캐시 무효화**: 적절한 TTL과 무효화 전략
4. **리소스 제한**: 무제한 성장 방지
5. **모니터링**: 실시간 성능 추적