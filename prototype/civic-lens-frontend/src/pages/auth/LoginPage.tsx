import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { loginUser } from '../../api/auth';
import { LogIn, Shield, AlertCircle } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please fill in all fields.');
      return;
    }
    setError(null);
    setSubmitting(true);

    try {
      const res = await loginUser(email, password);
      login(res.access_token, res.user);

      // Redirect according to authenticated user's role
      const userRole = res.user.role.toUpperCase();
      if (userRole === 'ADMIN') {
        navigate('/admin');
      } else if (userRole === 'SUPERVISOR') {
        navigate('/supervisor');
      } else if (userRole === 'OPERATOR') {
        navigate('/operator');
      } else {
        navigate('/citizen/issues');
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Invalid email or password. Please try again.';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleQuickLogin = (demoEmail: string, demoPwd: string) => {
    setEmail(demoEmail);
    setPassword(demoPwd);
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 py-12 bg-slate-50">
      <div className="max-w-md w-full space-y-8 bg-white p-8 rounded-xl border border-slate-200 shadow-xl">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 rounded-xl bg-blue-900 flex items-center justify-center text-white mb-4 shadow-sm">
            <Shield className="h-6 w-6" />
          </div>
          <h2 className="text-2xl font-bold text-slate-900">Sign in to CivicLens</h2>
          <p className="mt-2 text-sm text-slate-600">
            Access your authorized municipal workspace
          </p>
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center gap-3 text-red-400 text-sm">
            <AlertCircle className="h-5 w-5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-800 uppercase tracking-wider mb-2">
                Email Address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="user@civiclens.gov"
                className="w-full px-4 py-3 bg-white border border-slate-300 rounded-xl text-slate-900 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-800 uppercase tracking-wider mb-2">
                Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-4 py-3 bg-white border border-slate-300 rounded-xl text-slate-900 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-blue-700 hover:bg-blue-800 text-white font-medium shadow-md transition-all disabled:opacity-50"
          >
            <LogIn className="h-4 w-4" />
            <span>{submitting ? 'Signing in...' : 'Sign In'}</span>
          </button>
        </form>

        <div className="pt-4 border-t border-slate-200 text-center">
          <p className="text-sm text-slate-600">
            Don't have an account?{' '}
            <Link to="/register" className="text-blue-600 hover:underline font-medium">
              Register as Citizen
            </Link>
          </p>
        </div>

        {/* Development Quick Accounts */}
        <div className="pt-4 border-t border-slate-200/60">
          <p className="text-xs font-semibold text-slate-600 mb-2 uppercase tracking-wider">
            Development Quick Login:
          </p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <button
              onClick={() => handleQuickLogin('citizen@civiclens.gov', 'citizen123')}
              className="p-2 bg-white/60 hover:bg-slate-50 border border-slate-200 rounded-lg text-left text-slate-700"
            >
              <span className="font-semibold text-blue-400 block">Citizen</span>
              citizen@civiclens.gov
            </button>
            <button
              onClick={() => handleQuickLogin('operator@civiclens.gov', 'operator123')}
              className="p-2 bg-white/60 hover:bg-slate-50 border border-slate-200 rounded-lg text-left text-slate-700"
            >
              <span className="font-semibold text-emerald-400 block">Operator</span>
              operator@civiclens.gov
            </button>
            <button
              onClick={() => handleQuickLogin('supervisor@civiclens.gov', 'supervisor123')}
              className="p-2 bg-white/60 hover:bg-slate-50 border border-slate-200 rounded-lg text-left text-slate-700"
            >
              <span className="font-semibold text-amber-400 block">Supervisor</span>
              supervisor@civiclens.gov
            </button>
            <button
              onClick={() => handleQuickLogin('admin@civiclens.gov', 'admin123')}
              className="p-2 bg-white/60 hover:bg-slate-50 border border-slate-200 rounded-lg text-left text-slate-700"
            >
              <span className="font-semibold text-purple-400 block">Admin</span>
              admin@civiclens.gov
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
