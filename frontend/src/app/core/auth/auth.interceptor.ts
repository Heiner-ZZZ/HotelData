import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

import { getErrorStatus } from '../../shared/utils/http-error.util';
import { toast } from '../toast/toast.service';

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
  const credentialUrl = isCredentialedUrl(request.url);
  const credentialedRequest = credentialUrl
    ? request.clone({ withCredentials: true })
    : request;

  return next(credentialedRequest).pipe(
    catchError((error: unknown) => {
      // getErrorStatus cubre HttpErrorResponse (tests) y ApiError (defensivo
      // ante reorden de interceptores) — el 401 credentialed siempre redirige.
      if (getErrorStatus(error) === 401 && credentialUrl) {
        // ── Cualquier 401 en endpoint credentialed → sesión inválida ──
        //   El middleware solo retorna 401 cuando `not user`, es decir,
        //   cuando la cookie de sesión no es válida o no existe.
        //   Redirigimos al login SIN limpiar localStorage para que
        //   el flag persista y el próximo page load pueda reintentar.
        const now = Date.now();
        if (
          !redirectingToLogin &&
          now - lastRedirectTime > REDIRECT_COOLDOWN_MS &&
          !isAlreadyOnLogin()
        ) {
          redirectingToLogin = true;
          lastRedirectTime = now;
          toast('Sesión expirada. Redirigiendo al inicio de sesión…', 'error', 2500);
          const nextUrl = `${window.location.pathname}${window.location.search}`;
          void router.navigate(['/login'], { queryParams: { next: nextUrl } });
          setTimeout(() => { redirectingToLogin = false; }, 5000);
        }
      }
      return throwError(() => error);
    })
  );
};
