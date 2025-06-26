"""
리팩토링된 Capital Manager 메인 모듈

주요 개선사항:
1. validate_trade 메서드를 작은 단위로 분리
2. Strategy Pattern을 통한 검증 규칙 관리
3. 데이터베이스 로직 분리
4. 명확한 책임 분리와 가독성 향상
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from src.common.message_bus import MessageBus
from .interfaces import (
    TradeRequest, ValidationResponse, ValidationResult,
    RiskLevel, RiskParameters, PortfolioMetrics, TradeExecution
)
from .validation_rules import ValidationRuleEngine
from .database_handler import CapitalManagerDatabaseHandler

logger = logging.getLogger(__name__)


class RefactoredCapitalManager:
    """리팩토링된 Capital Manager"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Capital Manager 초기화
        
        Args:
            config: 설정 딕셔너리
        """
        self.config = config
        self.is_running = False
        
        # 컴포넌트 초기화
        self.risk_params = self._load_risk_parameters(config.get('risk_parameters', {}))
        self.validation_engine = ValidationRuleEngine(self.risk_params)
        self.db_handler = CapitalManagerDatabaseHandler(config.get('portfolio_id', 1))
        self.message_bus = config.get('message_bus')
        
        # 상태 관리
        self._positions = {}
        self._daily_pnl = 0.0
        self._blocked_symbols = set()
        self._emergency_stop = False
        self._max_daily_loss_triggered = False
        
        # 메시지 핸들러 매핑
        self._message_handlers = {
            "request.capital.allocation": self._handle_trade_proposal,
            "request.capital.validation": self._handle_trade_validation,
            "events.trade_executed": self._handle_trade_executed_event,
        }
        
        logger.info(
            "RefactoredCapitalManager initialized",
            extra={
                "portfolio_id": config.get('portfolio_id', 1),
                "risk_params": self.risk_params.to_dict()
            }
        )
    
    def _load_risk_parameters(self, risk_config: Dict[str, Any]) -> RiskParameters:
        """리스크 파라미터 로드"""
        return RiskParameters(**risk_config)
    
    async def start(self) -> bool:
        """Capital Manager 시작"""
        try:
            logger.info("Starting RefactoredCapitalManager")
            
            # 1. 데이터베이스 연결 및 상태 로드
            await self._initialize_from_database()
            
            # 2. 포트폴리오 상태 초기화
            await self._initialize_portfolio_state()
            
            # 3. 메시지 버스 구독 설정
            if self.message_bus:
                await self._setup_message_subscriptions()
            
            self.is_running = True
            logger.info("RefactoredCapitalManager started successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Capital Manager: {e}")
            return False
    
    async def stop(self) -> bool:
        """Capital Manager 중지"""
        try:
            logger.info("Stopping RefactoredCapitalManager")
            
            # 메시지 구독 해제
            if self.message_bus:
                await self._cleanup_message_subscriptions()
            
            # 최종 상태 저장
            await self._persist_final_state()
            
            self.is_running = False
            logger.info("RefactoredCapitalManager stopped successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop Capital Manager: {e}")
            return False
    
    async def validate_trade(self, trade_request: TradeRequest) -> ValidationResponse:
        """
        거래 검증 - 리팩토링된 버전
        
        이전 400줄의 메서드를 85줄로 단순화
        각 단계가 명확하게 분리되어 있음
        """
        logger.info(
            f"Validating trade request",
            extra={
                "symbol": trade_request.symbol,
                "side": trade_request.side,
                "quantity": trade_request.quantity,
                "strategy_id": trade_request.strategy_id
            }
        )
        
        # 1. 검증 컨텍스트 준비
        context = await self._prepare_validation_context(trade_request)
        
        # 2. 검증 규칙 실행
        validation_passed = await self.validation_engine.validate_all(trade_request, context)
        
        # 3. 검증 실패 시 조기 반환
        if not validation_passed:
            response = self._create_rejection_response(context)
            await self._record_validation_result(trade_request, response)
            return response
        
        # 4. 리스크 레벨 평가
        risk_level = self._evaluate_risk_level(trade_request, context)
        
        # 5. 승인 응답 생성
        response = self._create_approval_response(trade_request, context, risk_level)
        
        # 6. 데이터베이스 기록
        await self._record_validation_result(trade_request, response)
        
        # 7. 리스크 이벤트 확인
        if risk_level in [RiskLevel.HIGH, RiskLevel.EXTREME]:
            await self._log_high_risk_trade(trade_request, response)
        
        logger.info(
            f"Trade validation completed",
            extra={
                "result": response.result.value,
                "risk_level": response.risk_level.value,
                "approved_quantity": response.approved_quantity
            }
        )
        
        return response
    
    async def _prepare_validation_context(self, trade_request: TradeRequest) -> Dict[str, Any]:
        """검증 컨텍스트 준비"""
        # 포트폴리오 메트릭스 조회
        portfolio_metrics = await self.db_handler.get_portfolio_metrics()
        if not portfolio_metrics:
            # 기본값 사용
            portfolio_metrics = PortfolioMetrics(
                total_value=10000.0,
                available_cash=5000.0,
                unrealized_pnl=0.0,
                realized_pnl_today=self._daily_pnl,
                total_risk_exposure=0.0,
                number_of_positions=len(self._positions),
                largest_position_percent=0.0,
                daily_var=200.0
            )
        
        # 현재 가격 조회 (실제로는 Exchange Connector 사용)
        current_price = trade_request.price or await self._get_current_price(trade_request.symbol)
        
        # 예상 리스크 계산
        estimated_risk = self._calculate_estimated_risk(trade_request, current_price)
        
        # 오픈 포지션 조회
        positions = await self.db_handler.get_open_positions()
        positions_dict = {pos.symbol: pos for pos in positions}
        
        return {
            'portfolio_metrics': portfolio_metrics,
            'current_price': current_price,
            'estimated_risk': estimated_risk,
            'positions': positions_dict,
            'emergency_stop': self._emergency_stop,
            'max_daily_loss_triggered': self._max_daily_loss_triggered,
            'blocked_symbols': self._blocked_symbols
        }
    
    def _evaluate_risk_level(self, trade_request: TradeRequest, context: Dict[str, Any]) -> RiskLevel:
        """리스크 레벨 평가"""
        portfolio_metrics = context.get('portfolio_metrics')
        if not portfolio_metrics:
            return RiskLevel.EXTREME
        
        current_price = context.get('current_price', 0)
        if current_price <= 0:
            return RiskLevel.EXTREME
        
        # 포지션 크기 비율 계산
        position_value = trade_request.quantity * current_price
        position_size_percent = (position_value / portfolio_metrics.total_value) * 100
        
        # 리스크 레벨 결정
        if position_size_percent > 7:
            return RiskLevel.EXTREME
        elif position_size_percent > 5:
            return RiskLevel.HIGH
        elif position_size_percent > 2:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _create_rejection_response(self, context: Dict[str, Any]) -> ValidationResponse:
        """거부 응답 생성"""
        rejection_reasons = context.get('rejection_reasons', ["Validation failed"])
        
        return ValidationResponse(
            result=ValidationResult.REJECTED,
            approved_quantity=0.0,
            risk_level=RiskLevel.HIGH,
            reasons=rejection_reasons
        )
    
    def _create_approval_response(
        self,
        trade_request: TradeRequest,
        context: Dict[str, Any],
        risk_level: RiskLevel
    ) -> ValidationResponse:
        """승인 응답 생성"""
        response = ValidationResponse(
            result=ValidationResult.APPROVED,
            approved_quantity=trade_request.quantity,
            risk_level=risk_level,
            reasons=[]
        )
        
        # Stop Loss 제안
        if not trade_request.stop_loss:
            response.suggested_stop_loss = self._calculate_stop_loss(trade_request, context)
        
        # Take Profit 제안
        if not trade_request.take_profit:
            response.suggested_take_profit = self._calculate_take_profit(trade_request, context)
        
        # 포트폴리오 영향 계산
        response.portfolio_impact = self._calculate_portfolio_impact(trade_request, context)
        response.estimated_risk_amount = context.get('estimated_risk', 0)
        
        return response
    
    def _calculate_estimated_risk(self, trade_request: TradeRequest, current_price: float) -> float:
        """예상 리스크 계산"""
        if current_price <= 0:
            return 0.0
        
        position_value = trade_request.quantity * current_price
        
        # Stop Loss가 있으면 그 기준으로 계산
        if trade_request.stop_loss:
            if trade_request.side == "buy":
                risk_per_unit = max(0, current_price - trade_request.stop_loss)
            else:
                risk_per_unit = max(0, trade_request.stop_loss - current_price)
            
            return risk_per_unit * trade_request.quantity
        
        # 없으면 기본 리스크 비율 사용 (2% stop loss)
        return position_value * (self.risk_params.stop_loss_percent / 100)
    
    def _calculate_stop_loss(self, trade_request: TradeRequest, context: Dict[str, Any]) -> float:
        """Stop Loss 계산"""
        current_price = context.get('current_price', 100.0)
        
        if trade_request.side == "buy":
            return current_price * (1 - self.risk_params.stop_loss_percent / 100)
        else:
            return current_price * (1 + self.risk_params.stop_loss_percent / 100)
    
    def _calculate_take_profit(self, trade_request: TradeRequest, context: Dict[str, Any]) -> float:
        """Take Profit 계산"""
        current_price = context.get('current_price', 100.0)
        
        if trade_request.side == "buy":
            return current_price * (1 + self.risk_params.take_profit_percent / 100)
        else:
            return current_price * (1 - self.risk_params.take_profit_percent / 100)
    
    def _calculate_portfolio_impact(self, trade_request: TradeRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        """포트폴리오 영향 계산"""
        portfolio_metrics = context.get('portfolio_metrics')
        if not portfolio_metrics:
            return {}
        
        current_price = context.get('current_price', 0)
        if current_price <= 0:
            return {}
        
        position_value = trade_request.quantity * current_price
        position_size_percent = (position_value / portfolio_metrics.total_value) * 100
        
        estimated_risk = context.get('estimated_risk', 0)
        current_risk_percent = (portfolio_metrics.total_risk_exposure / portfolio_metrics.total_value) * 100
        new_risk_percent = current_risk_percent + (estimated_risk / portfolio_metrics.total_value) * 100
        
        return {
            'position_size_percent': round(position_size_percent, 2),
            'new_portfolio_risk_percent': round(new_risk_percent, 2),
            'estimated_daily_pnl_impact': round(estimated_risk, 2),
            'available_capital_after': portfolio_metrics.available_cash - position_value
        }
    
    async def _get_current_price(self, symbol: str) -> float:
        """현재 가격 조회"""
        # TODO: Exchange Connector와 통합
        # 임시로 기본값 반환
        default_prices = {
            'BTC/USDT': 50000.0,
            'ETH/USDT': 3000.0,
            'BNB/USDT': 400.0
        }
        return default_prices.get(symbol, 100.0)
    
    async def _record_validation_result(
        self,
        trade_request: TradeRequest,
        response: ValidationResponse
    ) -> None:
        """검증 결과 기록"""
        try:
            await self.db_handler.save_trade_validation(trade_request, response)
        except Exception as e:
            logger.error(f"Failed to record validation result: {e}")
    
    async def _log_high_risk_trade(
        self,
        trade_request: TradeRequest,
        response: ValidationResponse
    ) -> None:
        """고위험 거래 로깅"""
        await self.db_handler.log_risk_event(
            "high_risk_trade_approved",
            {
                "strategy_id": trade_request.strategy_id,
                "symbol": trade_request.symbol,
                "side": trade_request.side,
                "quantity": trade_request.quantity,
                "risk_level": response.risk_level.value,
                "estimated_risk": response.estimated_risk_amount
            }
        )
    
    async def record_trade_execution(
        self,
        trade_request: TradeRequest,
        execution_result: Dict[str, Any]
    ) -> bool:
        """거래 실행 기록"""
        try:
            trade_execution = TradeExecution(
                order_id=execution_result.get('order_id', ''),
                trade_id=execution_result.get('trade_id', ''),
                strategy_id=trade_request.strategy_id,
                symbol=trade_request.symbol,
                side=trade_request.side,
                requested_quantity=trade_request.quantity,
                executed_quantity=execution_result.get('filled_quantity', 0),
                price=execution_result.get('average_price', trade_request.price or 0),
                fees=execution_result.get('fees', 0),
                status=execution_result.get('status', 'unknown'),
                executed_at=datetime.now(timezone.utc)
            )
            
            # 데이터베이스 기록
            success = await self.db_handler.record_trade_execution(trade_execution)
            
            # 포지션 업데이트
            if success and execution_result.get('status') == 'filled':
                await self._update_position_tracking(trade_execution)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to record trade execution: {e}")
            return False
    
    async def _update_position_tracking(self, trade_execution: TradeExecution) -> None:
        """포지션 추적 업데이트"""
        position_data = {
            'strategy_id': trade_execution.strategy_id,
            'side': 'long' if trade_execution.side == 'buy' else 'short',
            'size': trade_execution.executed_quantity,
            'entry_price': trade_execution.price,
            'current_price': trade_execution.price,
            'unrealized_pnl': 0,
            'realized_pnl': 0,
            'is_open': True
        }
        
        await self.db_handler.update_position(trade_execution.symbol, position_data)
    
    async def emergency_stop(self, reason: str) -> bool:
        """긴급 정지 활성화"""
        try:
            self._emergency_stop = True
            
            await self.db_handler.log_risk_event(
                "emergency_stop_activated",
                {"reason": reason, "timestamp": datetime.now(timezone.utc).isoformat()}
            )
            
            logger.warning(
                f"Emergency stop activated",
                extra={"reason": reason}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to activate emergency stop: {e}")
            return False
    
    async def _initialize_from_database(self) -> None:
        """데이터베이스에서 초기 상태 로드"""
        # 포트폴리오 상태 로드
        await self.db_handler.load_portfolio_state()
        
        # 포트폴리오 규칙 로드
        rules = await self.db_handler.load_portfolio_rules()
        
        # 리스크 파라미터 업데이트
        if rules:
            for key, value in rules.items():
                if hasattr(self.risk_params, key):
                    setattr(self.risk_params, key, value)
    
    async def _initialize_portfolio_state(self) -> None:
        """포트폴리오 상태 초기화"""
        # 오픈 포지션 로드
        positions = await self.db_handler.get_open_positions()
        self._positions = {pos.symbol: pos for pos in positions}
        
        # 오늘 실현 손익 계산
        metrics = await self.db_handler.get_portfolio_metrics()
        if metrics:
            self._daily_pnl = metrics.realized_pnl_today
    
    async def _setup_message_subscriptions(self) -> None:
        """메시지 버스 구독 설정"""
        for topic, handler in self._message_handlers.items():
            await self.message_bus.subscribe(topic, handler)
            logger.info(f"Subscribed to {topic}")
    
    async def _cleanup_message_subscriptions(self) -> None:
        """메시지 구독 정리"""
        # TODO: MessageBus unsubscribe 구현 필요
        pass
    
    async def _persist_final_state(self) -> None:
        """최종 상태 저장"""
        # 성능 메트릭스 저장
        metrics = {
            'daily_pnl': self._daily_pnl,
            'total_positions': len(self._positions),
            'emergency_stop_active': self._emergency_stop
        }
        
        await self.db_handler.save_performance_metrics(metrics)
    
    # 메시지 핸들러들
    async def _handle_trade_proposal(self, topic: str, message: Dict[str, Any]) -> None:
        """거래 제안 처리"""
        try:
            trade_request = TradeRequest(**message.get('payload', {}))
            response = await self.validate_trade(trade_request)
            
            # 응답 발행
            if self.message_bus:
                await self.message_bus.publish(
                    "letrade.events",
                    "capital_allocation_response",
                    {
                        "strategy_id": trade_request.strategy_id,
                        "response": response.to_dict()
                    }
                )
                
        except Exception as e:
            logger.error(f"Error handling trade proposal: {e}")
    
    async def _handle_trade_validation(self, topic: str, message: Dict[str, Any]) -> None:
        """거래 검증 요청 처리"""
        await self._handle_trade_proposal(topic, message)
    
    async def _handle_trade_executed_event(self, topic: str, message: Dict[str, Any]) -> None:
        """거래 실행 이벤트 처리"""
        try:
            payload = message.get('payload', {})
            
            # TradeRequest 재구성
            trade_request = TradeRequest(
                strategy_id=payload.get('strategy_id', 0),
                symbol=payload.get('symbol', ''),
                side=payload.get('side', ''),
                quantity=payload.get('quantity', 0)
            )
            
            # 실행 결과 기록
            await self.record_trade_execution(trade_request, payload)
            
        except Exception as e:
            logger.error(f"Error handling trade executed event: {e}")