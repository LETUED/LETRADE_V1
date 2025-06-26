#!/usr/bin/env python3
"""
MA 전략 백테스트 실행 스크립트

이 스크립트는 MA Crossover 전략의 백테스트를 실행하고 
성능 메트릭을 계산하여 결과를 분석합니다.
"""

import asyncio
import logging
import os
import sys
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


class BacktestEngine:
    """백테스트 엔진"""
    
    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.position = 0.0  # 현재 포지션 (BTC 수량)
        self.trades = []
        self.equity_curve = []
        
    def execute_signal(self, signal: Dict[str, Any], price: float, timestamp: str):
        """거래 신호 실행"""
        side = signal.get('side')
        confidence = signal.get('confidence', 1.0)
        
        # 포지션 크기 계산 (confidence 기반)
        position_size = self.capital * 0.1 * confidence  # 자본의 10% * 신뢰도
        
        if side == 'buy' and self.position == 0:
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
            
            logger.info(f"매수 진입: {shares:.6f} BTC @ ${price:.2f}")
            
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
            
            logger.info(f"매도 청산: {self.position:.6f} BTC @ ${price:.2f}")
            self.position = 0.0
        
        # 포트폴리오 가치 계산
        portfolio_value = self.capital + (self.position * price)
        self.equity_curve.append({
            'timestamp': timestamp,
            'capital': self.capital,
            'position_value': self.position * price,
            'total_value': portfolio_value,
            'price': price
        })
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """백테스트 성능 메트릭 계산"""
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
        for i, buy_trade in enumerate(buy_trades):
            if i < len(sell_trades):
                sell_trade = sell_trades[i]
                pnl = sell_trade['value'] - buy_trade['value']
                pnl_pct = pnl / buy_trade['value']
                
                completed_trades.append({
                    'buy_price': buy_trade['price'],
                    'sell_price': sell_trade['price'],
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'holding_period': sell_trade['timestamp']
                })
        
        # 승률 계산
        winning_trades = [t for t in completed_trades if t['pnl'] > 0]
        win_rate = len(winning_trades) / len(completed_trades) if completed_trades else 0
        
        # 평균 수익/손실
        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl'] for t in completed_trades if t['pnl'] < 0])
        if np.isnan(avg_loss):
            avg_loss = 0
        
        # 최대 드로우다운 계산
        equity_values = [point['total_value'] for point in self.equity_curve]
        peak = np.maximum.accumulate(equity_values)
        drawdown = (peak - equity_values) / peak
        max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
        
        return {
            'initial_capital': self.initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'total_return_pct': total_return * 100,
            'total_trades': len(self.trades),
            'completed_trades': len(completed_trades),
            'win_rate': win_rate,
            'win_rate_pct': win_rate * 100,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else float('inf'),
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown * 100,
            'final_position': self.position,
            'trades': self.trades,
            'completed_trades': completed_trades,
            'equity_curve': self.equity_curve
        }


async def run_backtest_scenario(
    strategy_config: StrategyConfig,
    data_config: DataSourceConfig,
    scenario_name: str
) -> Dict[str, Any]:
    """백테스트 시나리오 실행"""
    logger.info(f"백테스트 시나리오 시작: {scenario_name}")
    
    # 데이터 로드
    data_loader = BacktestDataLoader(data_config)
    historical_data = await data_loader.load_data()
    
    if historical_data.empty:
        logger.error(f"데이터 로드 실패: {scenario_name}")
        return {"error": "No data loaded"}
    
    logger.info(f"데이터 로드 완료: {len(historical_data)} 개 데이터 포인트")
    
    # 전략 초기화
    strategy = MAcrossoverStrategy(strategy_config)
    
    # 지표 계산
    df_with_indicators = strategy.populate_indicators(historical_data)
    
    # 백테스트 엔진 초기화
    backtest_engine = BacktestEngine(initial_capital=10000.0)
    
    # 백테스트 실행
    signals_generated = 0
    
    # 충분한 데이터가 있는 구간부터 시작
    start_idx = max(strategy_config.custom_params.get('slow_period', 20), 20)
    
    for i in range(start_idx, len(df_with_indicators)):
        current_data = df_with_indicators.iloc[:i+1]
        
        # 현재 시점의 시장 데이터
        market_data = {
            'close': current_data['close'].iloc[-1],
            'timestamp': current_data.index[-1].isoformat()
        }
        
        # 신호 생성
        signal = strategy.on_data(market_data, current_data)
        
        if signal:
            signals_generated += 1
            # 신호 실행
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
        'min_crossover_strength': strategy_config.custom_params.get('min_crossover_strength')
    }
    
    logger.info(f"백테스트 완료: {scenario_name}")
    logger.info(f"총 수익률: {performance.get('total_return_pct', 0):.2f}%")
    logger.info(f"승률: {performance.get('win_rate_pct', 0):.2f}%")
    logger.info(f"생성된 신호: {signals_generated}개")
    
    return performance


async def main():
    """메인 백테스트 실행 함수"""
    logger.info("=" * 60)
    logger.info("🚀 MA Crossover 전략 백테스트 시작")
    logger.info("=" * 60)
    
    # 백테스트 시나리오 정의
    scenarios = [
        # 시나리오 1: 표준 MA 50/200 (트렌드 데이터)
        {
            'name': 'Standard_MA_50_200_Trending',
            'strategy_config': StrategyConfig(
                strategy_id="backtest_ma_50_200",
                name="Standard MA 50/200",
                enabled=True,
                dry_run=True,
                custom_params={
                    "fast_period": 50,
                    "slow_period": 200,
                    "symbol": "BTC/USDT",
                    "exchange": "binance",
                    "min_signal_interval": 3600,  # 1시간
                    "min_crossover_strength": 0.1  # 0.1%
                }
            ),
            'data_config': DataSourceConfig(
                source_type='mock',
                symbol='BTC/USDT',
                timeframe='1h',
                mock_config={
                    'num_periods': 500,
                    'base_price': 45000.0,
                    'volatility': 0.03,
                    'add_trends': True,
                    'trend_probability': 0.7
                }
            )
        },
        
        # 시나리오 2: 빠른 MA 10/30 (고빈도)
        {
            'name': 'Fast_MA_10_30_HighFreq',
            'strategy_config': StrategyConfig(
                strategy_id="backtest_ma_10_30",
                name="Fast MA 10/30",
                enabled=True,
                dry_run=True,
                custom_params={
                    "fast_period": 10,
                    "slow_period": 30,
                    "symbol": "BTC/USDT",
                    "exchange": "binance",
                    "min_signal_interval": 1800,  # 30분
                    "min_crossover_strength": 0.1  # 0.1%
                }
            ),
            'data_config': DataSourceConfig(
                source_type='mock',
                symbol='BTC/USDT',
                timeframe='15m',
                mock_config={
                    'num_periods': 1000,
                    'base_price': 50000.0,
                    'volatility': 0.02,
                    'add_trends': True,
                    'trend_probability': 0.5
                }
            )
        },
        
        # 시나리오 3: 느린 MA 100/300 (장기 트렌드)
        {
            'name': 'Slow_MA_100_300_LongTerm',
            'strategy_config': StrategyConfig(
                strategy_id="backtest_ma_100_300",
                name="Slow MA 100/300",
                enabled=True,
                dry_run=True,
                custom_params={
                    "fast_period": 100,
                    "slow_period": 300,
                    "symbol": "BTC/USDT",
                    "exchange": "binance",
                    "min_signal_interval": 7200,  # 2시간
                    "min_crossover_strength": 0.3  # 0.3%
                }
            ),
            'data_config': DataSourceConfig(
                source_type='mock',
                symbol='BTC/USDT',
                timeframe='4h',
                mock_config={
                    'num_periods': 800,
                    'base_price': 48000.0,
                    'volatility': 0.04,
                    'add_trends': True,
                    'trend_probability': 0.8
                }
            )
        },
        
        # 시나리오 4: 횡보장 테스트
        {
            'name': 'Sideways_Market_Test',
            'strategy_config': StrategyConfig(
                strategy_id="backtest_ma_sideways",
                name="Sideways Market MA Test",
                enabled=True,
                dry_run=True,
                custom_params={
                    "fast_period": 20,
                    "slow_period": 50,
                    "symbol": "BTC/USDT",
                    "exchange": "binance",
                    "min_signal_interval": 3600,
                    "min_crossover_strength": 0.1
                }
            ),
            'data_config': DataSourceConfig(
                source_type='mock',
                symbol='BTC/USDT',
                timeframe='1h',
                mock_config={
                    'num_periods': 600,
                    'base_price': 47000.0,
                    'volatility': 0.015,
                    'add_trends': False,  # 횡보장
                    'trend_probability': 0.1
                }
            )
        }
    ]
    
    # 모든 시나리오 실행
    results = []
    
    for scenario in scenarios:
        try:
            result = await run_backtest_scenario(
                strategy_config=scenario['strategy_config'],
                data_config=scenario['data_config'],
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
    logger.info("\n" + "=" * 60)
    logger.info("📊 백테스트 결과 요약")
    logger.info("=" * 60)
    
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
        logger.info(f"   생성된 신호: {result.get('signals_generated', 0)}")
        
        if result.get('profit_factor', 0) != float('inf'):
            logger.info(f"   수익 팩터: {result.get('profit_factor', 0):.2f}")
    
    # 최고 성과 시나리오 찾기
    valid_results = [r for r in results if 'error' not in r and r.get('total_return_pct', 0) is not None]
    
    if valid_results:
        best_result = max(valid_results, key=lambda x: x.get('total_return_pct', 0))
        logger.info(f"\n🏆 최고 성과 시나리오: {best_result['scenario_name']}")
        logger.info(f"   수익률: {best_result.get('total_return_pct', 0):.2f}%")
        
        # 전략 파라미터 분석
        logger.info(f"\n📈 최적 전략 파라미터:")
        strategy_config = best_result.get('strategy_config', {})
        logger.info(f"   Fast Period: {strategy_config.get('fast_period')}")
        logger.info(f"   Slow Period: {strategy_config.get('slow_period')}")
        logger.info(f"   Min Crossover Strength: {strategy_config.get('min_crossover_strength')}%")
    
    # 결과를 파일로 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"/Users/jeondonghwan/Letrade_v1/backtest_results_{timestamp}.json"
    
    import json
    try:
        # JSON 직렬화 가능하도록 결과 정리
        serializable_results = []
        for result in results:
            clean_result = {}
            for key, value in result.items():
                if key in ['trades', 'completed_trades', 'equity_curve']:
                    # 리스트 데이터는 길이만 저장
                    clean_result[f"{key}_count"] = len(value) if isinstance(value, list) else 0
                elif isinstance(value, (int, float, str, bool, type(None))):
                    clean_result[key] = value
                elif isinstance(value, dict):
                    clean_result[key] = value
        
        serializable_results.append(clean_result)
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n💾 백테스트 결과 저장: {results_file}")
        
    except Exception as e:
        logger.error(f"결과 저장 실패: {e}")
    
    logger.info("\n" + "=" * 60)
    logger.info("🏁 백테스트 완료")
    logger.info("=" * 60)
    
    return results


if __name__ == "__main__":
    asyncio.run(main())