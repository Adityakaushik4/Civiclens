import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth, type UserRole } from '../../context/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactElement;
  allowedRoles?: UserRole[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
  const { isAuthenticated, role, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && allowedRoles.length > 0 && !allowedRoles.includes(role)) {
    // Redirect to default home page based on actual authenticated role
    if (role === 'citizen') return <Navigate to="/citizen/issues" replace />;
    if (role === 'operator') return <Navigate to="/operator" replace />;
    if (role === 'supervisor') return <Navigate to="/supervisor" replace />;
    if (role === 'admin') return <Navigate to="/admin" replace />;
    return <Navigate to="/public" replace />;
  }

  return children;
};
