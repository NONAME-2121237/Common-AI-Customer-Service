import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Sessions from './pages/Sessions';
import Chat from './pages/Chat';
import Users from './pages/Users';
import Settings from './pages/Settings';
import Knowledge from './pages/Knowledge';
import NoPermission from './pages/NoPermission';

const ProtectedRoute: React.FC<{ children: React.ReactNode; permission?: string }> = ({ 
  children, 
  permission 
}) => {
  const { isAuthenticated, hasPermission } = useAuthStore();
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  if (permission && !hasPermission(permission as any)) {
    return <NoPermission />;
  }
  
  return <>{children}</>;
};

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="sessions" element={<Sessions />} />
          <Route path="chat/:sessionId?" element={<Chat />} />
          <Route path="knowledge" element={<Knowledge />} />
          <Route path="users" element={<Users />} />
          <Route path="settings" element={<Settings />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
