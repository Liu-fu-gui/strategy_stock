import React, { useState, useEffect } from 'react';
import { Card, Form, Input, Button, message } from 'antd';
import { getEnvSettings, updateEnvSettings } from '../services/api';

const Settings: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const res = await getEnvSettings();
      form.setFieldsValue(res.data);
    } catch (e: any) {
      message.error('加载配置失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const values = await form.validateFields();
      await updateEnvSettings(values);
      message.success('配置已保存，请重启后端服务生效');
    } catch (e: any) {
      message.error('保存失败');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card title="系统设置" loading={loading}>
      <Form form={form} layout="vertical" style={{ maxWidth: 600 }}>
        <Form.Item label="数据库地址" name="database_url" rules={[{ required: true }]}>
          <Input placeholder="postgresql+asyncpg://user:pass@host:port/db" />
        </Form.Item>
        <Form.Item label="Redis地址" name="redis_url" rules={[{ required: true }]}>
          <Input placeholder="redis://:password@host:port/0" />
        </Form.Item>
        <Form.Item label="Xtick API地址" name="xtick_base_url" rules={[{ required: true }]}>
          <Input placeholder="http://api.xtick.top" />
        </Form.Item>
        <Form.Item label="Xtick Token" name="xtick_token" rules={[{ required: true }]}>
          <Input placeholder="your_token_here" />
        </Form.Item>
        <Form.Item>
          <Button type="primary" onClick={handleSave} loading={saving}>
            保存配置
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );
};

export default Settings;
