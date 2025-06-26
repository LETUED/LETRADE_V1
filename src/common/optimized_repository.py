"""
최적화된 데이터베이스 Repository
캐싱과 배치 처리를 통한 성능 향상
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Union, Type
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from src.common.models import (
    Portfolio, Strategy, Trade, Position,
    PerformanceMetric, SystemLog
)
from src.common.cache_manager import CacheManager, cached

logger = logging.getLogger(__name__)


class OptimizedRepository:
    """최적화된 데이터베이스 Repository"""
    
    def __init__(self, session: AsyncSession, cache_manager: CacheManager):
        self.session = session
        self.cache_manager = cache_manager
        
    @cached(ttl=300)  # 5분 캐시
    async def get_portfolio_metrics(self, portfolio_id: int) -> Dict[str, Any]:
        """포트폴리오 메트릭스 조회 (캐시됨)"""
        # 포트폴리오 기본 정보
        portfolio = await self.session.get(Portfolio, portfolio_id)
        if not portfolio:
            return None
            
        # 오픈 포지션 집계
        open_positions_query = select(
            func.count(Position.id).label('count'),
            func.sum(Position.size * Position.current_price).label('total_value'),
            func.sum(Position.unrealized_pnl).label('unrealized_pnl')
        ).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.is_open == True
            )
        )
        
        result = await self.session.execute(open_positions_query)
        position_stats = result.one()
        
        # 오늘 실현 손익
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        today_pnl_query = select(
            func.sum(Trade.realized_pnl)
        ).where(
            and_(
                Trade.portfolio_id == portfolio_id,
                Trade.executed_at >= today_start,
                Trade.status == 'filled'
            )
        )
        
        result = await self.session.execute(today_pnl_query)
        today_pnl = result.scalar() or 0
        
        return {
            'portfolio_id': portfolio_id,
            'total_value': float(portfolio.total_capital),
            'available_cash': float(portfolio.available_capital),
            'open_positions_count': position_stats.count or 0,
            'positions_value': float(position_stats.total_value or 0),
            'unrealized_pnl': float(position_stats.unrealized_pnl or 0),
            'realized_pnl_today': float(today_pnl),
            'last_updated': datetime.now()
        }
    
    @cached(ttl=60)  # 1분 캐시
    async def get_active_strategies(self, portfolio_id: int) -> List[Strategy]:
        """활성 전략 목록 조회 (캐시됨)"""
        query = select(Strategy).where(
            and_(
                Strategy.portfolio_id == portfolio_id,
                Strategy.is_active == True
            )
        ).options(
            selectinload(Strategy.trades)  # 관련 거래 미리 로드
        )
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def batch_insert_trades(self, trades: List[Trade]) -> bool:
        """거래 배치 삽입"""
        try:
            self.session.add_all(trades)
            await self.session.commit()
            
            # 캐시 무효화
            for trade in trades:
                cache_key = self.cache_manager.cache_key(
                    "portfolio_metrics",
                    trade.portfolio_id
                )
                await self.cache_manager.delete(cache_key)
            
            return True
            
        except Exception as e:
            logger.error(f"Batch insert trades failed: {e}")
            await self.session.rollback()
            return False
    
    async def get_recent_trades(
        self,
        portfolio_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> List[Trade]:
        """최근 거래 조회 (페이지네이션)"""
        # 캐시 키
        cache_key = self.cache_manager.cache_key(
            "recent_trades",
            portfolio_id,
            limit=limit,
            offset=offset
        )
        
        # 캐시 확인
        cached_result = await self.cache_manager.get(cache_key)
        if cached_result:
            return cached_result
        
        # DB 조회
        query = select(Trade).where(
            Trade.portfolio_id == portfolio_id
        ).order_by(
            Trade.created_at.desc()
        ).limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        trades = result.scalars().all()
        
        # 캐시 저장 (30초)
        await self.cache_manager.set(cache_key, trades, ttl=30)
        
        return trades
    
    async def update_position_batch(
        self,
        position_updates: List[Dict[str, Any]]
    ) -> int:
        """포지션 배치 업데이트"""
        updated_count = 0
        
        try:
            for update_data in position_updates:
                position_id = update_data.pop('id')
                
                stmt = update(Position).where(
                    Position.id == position_id
                ).values(**update_data)
                
                result = await self.session.execute(stmt)
                updated_count += result.rowcount
            
            await self.session.commit()
            
            # 관련 캐시 무효화
            portfolio_ids = set()
            for update_data in position_updates:
                position = await self.session.get(Position, update_data.get('id'))
                if position:
                    portfolio_ids.add(position.portfolio_id)
            
            for portfolio_id in portfolio_ids:
                cache_key = self.cache_manager.cache_key(
                    "portfolio_metrics",
                    portfolio_id
                )
                await self.cache_manager.delete(cache_key)
            
            return updated_count
            
        except Exception as e:
            logger.error(f"Batch update positions failed: {e}")
            await self.session.rollback()
            return 0
    
    @cached(ttl=3600)  # 1시간 캐시
    async def get_performance_summary(
        self,
        strategy_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """전략 성능 요약 (캐시됨)"""
        start_date = datetime.now() - timedelta(days=days)
        
        # 거래 통계
        trade_stats_query = select(
            func.count(Trade.id).label('total_trades'),
            func.sum(case((Trade.realized_pnl > 0, 1), else_=0)).label('winning_trades'),
            func.sum(Trade.realized_pnl).label('total_pnl'),
            func.avg(Trade.realized_pnl).label('avg_pnl'),
            func.max(Trade.realized_pnl).label('max_profit'),
            func.min(Trade.realized_pnl).label('max_loss')
        ).where(
            and_(
                Trade.strategy_id == strategy_id,
                Trade.executed_at >= start_date,
                Trade.status == 'filled'
            )
        )
        
        result = await self.session.execute(trade_stats_query)
        stats = result.one()
        
        # 승률 계산
        win_rate = 0
        if stats.total_trades > 0:
            win_rate = (stats.winning_trades / stats.total_trades) * 100
        
        return {
            'strategy_id': strategy_id,
            'period_days': days,
            'total_trades': stats.total_trades or 0,
            'winning_trades': stats.winning_trades or 0,
            'win_rate': round(win_rate, 2),
            'total_pnl': float(stats.total_pnl or 0),
            'avg_pnl': float(stats.avg_pnl or 0),
            'max_profit': float(stats.max_profit or 0),
            'max_loss': float(stats.max_loss or 0),
            'last_updated': datetime.now()
        }
    
    async def log_system_event_batch(
        self,
        events: List[Dict[str, Any]]
    ) -> bool:
        """시스템 이벤트 배치 로깅"""
        try:
            logs = [
                SystemLog(
                    log_level=event.get('level', 'INFO'),
                    component=event.get('component', 'unknown'),
                    message=event.get('message', ''),
                    details=event.get('details', {})
                )
                for event in events
            ]
            
            self.session.add_all(logs)
            await self.session.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Batch log system events failed: {e}")
            await self.session.rollback()
            return False
    
    async def cleanup_old_data(self, days_to_keep: int = 30) -> Dict[str, int]:
        """오래된 데이터 정리"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        deleted_counts = {}
        
        try:
            # 오래된 로그 삭제
            stmt = delete(SystemLog).where(
                SystemLog.created_at < cutoff_date
            )
            result = await self.session.execute(stmt)
            deleted_counts['system_logs'] = result.rowcount
            
            # 오래된 성능 메트릭 삭제
            stmt = delete(PerformanceMetric).where(
                PerformanceMetric.created_at < cutoff_date
            )
            result = await self.session.execute(stmt)
            deleted_counts['performance_metrics'] = result.rowcount
            
            await self.session.commit()
            
            logger.info(f"Cleaned up old data: {deleted_counts}")
            return deleted_counts
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            await self.session.rollback()
            return {}
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 조회"""
        return self.cache_manager.get_stats()


class RepositoryFactory:
    """Repository 팩토리"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
    
    def create(self, session: AsyncSession) -> OptimizedRepository:
        """Repository 인스턴스 생성"""
        return OptimizedRepository(session, self.cache_manager)