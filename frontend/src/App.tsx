import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { Navbar } from './components/Navbar';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { VerifyEmailPage } from './pages/VerifyEmailPage';
import { AgentsPage } from './pages/AgentsPage';
import { AppointmentsPage } from './pages/AppointmentsPage';
import { ChatHistoryPage } from './pages/ChatHistoryPage';
import type { ReactNode } from 'react';

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen text-text-secondary">
        Loading...
      </div>
    );
  }

  if (!user) return <Navigate to="/login" replace />;

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />
      {children}
    </div>
  );
}

function AppRoutes() {
  const { user, loading } = useAuth();

  if (loading) return null;

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/agents" replace /> : <LoginPage />} />
      <Route path="/register" element={user ? <Navigate to="/agents" replace /> : <RegisterPage />} />
      <Route path="/verify-email" element={user ? <Navigate to="/agents" replace /> : <VerifyEmailPage />} />
      <Route path="/agents" element={<ProtectedRoute><AgentsPage /></ProtectedRoute>} />
      <Route path="/appointments" element={<ProtectedRoute><AppointmentsPage /></ProtectedRoute>} />
      <Route path="/chat-history" element={<ProtectedRoute><ChatHistoryPage /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/agents" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}
