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
    session: null
  });

  readonly authState = this.authStateSignal.asReadonly();
  readonly currentUser = computed(() => this.authStateSignal().user);
  readonly isAuthenticated = computed(() => this.authStateSignal().authenticated);

  loadSession() {
    return this.http
      .get<AuthMeDto>(`${this.apiConfig.baseUrl}/auth/me`, { withCredentials: true })
      .pipe(
        map((dto) => this.mapAuthState(dto)),
        tap((state) => this.authStateSignal.set(state)),
        catchError(() => {
          const anonymousState: AuthState = {
            authenticated: false,
            user: null,
            session: null
          };
          this.authStateSignal.set(anonymousState);
          return of(anonymousState);
        })
      );
  }

  private mapAuthState(dto: AuthMeDto): AuthState {
    return {
      authenticated: dto.authenticated,
      user: dto.user
        ? {
            username: dto.user.username,
            email: dto.user.email,
            primaryRole: dto.user.primary_role,
            isActive: dto.user.is_active
          }
        : null,
      session: dto.session
        ? {
            token: dto.session.token,
            expiresAt: dto.session.expires_at,
            createdAt: dto.session.created_at
          }
        : null
    };
  }
}
