import { Routes } from '@angular/router';

export const ACCOUNT_ROUTES: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'bookings'
  },
  {
    path: 'bookings',
    loadChildren: () =>
      import('../reservations/reservations.routes').then((m) => m.RESERVATIONS_ROUTES)
  },
  {
    path: 'profile',
    loadComponent: () =>
      import('./pages/profile-page/profile-page').then((m) => m.ProfilePageComponent)
  }
];
