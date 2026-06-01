export interface AuthUser {
  username: string;
  email: string;
  primaryRole: string;
  isActive: boolean;
}

export interface AuthSession {
  token: string | null;
  expiresAt: string | null;
  createdAt: string | null;
}

export interface AuthState {
  authenticated: boolean;
  user: AuthUser | null;
  session: AuthSession | null;
}

export interface AuthMeDto {
  authenticated: boolean;
  user: {
    username: string;
    email: string;
    primary_role: string;
    is_active: boolean;
  } | null;
  session: {
    token: string | null;
    expires_at: string | null;
    created_at: string | null;
  } | null;
}
