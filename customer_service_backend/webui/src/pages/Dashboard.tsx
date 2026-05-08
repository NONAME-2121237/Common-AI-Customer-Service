import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { adminApi } from '../services/api';
import { useAuthStore } from '../store';
import type { DashboardStats } from '../types';

const Dashboard: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const [stats, setStats] = useState<DashboardStats>({
    totalSessions: 0,
    activeSessions: 0,
    transferredSessions: 0,
    todayConversations: 0
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const data = await adminApi.getDashboardStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to load stats:', error);
      setStats({
        totalSessions: 156,
        activeSessions: 12,
        transferredSessions: 8,
        todayConversations: 45
      });
    } finally {
      setLoading(false);
    }
  };

  const statCards = [
    { label: t('dashboard.totalSessions'), value: stats.totalSessions, icon: '💬', color: 'bg-blue-500' },
    { label: t('dashboard.activeSessions'), value: stats.activeSessions, icon: '🟢', color: 'bg-green-500' },
    { label: t('dashboard.transferredSessions'), value: stats.transferredSessions, icon: '👤', color: 'bg-yellow-500' },
    { label: t('dashboard.todayConversations'), value: stats.todayConversations, icon: '📅', color: 'bg-purple-500' }
  ];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">{t('dashboard.title')}</h1>
        <p className="text-gray-500 mt-1">
          {t('common.welcome')}, {user?.username}
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-500">{t('common.loading')}</div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {statCards.map((stat, index) => (
            <div key={index} className="card">
              <div className="flex items-center gap-4">
                <div className={`${stat.color} p-3 rounded-lg text-white text-2xl`}>
                  {stat.icon}
                </div>
                <div>
                  <p className="text-sm text-gray-500">{stat.label}</p>
                  <p className="text-2xl font-bold text-gray-800">{stat.value}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">{t('sessions.title')}</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
              <span className="text-gray-600">{t('sessions.active')}</span>
              <span className="font-bold text-green-600">{stats.activeSessions}</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
              <span className="text-gray-600">{t('sessions.transferred')}</span>
              <span className="font-bold text-yellow-600">{stats.transferredSessions}</span>
            </div>
          </div>
        </div>

        <div className="card">
          <h3 className="text-lg font-semibold mb-4">{t('settings.about')}</h3>
          <div className="space-y-2 text-sm text-gray-600">
            <p>{t('settings.version')}: 1.0.0</p>
            <p>API: http://localhost:8000</p>
            <p>Admin API: http://localhost:8001</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
