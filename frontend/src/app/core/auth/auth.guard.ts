import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';

import { ToastService } from '../../shared/services/toast.service';
import { AuthService } from './auth.service';
import { hasAllowedRole, hasRequiredPermission } from './route-access';
import { pickFirstAccessibleManagementHref } from '../../features/management/management-redirect';

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
  const toast = inject(ToastService);
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
    // If either guard was applicable and failed, announce it globally and
    // redirect home. Red toast (error), same vocabulary used by the HTTP
    // error boundary for backend 403s, so navigation and action denials
    // feel identical — a denied access is an error, not a warning.
    if (requiredPermission || (allowedRoles?.length ?? 0) > 0) {
      toast.error('No tienes permiso para acceder a esta sección.');
      // Para dashboards estratégicos sin permiso, redirigir dinámicamente a
      // la primera ruta de /management que sí tiene permitido (no estático
      // a /search). Es dinámico porque depende de permissionCodes del usuario
      // (housekeeping → /management/housekeeping, maintenance → housekeeping/hr, etc.).
      if (requiredPermission?.startsWith('reports.strategic')) {
        const href = pickFirstAccessibleManagementHref(
          authState.permissionCodes,
          authState.user?.primaryRole ?? null,
        );
        const qp = (route as unknown as { queryParams?: Record<string, string> }).queryParams ?? {};
        return router.createUrlTree([href], { queryParams: qp });
      }
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
