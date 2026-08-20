import { apiClient } from './client';
import type { CivicAnalyticsSnapshot, CivicHotspot, CivicProjectOpportunity } from '../types';

export async function getAnalyticsSummary(jurisdictionId?: string): Promise<CivicAnalyticsSnapshot> {
  const response = await apiClient.get<CivicAnalyticsSnapshot>('/analytics/summary', {
    params: { jurisdiction_id: jurisdictionId },
  });
  return response.data;
}

export async function getAnalyticsHotspots(jurisdictionId?: string): Promise<CivicHotspot[]> {
  const response = await apiClient.get<CivicHotspot[]>('/analytics/hotspots', {
    params: { jurisdiction_id: jurisdictionId },
  });
  return response.data;
}

export async function getProjectOpportunities(): Promise<CivicProjectOpportunity[]> {
  const response = await apiClient.get<CivicProjectOpportunity[]>('/project-opportunities');
  return response.data;
}
