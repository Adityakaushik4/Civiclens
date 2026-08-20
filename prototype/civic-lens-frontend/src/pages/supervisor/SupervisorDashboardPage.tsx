import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getAnalyticsSummary } from '../../api/analytics';
import { getMasterIssues } from '../../api/issues';
import { Shield, Clock, CheckCircle2, RotateCcw, AlertTriangle, Building2 } from 'lucide-react';

export const SupervisorDashboardPage: React.FC = () => {
  const { data: analytics, isLoading: isAnalyticsLoading } = useQuery({
    queryKey: ['analyticsSummary'],
    queryFn: () => getAnalyticsSummary(),
  });

  const { data: issues, isLoading: isIssuesLoading } = useQuery({
    queryKey: ['masterIssues'],
    queryFn: () => getMasterIssues(),
  });

  const isLoading = isAnalyticsLoading || isIssuesLoading;

  const totalHandled = analytics?.total_master_issues ?? issues?.length ?? 0;
  const pendingVerification = analytics?.pending_verification_count ?? issues?.filter(i => i.status === 'AWAITING_VERIFICATION' || i.status === 'WORK_SUBMITTED').length ?? 0;
  const resolvedToday = analytics?.resolved_today_count ?? 0;
  const reopenedCount = analytics?.reopened_count ?? issues?.filter(i => i.status === 'REOPENED').length ?? 0;

  // Department distribution from real analytics department_distribution
  const deptDist: Record<string, number> = analytics?.department_distribution || {};
  const deptStats = Object.entries(deptDist).map(([dept, count]) => ({
    dept,
    count: count as number,
    percent: Math.min(100, Math.round(((count as number) / (totalHandled || 1)) * 100)),
  }));

  // Priority distribution from real analytics priority_distribution (CRITICAL, HIGH, MEDIUM, LOW)
  const priorityDist = analytics?.priority_distribution || {};
  const criticalCount = priorityDist['CRITICAL'] ?? 0;
  const highCount = priorityDist['HIGH'] ?? 0;
  const mediumCount = priorityDist['MEDIUM'] ?? 0;
  const lowCount = priorityDist['LOW'] ?? 0;

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 sm:px-6 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Supervisor Dashboard</h1>
        <p className="text-xs text-slate-600">Overview of department performance and evidence verification queue</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white/80 border border-slate-200 rounded-lg p-4 shadow-sm">
          <div className="flex items-center space-x-3 mb-2">
            <div className="p-2 bg-blue-500/10 rounded-lg border border-blue-500/20">
              <Shield className="w-5 h-5 text-blue-400" />
            </div>
            <h3 className="text-xs font-semibold text-slate-600 uppercase tracking-wider">Total Handled</h3>
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {isLoading ? '...' : totalHandled.toLocaleString()}
          </div>
        </div>

        <div className="bg-white/80 border border-slate-200 rounded-lg p-4 shadow-sm">
          <div className="flex items-center space-x-3 mb-2">
            <div className="p-2 bg-amber-500/10 rounded-lg border border-amber-500/20">
              <Clock className="w-5 h-5 text-amber-400" />
            </div>
            <h3 className="text-xs font-semibold text-slate-600 uppercase tracking-wider">Pending Verification</h3>
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {isLoading ? '...' : pendingVerification.toLocaleString()}
          </div>
        </div>

        <div className="bg-white/80 border border-slate-200 rounded-lg p-4 shadow-sm">
          <div className="flex items-center space-x-3 mb-2">
            <div className="p-2 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            </div>
            <h3 className="text-xs font-semibold text-slate-600 uppercase tracking-wider">Resolved Today</h3>
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {isLoading ? '...' : resolvedToday.toLocaleString()}
          </div>
        </div>

        <div className="bg-white/80 border border-slate-200 rounded-lg p-4 shadow-sm">
          <div className="flex items-center space-x-3 mb-2">
            <div className="p-2 bg-rose-500/10 rounded-lg border border-rose-500/20">
              <RotateCcw className="w-5 h-5 text-rose-400" />
            </div>
            <h3 className="text-xs font-semibold text-slate-600 uppercase tracking-wider">Reopened</h3>
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {isLoading ? '...' : reopenedCount.toLocaleString()}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Issues by Department */}
        <div className="lg:col-span-2 bg-white/80 border border-slate-200 rounded-xl p-6">
          <h2 className="text-sm font-bold text-slate-900 mb-4 flex items-center gap-2">
            <Building2 className="w-4 h-4 text-blue-400" /> Open Issues by Primary Department
          </h2>
          <div className="space-y-3">
            {deptStats.length > 0 ? (
              deptStats.map((stat) => (
                <div key={stat.dept} className="flex items-center justify-between text-xs">
                  <span className="text-slate-700 flex-1">{stat.dept}</span>
                  <div className="w-1/3 bg-slate-50 rounded-full h-1.5 mx-4">
                    <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${stat.percent}%` }}></div>
                  </div>
                  <span className="text-slate-900 font-medium w-8 text-right">{stat.count}</span>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-500">No open issue department data.</p>
            )}
          </div>
        </div>

        {/* Priority Breakdown */}
        <div className="bg-white/80 border border-slate-200 rounded-xl p-6">
          <h2 className="text-sm font-bold text-slate-900 mb-4 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400" /> Calculated Priority Status
          </h2>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl">
              <span className="text-xs font-bold text-rose-400">CRITICAL</span>
              <span className="text-sm font-bold text-slate-900">{criticalCount}</span>
            </div>
            <div className="flex items-center justify-between p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl">
              <span className="text-xs font-bold text-amber-400">HIGH</span>
              <span className="text-sm font-bold text-slate-900">{highCount}</span>
            </div>
            <div className="flex items-center justify-between p-3 bg-blue-500/10 border border-blue-500/20 rounded-xl">
              <span className="text-xs font-bold text-blue-400">MEDIUM</span>
              <span className="text-sm font-bold text-slate-900">{mediumCount}</span>
            </div>
            <div className="flex items-center justify-between p-3 bg-slate-500/10 border border-slate-500/20 rounded-xl">
              <span className="text-xs font-bold text-slate-600">LOW</span>
              <span className="text-sm font-bold text-slate-900">{lowCount}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
