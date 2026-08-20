import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth, type UserRole } from '../../context/AuthContext';
import { Shield, Sparkles, LogOut, LogIn, User as UserIcon, Globe } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { role, user, isAuthenticated, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const roleNavItems: Record<UserRole, Array<{ path: string; label: string }>> = {
    public: [
      { path: '/public', label: 'Overview' },
      { path: '/public/transparency', label: 'Transparency' },
      { path: '/public/hotspots', label: 'Hotspot Projects' },
      { path: '/public/budget', label: 'Participatory Budget' },
    ],
    citizen: [
      { path: '/', label: 'Home' },
      { path: '/citizen/report', label: 'Report Issue' },
      { path: '/citizen/issues', label: 'My Issues' },
      { path: '/citizen/proposals', label: 'Proposals' },
      { path: '/citizen/voting', label: 'Voting' },
      { path: '/public', label: 'Public Portal' },
    ],
    operator: [
      { path: '/operator', label: 'Issue Triage' },
      { path: '/operator/map', label: 'Public Map' },
      { path: '/public', label: 'Public Portal' },
    ],
    supervisor: [
      { path: '/supervisor', label: 'Dashboard' },
      { path: '/supervisor/evidence', label: 'Evidence Queue' },
      { path: '/public', label: 'Public Portal' },
    ],
    admin: [
      { path: '/admin', label: 'Governance' },
      { path: '/admin/rag', label: 'Knowledge Base (RAG)' },
      { path: '/public', label: 'Public Portal' },
    ],
  };

  const getRoleBadgeStyle = (userRole: string) => {
    switch (userRole.toUpperCase()) {
      case 'ADMIN':
        return 'bg-purple-500/20 text-purple-300 border-purple-500/30';
      case 'SUPERVISOR':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/30';
      case 'OPERATOR':
        return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
      default:
        return 'bg-blue-500/20 text-blue-700 border-blue-200';
    }
  };

  return (
    <header className="bg-blue-900 border-b border-blue-800 sticky top-0 z-[2000] transition-all">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-3 group">
            <div className="w-10 h-10 rounded-xl bg-white flex items-center justify-center shadow-md group-hover:scale-105 transition-transform">
              <Shield className="w-6 h-6 text-blue-900" />
            </div>
            <div>
              <div className="flex items-center space-x-1.5">
                <span className="font-bold text-xl tracking-tight text-white">CivicLens</span>
                <span className="bg-blue-800 text-blue-100 text-xs px-2 py-0.5 rounded-full font-medium border border-blue-700 flex items-center gap-1">
                  <Sparkles className="w-3 h-3" /> AI
                </span>
              </div>
              <p className="text-[10px] text-blue-200 font-medium tracking-wide">MUNICIPAL GOVERNANCE ENGINE</p>
            </div>
          </Link>

          {/* Dynamic role-based navigation links */}
          <nav className="hidden md:flex items-center space-x-1">
            {roleNavItems[role]?.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-blue-800 text-white border border-blue-700'
                      : 'text-blue-100 hover:text-white hover:bg-blue-800/50'
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>

          {/* User Auth Profile Controls */}
          <div className="flex items-center space-x-3">
            {isAuthenticated && user ? (
              <div className="flex items-center space-x-3">
                <div className="flex items-center space-x-2 bg-blue-800 border border-blue-700 rounded-xl px-3 py-1.5">
                  <UserIcon className="w-4 h-4 text-blue-200" />
                  <div className="flex flex-col text-left">
                    <span className="text-xs font-semibold text-white">{user.full_name}</span>
                    <span className="text-[10px] text-blue-200">{user.email}</span>
                  </div>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold border ${getRoleBadgeStyle(user.role)}`}>
                    {user.role}
                  </span>
                </div>
                <button
                  onClick={handleLogout}
                  className="px-3 py-1.5 rounded-xl bg-blue-800 hover:bg-blue-700 text-white text-xs font-medium border border-blue-700 flex items-center gap-1.5 transition-all"
                  title="Sign Out"
                >
                  <LogOut className="w-3.5 h-3.5" /> Sign Out
                </button>
              </div>
            ) : (
              <div className="flex items-center space-x-2">
                <Link
                  to="/public"
                  className="hidden sm:flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-medium text-blue-100 hover:text-white hover:bg-blue-800 transition-colors"
                >
                  <Globe className="w-3.5 h-3.5 text-blue-200" /> Public Portal
                </Link>
                <Link
                  to="/login"
                  className="px-3.5 py-1.5 rounded-xl bg-white hover:bg-slate-100 text-blue-900 text-xs font-bold shadow-md flex items-center gap-1.5 transition-all"
                >
                  <LogIn className="w-3.5 h-3.5" /> Sign In
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
