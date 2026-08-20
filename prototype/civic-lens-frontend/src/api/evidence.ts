import { apiClient } from './client';

export interface ResolutionEvidenceRecord {
  evidence_id: string;
  issue_id: string;
  evidence_type: 'BEFORE_IMAGE' | 'AFTER_IMAGE' | 'VOICE_NOTE' | 'WORK_LOG' | 'COMPLETION_CERTIFICATE';
  file_name: string;
  mime_type: string;
  uploaded_by: string;
  uploaded_at: string;
  verification_status: 'PENDING' | 'APPROVED' | 'REJECTED';
  public_token?: string;
  media_url?: string;
}

export interface VerificationRecord {
  verification_id: string;
  evidence_id: string;
  issue_id: string;
  verifier_id: string;
  decision: 'APPROVED' | 'REJECTED';
  rejection_reason?: string;
  verified_at: string;
}

export async function uploadEvidence(
  issueId: string,
  evidenceType: 'BEFORE_IMAGE' | 'AFTER_IMAGE' | 'WORK_LOG' | 'COMPLETION_CERTIFICATE',
  file: File,
  uploadedBy: string = 'operator_1'
): Promise<ResolutionEvidenceRecord> {
  const formData = new FormData();
  formData.append('issue_id', issueId);
  formData.append('evidence_type', evidenceType);
  formData.append('uploaded_by', uploadedBy);
  formData.append('file', file);

  const response = await apiClient.post<ResolutionEvidenceRecord>('/evidence/upload', formData, {
    headers: { 'Content-Type': undefined },
  });
  return response.data;
}

export async function getIssueEvidence(issueId: string): Promise<{
  issue_id: string;
  evidence: ResolutionEvidenceRecord[];
  verifications: VerificationRecord[];
}> {
  const response = await apiClient.get<{
    issue_id: string;
    evidence: ResolutionEvidenceRecord[];
    verifications: VerificationRecord[];
  }>(`/evidence/${issueId}`);
  return response.data;
}

export async function verifyEvidence(
  evidenceId: string,
  decision: 'APPROVED' | 'REJECTED',
  verifierId: string = 'supervisor_1',
  rejectionReason?: string
): Promise<VerificationRecord> {
  const response = await apiClient.post<VerificationRecord>(`/evidence/${evidenceId}/verify`, {
    evidence_id: evidenceId,
    verifier_id: verifierId,
    decision,
    rejection_reason: rejectionReason,
  });
  return response.data;
}

export interface SupervisorVerificationQueueItem {
  evidence_id: string;
  issue_id: string;
  title: string;
  category: string;
  status: string;
  submitted_by: string;
  department: string;
  assigned_unit?: string;
  assigned_crew?: string;
  work_started: string;
  work_completed: string;
  before_image_url?: string;
  after_image_url?: string;
  before_captured?: string;
  after_captured?: string;
  location: string;
  ai_metadata: {
    exif_sanitized: boolean;
    gps_match: string;
    timestamp: string;
    resolution_match_confidence: number;
  };
  reopen_history: number;
  escalated: boolean;
}

export async function getVerificationQueue(): Promise<SupervisorVerificationQueueItem[]> {
  const response = await apiClient.get<SupervisorVerificationQueueItem[]>('/supervisor/verification-queue');
  return response.data;
}
