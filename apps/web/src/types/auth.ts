export type UserRole = 'ADMIN' | 'PLANNER'

export interface AuthUser {
  id: string
  email: string
  display_name: string
  role: UserRole
}

export interface LoginResponse {
  user: AuthUser
}
