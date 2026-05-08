import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User, UserRole, Permission } from '../types';
import { rolePermissions } from '../types';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (user: User, token: string) => void;
  logout: () => void;
  hasPermission: (permission: Permission) => boolean;
  hasRole: (role: UserRole) => boolean;
  isSuperAdmin: () => boolean;
  isAdmin: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      login: (user: User, token: string) => {
        set({ user, token, isAuthenticated: true });
      },

      logout: () => {
        set({ user: null, token: null, isAuthenticated: false });
      },

      hasPermission: (permission: Permission) => {
        const { user } = get();
        if (!user) return false;
        
        const rolePerms = rolePermissions[user.role] || [];
        return rolePerms.includes(permission);
      },

      hasRole: (role: UserRole) => {
        const { user } = get();
        if (!user) return false;
        
        if (user.role === 'super_admin') return true;
        
        return user.role === role;
      },

      isSuperAdmin: () => {
        const { user } = get();
        return user?.role === 'super_admin';
      },

      isAdmin: () => {
        const { user } = get();
        return user?.role === 'admin' || user?.role === 'super_admin';
      }
    }),
    {
      name: 'auth-storage'
    }
  )
);

interface SessionState {
  sessions: Session[];
  currentSession: Session | null;
  messages: Message[];
  setSessions: (sessions: Session[]) => void;
  setCurrentSession: (session: Session | null) => void;
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
}

interface Session {
  id: string;
  userId: string;
  status: 'active' | 'transferred' | 'closed';
  createdAt: string;
  updatedAt: string;
  lastMessage?: string;
  messageCount: number;
}

interface Message {
  id: string;
  sessionId: string;
  role: 'user' | 'assistant' | 'system' | 'agent';
  content: string;
  timestamp: string;
}

export const useSessionStore = create<SessionState>((set) => ({
  sessions: [],
  currentSession: null,
  messages: [],

  setSessions: (sessions) => set({ sessions }),
  setCurrentSession: (session) => set({ currentSession: session }),
  setMessages: (messages) => set({ messages }),
  addMessage: (message) => set((state) => ({ 
    messages: [...state.messages, message] 
  }))
}));

interface SettingsState {
  language: string;
  theme: 'light' | 'dark';
  sidebarCollapsed: boolean;
  setLanguage: (lang: string) => void;
  setTheme: (theme: 'light' | 'dark') => void;
  toggleSidebar: () => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      language: 'zh-CN',
      theme: 'light',
      sidebarCollapsed: false,
      setLanguage: (language) => set({ language }),
      setTheme: (theme) => set({ theme }),
      toggleSidebar: () => set((state) => ({ 
        sidebarCollapsed: !state.sidebarCollapsed 
      }))
    }),
    {
      name: 'settings-storage'
    }
  )
);
