"""
WebSocket-based Exchange Connector for real-time data streaming
실시간 시장 데이터를 위한 WebSocket 기반 거래소 연결기

이 모듈은 성능 최적화를 위해 다음 기능을 제공합니다:
- WebSocket 실시간 데이터 스트리밍
- 연결 풀링 및 재사용
- 로컬 캐싱으로 레이턴시 최소화
- 자동 재연결 및 에러 복구
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Callable, Set
from dataclasses import dataclass, field
from collections import defaultdict, deque
import websockets
import aiohttp

from .interfaces import (
    IExchangeConnector, ExchangeConfig, MarketData as NewMarketData,
    OrderRequest as NewOrderRequest, OrderResponse, AccountBalance,
    OrderSide as NewOrderSide, OrderType as NewOrderType, OrderStatus as NewOrderStatus
)

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """캐시 엔트리"""
    data: Any
    timestamp: float
    ttl: float = 1.0  # 1초 TTL


class PriceCache:
    """가격 데이터 캐시 (최대 성능을 위한 로컬 캐싱)"""
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 1.0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: deque = deque()  # LRU용
        
    def get(self, key: str) -> Optional[Any]:
        """캐시에서 데이터 조회"""
        entry = self._cache.get(key)
        if not entry:
            return None
            
        # TTL 확인
        if time.time() - entry.timestamp > entry.ttl:
            self.remove(key)
            return None
            
        # LRU 업데이트
        try:
            self._access_order.remove(key)
        except ValueError:
            pass
        self._access_order.append(key)
        
        return entry.data
    
    def set(self, key: str, data: Any, ttl: Optional[float] = None) -> None:
        """캐시에 데이터 저장"""
        if len(self._cache) >= self.max_size and key not in self._cache:
            # LRU 제거
            oldest_key = self._access_order.popleft()
            self._cache.pop(oldest_key, None)
        
        entry = CacheEntry(
            data=data,
            timestamp=time.time(),
            ttl=ttl or self.default_ttl
        )
        
        self._cache[key] = entry
        
        # LRU 업데이트
        try:
            self._access_order.remove(key)
        except ValueError:
            pass
        self._access_order.append(key)
    
    def remove(self, key: str) -> None:
        """캐시에서 항목 제거"""
        self._cache.pop(key, None)
        try:
            self._access_order.remove(key)
        except ValueError:
            pass
    
    def clear(self) -> None:
        """캐시 전체 삭제"""
        self._cache.clear()
        self._access_order.clear()
    
    def size(self) -> int:
        """현재 캐시 크기"""
        return len(self._cache)


class WebSocketStreamManager:
    """WebSocket 스트림 관리자"""
    
    def __init__(self, exchange_name: str):
        self.exchange_name = exchange_name.lower()
        self.connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.running = False
        self._reconnect_delays = defaultdict(int)
        self.max_reconnect_delay = 60
        
        # Binance WebSocket URLs
        self.ws_urls = {
            'binance': 'wss://stream.binance.com:9443/ws',
            'binance_testnet': 'wss://testnet.binance.vision/ws'
        }
        
    async def start(self):
        """스트림 관리자 시작"""
        self.running = True
        logger.info(f"WebSocket stream manager started for {self.exchange_name}")
    
    async def stop(self):
        """스트림 관리자 중지"""
        self.running = False
        
        # 모든 연결 종료
        for stream_id, ws in self.connections.items():
            try:
                await ws.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket {stream_id}: {e}")
        
        self.connections.clear()
        self.subscribers.clear()
        logger.info("WebSocket stream manager stopped")
    
    async def subscribe_ticker(self, symbol: str, callback: Callable) -> bool:
        """실시간 티커 구독"""
        try:
            # 심볼 표준화 (BTC/USDT -> btcusdt)
            normalized_symbol = symbol.replace('/', '').lower()
            stream_id = f"{normalized_symbol}@ticker"
            
            # 콜백 등록
            self.subscribers[stream_id].append(callback)
            
            # 기존 연결이 있으면 재사용
            if stream_id in self.connections:
                logger.debug(f"Reusing existing WebSocket connection for {stream_id}")
                return True
            
            # 새 WebSocket 연결 생성
            await self._create_connection(stream_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe to ticker {symbol}: {e}")
            return False
    
    async def subscribe_kline(self, symbol: str, interval: str, callback: Callable) -> bool:
        """실시간 K라인 구독"""
        try:
            normalized_symbol = symbol.replace('/', '').lower()
            stream_id = f"{normalized_symbol}@kline_{interval}"
            
            self.subscribers[stream_id].append(callback)
            
            if stream_id in self.connections:
                return True
            
            await self._create_connection(stream_id)
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe to kline {symbol}: {e}")
            return False
    
    async def _create_connection(self, stream_id: str) -> None:
        """WebSocket 연결 생성"""
        if not self.running:
            return
        
        ws_url = self.ws_urls.get(self.exchange_name, self.ws_urls['binance'])
        
        try:
            # WebSocket 연결
            ws = await websockets.connect(
                f"{ws_url}/{stream_id}",
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            
            self.connections[stream_id] = ws
            self._reconnect_delays[stream_id] = 0
            
            # 메시지 처리 태스크 시작
            asyncio.create_task(self._handle_messages(stream_id, ws))
            
            logger.info(f"WebSocket connected: {stream_id}")
            
        except Exception as e:
            logger.error(f"Failed to create WebSocket connection {stream_id}: {e}")
            await self._schedule_reconnect(stream_id)
    
    async def _handle_messages(self, stream_id: str, ws):
        """WebSocket 메시지 처리"""
        try:
            async for message in ws:
                if not self.running:
                    break
                
                try:
                    data = json.loads(message)
                    await self._process_message(stream_id, data)
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON from {stream_id}: {e}")
                except Exception as e:
                    logger.error(f"Error processing message from {stream_id}: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"WebSocket connection closed: {stream_id}")
        except Exception as e:
            logger.error(f"WebSocket error for {stream_id}: {e}")
        finally:
            # 연결 정리
            self.connections.pop(stream_id, None)
            if self.running:
                await self._schedule_reconnect(stream_id)
    
    async def _process_message(self, stream_id: str, data: Dict) -> None:
        """메시지 처리 및 콜백 실행"""
        try:
            # 구독자들에게 데이터 전달
            callbacks = self.subscribers.get(stream_id, [])
            
            for callback in callbacks:
                try:
                    # 비동기 콜백 처리
                    if asyncio.iscoroutinefunction(callback):
                        await callback(stream_id, data)
                    else:
                        callback(stream_id, data)
                except Exception as e:
                    logger.error(f"Callback error for {stream_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in message processing for {stream_id}: {e}")
    
    async def _schedule_reconnect(self, stream_id: str) -> None:
        """재연결 스케줄링"""
        if not self.running:
            return
        
        delay = min(self._reconnect_delays[stream_id], self.max_reconnect_delay)
        if delay == 0:
            delay = 1
        else:
            delay = min(delay * 2, self.max_reconnect_delay)
        
        self._reconnect_delays[stream_id] = delay
        
        logger.info(f"Scheduling reconnect for {stream_id} in {delay}s")
        await asyncio.sleep(delay)
        await self._create_connection(stream_id)


class OptimizedExchangeConnector(IExchangeConnector):
    """최적화된 거래소 연결기 (WebSocket + 캐싱)"""
    
    def __init__(self, config: ExchangeConfig):
        """초기화"""
        self.config = config
        self.exchange_name = config.exchange_name
        self.is_connected = False
        
        # 성능 최적화 컴포넌트
        self.price_cache = PriceCache(max_size=1000, default_ttl=0.5)  # 500ms 캐시
        self.ws_manager = WebSocketStreamManager(self.exchange_name)
        
        # REST API 세션 (연결 풀링)
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = self._get_rest_base_url()
        
        # 통계
        self.stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'ws_messages': 0,
            'rest_requests': 0
        }
        
        logger.info(f"Optimized Exchange Connector initialized for {config.exchange_name}")
    
    def _get_rest_base_url(self) -> str:
        """REST API 기본 URL 반환"""
        if self.config.sandbox:
            return "https://testnet.binance.vision"
        return "https://api.binance.com"
    
    async def connect(self) -> bool:
        """거래소 연결"""
        try:
            # HTTP 세션 생성 (연결 풀링)
            connector = aiohttp.TCPConnector(
                limit=100,  # 최대 연결 수
                limit_per_host=30,  # 호스트당 최대 연결 수
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            
            timeout = aiohttp.ClientTimeout(total=10)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'User-Agent': 'Letrade/1.0',
                    'Content-Type': 'application/json'
                }
            )
            
            # WebSocket 스트림 관리자 시작
            await self.ws_manager.start()
            
            # 연결 테스트
            await self._test_connection()
            
            self.is_connected = True
            logger.info(f"Successfully connected to {self.exchange_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to exchange: {e}")
            await self.disconnect()
            return False
    
    async def disconnect(self) -> bool:
        """거래소 연결 해제"""
        try:
            self.is_connected = False
            
            # WebSocket 스트림 관리자 중지
            if self.ws_manager:
                await self.ws_manager.stop()
            
            # HTTP 세션 종료
            if self.session:
                await self.session.close()
                self.session = None
            
            # 캐시 정리
            self.price_cache.clear()
            
            logger.info(f"Disconnected from {self.exchange_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
            return False
    
    async def get_market_data(self, symbol: str, timeframe: str = '1m', limit: int = 100) -> List[NewMarketData]:
        """시장 데이터 조회 (캐시 우선)"""
        cache_key = f"market_data:{symbol}:{timeframe}:{limit}"
        
        # 캐시 확인
        cached_data = self.price_cache.get(cache_key)
        if cached_data:
            self.stats['cache_hits'] += 1
            logger.debug(f"Cache hit for {cache_key}")
            return cached_data
        
        self.stats['cache_misses'] += 1
        
        # REST API 호출
        try:
            start_time = time.time()
            
            # 심볼 표준화
            api_symbol = symbol.replace('/', '')
            
            # API 호출
            params = {
                'symbol': api_symbol,
                'interval': timeframe,
                'limit': limit
            }
            
            async with self.session.get(f"{self.base_url}/api/v3/klines", params=params) as response:
                if response.status != 200:
                    raise Exception(f"API error: {response.status}")
                
                klines = await response.json()
                self.stats['rest_requests'] += 1
            
            # 데이터 변환
            market_data = []
            for kline in klines:
                market_data.append(NewMarketData(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(kline[0] / 1000, timezone.utc),
                    open=Decimal(str(kline[1])),
                    high=Decimal(str(kline[2])),
                    low=Decimal(str(kline[3])),
                    close=Decimal(str(kline[4])),
                    volume=Decimal(str(kline[5]))
                ))
            
            # 캐시 저장 (짧은 TTL로 자주 업데이트)
            self.price_cache.set(cache_key, market_data, ttl=2.0)
            
            elapsed = (time.time() - start_time) * 1000
            logger.debug(f"Market data fetched in {elapsed:.2f}ms")
            
            return market_data
            
        except Exception as e:
            logger.error(f"Failed to fetch market data: {e}")
            raise
    
    async def subscribe_market_data(self, symbols: List[str], callback: Callable[[NewMarketData], None]) -> bool:
        """실시간 시장 데이터 구독"""
        try:
            success_count = 0
            
            for symbol in symbols:
                # 티커 구독 (가격 업데이트)
                ticker_success = await self.ws_manager.subscribe_ticker(
                    symbol, 
                    lambda stream_id, data: self._handle_ticker_update(symbol, data, callback)
                )
                
                # K라인 구독 (봉 데이터)
                kline_success = await self.ws_manager.subscribe_kline(
                    symbol, 
                    '1m',
                    lambda stream_id, data: self._handle_kline_update(symbol, data, callback)
                )
                
                if ticker_success and kline_success:
                    success_count += 1
            
            logger.info(f"Subscribed to real-time data for {success_count}/{len(symbols)} symbols")
            return success_count == len(symbols)
            
        except Exception as e:
            logger.error(f"Failed to subscribe to market data: {e}")
            return False
    
    async def _handle_ticker_update(self, symbol: str, data: Dict, callback: Callable) -> None:
        """티커 업데이트 처리"""
        try:
            if 'c' in data:  # 현재 가격
                # 간단한 MarketData 객체 생성 (티커용)
                market_data = NewMarketData(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(data.get('E', time.time() * 1000) / 1000, timezone.utc),
                    open=Decimal(str(data.get('o', '0'))),
                    high=Decimal(str(data.get('h', '0'))),
                    low=Decimal(str(data.get('l', '0'))),
                    close=Decimal(str(data.get('c', '0'))),
                    volume=Decimal(str(data.get('v', '0')))
                )
                
                # 캐시 업데이트
                cache_key = f"latest_price:{symbol}"
                self.price_cache.set(cache_key, market_data, ttl=1.0)
                
                # 콜백 실행
                if callback:
                    callback(market_data)
                
                self.stats['ws_messages'] += 1
                
        except Exception as e:
            logger.error(f"Error handling ticker update: {e}")
    
    async def _handle_kline_update(self, symbol: str, data: Dict, callback: Callable) -> None:
        """K라인 업데이트 처리"""
        try:
            if 'k' in data:
                kline = data['k']
                
                market_data = NewMarketData(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(kline['t'] / 1000, timezone.utc),
                    open=Decimal(str(kline['o'])),
                    high=Decimal(str(kline['h'])),
                    low=Decimal(str(kline['l'])),
                    close=Decimal(str(kline['c'])),
                    volume=Decimal(str(kline['v']))
                )
                
                # 콜백 실행
                if callback:
                    callback(market_data)
                
                self.stats['ws_messages'] += 1
                
        except Exception as e:
            logger.error(f"Error handling kline update: {e}")
    
    async def _test_connection(self) -> None:
        """연결 테스트"""
        try:
            async with self.session.get(f"{self.base_url}/api/v3/ping") as response:
                if response.status != 200:
                    raise Exception(f"Connection test failed: {response.status}")
        except Exception as e:
            raise Exception(f"Connection test failed: {e}")
    
    async def place_order(self, order_request: NewOrderRequest) -> OrderResponse:
        """주문 실행 (Mock 구현)"""
        # 실제 주문 실행 로직 구현 필요
        raise NotImplementedError("Order placement not implemented in optimized connector")
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """주문 취소 (Mock 구현)"""
        raise NotImplementedError("Order cancellation not implemented in optimized connector")
    
    async def get_order_status(self, order_id: str, symbol: str) -> OrderResponse:
        """주문 상태 조회 (Mock 구현)"""
        raise NotImplementedError("Order status check not implemented in optimized connector")
    
    async def get_account_balance(self) -> Dict[str, AccountBalance]:
        """계정 잔고 조회 (Mock 구현)""" 
        raise NotImplementedError("Account balance check not implemented in optimized connector")
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[OrderResponse]:
        """열린 주문 조회 (Mock 구현)"""
        raise NotImplementedError("Open orders check not implemented in optimized connector")
    
    async def health_check(self) -> Dict[str, Any]:
        """헬스체크"""
        return {
            'exchange': self.exchange_name,
            'connected': self.is_connected,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'cache_size': self.price_cache.size(),
            'websocket_connections': len(self.ws_manager.connections),
            'statistics': self.stats
        }
    
    async def cleanup(self) -> bool:
        """리소스 정리"""
        return await self.disconnect()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """성능 통계 반환"""
        cache_hit_rate = 0
        if self.stats['cache_hits'] + self.stats['cache_misses'] > 0:
            cache_hit_rate = self.stats['cache_hits'] / (self.stats['cache_hits'] + self.stats['cache_misses'])
        
        return {
            'cache_hit_rate': cache_hit_rate,
            'cache_size': self.price_cache.size(),
            'websocket_connections': len(self.ws_manager.connections),
            'total_cache_hits': self.stats['cache_hits'],
            'total_cache_misses': self.stats['cache_misses'],
            'total_ws_messages': self.stats['ws_messages'],
            'total_rest_requests': self.stats['rest_requests']
        }


# Factory function
def create_optimized_connector(config: ExchangeConfig) -> OptimizedExchangeConnector:
    """최적화된 거래소 연결기 생성"""
    return OptimizedExchangeConnector(config)