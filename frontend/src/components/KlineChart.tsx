import React from 'react';
import ReactECharts from 'echarts-for-react';

interface KlineData {
  trade_date: string;
  open: number;
  close: number;
  low: number;
  high: number;
  volume: number;
  is_limit_up: boolean;
}

interface Props {
  data: KlineData[];
  title?: string;
}

const KlineChart: React.FC<Props> = ({ data, title }) => {
  if (!data || data.length === 0) {
    return <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无K线数据</div>;
  }

  const sorted = [...data].reverse();
  const dates = sorted.map((d) => d.trade_date);
  const klineData = sorted.map((d) => [d.open, d.close, d.low, d.high]);
  const volumeData = sorted.map((d) => ({
    value: d.volume,
    itemStyle: { color: d.close >= d.open ? '#ef5350' : '#26a69a' },
  }));

  const option = {
    title: { text: title || 'K线图', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
    },
    grid: [
      { left: '8%', right: '4%', top: '10%', height: '55%' },
      { left: '8%', right: '4%', top: '72%', height: '18%' },
    ],
    xAxis: [
      { type: 'category', data: dates, gridIndex: 0, axisLabel: { fontSize: 10 } },
      { type: 'category', data: dates, gridIndex: 1, axisLabel: { show: false } },
    ],
    yAxis: [
      { scale: true, gridIndex: 0, splitNumber: 4 },
      { scale: true, gridIndex: 1, splitNumber: 2, axisLabel: { fontSize: 10 } },
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], start: 60, end: 100 },
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        data: klineData,
        xAxisIndex: 0,
        yAxisIndex: 0,
        itemStyle: {
          color: '#ef5350',
          color0: '#26a69a',
          borderColor: '#ef5350',
          borderColor0: '#26a69a',
        },
      },
      {
        name: '成交量',
        type: 'bar',
        data: volumeData,
        xAxisIndex: 1,
        yAxisIndex: 1,
      },
    ],
  };

  return <ReactECharts option={option} style={{ height: 400 }} />;
};

export default KlineChart;
