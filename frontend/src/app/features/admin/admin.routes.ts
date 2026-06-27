import { Routes } from '@angular/router';

export const ADMIN_ROUTES: Routes = [
  {
    path: 'earnings',
    loadComponent: () =>
      import('./pages/earnings-page/earnings-page').then((m) => m.EarningsPageComponent),
  },
  {
    path: 'global-settings',
    loadComponent: () =>
      import('./pages/global-settings-page/global-settings-page').then((m) => m.GlobalSettingsPageComponent),
  },
  // Map & Geo-localization (CU-O35 to CU-O38)
  ...(await import('../../features/map/map.routes')).MAP_ROUTES,

  // Billing (CU-O24, CU-O25)
  {
    path: 'billing',
    loadChildren: () =>
      import('../../features/billing/billing.routes').then((m) => m.BILLING_ROUTES),
  },

  // Geographic Catalog
  {
    path: 'geo-catalog',
    loadChildren: () =>
      import('../../features/geo-catalog/geo-catalog.routes').then((m) => m.GEO_CATALOG_ROUTES),
  },
];
