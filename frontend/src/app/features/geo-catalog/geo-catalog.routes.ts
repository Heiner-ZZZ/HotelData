import { Routes } from '@angular/router';

export const GEO_CATALOG_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/geo-catalog-page/geo-catalog-page').then((m) => m.GeoCatalogPageComponent),
  },
];
