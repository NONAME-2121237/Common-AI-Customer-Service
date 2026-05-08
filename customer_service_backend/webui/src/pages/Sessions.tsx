import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { sessionApi } from '../services/api';
import { useAuthStore } from '../store';
import type { Session } from '../types';

const Sessions: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { hasPermission } = useAuthStore();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'active' | 'transferred'>('all');
  const [search, setSearch] = useState('');

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      const data = await sessionApi.getSessions();
      setSessions(data);
    } catch (error) {
      console.error('Failed to load sessions:', error);
      setSessions([
        {
          id: '1',
          userId: 'user001',
          status: 'active',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          lastMessage: '你好，我想咨询一下',
          messageCount: 5
        },
        {
          id: '2',
          userId: 'user002',
          status: 'transferred',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          lastMessage: '转接人工服务',
          messageCount: 10
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const filteredSessions = sessions.filter((session) => {
    if (filter !== 'all' && session.status !== filter) return false;
    if (search && !session.userId.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return <span className="badge badge-success">{t('sessions.active')}</span>;
      case 'transferred':
        return <span className="badge badge-warning">{t('sessions.transferred')}</span>;
      case 'closed':
        return <span className="badge badge-info">{t('sessions.closed')}</span>;
      default:
        return null;
    }
  };

  const handleChat = (sessionId: string) => {
    navigate(`/chat/${sessionId}`);
  };

  const handleTransfer = async (sessionId: string) => {
    try {
      await sessionApi.transferToHuman(sessionId);
      loadSessions();
    } catch (error) {
      console.error('Failed to transfer:', error);
    }
  };

  return (
    <div>
      <div className="mb-6 flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-800">{t('sessions.title')}</h1>
        <button onClick={loadSessions} className="btn-secondary">
          {t('common.refresh')}
        </button>
      </div>

      <div className="card mb-6">
        <div className="flex gap-4 items-center">
          <input
            type="text"
            placeholder={t('common.search')}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input flex-1"
          />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as any)}
            className="input w-40"
          >
            <option value="all">{t('common.all') || 'All'}</option>
            <option value="active">{t('sessions.active')}</option>
            <option value="transferred">{t('sessions.transferred')}</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-500">{t('common.loading')}</div>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="table">
            <thead>
              <tr>
                <th>{t('sessions.sessionId')}</th>
                <th>{t('sessions.userId')}</th>
                <th>{t('sessions.status')}</th>
                <th>{t('sessions.lastMessage')}</th>
                <th>{t('sessions.updatedAt')}</th>
                <th>{t('common.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {filteredSessions.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-8 text-gray-500">
                    {t('common.noData')}
                  </td>
                </tr>
              ) : (
                filteredSessions.map((session) => (
                  <tr key={session.id}>
                    <td className="font-mono text-sm">{session.id.slice(0, 8)}...</td>
                    <td>{session.userId}</td>
                    <td>{getStatusBadge(session.status)}</td>
                    <td className="max-w-xs truncate">{session.lastMessage || '-'}</td>
                    <td>{new Date(session.updatedAt).toLocaleString()}</td>
                    <td>
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleChat(session.id)}
                          className="text-primary-600 hover:text-primary-700 text-sm"
                        >
                          {t('chat.title')}
                        </button>
                        {session.status === 'active' && hasPermission('reply_sessions') && (
                          <button
                            onClick={() => handleTransfer(session.id)}
                            className="text-yellow-600 hover:text-yellow-700 text-sm"
                          >
                            {t('sessions.transferToHuman')}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default Sessions;
