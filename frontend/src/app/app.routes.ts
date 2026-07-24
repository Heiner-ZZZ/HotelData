import { Routes } from '@angular/router';

import { authGuard, roleGuard } from './core/auth/auth.guard';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'welcome'
  },
  {
    path: 'welcome',
    loadComponent: () =>
      import('./features/welcome/pages/welcome-page/welcome-page').then((m) => m.WelcomePageComponent)
  },
  {
    path: 'login',
    loadComponent: () =>
      import('./core/auth/login-page').then((m) => m.LoginPageComponent)
  },
  {
    path: 'register',
    loadComponent: () =>
      import('./core/auth/register-page').then((m) => m.RegisterPageComponent)
  },
  {
    path: 'onboarding/alojamiento',
    loadComponent: () =>
      import('./features/onboarding/onboarding-property').then((m) => m.OnboardingPropertyComponent)
  },
  {
    path: 'recover',
    loadComponent: () =>
      import('./core/auth/recover-page').then((m) => m.RecoverPageComponent)
  },
  {
    path: 'reset',
    loadComponent: () =>
      import('./core/auth/reset-page').then((m) => m.ResetPageComponent)
  },
  {
    path: 'verify-email',
    loadComponent: () =>
      import('./core/auth/verify-email-page').then((m) => m.VerifyEmailPageComponent)
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
        path: 'hotels/compare',
        loadChildren: () =>
          import('./features/hotel-compare/hotel-compare.routes').then((m) => m.HOTEL_COMPARE_ROUTES)
      },
      {
        path: 'hotels',
        loadChildren: () =>
          import('./features/hotel-detail/hotel-detail.routes').then((m) => m.HOTEL_DETAIL_ROUTES)
      },
      {
        path: 'reservations',
        pathMatch: 'full',
        redirectTo: '/account/bookings'
      }
    ]
  },
  {
    path: 'account',
    loadComponent: () =>
      import('./core/layout/account-shell/account-shell').then((m) => m.AccountShellComponent),
    canActivate: [authGuard, roleGuard],
    data: {
      requiredPermission: 'account.read',
      allowedRoles: ['super_admin', 'admin_sistema', 'cliente', 'recepcionista', 'hotel_partner', 'gerente_hotel', 'revenue_manager', 'marketing_hotelero', 'operador_datos', 'auditor_datos', 'maintenance', 'housekeeping', 'concierge']
    },
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
    canActivate: [authGuard, roleGuard],
    data: {
      requiredPermission: 'dashboard.read',
      allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel', 'revenue_manager', 'marketing_hotelero', 'operador_datos', 'auditor_datos', 'maintenance', 'recepcionista', 'housekeeping', 'concierge']
    },
    children: [
      {
        path: '',
        loadChildren: () =>
          import('./features/management/management.routes').then((m) => m.MANAGEMENT_ROUTES)
      },
      {
        path: 'hr',
        loadChildren: () =>
          import('./features/hr/hr.routes').then((m) => m.HR_ROUTES)
      },
    ]
  },
  {
    path: 'ownership',
    loadComponent: () =>
      import('./core/layout/system-admin-shell/system-admin-shell').then((m) => m.SystemAdminShellComponent),
    canActivate: [authGuard, roleGuard],
    data: {
      requiredPermission: 'users.manage',
      allowedRoles: ['super_admin']
    },
    children: [
      {
        path: '',
        loadChildren: () =>
          import('./features/ownership/ownership.routes').then((m) => m.OWNERSHIP_ROUTES)
      }
    ]
  },
  {
    path: 'system',
    loadComponent: () =>
      import('./core/layout/system-admin-shell/system-admin-shell').then((m) => m.SystemAdminShellComponent),
    canActivate: [authGuard, roleGuard],
    data: {
      requiredPermission: 'users.read',
      allowedRoles: ['super_admin', 'admin_sistema', 'operador_datos', 'auditor_datos']
    },
    children: [
      {
        path: '',
        loadChildren: () =>
          import('./features/system-admin/system-admin.routes').then((m) => m.SYSTEM_ADMIN_ROUTES)
      }
    ]
  },
  {
    path: 'reservations/new',
    pathMatch: 'full',
    redirectTo: 'account/bookings/new'
  },
  {
    path: 'admin',
    pathMatch: 'full',
    redirectTo: 'admin/global-settings'
  },
  {
    path: 'admin',
    loadComponent: () =>
      import('./core/layout/system-admin-shell/system-admin-shell').then((m) => m.SystemAdminShellComponent),
    canActivate: [authGuard, roleGuard],
    data: {
      requiredPermission: 'users.read',
      allowedRoles: ['super_admin', 'admin_sistema', 'operador_datos', 'auditor_datos']
    },
    children: [
      {
        path: '',
        loadChildren: () =>
          import('./features/admin/admin.routes').then((m) => m.ADMIN_ROUTES)
      }
    ]
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
    path: 'admin/settings',
    redirectTo: 'management/settings'
  },
  {
    path: 'stay',
    loadComponent: () =>
      import('./features/in-stay/pages/guest-portal/guest-portal-page').then((m) => m.GuestPortalPageComponent)
  },
  {
    path: 'stay/:token',
    loadComponent: () =>
      import('./features/in-stay/pages/guest-portal/guest-portal-page').then((m) => m.GuestPortalPageComponent)
  },
  {
    path: '**',
    redirectTo: 'welcome'
  }
];
