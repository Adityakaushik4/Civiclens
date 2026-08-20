import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getAnalyticsSummary, getAnalyticsHotspots } from '../../api/analytics';
import { CivicMap } from '../../components/maps/CivicMap';
import { mapValidPublicHotspots } from '../../utils/hotspotMapper';
import { MapPin, Lock, AlertCircle } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

export const PublicDashboardPage: React.FC = () => {
  const { data: analytics } = useQuery({
    queryKey: ['analyticsSummary'],
    queryFn: () => getAnalyticsSummary(),
  });

  const { data: hotspots } = useQuery({
    queryKey: ['analyticsHotspots'],
    queryFn: () => getAnalyticsHotspots(),
  });

  const categoryChartData = analytics?.category_counts
    ? Object.entries(analytics.category_counts).map(([cat, count]) => ({
        name: cat.replace('_', ' '),
        value: count,
      }))
    : [];

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444'];

  const mapHotspots = mapValidPublicHotspots(hotspots);

  const totalComplaints = analytics?.total_citizen_reports ?? analytics?.total_master_issues ?? 0;
  const totalResolved = analytics?.total_issues_resolved ?? 0;
  const resolutionRate = analytics?.resolution_rate_percent ?? analytics?.resolution_rate ?? 0;
  const slaCompliance = analytics?.sla_compliance_percent ?? (analytics ? Math.max(0, Math.round((100 - (analytics.sla_breach_rate || 0)) * 10) / 10) : 0);
  const avgResolutionHours = analytics?.average_resolution_hours ?? 0;

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 space-y-8">
      {/* Privacy Notice Banner (Section 3.G & Section 12) */}
      <div className="bg-blue-600/10 border border-blue-500/20 rounded-lg p-4 flex items-center justify-between text-xs text-blue-700">
        <div className="flex items-center space-x-2">
          <Lock className="w-4 h-4 text-blue-400 flex-shrink-0" />
          <span>
            <strong>Privacy Guarantee:</strong> All public coordinates are spatially fuzzed to protecting citizen anonymity. Complainant identities and internal notes are strictly redacted.
          </span>
        </div>
        <span className="font-mono text-emerald-400 font-semibold hidden sm:inline">PG-VECTOR ANONYMIZED</span>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Public Civic Transparency Dashboard</h1>
          <p className="text-xs text-slate-600">Open municipal data, SLA performance, and spatial civic hotspots</p>
        </div>
      </div>

      {/* Analytics Snapshot Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white/80 border border-slate-200 rounded-lg p-5 space-y-2">
          <span className="text-xs text-slate-600 uppercase tracking-wider font-medium">Total Complaints</span>
          <p className="text-3xl font-extrabold text-slate-900">{totalComplaints.toLocaleString()}</p>
          <span className="text-xs text-slate-500">Jurisdiction: Ward 7</span>
        </div>

        <div className="bg-white/80 border border-slate-200 rounded-lg p-5 space-y-2">
          <span className="text-xs text-slate-600 uppercase tracking-wider font-medium">Verified Resolved</span>
          <p className="text-3xl font-extrabold text-emerald-400">{totalResolved.toLocaleString()}</p>
          <span className="text-xs text-emerald-400 font-semibold">
            {resolutionRate}% Resolution Rate
          </span>
        </div>

        <div className="bg-white/80 border border-slate-200 rounded-lg p-5 space-y-2">
          <span className="text-xs text-slate-600 uppercase tracking-wider font-medium">SLA Compliance</span>
          <p className="text-3xl font-extrabold text-amber-400">{slaCompliance}%</p>
          <span className="text-xs text-slate-500">Target Resolution: &lt; 24h</span>
        </div>

        <div className="bg-white/80 border border-slate-200 rounded-lg p-5 space-y-2">
          <span className="text-xs text-slate-600 uppercase tracking-wider font-medium">Avg Resolution Time</span>
          <p className="text-3xl font-extrabold text-purple-400">{avgResolutionHours} hrs</p>
          <span className="text-xs text-purple-300 font-medium">Automated Dispatch</span>
        </div>
      </div>

      {/* Charts & Hotspot Map */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Category Distribution Chart */}
        <div className="lg:col-span-5 bg-white/80 border border-slate-200 rounded-xl p-6 space-y-4">
          <h3 className="text-base font-bold text-slate-900">Complaint Distribution by Category</h3>
          {categoryChartData.length > 0 ? (
            <>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={categoryChartData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={90}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {categoryChartData.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs">
                {categoryChartData.map((item, idx) => (
                  <div key={item.name} className="flex items-center space-x-2">
                    <span className="w-3 h-3 rounded-full inline-block" style={{ backgroundColor: COLORS[idx % COLORS.length] }} />
                    <span className="text-slate-700 font-medium truncate">{item.name}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="h-64 flex items-center justify-center text-xs text-slate-500">
              No category distribution data available yet.
            </div>
          )}
        </div>

        {/* Hotspot Cluster Map */}
        <div className="lg:col-span-7 bg-white/80 border border-slate-200 rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <MapPin className="w-4 h-4 text-red-400" /> Spatial Civic Hotspots (Fuzzed)
            </h3>
            <span className="text-xs text-slate-600">Cluster Density Threshold &ge; 5</span>
          </div>

          {mapHotspots.length > 0 ? (
            <CivicMap
              center={[20.2961, 85.8245]}
              hotspots={mapHotspots}
              className="h-80 w-full rounded-lg overflow-hidden border border-slate-200 shadow-xl"
            />
          ) : (
            <div className="h-80 w-full rounded-lg border border-slate-200 shadow-xl bg-white/50 flex flex-col items-center justify-center text-slate-600 p-6 text-center space-y-3">
              <AlertCircle className="w-8 h-8 text-slate-500 mb-2" />
              <p className="font-medium text-slate-700">No public hotspots available</p>
              <p className="text-xs">There are currently no civic hotspots meeting the density threshold for public display, or they are suppressed for privacy.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
