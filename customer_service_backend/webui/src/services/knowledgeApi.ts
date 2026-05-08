import axios from 'axios';
import { useAuthStore } from '../store';

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' }
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

interface KBDocument {
  id: string;
  title: string;
  content: string;
  type: string;
  active: boolean;
  created_at: number;
}

interface KBConfig {
  vector_model: string;
  retrieve_mode: string;
  top_k: number;
  similarity_threshold: number;
}

export const knowledgeApi = {
  getDocuments: async (): Promise<{ documents: KBDocument[]; count: number }> => {
    const response = await api.get('/kb/documents');
    return response.data;
  },

  getDocument: async (id: string): Promise<KBDocument> => {
    const response = await api.get(`/kb/documents/${id}`);
    return response.data;
  },

  createDocument: async (doc: { title: string; content: string; type: string }): Promise<{ id: string }> => {
    const response = await api.post('/kb/documents', doc);
    return response.data;
  },

  updateDocument: async (id: string, doc: { title: string; content: string; type: string }): Promise<void> => {
    await api.put(`/kb/documents/${id}`, doc);
  },

  deleteDocument: async (id: string): Promise<void> => {
    await api.delete(`/kb/documents/${id}`);
  },

  getConfig: async (): Promise<KBConfig> => {
    const response = await api.get('/kb/config');
    return response.data;
  },

  updateConfig: async (config: KBConfig): Promise<void> => {
    await api.put('/kb/config', config);
  },

  query: async (query: string, topK: number = 3): Promise<{ results: any[] }> => {
    const response = await api.post('/kb/query', { query, top_k: topK });
    return response.data;
  }
};
