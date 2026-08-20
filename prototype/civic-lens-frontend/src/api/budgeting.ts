import { apiClient } from './client';
import type {
  CitizenProposal,
  AIDraftProposalResponse,
  ProposalEligibility,
  ProposalScore,
  BudgetCycle,
  BudgetAllocationResult,
  CivicProjectOpportunity,
} from '../types';

export async function listOpportunities(jurisdictionId?: string): Promise<CivicProjectOpportunity[]> {
  const response = await apiClient.get<CivicProjectOpportunity[]>('/project-opportunities', {
    params: { jurisdiction_id: jurisdictionId },
  });
  return response.data;
}

export async function listProposals(jurisdictionId?: string): Promise<CitizenProposal[]> {
  const response = await apiClient.get<CitizenProposal[]>('/proposals', {
    params: { jurisdiction_id: jurisdictionId },
  });
  return response.data;
}

export async function getProposalDetail(proposalId: string): Promise<CitizenProposal> {
  const response = await apiClient.get<CitizenProposal>(`/proposals/${proposalId}`);
  return response.data;
}

export async function createProposal(payload: {
  title: string;
  description: string;
  category: string;
  opportunity_id?: string;
  author_citizen_id: string;
  requested_budget: number;
  linked_master_issue_ids?: string[];
}): Promise<CitizenProposal> {
  const response = await apiClient.post<CitizenProposal>('/proposals', payload);
  return response.data;
}

export async function generateAIDraftProposal(opportunityId: string, proposerId: string): Promise<AIDraftProposalResponse> {
  const response = await apiClient.post<AIDraftProposalResponse>('/proposals/ai-draft', {
    opportunity_id: opportunityId,
    proposer_id: proposerId,
  });
  return response.data;
}

export async function evaluateEligibility(proposalId: string, cycleId: string = 'cycle_ward7_2027'): Promise<ProposalEligibility> {
  const response = await apiClient.post<ProposalEligibility>(`/proposals/${proposalId}/eligibility`, null, {
    params: { cycle_id: cycleId },
  });
  return response.data;
}

export async function getProposalScore(proposalId: string, cycleId: string = 'cycle_ward7_2027'): Promise<ProposalScore> {
  const response = await apiClient.get<ProposalScore>(`/proposals/${proposalId}/score`, {
    params: { cycle_id: cycleId },
  });
  return response.data;
}

export async function getBudgetCycle(cycleId: string = 'cycle_ward7_2027'): Promise<BudgetCycle> {
  const response = await apiClient.get<BudgetCycle>(`/budget-cycles/${cycleId}`);
  return response.data;
}

export async function castVote(cycleId: string, proposalId: string, citizenId: string = 'citizen_1'): Promise<any> {
  const response = await apiClient.post(`/voting/${cycleId}/vote`, {
    cycle_id: cycleId,
    proposal_id: proposalId,
    citizen_id: citizenId,
  });
  return response.data;
}

export async function getPublicBudgetDashboard(cycleId: string = 'cycle_ward7_2027'): Promise<any> {
  const response = await apiClient.get(`/public/participatory-budgeting/${cycleId}`);
  return response.data;
}

export async function runBudgetAllocation(cycleId: string = 'cycle_ward7_2027'): Promise<BudgetAllocationResult> {
  const response = await apiClient.post<BudgetAllocationResult>(`/admin/budget-cycles/${cycleId}/allocate`);
  return response.data;
}
