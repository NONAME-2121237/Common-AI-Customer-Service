import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { userApi } from '../services/api';
import { useAuthStore } from '../store';
import type { User, UserRole, Permission } from '../types';
import { rolePermissions } from '../types';

const Users: React.FC = () => {
  const { t } = useTranslation();
  const { user: currentUser, hasPermission, isSuperAdmin } = useAuthStore();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    role: 'user' as UserRole,
    permissions: [] as Permission[]
  });

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      const data = await userApi.getUsers();
      setUsers(data);
    } catch (error) {
      console.error('Failed to load users:', error);
      setUsers([
        {
          id: '1',
          username: 'admin',
          email: 'admin@example.com',
          role: 'super_admin',
          permissions: rolePermissions['super_admin'],
          status: 'active',
          createdAt: new Date().toISOString()
        },
        {
          id: '2',
          username: 'operator1',
          email: 'op1@example.com',
          role: 'admin',
          permissions: rolePermissions['admin'],
          status: 'active',
          createdAt: new Date().toISOString()
        },
        {
          id: '3',
          username: 'user1',
          role: 'user',
          permissions: rolePermissions['user'],
          status: 'active',
          createdAt: new Date().toISOString()
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = () => {
    setEditingUser(null);
    setFormData({
      username: '',
      password: '',
      role: 'user',
      permissions: rolePermissions['user']
    });
    setShowModal(true);
  };

  const handleEdit = (user: User) => {
    if (user.role === 'super_admin' && !isSuperAdmin()) return;
    setEditingUser(user);
    setFormData({
      username: user.username,
      password: '',
      role: user.role,
      permissions: user.permissions
    });
    setShowModal(true);
  };

  const handleDelete = async (userId: string) => {
    const user = users.find(u => u.id === userId);
    if (user?.role === 'super_admin') return;
    
    if (confirm(t('users.confirmDelete'))) {
      try {
        await userApi.deleteUser(userId);
        loadUsers();
      } catch (error) {
        console.error('Failed to delete user:', error);
      }
    }
  };

  const handleSubmit = async () => {
    try {
      if (editingUser) {
        await userApi.updateUser(editingUser.id, formData);
      } else {
        await userApi.createUser(formData);
      }
      setShowModal(false);
      loadUsers();
    } catch (error) {
      console.error('Failed to save user:', error);
    }
  };

  const handleRoleChange = (role: UserRole) => {
    setFormData({
      ...formData,
      role,
      permissions: rolePermissions[role]
    });
  };

  const getRoleBadge = (role: string) => {
    switch (role) {
      case 'super_admin':
        return <span className="badge badge-danger">{t('roles.superAdmin')}</span>;
      case 'admin':
        return <span className="badge badge-warning">{t('roles.admin')}</span>;
      case 'user':
        return <span className="badge badge-info">{t('roles.user')}</span>;
      case 'viewer':
        return <span className="badge badge-success">{t('roles.viewer')}</span>;
      default:
        return null;
    }
  };

  return (
    <div>
      <div className="mb-6 flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-800">{t('users.title')}</h1>
        {hasPermission('manage_users') && (
          <button onClick={handleAdd} className="btn-primary">
            {t('users.addUser')}
          </button>
        )}
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
                <th>{t('users.username')}</th>
                <th>{t('users.role')}</th>
                <th>{t('users.status')}</th>
                <th>{t('users.createdAt')}</th>
                <th>{t('users.lastLogin')}</th>
                <th>{t('common.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td className="font-medium">{user.username}</td>
                  <td>{getRoleBadge(user.role)}</td>
                  <td>
                    <span className={`badge ${user.status === 'active' ? 'badge-success' : 'badge-danger'}`}>
                      {user.status === 'active' ? t('users.enabled') : t('users.disabled')}
                    </span>
                  </td>
                  <td>{new Date(user.createdAt).toLocaleDateString()}</td>
                  <td>{user.lastLogin ? new Date(user.lastLogin).toLocaleString() : '-'}</td>
                  <td>
                    {hasPermission('manage_users') && user.role !== 'super_admin' && (
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleEdit(user)}
                          className="text-primary-600 hover:text-primary-700 text-sm"
                        >
                          {t('common.edit')}
                        </button>
                        {isSuperAdmin() && (
                          <button
                            onClick={() => handleDelete(user.id)}
                            className="text-red-600 hover:text-red-700 text-sm"
                          >
                            {t('common.delete')}
                          </button>
                        )}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">
              {editingUser ? t('users.editUser') : t('users.addUser')}
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('users.username')}
                </label>
                <input
                  type="text"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  className="input"
                  required
                />
              </div>

              {!editingUser && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {t('auth.password')}
                  </label>
                  <input
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    className="input"
                    required={!editingUser}
                  />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('users.role')}
                </label>
                <select
                  value={formData.role}
                  onChange={(e) => handleRoleChange(e.target.value as UserRole)}
                  className="input"
                >
                  {isSuperAdmin() && (
                    <option value="super_admin">{t('roles.superAdmin')}</option>
                  )}
                  <option value="admin">{t('roles.admin')}</option>
                  <option value="user">{t('roles.user')}</option>
                  <option value="viewer">{t('roles.viewer')}</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {t('permissions.title') || 'Permissions'}
                </label>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {formData.permissions.map((perm) => (
                    <label key={perm} className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked
                        disabled
                        className="rounded text-primary-600"
                      />
                      <span className="text-sm">{t(`permissions.${perm.replace('_', '')}`)}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => setShowModal(false)} className="btn-secondary">
                {t('common.cancel')}
              </button>
              <button onClick={handleSubmit} className="btn-primary">
                {t('common.save')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Users;
