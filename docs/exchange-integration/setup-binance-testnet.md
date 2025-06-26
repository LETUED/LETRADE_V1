# Binance Testnet API 설정 가이드

## Spot Trading Testnet 설정

### 1. API 키 발급
1. https://testnet.binance.vision/ 접속
2. GitHub 계정으로 로그인
3. `Generate HMAC_SHA256 Key` 클릭하여 API 키 생성
4. API Key와 Secret Key를 안전하게 보관

### 2. 환경변수 설정
```bash
# .env 파일에 추가
BINANCE_TESTNET_API_KEY=your_testnet_api_key_here
BINANCE_TESTNET_SECRET_KEY=your_testnet_secret_key_here

# 테스트넷 기본 URL
BINANCE_TESTNET_BASE_URL=https://testnet.binance.vision/api/v3

# Testnet 모드 활성화
EXCHANGE_TESTNET_MODE=true
```

### 3. Exchange Connector 테스트 계획

#### Phase 1: 기본 연결 테스트
- [ ] API 키 인증 테스트
- [ ] 계정 정보 조회 (잔고 확인)
- [ ] 서버 시간 동기화 테스트
- [ ] Rate Limit 처리 테스트

#### Phase 2: 시장 데이터 테스트
- [ ] 심볼 정보 조회
- [ ] 현재 가격 조회
- [ ] Kline/Candlestick 데이터 조회
- [ ] 24hr Ticker 통계 조회

#### Phase 3: 주문 관리 테스트 (Paper Trading)
- [ ] 테스트 주문 생성 (LIMIT, MARKET)
- [ ] 주문 상태 조회
- [ ] 주문 취소
- [ ] 주문 히스토리 조회

#### Phase 4: 실시간 데이터 테스트
- [ ] WebSocket 연결 테스트
- [ ] 실시간 가격 스트림
- [ ] 계정 업데이트 스트림

### 4. 보안 고려사항

#### API 키 보안
- API 키는 환경변수나 Secret Manager에만 저장
- 코드에 하드코딩 절대 금지
- IP 화이트리스트 설정 권장

#### 권한 설정
- Testnet에서도 최소 권한 원칙 적용
- Spot Trading 권한만 활성화
- Withdrawal 권한은 비활성화

### 5. 테스트 시나리오

#### 기본 시나리오
```python
# 1. 연결 테스트
exchange = BinanceConnector(testnet=True)
assert exchange.test_connectivity()

# 2. 계정 정보 확인
account_info = exchange.get_account_info()
assert account_info['balances'] is not None

# 3. 심볼 정보 조회
symbol_info = exchange.get_symbol_info('BTCUSDT')
assert symbol_info['status'] == 'TRADING'

# 4. 현재 가격 조회
ticker = exchange.get_ticker('BTCUSDT')
assert ticker['price'] > 0
```

#### 거래 시나리오
```python
# 1. 테스트 주문 생성
order = exchange.create_order(
    symbol='BTCUSDT',
    side='BUY',
    type='LIMIT',
    quantity=0.001,
    price=30000.0,
    timeInForce='GTC'
)
assert order['orderId'] is not None

# 2. 주문 상태 확인
status = exchange.get_order_status('BTCUSDT', order['orderId'])
assert status['status'] in ['NEW', 'PARTIALLY_FILLED', 'FILLED']

# 3. 주문 취소
cancel_result = exchange.cancel_order('BTCUSDT', order['orderId'])
assert cancel_result['status'] == 'CANCELED'
```

### 6. 에러 처리 테스트

#### Rate Limiting
- 초당 요청 수 제한 테스트
- Exponential backoff 구현 확인

#### 네트워크 오류
- 연결 타임아웃 처리
- 재시도 로직 검증

#### API 오류
- 잘못된 파라미터 처리
- 권한 오류 처리
- 서버 오류 처리

### 7. 성능 테스트

#### 응답 시간 측정
- 각 API 엔드포인트별 응답 시간 측정
- 목표: 평균 < 200ms

#### 처리량 테스트
- 동시 요청 처리 능력 테스트
- 최대 RPS (Requests Per Second) 측정

### 8. 모니터링 및 로깅

#### 로그 수집
- 모든 API 요청/응답 로깅
- 에러 발생 시 상세 정보 기록

#### 메트릭 수집
- API 호출 성공률
- 평균 응답 시간
- 에러율 및 에러 타입별 분류

### 9. 다음 단계

1. **API 키 발급 및 기본 연결 테스트**
2. **Exchange Connector 구현 완성**
3. **통합 테스트 실행**
4. **성능 벤치마크**
5. **Production 환경 준비**

## 참고 링크

- [Binance Spot Testnet](https://testnet.binance.vision/)
- [Binance API Documentation](https://developers.binance.com/docs/binance-spot-api-docs)
- [CCXT Binance Integration](https://github.com/ccxt/ccxt/wiki/Manual#binance)