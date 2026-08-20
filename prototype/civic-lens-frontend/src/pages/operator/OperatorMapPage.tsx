import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getMasterIssues } from '../../api/issues';
import { CivicMap } from '../../components/maps/CivicMap';
import { MapPin, Filter, Search, ShieldAlert, Clock } from 'lucide-react';
import { DEPARTMENTS } from '../../constants/departments';

export const OperatorMapPage: React.FC = () => {
  const { data: issues, isLoading, isError } = useQuery({
    queryKey: ['operatorMapIssues'],
    queryFn: getMasterIssues,
    retry: 1,
  });

  const [selectedDept, setSelectedDept] = useState<string>('ALL');
  const [selectedPriority, setSelectedPriority] = useState<string>('ALL');
  const [activeIssueId, setActiveIssueId] = useState<string | null>(null);

  const filteredIssues = useMemo(() => {
    if (!issues) return [];
    return issues.filter(issue => {
      if (selectedDept !== 'ALL' && issue.department !== selectedDept) return false;
      if (selectedPriority !== 'ALL') {
        const p = issue.severity_score === 5 ? 'CRITICAL' : issue.severity_score === 4 ? 'HIGH' : issue.severity_score === 3 ? 'MEDIUM' : 'LOW';
        if (p !== selectedPriority) return false;
      }
      return true;
    });
  }, [issues, selectedDept, selectedPriority]);

  const mapPins = useMemo(() => {
    return filteredIssues.map(issue => ({
      id: issue.id,
      lat: issue.latitude || 20.2961,
      lng: issue.longitude || 85.8245,
      title: issue.title || 'Civic Issue',
      category: issue.department || 'General',
      status: issue.status || 'UNKNOWN',
      priority: issue.severity_score === 5 ? 'CRITICAL' : issue.severity_score === 4 ? 'HIGH' : issue.severity_score === 3 ? 'MEDIUM' : 'LOW',
      department: issue.department || 'Other'
    }));
  }, [filteredIssues]);



  return (
    <div className="max-w-[1600px] mx-auto py-4 px-4 sm:px-6 h-[calc(100vh-4rem)] flex flex-col space-y-4">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white/80 border border-slate-200 p-4 rounded-lg shrink-0">
        <div>
          <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <MapPin className="w-5 h-5 text-blue-400" /> Operational Issue Map
          </h1>
          <p className="text-xs text-slate-600">Geospatial overview of municipal issues and dispatch locations.</p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <Filter className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 transform -translate-y-1/2" />
            <select
              value={selectedDept}
              onChange={(e) => setSelectedDept(e.target.value)}
              className="bg-white border border-slate-200 rounded-xl pl-9 pr-8 py-2 text-xs text-slate-900 focus:border-blue-500/50 outline-none appearance-none cursor-pointer"
            >
              <option value="ALL">All Departments</option>
              {DEPARTMENTS.map(d => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>

          <div className="relative">
            <ShieldAlert className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 transform -translate-y-1/2" />
            <select
              value={selectedPriority}
              onChange={(e) => setSelectedPriority(e.target.value)}
              className="bg-white border border-slate-200 rounded-xl pl-9 pr-8 py-2 text-xs text-slate-900 focus:border-blue-500/50 outline-none appearance-none cursor-pointer"
            >
              <option value="ALL">All Priorities</option>
              <option value="HIGH">High Priority</option>
              <option value="MEDIUM">Medium Priority</option>
              <option value="LOW">Low Priority</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-grow flex gap-4 min-h-0">
        {/* Map Area */}
        <div className="flex-grow bg-white/60 border border-slate-200 rounded-lg overflow-hidden relative">
          <CivicMap
            center={[20.2961, 85.8245]}
            zoom={12}
            pins={mapPins}
            className="w-full h-full"
            interactivePinPicker={false}
            selectedPinId={activeIssueId}
            onPinSelect={(id) => setActiveIssueId(id)}
          />
          
          {/* Map Legend Overlay */}
          <div className="absolute bottom-4 left-4 z-[1000] bg-white/90 border border-slate-300 p-3 rounded-xl shadow-xl pointer-events-none">
            <span className="text-[10px] font-bold text-slate-600 uppercase tracking-wider mb-2 block">Priority Legend</span>
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-red-500 border border-red-200"></div><span className="text-xs text-slate-900">Critical (Score 5)</span></div>
              <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-orange-500 border border-orange-200"></div><span className="text-xs text-slate-900">High (Score 4)</span></div>
              <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-amber-400 border border-amber-100"></div><span className="text-xs text-slate-900">Medium (Score 3)</span></div>
              <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-emerald-500 border border-emerald-200"></div><span className="text-xs text-slate-900">Low (Score 1-2)</span></div>
            </div>
          </div>
          
          {isError && (
            <div className="absolute inset-0 bg-white/80 flex items-center justify-center z-[1000]">
              <div className="text-red-400 font-semibold flex flex-col items-center gap-2 p-6 bg-white rounded-lg border border-red-500/30 max-w-sm text-center">
                <ShieldAlert className="w-10 h-10 mb-2 opacity-80" />
                <span>Unable to load operational issues.</span>
                <span className="text-sm font-normal text-slate-700 mt-1">Check that the CivicLens backend is running and accessible.</span>
              </div>
            </div>
          )}
          {isLoading && (
            <div className="absolute inset-0 bg-white/50 flex items-center justify-center z-[1000]">
              <div className="text-slate-900 font-semibold flex items-center gap-2">
                <Clock className="w-5 h-5 animate-spin" /> Loading geospatial data...
              </div>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="w-80 shrink-0 bg-white/80 border border-slate-200 rounded-lg p-4 flex flex-col h-full overflow-hidden">
          <h3 className="text-sm font-bold text-slate-900 mb-4 flex items-center gap-2 pb-3 border-b border-slate-200">
            <Search className="w-4 h-4 text-slate-600" /> Issue Directory ({filteredIssues.length})
          </h3>
          
          <div className="flex-grow overflow-y-auto pr-2 space-y-3 custom-scrollbar">
            {!isLoading && !isError && filteredIssues.length === 0 ? (
              <div className="text-center py-8 text-xs text-slate-500 flex flex-col items-center gap-3">
                <Search className="w-8 h-8 opacity-20" />
                No operational issues available matching criteria.
              </div>
            ) : (
              filteredIssues.map(issue => {
                const priorityStr = issue.severity_score === 5 ? 'CRITICAL' : issue.severity_score === 4 ? 'HIGH' : issue.severity_score === 3 ? 'MEDIUM' : 'LOW';
                return (
                  <div 
                    key={issue.id}
                    onClick={() => setActiveIssueId(issue.id)}
                    className={`p-3 rounded-xl border transition-all cursor-pointer ${
                      activeIssueId === issue.id 
                        ? 'bg-blue-600/10 border-blue-500/50' 
                        : 'bg-white/40 border-slate-200/80 hover:border-slate-600 hover:bg-white'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <span className="text-[10px] font-mono text-slate-500">#{issue.id.slice(-6)}</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold border ${
                        priorityStr === 'CRITICAL' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                        priorityStr === 'HIGH' ? 'bg-orange-500/10 text-orange-400 border-orange-500/20' :
                        priorityStr === 'MEDIUM' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
                        'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                      }`}>
                        {priorityStr}
                      </span>
                    </div>
                    <p className="text-xs font-semibold text-slate-900 line-clamp-2 mb-2">{issue.title}</p>
                    <div className="flex items-center gap-2 text-[10px]">
                      <span className="bg-slate-50 text-slate-700 px-2 py-0.5 rounded text-[9px] font-bold tracking-wide uppercase">
                        {issue.status?.replace(/_/g, ' ')}
                      </span>
                      <span className="text-slate-500 truncate">{issue.department}</span>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
