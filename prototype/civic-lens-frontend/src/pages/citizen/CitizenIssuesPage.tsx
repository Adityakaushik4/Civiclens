import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getMasterIssues } from '../../api/issues';
import { FileText, MapPin, ArrowRight, ShieldCheck } from 'lucide-react';

export const CitizenIssuesPage: React.FC = () => {
  const { data: masterIssues, isLoading } = useQuery({
    queryKey: ['masterIssues'],
    queryFn: getMasterIssues,
  });

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 sm:px-6 space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">My Reported Issues</h1>
          <p className="text-xs text-slate-600">Track real-time resolution status and department SLA timers</p>
        </div>

        <Link
          to="/citizen/report"
          className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-slate-900 font-semibold text-xs flex items-center gap-1.5 self-start transition-all shadow-lg shadow-sm"
        >
          Report New Issue <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-slate-500 text-xs">Loading reported issues...</div>
      ) : masterIssues && masterIssues.length > 0 ? (
        <div className="grid grid-cols-1 gap-4">
          {masterIssues.map((issue) => (
            <div
              key={issue.id}
              className="bg-white border border-slate-200 rounded-lg p-6 hover:border-slate-300 transition-all space-y-4 shadow-sm"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="font-mono text-xs text-blue-700 font-bold bg-blue-50 px-2.5 py-1 rounded-full border border-blue-200">
                    {issue.id}
                  </span>
                  <span className="bg-slate-100 text-slate-700 text-xs px-2.5 py-1 rounded-full font-medium">
                    {issue.category}
                  </span>
                </div>
                <span className={`text-xs font-bold px-3 py-1 rounded-full border ${
                  issue.status === 'RESOLVED' || issue.status === 'CLOSED' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                  issue.status === 'ROUTED' || issue.status === 'ACKNOWLEDGED' ? 'bg-blue-50 text-blue-700 border-blue-200' :
                  issue.status === 'IN_PROGRESS' || issue.status === 'OVERDUE' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                  'bg-slate-50 text-slate-700 border-slate-200'
                }`}>
                  {issue.status}
                </span>
              </div>

              <div>
                <h3 className="text-base font-bold text-slate-900">{issue.title}</h3>
                {issue.description && (
                  <p className="text-sm text-slate-700 mt-2 line-clamp-2">{issue.description}</p>
                )}
                <p className="text-xs text-slate-600 mt-1 flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5 text-red-400" /> Lat: {issue.latitude.toFixed(4)}, Lng: {issue.longitude.toFixed(4)}
                </p>
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-slate-200 text-xs">
                <span className="text-slate-600 flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-blue-400" /> {issue.citizen_reporter_count} Citizen Reports
                </span>
                <Link
                  to={`/citizen/issues/${issue.id}`}
                  className="text-blue-600 hover:text-blue-800 font-semibold flex items-center gap-1"
                >
                  View Details & Timeline <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white/60 border border-slate-200 rounded-xl p-12 text-center space-y-4">
          <FileText className="w-12 h-12 text-slate-600 mx-auto" />
          <h3 className="text-lg font-bold text-slate-900">No Issues Reported Yet</h3>
          <p className="text-xs text-slate-600 max-w-sm mx-auto">
            You have not submitted any complaints yet. Report an issue to help improve your neighborhood!
          </p>
          <Link
            to="/citizen/report"
            className="px-6 py-3 rounded-xl bg-blue-700 hover:bg-blue-800 text-white font-semibold text-xs inline-block shadow-sm"
          >
            Report an Issue Now
          </Link>
        </div>
      )}
    </div>
  );
};
