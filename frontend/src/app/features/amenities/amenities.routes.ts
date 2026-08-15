import { Routes } from '@angular/router';

const amenitiesPage = () =>
  import('./pages/amenities-page/amenities-page').then((m) => m.AmenitiesPageComponent);

export const AMENITIES_ROUTES: Routes = [
  {
    // Legacy URL: /management/amenities?prop_id=N
    path: '',
    pathMatch: 'full',
    redirectTo: 'servicios'
  },
  {
    // Both sections share one route config. Angular reuses the component when
    // only this parameter changes, so the property selector stays mounted.
    path: ':section',
    loadComponent: amenitiesPage
  }
];
