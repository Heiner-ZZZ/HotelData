import { Routes } from '@angular/router';

export const CHECK_OUTS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./pages/check-outs-page/check-outs-page').then((m) => m.CheckOutsPageComponent)
  },
  {
    path: ':bookingId',
    loadComponent: () => import('./pages/check-out-detail-page/check-out-detail-page').then((m) => m.CheckOutDetailPageComponent)
  }
];
