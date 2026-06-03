import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

function isCredentialedUrl(url: string): boolean {
  return url.startsWith('/api') || url.startsWith('/auth') || url.startsWith('/system');
}

function isPublicJsonUrl(url: string): boolean {
  return url.startsWith('/api/hotels');
}

function isAuthProbe(url: string): boolean {
  return url.startsWith('/api/auth/me') || url.startsWith('/api/auth/login');
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
        !isAuthProbe(request.url)
      ) {
        const nextUrl = `${window.location.pathname}${window.location.search}`;
        void router.navigate(['/login'], { queryParams: { next: nextUrl } });
      }
      return throwError(() => error);
    })
  );
};
