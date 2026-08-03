import { Routes } from '@angular/router';

export const RATES_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./pages/rates-page/rates-page').then((m) => m.RatesPageComponent)
  },
  {
    path: 'dashboard',
    loadComponent: () =>
      import('./pages/rates-dashboard-page/rates-dashboard-page').then((m) => m.RatesDashboardPageComponent)
  },
  {
    path: 'calendar',
    loadComponent: () =>
      import('./pages/rates-calendar-dashboard-page/rates-calendar-dashboard-page').then(
        (m) => m.RatesCalendarDashboardPageComponent
      )
  }
];
