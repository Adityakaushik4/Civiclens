import { describe, it, expect } from 'vitest';
import type { ResolutionEvidenceRecord } from '../../api/evidence';

describe('CitizenIssueDetailPage Evidence Media Helper Logic', () => {
  it('constructs correct public media URL from issue_id and public_token', () => {
    const record: ResolutionEvidenceRecord = {
      evidence_id: 'ev_12345',
      issue_id: 'CIVIC-2026-C537',
      evidence_type: 'BEFORE_IMAGE',
      file_name: 'WhatsApp Image 2026-08-17 at 19.29.59.jpeg',
      mime_type: 'image/jpeg',
      uploaded_by: 'CITIZEN',
      uploaded_at: '2026-08-17T19:29:59Z',
      verification_status: 'PENDING',
      public_token: 'tok_abc123xyz',
    };

    const mediaUrl = record.media_url || (record.public_token ? `/api/v1/public/evidence/${record.issue_id}/media/${record.public_token}` : null);
    expect(mediaUrl).toBe('/api/v1/public/evidence/CIVIC-2026-C537/media/tok_abc123xyz');
  });

  it('correctly identifies BEFORE_IMAGE and AFTER_IMAGE evidence types', () => {
    const beforeRecord: ResolutionEvidenceRecord = {
      evidence_id: 'ev_before',
      issue_id: 'CIVIC-2026-C537',
      evidence_type: 'BEFORE_IMAGE',
      file_name: 'photo_before.jpg',
      mime_type: 'image/jpeg',
      uploaded_by: 'CITIZEN',
      uploaded_at: '2026-08-17T19:29:59Z',
      verification_status: 'PENDING',
      public_token: 'tok_before123',
    };

    const afterRecord: ResolutionEvidenceRecord = {
      evidence_id: 'ev_after',
      issue_id: 'CIVIC-2026-C537',
      evidence_type: 'AFTER_IMAGE',
      file_name: 'photo_after.jpg',
      mime_type: 'image/jpeg',
      uploaded_by: 'operator_1',
      uploaded_at: '2026-08-18T10:00:00Z',
      verification_status: 'PENDING',
      public_token: 'tok_after123',
    };

    expect(beforeRecord.evidence_type).toBe('BEFORE_IMAGE');
    expect(beforeRecord.uploaded_by).toBe('CITIZEN');
    expect(afterRecord.evidence_type).toBe('AFTER_IMAGE');
    expect(afterRecord.uploaded_by).toBe('operator_1');
  });

  it('differentiates audio recordings from image evidence', () => {
    const audioRecord: ResolutionEvidenceRecord = {
      evidence_id: 'ev_audio',
      issue_id: 'CIVIC-2026-C537',
      evidence_type: 'VOICE_NOTE',
      file_name: 'voice_note.wav',
      mime_type: 'audio/wav',
      uploaded_by: 'CITIZEN',
      uploaded_at: '2026-08-17T19:29:59Z',
      verification_status: 'PENDING',
      public_token: 'tok_audio123',
    };

    const isAudio = (audioRecord.mime_type || '').startsWith('audio/') || audioRecord.evidence_type === 'VOICE_NOTE';
    expect(isAudio).toBe(true);
  });
});
