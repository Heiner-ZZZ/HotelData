import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

/**
 * Prevent redirect loops when multiple API calls fail with 401 simultaneously.
 * Once a redirect is in-flight, further 401s are ignored until the page reloads.
 */
let redirectingToLogin = false;

function isCredentialedUrl(url: string): boolean {
  return url.startsWith('/api') || url.startsWith('/auth') || url.startsWith('/system');
}

function isPublicJsonUrl(url: string): boolean {
  return url.startsWith('/api/hotels');
}

function isAuthProbe(url: string): boolean {
  return url.startsWith('/api/auth/me') || url.startsWith('/api/auth/login');
}

function isAlreadyOnLogin(): boolean {
  return window.location.pathname === '/login';
}

export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const router = inject(Router);
  const credentialedRequest = isCredentialedUrl(request.url)
    ? request.clone({ withCredentials: true })
    : request;

  return next(credentialedRequest).pipe(
    catchError((error: unknown) => {
      if (
        error instanceof HttpErrorResponse &&
        error.status === 401 &&
        isCredentialedUrl(request.url) &&
        !isPublicJsonUrl(request.url) &&
        !isAuthProbe(request.url) &&
        !redirectingToLogin &&
        !isAlreadyOnLogin()
      ) {
        redirectingToLogin = true;
        const nextUrl = `${window.location.pathname}${window.location.search}`;
        void router.navigate(['/login'], { queryParams: { next: nextUrl } });
        // Reset the flag after a timeout so future navigations can redirect again
        setTimeout(() => { redirectingToLogin = false; }, 5000);
      }
      return throwError(() => error);
    })
  );
};
