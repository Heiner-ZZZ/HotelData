import { Routes } from '@angular/router';

import { authGuard } from './core/auth/auth.guard';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'search'
  },
  {
    path: '',
    loadComponent: () =>
      import('./core/layout/public-shell/public-shell').then((m) => m.PublicShellComponent),
    children: [
      {
        path: 'search',
        loadChildren: () =>
          import('./features/hotel-search/hotel-search.routes').then((m) => m.HOTEL_SEARCH_ROUTES)
      },
      {
        path: 'hotels',
        loadChildren: () =>
          import('./features/hotel-detail/hotel-detail.routes').then((m) => m.HOTEL_DETAIL_ROUTES)
      },
      {
        path: 'login',
        loadComponent: () =>
          import('./core/auth/login-redirect-page').then((m) => m.LoginRedirectPageComponent)
      },
      {
        path: 'reservations',
        loadChildren: () =>
          import('./features/reservations/reservations.routes').then((m) => m.RESERVATIONS_ROUTES)
      }
    ]
  },
  {
    path: 'account',
    loadComponent: () =>
      import('./core/layout/account-shell/account-shell').then((m) => m.AccountShellComponent),
    canActivate: [authGuard],
    children: [
      {
        path: '',
        loadChildren: () => import('./features/account/account.routes').then((m) => m.ACCOUNT_ROUTES)
      }
    ]
  },
  {
    path: 'management',
    loadComponent: () =>
      import('./core/layout/management-shell/management-shell').then((m) => m.ManagementShellComponent),
    canActivate: [authGuard],
    children: [
      {
        path: '',
        loadChildren: () =>
          import('./features/management/management.routes').then((m) => m.MANAGEMENT_ROUTES)
      },
    ]
  },
  {
    path: 'system',
    loadComponent: () =>
      import('./core/layout/system-admin-shell/system-admin-shell').then((m) => m.SystemAdminShellComponent),
    canActivate: [authGuard],
    children: [
      {
        path: '',
        loadChildren: () =>
          import('./features/system-admin/system-admin.routes').then((m) => m.SYSTEM_ADMIN_ROUTES)
      }
    ]
  },
  {
    path: 'reservations',
    pathMatch: 'full',
    redirectTo: 'account/bookings'
  },
  {
    path: 'reservations/new',
    pathMatch: 'full',
    redirectTo: 'account/bookings/new'
  },
  {
    path: 'admin',
    pathMatch: 'full',
    redirectTo: 'management'
  },
  {
    // Legacy compatibility aliases preserved while /management is the primary experience.
    path: 'admin/properties',
    redirectTo: 'management/properties'
  },
  {
    path: 'admin/availability',
    redirectTo: 'management/availability'
  },
  {
    path: 'admin/reservations',
    redirectTo: 'management/reservations'
  },
  {
    path: '**',
    redirectTo: 'search'
  }
];
