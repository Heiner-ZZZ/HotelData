import { Routes } from '@angular/router';

export const ADMIN_ROUTES: Routes = [
  {
    path: '',
    redirectTo: 'bsc',
    pathMatch: 'full',
  },
  {
    path: 'bsc',
    loadComponent: () =>
      import('./pages/bsc-page/bsc-page').then((m) => m.BscPageComponent),
  },
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
];
