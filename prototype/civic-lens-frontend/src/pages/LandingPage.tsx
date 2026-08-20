import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getAnalyticsSummary, getProjectOpportunities } from '../api/analytics';
import { getPublicBudgetDashboard } from '../api/budgeting';
import {
  Mic,
  Image as ImageIcon,
  FileText,
  Sparkles,
  ArrowRight,
  TrendingUp,
  MapPin,
  CheckCircle,
  Clock,
  Coins,
  BrainCircuit,
  Eye,
} from 'lucide-react';

export const LandingPage: React.FC = () => {
  const { data: analytics } = useQuery({
    queryKey: ['analyticsSummary'],
    queryFn: () => getAnalyticsSummary(),
  });

  const { data: opportunities } = useQuery({
    queryKey: ['projectOpportunities'],
    queryFn: () => getProjectOpportunities(),
  });

  const { data: budgetData } = useQuery({
    queryKey: ['publicBudgetDashboard'],
    queryFn: () => getPublicBudgetDashboard('cycle_ward7_2027'),
  });

  return (
    <div className="space-y-16 py-8 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
      {/* Hero Section */}
      <section className="relative overflow-hidden rounded-xl bg-[#0F2747] border border-slate-700 p-8 sm:p-12 shadow-2xl">
        <div className="absolute top-0 right-0 -translate-y-12 translate-x-12 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-0 translate-y-12 -translate-x-12 w-96 h-96 bg-teal-600/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-7 space-y-6">
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-900/40 border border-blue-700/50 text-blue-300 text-xs font-semibold uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5 text-teal-400" /> SIH Municipal Intelligence Engine
            </div>

            <h1 className="text-4xl sm:text-6xl font-bold tracking-tight text-white leading-tight">
              AI-Powered Civic Redressal & Participatory Budgeting
            </h1>

            <p className="text-lg text-slate-300 leading-relaxed">
              Report civic complaints in any language via <span className="text-blue-300 font-medium">Text</span>,{' '}
              <span className="text-teal-400 font-medium">Voice</span>, or <span className="text-amber-400 font-medium">Photo</span>.
              CivicLens auto-classifies, detects duplicates, routes to departments, enforces SLAs, and empowers communities to allocate municipal funds.
            </p>

            <div className="flex flex-wrap gap-4 pt-2">
              <Link
                to="/citizen/report"
                className="px-6 py-3.5 rounded-xl bg-blue-700 hover:bg-blue-600 text-white font-semibold shadow-md flex items-center gap-2 transition-all transform hover:-translate-y-0.5"
              >
                Report Civic Issue <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                to="/public"
                className="px-6 py-3.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-100 font-semibold flex items-center gap-2 transition-all"
              >
                <Eye className="w-4 h-4 text-teal-400" /> Public Transparency
              </Link>
            </div>
          </div>

          <div className="lg:col-span-5 space-y-4">
            <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-md space-y-4">
              <h3 className="font-bold text-slate-900 text-sm tracking-wide uppercase flex items-center gap-2">
                <BrainCircuit className="w-4 h-4 text-blue-600" /> Multilingual AI Processing
              </h3>

              <div className="space-y-3">
                <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-2">
                    <FileText className="w-4 h-4 text-blue-600" />
                    <span className="text-slate-700 font-medium">Text Input (English, Hindi, Odia)</span>
                  </div>
                  <span className="text-teal-600 font-semibold">FastAPI Engine</span>
                </div>
                <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-2">
                    <Mic className="w-4 h-4 text-teal-600" />
                    <span className="text-slate-700 font-medium">Voice STT Audio Transcription</span>
                  </div>
                  <span className="text-teal-600 font-semibold">Gemini Audio</span>
                </div>
                <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-2">
                    <ImageIcon className="w-4 h-4 text-amber-500" />
                    <span className="text-slate-700 font-medium">Multimodal Vision & EXIF</span>
                  </div>
                  <span className="text-teal-600 font-semibold">Gemini Vision</span>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-200 flex items-center justify-between text-xs text-slate-600">
                <span>Duplicate Vector Match Score</span>
                <span className="text-blue-600 font-bold">0.85+ Spatial Threshold</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Live Civic Statistics */}
      <section className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Live Municipal Statistics</h2>
            <p className="text-sm text-slate-600">Real-time city performance and SLA compliance metrics</p>
          </div>
          <Link to="/public" className="text-xs text-blue-400 hover:text-blue-700 font-semibold flex items-center gap-1">
            View Analytics <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white/80 border border-slate-200 rounded-lg p-5 space-y-2">
            <div className="flex items-center justify-between text-slate-600">
              <span className="text-xs font-medium uppercase tracking-wider">Total Reported Issues</span>
              <FileText className="w-4 h-4 text-blue-400" />
            </div>
            <p className="text-3xl font-extrabold text-slate-900">{analytics?.total_issues_reported ?? 24}</p>
            <p className="text-xs text-emerald-400 font-medium flex items-center gap-1">
              <TrendingUp className="w-3 h-3" /> Updated in real-time
            </p>
          </div>

          <div className="bg-white/80 border border-slate-200 rounded-lg p-5 space-y-2">
            <div className="flex items-center justify-between text-slate-600">
              <span className="text-xs font-medium uppercase tracking-wider">Resolved Issues</span>
              <CheckCircle className="w-4 h-4 text-emerald-400" />
            </div>
            <p className="text-3xl font-extrabold text-emerald-400">{analytics?.total_issues_resolved ?? 18}</p>
            <p className="text-xs text-slate-600">
              {analytics?.resolution_rate_percent ?? 75}% Resolution Rate
            </p>
          </div>

          <div className="bg-white/80 border border-slate-200 rounded-lg p-5 space-y-2">
            <div className="flex items-center justify-between text-slate-600">
              <span className="text-xs font-medium uppercase tracking-wider">SLA Compliance</span>
              <Clock className="w-4 h-4 text-amber-400" />
            </div>
            <p className="text-3xl font-extrabold text-amber-400">{analytics?.sla_compliance_percent ?? 92}%</p>
            <p className="text-xs text-slate-600">Avg Resolution: {analytics?.average_resolution_hours ?? 18} hrs</p>
          </div>

          <div className="bg-white/80 border border-slate-200 rounded-lg p-5 space-y-2">
            <div className="flex items-center justify-between text-slate-600">
              <span className="text-xs font-medium uppercase tracking-wider">Active Budget Cycle</span>
              <Coins className="w-4 h-4 text-purple-400" />
            </div>
            <p className="text-3xl font-extrabold text-purple-400">
              ₹{((budgetData?.total_budget || 5000000) / 100000).toFixed(1)} Lakhs
            </p>
            <p className="text-xs text-purple-300 font-medium">Deterministic Priority-Ranked Budget Allocation</p>
          </div>
        </div>
      </section>

      {/* How CivicLens Works */}
      <section className="space-y-8 bg-white/60 border border-slate-200/80 rounded-xl p-8">
        <div className="text-center max-w-2xl mx-auto space-y-2">
          <h2 className="text-2xl font-bold text-slate-900">How CivicLens Works</h2>
          <p className="text-sm text-slate-600">A seamless 5-step automated workflow powered by Google Gemini AI</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
          <div className="bg-white/90 border border-slate-200 rounded-lg p-5 space-y-3 relative">
            <div className="w-8 h-8 rounded-xl bg-blue-100 text-blue-400 border border-blue-200 flex items-center justify-center font-bold text-sm">
              1
            </div>
            <h4 className="font-bold text-slate-900 text-sm">Citizen Reports</h4>
            <p className="text-xs text-slate-600">Submit text, spoken audio, or photo with GPS coordinates.</p>
          </div>

          <div className="bg-white/90 border border-slate-200 rounded-lg p-5 space-y-3 relative">
            <div className="w-8 h-8 rounded-xl bg-indigo-100 text-indigo-400 border border-indigo-200 flex items-center justify-center font-bold text-sm">
              2
            </div>
            <h4 className="font-bold text-slate-900 text-sm">AI Understanding</h4>
            <p className="text-xs text-slate-600">Gemini extracts category, severity score, and safety risk.</p>
          </div>

          <div className="bg-white/90 border border-slate-200 rounded-lg p-5 space-y-3 relative">
            <div className="w-8 h-8 rounded-xl bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 flex items-center justify-center font-bold text-sm">
              3
            </div>
            <h4 className="font-bold text-slate-900 text-sm">Duplicate Check</h4>
            <p className="text-xs text-slate-600">Matches nearby complaints into unified Master Issues.</p>
          </div>

          <div className="bg-white/90 border border-slate-200 rounded-lg p-5 space-y-3 relative">
            <div className="w-8 h-8 rounded-xl bg-amber-600/20 text-amber-400 border border-amber-500/30 flex items-center justify-center font-bold text-sm">
              4
            </div>
            <h4 className="font-bold text-slate-900 text-sm">Routing & SLA</h4>
            <p className="text-xs text-slate-600">Auto-routes to department with strict countdown SLA.</p>
          </div>

          <div className="bg-white/90 border border-slate-200 rounded-lg p-5 space-y-3 relative">
            <div className="w-8 h-8 rounded-xl bg-purple-600/20 text-purple-400 border border-purple-500/30 flex items-center justify-center font-bold text-sm">
              5
            </div>
            <h4 className="font-bold text-slate-900 text-sm">Evidence Verification</h4>
            <p className="text-xs text-slate-600">Supervisor inspects Before/After photos to resolve.</p>
          </div>
        </div>
      </section>

      {/* Hotspot Projects & Participatory Budgeting Showcase */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Hotspot Projects */}
        <div className="bg-white/80 border border-slate-200 rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-slate-900 text-lg flex items-center gap-2">
              <MapPin className="w-5 h-5 text-red-400" /> Hotspot-Derived Project Opportunities
            </h3>
            <Link to="/public/hotspots" className="text-xs text-blue-400 hover:underline">
              View All
            </Link>
          </div>

          <div className="space-y-3">
            {opportunities && opportunities.length > 0 ? (
              opportunities.slice(0, 3).map((opp) => (
                <div key={opp.opportunity_id} className="bg-white/60 border border-slate-200/80 rounded-xl p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-900 text-sm">{opp.title}</span>
                    <span className="text-xs bg-red-500/10 text-red-400 px-2 py-0.5 rounded-full border border-red-500/20 font-medium">
                      {opp.total_citizen_reports ?? opp.complaint_count ?? opp.linked_master_issue_ids?.length ?? 0} Complaints
                    </span>
                  </div>
                  <p className="text-xs text-slate-600">{opp.description || 'Spatial cluster opportunity detected.'}</p>
                  <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-200/60">
                    <span className="text-slate-500">{opp.affected_area_description || 'Ward 7'}</span>
                    {opp.suggested_budget != null && !isNaN(Number(opp.suggested_budget)) ? (
                      <span className="text-emerald-400 font-bold">Suggested: ₹{(Number(opp.suggested_budget) / 100000).toFixed(2)} L</span>
                    ) : (
                      <span className="text-slate-600 italic">Budget unavailable</span>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="p-4 rounded-xl bg-white/40 border border-slate-200 text-xs text-slate-600 text-center">
                3 Civic Hotspots identified in Ward 7 (Road Damage, Streetlight Defect, Drainage Overflow).
              </div>
            )}
          </div>
        </div>

        {/* Participatory Budgeting */}
        <div className="bg-white/80 border border-slate-200 rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-slate-900 text-lg flex items-center gap-2">
              <Coins className="w-5 h-5 text-purple-400" /> Ward 7 Participatory Budget Cycle
            </h3>
            <Link to="/citizen/budget" className="text-xs text-purple-400 hover:underline font-semibold">
              Vote Now
            </Link>
          </div>

          <div className="bg-white/60 border border-slate-200/80 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-600">Total Ward Allocation:</span>
              <span className="text-slate-900 font-bold">₹50,000,000</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-600">Allocation Strategy:</span>
              <span className="text-purple-400 font-semibold">Deterministic Priority-Ranked Budget Allocation</span>
            </div>
            <div className="w-full bg-slate-50 rounded-full h-2 overflow-hidden">
              <div className="bg-gradient-to-r from-blue-500 to-purple-500 h-full w-[65%]" />
            </div>
            <div className="flex items-center justify-between text-xs text-slate-600 pt-1">
              <span>Active Proposals: 8</span>
              <span className="text-emerald-400 font-medium">Voting Open</span>
            </div>
          </div>

          <div className="pt-2">
            <Link
              to="/citizen/proposals"
              className="w-full py-3 rounded-xl bg-purple-600/20 hover:bg-purple-600/30 border border-purple-500/30 text-purple-300 font-semibold text-xs flex items-center justify-center gap-2 transition-all"
            >
              <Sparkles className="w-3.5 h-3.5" /> Draft Proposal with AI Assistance
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
};
