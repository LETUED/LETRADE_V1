"""State Reconciliation Protocol for Letrade_v1 trading system.

Implements MVP Section 3.6 requirements for state synchronization between
system components and external exchange state. Critical for system restart
scenarios and maintaining data integrity.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from decimal import Decimal

from src.common.database import (
    db_manager, Strategy, Trade, Position, Portfolio, 
    PortfolioRule, PerformanceMetric, SystemLog
)

logger = logging.getLogger(__name__)


class ReconciliationStatus(Enum):
    """Status of reconciliation process."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class DiscrepancyType(Enum):
    """Types of state discrepancies."""
    MISSING_POSITION = "missing_position"
    EXTRA_POSITION = "extra_position"
    POSITION_SIZE_MISMATCH = "position_size_mismatch"
    MISSING_ORDER = "missing_order"
    ORDER_STATUS_MISMATCH = "order_status_mismatch"
    BALANCE_MISMATCH = "balance_mismatch"
    TRADE_RECORD_MISSING = "trade_record_missing"


class ReconciliationSeverity(Enum):
    """Severity levels for discrepancies."""
    LOW = "low"           # Minor differences, auto-correctable
    MEDIUM = "medium"     # Significant differences, needs attention
    HIGH = "high"         # Critical differences, manual intervention
    CRITICAL = "critical" # System integrity at risk, halt trading


@dataclass
class StateDiscrepancy:
    """Represents a single state discrepancy."""
    
    type: DiscrepancyType
    severity: ReconciliationSeverity
    description: str
    system_state: Dict[str, Any]
    exchange_state: Dict[str, Any]
    strategy_id: Optional[int] = None
    symbol: Optional[str] = None
    suggested_action: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging and storage."""
        return {
            'type': self.type.value,
            'severity': self.severity.value,
            'description': self.description,
            'system_state': self.system_state,
            'exchange_state': self.exchange_state,
            'strategy_id': self.strategy_id,
            'symbol': self.symbol,
            'suggested_action': self.suggested_action,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class ReconciliationReport:
    """Comprehensive reconciliation report."""
    
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: ReconciliationStatus = ReconciliationStatus.PENDING
    discrepancies: List[StateDiscrepancy] = field(default_factory=list)
    actions_taken: List[Dict[str, Any]] = field(default_factory=list)
    strategies_checked: Set[int] = field(default_factory=set)
    exchanges_checked: Set[str] = field(default_factory=set)
    total_positions_checked: int = 0
    total_orders_checked: int = 0
    
    def add_discrepancy(self, discrepancy: StateDiscrepancy) -> None:
        """Add a new discrepancy to the report."""
        self.discrepancies.append(discrepancy)
        
        # Log based on severity
        if discrepancy.severity in [ReconciliationSeverity.HIGH, ReconciliationSeverity.CRITICAL]:
            logger.error(f"Critical discrepancy found: {discrepancy.description}")
        elif discrepancy.severity == ReconciliationSeverity.MEDIUM:
            logger.warning(f"Significant discrepancy found: {discrepancy.description}")
        else:
            logger.info(f"Minor discrepancy found: {discrepancy.description}")
    
    def get_critical_discrepancies(self) -> List[StateDiscrepancy]:
        """Get only critical and high severity discrepancies."""
        return [d for d in self.discrepancies 
                if d.severity in [ReconciliationSeverity.HIGH, ReconciliationSeverity.CRITICAL]]
    
    def to_summary(self) -> Dict[str, Any]:
        """Generate summary report."""
        severity_counts = {}
        for severity in ReconciliationSeverity:
            severity_counts[severity.value] = len([
                d for d in self.discrepancies if d.severity == severity
            ])
        
        return {
            'session_id': self.session_id,
            'status': self.status.value,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': (
                (self.end_time - self.start_time).total_seconds() 
                if self.end_time else None
            ),
            'total_discrepancies': len(self.discrepancies),
            'severity_breakdown': severity_counts,
            'strategies_checked': list(self.strategies_checked),
            'exchanges_checked': list(self.exchanges_checked),
            'total_positions_checked': self.total_positions_checked,
            'total_orders_checked': self.total_orders_checked,
            'actions_taken_count': len(self.actions_taken),
            'requires_attention': len(self.get_critical_discrepancies()) > 0
        }


class StateReconciliationEngine:
    """Core engine for state reconciliation between system and exchange.
    
    Implements MVP Section 3.6 requirements:
    - FR-SR-001: State discrepancy detection
    - FR-SR-002: State reconciliation execution
    """
    
    def __init__(self, exchange_connector, capital_manager):
        """Initialize reconciliation engine.
        
        Args:
            exchange_connector: Exchange connector instance
            capital_manager: Capital manager instance
        """
        self.exchange_connector = exchange_connector
        self.capital_manager = capital_manager
        self.current_report = None
        self.auto_correct = True  # Auto-correct minor discrepancies
        self.max_position_variance = Decimal('0.001')  # 0.1% tolerance for position sizes
        
        logger.info("State reconciliation engine initialized")
    
    async def perform_full_reconciliation(self) -> ReconciliationReport:
        """Perform comprehensive state reconciliation.
        
        Returns:
            ReconciliationReport with all findings and actions
        """
        import uuid
        session_id = str(uuid.uuid4())[:8]
        
        self.current_report = ReconciliationReport(
            session_id=session_id,
            start_time=datetime.now(timezone.utc)
        )
        
        logger.info(f"Starting full state reconciliation (session: {session_id})")
        
        try:
            self.current_report.status = ReconciliationStatus.IN_PROGRESS
            
            # Step 1: Reconcile portfolio balances
            await self._reconcile_portfolio_balances()
            
            # Step 2: Reconcile active positions
            await self._reconcile_active_positions()
            
            # Step 3: Reconcile open orders
            await self._reconcile_open_orders()
            
            # Step 4: Reconcile strategy states
            await self._reconcile_strategy_states()
            
            # Step 5: Apply corrections for minor discrepancies
            if self.auto_correct:
                await self._apply_auto_corrections()
            
            # Step 6: Generate final report
            await self._finalize_reconciliation()
            
            self.current_report.status = ReconciliationStatus.COMPLETED
            logger.info(f"State reconciliation completed (session: {session_id})")
            
        except Exception as e:
            self.current_report.status = ReconciliationStatus.FAILED
            logger.error(f"State reconciliation failed (session: {session_id}): {e}")
            
            # Log critical system event
            await self._log_system_event(
                level="ERROR",
                message=f"State reconciliation failed: {e}",
                context={'session_id': session_id, 'error': str(e)}
            )
            
        finally:
            self.current_report.end_time = datetime.now(timezone.utc)
            await self._save_reconciliation_report()
        
        return self.current_report
    
    async def _reconcile_portfolio_balances(self) -> None:
        """Reconcile portfolio balances with exchange."""
        logger.info("Reconciling portfolio balances...")
        
        try:
            # Get exchange balances
            exchange_balances = await self.exchange_connector.get_account_balance()
            
            # Get system portfolio state
            with db_manager.get_session() as session:
                portfolios = session.query(Portfolio).filter_by(is_active=True).all()
                
                for portfolio in portfolios:
                    portfolio_currency = portfolio.currency
                    
                    if portfolio_currency in exchange_balances:
                        exchange_balance = exchange_balances[portfolio_currency]
                        system_total = portfolio.total_capital
                        exchange_total = exchange_balance.total
                        
                        # Check for significant balance discrepancies
                        variance = abs(system_total - exchange_total) / max(system_total, Decimal('1'))
                        
                        if variance > Decimal('0.05'):  # 5% variance threshold
                            discrepancy = StateDiscrepancy(
                                type=DiscrepancyType.BALANCE_MISMATCH,
                                severity=ReconciliationSeverity.HIGH if variance > Decimal('0.20') else ReconciliationSeverity.MEDIUM,
                                description=f"Portfolio {portfolio.name} balance mismatch: "
                                           f"System={system_total}, Exchange={exchange_total}",
                                system_state={'total_capital': float(system_total)},
                                exchange_state={'total_balance': float(exchange_total)},
                                suggested_action="Update portfolio total_capital from exchange balance"
                            )
                            self.current_report.add_discrepancy(discrepancy)
                    
                    else:
                        # Portfolio currency not found on exchange
                        discrepancy = StateDiscrepancy(
                            type=DiscrepancyType.BALANCE_MISMATCH,
                            severity=ReconciliationSeverity.MEDIUM,
                            description=f"Portfolio currency {portfolio_currency} not found on exchange",
                            system_state={'currency': portfolio_currency},
                            exchange_state={'available_currencies': list(exchange_balances.keys())},
                            suggested_action="Verify portfolio currency configuration"
                        )
                        self.current_report.add_discrepancy(discrepancy)
                        
        except Exception as e:
            logger.error(f"Error reconciling portfolio balances: {e}")
            raise
    
    async def _reconcile_active_positions(self) -> None:
        """Reconcile active positions with exchange."""
        logger.info("Reconciling active positions...")
        
        try:
            # Get all open positions from database
            with db_manager.get_session() as session:
                db_positions = session.query(Position).filter_by(is_open=True).all()
                
                # For each position, verify with exchange
                for db_position in db_positions:
                    self.current_report.total_positions_checked += 1
                    
                    # Note: Most spot exchanges don't have "positions" concept
                    # We'll verify through balance and order history instead
                    symbol_base = db_position.symbol.split('/')[0]
                    
                    # Get balance for the base currency
                    exchange_balances = await self.exchange_connector.get_account_balance()
                    
                    if symbol_base in exchange_balances:
                        exchange_balance = exchange_balances[symbol_base]
                        
                        # For spot trading, we check if we have the expected holdings
                        if hasattr(db_position, 'side') and db_position.side == 'long':
                            expected_holding = db_position.current_size
                            actual_holding = exchange_balance.total
                            
                            variance = abs(expected_holding - actual_holding) / max(expected_holding, Decimal('0.001'))
                            
                            if variance > self.max_position_variance:
                                discrepancy = StateDiscrepancy(
                                    type=DiscrepancyType.POSITION_SIZE_MISMATCH,
                                    severity=ReconciliationSeverity.MEDIUM,
                                    description=f"Position size mismatch for {db_position.symbol}: "
                                               f"DB={expected_holding}, Exchange={actual_holding}",
                                    system_state={
                                        'position_id': db_position.id,
                                        'symbol': db_position.symbol,
                                        'side': getattr(db_position, 'side', 'unknown'),
                                        'size': float(expected_holding)
                                    },
                                    exchange_state={
                                        'symbol': db_position.symbol,
                                        'balance': float(actual_holding)
                                    },
                                    strategy_id=db_position.strategy_id,
                                    symbol=db_position.symbol,
                                    suggested_action="Update position size from exchange balance"
                                )
                                self.current_report.add_discrepancy(discrepancy)
                        
                        self.current_report.strategies_checked.add(db_position.strategy_id)
                    
                    else:
                        # Position currency not found on exchange
                        discrepancy = StateDiscrepancy(
                            type=DiscrepancyType.MISSING_POSITION,
                            severity=ReconciliationSeverity.HIGH,
                            description=f"Position {db_position.symbol} not found on exchange",
                            system_state={
                                'position_id': db_position.id,
                                'symbol': db_position.symbol,
                                'size': float(db_position.current_size)
                            },
                            exchange_state={'message': 'Position not found'},
                            strategy_id=db_position.strategy_id,
                            symbol=db_position.symbol,
                            suggested_action="Close position in database or investigate missing exchange position"
                        )
                        self.current_report.add_discrepancy(discrepancy)
                        
        except Exception as e:
            logger.error(f"Error reconciling active positions: {e}")
            raise
    
    async def _reconcile_open_orders(self) -> None:
        """Reconcile open orders with exchange."""
        logger.info("Reconciling open orders...")
        
        try:
            # Get all pending/open orders from database
            with db_manager.get_session() as session:
                db_orders = session.query(Trade).filter(
                    Trade.status.in_(['pending', 'open'])
                ).all()
                
                # Get all open orders from exchange
                exchange_orders = await self.exchange_connector.get_open_orders()
                exchange_order_ids = {order.order_id for order in exchange_orders}
                
                # Check database orders against exchange
                for db_order in db_orders:
                    self.current_report.total_orders_checked += 1
                    
                    if db_order.exchange_order_id not in exchange_order_ids:
                        # Order exists in DB but not on exchange
                        discrepancy = StateDiscrepancy(
                            type=DiscrepancyType.MISSING_ORDER,
                            severity=ReconciliationSeverity.MEDIUM,
                            description=f"Order {db_order.exchange_order_id} exists in DB but not on exchange",
                            system_state={
                                'trade_id': db_order.id,
                                'exchange_order_id': db_order.exchange_order_id,
                                'status': db_order.status,
                                'symbol': db_order.symbol
                            },
                            exchange_state={'message': 'Order not found on exchange'},
                            strategy_id=db_order.strategy_id,
                            symbol=db_order.symbol,
                            suggested_action="Update order status to cancelled or check exchange order ID"
                        )
                        self.current_report.add_discrepancy(discrepancy)
                
                # Check for orders on exchange not in database
                db_order_ids = {order.exchange_order_id for order in db_orders}
                
                for exchange_order in exchange_orders:
                    if exchange_order.order_id not in db_order_ids:
                        # Order exists on exchange but not in DB
                        discrepancy = StateDiscrepancy(
                            type=DiscrepancyType.TRADE_RECORD_MISSING,
                            severity=ReconciliationSeverity.HIGH,
                            description=f"Exchange order {exchange_order.order_id} not found in database",
                            system_state={'message': 'Order not found in database'},
                            exchange_state={
                                'order_id': exchange_order.order_id,
                                'symbol': exchange_order.symbol,
                                'side': exchange_order.side.value,
                                'status': exchange_order.status.value
                            },
                            symbol=exchange_order.symbol,
                            suggested_action="Create trade record in database or cancel orphaned exchange order"
                        )
                        self.current_report.add_discrepancy(discrepancy)
                        
        except Exception as e:
            logger.error(f"Error reconciling open orders: {e}")
            raise
    
    async def _reconcile_strategy_states(self) -> None:
        """Reconcile strategy internal states."""
        logger.info("Reconciling strategy states...")
        
        try:
            with db_manager.get_session() as session:
                active_strategies = session.query(Strategy).filter_by(is_active=True).all()
                
                for strategy in active_strategies:
                    self.current_report.strategies_checked.add(strategy.id)
                    
                    # Check for missing performance metrics
                    latest_metric = session.query(PerformanceMetric)\
                        .filter_by(strategy_id=strategy.id)\
                        .order_by(PerformanceMetric.timestamp.desc())\
                        .first()
                    
                    if not latest_metric:
                        discrepancy = StateDiscrepancy(
                            type=DiscrepancyType.TRADE_RECORD_MISSING,
                            severity=ReconciliationSeverity.LOW,
                            description=f"Strategy {strategy.name} has no performance metrics",
                            system_state={
                                'strategy_id': strategy.id,
                                'name': strategy.name,
                                'is_active': strategy.is_active
                            },
                            exchange_state={'message': 'No metrics available'},
                            strategy_id=strategy.id,
                            suggested_action="Initialize strategy performance tracking"
                        )
                        self.current_report.add_discrepancy(discrepancy)
                    
                    # Check strategy parameters consistency
                    if not strategy.parameters:
                        discrepancy = StateDiscrepancy(
                            type=DiscrepancyType.TRADE_RECORD_MISSING,
                            severity=ReconciliationSeverity.MEDIUM,
                            description=f"Strategy {strategy.name} has no parameters configured",
                            system_state={
                                'strategy_id': strategy.id,
                                'name': strategy.name,
                                'parameters': strategy.parameters
                            },
                            exchange_state={'message': 'Parameters required'},
                            strategy_id=strategy.id,
                            suggested_action="Configure strategy parameters"
                        )
                        self.current_report.add_discrepancy(discrepancy)
                        
        except Exception as e:
            logger.error(f"Error reconciling strategy states: {e}")
            raise
    
    async def _apply_auto_corrections(self) -> None:
        """Apply automatic corrections for minor discrepancies."""
        logger.info("Applying automatic corrections...")
        
        auto_correctable = [
            d for d in self.current_report.discrepancies 
            if d.severity == ReconciliationSeverity.LOW
        ]
        
        for discrepancy in auto_correctable:
            try:
                action_taken = await self._apply_correction(discrepancy)
                if action_taken:
                    self.current_report.actions_taken.append(action_taken)
                    logger.info(f"Auto-corrected: {discrepancy.description}")
                    
            except Exception as e:
                logger.warning(f"Failed to auto-correct discrepancy: {e}")
    
    async def _apply_correction(self, discrepancy: StateDiscrepancy) -> Optional[Dict[str, Any]]:
        """Apply a specific correction for a discrepancy."""
        # For now, we'll implement basic corrections
        # More sophisticated corrections can be added later
        
        action = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'discrepancy_type': discrepancy.type.value,
            'action': 'auto_correction',
            'success': False
        }
        
        try:
            if discrepancy.type == DiscrepancyType.TRADE_RECORD_MISSING:
                # Log the discrepancy for manual review
                await self._log_system_event(
                    level="INFO",
                    message="Auto-correction: Logged missing trade record for review",
                    context=discrepancy.to_dict()
                )
                action['success'] = True
                action['details'] = "Logged for manual review"
                
            return action
            
        except Exception as e:
            action['error'] = str(e)
            logger.error(f"Error applying correction: {e}")
            return action
    
    async def _finalize_reconciliation(self) -> None:
        """Finalize reconciliation process."""
        logger.info("Finalizing reconciliation...")
        
        # Determine final status
        critical_discrepancies = self.current_report.get_critical_discrepancies()
        
        if critical_discrepancies:
            self.current_report.status = ReconciliationStatus.PARTIAL
            
            # Log critical issues
            await self._log_system_event(
                level="ERROR",
                message=f"Reconciliation found {len(critical_discrepancies)} critical discrepancies",
                context={
                    'session_id': self.current_report.session_id,
                    'critical_discrepancies': len(critical_discrepancies),
                    'total_discrepancies': len(self.current_report.discrepancies)
                }
            )
        else:
            self.current_report.status = ReconciliationStatus.COMPLETED
            
        # Add exchange info to report
        if hasattr(self.exchange_connector, 'config') and hasattr(self.exchange_connector.config, 'exchange_name'):
            self.current_report.exchanges_checked.add(self.exchange_connector.config.exchange_name)
        else:
            self.current_report.exchanges_checked.add("unknown_exchange")
    
    async def _save_reconciliation_report(self) -> None:
        """Save reconciliation report to database."""
        try:
            await self._log_system_event(
                level="INFO",
                message="State reconciliation completed",
                context=self.current_report.to_summary()
            )
            
            logger.info(f"Reconciliation report saved (session: {self.current_report.session_id})")
            
        except Exception as e:
            logger.error(f"Error saving reconciliation report: {e}")
    
    async def _log_system_event(self, level: str, message: str, context: Dict[str, Any]) -> None:
        """Log system event to database."""
        try:
            with db_manager.get_session() as session:
                log_entry = SystemLog(
                    level=level,
                    logger_name="StateReconciliation",
                    message=message,
                    context=context
                )
                session.add(log_entry)
                session.commit()
                
        except Exception as e:
            logger.error(f"Error logging system event: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on reconciliation engine."""
        exchange_connected = False
        if hasattr(self.exchange_connector, 'is_connected'):
            exchange_connected = self.exchange_connector.is_connected
        
        capital_manager_ready = False
        if hasattr(self.capital_manager, 'is_running'):
            capital_manager_ready = self.capital_manager.is_running
        
        return {
            'reconciliation_engine_ready': True,
            'exchange_connected': exchange_connected,
            'capital_manager_ready': capital_manager_ready,
            'auto_correct_enabled': self.auto_correct,
            'last_reconciliation': (
                self.current_report.end_time.isoformat() 
                if self.current_report and self.current_report.end_time 
                else None
            ),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }