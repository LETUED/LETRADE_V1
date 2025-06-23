-- =============================================================================
-- Letrade_v1 초기 데이터베이스 스키마
-- 생성일: 2024-01-15
-- 버전: 1.0.0
-- =============================================================================

-- UUID 확장 활성화
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 시간대 설정
SET timezone = 'UTC';

-- =============================================================================
-- 1. 포트폴리오 테이블
-- =============================================================================
CREATE TABLE portfolios (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    total_capital NUMERIC(20, 8) NOT NULL CHECK (total_capital > 0),
    available_capital NUMERIC(20, 8) NOT NULL CHECK (available_capital >= 0),
    currency VARCHAR(10) NOT NULL DEFAULT 'USDT',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 포트폴리오 테이블 인덱스
CREATE INDEX idx_portfolios_is_active ON portfolios(is_active);
CREATE INDEX idx_portfolios_currency ON portfolios(currency);

-- =============================================================================
-- 2. 거래 전략 테이블  
-- =============================================================================
CREATE TABLE strategies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    strategy_type VARCHAR(50) NOT NULL DEFAULT 'MA_CROSSOVER',
    exchange VARCHAR(50) NOT NULL DEFAULT 'binance',
    symbol VARCHAR(50) NOT NULL,
    parameters JSONB DEFAULT '{"fast": 50, "slow": 200}',
    position_sizing_config JSONB DEFAULT '{"model": "fixed_fractional", "risk_percent": 0.02}',
    is_active BOOLEAN NOT NULL DEFAULT false,
    portfolio_id INTEGER REFERENCES portfolios(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- 제약 조건
    CONSTRAINT valid_strategy_type CHECK (strategy_type IN ('MA_CROSSOVER', 'MEAN_REVERSION', 'MOMENTUM', 'DCA', 'ML_BASED')),
    CONSTRAINT valid_exchange CHECK (exchange IN ('binance', 'coinbase', 'kraken', 'okx')),
    CONSTRAINT valid_symbol_format CHECK (symbol ~ '^[A-Z]{3,10}\/[A-Z]{3,10}$')
);

-- 전략 테이블 인덱스
CREATE INDEX idx_strategies_is_active ON strategies(is_active);
CREATE INDEX idx_strategies_exchange_symbol ON strategies(exchange, symbol);
CREATE INDEX idx_strategies_strategy_type ON strategies(strategy_type);
CREATE INDEX idx_strategies_portfolio_id ON strategies(portfolio_id);

-- =============================================================================
-- 3. 거래 내역 테이블
-- =============================================================================
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('buy', 'sell')),
    type VARCHAR(20) NOT NULL CHECK (type IN ('market', 'limit', 'stop_loss', 'take_profit')),
    amount DOUBLE PRECISION NOT NULL CHECK (amount > 0),
    price DOUBLE PRECISION CHECK (price > 0),
    cost DOUBLE PRECISION CHECK (cost > 0),
    fee DOUBLE PRECISION DEFAULT 0 CHECK (fee >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    exchange_order_id VARCHAR(255),
    error_message TEXT,
    timestamp_created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    timestamp_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- 제약 조건
    CONSTRAINT valid_trade_status CHECK (status IN ('pending', 'open', 'closed', 'canceled', 'failed')),
    CONSTRAINT price_required_for_limit CHECK (
        (type = 'market') OR (type != 'market' AND price IS NOT NULL)
    )
);

-- 거래 테이블 인덱스
CREATE INDEX idx_trades_strategy_id ON trades(strategy_id);
CREATE INDEX idx_trades_exchange_symbol ON trades(exchange, symbol);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_trades_timestamp_created ON trades(timestamp_created);
CREATE INDEX idx_trades_exchange_order_id ON trades(exchange_order_id);

-- =============================================================================
-- 4. 포지션 테이블
-- =============================================================================
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('long', 'short')),
    entry_price DOUBLE PRECISION NOT NULL CHECK (entry_price > 0),
    current_size DOUBLE PRECISION NOT NULL CHECK (current_size > 0),
    avg_entry_price DOUBLE PRECISION NOT NULL CHECK (avg_entry_price > 0),
    stop_loss_price DOUBLE PRECISION CHECK (stop_loss_price > 0),
    take_profit_price DOUBLE PRECISION CHECK (take_profit_price > 0),
    unrealized_pnl DOUBLE PRECISION DEFAULT 0,
    realized_pnl DOUBLE PRECISION DEFAULT 0,
    total_fees DOUBLE PRECISION DEFAULT 0 CHECK (total_fees >= 0),
    is_open BOOLEAN NOT NULL DEFAULT true,
    opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    
    -- 제약 조건
    CONSTRAINT position_close_logic CHECK (
        (is_open = true AND closed_at IS NULL) OR 
        (is_open = false AND closed_at IS NOT NULL)
    )
);

-- 포지션 테이블 인덱스
CREATE INDEX idx_positions_strategy_id ON positions(strategy_id);
CREATE INDEX idx_positions_is_open ON positions(is_open);
CREATE INDEX idx_positions_exchange_symbol ON positions(exchange, symbol);
CREATE INDEX idx_positions_opened_at ON positions(opened_at);

-- =============================================================================
-- 5. 포트폴리오 리스크 규칙 테이블
-- =============================================================================
CREATE TABLE portfolio_rules (
    id SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    rule_type VARCHAR(50) NOT NULL,
    rule_value JSONB NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- 제약 조건
    CONSTRAINT valid_rule_type CHECK (rule_type IN (
        'max_position_size_percent',
        'max_daily_loss_percent', 
        'max_portfolio_exposure_percent',
        'min_position_size_usd',
        'max_positions_per_symbol',
        'blacklisted_symbols'
    ))
);

-- 포트폴리오 규칙 테이블 인덱스
CREATE INDEX idx_portfolio_rules_portfolio_id ON portfolio_rules(portfolio_id);
CREATE INDEX idx_portfolio_rules_rule_type ON portfolio_rules(rule_type);
CREATE INDEX idx_portfolio_rules_is_active ON portfolio_rules(is_active);

-- =============================================================================
-- 6. 시스템 로그 테이블
-- =============================================================================
CREATE TABLE system_logs (
    id SERIAL PRIMARY KEY,
    level VARCHAR(20) NOT NULL CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    logger_name VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    context JSONB,
    strategy_id INTEGER REFERENCES strategies(id) ON DELETE SET NULL,
    trade_id INTEGER REFERENCES trades(id) ON DELETE SET NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 시스템 로그 테이블 인덱스
CREATE INDEX idx_system_logs_level ON system_logs(level);
CREATE INDEX idx_system_logs_timestamp ON system_logs(timestamp);
CREATE INDEX idx_system_logs_logger_name ON system_logs(logger_name);
CREATE INDEX idx_system_logs_strategy_id ON system_logs(strategy_id);

-- =============================================================================
-- 7. 성능 지표 테이블
-- =============================================================================
CREATE TABLE performance_metrics (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    metric_unit VARCHAR(20),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- 제약 조건  
    CONSTRAINT valid_metric_name CHECK (metric_name IN (
        'total_return_percent',
        'sharpe_ratio',
        'max_drawdown_percent',
        'win_rate_percent',
        'profit_factor',
        'total_trades',
        'avg_trade_duration_hours'
    ))
);

-- 성능 지표 테이블 인덱스
CREATE INDEX idx_performance_metrics_strategy_id ON performance_metrics(strategy_id);
CREATE INDEX idx_performance_metrics_metric_name ON performance_metrics(metric_name);
CREATE INDEX idx_performance_metrics_timestamp ON performance_metrics(timestamp);

-- =============================================================================
-- 8. 트리거 함수 정의
-- =============================================================================

-- updated_at 자동 업데이트 함수
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- updated_at 트리거 적용
CREATE TRIGGER update_portfolios_updated_at BEFORE UPDATE ON portfolios
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_strategies_updated_at BEFORE UPDATE ON strategies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trades_updated_at BEFORE UPDATE ON trades
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- 9. 초기 데이터 삽입
-- =============================================================================

-- 기본 포트폴리오 생성
INSERT INTO portfolios (name, total_capital, available_capital, currency) VALUES 
('Default Portfolio', 10000.00, 10000.00, 'USDT');

-- 기본 포트폴리오 리스크 규칙 설정
INSERT INTO portfolio_rules (portfolio_id, rule_type, rule_value) VALUES 
(1, 'max_position_size_percent', '{"value": 10.0}'),
(1, 'max_daily_loss_percent', '{"value": 5.0}'),
(1, 'max_portfolio_exposure_percent', '{"value": 80.0}'),
(1, 'min_position_size_usd', '{"value": 10.0}');

-- 샘플 이동평균 교차 전략
INSERT INTO strategies (
    name, strategy_type, exchange, symbol, 
    parameters, position_sizing_config, portfolio_id
) VALUES (
    'BTC MA Crossover',
    'MA_CROSSOVER',
    'binance',
    'BTC/USDT',
    '{"fast": 50, "slow": 200, "min_volume_24h": 1000000}',
    '{"model": "fixed_fractional", "risk_percent": 0.02}',
    1
);

-- =============================================================================
-- 10. 뷰 생성 (편의성)
-- =============================================================================

-- 활성 포지션 뷰
CREATE VIEW active_positions AS
SELECT 
    p.*,
    s.name as strategy_name,
    s.strategy_type,
    (p.current_size * p.avg_entry_price) as position_value_usd
FROM positions p
JOIN strategies s ON p.strategy_id = s.id
WHERE p.is_open = true;

-- 일일 거래 요약 뷰
CREATE VIEW daily_trade_summary AS
SELECT 
    DATE(timestamp_created) as trade_date,
    strategy_id,
    s.name as strategy_name,
    COUNT(*) as total_trades,
    SUM(CASE WHEN side = 'buy' THEN cost ELSE 0 END) as total_bought,
    SUM(CASE WHEN side = 'sell' THEN cost ELSE 0 END) as total_sold,
    SUM(fee) as total_fees
FROM trades t
JOIN strategies s ON t.strategy_id = s.id
WHERE status = 'closed'
GROUP BY DATE(timestamp_created), strategy_id, s.name
ORDER BY trade_date DESC;

-- =============================================================================
-- 11. 보안 설정
-- =============================================================================

-- 읽기 전용 사용자 생성 (모니터링용)
-- CREATE USER letrade_readonly WITH PASSWORD 'readonly_password';
-- GRANT CONNECT ON DATABASE letrade_db TO letrade_readonly;
-- GRANT USAGE ON SCHEMA public TO letrade_readonly;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO letrade_readonly;

-- 스키마 생성 완료 로그
INSERT INTO system_logs (level, logger_name, message, context) VALUES 
('INFO', 'database.migration', 'Initial schema migration completed successfully', 
 '{"version": "001", "tables_created": 7, "views_created": 2}');