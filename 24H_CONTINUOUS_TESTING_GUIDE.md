# 🔄 24시간 연속 드라이런 테스트 가이드

## 📋 **개요**

Letrade_v1 시스템의 안정성과 신뢰성을 검증하기 위한 24시간 연속 테스트 시스템입니다.

### 🎯 **테스트 목표**
- **안정성**: 99.9% 이상 성공률
- **성능**: 평균 레이턴시 <1ms 유지
- **신뢰성**: 24시간 무중단 운영
- **복구 능력**: 자동 오류 감지 및 복구

---

## 🚀 **실행 방법**

### **1. 빠른 테스트 (5분)**
```bash
python continuous_testing_system.py --quick
```

### **2. 전체 24시간 테스트**
```bash
python continuous_testing_system.py
```

### **3. 사용자 정의 기간**
```bash
export TEST_DURATION_HOURS=1.0  # 1시간 테스트
python continuous_testing_system.py
```

---

## 📊 **모니터링 메트릭**

### **실시간 메트릭**
- **총 연산 수**: 실행된 거래 시뮬레이션 횟수
- **성공률**: 성공한 연산의 비율 (목표: 99.9%)
- **평균 레이턴시**: 평균 응답 시간 (목표: <1ms)
- **피크 레이턴시**: 최대 응답 시간
- **오류 수**: 발생한 오류의 총 개수

### **5분마다 진행 보고**
```
📊 Progress Report
----------------------------------------
⏱️  Duration: 0.25 hours
🔢 Total Operations: 900
✅ Success Rate: 99.89%
⚡ Avg Latency: 0.653ms
🔥 Peak Latency: 2.1ms
⚠️  Errors: 1
🎉 EXCELLENT performance maintained
```

---

## 🎯 **성능 등급 기준**

### **A+ (Excellent)**
- 성공률: ≥99.9%
- 평균 레이턴시: <1ms
- 상태: 프로덕션 준비 완료

### **A (Very Good)**
- 성공률: ≥99.5%
- 평균 레이턴시: <5ms
- 상태: 고성능 거래 준비

### **B (Good)**
- 성공률: ≥99.0%
- 평균 레이턴시: <200ms
- 상태: MVP 요구사항 충족

### **C (Needs Improvement)**
- 성공률: <99.0% 또는 레이턴시 >200ms
- 상태: 성능 개선 필요

---

## 📄 **최종 보고서**

테스트 완료 후 다음과 같은 최종 보고서가 생성됩니다:

### **콘솔 출력**
```
🎯 24-Hour Continuous Test Final Report
============================================================
⏱️  Test Duration: 24.00 hours
🔢 Total Operations: 86,400
✅ Successful Operations: 86,315
❌ Failed Operations: 85
📊 Success Rate: 99.90%
⚡ Average Latency: 0.847ms
🔥 Peak Latency: 12.3ms
🚀 Min Latency: 0.412ms
⚠️  Total Errors: 85
🎉 EXCELLENT: Production-ready performance achieved!
```

### **JSON 보고서 파일**
```json
{
  "test_type": "24_hour_continuous_dry_run",
  "start_time": "2025-06-24T15:00:00Z",
  "end_time": "2025-06-25T15:00:00Z",
  "duration_hours": 24.0,
  "total_operations": 86400,
  "success_rate": 99.90,
  "average_latency_ms": 0.847,
  "peak_latency_ms": 12.3,
  "performance_grade": "A+",
  "targets_met": {
    "latency": true,
    "success_rate": true,
    "overall": true
  }
}
```

---

## 🔧 **시스템 기능**

### **자동 모니터링**
- 실시간 성능 추적
- 메모리 및 CPU 사용량 모니터링
- 자동 오류 감지 및 로깅

### **자동 복구**
- 연결 실패 시 자동 재연결
- 서킷 브레이커 패턴 적용
- 오류 발생 시 자동 복구 시도

### **안전한 종료**
- SIGINT/SIGTERM 신호 처리
- 우아한 종료 (Graceful Shutdown)
- 진행 중인 작업 완료 후 종료

---

## ⚠️ **주의사항**

### **시스템 요구사항**
- Python 3.11+
- 최소 1GB RAM
- 안정적인 네트워크 연결

### **테스트 환경**
- 드라이런 모드에서만 실행
- 실제 거래 없음 (Mock 데이터 사용)
- 로그 파일 자동 생성

### **리소스 관리**
- 로그 파일 크기 모니터링
- 메모리 사용량 주의
- 디스크 공간 확보

---

## 🎯 **MVP 검증 체크리스트**

### **✅ 필수 요구사항**
- [ ] 24시간 무중단 운영
- [ ] 99.9% 이상 성공률
- [ ] 평균 레이턴시 <1ms
- [ ] 자동 오류 복구
- [ ] 상세한 메트릭 수집

### **✅ 성능 목표**
- [ ] 초당 1회 이상 거래 시뮬레이션
- [ ] 피크 레이턴시 <10ms
- [ ] 메모리 사용량 <500MB
- [ ] CPU 사용률 <50%

### **✅ 안정성 검증**
- [ ] 네트워크 오류 복구
- [ ] 메모리 누수 없음
- [ ] 리소스 정리 완료
- [ ] 로그 무결성 확인

---

## 📈 **다음 단계**

### **테스트 통과 시**
1. 🎉 **MVP 완성 인증**
2. 🚀 **소액 실거래 테스트 준비**
3. 📊 **프로덕션 배포 계획**
4. 🔒 **보안 감사 진행**

### **테스트 실패 시**
1. ⚠️ **성능 이슈 분석**
2. 🔧 **시스템 최적화**
3. 🔄 **재테스트 실행**
4. 📋 **문제점 문서화**

---

## 🤖 **자동화 스크립트**

### **Jenkins/GitHub Actions 연동**
```yaml
name: 24h-continuous-test
on:
  schedule:
    - cron: '0 0 * * 0'  # 매주 일요일 실행
  
jobs:
  continuous-test:
    runs-on: ubuntu-latest
    timeout-minutes: 1500  # 25시간 타임아웃
    
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run 24h continuous test
        run: python continuous_testing_system.py
      
      - name: Upload test report
        uses: actions/upload-artifact@v3
        with:
          name: 24h-test-report
          path: '24h_test_report_*.json'
```

---

**🎯 이 24시간 연속 테스트를 통과하면 Letrade_v1 시스템이 프로덕션 환경에서 안정적으로 운영될 준비가 완료됩니다!**