import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './routes/ProtectedRoute';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import NotFound from './pages/NotFound';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Root redirects based on auth state is handled by Login/Dashboard */}
          <Route path="/" element={<RootRedirect />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

/**
 * Root route: redirects to dashboard or login.
 * Uses a lightweight component that reads auth state from context.
 */
function RootRedirect() {
  // We use a dynamic import approach — just check if token exists
  // The AuthContext will handle the actual redirect on render
  const token = localStorage.getItem('access_token');
  return token ? <Navigate to="/dashboard" replace /> : <Navigate to="/login" replace />;
}

export default App;