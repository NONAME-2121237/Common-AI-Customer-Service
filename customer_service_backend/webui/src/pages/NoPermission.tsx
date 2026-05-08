import React from 'react';
import { useTranslation } from 'react-i18next';

const NoPermission: React.FC = () => {
  const { t } = useTranslation();

  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <div className="text-6xl mb-4">🚫</div>
        <h2 className="text-2xl font-bold text-gray-800 mb-2">{t('common.warning')}</h2>
        <p className="text-gray-600">{t('auth.noPermission')}</p>
      </div>
    </div>
  );
};

export default NoPermission;
