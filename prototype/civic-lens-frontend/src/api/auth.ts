import { apiClient } from './client';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: 'CITIZEN' | 'OPERATOR' | 'SUPERVISOR' | 'ADMIN';
  jurisdiction_id: string;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export async function loginUser(email: string, password: string): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>('/auth/login', { email, password });
  return response.data;
}

export async function registerUser(payload: {
  email: string;
  password: string;
  full_name: string;
  role?: string;
}): Promise<User> {
  const response = await apiClient.post<User>('/auth/register', payload);
  return response.data;
}

export async function getMe(token: string): Promise<User> {
  const response = await apiClient.get<User>('/auth/me', {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data;
}
