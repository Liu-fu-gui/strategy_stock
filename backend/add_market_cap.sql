-- 给 stocks 表添加流通市值字段
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS circulating_market_cap NUMERIC(20, 2);
