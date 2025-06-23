#!/usr/bin/env python3
"""
MA 전략 디버깅 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from src.strategies.ma_crossover import MAcrossoverStrategy
from src.strategies.base_strategy import StrategyConfig

def create_test_data():
    """명확한 골든 크로스 데이터 생성"""
    # 실제 크로스오버가 발생하는 시나리오 생성
    prices = []
    
    # 긴 하락 트렌드 (확실히 단기MA < 장기MA 상태 만들기)
    base_price = 50000
    for i in range(20):
        price = base_price - (i * 150)  # 지속적인 하락
        prices.append(price)
    
    # 급격한 상승 트렌드 (골든 크로스 강제 유발)
    for i in range(20):
        price = prices[-1] + (i * 300)  # 매우 강한 상승으로 크로스오버 유발
        prices.append(price)
    
    dates = pd.date_range('2024-01-01', periods=len(prices), freq='1h')
    
    df = pd.DataFrame({
        'close': prices,
        'open': [p * 0.999 for p in prices],
        'high': [p * 1.002 for p in prices],
        'low': [p * 0.998 for p in prices],
        'volume': [1000] * len(prices)
    }, index=dates)
    
    return df

def main():
    print("🔍 MA 전략 디버깅 시작")
    
    # 전략 설정
    config = StrategyConfig(
        strategy_id="debug_ma_001",
        name="Debug MA Strategy",
        enabled=True,
        dry_run=True,
        custom_params={
            "fast_period": 5,
            "slow_period": 10,
            "symbol": "BTC/USDT",
            "exchange": "binance",
            "min_signal_interval": 0,  # 신호 간격 제한 없음
            "min_crossover_strength": 0.1  # 낮은 임계값
        }
    )
    
    # 전략 생성
    strategy = MAcrossoverStrategy(config)
    
    # 테스트 데이터 생성
    test_data = create_test_data()
    print(f"테스트 데이터 생성: {len(test_data)} 개 포인트")
    print(f"가격 범위: {test_data['close'].min():.2f} - {test_data['close'].max():.2f}")
    
    # 지표 계산
    print("\n📊 지표 계산 중...")
    df_with_indicators = strategy.populate_indicators(test_data)
    
    print(f"계산된 지표:")
    print(f"- Fast MA (5): {df_with_indicators['ma_fast'].iloc[-5:].tolist()}")
    print(f"- Slow MA (10): {df_with_indicators['ma_slow'].iloc[-5:].tolist()}")
    print(f"- Signal: {df_with_indicators['ma_signal'].iloc[-5:].tolist()}")
    print(f"- 전체 Signal 변화: {df_with_indicators['ma_signal'].tolist()}")
    
    # 마지막 몇 개 데이터포인트에서 신호 테스트
    print("\n🎯 신호 생성 테스트:")
    
    # 크로스오버 포인트 근처에서 테스트 (인덱스 22-26)
    for i in range(22, min(27, len(df_with_indicators))):
        current_data = df_with_indicators.iloc[:i+1]
        market_data = {
            'close': current_data['close'].iloc[-1],
            'timestamp': current_data.index[-1].isoformat()
        }
        
        # 디버깅 정보 출력
        if i >= 10:
            latest_row = current_data.iloc[-1]
            prev_row = current_data.iloc[-2] if len(current_data) >= 2 else None
            
            print(f"\n--- 인덱스 {i} 분석 ---")
            print(f"가격: {market_data['close']:.2f}")
            print(f"Fast MA: {latest_row.get('ma_fast', 'NaN'):.2f}")
            print(f"Slow MA: {latest_row.get('ma_slow', 'NaN'):.2f}")
            print(f"Signal: {latest_row.get('ma_signal', 'NaN')}")
            print(f"Difference %: {latest_row.get('ma_difference_pct', 'NaN'):.4f}")
            
            if prev_row is not None:
                print(f"이전 Signal: {prev_row.get('ma_signal', 'NaN')}")
                print(f"Last crossover direction: {strategy._last_crossover_direction}")
        
        signal = strategy.on_data(market_data, current_data)
        
        if signal:
            print(f"✅ 신호 생성 (인덱스 {i}):")
            print(f"   가격: {market_data['close']:.2f}")
            print(f"   신호: {signal['payload']['side']}")
            print(f"   신뢰도: {signal['payload']['confidence']:.3f}")
            print(f"   라우팅 키: {signal['routing_key']}")
        else:
            # 신호가 없는 이유 분석
            if i >= 10:  # 충분한 데이터가 있을 때만
                fast_ma = current_data['ma_fast'].iloc[-1] if not current_data['ma_fast'].isna().all() else None
                slow_ma = current_data['ma_slow'].iloc[-1] if not current_data['ma_slow'].isna().all() else None
                signal_val = current_data['ma_signal'].iloc[-1] if not current_data['ma_signal'].isna().all() else None
                
                fast_str = f"{fast_ma:.2f}" if fast_ma is not None and not pd.isna(fast_ma) else "NaN"
                slow_str = f"{slow_ma:.2f}" if slow_ma is not None and not pd.isna(slow_ma) else "NaN"
                print(f"❌ 신호 없음 (인덱스 {i}): Fast={fast_str}, Slow={slow_str}, Signal={signal_val}")
    
    print("\n✅ 디버깅 완료")

if __name__ == "__main__":
    main()