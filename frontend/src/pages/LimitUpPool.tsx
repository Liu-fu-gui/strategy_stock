import React, { useEffect, useState } from 'react';
import { Card, Table, Button, Space, message, Tag } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { getLimitUpPool } from '../services/api';

interface LimitUpItem {
  code: string;
  name: string;
  board: string;
  close?: number;
  amount?: number;
  limit_up_time?: string | number | null;
  last_limit_up_time?: string | number | null;
  open_count?: number;
  limit_up_count?: number;
  sealed_fund?: number;
  change_pct?: number;
}

const formatNumber = (value: unknown, digits = 2) => {
  const num = Number(value);
  return Number.isFinite(num) ? num.toFixed(digits) : '-';
};

const formatLimitUpTime = (value: unknown) => {
  if (value == null || value === '') {
    return '-';
  }
  if (typeof value === 'number') {
    const text = String(value).padStart(6, '0');
    return `${text.slice(0, 2)}:${text.slice(2, 4)}:${text.slice(4, 6)}`;
  }
  return String(value);
};

const LimitUpPool: React.FC = () => {
  const [data, setData] = useState<LimitUpItem[]>([]);
  const [loading, setLoading] = useState(false);
  const dateStr = dayjs().format('YYYY-MM-DD');

  const handleLoad = async () => {
    setLoading(true);
    try {
      const res = await getLimitUpPool();
      setData(res.data.data || []);
      if (res.data.count > 0) {
        message.success(`加载完成: ${res.data.count} 只涨停`);
      } else {
        message.warning('当天涨停池暂无数据');
      }
    } catch (e: any) {
      message.error('加载当天涨停池失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    handleLoad();
  }, []);

  const columns: ColumnsType<LimitUpItem> = [
    { title: '序号', width: 60, render: (_, __, i) => i + 1 },
    { title: '代码', dataIndex: 'code', width: 100 },
    { title: '名称', dataIndex: 'name', width: 120 },
    {
      title: '板块',
      dataIndex: 'board',
      width: 120,
      render: (value: string) => <Tag color="blue">{value || '-'}</Tag>,
    },
    {
      title: '涨幅%',
      dataIndex: 'change_pct',
      width: 80,
      render: (value) => <span style={{ color: '#cf1322' }}>{formatNumber(value, 2)}%</span>,
    },
    { title: '收盘价', dataIndex: 'close', width: 90, render: (value) => formatNumber(value, 2) },
    { title: '首次封板', dataIndex: 'limit_up_time', width: 100, render: (value) => formatLimitUpTime(value) },
    { title: '最后封板', dataIndex: 'last_limit_up_time', width: 100, render: (value) => formatLimitUpTime(value) },
    { title: '打开次数', dataIndex: 'open_count', width: 90, render: (value) => Number.isFinite(Number(value)) ? value : '-' },
    { title: '连板数', dataIndex: 'limit_up_count', width: 80, render: (value) => Number.isFinite(Number(value)) ? value : '-' },
    {
      title: '成交额(万)',
      dataIndex: 'amount',
      width: 120,
      render: (value) => Number.isFinite(Number(value)) ? (Number(value) / 10000).toFixed(0) : '-',
    },
    {
      title: '封单额(万)',
      dataIndex: 'sealed_fund',
      width: 120,
      render: (value) => Number.isFinite(Number(value)) ? (Number(value) / 10000).toFixed(0) : '-',
    },
  ];

  return (
    <Card
      title={`涨停池 (${dateStr})`}
      extra={
        <Space>
          <Button size="small" icon={<ReloadOutlined />} loading={loading} onClick={handleLoad}>
            刷新当天
          </Button>
        </Space>
      }
    >
      <Table
        columns={columns}
        dataSource={data}
        rowKey="code"
        loading={loading}
        size="small"
        pagination={{ pageSize: 50 }}
      />
    </Card>
  );
};

export default LimitUpPool;
