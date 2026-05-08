import React from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuthStore, useSettingsStore } from '../store';
import { languages } from '../i18n';

const Layout: React.FC = () => {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, isSuperAdmin, isAdmin, hasPermission } = useAuthStore();
  const { sidebarCollapsed, toggleSidebar } = useSettingsStore();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const changeLanguage = (lang: string) => {
    i18n.changeLanguage(lang);
  };

  const menuItems = [
    { path: '/dashboard', label: t('menu.dashboard'), icon: '📊', permission: 'view_sessions' },
    { path: '/sessions', label: t('menu.conversations'), icon: '💬', permission: 'view_sessions' },
    { path: '/chat', label: t('menu.chat'), icon: '🎧', permission: 'chat_sessions' },
    { path: '/knowledge', label: t('menu.knowledge'), icon: '🧠', permission: 'manage_config' },
    { path: '/users', label: t('menu.users'), icon: '👥', permission: 'manage_users' },
    { path: '/settings', label: t('menu.settings'), icon: '⚙️', permission: undefined }
  ];

  const filteredMenuItems = menuItems.filter(item => 
    !item.permission || hasPermission(item.permission as any)
  );

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div className={`sidebar bg-white shadow-lg ${sidebarCollapsed ? 'w-16' : 'w-64'}`}>
        <div className="flex items-center justify-between p-4 border-b">
          {!sidebarCollapsed && (
            <h1 className="text-lg font-bold text-primary-600">{t('common.appName')}</h1>
          )}
          <button
            onClick={toggleSidebar}
            className="p-2 rounded hover:bg-gray-100"
          >
            {sidebarCollapsed ? '→' : '←'}
          </button>
        </div>

        <nav className="mt-4">
          {filteredMenuItems.map((item) => (
            <div
              key={item.path}
              onClick={() => navigate(item.path)}
              className={`sidebar-item ${location.pathname === item.path ? 'active' : ''}`}
            >
              <span className="text-xl">{item.icon}</span>
              {!sidebarCollapsed && <span>{item.label}</span>}
            </div>
          ))}
        </nav>

        <div className="absolute bottom-0 w-full p-4 border-t bg-white">
          {!sidebarCollapsed && (
            <div className="mb-4">
              <div className="text-sm text-gray-600 mb-2">
                {t('settings.language')}
              </div>
              <select
                value={i18n.language}
                onChange={(e) => changeLanguage(e.target.value)}
                className="w-full px-2 py-1 text-sm border rounded"
              >
                {languages.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.nativeName}
                  </option>
                ))}
              </select>
            </div>
          )}
          
          <div className="flex items-center gap-2">
            <div className="flex-1 min-w-0">
              {!sidebarCollapsed && (
                <>
                  <div className="text-sm font-medium truncate">{user?.username}</div>
                  <div className="text-xs text-gray-500">
                    {user?.role === 'super_admin' ? t('roles.superAdmin') : 
                     user?.role === 'admin' ? t('roles.admin') : t('roles.user')}
                  </div>
                </>
              )}
            </div>
            <button
              onClick={handleLogout}
              className="p-2 text-red-500 hover:bg-red-50 rounded"
              title={t('common.logout')}
            >
              🚪
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 main-content overflow-auto">
        <div className="p-6">
          <Outlet />
        </div>
      </div>
    </div>
  );
};

export default Layout;
