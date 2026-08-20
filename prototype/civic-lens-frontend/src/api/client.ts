import axios from 'axios';

// Base Axios instance
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120000,
});

// Interceptor for attaching auth token and admin key headers
apiClient.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('civiclens_jwt_token') || localStorage.getItem('civiclens_jwt_token');
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  const adminKey = localStorage.getItem('civiclens_admin_key') || 'admin-secret-key';
  config.headers['X-Admin-API-Key'] = adminKey;
  return config;
});

// User friendly error transformer
export function formatApiError(error: any): string {
  if (axios.isAxiosError(error)) {
    if (error.response?.status === 429 || error.response?.status === 503) {
      return 'AI services are temporarily busy. Your report has been saved locally and will process shortly.';
    }
    if (error.response?.status === 413) {
      return 'Uploaded file exceeds the maximum 10MB limit.';
    }
    if (error.response?.status === 415) {
      return 'File format not supported. Please upload JPG, PNG, WAV, or MP3.';
    }
    if (error.response?.data?.detail) {
      return typeof error.response.data.detail === 'string'
        ? error.response.data.detail
        : JSON.stringify(error.response.data.detail);
    }
  }
  return error?.message || 'An unexpected error occurred. Please try again.';
}
