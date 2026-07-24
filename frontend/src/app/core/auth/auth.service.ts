import { HttpClient } from '@angular/common/http';
import { computed, inject, Injectable, signal } from '@angular/core';
import { catchError, map, of, tap } from 'rxjs';

import { toast } from '../toast/toast.service';
import { API_CONFIG } from '../api/api.config';
import type { AuthMeDto, AuthState } from './auth.models';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  private readonly SESSION_FLAG_KEY = 'hoteldata_session';

  private readonly authStateSignal = signal<AuthState>({
    authenticated: false,
    user: null,
    session: null,
    homeHref: null,
    permissionCodes: [],
  });
  private readonly sessionLoadedSignal = signal(false);

  /** Check if there's a saved session flag from a previous login. */
  private _hasStoredSession(): boolean {
    try {
      return localStorage.getItem(this.SESSION_FLAG_KEY) === '1';
    } catch {
      return false;
    }
  }

  /** Save a flag so future page loads know a session may exist. */
  private _saveSessionFlag(): void {
    try {
      localStorage.setItem(this.SESSION_FLAG_KEY, '1');
    } catch { /* localStorage unavailable */ }
  }

  /** Clear the session flag (logout or session expired). */
  private _clearSessionFlag(): void {
    try {
      localStorage.removeItem(this.SESSION_FLAG_KEY);
    } catch { /* localStorage unavailable */ }
  }

  /** Invalidate session without requiring an API call — used when auth
   *  interceptor detects a 401 so guards immediately block access. */
  invalidateSession(): void {
    this._clearSessionFlag();
    this.authStateSignal.set({
      authenticated: false,
      user: null,
      session: null,
      homeHref: null,
      permissionCodes: [],
    });
  }

  readonly authState = this.authStateSignal.asReadonly();
  readonly currentUser = computed(() => this.authStateSignal().user);
  readonly isAuthenticated = computed(() => this.authStateSignal().authenticated);
  readonly sessionLoaded = this.sessionLoadedSignal.asReadonly();

  /** Update the current user's avatar URL in the auth state so the
   *  top-nav and other components that read currentUser react immediately. */
  updateAvatar(avatarUrl: string): void {
    const state = this.authStateSignal();
    if (!state.user) return;
    this.authStateSignal.set({
      ...state,
      user: { ...state.user, avatarUrl },
    });
  }

  /** Check if the current user has a specific permission code (or *.*).
   *  Available for component-level permission checks (e.g. nav menus). */
  readonly hasPermission = computed(() => {
    const codes = this.authStateSignal().permissionCodes;
    if (codes.includes('*.*')) return (_code: string) => true;
    return (code: string) => codes.includes(code);
  });

  loadSession() {
    // If no stored session flag, skip the HTTP call entirely — avoids a
    // browser console 401 log for first-time / anonymous visitors.
    if (!this._hasStoredSession()) {
      const anonymousState: AuthState = {
        authenticated: false,
        user: null,
        session: null,
        homeHref: null,
        permissionCodes: [],
      };
      this.authStateSignal.set(anonymousState);
      this.sessionLoadedSignal.set(true);
      return of(anonymousState);
    }

    return this.http
      .get<AuthMeDto>(`${this.apiConfig.baseUrl}/auth/me`, { withCredentials: true })
      .pipe(
        map((dto) => this.mapAuthState(dto)),
        tap((state) => {
          // If the flag exists but the backend says unauthenticated,
          // the session expired — show a brief notification before
          // the guard redirects to /login.
          if (!state.authenticated) {
            toast('Sesión expirada. Redirigiendo al inicio de sesión…', 'error', 2500);
          }
          this.authStateSignal.set(state);
          this.sessionLoadedSignal.set(true);
        }),
        catchError(() => {
          // Session flag was stale — session expired or invalidated
          toast('Sesión expirada. Redirigiendo al inicio de sesión…', 'error', 2500);
          this._clearSessionFlag();
          const anonymousState: AuthState = {
            authenticated: false,
            user: null,
            session: null,
            homeHref: null,
            permissionCodes: [],
          };
          this.authStateSignal.set(anonymousState);
          this.sessionLoadedSignal.set(true);
          return of(anonymousState);
        })
      );
  }

  login(identifier: string, password: string, nextUrl: string | null = null, rememberMe = false) {
    return this.http
      .post<AuthMeDto>(
        `${this.apiConfig.baseUrl}/auth/login`,
        {
          identifier,
          password,
          next: nextUrl ?? '',
          remember_me: rememberMe
        },
        { withCredentials: true }
      )
      .pipe(
        map((dto) => this.mapAuthState(dto)),
        tap((state) => {
          this.authStateSignal.set(state);
          this.sessionLoadedSignal.set(true);
          if (state.authenticated) {
            this._saveSessionFlag();
          }
        })
      );
  }

  /**
   * Resolve where an authenticated user should land after entering a public
   * entry route (login, welcome, future marketing pages).
   * Priority: explicit user override (saved dashboard) → server-supplied
   * homeHref → public search fallback. Shared by `LoginPageComponent` and
   * `WelcomePageComponent` so the redirect behavior stays consistent.
   */
  resolveDefaultDestination(defaultHref: string | null): string {
    try {
      const saved = localStorage.getItem('hoteldata-default-dashboard');
      if (saved) return saved;
    } catch { /* localStorage unavailable */ }
    return defaultHref || '/search';
  }

  ensureSessionLoaded() {
    if (this.sessionLoadedSignal()) {
      return of(this.authStateSignal());
    }
    return this.loadSession();
  }

  private mapAuthState(dto: AuthMeDto): AuthState {
    return {
      authenticated: dto.authenticated,
      user: dto.user
        ? {
            username: dto.user.username,
            email: dto.user.email,
            displayName: dto.user.display_name || dto.user.username,
            primaryRole: dto.user.primary_role,
            primaryRoleId: dto.user.primary_role_id || '',
            isActive: dto.user.is_active ?? true,
            avatarUrl: dto.user.avatar_url ?? ''
          }
        : null,
      session: dto.session
        ? {
            token: dto.session.token ?? dto.session.session_token ?? null,
            expiresAt: dto.session.expires_at,
            createdAt: dto.session.created_at
          }
        : null,
      homeHref: dto.home_href ?? null,
      permissionCodes: dto.permission_codes ?? [],
    };
  }
}
