import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

import { AuthService } from './auth.service';

/**
 * Prevent redirect loops when multiple API calls fail with 401 simultaneously.
 * Once a redirect is in-flight, further 401s are ignored until the page reloads.
 */
let redirectingToLogin = false;
/** Cooldown timestamp — ignore 401 redirects for N ms after the last one. */
let lastRedirectTime = 0;
const REDIRECT_COOLDOWN_MS = 10000;

function isCredentialedUrl(url: string): boolean {
  return url.startsWith('/api') || url.startsWith('/auth') || url.startsWith('/system') ||
    url.includes('/api/') || url.includes('/auth/') || url.includes('/system/');
}

function isAlreadyOnLogin(): boolean {
  return window.location.pathname === '/login';
}

export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const router = inject(Router);
  const authService = inject(AuthService);
  const credentialedRequest = isCredentialedUrl(request.url)
    ? request.clone({ withCredentials: true })
    : request;

  return next(credentialedRequest).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse && error.status === 401) {
        // ── ANY 401 means unauthenticated ──
        //   REST semantics: 401 = no autenticado, 403 = sin permisos.
        //   Invalidate session and redirect to login with cooldown
        //   to prevent redirect storms when multiple API calls fail.
        authService.invalidateSession();
        const now = Date.now();
        if (
          !redirectingToLogin &&
          now - lastRedirectTime > REDIRECT_COOLDOWN_MS &&
          !isAlreadyOnLogin()
        ) {
          redirectingToLogin = true;
          lastRedirectTime = now;
          const nextUrl = `${window.location.pathname}${window.location.search}`;
          void router.navigate(['/login'], { queryParams: { next: nextUrl } });
          setTimeout(() => { redirectingToLogin = false; }, 5000);
        }
      }
      return throwError(() => error);
    })
  );
};
