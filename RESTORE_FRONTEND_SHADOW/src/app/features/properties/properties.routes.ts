import { Routes } from '@angular/router';

export const PROPERTIES_ROUTES: Routes = [
  {
    path: ':propertyId',
    loadComponent: () =>
      import('./pages/property-detail-page/property-detail-page').then(
        (m) => m.PropertyDetailPageComponent
      )
  },
  {
    path: '',
    pathMatch: 'full',
    loadComponent: () =>
      import('./pages/properties-list-page/properties-list-page').then(
        (m) => m.PropertiesListPageComponent
      )
  }
];
