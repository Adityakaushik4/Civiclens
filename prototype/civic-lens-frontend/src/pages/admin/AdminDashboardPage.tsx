import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listSlaPolicies, listReopenPolicies, createSlaPolicy } from '../../api/admin';
import { Clock, ShieldAlert, Plus } from 'lucide-react';

export const AdminDashboardPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'sla' | 'reopen'>('sla');
  const [showSlaModal, setShowSlaModal] = useState(false);
  const [category, setCategory] = useState('ROAD_DAMAGE');
  const [ackMins, setAckMins] = useState(60);
  const [resMins, setResMins] = useState(1440);

  const { data: slaPolicies } = useQuery({
    queryKey: ['adminSlaPolicies'],
    queryFn: listSlaPolicies,
  });

  const { data: reopenPolicies } = useQuery({
    queryKey: ['adminReopenPolicies'],
    queryFn: listReopenPolicies,
  });

  const createSlaMutation = useMutation({
    mutationFn: () =>
      createSlaPolicy({
        jurisdiction_id: 'ward_7',
        category,
        priority_level: 'HIGH',
        acknowledgement_minutes: Number(ackMins),
        resolution_minutes: Number(resMins),
        status: 'ACTIVE',
        source_reference: 'Gazette-2026-PWD-Rule4',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminSlaPolicies'] });
      setShowSlaModal(false);
    },
  });

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Municipal Admin & Policy Governance</h1>
          <p className="text-xs text-slate-600">Configure SLA policies, reopen thresholds, and ingest statutory RAG documents</p>
        </div>

        <div className="flex items-center space-x-2 bg-white border border-slate-200 p-1.5 rounded-lg">
          <button
            onClick={() => setActiveTab('sla')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
              activeTab === 'sla' ? 'bg-blue-600 text-slate-900 shadow-md' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Clock className="w-3.5 h-3.5" /> SLA Policies
          </button>
          <button
            onClick={() => setActiveTab('reopen')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
              activeTab === 'reopen' ? 'bg-amber-600 text-slate-900 shadow-md' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5" /> Reopen Escalations
          </button>
        </div>
      </div>

      {/* SLA Policies Tab */}
      {activeTab === 'sla' && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-bold text-slate-900">Configured Municipal SLA Policies</h3>
            <button
              onClick={() => setShowSlaModal(true)}
              className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-slate-900 font-semibold text-xs flex items-center gap-1.5"
            >
              <Plus className="w-4 h-4" /> Add SLA Policy
            </button>
          </div>

          <div className="bg-white/80 border border-slate-200 rounded-xl overflow-hidden shadow-xl">
            <table className="w-full text-left text-xs text-slate-700">
              <thead className="bg-white text-slate-600 font-semibold border-b border-slate-200">
                <tr>
                  <th className="p-4">Policy ID</th>
                  <th className="p-4">Category</th>
                  <th className="p-4">Priority Level</th>
                  <th className="p-4">Ack Target</th>
                  <th className="p-4">Resolution Target</th>
                  <th className="p-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {slaPolicies && slaPolicies.length > 0 ? (
                  slaPolicies.map((pol) => (
                    <tr key={pol.policy_id} className="hover:bg-slate-50/40">
                      <td className="p-4 font-mono text-blue-400 font-bold">{pol.policy_id}</td>
                      <td className="p-4 font-semibold text-slate-900">{pol.category}</td>
                      <td className="p-4 text-amber-400 font-bold">{pol.priority_level}</td>
                      <td className="p-4">{pol.acknowledgement_minutes} mins</td>
                      <td className="p-4">{(pol.resolution_minutes / 60).toFixed(0)} hours</td>
                      <td className="p-4">
                        <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full font-bold">
                          {pol.status}
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="p-8 text-center text-slate-500">
                      No SLA policies configured yet. Click "Add SLA Policy" to create one.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Reopen Escalations Tab */}
      {activeTab === 'reopen' && (
        <div className="space-y-6">
          <h3 className="text-lg font-bold text-slate-900">Reopen Escalation Rules</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {reopenPolicies && reopenPolicies.length > 0 ? (
              reopenPolicies.map((p) => (
                <div key={p.policy_id} className="bg-white/80 border border-slate-200 rounded-xl p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900 text-sm">{p.policy_id}</span>
                    <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2.5 py-0.5 rounded-full font-semibold">
                      {p.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600">Target: {p.escalation_target}</p>
                  <div className="flex justify-between items-center text-xs pt-2 border-t border-slate-200">
                    <span className="text-slate-500">Reopen Threshold:</span>
                    <span className="text-amber-400 font-bold">{p.reopen_threshold} Reopens</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="col-span-2 bg-white/60 border border-slate-200 rounded-xl p-6 text-xs text-slate-500 text-center">
                No reopen policies configured.
              </div>
            )}
          </div>
        </div>
      )}


      {/* Add SLA Policy Modal */}
      {showSlaModal && (
        <div className="fixed inset-0 bg-white/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-xl p-6 max-w-md w-full space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Clock className="w-5 h-5 text-blue-400" /> Create SLA Policy
            </h3>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Category</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full bg-white border border-slate-200 rounded-xl p-3 text-slate-900"
                >
                  <option value="ROAD_DAMAGE">Road Damage</option>
                  <option value="GARBAGE_UNCOLLECTED">Garbage Uncollected</option>
                  <option value="STREETLIGHT_DEFECT">Streetlight Defect</option>
                  <option value="WATER_LEAKAGE">Water Leakage</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-700 font-semibold mb-1">Acknowledgement Target (Minutes)</label>
                <input
                  type="number"
                  value={ackMins}
                  onChange={(e) => setAckMins(Number(e.target.value))}
                  className="w-full bg-white border border-slate-200 rounded-xl p-3 text-slate-900"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-semibold mb-1">Resolution Target (Minutes)</label>
                <input
                  type="number"
                  value={resMins}
                  onChange={(e) => setResMins(Number(e.target.value))}
                  className="w-full bg-white border border-slate-200 rounded-xl p-3 text-slate-900"
                />
              </div>
            </div>

            <div className="flex justify-end space-x-3 pt-2">
              <button
                onClick={() => setShowSlaModal(false)}
                className="px-4 py-2 rounded-xl bg-slate-50 text-slate-700 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={() => createSlaMutation.mutate()}
                className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-slate-900 text-xs font-semibold"
              >
                Create Policy
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
