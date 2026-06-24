import { Routes } from '@angular/router';

export const MANUAL_RESERVATIONS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/manual-reservations-list-page/manual-reservations-list-page').then((m) => m.ManualReservationsListPageComponent)
  },
  {
    path: 'new',
    loadComponent: () =>
      import('./pages/manual-reservation-new-page/manual-reservation-new-page').then((m) => m.ManualReservationNewPageComponent)
  }
];
