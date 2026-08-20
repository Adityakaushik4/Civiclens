import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getPublicBudgetDashboard, castVote } from '../../api/budgeting';
import { useAuth } from '../../context/AuthContext';
import { CheckCircle2, ThumbsUp, AlertCircle, Loader2 } from 'lucide-react';

export const CitizenVotingPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { userId } = useAuth();
  const [voteError, setVoteError] = useState<string | null>(null);

  const { data: dashboardData, isLoading } = useQuery({
    queryKey: ['publicBudgetDashboard', 'cycle_ward7_2027'],
    queryFn: () => getPublicBudgetDashboard('cycle_ward7_2027'),
  });

  const voteMutation = useMutation({
    mutationFn: (proposalId: string) => castVote('cycle_ward7_2027', proposalId, userId),
    onSuccess: () => {
      setVoteError(null);
      queryClient.invalidateQueries({ queryKey: ['publicBudgetDashboard'] });
    },
    onError: (error: any) => {
      setVoteError(error?.response?.data?.detail || 'Failed to cast vote. You may have already voted or the cycle is closed.');
    },
  });

  const eligibleProposals = dashboardData?.proposals?.filter((p: any) => p.status === 'ELIGIBLE') || [];

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 sm:px-6 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
          Participatory Budget Voting
        </h1>
        <p className="text-xs text-slate-600 mt-1">
          Review eligible community proposals and cast your vote to allocate public funds.
          {dashboardData?.total_budget ? ` Total Pool: ₹${(dashboardData.total_budget / 100000).toFixed(0)} Lakhs` : ''}
        </p>
      </div>

      {voteError && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
          <p className="text-sm text-red-300">{voteError}</p>
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-12 text-slate-500 text-xs flex flex-col items-center">
          <Loader2 className="w-6 h-6 animate-spin mb-2" />
          Loading eligible proposals...
        </div>
      ) : eligibleProposals.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {eligibleProposals.map((prop: any) => (
            <div
              key={prop.proposal_id}
              className="bg-white/80 border border-slate-200 rounded-xl p-6 hover:border-slate-300 transition-all space-y-4 flex flex-col justify-between"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200 px-2.5 py-1 rounded-full">
                    {prop.category}
                  </span>
                  <span className="text-xs text-emerald-400 font-semibold flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> ELIGIBLE
                  </span>
                </div>

                <h3 className="text-base font-bold text-slate-900 leading-snug">{prop.title}</h3>
                
                <div className="flex items-center justify-between text-xs py-2">
                  <span className="text-slate-500">Requested Budget:</span>
                  <span className="text-slate-900 font-bold">₹{(prop.requested_budget / 100000).toFixed(2)} Lakhs</span>
                </div>
                
                <div className="flex items-center justify-between text-xs py-2 border-t border-slate-200">
                  <span className="text-slate-500">Current Votes:</span>
                  <span className="text-blue-700 font-bold text-sm">{prop.vote_count || 0}</span>
                </div>
              </div>

              <div className="pt-2">
                <button
                  onClick={() => voteMutation.mutate(prop.proposal_id)}
                  disabled={voteMutation.isPending}
                  className="w-full py-2.5 rounded-xl bg-blue-700 hover:bg-blue-800 text-white font-semibold text-xs flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                >
                  {voteMutation.isPending ? (
                    <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Voting...</>
                  ) : (
                    <><ThumbsUp className="w-3.5 h-3.5" /> Cast Vote</>
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white/60 border border-slate-200 rounded-xl p-12 text-center space-y-4">
          <ThumbsUp className="w-12 h-12 text-slate-500 mx-auto" />
          <h3 className="text-lg font-bold text-slate-900">No Eligible Proposals to Vote On</h3>
          <p className="text-xs text-slate-600 max-w-sm mx-auto">
            Proposals are currently being submitted or reviewed. Check back later once proposals have been marked as eligible for voting.
          </p>
        </div>
      )}
    </div>
  );
};
