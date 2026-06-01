import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';

import { AuthService } from './auth.service';

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
