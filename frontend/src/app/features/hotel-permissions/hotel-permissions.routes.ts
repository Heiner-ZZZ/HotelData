import { Routes } from '@angular/router';

import { roleGuard } from '../../core/auth/auth.guard';
import { HOTEL_MANAGE_ROLES } from '../../core/auth/permission.constants';

export const HOTEL_PERMISSIONS_ROUTES: Routes = [
  {
    path: '',
    pathMatch: 'full',
    canActivate: [roleGuard],
    data: { requiredPermission: HOTEL_MANAGE_ROLES },
    loadComponent: () =>
      import('./pages/team-permissions-page/team-permissions-page').then(
        (m) => m.TeamPermissionsPageComponent,
      ),
  },
];
