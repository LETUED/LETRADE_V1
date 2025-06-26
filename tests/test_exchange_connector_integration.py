"""
Exchange Connector 통합 테스트
실제 Binance API와의 통합 테스트 (Testnet 사용)
"""

import pytest
import asyncio
import os
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.exchange_connector.main import CCXTExchangeConnector
from src.exchange_connector.websocket_connector import OptimizedExchangeConnector
from src.exchange_connector.interfaces import (
    ExchangeConfig, OrderRequest, OrderSide, OrderType, OrderStatus
)
from src.common.message_bus import MessageBus


class TestExchangeConnectorIntegration:
    """Exchange Connector 통합 테스트"""
    
    @pytest.fixture
    def exchange_config(self):
        """Exchange 설정"""
        return ExchangeConfig(
            exchange_name="binance",
            api_key=os.getenv("BINANCE_TESTNET_API_KEY", "test_key"),
            api_secret=os.getenv("BINANCE_TESTNET_SECRET_KEY", "test_secret"),
            testnet=True
        )
    
    @pytest.fixture
    async def connector(self, exchange_config):
        """CCXT Connector 인스턴스"""
        connector = CCXTExchangeConnector(exchange_config)
        await connector.connect()
        yield connector
        await connector.disconnect()
    
    @pytest.fixture
    async def optimized_connector(self, exchange_config):
        """최적화된 Connector 인스턴스"""
        connector = OptimizedExchangeConnector(exchange_config)
        await connector.connect()
        yield connector
        await connector.disconnect()
    
    @pytest.mark.asyncio
    async def test_connection_and_authentication(self, connector):
        """연결 및 인증 테스트"""
        assert connector.is_connected
        
        # 계정 잔액 조회로 인증 확인
        balance = await connector.get_balance()
        assert balance is not None
        assert hasattr(balance, 'total')
        assert hasattr(balance, 'free')
        assert hasattr(balance, 'used')
    
    @pytest.mark.asyncio
    async def test_market_data_retrieval(self, connector):
        """시장 데이터 조회 테스트"""
        # Ticker 조회
        ticker = await connector.get_ticker("BTC/USDT")
        assert ticker > 0
        assert isinstance(ticker, (int, float, Decimal))
        
        # Order Book 조회
        orderbook = await connector.get_orderbook("BTC/USDT", limit=10)
        assert 'bids' in orderbook
        assert 'asks' in orderbook
        assert len(orderbook['bids']) > 0
        assert len(orderbook['asks']) > 0
    
    @pytest.mark.asyncio
    async def test_websocket_real_time_data(self, optimized_connector):
        """WebSocket 실시간 데이터 테스트"""
        received_updates = []
        
        # 콜백 함수
        def on_price_update(symbol: str, price: float):
            received_updates.append({
                'symbol': symbol,
                'price': price,
                'timestamp': datetime.now()
            })
        
        # 가격 업데이트 구독
        optimized_connector.subscribe_ticker("BTC/USDT", on_price_update)
        
        # 5초간 데이터 수집
        await asyncio.sleep(5)
        
        # 검증
        assert len(received_updates) > 0
        
        # 업데이트 빈도 확인
        if len(received_updates) > 1:
            time_diffs = []
            for i in range(1, len(received_updates)):
                diff = (received_updates[i]['timestamp'] - 
                       received_updates[i-1]['timestamp']).total_seconds()
                time_diffs.append(diff)
            
            avg_interval = sum(time_diffs) / len(time_diffs)
            assert avg_interval < 2.0  # 평균 2초 미만 간격
    
    @pytest.mark.asyncio
    async def test_order_lifecycle(self, connector):
        """주문 생명주기 테스트 (Testnet)"""
        # 현재 가격 조회
        current_price = await connector.get_ticker("BTC/USDT")
        
        # 매수 주문 생성 (현재가보다 낮은 가격으로)
        order_request = OrderRequest(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.001"),  # 최소 주문량
            price=Decimal(str(current_price * 0.9))  # 10% 낮은 가격
        )
        
        # 주문 실행
        response = await connector.place_order(order_request)
        assert response.success
        assert response.order_id is not None
        assert response.status == OrderStatus.PENDING
        
        # 주문 상태 확인
        await asyncio.sleep(1)
        order_info = await connector.get_order_status(response.order_id, "BTC/USDT")
        assert order_info is not None
        
        # 주문 취소
        cancel_result = await connector.cancel_order(response.order_id, "BTC/USDT")
        assert cancel_result
        
        # 취소 확인
        await asyncio.sleep(1)
        order_info = await connector.get_order_status(response.order_id, "BTC/USDT")
        assert order_info['status'] == 'canceled'
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self, connector):
        """Circuit Breaker 기능 테스트"""
        # 실패 카운터 초기화
        connector._circuit_breaker_failures = 0
        
        # 임시로 잘못된 심볼로 실패 유도
        for i in range(connector.max_failures + 2):
            try:
                await connector.get_ticker("INVALID/SYMBOL")
            except Exception:
                pass
        
        # Circuit이 열렸는지 확인
        assert connector._circuit_breaker_open
        
        # Circuit이 열린 상태에서 요청 시도
        with pytest.raises(Exception) as exc_info:
            await connector.get_ticker("BTC/USDT")
        
        assert "Circuit breaker is open" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, connector):
        """Rate Limiting 테스트"""
        request_times = []
        
        # 연속적인 요청
        for i in range(10):
            start = asyncio.get_event_loop().time()
            try:
                await connector.get_ticker("BTC/USDT")
                elapsed = asyncio.get_event_loop().time() - start
                request_times.append(elapsed)
            except Exception as e:
                # Rate limit 에러 처리
                if "rate limit" in str(e).lower():
                    await asyncio.sleep(1)
        
        # 요청 간격 확인
        assert len(request_times) > 0
        avg_time = sum(request_times) / len(request_times)
        assert avg_time < 1.0  # 평균 응답 시간 1초 미만
    
    @pytest.mark.asyncio
    async def test_error_recovery(self, connector):
        """에러 복구 테스트"""
        # 연결 끊기
        await connector.disconnect()
        assert not connector.is_connected
        
        # 재연결
        await connector.connect()
        assert connector.is_connected
        
        # 정상 작동 확인
        ticker = await connector.get_ticker("BTC/USDT")
        assert ticker > 0
    
    @pytest.mark.asyncio
    async def test_performance_optimization(self, optimized_connector):
        """성능 최적화 테스트"""
        # 첫 번째 요청 (캐시 미스)
        start1 = asyncio.get_event_loop().time()
        price1 = await optimized_connector.get_ticker("BTC/USDT")
        time1 = asyncio.get_event_loop().time() - start1
        
        # 두 번째 요청 (캐시 히트)
        start2 = asyncio.get_event_loop().time()
        price2 = await optimized_connector.get_ticker("BTC/USDT")
        time2 = asyncio.get_event_loop().time() - start2
        
        # 캐시 효과 확인
        assert price1 == price2  # 같은 가격 (캐시됨)
        assert time2 < time1 * 0.5  # 두 번째 요청이 50% 이상 빠름
        
        # 통계 확인
        stats = optimized_connector.get_statistics()
        assert stats['cache_hits'] > 0


class TestMessageBusIntegration:
    """Message Bus 통합 테스트"""
    
    @pytest.fixture
    async def message_bus(self):
        """Message Bus 인스턴스"""
        bus = MessageBus()
        await bus.connect()
        yield bus
        await bus.disconnect()
    
    @pytest.mark.asyncio
    async def test_exchange_connector_message_flow(self, message_bus):
        """Exchange Connector 메시지 플로우 테스트"""
        received_messages = []
        
        # 메시지 핸들러
        async def on_trade_executed(topic: str, message: dict):
            received_messages.append(message)
        
        # 구독
        await message_bus.subscribe("events.trade_executed", on_trade_executed)
        
        # 거래 실행 메시지 발행
        trade_message = {
            "order_id": "TEST123",
            "symbol": "BTC/USDT",
            "side": "buy",
            "quantity": 0.001,
            "price": 50000.0,
            "status": "filled",
            "timestamp": datetime.now().isoformat()
        }
        
        await message_bus.publish(
            "letrade.events",
            "trade_executed",
            trade_message
        )
        
        # 메시지 수신 대기
        await asyncio.sleep(0.5)
        
        # 검증
        assert len(received_messages) == 1
        assert received_messages[0]['order_id'] == "TEST123"


@pytest.mark.asyncio
async def test_end_to_end_trading_flow():
    """End-to-End 거래 플로우 테스트"""
    # 설정
    config = ExchangeConfig(
        exchange_name="binance",
        api_key=os.getenv("BINANCE_TESTNET_API_KEY", ""),
        api_secret=os.getenv("BINANCE_TESTNET_SECRET_KEY", ""),
        testnet=True
    )
    
    # 컴포넌트 생성
    message_bus = MessageBus()
    connector = CCXTExchangeConnector(config)
    
    try:
        # 연결
        await message_bus.connect()
        await connector.connect()
        
        # 메시지 핸들러 설정
        trade_responses = []
        
        async def on_trade_response(topic: str, message: dict):
            trade_responses.append(message)
        
        await message_bus.subscribe("events.trade_executed", on_trade_response)
        
        # 거래 시나리오
        # 1. 현재 가격 조회
        current_price = await connector.get_ticker("BTC/USDT")
        
        # 2. 주문 생성
        order = OrderRequest(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.001"),
            price=Decimal(str(current_price * 0.95))
        )
        
        # 3. 주문 실행
        response = await connector.place_order(order)
        
        # 4. 메시지 발행
        if response.success:
            await message_bus.publish(
                "letrade.events",
                "trade_executed",
                {
                    "order_id": response.order_id,
                    "symbol": order.symbol,
                    "side": order.side.value,
                    "quantity": float(order.quantity),
                    "price": float(order.price),
                    "status": response.status.value
                }
            )
        
        # 5. 응답 확인
        await asyncio.sleep(1)
        assert len(trade_responses) > 0
        
        # 6. 주문 취소
        await connector.cancel_order(response.order_id, "BTC/USDT")
        
    finally:
        # 정리
        await connector.disconnect()
        await message_bus.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])