export interface AuthUser {
  username: string;
  email: string;
  displayName: string;
  primaryRole: string;
  isActive: boolean;
  avatarUrl: string;
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
  homeHref: string | null;
  permissionCodes: string[];
}

export interface AuthMeDto {
  authenticated: boolean;
  user: {
    user_id?: string;
    username: string;
    email: string;
    display_name?: string;
    primary_role: string;
    is_active?: boolean;
    avatar_url?: string;
  } | null;
  session: {
    token?: string | null;
    session_token?: string | null;
    expires_at: string | null;
    created_at: string | null;
  } | null;
  home_href?: string;
  login_url?: string;
  permission_codes?: string[];
}
