import { apiClient } from './client';
import type {
  ComplaintAnalysis,
  AudioComplaintAnalysisResponse,
  ImageComplaintAnalysisResponse,
  DuplicateCheckResponse,
  LocationExtractionResponse,
  AudioTranscriptionResponse,
} from '../types';

export async function analyzeTextComplaint(text: string): Promise<ComplaintAnalysis> {
  const response = await apiClient.post<ComplaintAnalysis>('/ai/analyze', { text });
  return response.data;
}

export async function analyzeAudioComplaint(audioFile: File): Promise<AudioComplaintAnalysisResponse> {
  const formData = new FormData();
  formData.append('file', audioFile);
  const response = await apiClient.post<AudioComplaintAnalysisResponse>('/ai/analyze-audio', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function analyzeImageComplaint(
  imageFile: File,
  optionalText?: string
): Promise<ImageComplaintAnalysisResponse> {
  const formData = new FormData();
  formData.append('file', imageFile);
  if (optionalText) {
    formData.append('optional_text', optionalText);
  }
  const response = await apiClient.post<ImageComplaintAnalysisResponse>('/ai/analyze-image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function checkDuplicates(payload: {
  text: string;
  category: string;
  subcategory: string;
  latitude: number;
  longitude: number;
  severity: number;
  safety_risk: boolean;
  description: string;
}): Promise<DuplicateCheckResponse> {
  const response = await apiClient.post<DuplicateCheckResponse>('/ai/duplicates/check', payload);
  return response.data;
}

export async function transcribeAudio(audioFile: File): Promise<AudioTranscriptionResponse> {
  const formData = new FormData();
  formData.append('file', audioFile);
  const response = await apiClient.post<AudioTranscriptionResponse>('/ai/transcribe-audio', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function extractLocationClues(text: string): Promise<LocationExtractionResponse> {
  const response = await apiClient.post<LocationExtractionResponse>('/ai/extract-location', { text });
  return response.data;
}

