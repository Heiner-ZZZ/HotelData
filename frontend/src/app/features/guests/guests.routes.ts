import { Routes } from '@angular/router';

export const GUESTS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/guests-page/guests-page').then((m) => m.GuestsPageComponent),
  },
];
