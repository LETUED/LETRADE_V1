#!/usr/bin/env python3
"""
WebSocket 연결 테스트 스크립트
Binance WebSocket 스트림 연결 및 실시간 데이터 수신 테스트
"""

import asyncio
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.exchange_connector.websocket_connector import (
    WebSocketStreamManager, OptimizedExchangeConnector
)
from src.exchange_connector.interfaces import ExchangeConfig
from src.common.config import load_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WebSocketTester:
    """WebSocket 연결 테스터"""
    
    def __init__(self):
        self.received_messages = []
        self.start_time = datetime.now()
        
    async def on_ticker_update(self, stream_id: str, data: dict):
        """티커 업데이트 콜백"""
        self.received_messages.append(data)
        
        if 's' in data:  # Binance ticker format
            symbol = data['s']
            price = data.get('c', 'N/A')  # Current price
            volume = data.get('v', 'N/A')  # Volume
            
            logger.info(f"[{stream_id}] {symbol}: Price={price}, Volume={volume}")
        else:
            logger.info(f"[{stream_id}] Data: {json.dumps(data, indent=2)}")
            
        # 성능 통계
        if len(self.received_messages) % 100 == 0:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            rate = len(self.received_messages) / elapsed
            logger.info(f"📊 Stats: {len(self.received_messages)} messages, {rate:.2f} msg/s")


async def test_websocket_streams():
    """WebSocket 스트림 테스트"""
    logger.info("🚀 Starting WebSocket connection test...")
    
    # WebSocket Manager 생성
    ws_manager = WebSocketStreamManager("binance")
    tester = WebSocketTester()
    
    try:
        # WebSocket Manager 시작
        await ws_manager.start()
        logger.info("✅ WebSocket manager started")
        
        # 스트림 구독
        symbols = ["btcusdt", "ethusdt", "bnbusdt"]
        
        for symbol in symbols:
            # Ticker 스트림 구독
            stream_id = f"{symbol}@ticker"
            ws_manager.subscribe(stream_id, tester.on_ticker_update)
            logger.info(f"📡 Subscribed to {stream_id}")
            
        # 연결 대기
        await asyncio.sleep(2)
        
        # 실시간 데이터 수신 (30초)
        logger.info("📊 Receiving real-time data for 30 seconds...")
        await asyncio.sleep(30)
        
        # 통계 출력
        logger.info(f"\n📈 Final Statistics:")
        logger.info(f"- Total messages: {len(tester.received_messages)}")
        logger.info(f"- Duration: 30 seconds")
        logger.info(f"- Average rate: {len(tester.received_messages)/30:.2f} msg/s")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        
    finally:
        # 정리
        await ws_manager.stop()
        logger.info("🛑 WebSocket manager stopped")


async def test_optimized_connector():
    """최적화된 Exchange Connector 테스트"""
    logger.info("\n🚀 Testing Optimized Exchange Connector...")
    
    # 설정 로드
    config = ExchangeConfig(
        exchange_name="binance",
        api_key=os.getenv("BINANCE_API_KEY", ""),
        api_secret=os.getenv("BINANCE_SECRET_KEY", ""),
        testnet=True
    )
    
    # Connector 생성
    connector = OptimizedExchangeConnector(config)
    
    try:
        # 연결
        await connector.connect()
        logger.info("✅ Connector connected")
        
        # 실시간 가격 조회 (캐시 활용)
        symbols = ["BTC/USDT", "ETH/USDT"]
        
        # 첫 번째 조회 (캐시 미스)
        start = asyncio.get_event_loop().time()
        for symbol in symbols:
            price = await connector.get_ticker(symbol)
            logger.info(f"💰 {symbol}: ${price:.2f}")
        first_time = asyncio.get_event_loop().time() - start
        
        # 짧은 대기
        await asyncio.sleep(0.1)
        
        # 두 번째 조회 (캐시 히트)
        start = asyncio.get_event_loop().time()
        for symbol in symbols:
            price = await connector.get_ticker(symbol)
            logger.info(f"💰 {symbol}: ${price:.2f} (cached)")
        second_time = asyncio.get_event_loop().time() - start
        
        # 성능 비교
        logger.info(f"\n⚡ Performance Comparison:")
        logger.info(f"- First query: {first_time*1000:.2f}ms")
        logger.info(f"- Cached query: {second_time*1000:.2f}ms")
        logger.info(f"- Speed improvement: {first_time/second_time:.1f}x")
        
        # 통계 출력
        stats = connector.get_statistics()
        logger.info(f"\n📊 Connector Statistics:")
        for key, value in stats.items():
            logger.info(f"- {key}: {value}")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        
    finally:
        # 연결 해제
        await connector.disconnect()
        logger.info("🛑 Connector disconnected")


async def main():
    """메인 테스트 함수"""
    # WebSocket 스트림 테스트
    await test_websocket_streams()
    
    # 최적화된 Connector 테스트
    await test_optimized_connector()


if __name__ == "__main__":
    asyncio.run(main())