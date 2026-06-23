import { HttpClient } from '@angular/common/http';
import { computed, inject, Injectable, signal } from '@angular/core';
import { catchError, map, of, tap } from 'rxjs';

import { API_CONFIG } from '../api/api.config';
import type { AuthMeDto, AuthState } from './auth.models';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  private readonly authStateSignal = signal<AuthState>({
    authenticated: false,
    user: null,
    session: null,
    homeHref: null
  });
  private readonly sessionLoadedSignal = signal(false);

  readonly authState = this.authStateSignal.asReadonly();
  readonly currentUser = computed(() => this.authStateSignal().user);
  readonly isAuthenticated = computed(() => this.authStateSignal().authenticated);
  readonly sessionLoaded = this.sessionLoadedSignal.asReadonly();

  loadSession() {
    return this.http
      .get<AuthMeDto>(`${this.apiConfig.baseUrl}/auth/me`, { withCredentials: true })
      .pipe(
        map((dto) => this.mapAuthState(dto)),
        tap((state) => {
          this.authStateSignal.set(state);
          this.sessionLoadedSignal.set(true);
        }),
        catchError(() => {
          const anonymousState: AuthState = {
            authenticated: false,
            user: null,
            session: null,
            homeHref: null
          };
          this.authStateSignal.set(anonymousState);
          this.sessionLoadedSignal.set(true);
          return of(anonymousState);
        })
      );
  }

  login(identifier: string, password: string, nextUrl: string | null = null, rememberMe: boolean = false) {
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
        })
      );
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
            isActive: dto.user.is_active ?? true
          }
        : null,
      session: dto.session
        ? {
            token: dto.session.token ?? dto.session.session_token ?? null,
            expiresAt: dto.session.expires_at,
            createdAt: dto.session.created_at
          }
        : null,
      homeHref: dto.home_href ?? null
    };
  }
}
