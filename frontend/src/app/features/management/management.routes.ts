import { Routes } from '@angular/router';

export const MANAGEMENT_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/dashboard-page/dashboard-page').then((m) => m.ManagementDashboardPageComponent)
  },
  {
    path: 'recepcion',
    loadChildren: () =>
      import('../reservations/reservations.routes').then((m) => m.RESERVATIONS_ROUTES)
  },
  {
    path: 'reservations',
    redirectTo: 'recepcion'
  },
  {
    path: 'properties',
    loadChildren: () =>
      import('../properties/properties.routes').then((m) => m.PROPERTIES_ROUTES)
  },
  {
    path: 'availability',
    loadChildren: () =>
      import('../availability/availability.routes').then((m) => m.AVAILABILITY_ROUTES)
  },
  {
    path: 'rooms',
    loadChildren: () =>
      import('../rooms/rooms.routes').then((m) => m.ROOMS_ROUTES)
  },
  {
    path: 'rates',
    loadChildren: () =>
      import('../rates/rates.routes').then((m) => m.RATES_ROUTES)
  },
  {
    path: 'policies',
    loadChildren: () =>
      import('../policies/policies.routes').then((m) => m.POLICIES_ROUTES)
  },
  {
    path: 'amenities',
    loadChildren: () =>
      import('../amenities/amenities.routes').then((m) => m.AMENITIES_ROUTES)
  },
  {
    path: 'check-ins',
    loadChildren: () =>
      import('../check-ins/check-ins.routes').then((m) => m.CHECK_INS_ROUTES)
  },
  {
    path: 'check-outs',
    loadChildren: () =>
      import('../check-outs/check-outs.routes').then((m) => m.CHECK_OUTS_ROUTES)
  },
  {
    path: 'reviews',
    loadChildren: () =>
      import('../reviews/reviews.routes').then((m) => m.REVIEWS_ROUTES)
  },
  {
    path: 'billing',
    loadChildren: () =>
      import('../billing/billing.routes').then((m) => m.BILLING_ROUTES)
  },
  {
    path: 'manual-reservations',
    loadChildren: () =>
      import('../manual-reservations/manual-reservations.routes').then((m) => m.MANUAL_RESERVATIONS_ROUTES)
  },
  {
    path: 'housekeeping',
    loadChildren: () =>
      import('../housekeeping/housekeeping.routes').then((m) => m.HOUSEKEEPING_ROUTES)
  },
  {
    path: 'reports',
    loadComponent: () =>
      import('./pages/reports-page/reports-page').then((m) => m.ManagementReportsPageComponent)
  },
  {
    path: 'audit-log',
    loadComponent: () =>
      import('./pages/audit-log-page/audit-log-page').then((m) => m.AuditLogPageComponent)
  },
  {
    path: 'lost-and-found',
    loadChildren: () =>
      import('../lost-and-found/lost-and-found.routes').then((m) => m.LOST_AND_FOUND_ROUTES)
  },
  {
    path: 'settings',
    loadComponent: () =>
      import('./pages/settings-page/settings-page').then((m) => m.SettingsPageComponent)
  }
];
