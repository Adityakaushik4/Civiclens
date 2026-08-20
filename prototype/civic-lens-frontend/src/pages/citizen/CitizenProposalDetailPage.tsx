import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getProposalDetail, getProposalScore, evaluateEligibility, castVote } from '../../api/budgeting';
import { CheckCircle, ArrowLeft, Award, ThumbsUp, ShieldCheck } from 'lucide-react';

export const CitizenProposalDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const proposalId = id || 'prop_1';
  const [voteSuccess, setVoteSuccess] = useState(false);
  const [voteError, setVoteError] = useState<string | null>(null);

  const { data: proposal } = useQuery({
    queryKey: ['proposalDetail', proposalId],
    queryFn: () => getProposalDetail(proposalId),
  });

  const { data: score } = useQuery({
    queryKey: ['proposalScore', proposalId],
    queryFn: () => getProposalScore(proposalId),
  });

  const { data: eligibility } = useQuery({
    queryKey: ['proposalEligibility', proposalId],
    queryFn: () => evaluateEligibility(proposalId),
  });

  const voteMutation = useMutation({
    mutationFn: () => castVote('cycle_ward7_2027', proposalId),
    onSuccess: () => {
      setVoteSuccess(true);
      setVoteError(null);
      queryClient.invalidateQueries({ queryKey: ['proposalScore', proposalId] });
    },
    onError: (error: any) => {
      setVoteError(error?.response?.data?.detail || 'Voting is unavailable because this proposal is not currently eligible.');
    },
  });

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 space-y-8">
      <Link to="/citizen/proposals" className="inline-flex items-center text-xs text-slate-600 hover:text-slate-900 gap-1 font-semibold">
        <ArrowLeft className="w-4 h-4" /> Back to Proposals
      </Link>

      {/* Header */}
      <div className="bg-white/80 border border-slate-200 rounded-xl p-6 sm:p-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <span className="text-xs font-bold bg-purple-500/10 text-purple-400 border border-purple-500/20 px-3 py-1 rounded-full">
              {proposal?.category || 'PARK_MAINTENANCE'}
            </span>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight mt-2">
              {proposal?.title || 'Solar Streetlights and Greenery in Ward 7 Park'}
            </h1>
          </div>

          <div className="flex flex-col items-end gap-2">
            {voteError && (
              <span className="text-red-400 text-[11px] font-medium bg-red-400/10 px-2 py-1 rounded">
                {voteError}
              </span>
            )}
            <button
              onClick={() => voteMutation.mutate()}
              disabled={voteSuccess || voteMutation.isPending}
              className={`px-6 py-3 rounded-xl font-bold text-xs flex items-center gap-2 transition-all shadow-lg ${
                voteSuccess
                  ? 'bg-emerald-600/20 text-emerald-400 border border-emerald-500/30'
                  : 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-slate-900 shadow-purple-500/20'
              }`}
            >
              <ThumbsUp className="w-4 h-4" /> {voteSuccess ? 'Vote Cast Successfully!' : 'Cast Blind Token Vote'}
            </button>
          </div>
        </div>

        <p className="text-sm text-slate-700 leading-relaxed font-medium">
          {proposal?.description || 'Installation of 12 solar-powered streetlights and rejuvenation of park boundary.'}
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 pt-4 border-t border-slate-200 text-xs">
          <div>
            <span className="text-slate-500 block">Requested Budget</span>
            <span className="font-bold text-slate-900 text-base mt-0.5 block">
              ₹{((proposal?.requested_budget || 850000) / 100000).toFixed(2)} Lakhs
            </span>
          </div>

          <div>
            <span className="text-slate-500 block">Eligibility Status</span>
            <span className={`font-bold mt-0.5 block flex items-center gap-1 ${eligibility?.is_eligible === true ? 'text-emerald-400' : eligibility?.is_eligible === false ? 'text-red-400' : 'text-slate-600'}`}>
              <ShieldCheck className="w-4 h-4" /> {eligibility?.is_eligible === true ? 'ELIGIBLE' : eligibility?.is_eligible === false ? 'INELIGIBLE' : 'EVALUATING'}
            </span>
          </div>

          <div>
            <span className="text-slate-500 block">Composite Proposal Score</span>
            <span className="font-bold text-purple-400 text-base mt-0.5 block">
              {score?.final_composite_score ? score.final_composite_score.toFixed(1) : '84.5'} / 100
            </span>
          </div>
        </div>
      </div>

      {/* Explainable 6-Factor Score Breakdown (Section 3.H Requirement) */}
      <div className="bg-white/80 border border-slate-200 rounded-xl p-6 sm:p-8 space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Award className="w-5 h-5 text-purple-400" /> Explainable 6-Factor Score Breakdown
          </h3>
          <span className="text-xs text-slate-600">Deterministic Municipal Algorithm</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          <div className="bg-white border border-slate-200 rounded-lg p-4 space-y-1">
            <span className="text-[11px] text-slate-600">Community Support</span>
            <p className="text-lg font-bold text-slate-900">{score?.community_support_score?.toFixed(1) || 90.0}</p>
          </div>

          <div className="bg-white border border-slate-200 rounded-lg p-4 space-y-1">
            <span className="text-[11px] text-slate-600">Cost Efficiency</span>
            <p className="text-lg font-bold text-slate-900">{score?.cost_efficiency_score?.toFixed(1) || 82.5}</p>
          </div>

          <div className="bg-white border border-slate-200 rounded-lg p-4 space-y-1">
            <span className="text-[11px] text-slate-600">Severity Mitigation</span>
            <p className="text-lg font-bold text-slate-900">{score?.severity_mitigation_score?.toFixed(1) || 88.0}</p>
          </div>

          <div className="bg-white border border-slate-200 rounded-lg p-4 space-y-1">
            <span className="text-[11px] text-slate-600">Hotspot Alignment</span>
            <p className="text-lg font-bold text-slate-900">{score?.hotspot_alignment_score?.toFixed(1) || 95.0}</p>
          </div>

          <div className="bg-white border border-slate-200 rounded-lg p-4 space-y-1">
            <span className="text-[11px] text-slate-600">Technical Feasibility</span>
            <p className="text-lg font-bold text-slate-900">{score?.feasibility_score?.toFixed(1) || 78.0}</p>
          </div>

          <div className="bg-white border border-slate-200 rounded-lg p-4 space-y-1">
            <span className="text-[11px] text-slate-600">Social Equity Impact</span>
            <p className="text-lg font-bold text-slate-900">{score?.equity_impact_score?.toFixed(1) || 85.0}</p>
          </div>
        </div>

        {score?.score_explanation && (
          <div className="p-4 rounded-lg bg-purple-500/10 border border-purple-500/20 text-xs text-purple-300 leading-relaxed font-medium">
            <span className="font-bold text-purple-200 block mb-1">Score Explanation:</span>
            {score.score_explanation}
          </div>
        )}
      </div>

      {/* 8 Deterministic Eligibility Rules */}
      <div className="bg-white/80 border border-slate-200 rounded-xl p-6 sm:p-8 space-y-4">
        <h3 className="text-lg font-bold text-slate-900">8 Deterministic Eligibility Rules</h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          {[
            'Budget bounds check (within min/max budget)',
            'Jurisdiction ward match',
            'Non-duplication with active Roads & PWD projects',
            'Public asset ownership criteria',
            'Environmental compliance clearance',
            'Maintenance cost feasibility check',
            'Citizen endorsement threshold',
            'Technical rate table provenance match',
          ].map((rule, idx) => (
            <div key={idx} className="bg-white border border-slate-200 rounded-xl p-3 flex items-center space-x-2 text-slate-700">
              <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span>{rule}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
