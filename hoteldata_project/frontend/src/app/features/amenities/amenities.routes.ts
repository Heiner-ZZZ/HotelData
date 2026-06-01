import { Routes } from '@angular/router';

export const AMENITIES_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./pages/amenities-page/amenities-page').then((m) => m.AmenitiesPageComponent)
  }
];
