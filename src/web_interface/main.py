"""
바이낸스 스타일 웹 인터페이스 메인 서버

FastAPI 기반 실시간 거래 대시보드
- WebSocket 실시간 데이터 스트림
- REST API 엔드포인트
- 텔레그램 봇 연동
- 반응형 모바일 지원
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn

# 프로젝트 임포트
from common.message_bus import MessageBus
from common.config import Config
from telegram_interface.service_client import ServiceClient

logger = logging.getLogger(__name__)

# 보안 설정
security = HTTPBearer(auto_error=False)

class WebInterface:
    """바이낸스 스타일 웹 인터페이스 메인 클래스"""
    
    def __init__(self):
        """웹 인터페이스 초기화"""
        self.app = FastAPI(
            title="Letrade V1 Pro Dashboard",
            description="바이낸스 스타일 전문 거래 대시보드",
            version="1.0.0",
            docs_url="/api/docs",
            redoc_url="/api/redoc"
        )
        
        # 실시간 연결 관리
        self.active_connections: List[WebSocket] = []
        self.message_bus: Optional[MessageBus] = None
        self.service_client: Optional[ServiceClient] = None
        
        # 데이터 캐시
        self.data_cache = {
            'market_data': {},
            'portfolio': {},
            'strategies': {},
            'system_status': {},
            'telegram_activity': []
        }
        
        self._setup_middleware()
        self._setup_routes()
        
    def _setup_middleware(self):
        """미들웨어 설정"""
        # CORS 설정
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 요청 로깅 미들웨어
        @self.app.middleware("http")
        async def log_requests(request: Request, call_next):
            start_time = time.time()
            response = await call_next(request)
            process_time = time.time() - start_time
            
            logger.info(
                f"{request.method} {request.url.path} - "
                f"{response.status_code} - {process_time:.3f}s"
            )
            return response
    
    def _setup_routes(self):
        """라우트 설정"""
        
        # 메인 대시보드
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard():
            return self._get_dashboard_html()
        
        # WebSocket 엔드포인트
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self.connect_websocket(websocket)
        
        # REST API 엔드포인트
        @self.app.get("/api/health")
        async def health_check():
            return {
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
                "services": {
                    "web_interface": "running",
                    "websocket_connections": len(self.active_connections),
                    "message_bus": "connected" if self.message_bus and self.message_bus.is_connected else "disconnected"
                }
            }
        
        @self.app.get("/api/dashboard/data")
        async def get_dashboard_data():
            """대시보드 초기 데이터 제공"""
            return {
                "market_data": await self._get_market_data(),
                "portfolio": await self._get_portfolio_data(),
                "strategies": await self._get_strategies_data(),
                "system_status": await self._get_system_status(),
                "telegram_activity": self.data_cache['telegram_activity'][-10:]  # 최근 10개
            }
        
        @self.app.get("/api/market/{symbol}")
        async def get_market_data(symbol: str):
            """특정 심볼 시장 데이터"""
            return await self._get_symbol_market_data(symbol)
        
        @self.app.get("/api/portfolio")
        async def get_portfolio():
            """포트폴리오 상세 정보"""
            return await self._get_portfolio_data()
        
        @self.app.get("/api/strategies")
        async def get_strategies():
            """전략 목록 및 상태"""
            return await self._get_strategies_data()
        
        @self.app.post("/api/strategy/{strategy_id}/start")
        async def start_strategy(strategy_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
            """전략 시작"""
            if not await self._verify_token(credentials):
                raise HTTPException(status_code=401, detail="Unauthorized")
            
            result = await self._execute_strategy_action(strategy_id, "start")
            
            # 텔레그램 알림
            await self._notify_telegram(f"전략 {strategy_id} 웹에서 시작됨")
            
            return result
        
        @self.app.post("/api/strategy/{strategy_id}/stop")
        async def stop_strategy(strategy_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
            """전략 중지"""
            if not await self._verify_token(credentials):
                raise HTTPException(status_code=401, detail="Unauthorized")
            
            result = await self._execute_strategy_action(strategy_id, "stop")
            
            # 텔레그램 알림
            await self._notify_telegram(f"전략 {strategy_id} 웹에서 중지됨")
            
            return result
        
        @self.app.post("/api/system/emergency_stop")
        async def emergency_stop(credentials: HTTPAuthorizationCredentials = Depends(security)):
            """긴급 중지"""
            if not await self._verify_token(credentials):
                raise HTTPException(status_code=401, detail="Unauthorized")
            
            result = await self._execute_emergency_stop()
            
            # 텔레그램 긴급 알림
            await self._notify_telegram("🚨 웹에서 긴급 중지 실행됨", priority="high")
            
            return result
        
        @self.app.post("/api/telegram/send")
        async def send_telegram_message(
            request: Dict[str, Any], 
            credentials: HTTPAuthorizationCredentials = Depends(security)
        ):
            """텔레그램 메시지 전송"""
            if not await self._verify_token(credentials):
                raise HTTPException(status_code=401, detail="Unauthorized")
            
            message = request.get("message", "")
            priority = request.get("priority", "normal")
            
            result = await self._notify_telegram(message, priority)
            
            # 활동 기록
            self.data_cache['telegram_activity'].append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": "outgoing",
                "message": message,
                "source": "web_interface"
            })
            
            return {"success": True, "message_sent": message}
    
    async def connect_websocket(self, websocket: WebSocket):
        """WebSocket 연결 관리"""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        logger.info(f"WebSocket 연결됨. 총 연결: {len(self.active_connections)}")
        
        try:
            # 초기 데이터 전송
            await self.send_to_websocket(websocket, {
                "type": "initial_data",
                "data": await self._get_dashboard_data()
            })
            
            # 연결 유지 및 메시지 수신
            while True:
                try:
                    # 클라이언트로부터 메시지 수신 (ping/pong, 구독 요청 등)
                    message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                    await self._handle_websocket_message(websocket, json.loads(message))
                except asyncio.TimeoutError:
                    # 30초마다 ping 전송
                    await self.send_to_websocket(websocket, {"type": "ping"})
                    
        except WebSocketDisconnect:
            logger.info("WebSocket 연결 해제됨")
        except Exception as e:
            logger.error(f"WebSocket 오류: {e}")
        finally:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
    
    async def send_to_websocket(self, websocket: WebSocket, data: Dict[str, Any]):
        """WebSocket으로 데이터 전송"""
        try:
            await websocket.send_text(json.dumps(data, ensure_ascii=False))
        except Exception as e:
            logger.error(f"WebSocket 전송 오류: {e}")
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
    
    async def broadcast_to_all(self, data: Dict[str, Any]):
        """모든 WebSocket 연결에 브로드캐스트"""
        if not self.active_connections:
            return
        
        disconnected = []
        for websocket in self.active_connections:
            try:
                await websocket.send_text(json.dumps(data, ensure_ascii=False))
            except Exception as e:
                logger.error(f"브로드캐스트 오류: {e}")
                disconnected.append(websocket)
        
        # 연결 끊어진 WebSocket 제거
        for ws in disconnected:
            self.active_connections.remove(ws)
    
    async def _handle_websocket_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """WebSocket 메시지 처리"""
        msg_type = message.get("type")
        
        if msg_type == "pong":
            # Pong 응답 처리
            await self.send_to_websocket(websocket, {"type": "pong_ack"})
        
        elif msg_type == "subscribe":
            # 특정 데이터 구독 요청
            topics = message.get("topics", [])
            # 구독 로직 구현
            await self.send_to_websocket(websocket, {
                "type": "subscription_confirmed",
                "topics": topics
            })
        
        elif msg_type == "unsubscribe":
            # 구독 해제
            topics = message.get("topics", [])
            await self.send_to_websocket(websocket, {
                "type": "unsubscription_confirmed", 
                "topics": topics
            })
    
    async def start_background_tasks(self):
        """백그라운드 작업 시작"""
        # 실시간 데이터 업데이트 태스크
        asyncio.create_task(self._data_update_loop())
        
        # MessageBus 연결 및 리스너
        await self._connect_message_bus()
        asyncio.create_task(self._message_bus_listener())
    
    async def _data_update_loop(self):
        """실시간 데이터 업데이트 루프"""
        while True:
            try:
                # 시장 데이터 업데이트 (5초마다)
                if int(time.time()) % 5 == 0:
                    market_data = await self._get_market_data()
                    if market_data != self.data_cache['market_data']:
                        self.data_cache['market_data'] = market_data
                        await self.broadcast_to_all({
                            "type": "market_update",
                            "data": market_data,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                
                # 포트폴리오 업데이트 (10초마다)
                if int(time.time()) % 10 == 0:
                    portfolio_data = await self._get_portfolio_data()
                    if portfolio_data != self.data_cache['portfolio']:
                        self.data_cache['portfolio'] = portfolio_data
                        await self.broadcast_to_all({
                            "type": "portfolio_update",
                            "data": portfolio_data,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                
                # 시스템 상태 업데이트 (15초마다)
                if int(time.time()) % 15 == 0:
                    system_status = await self._get_system_status()
                    if system_status != self.data_cache['system_status']:
                        self.data_cache['system_status'] = system_status
                        await self.broadcast_to_all({
                            "type": "system_update",
                            "data": system_status,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                
                await asyncio.sleep(1)  # 1초마다 체크
                
            except Exception as e:
                logger.error(f"데이터 업데이트 루프 오류: {e}")
                await asyncio.sleep(5)
    
    async def _connect_message_bus(self):
        """MessageBus 연결"""
        try:
            config = Config()
            message_bus_config = config.get_message_bus_config()
            
            self.message_bus = MessageBus(message_bus_config)
            await self.message_bus.connect()
            
            # ServiceClient 초기화
            self.service_client = ServiceClient(message_bus=self.message_bus)
            
            logger.info("MessageBus 연결 완료")
            
        except Exception as e:
            logger.error(f"MessageBus 연결 실패: {e}")
    
    async def _message_bus_listener(self):
        """MessageBus 메시지 리스너"""
        if not self.message_bus:
            return
        
        try:
            # 텔레그램 활동 모니터링
            await self.message_bus.subscribe("telegram.activity.*", self._handle_telegram_activity)
            
            # 전략 상태 변화 모니터링
            await self.message_bus.subscribe("strategy.status.*", self._handle_strategy_status)
            
            # 거래 실행 알림
            await self.message_bus.subscribe("trade.executed", self._handle_trade_executed)
            
            logger.info("MessageBus 리스너 시작됨")
            
        except Exception as e:
            logger.error(f"MessageBus 리스너 오류: {e}")
    
    async def _handle_telegram_activity(self, message: Dict[str, Any]):
        """텔레그램 활동 처리"""
        # 텔레그램 활동을 웹 인터페이스에 실시간 반영
        activity = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": message.get("type", "unknown"),
            "content": message.get("content", ""),
            "source": "telegram"
        }
        
        self.data_cache['telegram_activity'].append(activity)
        
        # 최근 50개만 유지
        if len(self.data_cache['telegram_activity']) > 50:
            self.data_cache['telegram_activity'] = self.data_cache['telegram_activity'][-50:]
        
        # 웹 클라이언트에 브로드캐스트
        await self.broadcast_to_all({
            "type": "telegram_activity",
            "data": activity
        })
    
    async def _handle_strategy_status(self, message: Dict[str, Any]):
        """전략 상태 변화 처리"""
        # 전략 상태 변화를 실시간 반영
        await self.broadcast_to_all({
            "type": "strategy_status_update",
            "data": message
        })
    
    async def _handle_trade_executed(self, message: Dict[str, Any]):
        """거래 실행 처리"""
        # 거래 실행을 실시간 반영
        await self.broadcast_to_all({
            "type": "trade_executed",
            "data": message
        })
    
    async def _get_market_data(self) -> Dict[str, Any]:
        """시장 데이터 조회 (실제 구현에서는 거래소 API 연동)"""
        # Mock 데이터 (실제 구현에서는 Exchange Connector 사용)
        import random
        
        base_prices = {
            "BTCUSDT": 50000 + random.uniform(-1000, 1000),
            "ETHUSDT": 3000 + random.uniform(-100, 100),
            "ADAUSDT": 0.5 + random.uniform(-0.05, 0.05),
            "BNBUSDT": 300 + random.uniform(-20, 20)
        }
        
        market_data = {}
        for symbol, price in base_prices.items():
            change_24h = random.uniform(-5, 5)
            market_data[symbol] = {
                "symbol": symbol,
                "price": round(price, 2),
                "change_24h": round(change_24h, 2),
                "change_24h_percent": round(change_24h / price * 100, 2),
                "volume_24h": round(random.uniform(1000, 50000), 2),
                "high_24h": round(price * 1.05, 2),
                "low_24h": round(price * 0.95, 2),
                "last_update": datetime.now(timezone.utc).isoformat()
            }
        
        return market_data
    
    async def _get_portfolio_data(self) -> Dict[str, Any]:
        """포트폴리오 데이터 조회"""
        if self.service_client:
            try:
                return await self.service_client.get_portfolio_status()
            except Exception as e:
                logger.error(f"포트폴리오 데이터 조회 오류: {e}")
        
        # Mock 데이터
        return {
            "total_value": 1234.56,
            "available_balance": 1200.34,
            "total_pnl": 12.34,
            "total_pnl_percent": 1.02,
            "positions": [
                {
                    "symbol": "BTCUSDT",
                    "side": "long",
                    "size": 0.001,
                    "entry_price": 50000.0,
                    "current_price": 50234.56,
                    "pnl": 0.23,
                    "pnl_percent": 0.47
                }
            ],
            "trades_today": 3,
            "win_rate": 66.7
        }
    
    async def _get_strategies_data(self) -> Dict[str, Any]:
        """전략 데이터 조회"""
        if self.service_client:
            try:
                return await self.service_client.get_strategies_status()
            except Exception as e:
                logger.error(f"전략 데이터 조회 오류: {e}")
        
        # Mock 데이터
        return {
            "active_strategies": 1,
            "total_strategies": 3,
            "strategies": [
                {
                    "id": "ma_crossover_btc",
                    "name": "MA Crossover",
                    "symbol": "BTCUSDT",
                    "status": "active",
                    "pnl": 1.23,
                    "pnl_percent": 0.47,
                    "win_rate": 65.2,
                    "last_signal": "HOLD",
                    "last_signal_time": datetime.now(timezone.utc).isoformat()
                }
            ]
        }
    
    async def _get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 조회"""
        return {
            "status": "operational",
            "uptime": "99.9%",
            "cpu_usage": 2.4,
            "memory_usage_mb": 8.6,
            "avg_latency_ms": 1.921,
            "active_connections": len(self.active_connections),
            "message_bus_connected": self.message_bus.is_connected if self.message_bus else False,
            "telegram_connected": True,  # TODO: 실제 텔레그램 상태 확인
            "last_update": datetime.now(timezone.utc).isoformat()
        }
    
    async def _get_symbol_market_data(self, symbol: str) -> Dict[str, Any]:
        """특정 심볼 상세 데이터"""
        market_data = await self._get_market_data()
        if symbol in market_data:
            return market_data[symbol]
        else:
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
    
    async def _execute_strategy_action(self, strategy_id: str, action: str) -> Dict[str, Any]:
        """전략 액션 실행"""
        if self.service_client:
            try:
                if action == "start":
                    return await self.service_client.start_strategy(strategy_id)
                elif action == "stop":
                    return await self.service_client.stop_strategy(strategy_id)
                else:
                    raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
            except Exception as e:
                logger.error(f"전략 액션 실행 오류: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Mock 응답
        return {
            "success": True,
            "strategy_id": strategy_id,
            "action": action,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _execute_emergency_stop(self) -> Dict[str, Any]:
        """긴급 중지 실행"""
        if self.service_client:
            try:
                return await self.service_client.emergency_stop()
            except Exception as e:
                logger.error(f"긴급 중지 실행 오류: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Mock 응답
        return {
            "success": True,
            "action": "emergency_stop",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _notify_telegram(self, message: str, priority: str = "normal") -> bool:
        """텔레그램 알림 전송"""
        if self.message_bus:
            try:
                await self.message_bus.publish("telegram.notify", {
                    "message": message,
                    "priority": priority,
                    "source": "web_interface",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                return True
            except Exception as e:
                logger.error(f"텔레그램 알림 전송 오류: {e}")
                return False
        
        return False
    
    async def _verify_token(self, credentials: Optional[HTTPAuthorizationCredentials]) -> bool:
        """JWT 토큰 검증 (간단한 구현)"""
        if not credentials:
            return False
        
        # TODO: 실제 JWT 검증 구현
        # 현재는 개발용으로 간단한 토큰 체크
        return credentials.credentials == "letrade-web-token"
    
    def _get_dashboard_html(self) -> str:
        """대시보드 HTML 생성"""
        return """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Letrade V1 Pro - 바이낸스 스타일 대시보드</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://unpkg.com/react@18/umd/react.development.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <style>
        /* 바이낸스 스타일 CSS */
        :root {
            --bg-primary: #0b0e11;
            --bg-secondary: #1e2329;
            --bg-tertiary: #2b3139;
            --text-primary: #f0f0f0;
            --text-secondary: #c7c7c7;
            --text-muted: #888888;
            --accent-green: #0ecb81;
            --accent-red: #f6465d;
            --accent-yellow: #fcd535;
            --accent-blue: #00d4ff;
            --border-primary: #2b3139;
            --border-light: #404040;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            overflow-x: hidden;
        }
        
        .dashboard-container {
            display: flex;
            height: 100vh;
        }
        
        .sidebar {
            width: 240px;
            background: var(--bg-secondary);
            border-right: 1px solid var(--border-primary);
            display: flex;
            flex-direction: column;
        }
        
        .main-content {
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        
        .header {
            height: 64px;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-primary);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 24px;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 18px;
            font-weight: 600;
        }
        
        .status-indicators {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        
        .status-item {
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: 12px;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--accent-green);
        }
        
        .portfolio-summary {
            display: flex;
            gap: 24px;
        }
        
        .portfolio-item {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
        }
        
        .change.positive {
            color: var(--accent-green);
        }
        
        .change.negative {
            color: var(--accent-red);
        }
        
        .widget-grid {
            padding: 24px;
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 24px;
            flex: 1;
            overflow-y: auto;
        }
        
        .widget {
            background: var(--bg-secondary);
            border: 1px solid var(--border-primary);
            border-radius: 8px;
            padding: 20px;
            transition: all 0.3s ease;
        }
        
        .widget:hover {
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
            transform: translateY(-2px);
        }
        
        .widget-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        
        .widget-title {
            font-size: 16px;
            font-weight: 600;
            color: var(--text-primary);
        }
        
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .btn-primary {
            background: var(--accent-green);
            color: white;
        }
        
        .btn-primary:hover {
            background: #0bb574;
        }
        
        .btn-danger {
            background: var(--accent-red);
            color: white;
        }
        
        .btn-danger:hover {
            background: #e53e52;
        }
        
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
        }
        
        .metric-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid var(--border-primary);
        }
        
        .metric-label {
            color: var(--text-secondary);
            font-size: 12px;
        }
        
        .metric-value {
            font-weight: 600;
            font-size: 14px;
        }
        
        .loading {
            text-align: center;
            color: var(--text-muted);
            padding: 20px;
        }
        
        .connection-status {
            padding: 12px;
            margin: 12px;
            border-radius: 6px;
            text-align: center;
            font-size: 12px;
        }
        
        .connection-status.connected {
            background: rgba(14, 203, 129, 0.1);
            border: 1px solid var(--accent-green);
            color: var(--accent-green);
        }
        
        .connection-status.disconnected {
            background: rgba(246, 70, 93, 0.1);
            border: 1px solid var(--accent-red);
            color: var(--accent-red);
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .animate-pulse {
            animation: pulse 2s infinite;
        }
        
        @media (max-width: 768px) {
            .sidebar {
                display: none;
            }
            
            .widget-grid {
                grid-template-columns: 1fr;
                padding: 16px;
            }
            
            .header {
                padding: 0 16px;
            }
            
            .portfolio-summary {
                display: none;
            }
        }
    </style>
</head>
<body>
    <div id="dashboard-root"></div>
    
    <script type="text/babel">
        const { useState, useEffect, useRef } = React;
        
        // WebSocket 훅
        function useWebSocket(url) {
            const [socket, setSocket] = useState(null);
            const [connected, setConnected] = useState(false);
            const [data, setData] = useState({});
            
            useEffect(() => {
                const ws = new WebSocket(url);
                
                ws.onopen = () => {
                    console.log('WebSocket 연결됨');
                    setConnected(true);
                    setSocket(ws);
                };
                
                ws.onmessage = (event) => {
                    const message = JSON.parse(event.data);
                    setData(prevData => ({
                        ...prevData,
                        [message.type]: message.data
                    }));
                };
                
                ws.onclose = () => {
                    console.log('WebSocket 연결 해제됨');
                    setConnected(false);
                };
                
                ws.onerror = (error) => {
                    console.error('WebSocket 오류:', error);
                    setConnected(false);
                };
                
                return () => {
                    ws.close();
                };
            }, [url]);
            
            return { socket, connected, data };
        }
        
        // 메인 대시보드 컴포넌트
        function Dashboard() {
            const wsUrl = `ws://${window.location.host}/ws`;
            const { socket, connected, data } = useWebSocket(wsUrl);
            const [dashboardData, setDashboardData] = useState(null);
            
            useEffect(() => {
                // 초기 데이터 로드
                fetch('/api/dashboard/data')
                    .then(res => res.json())
                    .then(setDashboardData)
                    .catch(console.error);
            }, []);
            
            useEffect(() => {
                // WebSocket 데이터 업데이트
                if (data.initial_data) {
                    setDashboardData(data.initial_data);
                }
                
                if (data.market_update && dashboardData) {
                    setDashboardData(prev => ({
                        ...prev,
                        market_data: data.market_update
                    }));
                }
                
                if (data.portfolio_update && dashboardData) {
                    setDashboardData(prev => ({
                        ...prev,
                        portfolio: data.portfolio_update
                    }));
                }
                
                if (data.system_update && dashboardData) {
                    setDashboardData(prev => ({
                        ...prev,
                        system_status: data.system_update
                    }));
                }
            }, [data, dashboardData]);
            
            if (!dashboardData) {
                return (
                    <div className="loading">
                        <h2>로딩 중...</h2>
                        <p>대시보드 데이터를 불러오고 있습니다.</p>
                    </div>
                );
            }
            
            return (
                <div className="dashboard-container">
                    <Sidebar />
                    <div className="main-content">
                        <Header 
                            connected={connected} 
                            portfolio={dashboardData.portfolio} 
                        />
                        <div className="widget-grid">
                            <MarketWidget data={dashboardData.market_data} />
                            <PortfolioWidget data={dashboardData.portfolio} />
                            <SystemStatusWidget data={dashboardData.system_status} />
                            <StrategyControlWidget data={dashboardData.strategies} />
                            <TelegramWidget data={dashboardData.telegram_activity} />
                            <PerformanceWidget data={dashboardData.portfolio} />
                        </div>
                    </div>
                </div>
            );
        }
        
        // 사이드바 컴포넌트
        function Sidebar() {
            return (
                <div className="sidebar">
                    <div style={{padding: '20px', borderBottom: '1px solid var(--border-primary)'}}>
                        <div className="logo">
                            <span>🚀</span>
                            <span>LETRADE V1</span>
                        </div>
                    </div>
                    
                    <nav style={{padding: '20px', flex: 1}}>
                        <div style={{marginBottom: '24px'}}>
                            <h4 style={{color: 'var(--text-muted)', fontSize: '12px', marginBottom: '12px'}}>모니터링</h4>
                            <div style={{padding: '8px 12px', background: 'rgba(0, 212, 255, 0.1)', borderRadius: '6px', fontSize: '14px'}}>
                                📊 대시보드
                            </div>
                        </div>
                        
                        <div style={{marginBottom: '24px'}}>
                            <h4 style={{color: 'var(--text-muted)', fontSize: '12px', marginBottom: '12px'}}>거래</h4>
                            <div style={{padding: '8px 12px', fontSize: '14px', cursor: 'pointer'}}>
                                📈 차트
                            </div>
                            <div style={{padding: '8px 12px', fontSize: '14px', cursor: 'pointer'}}>
                                🎯 전략
                            </div>
                        </div>
                        
                        <div>
                            <h4 style={{color: 'var(--text-muted)', fontSize: '12px', marginBottom: '12px'}}>시스템</h4>
                            <div style={{padding: '8px 12px', fontSize: '14px', cursor: 'pointer'}}>
                                ⚙️ 설정
                            </div>
                            <div style={{padding: '8px 12px', fontSize: '14px', cursor: 'pointer'}}>
                                📱 텔레그램
                            </div>
                        </div>
                    </nav>
                </div>
            );
        }
        
        // 헤더 컴포넌트
        function Header({ connected, portfolio }) {
            return (
                <header className="header">
                    <div style={{display: 'flex', alignItems: 'center', gap: '24px'}}>
                        <div className="logo">
                            <span>🚀</span>
                            <span>LETRADE V1 PRO</span>
                        </div>
                        
                        <div className="status-indicators">
                            <div className="status-item">
                                <span className={`status-dot ${connected ? 'animate-pulse' : ''}`} 
                                      style={{background: connected ? 'var(--accent-green)' : 'var(--accent-red)'}}></span>
                                <span>{connected ? '실시간' : '연결 끊김'}</span>
                            </div>
                        </div>
                    </div>
                    
                    {portfolio && (
                        <div className="portfolio-summary">
                            <div className="portfolio-item">
                                <span>총 자산:</span>
                                <span style={{fontWeight: '600'}}>${portfolio.total_value?.toFixed(2)}</span>
                                <span className={`change ${portfolio.total_pnl >= 0 ? 'positive' : 'negative'}`}>
                                    {portfolio.total_pnl >= 0 ? '+' : ''}${portfolio.total_pnl?.toFixed(2)}
                                </span>
                            </div>
                        </div>
                    )}
                    
                    <div style={{display: 'flex', alignItems: 'center', gap: '16px'}}>
                        <span>👤 Admin</span>
                        <button className="btn btn-primary">⚙️</button>
                    </div>
                </header>
            );
        }
        
        // 시장 현황 위젯
        function MarketWidget({ data }) {
            if (!data) return <div className="widget"><div className="loading">로딩...</div></div>;
            
            return (
                <div className="widget">
                    <div className="widget-header">
                        <h3 className="widget-title">📊 실시간 시장 현황</h3>
                        <span className="animate-pulse" style={{color: 'var(--accent-green)', fontSize: '12px'}}>실시간</span>
                    </div>
                    
                    <div>
                        {Object.entries(data).slice(0, 4).map(([symbol, info]) => (
                            <div key={symbol} className="metric-item">
                                <div>
                                    <div style={{fontWeight: '600'}}>{symbol}</div>
                                    <div style={{fontSize: '12px', color: 'var(--text-secondary)'}}>
                                        ${info.price?.toFixed(2)}
                                    </div>
                                </div>
                                <div className={`change ${info.change_24h >= 0 ? 'positive' : 'negative'}`}>
                                    {info.change_24h >= 0 ? '+' : ''}{info.change_24h?.toFixed(2)}%
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            );
        }
        
        // 포트폴리오 위젯
        function PortfolioWidget({ data }) {
            if (!data) return <div className="widget"><div className="loading">로딩...</div></div>;
            
            return (
                <div className="widget">
                    <div className="widget-header">
                        <h3 className="widget-title">💰 포트폴리오</h3>
                    </div>
                    
                    <div className="metric-grid">
                        <div className="metric-item">
                            <span className="metric-label">총 자산</span>
                            <span className="metric-value">${data.total_value?.toFixed(2)}</span>
                        </div>
                        <div className="metric-item">
                            <span className="metric-label">가용 잔고</span>
                            <span className="metric-value">${data.available_balance?.toFixed(2)}</span>
                        </div>
                        <div className="metric-item">
                            <span className="metric-label">P&L</span>
                            <span className={`metric-value change ${data.total_pnl >= 0 ? 'positive' : 'negative'}`}>
                                {data.total_pnl >= 0 ? '+' : ''}${data.total_pnl?.toFixed(2)}
                            </span>
                        </div>
                        <div className="metric-item">
                            <span className="metric-label">승률</span>
                            <span className="metric-value">{data.win_rate?.toFixed(1)}%</span>
                        </div>
                    </div>
                </div>
            );
        }
        
        // 시스템 상태 위젯
        function SystemStatusWidget({ data }) {
            if (!data) return <div className="widget"><div className="loading">로딩...</div></div>;
            
            return (
                <div className="widget">
                    <div className="widget-header">
                        <h3 className="widget-title">📊 시스템 상태</h3>
                        <span style={{color: 'var(--accent-green)', fontSize: '12px'}}>정상</span>
                    </div>
                    
                    <div className="metric-grid">
                        <div className="metric-item">
                            <span className="metric-label">CPU</span>
                            <span className="metric-value">{data.cpu_usage?.toFixed(1)}%</span>
                        </div>
                        <div className="metric-item">
                            <span className="metric-label">메모리</span>
                            <span className="metric-value">{data.memory_usage_mb?.toFixed(1)}MB</span>
                        </div>
                        <div className="metric-item">
                            <span className="metric-label">레이턴시</span>
                            <span className="metric-value">{data.avg_latency_ms?.toFixed(1)}ms</span>
                        </div>
                        <div className="metric-item">
                            <span className="metric-label">가동률</span>
                            <span className="metric-value">{data.uptime}</span>
                        </div>
                    </div>
                </div>
            );
        }
        
        // 전략 제어 위젯
        function StrategyControlWidget({ data }) {
            const [loading, setLoading] = useState(false);
            
            const handleStrategyAction = async (action) => {
                setLoading(true);
                try {
                    const response = await fetch(`/api/strategy/ma_crossover_btc/${action}`, {
                        method: 'POST',
                        headers: {
                            'Authorization': 'Bearer letrade-web-token'
                        }
                    });
                    
                    if (response.ok) {
                        console.log(`전략 ${action} 성공`);
                    }
                } catch (error) {
                    console.error(`전략 ${action} 오류:`, error);
                } finally {
                    setLoading(false);
                }
            };
            
            return (
                <div className="widget">
                    <div className="widget-header">
                        <h3 className="widget-title">⚡ 전략 제어</h3>
                        <span style={{color: 'var(--accent-green)', fontSize: '12px'}}>
                            {data?.active_strategies || 0}개 활성
                        </span>
                    </div>
                    
                    <div style={{display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px', marginBottom: '16px'}}>
                        <button 
                            className="btn btn-primary" 
                            onClick={() => handleStrategyAction('start')}
                            disabled={loading}
                        >
                            ▶️ 시작
                        </button>
                        <button 
                            className="btn btn-danger" 
                            onClick={() => handleStrategyAction('stop')}
                            disabled={loading}
                        >
                            🛑 중지
                        </button>
                    </div>
                    
                    {data?.strategies?.map(strategy => (
                        <div key={strategy.id} className="metric-item">
                            <div>
                                <div style={{fontWeight: '600'}}>{strategy.name}</div>
                                <div style={{fontSize: '12px', color: 'var(--text-secondary)'}}>
                                    {strategy.symbol}
                                </div>
                            </div>
                            <div className={`change ${strategy.pnl >= 0 ? 'positive' : 'negative'}`}>
                                {strategy.pnl >= 0 ? '+' : ''}{strategy.pnl?.toFixed(2)}%
                            </div>
                        </div>
                    ))}
                </div>
            );
        }
        
        // 텔레그램 위젯
        function TelegramWidget({ data }) {
            const [message, setMessage] = useState('');
            const [sending, setSending] = useState(false);
            
            const sendMessage = async () => {
                if (!message.trim()) return;
                
                setSending(true);
                try {
                    const response = await fetch('/api/telegram/send', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': 'Bearer letrade-web-token'
                        },
                        body: JSON.stringify({ message: message.trim() })
                    });
                    
                    if (response.ok) {
                        setMessage('');
                        console.log('텔레그램 메시지 전송 성공');
                    }
                } catch (error) {
                    console.error('텔레그램 메시지 전송 오류:', error);
                } finally {
                    setSending(false);
                }
            };
            
            return (
                <div className="widget">
                    <div className="widget-header">
                        <h3 className="widget-title">📱 텔레그램 연동</h3>
                        <span style={{color: 'var(--accent-green)', fontSize: '12px'}}>연결됨</span>
                    </div>
                    
                    <div style={{marginBottom: '16px'}}>
                        <h4 style={{fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '8px'}}>최근 활동</h4>
                        <div style={{maxHeight: '100px', overflowY: 'auto'}}>
                            {data && data.slice(-3).map((activity, index) => (
                                <div key={index} style={{fontSize: '12px', padding: '4px 0', borderBottom: '1px solid var(--border-primary)'}}>
                                    <span style={{color: 'var(--text-muted)'}}>
                                        {new Date(activity.timestamp).toLocaleTimeString()}
                                    </span>
                                    <span style={{marginLeft: '8px'}}>
                                        {activity.type === 'outgoing' ? '📤' : '📥'} {activity.content || activity.message}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                    
                    <div style={{display: 'flex', gap: '8px'}}>
                        <input
                            type="text"
                            value={message}
                            onChange={(e) => setMessage(e.target.value)}
                            placeholder="테스트 메시지..."
                            style={{
                                flex: 1,
                                padding: '8px',
                                background: 'var(--bg-tertiary)',
                                border: '1px solid var(--border-primary)',
                                borderRadius: '4px',
                                color: 'var(--text-primary)',
                                fontSize: '12px'
                            }}
                            onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                        />
                        <button 
                            className="btn btn-primary" 
                            onClick={sendMessage}
                            disabled={sending || !message.trim()}
                            style={{fontSize: '12px'}}
                        >
                            📤
                        </button>
                    </div>
                </div>
            );
        }
        
        // 성과 위젯
        function PerformanceWidget({ data }) {
            if (!data) return <div className="widget"><div className="loading">로딩...</div></div>;
            
            return (
                <div className="widget">
                    <div className="widget-header">
                        <h3 className="widget-title">📈 성과 차트</h3>
                        <span style={{fontSize: '12px', color: 'var(--text-secondary)'}}>24시간</span>
                    </div>
                    
                    <div style={{textAlign: 'center', padding: '20px'}}>
                        <div style={{fontSize: '24px', marginBottom: '8px'}}>
                            📊
                        </div>
                        <div style={{fontSize: '14px', color: 'var(--text-secondary)'}}>
                            차트 구현 예정
                        </div>
                    </div>
                    
                    <div className="metric-grid">
                        <div className="metric-item">
                            <span className="metric-label">일일 수익률</span>
                            <span className={`metric-value change ${data.total_pnl >= 0 ? 'positive' : 'negative'}`}>
                                {data.total_pnl_percent >= 0 ? '+' : ''}{data.total_pnl_percent?.toFixed(2)}%
                            </span>
                        </div>
                        <div className="metric-item">
                            <span className="metric-label">오늘 거래</span>
                            <span className="metric-value">{data.trades_today || 0}건</span>
                        </div>
                    </div>
                </div>
            );
        }
        
        // 앱 렌더링
        ReactDOM.render(<Dashboard />, document.getElementById('dashboard-root'));
    </script>
</body>
</html>
        """

# 웹 인터페이스 인스턴스 생성
web_interface = WebInterface()
app = web_interface.app

async def startup_event():
    """서버 시작 시 실행"""
    logger.info("🚀 바이낸스 스타일 웹 인터페이스 시작")
    await web_interface.start_background_tasks()

app.add_event_handler("startup", startup_event)

if __name__ == "__main__":
    import os
    
    # 환경 변수 설정
    host = os.getenv("WEB_HOST", "127.0.0.1")
    port = int(os.getenv("WEB_PORT", "8080"))
    
    uvicorn.run(
        "web_interface.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )