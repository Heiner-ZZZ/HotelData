import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';

import { AuthService } from './auth.service';

function hasAllowedRole(role: string | undefined, allowedRoles: string[] | undefined): boolean {
  if (!allowedRoles?.length) {
    return true;
  }
  return !!role && allowedRoles.includes(role);
}

export const authGuard: CanActivateFn = (_route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.isAuthenticated()) {
    return true;
  }

  return authService.loadSession().pipe(
    map((sessionState) =>
      sessionState.authenticated
        ? true
        : router.createUrlTree(['/login'], { queryParams: { next: state.url } })
    ),
    catchError(() => of(router.createUrlTree(['/login'], { queryParams: { next: state.url } })))
  );
};

export const roleGuard: CanActivateFn = (route) => {
  const authService = inject(AuthService);
  const router = inject(Router);
  const allowedRoles = route.data?.['allowedRoles'] as string[] | undefined;

  const resolveAuthorizedState = () => {
    const authState = authService.authState();
    if (!authState.authenticated) {
      return router.createUrlTree(['/login']);
    }
    if (hasAllowedRole(authState.user?.primaryRole, allowedRoles)) {
      return true;
    }
    return router.parseUrl(authState.homeHref || '/search');
  };

  if (authService.sessionLoaded()) {
    return resolveAuthorizedState();
  }

  return authService.loadSession().pipe(
    map(() => resolveAuthorizedState()),
    catchError(() => of(router.createUrlTree(['/login'])))
  );
};
