#!/usr/bin/env python3
"""
개선된 MA 전략 백테스트

더 현실적인 시나리오와 완전한 거래 사이클을 포함한 백테스트
"""

import asyncio
import logging
import os
import sys
import json
from datetime import datetime, timezone
from typing import Dict, List, Any

import pandas as pd
import numpy as np

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.strategies.ma_crossover import MAcrossoverStrategy
from src.strategies.base_strategy import StrategyConfig
from src.data_loader.backtest_data_loader import BacktestDataLoader, DataSourceConfig

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedBacktestEngine:
    """향상된 백테스트 엔진"""
    
    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.position = 0.0
        self.trades = []
        self.equity_curve = []
        self.max_portfolio_value = initial_capital
        
    def execute_signal(self, signal: Dict[str, Any], price: float, timestamp: str):
        """거래 신호 실행 (개선된 로직)"""
        side = signal.get('side')
        confidence = signal.get('confidence', 1.0)
        
        # 포지션 크기 계산 (confidence 기반, 더 공격적)
        position_size = self.capital * 0.2 * confidence  # 자본의 20% * 신뢰도
        
        if side == 'buy' and self.position == 0 and self.capital > position_size:
            # 매수 진입
            shares = position_size / price
            self.position = shares
            self.capital -= position_size
            
            self.trades.append({
                'timestamp': timestamp,
                'side': 'buy',
                'price': price,
                'quantity': shares,
                'value': position_size,
                'confidence': confidence,
                'capital_after': self.capital
            })
            
            logger.info(f"📈 매수 진입: {shares:.6f} BTC @ ${price:.2f} (신뢰도: {confidence:.3f})")
            
        elif side == 'sell' and self.position > 0:
            # 매도 청산
            sell_value = self.position * price
            self.capital += sell_value
            
            self.trades.append({
                'timestamp': timestamp,
                'side': 'sell',
                'price': price,
                'quantity': self.position,
                'value': sell_value,
                'confidence': confidence,
                'capital_after': self.capital
            })
            
            logger.info(f"📉 매도 청산: {self.position:.6f} BTC @ ${price:.2f} (신뢰도: {confidence:.3f})")
            self.position = 0.0
        
        # 포트폴리오 가치 추적
        portfolio_value = self.capital + (self.position * price)
        self.max_portfolio_value = max(self.max_portfolio_value, portfolio_value)
        
        self.equity_curve.append({
            'timestamp': timestamp,
            'capital': self.capital,
            'position_value': self.position * price,
            'total_value': portfolio_value,
            'price': price
        })
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """성능 메트릭 계산 (개선된 버전)"""
        if not self.trades:
            return {"error": "No trades executed"}
        
        # 최종 포트폴리오 가치
        final_price = self.equity_curve[-1]['price'] if self.equity_curve else 0
        final_value = self.capital + (self.position * final_price)
        
        # 수익률 계산
        total_return = (final_value - self.initial_capital) / self.initial_capital
        
        # 거래 분석
        buy_trades = [t for t in self.trades if t['side'] == 'buy']
        sell_trades = [t for t in self.trades if t['side'] == 'sell']
        
        # 완료된 거래 쌍 분석
        completed_trades = []
        for i in range(min(len(buy_trades), len(sell_trades))):
            buy_trade = buy_trades[i]
            sell_trade = sell_trades[i]
            
            pnl = sell_trade['value'] - buy_trade['value']
            pnl_pct = pnl / buy_trade['value']
            
            completed_trades.append({
                'buy_price': buy_trade['price'],
                'sell_price': sell_trade['price'],
                'buy_time': buy_trade['timestamp'],
                'sell_time': sell_trade['timestamp'],
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'quantity': buy_trade['quantity']
            })
        
        # 통계 계산
        winning_trades = [t for t in completed_trades if t['pnl'] > 0]
        losing_trades = [t for t in completed_trades if t['pnl'] < 0]
        
        win_rate = len(winning_trades) / len(completed_trades) if completed_trades else 0
        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
        
        # 최대 드로우다운 계산
        equity_values = [point['total_value'] for point in self.equity_curve]
        peak = np.maximum.accumulate(equity_values)
        drawdown = (peak - equity_values) / peak
        max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
        
        # 샤프 비율 계산 (단순화된 버전)
        if len(equity_values) > 1:
            returns = np.diff(equity_values) / equity_values[:-1]
            sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        else:
            sharpe_ratio = 0
        
        return {
            'initial_capital': self.initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'total_return_pct': total_return * 100,
            'total_trades': len(self.trades),
            'buy_trades': len(buy_trades),
            'sell_trades': len(sell_trades),
            'completed_trades': len(completed_trades),
            'open_position_value': self.position * final_price,
            'win_rate': win_rate,
            'win_rate_pct': win_rate * 100,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else float('inf'),
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown * 100,
            'sharpe_ratio': sharpe_ratio,
            'final_position_btc': self.position,
            'trades_detail': completed_trades[:5],  # 처음 5개 거래만 표시
            'total_completed_trades': completed_trades
        }


def create_realistic_crypto_data(periods: int, base_price: float = 45000) -> pd.DataFrame:
    """현실적인 암호화폐 가격 데이터 생성"""
    np.random.seed(42)  # 재현 가능한 결과를 위해
    
    prices = [base_price]
    
    # 트렌드 구간별로 나누어 생성
    trend_length = periods // 4
    
    for phase in range(4):
        if phase == 0:  # 하락 트렌드
            trend = -0.002
            volatility = 0.03
        elif phase == 1:  # 횡보
            trend = 0.0001
            volatility = 0.02
        elif phase == 2:  # 상승 트렌드
            trend = 0.003
            volatility = 0.025
        else:  # 조정
            trend = -0.001
            volatility = 0.035
        
        for i in range(trend_length):
            # 가격 변화 = 트렌드 + 랜덤 변동
            change = trend + np.random.normal(0, volatility)
            new_price = prices[-1] * (1 + change)
            prices.append(max(new_price, base_price * 0.5))  # 최소 가격 제한
    
    # 남은 기간 채우기
    while len(prices) < periods + 1:
        change = np.random.normal(0, 0.02)
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, base_price * 0.5))
    
    prices = prices[:periods]
    
    # 날짜 생성
    dates = pd.date_range('2024-01-01', periods=len(prices), freq='1h')
    
    # OHLCV 데이터 생성
    df = pd.DataFrame({
        'open': [p * (1 + np.random.normal(0, 0.001)) for p in prices],
        'high': [p * (1 + abs(np.random.normal(0, 0.002))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.002))) for p in prices],
        'close': prices,
        'volume': [1000 + np.random.randint(0, 500) for _ in prices]
    }, index=dates)
    
    # high >= close >= low 확인
    df['high'] = np.maximum(df['high'], df['close'])
    df['low'] = np.minimum(df['low'], df['close'])
    
    return df


async def run_enhanced_backtest_scenario(
    strategy_config: StrategyConfig,
    test_data: pd.DataFrame,
    scenario_name: str
) -> Dict[str, Any]:
    """향상된 백테스트 시나리오 실행"""
    logger.info(f"🚀 백테스트 시나리오 시작: {scenario_name}")
    
    # 전략 초기화
    strategy = MAcrossoverStrategy(strategy_config)
    
    # 지표 계산
    df_with_indicators = strategy.populate_indicators(test_data)
    
    # 백테스트 엔진 초기화
    backtest_engine = EnhancedBacktestEngine(initial_capital=10000.0)
    
    # 백테스트 실행
    signals_generated = 0
    start_idx = max(strategy_config.custom_params.get('slow_period', 20), 20)
    
    for i in range(start_idx, len(df_with_indicators)):
        current_data = df_with_indicators.iloc[:i+1]
        
        market_data = {
            'close': current_data['close'].iloc[-1],
            'timestamp': current_data.index[-1].isoformat()
        }
        
        # 신호 생성
        signal = strategy.on_data(market_data, current_data)
        
        if signal:
            signals_generated += 1
            backtest_engine.execute_signal(
                signal=signal['payload'],
                price=market_data['close'],
                timestamp=market_data['timestamp']
            )
        else:
            # 신호가 없어도 포트폴리오 가치 추적
            portfolio_value = backtest_engine.capital + (backtest_engine.position * market_data['close'])
            backtest_engine.equity_curve.append({
                'timestamp': market_data['timestamp'],
                'capital': backtest_engine.capital,
                'position_value': backtest_engine.position * market_data['close'],
                'total_value': portfolio_value,
                'price': market_data['close']
            })
    
    # 성능 메트릭 계산
    performance = backtest_engine.get_performance_metrics()
    performance['scenario_name'] = scenario_name
    performance['signals_generated'] = signals_generated
    performance['data_points'] = len(df_with_indicators)
    performance['strategy_config'] = {
        'fast_period': strategy_config.custom_params.get('fast_period'),
        'slow_period': strategy_config.custom_params.get('slow_period'),
        'min_crossover_strength': strategy_config.custom_params.get('min_crossover_strength'),
        'min_signal_interval': strategy_config.custom_params.get('min_signal_interval')
    }
    
    logger.info(f"✅ 백테스트 완료: {scenario_name}")
    logger.info(f"   총 수익률: {performance.get('total_return_pct', 0):.2f}%")
    logger.info(f"   완료된 거래: {performance.get('completed_trades', 0)}개")
    logger.info(f"   승률: {performance.get('win_rate_pct', 0):.2f}%")
    logger.info(f"   생성된 신호: {signals_generated}개")
    
    return performance


async def main():
    """메인 백테스트 실행 함수"""
    logger.info("=" * 70)
    logger.info("🚀 향상된 MA Crossover 전략 백테스트")
    logger.info("=" * 70)
    
    # 현실적인 테스트 데이터 생성
    logger.info("📊 현실적인 암호화폐 데이터 생성 중...")
    test_data = create_realistic_crypto_data(periods=1000, base_price=45000)
    logger.info(f"   데이터 기간: {test_data.index[0]} ~ {test_data.index[-1]}")
    logger.info(f"   가격 범위: ${test_data['close'].min():.2f} ~ ${test_data['close'].max():.2f}")
    
    # 백테스트 시나리오들
    scenarios = [
        {
            'name': 'MA_5_20_High_Freq',
            'config': StrategyConfig(
                strategy_id="enhanced_ma_5_20",
                name="High Frequency MA 5/20",
                enabled=True,
                dry_run=True,
                custom_params={
                    "fast_period": 5,
                    "slow_period": 20,
                    "symbol": "BTC/USDT",
                    "exchange": "binance",
                    "min_signal_interval": 0,  # 신호 간격 제한 없음
                    "min_crossover_strength": 0.1
                }
            )
        },
        {
            'name': 'MA_10_50_Medium_Freq',
            'config': StrategyConfig(
                strategy_id="enhanced_ma_10_50",
                name="Medium Frequency MA 10/50",
                enabled=True,
                dry_run=True,
                custom_params={
                    "fast_period": 10,
                    "slow_period": 50,
                    "symbol": "BTC/USDT",
                    "exchange": "binance",
                    "min_signal_interval": 0,
                    "min_crossover_strength": 0.2
                }
            )
        },
        {
            'name': 'MA_20_100_Low_Freq',
            'config': StrategyConfig(
                strategy_id="enhanced_ma_20_100",
                name="Low Frequency MA 20/100",
                enabled=True,
                dry_run=True,
                custom_params={
                    "fast_period": 20,
                    "slow_period": 100,
                    "symbol": "BTC/USDT",
                    "exchange": "binance",
                    "min_signal_interval": 0,
                    "min_crossover_strength": 0.3
                }
            )
        }
    ]
    
    # 모든 시나리오 실행
    results = []
    
    for scenario in scenarios:
        try:
            result = await run_enhanced_backtest_scenario(
                strategy_config=scenario['config'],
                test_data=test_data,
                scenario_name=scenario['name']
            )
            results.append(result)
            
        except Exception as e:
            logger.error(f"시나리오 실행 실패 {scenario['name']}: {e}")
            results.append({
                'scenario_name': scenario['name'],
                'error': str(e)
            })
    
    # 결과 요약
    logger.info("\n" + "=" * 70)
    logger.info("📊 향상된 백테스트 결과 요약")
    logger.info("=" * 70)
    
    for result in results:
        if 'error' in result:
            logger.error(f"❌ {result['scenario_name']}: {result['error']}")
            continue
        
        logger.info(f"\n🎯 {result['scenario_name']}")
        logger.info(f"   총 수익률: {result.get('total_return_pct', 0):.2f}%")
        logger.info(f"   총 거래 수: {result.get('total_trades', 0)}")
        logger.info(f"   완료된 거래: {result.get('completed_trades', 0)}")
        logger.info(f"   승률: {result.get('win_rate_pct', 0):.2f}%")
        logger.info(f"   최대 드로우다운: {result.get('max_drawdown_pct', 0):.2f}%")
        logger.info(f"   샤프 비율: {result.get('sharpe_ratio', 0):.3f}")
        logger.info(f"   생성된 신호: {result.get('signals_generated', 0)}")
        
        if result.get('completed_trades', 0) > 0:
            logger.info(f"   평균 수익: ${result.get('avg_win', 0):.2f}")
            logger.info(f"   평균 손실: ${result.get('avg_loss', 0):.2f}")
            
            if result.get('profit_factor', 0) != float('inf'):
                logger.info(f"   수익 팩터: {result.get('profit_factor', 0):.2f}")
    
    # 최고 성과 시나리오
    valid_results = [r for r in results if 'error' not in r]
    
    if valid_results:
        best_result = max(valid_results, key=lambda x: x.get('total_return_pct', -999))
        logger.info(f"\n🏆 최고 성과 시나리오: {best_result['scenario_name']}")
        logger.info(f"   수익률: {best_result.get('total_return_pct', 0):.2f}%")
        
        strategy_config = best_result.get('strategy_config', {})
        logger.info(f"\n📈 최적 전략 파라미터:")
        logger.info(f"   Fast Period: {strategy_config.get('fast_period')}")
        logger.info(f"   Slow Period: {strategy_config.get('slow_period')}")
        logger.info(f"   Min Crossover Strength: {strategy_config.get('min_crossover_strength')}%")
    
    # 결과 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"/Users/jeondonghwan/Letrade_v1/enhanced_backtest_results_{timestamp}.json"
    
    try:
        # JSON 직렬화 가능한 결과 정리
        clean_results = []
        for result in valid_results:
            clean_result = {}
            for key, value in result.items():
                if key == 'total_completed_trades':
                    clean_result[f"{key}_count"] = len(value) if isinstance(value, list) else 0
                elif isinstance(value, (int, float, str, bool, type(None))):
                    clean_result[key] = value
                elif isinstance(value, dict):
                    clean_result[key] = value
                elif isinstance(value, list) and len(value) <= 10:  # 작은 리스트만 저장
                    clean_result[key] = value
            
            clean_results.append(clean_result)
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(clean_results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n💾 백테스트 결과 저장: {results_file}")
        
    except Exception as e:
        logger.error(f"결과 저장 실패: {e}")
    
    logger.info("\n" + "=" * 70)
    logger.info("🏁 향상된 백테스트 완료")
    logger.info("=" * 70)
    
    return results


if __name__ == "__main__":
    asyncio.run(main())