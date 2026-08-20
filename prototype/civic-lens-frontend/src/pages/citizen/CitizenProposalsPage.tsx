import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listProposals, generateAIDraftProposal, createProposal, getBudgetCycle, listOpportunities } from '../../api/budgeting';
import { useAuth } from '../../context/AuthContext';
import { Coins, Sparkles, ArrowRight, Loader2 } from 'lucide-react';

export const CitizenProposalsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { userId } = useAuth();
  const [showDraftModal, setShowDraftModal] = useState(false);
  const [selectedOpportunityId, setSelectedOpportunityId] = useState('');

  const { data: activeCycle } = useQuery({
    queryKey: ['activeBudgetCycle', 'cycle_ward7_2027'],
    queryFn: () => getBudgetCycle('cycle_ward7_2027'),
  });

  const { data: proposals, isLoading: proposalsLoading } = useQuery({
    queryKey: ['citizenProposals'],
    queryFn: () => listProposals(),
  });

  const { data: opportunities, isLoading: oppsLoading } = useQuery({
    queryKey: ['opportunities'],
    queryFn: () => listOpportunities(),
  });

  const aiDraftMutation = useMutation({
    mutationFn: () => generateAIDraftProposal(selectedOpportunityId, userId || 'citizen_1'),
    onSuccess: (draft) => {
      const opp = opportunities?.find(o => o.opportunity_id === draft.opportunity_id);
      createProposal({
        title: draft.suggested_title,
        description: draft.suggested_description,
        category: opp?.category || 'OTHER',
        opportunity_id: draft.opportunity_id,
        author_citizen_id: userId || 'citizen_1',
        requested_budget: opp?.suggested_budget || 1000000,
        linked_master_issue_ids: draft.linked_master_issue_ids,
      }).then(() => {
        queryClient.invalidateQueries({ queryKey: ['citizenProposals'] });
        setShowDraftModal(false);
        setSelectedOpportunityId('');
      });
    },
  });

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 sm:px-6 space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            {activeCycle?.cycle_name || 'Ward 7 Participatory Budget Cycle 2027'}
          </h1>
          <p className="text-xs text-slate-600">
            Propose municipal improvements and allocate Ward 7 community funds
            {activeCycle?.total_budget ? ` (Total Pool: ₹${(activeCycle.total_budget / 100000).toFixed(0)} Lakhs)` : ''}
          </p>
        </div>

        <button
          onClick={() => setShowDraftModal(true)}
          className="px-5 py-2.5 rounded-xl bg-blue-700 hover:bg-blue-800 text-white font-semibold text-xs flex items-center gap-2 transition-all shadow-md"
        >
          <Sparkles className="w-4 h-4" /> Draft Proposal with AI
        </button>
      </div>

      {/* Proposals Grid */}
      {proposalsLoading ? (
        <div className="text-center py-12 text-slate-500 text-xs">Loading citizen proposals...</div>
      ) : proposals && proposals.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {proposals.map((prop) => (
            <div
              key={prop.proposal_id}
              className="bg-white/80 border border-slate-200 rounded-xl p-6 hover:border-slate-300 transition-all space-y-4 flex flex-col justify-between"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200 px-2.5 py-1 rounded-full">
                    {prop.category}
                  </span>
                  <span className="text-xs text-emerald-400 font-semibold">{prop.status}</span>
                </div>

                <h3 className="text-base font-bold text-slate-900 leading-snug">{prop.title}</h3>
                <p className="text-xs text-slate-600 leading-relaxed line-clamp-3">{prop.description}</p>
              </div>

              <div className="pt-4 border-t border-slate-200 space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-500">Requested Budget:</span>
                  <span className="text-slate-900 font-bold">₹{(prop.requested_budget / 100000).toFixed(2)} Lakhs</span>
                </div>

                <Link
                  to={`/citizen/proposals/${prop.proposal_id}`}
                  className="w-full py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 font-semibold text-xs flex items-center justify-center gap-1.5 transition-colors"
                >
                  Inspect Score & Cast Vote <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white/60 border border-slate-200 rounded-xl p-12 text-center space-y-4">
          <Coins className="w-12 h-12 text-purple-400 mx-auto" />
          <h3 className="text-lg font-bold text-slate-900">No Proposals Submitted Yet</h3>
          <p className="text-xs text-slate-600 max-w-sm mx-auto">
            Be the first citizen to draft an AI-assisted proposal for Ward 7 infrastructure!
          </p>
          <button
            onClick={() => setShowDraftModal(true)}
            className="px-6 py-3 rounded-xl bg-blue-700 hover:bg-blue-800 text-white font-semibold text-xs inline-flex items-center gap-2"
          >
            <Sparkles className="w-4 h-4" /> Draft Proposal Now
          </button>
        </div>
      )}

      {/* AI Draft Proposal Modal */}
      {showDraftModal && (
        <div className="fixed inset-0 bg-white/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-xl p-6 max-w-lg w-full space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-blue-600" /> AI Proposal Co-Pilot
              </h3>
              <button onClick={() => setShowDraftModal(false)} className="text-slate-600 hover:text-slate-900">✕</button>
            </div>

            <p className="text-xs text-slate-600">
              Select a system-detected project opportunity. Gemini AI will structure a complete proposal based on evidence and linked master issues.
            </p>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Project Opportunity</label>
                {oppsLoading ? (
                  <div className="text-slate-600 text-xs">Loading opportunities...</div>
                ) : (
                  <select
                    value={selectedOpportunityId}
                    onChange={(e) => setSelectedOpportunityId(e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-xl p-3 text-slate-900 text-xs"
                  >
                    <option value="" disabled>Select an opportunity...</option>
                    {opportunities?.map((opp) => (
                      <option key={opp.opportunity_id} value={opp.opportunity_id}>
                        {opp.title} ({opp.total_citizen_reports || 0} reports)
                      </option>
                    ))}
                  </select>
                )}
              </div>
            </div>

            <div className="flex justify-end space-x-3 pt-2">
              <button
                onClick={() => setShowDraftModal(false)}
                className="px-4 py-2 rounded-xl bg-slate-50 text-slate-700 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={() => aiDraftMutation.mutate()}
                disabled={aiDraftMutation.isPending || !selectedOpportunityId}
                className="px-5 py-2 rounded-xl bg-blue-700 hover:bg-blue-800 text-white text-xs font-semibold flex items-center gap-1.5"
              >
                {aiDraftMutation.isPending ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" /> Generating Draft...
                  </>
                ) : (
                  <>
                    Generate & Submit Draft <Sparkles className="w-3.5 h-3.5" />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
