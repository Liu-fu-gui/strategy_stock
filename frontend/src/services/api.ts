import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 30000,
});

// ---- 数据同步 ----
export const syncAll = (trade_date: string) =>
  api.post('/data/sync/all', { trade_date });

export const syncStocks = () =>
  api.post('/data/sync/stocks');

export const syncKline = (trade_date: string) =>
  api.post('/data/sync/kline', { trade_date });

export const syncAuction = (trade_date: string) =>
  api.post('/data/sync/auction', { trade_date });

export const syncBatch = (trade_date: string, days = 7) =>
  api.post('/data/sync/batch', { trade_date }, { params: { days }, timeout: 180000 });

// ---- 股票 ----
export const getStockList = (keyword = '', board = '', page = 1, page_size = 20) =>
  api.get('/stocks', { params: { keyword, board, page, page_size } });

export const getStockKline = (code: string, limit = 60) =>
  api.get(`/stocks/${code}/kline`, { params: { limit } });

// ---- 策略 ----
export const runStrategy = (trade_date: string, strategy_text: string, strategy_name = '竞价低吸') =>
  api.post('/strategy/run', { trade_date, strategy_text, strategy_name });

export const getStrategyResults = (trade_date: string, strategy_name = '竞价低吸') =>
  api.get('/strategy/results', { params: { trade_date, strategy_name } });

export const getStrategyHistory = (strategy_name = '竞价低吸', limit = 30) =>
  api.get('/strategy/history', { params: { strategy_name, limit } });

export const runBatchStrategy = (trade_date: string, strategy_text: string, strategy_name = '竞价低吸', days = 7) =>
  api.post('/strategy/run-batch', { trade_date, strategy_text, strategy_name }, { params: { days }, timeout: 180000 });

export const getStrategyTemplates = () =>
  api.get('/strategy/templates');

export const saveStrategyTemplate = (name: string, content: string) =>
  api.post('/strategy/templates', null, { params: { name, content } });

export const deleteStrategyTemplate = (id: number) =>
  api.delete(`/strategy/templates/${id}`);

export const getLimitUpPool = () =>
  api.get('/strategy/limitup');

// ---- 系统设置 ----
export const getEnvSettings = () =>
  api.get('/settings/env');

export const updateEnvSettings = (data: any) =>
  api.post('/settings/env', data);

export default api;
