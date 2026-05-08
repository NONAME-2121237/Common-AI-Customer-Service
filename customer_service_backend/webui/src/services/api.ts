import axios from 'axios';
import type { User, LoginRequest, LoginResponse, Session, Message, ConfigItem, DashboardStats } from '../types';
import { useAuthStore } from '../store';

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const response = await api.post<LoginResponse>('/auth/login', data);
    return response.data;
  },
  
  logout: async (): Promise<void> => {
    await api.post('/auth/logout');
  },
  
  getCurrentUser: async (): Promise<User> => {
    const response = await api.get<User>('/auth/me');
    return response.data;
  }
};

export const sessionApi = {
  getSessions: async (): Promise<Session[]> => {
    const response = await api.get<Session[]>('/sessions');
    return response.data;
  },
  
  getSession: async (sessionId: string): Promise<Session> => {
    const response = await api.get<Session>(`/sessions/${sessionId}`);
    return response.data;
  },
  
  getSessionMessages: async (sessionId: string): Promise<Message[]> => {
    const response = await api.get<Message[]>(`/sessions/${sessionId}/messages`);
    return response.data;
  },
  
  transferToHuman: async (sessionId: string): Promise<void> => {
    await api.post(`/sessions/${sessionId}/transfer`);
  },
  
  releaseSession: async (sessionId: string): Promise<void> => {
    await api.post(`/sessions/${sessionId}/release`);
  }
};

export const chatApi = {
  sendMessage: async (userId: string, userInput: string): Promise<{ response: string; sessionId: string }> => {
    const response = await api.post('/v1/chat', { user_id: userId, user_input: userInput });
    return response.data;
  }
};

export const userApi = {
  getUsers: async (): Promise<User[]> => {
    const response = await api.get<User[]>('/users');
    return response.data;
  },
  
  getUser: async (userId: string): Promise<User> => {
    const response = await api.get<User>(`/users/${userId}`);
    return response.data;
  },
  
  createUser: async (user: Partial<User>): Promise<User> => {
    const response = await api.post<User>('/users', user);
    return response.data;
  },
  
  updateUser: async (userId: string, user: Partial<User>): Promise<User> => {
    const response = await api.put<User>(`/users/${userId}`, user);
    return response.data;
  },
  
  deleteUser: async (userId: string): Promise<void> => {
    await api.delete(`/users/${userId}`);
  },
  
  updateUserRole: async (userId: string, role: string, permissions: string[]): Promise<void> => {
    await api.put(`/users/${userId}/role`, { role, permissions });
  }
};

export const configApi = {
  getConfig: async (): Promise<any> => {
    const response = await api.get('/admin/config');
    return response.data;
  },
  
  updateConfig: async (path: string, value: any): Promise<void> => {
    await api.put('/admin/config', { path, value });
  },
  
  getRawConfig: async (): Promise<string> => {
    const response = await api.get('/admin/config/raw');
    return response.data.content;
  },
  
  updateRawConfig: async (content: string): Promise<void> => {
    await api.put('/admin/config/raw', { content });
  }
};

export const adminApi = {
  getDashboardStats: async (): Promise<DashboardStats> => {
    const response = await api.get<DashboardStats>('/admin/dashboard');
    return response.data;
  },
  
  getTransferredSessions: async (): Promise<Session[]> => {
    const response = await api.get<Session[]>('/admin/sessions/transferred');
    return response.data;
  },
  
  getComponentStatus: async (): Promise<any> => {
    const response = await api.get('/admin/components/status');
    return response.data;
  }
};

export default api;
