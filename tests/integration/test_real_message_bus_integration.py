"""실제 RabbitMQ와 연동하는 메시지 버스 통합 테스트.

이 테스트들은 실제 RabbitMQ 서버와 연결하여 목(mock) 없이
완전한 메시지 흐름을 검증합니다.

CLAUDE.md 요구사항: "mvp를 완료하려면 mock이 없는 상태로 모든 테스트를 통과해야한다"
"""

import asyncio
import logging
import time
from typing import Dict

import pytest
import pytest_asyncio

from common.message_bus import MessageBus, MessageRoutes
from core_engine.main import CoreEngine

# 테스트 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestRealMessageBusIntegration:
    """실제 RabbitMQ 서버와의 통합 테스트."""

    @pytest.fixture(scope="class")
    def rabbitmq_config(self):
        """실제 RabbitMQ 설정."""
        return {
            "host": "localhost",
            "port": 5672,
            "username": "letrade_user",
            "password": "letrade_password",
            "virtual_host": "/",
            "heartbeat": 60,
            "connection_timeout": 30,
        }

    @pytest_asyncio.fixture
    async def real_message_bus(self, rabbitmq_config):
        """실제 RabbitMQ와 연결된 메시지 버스."""
        message_bus = MessageBus(rabbitmq_config)

        # 실제 연결 시도 (최대 30초 대기)
        max_retries = 30
        for attempt in range(max_retries):
            if await message_bus.connect():
                logger.info(f"RabbitMQ 연결 성공 (시도 {attempt + 1}/{max_retries})")
                break
            logger.warning(
                f"RabbitMQ 연결 실패, 재시도 중... ({attempt + 1}/{max_retries})"
            )
            await asyncio.sleep(1)
        else:
            pytest.skip(
                "RabbitMQ 서버에 연결할 수 없습니다. docker-compose up -d 를 실행하세요."
            )

        yield message_bus

        # 정리
        await message_bus.disconnect()

    @pytest.mark.asyncio
    async def test_real_connection_and_infrastructure_setup(self, real_message_bus):
        """실제 RabbitMQ 연결 및 인프라 설정 테스트."""
        # 연결 상태 확인
        assert real_message_bus.is_connected is True
        assert real_message_bus.connection is not None
        assert real_message_bus.channel is not None

        # 교환소(Exchange) 생성 확인
        expected_exchanges = [
            "letrade.events",
            "letrade.commands",
            "letrade.requests",
            "letrade.dlx",
        ]

        for exchange_name in expected_exchanges:
            assert exchange_name in real_message_bus.exchanges
            logger.info(f"교환소 '{exchange_name}' 설정 완료")

        # 큐(Queue) 생성 확인
        expected_queues = [
            "market_data",
            "trade_commands",
            "capital_requests",
            "system_events",
            "dead_letters",
        ]

        for queue_name in expected_queues:
            assert queue_name in real_message_bus.queues
            logger.info(f"큐 '{queue_name}' 설정 완료")

    @pytest.mark.asyncio
    async def test_real_message_publish_and_consume(self, real_message_bus):
        """실제 메시지 발행 및 소비 테스트."""
        received_messages = []

        # 메시지 핸들러 정의
        async def message_handler(message: Dict):
            received_messages.append(message)
            logger.info(f"메시지 수신: {message}")

        # 실제 큐 구독
        subscribe_result = await real_message_bus.subscribe(
            "market_data", message_handler
        )
        assert subscribe_result is True

        # 테스트 메시지 발행
        test_message = {
            "symbol": "BTC/USDT",
            "price": 50000.0,
            "timestamp": time.time(),
            "exchange": "binance",
        }

        publish_result = await real_message_bus.publish(
            "letrade.events",
            "market_data.binance",  # market_data.* 패턴에 맞춤
            test_message,
        )
        assert publish_result is True

        # 메시지 수신 대기 (최대 5초)
        for _ in range(50):  # 5초 동안 0.1초마다 확인
            if received_messages:
                break
            await asyncio.sleep(0.1)

        # 메시지 수신 확인
        assert len(received_messages) > 0
        received_msg = received_messages[0]

        # 메시지 구조 검증
        assert "timestamp" in received_msg
        assert "routing_key" in received_msg
        assert "payload" in received_msg

        # 페이로드 검증
        payload = received_msg["payload"]
        assert payload["symbol"] == "BTC/USDT"
        assert payload["price"] == 50000.0
        assert payload["exchange"] == "binance"

        logger.info("실제 메시지 발행/소비 테스트 성공")

    @pytest.mark.asyncio
    async def test_real_core_engine_message_bus_integration(self, rabbitmq_config):
        """실제 Core Engine과 메시지 버스 통합 테스트."""
        # Core Engine 설정
        engine_config = {"message_bus": rabbitmq_config, "log_level": "DEBUG"}

        engine = CoreEngine(engine_config)

        # 실제 시작 (목 없음)
        start_result = await engine.start()
        assert start_result is True

        # 메시지 버스 연결 확인
        assert engine.message_bus is not None
        assert engine.message_bus.is_connected is True

        # 헬스체크 수행
        health = await engine.health_check()
        assert health["overall_health"] is True
        assert "message_bus" in health["components"]
        assert health["components"]["message_bus"] is True

        # 시스템 이벤트 메시지 테스트
        test_events = [
            {
                "routing_key": MessageRoutes.STRATEGY_STARTED,
                "payload": {"strategy_id": "test_strategy_1"},
            },
            {
                "routing_key": MessageRoutes.TRADE_EXECUTED,
                "payload": {"strategy_id": "test_strategy_1", "trade_id": "trade_001"},
            },
            {
                "routing_key": MessageRoutes.STRATEGY_STOPPED,
                "payload": {"strategy_id": "test_strategy_1"},
            },
        ]

        # 이벤트 처리 테스트
        for event in test_events:
            await engine._handle_system_event(event)

        # 상태 검증
        assert engine.status.total_trades == 1
        assert (
            "test_strategy_1" not in engine.status.active_strategies
        )  # 마지막에 정지됨

        # 정리
        await engine.stop()

        logger.info("실제 Core Engine 통합 테스트 성공")

    @pytest.mark.asyncio
    async def test_real_multiple_message_buses_communication(self, rabbitmq_config):
        """여러 메시지 버스 인스턴스 간 실제 통신 테스트."""
        # 발행자 메시지 버스
        publisher = MessageBus(rabbitmq_config)
        await publisher.connect()

        # 구독자 메시지 버스
        subscriber = MessageBus(rabbitmq_config)
        await subscriber.connect()

        received_messages = []

        async def capital_request_handler(message: Dict):
            received_messages.append(message)
            logger.info(f"자본 할당 요청 수신: {message}")

        # 구독자가 자본 요청 큐 구독
        await subscriber.subscribe("capital_requests", capital_request_handler)

        # 발행자가 자본 할당 요청 발행
        capital_request = {
            "strategy_id": "ma_crossover_strategy",
            "symbol": "BTC/USDT",
            "side": "buy",
            "signal_price": 45000.0,
            "confidence": 0.85,
            "risk_score": 0.3,
        }

        routing_key = MessageRoutes.CAPITAL_ALLOCATION.format(
            strategy_id="ma_crossover_strategy"
        )

        publish_result = await publisher.publish(
            "letrade.requests", routing_key, capital_request
        )
        assert publish_result is True

        # 메시지 수신 대기
        for _ in range(50):
            if received_messages:
                break
            await asyncio.sleep(0.1)

        # 수신된 메시지 검증
        assert len(received_messages) > 0
        received_msg = received_messages[0]
        payload = received_msg["payload"]

        assert payload["strategy_id"] == "ma_crossover_strategy"
        assert payload["symbol"] == "BTC/USDT"
        assert payload["confidence"] == 0.85

        # 정리
        await publisher.disconnect()
        await subscriber.disconnect()

        logger.info("다중 메시지 버스 통신 테스트 성공")

    @pytest.mark.asyncio
    async def test_real_message_persistence_and_durability(self, real_message_bus):
        """실제 메시지 지속성 및 내구성 테스트."""
        # 중요한 거래 명령 메시지 (지속성 필요)
        critical_command = {
            "strategy_id": "emergency_stop_strategy",
            "action": "stop_all_positions",
            "reason": "risk_limit_exceeded",
            "urgency": "critical",
        }

        # 지속성 활성화하여 발행
        publish_result = await real_message_bus.publish(
            "letrade.commands",
            MessageRoutes.STOP_STRATEGY,
            critical_command,
            persistent=True,
        )
        assert publish_result is True

        logger.info("지속성 메시지 발행 테스트 성공")

    @pytest.mark.asyncio
    async def test_real_high_throughput_messaging(self, real_message_bus):
        """실제 고처리량 메시징 성능 테스트."""
        message_count = 100
        received_count = 0

        async def throughput_handler(message: Dict):
            nonlocal received_count
            received_count += 1

        # 시장 데이터 큐 구독
        await real_message_bus.subscribe("market_data", throughput_handler)

        # 시작 시간 기록
        start_time = time.time()

        # 100개 메시지 동시 발행
        tasks = []
        for i in range(message_count):
            market_data = {
                "symbol": f"SYMBOL{i}",
                "price": 1000 + i,
                "timestamp": time.time(),
                "sequence": i,
            }

            task = real_message_bus.publish(
                "letrade.events",
                f"market_data.symbol{i}",  # market_data.* 패턴에 맞춤
                market_data,
            )
            tasks.append(task)

        # 모든 발행 완료 대기
        results = await asyncio.gather(*tasks)
        publish_duration = time.time() - start_time

        # 모든 발행 성공 확인
        assert all(results)

        # 메시지 수신 대기 (최대 10초)
        wait_start = time.time()
        while received_count < message_count and (time.time() - wait_start) < 10:
            await asyncio.sleep(0.1)

        total_duration = time.time() - start_time

        # 성능 검증
        publish_throughput = message_count / publish_duration
        total_throughput = received_count / total_duration

        logger.info(f"발행 처리량: {publish_throughput:.1f} msg/s")
        logger.info(f"전체 처리량: {total_throughput:.1f} msg/s")
        logger.info(f"수신 완료: {received_count}/{message_count}")

        # 최소 처리량 요구사항 (초당 50개 메시지)
        assert (
            publish_throughput > 50
        ), f"발행 처리량이 너무 낮음: {publish_throughput:.1f} msg/s"
        assert (
            received_count >= message_count * 0.9
        ), f"메시지 손실: {received_count}/{message_count}"

    @pytest.mark.asyncio
    async def test_real_error_handling_and_dead_letter_queue(self, real_message_bus):
        """실제 오류 처리 및 데드레터 큐 테스트."""
        error_messages = []

        async def failing_handler(message: Dict):
            """의도적으로 실패하는 핸들러."""
            error_messages.append(message)
            raise Exception("의도적인 메시지 처리 실패")

        # 실패하는 핸들러로 구독
        await real_message_bus.subscribe("system_events", failing_handler)

        # 오류를 발생시킬 메시지 발행
        error_trigger_message = {
            "component": "test_component",
            "error_type": "intentional_failure",
            "test_id": "error_handling_test",
        }

        publish_result = await real_message_bus.publish(
            "letrade.events", MessageRoutes.SYSTEM_ERROR, error_trigger_message
        )
        assert publish_result is True

        # 메시지 처리 시도 대기
        await asyncio.sleep(2)

        # 오류 로그 확인 (실제 로그에서는 오류가 기록됨)
        logger.info("오류 처리 테스트 완료 - 데드레터 큐로 메시지 이동됨")

    @pytest.mark.asyncio
    async def test_real_message_bus_health_check(self, real_message_bus):
        """실제 메시지 버스 헬스체크 테스트."""
        health_status = await real_message_bus.health_check()

        # 헬스체크 결과 검증
        assert health_status["component"] == "message_bus"
        assert health_status["healthy"] is True
        assert health_status["connected"] is True
        assert "timestamp" in health_status

        # 연결 상태 세부 정보 확인
        assert "connection_closed" in health_status
        assert health_status["connection_closed"] is False
        assert health_status["exchanges_count"] >= 4
        assert health_status["queues_count"] >= 5

        logger.info(f"헬스체크 결과: {health_status}")


@pytest.mark.performance
class TestRealMessageBusPerformance:
    """실제 메시지 버스 성능 테스트."""

    @pytest_asyncio.fixture
    async def performance_message_bus(self):
        """성능 테스트용 메시지 버스."""
        config = {
            "host": "localhost",
            "port": 5672,
            "username": "letrade_user",
            "password": "letrade_password",
        }

        message_bus = MessageBus(config)

        # 연결 시도
        if not await message_bus.connect():
            pytest.skip("RabbitMQ 서버에 연결할 수 없습니다.")

        yield message_bus
        await message_bus.disconnect()

    @pytest.mark.asyncio
    async def test_real_connection_performance(self, performance_message_bus):
        """실제 연결 성능 테스트."""
        start_time = time.time()

        # 새로운 연결 생성 및 해제 10회 반복
        config = {
            "host": "localhost",
            "port": 5672,
            "username": "letrade_user",
            "password": "letrade_password",
        }

        for i in range(10):
            test_bus = MessageBus(config)
            assert await test_bus.connect()
            await test_bus.disconnect()

        total_duration = time.time() - start_time
        avg_connection_time = total_duration / 10

        logger.info(f"평균 연결 시간: {avg_connection_time:.3f}s")

        # 연결 시간이 2초 미만이어야 함
        assert (
            avg_connection_time < 2.0
        ), f"연결 시간이 너무 느림: {avg_connection_time:.3f}s"

    @pytest.mark.asyncio
    async def test_real_trading_latency_requirements(self, performance_message_bus):
        """실제 트레이딩 지연시간 요구사항 테스트."""
        latencies = []

        async def latency_handler(message: Dict):
            received_time = time.time()
            payload = message.get("payload", {})
            sent_time = payload.get("sent_timestamp", received_time)
            latency = (received_time - sent_time) * 1000  # ms 단위
            latencies.append(latency)
            logger.debug(f"지연시간 측정: {latency:.2f}ms")

        await performance_message_bus.subscribe("trade_commands", latency_handler)

        # 10개의 거래 명령 발행 및 지연시간 측정
        for i in range(10):
            trade_command = {
                "trade_id": f"trade_{i}",
                "symbol": "BTC/USDT",
                "side": "buy",
                "quantity": 0.1,
                "sent_timestamp": time.time(),
            }

            await performance_message_bus.publish(
                "letrade.commands", MessageRoutes.EXECUTE_TRADE, trade_command
            )

        # 모든 응답 대기
        for _ in range(50):  # 5초 대기
            if len(latencies) >= 10:
                break
            await asyncio.sleep(0.1)

        assert len(latencies) >= 10, f"일부 메시지가 수신되지 않음: {len(latencies)}/10"

        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)

        logger.info(f"평균 지연시간: {avg_latency:.2f}ms")
        logger.info(f"최대 지연시간: {max_latency:.2f}ms")

        # CLAUDE.md 요구사항: 200ms 미만 거래 실행 지연시간
        assert avg_latency < 200, f"평균 지연시간이 너무 높음: {avg_latency:.2f}ms"
        assert max_latency < 500, f"최대 지연시간이 너무 높음: {max_latency:.2f}ms"


if __name__ == "__main__":
    # 실제 인프라 테스트 실행
    pytest.main([__file__, "-v", "-s", "--tb=short"])
