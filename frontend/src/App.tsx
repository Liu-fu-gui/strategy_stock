import React from 'react';
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { ConfigProvider, Layout, Menu, theme } from 'antd';
import {
  ThunderboltOutlined, HistoryOutlined, RiseOutlined, SettingOutlined,
} from '@ant-design/icons';
import zhCN from 'antd/locale/zh_CN';
import Dashboard from './pages/Dashboard';
import History from './pages/History';
import LimitUpPool from './pages/LimitUpPool';
import Settings from './pages/Settings';

const { Header, Content, Sider } = Layout;

const menuItems = [
  { key: '/', icon: <ThunderboltOutlined />, label: '策略选股' },
  { key: '/history', icon: <HistoryOutlined />, label: '历史记录' },
  { key: '/limitup', icon: <RiseOutlined />, label: '涨停池' },
  { key: '/settings', icon: <SettingOutlined />, label: '系统设置' },
];

const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider theme="dark" width={180}>
        <div style={{
          height: 48, display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#fff', fontWeight: 700, fontSize: 16, borderBottom: '1px solid #303030',
        }}>
          策略选股系统
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{
          background: '#fff', padding: '0 24px', fontSize: 16, fontWeight: 600,
          borderBottom: '1px solid #f0f0f0',
        }}>
          {menuItems.find((m) => m.key === location.pathname)?.label || '策略选股'}
        </Header>
        <Content style={{ margin: 16 }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/history" element={<History />} />
            <Route path="/limitup" element={<LimitUpPool />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
};

const App: React.FC = () => (
  <ConfigProvider
    locale={zhCN}
    theme={{
      algorithm: theme.defaultAlgorithm,
      token: { colorPrimary: '#1677ff' },
    }}
  >
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  </ConfigProvider>
);

export default App;
