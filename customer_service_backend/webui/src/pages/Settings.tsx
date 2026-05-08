import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { configApi } from '../services/api';
import { useSettingsStore, useAuthStore } from '../store';
import { languages } from '../i18n';

const Settings: React.FC = () => {
  const { t, i18n } = useTranslation();
  const { user, hasPermission, isSuperAdmin } = useAuthStore();
  const { language, setLanguage, theme, setTheme } = useSettingsStore();
  const [config, setConfig] = useState<any>({});
  const [configContent, setConfigContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    setLoading(true);
    try {
      const data = await configApi.getConfig();
      setConfig(data);
      const raw = await configApi.getRawConfig();
      setConfigContent(raw);
    } catch (error) {
      console.error('Failed to load config:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLanguageChange = (lang: string) => {
    setLanguage(lang);
    i18n.changeLanguage(lang);
  };

  const handleSaveConfig = async () => {
    setSaving(true);
    try {
      await configApi.updateRawConfig(configContent);
      alert(t('common.success'));
    } catch (error) {
      console.error('Failed to save config:', error);
      alert(t('common.error'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">{t('settings.title')}</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* General Settings */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">{t('settings.general')}</h2>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('settings.language')}
              </label>
              <select
                value={i18n.language}
                onChange={(e) => handleLanguageChange(e.target.value)}
                className="input"
              >
                {languages.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.nativeName} ({lang.name})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('settings.theme')}
              </label>
              <div className="flex gap-4">
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="theme"
                    checked={theme === 'light'}
                    onChange={() => setTheme('light')}
                  />
                  <span>Light</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="theme"
                    checked={theme === 'dark'}
                    onChange={() => setTheme('dark')}
                  />
                  <span>Dark</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        {/* Profile */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">{t('menu.profile')}</h2>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-500">{t('users.username')}</label>
              <p className="font-medium">{user?.username}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-500">{t('users.role')}</label>
              <p className="font-medium">
                {user?.role === 'super_admin' ? t('roles.superAdmin') :
                 user?.role === 'admin' ? t('roles.admin') : t('roles.user')}
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-500">ID</label>
              <p className="font-mono text-sm">{user?.id}</p>
            </div>
          </div>
        </div>

        {/* Config Management */}
        {(hasPermission('manage_config') || isSuperAdmin()) && (
          <div className="card lg:col-span-2">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold">{t('settings.configManagement')}</h2>
              <button
                onClick={handleSaveConfig}
                disabled={saving}
                className="btn-primary"
              >
                {saving ? t('common.loading') : t('common.save')}
              </button>
            </div>
            
            {loading ? (
              <div className="text-center py-8 text-gray-500">
                {t('common.loading')}
              </div>
            ) : (
              <textarea
                value={configContent}
                onChange={(e) => setConfigContent(e.target.value)}
                className="input font-mono text-sm h-64"
                spellCheck={false}
              />
            )}
            
            <p className="text-sm text-gray-500 mt-2">
              ⚠️ {isSuperAdmin() ? '您可以修改所有配置' : '您只能修改部分配置'}
            </p>
          </div>
        )}

        {/* About */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">{t('settings.about')}</h2>
          
          <div className="space-y-2 text-sm text-gray-600">
            <p>{t('common.appName')}</p>
            <p>{t('settings.version')}: 1.0.0</p>
            <p>API: http://localhost:8000</p>
            <p>Admin API: http://localhost:8001</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;
