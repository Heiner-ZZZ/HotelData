import { Routes } from '@angular/router';

export const PROPERTIES_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/properties-list-page/properties-list-page').then((m) => m.PropertiesListPageComponent)
  },
  {
    path: ':propertyId',
    loadComponent: () =>
      import('./pages/property-detail-page/property-detail-page').then((m) => m.PropertyDetailPageComponent)
  }
];
