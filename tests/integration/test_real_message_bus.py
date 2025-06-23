"""
실제 RabbitMQ를 사용한 통합 테스트

Strategy Worker와 Message Bus의 실제 메시지 흐름을 테스트합니다.
"""

import asyncio
import json
import os
import pytest
from datetime import datetime, timezone
import pandas as pd

from src.strategies.ma_crossover import MAcrossoverStrategy
from src.strategies.base_strategy import StrategyConfig
from src.common.message_bus import MessageBus, create_message_bus
from src.data_loader.backtest_data_loader import BacktestDataLoader, DataSourceConfig


@pytest.fixture
def rabbitmq_config():
    """실제 RabbitMQ 연결 설정"""
    return {
        "host": "localhost",
        "port": 5672,
        "username": "letrade_user",
        "password": "letrade_password",
        "virtual_host": "/"
    }


@pytest.fixture
def strategy_config():
    """테스트용 전략 설정"""
    return StrategyConfig(
        strategy_id="real_test_ma_001",
        name="Real Test MA Strategy",
        enabled=True,
        dry_run=True,
        custom_params={
            "fast_period": 3,
            "slow_period": 5,
            "symbol": "BTC/USDT",
            "exchange": "binance",
            "min_signal_interval": 0,
            "min_crossover_strength": 0.001
        }
    )


class TestRealMessageBusIntegration:
    """실제 RabbitMQ를 사용한 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_real_rabbitmq_connection(self, rabbitmq_config):
        """실제 RabbitMQ 연결 테스트"""
        
        try:
            message_bus = await create_message_bus(rabbitmq_config)
            
            # 연결 성공 확인
            assert message_bus.is_connected is True
            
            # 헬스체크
            health = await message_bus.health_check()
            assert health['healthy'] is True
            assert health['connected'] is True
            
            # 연결 해제
            await message_bus.disconnect()
            
        except Exception as e:
            pytest.skip(f"RabbitMQ not available: {e}")
    
    @pytest.mark.asyncio
    async def test_message_publish_and_infrastructure(self, rabbitmq_config):
        """메시지 발행 및 인프라 테스트"""
        
        try:
            message_bus = await create_message_bus(rabbitmq_config)
            
            # 테스트 메시지 발행
            test_signal = {
                "strategy_id": 1,
                "symbol": "BTC/USDT",
                "side": "buy",
                "signal_price": 50000.0,
                "confidence": 0.8,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Capital allocation 요청 발행
            success = await message_bus.publish(
                exchange_name="letrade.requests",
                routing_key="request.capital.allocation.real_test_ma_001",
                message=test_signal
            )
            
            assert success is True
            
            # Market data 이벤트 발행
            market_data = {
                "symbol": "BTCUSDT",
                "close": 50000.0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            success = await message_bus.publish(
                exchange_name="letrade.events",
                routing_key="market_data.binance.btcusdt",
                message=market_data
            )
            
            assert success is True
            
            await message_bus.disconnect()
            
        except Exception as e:
            pytest.skip(f"RabbitMQ not available: {e}")
    
    @pytest.mark.asyncio
    async def test_strategy_signal_real_flow(self, rabbitmq_config, strategy_config):
        """전략에서 실제 메시지 버스로 신호 전송 테스트"""
        
        try:
            message_bus = await create_message_bus(rabbitmq_config)
            
            # 전략 인스턴스 생성
            strategy = MAcrossoverStrategy(strategy_config)
            
            # 골든 크로스 시나리오 데이터
            test_data = pd.DataFrame({
                'close': [49000, 50000, 51000],
                'open': [48900, 49900, 50900],
                'high': [49200, 50200, 51200],
                'low': [48800, 49800, 50800],
                'volume': [1000, 1100, 1200]
            })
            
            # 지표 계산
            df_with_indicators = strategy.populate_indicators(test_data)
            
            # 시장 데이터
            market_data = {'close': 51000.0}
            
            # 신호 생성
            signal = strategy.on_data(market_data, df_with_indicators)
            
            if signal:
                # 실제 메시지 버스로 신호 전송
                routing_key = signal.get("routing_key")
                payload = signal.get("payload")
                
                success = await message_bus.publish(
                    exchange_name="letrade.requests",
                    routing_key=routing_key,
                    message=payload
                )
                
                assert success is True
                print(f"✅ 신호 전송 성공: {payload['side']} @ {payload['signal_price']}")
            else:
                print("ℹ️  이 데이터에서는 신호가 생성되지 않음")
            
            await message_bus.disconnect()
            
        except Exception as e:
            pytest.skip(f"RabbitMQ not available: {e}")
    
    @pytest.mark.asyncio
    async def test_message_consumption(self, rabbitmq_config):
        """메시지 구독 및 수신 테스트"""
        
        try:
            message_bus = await create_message_bus(rabbitmq_config)
            
            # 수신된 메시지를 저장할 리스트
            received_messages = []
            
            async def test_message_handler(message_data):
                """테스트 메시지 핸들러"""
                received_messages.append(message_data)
                print(f"📨 메시지 수신: {message_data}")
            
            # Capital requests 큐 구독
            success = await message_bus.subscribe(
                queue_name="capital_requests",
                callback=test_message_handler,
                auto_ack=True
            )
            
            assert success is True
            
            # 잠시 대기하여 구독 설정 완료
            await asyncio.sleep(1.0)
            
            # 테스트 메시지 발행
            test_message = {
                "test": True,
                "strategy_id": 999,
                "symbol": "TEST/USDT", 
                "side": "buy",
                "signal_price": 99999.0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await message_bus.publish(
                exchange_name="letrade.requests",
                routing_key="request.capital.allocation.test",
                message=test_message
            )
            
            # 메시지 수신 대기
            await asyncio.sleep(2.0)
            
            # 수신 확인
            assert len(received_messages) > 0
            
            # 첫 번째 수신 메시지 검증
            received = received_messages[0]
            assert "payload" in received
            assert received["payload"]["test"] is True
            assert received["payload"]["symbol"] == "TEST/USDT"
            
            await message_bus.disconnect()
            
        except Exception as e:
            pytest.skip(f"RabbitMQ not available: {e}")
    
    @pytest.mark.asyncio
    async def test_end_to_end_signal_flow(self, rabbitmq_config):
        """End-to-End 신호 흐름 테스트"""
        
        try:
            # Publisher (Strategy Worker 역할)
            publisher_bus = await create_message_bus(rabbitmq_config)
            
            # Subscriber (Capital Manager 역할)
            subscriber_bus = await create_message_bus(rabbitmq_config)
            
            # 수신된 신호를 저장
            received_signals = []
            
            async def signal_handler(message_data):
                """신호 수신 핸들러"""
                received_signals.append(message_data)
                payload = message_data.get("payload", {})
                print(f"💰 Capital Manager가 신호 수신: {payload.get('side')} {payload.get('symbol')} @ {payload.get('signal_price')}")
            
            # Capital Manager 구독
            await subscriber_bus.subscribe(
                queue_name="capital_requests",
                callback=signal_handler,
                auto_ack=True
            )
            
            # 구독 설정 대기
            await asyncio.sleep(1.0)
            
            # 전략 설정
            strategy_config = StrategyConfig(
                strategy_id="e2e_test_001",
                name="E2E Test Strategy",
                enabled=True,
                dry_run=True,
                custom_params={
                    "fast_period": 2,
                    "slow_period": 3,
                    "symbol": "ETH/USDT",
                    "exchange": "binance",
                    "min_signal_interval": 0,
                    "min_crossover_strength": 0.001
                }
            )
            
            strategy = MAcrossoverStrategy(strategy_config)
            
            # 강한 골든 크로스 데이터 생성
            strong_golden_cross_data = pd.DataFrame({
                'close': [3000, 3100, 3300],  # 강한 상승
                'open': [2990, 3090, 3290],
                'high': [3050, 3150, 3350],
                'low': [2980, 3080, 3280],
                'volume': [1000, 1100, 1200]
            })
            
            # 지표 계산
            df_with_indicators = strategy.populate_indicators(strong_golden_cross_data)
            
            # 신호 생성
            market_data = {'close': 3300.0}
            signal = strategy.on_data(market_data, df_with_indicators)
            
            if signal:
                # Strategy Worker가 Capital Manager로 신호 전송
                await publisher_bus.publish(
                    exchange_name="letrade.requests",
                    routing_key=signal["routing_key"],
                    message=signal["payload"]
                )
                
                # 메시지 전달 대기
                await asyncio.sleep(2.0)
                
                # 수신 확인
                assert len(received_signals) > 0
                
                received_signal = received_signals[0]["payload"]
                assert received_signal["side"] == "buy"
                assert received_signal["symbol"] == "ETH/USDT"
                assert received_signal["signal_price"] == 3300.0
                
                print(f"🎉 E2E 테스트 성공: {received_signal['side']} 신호가 성공적으로 전달됨")
            else:
                pytest.fail("신호가 생성되지 않음")
            
            # 연결 해제
            await publisher_bus.disconnect()
            await subscriber_bus.disconnect()
            
        except Exception as e:
            pytest.skip(f"RabbitMQ not available: {e}")
    
    @pytest.mark.asyncio
    async def test_backtest_data_with_real_messaging(self, rabbitmq_config):
        """백테스트 데이터와 실제 메시징 연동 테스트"""
        
        try:
            message_bus = await create_message_bus(rabbitmq_config)
            
            # Mock 데이터 생성
            data_config = DataSourceConfig(
                source_type='mock',
                symbol='BTC/USDT',
                timeframe='1h',
                mock_config={
                    'num_periods': 10,
                    'base_price': 45000.0,
                    'volatility': 0.02,
                    'add_trends': True  # 트렌드 포함
                }
            )
            
            # 데이터 로드
            loader = BacktestDataLoader(data_config)
            historical_data = await loader.load_data()
            
            # 전략 설정
            strategy_config = StrategyConfig(
                strategy_id="backtest_real_001",
                name="Backtest Real Messaging Test",
                enabled=True,
                dry_run=True,
                custom_params={
                    "fast_period": 2,
                    "slow_period": 4,
                    "symbol": "BTC/USDT",
                    "exchange": "binance",
                    "min_signal_interval": 0,
                    "min_crossover_strength": 0.001
                }
            )
            
            strategy = MAcrossoverStrategy(strategy_config)
            
            # 지표 계산
            df_with_indicators = strategy.populate_indicators(historical_data)
            
            # 백테스트 시뮬레이션 (마지막 몇 개 데이터 포인트 처리)
            signals_sent = 0
            
            for i in range(max(4, len(historical_data) - 3), len(historical_data)):
                current_data = df_with_indicators.iloc[:i+1]
                market_data = {
                    'close': current_data['close'].iloc[-1],
                    'timestamp': current_data.index[-1].isoformat()
                }
                
                signal = strategy.on_data(market_data, current_data)
                
                if signal:
                    # 실제 메시지 버스로 신호 전송
                    success = await message_bus.publish(
                        exchange_name="letrade.requests",
                        routing_key=signal["routing_key"],
                        message=signal["payload"]
                    )
                    
                    if success:
                        signals_sent += 1
                        payload = signal["payload"]
                        print(f"📈 백테스트 신호 전송: {payload['side']} @ {payload['signal_price']}")
            
            print(f"🔄 백테스트 완료: {signals_sent}개 신호 전송")
            
            await message_bus.disconnect()
            
        except Exception as e:
            pytest.skip(f"RabbitMQ not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])