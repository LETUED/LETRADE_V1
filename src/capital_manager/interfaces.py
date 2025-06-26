"""
Capital Manager 인터페이스 및 데이터 구조 정의
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
from decimal import Decimal


class RiskLevel(Enum):
    """리스크 레벨 카테고리"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class ValidationResult(Enum):
    """거래 검증 결과"""
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUIRES_APPROVAL = "requires_approval"


@dataclass
class RiskParameters:
    """리스크 관리 파라미터"""
    # 포지션 크기 제한
    max_position_size_percent: float = 10.0  # 전체 자본의 최대 %
    max_positions_per_symbol: int = 1  # 심볼당 최대 포지션 수
    max_total_positions: int = 10  # 전체 최대 포지션 수
    
    # 포트폴리오 리스크 제한
    max_portfolio_risk_percent: float = 20.0  # 전체 포트폴리오 최대 리스크 %
    max_daily_loss_percent: float = 5.0  # 일일 최대 손실 %
    max_drawdown_percent: float = 15.0  # 최대 낙폭 %
    
    # 거래 크기 제한
    min_trade_amount: float = 10.0  # 최소 거래 금액 (USD)
    max_trade_amount: float = 10000.0  # 최대 거래 금액 (USD)
    
    # 리스크 관리 기본값
    stop_loss_percent: float = 2.0  # 기본 손절매 %
    take_profit_percent: float = 5.0  # 기본 익절매 %
    risk_free_rate: float = 0.02  # 무위험 이자율 (연간)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "max_position_size_percent": self.max_position_size_percent,
            "max_positions_per_symbol": self.max_positions_per_symbol,
            "max_total_positions": self.max_total_positions,
            "max_portfolio_risk_percent": self.max_portfolio_risk_percent,
            "max_daily_loss_percent": self.max_daily_loss_percent,
            "max_drawdown_percent": self.max_drawdown_percent,
            "min_trade_amount": self.min_trade_amount,
            "max_trade_amount": self.max_trade_amount,
            "stop_loss_percent": self.stop_loss_percent,
            "take_profit_percent": self.take_profit_percent,
            "risk_free_rate": self.risk_free_rate,
        }


@dataclass
class TradeRequest:
    """거래 요청 데이터 구조"""
    strategy_id: int
    symbol: str
    side: str  # "buy" or "sell"
    quantity: float
    price: Optional[float] = None  # None for market orders
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    order_type: str = "market"
    time_in_force: str = "GTC"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """초기화 후 검증"""
        if self.side not in ["buy", "sell"]:
            raise ValueError(f"Invalid side: {self.side}")
        if self.quantity <= 0:
            raise ValueError(f"Invalid quantity: {self.quantity}")


@dataclass
class ValidationResponse:
    """거래 검증 응답"""
    result: ValidationResult
    approved_quantity: float
    risk_level: RiskLevel
    reasons: List[str] = field(default_factory=list)
    suggested_stop_loss: Optional[float] = None
    suggested_take_profit: Optional[float] = None
    estimated_risk_amount: float = 0.0
    portfolio_impact: Dict[str, Any] = field(default_factory=dict)
    
    def is_approved(self) -> bool:
        """승인 여부 확인"""
        return self.result == ValidationResult.APPROVED
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "result": self.result.value,
            "approved_quantity": self.approved_quantity,
            "risk_level": self.risk_level.value,
            "reasons": self.reasons,
            "suggested_stop_loss": self.suggested_stop_loss,
            "suggested_take_profit": self.suggested_take_profit,
            "estimated_risk_amount": self.estimated_risk_amount,
            "portfolio_impact": self.portfolio_impact,
        }


@dataclass
class PortfolioMetrics:
    """포트폴리오 메트릭스"""
    total_value: float  # 전체 포트폴리오 가치
    available_cash: float  # 사용 가능한 현금
    unrealized_pnl: float  # 미실현 손익
    realized_pnl_today: float  # 오늘 실현 손익
    total_risk_exposure: float  # 전체 리스크 노출
    number_of_positions: int  # 포지션 수
    largest_position_percent: float  # 가장 큰 포지션의 비율
    daily_var: float  # 일일 Value at Risk
    risk_level: float = 0.0  # 리스크 레벨 (0-10)
    
    def get_used_capital(self) -> float:
        """사용 중인 자본 계산"""
        return self.total_value - self.available_cash
    
    def get_available_capital_percent(self) -> float:
        """사용 가능한 자본 비율"""
        if self.total_value > 0:
            return (self.available_cash / self.total_value) * 100
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "total_value": self.total_value,
            "available_cash": self.available_cash,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl_today": self.realized_pnl_today,
            "total_risk_exposure": self.total_risk_exposure,
            "number_of_positions": self.number_of_positions,
            "largest_position_percent": self.largest_position_percent,
            "daily_var": self.daily_var,
            "risk_level": self.risk_level,
            "used_capital": self.get_used_capital(),
            "available_capital_percent": self.get_available_capital_percent(),
        }


@dataclass
class PositionInfo:
    """포지션 정보"""
    symbol: str
    side: str  # "long" or "short"
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    opened_at: datetime = field(default_factory=datetime.utcnow)
    strategy_id: Optional[int] = None
    
    def get_position_value(self) -> float:
        """포지션 가치 계산"""
        return self.size * self.current_price
    
    def get_pnl_percent(self) -> float:
        """손익률 계산"""
        if self.entry_price > 0:
            if self.side == "long":
                return ((self.current_price - self.entry_price) / self.entry_price) * 100
            else:  # short
                return ((self.entry_price - self.current_price) / self.entry_price) * 100
        return 0.0
    
    def get_risk_amount(self) -> float:
        """리스크 금액 계산 (Stop Loss 기준)"""
        if self.stop_loss:
            if self.side == "long":
                risk_per_unit = self.current_price - self.stop_loss
            else:  # short
                risk_per_unit = self.stop_loss - self.current_price
            return abs(risk_per_unit * self.size)
        return 0.0


@dataclass
class TradeExecution:
    """거래 실행 정보"""
    order_id: str
    trade_id: str
    strategy_id: int
    symbol: str
    side: str
    requested_quantity: float
    executed_quantity: float
    price: float
    fees: float
    status: str  # "filled", "partial", "cancelled"
    executed_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_total_cost(self) -> float:
        """총 비용 계산 (수수료 포함)"""
        base_cost = self.executed_quantity * self.price
        if self.side == "buy":
            return base_cost + self.fees
        else:  # sell
            return base_cost - self.fees