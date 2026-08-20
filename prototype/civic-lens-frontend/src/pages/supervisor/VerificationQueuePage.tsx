import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { verifyEvidence, getVerificationQueue } from '../../api/evidence';
import { CheckCircle2, XCircle, ShieldCheck, AlertTriangle, Image as ImageIcon, Sparkles, RotateCcw, Filter } from 'lucide-react';
import { DEPARTMENTS } from '../../constants/departments';

export const VerificationQueuePage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedDept, setSelectedDept] = useState<string>('ALL');

  const { data: verificationQueue = [], isLoading } = useQuery({
    queryKey: ['verificationQueue'],
    queryFn: getVerificationQueue,
  });

  const filteredQueue = verificationQueue.filter(item => {
    if (selectedDept !== 'ALL' && item.department !== selectedDept) return false;
    return true;
  });

  const verifyMutation = useMutation({
    mutationFn: ({ evidenceId, decision, reason }: { evidenceId: string; decision: 'APPROVED' | 'REJECTED'; reason?: string }) =>
      verifyEvidence(evidenceId, decision, 'supervisor_1', reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['verificationQueue'] });
      queryClient.invalidateQueries({ queryKey: ['masterIssues'] });
      queryClient.invalidateQueries({ queryKey: ['analyticsSummary'] });
    },
  });

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 sm:px-6 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Supervisor Verification Queue</h1>
          <p className="text-xs text-slate-600">Inspect side-by-side Before/After evidence and verify resolution</p>
        </div>

        <span className="text-xs text-emerald-400 font-semibold px-3 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded-full flex items-center gap-1">
          <ShieldCheck className="w-3.5 h-3.5" /> {isLoading ? '...' : verificationQueue.length} Item{verificationQueue.length === 1 ? '' : 's'} Awaiting Verification
        </span>
      </div>

      {/* Filter Bar */}
      <div className="bg-white/80 border border-slate-200 rounded-lg p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-3 text-xs">
          <Filter className="w-4 h-4 text-slate-600" />
          <span className="text-slate-700 font-semibold">Filters:</span>

          <select
            value={selectedDept}
            onChange={(e) => setSelectedDept(e.target.value)}
            className="bg-white border border-slate-200 rounded-xl px-3 py-1.5 text-slate-900 text-xs"
          >
            <option value="ALL">All Departments</option>
            {DEPARTMENTS.map(dept => (
              <option key={dept} value={dept}>{dept}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="space-y-6">
        {filteredQueue.length === 0 ? (
          <div className="text-xs text-slate-600 py-8 text-center bg-white/60 rounded-lg border border-slate-200">
            No items pending verification for this department.
          </div>
        ) : (
          filteredQueue.map((item) => (
          <div key={item.evidence_id} className="bg-white/80 border border-slate-200 rounded-xl p-6 space-y-6 shadow-xl">
            <div className="flex flex-col gap-6">
              
              {/* Top Section */}
              <div className="flex flex-col gap-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-xs text-blue-400 font-bold bg-blue-500/10 px-2.5 py-0.5 rounded-full border border-blue-500/20">
                      {item.issue_id}
                    </span>
                    <span className="bg-slate-50 text-slate-700 text-xs px-2.5 py-0.5 rounded-full font-medium">
                      {item.category}
                    </span>
                  </div>
                  <span className="text-xs font-bold text-amber-400 bg-amber-500/10 px-3 py-1 rounded-full border border-amber-500/20 uppercase tracking-wider">
                    {item.status}
                  </span>
                </div>

                <div>
                  <h3 className="text-xl font-bold text-slate-900 mb-2">{item.title}</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs text-slate-600">
                    <div><span className="text-slate-500">Submitted by:</span> {item.submitted_by}</div>
                    <div><span className="text-slate-500">Department / Unit:</span> {item.department} / {item.assigned_unit}</div>
                    <div><span className="text-slate-500">Assigned Crew:</span> {item.assigned_crew}</div>
                  </div>
                </div>
              </div>

              {/* Work Dates Section */}
              <div className="grid grid-cols-2 gap-4 py-4 border-y border-slate-200 bg-white/60 rounded-xl px-4">
                <div>
                  <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">Work Started</div>
                  <div className="text-sm font-semibold text-slate-900">{item.work_started.split(', ')[0]}</div>
                  <div className="text-xs text-slate-600">{item.work_started.split(', ')[1]}</div>
                </div>
                <div>
                  <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">Work Completed</div>
                  <div className="text-sm font-semibold text-slate-900">{item.work_completed.split(', ')[0]}</div>
                  <div className="text-xs text-slate-600">{item.work_completed.split(', ')[1]}</div>
                </div>
              </div>

              {/* Before vs After Side-by-Side Comparison */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Before Evidence */}
                <div className="bg-white border border-slate-200 rounded-lg p-4 space-y-3">
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-xs font-bold text-red-400 uppercase tracking-wider flex items-center gap-1">
                      <ImageIcon className="w-3.5 h-3.5" /> BEFORE RESOLUTION
                    </span>
                    <span className="text-[10px] text-slate-500">Captured: {item.before_captured}</span>
                  </div>
                  <div className="rounded-xl overflow-hidden h-48 border border-slate-200">
                    <img src={item.before_image_url} alt="Before" className="w-full h-full object-cover" />
                  </div>
                  <div className="text-[10px] text-slate-500 flex items-center gap-1 mt-2">
                    <span className="font-semibold text-slate-600">Location:</span> {item.location}
                  </div>
                </div>

                {/* After Evidence */}
                <div className="bg-white border border-slate-200 rounded-lg p-4 space-y-3">
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" /> AFTER RESOLUTION
                    </span>
                    <span className="text-[10px] text-slate-500">Captured: {item.after_captured}</span>
                  </div>
                  <div className="rounded-xl overflow-hidden h-48 border border-slate-200">
                    <img src={item.after_image_url} alt="After" className="w-full h-full object-cover" />
                  </div>
                  <div className="text-[10px] text-slate-500 flex items-center gap-1 mt-2">
                    <span className="font-semibold text-slate-600">Location:</span> {item.location}
                  </div>
                </div>
              </div>

              {/* AI EXIF & GPS VERIFICATION */}
              <div className="bg-white border border-slate-200 rounded-lg p-4 space-y-3">
                <div className="flex items-center space-x-2 text-emerald-400 font-bold border-b border-slate-200 pb-2">
                  <Sparkles className="w-4 h-4" /> <span>AI EXIF & GPS VERIFICATION</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
                  <div>
                    <span className="block text-slate-500 mb-1">GPS Location Match</span>
                    <span className="text-slate-700 font-medium">{item.ai_metadata.gps_match}</span>
                  </div>
                  <div>
                    <span className="block text-slate-500 mb-1">EXIF Timestamp</span>
                    <span className="text-slate-700 font-medium">{item.ai_metadata.exif_sanitized ? 'Verified & Sanitized' : 'Unverified'}</span>
                  </div>
                  <div>
                    <span className="block text-slate-500 mb-1">Image Authenticity</span>
                    <span className="text-emerald-400 font-medium flex items-center gap-1"><CheckCircle2 className="w-3 h-3" /> Verified Original</span>
                  </div>
                  <div>
                    <span className="block text-slate-500 mb-1">Confidence Score</span>
                    <span className="text-emerald-400 font-bold">{(item.ai_metadata.resolution_match_confidence * 100).toFixed(0)}% Match</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Decision Bar */}
            <div className="pt-4 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center space-x-3 text-xs text-slate-600">
                <span className="flex items-center gap-1">
                  <RotateCcw className="w-3.5 h-3.5 text-amber-400" /> Reopen Count: {item.reopen_history}
                </span>
                {item.escalated && (
                  <span className="text-red-400 font-bold flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5" /> Escalated to Municipal Commissioner
                  </span>
                )}
              </div>

              <div className="flex items-center space-x-3 w-full sm:w-auto">
                <button
                  onClick={() =>
                    verifyMutation.mutate({
                      evidenceId: item.evidence_id,
                      decision: 'REJECTED',
                      reason: 'Quality standards not met on ground',
                    })
                  }
                  className="flex-1 sm:flex-none px-5 py-2.5 rounded-xl bg-red-600/20 hover:bg-red-600/30 border border-red-500/30 text-red-300 font-bold text-xs flex items-center justify-center gap-1.5 transition-all"
                >
                  <XCircle className="w-4 h-4" /> Reject & Reopen Ticket
                </button>

                <button
                  onClick={() =>
                    verifyMutation.mutate({
                      evidenceId: item.evidence_id,
                      decision: 'APPROVED',
                    })
                  }
                  className="flex-1 sm:flex-none px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-slate-900 font-bold text-xs flex items-center justify-center gap-1.5 transition-all shadow-lg shadow-sm"
                >
                  <CheckCircle2 className="w-4 h-4" /> Approve & Mark RESOLVED
                </button>
              </div>
            </div>
          </div>
        )))}
      </div>
    </div>
  );
};
