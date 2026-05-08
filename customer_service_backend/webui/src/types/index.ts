export type UserRole = 'super_admin' | 'admin' | 'user' | 'viewer';

export type Permission =
  | 'view_sessions'
  | 'chat_sessions'
  | 'reply_sessions'
  | 'manage_users'
  | 'manage_config'
  | 'assign_roles'
  | 'manage_admins';

export interface User {
  id: string;
  username: string;
  email?: string;
  role: UserRole;
  permissions: Permission[];
  status: 'active' | 'disabled';
  createdAt: string;
  lastLogin?: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  token: string;
  user: User;
}

export interface Session {
  id: string;
  userId: string;
  status: 'active' | 'transferred' | 'closed';
  createdAt: string;
  updatedAt: string;
  lastMessage?: string;
  messageCount: number;
}

export interface Message {
  id: string;
  sessionId: string;
  role: 'user' | 'assistant' | 'system' | 'agent';
  content: string;
  timestamp: string;
}

export interface ChatRequest {
  userId: string;
  userInput: string;
}

export interface ChatResponse {
  response: string;
  sessionId: string;
  userId: string;
  shouldEscalate: boolean;
}

export interface ConfigItem {
  path: string;
  value: any;
}

export interface DashboardStats {
  totalSessions: number;
  activeSessions: number;
  transferredSessions: number;
  todayConversations: number;
}

export const rolePermissions: Record<UserRole, Permission[]> = {
  super_admin: [
    'view_sessions',
    'chat_sessions',
    'reply_sessions',
    'manage_users',
    'manage_config',
    'assign_roles',
    'manage_admins'
  ],
  admin: [
    'view_sessions',
    'chat_sessions',
    'reply_sessions',
    'manage_users',
    'manage_config'
  ],
  user: [
    'view_sessions',
    'chat_sessions',
    'reply_sessions'
  ],
  viewer: [
    'view_sessions'
  ]
};
