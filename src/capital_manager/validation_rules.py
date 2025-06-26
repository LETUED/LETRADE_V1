"""
Capital Manager 검증 규칙 모듈

Strategy Pattern을 사용하여 각 검증 규칙을 독립적으로 구현
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List

from .interfaces import RiskLevel, RiskParameters, TradeRequest

logger = logging.getLogger(__name__)


class ValidationRule(ABC):
    """검증 규칙 기본 클래스"""

    def __init__(self, name: str):
        self.name = name
        self.enabled = True

    @abstractmethod
    async def validate(
        self, trade_request: TradeRequest, context: Dict[str, Any]
    ) -> bool:
        """
        거래 요청 검증

        Args:
            trade_request: 검증할 거래 요청
            context: 검증 컨텍스트 (portfolio_metrics, positions, etc.)

        Returns:
            True if validation passes, False otherwise
        """
        pass

    @abstractmethod
    def get_rejection_reason(self) -> str:
        """검증 실패 사유 반환"""
        pass


class EmergencyStopRule(ValidationRule):
    """긴급 정지 검증 규칙"""

    def __init__(self):
        super().__init__("EmergencyStop")
        self._rejection_reason = ""

    async def validate(
        self, trade_request: TradeRequest, context: Dict[str, Any]
    ) -> bool:
        """긴급 정지 상태 확인"""
        if context.get("emergency_stop", False):
            self._rejection_reason = "Emergency stop is active"
            return False
        return True

    def get_rejection_reason(self) -> str:
        return self._rejection_reason


class DailyLossLimitRule(ValidationRule):
    """일일 손실 한도 검증 규칙"""

    def __init__(self, risk_params: RiskParameters):
        super().__init__("DailyLossLimit")
        self.risk_params = risk_params
        self._rejection_reason = ""

    async def validate(
        self, trade_request: TradeRequest, context: Dict[str, Any]
    ) -> bool:
        """일일 손실 한도 확인"""
        portfolio_metrics = context.get("portfolio_metrics")
        if not portfolio_metrics:
            self._rejection_reason = "Portfolio metrics not available"
            return False

        # 현재 일일 손실률 계산
        daily_loss_percent = 0
        if portfolio_metrics.total_value > 0:
            daily_loss_percent = (
                abs(
                    portfolio_metrics.realized_pnl_today / portfolio_metrics.total_value
                )
                * 100
            )

        # 예상 추가 손실 계산
        estimated_risk = context.get("estimated_risk", 0)
        potential_loss_percent = (
            daily_loss_percent + (estimated_risk / portfolio_metrics.total_value) * 100
        )

        if potential_loss_percent > self.risk_params.max_daily_loss_percent:
            self._rejection_reason = (
                f"Trade would exceed daily loss limit "
                f"({potential_loss_percent:.2f}% > {self.risk_params.max_daily_loss_percent}%)"
            )
            return False

        return True

    def get_rejection_reason(self) -> str:
        return self._rejection_reason


class PositionLimitRule(ValidationRule):
    """포지션 수 제한 검증 규칙"""

    def __init__(self, risk_params: RiskParameters):
        super().__init__("PositionLimit")
        self.risk_params = risk_params
        self._rejection_reason = ""

    async def validate(
        self, trade_request: TradeRequest, context: Dict[str, Any]
    ) -> bool:
        """포지션 수 제한 확인"""
        positions = context.get("positions", {})

        # 전체 포지션 수 확인
        total_positions = len(positions)
        if total_positions >= self.risk_params.max_total_positions:
            self._rejection_reason = f"Maximum total positions ({self.risk_params.max_total_positions}) reached"
            return False

        # 심볼별 포지션 수 확인
        symbol_positions = sum(
            1 for p in positions.values() if p.get("symbol") == trade_request.symbol
        )
        if symbol_positions >= self.risk_params.max_positions_per_symbol:
            self._rejection_reason = (
                f"Maximum positions per symbol ({self.risk_params.max_positions_per_symbol}) "
                f"reached for {trade_request.symbol}"
            )
            return False

        return True

    def get_rejection_reason(self) -> str:
        return self._rejection_reason


class TradeSizeRule(ValidationRule):
    """거래 크기 검증 규칙"""

    def __init__(self, risk_params: RiskParameters):
        super().__init__("TradeSize")
        self.risk_params = risk_params
        self._rejection_reason = ""

    async def validate(
        self, trade_request: TradeRequest, context: Dict[str, Any]
    ) -> bool:
        """거래 크기 제한 확인"""
        current_price = trade_request.price or context.get("current_price", 0)
        if current_price <= 0:
            self._rejection_reason = "Invalid price for trade size calculation"
            return False

        trade_value = trade_request.quantity * current_price

        # 최소 거래 금액 확인
        if trade_value < self.risk_params.min_trade_amount:
            self._rejection_reason = (
                f"Trade value ${trade_value:.2f} below minimum "
                f"${self.risk_params.min_trade_amount}"
            )
            return False

        # 최대 거래 금액 확인
        if trade_value > self.risk_params.max_trade_amount:
            self._rejection_reason = (
                f"Trade value ${trade_value:.2f} exceeds maximum "
                f"${self.risk_params.max_trade_amount}"
            )
            return False

        return True

    def get_rejection_reason(self) -> str:
        return self._rejection_reason


class PositionSizeRule(ValidationRule):
    """포지션 크기 검증 규칙"""

    def __init__(self, risk_params: RiskParameters):
        super().__init__("PositionSize")
        self.risk_params = risk_params
        self._rejection_reason = ""

    async def validate(
        self, trade_request: TradeRequest, context: Dict[str, Any]
    ) -> bool:
        """포지션 크기 제한 확인"""
        portfolio_metrics = context.get("portfolio_metrics")
        if not portfolio_metrics or portfolio_metrics.total_value <= 0:
            self._rejection_reason = "Invalid portfolio metrics"
            return False

        current_price = trade_request.price or context.get("current_price", 0)
        if current_price <= 0:
            self._rejection_reason = "Invalid price for position size calculation"
            return False

        position_value = trade_request.quantity * current_price
        position_size_percent = (position_value / portfolio_metrics.total_value) * 100

        if position_size_percent > self.risk_params.max_position_size_percent:
            self._rejection_reason = (
                f"Position size {position_size_percent:.2f}% exceeds maximum "
                f"{self.risk_params.max_position_size_percent}%"
            )
            return False

        return True

    def get_rejection_reason(self) -> str:
        return self._rejection_reason


class PortfolioRiskRule(ValidationRule):
    """포트폴리오 전체 리스크 검증 규칙"""

    def __init__(self, risk_params: RiskParameters):
        super().__init__("PortfolioRisk")
        self.risk_params = risk_params
        self._rejection_reason = ""

    async def validate(
        self, trade_request: TradeRequest, context: Dict[str, Any]
    ) -> bool:
        """포트폴리오 리스크 한도 확인"""
        portfolio_metrics = context.get("portfolio_metrics")
        if not portfolio_metrics or portfolio_metrics.total_value <= 0:
            self._rejection_reason = "Invalid portfolio metrics"
            return False

        # 현재 포트폴리오 리스크 비율
        current_risk_percent = (
            portfolio_metrics.total_risk_exposure / portfolio_metrics.total_value
        ) * 100

        # 예상 추가 리스크
        estimated_risk = context.get("estimated_risk", 0)
        new_risk_percent = (
            current_risk_percent
            + (estimated_risk / portfolio_metrics.total_value) * 100
        )

        if new_risk_percent > self.risk_params.max_portfolio_risk_percent:
            self._rejection_reason = (
                f"Trade would exceed portfolio risk limit "
                f"({new_risk_percent:.2f}% > {self.risk_params.max_portfolio_risk_percent}%)"
            )
            return False

        return True

    def get_rejection_reason(self) -> str:
        return self._rejection_reason


class BlockedSymbolRule(ValidationRule):
    """차단된 심볼 검증 규칙"""

    def __init__(self):
        super().__init__("BlockedSymbol")
        self._rejection_reason = ""

    async def validate(
        self, trade_request: TradeRequest, context: Dict[str, Any]
    ) -> bool:
        """차단된 심볼 확인"""
        blocked_symbols = context.get("blocked_symbols", set())

        if trade_request.symbol in blocked_symbols:
            self._rejection_reason = f"Symbol {trade_request.symbol} is blocked"
            return False

        return True

    def get_rejection_reason(self) -> str:
        return self._rejection_reason


class CircuitBreakerRule(ValidationRule):
    """서킷 브레이커 검증 규칙"""

    def __init__(self):
        super().__init__("CircuitBreaker")
        self._rejection_reason = ""

    async def validate(
        self, trade_request: TradeRequest, context: Dict[str, Any]
    ) -> bool:
        """서킷 브레이커 상태 확인"""
        if context.get("max_daily_loss_triggered", False):
            self._rejection_reason = "Daily loss circuit breaker is active"
            return False

        if context.get("max_drawdown_triggered", False):
            self._rejection_reason = "Drawdown circuit breaker is active"
            return False

        return True

    def get_rejection_reason(self) -> str:
        return self._rejection_reason


class ValidationRuleEngine:
    """검증 규칙 엔진"""

    def __init__(self, risk_params: RiskParameters):
        """검증 엔진 초기화"""
        self.risk_params = risk_params

        # 모든 검증 규칙 초기화
        self.rules: List[ValidationRule] = [
            EmergencyStopRule(),
            CircuitBreakerRule(),
            BlockedSymbolRule(),
            DailyLossLimitRule(risk_params),
            PositionLimitRule(risk_params),
            TradeSizeRule(risk_params),
            PositionSizeRule(risk_params),
            PortfolioRiskRule(risk_params),
        ]

        logger.info(f"ValidationRuleEngine initialized with {len(self.rules)} rules")

    async def validate_all(
        self, trade_request: TradeRequest, context: Dict[str, Any]
    ) -> bool:
        """
        모든 검증 규칙 실행

        Args:
            trade_request: 검증할 거래 요청
            context: 검증 컨텍스트

        Returns:
            모든 검증을 통과하면 True, 하나라도 실패하면 False
        """
        rejection_reasons = []

        for rule in self.rules:
            if not rule.enabled:
                continue

            try:
                if not await rule.validate(trade_request, context):
                    reason = rule.get_rejection_reason()
                    rejection_reasons.append(f"[{rule.name}] {reason}")
                    logger.warning(
                        f"Validation rule {rule.name} failed",
                        extra={
                            "rule": rule.name,
                            "reason": reason,
                            "symbol": trade_request.symbol,
                            "strategy_id": trade_request.strategy_id,
                        },
                    )

            except Exception as e:
                logger.error(
                    f"Error in validation rule {rule.name}",
                    extra={"error": str(e), "rule": rule.name},
                )
                rejection_reasons.append(f"[{rule.name}] Validation error: {str(e)}")

        # 모든 거부 사유를 context에 저장
        if rejection_reasons:
            context["rejection_reasons"] = rejection_reasons
            context["rejection_reason"] = "; ".join(rejection_reasons)
            return False

        return True

    def add_rule(self, rule: ValidationRule) -> None:
        """새로운 검증 규칙 추가"""
        self.rules.append(rule)
        logger.info(f"Added validation rule: {rule.name}")

    def remove_rule(self, rule_name: str) -> bool:
        """검증 규칙 제거"""
        for i, rule in enumerate(self.rules):
            if rule.name == rule_name:
                del self.rules[i]
                logger.info(f"Removed validation rule: {rule_name}")
                return True
        return False

    def enable_rule(self, rule_name: str) -> bool:
        """검증 규칙 활성화"""
        for rule in self.rules:
            if rule.name == rule_name:
                rule.enabled = True
                logger.info(f"Enabled validation rule: {rule_name}")
                return True
        return False

    def disable_rule(self, rule_name: str) -> bool:
        """검증 규칙 비활성화"""
        for rule in self.rules:
            if rule.name == rule_name:
                rule.enabled = False
                logger.info(f"Disabled validation rule: {rule_name}")
                return True
        return False
