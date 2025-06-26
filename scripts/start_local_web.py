#!/usr/bin/env python3
"""
Letrade_v1 로컬 웹 인터페이스 시작 스크립트

REST API 서버를 시작하고 웹 인터페이스 접근 가능하도록 설정합니다.
"""

import asyncio
import logging
import os
import signal
import sys
import threading
import time
import webbrowser
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 환경 변수 설정
os.environ.setdefault("API_HOST", "127.0.0.1")
os.environ.setdefault("API_PORT", "8080")
os.environ.setdefault("API_LOG_LEVEL", "info")
os.environ.setdefault("JWT_SECRET_KEY", "demo-secret-key-for-testing")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080")
os.environ.setdefault("ALLOWED_HOSTS", "localhost,127.0.0.1")

# Mock 환경 변수 (실제 DB 없이도 API 실행 가능)
os.environ.setdefault("ENVIRONMENT", "demo")
os.environ.setdefault("RABBITMQ_HOST", "mock")
os.environ.setdefault("DATABASE_URL", "sqlite:///demo.db")

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class LocalWebServer:
    """로컬 웹 서버 관리자"""
    
    def __init__(self):
        self.api_process = None
        self.running = False
        self.api_port = int(os.getenv("API_PORT", "8080"))
        self.api_host = os.getenv("API_HOST", "127.0.0.1")
        
    def start_api_server(self):
        """API 서버 시작"""
        logger.info("🚀 REST API 서버 시작 중...")
        
        try:
            # Mock 환경에서 실행하기 위한 간단한 FastAPI 앱
            import uvicorn
            from fastapi import FastAPI
            from fastapi.middleware.cors import CORSMiddleware
            from fastapi.responses import JSONResponse, HTMLResponse
            
            # 간단한 FastAPI 앱 생성
            app = FastAPI(
                title="Letrade V1 Demo API",
                description="데모용 REST API 서버",
                version="1.0.0",
                docs_url="/docs",
                redoc_url="/redoc"
            )
            
            # CORS 설정
            app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            
            # 루트 엔드포인트
            @app.get("/")
            async def root():
                return HTMLResponse(content="""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Letrade V1 Demo Dashboard</title>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        body { 
                            font-family: Arial, sans-serif; 
                            margin: 0; 
                            padding: 20px; 
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: white;
                        }
                        .container { 
                            max-width: 1200px; 
                            margin: 0 auto; 
                            background: rgba(255,255,255,0.1);
                            padding: 30px;
                            border-radius: 15px;
                            backdrop-filter: blur(10px);
                        }
                        .header { 
                            text-align: center; 
                            margin-bottom: 40px; 
                        }
                        .header h1 { 
                            font-size: 3em; 
                            margin: 0; 
                            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                        }
                        .status-grid { 
                            display: grid; 
                            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
                            gap: 20px; 
                            margin-bottom: 30px; 
                        }
                        .status-card { 
                            background: rgba(255,255,255,0.2); 
                            padding: 20px; 
                            border-radius: 10px; 
                            text-align: center;
                            transition: transform 0.3s ease;
                        }
                        .status-card:hover {
                            transform: translateY(-5px);
                        }
                        .status-card h3 { 
                            margin-top: 0; 
                            color: #fff;
                        }
                        .api-links { 
                            text-align: center; 
                            margin-top: 30px; 
                        }
                        .api-links a { 
                            display: inline-block; 
                            margin: 10px; 
                            padding: 15px 30px; 
                            background: rgba(255,255,255,0.2); 
                            color: white; 
                            text-decoration: none; 
                            border-radius: 25px; 
                            transition: all 0.3s ease;
                        }
                        .api-links a:hover { 
                            background: rgba(255,255,255,0.3); 
                            transform: scale(1.05);
                        }
                        .metrics {
                            background: rgba(255,255,255,0.1);
                            padding: 20px;
                            border-radius: 10px;
                            margin-top: 20px;
                        }
                        .metric-row {
                            display: flex;
                            justify-content: space-between;
                            margin: 10px 0;
                            padding: 10px;
                            background: rgba(255,255,255,0.1);
                            border-radius: 5px;
                        }
                        @keyframes pulse {
                            0% { opacity: 1; }
                            50% { opacity: 0.7; }
                            100% { opacity: 1; }
                        }
                        .live { animation: pulse 2s infinite; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>🚀 Letrade V1 Demo Dashboard</h1>
                            <p>자동화 암호화폐 거래 시스템 - 웹 인터페이스 데모</p>
                        </div>
                        
                        <div class="status-grid">
                            <div class="status-card">
                                <h3>🟢 시스템 상태</h3>
                                <div class="live">✅ 온라인</div>
                                <p>API 서버 정상 작동</p>
                            </div>
                            
                            <div class="status-card">
                                <h3>📊 포트폴리오</h3>
                                <div>💰 $100.00</div>
                                <p>데모 계정 잔고</p>
                            </div>
                            
                            <div class="status-card">
                                <h3>📈 활성 전략</h3>
                                <div>⚡ MA Crossover</div>
                                <p>이동평균 교차 전략</p>
                            </div>
                            
                            <div class="status-card">
                                <h3>🎯 성과</h3>
                                <div class="live">📊 실시간 추적</div>
                                <p>P&L 모니터링</p>
                            </div>
                        </div>
                        
                        <div class="metrics">
                            <h3>📈 실시간 메트릭</h3>
                            <div class="metric-row">
                                <span>평균 레이턴시:</span>
                                <span><strong>1.921ms</strong></span>
                            </div>
                            <div class="metric-row">
                                <span>시스템 가용성:</span>
                                <span><strong>99.90%</strong></span>
                            </div>
                            <div class="metric-row">
                                <span>메모리 사용량:</span>
                                <span><strong>8.6MB</strong></span>
                            </div>
                            <div class="metric-row">
                                <span>CPU 사용률:</span>
                                <span><strong>2.4%</strong></span>
                            </div>
                        </div>
                        
                        <div class="api-links">
                            <h3>🔗 API 엔드포인트</h3>
                            <a href="/health">Health Check</a>
                            <a href="/api/status">시스템 상태</a>
                            <a href="/api/portfolio">포트폴리오</a>
                            <a href="/docs">API 문서</a>
                            <a href="/redoc">ReDoc</a>
                        </div>
                    </div>
                    
                    <script>
                        // 실시간 업데이트 시뮬레이션
                        setInterval(() => {
                            const now = new Date();
                            document.title = `Letrade V1 Demo - ${now.toLocaleTimeString()}`;
                        }, 1000);
                    </script>
                </body>
                </html>
                """)
            
            # Health Check 엔드포인트
            @app.get("/health")
            async def health():
                return {
                    "status": "healthy",
                    "timestamp": time.time(),
                    "api_version": "1.0.0",
                    "services": {
                        "api_server": "running",
                        "demo_mode": "active"
                    }
                }
            
            # 시스템 상태 엔드포인트
            @app.get("/api/status")
            async def system_status():
                return {
                    "system": {
                        "status": "operational",
                        "uptime": "running",
                        "version": "1.0.0-MVP"
                    },
                    "performance": {
                        "avg_latency_ms": 1.921,
                        "availability_percent": 99.90,
                        "memory_usage_mb": 8.6,
                        "cpu_usage_percent": 2.4
                    },
                    "trading": {
                        "active_strategies": 1,
                        "strategy_name": "MA Crossover",
                        "dry_run": True
                    }
                }
            
            # 포트폴리오 엔드포인트
            @app.get("/api/portfolio")
            async def portfolio():
                return {
                    "account": {
                        "balance_usd": 100.00,
                        "available_usd": 98.19,
                        "total_pnl": -1.81,
                        "pnl_percent": -1.81
                    },
                    "positions": [
                        {
                            "symbol": "BTCUSDT",
                            "side": "long",
                            "size": 0.00002,
                            "entry_price": 50000.0,
                            "current_price": 49950.0,
                            "pnl": -1.0,
                            "pnl_percent": -0.1
                        }
                    ],
                    "trades_today": 2,
                    "win_rate": 50.0
                }
            
            # Prometheus 메트릭 스타일 엔드포인트
            @app.get("/metrics")
            async def metrics():
                return JSONResponse(content={
                    "metrics": {
                        "letrade_api_requests_total": 156,
                        "letrade_trade_executions_total": 2,
                        "letrade_avg_latency_seconds": 0.001921,
                        "letrade_memory_usage_bytes": 9020743,
                        "letrade_cpu_usage_ratio": 0.024,
                        "letrade_portfolio_value_usd": 100.0,
                        "letrade_active_strategies": 1
                    }
                })
            
            # API 서버 실행
            logger.info(f"📡 API 서버 시작: http://{self.api_host}:{self.api_port}")
            
            uvicorn.run(
                app,
                host=self.api_host,
                port=self.api_port,
                log_level="info",
                access_log=True
            )
            
        except Exception as e:
            logger.error(f"❌ API 서버 시작 실패: {e}")
            return False
    
    def start(self):
        """웹 서버 시작"""
        logger.info("🌐 로컬 웹 인터페이스 시작...")
        
        self.running = True
        
        # API 서버를 별도 스레드에서 실행
        api_thread = threading.Thread(target=self.start_api_server, daemon=True)
        api_thread.start()
        
        # 잠시 대기 후 브라우저 열기
        time.sleep(2)
        
        try:
            base_url = f"http://{self.api_host}:{self.api_port}"
            logger.info(f"🎉 웹 인터페이스 준비 완료!")
            logger.info(f"📱 대시보드: {base_url}")
            logger.info(f"📋 API 문서: {base_url}/docs")
            logger.info(f"💊 Health Check: {base_url}/health")
            logger.info(f"📊 메트릭: {base_url}/metrics")
            
            # 브라우저에서 열기
            webbrowser.open(base_url)
            
            # 메인 스레드에서 대기
            logger.info("⏹️ Ctrl+C를 눌러 서버를 종료하세요")
            
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("🛑 사용자가 서버 종료를 요청했습니다")
            self.stop()
    
    def stop(self):
        """웹 서버 정지"""
        logger.info("🔄 웹 서버 종료 중...")
        self.running = False


def signal_handler(signum, frame):
    """시그널 핸들러"""
    logger.info(f"📡 시그널 {signum} 수신, 안전 종료 중...")
    sys.exit(0)


def main():
    """메인 실행 함수"""
    print("🚀 Letrade V1 로컬 웹 인터페이스")
    print("=" * 50)
    print("이 스크립트는 로컬호스트에서 웹 대시보드를 실행합니다.")
    print("=" * 50)
    
    # 시그널 핸들러 설정
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 웹 서버 시작
    server = LocalWebServer()
    server.start()


if __name__ == "__main__":
    main()