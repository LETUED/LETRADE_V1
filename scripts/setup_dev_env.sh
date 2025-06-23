#!/bin/bash

# =============================================================================
# Letrade_v1 개발 환경 설정 스크립트
# =============================================================================

set -e  # 에러 발생 시 스크립트 중단

echo "🚀 Letrade_v1 개발 환경 설정을 시작합니다..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 함수 정의
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. 사전 요구사항 확인
print_status "사전 요구사항을 확인합니다..."

# Python 버전 확인
if ! command -v python3 &> /dev/null; then
    print_error "Python3가 설치되어 있지 않습니다."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.11"

if [[ $(echo "$PYTHON_VERSION >= $REQUIRED_VERSION" | bc -l) -eq 0 ]]; then
    print_error "Python 3.11 이상이 필요합니다. 현재 버전: $PYTHON_VERSION"
    exit 1
fi

print_success "Python $PYTHON_VERSION 확인됨"

# Docker 확인
if ! command -v docker &> /dev/null; then
    print_error "Docker가 설치되어 있지 않습니다."
    exit 1
fi

# Docker Compose 확인
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose가 설치되어 있지 않습니다."
    exit 1
fi

print_success "Docker 및 Docker Compose 확인됨"

# 2. 가상환경 설정
print_status "Python 가상환경을 설정합니다..."

if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "가상환경이 생성되었습니다."
else
    print_warning "가상환경이 이미 존재합니다."
fi

# 가상환경 활성화
source venv/bin/activate
print_success "가상환경이 활성화되었습니다."

# 3. Python 패키지 설치
print_status "Python 패키지를 설치합니다..."

# pip 업그레이드
python -m pip install --upgrade pip

# 의존성 설치
pip install -e ".[dev]"
print_success "Python 패키지 설치가 완료되었습니다."

# 4. 환경 변수 파일 설정
print_status "환경 변수 파일을 설정합니다..."

if [ ! -f ".env" ]; then
    cp .env.example .env
    print_success ".env 파일이 생성되었습니다."
    print_warning "⚠️  .env 파일의 값들을 실제 설정으로 수정해주세요."
else
    print_warning ".env 파일이 이미 존재합니다."
fi

# 5. 로그 디렉터리 생성
print_status "로그 디렉터리를 생성합니다..."
mkdir -p logs
print_success "로그 디렉터리가 생성되었습니다."

# 6. Docker 서비스 시작
print_status "Docker 서비스를 시작합니다..."

# Docker Compose 서비스 시작
docker-compose up -d

# 서비스 시작 대기
print_status "서비스 시작을 대기합니다..."
sleep 10

# 서비스 상태 확인
if docker-compose ps | grep -q "Up"; then
    print_success "Docker 서비스가 성공적으로 시작되었습니다."
else
    print_error "Docker 서비스 시작에 실패했습니다."
    print_status "서비스 로그를 확인합니다:"
    docker-compose logs
    exit 1
fi

# 7. 데이터베이스 마이그레이션
print_status "데이터베이스 마이그레이션을 실행합니다..."

# PostgreSQL 연결 대기
for i in {1..30}; do
    if docker-compose exec -T postgres pg_isready -U letrade_user -d letrade_db; then
        break
    fi
    print_status "PostgreSQL 연결 대기 중... ($i/30)"
    sleep 2
done

# 마이그레이션 실행
if docker-compose exec -T postgres psql -U letrade_user -d letrade_db -f /docker-entrypoint-initdb.d/001_initial_schema.sql; then
    print_success "데이터베이스 마이그레이션이 완료되었습니다."
else
    print_error "데이터베이스 마이그레이션에 실패했습니다."
    exit 1
fi

# 8. Pre-commit 훅 설정
print_status "Pre-commit 훅을 설정합니다..."
pre-commit install
print_success "Pre-commit 훅이 설정되었습니다."

# 9. 개발 환경 검증
print_status "개발 환경을 검증합니다..."

# 데이터베이스 연결 테스트
python -c "
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    conn.close()
    print('✅ 데이터베이스 연결 성공')
except Exception as e:
    print(f'❌ 데이터베이스 연결 실패: {e}')
    exit(1)
"

# RabbitMQ 연결 테스트
python -c "
import pika
import os
from dotenv import load_dotenv

load_dotenv()

try:
    connection = pika.BlockingConnection(pika.URLParameters(os.getenv('RABBITMQ_URL')))
    connection.close()
    print('✅ RabbitMQ 연결 성공')
except Exception as e:
    print(f'❌ RabbitMQ 연결 실패: {e}')
    exit(1)
"

print_success "개발 환경 검증이 완료되었습니다."

# 10. 최종 안내
echo ""
echo "🎉 Letrade_v1 개발 환경 설정이 완료되었습니다!"
echo ""
echo "📋 다음 단계:"
echo "  1. .env 파일의 API 키들을 실제 값으로 설정"
echo "  2. 개발 시작: source venv/bin/activate"
echo "  3. 테스트 실행: pytest"
echo "  4. 코드 포맷팅: black src/ tests/"
echo "  5. 타입 체크: mypy src/"
echo ""
echo "🔗 유용한 URL:"
echo "  - RabbitMQ 관리 UI: http://localhost:15672 (letrade_user/letrade_password)"
echo "  - PostgreSQL: localhost:5432 (letrade_user/letrade_password)"
echo "  - Redis: localhost:6379"
echo ""
echo "📊 서비스 상태 확인: docker-compose ps"
echo "📋 로그 확인: docker-compose logs [service_name]"
echo ""
print_success "Happy coding! 🚀"