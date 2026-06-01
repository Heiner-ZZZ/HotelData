import { Routes } from '@angular/router';

export const AVAILABILITY_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/availability-page/availability-page').then(
        (m) => m.AvailabilityPageComponent
      )
  }
];
