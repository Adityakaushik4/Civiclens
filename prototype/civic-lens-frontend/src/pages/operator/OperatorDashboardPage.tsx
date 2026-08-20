import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMasterIssues, acknowledgeIssue, startWork, submitCompletion } from '../../api/issues';
import { uploadEvidence } from '../../api/evidence';
import {
  AlertTriangle,
  Clock,
  Building,
  CheckCircle2,
  Filter,
  Play,
  UserCheck,
  MapPin,
  ChevronRight,
  ShieldAlert,
} from 'lucide-react';
import { DEPARTMENTS } from '../../constants/departments';

export const OperatorDashboardPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedPriority, setSelectedPriority] = useState<string>('ALL');
  const [selectedDept, setSelectedDept] = useState<string>('ALL');
  const [activeIssueId, setActiveIssueId] = useState<string | null>(null);
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
  const [completionNotes, setCompletionNotes] = useState('');
  const [operatorErrorMessage, setOperatorErrorMessage] = useState<string | null>(null);

  const { data: issues, isLoading } = useQuery({
    queryKey: ['masterIssues'],
    queryFn: getMasterIssues,
  });

  const activeIssue = issues?.find(iss => iss.id === activeIssueId) || null;

  const filteredIssues = issues?.filter(iss => {
    if (selectedDept !== 'ALL' && iss.department !== selectedDept && iss.category !== selectedDept) return false;
    if (selectedPriority !== 'ALL') {
      const pLevel = iss.priority_level || (iss.severity_score === 5 ? 'CRITICAL' : iss.severity_score === 4 ? 'HIGH' : iss.severity_score === 3 ? 'MEDIUM' : 'LOW');
      if (selectedPriority !== pLevel) return false;
    }
    return true;
  });

  const overdueCount = issues?.filter(i => i.is_overdue || i.status === 'OVERDUE').length ?? 0;
  const activeQueueCount = issues?.filter(i => i.status === 'OPEN' || i.status === 'IN_PROGRESS' || i.status === 'ROUTED' || i.status === 'ACKNOWLEDGED').length ?? 0;
  const completedCount = issues?.filter(i => i.status === 'RESOLVED' || i.status === 'CLOSED' || i.status === 'WORK_SUBMITTED' || i.status === 'AWAITING_VERIFICATION').length ?? 0;

  const ackMutation = useMutation({
    mutationFn: (issueId: string) => acknowledgeIssue(issueId, 'operator_1', 'Acknowledged by dispatcher'),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['masterIssues'] }),
  });

  const startMutation = useMutation({
    mutationFn: (issueId: string) => startWork(issueId, 'operator_1', 'Field crew deployed on ground'),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['masterIssues'] }),
  });

  const submitMutation = useMutation({
    mutationFn: async (issueId: string) => {
      if (evidenceFile) {
        await uploadEvidence(issueId, 'AFTER_IMAGE', evidenceFile, 'operator_1');
      }
      await submitCompletion(issueId, 'operator_1', completionNotes || 'Work completed on ground');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['masterIssues'] });
      setActiveIssueId(null);
      setEvidenceFile(null);
    },
  });

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 space-y-8">
      {/* Header & SLA Summary Cards */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Municipal Operator Triage Dashboard</h1>
          <p className="text-xs text-slate-600">Manage issue assignment, field work execution, and SLA timers</p>
        </div>

        {/* SLA Status Badges */}
        <div className="flex items-center space-x-2 text-xs">
          <span className="px-3 py-1.5 rounded-xl bg-red-50 border border-red-200 text-red-700 font-bold flex items-center gap-1">
            <AlertTriangle className="w-3.5 h-3.5" /> {isLoading ? '...' : overdueCount} Overdue
          </span>
          <span className="px-3 py-1.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-700 font-bold flex items-center gap-1">
            <Clock className="w-3.5 h-3.5" /> {isLoading ? '...' : activeQueueCount} Active
          </span>
          <span className="px-3 py-1.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-700 font-bold flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" /> {isLoading ? '...' : completedCount} Completed
          </span>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white/80 border border-slate-200 rounded-lg p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-3 text-xs">
          <Filter className="w-4 h-4 text-slate-600" />
          <span className="text-slate-700 font-semibold">Filters:</span>

          <select
            value={selectedPriority}
            onChange={(e) => setSelectedPriority(e.target.value)}
            className="bg-white border border-slate-200 rounded-xl px-3 py-1.5 text-slate-900 text-xs"
          >
            <option value="ALL">All Priorities (Critical, High, Med, Low)</option>
            <option value="CRITICAL">Critical (Severity 4-5)</option>
            <option value="HIGH">High Priority (Severity 3)</option>
            <option value="MEDIUM">Medium Priority (Severity 2)</option>
            <option value="LOW">Low Priority (Severity 1)</option>
          </select>

          <select
            value={selectedDept}
            onChange={(e) => setSelectedDept(e.target.value)}
            className="bg-white border border-slate-200 rounded-xl px-3 py-1.5 text-slate-900 text-xs"
          >
            <option value="ALL">All Departments ({DEPARTMENTS.length})</option>
            {DEPARTMENTS.map(dept => (
              <option key={dept} value={dept}>{dept}</option>
            ))}
          </select>
        </div>

        <span className="text-xs text-slate-500 font-mono">Operator ID: operator_1 (Active)</span>
      </div>

      {/* Main Grid & Action Drawer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Issue List */}
        <div className="lg:col-span-7 space-y-4">
          <h3 className="text-base font-bold text-slate-900">Active Queue</h3>

          {isLoading ? (
            <div className="text-xs text-slate-500 py-8 text-center">Loading operator issue queue...</div>
          ) : filteredIssues && filteredIssues.length > 0 ? (
            filteredIssues.map((iss) => (
              <div
                key={iss.id}
                onClick={() => setActiveIssueId(iss.id)}
                className={`bg-white border rounded-lg p-5 cursor-pointer transition-all space-y-3 ${
                  activeIssueId === iss.id
                    ? 'border-blue-500 shadow-md ring-1 ring-blue-500'
                    : 'border-slate-200 hover:border-slate-300 shadow-sm'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-xs text-blue-700 font-bold bg-blue-50 px-2.5 py-0.5 rounded-full border border-blue-200">
                      {iss.id}
                    </span>
                    <span className="bg-slate-50 text-slate-700 text-xs px-2.5 py-0.5 rounded-full font-medium">
                      {iss.category}
                    </span>
                    {iss.department && (
                      <span className="bg-slate-50/80 text-blue-700 text-xs px-2.5 py-0.5 rounded-full font-medium border border-blue-500/20">
                        {iss.department}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center space-x-2">
                    {iss.priority_level && (
                      <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full border ${
                        iss.priority_level === 'CRITICAL' ? 'text-red-700 bg-red-50 border-red-200' :
                        iss.priority_level === 'HIGH' ? 'text-amber-700 bg-amber-50 border-amber-200' :
                        iss.priority_level === 'MEDIUM' ? 'text-blue-700 bg-blue-50 border-blue-200' :
                        'text-slate-700 bg-slate-50 border-slate-200'
                      }`}>
                        {iss.priority_level}
                      </span>
                    )}
                    <span className="text-xs font-bold text-slate-700 bg-slate-50/60 px-2.5 py-0.5 rounded-full border border-slate-300">
                      Sev: {iss.severity_score}/5
                    </span>
                  </div>
                </div>

                <h4 className="font-bold text-slate-900 text-sm">{iss.title}</h4>

                <div className="flex items-center justify-between text-xs text-slate-600 pt-2 border-t border-slate-200">
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5 text-red-400" /> Lat: {iss.latitude.toFixed(4)}, Lng: {iss.longitude.toFixed(4)}
                  </span>
                  <span className="text-blue-600 font-semibold flex items-center gap-1">
                    Action <ChevronRight className="w-3.5 h-3.5" />
                  </span>
                </div>
              </div>
            ))
          ) : (
            <div className="text-xs text-slate-600 py-8 text-center bg-white/60 rounded-lg border border-slate-200">
              No pending issues in queue.
            </div>
          )}
        </div>

        {/* Action Panel */}
        <div className="lg:col-span-5 space-y-4">
          <h3 className="text-base font-bold text-slate-900">Action Panel</h3>

          {activeIssue ? (
            <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-6 shadow-md sticky top-24">
              <div className="space-y-1">
                <span className="font-mono text-xs text-blue-700 font-bold">{activeIssue.id}</span>
                <h4 className="font-bold text-slate-900 text-base">{activeIssue.title}</h4>
                <p className="text-xs text-slate-600">Category: {activeIssue.category} ({activeIssue.subcategory})</p>
              </div>

              {/* Action Buttons */}
              <div className="space-y-3 pt-2">
                {activeIssue.status === 'ROUTED' ? (
                  <button
                    onClick={() => ackMutation.mutate(activeIssue.id)}
                    disabled={ackMutation.isPending}
                    className="w-full py-3 rounded-xl bg-blue-100 hover:bg-blue-600/30 border border-blue-200 text-blue-700 font-bold text-xs flex items-center justify-center gap-2 transition-all disabled:opacity-50"
                  >
                    <UserCheck className="w-4 h-4" /> 1. Acknowledge Ticket
                  </button>
                ) : (
                  <button disabled className="w-full py-3 rounded-xl bg-blue-900/20 border border-blue-900/30 text-blue-500 font-bold text-xs flex items-center justify-center gap-2 opacity-50 cursor-not-allowed">
                    <UserCheck className="w-4 h-4" /> ✓ Acknowledged
                  </button>
                )}

                {['ROUTED', 'ACKNOWLEDGED'].includes(activeIssue.status) ? (
                  <button
                    onClick={() => startMutation.mutate(activeIssue.id)}
                    disabled={activeIssue.status === 'ROUTED' || startMutation.isPending}
                    className="w-full py-3 rounded-xl bg-indigo-100 hover:bg-indigo-600/30 border border-indigo-200 text-indigo-700 font-bold text-xs flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Play className="w-4 h-4" /> 2. Start Work (Mark IN_PROGRESS)
                  </button>
                ) : (
                  <button disabled className="w-full py-3 rounded-xl bg-indigo-900/20 border border-indigo-900/30 text-indigo-500 font-bold text-xs flex items-center justify-center gap-2 opacity-50 cursor-not-allowed">
                    <Play className="w-4 h-4" /> ✓ Work Started / IN_PROGRESS
                  </button>
                )}

                {/* Evidence Upload */}
                {['ROUTED', 'ACKNOWLEDGED', 'IN_PROGRESS'].includes(activeIssue.status) ? (
                  <div className={`bg-white border border-slate-200 rounded-lg p-4 space-y-3 ${activeIssue.status !== 'IN_PROGRESS' ? 'opacity-50 pointer-events-none' : ''}`}>
                    {operatorErrorMessage && (
                      <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm flex items-center gap-3 mb-2">
                        <ShieldAlert className="w-5 h-5 flex-shrink-0" />
                        <span>{operatorErrorMessage}</span>
                      </div>
                    )}
                    <label className="block text-xs font-bold text-slate-700">3. Upload Resolution Evidence Photo</label>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(e) => {
                        if (e.target.files && e.target.files[0]) {
                          const file = e.target.files[0];
                          const maxBytes = 10 * 1024 * 1024; // 10 MB
                          if (file.size > maxBytes) {
                            setOperatorErrorMessage('Image is too large. Maximum allowed size is 10 MB.');
                            setEvidenceFile(null);
                            e.target.value = '';
                            return;
                          }
                          setOperatorErrorMessage(null);
                          setEvidenceFile(file);
                        }
                      }}
                      className="text-xs text-slate-600 file:mr-2 file:py-1 file:px-3 file:rounded-xl file:border-0 file:text-xs file:bg-slate-50 file:text-slate-900"
                    />
                    <p className="text-[10px] text-slate-400">Max size: 10MB</p>

                    <textarea
                      value={completionNotes}
                      onChange={(e) => setCompletionNotes(e.target.value)}
                      placeholder="Field completion notes..."
                      rows={2}
                      className="w-full bg-white border border-slate-200 rounded-xl p-2.5 text-slate-900 text-xs focus:outline-none"
                    />

                    <button
                      onClick={() => submitMutation.mutate(activeIssue.id)}
                      disabled={submitMutation.isPending || !evidenceFile}
                      className="w-full py-3 rounded-xl bg-teal-600 hover:bg-teal-700 text-slate-900 font-bold text-xs flex items-center justify-center gap-2 transition-all shadow-lg shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <CheckCircle2 className="w-4 h-4" /> Submit Completion (Awaiting Verification)
                    </button>
                  </div>
                ) : (
                  <div className="bg-white/60 border border-emerald-900/30 rounded-lg p-4 text-center">
                    <span className="text-emerald-500 font-bold text-xs flex items-center justify-center gap-2">
                      <CheckCircle2 className="w-4 h-4" /> Status: {activeIssue.status}
                    </span>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-white/60 border border-slate-200 rounded-xl p-8 text-center text-xs text-slate-500 space-y-2">
              <Building className="w-8 h-8 mx-auto text-slate-600" />
              <p>Select an issue from the queue to take operator action.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
