import { Routes } from '@angular/router';

export const RESERVATIONS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/reservations-list-page/reservations-list-page').then((m) => m.ReservationsListPageComponent)
  },
  {
    path: 'new',
    loadComponent: () =>
      import('./pages/reservation-new-page/reservation-new-page').then((m) => m.ReservationNewPageComponent)
  },
  {
    path: 'confirmed/:bookingId',
    loadComponent: () =>
      import('./pages/booking-confirmed-page/booking-confirmed-page').then((m) => m.BookingConfirmedPageComponent)
  },
  {
    path: ':bookingId',
    loadComponent: () =>
      import('./pages/reservation-detail-page/reservation-detail-page').then((m) => m.ReservationDetailPageComponent)
  }
];
