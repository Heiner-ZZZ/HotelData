import { Routes } from '@angular/router';

import { roleGuard } from '../../core/auth/auth.guard';
import { LOST_FOUND_READ } from '../../core/auth/permission.constants';

export const LOST_AND_FOUND_ROUTES: Routes = [
  {
    path: '',
    canActivate: [roleGuard],
    data: { requiredPermission: LOST_FOUND_READ },
    loadComponent: () =>
      import('./pages/lost-and-found-page/lost-and-found-page').then((m) => m.LostAndFoundPageComponent),
  },
];
