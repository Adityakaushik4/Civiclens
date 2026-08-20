import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getAnalyticsSummary } from '../../api/analytics';
import { Shield, BarChart3, MapPin, Coins, ArrowRight, Activity, Users, CheckCircle2 } from 'lucide-react';

export const PublicOverviewPage: React.FC = () => {
  const { data: analytics, isLoading } = useQuery({
    queryKey: ['analyticsSummary'],
    queryFn: () => getAnalyticsSummary(),
  });

  const totalReports = analytics?.total_citizen_reports ?? analytics?.total_master_issues ?? 0;
  const resolutionRate = analytics?.resolution_rate ?? 0;
  const slaBreachRate = analytics?.sla_breach_rate ?? 0;
  const slaCompliance = Math.max(0, Math.round((100 - slaBreachRate) * 10) / 10);

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 space-y-8">
      {/* Header */}
      <div className="bg-[#0F2747] rounded-xl p-8 relative overflow-hidden">
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-blue-600/10 rounded-full blur-3xl"></div>
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-4 max-w-2xl">
            <div className="flex items-center space-x-2">
              <Shield className="w-8 h-8 text-teal-400" />
              <h1 className="text-3xl font-bold text-white tracking-tight">CivicLens Public Overview</h1>
            </div>
            <p className="text-sm text-slate-300 leading-relaxed">
              Welcome to the CivicLens open governance portal. We believe in complete transparency, community-driven development, and data-backed accountability. Explore real-time municipal performance, ongoing civic projects, and participate in community budgeting.
            </p>
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-teal-900/40 border border-teal-700/50 rounded-full text-xs font-bold text-teal-300">
              <Shield className="w-3.5 h-3.5" /> Privacy-Preserving Open Data
            </div>
          </div>
        </div>
      </div>

      {/* High-Level Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white/80 border border-slate-200 rounded-lg p-6 shadow-sm">
          <div className="flex items-center space-x-3 mb-4">
            <div className="p-2.5 bg-blue-50 rounded-xl border border-blue-200">
              <Activity className="w-5 h-5 text-blue-600" />
            </div>
            <h3 className="text-xs font-bold text-slate-600 uppercase tracking-wider">Total Reports</h3>
          </div>
          <div className="text-3xl font-black text-slate-900 mb-1">
            {isLoading ? '...' : totalReports.toLocaleString()}
          </div>
          <p className="text-xs text-blue-600 flex items-center gap-1">
            <ArrowRight className="w-3 h-3 -rotate-45" /> Live Persisted Metrics
          </p>
        </div>

        <div className="bg-white/80 border border-slate-200 rounded-lg p-6 shadow-sm">
          <div className="flex items-center space-x-3 mb-4">
            <div className="p-2.5 bg-emerald-50 rounded-xl border border-emerald-200">
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            </div>
            <h3 className="text-xs font-bold text-slate-600 uppercase tracking-wider">Resolved Issues</h3>
          </div>
          <div className="text-3xl font-black text-slate-900 mb-1">
            {isLoading ? '...' : (analytics?.total_issues_resolved ?? 0).toLocaleString()}
          </div>
          <p className="text-xs text-emerald-600">{resolutionRate}% Resolution Rate</p>
        </div>

        <div className="bg-white/80 border border-slate-200 rounded-lg p-6 shadow-sm">
          <div className="flex items-center space-x-3 mb-4">
            <div className="p-2.5 bg-amber-50 rounded-xl border border-amber-200">
              <Users className="w-5 h-5 text-amber-600" />
            </div>
            <h3 className="text-xs font-bold text-slate-600 uppercase tracking-wider">Total Citizen Submissions</h3>
          </div>
          <div className="text-3xl font-black text-slate-900 mb-1">
            {isLoading ? '...' : totalReports.toLocaleString()}
          </div>
          <p className="text-xs text-slate-600">Total citizen complaint reports logged</p>
        </div>

        <div className="bg-white/80 border border-slate-200 rounded-lg p-6 shadow-sm">
          <div className="flex items-center space-x-3 mb-4">
            <div className="p-2.5 bg-slate-100 rounded-xl border border-slate-300">
              <Shield className="w-5 h-5 text-slate-700" />
            </div>
            <h3 className="text-xs font-bold text-slate-600 uppercase tracking-wider">SLA Compliance</h3>
          </div>
          <div className="text-3xl font-black text-slate-900 mb-1">
            {isLoading ? '...' : `${slaCompliance}%`}
          </div>
          <p className="text-xs text-emerald-600 flex items-center gap-1">
            <ArrowRight className="w-3 h-3 -rotate-45" /> Deterministic SLA Policy
          </p>
        </div>
      </div>

      {/* Navigation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Transparency */}
        <Link to="/public/transparency" className="group bg-white hover:bg-slate-50 border border-slate-200 rounded-xl p-6 transition-all shadow-sm flex flex-col h-full">
          <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl w-fit mb-4 group-hover:scale-110 transition-transform">
            <BarChart3 className="w-6 h-6 text-blue-600" />
          </div>
          <h3 className="text-xl font-bold text-slate-900 mb-2">Civic Transparency</h3>
          <p className="text-sm text-slate-600 mb-6 flex-grow">
            Dive deep into municipal performance metrics, resolution times, and department-level SLA compliance data.
          </p>
          <div className="flex items-center text-blue-600 text-sm font-bold mt-auto">
            View Dashboard <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>

        {/* Hotspots */}
        <Link to="/public/hotspots" className="group bg-white hover:bg-slate-50 border border-slate-200 rounded-xl p-6 transition-all shadow-sm flex flex-col h-full">
          <div className="p-3 bg-red-50 border border-red-200 rounded-xl w-fit mb-4 group-hover:scale-110 transition-transform">
            <MapPin className="w-6 h-6 text-red-600" />
          </div>
          <h3 className="text-xl font-bold text-slate-900 mb-2">Hotspot Projects</h3>
          <p className="text-sm text-slate-600 mb-6 flex-grow">
            Discover active civic interventions derived from clustered issue reports. See where major repairs and upgrades are happening.
          </p>
          <div className="flex items-center text-red-600 text-sm font-bold mt-auto">
            Explore Hotspots <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>

        {/* Participatory Budget */}
        <Link to="/public/budget" className="group bg-white hover:bg-slate-50 border border-slate-200 rounded-xl p-6 transition-all shadow-sm flex flex-col h-full">
          <div className="p-3 bg-teal-50 border border-teal-200 rounded-xl w-fit mb-4 group-hover:scale-110 transition-transform">
            <Coins className="w-6 h-6 text-teal-600" />
          </div>
          <h3 className="text-xl font-bold text-slate-900 mb-2">Participatory Budget</h3>
          <p className="text-sm text-slate-600 mb-6 flex-grow">
            Vote on community-proposed infrastructure projects and influence how municipal funds are allocated in your ward.
          </p>
          <div className="flex items-center text-teal-600 text-sm font-bold mt-auto">
            View Proposals <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>
      </div>
    </div>
  );
};
