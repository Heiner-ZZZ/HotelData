import { Routes } from '@angular/router';

export const MANAGEMENT_ROUTES: Routes = [
  {
    path: '',
    pathMatch: 'full',
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
    path: 'guests',
    loadChildren: () =>
      import('../guests/guests.routes').then((m) => m.GUESTS_ROUTES)
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
    path: 'products',
    loadChildren: () =>
      import('../products/products.routes').then((m) => m.PRODUCTS_ROUTES)
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
    path: 'hr',
    loadChildren: () =>
      import('../hr/hr.routes').then((m) => m.HR_ROUTES)
  },
  {
    path: 'expenses',
    loadChildren: () =>
      import('../expenses/expenses.routes').then((m) => m.EXPENSES_ROUTES)
  },
  {
    path: 'revenue',
    redirectTo: 'reports'
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
    path: 'stay-inbox',
    loadComponent: () =>
      import('../in-stay/pages/staff-inbox/staff-inbox-page').then((m) => m.StaffInboxPageComponent)
  },
  {
    path: 'service-requests',
    loadComponent: () =>
      import('../in-stay/pages/service-requests-dashboard-page/service-requests-dashboard-page').then(
        (m) => m.ServiceRequestsDashboardPageComponent
      )
  },
  {
    path: 'shifts',
    loadChildren: () =>
      import('../shifts/shifts.routes').then((m) => m.SHIFTS_ROUTES)
  },
  {
    path: 'settings',
    loadComponent: () =>
      import('./pages/settings-page/settings-page').then((m) => m.SettingsPageComponent)
  },
  {
    path: 'profile',
    loadComponent: () =>
      import('../account/pages/profile-page/profile-page').then((m) => m.ProfilePageComponent)
  }
];
