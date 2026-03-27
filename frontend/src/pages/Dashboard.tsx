import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Card, Table, Tag, Button, DatePicker, Space, message, Modal, Spin,
  Input, Typography, Switch, Select,
} from 'antd';
import {
  ThunderboltOutlined, SyncOutlined, EditOutlined, StockOutlined,
  CheckCircleOutlined, ReloadOutlined, SaveOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { runStrategy, syncAll, getStockKline, runBatchStrategy, syncBatch, getStrategyTemplates, saveStrategyTemplate } from '../services/api';
import KlineChart from '../components/KlineChart';

const { TextArea } = Input;
const { Text } = Typography;

const DEFAULT_STRATEGY = '近5日有涨停，近3日回调超过5%，竞价抢筹，竞价金额大于1000万，流通市值大于50亿小于300亿，非科创，非创业板，非北交所，非ST';

interface ConditionStep {
  label: string;
  count: number;
}

interface ResultItem {
  code: string;
  name: string;
  change_pct: number;
  current_price: number;
  limit_up_dates: string[];
  auction_amount: number;
  auction_change_pct: number;
  trend: number;
  circulating_market_cap: number | null;
}

interface SyncResult {
  success: boolean;
  stocks: number;
  klines: number;
  auctions: number;
  market_caps?: number;
  errors?: string[];
}

const Dashboard: React.FC = () => {
  const [date, setDate] = useState(dayjs());
  const [strategyText, setStrategyText] = useState(DEFAULT_STRATEGY);
  const [editingStrategy, setEditingStrategy] = useState(false);
  const [tempStrategy, setTempStrategy] = useState(DEFAULT_STRATEGY);

  const [conditions, setConditions] = useState<ConditionStep[]>([]);
  const [results, setResults] = useState<ResultItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [lastUpdateTime, setLastUpdateTime] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(false);
  const timerRef = useRef<NodeJS.Timer | null>(null);

  const [klineVisible, setKlineVisible] = useState(false);
  const [klineData, setKlineData] = useState<any[]>([]);
  const [klineTitle, setKlineTitle] = useState('');
  const [klineLoading, setKlineLoading] = useState(false);

  const [templates, setTemplates] = useState<any[]>([]);
  const [saveModalVisible, setSaveModalVisible] = useState(false);
  const [templateName, setTemplateName] = useState('');

  const dateStr = date.format('YYYY-MM-DD');

  // 执行策略
  const handleRun = useCallback(async () => {
    setLoading(true);
    try {
      const res = await runStrategy(dateStr, strategyText);
      const data = res.data;
      setConditions(data.conditions || []);
      setResults(data.results || []);
      setLastUpdateTime(dayjs().format('MM-DD HH:mm'));
      if (data.count > 0) {
        message.success(`选股结果: ${data.count} 只`);
      } else {
        message.info('未筛选出符合条件的股票');
      }
    } catch (e: any) {
      message.error('执行失败: ' + (e.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  }, [dateStr, strategyText]);

  // 同步数据
  const handleSync = async () => {
    setSyncing(true);
    try {
      const res = await syncAll(dateStr);
      const data: SyncResult = res.data;
      const summary = `股票${data.stocks}, K线${data.klines}, 竞价${data.auctions}, 市值${data.market_caps || 0}`;
      if (data.errors?.length) {
        message.warning(`同步部分完成: ${summary}；${data.errors.join('；')}`);
      } else {
        message.success(`同步完成: ${summary}`);
      }
    } catch (e: any) {
      const data: SyncResult | undefined = e.response?.data;
      if (data) {
        const summary = `股票${data.stocks}, K线${data.klines}, 竞价${data.auctions}, 市值${data.market_caps || 0}`;
        const errorText = data.errors?.join('；') || e.message;
        message.error(`同步失败: ${summary}；${errorText}`);
      } else {
        message.error('同步失败: ' + (e.response?.data?.detail || e.message));
      }
    } finally {
      setSyncing(false);
    }
  };

  // 批量运行最近7天
  const handleRunBatch = async () => {
    setLoading(true);
    try {
      const res = await runBatchStrategy(dateStr, strategyText, '竞价低吸', 7);
      const batchResults = res.data.results || [];
      const success = batchResults.filter((r: any) => r.success).length;
      message.success(`批量运行完成: ${success}/${batchResults.length} 天成功`);
      await handleRun();
    } catch (e: any) {
      message.error('批量运行失败: ' + (e.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  };

  // 批量同步最近7天
  const handleSyncBatch = async () => {
    setSyncing(true);
    try {
      const res = await syncBatch(dateStr, 7);
      const results = res.data.results || [];
      const success = results.filter((r: any) => r.success).length;
      message.success(`批量同步完成: ${success}/${results.length} 天成功`);
    } catch (e: any) {
      message.error('批量同步失败: ' + (e.response?.data?.detail || e.message));
    } finally {
      setSyncing(false);
    }
  };

  // 加载策略模板
  const loadTemplates = async () => {
    try {
      const res = await getStrategyTemplates();
      setTemplates(res.data || []);
    } catch (e: any) {
      message.error('加载模板失败');
    }
  };

  // 保存策略模板
  const handleSaveTemplate = async () => {
    if (!templateName.trim()) {
      message.error('请输入模板名称');
      return;
    }
    try {
      await saveStrategyTemplate(templateName, strategyText);
      message.success('策略已保存');
      setSaveModalVisible(false);
      setTemplateName('');
      loadTemplates();
    } catch (e: any) {
      message.error('保存失败');
    }
  };

  // 加载策略模板
  const handleLoadTemplate = (content: string) => {
    setStrategyText(content);
    message.success('策略已加载');
  };

  // 自动刷新
  useEffect(() => {
    if (autoRefresh) {
      timerRef.current = setInterval(() => { handleRun(); }, 60000);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [autoRefresh, handleRun]);

  useEffect(() => {
    loadTemplates();
  }, []);

  // 编辑策略
  const handleEditConfirm = () => {
    setStrategyText(tempStrategy);
    setEditingStrategy(false);
  };

  // K线弹窗
  const showKline = async (code: string, name: string) => {
    setKlineVisible(true);
    setKlineTitle(`${name} (${code})`);
    setKlineLoading(true);
    try {
      const res = await getStockKline(code, 60);
      setKlineData(res.data || []);
    } catch {
      setKlineData([]);
    } finally {
      setKlineLoading(false);
    }
  };

  // 结果表格列
  const columns: ColumnsType<ResultItem> = [
    {
      title: '',
      width: 50,
      render: (_, __, index) => <span style={{ color: '#999' }}>{index + 1}</span>,
    },
    {
      title: '代码',
      dataIndex: 'code',
      width: 100,
      render: (code, record) => (
        <Button type="link" size="small" onClick={() => showKline(code, record.name)} style={{ padding: 0, fontWeight: 600 }}>
          {code}
        </Button>
      ),
    },
    {
      title: '名称',
      dataIndex: 'name',
      width: 100,
    },
    {
      title: '涨幅%',
      dataIndex: 'change_pct',
      width: 100,
      defaultSortOrder: 'descend',
      sorter: (a, b) => a.change_pct - b.change_pct,
      render: (v) => (
        <span style={{ color: v >= 0 ? '#cf1322' : '#3f8600', fontWeight: 700 }}>
          {v >= 0 ? '+' : ''}{v.toFixed(2)}%
        </span>
      ),
    },
    {
      title: '现价',
      dataIndex: 'current_price',
      width: 90,
      render: (v) => <span style={{ color: '#1677ff', fontWeight: 600 }}>{v.toFixed(2)}</span>,
    },
    {
      title: '涨停满足条件',
      dataIndex: 'limit_up_dates',
      width: 160,
      render: (dates: string[]) => (
        <span>{dates?.length > 0 ? dates.join(', ') : '-'}</span>
      ),
    },
    {
      title: '竞价金额(万)',
      dataIndex: 'auction_amount',
      width: 120,
      sorter: (a, b) => a.auction_amount - b.auction_amount,
      render: (v) => <span style={{ color: '#cf1322' }}>{(v / 10000).toFixed(0)}</span>,
    },
    {
      title: '流通市值(亿)',
      dataIndex: 'circulating_market_cap',
      width: 110,
      sorter: (a, b) => (a.circulating_market_cap || 0) - (b.circulating_market_cap || 0),
      render: (v) => v ? v.toFixed(1) : '-',
    },
    {
      title: '操作',
      width: 70,
      render: (_, record) => (
        <Button type="link" size="small" icon={<StockOutlined />}
          onClick={() => showKline(record.code, record.name)}>K线</Button>
      ),
    },
  ];

  return (
    <div>
      {/* ===== 策略输入区 ===== */}
      <Card size="small" style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            flex: 1, background: '#fafafa', border: '1px solid #d9d9d9',
            borderRadius: 6, padding: '8px 12px', fontSize: 14, minHeight: 36,
            cursor: 'pointer', color: '#333',
          }} onClick={() => { setTempStrategy(strategyText); setEditingStrategy(true); }}>
            {strategyText}
          </div>
          <Button icon={<EditOutlined />} onClick={() => { setTempStrategy(strategyText); setEditingStrategy(true); }}>
            编辑策略
          </Button>
        </div>
      </Card>

      {/* 策略编辑弹窗 */}
      <Modal
        title="编辑策略"
        open={editingStrategy}
        onOk={handleEditConfirm}
        onCancel={() => setEditingStrategy(false)}
        okText="确认"
        cancelText="取消"
        width={600}
      >
        <TextArea
          rows={6}
          value={tempStrategy}
          onChange={(e) => setTempStrategy(e.target.value)}
          placeholder="输入策略条件，用逗号分隔。例如：&#10;近5日有涨停，近3日回调超过5%，竞价抢筹，竞价金额大于1000万，流通市值大于50亿小于300亿，非科创，非创业板，非北交所，非ST"
          style={{ fontSize: 14 }}
        />
        <div style={{ marginTop: 12, color: '#888', fontSize: 12 }}>
          <div><b>支持的条件:</b></div>
          <div>- 近N日有涨停 / 近N日涨停</div>
          <div>- 近N日回调超过X%</div>
          <div>- 竞价抢筹 / 竞价异动</div>
          <div>- 竞价金额大于X万</div>
          <div>- 流通市值大于X亿小于Y亿</div>
          <div>- 非科创 / 非创业板 / 非北交所 / 非ST</div>
        </div>
      </Modal>

      {/* ===== 解析结果 ===== */}
      {conditions.length > 0 && (
        <Card size="small" style={{ marginBottom: 12 }}
          title={<span style={{ fontSize: 14 }}>解析结果:</span>}
        >
          <div style={{ lineHeight: 2.2 }}>
            {conditions.map((c, i) => (
              <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 12 }} />
                <span>{c.label}</span>
                <Tag color="orange" style={{ marginLeft: 4 }}>{c.count}只</Tag>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* ===== 操作栏 + 选股结果 ===== */}
      <Card
        size="small"
        title={
          <Space>
            <span>选股结果:</span>
            <Tag color="red" style={{ fontSize: 14, padding: '2px 12px' }}>
              {results.length} 只
            </Tag>
            {lastUpdateTime && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                (最近更新时间:{lastUpdateTime})
              </Text>
            )}
            <Switch
              checkedChildren="自动刷新"
              unCheckedChildren="自动刷新"
              checked={autoRefresh}
              onChange={setAutoRefresh}
              size="small"
            />
          </Space>
        }
        extra={
          <Space>
            <DatePicker value={date} onChange={(d) => d && setDate(d)} allowClear={false} size="small" />
            <Button size="small" icon={<SyncOutlined spin={syncing} />} loading={syncing} onClick={handleSync}>
              同步数据
            </Button>
            <Button size="small" ghost loading={syncing} onClick={handleSyncBatch}>
              同步最近7天
            </Button>
            <Button size="small" type="primary" icon={<ThunderboltOutlined />} loading={loading} onClick={handleRun}>
              执行策略
            </Button>
            <Button size="small" type="primary" ghost loading={loading} onClick={handleRunBatch}>
              运行最近7天
            </Button>
            <Button size="small" icon={<ReloadOutlined />} onClick={handleRun}>刷新</Button>
            <Select
              size="small"
              placeholder="加载策略"
              style={{ width: 150 }}
              onChange={handleLoadTemplate}
              value={undefined}
            >
              {templates.map(t => <Select.Option key={t.id} value={t.content}>{t.name}</Select.Option>)}
            </Select>
            <Button size="small" icon={<SaveOutlined />} onClick={() => setSaveModalVisible(true)}>保存策略</Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={results}
          rowKey="code"
          loading={loading}
          pagination={false}
          size="small"
          scroll={{ x: 900 }}
          rowClassName={(record) =>
            record.change_pct >= 9.5 ? 'row-limit-up' : ''
          }
        />
      </Card>

      {/* K线弹窗 */}
      <Modal
        title={klineTitle}
        open={klineVisible}
        onCancel={() => setKlineVisible(false)}
        footer={null}
        width={800}
        destroyOnClose
      >
        {klineLoading ? (
          <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /></div>
        ) : (
          <KlineChart data={klineData} title={klineTitle} />
        )}
      </Modal>

      <Modal
        title="保存策略"
        open={saveModalVisible}
        onOk={handleSaveTemplate}
        onCancel={() => setSaveModalVisible(false)}
      >
        <Input
          placeholder="输入策略名称"
          value={templateName}
          onChange={(e) => setTemplateName(e.target.value)}
        />
      </Modal>
    </div>
  );
};

export default Dashboard;
