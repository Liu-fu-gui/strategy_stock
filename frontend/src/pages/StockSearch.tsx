import React, { useState } from 'react';
import { Card, Input, Table, Tag, Button, Space, Modal, Spin, Select, message } from 'antd';
import { SearchOutlined, StockOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { getStockList, getStockKline } from '../services/api';
import KlineChart from '../components/KlineChart';

interface StockItem {
  code: string;
  name: string;
  market: string;
  board: string;
  is_st: boolean;
}

const boardMap: Record<string, { label: string; color: string }> = {
  main: { label: '主板', color: 'blue' },
  cyb: { label: '创业板', color: 'orange' },
  kcb: { label: '科创板', color: 'purple' },
  bj: { label: '北交所', color: 'cyan' },
};

const StockSearch: React.FC = () => {
  const [keyword, setKeyword] = useState('');
  const [board, setBoard] = useState('');
  const [stocks, setStocks] = useState<StockItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);

  const [klineVisible, setKlineVisible] = useState(false);
  const [klineData, setKlineData] = useState<any[]>([]);
  const [klineTitle, setKlineTitle] = useState('');
  const [klineLoading, setKlineLoading] = useState(false);

  const handleSearch = async (p = 1) => {
    setLoading(true);
    setPage(p);
    try {
      const res = await getStockList(keyword, board, p, 20);
      setStocks(res.data || []);
    } catch {
      message.error('搜索失败');
    } finally {
      setLoading(false);
    }
  };

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

  const columns: ColumnsType<StockItem> = [
    { title: '代码', dataIndex: 'code', width: 100 },
    { title: '名称', dataIndex: 'name', width: 120 },
    {
      title: '市场',
      dataIndex: 'market',
      width: 80,
      render: (v) => v?.toUpperCase(),
    },
    {
      title: '板块',
      dataIndex: 'board',
      width: 100,
      render: (v) => {
        const info = boardMap[v] || { label: v, color: 'default' };
        return <Tag color={info.color}>{info.label}</Tag>;
      },
    },
    {
      title: 'ST',
      dataIndex: 'is_st',
      width: 60,
      render: (v) => v ? <Tag color="red">ST</Tag> : null,
    },
    {
      title: '操作',
      width: 80,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          icon={<StockOutlined />}
          onClick={() => showKline(record.code, record.name)}
        >
          K线
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <Input
            placeholder="输入代码或名称"
            prefix={<SearchOutlined />}
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onPressEnter={() => handleSearch(1)}
            style={{ width: 200 }}
            allowClear
          />
          <Select
            placeholder="板块筛选"
            value={board || undefined}
            onChange={(v) => setBoard(v || '')}
            style={{ width: 120 }}
            allowClear
            options={[
              { label: '主板', value: 'main' },
              { label: '创业板', value: 'cyb' },
              { label: '科创板', value: 'kcb' },
              { label: '北交所', value: 'bj' },
            ]}
          />
          <Button type="primary" onClick={() => handleSearch(1)}>搜索</Button>
        </Space>
      </Card>

      <Card title="股票列表">
        <Table
          columns={columns}
          dataSource={stocks}
          rowKey="code"
          loading={loading}
          size="middle"
          pagination={{
            current: page,
            pageSize: 20,
            onChange: (p) => handleSearch(p),
          }}
        />
      </Card>

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

export default StockSearch;
