import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';

import { AuthService } from './auth.service';
import { SUPERUSER_WILDCARD } from './permission.constants';

function hasAllowedRole(role: string | undefined, allowedRoles: string[] | undefined): boolean {
  if (!allowedRoles?.length) {
    return true;
  }
  return !!role && allowedRoles.includes(role);
}

function hasRequiredPermission(permissionCodes: string[], requiredPermission: string | undefined): boolean {
  if (!requiredPermission) {
    return true;
  }
  // *.* super_admin wildcard grants access to everything
  if (permissionCodes.includes(SUPERUSER_WILDCARD)) {
    return true;
  }
  return permissionCodes.includes(requiredPermission);
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
  const requiredPermission = route.data?.['requiredPermission'] as string | undefined;

  const resolveAuthorizedState = () => {
    const authState = authService.authState();
    if (!authState.authenticated) {
      return router.createUrlTree(['/login']);
    }
    // Permission-based check (migration: OR with legacy roles)
    if (requiredPermission && hasRequiredPermission(authState.permissionCodes, requiredPermission)) {
      return true;
    }
    // Legacy role-based check (backward compat)
    if (hasAllowedRole(authState.user?.primaryRole, allowedRoles)) {
      return true;
    }
    // If either guard was applicable and failed, redirect
    if (requiredPermission || (allowedRoles?.length ?? 0) > 0) {
      return router.parseUrl(authState.homeHref || '/search');
    }
    // No restrictions → allow
    return true;
  };

  if (authService.sessionLoaded()) {
    return resolveAuthorizedState();
  }

  return authService.loadSession().pipe(
    map(() => resolveAuthorizedState()),
    catchError(() => of(router.createUrlTree(['/login'])))
  );
};
