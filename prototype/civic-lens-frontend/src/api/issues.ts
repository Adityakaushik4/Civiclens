import { apiClient } from './client';
import type {
  PriorityAssessmentResult,
  RoutingDecisionResult,
  IssueLifecycleRecord,
  PublicIssueView,
  PublicTimelineEntry,
  MasterIssueModel,
} from '../types';

export async function getMasterIssues(): Promise<MasterIssueModel[]> {
  const response = await apiClient.get<MasterIssueModel[]>('/ai/master-issues');
  return response.data;
}

export async function calculatePriority(payload: {
  category: string;
  subcategory: string;
  severity: number;
  safety_risk: boolean;
  public_impact: number;
  location_description?: string;
  latitude: number;
  longitude: number;
}): Promise<PriorityAssessmentResult> {
  const response = await apiClient.post<PriorityAssessmentResult>('/priority/calculate', payload);
  return response.data;
}

export async function routeIssue(payload: {
  category: string;
  subcategory: string;
  priority_score: number;
  priority_level: string;
  jurisdiction_id?: string;
  latitude?: number;
  longitude?: number;
  issue_id?: string;
}): Promise<RoutingDecisionResult> {
  const response = await apiClient.post<RoutingDecisionResult>('/routing/route', payload);
  return response.data;
}

export async function submitCitizenReport(formData: FormData): Promise<RoutingDecisionResult> {
  const response = await apiClient.post<RoutingDecisionResult>('/issues/citizen-report', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function acknowledgeIssue(issueId: string, operatorId: string = 'operator_1', notes?: string): Promise<IssueLifecycleRecord> {
  const response = await apiClient.post<IssueLifecycleRecord>(`/routing/${issueId}/acknowledge`, {
    operator_id: operatorId,
    notes,
  });
  return response.data;
}

export async function startWork(issueId: string, operatorId: string = 'operator_1', notes?: string): Promise<IssueLifecycleRecord> {
  const response = await apiClient.post<IssueLifecycleRecord>(`/work/${issueId}/start`, null, {
    params: { operator_id: operatorId, notes },
  });
  return response.data;
}

export async function submitCompletion(issueId: string, operatorId: string = 'operator_1', notes?: string): Promise<IssueLifecycleRecord> {
  const response = await apiClient.post<IssueLifecycleRecord>(`/work/${issueId}/submit-completion`, {
    operator_id: operatorId,
    notes,
  });
  return response.data;
}

export async function reopenIssue(issueId: string, reason: string, notes?: string): Promise<IssueLifecycleRecord> {
  const response = await apiClient.post<IssueLifecycleRecord>(`/issues/${issueId}/reopen`, {
    actor_id: 'citizen_1',
    reason,
    notes,
  });
  return response.data;
}

export async function getPublicIssueView(anonymizedId: string): Promise<PublicIssueView> {
  const response = await apiClient.get<PublicIssueView>(`/public/issues/${anonymizedId}`);
  return response.data;
}

export async function getPublicIssueTimeline(anonymizedId: string): Promise<PublicTimelineEntry[]> {
  const response = await apiClient.get<PublicTimelineEntry[]>(`/public/issues/${anonymizedId}/timeline`);
  return response.data;
}
