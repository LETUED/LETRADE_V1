"""
리팩토링된 Capital Manager - 책임 분리와 Strategy Pattern 적용

주요 개선사항:
1. validate_trade 메서드를 여러 작은 메서드로 분리
2. Validation Rules를 Strategy Pattern으로 구현
3. 데이터베이스 로직 분리
4. 리스크 계산 로직 분리
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from decimal import Decimal

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """리스크 레벨"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class ValidationResult(Enum):
    """검증 결과"""
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUIRES_APPROVAL = "requires_approval"


@dataclass
class TradeRequest:
    """거래 요청 데이터"""
    strategy_id: int
    symbol: str
    side: str  # "buy" or "sell"
    quantity: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    order_type: str = "market"
    metadata: Dict[str, Any] = None


@dataclass
class ValidationResponse:
    """검증 응답 데이터"""
    result: ValidationResult
    approved_quantity: float
    risk_level: RiskLevel
    reasons: List[str]
    suggested_stop_loss: Optional[float] = None
    suggested_take_profit: Optional[float] = None
    estimated_risk_amount: float = 0.0
    portfolio_impact: Dict[str, Any] = None


@dataclass
class PortfolioMetrics:
    """포트폴리오 메트릭스"""
    total_value: float
    available_cash: float
    unrealized_pnl: float
    realized_pnl_today: float
    total_risk_exposure: float
    number_of_positions: int
    largest_position_percent: float
    daily_var: float


@dataclass
class RiskParameters:
    """리스크 파라미터"""
    max_position_size_percent: float = 10.0
    max_portfolio_risk_percent: float = 20.0
    stop_loss_percent: float = 2.0
    take_profit_percent: float = 5.0
    max_daily_loss_percent: float = 5.0
    max_drawdown_percent: float = 15.0
    risk_free_rate: float = 0.02
    min_trade_amount: float = 10.0
    max_trade_amount: float = 10000.0
    max_positions_per_symbol: int = 1
    max_total_positions: int = 10


# ============== Validation Rules (Strategy Pattern) ==============

class ValidationRule:
    """검증 규칙 기본 클래스"""
    
    def __init__(self, name: str):
        self.name = name
    
    async def validate(self, request: TradeRequest, context: Dict[str, Any]) -> bool:
        """검증 수행"""
        raise NotImplementedError
    
    def get_rejection_reason(self, request: TradeRequest, context: Dict[str, Any]) -> str:
        """거부 사유 반환"""
        raise NotImplementedError


class EmergencyStopRule(ValidationRule):
    """긴급 정지 검증 규칙"""
    
    def __init__(self):
        super().__init__("EmergencyStop")
    
    async def validate(self, request: TradeRequest, context: Dict[str, Any]) -> bool:
        return not context.get('emergency_stop', False)
    
    def get_rejection_reason(self, request: TradeRequest, context: Dict[str, Any]) -> str:
        return "Emergency stop is active"


class DailyLossLimitRule(ValidationRule):
    """일일 손실 한도 검증 규칙"""
    
    def __init__(self, risk_params: RiskParameters):
        super().__init__("DailyLossLimit")
        self.risk_params = risk_params
    
    async def validate(self, request: TradeRequest, context: Dict[str, Any]) -> bool:
        portfolio_metrics = context.get('portfolio_metrics')
        if not portfolio_metrics:
            return False
            
        daily_loss_percent = abs(portfolio_metrics.realized_pnl_today / portfolio_metrics.total_value) * 100
        return daily_loss_percent < self.risk_params.max_daily_loss_percent
    
    def get_rejection_reason(self, request: TradeRequest, context: Dict[str, Any]) -> str:
        return f"Daily loss limit exceeded ({self.risk_params.max_daily_loss_percent}%)"


class PositionLimitRule(ValidationRule):
    """포지션 한도 검증 규칙"""
    
    def __init__(self, risk_params: RiskParameters):
        super().__init__("PositionLimit")
        self.risk_params = risk_params
    
    async def validate(self, request: TradeRequest, context: Dict[str, Any]) -> bool:
        positions = context.get('positions', {})
        
        # 전체 포지션 수 검사
        if len(positions) >= self.risk_params.max_total_positions:
            return False
        
        # 심볼별 포지션 수 검사
        symbol_positions = sum(1 for p in positions.values() if p.get('symbol') == request.symbol)
        return symbol_positions < self.risk_params.max_positions_per_symbol
    
    def get_rejection_reason(self, request: TradeRequest, context: Dict[str, Any]) -> str:
        positions = context.get('positions', {})
        if len(positions) >= self.risk_params.max_total_positions:
            return f"Maximum total positions ({self.risk_params.max_total_positions}) reached"
        return f"Maximum positions per symbol ({self.risk_params.max_positions_per_symbol}) reached"


class TradeSizeRule(ValidationRule):
    """거래 크기 검증 규칙"""
    
    def __init__(self, risk_params: RiskParameters):
        super().__init__("TradeSize")
        self.risk_params = risk_params
    
    async def validate(self, request: TradeRequest, context: Dict[str, Any]) -> bool:
        current_price = request.price or context.get('current_price', 0)
        if current_price == 0:
            return False
            
        trade_value = request.quantity * current_price
        
        # 최소/최대 거래 금액 검사
        if trade_value < self.risk_params.min_trade_amount:
            return False
        if trade_value > self.risk_params.max_trade_amount:
            return False
            
        return True
    
    def get_rejection_reason(self, request: TradeRequest, context: Dict[str, Any]) -> str:
        current_price = request.price or context.get('current_price', 0)
        trade_value = request.quantity * current_price
        
        if trade_value < self.risk_params.min_trade_amount:
            return f"Trade value ${trade_value:.2f} below minimum ${self.risk_params.min_trade_amount}"
        return f"Trade value ${trade_value:.2f} exceeds maximum ${self.risk_params.max_trade_amount}"


class PortfolioRiskRule(ValidationRule):
    """포트폴리오 리스크 검증 규칙"""
    
    def __init__(self, risk_params: RiskParameters):
        super().__init__("PortfolioRisk")
        self.risk_params = risk_params
    
    async def validate(self, request: TradeRequest, context: Dict[str, Any]) -> bool:
        portfolio_metrics = context.get('portfolio_metrics')
        if not portfolio_metrics:
            return False
            
        # 포지션 크기 검사
        current_price = request.price or context.get('current_price', 0)
        position_value = request.quantity * current_price
        position_size_percent = (position_value / portfolio_metrics.total_value) * 100
        
        if position_size_percent > self.risk_params.max_position_size_percent:
            return False
            
        # 포트폴리오 리스크 검사
        estimated_risk = context.get('estimated_risk', 0)
        current_risk_percent = (portfolio_metrics.total_risk_exposure / portfolio_metrics.total_value) * 100
        new_risk_percent = current_risk_percent + (estimated_risk / portfolio_metrics.total_value) * 100
        
        return new_risk_percent <= self.risk_params.max_portfolio_risk_percent
    
    def get_rejection_reason(self, request: TradeRequest, context: Dict[str, Any]) -> str:
        portfolio_metrics = context.get('portfolio_metrics')
        current_price = request.price or context.get('current_price', 0)
        position_value = request.quantity * current_price
        position_size_percent = (position_value / portfolio_metrics.total_value) * 100
        
        if position_size_percent > self.risk_params.max_position_size_percent:
            return f"Position size {position_size_percent:.2f}% exceeds limit {self.risk_params.max_position_size_percent}%"
        
        return f"Trade would exceed portfolio risk limit"


# ============== 리팩토링된 Capital Manager ==============

class RefactoredCapitalManager:
    """리팩토링된 Capital Manager"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.risk_params = self._load_risk_parameters(config)
        
        # Validation Rules 초기화
        self.validation_rules = [
            EmergencyStopRule(),
            DailyLossLimitRule(self.risk_params),
            PositionLimitRule(self.risk_params),
            TradeSizeRule(self.risk_params),
            PortfolioRiskRule(self.risk_params)
        ]
        
        # 상태 관리
        self._positions = {}
        self._daily_pnl = 0.0
        self._emergency_stop = False
        
        logger.info("RefactoredCapitalManager initialized")
    
    def _load_risk_parameters(self, config: Dict[str, Any]) -> RiskParameters:
        """리스크 파라미터 로드"""
        risk_config = config.get('risk_parameters', {})
        return RiskParameters(**risk_config)
    
    async def validate_trade(self, trade_request: TradeRequest) -> ValidationResponse:
        """
        거래 검증 - 리팩토링된 버전
        
        주요 개선사항:
        1. 단일 책임 원칙 적용
        2. 검증 로직을 개별 규칙으로 분리
        3. 컨텍스트 기반 검증
        4. 명확한 흐름
        """
        logger.info(f"Validating trade request for {trade_request.symbol}")
        
        # 1. 검증 컨텍스트 준비
        context = await self._prepare_validation_context(trade_request)
        
        # 2. 검증 규칙 실행
        validation_errors = await self._run_validation_rules(trade_request, context)
        
        # 3. 리스크 레벨 평가
        risk_level = self._evaluate_risk_level(trade_request, context)
        
        # 4. 응답 생성
        response = self._create_validation_response(
            trade_request, 
            context, 
            validation_errors, 
            risk_level
        )
        
        # 5. 데이터베이스 기록 (비동기)
        # await self._record_validation_result(trade_request, response)
        
        return response
    
    async def _prepare_validation_context(self, trade_request: TradeRequest) -> Dict[str, Any]:
        """검증 컨텍스트 준비"""
        # 포트폴리오 메트릭스 조회
        portfolio_metrics = await self.get_portfolio_metrics()
        
        # 현재 가격 조회 (실제로는 Exchange Connector 사용)
        current_price = trade_request.price or await self._get_current_price(trade_request.symbol)
        
        # 예상 리스크 계산
        estimated_risk = self._calculate_estimated_risk(trade_request, current_price)
        
        return {
            'portfolio_metrics': portfolio_metrics,
            'current_price': current_price,
            'estimated_risk': estimated_risk,
            'positions': self._positions,
            'emergency_stop': self._emergency_stop
        }
    
    async def _run_validation_rules(self, trade_request: TradeRequest, context: Dict[str, Any]) -> List[str]:
        """모든 검증 규칙 실행"""
        errors = []
        
        for rule in self.validation_rules:
            try:
                if not await rule.validate(trade_request, context):
                    reason = rule.get_rejection_reason(trade_request, context)
                    errors.append(reason)
                    logger.warning(f"Validation rule {rule.name} failed: {reason}")
            except Exception as e:
                logger.error(f"Error in validation rule {rule.name}: {e}")
                errors.append(f"Validation error in {rule.name}")
        
        return errors
    
    def _evaluate_risk_level(self, trade_request: TradeRequest, context: Dict[str, Any]) -> RiskLevel:
        """리스크 레벨 평가"""
        portfolio_metrics = context.get('portfolio_metrics')
        if not portfolio_metrics:
            return RiskLevel.EXTREME
        
        # 포지션 크기 기반 리스크 평가
        current_price = context.get('current_price', 0)
        position_value = trade_request.quantity * current_price
        position_size_percent = (position_value / portfolio_metrics.total_value) * 100
        
        if position_size_percent > 5:
            return RiskLevel.HIGH
        elif position_size_percent > 2:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _create_validation_response(
        self,
        trade_request: TradeRequest,
        context: Dict[str, Any],
        validation_errors: List[str],
        risk_level: RiskLevel
    ) -> ValidationResponse:
        """검증 응답 생성"""
        # 검증 실패 시
        if validation_errors:
            return ValidationResponse(
                result=ValidationResult.REJECTED,
                approved_quantity=0.0,
                risk_level=risk_level,
                reasons=validation_errors
            )
        
        # 검증 성공 시
        response = ValidationResponse(
            result=ValidationResult.APPROVED,
            approved_quantity=trade_request.quantity,
            risk_level=risk_level,
            reasons=[]
        )
        
        # Stop Loss/Take Profit 제안
        if not trade_request.stop_loss:
            response.suggested_stop_loss = self._calculate_stop_loss(trade_request, context)
        
        if not trade_request.take_profit:
            response.suggested_take_profit = self._calculate_take_profit(trade_request, context)
        
        # 포트폴리오 영향 계산
        response.portfolio_impact = self._calculate_portfolio_impact(trade_request, context)
        response.estimated_risk_amount = context.get('estimated_risk', 0)
        
        return response
    
    def _calculate_estimated_risk(self, trade_request: TradeRequest, current_price: float) -> float:
        """예상 리스크 계산"""
        position_value = trade_request.quantity * current_price
        
        # Stop Loss 기반 리스크 계산
        if trade_request.stop_loss:
            if trade_request.side == "buy":
                risk_per_unit = current_price - trade_request.stop_loss
            else:
                risk_per_unit = trade_request.stop_loss - current_price
            
            return abs(risk_per_unit * trade_request.quantity)
        
        # 기본 리스크 (포지션의 2%)
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
        current_price = context.get('current_price', 0)
        
        position_value = trade_request.quantity * current_price
        position_size_percent = (position_value / portfolio_metrics.total_value) * 100
        
        estimated_risk = context.get('estimated_risk', 0)
        current_risk_percent = (portfolio_metrics.total_risk_exposure / portfolio_metrics.total_value) * 100
        new_risk_percent = current_risk_percent + (estimated_risk / portfolio_metrics.total_value) * 100
        
        return {
            'position_size_percent': position_size_percent,
            'new_portfolio_risk_percent': new_risk_percent,
            'estimated_daily_pnl_impact': estimated_risk
        }
    
    async def _get_current_price(self, symbol: str) -> float:
        """현재 가격 조회 (Mock)"""
        # 실제로는 Exchange Connector 사용
        return 50000.0  # BTC 기본값
    
    async def get_portfolio_metrics(self) -> PortfolioMetrics:
        """포트폴리오 메트릭스 조회"""
        # 실제로는 데이터베이스에서 조회
        return PortfolioMetrics(
            total_value=10000.0,
            available_cash=5000.0,
            unrealized_pnl=100.0,
            realized_pnl_today=self._daily_pnl,
            total_risk_exposure=500.0,
            number_of_positions=len(self._positions),
            largest_position_percent=10.0,
            daily_var=200.0
        )


# ============== 사용 예시 ==============

async def example_usage():
    """사용 예시"""
    config = {
        'risk_parameters': {
            'max_position_size_percent': 10.0,
            'max_portfolio_risk_percent': 20.0,
            'stop_loss_percent': 2.0,
            'take_profit_percent': 5.0,
            'max_daily_loss_percent': 5.0
        }
    }
    
    manager = RefactoredCapitalManager(config)
    
    # 거래 요청
    trade_request = TradeRequest(
        strategy_id=1,
        symbol="BTC/USDT",
        side="buy",
        quantity=0.1,
        price=50000.0
    )
    
    # 검증
    response = await manager.validate_trade(trade_request)
    
    print(f"Validation Result: {response.result.value}")
    print(f"Risk Level: {response.risk_level.value}")
    if response.suggested_stop_loss:
        print(f"Suggested Stop Loss: ${response.suggested_stop_loss:.2f}")
    if response.suggested_take_profit:
        print(f"Suggested Take Profit: ${response.suggested_take_profit:.2f}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())