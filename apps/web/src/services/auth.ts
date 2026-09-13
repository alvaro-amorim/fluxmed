import { apiRequest } from './api'
import type { AuthUser, LoginResponse } from '../types/auth'

export function getCurrentUser(): Promise<AuthUser> {
  return apiRequest<AuthUser>('/api/v1/auth/me')
}

export function login(email: string, password: string): Promise<LoginResponse> {
  return apiRequest<LoginResponse>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export function logout(): Promise<void> {
  return apiRequest<void>('/api/v1/auth/logout', { method: 'POST' })
}
