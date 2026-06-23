import { Routes } from '@angular/router';

import { roleGuard } from '../../core/auth/auth.guard';

export const OWNERSHIP_ROUTES: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'users'
  },
  {
    path: 'users',
    loadComponent: () =>
      import('./pages/ownership-list-page/ownership-list-page').then((m) => m.OwnershipListPageComponent),
    canActivate: [roleGuard],
    data: { allowedRoles: ['super_admin'] }
  },
  {
    path: 'users/new',
    loadComponent: () =>
      import('./pages/ownership-create-page/ownership-create-page').then((m) => m.OwnershipCreatePageComponent),
    canActivate: [roleGuard],
    data: { allowedRoles: ['super_admin'] }
  },
  {
    path: 'users/:userId',
    loadComponent: () =>
      import('./pages/ownership-user-detail-page/ownership-user-detail-page').then((m) => m.OwnershipUserDetailPageComponent),
    canActivate: [roleGuard],
    data: { allowedRoles: ['super_admin'] }
  }
];
