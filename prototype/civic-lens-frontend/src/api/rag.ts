import { apiClient } from './client';
import type { GroundedQAResponse } from '../types';

export interface CivicDocumentItem {
  document_id: string;
  doc_id?: string;
  title: string;
  issuing_authority: string;
  document_type: string;
  authority_status: string;
  access_level: string;
  current_version_id?: string;
  source_reference?: string;
  created_at: string;
  updated_at?: string;
}

export async function publicRagQuery(query: string, jurisdictionId?: string): Promise<GroundedQAResponse> {
  const response = await apiClient.post<GroundedQAResponse>('/rag/public/query', {
    query,
    jurisdiction_id: jurisdictionId,
    top_k: 3,
  });
  return response.data;
}

export async function explainRouting(issueId: string): Promise<GroundedQAResponse> {
  const response = await apiClient.get<GroundedQAResponse>(`/rag/explain/routing/${issueId}`);
  return response.data;
}

export async function explainSLA(issueId: string): Promise<GroundedQAResponse> {
  const response = await apiClient.get<GroundedQAResponse>(`/rag/explain/sla/${issueId}`);
  return response.data;
}

export async function listRagDocuments(): Promise<CivicDocumentItem[]> {
  const response = await apiClient.get<CivicDocumentItem[]>('/admin/rag/documents');
  return response.data;
}

export async function ingestRagDocument(formData: FormData): Promise<any> {
  const response = await apiClient.post('/admin/rag/documents/ingest', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}
