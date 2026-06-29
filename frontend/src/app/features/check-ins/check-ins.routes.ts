import { Routes } from '@angular/router';

export const CHECK_INS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./pages/check-ins-page/check-ins-page').then((m) => m.CheckInsPageComponent)
  },
  {
    path: ':bookingId',
    loadComponent: () =>
      import('./pages/check-in-detail-page/check-in-detail-page').then((m) => m.CheckInDetailPageComponent)
  }
];
