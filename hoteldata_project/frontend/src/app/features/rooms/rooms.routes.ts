import { Routes } from '@angular/router';

export const ROOMS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./pages/rooms-page/rooms-page').then((m) => m.RoomsPageComponent)
  }
];
