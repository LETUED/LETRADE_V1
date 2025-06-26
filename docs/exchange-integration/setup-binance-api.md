# Binance API 설정 가이드

## 1. Testnet API 키 생성 (개발/테스트용)

1. Binance Testnet 접속: https://testnet.binance.vision/
2. 계정 생성 또는 로그인
3. API Management 페이지로 이동
4. "Create API" 클릭
5. API 키와 Secret 키 저장

## 2. 실제 API 키 생성 (운영용)

1. Binance 메인넷 접속: https://www.binance.com/
2. 계정 설정 → API Management
3. "Create API" 클릭
4. 2FA 인증 완료
5. API 제한 설정:
   - Enable Reading ✓
   - Enable Spot Trading ✓ (필요시)
   - IP 제한 설정 (보안 강화)

## 3. 환경 변수 설정

`.env` 파일에 다음 추가:

```bash
# Testnet (개발용)
BINANCE_TESTNET_API_KEY=your_testnet_api_key_here
BINANCE_TESTNET_SECRET_KEY=your_testnet_secret_key_here
BINANCE_TESTNET=true

# Mainnet (운영용 - 주의!)
BINANCE_API_KEY=your_mainnet_api_key_here
BINANCE_SECRET_KEY=your_mainnet_secret_key_here
BINANCE_TESTNET=false
```

## 4. 보안 주의사항

- **절대 API 키를 Git에 커밋하지 마세요**
- 운영 환경에서는 GCP Secret Manager 사용
- IP 화이트리스트 설정 권장
- 최소한의 권한만 부여
- 정기적으로 API 키 재생성

## 5. 테스트

```bash
# API 연결 테스트
python scripts/test_binance_connection.py
```