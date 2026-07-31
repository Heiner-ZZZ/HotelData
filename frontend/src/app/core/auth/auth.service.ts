import { HttpClient } from '@angular/common/http';
import { computed, inject, Injectable, signal } from '@angular/core';
import { catchError, map, of, tap } from 'rxjs';

import { toast } from '../toast/toast.service';
import { API_CONFIG } from '../api/api.config';
import type { AuthMeDto, AuthState } from './auth.models';
import { SUPERUSER_WILDCARD, type PermissionCode } from './permission.constants';

/**
 * Re-export `AuthUser` as a named type so feature services can do
 * ``as AuthUser | null`` narrowing on ``AuthService.currentUser()`` without
 * having to import from ``./auth.models``. Derived from ``AuthState['user']``
 * so any future shape change in ``AuthState.user`` propagates here for free.
 */
export type AuthUser = NonNullable<AuthState['user']>;

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

  /**
   * Check if the current user has a specific permission code (or the
   * ``*.*`` superuser wildcard). Available for component-level
   * permission checks (action buttons, nav menus, route guards).
   *
   * Reads ``permissionCodes`` directly from the underlying signal, so
   * callers that wrap this in a ``computed()`` will recompute whenever
   * the user's permission set changes (login, logout, role elevation,
   * session expiry). A plain method call in a template-only context
   * is also reactive: Angular re-renders the template on every signal
   * change, which re-evaluates this method.
   *
   * History: this was previously a ``computed()`` returning a closure
   * (``this.auth.hasPermission()('shifts.create')``). That shape was
   * unintuitive and tripped TS2554 in callers; it has been replaced by
   * this plain method so callers write
   * ``this.auth.hasPermission('shifts.create')`` directly.
   */
  hasPermission(code: PermissionCode): boolean {
    const codes = this.authStateSignal().permissionCodes;
    if (codes.includes(SUPERUSER_WILDCARD)) return true;
    return codes.includes(code);
  }

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
