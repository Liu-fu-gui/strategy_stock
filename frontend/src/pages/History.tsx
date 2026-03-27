import React, { useState, useEffect } from 'react';
import { Card, Table, Tag, Button, Space, message, Modal, Spin, Empty } from 'antd';
import { StockOutlined, ReloadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { getStrategyHistory, getStrategyResults, getStockKline } from '../services/api';
import KlineChart from '../components/KlineChart';

interface ResultItem {
  id: number;
  code: string;
  name: string;
  auction_amount: number;
  auction_change_pct: number;
  recent_limit_up_date: string;
  pullback_pct: number;
  circulating_market_cap: number | null;
  trend: number;
}

interface DayResult {
  trade_date: string;
  count: number;
  results: ResultItem[];
  loading: boolean;
}

const History: React.FC = () => {
  const [days, setDays] = useState<DayResult[]>([]);
  const [loading, setLoading] = useState(false);

  const [klineVisible, setKlineVisible] = useState(false);
  const [klineData, setKlineData] = useState<any[]>([]);
  const [klineTitle, setKlineTitle] = useState('');
  const [klineLoading, setKlineLoading] = useState(false);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const histRes = await getStrategyHistory('竞价低吸', 7);
      const histData: { trade_date: string; count: number }[] = histRes.data || [];

      // 并发拉取每天的详情
      const dayResults: DayResult[] = await Promise.all(
        histData.map(async (h) => {
          try {
            const res = await getStrategyResults(h.trade_date);
            return {
              trade_date: h.trade_date,
              count: h.count,
              results: res.data.results || [],
              loading: false,
            };
          } catch {
            return { trade_date: h.trade_date, count: h.count, results: [], loading: false };
          }
        })
      );
      setDays(dayResults);
    } catch {
      message.error('加载历史记录失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAll(); }, []);

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

  const columns: ColumnsType<ResultItem> = [
    {
      title: '',
      width: 40,
      render: (_, __, i) => <span style={{ color: '#999' }}>{i + 1}</span>,
    },
    {
      title: '代码',
      dataIndex: 'code',
      width: 90,
      render: (code, record) => (
        <Button type="link" size="small" onClick={() => showKline(code, record.name)} style={{ padding: 0, fontWeight: 600 }}>
          {code}
        </Button>
      ),
    },
    {
      title: '名称',
      dataIndex: 'name',
      width: 90,
    },
    {
      title: '竞价金额(万)',
      dataIndex: 'auction_amount',
      width: 110,
      render: (v) => <span style={{ color: '#cf1322' }}>{(v / 10000).toFixed(0)}</span>,
    },
    {
      title: '竞价涨幅',
      dataIndex: 'auction_change_pct',
      width: 90,
      render: (v) => (
        <span style={{ color: Number(v) >= 0 ? '#cf1322' : '#3f8600' }}>
          {Number(v) >= 0 ? '+' : ''}{Number(v).toFixed(2)}%
        </span>
      ),
    },
    {
      title: '方向',
      dataIndex: 'trend',
      width: 60,
      render: (v) => v === 1 ? <Tag color="red">抢筹</Tag> : v === -1 ? <Tag color="green">出货</Tag> : <Tag>中性</Tag>,
    },
    {
      title: '涨停日',
      dataIndex: 'recent_limit_up_date',
      width: 110,
    },
    {
      title: '回调',
      dataIndex: 'pullback_pct',
      width: 80,
      render: (v) => v != null ? <span style={{ color: '#3f8600' }}>{Number(v).toFixed(2)}%</span> : '-',
    },
    {
      title: '流通市值(亿)',
      dataIndex: 'circulating_market_cap',
      width: 100,
      render: (v) => v ? Number(v).toFixed(1) : '-',
    },
    {
      title: '',
      width: 60,
      render: (_, record) => (
        <Button type="link" size="small" icon={<StockOutlined />}
          onClick={() => showKline(record.code, record.name)}>K线</Button>
      ),
    },
  ];

  return (
    <div>
      <Card
        size="small"
        style={{ marginBottom: 12 }}
        extra={
          <Button size="small" icon={<ReloadOutlined />} onClick={fetchAll} loading={loading}>
            刷新
          </Button>
        }
      >
        <span style={{ fontWeight: 600 }}>近7天选股记录</span>
        <span style={{ color: '#999', marginLeft: 12 }}>
          共 {days.length} 个交易日，{days.reduce((s, d) => s + d.count, 0)} 只选票
        </span>
      </Card>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /></div>
      ) : days.length === 0 ? (
        <Empty description="暂无历史记录" />
      ) : (
        days.map((day) => (
          <Card
            key={day.trade_date}
            size="small"
            style={{ marginBottom: 12 }}
            title={
              <Space>
                <span style={{ fontWeight: 600 }}>{day.trade_date}</span>
                <Tag color="red">{day.count} 只</Tag>
              </Space>
            }
          >
            {day.results.length > 0 ? (
              <Table
                columns={columns}
                dataSource={day.results}
                rowKey="id"
                pagination={false}
                size="small"
                scroll={{ x: 800 }}
              />
            ) : (
              <Empty description="无筛选结果" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>
        ))
      )}

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
    </div>
  );
};

export default History;
