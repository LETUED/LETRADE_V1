"""add performance indexes

Revision ID: 003
Revises: 002
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    """성능 최적화를 위한 인덱스 추가"""
    
    # trades 테이블 인덱스
    op.create_index(
        'idx_trades_strategy_created',
        'trades',
        ['strategy_id', 'created_at'],
        postgresql_where=sa.text("status IN ('filled', 'partial')")
    )
    
    op.create_index(
        'idx_trades_portfolio_symbol_created',
        'trades',
        ['portfolio_id', 'symbol', 'created_at']
    )
    
    op.create_index(
        'idx_trades_executed_at',
        'trades',
        ['executed_at'],
        postgresql_where=sa.text("executed_at IS NOT NULL")
    )
    
    # positions 테이블 인덱스
    op.create_index(
        'idx_positions_portfolio_open',
        'positions',
        ['portfolio_id', 'is_open'],
        postgresql_where=sa.text("is_open = TRUE")
    )
    
    op.create_index(
        'idx_positions_symbol_open',
        'positions',
        ['symbol', 'is_open'],
        postgresql_where=sa.text("is_open = TRUE")
    )
    
    op.create_index(
        'idx_positions_strategy_open',
        'positions',
        ['strategy_id', 'is_open'],
        postgresql_where=sa.text("is_open = TRUE")
    )
    
    # performance_metrics 테이블 인덱스
    op.create_index(
        'idx_performance_metrics_strategy_name_created',
        'performance_metrics',
        ['strategy_id', 'metric_name', 'created_at']
    )
    
    op.create_index(
        'idx_performance_metrics_created_desc',
        'performance_metrics',
        [sa.text('created_at DESC')]
    )
    
    # system_logs 테이블 인덱스
    op.create_index(
        'idx_system_logs_level_created',
        'system_logs',
        ['log_level', 'created_at'],
        postgresql_where=sa.text("log_level IN ('ERROR', 'WARNING')")
    )
    
    op.create_index(
        'idx_system_logs_component_created',
        'system_logs',
        ['component', 'created_at']
    )
    
    # strategies 테이블 인덱스
    op.create_index(
        'idx_strategies_portfolio_active',
        'strategies',
        ['portfolio_id', 'is_active'],
        postgresql_where=sa.text("is_active = TRUE")
    )
    
    # portfolio_rules 테이블 인덱스
    op.create_index(
        'idx_portfolio_rules_portfolio_active',
        'portfolio_rules',
        ['portfolio_id', 'is_active'],
        postgresql_where=sa.text("is_active = TRUE")
    )
    
    # 복합 인덱스 (조인 최적화)
    op.create_index(
        'idx_trades_strategy_portfolio',
        'trades',
        ['strategy_id', 'portfolio_id']
    )
    
    op.create_index(
        'idx_positions_portfolio_strategy',
        'positions',
        ['portfolio_id', 'strategy_id']
    )


def downgrade():
    """인덱스 제거"""
    # trades 인덱스 제거
    op.drop_index('idx_trades_strategy_created', 'trades')
    op.drop_index('idx_trades_portfolio_symbol_created', 'trades')
    op.drop_index('idx_trades_executed_at', 'trades')
    op.drop_index('idx_trades_strategy_portfolio', 'trades')
    
    # positions 인덱스 제거
    op.drop_index('idx_positions_portfolio_open', 'positions')
    op.drop_index('idx_positions_symbol_open', 'positions')
    op.drop_index('idx_positions_strategy_open', 'positions')
    op.drop_index('idx_positions_portfolio_strategy', 'positions')
    
    # performance_metrics 인덱스 제거
    op.drop_index('idx_performance_metrics_strategy_name_created', 'performance_metrics')
    op.drop_index('idx_performance_metrics_created_desc', 'performance_metrics')
    
    # system_logs 인덱스 제거
    op.drop_index('idx_system_logs_level_created', 'system_logs')
    op.drop_index('idx_system_logs_component_created', 'system_logs')
    
    # strategies 인덱스 제거
    op.drop_index('idx_strategies_portfolio_active', 'strategies')
    
    # portfolio_rules 인덱스 제거
    op.drop_index('idx_portfolio_rules_portfolio_active', 'portfolio_rules')