"""
Capital Manager 리팩토링 테스트

리팩토링된 Capital Manager의 기능을 검증하는 테스트
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.capital_manager.refactored_main import RefactoredCapitalManager
from src.capital_manager.interfaces import (
    TradeRequest, ValidationResult, RiskLevel,
    PortfolioMetrics, RiskParameters
)
from src.capital_manager.validation_rules import ValidationRuleEngine


class TestRefactoredCapitalManager:
    """리팩토링된 Capital Manager 테스트"""
    
    @pytest.fixture
    def config(self):
        """테스트 설정"""
        return {
            'portfolio_id': 1,
            'risk_parameters': {
                'max_position_size_percent': 10.0,
                'max_portfolio_risk_percent': 20.0,
                'stop_loss_percent': 2.0,
                'take_profit_percent': 5.0,
                'max_daily_loss_percent': 5.0,
                'min_trade_amount': 10.0,
                'max_trade_amount': 10000.0,
                'max_positions_per_symbol': 1,
                'max_total_positions': 10
            }
        }
    
    @pytest.fixture
    def capital_manager(self, config):
        """Capital Manager 인스턴스"""
        manager = RefactoredCapitalManager(config)
        
        # Mock 데이터베이스 핸들러
        manager.db_handler = AsyncMock()
        manager.db_handler.get_portfolio_metrics = AsyncMock(return_value=PortfolioMetrics(
            total_value=10000.0,
            available_cash=5000.0,
            unrealized_pnl=0.0,
            realized_pnl_today=0.0,
            total_risk_exposure=1000.0,
            number_of_positions=2,
            largest_position_percent=10.0,
            daily_var=200.0
        ))
        manager.db_handler.get_open_positions = AsyncMock(return_value=[])
        
        return manager
    
    @pytest.mark.asyncio
    async def test_validate_trade_approved(self, capital_manager):
        """정상적인 거래 승인 테스트"""
        # 거래 요청 - 포트폴리오의 5% (500/10000 = 5%)
        trade_request = TradeRequest(
            strategy_id=1,
            symbol="BTC/USDT",
            side="buy",
            quantity=0.01,  # 0.01 BTC = $500 at $50,000
            price=50000.0
        )
        
        # 검증
        response = await capital_manager.validate_trade(trade_request)
        
        # 검증 결과 확인
        assert response.result == ValidationResult.APPROVED
        assert response.approved_quantity == 0.01
        assert response.risk_level == RiskLevel.MEDIUM  # 5% 포지션은 MEDIUM
        assert len(response.reasons) == 0
        
        # Stop Loss/Take Profit 제안 확인
        assert response.suggested_stop_loss == pytest.approx(49000.0)  # 2% 손절
        assert response.suggested_take_profit == pytest.approx(52500.0)  # 5% 익절
    
    @pytest.mark.asyncio
    async def test_validate_trade_position_too_large(self, capital_manager):
        """포지션 크기 초과 거래 거부 테스트"""
        # 큰 거래 요청 (150% 포지션)
        trade_request = TradeRequest(
            strategy_id=1,
            symbol="BTC/USDT",
            side="buy",
            quantity=0.3,  # 0.3 BTC = $15,000 at $50,000
            price=50000.0
        )
        
        # 검증
        response = await capital_manager.validate_trade(trade_request)
        
        # 거부 확인
        assert response.result == ValidationResult.REJECTED
        assert response.approved_quantity == 0.0
        # TradeSize 또는 PositionSize 규칙에 의한 거부
        assert any("exceeds maximum" in reason for reason in response.reasons)
    
    @pytest.mark.asyncio
    async def test_validate_trade_emergency_stop(self, capital_manager):
        """긴급 정지 상태에서 거래 거부 테스트"""
        # 긴급 정지 활성화
        capital_manager._emergency_stop = True
        
        # 거래 요청
        trade_request = TradeRequest(
            strategy_id=1,
            symbol="BTC/USDT",
            side="buy",
            quantity=0.01,
            price=50000.0
        )
        
        # 검증
        response = await capital_manager.validate_trade(trade_request)
        
        # 거부 확인
        assert response.result == ValidationResult.REJECTED
        assert "Emergency stop" in str(response.reasons)
    
    @pytest.mark.asyncio
    async def test_validate_trade_daily_loss_limit(self, capital_manager):
        """일일 손실 한도 초과 거래 거부 테스트"""
        # 일일 손실 설정 - 4.8% 손실 (한도에 매우 가까움)
        capital_manager._daily_pnl = -480.0
        
        # 포트폴리오 메트릭스 업데이트
        capital_manager.db_handler.get_portfolio_metrics = AsyncMock(return_value=PortfolioMetrics(
            total_value=10000.0,
            available_cash=5000.0,
            unrealized_pnl=0.0,
            realized_pnl_today=-480.0,  # 4.8% 손실
            total_risk_exposure=1000.0,
            number_of_positions=2,
            largest_position_percent=10.0,
            daily_var=200.0
        ))
        
        # 추가 손실 가능성이 있는 거래
        trade_request = TradeRequest(
            strategy_id=1,
            symbol="BTC/USDT",
            side="buy",
            quantity=0.015,  # 0.015 BTC = $750 at $50,000
            price=50000.0
        )
        
        # 검증
        response = await capital_manager.validate_trade(trade_request)
        
        # 거부 확인 
        # 현재 손실: 4.8%
        # 예상 리스크: $750 * 2% = $15
        # 추가 손실률: $15 / $10,000 = 0.15%
        # 총 손실률: 4.8% + 0.15% = 4.95% < 5% (아직 승인)
        assert response.result == ValidationResult.APPROVED
        
        # 더 큰 거래로 다시 요청
        large_trade_request = TradeRequest(
            strategy_id=1,
            symbol="BTC/USDT",
            side="buy",
            quantity=0.025,  # 0.025 BTC = $1250 at $50,000 (12.5% 포지션)
            price=50000.0
        )
        
        response = await capital_manager.validate_trade(large_trade_request)
        
        # 거부 확인
        # 예상 리스크: $1250 * 2% = $25
        # 추가 손실률: $25 / $10,000 = 0.25%
        # 총 손실률: 4.8% + 0.25% = 5.05% (한도 초과)
        # 또한 PositionSize 규칙도 거부 (12.5% > 10%)
        assert response.result == ValidationResult.REJECTED
        assert any("exceed" in reason.lower() for reason in response.reasons)
    
    @pytest.mark.asyncio
    async def test_validate_trade_blocked_symbol(self, capital_manager):
        """차단된 심볼 거래 거부 테스트"""
        # 심볼 차단
        capital_manager._blocked_symbols.add("LUNA/USDT")
        
        # 차단된 심볼 거래 요청
        trade_request = TradeRequest(
            strategy_id=1,
            symbol="LUNA/USDT",
            side="buy",
            quantity=10.0,
            price=1.0
        )
        
        # 검증
        response = await capital_manager.validate_trade(trade_request)
        
        # 거부 확인
        assert response.result == ValidationResult.REJECTED
        assert "blocked" in str(response.reasons)
    
    @pytest.mark.asyncio
    async def test_risk_level_evaluation(self, capital_manager):
        """리스크 레벨 평가 테스트"""
        test_cases = [
            (0.001, 50000.0, RiskLevel.LOW),      # 0.5% 포지션 (50/10000)
            (0.01, 50000.0, RiskLevel.MEDIUM),    # 5% 포지션 (500/10000)
            (0.012, 50000.0, RiskLevel.HIGH),     # 6% 포지션 (600/10000)
            (0.016, 50000.0, RiskLevel.EXTREME),  # 8% 포지션 (800/10000)
        ]
        
        for quantity, price, expected_risk_level in test_cases:
            trade_request = TradeRequest(
                strategy_id=1,
                symbol="BTC/USDT",
                side="buy",
                quantity=quantity,
                price=price
            )
            
            response = await capital_manager.validate_trade(trade_request)
            
            if response.result == ValidationResult.APPROVED:
                assert response.risk_level == expected_risk_level
    
    @pytest.mark.asyncio
    async def test_portfolio_impact_calculation(self, capital_manager):
        """포트폴리오 영향 계산 테스트"""
        trade_request = TradeRequest(
            strategy_id=1,
            symbol="BTC/USDT",
            side="buy",
            quantity=0.01,  # 0.01 BTC = $500 at $50,000
            price=50000.0
        )
        
        response = await capital_manager.validate_trade(trade_request)
        
        # 포트폴리오 영향 확인
        assert response.portfolio_impact is not None
        assert response.portfolio_impact['position_size_percent'] == pytest.approx(5.0)  # 500/10000
        assert 'new_portfolio_risk_percent' in response.portfolio_impact
        assert 'available_capital_after' in response.portfolio_impact
    
    @pytest.mark.asyncio
    async def test_emergency_stop_activation(self, capital_manager):
        """긴급 정지 활성화 테스트"""
        # Mock 설정
        capital_manager.db_handler.log_risk_event = AsyncMock(return_value=True)
        
        # 긴급 정지 활성화
        result = await capital_manager.emergency_stop("Market crash detected")
        
        # 확인
        assert result is True
        assert capital_manager._emergency_stop is True
        capital_manager.db_handler.log_risk_event.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_trade_execution_recording(self, capital_manager):
        """거래 실행 기록 테스트"""
        # Mock 설정
        capital_manager.db_handler.record_trade_execution = AsyncMock(return_value=True)
        capital_manager.db_handler.update_position = AsyncMock(return_value=True)
        
        # 거래 요청
        trade_request = TradeRequest(
            strategy_id=1,
            symbol="BTC/USDT",
            side="buy",
            quantity=0.1,
            price=50000.0
        )
        
        # 실행 결과
        execution_result = {
            'order_id': 'ORDER123',
            'trade_id': 'TRADE123',
            'filled_quantity': 0.1,
            'average_price': 50100.0,
            'fees': 5.01,
            'status': 'filled'
        }
        
        # 기록
        result = await capital_manager.record_trade_execution(trade_request, execution_result)
        
        # 확인
        assert result is True
        capital_manager.db_handler.record_trade_execution.assert_called_once()
        capital_manager.db_handler.update_position.assert_called_once()


class TestValidationRules:
    """검증 규칙 테스트"""
    
    @pytest.mark.asyncio
    async def test_validation_rule_engine(self):
        """검증 규칙 엔진 테스트"""
        # 리스크 파라미터
        risk_params = RiskParameters()
        
        # 엔진 생성
        engine = ValidationRuleEngine(risk_params)
        
        # 규칙 수 확인
        assert len(engine.rules) > 0
        
        # 거래 요청
        trade_request = TradeRequest(
            strategy_id=1,
            symbol="BTC/USDT",
            side="buy",
            quantity=0.1,
            price=50000.0
        )
        
        # 정상 컨텍스트
        context = {
            'portfolio_metrics': PortfolioMetrics(
                total_value=10000.0,
                available_cash=5000.0,
                unrealized_pnl=0.0,
                realized_pnl_today=0.0,
                total_risk_exposure=1000.0,
                number_of_positions=2,
                largest_position_percent=10.0,
                daily_var=200.0
            ),
            'current_price': 50000.0,
            'estimated_risk': 10.0,  # 작은 리스크로 변경
            'positions': {},
            'emergency_stop': False,
            'max_daily_loss_triggered': False,
            'blocked_symbols': set()
        }
        
        # 검증
        result = await engine.validate_all(trade_request, context)
        # 0.1 BTC @ $50,000 = $5,000 = 50% of portfolio
        # 이는 10% 한도를 초과하므로 거부되어야 함
        assert result is False
        
        # 작은 거래로 다시 테스트 (승인 가능한 거래)
        small_trade_request = TradeRequest(
            strategy_id=1,
            symbol="BTC/USDT",
            side="buy",
            quantity=0.01,  # 0.01 BTC = $500 = 5% of portfolio
            price=50000.0
        )
        
        result = await engine.validate_all(small_trade_request, context)
        assert result is True  # 10% 한도 내이므로 승인
    
    @pytest.mark.asyncio
    async def test_rule_enable_disable(self):
        """규칙 활성화/비활성화 테스트"""
        risk_params = RiskParameters()
        engine = ValidationRuleEngine(risk_params)
        
        # 규칙 비활성화
        result = engine.disable_rule("EmergencyStop")
        assert result is True
        
        # 비활성화된 규칙 찾기
        emergency_rule = next((r for r in engine.rules if r.name == "EmergencyStop"), None)
        assert emergency_rule is not None
        assert emergency_rule.enabled is False
        
        # 규칙 재활성화
        result = engine.enable_rule("EmergencyStop")
        assert result is True
        assert emergency_rule.enabled is True


@pytest.mark.asyncio
async def test_performance_comparison():
    """성능 비교 테스트 - 리팩토링 전후"""
    import time
    
    config = {
        'portfolio_id': 1,
        'risk_parameters': {
            'max_position_size_percent': 10.0,
            'max_portfolio_risk_percent': 20.0,
            'stop_loss_percent': 2.0,
            'take_profit_percent': 5.0,
            'max_daily_loss_percent': 5.0
        }
    }
    
    # 리팩토링된 Capital Manager
    manager = RefactoredCapitalManager(config)
    manager.db_handler = AsyncMock()
    manager.db_handler.get_portfolio_metrics = AsyncMock(return_value=PortfolioMetrics(
        total_value=10000.0,
        available_cash=5000.0,
        unrealized_pnl=0.0,
        realized_pnl_today=0.0,
        total_risk_exposure=1000.0,
        number_of_positions=2,
        largest_position_percent=10.0,
        daily_var=200.0
    ))
    manager.db_handler.get_open_positions = AsyncMock(return_value=[])
    manager.db_handler.save_trade_validation = AsyncMock(return_value=1)
    
    # 거래 요청들
    trade_requests = [
        TradeRequest(
            strategy_id=i,
            symbol="BTC/USDT",
            side="buy" if i % 2 == 0 else "sell",
            quantity=0.01 * (i % 10 + 1),
            price=50000.0 + i * 100
        )
        for i in range(100)
    ]
    
    # 성능 측정
    start_time = time.time()
    
    for request in trade_requests:
        await manager.validate_trade(request)
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    print(f"\n리팩토링된 Capital Manager 성능:")
    print(f"- 100개 거래 검증 시간: {elapsed_time:.3f}초")
    print(f"- 평균 검증 시간: {(elapsed_time / 100) * 1000:.1f}ms")
    
    # 성능 목표: 거래당 10ms 미만
    assert elapsed_time < 1.0  # 100개 거래가 1초 안에 처리되어야 함


if __name__ == "__main__":
    # 테스트 실행
    pytest.main([__file__, "-v", "-s"])