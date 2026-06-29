import { Routes } from '@angular/router';

export const LOST_AND_FOUND_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/lost-and-found-page/lost-and-found-page').then((m) => m.LostAndFoundPageComponent),
  },
];
