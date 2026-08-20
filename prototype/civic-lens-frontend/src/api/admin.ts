import { apiClient } from './client';

export interface SLAPolicyItem {
  policy_id: string;
  jurisdiction_id: string;
  category: string;
  subcategory?: string;
  priority_level: string;
  acknowledgement_minutes: number;
  resolution_minutes: number;
  status: string;
  source_reference?: string;
  source_title?: string;
  active: boolean;
}

export interface ReopenPolicyItem {
  policy_id: string;
  jurisdiction_id: string;
  enabled: boolean;
  reopen_threshold: number;
  escalation_target: string;
  status: string;
  active: boolean;
}

export async function listSlaPolicies(): Promise<SLAPolicyItem[]> {
  const response = await apiClient.get<SLAPolicyItem[]>('/admin/sla-policies');
  return response.data;
}

export async function createSlaPolicy(payload: Partial<SLAPolicyItem>): Promise<SLAPolicyItem> {
  const response = await apiClient.post<SLAPolicyItem>('/admin/sla-policies', payload);
  return response.data;
}

export async function listReopenPolicies(): Promise<ReopenPolicyItem[]> {
  const response = await apiClient.get<ReopenPolicyItem[]>('/admin/reopen-policies');
  return response.data;
}

export async function createReopenPolicy(payload: Partial<ReopenPolicyItem>): Promise<ReopenPolicyItem> {
  const response = await apiClient.post<ReopenPolicyItem>('/admin/reopen-policies', payload);
  return response.data;
}
