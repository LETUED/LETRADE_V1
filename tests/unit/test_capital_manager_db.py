"""
Capital Manager 데이터베이스 통합 테스트

Capital Manager의 데이터베이스 연동 기능을 테스트합니다.
MVP 상태 조정 프로토콜 요구사항을 검증합니다.
"""

import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from decimal import Decimal

from src.capital_manager.main import (
    CapitalManager, TradeRequest, ValidationResult, RiskLevel
)

class TestCapitalManagerDatabase:
    """Capital Manager 데이터베이스 기능 테스트"""
    
    @pytest.fixture
    def capital_manager(self):
        """테스트용 Capital Manager 인스턴스"""
        config = {
            'portfolio_id': 1,
            'risk_parameters': {
                'max_position_size_percent': 10.0,
                'max_daily_loss_percent': 5.0
            }
        }
        return CapitalManager(config=config)
    
    @pytest.fixture
    def sample_trade_request(self):
        """테스트용 거래 요청"""
        return TradeRequest(
            strategy_id="test_strategy",
            symbol="BTC/USDT",
            side="buy",
            quantity=0.1,
            price=50000.0
        )
    
    @patch('src.capital_manager.main.db_manager')
    def test_initialize_database_connection(self, mock_db_manager, capital_manager):
        """데이터베이스 연결 초기화 테스트"""
        # Mock 설정
        mock_db_manager.engine = None
        
        # 테스트 실행
        import asyncio
        asyncio.run(capital_manager._initialize_database_connection())
        
        # 검증
        mock_db_manager.connect.assert_called_once()
        assert capital_manager._db_connected is True
    
    @patch('src.capital_manager.main.db_manager')
    def test_load_portfolio_state_from_db(self, mock_db_manager, capital_manager):
        """포트폴리오 상태 로드 테스트"""
        # Mock 설정
        mock_session = MagicMock()
        mock_db_manager.get_session.return_value = mock_session
        mock_session.__enter__.return_value = mock_session
        
        # Mock 포트폴리오
        mock_portfolio = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_portfolio
        
        # Mock 포트폴리오 규칙
        mock_rule = MagicMock()
        mock_rule.rule_type = 'max_position_size_percent'
        mock_rule.rule_value = {'value': 15.0}
        mock_session.query.return_value.filter_by.return_value.all.return_value = [mock_rule]
        
        # Mock 포지션 (빈 리스트)
        mock_session.query.return_value.join.return_value.filter.return_value.all.return_value = []
        
        capital_manager._db_connected = True
        
        # 테스트 실행
        import asyncio
        asyncio.run(capital_manager._load_portfolio_state_from_db())
        
        # 검증
        assert capital_manager.risk_params.max_position_size_percent == 15.0
    
    @patch('src.capital_manager.main.db_manager')
    def test_save_trade_to_db(self, mock_db_manager, capital_manager, sample_trade_request):
        """거래 저장 테스트"""
        # Mock 설정
        mock_session = MagicMock()
        mock_db_manager.get_session.return_value = mock_session
        mock_session.__enter__.return_value = mock_session
        
        # Mock 전략
        mock_strategy = MagicMock()
        mock_strategy.exchange = 'binance'
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_strategy
        
        # Mock validation response
        from src.capital_manager.main import ValidationResponse
        validation_response = ValidationResponse(
            result=ValidationResult.APPROVED,
            approved_quantity=0.1,
            risk_level=RiskLevel.LOW
        )
        
        capital_manager._db_connected = True
        
        # 테스트 실행
        capital_manager.save_trade_to_db(sample_trade_request, validation_response)
        
        # 검증
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
    
    @patch('src.capital_manager.main.db_manager')
    def test_update_position_in_db(self, mock_db_manager, capital_manager):
        """포지션 업데이트 테스트"""
        # Mock 설정
        mock_session = MagicMock()
        mock_db_manager.get_session.return_value = mock_session
        mock_session.__enter__.return_value = mock_session
        
        # Mock 기존 포지션 없음
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        position_data = {
            'strategy_id': 'test_strategy',
            'side': 'long',
            'size': 0.1,
            'entry_price': 50000.0,
            'unrealized_pnl': 100.0,
            'realized_pnl': 0.0
        }
        
        capital_manager._db_connected = True
        
        # 테스트 실행
        capital_manager.update_position_in_db('BTC/USDT', position_data)
        
        # 검증
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
    
    @patch('src.capital_manager.main.db_manager')
    def test_log_risk_event_to_db(self, mock_db_manager, capital_manager):
        """리스크 이벤트 로그 테스트"""
        # Mock 설정
        mock_session = MagicMock()
        mock_db_manager.get_session.return_value = mock_session
        mock_session.__enter__.return_value = mock_session
        
        event_details = {
            'strategy_id': 'test_strategy',
            'symbol': 'BTC/USDT',
            'reasons': ['Position size too large'],
            'risk_level': 'high'
        }
        
        capital_manager._db_connected = True
        
        # 테스트 실행
        capital_manager.log_risk_event_to_db('trade_rejected', event_details)
        
        # 검증
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
    
    @patch('src.capital_manager.main.db_manager')
    @pytest.mark.asyncio
    async def test_validate_trade_with_db_integration(self, mock_db_manager, capital_manager, sample_trade_request):
        """거래 검증과 데이터베이스 통합 테스트"""
        # Mock 설정
        mock_session = MagicMock()
        mock_db_manager.get_session.return_value = mock_session
        mock_session.__enter__.return_value = mock_session
        
        # Mock 전략
        mock_strategy = MagicMock()
        mock_strategy.exchange = 'binance'
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_strategy
        
        # Capital Manager 상태 설정
        capital_manager.is_running = True
        capital_manager._db_connected = True
        
        # Mock portfolio metrics
        with patch.object(capital_manager, 'get_portfolio_metrics') as mock_metrics:
            from src.capital_manager.main import PortfolioMetrics
            mock_metrics.return_value = PortfolioMetrics(
                total_value=10000.0,
                available_cash=5000.0,
                unrealized_pnl=0.0,
                realized_pnl_today=0.0,
                total_risk_exposure=1000.0,
                number_of_positions=1,
                largest_position_percent=5.0,
                daily_var=200.0
            )
            
            # 테스트 실행
            result = await capital_manager.validate_trade(sample_trade_request)
            
            # 검증
            assert result.result == ValidationResult.APPROVED
            mock_session.add.assert_called()  # Trade 저장
            mock_session.commit.assert_called()
    
    def test_get_db_session_context_manager(self, capital_manager):
        """데이터베이스 세션 컨텍스트 매니저 테스트"""
        with patch('src.capital_manager.main.db_manager') as mock_db_manager:
            mock_session = MagicMock()
            mock_db_manager.get_session.return_value = mock_session
            
            # 정상 케이스
            with capital_manager._get_db_session() as session:
                assert session == mock_session
            
            mock_session.close.assert_called_once()
    
    def test_get_db_session_with_exception(self, capital_manager):
        """데이터베이스 세션 예외 처리 테스트"""
        with patch('src.capital_manager.main.db_manager') as mock_db_manager:
            mock_session = MagicMock()
            mock_db_manager.get_session.return_value = mock_session
            
            # 예외 발생 케이스
            try:
                with capital_manager._get_db_session() as session:
                    raise Exception("Test exception")
            except Exception:
                pass
            
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()

class TestCapitalManagerStateReconciliation:
    """Capital Manager 상태 조정 프로토콜 테스트"""
    
    @pytest.fixture
    def capital_manager(self):
        """테스트용 Capital Manager 인스턴스"""
        config = {'portfolio_id': 1}
        return CapitalManager(config=config)
    
    @patch('src.capital_manager.main.db_manager')
    @pytest.mark.asyncio
    async def test_full_state_reconciliation_flow(self, mock_db_manager, capital_manager):
        """완전한 상태 조정 플로우 테스트"""
        # Mock 설정
        mock_session = MagicMock()
        mock_db_manager.get_session.return_value = mock_session
        mock_session.__enter__.return_value = mock_session
        mock_db_manager.engine = MagicMock()
        
        # Mock 포트폴리오
        mock_portfolio = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_portfolio
        
        # Mock 규칙
        mock_rule1 = MagicMock()
        mock_rule1.rule_type = 'max_position_size_percent'
        mock_rule1.rule_value = {'value': 10.0}
        
        mock_rule2 = MagicMock()
        mock_rule2.rule_type = 'max_daily_loss_percent'
        mock_rule2.rule_value = {'value': 3.0}
        
        mock_session.query.return_value.filter_by.return_value.all.return_value = [mock_rule1, mock_rule2]
        
        # Mock 포지션
        mock_position = MagicMock()
        mock_position.strategy_id = 'test_strategy'
        mock_position.symbol = 'BTC/USDT'
        mock_position.side = 'long'
        mock_position.current_size = Decimal('0.1')
        mock_position.entry_price = Decimal('50000.0')
        mock_position.unrealized_pnl = Decimal('100.0')
        mock_position.realized_pnl = Decimal('0.0')
        
        mock_session.query.return_value.join.return_value.filter.return_value.all.return_value = [mock_position]
        
        # 테스트 실행 - 전체 시작 플로우
        success = await capital_manager.start()
        
        # 검증
        assert success is True
        assert capital_manager._db_connected is True
        assert capital_manager.risk_params.max_position_size_percent == 10.0
        assert capital_manager.risk_params.max_daily_loss_percent == 3.0
        assert len(capital_manager._positions) == 1
        assert 'BTC/USDT' in capital_manager._positions

if __name__ == "__main__":
    pytest.main([__file__, "-v"])