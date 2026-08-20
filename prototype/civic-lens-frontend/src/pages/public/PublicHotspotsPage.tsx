import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getProjectOpportunities } from '../../api/analytics';
import { MapPin, AlertCircle, TrendingUp, Users } from 'lucide-react';

export const PublicHotspotsPage: React.FC = () => {
  const { data: opportunities, isLoading } = useQuery({
    queryKey: ['projectOpportunities'],
    queryFn: () => getProjectOpportunities(),
  });

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
          <MapPin className="w-6 h-6 text-red-400" /> Civic Hotspot Projects
        </h1>
        <p className="text-xs text-slate-600">Discover active civic interventions derived from clustered issue reports.</p>
      </div>

      <div className="bg-white/80 border border-slate-200 rounded-xl p-6">
        <div className="space-y-4">
          {isLoading ? (
            <div className="text-center py-12 text-slate-600">Loading hotspot projects...</div>
          ) : opportunities && opportunities.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {opportunities.map((opp) => {
                const reportCount = opp.total_citizen_reports ?? opp.complaint_count ?? opp.linked_master_issue_ids?.length ?? 0;
                const areaDesc = opp.affected_area_description || (opp.category ? `${opp.category.replace('_', ' ')} Cluster` : 'Civic Cluster');
                const description = opp.description || `Spatial cluster containing ${reportCount} aggregated citizen report(s). Automated project opportunity detected for municipal planning.`;
                const department = opp.department || 'Municipal Services';
                
                return (
                  <div key={opp.opportunity_id} className="bg-white/60 border border-slate-200/80 rounded-lg p-5 flex flex-col h-full shadow-lg hover:shadow-red-500/5 transition-all">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs bg-red-500/10 text-red-400 px-2.5 py-0.5 rounded-full border border-red-500/20 font-bold flex items-center gap-1">
                        <AlertCircle className="w-3.5 h-3.5" /> {reportCount} Citizen Report{reportCount === 1 ? '' : 's'}
                      </span>
                      <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold truncate max-w-[150px]">{areaDesc}</span>
                    </div>
                    
                    <h3 className="font-bold text-slate-900 text-base mb-2 leading-snug">{opp.title}</h3>
                    <p className="text-xs text-slate-600 mb-4 flex-grow line-clamp-3">{description}</p>
                    
                    <div className="space-y-3 pt-4 border-t border-slate-200/60 mt-auto">
                      <div className="flex justify-between items-center text-xs">
                        <span className="text-slate-500 flex items-center gap-1"><Users className="w-3.5 h-3.5" /> Dept Involved</span>
                        <span className="text-slate-700 font-medium">{department}</span>
                      </div>
                      <div className="flex justify-between items-center text-xs">
                        <span className="text-slate-500 flex items-center gap-1"><TrendingUp className="w-3.5 h-3.5" /> Suggested Budget</span>
                        {opp.suggested_budget != null && !isNaN(Number(opp.suggested_budget)) ? (
                          <span className="text-emerald-400 font-bold">₹{(Number(opp.suggested_budget) / 100000).toFixed(2)} L</span>
                        ) : (
                          <span className="text-slate-600 font-normal italic">Budget estimate unavailable</span>
                        )}
                      </div>
                      
                      <button className="w-full mt-2 py-2 bg-slate-50 hover:bg-slate-700 text-slate-900 text-xs font-semibold rounded-xl transition-colors">
                        View Project Details
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="p-8 rounded-lg bg-white/40 border border-slate-200 text-sm text-slate-600 text-center">
              No civic hotspots identified matching the required reporting density threshold.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
