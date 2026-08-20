import React, { createContext, useContext, useState, useEffect } from 'react';
import { type User, getMe } from '../api/auth';

export type UserRole = 'public' | 'citizen' | 'operator' | 'supervisor' | 'admin';

interface AuthContextType {
  role: UserRole;
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
  adminKey: string;
  setAdminKey: (key: string) => void;
  userId: string;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(
    sessionStorage.getItem('civiclens_jwt_token') || localStorage.getItem('civiclens_jwt_token')
  );
  const [user, setUser] = useState<User | null>(() => {
    const cached = sessionStorage.getItem('civiclens_user') || localStorage.getItem('civiclens_user');
    if (cached) {
      try {
        return JSON.parse(cached);
      } catch {
        return null;
      }
    }
    return null;
  });
  const [loading, setLoading] = useState<boolean>(false);
  const [adminKey, setAdminKeyState] = useState<string>(
    localStorage.getItem('civiclens_admin_key') || 'admin-secret-key'
  );

  useEffect(() => {
    if (token && !user) {
      setLoading(true);
      getMe(token)
        .then((fetchedUser) => {
          setUser(fetchedUser);
          sessionStorage.setItem('civiclens_user', JSON.stringify(fetchedUser));
        })
        .catch(() => {
          logout();
        })
        .finally(() => {
          setLoading(false);
        });
    }
  }, [token]);

  const login = (newToken: string, newUser: User) => {
    setToken(newToken);
    setUser(newUser);
    sessionStorage.setItem('civiclens_jwt_token', newToken);
    sessionStorage.setItem('civiclens_user', JSON.stringify(newUser));
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    sessionStorage.removeItem('civiclens_jwt_token');
    localStorage.removeItem('civiclens_jwt_token');
    sessionStorage.removeItem('civiclens_user');
    localStorage.removeItem('civiclens_user');
  };

  const setAdminKey = (key: string) => {
    localStorage.setItem('civiclens_admin_key', key);
    setAdminKeyState(key);
  };

  const role: UserRole = user
    ? (user.role.toLowerCase() as UserRole)
    : 'public';

  const userId = user?.id || (role === 'operator' ? 'operator_1' : role === 'supervisor' ? 'supervisor_1' : 'citizen_1');
  const isAuthenticated = !!token && !!user;

  return (
    <AuthContext.Provider
      value={{
        role,
        user,
        token,
        isAuthenticated,
        login,
        logout,
        adminKey,
        setAdminKey,
        userId,
        loading,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
