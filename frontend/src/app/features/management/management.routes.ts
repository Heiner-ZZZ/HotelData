import { Routes } from '@angular/router';

import { roleGuard } from '../../core/auth/auth.guard';

export const MANAGEMENT_ROUTES: Routes = [
  {
    // TAF14 — Management Overview eliminado (2026-08-23): /management?prop_id=1
    // ya no existe. Entry point de GESTIÓN es dinámico según permisos del
    // usuario (no estático a h01). Si tiene reports.strategic.read → h01,
    // si no → primera ruta de /management que sí tiene permitido
    // (housekeeping → /management/housekeeping, maintenance → housekeeping, etc.).
    // Preserva ?prop_id & ?prop_label. Evita el 403 que veía housekeeping
    // (Carlos) al caer siempre en el estratégico sin permiso.
    path: '',
    pathMatch: 'full',
    loadComponent: () =>
      import('./pages/management-redirect/management-redirect.component').then(
        (m) => m.ManagementRedirectComponent,
      ),
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
    path: 'promotions',
    loadChildren: () =>
      import('../marketing/marketing.routes').then((m) => m.MARKETING_ROUTES)
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
    // Suscripción del dueño a la plataforma (PLAN_SUSCRIPCION_Y_PAGOS.md §14.4).
    path: 'subscription',
    loadComponent: () =>
      import('../subscription/pages/my-subscription-page/my-subscription-page').then(
        (m) => m.MySubscriptionPageComponent
      )
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
    path: 'financial-control',
    loadComponent: () =>
      import('../financial-control/pages/financial-control-page/financial-control-page').then((m) => m.FinancialControlPageComponent)
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
    // Informes estratégicos TAF14 — VISTA A (hotel individual del dueño).
    // Separada de la cartera del sistema (/informes-estrategicos, Vista B):
    // este botón (ítem GESTIÓN) abre SIEMPRE la vista del hotel; el property
    // context inyecta prop_id en modo single/multi. Gate por permiso, igual
    // que el backend /api/strategic/* (el sidebar ya filtra el ítem). Cada
    // informe IE-H0x es una interfaz propia (patrón táctico, menú horizontal).
    path: 'informes-estrategicos',
    canActivate: [roleGuard],
    data: { requiredPermission: 'reports.strategic.read' },
    children: [
      {
        path: '',
        pathMatch: 'full',
        redirectTo: 'h01'
      },
      {
        path: ':report',
        loadComponent: () =>
          import('../system-admin/pages/strategic-dashboard-page/strategic-dashboard-page').then(
            (m) => m.StrategicDashboardPageComponent
          )
      }
    ]
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
    children: [
      {
        path: '',
        pathMatch: 'full',
        loadComponent: () =>
          import('../in-stay/pages/staff-inbox/staff-inbox-page').then((m) => m.StaffInboxPageComponent)
      },
      {
        path: 'folios',
        loadComponent: () =>
          import('../in-stay/pages/staff-inbox/staff-inbox-page').then((m) => m.StaffInboxPageComponent)
      },
      {
        path: 'sessions',
        loadComponent: () =>
          import('../in-stay/pages/staff-inbox/staff-inbox-page').then((m) => m.StaffInboxPageComponent)
      },
      {
        path: 'lost-found',
        loadComponent: () =>
          import('../in-stay/pages/staff-inbox/staff-inbox-page').then((m) => m.StaffInboxPageComponent)
      },
    ]
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
    path: 'team-permissions',
    loadChildren: () =>
      import('../hotel-permissions/hotel-permissions.routes').then((m) => m.HOTEL_PERMISSIONS_ROUTES)
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
