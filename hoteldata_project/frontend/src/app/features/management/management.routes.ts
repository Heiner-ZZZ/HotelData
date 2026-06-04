import { Routes } from '@angular/router';

import { PlaceholderFeaturePageComponent } from '../shared-placeholder/placeholder-feature-page.component';

export const MANAGEMENT_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/dashboard-page/dashboard-page').then((m) => m.ManagementDashboardPageComponent)
  },
  {
    path: 'reservations',
    loadChildren: () =>
      import('../reservations/reservations.routes').then((m) => m.RESERVATIONS_ROUTES)
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
    path: 'reports',
    loadComponent: () =>
      import('./pages/reports-page/reports-page').then((m) => m.ManagementReportsPageComponent)
  },
  {
    path: 'settings',
    component: PlaceholderFeaturePageComponent,
    data: {
      title: 'Configuracion',
      description: 'Ruta preparada para perfil del hotel, usuarios, roles e integraciones.'
    }
  }
];
