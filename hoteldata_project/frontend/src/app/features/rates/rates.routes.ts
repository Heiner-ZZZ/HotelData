import { Routes } from '@angular/router';

export const RATES_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./pages/rates-page/rates-page').then((m) => m.RatesPageComponent)
  }
];
