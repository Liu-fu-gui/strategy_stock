-- 涨停板数据表
CREATE TABLE IF NOT EXISTS limit_up_boards (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    name VARCHAR(20),
    limit_up_time VARCHAR(20),
    open_count INTEGER,
    reason VARCHAR(200),
    UNIQUE(code, trade_date)
);

CREATE INDEX IF NOT EXISTS ix_limitup_code_date ON limit_up_boards(code, trade_date);

-- 交易日历表
CREATE TABLE IF NOT EXISTS trading_calendars (
    trade_date DATE PRIMARY KEY,
    is_trading_day BOOLEAN DEFAULT TRUE
);
